"""
Thread-safe queues for inter-prime communication.
"""

import queue
from threading import Lock
from typing import Any, Optional

# Global observation queue for perceptor outputs
observation_queue = queue.Queue(maxsize=10000)  # Bounded to prevent memory explosion

# Near-compound candidates from SYMBOL → DATA
candidate_queue = queue.Queue(maxsize=10000)

# Responses from THINK → GUI
response_queue = queue.Queue(maxsize=1000)

# Conscious trigger signals from DATA → THINK
# Dispatched by DATA after a conscious_trigger=True utterance compound is committed to KNOW.
# Each item: {"utterance_compound_id": int, "timestamp": float, "source": str}
think_queue = queue.Queue(maxsize=1000)


class PrimeRegistry:
    """Registry for dynamically loaded prime instances."""
    
    def __init__(self):
        self._primes = {}
        self._lock = Lock()
    
    def get_prime(self, prime_name: str):
        """Get a prime instance by name, loading it dynamically if needed."""
        with self._lock:
            if prime_name not in self._primes:
                # Dynamic import
                import importlib
                module = importlib.import_module(f"primes.{prime_name}")
                prime_instance = getattr(module, prime_name.lower())
                self._primes[prime_name] = prime_instance
            return self._primes[prime_name]
    
    def call_prime(self, prime_name: str, context: dict) -> Any:
        """Dynamically import and call a prime with context."""
        prime = self.get_prime(prime_name)
        return prime(context)


# Global registry singleton
prime_registry = PrimeRegistry()