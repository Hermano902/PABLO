Primes – Architecture

This document describes how primes are implemented. The conceptual contract lives in CONCEPT.md; implement and extend primes according to both.


1. Base Class (core.prime_base.Prime)
All primes inherit from the abstract base class `Prime` in `core/prime_base.py`. It provides:

- Identity: `self.name` — the prime's canonical name (e.g. "READ").
- Lifecycle hooks: `initialize()` and `shutdown()` for startup and graceful teardown.
- Thread safety: `self._lock` (reentrant lock) and `self._shutdown_flag` (threading.Event) shared across all prime instances.
- Abstract interface: `__call__(context)` — every prime must implement this.

Lifecycle:
  initialize()     called once at system startup; sets _initialized = True; calls _on_initialize()
  __call__(ctx)    called on every invocation; must return a Compound (consultation mode)
  shutdown()       called at system teardown; sets _shutdown_flag; calls _on_shutdown()

Override `_on_initialize()` and `_on_shutdown()` for prime-specific setup/teardown logic. Never override `initialize()` or `shutdown()` directly.


2. Module Structure and Singleton Pattern
Each prime lives in its own file under `primes/` named exactly after the prime (e.g. `primes/READ.py`). The file exports a single lowercase singleton instance:

```python
# primes/READ.py
class READ(Prime):
    def __call__(self, context):
        ...

read = READ()   # singleton exported at module level
```

No other prime imports `READ` methods or helpers directly. The only valid interface is the singleton instance. Internal helpers are private (prefix `_`).


3. The __call__ Interface
Every prime implements `__call__(context: dict) -> Compound`. The context dict has no fixed schema — each prime defines and documents what keys it expects. Primes should be tolerant of missing keys (use `.get()` with defaults).

In consultation mode, `__call__` must always return a valid `Compound`. In autonomous mode (perceptors and SYMBOL), `__call__` may return `None` after pushing to a queue.

Each prime documents its own expected context keys and return shape in its file's module docstring. That is the authoritative per-prime contract; this document defines only the shared interface.

```python
# Caller (e.g. THINK)
import importlib
data_mod = importlib.import_module("primes.DATA")
result = data_mod.data({"mode": "structure", "tokens": [...]})
# result is a Compound — no other access to DATA's internals
```


4. Dynamic Import (No Static Cross-Prime Imports)
Primes never statically import each other. All cross-prime calls go through `importlib` at runtime:

```python
mod = importlib.import_module("primes.KNOW")
compound = mod.know({"action": "store", "compound": c})
```

Benefits: no circular imports, true encapsulation, and primes can evolve independently without breaking static dependency graphs.


5. Execution Modes

On-demand (all primes)
- Called directly by THINK or another prime via dynamic import.
- Runs synchronously in the caller's thread.
- Must return a Compound.

Autonomous primes: READ, SEE, HEAR (perceptors) and SYMBOL (interpretation)
- SEE and HEAR are dormant until their modality is implemented.
- Started via `initialize()`, which spawns a daemon thread.
- Perceptors: thread runs a continuous loop: sample → change detection → queue push → sleep. Pushes raw observation dicts to `observation_queue`.
- SYMBOL: thread runs a continuous loop: pull from `observation_queue` → run specialists → push near-compound candidates to `candidate_queue`. Also accepts on-demand calls from THINK/KNOW (consultation mode) to ground a specific placeholder compound.
- Autonomous primes do not return a Compound from their thread; they push to queues.
- Exempt from the compound-only rule in autonomous mode.
- Thread is stopped cleanly via `shutdown()` / `_shutdown_flag`.

```python
# READ autonomous thread skeleton
def _observation_loop(self):
    while self._running:
        self._check_shutdown()
        sample = self._acquire_sample()
        if self._has_changed(sample):
            obs = self._build_observation(sample)
            if not observation_queue.full():
                observation_queue.put(obs)
            self._update_state(sample)
        time.sleep(self._sample_interval)
```


6. Queues
`core/queues.py` exports four bounded queues:

- `observation_queue` (maxsize=10000): Perceptors push raw observation dicts; SYMBOL's autonomous thread pulls from it. No other prime reads or writes to this queue.
- `candidate_queue` (maxsize=10000): SYMBOL pushes near-compound candidate dicts; DATA's background thread pulls from it. No other prime reads or writes to this queue.
- `response_queue` (maxsize=1000): THINK pushes response dicts; the GUI timer drains it. No prime reads or writes to this queue except THINK (writer) and the GUI timer (reader).
- `think_queue` (maxsize=1000): DATA pushes conscious-trigger signals after committing a `conscious_trigger=True` utterance compound to KNOW. THINK's background thread pulls from it.

Queue-full behavior: the item is dropped and a metric counter is incremented. Autonomous primes must never block on a full queue.

Conscious trigger flow:
READ marks utterances as conscious triggers by setting `"conscious_trigger": True` in the
observation dict when an utterance boundary is detected (Enter key / newline). This flag
travels through SYMBOL (passes it through untouched) and DATA (passes it through; once the
utterance compound is committed to KNOW, DATA pushes to `think_queue`). THINK wakes and
finds complete, valid data already in KNOW.


7. Raw Observation Format
Autonomous perceptors push dicts with this minimal shape:

```python
{
    "timestamp":  float,        # seconds since epoch
    "modality":   str,          # "READ" | "SEE" | "HEAR"
    "event_type": str,          # modality-specific (e.g. "line", "appearance", "sound_onset")
    "data":       dict,         # modality-specific payload
    "metadata":   dict          # source, confidence, etc.
}
```

This format is consumed by SYMBOL (pulled from `observation_queue`). Any extension must remain backward-compatible.

SYMBOL pushes near-compound candidates to `candidate_queue` with this shape:

```python
{
    "timestamp":         float,     # seconds since epoch — from the source observation
    "modality":          str,       # "READ" | "SEE" | "HEAR" — inherited from source
    "candidate_primes":  list[str], # e.g. ["MOVE", "LEFT", "ENTITY"]
    "roles":             dict,      # prime → span mapping, e.g. {"ENTITY": [0, 3]}
    "spans":             list,      # character or token spans from source
    "confidence":        float,     # 0.0–1.0 — specialist confidence score
    "provenance":        str,       # "heuristic" | "llm:<model_id>"
    "raw_input":         dict       # the original observation dict — kept for traceability
}
```

This format is consumed by DATA (pulled from `candidate_queue`). Any extension must remain backward-compatible.


8. Thread Safety
- All mutable state in a prime must be accessed under `self._lock` (reentrant).
- Use `_thread_safe_execute(fn, *args)` for convenience when wrapping critical sections.
- Perceptor tracking structures (cooldown caches, object trackers) are private and always accessed under the lock.


9. Error Handling
- Raise `PrimeError` (from `core.prime_base`) for execution failures.
- Perceptor threads must catch all exceptions internally, log them, and continue the loop — a crash in the observation loop must not bring down the thread silently.
- Queue full and malformed sample errors are non-fatal; increment the relevant metric and continue.


10. Adding a New Prime
1. Create `primes/MYPRIME.py` with a class `MYPRIME(Prime)`.
2. Implement `__call__(context)` returning a Compound.
3. Override `_on_initialize()` and `_on_shutdown()` if needed.
4. Export `myprime = MYPRIME()` at module level.
5. Document the expected context keys and return shape in the file's docstring.
6. If the prime requires autonomous execution, add a daemon thread in `_on_initialize()`.


See CONCEPT.md for the conceptual contract and prime groupings.
See core/prime_base.py for the base class implementation.
See core/queues.py for the observation queue definition.
