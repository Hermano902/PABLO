# Compound — Architecture & Implementation

This file is the canonical implementation reference for `core/compound.py`.
It is phase-separated: Phase 1 is the complete implementable target. Phase 2+
sections are preserved for future reference and must not be implemented until
the relevant phase begins.

See `CONCEPT.md` for the conceptual contract. Implement against both.

---

## PHASE 1 — Implement Now

---

### 1. Scope & Purpose

Compound is a shared data structure — not a prime, not a cognitive component.
It is the universal unit of representation that all primes read and write.
No prime subclasses Compound. No prime reaches into another prime's Compound
internals — they pass Compounds as opaque outputs and receive them as opaque inputs.

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

```python
@dataclass
class Relation:
    role:       str      # "subject" | "verb" | "object" | "modifier" | "part" | "kind"
    target_id:  int      # permanent compound ID this relation points to
    primebit:   PrimeBit # which prime encodes this relation (e.g. PART, KIND, WITH)
```

`target_id` must always be a permanent ID (200+) by the time a Compound is
stored in KNOW. Temp IDs must never appear in stored Relations — see Section 7.

#### Slot (Phase 1 definition only — not used until Layer 3)

```python
@dataclass
class Slot:
    name:       str       # "agent" | "target" | "direction" | etc.
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
An empty list `[]` is valid for a compound that has been defined but not yet populated.
Steps are not validated at construction time — validation happens at execution time in THINK.

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
    text:               str           # human-readable label only; meaning lives in primebit

    # ── Layer classification ──────────────────────────────────────────────────
    compound_type:      str           # see TYPE_TO_LAYER below
    layer:              int | None    # derived from compound_type on construction

    # ── Semantic content ──────────────────────────────────────────────────────
    primebit:           PrimeBit      # 64-bit prime mask — machine-readable meaning

    # ── Structure ─────────────────────────────────────────────────────────────
    children:           list[int]     # ordered permanent IDs of child compounds (Layer 1+)
    relations:          list[Relation]# typed links to other compounds

    # ── Executability (Layer 3–4 only — see Phase 2) ──────────────────────────
    executable:         bool              # False for Layers 0–2
    execution_path:     list[dict] | None # ordered Steps — Phase 2 only; None for Layers 0–2
    trigger_condition:  PrimeBit | None   # primebit pattern for auto-activation — Phase 2
    arity:              int               # number of required slots (0 for Layers 0–2)
    slots:              list[Slot]        # named argument slots — Phase 2 only

    # ── Grounding state ───────────────────────────────────────────────────────
    grounded:           bool          # True = primebit confirmed by SYMBOL
                                      # False = placeholder, awaiting grounding

    # ── Version ───────────────────────────────────────────────────────────────
    version:            int           # incremented on meaningful update (starts at 0)

    # ── Refinement signals ────────────────────────────────────────────────────
    usage_count:        int           # times this compound has been used
    success_rate:       float         # fraction of uses with successful outcomes (0.0–1.0)
    query_count:        int           # times retrieved by KNOW
    confidence_score:   float         # SYMBOL's grounding confidence (0.0–1.0)
    candidate_interpretations: list[dict]  # alternative primebits considered during grounding

    # ── Logic compound fields (logic type only) ───────────────────────────────
    operation_arity:    int | None    # for logic compounds: number of operands; None otherwise
    slot_names:         list[str]     # for logic compounds: operand slot names; [] otherwise

    # ── Provenance ────────────────────────────────────────────────────────────
    provenance:         dict          # source, observation_id, confidence, model, etc.

    # ── Timestamp ─────────────────────────────────────────────────────────────
    created_at:         float         # unix timestamp
```

#### TYPE_TO_LAYER mapping

```python
TYPE_TO_LAYER: dict[str, int | None] = {
    "data":       0,
    "aggregate":  1,
    "definition": 2,
    "action":     3,
    "macro":      4,
    "logic":      None,    # logic compounds are layer-agnostic
    "internal":   None,
}
```

`layer` is set on construction by looking up `compound_type` in `TYPE_TO_LAYER`.
If `compound_type` is not in the map, raise `ValueError` immediately.

#### Valid compound_type values

```
"data"        Layer 0 — token compound, one per input token
"aggregate"   Layer 1 — utterance compound, groups ordered tokens
"definition"  Layer 2 — intent compound, THINK's interpretation
"action"      Layer 3 — executable compound, derived by THINK (Phase 2)
"macro"       Layer 4 — self-created reusable compound (Phase 2)
"logic"       Logic operators, loaded from core/logic_compounds.json at startup
"internal"    System-use compounds not from external observations
```

