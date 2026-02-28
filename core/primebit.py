"""
PrimeBit implementation - 64-bit integer encoding for prime sets.
"""

from typing import Set, Union, Optional
from .constants import (
    PRIME_MASK, 
    COMPOUND_FLAG_BIT, 
    COMPOUND_FLAG_MASK,
    PRIME_TO_INDEX,
    INDEX_TO_PRIME
)


class PrimeBit:
    """64-bit encoding for prime sets with compound flag."""
    
    def __init__(self, value: int):
        self.value = value
        self.validate()
    
    def validate(self) -> None:
        """Raise exception on invalid state."""
        is_compound = self.is_compound
        
        if is_compound:
            # Compound flag set: bits 0-62 should be valid ID
            compound_id = self.compound_id
            if compound_id < 0:
                raise ValueError(f"Compound ID cannot be negative: {compound_id}")
        else:
            # Prime bitset: all set bits must be 0-62
            for bit in range(64):
                if (self.value >> bit) & 1:
                    if bit > 62:
                        raise ValueError(f"Invalid prime index {bit}, must be 0-62")
    
    @property
    def is_compound(self) -> bool:
        """Check if this PrimeBit represents a compound reference."""
        return bool((self.value >> COMPOUND_FLAG_BIT) & 1)
    
    @property
    def compound_id(self) -> Optional[int]:
        """Get compound ID if this is a compound reference."""
        if self.is_compound:
            return self.value & PRIME_MASK
        return None
    
    @classmethod
    def from_primes(cls, prime_indices: Set[int]) -> 'PrimeBit':
        """Create PrimeBit from set of prime indices."""
        value = 0
        for idx in prime_indices:
            if idx < 0 or idx > 62:
                raise ValueError(f"Prime index {idx} out of range 0-62")
            value |= (1 << idx)
        return cls(value)
    
    @classmethod
    def from_prime_names(cls, prime_names: Set[str]) -> 'PrimeBit':
        """Create PrimeBit from set of prime names."""
        indices = {PRIME_TO_INDEX[name] for name in prime_names}
        return cls.from_primes(indices)
    
    @classmethod
    def from_compound_id(cls, compound_id: int) -> 'PrimeBit':
        """Create PrimeBit referencing a compound."""
        if compound_id < 0:
            raise ValueError(f"Compound ID cannot be negative: {compound_id}")
        value = compound_id | COMPOUND_FLAG_MASK
        return cls(value)
    
    def get_primes(self) -> Set[int]:
        """Get set of prime indices (empty if compound reference)."""
        if self.is_compound:
            return set()
        
        primes = set()
        for idx in range(63):  # 0-62
            if (self.value >> idx) & 1:
                primes.add(idx)
        return primes
    
    def get_prime_names(self) -> Set[str]:
        """Get set of prime names (empty if compound reference)."""
        return {INDEX_TO_PRIME[idx] for idx in self.get_primes()}
    
    def has_prime(self, prime_idx: int) -> bool:
        """Check if prime index is set."""
        if prime_idx < 0 or prime_idx > 62:
            raise ValueError(f"Prime index {prime_idx} out of range 0-62")
        return bool((self.value >> prime_idx) & 1)
    
    def has_prime_name(self, prime_name: str) -> bool:
        """Check if prime name is set."""
        prime_idx = PRIME_TO_INDEX[prime_name]
        return self.has_prime(prime_idx)
    
    # Bitwise operations
    
    def __and__(self, other: 'PrimeBit') -> 'PrimeBit':
        if self.is_compound or other.is_compound:
            raise ValueError("Cannot AND compound references directly")
        return PrimeBit(self.value & other.value)
    
    def __or__(self, other: 'PrimeBit') -> 'PrimeBit':
        if self.is_compound or other.is_compound:
            raise ValueError("Cannot OR compound references directly")
        return PrimeBit(self.value | other.value)
    
    def __invert__(self) -> 'PrimeBit':
        if self.is_compound:
            raise ValueError("Cannot NOT a compound reference")
        return PrimeBit((~self.value) & PRIME_MASK)
    
    def __xor__(self, other: 'PrimeBit') -> 'PrimeBit':
        if self.is_compound or other.is_compound:
            raise ValueError("Cannot XOR compound references directly")
        return PrimeBit(self.value ^ other.value)
    
    def implies(self, other: 'PrimeBit') -> 'PrimeBit':
        """Logical implication: self → other."""
        if self.is_compound or other.is_compound:
            raise ValueError("Cannot IMPLY with compound references")
        return PrimeBit((~self.value) | other.value) & PRIME_MASK
    
    # Comparison operators
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrimeBit):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    def __str__(self) -> str:
        if self.is_compound:
            return f"PrimeBit(compound_id={self.compound_id})"
        else:
            primes = sorted(self.get_prime_names())
            return f"PrimeBit({primes})"
    
    def __repr__(self) -> str:
        return str(self)