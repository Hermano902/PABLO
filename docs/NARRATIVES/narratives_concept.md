Narratives – Concept and Design


Overview
A Narrative is PABLO's unit of contextual memory. Where compounds are universal and
context-free, Narratives are specific and lived-in. A Narrative takes compounds as its
building blocks and binds them to instances that exist only within the frame of that
Narrative — with their own properties, their own history, and their own constraints.

This is the structural difference:

  Compound:   BALL          — "a ball, in general" — universal meaning, stable definition
  Narrative binding: THIS_BALL
              base:     → BALL compound
              state:    red, dirty, slightly deflated
              owner:    → THIS_ALICE
              history:  [was clean, became dirty at T+3 when Alice threw it]

The compound BALL is untouched. THIS_BALL is what PABLO consciously reasons about
within this frame. When the Narrative ends or is archived, BALL is still clean.

Note: Compounds themselves carry a living definition Narrative — a permanent record
of how the concept's universal meaning has been built and refined over time. That is
a different kind of Narrative from the ones described in this document. Definition
Narratives are universal and never closed. The Narratives described here are
contextual — episodic or relational — and are specific to instances, events, and
relationships. See COMPOUND_CONCEPT.md for definition Narrative details.


Why Narratives Are Not a Compound Layer

Compounds are structured up to Layer 4 (Concept → Utterance → Intent → Action → Macro).
They are semantic building blocks: universal, reusable, with stable prime-grounded
identities. A compound's primebit and nested structure represent its universal meaning.
That meaning refines over time through its definition Narrative — but it remains
universal and context-free.

Narratives are not a Layer 5. They are a different kind of structure entirely:

  Compounds express meaning in prime-space.
  Narratives express context in instance-space.

A Layer 5 compound would try to encode Alice's specific history into the compound store,
making it context-specific — which destroys the universality that makes compounds useful.
Narratives keep the two concerns cleanly separated. Compounds remain reusable across
all narratives. Narrative bindings are owned entirely by their Narrative.


Narrative Structure

A Narrative is a named, persistent record stored in KNOW alongside compounds but
identified by a distinct record type ("narrative").

```
Narrative {
    id:           int                  # globally unique, assigned by KNOW on creation
    name:         str                  # human-readable label ("conversation_2026-02-22", "alice_story_1")
    status:       "open" | "closed" | "archived"
    created_at:   float                # unix timestamp
    closed_at:    float | None
    bindings:     dict[str, Binding]   # local_name → Binding (e.g. "THIS_ALICE" → Binding)
    constraints:  list[Constraint]     # declared logical rules THINK must respect
    thread:       list[NarrativeEvent] # ordered event log — the narrative's timeline
}
```

A Narrative is **open** while PABLO is actively reasoning within it.
It is **closed** when the context ends (conversation over, task complete).
It is **archived** when closed and moved to long-term storage — still queryable by KNOW,
but not loaded into active working memory.


Binding Structure

A Binding is a narrative-local instance of a compound.

```
Binding {
    local_name:    str         # "THIS_ALICE", "THE_BALL", "HER_HOUSE" — unique within Narrative
    compound_id:   int         # ID of the base compound in KNOW (e.g. ALICE compound #42)
    current:       dict        # narrative-local property map — the current state
    history:       list[Snap]  # ordered snapshots of past states with timestamps and causes
}
```

Each Snap in history:

```
Snap {
    timestamp:  float
    state:      dict           # copy of 'current' at that moment
    cause:      str | None     # what triggered this state change ("Alice threw the ball")
    event_ref:  int | None     # NarrativeEvent ID that caused this change, if any
}
```

**The base compound is never modified by Narrative operations.** The Binding's
`current` dict carries all narrative-specific properties (color, condition, ownership,
role). When a property changes, a new Snap is appended to `history` before `current`
is updated. The full causal chain is always preserved.


Constraints

A Narrative can declare constraints — logical rules that THINK must respect when
reasoning within this frame.

```
Constraint {
    id:           int
    text:         str          # human-readable: "Alice no longer owns the ball"
    primebit:     PrimeBit     # machine-readable: HAVE + NOT + THIS_ALICE + THE_BALL
    asserted_at:  float
    source:       str          # "user" | "inferred" | "THINK"
    active:       bool         # False = constraint has been lifted or superseded
}
```