---

### 5. ID Ranges

```
0–99      Reserved for system bootstrapping
100–199   Logic compounds (fixed at startup, loaded from core/logic_compounds.json)
200+      All runtime compounds — data, aggregate, definition, action, macro, internal
          Assigned sequentially by KNOW
negative  Temp IDs assigned by DATA during batch construction (never stored)
```

---

### 6. Construction Helpers

Convenience constructors for each layer. All set `created_at` to `time.time()`
and `layer` from `TYPE_TO_LAYER`. All assign temp IDs — permanent IDs are
assigned by KNOW at storage time.

```python
@classmethod
def token(
    cls,
    temp_id:    int,
    text:       str,
    primebit:   PrimeBit,
    provenance: dict,
    grounded:   bool = False,
) -> "Compound":
    """Create a Layer 0 token Compound with a temp ID.

    grounded=False by default — SYMBOL confirms grounding before storage.
    grounded=True only when the prime assignment is certain (e.g. logic tokens).
    """
    return cls(
        id=temp_id,
        text=text,
        compound_type="data",
        layer=0,
        primebit=primebit,
        children=[],
        relations=[],
        executable=False,
        execution_path=None,
        trigger_condition=None,
        arity=0,
        slots=[],
        grounded=grounded,
        version=0,
        usage_count=0,
        success_rate=0.0,
        query_count=0,
        confidence_score=provenance.get("confidence", 0.0),
        candidate_interpretations=[],
        operation_arity=None,
        slot_names=[],
        provenance=provenance,
        created_at=time.time(),
    )

@classmethod
def utterance(
    cls,
    temp_id:    int,
    text:       str,
    children:   list[int],
    primebit:   PrimeBit,
    provenance: dict,
) -> "Compound":
    """Create a Layer 1 utterance Compound.

    children is an ordered list of temp IDs at construction time.
    DATA resolves these to permanent IDs before handing the batch to KNOW.
    primebit is the union of all constituent token primebits.
    """
    return cls(
        id=temp_id,
        text=text,
        compound_type="aggregate",
        layer=1,
        primebit=primebit,
        children=children,
        relations=[],
        executable=False,
        execution_path=None,
        trigger_condition=None,
        arity=0,
        slots=[],
        grounded=True,
        version=0,
        usage_count=0,
        success_rate=0.0,
        query_count=0,
        confidence_score=1.0,
        candidate_interpretations=[],
        operation_arity=None,
        slot_names=[],
        provenance=provenance,
        created_at=time.time(),
    )

@classmethod
def intent(
    cls,
    temp_id:      int,
    text:         str,
    primebit:     PrimeBit,
    utterance_id: int,
    provenance:   dict,
) -> "Compound":
    """Create a Layer 2 intent Compound.

    utterance_id must be a permanent ID — intents are created by THINK
    after the utterance compound is already stored in KNOW.
    """
    return cls(
        id=temp_id,
        text=text,
        compound_type="definition",
        layer=2,
        primebit=primebit,
        children=[],
        relations=[Relation(
            role="source",
            target_id=utterance_id,
            primebit=PrimeBit.from_prime_names({"FROM"}),
        )],
        executable=False,
        execution_path=None,
        trigger_condition=None,
        arity=0,
        slots=[],
        grounded=True,
        version=0,
        usage_count=0,
        success_rate=0.0,
        query_count=0,
        confidence_score=1.0,
        candidate_interpretations=[],
        operation_arity=None,
        slot_names=[],
        provenance=provenance,
        created_at=time.time(),
    )
```

---

### 7. Temp ID Contract & Batch Resolution

DATA assigns temp IDs using a descending counter scoped to one observation:

```python
# Inside DATA
self._temp_counter: int = 0

def _next_temp_id(self) -> int:
    self._temp_counter -= 1
    return self._temp_counter  # returns -1, -2, -3, ...
```

The counter resets to 0 at the start of each observation batch.

**Within a batch, temp IDs may appear in `children` and `relations.target_id`
of sibling compounds.** Before handing the batch to KNOW, DATA must resolve
all internal temp ID references to the correct siblings.

Resolution algorithm:

```python
def _resolve_batch(self, compounds: list[Compound]) -> list[Compound]:
    """Replace all intra-batch temp ID references with correct positions.

    After resolution, no temp ID should appear in any children list or
    relation target_id within the batch. The compounds' own .id fields
    remain negative — KNOW replaces those.
    """
    temp_to_index = {c.id: i for c in compounds for i in [compounds.index(c)]}

    for compound in compounds:
        compound.children = [
            compounds[temp_to_index[cid]].id if cid < 0 else cid
            for cid in compound.children
        ]
        for relation in compound.relations:
            if relation.target_id < 0:
                relation.target_id = compounds[temp_to_index[relation.target_id]].id

    return compounds
```

