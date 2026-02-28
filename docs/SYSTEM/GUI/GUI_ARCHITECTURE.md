PABLO GUI – Architecture


This document describes how the GUI is implemented. The conceptual contract lives in CONCEPT.md; implement the GUI according to both.


1. File Structure
The GUI lives in a dedicated top-level package:

```
gui/
    __init__.py
    app.py           # entry point: builds layout, registers panels, calls ui.run()
    input_source.py  # GUIInputSource — bridges the GUI input bar to READ
    state.py         # system_state snapshot assembly
    panels/
        __init__.py
        base.py          # GUIPanel base class
        conversation.py  # Conversation panel
        system.py        # System panel
```

Nothing inside `gui/` imports from `primes/` directly. The only imports from the cognitive core are `core/queues.py` (to access `response_queue` and queue sizes) and the prime registry's `status()` method.


2. GUIPanel Interface
Every panel is a class that inherits from `GUIPanel`:

```python
class GUIPanel:
    name:   str    # unique identifier, e.g. "conversation"
    title:  str    # displayed in the panel header
    active: bool   # False = panel is registered but not rendered

    def build(self, container) -> None:
        """Mount all NiceGUI elements into the given container. Called once at startup."""
        ...

    def refresh(self, state: dict) -> None:
        """Receive the latest system_state snapshot. Called on every timer tick."""
        ...
```

The root layout in `app.py` calls `build()` once per panel at startup and `refresh()` on every timer tick. Panels never call each other. A panel does not pull state — it receives it passively via `refresh()`.


3. Timer and State Snapshot
A single `ui.timer(interval=0.1)` drives all panel updates. On each tick:

1. `state.py` assembles a `system_state` snapshot:

```python
{
    "primes": {
        "READ":   {"status": "running" | "idle" | "error", "drop_count": int},
        "SYMBOL": {"status": "running" | "idle" | "error"},
        "DATA":   {"status": "running" | "idle" | "error"},
        "KNOW":   {"status": "running" | "idle" | "error"},
        "THINK":  {"status": "running" | "idle" | "error"},
    },
    "queues": {
        "observation": {"size": int, "maxsize": int},
        "candidate":   {"size": int, "maxsize": int},
        "response":    {"size": int, "maxsize": int},
    },
    "events": list[str],   # rolling tail of recent log lines, max 100
    "timestamp": float
}
```

2. All pending items are drained from `response_queue` (non-blocking) and passed to the Conversation panel.

3. `refresh(state)` is called on every active panel.

Primes expose a read-only `status() -> dict` method. `state.py` calls this; it never accesses prime internals directly.


4. Response Queue Contract
THINK pushes dicts to `response_queue`. The GUI drains them on each timer tick.

```python
{
    "timestamp":   float,
    "type":        str,        # "response" | "status" | "error"
    "text":        str,        # human-readable content for the Conversation panel
    "compound_id": int | None  # compound that produced this response, if applicable
}
```

`response_queue` is defined in `core/queues.py` alongside `observation_queue` and `candidate_queue`. Bounded at maxsize=1000 (responses are smaller and consumed faster than raw observations).

Background prime threads never call any NiceGUI function. They only write to `response_queue`. The GUI timer is the only thread that reads from it and updates UI elements.


5. GUIInputSource
Defined in `gui/input_source.py`. Implements the `ReadSource` interface (see READ_ARCHITECTURE.md section 2).

```python
class GUIInputSource(ReadSource):
    name   = "keyboard"
    active = True

    def __init__(self):
        self._pending: queue.Queue[str] = queue.Queue()

    def inject(self, text: str) -> None:
        """Called by the NiceGUI Send button callback. Thread-safe."""
        if text.strip():
            self._pending.put(text.strip())

    def acquire(self) -> str | None:
        try:
            return self._pending.get_nowait()
        except queue.Empty:
            return None

    def has_changed(self, sample: str) -> bool:
        return bool(sample)   # dedup handled by KeyboardSource cooldown layer

    def update_state(self, sample: str) -> None:
        pass   # no state to advance

    def event_type(self, sample: str) -> str:
        return "line_entered"
```

The Send button callback in `app.py`:

```python
def on_send():
    text = input_box.value
    gui_input_source.inject(text)
    input_box.value = ""
```

`gui_input_source` is the singleton `GUIInputSource` instance passed to `READ` at construction. READ's autonomous loop calls `acquire()` on its normal 10ms cycle — no special handling needed.


6. Startup Sequence
```
main.py
  │
  ├── instantiate primes (READ, SYMBOL, DATA, KNOW, THINK)
  │    READ receives gui_input_source at construction
  │
  ├── app.on_startup: read.initialize()      ← starts daemon thread
  ├── app.on_startup: symbol.initialize()    ← starts daemon thread
  ├── app.on_startup: data.initialize()
  ├── app.on_startup: know.initialize()
  ├── app.on_startup: think.initialize()
  │
  ├── build GUI layout (app.py)
  │    ├── register panels
  │    ├── disable input bar
  │    └── register ui.timer(0.1, on_tick)
  │
  └── ui.run()   ← main thread belongs to NiceGUI from here
```

The input bar is enabled by the System panel's `refresh()` once all primes report `status == "running"`. A startup message is appended to the Conversation panel at that point.


7. Thread Safety Rules
- GUI timer callback (on_tick) runs on NiceGUI's async loop — it may call NiceGUI UI methods.
- Prime daemon threads must NEVER call NiceGUI UI methods. Write to `response_queue` only.
- `GUIInputSource.inject()` is called from NiceGUI's async loop (button callback); it uses `queue.Queue.put()` which is thread-safe.
- `state.py` calls `prime.status()` from the timer; primes must return status under their own lock without blocking.


8. Deployment

Local:
```
python main.py
# opens http://localhost:8080 in the default browser
```

Remote (behind nginx):
```nginx
location / {
    proxy_pass         http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header   Upgrade $http_upgrade;
    proxy_set_header   Connection "upgrade";
}
```
WebSocket upgrade headers are required for NiceGUI's real-time updates.

Mobile: same URL in a mobile browser. NiceGUI's responsive grid is used throughout; the System sidebar collapses to a drawer on narrow screens.

Access control: not in Phase 1 scope. For remote access, sit behind an authenticating reverse proxy (Authelia, Caddy basicauth) rather than implementing auth inside PABLO.


9. Configuration Parameters

Parameter              Default     Description
ui.timer interval      0.1 s       Polling frequency for queue drain and panel refresh
response_queue maxsize 1000        Bounded response queue in core/queues.py
event_log max lines    100         Rolling tail length in system_state["events"]
host                   127.0.0.1   Bind address for ui.run()
port                   8080        Bind port for ui.run()
dark_mode              True        NiceGUI dark theme on by default


See CONCEPT.md for what the GUI is and what each panel shows.
See docs/PRIMES/PERCEPTORS/READ/READ_ARCHITECTURE.md for the ReadSource interface GUIInputSource implements.
See core/queues.py for all queue definitions and sizes.
