"""
Development panel — KNOW memory inspector, compound browser, danger zone.

Uses ui.refreshable for stats and memory count sections.
Compound browser is imperative (user-triggered search).
"""

import time
from nicegui import ui
from gui.panels.base import GUIPanel

_CLR_ACCENT = "#00c8c8"
_CLR_DIM    = "#333333"
_CLR_MID    = "#555555"
_CLR_TEXT   = "#999999"
_CLR_BRIGHT = "#cccccc"
_CLR_DANGER = "#ff4444"
_CLR_WARN   = "#cc8800"
_CLR_BG     = "#0a0a0a"
_CLR_CARD   = "#0f0f0f"
_CLR_BORDER = "#1a1a1a"

_MONO    = "font-family:monospace;"
_SECTION = f"font-size:10px; color:#444444; {_MONO} letter-spacing:0.12em; margin-bottom:4px;"


class DevelopmentPanel(GUIPanel):
    name  = "development"
    title = "Dev"

    def __init__(self):
        self._state:       dict = {}
        self._init_time:   float | None = None
        self._uptime_label = None
        self._search_input     = None
        self._compound_table   = None
        self._compound_detail  = None
        self._wipe_confirm     = None

    # ══════════════════════════════════════════════════════════════════════
    # Build
    # ══════════════════════════════════════════════════════════════════════

    def build(self, container) -> None:
        with container:
            root = ui.scroll_area().classes("w-full h-full").style(
                f"background:{_CLR_BG}; padding:16px 20px;"
            )
            with root:
                with ui.column().classes("w-full gap-4"):
                    self._build_header()
                    with ui.row().classes("w-full gap-4").style("flex-wrap:wrap;"):
                        with ui.column().classes("gap-4").style(
                            "flex:1; min-width:280px; max-width:340px;"
                        ):
                            self._render_know_stats()
                            self._render_memory_counts()
                        with ui.column().classes("gap-4").style("flex:2; min-width:400px;"):
                            self._build_compound_browser()
                    self._build_danger_zone()

    def _build_header(self):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("PABLO  /  DEVELOPMENT").style(
                f"font-size:12px; color:{_CLR_DIM}; {_MONO} letter-spacing:0.2em;"
            )
            self._uptime_label = ui.label("uptime: --:--:--").style(
                f"font-size:11px; color:{_CLR_DIM}; {_MONO}"
            )

    # ── KNOW stats (refreshable) ──────────────────────────────────────────

    @ui.refreshable
    def _render_know_stats(self) -> None:
        with _card():
            ui.label("KNOW OPERATIONS").style(_SECTION)
            know_stats = self._state.get("know", {})
            op = know_stats.get("operation_stats", {})
            with ui.column().classes("w-full gap-1"):
                for key, label in [
                    ("compounds_stored",    "stored"),
                    ("compounds_retrieved", "retrieved"),
                    ("cache_hits",          "cache hits"),
                    ("definitions_loaded",  "definitions"),
                    ("narratives_stored",   "narratives"),
                    ("triples_stored",      "triples"),
                    ("saves_to_disk",       "disk saves"),
                    ("errors",              "errors"),
                ]:
                    val    = op.get(key, 0)
                    colour = _CLR_DANGER if key == "errors" and val > 0 else _CLR_DIM
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label(label).style(
                            f"font-size:11px; color:{_CLR_TEXT}; {_MONO}"
                        )
                        ui.label(str(val)).style(
                            f"font-size:11px; color:{colour}; {_MONO}"
                        )

    # ── Memory counts (refreshable) ───────────────────────────────────────

    @ui.refreshable
    def _render_memory_counts(self) -> None:
        with _card():
            ui.label("MEMORY").style(_SECTION)
            know_stats = self._state.get("know", {})
            ss = know_stats.get("store_stats", {})
            with ui.row().classes("w-full gap-6"):
                for key, label in [
                    ("total_compounds",   "Compounds"),
                    ("total_definitions", "Definitions"),
                    ("total_narratives",  "Narratives"),
                    ("total_triples",     "Triples"),
                ]:
                    with ui.column().classes("items-center gap-0"):
                        ui.label(str(ss.get(key, "--"))).style(
                            f"font-size:22px; color:{_CLR_ACCENT}; {_MONO}"
                        )
                        ui.label(label).style(
                            f"font-size:10px; color:{_CLR_DIM}; {_MONO}"
                        )
            ui.separator().style(f"border-color:{_CLR_BORDER}; margin:8px 0;")
            with ui.row().classes("w-full gap-6"):
                for key, label in [
                    ("next_id",        "next compound ID"),
                    ("next_triple_id", "next triple ID"),
                    ("cache_size",     "cache size"),
                ]:
                    with ui.column().classes("gap-0"):
                        ui.label(label).style(
                            f"font-size:9px; color:{_CLR_DIM}; {_MONO}"
                        )
                        ui.label(str(ss.get(key, "--"))).style(
                            f"font-size:12px; color:{_CLR_TEXT}; {_MONO}"
                        )

    # ── Compound browser (imperative — user triggered) ────────────────────

    def _build_compound_browser(self):
        with _card():
            with ui.row().classes("w-full items-center gap-2 justify-between"):
                ui.label("COMPOUND BROWSER").style(_SECTION)
                with ui.row().classes("items-center gap-2"):
                    self._search_input = (
                        ui.input(placeholder="symbol or empty for recent…")
                        .style(
                            f"background:{_CLR_BG}; color:{_CLR_TEXT}; {_MONO}"
                            "font-size:11px; max-width:200px;"
                        )
                        .props("outlined dense")
                    )
                    self._search_input.on("keydown.enter", self._on_search)
                    ui.button("↺", on_click=self._on_search).style(
                        f"background:transparent !important;"
                        f"border:1px solid {_CLR_BORDER} !important;"
                        f"color:{_CLR_MID} !important;"
                        f"{_MONO} font-size:12px; padding:4px 10px; min-width:0;"
                        "border-radius:2px;"
                    ).props("flat unelevated dense")

            with ui.row().classes("w-full gap-0 mt-1").style(
                f"border-bottom:1px solid {_CLR_BORDER}; padding-bottom:3px;"
            ):
                for hdr, w in [
                    ("ID", "44px"), ("Symbol", "140px"), ("Type", "72px"),
                    ("Gnd", "36px"), ("Src", "80px"), ("Primebit", ""),
                ]:
                    ui.label(hdr).style(
                        f"font-size:10px; color:{_CLR_DIM}; {_MONO} width:{w};"
                    )

            self._compound_table = ui.column().classes("w-full gap-0").style(
                "max-height:260px; overflow-y:auto;"
            )
            ui.separator().style(f"border-color:{_CLR_BORDER}; margin:10px 0;")
            ui.label("DETAIL").style(_SECTION)
            self._compound_detail = ui.column().classes("w-full gap-1").style(
                f"background:{_CLR_BG}; border:1px solid {_CLR_BORDER};"
                "border-radius:4px; padding:10px; min-height:60px;"
                "max-height:320px; overflow-y:auto;"
            )
            with self._compound_detail:
                ui.label("Select a compound above.").style(
                    f"font-size:11px; color:{_CLR_DIM}; {_MONO}"
                )

    # ── Danger zone ───────────────────────────────────────────────────────

    def _build_danger_zone(self):
        with ui.card().classes("w-full").style(
            "background:#0c0808; border:1px solid #2a1111;"
            "border-radius:6px; padding:14px;"
        ).props("flat"):
            ui.label("DANGER ZONE").style(
                f"font-size:10px; color:{_CLR_DANGER}; {_MONO} letter-spacing:0.12em;"
            )
            ui.label(
                "Wipes all runtime compounds, definitions, narratives, triples, "
                "and symbol index. Logic compounds (IDs 100–199) are preserved."
            ).style(f"font-size:11px; color:#553333; {_MONO} margin:6px 0;")
            with ui.row().classes("items-center gap-3"):
                ui.button("Wipe All Compounds", on_click=self._show_wipe_confirm).style(
                    "background:transparent !important;"
                    "border:1px solid #441111 !important;"
                    f"color:{_CLR_DANGER} !important;"
                    f"{_MONO} font-size:11px; letter-spacing:0.08em;"
                    "padding:6px 18px; border-radius:2px;"
                ).props("flat unelevated")
                self._wipe_confirm = ui.row().classes("items-center gap-2")
                self._wipe_confirm.set_visibility(False)
                with self._wipe_confirm:
                    ui.label("Are you sure?").style(
                        f"font-size:11px; color:{_CLR_WARN}; {_MONO}"
                    )
                    ui.button("Yes, wipe everything", on_click=self._do_wipe).style(
                        f"background:{_CLR_DANGER} !important; color:#000000 !important;"
                        f"{_MONO} font-size:10px; padding:4px 14px; border-radius:2px;"
                    ).props("flat unelevated")
                    ui.button("Cancel", on_click=self._cancel_wipe).style(
                        "background:transparent !important;"
                        f"border:1px solid {_CLR_BORDER} !important;"
                        f"color:{_CLR_MID} !important;"
                        f"{_MONO} font-size:10px; padding:4px 14px; border-radius:2px;"
                    ).props("flat unelevated")

    # ══════════════════════════════════════════════════════════════════════
    # Timer refresh
    # ══════════════════════════════════════════════════════════════════════

    def refresh(self, state: dict) -> None:
        self._state = state

        # Uptime
        know_stats = state.get("know", {})
        op = know_stats.get("operation_stats", {})
        if self._init_time is None and op.get("compounds_stored", 0) > 0:
            self._init_time = time.time()
        if self._init_time and self._uptime_label:
            elapsed = int(time.time() - self._init_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self._uptime_label.set_text(f"uptime: {h:02d}:{m:02d}:{s:02d}")

        self._render_know_stats.refresh()
        self._render_memory_counts.refresh()

    # ══════════════════════════════════════════════════════════════════════
    # Compound browser
    # ══════════════════════════════════════════════════════════════════════

    def _on_search(self, _=None):
        know = _get_know()
        if know is None:
            return
        query = (self._search_input.value or "").strip() if self._search_input else ""
        if query:
            exact = know.by_symbol(query)
            exact_id = exact.id if exact else None
            with know._lock:
                compounds = [
                    c for c in know._compounds.values()
                    if query.lower() in c.symbol.lower()
                ]
            compounds.sort(key=lambda c: (c.id != exact_id, c.id))
            compounds = compounds[:50]
        else:
            with know._lock:
                compounds = sorted(
                    know._compounds.values(), key=lambda c: c.id, reverse=True
                )[:50]

        self._compound_table.clear()
        with self._compound_table:
            if not compounds:
                ui.label("No compounds found.").style(
                    f"font-size:11px; color:{_CLR_DIM}; {_MONO} padding:8px;"
                )
                return
            for c in compounds:
                pb_hex = hex(c.primebit) if isinstance(c.primebit, int) else str(c.primebit)
                g_colour = _CLR_ACCENT if c.grounded else _CLR_WARN
                with ui.row().classes("w-full items-center gap-0 cursor-pointer").style(
                    f"padding:3px 4px; border-bottom:1px solid {_CLR_BORDER};"
                ).on("click", lambda _, _id=c.id: self._show_compound_detail(_id)):
                    ui.label(str(c.id)).style(
                        f"font-size:11px; color:{_CLR_DIM}; {_MONO} width:44px;"
                    )
                    ui.label(c.symbol[:22]).style(
                        f"font-size:11px; color:{_CLR_BRIGHT}; {_MONO} width:140px;"
                        "overflow:hidden; white-space:nowrap; text-overflow:ellipsis;"
                    )
                    ui.label(getattr(c, "compound_type", "?")[:10]).style(
                        f"font-size:11px; color:{_CLR_MID}; {_MONO} width:72px;"
                    )
                    ui.label("✓" if c.grounded else "·").style(
                        f"font-size:11px; color:{g_colour}; {_MONO} width:36px;"
                    )
                    ui.label((c.source or "—")[:12]).style(
                        f"font-size:10px; color:{_CLR_DIM}; {_MONO} width:80px;"
                    )
                    ui.label(pb_hex[:18]).style(
                        f"font-size:10px; color:{_CLR_DIM}; {_MONO}"
                    )

    def _show_compound_detail(self, compound_id: int):
        know = _get_know()
        if know is None:
            return
        c = know.by_id(compound_id)
        if c is None:
            return
        self._compound_detail.clear()
        with self._compound_detail:
            ui.label(f"#{c.id}  {c.symbol}").style(
                f"font-size:13px; color:{_CLR_BRIGHT}; {_MONO} font-weight:bold;"
            )
            _sep()
            for fname, fval in [
                ("type",       getattr(c, "compound_type", "?")),
                ("grounded",   c.grounded),
                ("confidence", f"{c.confidence:.3f}"),
                ("version",    c.version),
                ("source",     c.source or "—"),
                ("primebit",   hex(c.primebit) if isinstance(c.primebit, int) else str(c.primebit)),
                ("resolved",   hex(c.resolved_primebit) if hasattr(c, "resolved_primebit") and isinstance(c.resolved_primebit, int) else "—"),
                ("created",    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(c.created_at))),
            ]:
                with ui.row().classes("items-baseline gap-2"):
                    ui.label(fname).style(
                        f"font-size:10px; color:{_CLR_DIM}; {_MONO} width:80px;"
                    )
                    ui.label(str(fval)).style(
                        f"font-size:11px; color:{_CLR_TEXT}; {_MONO}"
                    )
            if c.nested:
                _sep()
                ui.label(f"NESTED  ({len(c.nested)})").style(_SECTION)
                for nid in c.nested:
                    try:
                        nc  = know.by_id(nid)
                        sym = nc.symbol if nc else "?"
                    except Exception:
                        sym = "?"
                    with ui.row().classes("items-baseline gap-2").style("padding-left:10px;"):
                        ui.label(f"#{nid}").style(
                            f"font-size:10px; color:{_CLR_DIM}; {_MONO} width:44px;"
                        )
                        ui.label(sym).style(
                            f"font-size:11px; color:{_CLR_TEXT}; {_MONO}"
                            "cursor:pointer; text-decoration:underline;"
                        ).on("click", lambda _, _id=nid: self._show_compound_detail(_id))
            if c.relations:
                _sep()
                ui.label(f"RELATIONS  ({len(c.relations)})").style(_SECTION)
                for r in c.relations[:20]:
                    tgt = f"→ #{r.to}" if isinstance(r.to, int) else f"→ {r.to}"
                    ui.label(f"{r.from_prime}  {r.predicate}  {tgt}").style(
                        f"font-size:11px; color:{_CLR_TEXT}; {_MONO} padding-left:10px;"
                    )

    # ── Danger zone callbacks ─────────────────────────────────────────────

    def _show_wipe_confirm(self):
        if self._wipe_confirm:
            self._wipe_confirm.set_visibility(True)

    def _cancel_wipe(self):
        if self._wipe_confirm:
            self._wipe_confirm.set_visibility(False)

    def _do_wipe(self):
        from gui.state import log_event
        import json, os
        know = _get_know()
        if know is None:
            return
        with know._lock:
            to_remove = [cid for cid in know._compounds if cid >= 200]
            for cid in to_remove:
                del know._compounds[cid]
            know._next_id = 200
            know._symbol_index = {
                c.symbol: c.id for c in know._compounds.values()
            }
            for cid in [cid for cid in know._cache if cid >= 200]:
                del know._cache[cid]
        with know._def_lock:
            know._definitions.clear()
            know._next_def_id = 1
        with know._nar_lock:
            know._narratives.clear()
            know._next_nar_id = 1
        with know._ref_lock:
            for cid in [cid for cid in know._refinement if cid >= 200]:
                del know._refinement[cid]
        with know._tri_lock:
            know._triples.clear()
            know._triple_index.clear()
            know._next_triple_id = 1
        for key in know.stats:
            know.stats[key] = 0
        storage_dir = "storage"
        os.makedirs(storage_dir, exist_ok=True)
        try:
            for fname in (
                "compounds.json", "definitions.json", "narratives.json",
                "refinement.json", "triples.json",
            ):
                with open(os.path.join(storage_dir, fname), "w") as f:
                    json.dump({}, f)
            with open(os.path.join(storage_dir, "metadata.json"), "w") as f:
                json.dump({
                    "next_id": 200, "next_def_id": 1, "next_nar_id": 1,
                    "next_triple_id": 1, "saved_at": time.time(),
                }, f)
        except Exception as e:
            log_event(f"DEV: Wipe storage write error: {e}")
        log_event("DEV: All compounds wiped. Storage cleared.")
        if self._wipe_confirm:
            self._wipe_confirm.set_visibility(False)
        self._on_search()


# ── module helpers ────────────────────────────────────────────────────────────

def _get_know():
    try:
        from primes.KNOW import know
        return know
    except Exception:
        return None


def _card():
    return ui.card().classes("w-full").style(
        f"background:{_CLR_CARD}; border:1px solid {_CLR_BORDER};"
        "border-radius:6px; padding:14px;"
    ).props("flat")


def _sep():
    ui.separator().style(f"border-color:{_CLR_BORDER}; margin:6px 0;")
