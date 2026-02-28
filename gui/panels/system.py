"""
System panel — prime status, queue depths, rolling event log.
Lives in the sidebar of the workspace screen.
"""

from nicegui import ui
from gui.panels.base import GUIPanel


_STATUS_COLOUR = {
    "running":    "#00c8c8",
    "idle":       "#555555",
    "error":      "#ff4444",
    "not loaded": "#333333",
}


class SystemPanel(GUIPanel):
    name  = "system"
    title = "System"

    def __init__(self, prime_names: list[str]):
        self._prime_names   = prime_names
        self._prime_labels: dict[str, ui.label] = {}
        self._queue_labels: dict[str, ui.label] = {}
        self._event_log_area = None

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, container) -> None:
        with container:
            # --- Primes ---
            ui.label("PRIMES").style(
                "font-size:10px; color:#444444; font-family:monospace; letter-spacing:0.12em;"
            )
            with ui.column().classes("w-full gap-1 mt-1 mb-3"):
                for name in self._prime_names:
                    with ui.row().classes("items-center gap-2"):
                        dot = ui.label("●").style(f"color:{_STATUS_COLOUR['not loaded']}; font-size:10px;")
                        ui.label(name).style(
                            "font-size:12px; color:#888888; font-family:monospace; width:60px;"
                        )
                        status_lbl = ui.label("not loaded").style(
                            "font-size:11px; color:#333333; font-family:monospace;"
                        )
                        self._prime_labels[name] = (dot, status_lbl)

            # --- Queues ---
            ui.label("QUEUES").style(
                "font-size:10px; color:#444444; font-family:monospace; letter-spacing:0.12em;"
            )
            with ui.column().classes("w-full gap-1 mt-1 mb-3"):
                for q_name in ("observation", "candidate", "response"):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label(q_name[:3]).style(
                            "font-size:11px; color:#666666; font-family:monospace; width:28px;"
                        )
                        lbl = ui.label("0").style(
                            "font-size:11px; color:#555555; font-family:monospace;"
                        )
                        self._queue_labels[q_name] = lbl

            # --- Event log ---
            ui.label("EVENTS").style(
                "font-size:10px; color:#444444; font-family:monospace; letter-spacing:0.12em;"
            )
            self._event_log_area = ui.scroll_area().classes("w-full flex-1").style(
                "background:#0d0d0d; border:1px solid #1e1e1e; "
                "border-radius:4px; padding:6px; min-height:0; max-height:300px;"
            )
            with self._event_log_area:
                self._event_rows = ui.column().classes("w-full gap-0")

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self, state: dict) -> None:
        # Prime status
        for name, (dot, lbl) in self._prime_labels.items():
            info   = state.get("primes", {}).get(name, {})
            status = info.get("status", "not loaded")
            colour = _STATUS_COLOUR.get(status, "#333333")
            dot.style(f"color:{colour}; font-size:10px;")
            lbl.set_text(status)
            lbl.style(f"font-size:11px; color:{colour}; font-family:monospace;")

        # Queue depths
        for q_name, lbl in self._queue_labels.items():
            q_info = state.get("queues", {}).get(q_name, {})
            size    = q_info.get("size", 0)
            maxsize = q_info.get("maxsize", 0)
            lbl.set_text(f"{size}/{maxsize}")

        # Event log — rebuild if changed
        events = state.get("events", [])
        self._event_rows.clear()
        with self._event_rows:
            for line in reversed(events[-30:]):
                ui.label(line).style(
                    "font-size:10px; color:#444444; font-family:monospace; white-space:pre;"
                )
