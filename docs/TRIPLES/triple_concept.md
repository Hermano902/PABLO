# Triples and Propositions — Concept

## Overview

The triple is the atomic unit of meaning in PABLO. Every relationship between
any two concepts — whether inside a compound definition, between compounds in
a sentence, or anchoring an event in a narrative — is expressed as a triple.

A triple is always exactly this shape:

    (compound_A,  PRIME,  compound_B)

Two compounds and the prime relation that connects them. No exceptions.
No special cases for grammar, tense, clause type, or language. The same
structure everywhere.

This document covers triples, propositions (sets of triples), and narratives
(propositions anchored in existence). Together these three levels form PABLO's
complete semantic layer — the layer between raw compound knowledge and lived
experience.


## The Triple

### Shape

    (compound_A,  PRIME,  compound_B)

compound_A   —  the source compound (permanent KNOW ID or prime name)
PRIME        —  one of the 63 primes, acting as the relation predicate
compound_B   —  the target compound (permanent KNOW ID or prime name)

The prime is always the middle element. It governs the relationship.
compound_B can be another compound OR a prime used as a terminal value.

Examples:
    ("running",   KIND,    "run")        family relation — running is a kind of run
    ("running",   WITH,    NOW)          tense — running happens now
    ("doctor",    HAS,     "exhaustion") state attribution
    ("bite",      FROM,    "dog")        agent — dog initiates bite
    ("bite",      TO,      "man")        patient — man receives bite
    ("bite",      WITH,    BEFORE)       time — bite happened before now
    ("run",       MORE,    "walk")       comparison — run is more than walk
    ("run",       USE,     "legs")       instrument — run uses legs


### The Prime as Predicate

Any of the 63 primes can act as a relation predicate. The prime's meaning
determines the nature of the relationship:

  Structural:   KIND, PART, BE, HAVE, WITH, FROM, TO, AT, IN
  Action:       DO, MAKE, MOVE, CHANGE, USE, SAY, WRITE, OPEN
  Causal:       CAUSE, BECAUSE
  Temporal:     BEFORE, AFTER, NOW, LAST, TIME
  Spatial:      HERE, NEAR, FAR, UP, DOWN, LEFT, RIGHT, BETWEEN, SIDE, AT
  Modal:        CAN, WANT, NEED
  Evaluative:   GOOD, BAD, MORE, LESS
  Perceptual:   SEE, HEAR, TOUCH, FEEL
  Cognitive:    THINK, KNOW, SYMBOL

Some primes appear as terminal targets rather than predicates:
  ENTITY, BODY, LIFE, SELF, YOU, OTHER, THIS
  ONE, MANY, ALL, SOME, NONE
  LIGHT, HEAT, NOW, BEFORE, AFTER


### Logic Compounds as Predicates

The 10 logic compounds (IDs 100-199) can also appear as predicates:
  IF, AND, OR, NOT, XOR, NAND, NOR, XNOR, TRUE, FALSE

These operate on propositions, not just compounds:
  (proposition_0,  IF,   proposition_1)    — if P1 then P0
  (triple_A,       AND,  triple_B)         — both relations hold
  (triple_A,       NOT,  triple_B)         — first holds, second does not


### WH Question Mapping

Every WH question maps to a prime predicate in the triple:

  WHO acts        FROM     ("bite", FROM, "dog")
  WHO receives    TO       ("bite", TO, "man")
  WHAT is it      BE       ("this", BE, "doctor")
  WHAT kind       KIND     ("running", KIND, "run")
  WHAT part       PART     ("finger", PART, "hand")
  WHEN            WITH     ("bite", WITH, BEFORE)
  WHERE           AT       ("run", AT, "hospital")
  WHY (cause)     CAUSE    ("run", CAUSE, "fear")
  WHY (purpose)   WANT     ("build", WANT, "shelter")
  HOW (manner)    WITH     ("run", WITH, "quickly")
  HOW (instrument)USE      ("run", USE, "legs")
  HOW MANY        MANY/ONE ("dogs", WITH, MANY)
  WHICH specific  THIS     ("this", BE, "doctor")

