"""
DATA — Graph integrity auditor prime.

Watches for scenes where KNOW has written concept_ids but
validation_flags is still empty. Checks each new Compound's
definition graph for orphan primes (primes in primebit with no
Relation) and writes the findings to validation_flags.

Entry condition: scene.concept_ids non-empty AND scene.validation_flags empty.

DATA is advisory — validation_flags annotate quality but never block progress.
DATA never calls another prime. It reads scene fields and writes one field.

See docs/PRIMES/data.md for full spec.
"""

from __future__ import annotations

import threading
import time

from core.cognitive_scene import CognitiveScene, SceneContribution, scene_store
from core.prime_base import Prime
from core.primebit import PRIME_INDEX


def _validate_graph(compound) -> tuple[bool, list[str]]:
    """
    Check that every prime bit in compound.primebit has ≥1 Relation.
    Returns (is_valid, orphan_prime_names).

    Phase 1: new Compounds have no relations yet — all primes will be orphans.
    valid=False, grounded=False is the expected early state; DATA flags it
    so future enrichment can target these Compounds.
    """
    if not compound.primebit.value:
        return True, []

    related: set[str] = {r.predicate for r in compound.relations}

    orphans: list[str] = []
    bits = compound.primebit.value
    for i, name in enumerate(PRIME_INDEX):
        if (bits >> i) & 1 and name not in related:
            orphans.append(name)

    return len(orphans) == 0, orphans


class DATA(Prime):
    """
    Graph integrity auditor. Runs autonomously on a background thread.
    Polls for scenes where KNOW has populated concept_ids but no
    validation has been run yet.
    """

    POLL_INTERVAL = 0.02   # 20 ms

    def __init__(self) -> None:
        super().__init__("DATA")
        self._thread: threading.Thread | None = None
        self._processed: set[str] = set()
        self._processed_lock = threading.Lock()

    def _on_initialize(self) -> None:
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="DATA-poll",
            daemon=True,
        )
        self._thread.start()

    def _on_shutdown(self) -> None:
        pass

    def __call__(self, context: dict) -> None:
        raise NotImplementedError("DATA is autonomous; do not call directly.")

    # ── Poll loop ─────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while not self._shutdown_flag.is_set():
            for scene in scene_store.active_unconscious():
                if self._should_process(scene):
                    self._process(scene)
            time.sleep(self.POLL_INTERVAL)

    def _should_process(self, scene: CognitiveScene) -> bool:
        """Entry condition: concept_ids present, validation_flags empty, not yet processed."""
        if not scene.concept_ids:
            return False
        if scene.validation_flags:
            return False
        with self._processed_lock:
            if scene.scene_id in self._processed:
                return False
        return True

    # ── Validation ────────────────────────────────────────────────────────

    def _process(self, scene: CognitiveScene) -> None:
        with self._processed_lock:
            self._processed.add(scene.scene_id)

        # Fetch KNOW's compound store to read compound objects by ID.
        # We read from KNOW's store — this is not a prime-to-prime call,
        # it is a read from shared storage (same as reading from disk).
        try:
            from primes.KNOW import know
        except Exception:
            return

        validation_flags: dict = {}
        new_symbol_set = set(scene.new_symbols)

        for cid in scene.concept_ids:
            # Only validate new Compounds — known ones are already validated
            compound = know.by_id(cid)
            if compound is None:
                continue
            if compound.symbol not in new_symbol_set:
                continue  # already validated in a prior scene

            valid, orphans = _validate_graph(compound)
            validation_flags[str(cid)] = {
                "valid": valid,
                "orphan_primes": orphans,
            }

        if not validation_flags:
            # No new compounds to validate — write an empty marker so we don't re-fire
            validation_flags["__checked"] = {"valid": True, "orphan_primes": []}

        scene.write(validation_flags=validation_flags)

        # SymbolicScene: positional AFTER triples between adjacent concepts
        from core.triple import Triple
        triples: list[Triple] = []
        concept_ids = scene.concept_ids
        for i in range(len(concept_ids) - 1):
            triples.append(Triple(
                id=hash(f"{scene.scene_id}:{concept_ids[i]}:AFTER:{concept_ids[i+1]}") & 0x7FFFFFFF,
                source_id=concept_ids[i],
                predicate="AFTER",
                target_prime=str(concept_ids[i + 1]),
                confidence=1.0,
                source="data",
            ))

        scene.contribute_symbolic(SceneContribution(
            prime="DATA",
            compounds=[],
            triples=triples,
            narrative_fragment=None,
        ))


# ── Module-level singleton ────────────────────────────────────────────────────
data = DATA()
