# Propositions — Concept

## Overview

A proposition is a coherent set of triples that together express one complete
thought. It is the layer above the triple and below the narrative in PABLO's
semantic stack.

    PRIME       → atomic unit of capability/description
    TRIPLE      → (compound_A, PRIME, compound_B) — one relationship
    PROPOSITION → coherent set of triples expressing one complete thought
    NARRATIVE   → proposition anchored by THIS + TIME + SPACE

Triples are individually meaningful but not self-contained. A single triple
"(dog, FROM, bite)" says "dog is the agent of bite" — but tells you nothing
about what happened, when, to whom, or in what context. A proposition groups
all the triples that belong to one semantic event into a coherent unit.

Minimum proposition: one triple.
Typical proposition: 3-6 triples.
Maximum: no limit — but a very large proposition is usually a nested proposition
(a proposition containing proposition references as targets).


## What Counts as One Proposition

A proposition groups triples that share a common anchor compound. The anchor
is the compound that all (or most) triples in the set reference — either as
source_id or as target_id.

"The exhausted doctor ran":

    anchor: "this" (THE specific entity)

    Triples:
      (this,  BE,    doctor)     ← "this" is the anchor of all four triples
      (this,  HAVE,  exhaustion)
      (this,  DO,    run)
      (run,   WITH,  BEFORE)     ← "run" is secondary anchor for the temporal triple

All four triples orbit around the same event — one entity identified as a
doctor, in an exhausted state, performing a run action in the past.
That is one proposition.

A new proposition begins when:
- A new anchor compound is introduced (new entity/event, not part of the current set)
- A causal or conditional link bridges two separate events (CAUSE, IF, AND between propositions)
- A nested clause introduces a separate event with its own anchor


## Three Categories of Proposition

### 1. Definition Proposition

A compound's definition — what it universally IS — expressed as triples.
Stored as the compound's Definition Narrative (triple set in KNOW).

    run_definition:
      (run,  KIND,  move)       run is a kind of movement
      (run,  MORE,  walk)       more than walking
      (run,  USE,   legs)       uses legs
      (run,  WITH,  NOW)        inherently present-tense event — running happens now
      (run,  FROM,  ENTITY)     done by an entity

This proposition is universal. It does not refer to any specific instance.
It is the definition of what "run" means across all contexts.

**Definition propositions never have THIS anchor.**
**Definition propositions are never TIME or SPACE anchored.**
**They are universal truths, not events.**


### 2. Utterance Proposition

The triples extracted from a specific sentence. Produced by SYMBOL/DATA
from a perceptor observation.

    "the dog bit the man":

      Utterance proposition:
        (bite,  FROM,  dog)       dog is the agent
        (bite,  TO,    man)       man is the patient
        (bite,  WITH,  BEFORE)    past tense

This proposition is still generic — it says something about dogs biting men
in the abstract. It is not anchored to a specific dog or specific man.

**Utterance propositions may or may not have THIS anchor.**
If the user says "I bit the man" — THIS_USER is the agent. If the user says
"dogs bite men" — the proposition is generic (no THIS).


### 3. Instance Proposition (Narrative Event)

An utterance proposition that has been anchored to specific entities in
the active narrative. Produced by THINK when it assigns utterance compounds
to narrative bindings (THIS_USER, THIS_DOG, THE_MAN, etc.).

    "the dog bit the man" → in active narrative:

      Instance proposition:
        (THIS_DOG,   FROM,  bite)      THIS specific dog is the agent
        (bite,       TO,    THIS_MAN)  THIS specific man is the patient
        (bite,       WITH,  BEFORE)    past tense
        (THIS_DOG,   AT,    park_compound)    where (if known from context)
        (THIS_DOG,   WITH,  Tuesday_time)     when (if known from context)

**Instance propositions always have THIS-anchored compounds as source or target.**
**They always include temporal and/or spatial triples when known.**
**They are the basis for Narrative Events.**


## Propositions as Universal Language

The same triple structure appears at every level:

