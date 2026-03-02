"""
PrimeBit — 64-bit integer encoding for prime sets and compound payloads.

This module is a pure encoding utility with zero dependencies on other PABLO
modules.  Its only job is to pack and unpack meaning into a 64-bit integer in
a way that is fast, deterministic, and consistent across the entire system.

Two mutually exclusive modes:
  prime-mask mode    (bit 63 == 0)  bits 0-62 are prime flags
  compound-payload   (bit 63 == 1)  bits 0-62 encode compound_id / rel_flags / schema_tag
"""

from __future__ import annotations


# ══════════════════════════════════════════════════════════════════════════════
# Canonical Prime Index — frozen, alphabetical, never modified at runtime
# ══════════════════════════════════════════════════════════════════════════════

PRIME_INDEX: list[str] = [
    "AFTER",    # bit 0
    "ALL",      # bit 1
    "AT",       # bit 2
    "BAD",      # bit 3
    "BE",       # bit 4
    "BECAUSE",  # bit 5
    "BEFORE",   # bit 6
    "BETWEEN",  # bit 7
    "BODY",     # bit 8
    "CAN",      # bit 9
    "CAUSE",    # bit 10
    "CHANGE",   # bit 11
    "DATA",     # bit 12
    "DO",       # bit 13
    "DOWN",     # bit 14
    "ENTITY",   # bit 15
    "FAR",      # bit 16
    "FEEL",     # bit 17
    "FROM",     # bit 18
    "GOOD",     # bit 19
    "HAVE",     # bit 20
    "HEAR",     # bit 21
    "HEAT",     # bit 22
    "HERE",     # bit 23
    "IN",       # bit 24
    "KIND",     # bit 25
    "KNOW",     # bit 26
    "LAST",     # bit 27
    "LEFT",     # bit 28
    "LESS",     # bit 29
    "LIFE",     # bit 30
    "LIGHT",    # bit 31
    "MAKE",     # bit 32
    "MANY",     # bit 33
    "MORE",     # bit 34
    "MOVE",     # bit 35
    "NEAR",     # bit 36
    "NEED",     # bit 37
    "NONE",     # bit 38
    "NOW",      # bit 39
    "ONE",      # bit 40
    "OPEN",     # bit 41
    "OTHER",    # bit 42
    "PART",     # bit 43
    "READ",     # bit 44
    "RIGHT",    # bit 45
    "SAY",      # bit 46
    "SEE",      # bit 47
    "SELF",     # bit 48
    "SIDE",     # bit 49
    "SOME",     # bit 50
    "SYMBOL",   # bit 51
    "THINK",    # bit 52
    "THIS",     # bit 53
    "TIME",     # bit 54
    "TO",       # bit 55
    "TOUCH",    # bit 56
    "UP",       # bit 57
    "USE",      # bit 58
    "WANT",     # bit 59
    "WITH",     # bit 60
    "WRITE",    # bit 61
    "YOU",      # bit 62
]

PRIME_TO_BIT: dict[str, int] = {name: idx for idx, name in enumerate(PRIME_INDEX)}

assert len(PRIME_INDEX) == 63, f"Expected 63 primes, got {len(PRIME_INDEX)}"


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

COMPOUND_FLAG: int      = 1 << 63
PAYLOAD_MASK: int       = (1 << 63) - 1           # low 63 bits

COMPOUND_ID_BITS: int   = 54
REL_FLAGS_BITS: int     = 5
SCHEMA_TAG_BITS: int    = 4

COMPOUND_ID_MASK: int   = (1 << COMPOUND_ID_BITS) - 1
REL_FLAGS_MASK: int     = (1 << REL_FLAGS_BITS) - 1
SCHEMA_TAG_MASK: int    = (1 << SCHEMA_TAG_BITS) - 1

CURRENT_SCHEMA_TAG: int = 1


class RelFlags:
    """Quick-hint bit flags stored in compound-payload rel_flags field."""
    HAS_CHILDREN      = 0x01
    HAS_RELATIONS     = 0x02
    HAS_RESOLVED_MASK = 0x04
    IS_NAMED          = 0x08
    NEEDS_ENRICHMENT  = 0x10


# ══════════════════════════════════════════════════════════════════════════════
# Backward-compatibility aliases (used by core/constants.py)
# ══════════════════════════════════════════════════════════════════════════════

PRIME_TO_INDEX: dict[str, int] = PRIME_TO_BIT
INDEX_TO_PRIME: dict[int, str] = {idx: name for idx, name in enumerate(PRIME_INDEX)}


