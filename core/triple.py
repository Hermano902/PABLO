"""
Triple — atomic unit of meaning.

A triple is always:  (compound_A, PRIME, compound_B)

Two compounds and the prime relation that connects them.
All relationships in PABLO — definitions, inflections, utterances, narratives —
are expressed as triples.

See docs/TRIPLES/triple_concept.md for the concept.
See docs/TRIPLES/triple_architecture.md for the implementation contract.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Triple:
    """
    Atomic unit of meaning: (source_compound, PRIME, target_compound).

    Fields
    ------
    id           : unique ID assigned by KNOW
    source_id    : compound ID of the left-hand side
    predicate    : one of the 63 canonical prime names (e.g. "FROM", "TO", "KIND")
    target_id    : compound ID of the right-hand side (or proposition ID for nested refs)
    target_prime : prime name used as terminal target value (e.g. "BEFORE")
                   Exactly one of target_id or target_prime is set; the other is None.
    confidence   : 0.0–1.0 confidence in this triple
    source       : where the triple came from — "definition"|"utterance"|"inferred"|
                   "specialist"|"manual"|"proposition_ref"
    observation_id : Phase 1 grouping key — all triples from one utterance share this.
                     Set by DATA when storing from an observation.
                     Replaced by prop_id in Phase 2.
    created_at   : Unix timestamp
    """

    id:             int
    source_id:      int
    predicate:      str
    target_id:      Optional[int]   = None
    target_prime:   Optional[str]   = None
    confidence:     float           = 1.0
    source:         str             = ""
    observation_id: Optional[str]   = None
    created_at:     float           = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "source_id":      self.source_id,
            "predicate":      self.predicate,
            "target_id":      self.target_id,
            "target_prime":   self.target_prime,
            "confidence":     self.confidence,
            "source":         self.source,
            "observation_id": self.observation_id,
            "created_at":     self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Triple":
        return cls(
            id=d["id"],
            source_id=d["source_id"],
            predicate=d["predicate"],
            target_id=d.get("target_id"),
            target_prime=d.get("target_prime"),
            confidence=d.get("confidence", 1.0),
            source=d.get("source", ""),
            observation_id=d.get("observation_id"),
            created_at=d.get("created_at", time.time()),
        )
