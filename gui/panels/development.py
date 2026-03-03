"""
Development panel — real-time internal state, memory inspector, storage wipe.

Shows what PABLO is doing right now: prime status, queue depths, KNOW operation
stats, compound/definition/narrative/triple counts, a searchable compound browser
with clickable detail (primebit, nested, triples, DefinitionNarrative thread),
and a danger-zone wipe that fully resets KNOW's runtime state.
"""

import time
from nicegui import ui
from gui.panels.base import GUIPanel


# ── Colour palette (dark theme) ──────────────────────────────────────────────

_CLR_ACCENT  = "#00c8c8"
_CLR_DIM     = "#333333"
_CLR_MID     = "#555555"
_CLR_TEXT    = "#999999"
_CLR_BRIGHT  = "#cccccc"
_CLR_DANGER  = "#ff4444"
_CLR_WARN    = "#cc8800"
_CLR_BG      = "#0a0a0a"
_CLR_CARD    = "#0f0f0f"
_CLR_BORDER  = "#1a1a1a"

_MONO = "font-family:monospace;"
_SECTION = (
    f"font-size:10px; color:#444444; {_MONO} "
    "letter-spacing:0.12em; margin-bottom:4px;"
)


class DevelopmentPanel(GUIPanel):
    name  = "development"
    title = "Dev"

    def __init__(self):
        self._uptime_label     = None
        self._init_time        = None

        # prime status: name → (dot_label, status_label)
        self._prime_rows: dict = {}
        # queue depths: name → size_label
        self._queue_rows: dict = {}

        # KNOW stats
        self._stats_labels: dict = {}   # stat_key → label

        # Memory overview counts
        self._mem_counts: dict = {}     # key → label

        # Compound browser
        self._search_input     = None
        self._compound_table   = None
        self._compound_detail  = None

        # Danger zone
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
                        # Left column: status cards
                        with ui.column().classes("gap-4").style(
                            "flex:1; min-width:280px; max-width:340px;"
                        ):
                            self._build_prime_status_card()
                            self._build_queues_card()
                            self._build_know_stats_card()
                        # Right column: memory + compound browser
                        with ui.column().classes("gap-4").style(
                            "flex:2; min-width:400px;"
                        ):
                            self._build_memory_card()
                            self._build_compound_browser()
                    self._build_danger_zone()

    # ── Header ────────────────────────────────────────────────────────────

    def _build_header(self):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("PABLO  /  DEVELOPMENT").style(
                f"font-size:12px; color:{_CLR_DIM}; {_MONO} letter-spacing:0.2em;"
            )
            self._uptime_label = ui.label("uptime: --:--:--").style(
                f"font-size:11px; color:{_CLR_DIM}; {_MONO}"
            )

    # ── Prime status ──────────────────────────────────────────────────────

    def _build_prime_status_card(self):
        with _card():
            ui.label("PRIME STATUS").style(_SECTION)
            with ui.column().classes("w-full gap-1"):
                for name in ["KNOW", "READ", "SYMBOL", "DATA", "SELF", "THINK"]:
                    with ui.row().classes("items-center gap-2 w-full"):
                        dot = ui.label("●").style(
                            f"color:{_CLR_DIM}; font-size:9px;"
                        )
                        ui.label(name).style(
                            f"font-size:11px; color:{_CLR_TEXT}; {_MONO} width:55px;"
                        )
                        status_lbl = ui.label("--").style(
                            f"font-size:11px; color:{_CLR_DIM}; {_MONO}"
                        )
                        self._prime_rows[name] = (dot, status_lbl)

    # ── Queue depths ──────────────────────────────────────────────────────

    def _build_queues_card(self):
        with _card():
            ui.label("QUEUES").style(_SECTION)
            with ui.column().classes("w-full gap-1"):
                for q in ("observation", "candidate", "think", "response"):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label(q).style(
                            f"font-size:11px; color:{_CLR_TEXT}; {_MONO}"
                        )
                        lbl = ui.label("0 / 0").style(
                            f"font-size:11px; color:{_CLR_DIM}; {_MONO}"
                        )
                        self._queue_rows[q] = lbl

    # ── KNOW operation stats ──────────────────────────────────────────────

    def _build_know_stats_card(self):
        with _card():
            ui.label("KNOW OPERATIONS").style(_SECTION)
            with ui.column().classes("w-full gap-1"):
                for key, label in [
                    ("compounds_stored",    "stored"),
                    ("compounds_retrieved", "retrieved"),
                    ("cache_hits",          "cache hits"),
                    ("definitions_loaded",  "definitions"),
                    ("narratives_stored",   "narratives"),
                    ("triples_stored",      "triples"),
                    ("enrichment_queued",   "enrichment Q"),
                    ("saves_to_disk",       "disk saves"),
                    ("errors",              "errors"),
                ]:
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label(label).style(
                            f"font-size:11px; color:{_CLR_TEXT}; {_MONO}"
                        )
                        val_lbl = ui.label("0").style(
                            f"font-size:11px; color:{_CLR_DIM}; {_MONO}"
                        )
                        self._stats_labels[key] = val_lbl

    # ── Memory overview ───────────────────────────────────────────────────

    def _build_memory_card(self):
        with _card():
            ui.label("MEMORY").style(_SECTION)
            with ui.row().classes("w-full gap-6"):
                for key, label in [
                    ("total_compounds",   "Compounds"),
                    ("total_definitions", "Definitions"),
                    ("total_narratives",  "Narratives"),
                    ("total_triples",     "Triples"),
                ]:
                    with ui.column().classes("items-center gap-0"):
                        count_lbl = ui.label("--").style(
                            f"font-size:22px; color:{_CLR_ACCENT}; {_MONO}"
                        )
                        ui.label(label).style(
                            f"font-size:10px; color:{_CLR_DIM}; {_MONO}"
                        )
                        self._mem_counts[key] = count_lbl

            ui.separator().style(f"border-color:{_CLR_BORDER}; margin:8px 0;")

            with ui.row().classes("w-full gap-6"):
                for key, label in [
                    ("next_id",       "next compound ID"),
                    ("next_triple_id","next triple ID"),
                    ("cache_size",    "cache size"),
                ]:
                    with ui.column().classes("gap-0"):
                        ui.label(label).style(
                            f"font-size:9px; color:{_CLR_DIM}; {_MONO}"
                        )
                        lbl = ui.label("--").style(
                            f"font-size:12px; color:{_CLR_TEXT}; {_MONO}"
                        )
                        self._mem_counts[key] = lbl

    # ── Compound browser ──────────────────────────────────────────────────

    def _build_compound_browser(self):
        with _card():
            # Row: title + search + refresh button
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

            # Results table
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
                f"max-height:260px; overflow-y:auto;"
            )

            ui.separator().style(f"border-color:{_CLR_BORDER}; margin:10px 0;")

            # Detail pane
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
                "Wipes all runtime compounds, definitions, narratives, triples, and "
                "symbol index. Logic compounds (IDs 100–199) are preserved."
            ).style(f"font-size:11px; color:#553333; {_MONO} margin:6px 0;")

            with ui.row().classes("items-center gap-3"):
                ui.button(
                    "Wipe All Compounds", on_click=self._show_wipe_confirm
                ).style(
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
                    ui.button(
                        "Yes, wipe everything", on_click=self._do_wipe
                    ).style(
                        f"background:{_CLR_DANGER} !important;"
                        "color:#000000 !important;"
                        f"{_MONO} font-size:10px; padding:4px 14px; border-radius:2px;"
                    ).props("flat unelevated")
                    ui.button(
                        "Cancel", on_click=self._cancel_wipe
                    ).style(
                        "background:transparent !important;"
                        f"border:1px solid {_CLR_BORDER} !important;"
                        f"color:{_CLR_MID} !important;"
                        f"{_MONO} font-size:10px; padding:4px 14px; border-radius:2px;"
                    ).props("flat unelevated")

    # ══════════════════════════════════════════════════════════════════════
    # Refresh  (called every timer tick)
    # ══════════════════════════════════════════════════════════════════════

    def refresh(self, state: dict) -> None:
        # ── uptime ────────────────────────────────────────────────────────
        if self._init_time is None:
            primes = state.get("primes", {})
            if any(p.get("status") == "running" for p in primes.values()):
                self._init_time = time.time()
        if self._init_time and self._uptime_label:
            elapsed = int(time.time() - self._init_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self._uptime_label.set_text(f"uptime: {h:02d}:{m:02d}:{s:02d}")

        # ── prime status ──────────────────────────────────────────────────
        _status_colours = {
            "running": _CLR_ACCENT, "idle": _CLR_MID,
            "error": _CLR_DANGER,   "not loaded": _CLR_DIM,
        }
        for name, (dot, status_lbl) in self._prime_rows.items():
            info   = state.get("primes", {}).get(name, {})
            status = info.get("status", "not loaded")
            colour = _status_colours.get(status, _CLR_DIM)
            dot.style(f"color:{colour}; font-size:9px;")
            status_lbl.set_text(status)
            status_lbl.style(f"font-size:11px; color:{colour}; {_MONO}")

        # ── queue depths ──────────────────────────────────────────────────
        queues = state.get("queues", {})
        for q_name, lbl in self._queue_rows.items():
            q_info = queues.get(q_name, {})
            size   = q_info.get("size", 0)
            maxs   = q_info.get("maxsize", 0)
            colour = _CLR_WARN if maxs > 0 and size > maxs * 0.8 else _CLR_DIM
            lbl.set_text(f"{size} / {maxs}")
            lbl.style(f"font-size:11px; color:{colour}; {_MONO}")

        # ── KNOW stats + memory (direct access) ───────────────────────────
        know = _get_know()
        if know is None:
            return

        try:
            kstats = know._get_stats()
        except Exception:
            return

        op = kstats.get("operation_stats", {})
        for key, lbl in self._stats_labels.items():
            val    = op.get(key, 0)
            colour = _CLR_DANGER if key == "errors" and val > 0 else _CLR_DIM
            lbl.set_text(str(val))
            lbl.style(f"font-size:11px; color:{colour}; {_MONO}")

        ss = kstats.get("store_stats", {})
        for key, lbl in self._mem_counts.items():
            lbl.set_text(str(ss.get(key, "--")))

    # ══════════════════════════════════════════════════════════════════════
    # Compound browser
    # ══════════════════════════════════════════════════════════════════════

    def _on_search(self, _=None):
        know = _get_know()
        if know is None:
            return

        query = (self._search_input.value or "").strip() if self._search_input else ""

        # Collect matching compounds
        if query:
            # Exact symbol hit first
            exact = know.by_symbol(query)
            exact_id = exact.id if exact else None

            # Partial match across all compounds (guarded by lock)
            with know._lock:
                compounds = [
                    c for c in know._compounds.values()
                    if query.lower() in c.symbol.lower()
                ]
            compounds.sort(key=lambda c: (c.id != exact_id, c.id))
            compounds = compounds[:50]
        else:
            # Most-recent 50 compounds
            with know._lock:
                compounds = sorted(
                    know._compounds.values(),
                    key=lambda c: c.id,
                    reverse=True,
                )[:50]

        self._compound_table.clear()
        with self._compound_table:
            if not compounds:
                ui.label("No compounds found.").style(
                    f"font-size:11px; color:{_CLR_DIM}; {_MONO} padding:8px;"
                )
                return

            for c in compounds:
                cid = c.id
                pb_hex = (
                    hex(c.primebit.value) if hasattr(c.primebit, "value")
                    else str(c.primebit)
                )
                g_colour = _CLR_ACCENT if c.grounded else _CLR_WARN
                with ui.row().classes(
                    "w-full items-center gap-0 cursor-pointer"
                ).style(
                    f"padding:3px 4px; border-bottom:1px solid {_CLR_BORDER};"
                ).on(
                    "click", lambda _, _id=cid: self._show_compound_detail(_id)
                ):
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
            # ── headline ──────────────────────────────────────────────
            ui.label(f"#{c.id}  {c.symbol}").style(
                f"font-size:13px; color:{_CLR_BRIGHT}; {_MONO} font-weight:bold;"
            )

            # ── text representation ───────────────────────────────────
            _sep()
            _hdr("TEXT REPR")
            repr1 = _compound_to_text(c, know, depth=1)
            ui.label(repr1).style(
                f"font-size:12px; color:{_CLR_ACCENT}; {_MONO}"
                "word-break:break-word; line-height:1.5;"
            )
            repr2 = _compound_to_text(c, know, depth=2)
            if repr2 != repr1:
                _hdr("EXPANDED (depth 2)", margin_top=True)
                ui.label(repr2).style(
                    f"font-size:11px; color:{_CLR_TEXT}; {_MONO}"
                    "word-break:break-word; line-height:1.5;"
                )

            # ── core fields ───────────────────────────────────────────
            _sep()
            for fname, fval in [
                ("type",       getattr(c, "compound_type", "?")),
                ("grounded",   c.grounded),
                ("confidence", f"{c.confidence:.3f}"),
                ("version",    c.version),
                ("source",     c.source or "—"),
                ("created",    time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(c.created_at)
                )),
            ]:
                with ui.row().classes("items-baseline gap-2"):
                    ui.label(fname).style(
                        f"font-size:10px; color:{_CLR_DIM}; {_MONO} width:80px;"
                    )
                    ui.label(str(fval)).style(
                        f"font-size:11px; color:{_CLR_TEXT}; {_MONO}"
                    )

            # ── primebit ──────────────────────────────────────────────
            _sep()
            _hdr("PRIMEBIT")
            try:
                active = c.primebit.active_prime_names()
                pstr   = ", ".join(sorted(active)) if active else "(empty)"
            except Exception:
                pstr = hex(c.primebit.value) if hasattr(c.primebit, "value") else str(c.primebit)
            ui.label(pstr).style(
                f"font-size:11px; color:{_CLR_ACCENT}; {_MONO} word-break:break-all;"
            )

            # ── nested ────────────────────────────────────────────────
            if c.nested:
                _sep()
                _hdr(f"NESTED  ({len(c.nested)})")
                for nid in c.nested:
                    try:
                        nc  = know.by_id(nid)
                        sym = nc.symbol if nc else "?"
                    except Exception:
                        sym = "?"
                    with ui.row().classes("items-baseline gap-2").style(
                        "padding-left:10px;"
                    ):
                        ui.label(f"#{nid}").style(
                            f"font-size:10px; color:{_CLR_DIM}; {_MONO} width:44px;"
                        )
                        ui.label(sym).style(
                            f"font-size:11px; color:{_CLR_TEXT}; {_MONO}"
                            "cursor:pointer; text-decoration:underline;"
                        ).on("click", lambda _, _id=nid: self._show_compound_detail(_id))

            # ── relations (Compound.relations bridge) ─────────────────
            if c.relations:
                _sep()
                _hdr(f"RELATIONS  ({len(c.relations)})")
                for r in c.relations[:20]:
                    tgt = (
                        f"→ #{r.target_id}" if r.target_id is not None
                        else f"→ {r.predicate}"
                    )
                    ui.label(f"{r.predicate}  {tgt}").style(
                        f"font-size:11px; color:{_CLR_TEXT}; {_MONO} padding-left:10px;"
                    )

            # ── triples from triple store ─────────────────────────────
            try:
                triples = know.get_triples(c.id)
            except Exception:
                triples = []
            if triples:
                _sep()
                _hdr(f"TRIPLES  ({len(triples)})")
                for t in triples[:20]:
                    if t.target_id is not None:
                        try:
                            tc  = know.by_id(t.target_id)
                            tgt = f"#{t.target_id} {tc.symbol}" if tc else f"#{t.target_id}"
                        except Exception:
                            tgt = f"#{t.target_id}"
                    else:
                        tgt = t.target_prime or "?"
                    ui.label(
                        f"{t.predicate}  →  {tgt}"
                        + (f"  [{t.confidence:.2f}]" if t.confidence < 1.0 else "")
                        + (f"  src:{t.source}" if t.source else "")
                    ).style(
                        f"font-size:11px; color:{_CLR_ACCENT}; {_MONO}"
                        "padding-left:10px;"
                    )

            # ── definition narrative ──────────────────────────────────
            try:
                dn = know.get_definition(c.id)
            except Exception:
                dn = None
            if dn is not None:
                _sep()
                _hdr(f"DEFINITION NARRATIVE  #{dn.id}  ({len(dn.thread)} entries)")
                for entry in dn.thread[:10]:
                    ts   = time.strftime(
                        "%H:%M:%S", time.localtime(entry.get("timestamp", 0))
                    )
                    etype = entry.get("type", "?")
                    prov  = entry.get("provenance", {})

                    with ui.column().classes("gap-0").style(
                        f"padding-left:10px; margin-bottom:4px;"
                    ):
                        ui.label(f"{ts}  {etype}").style(
                            f"font-size:10px; color:{_CLR_DIM}; {_MONO}"
                        )
                        if prov:
                            # Show initial_grounding items
                            ig = prov.get("initial_grounding", [])
                            if ig:
                                for item in ig[:6]:
                                    ui.label(str(item)).style(
                                        f"font-size:10px; color:{_CLR_TEXT}; {_MONO}"
                                        "padding-left:12px; word-break:break-all;"
                                    )
                            else:
                                ui.label(str(prov)[:120]).style(
                                    f"font-size:10px; color:{_CLR_TEXT}; {_MONO}"
                                    "padding-left:12px; word-break:break-all;"
                                )

            # ── narrative_id ──────────────────────────────────────────
            if c.narrative_id is not None:
                _sep()
                ui.label(f"narrative_id: #{c.narrative_id}").style(
                    f"font-size:10px; color:{_CLR_DIM}; {_MONO}"
                )

    # ══════════════════════════════════════════════════════════════════════
    # Danger zone
    # ══════════════════════════════════════════════════════════════════════

    def _show_wipe_confirm(self):
        if self._wipe_confirm:
            self._wipe_confirm.set_visibility(True)

    def _cancel_wipe(self):
        if self._wipe_confirm:
            self._wipe_confirm.set_visibility(False)

    def _do_wipe(self):
        """Wipe all runtime KNOW state.

        Preserves logic compounds (IDs 100–199).  Clears compounds, definitions,
        narratives, refinement records, triples, and all storage/ JSON files.
        Rebuilds the primary relational narrative and symbol index.
        """
        from gui.state import log_event
        import json, os

        know = _get_know()
        if know is None:
            return

        # ── compounds (keep 100-199) ──────────────────────────────────
        with know._lock:
            to_remove = [cid for cid in know._compounds if cid >= 200]
            for cid in to_remove:
                del know._compounds[cid]
            know._next_id = 200

            # Rebuild symbol index from surviving compounds
            know._symbol_index = {
                c.symbol: c.id for c in know._compounds.values()
            }

            # Clear cache entries >= 200
            for cid in [cid for cid in know._cache if cid >= 200]:
                del know._cache[cid]

        # ── definitions ───────────────────────────────────────────────
        with know._def_lock:
            know._definitions.clear()
            know._next_def_id = 1

        # ── narratives ────────────────────────────────────────────────
        with know._nar_lock:
            know._narratives.clear()
            know._next_nar_id = 1

        # ── refinement ────────────────────────────────────────────────
        with know._ref_lock:
            for cid in [cid for cid in know._refinement if cid >= 200]:
                del know._refinement[cid]

        # ── triples ───────────────────────────────────────────────────
        with know._tri_lock:
            know._triples.clear()
            know._triple_index.clear()
            know._next_triple_id = 1

        # ── stats ────────────────────────────────────────────────────
        for key in know.stats:
            know.stats[key] = 0

        # ── storage files ─────────────────────────────────────────────
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
                    "next_id":        200,
                    "next_def_id":    1,
                    "next_nar_id":    1,
                    "next_triple_id": 1,
                    "saved_at":       time.time(),
                }, f)
        except Exception as e:
            log_event(f"DEV: Wipe storage write error: {e}")

        # ── re-bootstrap relational narrative ─────────────────────────
        try:
            know._bootstrap_relational_narrative()
        except Exception:
            pass

        log_event("DEV: All compounds wiped.  Storage cleared.")
        if self._wipe_confirm:
            self._wipe_confirm.set_visibility(False)

        # Refresh compound browser to show empty state
        self._on_search()


