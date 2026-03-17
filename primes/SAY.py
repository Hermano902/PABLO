"""
SAY — Output prime.

Watches for conscious scenes that have a response_text ready (written by THINK)
but have not yet been closed. SAY:

  1. Emits the response to all registered output handlers
  2. Writes a final SymbolicScene contribution — the expressed response as a
     Compound sequence, archived in KNOW as a Narrative fragment
  3. Archives the scene

Entry condition: scene is conscious AND scene.response_text is set AND
                 scene.closed_at is None.

SAY never calls another prime.  It writes its Narrative contribution to KNOW
(shared storage) and archives the scene.

See docs/PRIMES/say.md for full spec.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from core.cognitive_scene import CognitiveScene, SceneContribution, scene_store
from core.compound import Compound
from core.prime_base import Prime
from core.primebit import PrimeBit, PRIME_TO_BIT


class SAY(Prime):
    """
    Output prime.  Polls the conscious queue for scenes with response_text ready.
    Emits the response and archives the scene.
    """

    POLL_INTERVAL = 0.02   # 20 ms

    def __init__(self) -> None:
        super().__init__("SAY")
        self._thread: threading.Thread | None = None
        self._processed: set[str] = set()
        self._processed_lock = threading.Lock()
        self._handlers: list[Callable[[str, CognitiveScene], None]] = []

    # ── Handler registration ──────────────────────────────────────────────

    def register_handler(self, handler: Callable[[str, CognitiveScene], None]) -> None:
        """
        Register an output handler.
        Called with (response_text, scene) whenever SAY emits a response.
        Safe to call before or after initialize().
        """
        self._handlers.append(handler)

    # ── Prime lifecycle ───────────────────────────────────────────────────

    def _on_initialize(self) -> None:
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="SAY-poll",
            daemon=True,
        )
        self._thread.start()

    def _on_shutdown(self) -> None:
        pass

    def __call__(self, context: dict) -> None:
        raise NotImplementedError("SAY is autonomous; do not call directly.")

    # ── Poll loop ─────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while not self._shutdown_flag.is_set():
            try:
                for scene in scene_store.conscious_queue():
                    if self._should_process(scene):
                        self._process(scene)
            except Exception:
                import traceback
                traceback.print_exc()
            time.sleep(self.POLL_INTERVAL)

    def _should_process(self, scene: CognitiveScene) -> bool:
        if scene.response_text is None:
            return False
        if scene.closed_at is not None:
            return False
        with self._processed_lock:
            if scene.scene_id in self._processed:
                return False
        return True

    # ── Output and archival ───────────────────────────────────────────────

    def _process(self, scene: CognitiveScene) -> None:
        with self._processed_lock:
            self._processed.add(scene.scene_id)

        response = scene.response_text or ""

        # 1. Emit to all registered handlers
        for handler in self._handlers:
            try:
                handler(response, scene)
            except Exception:
                import traceback
                traceback.print_exc()

        # 2. Write Narrative fragment to KNOW (the expressed response)
        self._write_expression_narrative(scene, response)

        # 3. SymbolicScene contribution
        say_bit = PrimeBit(1 << PRIME_TO_BIT["SAY"]) if "SAY" in PRIME_TO_BIT else PrimeBit(0)
        response_marker = Compound.concept(
            temp_id=0,
            symbol=response[:80],
            primebit=say_bit,
            confidence=1.0,
            grounded=True,
        )
        scene.contribute_symbolic(SceneContribution(
            prime="SAY",
            compounds=[response_marker],
            triples=[],
            narrative_fragment=response[:200],
        ))

        # 4. Archive the scene
        scene.archive()

    def _write_expression_narrative(self, scene: CognitiveScene, response: str) -> None:
        """
        Record the expressed response in the Instance Narrative for this source.
        Phase 1: stores as a NarrativeEvent in the thread.
        """
        try:
            from primes.KNOW import know
            from core.narrative import NarrativeEvent
            nar = know.narrative_by_source(scene.source)
            if nar is None:
                return
            event = NarrativeEvent(
                id=len(nar.thread),
                timestamp=time.time(),
                type="response",
                compound_id=scene.intent_id,
                binding_ref=None,
                text=response[:200],
            )
            nar.thread.append(event)
        except Exception:
            pass


# ── Module-level singleton ────────────────────────────────────────────────────
say = SAY()