| Level | Example | Type |
|-------|---------|------|
| Definition | (run, KIND, move) | universal truth |
| Utterance | (bite, FROM, dog) | generic event |
| Instance | (THIS_DOG, FROM, bite) | specific event |
| Nested | (ask, WITH, question_proposition) | embedded proposition |

No special machinery at any level. No different grammar. The same three-element
structure (source, predicate, target) expresses every relationship in PABLO
regardless of scope or specificity.


## Completeness of a Proposition

A proposition is considered complete when all WH questions answerable from the
event are filled:

    WHO does?      FROM triple (agent)
    WHO receives?  TO triple (patient)
    WHAT is it?    BE triple (identity)
    WHAT kind?     KIND triple (category)
    WHEN?          WITH → BEFORE / NOW / AFTER triple
    WHERE?         AT triple (location)
    WHY?           CAUSE triple (linked to another proposition)
    HOW?           USE or WITH triple (instrument or manner)

A proposition is INCOMPLETE when key WH questions are unanswerable. PABLO knows
a proposition is incomplete and can ask for or infer the missing triple.

"a dog bit" — incomplete:
    (bite, FROM, dog)     — WHO does: known
    missing: TO           — WHO receives: unknown
    missing: WITH         — WHEN: unknown


## Nested Propositions

When a sentence contains an embedded clause, the inner clause becomes its own
proposition referenced by a triple in the outer proposition.

"Dumbledore asked Harry whether he put his name in the goblet":

    Outer proposition:
      (THIS_D,  BE,    Dumbledore)
      (THIS_D,  DO,    ask)
      (ask,     TO,    THIS_H)
      (ask,     WITH,  inner_proposition_id)   ← inner proposition IS the WITH target
      (ask,     WITH,  BEFORE)

    Inner proposition (what was asked):
      (THIS_H,  DO,    put)
      (put,     WITH,  name)
      (name,    OF,    THIS_H)
      (put,     TO,    goblet)
      (goblet,  OF,    fire)

The inner proposition is stored as its own Proposition record in KNOW and
referenced by ID as the target of the outer triple (ask, WITH, inner_id).

This is how PABLO handles any embedded clause, question, or reported speech —
the embedded content is a proposition, the embedding is a triple pointing to it.


## The Proposition is the Unit THINK Reasons With

THINK does not reason about individual triples. It reasons about propositions.
When SELF fires THINK about an utterance, THINK constructs or extends the
active Proposition — adding triples, resolving THIS anchors, linking to prior
propositions in the narrative thread.

"What is the proposition THINK is currently processing?" is always a well-formed,
complete thought — not a fragment.


## Propositions and the Activation Cloud

When a new sentence arrives, the activation cloud assembles candidate triples
for each compound token. The proposition is the output of the cloud's resolution:
the set of triples that won the weighted activation competition.

The activation cloud inputs: raw observation + existing KNOW triples.
The activation cloud output: a ranked list of candidate triples.
The proposition: the accepted set of triples above confidence threshold.


## Phase 1 Scope

  ✅ Proposition concept — definition, utterance, instance, nested
  ✅ Proposition as coherent set of triples with shared anchor
  ✅ WH question completeness mapping
  ✅ Definition propositions (stored as Definition Narrative triple sets)
  ✅ Utterance propositions (triples extracted from sentence — Phase 1.5)
  ✅ Nested proposition references (inner proposition as WITH target)

  ❌ Proposition data structure as a named record in KNOW — Phase 2
  ❌ Instance proposition storage (THIS-anchored) — Phase 2
  ❌ Proposition linking (CAUSE, IF between propositions) — Phase 2
  ❌ Proposition completeness scoring — Phase 2
  ❌ Cross-proposition entity resolution — Phase 3


See docs/TRIPLES/triple_concept.md for the triple definition.
See docs/TRIPLES/triple_architecture.md for triple implementation.
See docs/PROPOSITIONS/proposition_architecture.md for proposition implementation.
See docs/NARRATIVES/narratives_concept.md for narrative anchoring.
See docs/ACTIVATION_CLOUD/activation_cloud_concept.md for cloud-to-proposition pipeline.
