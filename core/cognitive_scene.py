"""
core/cognitive_scene.py — CognitiveScene + SceneStore.

A CognitiveScene is a thinking thread, not a pipeline step.
Primes watch the SceneStore and contribute whenever their entry
conditions are met — no stage gates, no prime-to-prime calls.

Two thread classes:
  unconscious — low cost, always running (READ, SYMBOL, DATA, KNOW)
  conscious   — expensive, priority-queued (THINK, SAY), managed by SELF

See docs/SYSTEM/cognitive_scene.md for full architecture.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


# ══════════════════════════════════════════════════════════════════════════════
# Thread types and statuses
# ══════════════════════════════════════════════════════════════════════════════

THREAD_TYPES = {"unconscious", "conscious"}

# Active statuses — scene is still being worked on
ACTIVE_STATUSES = {"active", "promoted", "suppressed"}

# Terminal statuses — scene is done
TERMINAL_STATUSES = {"archived", "failed"}

# Conscious priority slots
CONSCIOUS_SLOTS = ("foreground", "background", "stagnation")


# ══════════════════════════════════════════════════════════════════════════════
# SymbolicScene (native PLanguage channel — grows over time)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SceneContribution:
    """A single prime's PLanguage contribution to the scene."""
    prime:              str
    compounds:          list         # list[Compound] — typed loosely to avoid circular import
    triples:            list         # list[Triple]
    narrative_fragment: str | None = None


@dataclass
class SymbolicScene:
    """Native PLanguage channel. Grows as primes learn to contribute."""
    contributions:    list[SceneContribution] = field(default_factory=list)
    narrative_thread: list[int]               = field(default_factory=list)  # ordered Compound IDs


# ══════════════════════════════════════════════════════════════════════════════
# CognitiveScene — the thinking thread
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CognitiveScene:
    """
    One thinking thread. Primes contribute by writing to their sections.
    Never call another prime directly — write here and let them watch.
    """

    # ── Identity ──────────────────────────────────────────────────────────
    scene_id:   str   = field(default_factory=lambda: str(uuid.uuid4()))
    opened_at:  float = field(default_factory=time.time)
    source:     str   = ""   # "keyboard" | "gui" | "internal" | "voice"

    # ── Thread control ────────────────────────────────────────────────────
    thread_type:  str   = "unconscious"   # "unconscious" | "conscious"
    status:       str   = "active"        # see ACTIVE_STATUSES / TERMINAL_STATUSES
    salience:     float = 0.0             # SELF updates this continuously
    conscious_slot: str | None = None     # "foreground" | "background" | "stagnation"

    # ── Stagnation detection ──────────────────────────────────────────────
    last_progress_at:      float     = field(default_factory=time.time)
    stagnation_timeout:    float     = 5.0   # wall-clock threshold, always active
    stagnation_max_cycles: int | None = None  # content-based; THINK sets this
    think_cycles:          int       = 0     # incremented by THINK each loop

    # ── PERCEPTION  [READ writes here] ───────────────────────────────────
    raw_input:          str       = ""
    modality:           str       = "text"
    preliminary_tokens: list[str] = field(default_factory=list)

    # ── SYMBOL  [SYMBOL writes here] ─────────────────────────────────────
    script:        str  = ""                           # dominant Unicode block: "latin" | "cyrillic" | ...
    language_hint: dict = field(default_factory=dict)  # {ISO-639 code: confidence} e.g. {"en": 0.92}

    # ── MEMORY  [KNOW writes here] ────────────────────────────────────────
    token_resolutions: list[dict] = field(default_factory=list)
    prime_field:       dict       = field(default_factory=dict)   # {prime_name: max_score}
    prime_field_bits:  int        = 0
    unresolved_tokens: list[str]  = field(default_factory=list)
    utterance_id:      int | None = None
    concept_ids:       list[int]  = field(default_factory=list)
    known_symbols:     list[str]  = field(default_factory=list)
    new_symbols:       list[str]  = field(default_factory=list)
    active_narratives: list[int]  = field(default_factory=list)

    # ── INTEGRITY  [DATA writes here] ─────────────────────────────────────
    validation_flags: dict = field(default_factory=dict)   # {compound_id: {valid, orphan_primes}}

    # ── AFFECTIVE  [FEEL writes here — Phase 4] ───────────────────────────
    valence:       float = 0.0
    intensity:     float = 0.0
    emotional_tag: str   = ""

    # ── MOTIVATIONAL  [WANT/NEED write here — Phase 5] ────────────────────
    goal_relevance: float = 0.0
    need_pressure:  float = 0.0
    active_goal:    str   = ""

    # ── RELATIONAL  [SELF writes here] ───────────────────────────────────
    attention_decision:   str | None   = None   # "conscious" | "archived"
    relationship_quality: float | None = None

    # ── EXECUTION  [THINK + SAY write here] ──────────────────────────────
    reasoning_mode: str | None = None
    intent_id:      int | None = None
    response_text:  str | None = None

    # ── CLOSE ─────────────────────────────────────────────────────────────
    closed_at: float | None = None

    # ── SymbolicScene (native PLanguage channel) ──────────────────────────
    symbolic: SymbolicScene = field(default_factory=SymbolicScene)

    # ── Internal write lock (primes write concurrently) ───────────────────
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def write(self, **kwargs: Any) -> None:
        """
        Thread-safe field update. Any prime calls scene.write(field=value, ...).
        Updates last_progress_at automatically.
        """
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    object.__setattr__(self, k, v)
            object.__setattr__(self, "last_progress_at", time.time())

    def contribute_symbolic(self, contribution: SceneContribution) -> None:
        """Append a PLanguage contribution. Thread-safe."""
        with self._lock:
            self.symbolic.contributions.append(contribution)
            object.__setattr__(self, "last_progress_at", time.time())

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def is_stagnant(self) -> bool:
        """True if either stagnation condition is met."""
        time_stagnant = (time.time() - self.last_progress_at) > self.stagnation_timeout
        if time_stagnant:
            return True
        if self.stagnation_max_cycles is not None:
            return self.think_cycles >= self.stagnation_max_cycles
        return False

    def archive(self) -> None:
        """Mark scene as complete and done."""
        with self._lock:
            object.__setattr__(self, "status", "archived")
            object.__setattr__(self, "closed_at", time.time())

    def fail(self) -> None:
        """Mark scene as failed."""
        with self._lock:
            object.__setattr__(self, "status", "failed")
            object.__setattr__(self, "closed_at", time.time())

    def promote(self, slot: str = "foreground") -> None:
        """SELF calls this to move scene to the conscious layer."""
        with self._lock:
            object.__setattr__(self, "thread_type", "conscious")
            object.__setattr__(self, "status", "promoted")
            object.__setattr__(self, "conscious_slot", slot)

    def suppress(self) -> None:
        """Park this scene — higher-salience scene took priority."""
        with self._lock:
            object.__setattr__(self, "status", "suppressed")


