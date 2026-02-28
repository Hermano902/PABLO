"""
Statistics panel — placeholder.
Phase 1: not yet implemented.
"""

from nicegui import ui
from gui.panels.base import GUIPanel


class StatisticsPanel(GUIPanel):
    name  = "statistics"
    title = "Statistics"

    def build(self, container) -> None:
        with container:
            with ui.column().classes("w-full h-full items-center justify-center gap-3").style(
                "min-height: 400px;"
            ):
                ui.label("Statistics").style(
                    "font-size:16px; color:#333333; font-family:monospace;"
                )
                ui.label("Not yet implemented.").style(
                    "font-size:12px; color:#2a2a2a; font-family:monospace;"
                )
                ui.label(
                    "Live charts: queue depths, observations/min, "
                    "compound creation rate, prime activity."
                ).style(
                    "font-size:11px; color:#222222; max-width:400px; text-align:center;"
                )

    def refresh(self, state: dict) -> None:
        pass
