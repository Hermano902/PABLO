"""
SceneTemplate — structured cognitive scene definition for compound meanings.

A compound's meaning is not a flat token list but an ordered, causal,
role-bearing structure: a scene template.

Primes are axiomatic — they have NO SceneTemplate.  The English gloss
("to look at written words and understand what they mean") is a human
label for READ-the-prime, not a definition PABLO processes.  Primes
are single-execution atomic operations.

Compounds are scenes — their DefinitionNarrative may carry a SceneTemplate
that captures which prime operations participate, in what order, with what
causal / temporal links between them, and what open slots are filled at
instantiation time.

Example — "read" as a concept compound:

    SceneTemplate(
        compound_id=<id>,
        steps=[
            SceneStep(0, "SEE",  "percept",   "written_input", "SYMBOL"),
            SceneStep(1, "KNOW", "content",   "meaning",       None),
        ],
        links=[
            SceneLink(0, 1, "BECAUSE"),   # KNOW BECAUSE SEE
            SceneLink(0, 1, "BEFORE"),    # SEE BEFORE KNOW
        ],
        open_slots={"written_input": "SYMBOL", "meaning": None},
    )

No imports from any prime module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Link type constants ───────────────────────────────────────────────────────

LINK_BECAUSE = "BECAUSE"   # step B is the causal result of step A
LINK_BEFORE  = "BEFORE"    # step A temporally precedes step B
LINK_AFTER   = "AFTER"     # step A temporally follows step B
LINK_WITH    = "WITH"      # steps co-occur

# ── Semantic role hinting — advisory, not enforced ───────────────────────────

PRIME_TO_ROLE: dict[str, str] = {
    "SEE":   "percept",    "HEAR":  "percept",   "FEEL":  "percept",
    "TOUCH": "percept",    "READ":  "decode",     "WRITE": "encode",
    "KNOW":  "content",    "THINK": "cognition",  "SAY":   "expression",
    "DO":    "action",     "MAKE":  "produce",    "MOVE":  "motion",
    "CAUSE": "cause",      "WANT":  "intention",  "NEED":  "necessity",
    "HAVE":  "possession", "BE":    "state",      "CHANGE":"transition",
    "USE":   "instrument", "GIVE":  "transfer",   "GET":   "receive",
}

SYMBOL_PRIMES: frozenset[str] = frozenset({
    "READ", "WRITE", "SYMBOL", "SAY",
})


# ══════════════════════════════════════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SceneStep:
    """One prime operation within a cognitive scene."""

    index:     int          # position in scene (0-based)
    prime:     str          # prime name: "SEE", "KNOW", "DO", …
    role:      str          # semantic role hint: "percept", "content", …
    slot_name: str          # open slot label filled at instantiation
    slot_type: str | None   # type constraint: "SYMBOL", "ENTITY", or None

    def to_dict(self) -> dict:
        return {
            "index":     self.index,
            "prime":     self.prime,
            "role":      self.role,
            "slot_name": self.slot_name,
            "slot_type": self.slot_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SceneStep:
        return cls(
            index=     d["index"],
            prime=     d["prime"],
            role=      d["role"],
            slot_name= d["slot_name"],
            slot_type= d.get("slot_type"),
        )


@dataclass
class SceneLink:
    """Causal or temporal link between two steps in a scene."""

    from_step: int    # index of source step
    to_step:   int    # index of target step
    link_type: str    # BECAUSE | BEFORE | AFTER | WITH

    def to_dict(self) -> dict:
        return {
            "from_step": self.from_step,
            "to_step":   self.to_step,
            "link_type": self.link_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SceneLink:
        return cls(
            from_step= d["from_step"],
            to_step=   d["to_step"],
            link_type= d["link_type"],
        )


@dataclass
class SceneTemplate:
    """Structured cognitive scene definition for one compound meaning.

    Primes never have a SceneTemplate — they are axiomatic.
    Every non-prime concept compound's DefinitionNarrative may have one.

    ``steps``      — ordered prime operations (SceneStep list)
    ``links``      — causal / temporal bonds between steps
    ``open_slots`` — slot_name → type_constraint, filled at instantiation
    """

    compound_id: int
    steps:       list[SceneStep]       = field(default_factory=list)
    links:       list[SceneLink]       = field(default_factory=list)
    open_slots:  dict[str, str | None] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "compound_id": self.compound_id,
            "steps":       [s.to_dict() for s in self.steps],
            "links":       [lk.to_dict() for lk in self.links],
            "open_slots":  self.open_slots,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SceneTemplate:
        return cls(
            compound_id= d["compound_id"],
            steps=       [SceneStep.from_dict(s)  for s in d.get("steps", [])],
            links=       [SceneLink.from_dict(lk) for lk in d.get("links", [])],
            open_slots=  d.get("open_slots", {}),
        )
