"""
Compound Registry with structured compounds for logical operators.
"""

import threading
import json
import time
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum


class CompoundType(Enum):
    """Types of compounds."""
    BAG = "bag"           # Unordered set of primes
    STRUCTURED = "structured"  # Ordered structure with operator
    RELATION = "relation"      # Role-based relationship
    EPHEMERAL = "ephemeral"    # Temporary/placeholder


class ChildKind(Enum):
    """Types of children in structured compounds."""
    PRIME = "prime"
    COMPOUND = "compound"
    OPERATOR = "operator"


@dataclass
class ChildDescriptor:
    """Descriptor for a child in structured compounds."""
    kind: ChildKind
    value: Union[int, str]  # Prime index, compound ID, or operator name
    role: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "kind": self.kind.value,
            "value": self.value,
            "role": self.role,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChildDescriptor':
        """Create from dict."""
        return cls(
            kind=ChildKind(data["kind"]),
            value=data["value"],
            role=data.get("role"),
            meta=data.get("meta", {})
        )


@dataclass
class RelationDescriptor:
    """Descriptor for a role-based relationship."""
    role: str  # e.g., "PART", "AFTER", "KIND"
    target: int  # Compound ID
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "role": self.role,
            "target": self.target,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationDescriptor':
        """Create from dict."""
        return cls(
            role=data["role"],
            target=data["target"],
            meta=data.get("meta", {})
        )


