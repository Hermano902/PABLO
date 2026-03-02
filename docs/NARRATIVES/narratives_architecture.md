Narratives – Architecture

This document describes how Narratives are implemented. The conceptual contract lives
in NARRATIVES_CONCEPT.md; implement Narratives according to both.


1. Class Location

All Narrative data structures live in core/narrative.py. They are not primes — they are
shared data structures used by THINK (creator/operator) and KNOW (store/retrieve).

Two distinct Narrative types are defined here:

  DefinitionNarrative   — the living definition of a compound's universal meaning.
                          One per concept compound. Permanent, never closed.
                          Stored and accessed via KNOW's definition API.

  Narrative             — contextual memory. Episodic or relational.
                          Created and operated by THINK. Stored via KNOW's narrative API.

```python
# core/narrative.py
from dataclasses import dataclass, field
import time
```


2. DefinitionNarrative Data Structure

A DefinitionNarrative stores the living definition of one concept compound.
It is created by KNOW during store_batch when a new concept compound is first stored.
It is updated by KNOW.refine_definition() — never directly by any other prime.

```python
@dataclass
class DefinitionNarrative:
    id:           int           # assigned by KNOW, separate counter from compounds
    compound_id:  int           # the compound this definition belongs to
    symbol:       str           # human-language handle — for readability only
    relations:    list[dict]    # predicate → target links forming the definition
                                # each entry: {"predicate": str, "target_id": int}
    thread:       list[dict]    # ordered history of how the definition was built
                                # each entry: {"timestamp", "type", "provenance",
                                #              "primebit", "relations", "confidence",
                                #              "version"}
    constraints:  list[dict]    # definitional rules that must hold universally
                                # each entry: {"text": str, "primebit": int,
                                #              "active": bool, "asserted_at": float}
    created_at:   float = field(default_factory=time.time)
```

#### DefinitionNarrative methods

```python
def add_relation(self, predicate: str, target_id: int,
                 provenance: dict | None = None) -> None:
    """Add a new relation to the definition. Appends to thread."""
    self.relations.append({"predicate": predicate, "target_id": target_id})
    self.thread.append({
        "timestamp":  time.time(),
        "type":       "relation_added",
        "provenance": provenance or {},
        "predicate":  predicate,
        "target_id":  target_id,
    })

def update_primebit(self, primebit_value: int, confidence: float,
                    provenance: dict | None = None, version: int = 0) -> None:
    """Record a primebit refinement in the thread."""
    self.thread.append({
        "timestamp":  time.time(),
        "type":       "primebit_refined",
        "provenance": provenance or {},
        "primebit":   primebit_value,
        "confidence": confidence,
        "version":    version,
    })

def assert_constraint(self, text: str, primebit: int,
                      provenance: dict | None = None) -> None:
    """Assert a universal definitional constraint."""
    self.constraints.append({
        "text":        text,
        "primebit":    primebit,
        "active":      True,
        "asserted_at": time.time(),
        "provenance":  provenance or {},
    })
```

#### DefinitionNarrative serialisation

```python
def to_dict(self) -> dict:
    return {
        "id":          self.id,
        "compound_id": self.compound_id,
        "symbol":      self.symbol,
        "relations":   self.relations,
        "thread":      self.thread,
        "constraints": self.constraints,
        "created_at":  self.created_at,
    }

@classmethod
def from_dict(cls, d: dict) -> "DefinitionNarrative":
    n = cls(
        id=          d["id"],
        compound_id= d["compound_id"],
        symbol=      d["symbol"],
        relations=   d.get("relations", []),
        thread=      d.get("thread", []),
        constraints= d.get("constraints", []),
        created_at=  d.get("created_at", time.time()),
    )
    return n
```


3. Instance Narrative Data Structures

These structures handle contextual memory — episodic and relational Narratives.
They are unchanged from prior design.

Snap — a historical state snapshot within a Binding:

```python
@dataclass
class Snap:
    timestamp:  float
    state:      dict          # copy of Binding.current at this moment
    cause:      str | None    # human-readable cause ("Alice threw the ball")
    event_ref:  int | None    # NarrativeEvent.id that triggered this change
```

Binding — a narrative-local instance of a base Compound:

```python
@dataclass
class Binding:
    local_name:   str           # "THIS_ALICE", "THE_BALL" — unique within Narrative
    compound_id:  int           # ID of base Compound in KNOW — never modified
    current:      dict          # narrative-local property map (mutable)
    history:      list[Snap] = field(default_factory=list)

    def update(self, new_state: dict, cause: str | None = None,
               event_ref: int | None = None):
        """Append Snap of current state, then apply new_state as delta."""
        self.history.append(Snap(
            timestamp=time.time(),
            state=dict(self.current),   # snapshot before update
            cause=cause,
            event_ref=event_ref,
        ))
        self.current.update(new_state)
```

