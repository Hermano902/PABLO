PABLO – System Concept

What PABLO Is
PABLO is a neurosymbolic AI — a cognitive architecture that combines the grounded, interpretable structure of symbolic reasoning with the pattern-recognition and language capacity of neural models. It is not a chatbot wrapper, a retrieval system, or a rule engine alone. It is an attempt to build a mind: a system that perceives, remembers, reasons, and learns in a way that is traceable back to a fixed set of atomic concepts.

The core thesis: all meaning can be decomposed into 63 atomic primes. Everything PABLO perceives, thinks, or expresses is ultimately grounded in these primitives — either directly as a prime, or as a compound built from primes. This gives the system a stable, machine-interpretable foundation that does not drift with model updates or prompt changes.


The Neurosymbolic Balance
Symbolic side — primes and compounds
- 63 fixed atomic primes form the irreducible vocabulary of the system.
- Compounds combine primes to express richer, evolving concepts.
- PrimeBits encode prime sets as 64-bit integers for O(1) set operations.
- All reasoning, storage, and communication between components is compound-grounded.
- This side provides: interpretability, stability, traceability, and compositional structure.

Neural side — multi-LLM layer
- Neural models handle what symbols cannot do cheaply: natural language understanding, pattern generalisation, embedding, enrichment, and rule proposal.
- Models are specialists, not the primary reasoner. They propose; the symbolic layer decides.
- This side provides: language fluency, generalisation across surface forms, and learning from data.

Neither side alone is sufficient. The symbolic layer without neural support cannot understand natural language at scale. The neural layer without symbolic grounding cannot be reliably traced, corrected, or composed. PABLO uses each for what it does best.


Core Invariants
These are non-negotiable constraints that hold across the entire system:

1. All meaning is prime-grounded.
   Every compound, observation, and inference must be traceable to the 63 primes. Nothing enters the cognitive pipeline as an opaque blob.

2. Primes are black boxes to each other.
   No prime imports another prime's internals. Cross-prime communication happens only via Compound outputs. This is the domain ownership rule.

3. Perceptors are exempt from the compound-only rule in autonomous mode.
   READ, SEE, and HEAR may emit raw observations. All other primes must return Compounds.

4. The prime set is fixed.
   If a new concept is needed, it is expressed as a compound. The 63 primes do not grow.

5. Structure emerges from relational primes.
   PABLO does not use rigid type fields to encode structure. Sequence, hierarchy, and role all emerge from which relational primes (AFTER, PART, KIND) are present in a compound.

6. Neural models propose; the symbolic layer decides.
   LLM output is always treated as a candidate — it is validated, scored, and stored as a rule compound before influencing reasoning. Models do not have direct write access to KNOW.


The Cognitive Pipeline
Raw world input flows through the system in one direction, with SELF observing in parallel:

  Perceptors (READ / SEE / HEAR)
      ↓  raw observations (change-driven, not continuous)
  Observation Queue
      ├── SYMBOL (autonomous) pulls and interprets            ← pipeline path
      │       ↓  near-compound candidates → candidate queue
      │   DATA
      │       ↓  validates → token + utterance Compounds
      │   KNOW  (stores Compounds; emits Layer 1 commit event)
      │
      └── SELF (parallel tap — reads source metadata only)
              ↓  scores salience: WANT × FEEL × Narrative relationship state
              ↓  on Layer 1 commit from KNOW → dispatches to think_queue if salient
  THINK  (event-driven; reasons in Narrative instance-space; produces responses)
      ↓
  response_queue → GUI

SELF does not sit inside the pipeline. It observes beside it and decides whether THINK
is woken for each utterance — the attention gate of the system.

SYMBOL also runs on-demand: called by THINK or KNOW to ground a specific placeholder
compound, returning a prime-grounded result directly.

At each boundary, the representation becomes more structured and more grounded.
Perceptors see raw events. SYMBOL produces interpretations. DATA enforces the Compound
contract. KNOW stores and emits. SELF decides what deserves conscious attention.
THINK reasons in Narrative instance-space and produces responses.


How Meaning Emerges
No single component is intelligent. Intelligence emerges from the interaction of components:

