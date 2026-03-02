"""
gui/app.py — NiceGUI page definition.

Registers the single @ui.page('/') handler.
All screen layout, event wiring, and timer logic lives here.
Import this module to register the page; call main_gui.py's ui.run() to start.
"""

import asyncio
from nicegui import ui

from gui.blob import make_blob_container, make_blob_script, THREE_JS_HEAD
from gui.input_source import gui_input_source
from gui.state import get_state, log_event, MANAGED_PRIMES
from gui.panels.conversation import ConversationPanel
from gui.panels.system import SystemPanel
from gui.panels.inspect import InspectPanel
from gui.panels.statistics import StatisticsPanel
from gui.panels.settings import SettingsPanel
from core.queues import prime_registry, response_queue


# Module-level panel refs so the timer can reach them across calls.
_conversation: ConversationPanel | None = None
_system: SystemPanel | None = None


@ui.page('/')
async def index():
    global _conversation, _system

    # ── Global styles + Three.js ────────────────────────────────────────
    ui.add_head_html(THREE_JS_HEAD)
    # Blob scripts go in body (NiceGUI 3.x forbids <script> in ui.html)
    ui.add_body_html(make_blob_script(280, 'boot'))
    ui.add_body_html(make_blob_script(32, 'mini'))
    ui.add_head_html("""
    <style>
      html, body { margin:0; padding:0; background:#0a0a0a !important;
                   overflow:hidden; height:100%; width:100%; }
      .nicegui-content { background:#0a0a0a !important; padding:0 !important; }
      * { box-sizing:border-box; }
      ::-webkit-scrollbar            { width:4px; height:4px; }
      ::-webkit-scrollbar-track      { background:#0a0a0a; }
      ::-webkit-scrollbar-thumb      { background:#222222; border-radius:2px; }
      ::-webkit-scrollbar-thumb:hover{ background:#2e2e2e; }
      input::placeholder { color:#333333 !important; }
    </style>
    """)

    # ════════════════════════════════════════════════════════════════════
    # BOOT SCREEN
    # ════════════════════════════════════════════════════════════════════
    boot_screen = ui.element('div').props('id=pablo-boot').style(
        'width:100vw; height:100vh;'
        'display:flex; flex-direction:column;'
        'align-items:center; justify-content:center;'
        'gap:20px; background:#0a0a0a;'
        'position:absolute; top:0; left:0; z-index:10;'
        'opacity:1; pointer-events:auto;'
        'transition:opacity 0.4s;'
    )
    with boot_screen:
        ui.html(make_blob_container(size=280, blob_id='boot'))

        status_label = ui.label('PABLO').style(
            'font-family:monospace; font-size:13px; color:#555555;'
            'letter-spacing:0.2em; min-height:18px; margin-top:-8px;'
        )

        init_btn = ui.button('Initialise').style(
            'background:transparent !important;'
            'border:1px solid #222222 !important;'
            'color:#444444 !important;'
            'font-family:monospace; font-size:12px;'
            'letter-spacing:0.12em; padding:8px 32px;'
            'margin-top:4px; border-radius:2px;'
        ).props('flat unelevated')

    # ════════════════════════════════════════════════════════════════════
    # MAIN SCREEN  (hidden until init)
    # ════════════════════════════════════════════════════════════════════
    main_screen = ui.element('div').props('id=pablo-main').style(
        'width:100vw; height:100vh;'
        'display:flex; flex-direction:column;'
        'background:#0a0a0a; overflow:hidden;'
        'position:absolute; top:0; left:0; z-index:5;'
        'opacity:0; pointer-events:none;'
        'transition:opacity 0.4s;'
    )
    with main_screen:

        # ── Top bar ────────────────────────────────────────────────────
        with ui.row().classes('w-full items-center justify-between').style(
            'padding:8px 16px; border-bottom:1px solid #141414;'
            'background:#0a0a0a; flex-shrink:0; height:50px;'
        ):
            with ui.row().classes('items-center gap-2'):
                ui.html(make_blob_container(size=32, blob_id='mini'))
                ui.label('PABLO').style(
                    'font-family:monospace; font-size:12px; color:#333333;'
                    'letter-spacing:0.25em; margin-left:4px;'
                )
            ui.label('● online').style(
                'font-family:monospace; font-size:10px; color:#00c8c8;'
            )

        # ── Tab bar ────────────────────────────────────────────────────
        with ui.tabs().classes('w-full').style(
            'background:#0a0a0a; border-bottom:1px solid #141414;'
            'min-height:38px; height:38px; flex-shrink:0; padding:0 12px;'
        ) as tabs:
            for label, active in [
                ('Talk', True), ('Inspect', False),
                ('Statistics', False), ('Settings', False)
            ]:
                colour = '#00c8c8' if active else '#2a2a2a'
                ui.tab(label).style(
                    f'font-family:monospace; font-size:11px;'
                    f'letter-spacing:0.1em; color:{colour};'
                    f'min-height:38px; padding:0 16px;'
                )
            tab_talk, tab_ins, tab_stats, tab_set = (
                tabs._props.get('modelValue'), None, None, None
            )

        # ── Tab panels ─────────────────────────────────────────────────
        content_area = ui.element('div').style(
            'flex:1; display:flex; flex-direction:column;'
            'min-height:0; overflow:hidden;'
        )
        with content_area:
            tab_panels = ui.tab_panels(tabs, value='Talk').classes('w-full flex-1').style(
                'background:#0a0a0a; min-height:0; overflow:hidden; flex:1;'
            )
            with tab_panels:

                # ── Talk ───────────────────────────────────────────────
                with ui.tab_panel('Talk').style(
                    'padding:0; display:flex; flex-direction:row;'
                    'height:100%; overflow:hidden; flex:1;'
                ):
                    # Left: conversation
                    conv_col = ui.column().classes('flex-1').style(
                        'min-width:0; height:100%; display:flex;'
                        'flex-direction:column; overflow:hidden;'
                    )
                    _conversation = ConversationPanel()
                    _conversation.build(conv_col)

                    # Input bar (inside conv_col)
                    with conv_col:
                        with ui.row().classes('w-full items-center gap-2').style(
                            'padding:10px 14px; border-top:1px solid #141414;'
                            'background:#0a0a0a; flex-shrink:0;'
                        ):
                            input_box = (
                                ui.input(placeholder='type something...')
                                .classes('flex-1')
                                .style(
                                    'background:#0f0f0f;'
                                    'color:#f0f0f0;'
                                    'font-size:14px;'
                                    'font-family:Inter,system-ui;'
                                    'border:none; outline:none;'
                                )
                                .props('outlined dense standout="bg-transparent"')
                            )
                            send_btn = ui.button('Send').style(
                                'background:transparent !important;'
                                'border:1px solid #1e1e1e !important;'
                                'color:#444444 !important;'
                                'font-family:monospace; font-size:11px;'
                                'letter-spacing:0.08em; padding:6px 14px;'
                                'border-radius:2px; flex-shrink:0;'
                            ).props('flat unelevated')

                    # Right: system sidebar
                    sys_col = ui.column().style(
                        'width:220px; flex-shrink:0; height:100%;'
                        'border-left:1px solid #141414;'
                        'background:#0a0a0a; overflow:hidden;'
                        'display:flex; flex-direction:column;'
                        'padding:12px 10px;'
                    )
                    _system = SystemPanel(MANAGED_PRIMES)
                    _system.build(sys_col)

                # ── Inspect ────────────────────────────────────────────
                with ui.tab_panel('Inspect').style('padding:0; height:100%;'):
                    InspectPanel().build(ui.column().classes('w-full h-full'))

                # ── Statistics ─────────────────────────────────────────
                with ui.tab_panel('Statistics').style('padding:0; height:100%;'):
                    StatisticsPanel().build(ui.column().classes('w-full h-full'))

                # ── Settings ───────────────────────────────────────────
                with ui.tab_panel('Settings').style('padding:0; height:100%;'):
                    settings_panel = SettingsPanel()
                    settings_panel.build(ui.column().classes('w-full h-full'))

    # ════════════════════════════════════════════════════════════════════
    # Shutdown handler  (Settings → back to boot screen)
    # ════════════════════════════════════════════════════════════════════
    def do_shutdown():
        ui.run_javascript(
            "document.getElementById('pablo-main').style.opacity='0';"
            "document.getElementById('pablo-main').style.pointerEvents='none';"
            "document.getElementById('pablo-boot').style.opacity='1';"
            "document.getElementById('pablo-boot').style.pointerEvents='auto';"
        )
        status_label.set_text('PABLO')
        init_btn.set_visibility(True)
        log_event('System shut down.')

    settings_panel._on_shutdown = do_shutdown

    # ════════════════════════════════════════════════════════════════════
    # Initialisation handler
    # ════════════════════════════════════════════════════════════════════
    async def do_init():
        init_btn.set_visibility(False)
        await ui.run_javascript("if(window.pablo?.blob?.boot) pablo.blob.boot.setSpeed(3.0)")

        for prime_name in MANAGED_PRIMES:
            try:
                status_label.set_text(f'{prime_name} initialising...')
                prime = prime_registry.get_prime(prime_name)
                prime.initialize()
                status_label.set_text(f'{prime_name} online.')
                log_event(f'{prime_name} online.')
            except Exception as exc:
                status_label.set_text(f'{prime_name} failed.')
                log_event(f'ERROR {prime_name}: {exc}')
            await asyncio.sleep(0.45)

        # Unsuspend SELF now that all primes are running
        try:
            self_prime = prime_registry.get_prime("SELF")
            self_prime.suspended = False
            log_event("SELF unsuspended — attention routing active.")
        except Exception:
            pass

        status_label.set_text('Ready.')
        await ui.run_javascript("if(window.pablo?.blob?.boot) pablo.blob.boot.pulse()")
        await asyncio.sleep(1.3)

        # Transition: fade boot out, fade main in
        await ui.run_javascript(
            "document.getElementById('pablo-boot').style.opacity='0';"
            "document.getElementById('pablo-boot').style.pointerEvents='none';"
        )
        await asyncio.sleep(0.45)
        await ui.run_javascript(
            "document.getElementById('pablo-main').style.opacity='1';"
            "document.getElementById('pablo-main').style.pointerEvents='auto';"
        )
        if _conversation:
            _conversation.add_system_message('All systems online.')

    # ════════════════════════════════════════════════════════════════════
    # Send handler
    # ════════════════════════════════════════════════════════════════════
    def handle_send():
        text = input_box.value.strip()
        if not text:
            return
        input_box.value = ''
        gui_input_source.inject(text)
        if _conversation:
            _conversation.add_user_message(text)

    init_btn.on('click', do_init)
    send_btn.on('click', handle_send)
    input_box.on('keydown.enter', handle_send)

    # ════════════════════════════════════════════════════════════════════
    # Timer  (100 ms — drains response_queue, refreshes system panel)
    # ════════════════════════════════════════════════════════════════════
    def on_tick():
        # Drain response queue → conversation
        responses = []
        while not response_queue.empty():
            try:
                responses.append(response_queue.get_nowait())
            except Exception:
                break
        if responses and _conversation:
            _conversation.refresh({'_responses': responses})

        # Refresh system sidebar
        if _system:
            try:
                state = get_state(prime_registry)
                _system.refresh(state)
            except Exception:
                pass

    ui.timer(0.1, on_tick)
