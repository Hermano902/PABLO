"""
System state snapshot — assembled once per timer tick and passed to all panels.

Rules:
- This module calls prime.status() (read-only).
- It never writes to any prime or queue.
- It never calls any NiceGUI function.
"""

import time
from core.queues import observation_queue, candidate_queue, response_queue

# Prime names that this PABLO session manages.
MANAGED_PRIMES = ["READ", "DATA", "KNOW", "THINK"]

# Rolling event log — appended to by other modules, read by state.py.
_event_log: list[str] = []
MAX_EVENT_LOG = 100


def log_event(message: str) -> None:
    """Append an event to the rolling log. Thread-safe (GIL-protected list append)."""
    ts = time.strftime("%H:%M:%S")
    _event_log.append(f"{ts}  {message}")
    if len(_event_log) > MAX_EVENT_LOG:
        del _event_log[:-MAX_EVENT_LOG]


def get_state(prime_registry) -> dict:
    """
    Assemble a system_state snapshot.
    Called from the NiceGUI timer callback — runs on the async event loop thread.
    """
    primes = {}
    for name in MANAGED_PRIMES:
        try:
            prime = prime_registry._primes.get(name)
            if prime is None:
                primes[name] = {"status": "not loaded"}
            elif hasattr(prime, "status") and callable(prime.status):
                primes[name] = prime.status()
            elif getattr(prime, "_initialized", False):
                primes[name] = {"status": "running"}
            else:
                primes[name] = {"status": "idle"}
        except Exception:
            primes[name] = {"status": "error"}

    return {
        "primes": primes,
        "queues": {
            "observation": {"size": observation_queue.qsize(), "maxsize": 10000},
            "candidate":   {"size": candidate_queue.qsize(),   "maxsize": 10000},
            "response":    {"size": response_queue.qsize(),    "maxsize": 1000},
        },
        "events": list(_event_log[-50:]),
        "timestamp": time.time(),
    }