If the prime set cannot express a relationship, that is a signal that a
prime may be missing or that the relationship should be decomposed into
multiple triples.


## The Proposition

A proposition is a coherent set of triples that together express one
complete thought. The triples in a proposition share at least one compound
(typically the core concept being described).

Minimum proposition: one triple.
Typical proposition: 3-6 triples.

### Example: "the exhausted doctor ran"

    Proposition:
      ("this",    BE,    "doctor")       ← what entity
      ("this",    HAS,   "exhaustion")   ← state
      ("this",    DO,    "run")          ← action
      ("run",     WITH,  BEFORE)         ← when

The proposition is complete when all WH questions about the event are
answerable from its triples:
  WHO ran?      this (a doctor)
  WHAT did?     ran
  WHAT state?   exhausted
  WHEN?         before (past)
  WHERE?        not specified — proposition is incomplete on location


### Compound Definitions as Propositions

A compound's definition IS a proposition. The triples that define what
"run" universally is:

    run_definition:
      ("run",  KIND,  "move")         run is a kind of movement
      ("run",  MORE,  "walk")         more than walking
      ("run",  USE,   "legs")         using legs
      ("run",  WITH,  FAST)           quickly
      ("run",  FROM,  ENTITY)         done by an entity

This is stored as the compound's Definition Narrative in KNOW. The same
triple format. The same prime relations. Compound definitions and utterance
propositions are the same structure at different scopes.


### Inflection Definitions as Propositions

Inflected forms are their own compounds with their own definition propositions:

    running_definition:
      ("running",  KIND,   "run")     running is a kind of run
      ("running",  WITH,   NOW)       happening now (progressive)

    ran_definition:
      ("ran",      KIND,   "run")     ran is a kind of run
      ("ran",      WITH,   BEFORE)    happened before (past)

The inflection information is baked into the compound definition as triples.
At utterance level, the proposition may reinforce or specify further.


### Nested Propositions

Complex sentences contain multiple propositions linked by prime relations.

"The dog bit the man because it was hungry":

    Proposition 0 (main event):
      ("bite",    FROM,   "dog")
      ("bite",    TO,     "man")
      ("bite",    WITH,   BEFORE)

    Proposition 1 (cause):
      ("dog",     HAS,    "hunger")
      ("hunger",  WITH,   BEFORE)

    Link:
      (proposition_0,  CAUSE,  proposition_1)

"Because" is not a word to be grounded — it is a proposition link.
The CAUSE prime expresses the relationship between the two propositions.


## The Narrative

A narrative is a proposition anchored in existence by three elements:

    TIME    — when it happened or is happening
    SPACE   — where it happened or is happening
    AGENT   — which specific entity (THIS, not the general compound)

Without anchoring, a proposition is a universal truth (a definition).
With anchoring, it becomes a specific event (an instance).

### Universal vs Instance

    Universal:  ("doctor",  DO,   "run")      — doctors run in general
                                               — this is a definition

    Instance:   ("THIS",    BE,   "doctor")   — THIS specific entity
                ("THIS",    DO,   "run")      — THIS entity ran
                ("THIS",    AT,   "hospital") — here
                ("THIS",    WITH, BEFORE)     — then
                                               — this is a narrative event

The THIS prime is the anchor. It converts a general compound reference
into a specific instance. THIS is what makes the difference between
"doctors run" (universal) and "the doctor ran" (instance).


### Narrative as Linked Propositions

A full narrative is multiple propositions linked in time and space:

