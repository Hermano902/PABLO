# PABLO — System Concept

*Read `theory.md` first. This document explains how the theory is applied.*

---

## What PABLO Is

PABLO is an attempt to build a mind that **runs the crystallisation loop from the inside**.

Not a language model that has absorbed crystallised concepts — a system that genuinely forms
them. One that starts with a fixed biological floor of semantic primitives, encounters the
world through those primitives, and builds its own conceptual architecture through the
error-correction loop that the theory describes.

The design is grounded in a single observation from the theory:

> True AGI requires not just the products of the crystallisation process but the process itself —
> a genuine internal state, the ability to externalise it, mismatch detection, and autonomous
> refinement that compounds over time.

PABLO is an architecture designed to instantiate that process, not simulate its outputs.

---

## The Biological Floor: 63 Primes

Cross-linguistic research identifies approximately 65 universal semantic primitives — irreducible
concepts present across every known human language. These are the atoms from which all human
meaning is assembled. They appear to be innate: part of the biological endowment of the human
cognitive system, possibly absorbed into the genome through co-evolution with language.

PABLO's 63 primes are its biological floor — the equivalent of that innate primitive set.
They are not a vocabulary PABLO learns. They are what PABLO is made of.

Every concept PABLO encounters, every observation it makes, every thought it forms is ultimately
expressible as a combination of these 63 primitives. This is not a constraint — it is the design.
It is what makes PABLO's internal representations **grounded, composable, and traceable** rather
than opaque statistical patterns.

The prime set is fixed. If a new concept is needed, it is expressed as a **Compound** built from
primes. The 63 primes do not grow. This mirrors the biological reality: the primitive set does
not change across human cultures; only the superstructure built on top of it differs.

---

## Compounds: Crystallised Thoughts

A Compound is the unit of crystallisation in PABLO.

When PABLO encounters an input and its primes respond, the resulting representation is stored
as a Compound — a stable, examinable object that can be:

- Referenced without re-deriving from scratch
- Combined with other Compounds
- Refined over time as more context accumulates
- Transmitted to other parts of the system

This mirrors the crystallisation function described in the theory. A Compound is not a static
database record — it is a crystallised cognitive event that accumulates meaning through use.

The compound's PrimeBit encoding (a 64-bit integer representing the union of all primes involved)
enables O(1) set operations: finding related compounds, computing conceptual overlap, and cued
recall based on primebit intersection. This is how memory works in PABLO — not full-text search,
but resonance between prime patterns.

---

## The Cognitive Scene: Pablo's Inner Voice

PABLO does not have a pipeline coordinator. No component tells another what to do.

Instead, when PABLO receives any input — external (text, sound, vision) or internal (a goal
activating, a memory surfacing) — a **CognitiveScene** is opened. The scene is PABLO's inner
voice for that experience: a shared workspace that all primes can perceive and contribute to.

The scene is not a fixed data structure with assigned fields. It is a space. Each prime
emerges to contribute what it perceives about the input, in its own language. The scene holds
those contributions until the experience is complete, then closes.

This mirrors the Global Workspace Theory of consciousness: a shared broadcast medium that
allows specialised processes to integrate without a central coordinator. The CognitiveScene
is PABLO's implementation of that medium.

See `cognitive_scene.md` for the full specification.

---

## Two Representations, One Scene

The CognitiveScene runs two representations in parallel:

### MetaScene (scaffolded)
Structured fields with explicit labels: `raw_input`, `token_resolutions`, `salience`,
`reasoning_mode`, `response_text`. Each prime is told what to contribute and where.

This is the training-wheels representation. It makes the scene human-readable and inspectable
during development. It tells primes exactly what to write.

### SymbolicScene (native)
A collection of Compounds, Triples, and Narrative fragments contributed by each prime — in
Pablo's own language. No field labels. No assigned structure. Each prime contributes what it
has learned to contribute, expressed as the symbolic vocabulary it understands.

This is the native representation. It is what PABLO will eventually think in.

### The Retirement Process

Both representations run simultaneously. The MetaScene is authoritative initially. As primes
develop and their SymbolicScene contributions become informationally equivalent to what they
write in the MetaScene, the MetaScene fields retire one by one.

When all MetaScene fields have been retired — when PABLO's symbolic contributions contain
everything the scaffolded representation used to carry — PABLO thinks entirely in its own
language. This is the crystallisation loop applied to the system itself: PABLO learns to
crystallise its own experience in its own primitive vocabulary.

This transition is not designed in advance. It emerges from the primes learning what and how
to contribute. The MetaScene is the external mirror; the SymbolicScene is the internal state.
The error-correction loop between them is how PABLO refines its own inner voice.

