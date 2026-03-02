"""
SELF — Meta-cognitive prime / attention router.

SELF does NOT interpret observations, reason, or write to KNOW.
It observes the pipeline at two points:
  1. Tap on observation_queue (early alert — source metadata only)
  2. KNOW Layer 1 commit callback (dispatch phase)

If salience >= threshold, SELF pushes to think_queue with full context.
SELF is the sole writer to think_queue.

See docs/PRIMES/SELF/ for concept and architecture.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any, Dict, Optional

from core.prime_base import Prime
from core.queues import register_tap, think_queue

log = logging.getLogger(__name__)

# ── Salience constants ────────────────────────────────────────────────────

BASE_SALIENCE: Dict[str, float] = {
    "keyboard": 1.0,
    "gui":      1.0,
    "stdin":    1.0,
    "vision":   0.4,
    "audio":    0.4,
    "internal": 0.2,
}

ATTENTION_THRESHOLD: float = 0.3


# ══════════════════════════════════════════════════════════════════════════
# SELF class
# ══════════════════════════════════════════════════════════════════════════

class SELF(Prime):
    """Meta-cognitive attention router.  Singleton via ``self_``."""

    def __init__(self) -> None:
        super().__init__(name="SELF")
        self.suspended: bool = True           # starts suspended during boot
        self._attention_threshold: float = ATTENTION_THRESHOLD
        self._tap_queue: queue.Queue = queue.Queue(maxsize=100)
        self._pending_sources: Dict[float, str] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._running: bool = False

        self.stats: Dict[str, int] = {
            "observations_tapped": 0,
            "layer1_received":     0,
            "dispatched":          0,
            "suppressed":          0,
        }

    # ── Prime interface ───────────────────────────────────────────────────

    def _on_initialize(self) -> None:
        """Register tap, register KNOW Layer 1 listener, start monitor thread."""
        from primes.KNOW import know

        # Callback-based tap: queues.py calls this for every put_observation
        register_tap(self._tap_callback)

        # Layer 1 commit listener — called from KNOW's input thread
        know.register_layer1_listener(self._on_utterance_committed)

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="SELF-monitor"
        )
        self._monitor_thread.start()
        log.info("SELF: Initialized (suspended=%s)", self.suspended)

    def _on_shutdown(self) -> None:
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        log.info("SELF: Shutdown complete")

    def __call__(self, context: Dict[str, Any]) -> Any:
        """Consultation mode — returns current attention state."""
        return {
            "suspended":   self.suspended,
            "threshold":   self._attention_threshold,
            "pending":     len(self._pending_sources),
            "stats":       dict(self.stats),
        }

    # ── Tap callback (called from perceptor thread via put_observation) ───

    def _tap_callback(self, obs: dict) -> None:
        """Non-destructive copy: forward observation to internal _tap_queue."""
        try:
            self._tap_queue.put_nowait(obs)
        except queue.Full:
            pass  # overflow — SELF's tap is non-critical

    # ── Monitor loop (early alert phase) ──────────────────────────────────

    def _monitor_loop(self) -> None:
        """Drain _tap_queue, record source metadata for early salience."""
        while self._running:
            try:
                obs = self._tap_queue.get(timeout=0.1)
                self.stats["observations_tapped"] += 1
                self._handle_early_observation(obs)
            except queue.Empty:
                continue
            except Exception:
                log.exception("SELF: error in monitor loop")

    def _handle_early_observation(self, obs: dict) -> None:
        """Phase 1: record pending source. Phase 2 would signal THINK pre-load."""
        source = obs.get("metadata", {}).get("source", "unknown")
        early_salience = self._early_salience_score(source)
        if early_salience > 0:
            self._pending_sources[obs.get("timestamp", time.time())] = source

    def _early_salience_score(self, source: str) -> float:
        """Quick score based on source alone — used for early alerting."""
        return BASE_SALIENCE.get(source, 0.2)

    # ── Layer 1 commit callback (dispatch phase) ─────────────────────────

    def _on_utterance_committed(self, utterance_id: int, source: str) -> None:
        """Called by KNOW's thread when a Layer 1 utterance is committed."""
        self.stats["layer1_received"] += 1

        if self.suspended:
            self.stats["suppressed"] += 1
            return

        salience = self._compute_salience(source)
        if salience < self._attention_threshold:
            self.stats["suppressed"] += 1
            return

        item = {
            "utterance_compound_id": utterance_id,
            "timestamp":             time.time(),
            "source":                source,
            "salience":              salience,
            "want_context":          self._active_want_goal(),
            "feel_state":            self._feel_state(),
        }
        think_queue.put(item)
        self.stats["dispatched"] += 1

    # ── Salience computation ──────────────────────────────────────────────

    def _compute_salience(self, source: str) -> float:
        """Phase 1: fixed base scores + narrative-aware modifiers."""
        base = BASE_SALIENCE.get(source, 0.2)
        want_mod, feel_mul = self._get_narrative_modifiers(source)
        return base * (1.0 + want_mod) * feel_mul

    def _get_narrative_modifiers(self, source: str) -> tuple:
        """Read THIS_USER.current from Relational Narrative.

        Returns (want_mod: float, feel_mul: float).
        """
        from primes.KNOW import know

        narrative = know.narrative_by_source(source)
        if narrative is None:
            return 0.0, 1.0

        # Look for THIS_USER binding
        binding = narrative.bindings.get("THIS_USER")

        if binding is None:
            return 0.0, 1.0

        rel_quality = binding.current.get("relationship_quality", 0.0)
        feel_state = binding.current.get("emotional_register", "neutral")
        feel_mul = {
            "warm":    1.3,
            "neutral": 1.0,
            "guarded": 0.5,
            "closed":  0.1,
        }.get(feel_state, 1.0)
        return rel_quality, feel_mul

    # ── Phase 1 stubs ────────────────────────────────────────────────────

    def _active_want_goal(self) -> str:
        """Phase 1: always returns 'default'. Phase 2 adds WANT sub-prime."""
        return "default"

    def _feel_state(self) -> str:
        """Phase 1: always returns 'neutral'. Phase 2 adds FEEL sub-prime."""
        return "neutral"


# ── Singleton ─────────────────────────────────────────────────────────────
self_ = SELF()
