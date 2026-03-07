# Primes

---

## Concept

A prime is an irreducible unit of meaning. It cannot be decomposed into simpler concepts.
It is the atom from which all of PABLO's meaning is built.

Cross-linguistic research (Natural Semantic Metalanguage) has identified approximately 65
such primitives that exist universally across all known human languages. These appear to
be innate — part of the biological endowment of the human cognitive system, absorbed into
the genome through co-evolution with language over tens of thousands of generations.

PABLO's 63 primes are its equivalent of that innate primitive set. They are not concepts
PABLO learns or acquires. They are what PABLO is made of. Every observation, every stored
Compound, every thought is ultimately expressible as a combination of these 63 primitives.

The prime set is **fixed**. It does not grow. If a new concept is needed, it is expressed
as a **Compound** built from primes. This constraint keeps all meaning grounded,
machine-interpretable, and traceable.

---

### A prime is two things simultaneously

**An executable capability** — a prime can do things within its domain.
READ perceives text. KNOW stores and retrieves. THINK reasons. SAY expresses.

**A semantic descriptor** — the same prime used to execute behaviour labels the meaning
of Compounds. A Compound with MOVE in its primebit describes something that involves
movement, whether that is an action to take or an observation to record.

This dual role means PABLO's action vocabulary and its meaning vocabulary are identical.
The same 63 primitives that define what PABLO can do also define how PABLO represents
what it experiences.

---

### Primes are subscribers to scene conditions

Primes do not receive instructions from other primes. When PABLO experiences something —
an input arriving, a goal activating, a memory surfacing — a CognitiveScene is opened.
Each prime perceives the scene and contributes what it is sensitive to.

A prime's **nature** is its sensitivity pattern — the scene conditions that cause it to
emerge and contribute:

| Prime | Nature — what conditions it responds to |
|-------|----------------------------------------|
| READ | Unprocessed external input present in the environment |
| SYMBOL | Uninterpreted signal in the scene's perception layer |
| DATA | SYMBOL's resolutions present; validation and assembly needed |
| KNOW | Compounds ready to store, or scene context that could be enriched by memory |
| SELF | Scene memory layer populated; attention decision pending |
| FEEL | Affective relevance in scene content — Phase 4 |
| WANT | Scene content matches active goals — Phase 5 |
| THINK | Scene marked conscious by SELF; execution layer empty |
| SAY | Execution layer populated; response ready to express |

No prime is told what to do by another prime. No prime knows about another prime's
internals. What they share is only the CognitiveScene.

---

### Primes learn their contribution

In Phase 1, primes write to the **MetaScene** — structured fields with explicit labels,
the scaffolded form designed for human inspection during development.

Over time, primes also write to the **SymbolicScene** — an unstructured collection of
Compounds, Triples, and Narrative fragments in PLanguage. Initially sparse. Gradually
richer as each prime learns to crystallise its perception symbolically.

When a prime's SymbolicScene contributions become informationally equivalent to its
MetaScene contributions, the MetaScene field retires. The prime is now thinking in
PABLO's native language for that aspect of its perception.

This is the crystallisation loop applied to the primes themselves.

---

### The 63 primes

Grouped by conceptual family. Canonical ordering is alphabetical (used for bit index
assignment in PrimeBit).

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

### Core invariants

These hold across all primes, always:

1. **The prime set is fixed.** 63 primes. New concepts are Compounds.

2. **Primes do not call each other.** Communication happens only through the CognitiveScene.
   A prime never imports another prime's internals.

3. **All meaning is prime-grounded.** Every Compound is traceable to the 63 primes.
   Nothing enters the cognitive system as an opaque blob.

4. **Neural models propose; the symbolic layer decides.** LLM output is always a candidate —
   validated by DATA and grounded before influencing the scene or storage.

5. **The scene is the source of truth.** During an experience, the CognitiveScene is
   authoritative. Primes write to it; they do not maintain private state about the experience.

---

## Architecture

### Prime implementation pattern

Each prime is a module in `primes/`. It exposes a single entry point:

```python
def contribute(scene: CognitiveScene) -> None:
    """Read scene conditions. If conditions are met, contribute."""
```

A prime checks its sensitivity condition against the scene state. If the condition is
not met, it returns immediately. If it is met, it writes to the scene and returns.

No prime holds state between scenes. No prime calls another prime's `contribute()`.

### Dormant primes

All primes begin dormant. A prime is activated (wired into the pipeline) only when its
Phase is reached. Dormant primes exist as stubs that return immediately regardless of
scene state.

This means the codebase always has all 63 primes present, but only the phase-appropriate
ones do work. Testing each prime in isolation — before wiring — is the standard workflow.

### Phase activation order

| Phase | Primes activated | What becomes possible |
|-------|-----------------|----------------------|
| 1 | READ, SYMBOL, DATA, KNOW | Perception → crystallisation → storage |
| 2 | SELF | Attention gating; not everything reaches THINK |
| 3 | THINK, SAY | Conscious reasoning and expression |
| 4 | FEEL | Affective weighting of salience |
| 5 | WANT, NEED | Motivational relevance; internal scenes |
| 6 | SEE, HEAR | Non-linguistic perception |
| 7 | WRITE | Persistent expression; artifact creation |

---

*See [cognitive_scene.md](../SYSTEM/cognitive_scene.md) for how primes contribute to scenes.*
*See [planguage.md](../PLANGUAGE/planguage.md) for the PLanguage units primes work with.*
*See [primebit.md](../SYSTEM/primebit.md) for the bit encoding of prime sets.*
*See [system.md](../SYSTEM/system.md) for the theoretical foundation.*