# ══════════════════════════════════════════════════════════════════════════════
# Mode detection
# ══════════════════════════════════════════════════════════════════════════════

def is_compound_primebit(value: int) -> bool:
    """Return True if bit 63 is set (compound-payload mode)."""
    return bool((value >> 63) & 1)


# ══════════════════════════════════════════════════════════════════════════════
# Prime-mask helpers
# ══════════════════════════════════════════════════════════════════════════════

def prime_mask(prime_names: list[str]) -> int:
    """Return a prime-mask int for the given list of prime names.

    Raises ValueError for any unknown prime name.
    """
    value = 0
    for name in prime_names:
        bit = PRIME_TO_BIT.get(name)
        if bit is None:
            raise ValueError(f"Unknown prime name: {name!r}")
        value |= (1 << bit)
    return value


def has_prime(primebit: int, prime_name: str) -> bool:
    """Return True if the prime-mask has the given prime set.

    Raises if primebit is in compound mode — caller must resolve first.
    """
    if is_compound_primebit(primebit):
        raise ValueError("Cannot check prime on compound-mode PrimeBit — resolve first")
    bit = PRIME_TO_BIT.get(prime_name)
    if bit is None:
        raise ValueError(f"Unknown prime name: {prime_name!r}")
    return bool((primebit >> bit) & 1)


def has_all_primes(primebit: int, prime_names: list[str]) -> bool:
    """Return True if all given primes are set in the prime-mask."""
    if is_compound_primebit(primebit):
        raise ValueError("Cannot check primes on compound-mode PrimeBit — resolve first")
    for name in prime_names:
        if not has_prime(primebit, name):
            return False
    return True


def prime_names_from_mask(primebit: int) -> list[str]:
    """Return the sorted list of prime names set in a prime-mask PrimeBit."""
    if is_compound_primebit(primebit):
        raise ValueError("Cannot extract prime names from compound-mode PrimeBit")
    names: list[str] = []
    for idx, name in enumerate(PRIME_INDEX):
        if (primebit >> idx) & 1:
            names.append(name)
    return names


# ══════════════════════════════════════════════════════════════════════════════
# Compound payload pack / unpack
# ══════════════════════════════════════════════════════════════════════════════

def pack_compound_payload(
    compound_id: int,
    rel_flags: int,
    schema_tag: int = CURRENT_SCHEMA_TAG,
) -> int:
    """Pack fields into a 64-bit compound-mode PrimeBit value.

    Always sets bit 63.  schema_tag must not be 0 (reserved for legacy).
    Returns the full 64-bit PrimeBit integer.
    """
    if not (0 <= compound_id < (1 << COMPOUND_ID_BITS)):
        raise ValueError(f"compound_id out of range: {compound_id}")
    if not (0 <= rel_flags < (1 << REL_FLAGS_BITS)):
        raise ValueError(f"rel_flags out of range: {rel_flags}")
    if not (1 <= schema_tag < (1 << SCHEMA_TAG_BITS)):
        raise ValueError(f"schema_tag must be 1-15, got: {schema_tag}")

    payload  = compound_id & COMPOUND_ID_MASK
    payload |= (rel_flags  & REL_FLAGS_MASK)  << COMPOUND_ID_BITS
    payload |= (schema_tag & SCHEMA_TAG_MASK) << (COMPOUND_ID_BITS + REL_FLAGS_BITS)
    return COMPOUND_FLAG | payload


def unpack_compound_payload(primebit_value: int) -> tuple[int, int, int]:
    """Unpack a compound-mode PrimeBit into (compound_id, rel_flags, schema_tag).

    Raises ValueError if bit 63 is not set.
    """
    if not is_compound_primebit(primebit_value):
        raise ValueError("not a compound-mode PrimeBit")
    payload     = primebit_value & PAYLOAD_MASK
    compound_id = payload & COMPOUND_ID_MASK
    rel_flags   = (payload >> COMPOUND_ID_BITS) & REL_FLAGS_MASK
    schema_tag  = (payload >> (COMPOUND_ID_BITS + REL_FLAGS_BITS)) & SCHEMA_TAG_MASK
    return (compound_id, rel_flags, schema_tag)


def primebit_from_payload(raw_payload: int) -> int:
    """Given a raw 63-bit payload integer, return the full 64-bit compound PrimeBit.

    Input must always be a raw 63-bit payload (bit 63 clear).
    This function always sets bit 63.  It never accepts a pre-flagged value.
    """
    if raw_payload & COMPOUND_FLAG:
        raise ValueError("raw_payload must not have bit63 set — pass the raw 63-bit value")
    return raw_payload | COMPOUND_FLAG


