# Compound — Architecture & Implementation

This file is the canonical implementation reference for `core/compound.py`.
It is phase-separated: Phase 1 is the complete implementable target. Phase 2+
sections are preserved for future reference and must not be implemented until
the relevant phase begins.

See `COMPOUND_CONCEPT.md` for the conceptual contract. Implement against both.

---

## PHASE 1 — Implement Now

---

### 1. Scope & Purpose

Compound is a shared data structure — not a prime, not a cognitive component.
It is the universal unit of meaning that all primes read and write. A Compound
represents what a concept universally IS — not a specific occurrence of it.
Occurrences live in Narratives.

`core/compound.py` has one external dependency: `core.primebit.PrimeBit`.
It must have no imports from any prime module.

---

### 2. PrimeBit Contract in Compound

Compound uses `PrimeBit` as a class (defined in `core/primebit.py`), not as a
raw int. All primebit fields on a Compound are `PrimeBit` instances.

Serialisation converts `PrimeBit` to/from int at the boundary:
- `to_dict()`: call `.value` to get the raw int for storage.
- `from_dict()`: call `PrimeBit(raw_int)` to reconstruct.

No other module should store or pass raw int primebits — always wrap in `PrimeBit`.

---

### 3. Supporting Dataclasses

#### Relation

A Relation expresses how this compound connects to another compound or prime.
The predicate is always a prime name — the prime that governs the relationship.

```python
@dataclass
class Relation:
    predicate:  str   # prime name governing this link ("BE", "KIND", "HAS", "CAN",
                      # "PART", "WITH", "FEEL", "WANT", etc.)
                      # For negation: wrap with logic compound — NOT(HAS) expressed
                      # as predicate="NOT_HAS" referencing logic compound for NOT(HAS)
    target_id:  int   # permanent compound ID this relation points to
```

`target_id` must always be a permanent ID (200+) by the time a Compound is
stored in KNOW. Temp IDs must never appear in stored Relations — see Section 7.

Relations live in the Definition Narrative, not directly on the Compound core
record. The Compound holds a `definition_narrative_id` pointer. Relations are
loaded on demand via `KNOW.get_definition(compound_id)`. For Phase 1, relations
are stored directly on the Compound for simplicity — the Definition Narrative
split is a Phase 2 concern (see D1).

#### Slot (Phase 1 definition only — not used until Layer 3)

```python
@dataclass
class Slot:
    name:       str         # "agent" | "target" | "direction" | etc.
    required:   bool
    prime_type: str | None  # expected prime family ("ENTITY", "MOVE", etc.)
    filled_by:  int | None  # compound ID filling this slot when instantiated
```

Slots are defined here for schema completeness. They are not populated until
Layer 3 (Action compounds) which is Phase 2.

#### Step (Layer 3–4 only — defines one entry in execution_path)

A Step is a plain dict with a `type` discriminator field. Three valid shapes:

```python
# Call a prime directly
{"type": "prime",    "name": "KNOW"}

# Execute another compound recursively (must be executable)
{"type": "compound", "id": 347}

# Conditional branch
{"type": "branch",   "condition_id": 44,
                     "true_path":  [Step, ...],
                     "false_path": [Step, ...]}
```

`execution_path` is a `list[dict]` where each dict matches one of the above shapes.
An empty list `[]` is valid for a compound defined but not yet populated.
Steps are not validated at construction time — validation happens at execution
time in THINK.

---

### 4. Compound Class & Fields

