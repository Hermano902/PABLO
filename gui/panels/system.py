"""
System panel — prime stage indicators and rolling event log.
Lives in the sidebar of the Talk tab.
Uses ui.refreshable for surgical updates.
"""

import time
from nicegui import ui
from gui.panels.base import GUIPanel
from gui.state import MANAGED_PRIMES

# Stage → colour mapping
_STAGE_COLOUR = {
    "perception": "#00c8c8",
    "symbol":     "#00c8c8",
    "memory":     "#00c8c8",
    "attention":  "#cc8800",
    "execution":  "#0088ff",
    "output":     "#0088ff",
    "closed":     "#333333",
    "archived":   "#333333",
    "dormant":    "#222222",
}
_DIM = "#222222"


class SystemPanel(GUIPanel):
    name  = "system"
    title = "System"

    def __init__(self):
        self._state: dict = {}

    def build(self, container) -> None:
        with container:
            self._render_primes()
            ui.separator().style("border-color:#141414; margin:8px 0;")
            self._render_events()

    @ui.refreshable
    def _render_primes(self) -> None:
        ui.label("PRIMES").style(
            "font-size:10px; color:#444444; font-family:monospace; letter-spacing:0.12em;"
        )
        with ui.column().classes("w-full gap-1 mt-1"):
            for name in MANAGED_PRIMES:
                scene = self._state.get("active_scene") or {}
                stage = scene.get("stage", "dormant") if scene else "dormant"
                # Prime is "active" if it is the current stage contributor
                prime_stage = _prime_to_stage(name)
                is_active = prime_stage is not None and prime_stage == stage
                colour = _STAGE_COLOUR.get(stage, _DIM) if is_active else _DIM
                with ui.row().classes("items-center gap-2"):
                    ui.label("●").style(f"color:{colour}; font-size:9px;")
                    ui.label(name).style(
                        f"font-size:11px; color:{'#888888' if is_active else '#333333'};"
                        "font-family:monospace; width:55px;"
                    )

    @ui.refreshable
    def _render_events(self) -> None:
        ui.label("EVENTS").style(
            "font-size:10px; color:#444444; font-family:monospace; letter-spacing:0.12em;"
        )
        scroll = ui.scroll_area().classes("w-full flex-1").style(
            "background:#0d0d0d; border:1px solid #1a1a1a;"
            "border-radius:4px; padding:6px; min-height:0; max-height:300px;"
        )
        with scroll:
            with ui.column().classes("w-full gap-0"):
                events = self._state.get("events", [])
                for line in reversed(events[-30:]):
                    ui.label(line).style(
                        "font-size:10px; color:#444444; font-family:monospace; white-space:pre;"
                    )

    def refresh(self, state: dict) -> None:
        self._state = state
        self._render_primes.refresh()
        self._render_events.refresh()


def _prime_to_stage(prime_name: str) -> str | None:
    """Map a prime name to the scene stage it is responsible for."""
    return {
        "READ":   "perception",
        "SYMBOL": "symbol",
        "DATA":   "memory",
        "KNOW":   "memory",
        "SELF":   "attention",
        "THINK":  "execution",
        "SAY":    "output",
    }.get(prime_name)