"Dumbledore asked Harry: Did you put your name in the goblet of fire?"

    Outer narrative:
      ("THIS_D",   BE,    "Dumbledore")
      ("THIS_D",   DO,    "ask")
      ("ask",      TO,    "THIS_H")
      ("ask",      WITH,  question_proposition)   ← the question IS a compound
      ("ask",      WITH,  BEFORE)

    Inner narrative (the question — nested inside ask's WITH relation):
      ("THIS_H",   DO,    "put")                  ← "you" = Harry, cross-reference
      ("put",      WITH,  name_compound)
      (name_compound, OF, "THIS_H")               ← Harry's name
      ("put",      TO,    goblet_compound)
      (goblet_compound, OF, fire_compound)

The cross-reference between outer and inner narrative (THIS_H appears in both)
IS the meaning. Without it "you" is unresolved.


## The Full Stack

    PRIME
      atomic irreducible concept (63 fixed)
      ↑ combine as predicate + target
    TRIPLE
      (compound_A, PRIME, compound_B)
      atomic unit of meaning
      ↑ coherent set sharing a compound
    PROPOSITION
      set of triples expressing one complete thought
      compound definitions ARE propositions
      inflection definitions ARE propositions
      ↑ anchored by THIS + TIME + SPACE
    NARRATIVE
      proposition made real by specific instance anchors
      ↑ linked over time
    STORY
      connected narratives (Phase 3+)

The same triple structure appears at every level. No special machinery
at any level. No exceptions.


## What This Means for the LLM

The LLM's job (DeepSeek in Phase 1, activation cloud in maturity) is:

  Given a sentence or phrase and an activation cloud:
  1. Identify what compounds are present
  2. Identify the prime relation between each pair
  3. Output triples

Not: parse English grammar
Not: identify subject/verb/object
Not: handle special cases for tense, voice, modality

Just: what are the compound pairs and what prime connects each pair?

The grammar categories (subject, object, tense, voice, aspect) are not
PABLO's concern. They are English's encoding choices. PABLO extracts
the underlying prime-space triples and discards the grammatical machinery.

English: "The man was bitten by the dog"    (passive voice)
English: "The dog bit the man"              (active voice)
PABLO:   identical triples in both cases:
           ("bite", FROM, "dog")
           ("bite", TO,   "man")
           ("bite", WITH, BEFORE)

Voice does not exist in prime space. Only relationships exist.


## Triples and the Activation Cloud

Every stored triple makes future activation clouds richer.

When "bite" arrives in a new sentence:
  The cloud fetches bite_compound's definition triples
  Those triples activate FROM, TO, WITH, BEFORE as candidate primes
  The cloud also activates what appeared before "bite" in this sentence
  The dominant triple pattern emerges from the weighted activation

The triple store is not just storage — it IS the activation cloud's
memory. Every triple stored is a connection in the semantic graph that
the cloud traverses when assembling activation patterns.


## Phase 1 Scope

  ✅ Triple data structure (source_id, predicate, target_id)
  ✅ Triple storage in KNOW (alongside compound definitions)
  ✅ Definition proposition (compound definition as set of triples)
  ✅ Inflection triples (KIND + grammatical primes)
  ✅ Utterance proposition (triples extracted from sentence)
  ✅ Logic compound predicates (IF, AND, NOT, etc. as triple predicates)
  ✅ THIS anchoring for instance propositions
  ✅ WH question mapping (every WH maps to a prime predicate)

  ❌ Narrative anchoring (TIME/SPACE/AGENT instance storage) — Phase 2
  ❌ Nested narrative cross-references — Phase 2
  ❌ Proposition linking (CAUSE, AND between propositions) — Phase 2
  ❌ Story-level connected narratives — Phase 3+


See docs/TRIPLES/triple_architecture.md for implementation contract.
See docs/ACTIVATION_CLOUD/activation_cloud_concept.md for how triples feed the cloud.
See docs/NARRATIVES/narratives_concept.md for narrative anchoring.
See docs/COMPOUND/compound_concept.md for compound definition propositions.
See core/logic_compounds.json for the 10 logic compound predicates.