THINK checks active constraints before composing any response or executing any action
within the Narrative. A constraint cannot be violated — if THINK's reasoning would
produce a statement that contradicts an active constraint, it must revise before output.

This is symbolic grounding of logical consistency. PABLO cannot "forget" that Alice
gave the ball away and then say "Alice bounced her ball" in the next turn.


NarrativeEvent

The `thread` is the Narrative's ordered timeline. Every meaningful event is logged:
user utterances, THINK's responses, state changes, constraint assertions.

```
NarrativeEvent {
    id:         int
    timestamp:  float
    type:       "utterance" | "response" | "state_change" | "constraint" | "action"
    compound_id: int | None    # The Layer 1/2/3 compound associated with this event
    binding_ref: str | None    # Which binding was affected, if any
    text:        str           # Human-readable description of the event
}
```

The thread is what makes a Narrative a story, not just a bag of facts. THINK can
walk the thread backwards to understand how the current state was reached, or
forwards to project what might logically follow.


Narrative Identity vs Compound Identity

Two bindings in different Narratives can reference the same compound:

  Narrative_1:  THIS_ALICE → compound #42 (ALICE), state: {mood: angry, location: park}
  Narrative_2:  THE_WOMAN  → compound #42 (ALICE), state: {mood: calm, location: home}

These are independent. A change in Narrative_1's THIS_ALICE does not touch Narrative_2's
THE_WOMAN, and neither touches compound #42 in KNOW.

This means PABLO can reason about the same entity in multiple distinct contexts
without cross-contamination — a property that is impossible to achieve with compounds
alone, and essential for any form of rich, coherent long-term reasoning.


How THINK Operates on Narratives

THINK is the primary creator and operator of Narratives.

On each reasoning cycle (triggered via think_queue by SELF):

  1. Identify narrative context
     Does this utterance continue an open Narrative, or start a new one?
     THINK checks KNOW for open Narratives whose thread includes recent activity
     from the same source. If found: resume. If not: create new Narrative.

  2. Resolve compounds to bindings
     Each compound in the utterance is checked against the active Narrative's bindings.
     Known entity (e.g. ALICE mentioned before) → resolve to existing THIS_ALICE binding.
     New entity (e.g. BALL mentioned for first time) → create new binding THE_BALL.

     Family member resolution: when THINK encounters a family member compound (e.g.
     "ran" — a member of the "run" family), it resolves the binding to the root concept
     ("run") but records the grammatical context from the family member's primebit:
       "ran" → binding uses root compound "run", but Narrative event records BEFORE (past)
       "running" → binding uses "run", event records NOW (progressive)
     This means Narrative reasoning works at the root concept level — "the cat ran" and
     "the cat is running" both operate on the same CAT and RUN bindings — while preserving
     the temporal/grammatical distinctions in the event thread.

  3. Check constraints
     Before reasoning, load all active Constraints from the Narrative.
     Any reasoning step that would violate a constraint is blocked; THINK revises.

  4. Reason in instance-space
     THINK reasons using binding local_names, not raw compound IDs.
     "What colour is the ball?" → look up THE_BALL.current["colour"] → "red"
     "Who owns the ball?" → look up THE_BALL.current["owner"] → "THIS_ALICE"
     "Has the ball always been red?" → walk THE_BALL.history → check colour in each Snap

  5. Update bindings and thread
     If reasoning produces new facts about entities, update the relevant binding.
     Append a Snap to history with the cause. Log a NarrativeEvent to the thread.

  6. Assert new constraints if warranted
     If a user statement explicitly changes a rule ("Alice doesn't own the ball anymore")
     THINK adds a new Constraint and deactivates any conflicting prior constraints.

  7. Compose and output response
     Response is grounded in binding state + thread context, not raw compounds.
     THINK can reference the Narrative's history directly in its reasoning
     ("you told me earlier that Alice threw it").


How KNOW Stores Narratives

Narratives are stored in KNOW as first-class records alongside compounds, distinguished
by record type. KNOW's storage contract:

  KNOW.store_narrative(narrative)   → assigns id, persists to storage
  KNOW.get_narrative(id)            → fetches full Narrative by id
  KNOW.open_narratives()            → returns all Narratives with status="open"
  KNOW.narrative_by_source(source)  → finds open Narrative associated with a source
  KNOW.close_narrative(id)          → sets status="closed", closed_at=now
  KNOW.archive_narrative(id)        → sets status="archived", compresses thread