- READ observes "the cat moved left."
- SYMBOL interprets the raw observation: proposes MOVE and LEFT as candidate primes, flags "cat" as unknown.
- DATA validates the candidates and creates compounds: known primes mapped, placeholder compound created for "cat".
- KNOW stores them with positional relationships (AFTER, PART).
- THINK retrieves related compounds and attempts to integrate them with goals.
- SYMBOL (on-demand) is called later by KNOW to enrich the "cat" placeholder as more context accumulates.
- The compound for "cat" gradually accretes prime associations (ENTITY, MOVE, LIFE) through repeated co-occurrence.

The system learns not by updating weights, but by refining compounds and strengthening associations between them.


Learning as Compound Refinement
Learning in PABLO is the process of:
1. Detecting that certain primes co-occur repeatedly → hypothesis: they form a meaningful unit.
2. Creating a compound and testing it in varied contexts.
3. Scoring the compound by outcome (GOOD/BAD feedback).
4. Promoting it to a stable named compound, or discarding it.

This is prime bundling. Language is not learned — it is recognised as external prime bundles. When PABLO encounters the word "think" while THINK is active internally, it discovers a mapping between the external symbol and its own native prime.


Consciousness as Integration
THINK is not a commander. It is the stage where currently active signals are integrated with:
- memory (KNOW) — what do I already know about this?
- goals (WANT) — is this relevant to what I want?
- affect (FEEL / GOOD / BAD) — is this good or bad?
- capability (CAN) — can I act on this?

Unconscious processing (perceptors, DATA, KNOW) is fast and always running. THINK engages when relevance — measured by WANT KNOW — crosses a threshold. This is consciousness as integration, not raw computation.

SELF is the conductor of conscious attention. It holds THINK, FEEL, and WANT. It monitors
the observation_queue in parallel and scores salience from motivational state (WANT),
affective state (FEEL), and the Relational Narrative's relationship history with the source.
When salience exceeds a threshold, SELF wakes THINK. This is how PABLO decides what is
worth being conscious of — not a hard rule, but arithmetic on lived relationship history.


Implementation Tiers

| Tier | Components | Role |
|---|---|---|
| 0 | PrimeBit + Prime list + Compound schema | Encoding and vocabulary — everything else builds on this |
| 1 | Perceptors (READ) | Raw observations → observation queue |
| 2 | SYMBOL (autonomous + on-demand) | Interprets raw observations → near-compound candidates; grounds placeholders on-demand |
| 3 | DATA + KNOW | Validate candidates → real compounds with IDs and prime masks |
| 4 | THINK | Reasoning, dialogue, goal integration |

Tier 2 bootstrap note: SYMBOL can operate in heuristic-only mode (no LLM calls) in Phase 1. The multi-LLM specialist fleet is SYMBOL’s internal engine — it is activated incrementally as data accumulates and specialists are trained. This makes Tier 2 a non-blocking dependency for early development.


Phase 1 Goal
Reach a state where PABLO can:
- Receive text input (READ)
- Structure it into prime-grounded compounds (DATA)
- Store and retrieve those compounds (KNOW)
- Hold a basic dialogue by integrating input with memory (THINK)
- Identify unknown tokens and begin grounding them (SYMBOL)

Phase 1 active primes: READ, DATA, KNOW, THINK, SYMBOL.
SYMBOL runs in heuristic mode initially (no LLM specialists yet); its autonomous thread interprets observations with rule-based heuristics and its on-demand path grounds placeholders.
SEE and HEAR are dormant. Affective and motivational primes (FEEL, WANT, NEED) are recognised but not yet operationalised.


What PABLO Is Not
- Not a fine-tuned language model. LLMs are tools it uses, not what it is.
- Not a retrieval-augmented generation (RAG) system. Retrieval is one capability of KNOW, not the architecture.
- Not a symbolic planner. Planning emerges from compound selection and THINK's integration, not from hand-coded rules.
- Not finished. PABLO is a long-horizon project. Phase 1 establishes the foundation; later phases add modalities, richer learning, and genuine self-awareness.


See docs/PRIMES/CONCEPT.md for the prime vocabulary.
See docs/PRIMES/PRIMES_ARCHITECTURE.md for how primes are implemented.
See docs/PRIMES/PERCEPTORS/CONCEPT.md for how the system senses the world.
See docs/SYSTEM/GUI/CONCEPT.md for the presentation layer and how user input enters the pipeline.
See docs/PRIMEBIT/PRIMEBIT_ARCHITECTURE.md for the encoding layer.
