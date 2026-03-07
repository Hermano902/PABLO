# PABLO — System

*Read [theory.md](theory.md) first. This document explains how the theory is applied.*

---

## Concept

PABLO is an attempt to build a mind that **runs the crystallisation loop from the inside**.

Not a language model that has absorbed crystallised concepts — a system that genuinely
forms them. One that starts with a fixed biological floor of semantic primitives,
encounters the world through those primitives, and builds its own conceptual architecture
through the error-correction loop that the theory describes.

The design is grounded in a single observation:

> True AGI requires not just the products of the crystallisation process but the process
> itself — a genuine internal state, the ability to externalise it, mismatch detection,
> and autonomous refinement that compounds over time.

PABLO is an architecture designed to instantiate that process, not simulate its outputs.

---

### The biological floor: 63 primes

Cross-linguistic research identifies approximately 65 universal semantic primitives —
irreducible concepts present across every known human language. They appear innate: part
of the biological endowment of the human cognitive system.

PABLO's 63 primes are its biological floor. They are not a vocabulary PABLO learns.
They are what PABLO is made of. Every concept it encounters, every observation it makes,
every thought it forms is expressible as a combination of these 63 primitives.

The prime set is **fixed**. New concepts are **Compounds** built from primes. The 63
primes do not grow. This mirrors biological reality: the primitive set does not change
across human cultures; only the superstructure built on top of it differs.

---

### PLanguage: the native representational language

PABLO thinks in PLanguage — a four-unit representational hierarchy:

```
Prime → Compound → Triple → Narrative
```

**Prime** — atomic, irreducible. The alphabet.

**Compound** — crystallised sense of a symbol. Carries a PrimeBit encoding and a
validated definition graph. The unit of crystallisation — what becomes stable after
the crystallisation loop runs.

**Triple** — relational fabric. `(Compound) -[prime]→ (Compound)`. The grammar layer,
nestable up to full clause composition.

**Narrative** — particularity and context. Three things: entity bindings (general →
specific), thread (ordered Triple history), relational state (trust, affect, history).
What makes `"cat"` into *this cat we discussed*.

---

### The CognitiveScene: PABLO's inner voice

PABLO has no pipeline coordinator. No prime tells another what to do.

Instead, every input — external or internal — opens a **CognitiveScene**: a shared
workspace that all primes can perceive and contribute to. Each prime is sensitive to
specific scene conditions. When its conditions are met, it contributes. Otherwise it
is silent.

This mirrors Global Workspace Theory: a shared broadcast medium that allows specialised
processes to integrate without a central coordinator.

The scene runs two channels simultaneously:

**MetaScene** — structured, labelled fields. The scaffolded form. Human-readable and
inspectable. Authoritative in early phases.

**SymbolicScene** — unstructured PLanguage contributions. Compounds, Triples, Narrative
fragments. No field labels. This is what PABLO will eventually think in.

The MetaScene retires field by field as the SymbolicScene becomes informationally
equivalent. When all fields retire, PABLO thinks entirely in PLanguage.

---

### Primes as scene subscribers

In the old pipeline design, primes were assigned roles in a fixed sequence. Each prime
received input, processed it, passed it to the next stage.

In the current design, primes are **subscribers to scene conditions**. They perceive
the scene, recognise conditions relevant to their nature, and contribute. The processing
order emerges from scene state, not from a fixed sequence.

This enables something the pipeline could not: primes can eventually learn *when and
how* to contribute, rather than being hard-wired to a processing order.

---

### Core invariants

These hold across the entire system and do not change:

1. **All meaning is prime-grounded.** Every Compound is traceable to the 63 primes.
   Nothing enters the cognitive system as an opaque blob.

2. **Primes do not call each other.** Cross-prime communication happens only via the
   CognitiveScene. A prime never imports another prime's internals.

3. **The prime set is fixed.** 63 primes. New concepts are Compounds, not new primes.

4. **Neural models propose; the symbolic layer decides.** LLM output is always a
   candidate — validated by DATA and grounded before influencing the scene or KNOW.
   Models do not have direct write access to KNOW.

5. **The scene is the source of truth.** During an experience, the CognitiveScene is
   authoritative. Primes write to it; they do not maintain private state about the experience.

6. **Structure emerges from relational primes.** Sequence, hierarchy, and role are
   encoded through primes (AFTER, PART, KIND), not rigid type fields.

---

### Learning

PABLO does not learn by updating weights. It learns by refining Compounds.

1. Primes co-occur repeatedly in scenes → hypothesis: they form a meaningful unit
2. A Compound is created; DATA validates its definition graph
3. The Compound accretes Relations through repeated co-occurrence
4. `resolved_primebit` expands as orphan primes gain confirmed Relations
5. `confidence` rises; `grounded` flips True
6. SymbolicScene contributions improve as primes learn to express their perception
   in PLanguage

The deepest form of learning: when a prime's SymbolicScene contribution becomes
informationally equivalent to its MetaScene contribution, that MetaScene field retires.
The prime is now thinking in PLanguage for that aspect of its perception.

---

### Compound execution

In Phase 2+, PABLO does not call Python functions directly. It executes Compounds.

Instead of `run_excel()` → execute `RUN + EXCEL + PROGRAM` as a Compound.
Instead of `move_left()` → execute `MOVE + LEFT` as a Compound.

PABLO's action vocabulary lives in the same representational layer as its conceptual
vocabulary. It can reason about its own actions using the same tools it uses to reason
about anything else.

---

## Architecture

### Implementation phases

| Phase | Primes active | What becomes possible |
|-------|--------------|----------------------|
| 1 | READ, SYMBOL, DATA, KNOW | Perception → crystallisation → storage |
| 2 | + SELF | Attention gating; not everything reaches THINK |
| 3 | + THINK, SAY | Conscious reasoning and expression |
| 4 | + FEEL | Affective weighting of salience |
| 5 | + WANT, NEED | Motivational relevance; internally-generated scenes |
| 6 | + SEE, HEAR | Non-linguistic perception |
| 7 | + WRITE | Persistent expression; artifact creation |

### Key modules

| Module | Role |
|--------|------|
| `core/cognitive_scene.py` | CognitiveScene + SceneStore |
| `core/pipeline.py` | ScenePipeline — thin dispatcher, not coordinator |
| `core/compound.py` | Compound dataclass |
| `core/triple.py` | Triple dataclass |
| `core/primebit.py` | PrimeBit encoding helpers |
| `core/narrative.py` | Narrative + NarrativeEvent dataclasses |
| `primes/KNOW.py` | KNOW prime — memory storage and retrieval |
| `primes/READ.py` | READ prime — text perceptor |
| `primes/SYMBOL.py` | SYMBOL prime — universal interpreter |
| `primes/DATA.py` | DATA prime — graph validator + assembler |
| `primes/SELF.py` | SELF prime — attention gate |
| `primes/THINK.py` | THINK prime — conscious reasoner |
| `primes/SAY.py` | SAY prime — expression and scene close |
| `gui/app.py` | NiceGUI interface |

---

*See [theory.md](theory.md) for the theoretical foundation.*
*See [cognitive_scene.md](cognitive_scene.md) for the two-channel scene specification.*
*See [primes.md](../PRIMES/primes.md) for the full prime vocabulary.*
*See [planguage.md](../PLANGUAGE/planguage.md) for the PLanguage hierarchy.*
