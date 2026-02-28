"""
Settings panel.
"""

from typing import Callable, Optional
from nicegui import ui
from gui.panels.base import GUIPanel


class SettingsPanel(GUIPanel):
    name  = "settings"
    title = "Settings"

    def __init__(self, on_shutdown: Optional[Callable] = None):
        self._on_shutdown = on_shutdown

    def build(self, container) -> None:
        with container:
            with ui.column().classes('w-full h-full items-center justify-center gap-4').style(
                'min-height:400px;'
            ):
                ui.label('Settings').style(
                    'font-size:13px; color:#333333; font-family:monospace;'
                    'letter-spacing:0.15em;'
                )

                ui.separator().style('width:160px; border-color:#1a1a1a; margin:4px 0;')

                def _shutdown_click():
                    if self._on_shutdown:
                        self._on_shutdown()

                ui.button('Shut Down', on_click=_shutdown_click).style(
                    'background:transparent !important;'
                    'border:1px solid #2a1a1a !important;'
                    'color:#553333 !important;'
                    'font-family:monospace; font-size:11px;'
                    'letter-spacing:0.12em; padding:8px 32px;'
                    'border-radius:2px;'
                ).props('flat unelevated')

    def refresh(self, state: dict) -> None:
        pass
