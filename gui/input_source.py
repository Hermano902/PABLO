"""
GUIInputSource — bridges the NiceGUI input bar to READ's source interface.

READ's autonomous loop calls acquire() on its normal 10ms cycle.
The NiceGUI Send button calls inject() from the async event loop thread.
queue.Queue provides the thread-safe hand-off between the two.
"""

import queue


class GUIInputSource:
    """
    Implements the ReadSource interface for GUI keyboard input.
    Replaces stdin entirely for all GUI-launched sessions.
    """

    name   = "keyboard"
    active = True

    def __init__(self):
        self._pending: queue.Queue[str] = queue.Queue()

    # ------------------------------------------------------------------
    # ReadSource interface
    # ------------------------------------------------------------------

    def acquire(self) -> str | None:
        """Non-blocking — returns next pending line, or None."""
        try:
            return self._pending.get_nowait()
        except queue.Empty:
            return None

    def has_changed(self, sample: str) -> bool:
        """Every non-empty string from the GUI is a new event."""
        return bool(sample and sample.strip())

    def update_state(self, sample: str) -> None:
        """No internal state to advance."""
        pass

    def event_type(self, sample: str) -> str:
        return "line_entered"

    # ------------------------------------------------------------------
    # GUI-side API (called from NiceGUI async event loop)
    # ------------------------------------------------------------------

    def inject(self, text: str) -> None:
        """
        Called by the Send button callback.
        Thread-safe — queue.Queue.put() is safe from any thread.
        """
        text = text.strip()
        if text:
            self._pending.put(text)


# Singleton — passed to READ at construction and to the GUI app.
gui_input_source = GUIInputSource()
