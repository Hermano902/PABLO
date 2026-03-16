"""
Narrative data structures — shared by THINK (creator/operator) and KNOW (store/retrieve).

Two distinct types:
  DefinitionNarrative  — living definition of a compound's universal meaning.
                         One per concept compound.  Permanent, never closed.
  Narrative            — contextual memory (episodic or relational).
                         Created/operated by THINK, stored via KNOW.

No imports from any prime module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time

from core.scene_template import SceneTemplate


# ══════════════════════════════════════════════════════════════════════════════
# DefinitionNarrative
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DefinitionNarrative:
    """Living definition of one concept compound.

    Created by KNOW during store_batch for new concept compounds.
    Updated only via KNOW.refine_definition() — never directly by any other prime.
    """

    id:             int               # assigned by KNOW (separate counter from compounds)
    compound_id:    int               # compound this definition belongs to
    symbol:         str               # human-language handle (readability only)
    relations:      list[dict]        # predicate -> target links forming the definition
    thread:         list[dict]        # ordered history of how meaning was built
    constraints:    list[dict]        # definitional rules that must hold universally
    created_at:     float = field(default_factory=time.time)
    # Primes have NO scene_template (they are axiomatic, single-execution).
    # Compound concepts carry a SceneTemplate: ordered prime steps + causal/temporal links.
    scene_template: SceneTemplate | None = None

    # ── Mutation methods ──────────────────────────────────────────────────

    def add_relation(
        self,
        predicate: str,
        target_id: int,
        provenance: dict | None = None,
    ) -> None:
        """Add a new relation to the definition.  Appends to thread."""
        self.relations.append({"predicate": predicate, "target_id": target_id})
        self.thread.append({
            "timestamp":  time.time(),
            "type":       "relation_added",
            "provenance": provenance or {},
            "predicate":  predicate,
            "target_id":  target_id,
        })

    def update_primebit(
        self,
        primebit_value: int,
        confidence: float,
        provenance: dict | None = None,
        version: int = 0,
    ) -> None:
        """Record a primebit refinement in the thread."""
        self.thread.append({
            "timestamp":  time.time(),
            "type":       "primebit_refined",
            "provenance": provenance or {},
            "primebit":   primebit_value,
            "confidence": confidence,
            "version":    version,
        })

    def assert_constraint(
        self,
        text: str,
        primebit: int,
        provenance: dict | None = None,
    ) -> None:
        """Assert a universal definitional constraint."""
        self.constraints.append({
            "text":        text,
            "primebit":    primebit,
            "active":      True,
            "asserted_at": time.time(),
            "provenance":  provenance or {},
        })

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "compound_id":    self.compound_id,
            "symbol":         self.symbol,
            "relations":      self.relations,
            "thread":         self.thread,
            "constraints":    self.constraints,
            "created_at":     self.created_at,
            "scene_template": self.scene_template.to_dict() if self.scene_template else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DefinitionNarrative:
        raw_st = d.get("scene_template")
        return cls(
            id=             d["id"],
            compound_id=    d["compound_id"],
            symbol=         d["symbol"],
            relations=      d.get("relations", []),
            thread=         d.get("thread", []),
            constraints=    d.get("constraints", []),
            created_at=     d.get("created_at", time.time()),
            scene_template= SceneTemplate.from_dict(raw_st) if raw_st else None,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Instance Narrative supporting structures
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Snap:
    """Historical state snapshot within a Binding."""
    timestamp:  float
    state:      dict              # copy of Binding.current at this moment
    cause:      str | None        # human-readable cause
    event_ref:  int | None        # NarrativeEvent.id that triggered this change


@dataclass
class Binding:
    """Narrative-local instance of a base Compound."""
    local_name:   str             # "THIS_ALICE", "THE_BALL" — unique within Narrative
    compound_id:  int             # ID of base Compound in KNOW — never modified
    current:      dict            # narrative-local property map (mutable)
    history:      list[Snap] = field(default_factory=list)

    def update(
        self,
        new_state: dict,
        cause: str | None = None,
        event_ref: int | None = None,
    ) -> None:
        """Append Snap of current state, then apply new_state as delta."""
        self.history.append(Snap(
            timestamp=time.time(),
            state=dict(self.current),
            cause=cause,
            event_ref=event_ref,
        ))
        self.current.update(new_state)


@dataclass
class Constraint:
    """A logical rule THINK must respect within this Narrative."""
    id:           int
    text:         str             # "Alice no longer owns the ball"
    primebit:     int             # 64-bit int (PrimeBit.value) — machine form
    asserted_at:  float
    source:       str             # "user" | "inferred" | "THINK"
    active:       bool = True

    def lift(self) -> None:
        self.active = False


@dataclass
class NarrativeEvent:
    """One entry in the Narrative's timeline thread."""
    id:           int
    timestamp:    float
    type:         str             # "utterance" | "response" | "state_change" | "constraint" | "action"
    compound_id:  int | None      # associated Layer 1/2/3 Compound, if any
    binding_ref:  str | None      # local_name of affected Binding, if any
    text:         str             # human-readable description