def primebit_to_payload(value: int) -> int:
    """Strip bit 63 and return the raw 63-bit payload integer."""
    return value & PAYLOAD_MASK


# ══════════════════════════════════════════════════════════════════════════════
# PrimeBit class
# ══════════════════════════════════════════════════════════════════════════════

class PrimeBit:
    """64-bit encoding wrapping a prime-mask or compound-payload integer.

    All primebit fields on a Compound are PrimeBit instances.
    Serialisation boundary: to_dict() -> .value (int),  from_dict() -> PrimeBit(int).
    """

    __slots__ = ("value",)

    def __init__(self, value: int = 0):
        self.value = value

    # ── Factories ─────────────────────────────────────────────────────────

    @classmethod
    def from_prime_names(cls, names: list[str] | set[str]) -> PrimeBit:
        """Create a prime-mask PrimeBit from prime names."""
        return cls(prime_mask(list(names)))

    @classmethod
    def from_primes(cls, prime_indices: set[int]) -> PrimeBit:
        """Create PrimeBit from set of prime bit indices."""
        value = 0
        for idx in prime_indices:
            if idx < 0 or idx > 62:
                raise ValueError(f"Prime index {idx} out of range 0-62")
            value |= (1 << idx)
        return cls(value)

    @classmethod
    def from_compound_id(cls, compound_id: int, rel_flags: int = 0) -> PrimeBit:
        """Create a compound-payload PrimeBit."""
        return cls(pack_compound_payload(compound_id, rel_flags))

    # ── Queries ───────────────────────────────────────────────────────────

    @property
    def is_compound(self) -> bool:
        """True if this PrimeBit is in compound-payload mode (bit 63 set)."""
        return is_compound_primebit(self.value)

    @property
    def compound_id(self) -> int | None:
        """Extract compound_id from payload, or None if prime-mask mode."""
        if not self.is_compound:
            return None
        cid, _, _ = unpack_compound_payload(self.value)
        return cid

    def has_prime(self, prime_name: str) -> bool:
        """Check if the given prime is set (prime-mask mode only)."""
        return has_prime(self.value, prime_name)

    def has_all_primes(self, prime_names: list[str]) -> bool:
        """Check if all given primes are set."""
        return has_all_primes(self.value, prime_names)

    def get_prime_names(self) -> list[str]:
        """Return sorted list of prime names set in this mask."""
        return prime_names_from_mask(self.value)

    def get_primes(self) -> set[int]:
        """Return set of prime bit indices (empty if compound mode)."""
        if self.is_compound:
            return set()
        return {idx for idx in range(63) if (self.value >> idx) & 1}

    # ── Bitwise operators (prime-mask mode only) ──────────────────────────

    def __and__(self, other: PrimeBit) -> PrimeBit:
        if self.is_compound or other.is_compound:
            raise ValueError("Cannot AND compound-mode PrimeBits")
        return PrimeBit(self.value & other.value)

    def __or__(self, other: PrimeBit) -> PrimeBit:
        if self.is_compound or other.is_compound:
            raise ValueError("Cannot OR compound-mode PrimeBits")
        return PrimeBit(self.value | other.value)

    def __xor__(self, other: PrimeBit) -> PrimeBit:
        if self.is_compound or other.is_compound:
            raise ValueError("Cannot XOR compound-mode PrimeBits")
        return PrimeBit(self.value ^ other.value)

    def __invert__(self) -> PrimeBit:
        if self.is_compound:
            raise ValueError("Cannot invert compound-mode PrimeBit")
        return PrimeBit((~self.value) & PAYLOAD_MASK)

    def implies(self, other: PrimeBit) -> PrimeBit:
        """Logical implication: self -> other."""
        if self.is_compound or other.is_compound:
            raise ValueError("Cannot IMPLY with compound-mode PrimeBits")
        return PrimeBit(((~self.value) & PAYLOAD_MASK) | other.value)

    # ── Comparison ────────────────────────────────────────────────────────

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrimeBit):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    # ── Display ───────────────────────────────────────────────────────────

    def __str__(self) -> str:
        if self.is_compound:
            cid, flags, tag = unpack_compound_payload(self.value)
            return f"PrimeBit(compound_id={cid}, rel_flags={flags:#04x}, schema={tag})"
        return f"PrimeBit({sorted(self.get_prime_names())})"

    def __repr__(self) -> str:
        return str(self)