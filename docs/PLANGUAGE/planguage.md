# PLanguage

*PABLO's native representational language. The medium in which crystallised thought lives.*

---

## Concept

PLanguage is the symbolic language PABLO thinks in. It is not a programming language and
not a natural language — it is a representational layer built from 63 atomic primitives,
designed to express any meaning that can be grounded in those primitives.

The four units of PLanguage form a strict hierarchy:

```
Prime → Compound → Triple → Narrative
```

Each level is built from the level below. Nothing enters a higher level without being
expressible in the levels beneath it. This is what makes all meaning in PABLO
grounded, traceable, and machine-interpretable.

---

### Prime — the alphabet

63 fixed, irreducible units of meaning. The biological floor. Every concept PABLO
can represent is ultimately a combination of these primitives.

Primes are simultaneously:
- **Executable** — a prime can do things within its domain (READ perceives, KNOW stores, THINK reasons)
- **Descriptive** — the same prime used to execute behaviour labels the meaning of Compounds

The prime set does not grow. New concepts are Compounds, not new primes.

*See [primes.md](../PRIMES/primes.md)*

---

### Compound — crystallised sense

A Compound is the stable, stored sense of a symbol. Not the surface token — the meaning.
`"cat"`, `"feline"`, and `"kitty"` are different tokens that may resolve to the same
Compound, because they carry the same sense in prime-space.

A Compound carries:
- `primebit` — all assigned primes (fast O(1) lookup)
- `resolved_primebit` — only primes validated by the definition graph (coherent subset)
- `relations` — the graph edges that make the definition internally consistent
- `grounded` — True when resolved and scene-confirmed

A Compound is **unresolved** until DATA validates that every prime in its definition
has at least one relation to another prime. Orphan primes — present but unconnected —
mean the definition is not yet coherent. Resolution is the moment of crystallisation.

*See [compound.md](COMPOUND/compound.md)*

---

### Triple — the relational fabric

A Triple links two Compounds through a typed relation:

```
(subject Compound) -[predicate]→ (object Compound)
```

The predicate is itself a prime or a Compound. Triples are nestable — a Triple can
appear as the subject or object of another Triple, enabling clause-level composition:

```
(Pablo knows)  -[BECAUSE]→  (Pablo reads)
(cat moved left)  -[BEFORE]→  (cat moved right)
```

Triples are the grammar of PLanguage. They encode:
- Syntactic relations (adjective+noun, verb+subject, aux+verb)
- Semantic relations (cause, part-of, kind-of, before, after)
- Clause-level relations (because, while, if-then)

*See [triples.md](TRIPLES/triples.md)*

---

### Narrative — particularity and context

A Compound is universal — the sense of `"cat"` valid across all contexts. A Narrative
is what makes it *this cat* — the one referenced in this relationship, at this point
in time.

A Narrative carries three things that no Triple can:

**Entity bindings** — the mapping from general Compounds to specific instances.
`cat` → `this_cat_we_discussed`. `user` → `this_user`. Without entity bindings,
PABLO has only universals — no particularity, no reference to shared context.

**Thread** — the ordered sequence of Triples that constitute the history of this
particular. Not just that a cat moved left, but that it did so in session 3, after
a specific prior exchange, in response to a specific input.

**Relational state** — the accumulated affective and relational context. Trust level,
interaction history, dominant topics, emotional register. This is what SELF reads to
compute salience.

The most important Narrative in Phase 1 is `THIS_USER` — the ongoing relational
context binding all interaction with the primary user.

*See [narratives.md](NARRATIVES/narratives.md)*

---

### Definition Narrative — the resolution audit trail

Each Compound links to a Definition Narrative — not the definition itself, but the
history of how the definition became resolved. Which scenes contributed which relations.
Which primes were dropped and why. How confidence evolved.

The Definition Narrative is not on the hot path. It is read by THINK for deep reasoning
and by humans for inspection. It makes the crystallisation loop visible for a single
concept across its entire lifetime.

*See [compound.md](COMPOUND/compound.md) — narrative_id field*

---

## The boundary between levels

| Level | Question it answers | What it cannot express |
|-------|--------------------|-----------------------|
| Prime | What are the atoms of meaning? | Any specific concept |
| Compound | What does this symbol mean? | Relations between meanings |
| Triple | How do meanings relate? | Particular instances, history |
| Narrative | What is happening *here*, *now*, *between us*? | — |

The hierarchy is strict. A Narrative is not a long Triple. A Triple is not a complex
Compound. Each level adds something the level below cannot represent.

---

## PLanguage and compound execution

In Phase 2+, PABLO does not call Python functions directly. It executes Compounds.

Instead of `run_excel()` — execute the Compound `RUN + EXCEL + PROGRAM`.
Instead of `move_left()` — execute the Compound `MOVE + LEFT`.

This means PABLO's action vocabulary is expressed in the same representational layer
as its conceptual vocabulary. PABLO can reason about its own actions using the same
tools it uses to reason about anything else. The system can inspect, refine, and
learn from its own behaviour in compound-space.

This is the crystallisation loop applied to PABLO's own cognition.

---

*See [system.md](../SYSTEM/system.md) for the theoretical foundation.*
*See [cognitive_scene.md](../SYSTEM/cognitive_scene.md) for how PLanguage units move through a scene.*
*See [primebit.md](../SYSTEM/primebit.md) for the encoding layer beneath Compounds.*