# ══════════════════════════════════════════════════════════════════════════════
# Instance Narrative
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Narrative:
    """Contextual memory container — episodic or relational."""

    id:               int = 0
    name:             str = ""
    narrative_type:   str = "episodic"     # "episodic" | "relational"
    status:           str = "open"         # "open" | "closed" | "archived"
    created_at:       float = field(default_factory=time.time)
    closed_at:        float | None = None
    bindings:         dict[str, Binding] = field(default_factory=dict)
    constraints:      list[Constraint]   = field(default_factory=list)
    thread:           list[NarrativeEvent] = field(default_factory=list)
    _next_event_id:      int = field(default=0, repr=False)
    _next_constraint_id: int = field(default=0, repr=False)

    # ── Binding management ────────────────────────────────────────────────

    def bind(
        self,
        local_name: str,
        compound_id: int,
        initial_state: dict | None = None,
    ) -> Binding:
        """Create and register a new Binding.  Raises if local_name exists."""
        if local_name in self.bindings:
            raise ValueError(f"Binding {local_name!r} already exists in this Narrative")
        b = Binding(
            local_name=local_name,
            compound_id=compound_id,
            current=initial_state or {},
        )
        self.bindings[local_name] = b
        return b

    def resolve(self, local_name: str) -> Binding | None:
        return self.bindings.get(local_name)

    # ── Constraint management ─────────────────────────────────────────────

    def assert_constraint(
        self,
        text: str,
        primebit: int,
        source: str = "THINK",
    ) -> Constraint:
        c = Constraint(
            id=self._next_constraint_id,
            text=text,
            primebit=primebit,
            asserted_at=time.time(),
            source=source,
        )
        self._next_constraint_id += 1
        self.constraints.append(c)
        return c

    def active_constraints(self) -> list[Constraint]:
        return [c for c in self.constraints if c.active]

    # ── Thread management ─────────────────────────────────────────────────

    def log_event(
        self,
        type: str,
        text: str,
        compound_id: int | None = None,
        binding_ref: str | None = None,
    ) -> NarrativeEvent:
        e = NarrativeEvent(
            id=self._next_event_id,
            timestamp=time.time(),
            type=type,
            compound_id=compound_id,
            binding_ref=binding_ref,
            text=text,
        )
        self._next_event_id += 1
        self.thread.append(e)
        return e

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def close(self) -> None:
        self.status = "closed"
        self.closed_at = time.time()

    def archive(self) -> None:
        self.status = "archived"

    # ── Serialisation ─────────────────────────────────────────────────────

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
            "constraints":         [c.__dict__ for c in self.constraints],
            "thread":              [e.__dict__ for e in self.thread],
            "_next_event_id":      self._next_event_id,
            "_next_constraint_id": self._next_constraint_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Narrative:
        n = cls()
        n.id             = d["id"]
        n.name           = d["name"]
        n.narrative_type = d.get("narrative_type", "episodic")
        n.status         = d["status"]
        n.created_at     = d["created_at"]
        n.closed_at      = d.get("closed_at")
        n._next_event_id      = d.get("_next_event_id", 0)
        n._next_constraint_id = d.get("_next_constraint_id", 0)
        for name, bd in d.get("bindings", {}).items():
            b = Binding(
                local_name=bd["local_name"],
                compound_id=bd["compound_id"],
                current=bd["current"],
                history=[Snap(**s) for s in bd.get("history", [])],
            )
            n.bindings[name] = b
        n.constraints = [Constraint(**c) for c in d.get("constraints", [])]
        n.thread      = [NarrativeEvent(**e) for e in d.get("thread", [])]
        return n