Constraint — a logical rule THINK must respect within this Narrative:

```python
@dataclass
class Constraint:
    id:           int
    text:         str           # "Alice no longer owns the ball"
    primebit:     int           # 64-bit int (PrimeBit.value) — machine form
    asserted_at:  float
    source:       str           # "user" | "inferred" | "THINK"
    active:       bool = True

    def lift(self):
        self.active = False
```

NarrativeEvent — one entry in the Narrative's timeline thread:

```python
@dataclass
class NarrativeEvent:
    id:           int
    timestamp:    float
    type:         str           # "utterance" | "response" | "state_change" | "constraint" | "action"
    compound_id:  int | None    # associated Layer 1/2/3 Compound, if any
    binding_ref:  str | None    # local_name of affected Binding, if any
    text:         str           # human-readable description
```

Narrative — the top-level container:

```python
@dataclass
class Narrative:
    id:           int = 0       # assigned by KNOW on storage
    name:         str = ""
    narrative_type: str = "episodic"   # "episodic" | "relational"
    status:       str = "open"         # "open" | "closed" | "archived"
    created_at:   float = field(default_factory=time.time)
    closed_at:    float | None = None
    bindings:     dict[str, Binding] = field(default_factory=dict)
    constraints:  list[Constraint] = field(default_factory=list)
    thread:       list[NarrativeEvent] = field(default_factory=list)
    _next_event_id: int = field(default=0, repr=False)
    _next_constraint_id: int = field(default=0, repr=False)
```


4. Narrative Methods

```python
# Binding management
def bind(self, local_name: str, compound_id: int,
         initial_state: dict | None = None) -> Binding:
    """Create and register a new Binding. Raises if local_name already exists."""
    b = Binding(local_name=local_name, compound_id=compound_id,
                current=initial_state or {})
    self.bindings[local_name] = b
    return b

def resolve(self, local_name: str) -> Binding | None:
    return self.bindings.get(local_name)

# Constraint management
def assert_constraint(self, text: str, primebit: int,
                      source: str = "THINK") -> Constraint:
    c = Constraint(id=self._next_constraint_id, text=text,
                   primebit=primebit, asserted_at=time.time(), source=source)
    self._next_constraint_id += 1
    self.constraints.append(c)
    return c

def active_constraints(self) -> list[Constraint]:
    return [c for c in self.constraints if c.active]

# Thread management
def log_event(self, type: str, text: str, compound_id: int | None = None,
              binding_ref: str | None = None) -> NarrativeEvent:
    e = NarrativeEvent(id=self._next_event_id, timestamp=time.time(),
                       type=type, compound_id=compound_id,
                       binding_ref=binding_ref, text=text)
    self._next_event_id += 1
    self.thread.append(e)
    return e

# Lifecycle
def close(self):
    self.status = "closed"
    self.closed_at = time.time()

def archive(self):
    self.status = "archived"
```


5. Narrative Serialisation

Narratives are persisted to storage/narratives.json by KNOW's autosave thread.

```python
def to_dict(self) -> dict:
    return {
        "id":             self.id,
        "name":           self.name,
        "narrative_type": self.narrative_type,
        "status":         self.status,
        "created_at":     self.created_at,
        "closed_at":      self.closed_at,
        "bindings": {
            name: {
                "local_name":  b.local_name,
                "compound_id": b.compound_id,
                "current":     b.current,
                "history":     [s.__dict__ for s in b.history],
            }
            for name, b in self.bindings.items()
        },
        "constraints": [c.__dict__ for c in self.constraints],
        "thread":       [e.__dict__ for e in self.thread],
        "_next_event_id":      self._next_event_id,
        "_next_constraint_id": self._next_constraint_id,
    }

@classmethod
def from_dict(cls, d: dict) -> "Narrative":
    n = cls()
    n.id             = d["id"]
    n.name           = d["name"]
    n.narrative_type = d.get("narrative_type", "episodic")
    n.status         = d["status"]
    n.created_at     = d["created_at"]
    n.closed_at      = d.get("closed_at")
    n._next_event_id       = d.get("_next_event_id", 0)
    n._next_constraint_id  = d.get("_next_constraint_id", 0)
    for name, bd in d.get("bindings", {}).items():
        b = Binding(local_name=bd["local_name"], compound_id=bd["compound_id"],
                    current=bd["current"],
                    history=[Snap(**s) for s in bd.get("history", [])])
        n.bindings[name] = b
    n.constraints = [Constraint(**c) for c in d.get("constraints", [])]
    n.thread      = [NarrativeEvent(**e) for e in d.get("thread", [])]
    return n
```


6. KNOW Integration

KNOW stores both DefinitionNarratives and instance Narratives in separate stores
with separate ID counters. See KNOW_ARCHITECTURE.md for full store and API details.

THINK interacts with instance Narratives exclusively through KNOW's narrative API:

```python
# THINK creates a new Narrative
narrative = Narrative(name="conversation_2026-02-22", narrative_type="episodic")
narrative = know.store_narrative(narrative)   # KNOW assigns id

# THINK resumes an open Narrative
narrative = know.narrative_by_source("gui")

# THINK updates a Narrative in place — KNOW holds the live reference
narrative.bind("THIS_ALICE", alice_compound_id, initial_state={"mood": "neutral"})
narrative.log_event("utterance", "User asked about Alice", compound_id=utterance_id)
# No re-store needed — KNOW holds a reference, autosave serialises current state
```

**Family member handling in Narrative bindings:**

When a family member compound (e.g. "ran") appears in an utterance, THINK:
1. Follows the KIND relation to find the root compound ("run")
2. Creates or resolves a binding to the root: `THIS_RUN → compound "run"`
3. Records the grammatical context in the NarrativeEvent:
   ```python
   narrative.log_event(
       "utterance", "cat ran (past tense action)",
       compound_id=utterance_id,
       binding_ref="THIS_RUN",
   )
   ```
4. The family member's grammatical primes (e.g. BEFORE for past tense) are
   recorded in the event's metadata — the binding itself stays at the root
   concept level for consistent cross-event reasoning.

This design means "the cat ran" and "the cat runs" both reference the same
RUN binding, while the tense distinction is preserved in the event thread.

SYMBOL interacts with DefinitionNarratives exclusively through KNOW's definition API:

```python
# SYMBOL enriches an existing compound's definition
know.refine_definition(
    compound_id=cat_compound_id,
    new_relations=[Relation(predicate="HAS", target_id=cat_body_compound_id)],
    updated_primebit=new_primebit,
    confidence=0.91,
    provenance={"model": "text-grounder-v1", "observation_id": "obs_123"},
)

# THINK reads a compound's full definition when needed
definition = know.get_definition(cat_compound_id)
# definition.relations → all predicate→target links
# definition.thread    → full history of how meaning was built
```

Because KNOW holds direct Python object references (not copies), instance Narrative
mutations by THINK are immediately visible to KNOW's autosave thread. The autosave
thread acquires its lock before serialising, so there is no torn-state risk.


7. Relational Narrative Bootstrap

On first startup (no narratives.json), KNOW creates the default relational Narrative
for the primary user during `_on_initialize()`:

```python
def _bootstrap_relational_narrative(self):
    n = Narrative(name="relationship_user_primary", narrative_type="relational")
    n.bind("THIS_USER", USER_COMPOUND_ID, initial_state={
        "relationship_quality": 0.0,
        "trust":                0.0,
        "curiosity":            0.2,
        "emotional_register":   "neutral",
        "last_tone":            "unknown",
        "interaction_count":    0,
        "notable_traits":       [],
    })
    self.store_narrative(n)
```

`USER_COMPOUND_ID` is the ID of the base ENTITY compound representing a generic
user — pre-seeded as a logic compound or bootstrapped on first run.


8. Compound Identity Contract

A Binding holds a `compound_id` that points to a base Compound in KNOW.
Narrative code never modifies a Compound's identity fields (`id`, `symbol`,
`created_at`) as a side effect of instance reasoning.

Narrative-local state lives entirely in `Binding.current` and `Binding.history`.

If THINK determines that a narrative-local fact is universally true and should
be promoted to the compound's definition, it calls `know.refine_definition()`
explicitly — a deliberate act with an audit trail in the DefinitionNarrative thread.
This is never a silent side effect of instance reasoning.

Phase 1: enforced by convention.
Phase 2: KNOW raises if a stored Compound with a positive ID is passed to
`know.store()` without going through `refine_definition()`.


9. Phase 1 Scope

  ✅ DefinitionNarrative dataclass (id, compound_id, symbol, relations, thread, constraints)
  ✅ DefinitionNarrative methods (add_relation, update_primebit, assert_constraint)
  ✅ DefinitionNarrative serialisation (to_dict / from_dict)
  ✅ All instance Narrative data structures (Narrative, Binding, Snap, Constraint, NarrativeEvent)
  ✅ Narrative methods (bind, resolve, assert_constraint, log_event, close, archive)
  ✅ Narrative serialisation (to_dict / from_dict, all structures)
  ✅ KNOW integration — live reference, autosave, narrative_by_source
  ✅ KNOW definition API usage (get_definition, refine_definition)
  ✅ Relational Narrative bootstrap (THIS_USER with default state)
  ✅ Episodic Narrative creation per conversation
  ❌ Constraint enforcement in THINK (Phase 2 — structures exist but not yet checked)
  ❌ History traversal reasoning (Phase 2)
  ❌ Narrative archiving / thread compression (Phase 2)
  ❌ Cross-narrative entity resolution (Phase 3)
  ❌ Compound promotion via refine_definition triggered by THINK (Phase 3)