Note: after `_resolve_batch`, internal references still point to negative temp IDs
(the siblings' own `.id` fields are still negative). KNOW receives the batch,
assigns permanent IDs sequentially, and returns a `{temp_id: permanent_id}` map.
DATA uses this map to do a final pass if needed, but since DATA discards the batch
after storage, the map is primarily for logging/debugging in Phase 1.

**KNOW's batch store contract:**

```python
KNOW.store_batch(compounds: list[Compound]) -> dict[int, int]
# Assigns permanent IDs (200+) in batch order.
# Updates all .id fields in place.
# Returns {temp_id: permanent_id} for the caller's reference.
# All children and relation target_ids pointing to temp IDs in the batch
# are also updated to permanent IDs before storage.
```

KNOW handles the final temp→permanent ID swap for all fields because it is the
only component that knows the permanent IDs at assignment time. DATA's
`_resolve_batch` ensures all intra-batch references are structurally consistent
before KNOW touches them — KNOW only needs to do a single sweep replacing
negative IDs with their assigned permanent counterparts.

---

### 8. Serialisation

Compounds serialise to/from dict for persistence (used by KNOW's autosave).
`PrimeBit` fields serialise as raw ints. All other fields serialise as-is.

```python
def to_dict(self) -> dict:
    return {
        "id":                          self.id,
        "text":                        self.text,
        "compound_type":               self.compound_type,
        "layer":                       self.layer,
        "primebit":                    self.primebit.value,
        "children":                    self.children,
        "relations":                   [
            {
                "role":      r.role,
                "target_id": r.target_id,
                "primebit":  r.primebit.value,
            }
            for r in self.relations
        ],
        "executable":                  self.executable,
        "execution_path":              self.execution_path,
        "trigger_condition":           self.trigger_condition.value if self.trigger_condition else None,
        "arity":                       self.arity,
        "slots":                       [s.__dict__ for s in self.slots],
        "grounded":                    self.grounded,
        "version":                     self.version,
        "usage_count":                 self.usage_count,
        "success_rate":                self.success_rate,
        "query_count":                 self.query_count,
        "confidence_score":            self.confidence_score,
        "candidate_interpretations":   self.candidate_interpretations,
        "operation_arity":             self.operation_arity,
        "slot_names":                  self.slot_names,
        "provenance":                  self.provenance,
        "created_at":                  self.created_at,
    }

@classmethod
def from_dict(cls, d: dict) -> "Compound":
    tc = d.get("trigger_condition")
    return cls(
        id=                          d["id"],
        text=                        d["text"],
        compound_type=               d["compound_type"],
        layer=                       d.get("layer", TYPE_TO_LAYER.get(d["compound_type"])),
        primebit=                    PrimeBit(d["primebit"]),
        children=                    d.get("children", []),
        relations=                   [
            Relation(
                role=      r["role"],
                target_id= r["target_id"],
                primebit=  PrimeBit(r["primebit"]),
            )
            for r in d.get("relations", [])
        ],
        executable=                  d.get("executable", False),
        execution_path=              d.get("execution_path"),
        trigger_condition=           PrimeBit(tc) if tc is not None else None,
        arity=                       d.get("arity", 0),
        slots=                       [Slot(**s) for s in d.get("slots", [])],
        grounded=                    d.get("grounded", False),
        version=                     d.get("version", 0),
        usage_count=                 d.get("usage_count", 0),
        success_rate=                d.get("success_rate", 0.0),
        query_count=                 d.get("query_count", 0),
        confidence_score=            d.get("confidence_score", 0.0),
        candidate_interpretations=   d.get("candidate_interpretations", []),
        operation_arity=             d.get("operation_arity"),
        slot_names=                  d.get("slot_names", []),
        provenance=                  d.get("provenance", {}),
        created_at=                  d.get("created_at", time.time()),
    )
```

---

### 9. Immutability Contract

Once a Compound has a permanent ID (≥ 200), it is treated as immutable.
No prime may modify `primebit`, `text`, or `compound_type` after storage.

The only permitted post-storage mutation is the temp→permanent ID swap
performed by KNOW during `store_batch` (Section 7).

If a concept evolves, a new Compound is created. The old one persists unchanged.

Phase 1: immutability is enforced by convention, not by runtime guard.
Phase 2: add a `__setattr__` guard that raises once a permanent ID is assigned.

---

### 10. Logic Compounds

Logic Compounds occupy IDs 100–199. They are defined in `core/logic_compounds.json`
and loaded by KNOW at startup. They are never created by DATA or THINK at runtime.

They follow the same Compound schema and serialise identically. They are excluded
from KNOW's autosave — always re-loaded from the JSON on startup.

Their `compound_type` is `"logic"` and `layer` is `None`.

---

### 11. Known Risks & Phase 2 Notes

**Runtime immutability:**
Phase 1 relies on convention. Phase 2 must add a `__setattr__` guard on
Compound that raises `ImmutableCompoundError` once `id >= 200`.

---

### 12. Tests — Phase 1

**Construction helpers:**
- `Compound.token()` produces `compound_type="data"`, `layer=0`, `executable=False`,
  `grounded=False` by default.
- `Compound.utterance()` produces `compound_type="aggregate"`, `layer=1`,
  `children` in correct order.
- `Compound.intent()` produces `compound_type="definition"`, `layer=2`,
  relation pointing to utterance_id with role `"source"`.

**TYPE_TO_LAYER:**
- All seven compound_type values map correctly.
- Unknown `compound_type` raises `ValueError` on construction.

**Serialisation round-trip:**
- `Compound.from_dict(c.to_dict()) == c` for Layer 0, 1, and 2 compounds.
- PrimeBit fields survive round-trip correctly (int → PrimeBit → int).
- `trigger_condition=None` serialises as `None` and deserialises as `None`.
- `execution_path=None` serialises as `None`; `execution_path=[]` serialises as `[]`.
- All refinement fields (`version`, `usage_count`, `success_rate`, `query_count`,
  `confidence_score`, `candidate_interpretations`) survive round-trip.
- `operation_arity=None` and `slot_names=[]` survive round-trip for non-logic compounds.

**New field defaults:**
- All construction helpers produce `version=0`, `usage_count=0`, `success_rate=0.0`,
  `query_count=0`, `candidate_interpretations=[]`, `operation_arity=None`, `slot_names=[]`.
- `confidence_score` on token compounds is read from `provenance.get("confidence", 0.0)`.
- `confidence_score` on utterance and intent compounds defaults to `1.0`.

**Temp ID batch resolution:**
- A batch of one utterance + two tokens: after `_resolve_batch`, utterance
  children list contains the token temp IDs (consistent within batch).
- After `KNOW.store_batch`, all IDs are ≥ 200 and all internal references
  are updated to permanent IDs.
- No temp ID (negative value) appears anywhere in stored compounds.

**Relation integrity:**
- Relations with `target_id < 0` after `_resolve_batch` indicate a bug —
  add an assertion that raises if any relation still has a temp target_id
  pointing outside the current batch.

---

## PHASE 2+ — Deferred (Do Not Implement Yet)

---

### D1. Runtime Immutability Enforcement

Add `__setattr__` guard on Compound. Once `self.id >= 200`, any attempt to
set `primebit`, `text`, or `compound_type` raises `ImmutableCompoundError`.
Permitted mutations after permanent ID assignment: none in normal operation.

---

### D2. Layer 3–4 Construction Helpers

```python
@classmethod
def action(cls, text, primebit, execution_path, trigger_condition, arity, slots) -> Compound: ...

@classmethod
def macro(cls, text, primebit, execution_path, trigger_condition, arity, slots) -> Compound: ...
```

These are deferred until THINK is implemented (Phase 6 in the roadmap).

---

### D3. resolved_prime_mask

For compounds with children, the effective prime set is the union of the
compound's own primebit and all descendants' primebits recursively.

Future: add optional `resolved_prime_mask: int | None` field to Compound.
Cache in KNOW metadata. Invalidate when children change. Compute lazily
in background. Presence signalled via `HAS_RESOLVED_MASK` in `rel_flags`.

See PRIMEBIT_ARCHITECTURE.md Phase 2+ section D1 for full spec.

---

### D5. Partitioned Storage API

For large-scale storage, split Compound data into three partitions:
- `main` — identity, primebit, type, layer, rel_flags (cheap, always loaded)
- `relations` — children and relation entries (moderate cost, load on demand)
- `context` — provenance, usage signals, large blobs (cold path)

API: `get_compound_main(id)`, `get_compound_relations(id)`,
`get_compound_context(id)`. Defined in KNOW's architecture, not here.

---

### D6. Slot Filling & Execution Instantiation

When THINK executes an Action or Macro compound, it binds argument compounds
to slots. The filled Compound is an instantiated copy — the original stored
Compound is never modified. Define the instantiation contract and copy
semantics when Layer 3 is implemented.