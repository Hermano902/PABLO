Primes – Concept and Design

Overview
Primes are the atomic, irreducible units of meaning in PABLO. Everything PABLO can think, sense, express, or reason about must ultimately decompose into these primitives. There are exactly 63 primes. This set is fixed and cannot be extended or reduced.

A prime is two things at once:
- Executable capability: a prime can be called to perform any action that falls within its domain.
- Descriptor: the same prime used to execute behavior is used to describe observations, states, and outcomes.

This dual role — executable and descriptive — is what makes each prime a universal multitool rather than a single narrow function.


The 63 Primes
Primes are grouped here by conceptual family for readability. Their canonical ordering is strictly alphabetical (used for bit index assignment).

Perceptors (external senses)
  READ, SEE, HEAR, TOUCH

Cognition & reasoning
  THINK, KNOW, SYMBOL, DATA, CAUSE, BECAUSE

Action & change
  DO, MAKE, MOVE, CHANGE, USE, WRITE, SAY, OPEN

Space & direction
  HERE, AT, IN, FROM, TO, UP, DOWN, LEFT, RIGHT, NEAR, FAR, BETWEEN, SIDE

Time & sequence
  NOW, BEFORE, AFTER, LAST, TIME

Affective & mental predicates
  FEEL, GOOD, BAD

Quantifiers
  ONE, MANY, ALL, SOME, NONE

Entity & identity
  THIS, OTHER, ENTITY, SELF, YOU, BODY, LIFE

Properties
  MORE, LESS, LIGHT, HEAT

Relations & structure
  PART, KIND, HAVE, WITH, BE  (BE is the existential/copula prime: asserts existence or identity, e.g. "X is Y")

Modality & agency
  CAN, WANT, NEED


Core Principles

1. Fixed and finite
The prime set does not grow. If a concept cannot be expressed with the 63 primes, it must be expressed as a compound — a combination of primes. This constraint forces all meaning to remain grounded and machine-interpretable.

2. Universal multitool
Each prime covers its entire domain. READ is not just "read text from stdin" — it is the full capability of textual perception in any form. A prime's behavior adapts to the context it receives, but its identity and domain never change.

3. Domain ownership
Each prime fully owns its domain and does not delegate to other primes' internals. READ owns all text perception logic. DATA owns all structuring logic. KNOW owns all memory. No prime reaches into another prime's implementation.

4. Decentralized agents
Primes are independent. They do not require a central coordinator to function. Each prime can operate on its own, producing outputs that other primes can consume.

5. Compound-only communication boundary
When one prime consults another, it receives only a Compound output — never raw data, internal state, or method calls. Primes are black boxes to each other. This boundary keeps them truly independent and replaceable.

6. Autonomous and consultation modes
Some primes (the perceptors: READ, SEE, HEAR) run continuously in the background without being called. In this autonomous mode, they are exempt from the compound-only rule and may emit raw observations. All other primes operate on-demand: they are called with a context and return a Compound.

7. Meaning emerges from interaction
No single prime carries rich meaning alone. Meaning emerges when primes interact through Compounds. READ's observations become meaningful when structured by DATA, which become persistent and searchable via KNOW. SELF's role is to direct attention — monitoring the data flow, scoring salience against active goals (WANT) and affective state (FEEL), and waking THINK when conscious reasoning is warranted. THINK then integrates what KNOW holds to produce a response.


Prime Orchestration Hierarchy
Primes form a natural hierarchy not of control, but of cognitive role:

  SELF  (meta-cognitive awareness — observes and biases the system)
    THINK  (cognitive coordination — integrates signals, goals, affect)
      READ, SEE, HEAR  (perception — sample the external world autonomously)
      SYMBOL  (interpretation — autonomous: raw obs → near-compound candidates; on-demand: ground placeholders)
      DATA   (structuring — validate near-compound candidates → real compounds)
      KNOW   (memory — store and retrieve compounds)
    FEEL  (affective state — valence awareness)
      GOOD, BAD
    WANT  (motivation — drives goals)
      NEED, CAN

This is an orchestration hierarchy: higher-level primes orchestrate lower-level ones by calling them, not by overriding them. Lower-level primes do not know who called them.


Primes vs Compounds vs Narratives
A prime is atomic — it cannot be decomposed further. A compound is composed — it is built
from primes (and other compounds) to express richer meaning. A narrative is contextual —
it takes compounds as building blocks and instantiates them within a specific lived frame.

For example:
  "fast" is not a prime. It can be expressed as the compound {MOVE, MORE, TIME, LESS}.
  "the red ball Alice threw" is not a compound. It is a narrative binding: THIS_BALL,
  based on compound BALL, with current state {colour: red, last_action: thrown, actor: THIS_ALICE}.

Primes are the vocabulary. Compounds are the words and sentences. Narratives are the story.


Design Decisions Summary

Decision                                          Rationale
Fixed set of 63 primes                            Forces all meaning to be grounded; prevents unbounded concept drift
Dual role (executable + descriptive)              Same primitives used for action and description; unified representation
Domain ownership (no cross-prime method imports)  True encapsulation; each prime is independently replaceable
Compound-only communication boundary              Clean interface between primes; prevents tight coupling
Autonomous mode for perceptor primes              Allows always-on sensing without blocking higher cognition
Meaning emerges from interaction                  Flexible, emergent intelligence without rigid hand-coded rules
