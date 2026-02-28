"""
DATA Prime - Data structuring and processing.
"""

import time
import json
import os
from typing import Dict, Any, List, Tuple, Set
from core.prime_base import Prime, PrimeError
from core.compound import Compound
from core.primebit import PrimeBit
from core.constants import PRIME_TO_INDEX, INDEX_TO_PRIME


class DATA(Prime):
    """DATA prime for structuring observations."""
    
    def __init__(self):
        super().__init__("DATA")
        # Symbol to prime mapping (starts with prime names themselves)
        self._symbol_map = self._initialize_symbol_map()
        # Logic token to compound ID mapping
        self._logic_token_map = self._load_logic_tokens()
        # Placeholder compounds awaiting resolution
        self._placeholder_registry = {}
        # Next placeholder ID
        self._next_placeholder_id = 0
        # Statistics
        self._stats = {
            "observations_processed": 0,
            "tokens_processed": 0,
            "primes_found": 0,
            "placeholders_created": 0,
            "logic_operators_found": 0
        }
    
    def _load_logic_tokens(self) -> Dict[str, int]:
        """Load logic token mappings from logic_compounds.json."""
        logic_token_map = {}
        
        try:
            # Get path to logic_compounds.json
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logic_compounds_path = os.path.join(current_dir, "..", "core", "logic_compounds.json")
            
            if not os.path.exists(logic_compounds_path):
                print(f"DATA: Warning - logic_compounds.json not found")
                return logic_token_map
            
            with open(logic_compounds_path, 'r') as f:
                compounds_list = json.load(f)
            
            # Build token -> ID mapping
            for compound_dict in compounds_list:
                compound_id = compound_dict["id"]
                # Map each token variant (case-insensitive)
                for token in compound_dict.get("token_variants", []):
                    logic_token_map[token.lower()] = compound_id
            
            print(f"DATA: Loaded {len(logic_token_map)} logic token mappings")
            return logic_token_map
        
        except Exception as e:
            print(f"DATA: Error loading logic tokens: {e}")
            return logic_token_map
        
    def _initialize_symbol_map(self) -> Dict[str, int]:
        """Initialize symbol map with prime names and common variations."""
        symbol_map = {}
        
        # Map prime names (lowercase) to their indices
        for prime_name, idx in PRIME_TO_INDEX.items():
            symbol_map[prime_name.lower()] = idx
        
        # Add common variations/aliases
        variations = {
            "moving": PRIME_TO_INDEX["MOVE"],
            "movement": PRIME_TO_INDEX["MOVE"],
            "reads": PRIME_TO_INDEX["READ"],
            "reading": PRIME_TO_INDEX["READ"],
            "thinks": PRIME_TO_INDEX["THINK"],
            "thinking": PRIME_TO_INDEX["THINK"],
            "knows": PRIME_TO_INDEX["KNOW"],
            "knowledge": PRIME_TO_INDEX["KNOW"],
            "feels": PRIME_TO_INDEX["FEEL"],
            "feeling": PRIME_TO_INDEX["FEEL"],
            "wants": PRIME_TO_INDEX["WANT"],
            "wanting": PRIME_TO_INDEX["WANT"],
            "needs": PRIME_TO_INDEX["NEED"],
            "needing": PRIME_TO_INDEX["NEED"],
            "sees": PRIME_TO_INDEX["SEE"],
            "seeing": PRIME_TO_INDEX["SEE"],
            "hears": PRIME_TO_INDEX["HEAR"],
            "hearing": PRIME_TO_INDEX["HEAR"],
            "says": PRIME_TO_INDEX["SAY"],
            "saying": PRIME_TO_INDEX["SAY"],
            "writes": PRIME_TO_INDEX["WRITE"],
            "writing": PRIME_TO_INDEX["WRITE"],
        }
        
        symbol_map.update(variations)
        return symbol_map
    
    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        Process data based on context.
        
        Autonomous mode (from queue):
        {
            "observation": raw_observation_dict,
            "mode": "autonomous"
        }
        
        Consultation mode (on-demand):
        {
            "input": raw_input_text,
            "mode": "consultation"
        }
        
        Or for structured data:
        {
            "data": structured_dict,
            "mode": "process"
        }
        """
        mode = context.get("mode", "autonomous")
        
        if mode == "autonomous" and "observation" in context:
            return self._structure_observation(context["observation"])
        elif mode == "consultation" and "input" in context:
            return self._consultation_mode(context)
        elif "query" in context:
            return self._handle_query(context)
        else:
            raise PrimeError("DATA: Invalid context - need observation, input, or query")
    
    def _structure_observation(self, raw_obs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure a raw observation into individual tokens.
        
        Returns a dict with tokens list - each token is independent
        but preserves observation context (raw text, sibling tokens).
        """
        self._stats["observations_processed"] += 1
        
        # Generate unique observation ID
        observation_id = f"obs_{int(time.time() * 1000)}"
        
        # Extract tokens
        tokens = raw_obs.get("preliminary_tokens", [])
        if not tokens and "raw_input" in raw_obs:
            tokens = self._tokenize(raw_obs["raw_input"])
        
        raw_input_text = raw_obs.get("raw_input", " ".join(tokens))
        
        self._stats["tokens_processed"] += len(tokens)
        
        # Process each token independently
        token_items = []
        
        for i, token in enumerate(tokens):
            token_lower = token.lower()
            
            # Check if token maps to a logic operator first
            logic_compound_id = None
            prime_idx = None
            is_known = False
            token_type = "data"  # "logic" or "data"
            
            if token_lower in self._logic_token_map:
                # Token is a logic operator (e.g., "if", "and", "or")
                logic_compound_id = self._logic_token_map[token_lower]
                is_known = True
                token_type = "logic"
                self._stats["logic_operators_found"] += 1
            elif token_lower in self._symbol_map:
                # Token maps to a known prime
                prime_idx = self._symbol_map[token_lower]
                is_known = True
                self._stats["primes_found"] += 1
            else:
                self._stats["placeholders_created"] += 1
            
            # Create token item - each will become its own compound
            token_item = {
                "token": token,
                "token_lower": token_lower,
                "position": i,
                "is_known": is_known,
                "token_type": token_type,  # "logic" or "data"
                "logic_compound_id": logic_compound_id,  # ID 100-109 if logic operator
                "prime_idx": prime_idx,
                "prime_name": INDEX_TO_PRIME[prime_idx] if prime_idx is not None else None
            }
            
            token_items.append(token_item)
        
        # Return structured observation with token list + context
        structured = {
            "observation_id": observation_id,
            "tokens": token_items,  # List of individual token items
            "raw_input": raw_input_text,
            "all_tokens": tokens,  # Complete list of all tokens in observation
            "metadata": {
                "source": raw_obs.get("metadata", {}).get("source", "unknown"),
                "mode": "autonomous",
                "processed_at": time.time(),
                "token_count": len(tokens),
                "raw_observation": raw_obs
            }
        }
        
        print(f"DATA: Structured observation {observation_id}: {len(token_items)} tokens")
        known_tokens = [t["token"] for t in token_items if t["is_known"]]
        if known_tokens:
            print(f"DATA: Known primes: {known_tokens}")
        
        return structured
    
    def _consultation_mode(self, context: Dict[str, Any]) -> Compound:
        """Handle on-demand consultation."""
        input_text = context.get("input", "")
        
        # Tokenize
        tokens = self._tokenize(input_text)
        
        # Process similar to autonomous mode but return Compound
        primes = []
        for token in tokens:
            token_lower = token.lower()
            if token_lower in self._symbol_map:
                primes.append(self._symbol_map[token_lower])
        
        # Create compound with new canonical schema
        primebit = PrimeBit.from_primes(set(primes)) if primes else PrimeBit.from_prime_names({"DATA"})
        
        compound = Compound(
            id=-1,  # Temporary
            text=input_text,
            primebit=primebit,
            compound_type="data",
            provenance_data={
                "provenance": ["DATA_consultation"],
                "raw_observation": input_text,
                "observation_tokens": tokens,
                "source": "consultation"
            },
            refinement_data={
                "usage_count": 0,
                "success_rate": 0.0
            }
        )
        
        return compound
    
    def _handle_query(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle queries about DATA state."""
        query = context.get("query", "")
        
        if query == "stats":
            return {
                "stats": self._stats,
                "symbol_map_size": len(self._symbol_map),
                "placeholder_registry_size": len(self._placeholder_registry)
            }
        elif query == "symbols":
            # Return symbol mapping (limited)
            limited_map = {}
            for symbol, idx in list(self._symbol_map.items())[:20]:  # First 20
                limited_map[symbol] = INDEX_TO_PRIME[idx]
            return {"symbols": limited_map}
        else:
            return {"error": f"Unknown query: {query}"}
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Basic tokenization - split on whitespace and punctuation
        import re
        # Split on whitespace and common punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _create_placeholder_id(self) -> str:
        """Generate a unique placeholder ID."""
        placeholder_id = f"ph_{self._next_placeholder_id}"
        self._next_placeholder_id += 1
        return placeholder_id
    
    def add_symbol_mapping(self, symbol: str, prime_name: str) -> None:
        """Add a symbol to prime mapping."""
        if prime_name in PRIME_TO_INDEX:
            self._symbol_map[symbol.lower()] = PRIME_TO_INDEX[prime_name]
            print(f"DATA: Added mapping: '{symbol}' -> {prime_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DATA statistics."""
        return self._stats.copy()


# Singleton instance
data = DATA()