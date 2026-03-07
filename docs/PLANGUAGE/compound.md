# Compound

---

## Concept

A Compound is the unit of crystallisation in PABLO. It is what becomes stable after the
crystallisation loop runs — a transient interpretation (a token resolution, a perceived
event, a reasoned intent) encoded in symbolic form and written to permanent storage.

Every concept PABLO recognises, every utterance it processes, every intent it forms is
represented as a Compound. The Compound is how PABLO holds a thought still long enough
to examine it, combine it with other thoughts, and build on it in future scenes.

This is precisely the role of language in the theory: writing cognitive events from RAM
to persistent storage. A Compound IS that write operation made concrete.

---

### Sense, not symbol

A Compound represents the *sense* of a symbol — not the surface form itself. The tokens
`"cat"`, `"feline"`, and `"kitty"` are different surface forms. They may all resolve to
the same Compound, because they carry the same sense in prime-space.

SYMBOL's job is to find the right Compound for a given surface form in a given context.
KNOW's job is to store and retrieve Compounds. The surface token is ephemeral; the
Compound is permanent.

---

### Two states: unresolved and resolved

A Compound moves through two states during its lifetime:

**Unresolved** — primes have been assigned (the `primebit` is populated), but the
definition graph has not been validated. Some primes may be orphaned — present in the
`primebit` but with no relation to any other prime in this Compound's definition.

**Resolved** — DATA has validated the definition graph. Every prime in the Compound
has at least one relation to another prime or to a Triple within the definition.
`resolved_primebit` equals `primebit`. No orphans. The definition is coherent.

`grounded` is True when the Compound is resolved and the prime assignment has been
confirmed across at least one scene. A grounded Compound is PABLO's stable, trusted
representation of a concept.

---

### Definition Narrative

Each Compound links to a Definition Narrative — the audit trail of how its definition
became resolved. This is not the definition itself (the `primebit` carries that), but
the history: which scenes contributed which relations, which primes were dropped and why,
how confidence evolved across refinement cycles.

The Definition Narrative is not on the hot path. SYMBOL uses the `primebit` for fast
resolution. The Definition Narrative is read by THINK for deep reasoning and by humans
for inspection. It is the crystallisation loop made visible for a single concept.

---

### Compound types

**concept** — a single token grounded to one or more primes. The atomic unit of
recognised meaning. `"cat"`, `"move"`, `"heat"`. Created by DATA from SYMBOL's
resolution, stored by KNOW.

**utterance** — an assembled sequence of concepts representing a complete input.
`"the cat moved left"`. Nested list contains ordered concept IDs. PrimeBit is the
union of all constituent concept primebits.

**intent** — THINK's crystallised understanding of a conscious scene. One per
conscious thought cycle. Records what PABLO understood, in prime-space.

**action** *(Phase 2+)* — an executable behaviour pattern with slots and a trigger
condition. The bridge between compound-space and system execution. PABLO does not
call `run_excel()` — it executes the Compound `RUN + EXCEL + PROGRAM`.

**macro** *(Phase 2+)* — a bundled action pattern promoted from repeated successful
execution. The fastest path through THINK.

---

## Architecture

### Data structure

```python
@dataclass
class Compound:
    id:                 int             # permanent ID assigned by KNOW; negative = temp
    symbol:             str             # surface form ("cat", "move left")
    primebit:           int             # 64-bit: all assigned primes (may include orphans)
    resolved_primebit:  int             # 64-bit: only primes with validated relations
    nested:             list[int]       # ordered IDs of component Compounds (utterances)
    relations:          list[Relation]  # graph edges validating the definition

    narrative_id:       int | None      # ID of this Compound's Definition Narrative
    grounded:           bool            # True when resolved + confirmed in at least one scene
    version:            int             # refinement count
    confidence:         float           # 0.0 → 1.0

    executable:         bool            # True if this Compound can be called as an action
    trigger_condition:  int | None      # PrimeBit pattern that fires this Compound (Phase 2+)
    arity:              int             # number of slots (0 = no slots)
    slots:              list[str]       # slot names for executable Compounds

    source:             str             # which prime/source created this
    created_at:         float           # unix timestamp
    compound_type:      str             # "concept"|"utterance"|"intent"|"action"|"macro"
```

### Relation

A Relation is a directed edge in the Compound's definition graph:

```python
@dataclass
class Relation:
    from_prime:     str         # source prime name
    predicate:      str         # relation type (prime name or compound symbol)
    to:             str | int   # target: prime name (str) or Compound ID (int)
```

A Compound is resolved when every prime in `primebit` appears as `from_prime` in at
least one Relation. DATA performs this check and writes `resolved_primebit` accordingly.

### ID lifecycle

Before KNOW assigns a permanent ID, a Compound carries a temporary negative ID.
`KNOW.store_batch()` replaces temp IDs with permanent ones and sweeps all nested
references. After storage, the permanent ID is stable and never changes.

### PrimeBit fast path

`primebit` enables O(1) set operations without traversing the definition graph:
- `a.primebit & b.primebit` — conceptual overlap between two Compounds
- `KNOW.by_primebit_intersection(bits)` — cued recall by prime resonance
- `PrimeBit.has(primebit, "MOVE")` — O(1) prime membership check

`resolved_primebit` is the trusted subset — used when coherence matters.
`primebit` is the full set — used for broad resonance matching.

### Refinement

A Compound is not static after creation:
- `version` increments each time the Compound is refined
- `confidence` rises as scenes confirm the prime assignment
- `relations` grow as DATA validates additional graph edges
- `resolved_primebit` expands as orphan primes gain relations
- `grounded` flips True when the definition is fully coherent and scene-confirmed

---

*See [primes.md](../../PRIMES/primes.md) for the prime vocabulary Compounds are built from.*
*See [triples.md](../TRIPLES/triples.md) for how Compounds relate to each other.*
*See [narratives.md](../NARRATIVES/narratives.md) for Instance Narratives that bind Compounds to context.*
*See [primebit.md](../../SYSTEM/primebit.md) for the encoding layer.*
*See [know.md](../../PRIMES/KNOW/know.md) for storage and retrieval.*
