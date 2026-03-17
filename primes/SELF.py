"""
SELF — Attention gate prime.

Watches for scenes whose memory layer (concept_ids, utterance_id) has been
populated by SYMBOL/KNOW but where no attention decision has been made yet.

Computes salience from relationship history and source type, then decides:
  - salience >= threshold → promote scene to conscious foreground
  - salience < threshold  → archive scene (THINK never engages)

Phase 1 formula:
    base    = source_weight(source)      # keyboard/gui = 1.0
    quality = narrative.relationship_quality  # -1.0 → +1.0 (0.0 for new sources)
    salience = base × (1.0 + quality)

SELF never calls another prime.  It reads KNOW's narrative store (shared storage)
and writes the relational layer to the scene.

See docs/PRIMES/self.md for full spec.
"""

from __future__ import annotations

import threading
import time

from core.cognitive_scene import CognitiveScene, SceneContribution, scene_store
from core.compound import Compound
from core.prime_base import Prime
from core.primebit import PrimeBit, PRIME_TO_BIT


# ── Source weights (Phase 1 — fixed) ─────────────────────────────────────────

_SOURCE_WEIGHTS: dict[str, float] = {
    "keyboard": 1.0,
    "gui":      1.0,
    "voice":    1.0,
    "internal": 0.8,
}

_CONSCIOUS_THRESHOLD = 0.5   # salience at or above this → conscious


class SELF(Prime):
    """
    Attention gate.  Polls active unconscious scenes that have a populated
    memory layer and no attention decision yet.
    """

    POLL_INTERVAL = 0.02   # 20 ms

    def __init__(self) -> None:
        super().__init__("SELF")
        self._thread: threading.Thread | None = None
        self._processed: set[str] = set()
        self._processed_lock = threading.Lock()

    def _on_initialize(self) -> None:
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="SELF-poll",
            daemon=True,
        )
        self._thread.start()

    def _on_shutdown(self) -> None:
        pass

    def __call__(self, context: dict) -> None:
        raise NotImplementedError("SELF is autonomous; do not call directly.")

    # ── Poll loop ─────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while not self._shutdown_flag.is_set():
            try:
                for scene in scene_store.active_unconscious():
                    if self._should_process(scene):
                        self._process(scene)
            except Exception:
                import traceback
                traceback.print_exc()
            time.sleep(self.POLL_INTERVAL)

    def _should_process(self, scene: CognitiveScene) -> bool:
        # Need a populated memory layer but no attention decision yet
        if not scene.concept_ids:
            return False
        if scene.attention_decision is not None:
            return False
        with self._processed_lock:
            if scene.scene_id in self._processed:
                return False
        return True

    # ── Attention computation ─────────────────────────────────────────────

    def _process(self, scene: CognitiveScene) -> None:
        with self._processed_lock:
            self._processed.add(scene.scene_id)

        # 1. Base salience from source type
        base = _SOURCE_WEIGHTS.get(scene.source, 0.8)

        # 2. Relationship quality from Instance Narrative
        relationship_quality = 0.0
        try:
            from primes.KNOW import know
            nar = know.narrative_by_source(scene.source)
            if nar is not None:
                binding = nar.resolve("THIS_USER")
                if binding:
                    relationship_quality = binding.current.get("relationship_quality", 0.0)
        except Exception:
            pass

        # 3. Salience formula (Phase 1 — no FEEL multiplier yet)
        salience = base * (1.0 + relationship_quality)

        # 4. Attention decision
        if salience >= _CONSCIOUS_THRESHOLD:
            decision = "conscious"
        else:
            decision = "archived"

        # 5. Write relational layer
        scene.write(
            salience=salience,
            attention_decision=decision,
            relationship_quality=relationship_quality,
        )

        if decision == "conscious":
            scene.promote(slot="foreground")
        else:
            scene.archive()

        # 6. SymbolicScene contribution
        self_bit = PrimeBit(1 << PRIME_TO_BIT["SELF"]) if "SELF" in PRIME_TO_BIT else PrimeBit(0)
        salience_marker = Compound.concept(
            temp_id=0,
            symbol=f"salience:{salience:.2f}",
            primebit=self_bit,
            confidence=1.0,
            grounded=True,
        )
        scene.contribute_symbolic(SceneContribution(
            prime="SELF",
            compounds=[salience_marker],
            triples=[],
            narrative_fragment=None,
        ))


# ── Module-level singleton ────────────────────────────────────────────────────
self_prime = SELF()
