# Propositions — Architecture & Implementation

This document specifies the implementation contract for propositions in PABLO.
The conceptual model — what a proposition is, its three categories (definition,
utterance, instance), and how propositions anchor to form narratives — lives in
proposition_concept.md. Implement propositions according to both.

---

## Phase 1 Status

**Phase 1 does not introduce a Proposition record or a proposition store in KNOW.**

In Phase 1, propositions are implicit — they are the semantic grouping that
THINK constructs mentally during a reasoning cycle, using the triple store as
raw material. Propositions become explicit named records in Phase 2.

What Phase 1 establishes:
- Triple storage (see triple_architecture.md)
- Definition propositions embedded in Definition Narratives (set of triples per compound)
- Utterance propositions: when SYMBOL outputs triples (Phase 1.5), DATA stores them as triples grouped by observation_id

What Phase 2 adds:
- Proposition data structure as a named record in KNOW
- Proposition IDs, proposition store
- Instance propositions with THIS-anchored compound IDs
- Proposition linking (CAUSE, IF, AND between propositions)

---

## PHASE 2 — Proposition Record

---

### 1. Proposition Dataclass

```python
# core/proposition.py
from dataclasses import dataclass, field
import time

@dataclass
class Proposition:
    id:              int              # globally unique, assigned by KNOW
    anchor_id:       int | None       # primary compound this proposition orbits
                                      # None for nested propositions
    triple_ids:      list[int]        # ordered list of triple IDs in this proposition
    proposition_type: str             # "definition" | "utterance" | "instance" | "nested"
    source:          str              # "specialist" | "inferred" | "definition" | "manual"
    confidence:      float = 1.0
    complete:        bool = False     # True when all required WH slots are filled
    narrative_id:    int | None = None  # If instance proposition — owning Narrative
    created_at:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "anchor_id":         self.anchor_id,
            "triple_ids":        self.triple_ids,
            "proposition_type":  self.proposition_type,
            "source":            self.source,
            "confidence":        self.confidence,
            "complete":          self.complete,
            "narrative_id":      self.narrative_id,
            "created_at":        self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Proposition":
        return cls(**d)
```

---

### 2. Proposition Store in KNOW

```python
# primes/KNOW.py — Phase 2 additions

self._propositions:       dict[int, Proposition]      = {}   # prop_id → Proposition
self._prop_index:         dict[int, list[int]]         = {}   # anchor_id → [prop_id, ...]
self._prop_lock           = threading.RLock()
self._next_prop_id:       int = 1
```

**Index:** `_prop_index` maps an anchor compound's ID to all propositions that orbit it.
Enables the activation cloud to pull all known propositions for a compound in O(1).

---

### 3. Proposition Store API

```python
def store_proposition(
    self,
    anchor_id:        int | None,
    triple_ids:       list[int],
    proposition_type: str = "utterance",
    source:           str = "specialist",
    confidence:       float = 1.0,
    narrative_id:     int | None = None,
) -> int:
    """
    Store one proposition. Assigns permanent ID. Updates prop_index.
    Returns proposition_id.
    """
    with self._prop_lock:
        p = Proposition(
            id=self._next_prop_id,
            anchor_id=anchor_id,
            triple_ids=triple_ids,
            proposition_type=proposition_type,
            source=source,
            confidence=confidence,
            narrative_id=narrative_id,
        )
        self._next_prop_id += 1
        self._propositions[p.id] = p
        if anchor_id is not None:
            self._prop_index.setdefault(anchor_id, []).append(p.id)
    return p.id

def get_proposition(self, prop_id: int) -> Proposition | None:
    with self._prop_lock:
        return self._propositions.get(prop_id)

def get_propositions(self, anchor_id: int) -> list[Proposition]:
    """Return all propositions orbiting a given anchor compound."""
    with self._prop_lock:
        ids = self._prop_index.get(anchor_id, [])
        return [self._propositions[i] for i in ids if i in self._propositions]

def get_propositions_for_narrative(self, narrative_id: int) -> list[Proposition]:
    """Return all instance propositions belonging to a narrative."""
    with self._prop_lock:
        return [p for p in self._propositions.values()
                if p.narrative_id == narrative_id]
```

---

### 4. Completeness Scoring

A proposition is complete when all WH questions answerable from its triples.
Phase 2 implements automatic completeness scoring:

```python
def score_completeness(self, prop_id: int) -> float:
    """
    Returns 0.0–1.0 completeness score.
    Checks which WH slots are filled by the proposition's triples.
    """
    prop = self.get_proposition(prop_id)
    if prop is None:
        return 0.0

    triples = [self.get_triple(tid) for tid in prop.triple_ids]
    predicates = {t.predicate for t in triples if t is not None}

    # WH slot → predicate(s)
    # Any of the predicates filling each slot counts
    wh_slots = {
        "who_agent":    {"FROM"},
        "who_patient":  {"TO"},
        "what_is":      {"BE"},
        "what_action":  {"DO", "MAKE", "MOVE", "CHANGE"},
        "when":         {"WITH"},        # WITH → BEFORE/NOW/AFTER terminal prime
        "where":        {"AT", "IN"},
    }

    filled = sum(1 for slot_preds in wh_slots.values()
                 if predicates & slot_preds)
    return filled / len(wh_slots)
```

---

### 5. Nested Proposition Reference

When a sentence contains an embedded clause, the inner clause is stored as
its own Proposition and referenced by the outer proposition via a triple.

```python
# Store inner proposition
inner_prop_id = know.store_proposition(
    anchor_id=harry_id,
    triple_ids=[put_triple_id, name_triple_id, goblet_triple_id],
    proposition_type="nested",
    source="specialist",
)

# Reference inner proposition from outer triple
# The inner proposition IS the target — stored as a triple with special target encoding
know.store_triple(
    source_id=ask_compound_id,
    predicate="WITH",
    target_id=inner_prop_id,      # target_id points to a proposition, not compound
    target_prime=None,
    confidence=0.9,
    source="utterance",
)
```

**Note:** when `target_id` references a proposition ID rather than a compound ID,
the triple's `source` field is set to `"proposition_ref"` to distinguish it from
compound references. THINK checks this when traversing triples.

---

### 6. Persistence

Propositions are saved to `storage/propositions.json` by the autosave thread.

```json
[
  {
    "id": 1,
    "anchor_id": 205,
    "triple_ids": [1, 2, 3, 4],
    "proposition_type": "utterance",
    "source": "specialist",
    "confidence": 0.92,
    "complete": true,
    "narrative_id": null,
    "created_at": 1772562097.0
  }
]
```

`next_prop_id` added to `storage/metadata.json`:

```json
{
  "next_id":        421,
  "next_def_id":    222,
  "next_nar_id":    5,
  "next_triple_id": 847,
  "next_prop_id":   63,
  "saved_at":       1772562097.0
}
```

---

### 7. Compute Tier

Propositions are Tier 2 (CPU sequential). Dict lookups and list appends only.
No bitwise operations, no GPU involvement.

---

### 8. ID Space

```
Proposition IDs:   separate counter, starts at 1
```

No overlap with compound, triple, definition, or narrative ID spaces.

---

### 9. Phase 2 Scope

```
✅ Proposition dataclass (anchor_id, triple_ids, type, confidence, complete, narrative_id)
✅ Proposition store in KNOW (_propositions dict + _prop_index by anchor_id)
✅ store_proposition() — assigns ID, updates index
✅ get_proposition() / get_propositions(anchor_id)
✅ get_propositions_for_narrative(narrative_id)
✅ Completeness scoring (WH slot coverage)
✅ Nested proposition references (triple pointing to proposition ID)
✅ Serialization to storage/propositions.json
✅ Load from disk on startup
✅ next_prop_id persisted in metadata.json

❌ Proposition linking (CAUSE, AND, IF between propositions) — Phase 2 late
❌ Auto-completion (infer missing WH slots from context) — Phase 3
❌ Cross-narrative proposition resolution — Phase 3
❌ Proposition clustering (group similar propositions) — Phase 3
```

---

## Phase 1 Bridging (Without Proposition Records)

Until Phase 2 introduces the Proposition record, Phase 1 uses `observation_id`
as the implicit proposition group key. All triples stored from one observation
share an `observation_id` tag:

```python
@dataclass
class Triple:
    ...
    observation_id: str | None = None   # Phase 1 grouping key; replaced by prop_id in Phase 2
```

To query "all triples from one observation" in Phase 1:

```python
def get_triples_by_observation(self, observation_id: str) -> list[Triple]:
    with self._tri_lock:
        return [t for t in self._triples.values()
                if t.observation_id == observation_id]
```

This is a linear scan in Phase 1 — acceptable since it is only called by THINK
once per reasoning cycle, not in the hot path.

In Phase 2, these triples are grouped into Proposition records and the linear
scan is replaced by O(1) prop_id lookup.
