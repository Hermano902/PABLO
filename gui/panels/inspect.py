"""
Inspect panel — placeholder.
Phase 1: not yet implemented.
"""

from nicegui import ui
from gui.panels.base import GUIPanel


class InspectPanel(GUIPanel):
    name  = "inspect"
    title = "Inspect"

    def build(self, container) -> None:
        with container:
            with ui.column().classes("w-full h-full items-center justify-center gap-3").style(
                "min-height: 400px;"
            ):
                ui.label("Compound Inspector").style(
                    "font-size:16px; color:#333333; font-family:monospace;"
                )
                ui.label("Not yet implemented.").style(
                    "font-size:12px; color:#2a2a2a; font-family:monospace;"
                )
                ui.label(
                    "Browse KNOW's compound storage, search by prime mask, "
                    "view full prime breakdowns."
                ).style(
                    "font-size:11px; color:#222222; max-width:400px; text-align:center;"
                )

    def refresh(self, state: dict) -> None:
        pass
