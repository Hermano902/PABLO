Compound – Architecture

This document describes how Compounds are implemented. The conceptual contract lives in CONCEPT.md;
implement Compounds according to both.


1. Class Location

The Compound class lives in core/compound.py. It is not a prime — it is a shared data
structure used by all primes. No prime subclasses Compound.

```python
# core/compound.py
from core.primebit import PrimeBit

class Compound:
    ...
```


2. Fields

All fields and their types:

```python
@dataclass
class Compound:
    # Identity
    id:              int            # permanent ID assigned by KNOW; negative = temp (from DATA)
    text:            str            # human-readable label; semantic content lives in primebit

    # Layer classification
    compound_type:   str            # "data" | "aggregate" | "definition" | "action" | "macro" | "logic" | "internal"
    layer:           int            # 0–4 (derived from compound_type; set on construction)

    # Semantic content
    primebit:        PrimeBit       # 64-bit prime mask — the machine-readable meaning

    # See also: PrimeBit operational details (resolved masks, rel_flags, approx-masks):
    # [docs/PRIMEBIT/PRIMEBIT_ARCHITECTURE.md](docs/PRIMEBIT/PRIMEBIT_ARCHITECTURE.md)

    # Structure
    children:        list[int]      # IDs of Compounds this one aggregates (Layer 1+)
    relations:       list[Relation] # typed links to other Compounds (subject/verb/object/modifier)

    # Executability (Layer 3–4 only)
    executable:      bool           # False for Layers 0–2; True for Layers 3–4
    execution_path:  str | None     # dotted path to callable ("primes.DO.do.move_left")
    trigger_condition: PrimeBit | None  # primebit pattern that activates this compound
    arity:           int            # number of required slots (0 = no slots)
    slots:           list[Slot]     # named argument slots for execution

    # Grounding state
    grounded:        bool           # True = primebit is confirmed; False = placeholder

    # Provenance
    provenance:      dict           # source, observation_id, model, confidence, etc.

    # Timestamps
    created_at:      float          # unix timestamp
```

`layer` is derived automatically from `compound_type` on construction:

```python
TYPE_TO_LAYER = {
    "data":       0,
    "aggregate":  1,
    "definition": 2,
    "action":     3,
    "macro":      4,
    "logic":      None,    # logic compounds span all layers conceptually
    "internal":   None,
}
```


3. Relation

```python
@dataclass
class Relation:
    role:        str   # "subject" | "verb" | "object" | "modifier" | "part" | "kind"
    target_id:   int   # ID of the Compound this relation points to
    primebit:    PrimeBit   # which prime encodes this relation (e.g. PART, KIND, WITH)
```


4. Slot (Layer 3–4 only)

```python
@dataclass
class Slot:
    name:         str           # "agent" | "target" | "direction" | etc.
    required:     bool
    prime_type:   str | None    # expected prime family for this slot ("ENTITY", "MOVE", etc.)
    filled_by:    int | None    # compound ID filling this slot in an instantiated execution
```


5. Construction Helpers

Convenience constructors for each layer, used by DATA and THINK:

```python
@classmethod
def token(cls, text: str, primebit: PrimeBit, provenance: dict,
          grounded: bool = True) -> "Compound":
    """Create a Layer 0 token Compound with a temporary negative ID."""
    ...

@classmethod
def utterance(cls, text: str, children: list[int], primebit: PrimeBit,
              provenance: dict) -> "Compound":
    """Create a Layer 1 utterance Compound with ordered children."""
    ...

@classmethod
def intent(cls, text: str, primebit: PrimeBit, utterance_id: int,
           provenance: dict) -> "Compound":
    """Create a Layer 2 intent Compound."""
    ...

@classmethod
def action(cls, text: str, primebit: PrimeBit, execution_path: str,
           trigger_condition: PrimeBit, arity: int, slots: list[Slot]) -> "Compound":
    """Create a Layer 3 action Compound."""
    ...

@classmethod
def macro(cls, text: str, primebit: PrimeBit, execution_path: str,
          trigger_condition: PrimeBit, arity: int, slots: list[Slot]) -> "Compound":
    """Create a Layer 4 macro Compound."""
    ...
```


6. Serialisation