```python
# core/compound.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import time

from core.primebit import PrimeBit

@dataclass
class Compound:
    # ── Identity ──────────────────────────────────────────────────────────────
    id:                 int           # permanent ID assigned by KNOW (200+)
                                      # negative = temp, assigned by DATA before storage
    symbol:             str           # human-language handle — the pointer, not the meaning
                                      # ("cat", "read", "fast", "NOT", "AND")

    # ── Semantic content ──────────────────────────────────────────────────────
    primebit:           PrimeBit      # fast prime index — which primes are present
                                      # used for routing and filtering; not the full definition

    # ── Compound graph structure ───────────────────────────────────────────────
    nested:             list[int]     # child compound IDs whose meanings compose this concept
                                      # empty = prime-terminal (bottom of reverse pyramid)
                                      # non-empty = load definition for full meaning
    relations:          list[Relation]# predicate → target links forming the definition
                                      # Phase 1: stored here directly
                                      # Phase 2: moved to Definition Narrative in KNOW

    # ── Definition Narrative pointer ──────────────────────────────────────────
    definition_narrative_id: int | None  # ID of this compound's Definition Narrative in KNOW
                                          # None until KNOW assigns it on first storage
                                          # load via KNOW.get_definition(compound_id)

    # ── Grounding state ───────────────────────────────────────────────────────
    grounded:           bool          # True = full resolution terminates at primes
                                      # False = placeholder, awaiting enrichment

    # ── Refinement ────────────────────────────────────────────────────────────
    version:            int           # incremented each time the definition refines
    confidence:         float         # certainty of current primebit encoding (0.0–1.0)
    candidate_interpretations: list[dict]  # alternative primebits considered by SYMBOL

    # ── Logic compound fields (logic type only) ───────────────────────────────
    operation_arity:    int | None    # for logic compounds: number of operands; None otherwise
    slot_names:         list[str]     # for logic compounds: operand slot names; [] otherwise

    # ── Executability (Layer 3–4 only — Phase 2) ──────────────────────────────
    executable:         bool              # False for Layers 0–2
    execution_path:     list[dict] | None # ordered Steps — None for Layers 0–2
    trigger_condition:  PrimeBit | None   # primebit pattern for auto-activation
    arity:              int               # number of required slots (0 for Layers 0–2)
    slots:              list[Slot]        # named argument slots

    # ── Timestamp ─────────────────────────────────────────────────────────────
    created_at:         float         # unix timestamp
```

**Fields deliberately absent:**

- `text` — replaced by `symbol`. Same data, clearer semantics.
- `compound_type` / `layer` — derived from structure, not stored. See TYPE_TO_LAYER.
- `children` — replaced by `nested`. Clearer: nested compounds compose meaning.
- `provenance` — observation context belongs in Instance Narratives, not compounds.
- `usage_count`, `success_rate`, `query_count` — belong in KNOW's refinement
  tracking sub-record. KNOW updates these automatically on every access.

#### TYPE_TO_LAYER mapping

```python
TYPE_TO_LAYER: dict[str, int | None] = {
    "concept":    0,    # Layer 0 — canonical concept definition, one per unique symbol
    "utterance":  1,    # Layer 1 — aggregate of ordered concept compounds
    "intent":     2,    # Layer 2 — THINK's interpretation of an utterance
    "action":     3,    # Layer 3 — executable compound derived by THINK
    "macro":      4,    # Layer 4 — self-created reusable compound
    "logic":      None, # layer-agnostic — structural operators
    "internal":   None, # system-use compounds
}
```

`layer` is derived from `compound_type` via `TYPE_TO_LAYER` on construction.
It is not stored — always recomputed. If `compound_type` is not in the map,
raise `ValueError` immediately on construction.

#### Valid compound_type values

```
"concept"     Layer 0 — canonical definition of a symbol's meaning.
              One per unique concept in KNOW — not one per observation.
              DATA checks KNOW first; only creates new compound if symbol unknown.

"utterance"   Layer 1 — ordered aggregate of concept compounds from one observation.

"intent"      Layer 2 — THINK's interpretation of an utterance.

"action"      Layer 3 — executable compound derived by THINK (Phase 2).

"macro"       Layer 4 — self-created reusable compound (Phase 2).

"logic"       Pre-defined structural operators (AND, OR, NOT, IF, THEN, etc.)
              Loaded from core/logic_compounds.json. IDs 100–199. Read-only.
              Used as predicate wrappers in relations (NOT wrapping HAS).

"internal"    System-use compounds not from external observations.
```

---

### 5. ID Ranges

