"""
PABLO Main Entry Point — Console mode.

Initialises all primes in the correct order, then runs an interactive
stdin loop (READ monitors stdin as a source).

For the GUI mode, run ``python main_gui.py`` instead.
"""

import time
import sys

from core.queues import prime_registry, response_queue


# Initialisation order must match dependency graph:
#   KNOW first (others store into it)
#   READ (starts observation loop — feeds observation_queue)
#   SYMBOL (drains observation_queue → candidate_queue)
#   DATA (drains candidate_queue → KNOW)
#   SELF (taps observation_queue + KNOW Layer 1 listener → think_queue)
#   THINK (drains think_queue → response_queue)
INIT_ORDER = ["KNOW", "READ", "SYMBOL", "DATA", "SELF", "THINK"]


def initialize_primes() -> None:
    print("=" * 60)
    print("PABLO — Console Mode")
    print("=" * 60)
    print("\nInitialising primes...")

    for name in INIT_ORDER:
        try:
            prime = prime_registry.get_prime(name)
            prime.initialize()
            print(f"  [OK] {name:10} — initialised")
            time.sleep(0.1)
        except Exception as e:
            print(f"  [!!] {name:10} — failed: {e}")

    # Unsuspend SELF once all primes are running
    try:
        self_prime = prime_registry.get_prime("SELF")
        self_prime.suspended = False
        print("  [OK] SELF       — unsuspended")
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("PABLO is running.  Type text and press Enter.")
    print("Press Ctrl+C to shutdown.")
    print("=" * 60 + "\n")


def shutdown_primes() -> None:
    print("\n" + "=" * 60)
    print("Shutting down PABLO...")

    for name in reversed(INIT_ORDER):
        try:
            prime = prime_registry.get_prime(name)
            prime.shutdown()
            print(f"  OK  {name}")
        except Exception as e:
            print(f"  ERR {name}: {e}")

    print("=" * 60)
    print("PABLO shutdown complete.")


def drain_responses() -> None:
    """Print any pending responses from THINK."""
    while not response_queue.empty():
        try:
            resp = response_queue.get_nowait()
            text = resp.get("text", "")
            if text:
                print(f"  PABLO> {text}")
        except Exception:
            break


def main() -> None:
    try:
        initialize_primes()

        # READ's stdin source will pick up lines from sys.stdin
        # We also drain response_queue to show THINK's output
        while True:
            drain_responses()
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nReceived shutdown signal...")
    finally:
        shutdown_primes()


if __name__ == "__main__":
    main()
