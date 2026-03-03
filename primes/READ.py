"""
READ — Linguistic Perceptor Prime

PABLO's ability to encounter written language.  Monitors registered text
sources, detects changes, and pushes raw observation dicts to
observation_queue.  READ does NOT interpret meaning — that is SYMBOL's job.

Pipeline position: READ → observation_queue → SYMBOL
Authoritative doc: docs/PRIMES/PERCEPTORS/READ/READ_ARCHITECTURE.md
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, List, Optional

from core.prime_base import Prime, PrimeError
from core.queues import observation_queue, put_observation
from core.compound import Compound
from core.primebit import PrimeBit
from gui.input_source import gui_input_source


# ══════════════════════════════════════════════════════════════════════════════
# ReadSource protocol (duck-typed)
# ══════════════════════════════════════════════════════════════════════════════
# Every source must expose:
#   name:   str
#   active: bool
#   acquire()       -> str | None
#   has_changed(s)  -> bool
#   update_state(s) -> None
#   event_type(s)   -> str


# ══════════════════════════════════════════════════════════════════════════════
# Dormant source stubs (registered but active=False)
# ══════════════════════════════════════════════════════════════════════════════

class ScreenSource:
    """Dormant — activate in Phase 2."""
    name   = "screen"
    active = False

    def acquire(self) -> Optional[str]:
        return None

    def has_changed(self, sample: str) -> bool:
        return False

    def update_state(self, sample: str) -> None:
        pass

    def event_type(self, sample: str) -> str:
        return "text_appeared"


class FileSource:
    """Dormant — activate in Phase 2."""
    name   = "file"
    active = False

    def acquire(self) -> Optional[str]:
        return None

    def has_changed(self, sample: str) -> bool:
        return False

    def update_state(self, sample: str) -> None:
        pass

    def event_type(self, sample: str) -> str:
        return "file_appended"


# ══════════════════════════════════════════════════════════════════════════════
# READ Prime
# ══════════════════════════════════════════════════════════════════════════════

class READ(Prime):
    """
    Linguistic perceptor.  Detects text changes across registered sources
    and pushes canonical observation dicts to observation_queue.

    Phase 1: only KeyboardSource (GUIInputSource) is active.
    """

    def __init__(self, simulate: bool = False):
        super().__init__("READ")
        self._simulate = simulate
        self._sources = self._build_sources()
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Deduplication / flood protection
        self._recent_hashes: set[int]          = set()
        self._last_sent_time: Dict[int, float] = {}
        self._send_cooldown  = 0.1     # seconds between identical observations
        self._cache_max_age  = 300.0   # seconds before cache entry eviction
        self._cache_max_size = 1000
        self._drop_count     = 0

        # Timing
        self._sample_interval = 0.01   # 10ms between loop iterations

        # Simulation
        self._sim_index = 0
        self._sim_inputs = [
            "the cat moved left",
            "hello world",
            "what is your name",
            "how are you today",
            "tell me something",
        ]

    def _build_sources(self) -> list:
        """Register all sources.  Phase 1: only keyboard is active."""
        return [
            gui_input_source,   # active
            ScreenSource(),     # dormant
            FileSource(),       # dormant
        ]

    # ══════════════════════════════════════════════════════════════════════
    # Lifecycle
    # ══════════════════════════════════════════════════════════════════════

    def _on_initialize(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._observation_loop,
            daemon=True,
            name="READ-observe",
        )
        self._thread.start()
        active = [s.name for s in self._sources if s.active]
        print(f"READ: Initialized — active sources: {active}")

    def _on_shutdown(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("READ: Shutdown complete")

    # ══════════════════════════════════════════════════════════════════════
    # __call__ — consultation mode
    # ══════════════════════════════════════════════════════════════════════

    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        Consultation mode — called by THINK (or another prime) directly.
        Returns a Compound; change detection and queue are bypassed.
        """
        text = (
            context.get("input")
            or context.get("query")
            or context.get("text")
            or ""
        )
        if not text:
            raise PrimeError("READ consultation: No input text provided")

        # Still build the observation internally (for tracing)
        obs = self._build_observation_dict(text, source="consultation", mode="consultation")

        # Return a minimal Compound (ephemeral, id=-1)
        primebit = PrimeBit.from_prime_names(["READ"])
        return Compound(
            id=-1,
            symbol=text,
            primebit=primebit,
            nested=[],
            relations=[],
            narrative_id=None,
            grounded=True,
            version=0,
            confidence=1.0,
            executable=False,
            trigger_condition=None,
            arity=0,
            slots=[],
            source="consultation",
            created_at=time.time(),
            compound_type="internal",
        )

    # ══════════════════════════════════════════════════════════════════════
    # Autonomous observation loop
    # ══════════════════════════════════════════════════════════════════════

    def _observation_loop(self) -> None:
        """Iterate registered sources; emit one observation per change."""
        while self._running:
            try:
                for source in self._sources:
                    if not source.active:
                        continue
                    sample = source.acquire()
                    if sample is None:
                        continue
                    if not source.has_changed(sample):
                        continue
                    # Deduplication
                    if self._is_duplicate(sample):
                        continue
                    # Build and queue
                    obs = self._build_observation_dict(
                        sample,
                        source=source.name,
                        event_type=source.event_type(sample),
                    )
                    if not observation_queue.full():
                        put_observation(obs)
                    else:
                        self._drop_count += 1
                    source.update_state(sample)
                    self._record_sent(sample)

                # Simulation path (test only, gated behind flag)
                if self._simulate:
                    self._run_simulation_step()

            except Exception as e:
                print(f"READ: Observation loop error: {e}")

            time.sleep(self._sample_interval)

    # ══════════════════════════════════════════════════════════════════════
    # Observation dict builder
    # ══════════════════════════════════════════════════════════════════════

    def _build_observation_dict(
        self,
        text: str,
        source: str = "keyboard",
        event_type: str = "line_entered",
        mode: str = "autonomous",
    ) -> Dict[str, Any]:
        """Canonical observation format per READ_ARCHITECTURE.md §4."""
        tokens = text.split()
        return {
            "timestamp": time.time(),
            "modality":  "READ",
            "event_type": event_type,
            "data": {
                "text":               text,
                "preliminary_tokens": tokens,
                "token_count":        len(tokens),
            },
            "metadata": {
                "source": source,
                "prime":  "READ",
                "mode":   mode,
            },
        }

    # ══════════════════════════════════════════════════════════════════════
    # Deduplication / flood protection
    # ══════════════════════════════════════════════════════════════════════

    def _is_duplicate(self, text: str) -> bool:
        h = hash(text)
        now = time.time()
        if h in self._recent_hashes:
            if now - self._last_sent_time.get(h, 0) < self._send_cooldown:
                return True
        return False

    def _record_sent(self, text: str) -> None:
        h = hash(text)
        self._recent_hashes.add(h)
        self._last_sent_time[h] = time.time()
        if len(self._recent_hashes) > self._cache_max_size:
            self._evict_old_entries()

    def _evict_old_entries(self) -> None:
        now = time.time()
        to_remove = [
            h for h, t in self._last_sent_time.items()
            if now - t > self._cache_max_age
        ]
        for h in to_remove:
            self._recent_hashes.discard(h)
            self._last_sent_time.pop(h, None)

    # ══════════════════════════════════════════════════════════════════════
    # Simulation (test harness only)
    # ══════════════════════════════════════════════════════════════════════

    def _run_simulation_step(self) -> None:
        """Inject one test string per call (only if simulate=True)."""
        if self._sim_index < len(self._sim_inputs):
            text = self._sim_inputs[self._sim_index]
            self._sim_index += 1
            obs = self._build_observation_dict(text, source="simulation")
            if not observation_queue.full():
                put_observation(obs)


# ══════════════════════════════════════════════════════════════════════════════
# Singleton — production instance.  simulate=False always.
# ══════════════════════════════════════════════════════════════════════════════

read = READ()
