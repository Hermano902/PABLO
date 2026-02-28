Perceptors – Architecture

This document describes how perceptors are implemented. The conceptual contract lives in CONCEPT.md; implement perceptors according to both.

Phase 1 scope: READ is the only active perceptor. SEE and HEAR are dormant until their modalities are implemented.


1. Perceptor as a Prime
Each perceptor is a class (READ, SEE, HEAR) that inherits from `Prime` (see docs/PRIMES/PRIMES_ARCHITECTURE.md). The base class provides lifecycle hooks, thread safety, and the `__call__` interface.

Perceptors extend the base by adding:
- A daemon thread for autonomous sampling (started in `_on_initialize()`).
- Internal change-detection state (cooldown cache, modality-specific trackers).
- A `_running` flag controlled by `initialize()` / `shutdown()`.

Each perceptor exports a singleton instance at module level:

```python
# primes/READ.py
class READ(Prime):
    ...
read = READ()
```


2. Threading Model
Each perceptor runs one daemon thread, started in `_on_initialize()` and stopped via `_running = False` + `_shutdown_flag` in `shutdown()`.

```
Main process
  └── READ thread  (autonomous loop: sample → change detect → queue push → sleep)
  └── SEE thread   (dormant — not started until SEE is implemented)
  └── HEAR thread  (dormant — not started until HEAR is implemented)
```

Consultation mode (`__call__`) runs synchronously in the caller's thread — no thread switching. The caller receives a Compound directly.

Threads are daemon threads: they do not block process exit.


3. Autonomous Loop
The background loop follows this fixed sequence for every perceptor:

```
1. acquire sample       — obtain raw data from the environment
2. change detection     — compare with internal state; skip if unchanged
3. flood protection     — check cooldown cache; skip if same event emitted recently
4. build observation    — construct raw observation dict
5. queue push           — non-blocking put; drop + log if queue is full
6. update state         — update tracking state for next iteration
7. sleep                — configurable interval to control sampling rate
```

Skeleton (matches READ implementation):

```python
def _observation_loop(self):
    while self._running:
        try:
            sample = self._acquire_sample()
            if self._has_changed(sample):
                if not self._is_on_cooldown(sample):
                    obs = self._build_observation(sample)
                    if not observation_queue.full():
                        observation_queue.put(obs)
                    else:
                        self._drop_count += 1
                    self._update_state(sample)
        except Exception as e:
            self._log_error(e)   # log and continue — never let the loop die silently
        time.sleep(self._sample_interval)
```


4. Change Detection — Per Modality

READ (Phase 1 — active)
- Streaming input (stdin): each new non-empty line is a change. Emit one observation per line.
- Deduplication: hash the text; if the same hash was emitted within `_send_cooldown` seconds, skip.
- Cache cleanup: entries older than 5 minutes are evicted to prevent unbounded growth.

SEE (dormant)
- Maintain a set of tracked objects with IDs, positions, and semantic states.
- Per frame: update positions via centroid tracking; detect events (appearance, disappearance, state change, interaction).
- Emit one observation per event, not per frame.

HEAR (dormant)
- Detect sound events via amplitude threshold or a small classifier.
- Emit one observation per onset event (new sound starts), not continuously.


5. Flood Protection
Each perceptor maintains a fixed-size cache mapping `(event_type, entity_id)` → `last_emission_time`.

- Cooldown period: configurable per perceptor (default 100 ms for READ). Duplicate events for the same entity within the cooldown window are suppressed.
- Cache eviction: entries older than a configurable max age (default 5 minutes) are removed periodically to prevent unbounded growth.
- READ implementation uses `_recent_sent` (set of hashes) and `_last_sent_time` (dict of hash → timestamp).


6. Raw Observation Format
All perceptors emit dicts with this shape:

```python
{
    "timestamp":  float,   # time.time()
    "modality":   str,     # "READ" | "SEE" | "HEAR"
    "event_type": str,     # "line" | "appearance" | "state_change" | "sound_onset" | ...
    "data":       dict,    # modality-specific payload (see below)
    "metadata":   dict     # source, confidence, prime name, mode
}
```

