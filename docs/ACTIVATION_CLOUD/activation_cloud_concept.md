# Activation Cloud — Concept

## Overview

The Activation Cloud is PABLO's pattern recognition mechanism. It is not a
preprocessing step that feeds an LLM. It IS the cognition — the equivalent of
the human brain's simultaneous firing of all relevant memory, context, emotion,
and goal state when processing a single input.

When a human reads the word "fire", the entire brain activates simultaneously:
semantic memory, episodic memory, emotional memory, motor memory, current context,
current goals. Meaning emerges from the weighted activation pattern before
conscious thought engages. There is no separate interpreter sitting on top of
this activation. The activation IS the interpretation.

PABLO's activation cloud replicates this. Every token that arrives causes the
entire compound graph to partially activate — weighted by how relevant each
compound is to that token, in that context, at that moment.

The cloud is not a data store. It is a transient activation pattern assembled
fresh for each token, used once, then discarded.


## The Brain Parallel

```
Human brain:                         PABLO activation cloud:
────────────────────────────────     ────────────────────────────────
Semantic memory fires                KNOW compound graph activates
Episodic memory fires                Active narrative activates
Working memory fires                 Utterance context activates
Emotional memory fires               FEEL valence activates (Phase 2)
Goal state fires                     WANT/NEED activates (Phase 3)
Relationship context fires           SELF/relational narrative (Phase 4)
All simultaneously                   Parallel assembly (Phase 2 GPU)
Meaning emerges from pattern         Triple emerges from dominant activation
No separate interpreter              No separate LLM when cloud is confident
```

This is pattern recognition, not lookup. The cloud is what the brain's pattern
recognition IS — not a model that performs pattern recognition, but the
mechanism itself.


## Relationship to the "Internal LLM"

There is no separate internal LLM sitting on top of the activation cloud.

The activation cloud IS the internal LLM equivalent. As the compound graph
grows richer and more densely connected, the cloud's ability to resolve triples
directly from activation patterns improves. DeepSeek (the external LLM) is only
called when the cloud cannot resolve confidently.

DeepSeek's role:
  Reads English surface forms
  Produces triples in PABLO's prime language
  Called when cloud confidence is below threshold
  Every output enriches the compound graph
  Called less and less as graph matures
  Retired when cloud agreement exceeds threshold


## What the Cloud Contains

### Cognitive Layer (Phase 1 — Active)

exact_match
  The existing compound for this exact surface form, if it exists in KNOW.
  If found: token is already grounded. Fast path — no LLM call.

family_root
  The root compound via KIND chain if this is an inflected form.
  "running" → root "run". Root's full definition included.
  Grammatical primes derived from surface form morphology.

definition_compounds
  The compounds that compose this token's definition in PABLO's knowledge.
  If "rebel" has a definition narrative, its nested compounds are fetched:
  person_compound, authority_compound, refuse_compound.
  These are the semantic building blocks already stored in KNOW.

utterance_compounds
  Already-resolved sibling compounds in this utterance, in order.
  Earlier tokens pre-activate the field for later tokens.
  Utterance context is directional — left to right, building up.

utterance_primebit
  Union primebit of all resolved utterance compounds so far.
  The "flavour" of the utterance — which prime families are already active.

narrative_compounds
  Recent N compounds from the active Instance Narrative (default N=5).
  Provides longer-range topic context than the current utterance.

narrative_primebit
  Union primebit of recent narrative compounds.
  "rebel" activates differently in a politics narrative vs a music narrative.

prime_candidates
  Pre-activation step: primes already lighting up from all cognitive sources.
  Weighted by source agreement — prime active in 3 sources > prime in 1 source.

fast_path
  True if cloud is confident enough to produce triples without LLM call.
  Either: exact_match confidence >= threshold
  Or: prime candidate convergence >= threshold across multiple sources.


### Affective Layer (Phase 2 — Dormant)

affective_valence    FEEL — emotional tone attached to this token (-1.0 to 1.0)
affective_intensity  FEEL — how strongly the valence is felt (0.0 to 1.0)


### Motivational Layer (Phase 3 — Dormant)

goal_relevance   WANT — relevance to currently active goals (0.0 to 1.0)
need_pressure    NEED — connection to current needs, stronger than want


### Relational Layer (Phase 4 — Dormant)

source_salience  SELF — relationship weight with the source of this observation
                        modulated by Relational Narrative history


