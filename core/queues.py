"""
Thread-safe queues for inter-prime communication.

Pipeline:
  READ → observation_queue → SYMBOL → candidate_queue → DATA → KNOW
  SELF taps observation_queue non-destructively, dispatches to think_queue
  THINK drains think_queue → response_queue → GUI
"""

import queue
from threading import Lock
from typing import Any, Callable

# ── Pipeline queues ───────────────────────────────────────────────────────

# Perceptor outputs (READ, SEE, HEAR) → SYMBOL
observation_queue = queue.Queue(maxsize=10000)

# Near-compound candidates from SYMBOL → DATA
candidate_queue = queue.Queue(maxsize=10000)

# Responses from THINK → GUI
response_queue = queue.Queue(maxsize=1000)

# SELF dispatches salient items here → THINK
think_queue = queue.Queue(maxsize=1000)


# ── SELF tap mechanism ────────────────────────────────────────────────────
# SELF registers a non-destructive tap on observation_queue.
# put_observation() writes to observation_queue AND copies to all taps.

_observation_taps: list[Callable] = []
_tap_lock = Lock()


def register_tap(callback: Callable) -> None:
    """Register a non-destructive tap on observations.

    The callback receives the same dict placed on observation_queue.
    SELF uses this to score salience without consuming the observation.
    """
    with _tap_lock:
        _observation_taps.append(callback)


def put_observation(observation: dict) -> None:
    """Put an observation on observation_queue AND notify all taps.

    All perceptors (READ, SEE, HEAR) must use this instead of
    observation_queue.put() directly so that SELF's tap fires.
    """
    observation_queue.put(observation)
    with _tap_lock:
        for tap in _observation_taps:
            try:
                tap(observation)
            except Exception:
                pass  # tap failure must never block the pipeline


# ── Prime registry ────────────────────────────────────────────────────────

class PrimeRegistry:
    """Registry for dynamically loaded prime instances."""

    def __init__(self):
        self._primes: dict[str, Any] = {}
        self._lock = Lock()

    def get_prime(self, prime_name: str):
        """Get a prime instance by name, loading it dynamically if needed."""
        with self._lock:
            if prime_name not in self._primes:
                import importlib
                module = importlib.import_module(f"primes.{prime_name}")
                # 'self' is reserved in Python — SELF.py exports 'self_'
                attr_name = "self_" if prime_name == "SELF" else prime_name.lower()
                prime_instance = getattr(module, attr_name)
                self._primes[prime_name] = prime_instance
            return self._primes[prime_name]

    def call_prime(self, prime_name: str, context: dict) -> Any:
        """Dynamically import and call a prime with context."""
        prime = self.get_prime(prime_name)
        return prime(context)


# Global registry singleton
prime_registry = PrimeRegistry()