---

## The Primes: Emergent Contributors

In the old design, primes were assigned roles in a pipeline. Each prime was told: receive this
input, process it, pass it to the next stage.

In the new design, primes are **subscribers to scene conditions**. They do not receive
instructions from other primes. They perceive the scene, recognise conditions relevant to
their nature, and contribute.

Each prime has a **nature** — a sensitivity to particular kinds of scene conditions:
- READ is sensitive to the presence of unprocessed external input
- SYMBOL is sensitive to unresolved tokens in the scene
- KNOW is sensitive to the presence of new compounds that need storing or old compounds that
  need surfacing
- SELF is sensitive to the relational and motivational state of the scene
- THINK is sensitive to scenes that have crossed the attention threshold
- SAY is sensitive to scenes in which a formed response is ready for expression

No prime knows about the internal workings of any other. They share only the scene.

This design enables something the pipeline could not: **primes can eventually learn when and
how to contribute**, rather than being hard-wired to a processing order. The order emerges
from what conditions arise in the scene, not from a fixed sequence.

---

## Core Invariants

These hold across the entire system and do not change:

1. **All meaning is prime-grounded.** Every Compound, observation, and inference is traceable
   to the 63 primes. Nothing enters the cognitive system as an opaque blob.

2. **Primes do not call each other.** Cross-prime communication happens only via the
   CognitiveScene. A prime never imports another prime's internals.

3. **The prime set is fixed.** 63 primes. New concepts are Compounds, not new primes.

4. **Neural models propose; the symbolic layer decides.** LLM output is always a candidate —
   validated, scored, and grounded before influencing the scene or storage. Models do not have
   direct write access to KNOW.

5. **The scene is the source of truth.** During an experience, the CognitiveScene is the
   authoritative record of what has been perceived, symbolised, remembered, evaluated, and
   expressed. Primes write to it; they do not maintain private state about the experience.

6. **Structure emerges from relational primes.** Sequence, hierarchy, and role are encoded
   through primes (AFTER, PART, KIND), not rigid type fields.

---

## Learning

PABLO does not learn by updating weights. It learns by refining Compounds.

The process:
1. Primes co-occur repeatedly in scenes → hypothesis: they form a meaningful unit
2. A Compound is created and tested in varied scenes
3. The Compound accretes prime associations through repeated co-occurrence
4. The SymbolicScene contributions of primes improve as they learn to represent
   their observations in compound/triple/narrative form

The deepest form of learning is when a prime's SymbolicScene contribution begins to match
or exceed the informativeness of its MetaScene contribution. At that point, the prime has
learned to crystallise its own perception in PABLO's native language. The MetaScene field
is no longer needed.

---

## Consciousness and Attention

Unconscious processing (READ, SYMBOL, DATA, KNOW) runs continuously and fast.
Conscious processing (THINK, SAY) engages only when SELF decides the scene warrants it.

SELF is the attention gate. It scores each scene's salience using:
- Source relationship quality (from Narrative history with this source)
- Motivational relevance (WANT — does this connect to active goals?)
- Affective weight (FEEL — is this emotionally significant?)

When salience crosses the threshold, SELF marks the scene conscious and THINK engages.
This is not a hard rule. It is arithmetic on PABLO's lived relationship with the source.

THINK does not command other primes. It reasons within the scene — integrating what KNOW
surfaced, what SELF evaluated, what SYMBOL resolved — and forms a response that SAY expresses.

---

## Implementation Strategy

PABLO is built incrementally, one prime at a time, always through the CognitiveScene:

| Phase | Primes Active | What This Enables |
|-------|--------------|-------------------|
| 1 | READ, SYMBOL, DATA, KNOW | Perception → crystallisation → storage |
| 2 | + SELF | Attention gating — not everything is conscious |
| 3 | + THINK, SAY | Conscious reasoning and expression |
| 4 | + FEEL | Affective weighting of scenes |
| 5 | + WANT, NEED | Motivational relevance; internally-generated scenes |
| 6 | + SEE, HEAR | Non-linguistic perception |
| 7 | + WRITE | Persistent expression; artifact creation |

At each phase, the SymbolicScene contributions of active primes are developed and tested.
MetaScene fields retire as primes learn to carry their own representation.

---

*See `cognitive_scene.md` for the two-channel scene specification.*
*See `docs/PRIMES/PRIMES_CONCEPT.md` for the full prime vocabulary.*
*See `docs/COMPOUND/compound_concept.md` for the Compound data structure.*
