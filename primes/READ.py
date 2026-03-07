"""
READ — Linguistic perceptor prime.

Monitors input sources for text. When a non-empty, non-duplicate
submission arrives, READ opens a CognitiveScene, writes the
PERCEPTION layer, and steps back.

READ never calls another prime. It opens the door; the scene
broadcasts to all other primes from there.

Entry condition: external signal arrives on a registered source.
Scene contribution: raw_input, modality, preliminary_tokens.

See docs/PRIMES/PERCEPTORS/read.md for full spec.
"""

from __future__ import annotations

import re
import threading
import time

from core.cognitive_scene import SceneContribution, SymbolicScene, scene_store
from core.prime_base import Prime


# Simple surface tokeniser — split on whitespace and punctuation boundaries
_TOKEN_RE = re.compile(r"[^\w']+")


def _surface_tokenise(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.split(text.strip()) if t]


class READ(Prime):
    """
    Linguistic perceptor. Runs an autonomous poll loop on a background thread.

    Sources are registered via register_source(). Any object with:
        acquire() -> str | None
        has_changed(sample) -> bool
    qualifies as a ReadSource.

    Duplicate suppression: identical text within COOLDOWN seconds is ignored.
    """

    POLL_INTERVAL = 0.01   # 10 ms
    COOLDOWN      = 0.5    # seconds before the same text can re-trigger

    def __init__(self) -> None:
        super().__init__("READ")
        self._sources: list = []
        self._last_text: str = ""
        self._last_scene_at: float = 0.0
        self._thread: threading.Thread | None = None

    # ── Source registration ───────────────────────────────────────────────

    def register_source(self, source) -> None:
        """Register a ReadSource. Safe to call before or after initialize()."""
        self._sources.append(source)

    # ── Prime lifecycle ───────────────────────────────────────────────────

    def _on_initialize(self) -> None:
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="READ-poll",
            daemon=True,
        )
        self._thread.start()

    def _on_shutdown(self) -> None:
        pass  # daemon thread exits with process

    def __call__(self, context: dict) -> None:
        """Not used — READ is autonomous. Raises if called directly."""
        raise NotImplementedError("READ is autonomous; do not call directly.")

    # ── Poll loop ─────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while not self._shutdown_flag.is_set():
            for source in self._sources:
                sample = source.acquire()
                if sample and source.has_changed(sample):
                    self._handle(sample, getattr(source, "name", "keyboard"))
            time.sleep(self.POLL_INTERVAL)

    def _handle(self, text: str, source_name: str) -> None:
        text = text.strip()
        if not text:
            return

        # Duplicate suppression
        now = time.time()
        if text == self._last_text and (now - self._last_scene_at) < self.COOLDOWN:
            return

        self._last_text = text
        self._last_scene_at = now

        tokens = _surface_tokenise(text)

        # Open scene — forced conscious until SELF is implemented
        scene = scene_store.open(
            source=source_name,
            thread_type="conscious",
            raw_input=text,
            modality="text",
            preliminary_tokens=tokens,
        )

        # SymbolicScene: minimal observation — no primebit yet
        from core.compound import Compound
        from core.primebit import PrimeBit
        obs = Compound.concept(
            temp_id=-(scene_store._scenes.index(scene) + 1),
            symbol=text[:80],
            primebit=PrimeBit(0),
        )
        scene.contribute_symbolic(SceneContribution(
            prime="READ",
            compounds=[obs],
            triples=[],
            narrative_fragment=None,
        ))


# ── Module-level singleton ────────────────────────────────────────────────────
read = READ()
