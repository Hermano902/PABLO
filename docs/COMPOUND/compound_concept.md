# Compound — Concept

*The crystallised unit of thought in PABLO.*

---

## What a Compound Is

A Compound is the unit of crystallisation in PABLO. It is what becomes stable after
the crystallisation loop runs — a transient cognitive event (a token resolution, an
utterance, a reasoned intent) encoded in symbolic form and written to permanent storage.

Every concept PABLO recognises, every utterance it processes, every intent it forms
is represented as a Compound. The Compound is how PABLO holds a thought still long
enough to examine it, combine it with other thoughts, and build on it in future scenes.

This is precisely the role of language in the theory: writing cognitive events from
RAM to persistent storage. A Compound IS that write operation made concrete.

---

## Structure

```python
@dataclass
class Compound:
    id:             int         # permanent ID assigned by KNOW; temp_id before storage
    symbol:         str         # surface form ("cat", "move left", "what is heat")
    primebit:       PrimeBit    # 64-bit encoding of which primes are present
    nested:         list[int]   # ordered IDs of component Compounds (for utterances)
    relations:      list[Relation]  # typed connections to other Compounds

    narrative_id:   int | None  # ID of this Compound's Definition Narrative
    grounded:       bool        # True if a prime has been assigned with confidence
    version:        int         # refinement count
    confidence:     float       # 0.0 → 1.0 confidence in prime assignment

    executable:     bool        # True if this Compound can be called as an action
    trigger_condition: int | None  # PrimeBit pattern that fires this Compound

    arity:          int         # number of slots (0 = no slots)
    slots:          list[str]   # slot names for executable Compounds

    source:         str         # provenance — which prime/source created this
    created_at:     float       # unix timestamp
    compound_type:  str         # "concept" | "utterance" | "definition" | "action" | "macro"
```

---

## Compound Types

**concept** — a single token grounded to one or more primes. The atomic unit of
recognised meaning. `"cat"`, `"move"`, `"heat"`. Created by DATA, stored by KNOW.

**utterance** — an assembled sequence of concepts. `"the cat moved left"`. Created by
DATA, nested list contains the ordered concept IDs.

**definition** — THINK's crystallised understanding of an experience. One per conscious
thought cycle. Records what THINK understood, in prime-space.

**action** (Phase 2+) — an executable behaviour pattern. Has slots, trigger_condition,
and an execution path.

**macro** (Phase 2+) — a bundled action pattern promoted from repeated successful
execution. The fastest path through THINK.

---

## PrimeBit Encoding

Every Compound carries a PrimeBit — a 64-bit integer where each bit corresponds to one
of the 63 primes. A set bit means that prime is present in this compound's meaning.

```
PrimeBit for "move left":
  bit 32 (MOVE) = 1
  bit 23 (LEFT) = 1
  all others    = 0
  value         = 0x0000000900000000 (example)
```

PrimeBit enables O(1) set operations:
- `a.primebit & b.primebit` — conceptual overlap between two compounds
- `KNOW.by_primebit_intersection(bits)` — cued recall by resonance
- `PrimeBit.has_prime("MOVE")` — O(1) prime membership test

This is how PABLO's memory works: not full-text search, but resonance between prime
patterns. A query for {MOVE, LEFT} retrieves all compounds with those primes active.

---

## Compound Refinement

A Compound is not static after creation. It accretes meaning over time:

- `version` increments each time the Compound is refined
- `confidence` rises as more scenes confirm the prime assignment
- `relations` grow as Triples are created linking this Compound to others
- `narrative_id` links to the Definition Narrative — the story of how PABLO came to
  understand this concept, accumulated across all scenes where it appeared

This refinement is the error-correction loop applied to individual concepts: each scene
where a concept appears is another opportunity to compare the stored form against the
new context and refine the prime assignment.

---

## Temporary vs Permanent IDs

Before KNOW assigns a permanent ID, a Compound has a temporary ID (negative integer).
`KNOW.store_batch()` replaces temp IDs with permanent ones and sweeps all nested
references. After storage, the permanent ID is stable and never changes.

---

*See `docs/PRIMES/PRIMES_CONCEPT.md` for the primes that compose Compounds.*
*See `docs/PRIMEBIT/PRIMEBIT_CONCEPT.md` for the encoding layer.*
*See `docs/NARRATIVES/narratives_concept.md` for the Definition Narrative linked to each Compound.*
