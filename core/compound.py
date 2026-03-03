"""
Compound — the universal unit of meaning in PABLO.

A Compound represents what a concept universally IS — not a specific occurrence
of it.  Occurrences live in Narratives.

One external dependency: core.primebit.PrimeBit.
No imports from any prime module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import time

from core.primebit import PrimeBit


# ══════════════════════════════════════════════════════════════════════════════
# Supporting dataclasses
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Relation:
    """Predicate -> target link forming part of a compound's definition.

    The predicate is always a prime name governing the relationship.
    target_id must be a permanent ID (200+) by the time the compound is stored.

    Phase 1 bridge — will migrate to the triple store in Phase 2.
    """
    predicate:  str   # prime name: "BE", "KIND", "HAS", "CAN", "PART", etc.
    target_id:  int   # permanent compound ID this relation points to


@dataclass
class Slot:
    """Named argument slot for action/macro compounds (Phase 2).

    Defined here for schema completeness — not populated until Phase 2.
    Kept on Compound to support actionable propositions and narratives.
    """
    name:       str
    required:   bool
    prime_type: str | None  = None   # expected prime family
    filled_by:  int | None  = None   # compound ID filling this slot when instantiated


# ══════════════════════════════════════════════════════════════════════════════
# Type-to-Layer mapping
# ══════════════════════════════════════════════════════════════════════════════

TYPE_TO_LAYER: dict[str, int | None] = {
    "concept":    0,       # Layer 0 — canonical concept definition
    "utterance":  1,       # Layer 1 — aggregate of ordered concept compounds
    "intent":     2,       # Layer 2 — THINK's interpretation of an utterance
    "action":     3,       # Layer 3 — executable compound (Phase 2)
    "macro":      4,       # Layer 4 — self-created reusable compound (Phase 2)
    "logic":      None,    # layer-agnostic structural operators
    "internal":   None,    # system-use compounds
}


# ══════════════════════════════════════════════════════════════════════════════
# Compound
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Compound:
    """Universal unit of meaning.  All primes read and write Compounds.

    Thin anchor design: Compound holds identity, semantic index, and the
    execution stub (for actionable propositions/narratives). All relational
    structure, provenance history, and grounding detail lives in Narratives
    and the Triple store.

    Fields deliberately absent (moved to Narrative/Triple layer):
      candidate_interpretations — initial grounding provenance → DefinitionNarrative thread
      operation_arity           — merged into arity; was always None
      slot_names                — redundant with slots[].name; was always []
      execution_path            — Phase 2 execution lives in action Narrative
      provenance_data (dict)    — replaced by source: str for Layer 1 commit events;
                                  full provenance context lives in Narratives
      text                      — replaced by symbol
      usage_count / success_rate / query_count — belong in KNOW refinement tracking
    """

    # ── Identity ──────────────────────────────────────────────────────────
    id:                         int            # permanent (200+) or temp (negative)
    symbol:                     str            # human-language handle ("cat", "read", "NOT")

    # ── Semantic content ──────────────────────────────────────────────────
    primebit:                   PrimeBit       # fast prime index

    # ── Compound graph structure (Phase 1 bridges → triples Phase 2) ─────
    nested:                     list[int]      # child compound IDs composing this concept
    relations:                  list[Relation]  # predicate -> target links

    # ── Narrative pointer ─────────────────────────────────────────────────
    narrative_id:               int | None     # associated Narrative in KNOW
    #   concept   → DefinitionNarrative (set by KNOW on first storage)
    #   utterance → episodic Narrative (Phase 2)
    #   intent    → intent Narrative (Phase 2)

    # ── Grounding state ───────────────────────────────────────────────────
    grounded:                   bool           # True = fully resolved to primes
    version:                    int            # incremented on each definition update
    confidence:                 float          # 0.0-1.0 certainty of primebit encoding

    # ── Execution (action/macro — Phase 2+) ───────────────────────────────
    executable:                 bool
    trigger_condition:          PrimeBit | None
    arity:                      int            # argument count (logic + action compounds)
    slots:                      list[Slot]     # named argument slots (action/macro)

    # ── Source tracking ───────────────────────────────────────────────────
    source:                     str = ""       # where this compound came from
    #   utterance: "keyboard" | "gui" | "stdin" | "screen" | "file"
    #   intent:    "THINK"
    #   concept:   "" (unknown / derived)

    # ── compound_type (stored for serialisation, drives layer derivation) ─
    compound_type:              str = "concept"

    # ── Timestamp ─────────────────────────────────────────────────────────
    created_at:                 float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Validate compound_type against TYPE_TO_LAYER."""
        if self.compound_type not in TYPE_TO_LAYER:
            raise ValueError(
                f"Invalid compound_type: {self.compound_type!r}. "
                f"Must be one of {list(TYPE_TO_LAYER.keys())}"
            )

    # ── Derived properties ────────────────────────────────────────────────

    @property
    def layer(self) -> int | None:
        """Derive layer from compound_type. Never stored."""
        return TYPE_TO_LAYER.get(self.compound_type)

    # ── Construction helpers ──────────────────────────────────────────────

    @classmethod
    def concept(
        cls,
        temp_id:    int,
        symbol:     str,
        primebit:   PrimeBit,
        confidence: float = 0.0,
        grounded:   bool = False,
    ) -> Compound:
        """Create a Layer 0 concept Compound with a temp ID."""
        return cls(
            id=temp_id,
            symbol=symbol,
            primebit=primebit,
            nested=[],
            relations=[],
            narrative_id=None,
            grounded=grounded,
            version=0,
            confidence=confidence,
            executable=False,
            trigger_condition=None,
            arity=0,
            slots=[],
            source="",
            created_at=time.time(),
            compound_type="concept",
        )

    @classmethod
    def utterance(
        cls,
        temp_id:  int,
        symbol:   str,
        nested:   list[int],
        primebit: PrimeBit,
        source:   str = "",
    ) -> Compound:
        """Create a Layer 1 utterance Compound."""
        return cls(
            id=temp_id,
            symbol=symbol,
            primebit=primebit,
            nested=nested,
            relations=[],
            narrative_id=None,
            grounded=True,
            version=0,
            confidence=1.0,
            executable=False,
            trigger_condition=None,
            arity=0,
            slots=[],
            source=source,
            created_at=time.time(),
            compound_type="utterance",
        )

    @classmethod
    def intent(
        cls,
        temp_id:      int,
        symbol:       str,
        primebit:     PrimeBit,
        utterance_id: int,
    ) -> Compound:
        """Create a Layer 2 intent Compound."""
        return cls(
            id=temp_id,
            symbol=symbol,
            primebit=primebit,
            nested=[],
            relations=[Relation(predicate="FROM", target_id=utterance_id)],
            narrative_id=None,
            grounded=True,
            version=0,
            confidence=1.0,
            executable=False,
            trigger_condition=None,
            arity=0,
            slots=[],
            source="THINK",
            created_at=time.time(),
            compound_type="intent",
        )

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to dict.  PrimeBit fields become raw ints."""
        return {
            "id":               self.id,
            "symbol":           self.symbol,
            "primebit":         self.primebit.value,
            "nested":           self.nested,
            "relations":        [
                {"predicate": r.predicate, "target_id": r.target_id}
                for r in self.relations
            ],
            "narrative_id":     self.narrative_id,
            "grounded":         self.grounded,
            "version":          self.version,
            "confidence":       self.confidence,
            "executable":       self.executable,
            "trigger_condition": self.trigger_condition.value if self.trigger_condition else None,
            "arity":            self.arity,
            "slots":            [s.__dict__ for s in self.slots],
            "source":           self.source,
            "compound_type":    self.compound_type,
            "created_at":       self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Compound:
        """Reconstruct from dict.  Handles missing keys gracefully.

        Accepts both 'narrative_id' (new) and 'definition_narrative_id' (legacy)
        so that compounds saved before the refactor can still be loaded.
        """
        tc = d.get("trigger_condition")
        narrative_id = d.get("narrative_id") or d.get("definition_narrative_id")
        return cls(
            id=                 d["id"],
            symbol=             d.get("symbol", d.get("text", "")),
            primebit=           PrimeBit(d.get("primebit", d.get("primebit_value", 0))),
            nested=             d.get("nested", d.get("children", [])),
            relations=          [
                Relation(predicate=r["predicate"], target_id=r["target_id"])
                for r in d.get("relations", [])
                if isinstance(r, dict)
            ],
            narrative_id=       narrative_id,
            grounded=           d.get("grounded", False),
            version=            d.get("version", 0),
            confidence=         d.get("confidence", 0.0),
            executable=         d.get("executable", False),
            trigger_condition=  PrimeBit(tc) if tc is not None else None,
            arity=              d.get("arity", d.get("operation_arity", 0) or 0),
            slots=              [Slot(**s) for s in d.get("slots", [])],
            source=             d.get("source", ""),
            compound_type=      d.get("compound_type", "concept"),
            created_at=         d.get("created_at", time.time()),
        )

    # ── Display ───────────────────────────────────────────────────────────

    def __str__(self) -> str:
        if self.primebit.is_compound:
            prime_str = f"compound:{self.primebit.compound_id}"
        else:
            prime_str = ",".join(sorted(self.primebit.get_prime_names()))
        return (
            f"Compound(id={self.id}, symbol={self.symbol!r}, "
            f"type={self.compound_type}, primes=[{prime_str}])"
        )

    def __repr__(self) -> str:
        return str(self)
