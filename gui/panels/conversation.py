"""
Conversation panel — the Talk tab.

Displays the exchange between the user and PABLO.
Drains response_queue on each timer tick and appends messages.
"""

import time
from nicegui import ui
from gui.panels.base import GUIPanel


class ConversationPanel(GUIPanel):
    name  = "conversation"
    title = "Talk"

    def __init__(self):
        self._scroll: ui.scroll_area | None  = None
        self._msg_area = None
        self._thinking_row = None
        self._thinking_visible = False

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, container) -> None:
        with container:
            # Scrollable message area — takes all available vertical space
            self._scroll = ui.scroll_area().classes(
                "w-full flex-1 rounded-lg"
            ).style(
                "background:#111111; min-height:0; padding: 16px 20px;"
            )
            with self._scroll:
                self._msg_area = ui.column().classes("w-full gap-2")
                with self._msg_area:
                    # Welcome message
                    self._append_system("PABLO is ready.")

    # ------------------------------------------------------------------
    # Refresh (called by timer)
    # ------------------------------------------------------------------

    def refresh(self, state: dict) -> None:
        # response_queue is drained in app.py and passed via state["_responses"]
        responses = state.get("_responses", [])
        for resp in responses:
            self._hide_thinking()
            rtype = resp.get("type", "response")
            text  = resp.get("text", "")
            if rtype == "response":
                self._append_pablo(text)
            elif rtype == "status":
                self._append_system(text)
            elif rtype == "error":
                self._append_error(text)

    # ------------------------------------------------------------------
    # Public API (called by app.py on user send)
    # ------------------------------------------------------------------

    def add_user_message(self, text: str) -> None:
        self._append_user(text)
        self._show_thinking()

    def add_system_message(self, text: str) -> None:
        self._append_system(text)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_user(self, text: str) -> None:
        ts = time.strftime("%H:%M:%S")
        with self._msg_area:
            with ui.column().classes("w-full gap-0 mt-2"):
                with ui.row().classes("items-baseline gap-2"):
                    ui.label("YOU").style(
                        "font-size:11px; color:#00c8c8; font-family:monospace; letter-spacing:0.1em;"
                    )
                    ui.label(ts).style("font-size:10px; color:#444444; font-family:monospace;")
                ui.label(text).style(
                    "font-size:15px; color:#aaaaaa; word-break:break-word; padding-left:4px;"
                )
        self._scroll_to_bottom()

    def _append_pablo(self, text: str) -> None:
        ts = time.strftime("%H:%M:%S")
        with self._msg_area:
            with ui.column().classes("w-full gap-0 mt-2"):
                with ui.row().classes("items-baseline gap-2"):
                    ui.label("PABLO").style(
                        "font-size:11px; color:#0088ff; font-family:monospace; letter-spacing:0.1em;"
                    )
                    ui.label(ts).style("font-size:10px; color:#444444; font-family:monospace;")
                ui.label(text).style(
                    "font-size:15px; color:#f0f0f0; word-break:break-word; padding-left:4px;"
                )
        self._scroll_to_bottom()

    def _append_system(self, text: str) -> None:
        ts = time.strftime("%H:%M:%S")
        with self._msg_area:
            ui.label(f"{ts}  {text}").style(
                "font-size:11px; color:#444444; font-family:monospace; margin-top:8px;"
            )
        self._scroll_to_bottom()

    def _append_error(self, text: str) -> None:
        with self._msg_area:
            ui.label(f"ERROR  {text}").style(
                "font-size:12px; color:#ff4444; font-family:monospace; margin-top:4px;"
            )
        self._scroll_to_bottom()

    def _show_thinking(self) -> None:
        if self._thinking_visible:
            return
        with self._msg_area:
            with ui.row().classes("items-baseline gap-2 mt-2") as row:
                self._thinking_row = row
                ui.label("PABLO").style(
                    "font-size:11px; color:#0088ff; font-family:monospace; letter-spacing:0.1em;"
                )
                ui.label("...").style("font-size:15px; color:#333333;")
        self._thinking_visible = True
        self._scroll_to_bottom()

    def _hide_thinking(self) -> None:
        if not self._thinking_visible:
            return
        if self._thinking_row:
            self._thinking_row.delete()
            self._thinking_row = None
        self._thinking_visible = False

    def _scroll_to_bottom(self) -> None:
        if self._scroll:
            self._scroll.scroll_to(percent=1.0)
