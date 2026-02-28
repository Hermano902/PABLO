READ – Architecture


This document describes how READ is implemented. The conceptual contract lives in CONCEPT.md; implement READ according to both.


1. Class Structure
READ inherits from Prime (see docs/PRIMES/PRIMES_ARCHITECTURE.md). Beyond the base class it adds:
- A list of registered source handlers (only KEYBOARD is active in Phase 1).
- A daemon thread running the autonomous loop.
- Per-source deduplication state.

```python
class READ(Prime):
    def __init__(self, simulate: bool = False):
        super().__init__("READ")
        self._simulate = simulate          # test-only flag — see section 7
        self._sources = self._build_sources()
        self._thread: threading.Thread | None = None
        self._running = False

    def _build_sources(self) -> list[ReadSource]:
        sources = [KeyboardSource()]       # Phase 1 — active
        # ScreenSource() and FileSource() registered as dormant placeholders
        return sources
```

The singleton at module level does NOT pass simulate=True — that is only for test harnesses:

```python
read = READ()
```


2. Source Interface
Each input source is a small object that implements four methods. This keeps the autonomous loop source-agnostic.

```python
class ReadSource:
    name: str                       # "keyboard" | "screen" | "file:<path>"
    active: bool                    # False = dormant; loop skips it

    def acquire(self) -> str | None:
        """Return new text if available, else None. Non-blocking."""
        ...

    def has_changed(self, sample: str) -> bool:
        """True if this sample is a meaningful new event."""
        ...

    def update_state(self, sample: str) -> None:
        """Advance internal tracking state after an observation is emitted."""
        ...

    def event_type(self, sample: str) -> str:
        """Return the event_type string for the observation dict."""
        ...
```

Phase 1 active source:

KeyboardSource — implemented as GUIInputSource
The active concrete implementation is GUIInputSource, located at gui/input_source.py.
GUIInputSource replaces stdin entirely. The NiceGUI Send button calls gui_input_source.inject(text) from the async event loop thread. READ's autonomous loop calls acquire() on its normal 10 ms cycle — queue.Queue provides the thread-safe hand-off.

GUIInputSource is already implemented and used in Phase 1:
- name: "keyboard", active: True
- acquire(): non-blocking get from internal queue.Queue; returns str or None
- has_changed(sample): True if sample is non-empty after strip()
- update_state(sample): no-op (deduplication lives in READ, not the source)
- event_type(sample): always returns "line_entered"
- inject(text): called by GUI; strips and enqueues the text

The singleton gui_input_source is exported from gui/input_source.py and passed to READ at construction. For headless or test runs, a StdinSource can be substituted — the loop does not change.

Dormant sources (registered but active=False):
- ScreenSource — event types: "text_appeared", "text_changed", "text_cleared"
- FileSource   — event types: "file_appended", "file_created", "file_deleted"


3. Autonomous Loop
The loop iterates over all registered sources and skips dormant ones. One observation is emitted per event.

```python
def _observation_loop(self) -> None:
    while self._running:
        try:
            for source in self._sources:
                if not source.active:
                    continue
                sample = source.acquire()
                if sample is None:
                    continue
                if not source.has_changed(sample):
                    continue
                obs = self._build_observation(source, sample)
                if not observation_queue.full():
                    observation_queue.put(obs)
                else:
                    self._drop_count += 1
                source.update_state(sample)
        except Exception as e:
            self._log_error(e)
        time.sleep(self._sample_interval)
```

The simulation path (if self._simulate) runs after the source loop in the same iteration, injecting a test string as if it came from KeyboardSource. See section 7.


4. Observation Format
All READ observations use this canonical shape. This normalises the current READ.py (which puts raw_input and preliminary_tokens at top level) into the standard structure.

```python
{
    "timestamp":  float,        # time.time()
    "modality":   "READ",
    "event_type": str,          # see section 2 for values per source
    "data": {
        "text":               str,        # raw input string
        "preliminary_tokens": list[str],  # whitespace-split — READ's only preprocessing
        "token_count":        int
    },
    "metadata": {
        "source": str,     # "keyboard" | "screen" | "file:<path>"
        "prime":  "READ",
        "mode":   "autonomous" | "consultation"
    }
}
```