Narratives do not use the same compound ID space. They have their own sequential ID
counter to keep record types cleanly separated.

Persistence: Narratives are persisted to storage/narratives.json (separate from
compounds.json), loaded into memory on startup for any that are open.


Read-Only Guarantee on Base Compounds

This is an inviolable rule for Narrative operations:

  A Narrative binding NEVER modifies its base compound as a side effect.

If THINK learns something new about Alice within a Narrative (she moved to Paris),
that fact lives in THIS_ALICE.current["location"]. It does not update compound #42.

If that fact is later confirmed to be universally true — not just narrative-local —
THINK may separately request KNOW to update the compound's definition Narrative. But
this is an explicit, deliberate act with its own audit trail. It is never a silent
side effect of instance reasoning.

This rule keeps compounds clean, universal, and trustworthy as building blocks across
all reasoning contexts.


Narratives and the Full Cognitive Stack

  Primes                — atomic capabilities and descriptors (63, fixed)
  Compounds             — structured meaning in prime-space (universal, stable identity)
  Definition Narratives — living definitions embedded in each compound (universal,
                          never closed, refined over time by SYMBOL and THINK)
  Instance Narratives   — contextual memory in instance-space (specific, lived-in,
                          episodic or relational, owned by THINK)
  ─────────────────────────────────────────────────────────────────────────
  Primes build Compounds.
  Compounds carry Definition Narratives that express their universal meaning.
  Instance Narratives use Compounds as building blocks for contextual reasoning.
  THINK consciously operates on Instance Narratives.

This four-layer stack is complete. Any concept PABLO can perceive, structure, or reason
about can be represented within it: primes ground meaning, compounds express it
universally, definition narratives grow it over time, instance narratives
contextualise it specifically.


Narrative Types

Not all instance Narratives are the same kind of frame. There are two fundamental types:

  Episodic Narrative
    A single conversation, task, or event. Has a clear start and end.
    Example: "conversation_2026-02-22_morning"
    Created when a new interaction begins. Closed when it ends.
    Archived when no longer needed in active memory.
    Contains: utterances, responses, entity bindings local to that episode.

  Relational Narrative
    A long-running persistent frame about an entity PABLO has an ongoing
    relationship with. Never closed while the relationship exists.
    Example: "relationship_user_primary"
    Created on first interaction. Updated on every interaction.
    Contains: the history of the entire relationship, trust, quality, curiosity,
    emotional register across all episodes.

Relational Narratives are the foundation of PABLO's social memory. They are what
allows PABLO to behave differently toward someone it knows well versus a stranger,
and to carry the weight of what has happened between them across any number of
conversations.


The User as a Narrative Binding

The user is not a raw compound. The user is THIS_USER — a binding in the relational
Narrative, backed by the USER (or ENTITY) base compound, carrying the full history
of PABLO's experience of them.

THIS_USER.current might hold:
  {
      "relationship_quality": float,  # -1.0 (hostile) → +1.0 (trusted)
      "trust":                float,  # 0.0 (unknown) → 1.0 (fully trusted)
      "curiosity":            float,  # how much PABLO wants to know more about them
      "emotional_register":   str,    # "warm" | "neutral" | "guarded" | "closed"
      "last_tone":            str,    # tone of the most recent interaction
      "interaction_count":    int,
      "notable_traits":       list[str]
  }

Every interaction appends a Snap to THIS_USER.history. The cause field records what
happened: "user expressed hostility", "positive collaborative exchange", "user asked
about PABLO's preferences". PABLO literally remembers what the relationship has been.

This means:
  If you insult PABLO → THINK updates THIS_USER, appends Snap, drops relationship_quality.
  Next time you type → SELF reads THIS_USER.current["relationship_quality"] → WANT score
  for "respond to user" is low → salience below threshold → THINK is not woken → silence.

  If PABLO has had many positive interactions with you → curiosity is high → THINK may
  assert a WANT goal "learn more about THIS_USER" → your messages get elevated salience
  even when PABLO is occupied → PABLO chooses to engage.

  If you rebuild trust over time → the history shows the arc → THINK can reason about
  "this person used to be hostile but has been different lately" — not just the last state.