## How Triples Emerge from the Cloud

The cloud produces triples, not just prime assignments.

A triple is the atomic unit of meaning: (compound_A, PRIME, compound_B)

When the cloud is sufficiently activated, the dominant triple pattern emerges
directly from the weighted activation without any external model:

  Most activated compound pair + most activated relational prime between them
  = triple candidate

When multiple triple candidates emerge with similar weights, the cloud is
uncertain. DeepSeek is called with the cloud as context to resolve ambiguity.

The LLM's job changes from:
  "What primes does this token probably have?"       ← guessing from nothing
to:
  "Given this activation field, which triple is correct?"  ← resolving ambiguity

Resolution is cheaper, faster, more accurate than guessing from scratch.


## Compound Deduplication

The exact_match check is the first step in cloud assembly. A token already in
KNOW is identified immediately. DATA never creates a duplicate. The cloud makes
deduplication explicit and primary rather than a hidden check inside DATA.


## Growth Over Time

The cloud improves as PABLO learns:

  Early PABLO:   sparse KNOW, thin clouds, heavy DeepSeek reliance
  Growing PABLO: richer KNOW, thicker clouds, fewer DeepSeek calls
  Mature PABLO:  dense KNOW, clouds self-sufficient, DeepSeek as exception
  
When FEEL, WANT, NEED, SELF come online, the cloud gains new dimensions without
changing the cognitive layer. Each new prime family makes grounding richer and
more contextually appropriate.


## SYMBOL Retirement

SYMBOL currently performs sequentially what the activation cloud will eventually
perform in parallel. Each step in SYMBOL's cascade is an activation cloud step:

  SYMBOL cascade today:
    KNOW exact lookup → lemmatize → family member → LLM → heuristic → placeholder

  Activation cloud assembly:
    exact_match     = KNOW exact lookup
    family_root     = lemmatize + KNOW lemma lookup
    family member   = KIND relation creation
    LLM             = DeepSeek fallback when cloud not confident
    heuristic       = prime candidate fast path
    placeholder     = low confidence unresolved node

As the cloud matures, SYMBOL's steps dissolve into cloud assembly one by one.
SYMBOL is scaffolding for an immature activation cloud. It is not permanent.

  Phase 1:  SYMBOL does heavy lifting, cloud assists
  Phase 2:  cloud handles known tokens, SYMBOL handles unknown/ambiguous
  Phase 3:  cloud handles almost everything, SYMBOL = thin edge case handler
  Phase 4:  SYMBOL retired, logic absorbed into cloud assembly
  
Final pipeline:
  Today:   READ → SYMBOL → DATA → KNOW → activation cloud → THINK
  Mature:  READ → activation cloud → THINK


## What the Activation Cloud Is Not

Not a data store — it stores nothing, borrows from KNOW and narratives.
Not a reasoning system — reasoning is THINK.
Not a search system — targeted queries, not scans.
Not persistent — exists for one token's grounding, then discarded.
Not a separate LLM — it IS the pattern recognition, not a consumer of it.


## Phase 1 Scope

  ✅ Cognitive layer assembly (exact match, family root, definition compounds)
  ✅ Utterance context (resolved siblings, utterance primebit)
  ✅ Narrative context (recent compounds, narrative primebit)
  ✅ Prime candidates (pre-activation from all cognitive sources)
  ✅ Candidate weights (multi-source agreement scoring)
  ✅ Fast path (cloud sufficient → no LLM call)
  ✅ Specialist context injection (cloud serialised into LLM prompt)
  ✅ Compound deduplication (exact match short-circuits compound creation)
  ✅ Triple emergence from dominant activation pattern

  ❌ Affective layer (FEEL) — dormant, None fields reserved
  ❌ Motivational layer (WANT, NEED) — dormant, None fields reserved
  ❌ Relational layer (SELF) — dormant, None fields reserved
  ❌ GPU parallel assembly — CPU sequential in Phase 1
  ❌ Prediction pre-activation — Phase 3+


See docs/ACTIVATION/activation_cloud_architecture.md for implementation contract.
See docs/TRIPLES/triple_concept.md for the triple format the cloud produces.
See docs/PRIMES/SYMBOL/symbol_concept.md for SYMBOL's retirement roadmap.
See docs/PRIMES/KNOW/know_concept.md for the memory sources the cloud draws from.