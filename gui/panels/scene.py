"""
Scene panel — live MetaScene inspector.

Shows the active CognitiveScene layers as primes contribute to them.
Each layer lights up when its prime has written to it.
Uses ui.refreshable for surgical updates — no full re-render on each tick.
"""

import time
from nicegui import ui
from gui.panels.base import GUIPanel

_MONO  = "font-family:monospace;"
_BG    = "#0a0a0a"
_CARD  = "#0d0d0d"
_BDR   = "#1a1a1a"
_DIM   = "#333333"
_MID   = "#555555"
_TEXT  = "#888888"
_ACNT  = "#00c8c8"
_BLUE  = "#0088ff"
_WARN  = "#cc8800"
_INACT = "#1a1a1a"

# Status → accent colour
_STATUS_COLOUR = {
    "active":     _ACNT,
    "promoted":   _WARN,
    "suppressed": _DIM,
    "archived":   _DIM,
    "failed":     "#cc4444",
}


class ScenePanel(GUIPanel):
    name  = "scene"
    title = "Scene"

    def __init__(self):
        self._state: dict = {}

    def build(self, container) -> None:
        with container:
            scroll = ui.scroll_area().classes("w-full h-full").style(
                f"background:{_BG}; padding:16px 20px;"
            )
            with scroll:
                with ui.column().classes("w-full gap-3"):
                    self._render_header()
                    self._render_scene_layers()
                    self._render_recent_scenes()

    @ui.refreshable
    def _render_header(self) -> None:
        scene = self._state.get("active_scene")
        if not scene:
            ui.label("No active scene.").style(
                f"font-size:12px; color:{_DIM}; {_MONO}"
            )
            return

        status  = scene.get("status", "active")
        ttype   = scene.get("thread_type", "unconscious")
        colour  = _STATUS_COLOUR.get(status, _DIM)
        elapsed = ""
        if scene.get("opened_at"):
            e = time.time() - scene["opened_at"]
            elapsed = f"  {e*1000:.0f}ms"

        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-3"):
                ui.label(f"● {status.upper()}").style(
                    f"font-size:12px; color:{colour}; {_MONO} letter-spacing:0.1em;"
                )
                ui.label(f"[{ttype}]").style(
                    f"font-size:10px; color:{_MID}; {_MONO}"
                )
                ui.label(scene.get("scene_id", "")[:8]).style(
                    f"font-size:10px; color:{_DIM}; {_MONO}"
                )
            ui.label(f"src:{scene.get('source','?')}{elapsed}").style(
                f"font-size:10px; color:{_DIM}; {_MONO}"
            )

    @ui.refreshable
    def _render_scene_layers(self) -> None:
        scene = self._state.get("active_scene")

        with ui.column().classes("w-full gap-2"):
            # ── PERCEPTION ──────────────────────────────────────────────
            active = scene and bool(scene.get("raw_input"))
            with _layer_card(active, "PERCEPTION", "READ", _ACNT):
                if scene and scene.get("raw_input"):
                    _field("input",    scene["raw_input"])
                    _field("modality", scene.get("modality", ""))
                    tokens = scene.get("preliminary_tokens", [])
                    if tokens:
                        _field("tokens", " | ".join(tokens))
                else:
                    _placeholder("waiting for input...")

            # ── SYMBOL ──────────────────────────────────────────────────
            active = scene and bool(scene.get("script"))
            with _layer_card(active, "SYMBOL", "SYMBOL", _ACNT):
                if scene and scene.get("script"):
                    _field("script", scene["script"])
                    lang = scene.get("language_hint", {})
                    if lang:
                        top = sorted(lang.items(), key=lambda x: -x[1])[:2]
                        _field("language", "  ".join(f"{k}:{v:.2f}" for k, v in top))
                    tokens = scene.get("preliminary_tokens", [])
                    if tokens:
                        _field("tokens", " | ".join(tokens[:12]))
                else:
                    _placeholder("waiting for symbol layer...")

            # ── MEMORY ──────────────────────────────────────────────────
            active = scene and scene.get("utterance_id") is not None
            with _layer_card(active, "MEMORY", "DATA + KNOW", _ACNT):
                if scene and scene.get("utterance_id") is not None:
                    _field("utterance_id", str(scene["utterance_id"]))
                    concepts = scene.get("concept_ids", [])
                    if concepts:
                        _field("concepts", str(concepts[:10]))
                    new_syms = scene.get("new_symbols", [])
                    known_syms = scene.get("known_symbols", [])
                    if new_syms:
                        _field("new", " | ".join(new_syms[:6]), _ACNT)
                    if known_syms:
                        _field("known", " | ".join(known_syms[:6]))
                    flags = scene.get("validation_flags", {})
                    if flags:
                        orphaned = [
                            cid for cid, f in flags.items()
                            if not f.get("valid", True)
                        ]
                        if orphaned:
                            _field("orphan primes", str(orphaned), _WARN)
                else:
                    _placeholder("waiting for memory layer...")

            # ── RELATIONAL ──────────────────────────────────────────────
            active = scene and scene.get("attention_decision") is not None
            with _layer_card(active, "RELATIONAL", "SELF", _WARN):
                if scene and scene.get("attention_decision") is not None:
                    decision = scene["attention_decision"]
                    col = _ACNT if decision == "conscious" else _DIM
                    _field("decision", decision, col)
                    sal = scene.get("salience", 0.0)
                    _field("salience", f"{sal:.3f}")
                    rq = scene.get("relationship_quality")
                    if rq is not None:
                        _field("rel_quality", f"{rq:.2f}")
                else:
                    _placeholder("waiting for attention gate...")

            # ── EXECUTION ───────────────────────────────────────────────
            active = scene and scene.get("reasoning_mode") is not None
            with _layer_card(active, "EXECUTION", "THINK + SAY", _BLUE):
                if scene and scene.get("reasoning_mode") is not None:
                    _field("mode",      scene["reasoning_mode"], _BLUE)
                    iid = scene.get("intent_id")
                    if iid is not None:
                        _field("intent_id", str(iid))
                    resp = scene.get("response_text")
                    if resp:
                        _field("response", resp[:120])
                else:
                    _placeholder("waiting for execution...")

    @ui.refreshable
    def _render_recent_scenes(self) -> None:
        recent = self._state.get("recent_scenes", [])
        if not recent:
            return

        ui.label("RECENT SCENES").style(
            f"font-size:10px; color:{_DIM}; {_MONO} letter-spacing:0.12em; margin-top:8px;"
        )
        with ui.column().classes("w-full gap-1"):
            for s in recent[:5]:
                status = s.get("status", "active")
                colour = _STATUS_COLOUR.get(status, _DIM)
                raw    = s.get("raw_input", "")[:50]
                sid    = s.get("scene_id", "")[:8]
                with ui.row().classes("w-full items-baseline gap-2").style(
                    f"border-bottom:1px solid {_INACT}; padding:3px 0;"
                ):
                    ui.label(f"● {status}").style(
                        f"font-size:10px; color:{colour}; {_MONO} width:80px;"
                    )
                    ui.label(sid).style(
                        f"font-size:10px; color:{_DIM}; {_MONO} width:60px;"
                    )
                    ui.label(raw or "(no input)").style(
                        f"font-size:10px; color:{_MID}; {_MONO}"
                        "overflow:hidden; white-space:nowrap; text-overflow:ellipsis;"
                    )

    def refresh(self, state: dict) -> None:
        self._state = state
        self._render_header.refresh()
        self._render_scene_layers.refresh()
        self._render_recent_scenes.refresh()


