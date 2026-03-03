"""
THINK — Conscious reasoning prime.

THINK is event-driven: activated by SELF via think_queue.
It fetches compounds from KNOW, analyses primebits, routes through
a symbolic routing table, creates Layer 2 Intent compounds, maintains
rich Narrative context with semantic bindings forming a web of meaning,
and pushes responses to response_queue.

Narrative interaction follows docs/NARRATIVES/:
  - Each utterance token gets a semantically-classified Binding
  - Bindings carry inter-binding relationships (the "web")
  - Returning entities get updated with history snaps
  - Utterance frames (subject-predicate-object) are built and logged
  - The relational narrative's THIS_USER tracks social state

THINK never touches observation_queue, candidate_queue, SYMBOL, or DATA.

See docs/PRIMES/THINK/ for concept and architecture.
See docs/NARRATIVES/ for narrative concept and architecture.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from core.compound import Compound
from core.narrative import Binding, Narrative, NarrativeEvent
from core.prime_base import Prime
from core.primebit import PrimeBit
from core.queues import response_queue, think_queue

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# Semantic Role Categories
# ══════════════════════════════════════════════════════════════════════════
# Each token compound's primebits are scored against these categories to
# determine its semantic role within the utterance.

AGENT_PRIMES = frozenset({
    "YOU", "SELF", "ENTITY", "THIS", "OTHER",
})
ACTION_PRIMES = frozenset({
    "DO", "MAKE", "MOVE", "CHANGE", "CAUSE", "USE", "OPEN", "WRITE", "SAY",
})
COGNITIVE_PRIMES = frozenset({
    "KNOW", "THINK", "SEE", "HEAR", "READ", "FEEL", "WANT", "NEED",
})
PROPERTY_PRIMES = frozenset({
    "GOOD", "BAD", "MORE", "LESS", "MANY", "ONE", "SOME", "NONE", "ALL",
})
SPATIAL_PRIMES = frozenset({
    "HERE", "FAR", "NEAR", "UP", "DOWN", "LEFT", "RIGHT", "IN",
    "BETWEEN", "FROM", "TO", "SIDE",
})
TEMPORAL_PRIMES = frozenset({
    "NOW", "BEFORE", "AFTER", "LAST", "TIME",
})
STRUCTURAL_PRIMES = frozenset({
    "PART", "KIND", "WITH", "BECAUSE", "BE", "HAVE", "CAN",
    "BODY", "LIFE", "LIGHT", "HEAT", "DATA", "SYMBOL",
})

# Role → binding name prefix
ROLE_PREFIX = {
    "agent":      "THIS",
    "action":     "ACT",
    "cognitive":  "ACT",
    "property":   "MOD",
    "spatial":    "LOC",
    "temporal":   "TMP",
    "structural": "THE",
    "unknown":    "THE",
}

# Typed relationship labels for the inter-binding web
REL_SUBJECT_OF   = "subject_of"
REL_PERFORMED_BY = "performed_by"
REL_ACTS_ON      = "acts_on"
REL_OBJECT_OF    = "object_of"
REL_MODIFIES     = "modifies"
REL_MODIFIED_BY  = "modified_by"
REL_CO_OCCURS    = "co_occurs"


# ── Routing table ─────────────────────────────────────────────────────────

ROUTING_TABLE: List[tuple] = [
    ({"KNOW", "BE"},      "knowledge_query"),
    ({"SAY", "YOU"},      "directed_message"),
    ({"DO", "MOVE"},      "action_request"),
    ({"DO", "MAKE"},      "action_request"),
    ({"DO", "CHANGE"},    "action_request"),
    ({"WANT"},            "preference_expression"),
    ({"NEED"},            "requirement_expression"),
    ({"THINK", "SELF"},   "introspective_query"),
]
DEFAULT_MODE = "reflective_acknowledgement"

MACRO_THRESHOLD = 3  # Phase 2 — promote action → macro after N successes


# ══════════════════════════════════════════════════════════════════════════
# THINK class
# ══════════════════════════════════════════════════════════════════════════

class THINK(Prime):
    """Conscious reasoning engine.  Singleton via ``think``."""

    def __init__(self) -> None:
        super().__init__(name="THINK")
        self._think_thread: Optional[threading.Thread] = None
        self._running: bool = False

        # Phase 2 — action fingerprint tracking for macro candidacy
        self._action_fingerprints: Dict[int, int] = {}

        self.stats: Dict[str, int] = {
            "cycles_completed":     0,
            "intents_created":      0,
            "responses_sent":       0,
            "narratives_created":   0,
            "bindings_created":     0,
            "bindings_updated":     0,
            "frames_built":         0,
            "relationships_linked": 0,
            "errors":               0,
        }

    # ══════════════════════════════════════════════════════════════════════
    # Prime interface
    # ══════════════════════════════════════════════════════════════════════

    def _on_initialize(self) -> None:
        self._running = True
        self._think_thread = threading.Thread(
            target=self._think_loop, daemon=True, name="THINK-loop"
        )
        self._think_thread.start()
        log.info("THINK: Initialized — reasoning thread started")

    def _on_shutdown(self) -> None:
        self._running = False
        if self._think_thread and self._think_thread.is_alive():
            self._think_thread.join(timeout=2.0)
        log.info("THINK: Shutdown complete")

    def __call__(self, context: Dict[str, Any]) -> Any:
        """Consultation mode — synchronous reasoning cycle.

        Expected keys: ``utterance_id`` (int), optionally ``source``, ``salience``.
        Returns the Layer 2 Intent Compound created (or None).
        """
        item = {
            "utterance_compound_id": context["utterance_id"],
            "source":                context.get("source", "internal"),
            "salience":              context.get("salience", 1.0),
            "want_context":          "consultation",
            "feel_state":            "neutral",
        }
        return self._run_cycle(item)

    # ══════════════════════════════════════════════════════════════════════
    # Think loop (daemon thread)
    # ══════════════════════════════════════════════════════════════════════

    def _think_loop(self) -> None:
        while self._running:
            try:
                item = think_queue.get(timeout=0.1)
                self._run_cycle(item)
            except queue.Empty:
                continue
            except Exception:
                log.exception("THINK: error in think loop")
                self.stats["errors"] += 1

    # ══════════════════════════════════════════════════════════════════════
    # Semantic Role Analysis
    # ══════════════════════════════════════════════════════════════════════

    def _classify_token_role(self, compound: Compound) -> str:
        """Classify a token compound's semantic role from its primebits.

        Scores each prime category and returns the highest-scoring one.
        Ungrounded tokens (no primes) return "unknown".
        """
        primes = set(compound.primebit.get_prime_names())
        if not primes:
            return "unknown"

        scores = {
            "agent":      len(primes & AGENT_PRIMES),
            "action":     len(primes & ACTION_PRIMES),
            "cognitive":  len(primes & COGNITIVE_PRIMES),
            "property":   len(primes & PROPERTY_PRIMES),
            "spatial":    len(primes & SPATIAL_PRIMES),
            "temporal":   len(primes & TEMPORAL_PRIMES),
            "structural": len(primes & STRUCTURAL_PRIMES),
        }

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "unknown"

    def _make_binding_name(self, compound: Compound, role: str) -> str:
        """Generate a semantic binding name from compound + role.

        Special cases: YOU → THIS_USER, SELF → THIS_SELF.
        Otherwise: {ROLE_PREFIX}_{SYMBOL}.
        """
        primes = set(compound.primebit.get_prime_names())

        # Special-case primes that are always specific entities
        if "YOU" in primes:
            return "THIS_USER"
        if "SELF" in primes:
            return "THIS_SELF"

        prefix = ROLE_PREFIX.get(role, "THE")
        symbol = compound.symbol.upper().replace(" ", "_")
        # Strip trailing punctuation for cleaner names
        symbol = symbol.rstrip("?!.,;:'\"")
        if not symbol:
            symbol = f"C{compound.id}"
        return f"{prefix}_{symbol}"

    # ══════════════════════════════════════════════════════════════════════
    # Utterance Frame Construction
    # ══════════════════════════════════════════════════════════════════════

    def _build_utterance_frame(
        self,
        token_data: List[Tuple[Compound, str, str]],
    ) -> dict:
        """Build a semantic frame from token role analysis.

        Fills subject-predicate-object slots from token order and role,
        with overflow into auxiliary, modifiers, spatial, temporal, unresolved.

        Args:
            token_data: List of (compound, role, local_name) tuples in
                        utterance token order.

        Returns:
            Frame dict with semantic slots filled.
        """
        frame = {
            "subject":    None,
            "predicate":  None,
            "object":     None,
            "auxiliary":  [],
            "modifiers":  [],
            "spatial":    [],
            "temporal":   [],
            "unresolved": [],
        }

        for compound, role, local_name in token_data:
            if role == "agent":
                if frame["subject"] is None:
                    frame["subject"] = local_name
                elif frame["object"] is None:
                    frame["object"] = local_name
                else:
                    frame["modifiers"].append(local_name)

            elif role in ("action", "cognitive"):
                if frame["predicate"] is None:
                    frame["predicate"] = local_name
                else:
                    frame["auxiliary"].append(local_name)

            elif role == "property":
                frame["modifiers"].append(local_name)

            elif role == "spatial":
                frame["spatial"].append(local_name)

            elif role == "temporal":
                frame["temporal"].append(local_name)

            elif role == "structural":
                if frame["object"] is None:
                    frame["object"] = local_name
                else:
                    frame["modifiers"].append(local_name)

            else:  # "unknown"
                if frame["object"] is None:
                    frame["object"] = local_name
                else:
                    frame["unresolved"].append(local_name)

        return frame

    def _get_frame_position(self, local_name: str, frame: dict) -> str:
        """Determine what position a binding holds in the utterance frame."""
        if frame.get("subject") == local_name:
            return "subject"
        if frame.get("predicate") == local_name:
            return "predicate"
        if frame.get("object") == local_name:
            return "object"
        if local_name in frame.get("auxiliary", []):
            return "auxiliary"
        if local_name in frame.get("modifiers", []):
            return "modifier"
        if local_name in frame.get("spatial", []):
            return "spatial"
        if local_name in frame.get("temporal", []):
            return "temporal"
        return "unresolved"

    # ══════════════════════════════════════════════════════════════════════
    # Binding Resolution — Creating the Web
    # ══════════════════════════════════════════════════════════════════════

    def _resolve_bindings(
        self,
        narrative: Narrative,
        token_data: List[Tuple[Compound, str, str]],
        frame: dict,
        utterance: Compound,
        source: str,
    ) -> List[str]:
        """Create or update bindings for all tokens in the utterance.

        New entities get rich initial state including role, primes,
        co-occurrences, and frame position.

        Returning entities get a history snap preserving prior state,
        then updated with latest context.

        Returns list of local_names for all bindings touched.
        """
        now = time.time()
        all_local_names = [td[2] for td in token_data]
        touched: List[str] = []

        for compound, role, local_name in token_data:
            frame_pos = self._get_frame_position(local_name, frame)
            co_bindings = [n for n in all_local_names if n != local_name]

            existing = narrative.resolve(local_name)

            if existing is not None:
                # ── Name collision check: different compound → disambiguate ──
                if existing.compound_id != compound.id:
                    local_name = f"{local_name}_{compound.id}"
                    existing = narrative.resolve(local_name)

            if existing is not None:
                # ── Returning entity: update with history snap ────────────
                old_count = existing.current.get("utterance_count", 1)
                old_co_history = existing.current.get("co_occurrence_history", [])
                old_frames = existing.current.get("frame_roles", [])

                existing.update(
                    new_state={
                        "last_seen":             now,
                        "utterance_count":       old_count + 1,
                        "latest_role":           role,
                        "latest_frame_pos":      frame_pos,
                        "latest_co_occurred":    co_bindings,
                        "co_occurrence_history": old_co_history + [co_bindings],
                        "frame_roles":           old_frames + [{
                            "frame_pos":    frame_pos,
                            "utterance_id": utterance.id,
                            "utterance":    utterance.symbol,
                            "timestamp":    now,
                        }],
                    },
                    cause=f"Re-appeared in '{utterance.symbol}' as {frame_pos}",
                )
                self.stats["bindings_updated"] += 1
            else:
                # ── New entity: create binding with rich state ────────────
                narrative.bind(
                    local_name=local_name,
                    compound_id=compound.id,
                    initial_state={
                        "role":            role,
                        "frame_position":  frame_pos,
                        "first_seen":      now,
                        "last_seen":       now,
                        "source":          source,
                        "utterance_count": 1,
                        "grounded":        compound.grounded,
                        "confidence":      compound.confidence,
                        "primes":          list(compound.primebit.get_prime_names()),
                        "co_occurred_with":     co_bindings,
                        "co_occurrence_history": [co_bindings],
                        "frame_roles":     [{
                            "frame_pos":    frame_pos,
                            "utterance_id": utterance.id,
                            "utterance":    utterance.symbol,
                            "timestamp":    now,
                        }],
                        "relationships":   {},
                    },
                )
                self.stats["bindings_created"] += 1

            touched.append(local_name)

        return touched

    # ══════════════════════════════════════════════════════════════════════
    # Inter-Binding Relationship Enrichment
    # ══════════════════════════════════════════════════════════════════════

    def _enrich_binding_relationships(
        self,
        narrative: Narrative,
        frame: dict,
    ) -> None:
        """Cross-link bindings based on their frame positions.

        This is what creates the **web**: each binding's ``relationships``
        dict maps other binding names to typed, counted relationship records.

        Example result for "do you know this":
          THIS_USER.relationships = {
              "ACT_KNOW": {"type": "subject_of",   "count": 1, ...},
              "THE_THIS": {"type": "co_occurs",    "count": 1, ...},
          }
          ACT_KNOW.relationships = {
              "THIS_USER": {"type": "performed_by", "count": 1, ...},
              "THE_THIS":  {"type": "acts_on",      "count": 1, ...},
          }
          THE_THIS.relationships = {
              "ACT_KNOW":  {"type": "object_of",    "count": 1, ...},
              "THIS_USER": {"type": "co_occurs",    "count": 1, ...},
          }
        """
        subj_name = frame.get("subject")
        pred_name = frame.get("predicate")
        obj_name  = frame.get("object")
        links_made = 0

        def _link(a_name: str, b_name: str, a_rel: str, b_rel: str) -> None:
            nonlocal links_made
            a = narrative.resolve(a_name)
            b = narrative.resolve(b_name)
            if a is None or b is None:
                return

            a_rels = a.current.setdefault("relationships", {})
            b_rels = b.current.setdefault("relationships", {})

            now = time.time()
            # a → b
            if b_name not in a_rels:
                a_rels[b_name] = {
                    "type": a_rel, "count": 1,
                    "first_linked": now, "last_linked": now,
                }
            else:
                a_rels[b_name]["count"] += 1
                a_rels[b_name]["type"] = a_rel
                a_rels[b_name]["last_linked"] = now

            # b → a (inverse)
            if a_name not in b_rels:
                b_rels[a_name] = {
                    "type": b_rel, "count": 1,
                    "first_linked": now, "last_linked": now,
                }
            else:
                b_rels[a_name]["count"] += 1
                b_rels[a_name]["type"] = b_rel
                b_rels[a_name]["last_linked"] = now

            links_made += 2

        # Subject ↔ Predicate
        if subj_name and pred_name:
            _link(subj_name, pred_name, REL_SUBJECT_OF, REL_PERFORMED_BY)

        # Predicate ↔ Object
        if pred_name and obj_name:
            _link(pred_name, obj_name, REL_ACTS_ON, REL_OBJECT_OF)

        # Subject ↔ Object (indirect co-occurrence)
        if subj_name and obj_name:
            _link(subj_name, obj_name, REL_CO_OCCURS, REL_CO_OCCURS)

        # Modifiers + auxiliary link to predicate (or subject as fallback)
        for mod_name in frame.get("modifiers", []) + frame.get("auxiliary", []):
            target = pred_name or subj_name
            if target:
                _link(mod_name, target, REL_MODIFIES, REL_MODIFIED_BY)

        # Spatial terms link to predicate
        for loc_name in frame.get("spatial", []):
            if pred_name:
                _link(loc_name, pred_name, REL_MODIFIES, REL_MODIFIED_BY)

        # Temporal terms link to predicate
        for tmp_name in frame.get("temporal", []):
            if pred_name:
                _link(tmp_name, pred_name, REL_MODIFIES, REL_MODIFIED_BY)

        self.stats["relationships_linked"] += links_made

    # ══════════════════════════════════════════════════════════════════════
    # Relational Narrative Interaction
    # ══════════════════════════════════════════════════════════════════════

    def _update_relational_user(
        self,
        narrative: Narrative,
        utterance: Compound,
        source: str,
    ) -> None:
        """Update THIS_USER in the relational narrative with interaction data.

        Per NARRATIVES_CONCEPT: the user is THIS_USER — a binding in the
        relational Narrative.  Each interaction updates social state:
        interaction_count, last_tone, relationship_quality drift.
        """
        from primes.KNOW import know

        rel_narratives = [
            n for n in know.open_narratives()
            if n.narrative_type == "relational"
            and n.name == "relationship_user_primary"
        ]
        if not rel_narratives:
            return

        rel = rel_narratives[0]
        this_user = rel.resolve("THIS_USER")
        if this_user is None:
            return

        count = this_user.current.get("interaction_count", 0)
        curiosity = this_user.current.get("curiosity", 0.2)

        # Derive tone from utterance primes
        tone = self._infer_tone(utterance)

        # Curiosity drifts up slightly each interaction (capped at 1.0)
        new_curiosity = min(1.0, curiosity + 0.01)

        # Trust drifts up very slowly from sustained interaction
        trust = this_user.current.get("trust", 0.0)
        new_trust = min(1.0, trust + 0.005)

        this_user.update(
            new_state={
                "interaction_count":  count + 1,
                "last_interaction":   time.time(),
                "last_source":        source,
                "last_utterance":     utterance.symbol,
                "last_tone":          tone,
                "curiosity":          new_curiosity,
                "trust":              new_trust,
            },
            cause=f"User said: '{utterance.symbol}' via {source}",
        )

        # Log event in relational narrative thread too
        rel.log_event(
            type="utterance",
            text=f"User interaction #{count + 1}: '{utterance.symbol}' (tone={tone})",
            compound_id=utterance.id,
            binding_ref="THIS_USER",
        )

    def _infer_tone(self, utterance: Compound) -> str:
        """Infer conversational tone from utterance primebits.

        Phase 1 heuristic — simple prime-based classification.
        """
        primes = set(utterance.primebit.get_prime_names())
        if primes & {"WANT", "NEED"}:
            return "assertive"
        if primes & {"KNOW", "THINK"}:
            return "inquisitive"
        if primes & {"GOOD", "LIGHT", "LIFE"}:
            return "warm"
        if primes & {"BAD", "NONE"}:
            return "negative"
        if primes & {"DO", "MAKE", "MOVE", "CHANGE"}:
            return "directive"
        return "neutral"

    # ══════════════════════════════════════════════════════════════════════
    # Reasoning Cycle
    # ══════════════════════════════════════════════════════════════════════

    def _run_cycle(self, item: dict) -> Optional[Compound]:
        """Execute the full reasoning cycle for one think_queue item.

        Steps:
          1. Fetch utterance compound from KNOW
          2. Identify or create Narrative context (episodic)
          3. Fetch token compounds + classify semantic roles
          4. Build utterance frame (subject-predicate-object)
          5. Resolve bindings (create new / update returning with snaps)
          6. Enrich inter-binding relationships (the web)
          7. Log utterance event with frame + state_change events
          8. Update relational narrative THIS_USER
          9. Check active Constraints (Phase 2 — structures only)
         10. PrimeBit population analysis
         11. Routing
         12. Intent construction (Layer 2)
         13. Log intent event
         14. Compose response
         15. Push to response_queue
        """
        from primes.KNOW import know

        utterance_id = item["utterance_compound_id"]
        source = item.get("source", "unknown")

        # ── Step 1: Fetch utterance compound ──────────────────────────
        utterance = know.by_id(utterance_id)
        if utterance is None:
            log.warning("THINK: utterance %d not found in KNOW", utterance_id)
            self.stats["errors"] += 1
            return None

        # ── Step 2: Identify or create Narrative context ──────────────
        narrative = know.narrative_by_source(source)
        if narrative is None:
            narrative = Narrative(
                name=f"session_{source}",
                narrative_type="episodic",
                status="open",
            )
            know.store_narrative(narrative)
            self.stats["narratives_created"] += 1
            log.info(
                "THINK: Created narrative '%s' (id=%d)",
                narrative.name, narrative.id,
            )

        # ── Step 3: Fetch tokens + classify semantic roles ────────────
        token_ids = utterance.nested or []
        token_compounds = know.by_ids(token_ids) if token_ids else []

        token_data: List[Tuple[Compound, str, str]] = []
        for tc in token_compounds:
            role = self._classify_token_role(tc)
            local_name = self._make_binding_name(tc, role)
            token_data.append((tc, role, local_name))

        # ── Step 4: Build utterance frame ─────────────────────────────
        frame = self._build_utterance_frame(token_data)
        self.stats["frames_built"] += 1

        # ── Step 5: Resolve bindings (create / update with snaps) ─────
        touched_names = self._resolve_bindings(
            narrative, token_data, frame, utterance, source,
        )

        # ── Step 6: Enrich inter-binding relationships (the web) ──────
        self._enrich_binding_relationships(narrative, frame)

        # ── Step 7: Log events ────────────────────────────────────────
        # Compact frame for storage (omit empty slots)
        clean_frame = {k: v for k, v in frame.items() if v}

        utt_event = narrative.log_event(
            type="utterance",
            text=(
                f"Received: '{utterance.symbol}'"
                f" | frame: {json.dumps(clean_frame)}"
            ),
            compound_id=utterance.id,
        )

        # Log state_change events for bindings that were updated
        # (returning entities with history)
        for tc, role, local_name in token_data:
            binding = narrative.resolve(local_name)
            if binding and len(binding.history) > 0:
                fp = self._get_frame_position(local_name, frame)
                narrative.log_event(
                    type="state_change",
                    text=(
                        f"{local_name} re-appeared as {fp}"
                        f" in '{utterance.symbol}'"
                        f" (count={binding.current.get('utterance_count', '?')})"
                    ),
                    compound_id=tc.id,
                    binding_ref=local_name,
                )

        # ── Step 8: Update relational narrative THIS_USER ─────────────
        self._update_relational_user(narrative, utterance, source)

        # ── Step 9: Check active Constraints (Phase 2) ────────────────
        _active = narrative.active_constraints()

        # ── Step 10: PrimeBit population analysis ─────────────────────
        population = self._analyse_population(token_compounds)
        dominant_primebit = self._build_dominant_primebit(
            token_compounds, population,
        )

        # ── Step 11: Routing ──────────────────────────────────────────
        mode = self._determine_routing(dominant_primebit)

        # ── Step 12: Intent construction (Layer 2) ────────────────────
        intent_primebit = PrimeBit(utterance.primebit.value)
        if not intent_primebit.has_prime("THINK"):
            think_bit = PrimeBit.from_prime_names({"THINK"})
            intent_primebit = PrimeBit(intent_primebit.value | think_bit.value)

        intent = Compound.intent(
            temp_id=-1,
            symbol=self._compose_intent_symbol(mode, utterance, population),
            primebit=intent_primebit,
            utterance_id=utterance.id,
        )

        intent_id = know.store(intent)
        self.stats["intents_created"] += 1

        # ── Step 13: Log intent event with frame ─────────────────────
        narrative.log_event(
            type="response",
            text=(
                f"Intent created: mode={mode}"
                f" | frame: {json.dumps(clean_frame)}"
            ),
            compound_id=intent_id,
        )

        # ── Step 14: Compose response ────────────────────────────────
        response_text = self._compose_response(
            mode, utterance, population, narrative, frame,
        )

        # ── Step 15: Push to response_queue ──────────────────────────
        response_queue.put({
            "timestamp":   time.time(),
            "type":        "response",
            "text":        response_text,
            "compound_id": intent_id,
            "source":      source,
            "frame":       clean_frame,
        })
        self.stats["responses_sent"] += 1
        self.stats["cycles_completed"] += 1

        log.info(
            "THINK: Cycle complete — mode=%s, intent=%d, bindings=%d, text=%r",
            mode, intent_id, len(touched_names), response_text[:60],
        )
        return intent

    # ══════════════════════════════════════════════════════════════════════
    # Population Analysis
    # ══════════════════════════════════════════════════════════════════════

    def _analyse_population(self, token_compounds: list) -> Dict[str, int]:
        """Count prime occurrences across all token compounds."""
        counts: Dict[str, int] = {}
        for tc in token_compounds:
            for name in tc.primebit.get_prime_names():
                counts[name] = counts.get(name, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def _build_dominant_primebit(
        self,
        token_compounds: list,
        population: Dict[str, int],
    ) -> PrimeBit:
        """Build a PrimeBit containing primes appearing in >50% of tokens."""
        n = len(token_compounds)
        if n == 0:
            return PrimeBit(0)
        threshold = n / 2
        dominant_names = {p for p, count in population.items() if count > threshold}
        if not dominant_names:
            dominant_names = set(population.keys())
        return PrimeBit.from_prime_names(dominant_names)

    # ══════════════════════════════════════════════════════════════════════
    # Routing
    # ══════════════════════════════════════════════════════════════════════

    def _determine_routing(self, dominant_primebit: PrimeBit) -> str:
        """Match dominant primebit against routing table."""
        for prime_set, mode in ROUTING_TABLE:
            if all(dominant_primebit.has_prime(p) for p in prime_set):
                return mode
        return DEFAULT_MODE

    # ══════════════════════════════════════════════════════════════════════
    # Response Composition
    # ══════════════════════════════════════════════════════════════════════

    def _compose_intent_symbol(
        self,
        mode: str,
        utterance: Compound,
        population: Dict[str, int],
    ) -> str:
        """Human-readable symbol for the Intent compound."""
        top_primes = list(population.keys())[:3]
        primes_str = "+".join(top_primes) if top_primes else "NONE"
        return f"[{mode}] {utterance.symbol} ({primes_str})"

    def _compose_response(
        self,
        mode: str,
        utterance: Compound,
        population: Dict[str, int],
        narrative: Narrative,
        frame: dict,
    ) -> str:
        """Produce response text based on routing mode."""
        handler = getattr(self, f"_respond_{mode}", None)
        if handler is not None:
            return handler(utterance, population, narrative, frame)
        return self._respond_reflective_acknowledgement(
            utterance, population, narrative, frame,
        )

    # ── Per-mode response handlers ────────────────────────────────────────

    def _respond_knowledge_query(
        self,
        utterance: Compound,
        population: Dict[str, int],
        narrative: Narrative,
        frame: dict,
    ) -> str:
        from primes.KNOW import know
        # Identify what's being asked about from the frame
        target_name = frame.get("object") or frame.get("subject")
        target_binding = narrative.resolve(target_name) if target_name else None

        # Query KNOW for compounds related to the dominant primes
        top_primes = list(population.keys())[:2]
        related = []
        for p in top_primes:
            related.extend(know.by_prime(p))
        if related:
            symbols = [c.symbol for c in related[:5] if c.symbol != utterance.symbol]
            if symbols:
                context = ""
                if target_binding:
                    rels = target_binding.current.get("relationships", {})
                    if rels:
                        context = f" ({target_name} is linked to {len(rels)} other concepts)"
                return f"I know about: {', '.join(symbols)}.{context}"
        return f"I received your query '{utterance.symbol}' but have limited knowledge so far."

    def _respond_directed_message(
        self,
        utterance: Compound,
        population: Dict[str, int],
        narrative: Narrative,
        frame: dict,
    ) -> str:
        return f"I hear you: '{utterance.symbol}'."

    def _respond_action_request(
        self,
        utterance: Compound,
        population: Dict[str, int],
        narrative: Narrative,
        frame: dict,
    ) -> str:
        action = frame.get("predicate", "unknown action")
        return f"Action requested: '{utterance.symbol}' (verb: {action}). (Execution is Phase 2.)"

    def _respond_preference_expression(
        self,
        utterance: Compound,
        population: Dict[str, int],
        narrative: Narrative,
        frame: dict,
    ) -> str:
        return f"Noted preference: '{utterance.symbol}'."

    def _respond_requirement_expression(
        self,
        utterance: Compound,
        population: Dict[str, int],
        narrative: Narrative,
        frame: dict,
    ) -> str:
        return f"Noted requirement: '{utterance.symbol}'."

    def _respond_introspective_query(
        self,
        utterance: Compound,
        population: Dict[str, int],
        narrative: Narrative,
        frame: dict,
    ) -> str:
        from primes.KNOW import know
        stats = know.statistics()
        binding_count = len(narrative.bindings)
        rel_count = sum(
            len(b.current.get("relationships", {}))
            for b in narrative.bindings.values()
        )
        return (
            f"Introspection: I have {stats.get('compounds_stored', 0)} compounds, "
            f"{stats.get('narratives_stored', 0)} narratives, "
            f"{binding_count} active bindings with {rel_count} relationships "
            f"in the current context."
        )

    def _respond_reflective_acknowledgement(
        self,
        utterance: Compound,
        population: Dict[str, int],
        narrative: Narrative,
        frame: dict,
    ) -> str:
        top = list(population.keys())[:3]
        # Include frame info in the acknowledgement
        frame_desc = ""
        if frame.get("subject") and frame.get("predicate"):
            frame_desc = f" (subject={frame['subject']}, verb={frame['predicate']}"
            if frame.get("object"):
                frame_desc += f", object={frame['object']}"
            frame_desc += ")"
        if top:
            return (
                f"I understood '{utterance.symbol}' with primes: "
                f"{', '.join(top)}.{frame_desc}"
            )
        return f"I received '{utterance.symbol}' but could not identify dominant primes."


# ── Singleton ─────────────────────────────────────────────────────────────
think = THINK()
