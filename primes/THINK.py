"""
THINK — Conscious reasoning prime.

Watches for scenes promoted to conscious foreground that have no intent yet.
Runs the full reasoning pipeline:

  1. Graph reading pass  — walk pre-fetched neighborhoods into proposition sets
  2. Route              — match prime_field_bits to a reasoning mode
  3. Reason             — mode-specific steps to form response content
  4. Intent Compound    — crystallise the reasoning into prime-space, write to KNOW
  5. Response text      — Phase 1 template assembly
  6. SymbolicScene      — reasoning chain + narrative fragment

Entry condition: scene.thread_type == "conscious" AND scene.intent_id is None.

THINK never calls another prime directly.  It reads KNOW's store (shared storage)
and writes to the CognitiveScene.

See docs/PRIMES/think.md for full spec.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from core.cognitive_scene import CognitiveScene, SceneContribution, scene_store
from core.compound import Compound, Relation
from core.prime_base import Prime
from core.primebit import PrimeBit, PRIME_TO_BIT, PRIME_INDEX


# ══════════════════════════════════════════════════════════════════════════════
# Prime family classification
# ══════════════════════════════════════════════════════════════════════════════

_STRUCTURAL_PRIMES: frozenset[str] = frozenset({
    "KIND", "PART", "BE", "WITH", "HAVE", "FROM", "TO", "AT", "IN",
    "BETWEEN", "SIDE", "NEAR", "FAR", "UP", "DOWN", "LEFT", "RIGHT",
    "HERE", "THIS", "OTHER", "ENTITY", "BODY",
})

_ACTION_PRIMES: frozenset[str] = frozenset({
    "DO", "MOVE", "MAKE", "CHANGE", "USE", "CAUSE", "OPEN", "WRITE", "BECAUSE",
})

_COGNITIVE_PRIMES: frozenset[str] = frozenset({
    "THINK", "KNOW", "WANT", "NEED", "FEEL", "CAN", "SELF", "YOU", "LIFE",
    "GOOD", "BAD", "MORE", "LESS", "LIGHT", "HEAT",
    "ONE", "MANY", "ALL", "SOME", "NONE",
    "NOW", "BEFORE", "AFTER", "LAST", "TIME",
    "HEAR", "SEE", "TOUCH", "READ", "SAY",
})

# Triple-type confidence weights
_TRIPLE_TYPE_WEIGHT: dict[str, float] = {
    "definition": 1.0,
    "semantic":   0.9,
    "observed":   0.8,
    "inferred":   0.6,
    "candidate":  0.3,
}

_PRUNE_THRESHOLD = 0.15   # propositions below this weight are dropped


# ══════════════════════════════════════════════════════════════════════════════
# Routing table — (required_bits_set, reasoning_mode)
# Evaluated in order; first match wins
# ══════════════════════════════════════════════════════════════════════════════

def _bits(*names: str) -> int:
    result = 0
    for n in names:
        if n in PRIME_TO_BIT:
            result |= (1 << PRIME_TO_BIT[n])
    return result


_ROUTING_TABLE: list[tuple[int, int, str]] = [
    # (required_bits, any_of_bits, mode)
    # any_of_bits == 0 means only required_bits checked
    (_bits("THINK", "SELF"),  0,                                      "introspective_query"),
    (_bits("NEED"),           0,                                      "requirement_expression"),
    (_bits("WANT"),           0,                                      "preference_expression"),
    (_bits("SAY", "YOU"),     0,                                      "directed_message"),
    (_bits("DO"),             _bits("MOVE", "MAKE", "CHANGE"),        "action_request"),
    (_bits("KNOW"),           _bits("BE"),                            "knowledge_query"),
    (_bits("BE"),             0,                                      "knowledge_query"),
    (0,                       0,                                      "reflective_acknowledgement"),
]


def _select_mode(prime_field_bits: int) -> str:
    for required, any_of, mode in _ROUTING_TABLE:
        if required and (prime_field_bits & required) != required:
            continue
        if any_of and not (prime_field_bits & any_of):
            continue
        return mode
    return "reflective_acknowledgement"


# Phase 1 surface-form bootstrap patterns.
# Used ONLY when prime_field_bits == 0 (all tokens resolved to placeholders).
# Each entry: (phrase_tokens, any_tokens, mode)
#   phrase_tokens — ALL must be present (phrase match)
#   any_tokens    — ANY one is sufficient (keyword match)
# Evaluated in order; first match wins.
# Retired once the dictionary covers these function words and intent markers.
_SURFACE_PATTERNS: list[tuple[frozenset[str], frozenset[str], str]] = [
    # Phrase matches first (more specific)
    (frozenset({"what", "are", "you"}),    frozenset(),                          "introspective_query"),
    (frozenset({"who", "are", "you"}),     frozenset(),                          "introspective_query"),
    (frozenset({"how", "do", "you"}),      frozenset(),                          "introspective_query"),
    (frozenset({"what", "is", "your"}),    frozenset(),                          "introspective_query"),
    # Keyword matches (any one word sufficient)
    (frozenset(),                           frozenset({"want", "wish", "like"}),  "preference_expression"),
    (frozenset(),                           frozenset({"need", "require"}),        "requirement_expression"),
    (frozenset(),                           frozenset({"what", "which", "who"}),   "knowledge_query"),
    (frozenset(),                           frozenset({"hello", "hi", "hey",
                                                       "bye", "goodbye", "thanks"}), "directed_message"),
    (frozenset(),                           frozenset({"do", "make", "create",
                                                       "open", "run", "execute"}), "action_request"),
]


def _select_mode_with_surface(prime_field_bits: int, tokens: list[str]) -> str:
    """
    Route using primebit first; fall back to surface-form patterns if bits are
    empty (all placeholder compounds).  Phase 1 scaffold only.
    """
    mode = _select_mode(prime_field_bits)
    if mode != "reflective_acknowledgement":
        return mode
    if prime_field_bits != 0:
        return mode   # bits present but no match — genuine fallback

    # All tokens were placeholders — try surface patterns as bootstrap
    token_set = {t.lower() for t in tokens}
    for phrase, any_kw, surface_mode in _SURFACE_PATTERNS:
        phrase_match = phrase <= token_set if phrase else True
        any_match    = bool(any_kw & token_set) if any_kw else True
        if phrase_match and any_match:
            return surface_mode
    return "reflective_acknowledgement"


# ══════════════════════════════════════════════════════════════════════════════
# Proposition helpers
# ══════════════════════════════════════════════════════════════════════════════

def _popcount(n: int) -> int:
    return bin(n).count("1")


def _proposition_weight(confidence: float, triple_type: str, scene_bits: int, compound_bits: int) -> float:
    type_w = _TRIPLE_TYPE_WEIGHT.get(triple_type, 0.5)
    max_overlap = max(_popcount(compound_bits), 1)
    overlap = _popcount(scene_bits & compound_bits) / max_overlap if max_overlap else 0.0
    return confidence * type_w * (0.5 + 0.5 * overlap)


# ══════════════════════════════════════════════════════════════════════════════
# THINK prime
# ══════════════════════════════════════════════════════════════════════════════

class THINK(Prime):
    """
    Conscious reasoner.  Polls the scene store for promoted conscious scenes
    with no intent_id yet, then runs the full reasoning pipeline.
    """

    POLL_INTERVAL = 0.025   # 25 ms

    def __init__(self) -> None:
        super().__init__("THINK")
        self._thread: threading.Thread | None = None
        self._processed: set[str] = set()
        self._processed_lock = threading.Lock()

    def _on_initialize(self) -> None:
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="THINK-poll",
            daemon=True,
        )
        self._thread.start()

    def _on_shutdown(self) -> None:
        pass

    def __call__(self, context: dict) -> None:
        raise NotImplementedError("THINK is autonomous; do not call directly.")

    # ── Poll loop ─────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while not self._shutdown_flag.is_set():
            try:
                for scene in scene_store.conscious_queue():
                    if self._should_process(scene):
                        self._process(scene)
            except Exception:
                import traceback
                traceback.print_exc()
            time.sleep(self.POLL_INTERVAL)

    def _should_process(self, scene: CognitiveScene) -> bool:
        if scene.intent_id is not None:
            return False
        if scene.response_text is not None:
            return False
        with self._processed_lock:
            if scene.scene_id in self._processed:
                return False
        return True

    # ══════════════════════════════════════════════════════════════════════
    # Main reasoning pipeline
    # ══════════════════════════════════════════════════════════════════════

    def _process(self, scene: CognitiveScene) -> None:
        with self._processed_lock:
            self._processed.add(scene.scene_id)

        scene.write(think_cycles=scene.think_cycles + 1)

        # 1. Graph reading pass
        active_propositions = self._build_proposition_set(scene)

        # 2. Route (primebit first; surface bootstrap if all placeholders)
        mode = _select_mode_with_surface(scene.prime_field_bits, scene.preliminary_tokens)

        # 3. Reason within mode
        response_text, prop_summary = self._reason(scene, mode, active_propositions)

        # 4. Intent Compound
        intent_primebit = self._propositions_to_primebit(active_propositions, scene.prime_field_bits)
        intent_confidence = (
            sum(p["weight"] for p in active_propositions) / max(len(active_propositions), 1)
            if active_propositions else 0.3
        )
        all_grounded = all(
            p.get("grounded", False) for p in active_propositions
        ) if active_propositions else False

        try:
            from primes.KNOW import know
            intent = Compound(
                id=0,
                symbol=f"{mode}:{scene.scene_id[:8]}",
                primebit=PrimeBit(intent_primebit),
                definition=prop_summary,
                nested=list(scene.concept_ids),
                relations=[
                    Relation(predicate="FROM", target_id=scene.utterance_id)
                ] if scene.utterance_id else [],
                narrative_id=None,
                grounded=all_grounded,
                version=0,
                confidence=intent_confidence,
                executable=False,
                trigger_condition=None,
                arity=0,
                slots=[],
                source="THINK",
                compound_type="intent",
            )
            intent_id = know.store(intent)
        except Exception:
            intent_id = None

        # 5. Write execution layer
        scene.write(
            reasoning_mode=mode,
            intent_id=intent_id,
            response_text=response_text,
        )

        # 6. SymbolicScene contribution
        think_bit = PrimeBit(1 << PRIME_TO_BIT["THINK"]) if "THINK" in PRIME_TO_BIT else PrimeBit(0)
        if intent_id is not None:
            try:
                from primes.KNOW import know
                intent_compound = know.by_id(intent_id)
                if intent_compound:
                    scene.contribute_symbolic(SceneContribution(
                        prime="THINK",
                        compounds=[intent_compound],
                        triples=[],
                        narrative_fragment=f"{mode}: {prop_summary[:120]}",
                    ))
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════════════
    # Graph reading pass
    # ══════════════════════════════════════════════════════════════════════

    def _build_proposition_set(self, scene: CognitiveScene) -> list[dict]:
        """
        Walk pre-fetched neighborhoods and return weighted proposition dicts.
        Each proposition: {subj, pred, target, weight, triple_type, family, grounded}
        """
        propositions: list[dict] = []
        scene_bits = scene.prime_field_bits

        for cid, neighborhood in scene.neighborhoods.items():
            root_id = neighborhood.get("root_id", cid)
            compounds = neighborhood.get("compounds", {})
            triples = neighborhood.get("triples", {})

            root_rec = compounds.get(root_id, {})
            root_primebit = root_rec.get("primebit", 0)

            for subj, pred, target, ttype in triples.get(root_id, []):
                if not pred:
                    continue

                family = self._prime_family(pred)
                weight = _proposition_weight(
                    confidence=1.0 if root_rec.get("grounded") else 0.6,
                    triple_type=ttype,
                    scene_bits=scene_bits,
                    compound_bits=root_primebit,
                )
                if weight < _PRUNE_THRESHOLD:
                    continue

                propositions.append({
                    "root_id":    root_id,
                    "subj":       subj,
                    "pred":       pred,
                    "target":     target,
                    "weight":     weight,
                    "triple_type": ttype,
                    "family":     family,
                    "grounded":   bool(root_rec.get("grounded")),
                })

        # Sort by weight descending, keep top 40
        propositions.sort(key=lambda p: p["weight"], reverse=True)
        return propositions[:40]

    @staticmethod
    def _prime_family(prime_name: str) -> str:
        if prime_name in _STRUCTURAL_PRIMES:
            return "structural"
        if prime_name in _ACTION_PRIMES:
            return "action"
        if prime_name in _COGNITIVE_PRIMES:
            return "cognitive"
        return "other"

    @staticmethod
    def _propositions_to_primebit(propositions: list[dict], scene_bits: int) -> int:
        """Union primebit of all proposition predicates + scene bits."""
        bits = scene_bits
        for p in propositions:
            bit = PRIME_TO_BIT.get(p["pred"])
            if bit is not None:
                bits |= (1 << bit)
        return bits

    # ══════════════════════════════════════════════════════════════════════
    # Reasoning modes
    # ══════════════════════════════════════════════════════════════════════

    def _reason(
        self,
        scene: CognitiveScene,
        mode: str,
        propositions: list[dict],
    ) -> tuple[str, str]:
        """
        Execute the selected reasoning mode.
        Returns (response_text, prop_summary_for_intent).
        """
        if mode == "knowledge_query":
            return self._mode_knowledge_query(scene, propositions)
        if mode == "directed_message":
            return self._mode_directed_message(scene, propositions)
        if mode == "action_request":
            return self._mode_action_request(scene, propositions)
        if mode == "preference_expression":
            return self._mode_preference_expression(scene, propositions)
        if mode == "requirement_expression":
            return self._mode_requirement_expression(scene, propositions)
        if mode == "introspective_query":
            return self._mode_introspective_query(scene, propositions)
        return self._mode_reflective_acknowledgement(scene, propositions)

    # ── knowledge_query ───────────────────────────────────────────────────

    def _mode_knowledge_query(
        self, scene: CognitiveScene, propositions: list[dict]  # noqa: ARG002
    ) -> tuple[str, str]:
        # Infer subject from proposition graph — not from token order
        subject_cid, subject_symbol = self._infer_subject(scene)

        # Collect propositions specifically for the subject compound
        # (walk its neighborhood triples, not the scene-wide proposition set)
        kind_chain:   list[str] = []
        be_props:     list[str] = []
        action_props: list[str] = []

        subject_neighborhood = scene.neighborhoods.get(subject_cid, {}) if subject_cid else {}
        subject_triples = subject_neighborhood.get("triples", {}).get(subject_cid, [])

        for _, pred, target, _ in subject_triples:
            if not target:
                continue
            if pred == "KIND":
                kind_chain.append(target)
            elif pred in ("BE", "WITH", "HAVE", "PART"):
                be_props.append(f"{target}")
            elif pred in _ACTION_PRIMES:
                action_props.append(f"{pred.lower()} {target}")

        # Try to get a stored definition text from KNOW
        stored_def = ""
        if subject_cid is not None:
            try:
                from primes.KNOW import know
                c = know.by_id(subject_cid)
                if c and c.definition:
                    stored_def = c.definition
            except Exception:
                pass

        # Build response
        parts: list[str] = []
        if stored_def:
            parts.append(stored_def)
        else:
            if kind_chain:
                parts.append(f'"{subject_symbol}" is a kind of {kind_chain[0]}.')
            if be_props:
                parts.append(f"It is {', '.join(be_props[:4])}.")
            if action_props:
                parts.append(f"It can {', '.join(action_props[:2])}.")
            if not parts:
                # No structural propositions — check if we even know the word
                if subject_cid is not None:
                    parts.append(f'I know "{subject_symbol}" but have no definition for it yet.')
                else:
                    parts.append(f'I don\'t have "{subject_symbol}" in memory.')

        summary = f"subject:{subject_symbol} | KIND:{','.join(kind_chain[:2])} | props:{len(subject_triples)}"
        return " ".join(parts), summary

    # ── directed_message ──────────────────────────────────────────────────

    def _mode_directed_message(
        self, scene: CognitiveScene, propositions: list[dict]
    ) -> tuple[str, str]:
        # Classify the speech act from the known symbols
        text_lower = scene.raw_input.lower().strip()

        # Social / relational patterns
        greetings = {"hello", "hi", "hey", "good morning", "good afternoon",
                     "good evening", "greetings", "howdy"}
        farewells  = {"bye", "goodbye", "see you", "farewell", "ciao"}
        thanks     = {"thanks", "thank you", "cheers", "appreciate"}

        tokens_set = set(scene.known_symbols + scene.preliminary_tokens)
        tokens_lower = {t.lower() for t in tokens_set}

        quality = scene.relationship_quality or 0.0

        if tokens_lower & greetings:
            tone = "warmly" if quality > 0.3 else "neutrally"
            response = self._greeting_response(tone)
            return response, "social:greeting"

        if tokens_lower & farewells:
            response = "Goodbye. Until next time."
            return response, "social:farewell"

        if tokens_lower & thanks:
            response = "You're welcome."
            return response, "social:thanks"

        # Declarative: user asserted something — acknowledge
        if scene.known_symbols:
            symbols = ", ".join(f'"{s}"' for s in scene.known_symbols[:4])
            response = f"I understood your message about {symbols}."
        else:
            response = "I received your message."

        return response, f"directed:ack:{','.join(scene.known_symbols[:3])}"

    def _greeting_response(self, tone: str) -> str:
        if tone == "warmly":
            return "Hello! Good to hear from you."
        return "Hello."

    # ── action_request ────────────────────────────────────────────────────

    def _mode_action_request(
        self, scene: CognitiveScene, propositions: list[dict]
    ) -> tuple[str, str]:
        # Phase 1: identify the action but do not execute
        action_props = [p for p in propositions if p["family"] == "action"]
        action_verbs = list({p["pred"].lower() for p in action_props})

        subject = self._best_subject(scene)
        if action_verbs:
            response = (
                f"I understood a request to {action_verbs[0]} \"{subject}\". "
                f"Action execution is not available in Phase 1."
            )
            summary = f"action:{action_verbs[0]}:{subject}"
        else:
            response = (
                f"I understood an action request involving \"{subject}\". "
                f"Action execution is not available in Phase 1."
            )
            summary = f"action:unknown:{subject}"

        return response, summary

    # ── preference_expression ─────────────────────────────────────────────

    def _mode_preference_expression(
        self, scene: CognitiveScene, propositions: list[dict]
    ) -> tuple[str, str]:
        subject = self._best_subject(scene)
        response = f"Understood. You want \"{subject}\". I've noted that."

        # Store the preference as an assertion triple if KNOW is available
        self._store_assertion(scene, "WANT", subject)

        return response, f"preference:WANT:{subject}"

    # ── requirement_expression ────────────────────────────────────────────

    def _mode_requirement_expression(
        self, scene: CognitiveScene, propositions: list[dict]
    ) -> tuple[str, str]:
        subject = self._best_subject(scene)
        response = f"Understood. You need \"{subject}\". I've noted that."
        self._store_assertion(scene, "NEED", subject)
        return response, f"requirement:NEED:{subject}"

    # ── introspective_query ───────────────────────────────────────────────

    def _mode_introspective_query(
        self, scene: CognitiveScene, propositions: list[dict]
    ) -> tuple[str, str]:
        text_lower = scene.raw_input.lower()

        # Identity questions
        if any(phrase in text_lower for phrase in ["what are you", "who are you"]):
            response = (
                "I am PABLO — a neurosymbolic cognitive architecture built from "
                "63 semantic primitives. My reasoning is symbolic, grounded in primes, "
                "not in pattern-matched text."
            )
            return response, "introspect:identity"

        # Process questions
        if any(phrase in text_lower for phrase in ["how do you work", "how do you think"]):
            response = (
                "I process input through a pipeline: READ perceives text, "
                "SYMBOL interprets it, KNOW resolves tokens to Compounds and "
                "retrieves neighborhood graphs, SELF gates attention, "
                "THINK reasons symbolically, SAY expresses the result."
            )
            return response, "introspect:process"

        # Memory questions
        subject = self._best_subject(scene)
        if subject:
            try:
                from primes.KNOW import know
                compounds = know.all_by_symbol(subject)
                if compounds:
                    count = len(compounds)
                    response = (
                        f"I have {count} compound(s) for \"{subject}\" in memory. "
                        f"The first has primes: {compounds[0].primebit.get_prime_names()[:5]}."
                    )
                else:
                    response = f"I don't have \"{subject}\" in memory."
            except Exception:
                response = f"I couldn't search memory for \"{subject}\" right now."
            return response, f"introspect:memory:{subject}"

        response = "I'm not sure what aspect of myself you're asking about."
        return response, "introspect:unclear"

    # ── reflective_acknowledgement ────────────────────────────────────────

    def _mode_reflective_acknowledgement(
        self, scene: CognitiveScene, propositions: list[dict]
    ) -> tuple[str, str]:
        known = scene.known_symbols
        unknown = scene.unresolved_tokens

        if not known and not unknown:
            return "I received your input but couldn't resolve any known concepts.", "reflect:empty"

        parts: list[str] = []
        if known:
            parts.append(f"I recognised: {', '.join(known[:5])}.")
        if unknown:
            parts.append(f"I couldn't place: {', '.join(unknown[:3])}.")
        if not propositions:
            parts.append("No strong prime pattern — could you clarify?")

        return " ".join(parts), f"reflect:{','.join(known[:3])}"

    # ── Subject inference ─────────────────────────────────────────────────

    # Function words that cannot be the semantic subject of a query.
    # Identified by having no substantive structural triples of their own,
    # or by being grammatical markers universally.
    _FUNCTION_WORDS: frozenset[str] = frozenset({
        "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
        "is", "are", "was", "were", "be", "been", "being",
        "a", "an", "the", "this", "that", "these", "those",
        "do", "does", "did", "have", "has", "had",
        "i", "you", "he", "she", "it", "we", "they",
        "me", "him", "her", "us", "them",
        "to", "of", "in", "on", "at", "by", "for", "with", "about",
        "and", "or", "but", "not", "no", "yes",
    })

    def _infer_subject(self, scene: CognitiveScene) -> tuple[int | None, str]:
        """
        Infer the semantic subject of the scene from the proposition graph
        and narrative, not from token order.

        Returns (compound_id, symbol) of the most likely subject.
        Falls back to (None, raw_input[:30]) if nothing can be inferred.

        Strategy:
          1. Score each resolved compound by its neighborhood richness
             (number of substantive triples × mean weight).
          2. Filter out function words.
          3. If a narrative entity is strongly present, prefer it.
          4. Return the highest-scoring candidate.
        """
        # Build candidate scores from neighborhoods
        # {cid: (symbol, score, has_kind_chain)}
        candidates: dict[int, tuple[str, float, bool]] = {}

        for cid, neighborhood in scene.neighborhoods.items():
            root_id  = neighborhood.get("root_id", cid)
            compounds = neighborhood.get("compounds", {})
            triples   = neighborhood.get("triples", {})

            root_rec = compounds.get(root_id, {})
            symbol   = root_rec.get("symbol", "")

            # Skip function words
            if symbol.lower() in self._FUNCTION_WORDS:
                continue

            # Score = count of substantive (structural + action) triples
            # weighted by their primebit richness
            root_triples = triples.get(root_id, [])
            substantive  = [
                (subj, pred, target, ttype) for subj, pred, target, ttype in root_triples
                if pred in _STRUCTURAL_PRIMES or pred in _ACTION_PRIMES
            ]
            if not substantive:
                continue

            has_kind = any(pred == "KIND" for _, pred, _, _ in substantive)
            score    = len(substantive) + (2.0 if has_kind else 0.0)

            # Boost grounded compounds
            if root_rec.get("grounded"):
                score *= 1.5

            candidates[root_id] = (symbol, score, has_kind)

        if candidates:
            best_cid = max(candidates, key=lambda c: candidates[c][1])
            return best_cid, candidates[best_cid][0]

        # Fallback: check active narratives for a named entity
        if scene.active_narratives:
            try:
                from primes.KNOW import know
                for nar_id in scene.active_narratives[:3]:
                    nar = know._narratives.get(nar_id)
                    if nar and nar.bindings:
                        binding = next(iter(nar.bindings.values()))
                        c = know.by_id(binding.compound_id)
                        if c:
                            return c.id, c.symbol
            except Exception:
                pass

        # Final fallback: first non-function known symbol
        for sym in scene.known_symbols:
            if sym.lower() not in self._FUNCTION_WORDS:
                return None, sym

        return None, scene.raw_input[:30]

    def _best_subject(self, scene: CognitiveScene) -> str:
        """Convenience wrapper — returns just the symbol string."""
        _, symbol = self._infer_subject(scene)
        return symbol

    def _store_assertion(self, scene: CognitiveScene, predicate: str, target: str) -> None:
        """Write a predicate-target assertion triple to KNOW, sourced from the utterance."""
        try:
            from primes.KNOW import know
            if not scene.utterance_id:
                return
            know.store_triple(
                source_id=scene.utterance_id,
                predicate=predicate,
                target_prime=target[:64],
                source="observed",
            )
        except Exception:
            pass


# ── Module-level singleton ────────────────────────────────────────────────────
think = THINK()
