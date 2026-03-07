# Narratives

---

## Concept

A Compound crystallises a concept — stable, universal, not tied to any particular
experience. A Narrative is what makes it *particular*.

The Compound for `cat` is universal — the sense of "cat" in prime-space, valid across
all contexts. The Narrative is what makes it *this cat* — the one referenced between
you and PABLO, in this relationship, at this point in time.

Without Narratives, PABLO has only universals. It knows what a cat is, but not which
cat we are talking about, nor that we talked about one last Tuesday, nor how that
conversation felt.

Narratives are PABLO's memory of the particular.

---

### Three things a Narrative carries

These are the three elements that make a Narrative distinct from a collection of Triples:

**Entity bindings** — the mapping from general Compounds to specific instances.
`cat` → `this_cat_we_discussed`. `user` → `this_user`. `session` → `this_session`.
Without entity bindings there is no reference — only description.

**Thread** — the ordered sequence of Triples that constitute the history of this
particular entity, relationship, or situation. Not a summary. The actual sequence:
what was said, what was understood, what was expressed, in order.

**Relational state** — the accumulated context that colours all future interaction.
Trust level, interaction count, dominant topics, affective history. This is what SELF
reads to compute salience. PABLO's responsiveness is not a rule — it is arithmetic
on the relational state a Narrative has accumulated.

---

### What a Narrative is not

A Narrative is not a long Triple. The distinction is structural: Triples express
relations between Compounds universally. Narratives bind those relations to specific
instances in specific contexts.

`(cat) -[MOVE]→ (left)` is a Triple — it is true of any cat that moved left.
The Narrative records that *this cat*, in *session 3*, *before you asked about it*,
was what moved left — and that you seemed pleased when it did.

---

### Instance Narrative vs Definition Narrative

**Instance Narrative** — tied to a specific entity or relationship. `THIS_USER`,
`THIS_SESSION`, a specific object PABLO has been told about. This is what the word
"Narrative" refers to by default in PLanguage.

**Definition Narrative** — tied to a Compound. Not about a specific instance but about
the history of how a Compound's definition became resolved: which scenes contributed
which relations, which primes were dropped, how confidence evolved. The resolution
audit trail.

The Definition Narrative is documented in [compound.md](COMPOUND/compound.md).
It is not what this document covers.

---

### The most important Narrative: THIS_USER

In Phase 1, the primary Instance Narrative is `THIS_USER` — the relational memory
binding PABLO to its primary user. SELF reads this Narrative to decide whether a
scene warrants conscious attention.

```
THIS_USER (Instance Narrative):
  entity_bindings: {
    "user":    THIS_USER_id
  }
  relational_state: {
    relationship_quality:  float    # -1.0 → +1.0
    last_interaction:      float    # unix timestamp
    interaction_count:     int
    dominant_topics:       list[str]
    affective_history:     list[str]
  }
  thread: [NarrativeEvent, ...]    # ordered history of interactions
```

---

## Architecture

### NarrativeEvent

Each scene that involves a Narrative entity appends one NarrativeEvent to the thread:

```python
@dataclass
class NarrativeEvent:
    scene_id:       str
    timestamp:      float
    utterance_id:   int             # utterance Compound from that scene
    prime_field:    dict            # dominant primes in that scene
    outcome:        str             # "conscious" | "archived"
    response_id:    int | None      # THINK's intent Compound, if formed
```

The thread is not a summary. It is the actual sequence of events. THINK walks this
thread when reasoning requires historical context — "you said earlier...", "the last
time this came up...", "the third time you mentioned this...".

### Narrative lifecycle

```
Scene opens
  → KNOW checks: is there an Instance Narrative for this source?
      Yes → load relational_state into scene; thread is available for THINK
      No  → create new Instance Narrative (fresh relationship)

Scene closes (SAY has expressed response)
  → Append NarrativeEvent to thread
  → Update relational_state (relationship_quality, last_interaction, etc.)
  → KNOW persists updated Narrative to disk
```

### How Narratives interact with the scene

**SELF reads** `relational_state.relationship_quality` to compute salience.
**THINK reads** the `thread` to resolve references and build on prior context.
**SAY updates** the Narrative when a scene closes — the response becomes part of
the thread.
**KNOW stores** all Narratives and surfaces the relevant ones into each scene.

### Persistence

Narratives are stored in KNOW as `narratives.json`. They persist across sessions —
a Narrative for THIS_USER accumulates across all conversations. This is PABLO's
long-term relational memory.

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | THIS_USER Instance Narrative: relational_state + thread |
| 1 | NarrativeEvent appended per scene close |
| 1 | SELF reads relational_state for salience computation |
| 2 | THINK walks thread for reference resolution and context |
| 2 | Multiple Instance Narratives (topics, objects, other entities) |
| 4 | Affective history in relational_state populated by FEEL |
| 5 | WANT reads dominant_topics for goal relevance computation |

---

*See [compound.md](COMPOUND/compound.md) for Definition Narratives (Compound resolution audit trail).*
*See [triples.md](TRIPLES/triples.md) for the Triple layer Narrative threads are built from.*
*See [know.md](../../PRIMES/KNOW/know.md) for Narrative storage and retrieval.*
*See [self.md](../../PRIMES/SELF/self.md) for how SELF reads Narratives for salience.*
*See [think.md](../../PRIMES/THINK/think.md) for how THINK walks Narrative threads.*
