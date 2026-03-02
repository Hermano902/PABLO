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
    """
    predicate:  str   # prime name: "BE", "KIND", "HAS", "CAN", "PART", etc.
    target_id:  int   # permanent compound ID this relation points to


@dataclass
class Slot:
    """Named argument slot for Layer 3-4 compounds (Phase 2).

    Defined here for schema completeness — not populated until Layer 3.
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

    Fields deliberately absent (see architecture doc):
      text         — replaced by symbol
      compound_type / layer stored — layer is derived via TYPE_TO_LAYER
      children     — replaced by nested
      provenance   — belongs in Instance Narratives
      usage_count, success_rate, query_count — belong in KNOW refinement tracking
    """

    # ── Identity ──────────────────────────────────────────────────────────
    id:                         int            # permanent (200+) or temp (negative)
    symbol:                     str            # human-language handle ("cat", "read", "NOT")

    # ── Semantic content ──────────────────────────────────────────────────
    primebit:                   PrimeBit       # fast prime index

    # ── Compound graph structure ──────────────────────────────────────────
    nested:                     list[int]      # child compound IDs composing this concept
    relations:                  list[Relation]  # predicate -> target links

    # ── Definition Narrative pointer ──────────────────────────────────────
    definition_narrative_id:    int | None     # set by KNOW on first storage

    # ── Grounding state ───────────────────────────────────────────────────
    grounded:                   bool           # True = fully resolved to primes

    # ── Refinement ────────────────────────────────────────────────────────
    version:                    int            # incremented on each definition update
    confidence:                 float          # 0.0-1.0 certainty of primebit encoding
    candidate_interpretations:  list[dict]     # alternatives considered by SYMBOL

    # ── Logic compound fields ─────────────────────────────────────────────
    operation_arity:            int | None     # for logic compounds only; None otherwise
    slot_names:                 list[str]      # for logic compounds: operand names; [] otherwise

    # ── Executability (Layer 3-4 — Phase 2) ───────────────────────────────
    executable:                 bool
    execution_path:             list[dict] | None
    trigger_condition:          PrimeBit | None
    arity:                      int
    slots:                      list[Slot]

    # ── Timestamp ─────────────────────────────────────────────────────────
    created_at:                 float

    # ── compound_type (stored for serialisation, drives layer derivation) ─
    compound_type:              str = "concept"

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
        candidate_interpretations: list[dict] | None = None,
    ) -> Compound:
        """Create a Layer 0 concept Compound with a temp ID."""
        return cls(
            id=temp_id,
            symbol=symbol,
            primebit=primebit,
            nested=[],
            relations=[],
            definition_narrative_id=None,
            grounded=grounded,
            version=0,
            confidence=confidence,
            candidate_interpretations=candidate_interpretations or [],
            operation_arity=None,
            slot_names=[],
            executable=False,
            execution_path=None,
            trigger_condition=None,
            arity=0,
            slots=[],
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
    ) -> Compound:
        """Create a Layer 1 utterance Compound."""
        return cls(
            id=temp_id,
            symbol=symbol,
            primebit=primebit,
            nested=nested,
            relations=[],
            definition_narrative_id=None,
            grounded=True,
            version=0,
            confidence=1.0,
            candidate_interpretations=[],
            operation_arity=None,
            slot_names=[],
            executable=False,
            execution_path=None,
            trigger_condition=None,
            arity=0,
            slots=[],
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
            definition_narrative_id=None,
            grounded=True,
            version=0,
            confidence=1.0,
            candidate_interpretations=[],
            operation_arity=None,
            slot_names=[],
            executable=False,
            execution_path=None,
            trigger_condition=None,
            arity=0,
            slots=[],
            created_at=time.time(),
            compound_type="intent",
        )

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to dict.  PrimeBit fields become raw ints."""
        return {
            "id":                        self.id,
            "symbol":                    self.symbol,
            "primebit":                  self.primebit.value,
            "nested":                    self.nested,
            "relations":                 [
                {"predicate": r.predicate, "target_id": r.target_id}
                for r in self.relations
            ],
            "definition_narrative_id":   self.definition_narrative_id,
            "grounded":                  self.grounded,
            "version":                   self.version,
            "confidence":                self.confidence,
            "candidate_interpretations": self.candidate_interpretations,
            "operation_arity":           self.operation_arity,
            "slot_names":                self.slot_names,
            "executable":                self.executable,
            "execution_path":            self.execution_path,
            "trigger_condition":         self.trigger_condition.value if self.trigger_condition else None,
            "arity":                     self.arity,
            "slots":                     [s.__dict__ for s in self.slots],
            "created_at":                self.created_at,
            "compound_type":             self.compound_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Compound:
        """Reconstruct from dict.  Handles missing keys gracefully."""
        tc = d.get("trigger_condition")
        return cls(
            id=                        d["id"],
            symbol=                    d.get("symbol", d.get("text", "")),
            primebit=                  PrimeBit(d.get("primebit", d.get("primebit_value", 0))),
            nested=                    d.get("nested", d.get("children", [])),
            relations=                 [
                Relation(predicate=r["predicate"], target_id=r["target_id"])
                for r in d.get("relations", [])
                if isinstance(r, dict)
            ],
            definition_narrative_id=   d.get("definition_narrative_id"),
            grounded=                  d.get("grounded", False),
            version=                   d.get("version", 0),
            confidence=                d.get("confidence", 0.0),
            candidate_interpretations= d.get("candidate_interpretations", []),
            operation_arity=           d.get("operation_arity"),
            slot_names=                d.get("slot_names", []),
            executable=                d.get("executable", False),
            execution_path=            d.get("execution_path"),
            trigger_condition=         PrimeBit(tc) if tc is not None else None,
            arity=                     d.get("arity", 0),
            slots=                     [Slot(**s) for s in d.get("slots", [])],
            created_at=                d.get("created_at", time.time()),
            compound_type=             d.get("compound_type", "concept"),
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