```
0–99      Reserved for system bootstrapping
100–199   Logic compounds (fixed at startup, loaded from core/logic_compounds.json)
200+      All runtime compounds — concept, utterance, intent, action, macro, internal
          Assigned sequentially by KNOW
negative  Temp IDs assigned by DATA during batch construction (never stored)
```

Narrative IDs use a separate counter and do not share this space.

---

### 6. Construction Helpers

Convenience constructors for each layer. All set `created_at` to `time.time()`.
All assign temp IDs — permanent IDs are assigned by KNOW at storage time.

```python
@classmethod
def concept(
    cls,
    temp_id:    int,
    symbol:     str,
    primebit:   PrimeBit,
    confidence: float = 0.0,
    grounded:   bool = False,
    candidate_interpretations: list[dict] | None = None,
) -> "Compound":
    """Create a Layer 0 concept Compound with a temp ID.

    grounded=False by default — SYMBOL confirms grounding before storage.
    grounded=True only when prime assignment is certain (e.g. logic tokens).
    No provenance on the compound — observation context goes to Instance Narrative.
    """
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
    )

@classmethod
def utterance(
    cls,
    temp_id:  int,
    symbol:   str,
    nested:   list[int],
    primebit: PrimeBit,
) -> "Compound":
    """Create a Layer 1 utterance Compound.

    nested is an ordered list of concept compound IDs (temp at construction time).
    DATA resolves these to permanent IDs before handing the batch to KNOW.
    primebit is the union of all constituent concept primebits.
    relations encode structural roles — subject, verb, object, modifier.
    """
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
    )

@classmethod
def intent(
    cls,
    temp_id:      int,
    symbol:       str,
    primebit:     PrimeBit,
    utterance_id: int,
) -> "Compound":
    """Create a Layer 2 intent Compound.

    utterance_id must be a permanent ID — intents are created by THINK
    after the utterance compound is already stored in KNOW.
    """
    return cls(
        id=temp_id,
        symbol=symbol,
        primebit=primebit,
        nested=[],
        relations=[Relation(
            predicate="FROM",
            target_id=utterance_id,
        )],
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
    )
```

---

### 7. Temp ID Contract & Batch Resolution

DATA assigns temp IDs using a descending counter scoped to one observation batch:

```python
# Inside DATA
self._temp_counter: int = 0

def _next_temp_id(self) -> int:
    self._temp_counter -= 1
    return self._temp_counter  # returns -1, -2, -3, ...
```

The counter resets to 0 at the start of each observation batch.

**Within a batch, temp IDs may appear in `nested` and `relations.target_id`
of sibling compounds.** Before handing the batch to KNOW, DATA must resolve
all internal temp ID references to the correct siblings.

Resolution algorithm:

```python
def _resolve_batch(self, compounds: list[Compound]) -> list[Compound]:
    """Replace all intra-batch temp ID references with correct sibling IDs.

    After resolution, no temp ID should appear in any nested list or
    relation target_id within the batch. The compounds' own .id fields
    remain negative — KNOW replaces those during store_batch.
    """
    temp_to_compound = {c.id: c for c in compounds}

    for compound in compounds:
        compound.nested = [
            temp_to_compound[nid].id if nid < 0 and nid in temp_to_compound else nid
            for nid in compound.nested
        ]
        for relation in compound.relations:
            if relation.target_id < 0 and relation.target_id in temp_to_compound:
                relation.target_id = temp_to_compound[relation.target_id].id

    return compounds
```

**KNOW's batch store contract:**

```python
KNOW.store_batch(compounds: list[Compound]) -> dict[int, int]
# Assigns permanent IDs (200+) in batch order.
# Updates all .id fields in place.
# Updates all nested and relation target_ids from temp to permanent.
# Creates a Definition Narrative for each new concept compound and
# sets definition_narrative_id on the compound before persisting.
# Returns {temp_id: permanent_id} for caller reference.
```

KNOW handles the final temp→permanent ID swap because it is the only component
that knows permanent IDs at assignment time. KNOW also creates the Definition
Narrative for each new concept compound during store_batch.