# ══════════════════════════════════════════════════════════════════════════
# Module-level helpers
# ══════════════════════════════════════════════════════════════════════════

def _get_know():
    """Return the KNOW prime instance, or None if not yet initialised."""
    try:
        from core.queues import prime_registry
        return prime_registry.get_prime("KNOW")
    except Exception:
        return None


def _card():
    """Context manager: a flat dark card."""
    return ui.card().classes("w-full").style(
        f"background:{_CLR_CARD}; border:1px solid {_CLR_BORDER};"
        "border-radius:6px; padding:14px;"
    ).props("flat")


def _sep():
    ui.separator().style(f"border-color:{_CLR_BORDER}; margin:6px 0;")


def _hdr(text: str, margin_top: bool = False):
    mt = " margin-top:4px;" if margin_top else ""
    ui.label(text).style(f"font-size:10px; color:{_CLR_DIM}; {_MONO}{mt}")


def _compound_to_text(
    compound,
    know,
    depth: int = 1,
    _seen: set | None = None,
) -> str:
    """Render compound as   symbol = PRIME1 + PRIME2 + nested_sym + …

    depth=1 : expand nested one level (show symbols).
    depth=2 : expand nested two levels.
    _seen  : guards circular nesting.
    """
    if _seen is None:
        _seen = set()
    if compound.id in _seen:
        return f"({compound.symbol}↻)"
    _seen.add(compound.id)

    parts: list[str] = []

    # Direct primes from primebit
    try:
        primes = compound.primebit.active_prime_names()
    except Exception:
        try:
            primes = compound.primebit.get_prime_names()
        except Exception:
            primes = []
    for p in sorted(primes):
        parts.append(p)

    # Nested compounds
    for nid in compound.nested:
        try:
            nc = know.by_id(nid)
            if nc is None:
                parts.append(f"?{nid}")
            elif depth > 1:
                inner = _compound_to_text(nc, know, depth - 1, _seen)
                parts.append(f"[{inner}]")
            else:
                parts.append(nc.symbol)
        except Exception:
            parts.append(f"?{nid}")

    if not parts:
        return f"{compound.symbol}  (empty)"
    return f"{compound.symbol} = " + " + ".join(parts)
