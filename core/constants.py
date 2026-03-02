"""
Canonical prime constants and mappings.

This module re-exports from core.primebit which is the single source of truth.
Kept for backward compatibility during migration.
"""

from .primebit import (
    PRIME_INDEX as PRIMES,
    PRIME_TO_BIT as PRIME_TO_INDEX,
    INDEX_TO_PRIME,
    PAYLOAD_MASK as PRIME_MASK,
    COMPOUND_FLAG,
)

# Backward-compat aliases
COMPOUND_FLAG_BIT = 63
COMPOUND_FLAG_MASK = COMPOUND_FLAG

# Validate we have exactly 63 primes
assert len(PRIMES) == 63, f"Expected 63 primes, got {len(PRIMES)}"