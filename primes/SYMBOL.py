"""
SYMBOL — Interpretation Prime

Resolves human-language symbols into prime-grounded near-compound candidates.
Consumes observations from observation_queue and pushes candidates to
candidate_queue for DATA to validate.

Resolution cascade (per SYMBOL_CONCEPT.md):
  1. KNOW exact lookup (by surface form)     — cheapest, sub-ms
  2. spaCy lemmatize → KNOW lemma lookup     — cheap, ~2ms
  3. Create family member (KIND relation)    — if root exists
  4. LLM specialist via Ollama               — expensive, fallback only
  5. Prime-name heuristic                    — last resort
  6. Placeholder (unresolved)                — DATA handles later

Pipeline position: READ → observation_queue → SYMBOL → candidate_queue → DATA
Authoritative docs: docs/PRIMES/SYMBOL/SYMBOL_ARCHITECTURE.md
                    docs/PRIMES/SYMBOL/symbol_concept.md
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from core.prime_base import Prime, PrimeError
from core.primebit import PRIME_INDEX
from core.queues import observation_queue, candidate_queue
from core.router import Router, TokenResolution
from core.specialists import SpecialistConfig, SpecialistRegistry

log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Phase 1 prime name lookup table  (still used as heuristic fallback)
# ══════════════════════════════════════════════════════════════════════════════

_PRIME_NAME_SET: set[str] = {name.lower() for name in PRIME_INDEX}
_LOWER_TO_CANONICAL: Dict[str, str] = {name.lower(): name for name in PRIME_INDEX}


# ══════════════════════════════════════════════════════════════════════════════
# SYMBOL Prime
# ══════════════════════════════════════════════════════════════════════════════

class SYMBOL(Prime):
    """
    Interpretation prime — resolves tokens to prime groundings.

    Autonomous mode:  daemon thread drains observation_queue, produces
                      near-compound candidates, pushes to candidate_queue.
    On-demand mode:   called directly by THINK or KNOW for a single symbol
                      resolution.  Returns a candidate dict synchronously.

    Resolution cascade (router):
      1. KNOW.by_symbol(surface)     → existing compound
      2. spaCy lemmatize + KNOW lemma lookup
      3. Family member creation       → KIND relation to root
      4. LLM specialist (Ollama)      → new root compound proposal
      5. Prime-name heuristic         → exact match on 63 primes
      6. Unresolved placeholder       → DATA creates placeholder
    """

    def __init__(self, specialist_config: Optional[SpecialistConfig] = None):
        super().__init__("SYMBOL", metadata={
            "role":        "interpretation",
            "description": "Symbol-to-prime grounding via router + specialists",
        })
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Specialist configuration
        self._specialist_config = specialist_config

        # Router and specialist registry (initialized lazily)
        self._router: Optional[Router] = None
        self._registry: Optional[SpecialistRegistry] = None

        # Statistics
        self.stats: Dict[str, int] = {
            "observations_processed": 0,
            "tokens_grounded":        0,
            "tokens_unresolved":      0,
            "candidates_produced":    0,
            "specialist_calls":       0,
            "errors":                 0,
        }

    # ══════════════════════════════════════════════════════════════════════
    # Lifecycle
    # ══════════════════════════════════════════════════════════════════════

    def _on_initialize(self) -> None:
        # Pre-load spaCy model so the first observation doesn't stall
        from core.lemmatizer import get_nlp
        get_nlp()

        # Set up specialist registry and router
        self._registry = SpecialistRegistry.create_default(self._specialist_config)
        self._router = Router(
            specialist_fn=self._registry.ground_token,
            enable_specialist=True,
        )

        self._running = True
        self._thread = threading.Thread(
            target=self._ingestion_loop,
            daemon=True,
            name="SYMBOL-ingest",
        )
        self._thread.start()
        model_name = (self._specialist_config.model
                      if self._specialist_config else "phi3:mini (default)")
        print(f"SYMBOL: Initialized — router + specialist ({model_name}) active")

    def _on_shutdown(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("SYMBOL: Shutdown complete")

    # ══════════════════════════════════════════════════════════════════════
    # __call__ — on-demand mode
    # ══════════════════════════════════════════════════════════════════════

    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        On-demand symbol resolution.

        context keys:
          "symbol"       — single token to ground  → returns candidate dict
          "observation"  — full observation dict    → returns candidate dict
        """
        if "symbol" in context:
            token = context["symbol"]
            # Use router for single-token resolution
            if self._router is not None:
                resolution = self._router.resolve_single(token)
                return resolution.to_candidate_entry()
            return self._ground_single_token(token)
        if "observation" in context:
            return self._interpret_observation(context["observation"])
        raise PrimeError("SYMBOL: context must contain 'symbol' or 'observation'")

    # ══════════════════════════════════════════════════════════════════════
    # Autonomous ingestion loop
    # ══════════════════════════════════════════════════════════════════════

    def _ingestion_loop(self) -> None:
        """Drain observation_queue, produce candidates, push to candidate_queue."""
        while self._running:
            try:
                obs = observation_queue.get(timeout=0.5)
                candidate = self._interpret_observation(obs)
                if candidate is not None:
                    if not candidate_queue.full():
                        candidate_queue.put(candidate)
                        self.stats["candidates_produced"] += 1
                    else:
                        self.stats["errors"] += 1
            except Exception:
                # queue.Empty on timeout — normal, just loop
                continue

    # ══════════════════════════════════════════════════════════════════════
    # Interpretation logic
    # ══════════════════════════════════════════════════════════════════════

    def _interpret_observation(self, obs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Take a READ observation dict and produce a near-compound candidate.

        Uses the router cascade: KNOW lookup → lemmatize → family member →
        specialist → heuristic → placeholder.

        Candidate shape (per data_concept.md):
          {
            "candidate_primes": [...],
            "roles":            [],
            "rule_template":    None,
            "confidence":       float,
            "provenance":       {...},
            "raw_input":        str,
            "observation_id":   str,
            "source":           str,
          }
        """
        self.stats["observations_processed"] += 1

        data = obs.get("data", {})
        raw_input = data.get("text") or obs.get("raw_input", "")
        source = obs.get("metadata", {}).get("source", "unknown")
        timestamp = obs.get("timestamp", time.time())

        if not raw_input:
            return None

        # ── Use router for full resolution cascade ────────────────────
        if self._router is not None:
            resolutions = self._router.resolve_observation(obs)
            if resolutions:
                candidate_primes = []
                total_score = 0.0

                for r in resolutions:
                    entry = r.to_candidate_entry()
                    candidate_primes.append(entry)
                    total_score += r.score

                    if r.score > 0.0:
                        self.stats["tokens_grounded"] += 1
                    else:
                        self.stats["tokens_unresolved"] += 1

                    if r.method == "specialist":
                        self.stats["specialist_calls"] += 1

                confidence = total_score / len(resolutions) if resolutions else 0.0

                return {
                    "candidate_primes": candidate_primes,
                    "roles":            [],                # Phase 2
                    "rule_template":    None,              # Phase 2
                    "confidence":       round(confidence, 4),
                    "provenance":       {"model": "router", "adapter": None},
                    "raw_input":        raw_input,
                    "observation_id":   f"obs_{int(timestamp * 1000)}",
                    "source":           source,
                }

        # ── Fallback: Phase 1 heuristic-only grounding ────────────────
        return self._heuristic_interpret(obs)

    def _heuristic_interpret(self, obs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Phase 1 fallback: heuristic-only interpretation when router unavailable.

        Splits text on whitespace and matches each token against the 63 primes.
        """
        data = obs.get("data", {})
        raw_input = data.get("text") or obs.get("raw_input", "")
        tokens = (data.get("preliminary_tokens")
                  or obs.get("preliminary_tokens")
                  or raw_input.split())
        source = obs.get("metadata", {}).get("source", "unknown")
        timestamp = obs.get("timestamp", time.time())

        if not raw_input or not tokens:
            return None

        candidate_primes: List[Dict[str, Any]] = []
        total_score = 0.0

        for i, token_text in enumerate(tokens):
            grounding = self._heuristic_ground(token_text)
            candidate_primes.append({
                "token":    token_text,
                "prime":    grounding["prime"],
                "score":    grounding["score"],
                "position": i,
            })
            total_score += grounding["score"]

            if grounding["prime"] is not None:
                self.stats["tokens_grounded"] += 1
            else:
                self.stats["tokens_unresolved"] += 1

        confidence = total_score / len(tokens) if tokens else 0.0

        return {
            "candidate_primes": candidate_primes,
            "roles":            [],
            "rule_template":    None,
            "confidence":       round(confidence, 4),
            "provenance":       {"model": "heuristic", "adapter": None},
            "raw_input":        raw_input,
            "observation_id":   f"obs_{int(timestamp * 1000)}",
            "source":           source,
        }

    def _heuristic_ground(self, token_text: str) -> Dict[str, Any]:
        """
        Phase 1 heuristic: exact case-insensitive match against the 63 primes.

        Returns {"prime": str|None, "score": float}.
        """
        lower = token_text.lower()
        if lower in _PRIME_NAME_SET:
            return {"prime": _LOWER_TO_CANONICAL[lower], "score": 1.0}
        return {"prime": None, "score": 0.0}

    def _ground_single_token(self, token: str) -> Dict[str, Any]:
        """On-demand grounding for a single token (used by THINK/KNOW)."""
        grounding = self._heuristic_ground(token)
        return {
            "token":  token,
            "prime":  grounding["prime"],
            "score":  grounding["score"],
            "method": "heuristic",
        }


# ══════════════════════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════════════════════

symbol = SYMBOL()