Compounds are serialised to/from dict for persistence (used by KNOW's autosave):

```python
def to_dict(self) -> dict:
    return {
        "id":               self.id,
        "text":             self.text,
        "compound_type":    self.compound_type,
        "layer":            self.layer,
        "primebit":         self.primebit.to_int(),   # 64-bit int
        "children":         self.children,
        "relations":        [r.__dict__ for r in self.relations],
        "executable":       self.executable,
        "execution_path":   self.execution_path,
        "trigger_condition": self.trigger_condition.to_int() if self.trigger_condition else None,
        "arity":            self.arity,
        "slots":            [s.__dict__ for s in self.slots],
        "grounded":         self.grounded,
        "provenance":       self.provenance,
        "created_at":       self.created_at,
    }

@classmethod
def from_dict(cls, d: dict) -> "Compound":
    c = cls.__new__(cls)
    c.id             = d["id"]
    c.text           = d["text"]
    c.compound_type  = d["compound_type"]
    c.layer          = d.get("layer", TYPE_TO_LAYER.get(d["compound_type"]))
    c.primebit       = PrimeBit.from_int(d["primebit"])
    c.children       = d.get("children", [])
    c.relations      = [Relation(**r) for r in d.get("relations", [])]
    c.executable     = d.get("executable", False)
    c.execution_path = d.get("execution_path")
    tc = d.get("trigger_condition")
    c.trigger_condition = PrimeBit.from_int(tc) if tc is not None else None
    c.arity          = d.get("arity", 0)
    c.slots          = [Slot(**s) for s in d.get("slots", [])]
    c.grounded       = d.get("grounded", True)
    c.provenance     = d.get("provenance", {})
    c.created_at     = d.get("created_at", 0.0)
    return c
```


7. Immutability Contract

Once a Compound is stored in KNOW (i.e. has a positive permanent ID), it is treated as
immutable. No prime modifies a stored Compound's primebit, text, or type fields.

The only permitted post-storage update is ID replacement: DATA creates Compounds with
negative temp IDs; KNOW replaces the ID with a permanent one before storage. After that,
the Compound is frozen.

If a concept evolves, a new Compound is created. The old one persists unchanged.


8. Logic Compounds

Logic Compounds (IDs 100–199) are a special subset defined in core/logic_compounds.json.
They are loaded by KNOW at startup and are never created by DATA or THINK at runtime.
Their compound_type is "logic" and their primebit encodes the corresponding logic prime
(e.g. AND Compound → CAUSE prime; NOT Compound → NONE prime).

Logic Compounds follow the same Compound schema and serialise identically. They are
excluded from KNOW's autosave (they are always re-loaded from the JSON).


9. Phase 1 Scope

  ✅ Full field set (all layers)
  ✅ TYPE_TO_LAYER derivation
  ✅ Relation and Slot dataclasses
  ✅ Layer 0–2 construction helpers (token, utterance, intent)
  ✅ to_dict / from_dict serialisation
  ✅ Immutability contract (documented; not enforced by runtime in Phase 1)
  ❌ Layer 3–4 construction helpers (action, macro) — Phase 2
  ❌ Runtime immutability enforcement (Phase 2 — __setattr__ guard after ID assigned)
  ❌ Slot filling / execution instantiation (Phase 2)


10. Resolved prime mask, update patterns, and operational guidance

Resolved prime mask (cached summary)
- Field: `resolved_prime_mask` (optional int) — a cached 64-bit mask representing the union
    of this Compound's `primebit` and the `resolved_prime_mask` of any structural children (recursively).
- Purpose: allow cheap header-only membership tests (bitwise AND) without loading full relations.
- Presence hint: encoded in PrimeBit `rel_flags` as `HAS_RESOLVED_MASK` (see
    [docs/PRIMEBIT/PRIMEBIT_ARCHITECTURE.md](docs/PRIMEBIT/PRIMEBIT_ARCHITECTURE.md)).
- Semantics: readers may treat `resolved_prime_mask` as authoritative when present. If absent,
    callers may request lazy compute or treat the mask as unknown and schedule background enrichment.

API contracts (header vs relations)
- `get_compound_main(id: int) -> dict`
    - Returns the header/main partition for `id` with fields: `id`, `text`, `compound_type`,
        `layer`, `primebit` (int), `rel_flags` (int), and optionally `resolved_prime_mask` (int).
    - Cost: cheap, single-record read.

- `get_compound_relations(id: int, roles: list[str]|None = None, page: int|None = None) -> list[Relation]`
    - Returns structural relations/children. Support pagination for large relation lists.
    - Cost: moderate; callers should request only when structure is required.

- `get_compound_context(id: int) -> dict`
    - Returns provenance, usage signals, and large blobs. Cold-path; restricted access.

Atomic update pattern & invalidation
- Recommended pattern when modifying structure: update the relations partition and either (a)
    recompute and write `resolved_prime_mask` into the main header in the same transaction, or (b)
    mark the header stale and set a `NEEDS_ENRICHMENT` flag and enqueue a background recompute job.
- Helper APIs to document/implement:
    - `update_relations_atomic(id: int, new_relations: list[Relation], expected_version: int|None) -> bool`
    - `invalidate_resolved_mask(id: int) -> None` (marks stale and enqueues recompute)
    - `enqueue_compound_recompute(id: int, priority: int = 0) -> None`

Immutability enforcement (Phase 2 plan)
- Runtime guard: after KNOW assigns a positive permanent ID, enforce immutability by preventing
    changes to `primebit`, `text`, and `compound_type` via a `__setattr__` guard or a freeze API.
- Temp→perm ID flow: DATA creates Compounds with negative temp IDs; KNOW replaces the ID and
    returns the canonical stored object. Document the exact swap/update API and race conditions.

Caching, metrics and operator checklist
- Cache: recommend LRU + TTL cache for `get_compound_main` headers (defaults: TTL 5m, size tuned to
    node memory). Cache both `resolved_prime_mask` and `rel_flags`.
- Metrics to expose: `compound_header_hits`, `resolved_mask_cache_hits`, `relation_update_latency`,
    `enrichment_backlog`, `compound_recompute_duration`.
- Operator checklist for relation edits:
    1. Call `update_relations_atomic` or `invalidate_resolved_mask`.
    2. Enqueue background recompute if needed (`enqueue_compound_recompute`).
    3. Emit an audit log entry with user/agent, compound id, and change summary.
    4. Monitor `enrichment_backlog` and `resolved_mask_cache_hits` for anomalies.

Cycle handling & reconciliation
- Compute `resolved_prime_mask` iteratively when possible. Detect cycles by tracking visited nodes.
- On cycles, break back-edges deterministically (e.g., ignore back-edge contribution to unions) and
    emit an audit event for manual reconciliation. Periodic full-reconciliation jobs should correct
    any drift introduced by cycle-breaking heuristics.

Acceptance criteria for 30% refinement
- `docs/COMPOUND/ARCHITECTURE.md` documents `resolved_prime_mask` semantics, header/relations/context
    APIs, atomic update pattern, immutability roadmap, caching/metrics guidance, and an operator checklist.