# ══════════════════════════════════════════════════════════════════════════════
# SceneStore — the pool of all live thinking threads
# ══════════════════════════════════════════════════════════════════════════════

class SceneStore:
    """
    Holds all CognitiveScenes for the current session.

    Primes call by_status() or active_unconscious() to find scenes to work on.
    Scenes are never deleted during a session — only their status changes.
    """

    MAX_SCENES = 200

    def __init__(self) -> None:
        self._scenes: list[CognitiveScene] = []
        self._lock = threading.Lock()

    def open(
        self,
        source: str,
        thread_type: str = "unconscious",
        **kwargs: Any,
    ) -> CognitiveScene:
        """Open a new thinking thread and register it."""
        scene = CognitiveScene(source=source, thread_type=thread_type, **kwargs)
        with self._lock:
            self._scenes.append(scene)
            # Evict oldest terminal scenes if over limit
            if len(self._scenes) > self.MAX_SCENES:
                terminal = [s for s in self._scenes if s.is_terminal]
                if terminal:
                    self._scenes.remove(terminal[0])
        return scene

    def get(self, scene_id: str) -> CognitiveScene | None:
        """Return scene by ID, or None."""
        with self._lock:
            for s in self._scenes:
                if s.scene_id == scene_id:
                    return s
        return None

    def recent(self, n: int = 5) -> list[CognitiveScene]:
        """Return the n most recently opened scenes."""
        with self._lock:
            return list(self._scenes[-n:])

    def by_status(self, status: str) -> list[CognitiveScene]:
        """Return all scenes with the given status."""
        with self._lock:
            return [s for s in self._scenes if s.status == status]

    def active_unconscious(self) -> list[CognitiveScene]:
        """Return all active unconscious scenes (the common poll target)."""
        with self._lock:
            return [
                s for s in self._scenes
                if s.thread_type == "unconscious" and s.is_active
            ]

    def conscious_queue(self) -> list[CognitiveScene]:
        """
        Return conscious scenes ordered by slot priority:
        foreground → background → stagnation.
        Within each slot, higher salience first.
        """
        slot_order = {s: i for i, s in enumerate(CONSCIOUS_SLOTS)}
        with self._lock:
            conscious = [s for s in self._scenes if s.thread_type == "conscious" and s.is_active]
        conscious.sort(
            key=lambda s: (slot_order.get(s.conscious_slot or "stagnation", 2), -s.salience)
        )
        return conscious

    def all_active(self) -> list[CognitiveScene]:
        """Return all scenes that are not yet terminal."""
        with self._lock:
            return [s for s in self._scenes if s.is_active]


# ── Module-level singleton ────────────────────────────────────────────────────
scene_store = SceneStore()
