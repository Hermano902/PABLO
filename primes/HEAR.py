"""
HEAR — Auditory perception prime (DORMANT).

HEAR is structurally complete but **not started** in Phase 1.
Its thread is never launched; ``active`` is always ``False``.

When implemented (Phase 2+), HEAR will:
  - Detect sound events via amplitude threshold or classifier
  - Emit one observation per onset event (not continuously)
  - Use put_observation() to write to observation_queue + SELF tap

See docs/PRIMES/PERCEPTORS/ for concept and architecture.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict

from core.compound import Compound
from core.prime_base import Prime
from core.primebit import PrimeBit

log = logging.getLogger(__name__)


class HEAR(Prime):
    """Auditory perception prime.  Dormant in Phase 1."""

    def __init__(self) -> None:
        super().__init__(name="HEAR")
        self.active: bool = False
        self._thread = None
        self._running: bool = False
        self._drop_count: int = 0

    def _on_initialize(self) -> None:
        """Phase 1: do NOT start the observation thread."""
        log.info("HEAR: Initialized (dormant — thread not started)")

    def _on_shutdown(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        log.info("HEAR: Shutdown complete")

    def __call__(self, context: Dict[str, Any]) -> Any:
        """Consultation mode — returns a placeholder Compound.

        Future: will return a snapshot of the current audio state.
        """
        primebit = PrimeBit.from_prime_names({"HEAR"})
        return Compound.concept(
            temp_id=-1,
            symbol="audio_placeholder",
            primebit=primebit,
        )


# ── Singleton ─────────────────────────────────────────────────────────────
hear = HEAR()
