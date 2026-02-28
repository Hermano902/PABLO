SELF – Architecture

This document describes how SELF is implemented. The conceptual contract lives in CONCEPT.md;
implement SELF according to both.


1. Module and Singleton

SELF lives in primes/SELF.py and exports a singleton instance:

```python
# primes/SELF.py
from core.prime_base import Prime

class SELF(Prime):
    ...

self_ = SELF()   # singleton — note: 'self' is reserved in Python, use 'self_'
```


2. Threading Model

SELF runs one daemon thread that monitors observation_queue (early alert phase).
The KNOW Layer 1 commit callback runs in KNOW's input thread — SELF does not own that thread.

```
Main process
  └── SELF monitor thread   (reads observation_queue for source metadata — non-destructive)
  └── KNOW input thread     → fires _on_utterance_committed() callback (runs in KNOW's thread)
  └── think_queue           ← SELF writes here from KNOW's thread (thread-safe queue)
```

SELF's observation_queue tap is **non-destructive**: it peeks at items but does not consume
them. SYMBOL's thread is the consumer. SELF reads source metadata only.

Implementation note: because Python's queue.Queue does not support peeking, SELF uses a
separate lightweight tap mechanism. observation_queue items are also forwarded to a
`self._tap_queue` (internal, maxsize=100) that SELF's monitor thread drains:

```python
# core/queues.py
def register_tap(tap_queue: queue.Queue):
    """Register a queue to receive copies of all items pushed to observation_queue."""
    _taps.append(tap_queue)

def put_observation(obs: dict):
    """Put to observation_queue and forward to all registered taps."""
    observation_queue.put(obs)
    for tap in _taps:
        try:
            tap.put_nowait(obs)
        except queue.Full:
            pass   # tap overflowed — drop silently; this is a non-critical early alert
```

SELF registers its tap queue in `_on_initialize()`:

```python
def _on_initialize(self):
    self._tap_queue = queue.Queue(maxsize=100)
    register_tap(self._tap_queue)
    know.register_layer1_listener(self._on_utterance_committed)
    self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
    self._monitor_thread.start()
```


3. Monitor Loop (Early Alert Phase)

The monitor thread reads source metadata from the tap queue and scores early salience:

```python
def _monitor_loop(self):
    while self._running:
        try:
            obs = self._tap_queue.get(timeout=0.1)
            self._handle_early_observation(obs)
        except queue.Empty:
            continue

def _handle_early_observation(self, obs: dict):
    source = obs.get("metadata", {}).get("source", "unknown")
    early_salience = self._early_salience_score(source)
    if early_salience > 0:
        # Signal THINK to begin pre-loading (Phase 2 — not yet implemented)
        self._pending_sources[obs.get("timestamp")] = source
```

In Phase 1, `_handle_early_observation` only records the pending source. The pre-load
signal to THINK is a Phase 2 feature.


4. Layer 1 Commit Callback (Dispatch Phase)

This method is called by KNOW's input thread when a Layer 1 utterance compound is stored:

```python
def _on_utterance_committed(self, utterance_id: int, source: str):
    if self.suspended:
        return
    salience = self._compute_salience(source)
    if salience < self._attention_threshold:
        return
    item = {
        "utterance_compound_id": utterance_id,
        "timestamp":             time.time(),
        "source":                source,
        "salience":              salience,
        "want_context":          self._active_want_goal(),
        "feel_state":            self._feel_state(),
    }
    think_queue.put(item)
```


5. Salience Computation

Phase 1 uses fixed base scores with Narrative-aware modifiers:

```python
BASE_SALIENCE = {
    "keyboard": 1.0,
    "gui":      1.0,
    "stdin":    1.0,
    "vision":   0.4,
    "audio":    0.4,
    "internal": 0.2,
}
ATTENTION_THRESHOLD = 0.3   # below this → THINK is not woken

def _compute_salience(self, source: str) -> float:
    base = BASE_SALIENCE.get(source, 0.2)
    want_mod, feel_mul = self._get_narrative_modifiers(source)
    return base * (1.0 + want_mod) * feel_mul

def _get_narrative_modifiers(self, source: str) -> tuple[float, float]:
    """Read THIS_USER.current from Relational Narrative. Returns (want_mod, feel_mul)."""
    narrative = know.narrative_by_source(source)
    if narrative is None:
        return 0.0, 1.0   # neutral modifiers for unknown source
    binding = narrative.bindings.get("THIS_USER")
    if binding is None:
        return 0.0, 1.0
    rel_quality = binding.current.get("relationship_quality", 0.0)
    feel_state = binding.current.get("emotional_register", "neutral")
    feel_mul = {"warm": 1.3, "neutral": 1.0, "guarded": 0.5, "closed": 0.1}.get(feel_state, 1.0)
    return rel_quality, feel_mul
```

In Phase 1, `_active_want_goal()` returns `"default"` and `_feel_state()` returns `"neutral"`
since WANT and FEEL sub-primes are not yet independently implemented.


6. The suspended Flag

```python
self.suspended: bool = True   # starts suspended during boot
```

SELF starts suspended. The boot sequence calls `self_.suspended = False` once
the system is fully initialised. While suspended, all `_on_utterance_committed` calls
return immediately without dispatching.


7. Queue Boundaries

```
observation_queue   →  SELF tap (non-destructive copy via register_tap)
KNOW layer1 notify  →  SELF._on_utterance_committed() callback
think_queue         ←  SELF writes
```

SELF never reads from candidate_queue.
SELF never calls SYMBOL, DATA, or READ.
SELF never writes to KNOW.
SELF never writes to response_queue.


8. Phase 1 Scope

  ✅ Tap registration on observation_queue (non-destructive, via register_tap)
  ✅ KNOW Layer 1 listener registration
  ✅ Fixed base salience scores per source
  ✅ Narrative-aware modifier (reads THIS_USER.current from KNOW)
  ✅ Attention threshold gate (default 0.3)
  ✅ Dispatches to think_queue with full context dict
  ✅ suspended flag (starts True, cleared after boot)
  ❌ Early preparation signal to THINK (Phase 2)
  ❌ Dynamic WANT-based goal scoring (Phase 2)
  ❌ Independent FEEL sub-prime multiplier (Phase 2)
  ❌ Overload detection / think_queue depth monitoring (Phase 2)