# ── helpers ──────────────────────────────────────────────────────────────────

def _layer_card(active: bool, label: str, prime_label: str, colour: str):
    border = colour if active else _INACT
    return ui.card().classes("w-full").style(
        f"background:{_CARD}; border:1px solid {border};"
        "border-radius:6px; padding:10px 14px;"
    ).props("flat").__enter__() and _LayerContext(label, prime_label, colour, active)


class _LayerContext:
    """Context manager that renders the layer header then yields for content."""
    def __init__(self, label, prime_label, colour, active):
        self._label       = label
        self._prime_label = prime_label
        self._colour      = colour
        self._active      = active

    def __enter__(self):
        col = self._colour if self._active else _DIM
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(self._label).style(
                f"font-size:10px; color:{col}; {_MONO} letter-spacing:0.12em;"
            )
            ui.label(self._prime_label).style(
                f"font-size:10px; color:{_DIM}; {_MONO}"
            )
        return self

    def __exit__(self, *_):
        pass


def _field(key: str, value: str, colour: str = _TEXT) -> None:
    with ui.row().classes("items-baseline gap-2"):
        ui.label(key).style(
            f"font-size:10px; color:{_DIM}; {_MONO} width:90px; flex-shrink:0;"
        )
        ui.label(value).style(
            f"font-size:11px; color:{colour}; {_MONO} word-break:break-all;"
        )


def _placeholder(text: str) -> None:
    ui.label(text).style(f"font-size:10px; color:{_INACT}; {_MONO}")
