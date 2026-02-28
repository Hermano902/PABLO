"""
THINK Prime - Cognitive coordination.
"""

from typing import Dict, Any
from core.prime_base import Prime
from core.compound import Compound
from core.primebit import PrimeBit


class THINK(Prime):
    """THINK prime for cognitive coordination."""
    
    def __init__(self):
        super().__init__("THINK")
        
    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        THINK prime interface.
        
        Context examples:
        {
            "goal": "understand",
            "state": current_state,
            "query": "what is this?"
        }
        """
        # For Phase 1C, THINK is a simple coordinator
        goal = context.get("goal", "default")
        
        if goal == "understand":
            return self._attempt_understanding(context)
        else:
            # Return a simple THINK compound
            primebit = PrimeBit.from_prime_names({"THINK"})
            return Compound(
                id=-1,
                text="think",
                primebit=primebit,
                compound_type="internal",
                provenance_data={
                    "provenance": ["THINK_execution"],
                    "source": "THINK"
                }
            )
    
    def _attempt_understanding(self, context: Dict[str, Any]) -> Compound:
        """Attempt to understand something."""
        # In later phases, this will coordinate between primes
        # For now, create a compound with THINK prime
        primebit = PrimeBit.from_prime_names({"THINK", "KNOW"})
        
        return Compound(
            id=-1,
            text="understand",
            primebit=primebit,
            compound_type="internal",
            provenance_data={
                "provenance": ["THINK_understanding"],
                "source": "THINK"
            }
        )


# Singleton instance
think = THINK()