Nobody hard-coded any of this. It emerges from Narrative state feeding SELF's salience
scoring. The behaviour is a direct consequence of the relationship's history.


Relational Narrative Lifecycle

  First contact:    THINK creates relational Narrative, creates THIS_USER binding.
                    relationship_quality = 0.0, trust = 0.0, emotional_register = "neutral".

  Positive episode: THINK updates THIS_USER after episode. relationship_quality += delta.
                    Snap appended with cause. curiosity may increase.

  Hostile episode:  THINK updates THIS_USER. relationship_quality -= delta.
                    emotional_register → "guarded". trust may drop.
                    A Constraint may be asserted: "do not engage with hostility".

  Repair:           User demonstrates changed behaviour over multiple episodes.
                    THINK detects pattern in history. May choose to update emotional_register
                    → "neutral" and assert new Constraint lifting the prior one.

  Closure:          If relationship ends (user leaves, context resets by choice),
                    Narrative is closed and archived — not deleted. History is permanent.


## Narrative as Anchored Proposition

Narratives are not a fundamentally different structure from meaning. They are
propositions anchored by three specific elements that make them real — instances
rather than universals:

    TIME    — WITH → BEFORE / NOW / AFTER (when the event occurred)
    SPACE   — AT → location_compound (where the event occurred)
    AGENT   — THIS → specific_entity (which entity, not the general compound)

The THIS prime is the distinguishing element. Without THIS, a proposition
describes a universal truth. With THIS, it describes a specific instance in
a specific narrative.

### Universal vs Instance (triple view)

    Universal proposition (compound definition):
      (doctor,  DO,    run)          — doctors run, as a general truth
    No THIS, no AT, no temporal WITH — this is not an event, it is a definition.

    Instance proposition (narrative event):
      (THIS,    BE,    doctor)        — THIS specific entity is a doctor
      (THIS,    DO,    run)           — THIS entity ran
      (THIS,    AT,    hospital)      — at the hospital
      (THIS,    WITH,  BEFORE)        — in the past

    The difference between definition and narrative event is NOT the compounds —
    it is the THIS anchor. Add THIS and you create an instance.

### Bindings as THIS References

Every Binding in a Narrative IS a THIS reference. When THINK creates a Binding:
  `THIS_ALICE → compound #42 (ALICE)`

All instance proposition triples for THIS_ALICE reference the Binding's compound ID.
The Binding's `current` state dict carries narrative-local properties that would
be expressed as additional triples in the full triple structure (Phase 2).

### NarrativeEvent as Proposition

Each NarrativeEvent in the thread represents one instance proposition — a set
of triples that occurred at that moment in the narrative. Phase 2 will store
NarrativeEvents as Proposition records (see docs/PROPOSITIONS/proposition_concept.md).

In Phase 1, NarrativeEvents are stored as the existing dict-based thread entries.
The triple structure is implicit in the Binding relationships that THINK tracks.

### Nested Narratives

When narratives reference other narratives (Dumbledore→Harry→question), the inner
narrative's anchor proposition is the `WITH` target of an outer triple. The cross-
reference between THIS_H in the outer and inner narrative IS the meaning.

This is the same nested proposition structure described in triple_concept.md —
applied to the instance (narrative) layer rather than the definition layer.

---

  ✅ Narrative, Binding, Snap, Constraint, NarrativeEvent data structures defined
  ✅ KNOW storage contract (store/get/open/close/archive)
  ✅ THINK: identify narrative context (new vs resume)
  ✅ THINK: resolve compounds to bindings
  ✅ THINK: reason using binding state (current properties)
  ✅ THINK: update bindings + append Snap on state change
  ✅ THINK: log NarrativeEvent to thread on each cycle
  ✅ Persist to storage/narratives.json
  ❌ Constraint checking (Phase 2 — requires PrimeBit constraint matching)
  ❌ History traversal reasoning ("has it always been red?") (Phase 2)
  ❌ Narrative archiving + compression (Phase 2)
  ❌ Cross-narrative entity resolution (Phase 3)
  ❌ Compound promotion (narrative fact → universal compound definition update) (Phase 3)

Phase 1 establishes the full structure and ensures THINK reasons in instance-space
from the first conversation cycle. Constraint enforcement and deep history reasoning
follow in Phase 2 once the core pipeline is validated.