class CompoundRegistry:
    """Registry for managing compounds with structured operators."""
    
    def __init__(self, enable_persistence: bool = True):
        self._store = {}  # ID -> CompoundRecord
        self._prime_index = {}  # Prime mask -> list of compound IDs
        self._name_index = {}  # Name/op -> list of compound IDs
        self._type_index = {}  # Compound type -> list of compound IDs
        self._next_id = 0
        self._lock = threading.RLock()
        self._enable_persistence = enable_persistence
        
        # Cache for resolved prime masks
        self._resolved_cache = {}
        self._cache_size = 1000
        self._cache_hits = 0
        self._cache_misses = 0
    
    def create_compound(
        self,
        compound_type: CompoundType = CompoundType.BAG,
        name: Optional[str] = None,
        prime_mask: int = 0,
        primes: Optional[List[str]] = None,
        children: Optional[List[ChildDescriptor]] = None,
        relations: Optional[List[RelationDescriptor]] = None,
        core: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        refinement: Optional[Dict[str, Any]] = None,
        signals: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create a new compound and return its ID."""
        with self._lock:
            compound_id = self._next_id
            self._next_id += 1
            
            # Calculate resolved prime mask
            resolved_prime_mask = self._calculate_resolved_mask(
                prime_mask, children or []
            )
            
            # Create compound record
            compound = {
                "id": compound_id,
                "compound_type": compound_type.value,
                "name": name,
                "prime_mask": prime_mask,
                "resolved_prime_mask": resolved_prime_mask,
                "primes": primes or [],
                "children": [child.to_dict() for child in (children or [])],
                "relations": [rel.to_dict() for rel in (relations or [])],
                "core": core or self._default_core(),
                "provenance": provenance or self._default_provenance(),
                "refinement": refinement or self._default_refinement(),
                "signals": signals or self._default_signals(),
                "context": context or {},
                "created_at": time.time(),
                "updated_at": time.time(),
                "version": 1
            }
            
            # Store
            self._store[compound_id] = compound
            
            # Update indexes
            self._update_indexes(compound_id, compound)
            
            # Clear cache for this compound and its dependents
            self._clear_cache_for(compound_id)
            
            return compound_id
    
    def get_compound(self, compound_id: int) -> Optional[Dict[str, Any]]:
        """Get a compound by ID."""
        with self._lock:
            return self._store.get(compound_id)
    
    def get_compound_main(self, compound_id: int) -> Optional[Dict[str, Any]]:
        """Get only main fields of a compound (lightweight)."""
        with self._lock:
            if compound_id not in self._store:
                return None
            
            compound = self._store[compound_id]
            return {
                "id": compound["id"],
                "compound_type": compound["compound_type"],
                "name": compound["name"],
                "prime_mask": compound["prime_mask"],
                "resolved_prime_mask": compound["resolved_prime_mask"],
                "primes": compound["primes"],
                "version": compound["version"],
                "signals": compound["signals"]
            }
    
    def get_compound_relations(self, compound_id: int) -> Optional[Dict[str, Any]]:
        """Get relation/child data of a compound."""
        with self._lock:
            if compound_id not in self._store:
                return None
            
            compound = self._store[compound_id]
            return {
                "children": compound["children"],
                "relations": compound["relations"]
            }
    
    def get_compound_exec(self, compound_id: int) -> Optional[Dict[str, Any]]:
        """Get execution metadata of a compound."""
        with self._lock:
            if compound_id not in self._store:
                return None
            
            compound = self._store[compound_id]
            return {
                "name": compound["name"],
                "compound_type": compound["compound_type"],
                "arg_spec": self._extract_arg_spec(compound),
                "eval_hints": compound.get("core", {}).get("eval_hints", {})
            }
    
    def _extract_arg_spec(self, compound: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract argument specification from compound."""
        arg_spec = []
        
        if compound["compound_type"] == CompoundType.STRUCTURED.value:
            for child_data in compound.get("children", []):
                child = ChildDescriptor.from_dict(child_data)
                if child.role:
                    arg_spec.append({
                        "role": child.role,
                        "kind": child.kind.value,
                        "optional": child.meta.get("optional", False)
                    })
        
        return arg_spec
    
    def update_compound(
        self,
        compound_id: int,
        updates: Dict[str, Any],
        increment_version: bool = True
    ) -> bool:
        """Update an existing compound."""
        with self._lock:
            if compound_id not in self._store:
                return False
            
            compound = self._store[compound_id]
            
            # Apply updates
            for key, value in updates.items():
                if key in ["children", "relations"]:
                    # Handle structured updates
                    if key == "children":
                        children = [ChildDescriptor.from_dict(c) for c in value]
                        compound["children"] = [c.to_dict() for c in children]
                    elif key == "relations":
                        relations = [RelationDescriptor.from_dict(r) for r in value]
                        compound["relations"] = [r.to_dict() for r in relations]
                elif key in ["prime_mask", "primes"]:
                    # Update prime-related fields
                    compound[key] = value
                elif key in compound:
                    # Update other fields
                    compound[key] = value
            
            # Recalculate resolved prime mask
            children = [ChildDescriptor.from_dict(c) for c in compound.get("children", [])]
            compound["resolved_prime_mask"] = self._calculate_resolved_mask(
                compound.get("prime_mask", 0),
                children
            )
            
            # Update metadata
            if increment_version:
                compound["version"] += 1
            compound["updated_at"] = time.time()
            
            # Update indexes
            self._update_indexes(compound_id, compound)
            
            # Clear cache
            self._clear_cache_for(compound_id)
            
            return True
    
    def resolve_prime_mask(self, compound_id: int) -> int:
        """Get the resolved prime mask for a compound (with caching)."""
        # Check cache
        if compound_id in self._resolved_cache:
            self._cache_hits += 1
            return self._resolved_cache[compound_id]
        
        self._cache_misses += 1
        
        with self._lock:
            if compound_id not in self._store:
                return 0
            
            compound = self._store[compound_id]
            mask = compound["resolved_prime_mask"]
            
            # Cache result
            if len(self._resolved_cache) >= self._cache_size:
                # Remove oldest (simple FIFO)
                self._resolved_cache.pop(next(iter(self._resolved_cache)))
            self._resolved_cache[compound_id] = mask
            
            return mask
    
    def _calculate_resolved_mask(
        self,
        prime_mask: int,
        children: List[ChildDescriptor]
    ) -> int:
        """Calculate resolved prime mask including children."""
        mask = prime_mask
        
        for child in children:
            if child.kind == ChildKind.PRIME:
                # Child is a prime index
                prime_idx = child.value
                if isinstance(prime_idx, int) and 0 <= prime_idx <= 62:
                    mask |= (1 << prime_idx)
            elif child.kind == ChildKind.COMPOUND:
                # Child is a compound ID - recursively include its mask
                child_mask = self.resolve_prime_mask(child.value)
                mask |= child_mask
        
        return mask
    
    def find_by_prime_mask(
        self,
        prime_mask: int,
        operation: str = "contains",
        compound_type: Optional[str] = None
    ) -> List[int]:
        """Find compounds by prime mask."""
        with self._lock:
            results = []
            
            for cid, compound in self._store.items():
                # Filter by type if specified
                if compound_type and compound["compound_type"] != compound_type:
                    continue
                
                cmp_mask = compound["resolved_prime_mask"]
                
                if operation == "contains":
                    # Check if compound contains all bits in prime_mask
                    if (cmp_mask & prime_mask) == prime_mask:
                        results.append(cid)
                elif operation == "intersects":
                    # Check if compound intersects with prime_mask
                    if (cmp_mask & prime_mask) != 0:
                        results.append(cid)
                elif operation == "equals":
                    # Check if compound exactly matches prime_mask
                    if cmp_mask == prime_mask:
                        results.append(cid)
            
            return results
    
    def find_by_name(self, name: str) -> List[int]:
        """Find compounds by name/operator."""
        with self._lock:
            return self._name_index.get(name, [])
    
    def _update_indexes(self, compound_id: int, compound: Dict[str, Any]) -> None:
        """Update all indexes for a compound."""
        # Prime index
        mask = compound["resolved_prime_mask"]
        if mask not in self._prime_index:
            self._prime_index[mask] = []
        if compound_id not in self._prime_index[mask]:
            self._prime_index[mask].append(compound_id)
        
        # Name index
        if compound["name"]:
            name = compound["name"]
            if name not in self._name_index:
                self._name_index[name] = []
            if compound_id not in self._name_index[name]:
                self._name_index[name].append(compound_id)
        
        # Type index
        ctype = compound["compound_type"]
        if ctype not in self._type_index:
            self._type_index[ctype] = []
        if compound_id not in self._type_index[ctype]:
            self._type_index[ctype].append(compound_id)
    
    def _clear_cache_for(self, compound_id: int) -> None:
        """Clear cache entries for a compound and its dependents."""
        # Remove from main cache
        self._resolved_cache.pop(compound_id, None)
        
        # Also clear any cache entries that might depend on this compound
        # (In a real implementation, you'd track dependencies)
    
    def _default_core(self) -> Dict[str, Any]:
        return {
            "token": None,
            "token_lower": None,
            "prime_name": None,
            "is_known": False,
            "eval_hints": {}
        }
    
    def _default_provenance(self) -> Dict[str, Any]:
        return {
            "created_at": time.time(),
            "provenance": [],
            "source": "unknown",
            "observation_id": None,
            "raw_observation": None,
            "observation_tokens": [],
            "sibling_tokens": [],
            "position": None
        }
    
    def _default_refinement(self) -> Dict[str, Any]:
        return {
            "usage_count": 0,
            "success_rate": 0.0,
            "query_count": 0,
            "candidate_interpretations": [],
            "confidence_score": 0.0
        }
    
    def _default_signals(self) -> Dict[str, Any]:
        return {
            "score": 0.0,
            "confidence": 0.0,
            "recency": 1.0,
            "last_updated": time.time()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            type_counts = {}
            for compound in self._store.values():
                ctype = compound["compound_type"]
                type_counts[ctype] = type_counts.get(ctype, 0) + 1
            
            return {
                "total_compounds": len(self._store),
                "type_counts": type_counts,
                "next_id": self._next_id,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_rate": (
                    self._cache_hits / (self._cache_hits + self._cache_misses)
                    if (self._cache_hits + self._cache_misses) > 0 else 0.0
                )
            }


# Global registry instance
registry = CompoundRegistry()