---

### 8. Serialisation

Compounds serialise to/from dict for persistence (used by KNOW's autosave).
`PrimeBit` fields serialise as raw ints. All other fields serialise as-is.

```python
def to_dict(self) -> dict:
    return {
        "id":                          self.id,
        "symbol":                      self.symbol,
        "primebit":                    self.primebit.value,
        "nested":                      self.nested,
        "relations":                   [
            {
                "predicate": r.predicate,
                "target_id": r.target_id,
            }
            for r in self.relations
        ],
        "definition_narrative_id":     self.definition_narrative_id,
        "grounded":                    self.grounded,
        "version":                     self.version,
        "confidence":                  self.confidence,
        "candidate_interpretations":   self.candidate_interpretations,
        "operation_arity":             self.operation_arity,
        "slot_names":                  self.slot_names,
        "executable":                  self.executable,
        "execution_path":              self.execution_path,
        "trigger_condition":           self.trigger_condition.value if self.trigger_condition else None,
        "arity":                       self.arity,
        "slots":                       [s.__dict__ for s in self.slots],
        "created_at":                  self.created_at,
    }

@classmethod
def from_dict(cls, d: dict) -> "Compound":
    tc = d.get("trigger_condition")
    return cls(
        id=                          d["id"],
        symbol=                      d["symbol"],
        primebit=                    PrimeBit(d["primebit"]),
        nested=                      d.get("nested", []),
        relations=                   [
            Relation(
                predicate=  r["predicate"],
                target_id=  r["target_id"],
            )
            for r in d.get("relations", [])
        ],
        definition_narrative_id=     d.get("definition_narrative_id"),
        grounded=                    d.get("grounded", False),
        version=                     d.get("version", 0),
        confidence=                  d.get("confidence", 0.0),
        candidate_interpretations=   d.get("candidate_interpretations", []),
        operation_arity=             d.get("operation_arity"),
        slot_names=                  d.get("slot_names", []),
        executable=                  d.get("executable", False),
        execution_path=              d.get("execution_path"),
        trigger_condition=           PrimeBit(tc) if tc is not None else None,
        arity=                       d.get("arity", 0),
        slots=                       [Slot(**s) for s in d.get("slots", [])],
        created_at=                  d.get("created_at", time.time()),
    )
```

---

### 9. Identity vs Definition Contract

A Compound's **identity** is stable once stored: `id`, `symbol`, `created_at`
never change after permanent ID assignment.

A Compound's **definition** is living: `primebit`, `nested`, `relations`,
`confidence`, `version` evolve as SYMBOL enriches the concept over time.
Each update increments `version` and is recorded in the Definition Narrative thread.

Permitted post-storage mutations (via KNOW.refine_definition only):
- `primebit` update — SYMBOL enrichment
- `nested` update — new child compounds discovered
- `relations` update — new definition relations confirmed
- `grounded` flip False → True — SYMBOL confirmation, once only
- `version` increment — automatic on any definition update
- `confidence` update — SYMBOL enrichment
- `definition_narrative_id` set — KNOW sets once on first storage

No prime may modify these fields directly. All definition updates go through
`KNOW.refine_definition(compound_id, ...)` which enforces audit trail and versioning.

Phase 2: add `__setattr__` guard raising `CompoundIdentityViolationError` if
`id`, `symbol`, or `created_at` are modified after permanent ID assignment.

---

### 10. Logic Compounds

Logic Compounds occupy IDs 100–199. Defined in `core/logic_compounds.json`
and loaded by KNOW at startup. Never created by DATA or THINK at runtime.

They follow the same Compound schema and serialise identically. Excluded from
KNOW's autosave — always re-loaded from the JSON on startup.

Their `compound_type` is `"logic"` and `layer` is `None`.

Logic compounds serve two roles:
1. Structural operators for reasoning (AND, OR, NOT, IF, THEN, IMPLIES)
2. Predicate wrappers in relations — NOT(HAS) expressed as a relation whose
   predicate references the NOT logic compound wrapping the HAS prime.

---

### 11. Known Risks & Phase 2 Notes

**Definition Narrative split:**
Phase 1 stores relations directly on the Compound for simplicity. Phase 2 must
move relations into the Definition Narrative in KNOW, replacing them with only
a `definition_narrative_id` pointer. This keeps the compound core record lean
and cacheable while definitions grow arbitrarily.

**Runtime identity guard:**
Phase 1 relies on convention. Phase 2 must add a `__setattr__` guard raising
`CompoundIdentityViolationError` if identity fields are modified after storage.

---

### 12. Tests — Phase 1

**Construction helpers:**
- `Compound.concept()` produces `grounded=False` by default, `executable=False`,
  `nested=[]`, `relations=[]`, `definition_narrative_id=None`.
- `Compound.utterance()` produces `grounded=True`, `nested` in correct order,
  `primebit` is union of constituent concept primebits.
- `Compound.intent()` produces `grounded=True`, one relation with
  `predicate="FROM"` pointing to utterance_id.

**TYPE_TO_LAYER:**
- All seven compound_type values map correctly.
- Unknown `compound_type` raises `ValueError` on construction.
- `layer` is not present in `to_dict()` output — it is not stored.

**Serialisation round-trip:**
- `Compound.from_dict(c.to_dict()) == c` for Layer 0, 1, and 2 compounds.
- PrimeBit fields survive round-trip correctly (int → PrimeBit → int).
- `trigger_condition=None` and `execution_path=None` survive round-trip.
- `nested=[]`, `relations=[]`, `definition_narrative_id=None` survive round-trip.

**Field absence:**
- `to_dict()` must NOT contain: `text`, `children`, `compound_type`, `layer`,
  `provenance`, `usage_count`, `success_rate`, `query_count`.
- `from_dict()` must not raise if these keys are absent.

**Temp ID batch resolution:**
- Batch of one utterance + two concept compounds: after `_resolve_batch`,
  utterance nested list references are consistent within batch.
- After `KNOW.store_batch`, all IDs ≥ 200, all internal references permanent.
- No negative ID appears anywhere in stored compounds.

**Relation integrity:**
- Assertion raises if any relation has `target_id < 0` after `_resolve_batch`
  pointing outside the current batch.

---

## PHASE 2+ — Deferred (Do Not Implement Yet)

---

### D1. Definition Narrative Split

Move `relations` out of the Compound core record into the Definition Narrative
stored separately in KNOW. Compound holds only `definition_narrative_id`.
Relations loaded on demand via `KNOW.get_definition(compound_id)`.

Key benefit: compound core record stays ~100 bytes and always cacheable.
Definitions grow arbitrarily without bloating the hot cache.

---

### D2. Layer 3–4 Construction Helpers

```python
@classmethod
def action(cls, symbol, primebit, execution_path, trigger_condition, arity, slots) -> Compound: ...

@classmethod
def macro(cls, symbol, primebit, execution_path, trigger_condition, arity, slots) -> Compound: ...
```

Deferred until THINK is implemented.

---

### D3. Resolved Prime Mask

For compounds with nested children, the effective prime set is the union of the
compound's own primebit and all descendants' primebits recursively.

Add optional `resolved_prime_mask: int | None` field. Cache in KNOW. Invalidate
when nested or relations change. Compute lazily in background.

See PRIMEBIT_ARCHITECTURE.md Phase 2+ section D1 for full spec.

---

### D4. Runtime Identity Guard

Add `__setattr__` guard. Once `self.id >= 200`, modifying `id`, `symbol`, or
`created_at` raises `CompoundIdentityViolationError`. Definition fields remain
mutable via KNOW's refine_definition API only.

---

### D5. Slot Filling & Execution Instantiation

When THINK executes an Action or Macro compound, it binds argument compounds
to slots. The filled Compound is an instantiated copy — the original stored
Compound is never modified. Define instantiation contract when Layer 3 is
implemented.