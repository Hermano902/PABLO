# Primes — Concept

*The biological floor of PABLO's intelligence.*

---

## What a Prime Is

A prime is an irreducible unit of meaning. It cannot be decomposed into simpler concepts.
It is the atom from which all of PABLO's meaning is built.

Cross-linguistic research (Natural Semantic Metalanguage theory) has identified approximately
65 such primitives that exist universally across all known human languages. These appear to be
innate — part of the biological endowment of the human cognitive system, absorbed into the
genome through co-evolution with language over tens of thousands of generations.

PABLO's 63 primes are its equivalent of that innate primitive set. They are not concepts
PABLO learns or acquires. They are what PABLO is made of. Every observation, every stored
compound, every thought is ultimately expressible as a combination of these 63 primitives.

The prime set is **fixed**. It does not grow. If a new concept is needed, it is expressed
as a **Compound** built from primes. This constraint keeps all meaning grounded,
machine-interpretable, and traceable.

---

## A Prime Is Two Things

Each prime is simultaneously:

**An executable capability** — a prime can do things that fall within its domain.
READ perceives text. KNOW stores and retrieves. THINK reasons. SAY expresses.

**A semantic descriptor** — the same prime used to execute behaviour is used to label
the meaning of compounds. A compound with MOVE in its PrimeBit describes something that
involves movement, whether that's an action to take or an observation to record.

This dual role — executable and descriptive — means PABLO's action vocabulary and its
meaning vocabulary are identical. The same 63 primitives that define what PABLO can do
also define how PABLO represents what it experiences.

---

## The 63 Primes

Grouped by conceptual family. Canonical ordering is alphabetical (used for bit index assignment).

**Perceptors** — sensing the world
`READ`, `SEE`, `HEAR`, `TOUCH`

**Cognition and reasoning**
`THINK`, `KNOW`, `SYMBOL`, `DATA`, `CAUSE`, `BECAUSE`

**Action and change**
`DO`, `MAKE`, `MOVE`, `CHANGE`, `USE`, `WRITE`, `SAY`, `OPEN`

**Space and direction**
`HERE`, `AT`, `IN`, `FROM`, `TO`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `NEAR`, `FAR`, `BETWEEN`, `SIDE`

**Time and sequence**
`NOW`, `BEFORE`, `AFTER`, `LAST`, `TIME`

**Affective and mental predicates**
`FEEL`, `GOOD`, `BAD`

**Quantifiers**
`ONE`, `MANY`, `ALL`, `SOME`, `NONE`

**Entity and identity**
`THIS`, `OTHER`, `ENTITY`, `SELF`, `YOU`, `BODY`, `LIFE`

**Properties**
`MORE`, `LESS`, `LIGHT`, `HEAT`

**Relations and structure**
`PART`, `KIND`, `HAVE`, `WITH`, `BE`

**Modality and agency**
`CAN`, `WANT`, `NEED`

---

## Primes as Scene Contributors

In the old design, primes were assigned roles in a pipeline — each one receiving a fixed
input, processing it, and passing output to the next stage.

In the current design, primes are **subscribers to scene conditions**. When PABLO
experiences something — an input arriving, a goal activating, a memory surfacing — a
CognitiveScene is opened. Each prime perceives the scene and contributes what it is
sensitive to.

A prime's **nature** is its sensitivity pattern — the conditions in the scene that
cause it to emerge and contribute:

| Prime | Nature — what conditions it responds to |
|-------|----------------------------------------|
| READ | Unprocessed external input present in the environment |
| SYMBOL | Uninterpreted tokens present in the scene's perception layer |
| DATA | Token interpretations present, needing validation and compound assembly |
| KNOW | Compounds ready to store, or memory patterns to surface |
| SELF | Scene ready for attention evaluation; motivational/affective state active |
| FEEL | Affective relevance in scene content — Phase 4 |
| WANT | Scene content matches active goals — Phase 5 |
| THINK | Scene marked conscious by SELF; execution layer empty |
| SAY | Execution layer populated; response ready to express |

No prime is told what to do by another prime. No prime knows about another prime's
internals. What they share is only the CognitiveScene.

---

## Primes Learn Their Contribution

The key long-term property of this design: primes are not permanently hard-wired to
specific outputs. They learn what and how to contribute.

In Phase 1, primes write to the **MetaScene** — structured fields with explicit labels,
designed by humans during development. This is the scaffolded form.

Over time, primes also write to the **SymbolicScene** — an unstructured collection of
Compounds, Triples, and Narrative fragments in PABLO's own language. Initially sparse.
Gradually richer as each prime learns to crystallise its perception symbolically.

When a prime's SymbolicScene contributions become informationally equivalent to its
MetaScene contributions, the MetaScene field retires. The prime is now thinking in
PABLO's native language for that aspect of its perception.

This is the crystallisation loop applied to the primes themselves. Each prime runs the
loop: externalise in symbols → compare to the MetaScene → detect mismatch → refine
symbolic contribution → repeat.

---

## Core Invariants

These hold across all primes, always:

1. **The prime set is fixed.** 63 primes. New concepts are Compounds.

2. **Primes do not call each other.** Communication happens only through the CognitiveScene.
   A prime never imports another prime's internals.

3. **All meaning is prime-grounded.** Every Compound is traceable to the 63 primes.
   Nothing enters the cognitive system as an opaque blob.

4. **Neural models propose; the symbolic layer decides.** LLM output is always a candidate —
   validated and grounded before influencing the scene or storage.

5. **The scene is the source of truth.** During an experience, the CognitiveScene is
   authoritative. Primes write to it; they do not maintain private state about the experience.

---

## Primes, Compounds, Narratives

**Prime** — atomic, irreducible. The vocabulary.

**Compound** — composed from primes. A crystallised thought. The words and sentences.
Example: *fast* = `{MOVE, MORE, LESS, TIME}`. *Anger* = `{FEEL, BAD, DO, MORE}`.

**Triple** — a relation between compounds. `(subject) -[predicate]→ (object)`.
The relational fabric linking crystallised thoughts.

**Narrative** — a temporal thread of compounds and triples instantiated in a specific
lived context. PABLO's memory of an ongoing relationship, situation, or experience.
The story.

Primes are the vocabulary. Compounds are the words. Triples are the grammar.
Narratives are the memory.

---

*See `docs/SYSTEM/theory.md` for the theoretical foundation.*
*See `docs/SYSTEM/cognitive_scene.md` for how primes contribute to scenes.*
*See `docs/COMPOUND/compound_concept.md` for the Compound data structure.*
*See `docs/PRIMEBIT/PRIMEBIT_CONCEPT.md` for the encoding layer.*
