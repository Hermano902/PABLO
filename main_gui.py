"""
main_gui.py — PABLO with NiceGUI interface.

Normal:  python main_gui.py          → native standalone window
Dev:     python main_gui.py --dev    → browser at http://localhost:8080, no auto-reload
"""

import sys

import gui.app  # registers the @ui.page('/') handler  # noqa: F401
from nicegui import ui

if __name__ in {'__main__', '__mp_main__'}:
    dev = '--dev' in sys.argv

    if dev:
        ui.run(
            host='127.0.0.1',
            port=8080,
            title='PABLO [dev]',
            dark=True,
            reload=False,
            show=True,
            favicon='🧠',
        )
    else:
        ui.run(
            host='127.0.0.1',
            port=8080,
            title='PABLO',
            dark=True,
            reload=False,
            native=True,
            window_size=(1200, 800),
            fullscreen=False,
            favicon='🧠',
        )