READ data payload:
```python
{
    "text":               str,    # raw input text
    "preliminary_tokens": list,   # whitespace-split tokens
    "token_count":        int
}
```

Note: the current READ implementation uses `raw_input` and `preliminary_tokens` at the top level rather than nested under `data`. This must be corrected to the format above on the next refactor of READ.py. The target format is specified in docs/PRIMES/PERCEPTORS/READ/READ_ARCHITECTURE.md section 4.

SEE data payload (future):
```python
{
    "object_id":    str,
    "event":        str,   # "appeared" | "disappeared" | "state_changed" | "interacted"
    "new_state":    str,
    "position":     dict   # {"x": float, "y": float}
}
```

HEAR data payload (future):
```python
{
    "event":        str,   # "onset" | "offset"
    "sound_class":  str,
    "amplitude":    float
}
```


7. Consultation Mode
Called directly by THINK (or another prime) via dynamic import. Runs in the caller's thread.
- Bypasses change detection and the queue entirely.
- Reads the current state of the modality synchronously.
- Returns a Compound with `id=-1` (ephemeral; KNOW assigns a permanent ID if stored).

READ context contract:
```python
# Any of these keys trigger consultation mode:
{"mode": "consultation", "input": str}
{"input": str}
{"query": str}
{"text": str}
```

READ returns a Compound with:
- `primebit` encoding the READ prime
- `text` set to the input text
- `compound_type = "data"`
- `provenance_data` recording source, tokens, timestamp, and mode


8. Integration with DATA and KNOW
- `observation_queue` is consumed by DATA's background thread (one consumer, multiple producers).
- DATA structures each raw observation into token-level compounds and passes them to KNOW for storage.
- Perceptors have no direct reference to DATA or KNOW; the queue is their only output channel in autonomous mode.


9. Configuration Parameters

Parameter              Default    Description
_sample_interval       0.01 s     Sleep time between autonomous loop iterations
_send_cooldown         0.1 s      Minimum time between identical observations
cache_max_age          300 s      Max age of cooldown cache entries before eviction
cache_max_size         1000       Max entries in cooldown cache before forced cleanup
observation_queue      maxsize=10000   Defined in core/queues.py; shared across all perceptors


10. Pre-Refinement Boundary
Perceptors perform only mechanical filtering — operations that require zero semantic judgment:

- Deduplication: identical input within the cooldown window is dropped (hash-based).
- Empty / malformed samples: null frames, empty strings, corrupt buffers are discarded silently.
- Queue backpressure: observations are dropped when the queue is full; drop count is incremented.

Everything else belongs in DATA:
- Tokenisation quality and normalisation
- Relevance scoring
- Structural interpretation and placeholder creation
- Provenance tracking

Rationale: a perceptor has no knowledge of what KNOW already contains, no ability to assign confidence, and no audit trail for dropped data. Moving semantic filtering into a perceptor would violate domain ownership and make data loss invisible to the rest of the system. If DATA throughput is insufficient, the correct fix is to scale DATA workers or tune queue capacity — not to push logic upstream into perceptors. The queue drop-rate metric is the observable signal for DATA backpressure.


11. Error Handling
- The autonomous loop must never exit silently. All exceptions inside the loop are caught, logged, and the loop continues after a brief back-off sleep (1.0 s).
- Queue full: observation is dropped; `_drop_count` is incremented. Never block on `queue.put()`.
- Malformed samples (sensor returns garbage): discard and continue; log at debug level.
- Shutdown: `_running = False` is set before joining the thread with a 2-second timeout.


See CONCEPT.md for the conceptual contract and modality descriptions.
See docs/PRIMES/PRIMES_ARCHITECTURE.md for the base Prime class and lifecycle.
See docs/PRIMES/PERCEPTORS/READ/ for READ's specific concept and architecture.
See core/queues.py for the observation queue definition.
See primes/READ.py for the Phase 1 reference implementation (to be refactored to match READ_ARCHITECTURE.md).
