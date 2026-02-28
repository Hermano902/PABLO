"""
Compound data structure for prime-grounded knowledge.
"""

from typing import Dict, List, Set, Tuple, Any, Optional
from datetime import datetime
from .constants import PRIME_TO_INDEX, INDEX_TO_PRIME
from .primebit import PrimeBit
import uuid


class Compound:
    """Prime-grounded structured data with categorized metadata."""
    
    def __init__(
        self,
        id: int,
        primebit: PrimeBit,
        text: str = "",
        relations: Optional[List[Tuple[str, int]]] = None,
        children: Optional[List[int]] = None,
        compound_type: str = "internal",  # "logic", "data", "aggregate", "definition", "internal"
        grounded: bool = False,
        version: int = 0,
        operation_arity: Optional[int] = None,
        slot_names: Optional[List[str]] = None,
        core_data: Optional[Dict[str, Any]] = None,
        provenance_data: Optional[Dict[str, Any]] = None,
        refinement_data: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.primebit = primebit
        self.text = text
        self.relations = relations or []
        self.children = children or []
        self.compound_type = compound_type
        self.grounded = grounded
        self.version = version
        self.operation_arity = operation_arity
        self.slot_names = slot_names or []
        
        # Categorized metadata
        self.core = core_data or self._default_core()
        self.provenance = provenance_data or self._default_provenance()
        self.refinement = refinement_data or self._default_refinement()
        
        self.validate()
    
    def _default_core(self) -> Dict[str, Any]:
        """Default core data."""
        return {
            "token": None,
            "token_lower": None,
            "prime_name": None,
            "is_known": False
        }
    
    def _default_provenance(self) -> Dict[str, Any]:
        """Default provenance data."""
        return {
            "created_at": datetime.now().isoformat(),
            "provenance": [],
            "source": "unknown",
            "observation_id": None,
            "raw_observation": None,
            "observation_tokens": [],
            "sibling_tokens": [],
            "position": None
        }
    
    def _default_refinement(self) -> Dict[str, Any]:
        """Default refinement data."""
        return {
            "usage_count": 0,
            "success_rate": 0.0,
            "query_count": 0,
            "candidate_interpretations": [],
            "confidence_score": 0.0
        }
    
    def get_data(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get data from specified categories.
        
        Args:
            categories: List of category names ('core', 'provenance', 'refinement')
                       If None, returns all categories.
        
        Returns:
            Dictionary with requested categories.
        """
        if categories is None:
            categories = ["core", "provenance", "refinement"]
        
        result = {}
        if "core" in categories:
            result["core"] = self.core.copy()
        if "provenance" in categories:
            result["provenance"] = self.provenance.copy()
        if "refinement" in categories:
            result["refinement"] = self.refinement.copy()
        
        return result
    
    def update_core(self, updates: Dict[str, Any]) -> None:
        """Update core data category."""
        self.core.update(updates)
    
    def update_provenance(self, updates: Dict[str, Any]) -> None:
        """Update provenance data category."""
        self.provenance.update(updates)
    
    def update_refinement(self, updates: Dict[str, Any]) -> None:
        """Update refinement data category."""
        self.refinement.update(updates)
    
    
    def validate(self) -> None:
        """Validate compound structure."""
        # Validate prime indices
        if not self.primebit.is_compound:
            primes = self.primebit.get_primes()
            for prime_idx in primes:
                if prime_idx < 0 or prime_idx > 62:
                    raise ValueError(f"Invalid prime index {prime_idx}, must be 0-62")
        
        # Validate relations (role-based links)
        for role, target_id in self.relations:
            if not isinstance(role, str):
                raise ValueError(f"Relation role must be string, got {type(role)}")
            if not isinstance(target_id, int) or target_id < 0:
                raise ValueError(f"Target ID must be non-negative int, got {target_id}")
        
        # Validate compound_type
        valid_types = ["logic", "data", "aggregate", "definition", "internal"]
        if self.compound_type not in valid_types:
            raise ValueError(f"Invalid compound_type: {self.compound_type}. Must be one of {valid_types}")
        
        # Validate logic compound specifics
        if self.compound_type == "logic":
            if self.operation_arity is None:
                raise ValueError("Logic compounds must have operation_arity")
            # slot_names must be a list (can be empty for 0-arity constants like TRUE/FALSE)
            if not isinstance(self.slot_names, list):
                raise ValueError("Logic compounds must have slot_names as a list")
    
    def increment_usage(self) -> None:
        """Increment usage count."""
        self.refinement["usage_count"] += 1
    
    def update_success_rate(self, success: bool) -> None:
        """Update success rate with new outcome."""
        current_rate = self.refinement["success_rate"]
        usage = self.refinement["usage_count"]
        
        # Simple moving average
        new_rate = ((current_rate * usage) + (1.0 if success else 0.0)) / (usage + 1)
        self.refinement["success_rate"] = new_rate
    
    def add_provenance_step(self, step: str) -> None:
        """Add a step to the provenance trail."""
        self.provenance["provenance"].append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "text": self.text,
            "compound_type": self.compound_type,
            "grounded": self.grounded,
            "version": self.version,
            "primebit_value": self.primebit.value,
            "relations": self.relations,
            "children": self.children,
            "core": self.core.copy(),
            "provenance": self.provenance.copy(),
            "refinement": self.refinement.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Compound':
        """Create Compound from dictionary representation."""
        primebit = PrimeBit(data["primebit_value"])
        compound = cls(
            id=data["id"],
            text=data.get("text", ""),
            primebit=primebit,
            relations=data.get("relations", []),
            children=data.get("children", []),
            compound_type=data.get("compound_type", "internal"),
            grounded=data.get("grounded", False),
            version=data.get("version", 0),
            operation_arity=data.get("operation_arity"),
            slot_names=data.get("slot_names")
        )
        # Restore categorized data
        if "core" in data:
            compound.core = data["core"]
        if "provenance" in data:
            compound.provenance = data["provenance"]
        if "refinement" in data:
            compound.refinement = data["refinement"]
        return compound
    
    def __str__(self) -> str:
        if self.primebit.is_compound:
            prime_str = f"compound:{self.primebit.compound_id}"
        else:
            prime_names = sorted(self.primebit.get_prime_names())
            prime_str = ",".join(prime_names)
        
        text_str = f'"{self.text}"' if self.text else "<empty>"
        return f"Compound(id={self.id}, text={text_str}, type={self.compound_type}, primes=[{prime_str}])"
    
    def __repr__(self) -> str:
        return str(self)