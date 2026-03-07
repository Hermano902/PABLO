# Triples

---

## Concept

A Triple is the atomic unit of relation in PLanguage. It expresses one directed
relationship between two Compounds, mediated by a prime predicate:

```
(Compound_A) -[PRIME]→ (Compound_B)
```

Triples are the grammar of PLanguage. Where Compounds crystallise sense (what something
means), Triples crystallise relation (how meanings connect). Every syntactic and semantic
relationship that matters — subject-action, cause-effect, part-whole, temporal sequence
— is expressed as a Triple over Compounds.

The same Triple structure appears at every level of the system. Compound definitions are
Triples. Utterance propositions are Triples. Narrative threads are sequences of Triples.
No special machinery at any level.

---

### The predicate is always a prime

Any of the 63 primes can act as a relation predicate. The prime's meaning determines
the nature of the relationship:

| Family | Primes |
|--------|--------|
| Structural | KIND, PART, BE, HAVE, WITH, FROM, TO, AT, IN |
| Action | DO, MAKE, MOVE, CHANGE, USE, SAY, WRITE, OPEN |
| Causal | CAUSE, BECAUSE |
| Temporal | BEFORE, AFTER, NOW, LAST, TIME |
| Spatial | HERE, NEAR, FAR, UP, DOWN, LEFT, RIGHT, BETWEEN, SIDE, AT |
| Modal | CAN, WANT, NEED |
| Evaluative | GOOD, BAD, MORE, LESS |
| Perceptual | SEE, HEAR, TOUCH, FEEL |
| Cognitive | THINK, KNOW, SYMBOL |

Logic Compounds (IF, AND, OR, NOT, XOR, etc.) can also act as predicates — they operate
on Triples rather than on Compounds, enabling proposition-level relations.

---

### Triples are nestable

The object of a Triple can itself be a Triple. This enables clause-level composition:

```
(Pablo knows)  -[BECAUSE]→  (Pablo reads)
(proposition_0)  -[CAUSE]→  (proposition_1)
```

This is not a special case. It is the same Triple structure applied recursively.
Complex sentences are nested Triple structures, not new syntactic machinery.

---

### WH questions map to prime predicates

Every WH question corresponds to a prime predicate in the Triple:

| Question | Prime | Example |
|----------|-------|---------|
| WHO acts | FROM | `("bite", FROM, "dog")` |
| WHO receives | TO | `("bite", TO, "man")` |
| WHAT is it | BE | `("this", BE, "doctor")` |
| WHAT kind | KIND | `("running", KIND, "run")` |
| WHAT part | PART | `("finger", PART, "hand")` |
| WHEN | WITH | `("bite", WITH, BEFORE)` |
| WHERE | AT | `("run", AT, "hospital")` |
| WHY (cause) | CAUSE | `("run", CAUSE, "fear")` |
| WHY (purpose) | WANT | `("build", WANT, "shelter")` |
| HOW (manner) | WITH | `("run", WITH, "quickly")` |
| HOW (instrument) | USE | `("run", USE, "legs")` |

If the prime set cannot express a relationship, that is a signal the relationship
should be decomposed into multiple Triples.

---

### Universals vs instances: the THIS anchor

A Triple without instance anchoring is a universal truth — a definition:

```
("doctor",  DO,  "run")    — doctors run in general (universal)
```

The `THIS` prime converts a general Compound reference into a specific instance:

```
("THIS",  BE,   "doctor")   — THIS specific entity
("THIS",  DO,   "run")      — THIS entity ran
("THIS",  AT,   "hospital") — here
("THIS",  WITH, BEFORE)     — then (instance)
```

`THIS` is what distinguishes "doctors run" from "the doctor ran." It is how Triples
become Narrative events — by anchoring to a specific entity in a specific context.

---

## Architecture

### Data structure

```python
@dataclass
class Triple:
    id:         int             # permanent ID assigned by KNOW
    source_id:  int | str       # Compound ID or prime name (subject)
    predicate:  str             # prime name or logic compound symbol
    target_id:  int | str       # Compound ID or prime name (object)
    scene_id:   str | None      # scene this Triple was created in
    created_at: float           # unix timestamp
```

`source_id` and `target_id` may be:
- A permanent Compound ID (integer)
- A prime name (string) — when the endpoint is a terminal prime value
- A nested Triple ID (integer, same ID space as Compounds) — for proposition-level relations

### Proposition

A proposition is a coherent set of Triples that together express one complete thought.
The Triples in a proposition share at least one Compound (typically the core concept).

Example — "the exhausted doctor ran":

```
("this",    BE,    "doctor")       ← what entity
("this",    HAS,   "exhaustion")   ← state
("this",    DO,    "run")          ← action
("run",     WITH,  BEFORE)         ← when
```

A proposition is complete when all WH questions about the event are answerable from
its Triples. Missing Triples leave questions unanswered — the proposition is partial.

### Compound definitions as propositions

A Compound's definition IS a proposition. The Triples that define what `run` universally
means in prime-space:

```
("run",  KIND,  "move")       run is a kind of movement
("run",  MORE,  "walk")       more than walking
("run",  USE,   "legs")       using legs
("run",  FROM,  ENTITY)       done by an entity
```

These are stored as Triples in KNOW, linked to the Compound via `narrative_id`.
The same Triple format serves both definition and utterance — no special cases.

### Voice and grammar are irrelevant

```
English: "The man was bitten by the dog"    (passive)
English: "The dog bit the man"              (active)
PLanguage: identical Triples in both cases:
    ("bite", FROM, "dog")
    ("bite", TO,   "man")
    ("bite", WITH, BEFORE)
```

Voice, aspect, and grammatical category do not exist in prime-space. Only relationships
exist. SYMBOL extracts prime-space Triples and discards grammatical machinery.

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | Triple data structure and KNOW storage |
| 1 | Compound definition propositions |
| 1 | Utterance propositions (Triples extracted from scene) |
| 1 | THIS anchoring for instance propositions |
| 1 | WH question mapping |
| 2 | Proposition linking (CAUSE, AND between propositions) |
| 2 | Nested narrative cross-references |
| 2 | Logic compound predicates (IF, AND, NOT as Triple predicates) |

---

*See [compound.md](../COMPOUND/compound.md) for Compound definitions expressed as Triple propositions.*
*See [narratives.md](../NARRATIVES/narratives.md) for Narrative threads built from Triples.*
*See [primes.md](../../PRIMES/primes.md) for the prime predicate vocabulary.*
*See [know.md](../../PRIMES/KNOW/know.md) for Triple storage and retrieval.*
