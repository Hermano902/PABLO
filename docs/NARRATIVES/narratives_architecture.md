Narratives – Architecture

This document describes how Narratives are implemented. The conceptual contract lives in CONCEPT.md;
implement Narratives according to both.


1. Class Location

All Narrative data structures live in core/narrative.py. They are not primes — they are
shared data structures used by THINK (creator/operator) and KNOW (store/retrieve).

```python
# core/narrative.py
from dataclasses import dataclass, field
import time
```


2. Data Structures

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

Constraint — a logical rule THINK must respect:

```python
@dataclass
class Constraint:
    id:           int
    text:         str           # "Alice no longer owns the ball"
    primebit:     int           # 64-bit int (PrimeBit.to_int()) — machine form
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


3. Narrative Methods

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


4. Serialisation

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


5. KNOW Integration

KNOW stores Narratives in a separate store with a separate ID counter (see KNOW/ARCHITECTURE.md).
THINK interacts with Narratives exclusively through KNOW's narrative API:

```python
# THINK creates a new Narrative
narrative = Narrative(name="conversation_2026-02-22", narrative_type="episodic")
narrative = know.store_narrative(narrative)   # KNOW assigns id

# THINK resumes an open Narrative
narrative = know.narrative_by_source("gui")

# THINK updates a Narrative in place — KNOW holds the live reference
narrative.bind("THIS_ALICE", alice_compound_id, initial_state={"mood": "neutral"})
narrative.log_event("utterance", "User asked about Alice", compound_id=utterance_id)
# No re-store needed — KNOW holds a reference, autosave serialises the current state
```

Because KNOW holds a direct Python object reference (not a copy), Narrative mutations
by THINK are immediately visible to KNOW's autosave thread. The autosave thread acquires
`_lock` before serialising, so there is no torn-state risk.


6. Relational Narrative Bootstrap

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

`USER_COMPOUND_ID` is the ID of the base ENTITY compound representing a generic user —
pre-seeded as a logic compound or bootstrapped on first run.


7. Immutability of Base Compounds

A Binding holds a `compound_id` that points to a base Compound in KNOW.
Narrative code never calls `know.store()` to overwrite an existing Compound.
Narrative-local state lives entirely in `Binding.current` and `Binding.history`.

This is enforced by convention in Phase 1. Phase 2 adds a runtime guard that raises
if a stored Compound with a positive ID is passed to `know.store()` again.


8. Phase 1 Scope

  ✅ All data structures (Narrative, Binding, Snap, Constraint, NarrativeEvent)
  ✅ Narrative methods (bind, resolve, assert_constraint, log_event, close, archive)
  ✅ to_dict / from_dict serialisation (all structures)
  ✅ KNOW integration — live reference, autosave, narrative_by_source
  ✅ Relational Narrative bootstrap (THIS_USER with default state)
  ✅ Episodic Narrative creation per conversation
  ❌ Constraint enforcement in THINK (Phase 2 — structures exist but not yet checked)
  ❌ History traversal reasoning (Phase 2)
  ❌ Narrative archiving / thread compression (Phase 2)
  ❌ Cross-narrative entity resolution (Phase 3)
  ❌ Compound promotion (narrative fact → universal compound update) (Phase 3)