preliminary_tokens is a whitespace split and nothing more. READ does not normalise case, strip punctuation, detect language, or assign any meaning. That boundary belongs to SYMBOL.

Note on current implementation: primes/READ.py emits raw_input and preliminary_tokens at the top level rather than nested under data. This must be corrected to the format above on the next refactor of READ.py.


5. Consultation Mode
Called directly by THINK (or another prime) via dynamic import. Runs synchronously in the caller's thread.

Context keys (any of these triggers consultation mode):

```python
{"mode": "consultation", "input": str}
{"input": str}
{"query": str}
{"text": str}
```

Behaviour:
- Change detection is bypassed — the provided text is always processed.
- The observation_queue is not used.
- Returns a Compound with id=-1 (ephemeral; KNOW assigns a permanent ID if stored).
- The observation dict is still constructed internally (for logging/traceability) but not queued.

Returned Compound fields:
- primebit:          PrimeBit encoding the READ prime
- text:              the input string
- compound_type:     "data"
- provenance_data:   {source, tokens, timestamp, mode: "consultation"}


6. Deduplication and Flood Protection
Implemented inside KeyboardSource (and each future source separately).

- Hash the text string.
- If the same hash was emitted within _send_cooldown seconds (default 0.1 s), skip.
- Cache entries older than cache_max_age (default 300 s) are evicted when cache exceeds cache_max_size (default 1000 entries).

Cache structure:
```python
_recent_hashes: set[int]         # hashes of recently emitted texts
_last_sent_time: dict[int, float]  # hash → timestamp
```

Queue-full behavior: observation is dropped, _drop_count incremented. READ never blocks on queue.put().


7. Simulation
The simulation facility is for isolated testing only. It is gated behind a constructor flag.

```python
read_test = READ(simulate=True)   # test harness only
read      = READ()                # production singleton — no simulation
```

When simulate=True, after each iteration of the source loop the simulation path checks a configurable trigger (elapsed time, counter, or explicit inject() call) and inserts a string from a predefined list into the pipeline as a "keyboard" event. The injected observation is built with metadata.source = "simulation" to distinguish it from real input.

The simulation code lives in a clearly demarcated block inside READ. Before any production hardening pass it is removed entirely. It is never active in the module-level singleton.


8. Configuration Parameters

Parameter            Default     Description
_sample_interval     0.01 s      Sleep between autonomous loop iterations
_send_cooldown       0.1 s       Min time between identical observations (per hash)
cache_max_age        300 s       Max age of cache entries before eviction
cache_max_size       1000        Max entries before forced cleanup
observation_queue    maxsize=10000   Defined in core/queues.py; shared with other perceptors


9. Phase 1 vs Future Sources

Source        Phase 1    Notes
KEYBOARD      active     GUIInputSource (gui/input_source.py) — one observation per non-empty line submitted via GUI input bar
SCREEN        dormant    Registered, active=False. Activate by setting active=True and implementing ScreenSource.acquire()
FILE          dormant    Registered, active=False. FileSource takes a path list at construction time


10. Relating to SYMBOL
SYMBOL's autonomous thread is the consumer of observation_queue. For READ observations, SYMBOL:
- Checks event_type to select the right text specialist.
- Reads data.text as the string to interpret.
- Reads metadata.source for provenance.
- Produces a near-compound candidate referencing the original observation timestamp and modality.

READ never calls SYMBOL directly. The queue is their only coupling.


See CONCEPT.md for what READ senses and why.
See docs/PRIMES/PERCEPTORS/PERCEPTORS_ARCHITECTURE.md for the shared perceptor skeleton.
See docs/PRIMES/PRIMES_ARCHITECTURE.md for the Prime base class.
See core/queues.py for the observation_queue definition.
See primes/READ.py for the current implementation (to be refactored to match this spec).
