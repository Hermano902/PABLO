# Narratives — Concept

*PABLO's contextual memory. The temporal thread of experience.*

---

## What a Narrative Is

A Compound crystallises a concept — stable, universal, not tied to any particular
experience. A Narrative is different: it instantiates concepts within a specific
lived context. It is the ongoing story of a relationship, a topic, or a situation
as PABLO has experienced it.

The distinction:
- **Compound**: `"move"` — the concept, universal, unchanging
- **Narrative**: `THIS_USER's relationship with PABLO` — the lived thread, personal,
  evolving with every scene

Primes are the vocabulary. Compounds are the words. Narratives are the memory.

---

## Two Kinds of Narrative

### Definition Narrative
One per Compound. Created by DATA when a Compound is first crystallised. Records how
PABLO came to understand this concept — what primes were assigned, in which scenes,
with what confidence.

Every time a scene includes this concept and refines its prime assignment, the Definition
Narrative is updated. It is the accumulated evidence for what this concept means in
PABLO's prime vocabulary.

The Definition Narrative is consulted by THINK when reasoning about a concept and by
SYMBOL when a token might be disambiguated by prior context.

### Instance Narrative
One per ongoing relationship or situation. Not tied to a single concept — tied to a
specific entity, relationship, or situation as it unfolds over time.

The most important in Phase 1: **THIS_USER** — the relational narrative binding for
the primary user of the system. SELF reads this to compute salience.

```
THIS_USER (Instance Narrative):
  current: {
    relationship_quality:  float  # -1.0 → +1.0
    last_interaction:      float  # unix timestamp
    interaction_count:     int
    dominant_topics:       list[str]
    affective_history:     list[str]
  }
  thread: [NarrativeEvent, ...]   # ordered history of interactions
```

Each scene that involves THIS_USER appends a NarrativeEvent to the thread. Over time,
the thread becomes PABLO's lived memory of the relationship.

---

## Narrative Events

A NarrativeEvent is a snapshot of one scene's contribution to a Narrative:

```python
@dataclass
class NarrativeEvent:
    scene_id:       str
    timestamp:      float
    utterance_id:   int       # the utterance Compound from that scene
    prime_field:    dict      # dominant primes in that scene
    outcome:        str       # "conscious" | "archived"
    response_id:    int | None  # THINK's intent Compound, if formed
```

The thread is PABLO's temporal memory — not a summary, but the actual sequence of
events. THINK walks this thread when reasoning requires historical context.

---

## Narrative and the CognitiveScene

Every closed CognitiveScene contributes to one or more Narratives:

- The utterance_id and prime_field from the scene's memory layer → appended to
  THIS_USER's Narrative thread
- If THINK formed an intent, the intent_id → recorded in the NarrativeEvent
- SAY's expressed response → crystallised as a Compound and appended to the
  SymbolicScene's narrative_thread (PABLO's inner-voice record of what it said)

The Narrative is how scenes accumulate into long-term memory. Each scene is ephemeral;
the Narrative is permanent.

---

## Why Narratives Matter

**For SELF:** The relationship_quality field in THIS_USER's Narrative directly shapes
salience computation. PABLO's responsiveness is not a rule — it is the arithmetic
consequence of relationship history.

**For THINK:** Narrative context is how THINK resolves pronouns, tracks topic continuity,
and deepens its understanding across multiple scenes. "You said earlier..." is Narrative
walking.

**For the crystallisation loop:** Each scene that updates a Definition Narrative is a
refinement cycle. The concept's prime assignment is tested against new context,
confirmed or challenged, and the accumulated evidence grows.

**For the SymbolicScene:** The narrative_thread in the SymbolicScene channel is PABLO's
native-language record of what was said and understood. When this thread becomes rich
enough to capture the scene's meaning without the MetaScene scaffold, PABLO is thinking
in its own language about its own experiences.

---

*See `docs/COMPOUND/compound_concept.md` for what Narratives contain.*
*See `docs/PRIMES/KNOW/know_concept.md` for Narrative storage and retrieval.*
*See `docs/PRIMES/SELF/self_concept.md` for how SELF reads Narratives for salience.*
*See `docs/PRIMES/THINK/think_concept.md` for how THINK walks Narratives.*
