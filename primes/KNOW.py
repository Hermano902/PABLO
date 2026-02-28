"""
KNOW Prime - Knowledge storage and retrieval with persistence.
"""

import time
import threading
import queue
import json
import os
from typing import Dict, Any, Optional, List
from core.prime_base import Prime, PrimeError
from core.compound import Compound
from core.primebit import PrimeBit
from core.queues import observation_queue, prime_registry
from core.persistence import persistence


class KNOW(Prime):
    """KNOW prime for knowledge storage and retrieval."""
    
    def __init__(self, enable_persistence: bool = True):
        super().__init__("KNOW")
        self._store = {}  # ID -> Compound
        self._next_id = 200  # Start after system compounds (0-99) and logic compounds (100-199)
        self._lock = threading.RLock()
        self._load_logic_compounds()  # Load system logic operators
        self._input_thread = None
        self._running = False
        self._stats = {
            "compounds_stored": 0,
            "compounds_retrieved": 0,
            "queries_processed": 0,
            "errors": 0,
            "loads_from_disk": 0,
            "saves_to_disk": 0
        }
        self._enable_persistence = enable_persistence
        self._autosave_interval = 30  # seconds
        self._last_autosave = 0
        self._autosave_thread = None
    
    def _load_logic_compounds(self) -> None:
        """Load pre-defined logic compounds from JSON file."""
        try:
            # Get path to logic_compounds.json
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logic_compounds_path = os.path.join(current_dir, "..", "core", "logic_compounds.json")
            
            if not os.path.exists(logic_compounds_path):
                print(f"KNOW: Warning - logic_compounds.json not found at {logic_compounds_path}")
                return
            
            with open(logic_compounds_path, 'r') as f:
                compounds_list = json.load(f)
            
            with self._lock:
                for compound_dict in compounds_list:
                    try:
                        # Create Compound from dict
                        compound = Compound.from_dict(compound_dict)
                        compound_id = compound_dict["id"]
                        self._store[compound_id] = compound
                        
                        # Update _next_id if needed (should be 200 already)
                        if compound_id >= self._next_id:
                            self._next_id = compound_id + 1
                    except Exception as e:
                        print(f"KNOW: Error loading logic compound {compound_dict.get('id')}: {e}")
                
                print(f"KNOW: Loaded {len([c for c in compounds_list])} logic compounds (IDs 100-109)")
        
        except Exception as e:
            print(f"KNOW: Error loading logic compounds: {e}")
        
    def initialize(self) -> None:
        """Start the input processing thread and load from persistence."""
        super().initialize()
        
        # Load from persistence if enabled
        if self._enable_persistence:
            self._load_from_persistence()
        
        self._running = True
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()
        
        # Start autosave thread if persistence enabled
        if self._enable_persistence:
            self._autosave_thread = threading.Thread(target=self._autosave_loop, daemon=True)
            self._autosave_thread.start()
        
        storage_info = persistence.get_storage_info()
        print(f"KNOW initialized - {len(self._store)} compounds loaded, persistence: {self._enable_persistence}")
        if self._enable_persistence and storage_info["data_file_exists"]:
            print(f"  Storage: {storage_info['data_file']} ({storage_info.get('data_file_size', 0)} bytes)")
    
    def shutdown(self) -> None:
        """Stop the input thread and save to persistence."""
        self._running = False
        
        if self._input_thread:
            self._input_thread.join(timeout=2.0)
        
        if self._autosave_thread:
            self._autosave_thread.join(timeout=1.0)
        
        # Save to persistence if enabled
        if self._enable_persistence:
            self._save_to_persistence()
        
        # Print summary
        print(f"\nKNOW Shutdown Summary:")
        print(f"  Total compounds stored: {self._stats['compounds_stored']}")
        print(f"  Current store size: {len(self._store)}")
        if self._enable_persistence:
            print(f"  Saved to disk: {self._stats['saves_to_disk']} times")
            print(f"  Loaded from disk: {self._stats['loads_from_disk']} times")
        
        super().shutdown()
    
    def _load_from_persistence(self) -> None:
        """Load compounds and state from persistence."""
        try:
            # Load state first (next_id and stats)
            next_id, saved_stats = persistence.load_state()
            self._next_id = next_id
            
            # Update stats with saved values
            for key, value in saved_stats.items():
                if key in self._stats:
                    self._stats[key] = value
            
            # Load compounds
            compounds_data = persistence.load_compounds()
            
            with self._lock:
                for compound_id, compound_dict in compounds_data.items():
                    try:
                        # Recreate compound from dict
                        compound = Compound.from_dict(compound_dict)
                        self._store[compound_id] = compound
                    except Exception as e:
                        print(f"KNOW: Error loading compound {compound_id}: {e}")
                
                self._stats["loads_from_disk"] += 1
                print(f"KNOW: Loaded {len(compounds_data)} compounds from persistence")
                
        except Exception as e:
            print(f"KNOW: Error loading from persistence: {e}")
    
    def _save_to_persistence(self) -> None:
        """Save compounds and state to persistence."""
        try:
            with self._lock:
                # Convert compounds to dict
                compounds_dict = {}
                for compound_id, compound in self._store.items():
                    compounds_dict[compound_id] = compound.to_dict()
                
                # Save compounds
                if persistence.save_compounds(compounds_dict):
                    self._stats["saves_to_disk"] += 1
                
                # Save state
                persistence.save_state(self._next_id, self._stats)
                
        except Exception as e:
            print(f"KNOW: Error saving to persistence: {e}")
    
    def _autosave_loop(self) -> None:
        """Periodically autosave to disk."""
        print("KNOW: Autosave thread started")
        
        while self._running:
            try:
                time.sleep(1)  # Check every second
                
                current_time = time.time()
                if current_time - self._last_autosave >= self._autosave_interval:
                    with self._lock:
                        if self._store:  # Only save if we have data
                            print(f"KNOW: Autosaving {len(self._store)} compounds...")
                            self._save_to_persistence()
                            self._last_autosave = current_time
                    
            except Exception as e:
                print(f"KNOW autosave error: {e}")
                time.sleep(5)  # Wait longer on error
    
    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        KNOW prime interface.
        
        Retrieve compound:
        {
            "id": compound_id,
            "query": "get"
        }
        
        Store compound:
        {
            "structured_data": data_dict,
            "mode": "store"
        }
        
        Query compounds:
        {
            "query": "find",
            "filter": {"type": "internal", "has_prime": "READ"}
        }
        
        Get stats:
        {
            "query": "stats"
        }
        
        Save command:
        {
            "query": "save"
        }
        """
        self._stats["queries_processed"] += 1
        
        try:
            # Route based on context
            if "id" in context:
                return self._retrieve_compound(context["id"])
            elif "structured_data" in context:
                return self._store_structured(context["structured_data"])
            elif "query" in context:
                return self._handle_query(context)
            else:
                raise PrimeError("KNOW: Invalid context - need id, structured_data, or query")
        except Exception as e:
            self._stats["errors"] += 1
            raise
    
    def _retrieve_compound(self, compound_id: Any) -> Optional[Compound]:
        """Retrieve a compound by ID."""
        try:
            # Handle string IDs (like placeholder IDs)
            if isinstance(compound_id, str) and compound_id.startswith("ph_"):
                # This is a placeholder reference
                # For now, return None - placeholders aren't stored as full compounds
                return None
            
            # Convert to int
            id_int = int(compound_id)
            
            with self._lock:
                compound = self._store.get(id_int)
                if compound:
                    compound.increment_usage()
                    self._stats["compounds_retrieved"] += 1
                return compound
        except (ValueError, TypeError):
            return None
    
    def _store_structured(self, structured_data: Dict[str, Any]) -> Compound:
        """
        Store structured data from DATA.
        
        Now structured_data contains a list of tokens from DATA.
        Create a separate compound for each token and link them.
        Also store observation context in each compound.
        """
        with self._lock:
            tokens = structured_data.get("tokens", [])
            observation_id = structured_data.get("observation_id", "unknown")
            raw_input = structured_data.get("raw_input", "")
            all_tokens = structured_data.get("all_tokens", [])
            
            if not tokens:
                # Empty observation
                return None
            
            compound_ids = []  # Track IDs of created compounds
            
            # Create a compound for each token
            for token_item in tokens:
                # Assign ID atomically
                compound_id = self._next_id
                self._next_id += 1
                compound_ids.append(compound_id)
                
                # Build primebit
                if token_item["is_known"] and token_item["prime_idx"] is not None:
                    primebit = PrimeBit.from_primes({token_item["prime_idx"]})
                    compound_type = "internal"
                else:
                    # Unknown token - placeholder
                    primebit = PrimeBit(0)
                    compound_type = "data"
                
                # Create categorized data structures
                core_data = {
                    "token": token_item["token"],
                    "token_lower": token_item["token_lower"],
                    "position": token_item["position"],
                    "is_known": token_item["is_known"],
                    "prime_name": token_item["prime_name"]
                }
                
                provenance_data = {
                    "provenance": ["DATA_token", f"KNOW_store_{compound_id}"],
                    "created_at": time.time(),
                    "source": structured_data.get("metadata", {}).get("source", "unknown"),
                    "observation_id": observation_id,
                    "raw_observation": raw_input,
                    "observation_tokens": all_tokens,
                    "sibling_tokens": [t for t in all_tokens if t != token_item["token"]]
                }
                
                refinement_data = {
                    "usage_count": 0,
                    "success_rate": 0.0
                }
                
                # Create compound for this token
                compound = Compound(
                    id=compound_id,
                    primebit=primebit,
                    relations=[],  # Will add syntactic relationships below
                    children=[],
                    compound_type=compound_type
                )
                
                # Populate categorized data
                compound.update_core(core_data)
                compound.update_provenance(provenance_data)
                compound.update_refinement(refinement_data)
                
                # Store
                self._store[compound_id] = compound
                self._stats["compounds_stored"] += 1
            
            # Now link compounds with syntactic relationships
            # Adjacent tokens have AFTER/BEFORE relationships
            for i in range(len(compound_ids) - 1):
                current_id = compound_ids[i]
                next_id = compound_ids[i + 1]
                
                # Current token is BEFORE next token (relationship type 6)
                self._store[current_id].relations.append(("BEFORE", next_id))
                # Next token is AFTER current token (relationship type 0)
                self._store[next_id].relations.append(("AFTER", current_id))
            
            # Print summary
            if len(compound_ids) > 0:
                known_count = sum(1 for c in self._store.values() if c.core.get("is_known"))
                unknown_count = len(self._store) - known_count
                print(f"KNOW: Stored {len(compound_ids)} token compounds (IDs: {compound_ids[0]}-{compound_ids[-1]})")
                print(f"KNOW:   Observation: {observation_id}")
                print(f"KNOW:   Raw: {raw_input}")
                if any(self._store[cid].core.get("is_known") for cid in compound_ids):
                    known_tokens = [self._store[cid].core["token"] 
                                   for cid in compound_ids 
                                   if self._store[cid].core.get("is_known")]
                    print(f"KNOW:   Known tokens: {known_tokens}")
                unknown_tokens = [self._store[cid].core["token"] 
                                 for cid in compound_ids 
                                 if not self._store[cid].core.get("is_known")]
                if unknown_tokens:
                    print(f"KNOW:   Unknown tokens: {unknown_tokens}")
            
            # Return first compound (or None if empty)
            if compound_ids:
                return self._store[compound_ids[0]]
            return None
    
    def _handle_query(self, context: Dict[str, Any]) -> Any:
        """Handle various queries."""
        query = context.get("query", "")
        
        if query == "stats":
            return {
                "store_stats": {
                    "total_compounds": len(self._store),
                    "next_id": self._next_id,
                    "by_type": self._count_by_type(),
                    "persistence_enabled": self._enable_persistence
                },
                "operation_stats": self._stats.copy()
            }
        elif query == "list":
            limit = context.get("limit", 10)
            offset = context.get("offset", 0)
            return self._list_compounds(limit, offset)
        elif query == "find":
            filter_dict = context.get("filter", {})
            return self._find_compounds(filter_dict)
        elif query == "count":
            return {"count": len(self._store)}
        elif query == "save" and self._enable_persistence:
            # Manual save command
            self._save_to_persistence()
            return {"status": "saved", "compound_count": len(self._store)}
        elif query == "storage_info" and self._enable_persistence:
            # Get storage information
            return persistence.get_storage_info()
        else:
            return {"error": f"Unknown query: {query}"}
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count compounds by type."""
        counts = {"logic": 0, "data": 0, "aggregate": 0, "definition": 0, "internal": 0}
        with self._lock:
            for compound in self._store.values():
                counts[compound.compound_type] = counts.get(compound.compound_type, 0) + 1
        return counts
    
    def _list_compounds(self, limit: int = 10, offset: int = 0) -> List[Dict]:
        """List compounds with pagination."""
        result = []
        with self._lock:
            ids = sorted(self._store.keys())[offset:offset + limit]
            for id in ids:
                compound = self._store[id]
                result.append({
                    "id": id,
                    "text": compound.text,
                    "compound_type": compound.compound_type,
                    "primes": list(compound.primebit.get_prime_names()),
                    "usage": compound.refinement.get("usage_count", 0),
                    "created_at": compound.provenance.get("created_at", "unknown")
                })
        return result
    
    def _find_compounds(self, filter_dict: Dict[str, Any]) -> List[Dict]:
        """Find compounds matching filter criteria."""
        # Simple filtering for Phase 1C
        results = []
        
        with self._lock:
            for id, compound in self._store.items():
                matches = True
                
                # Filter by compound_type
                if "compound_type" in filter_dict and compound.compound_type != filter_dict["compound_type"]:
                    matches = False
                
                # Filter by prime presence
                if "has_prime" in filter_dict:
                    prime_name = filter_dict["has_prime"]
                    if not compound.primebit.has_prime_name(prime_name):
                        matches = False
                
                if matches:
                    results.append({
                        "id": id,
                        "text": compound.text,
                        "compound_type": compound.compound_type,
                        "primes": list(compound.primebit.get_prime_names()),
                        "usage": compound.refinement.get("usage_count", 0)
                    })
        
        return results
    
    def _input_loop(self) -> None:
        """Process observations from queue (autonomous mode)."""
        print("KNOW: Input thread started - processing observation queue")
        
        empty_count = 0
        
        while self._running:
            try:
                # Pull from observation queue with timeout
                raw_obs = observation_queue.get(timeout=1.0)
                
                # Reset empty count
                empty_count = 0
                
                # Process through DATA
                data_prime = prime_registry.get_prime("DATA")
                
                structured = data_prime({
                    "observation": raw_obs,
                    "mode": "autonomous"
                })
                
                # Store in KNOW
                compound = self._store_structured(structured)
                
                # Print summary every 20 compounds
                if compound.id % 20 == 0:
                    print(f"KNOW: Processed {compound.id + 1} total compounds")
                
            except queue.Empty:
                # No observations yet
                empty_count += 1
                if empty_count % 60 == 0:  # Every minute of emptiness
                    print(f"KNOW: Queue empty for {empty_count} seconds")
                continue
            except Exception as e:
                print(f"KNOW input loop error: {e}")
                time.sleep(0.5)
    
    def get_store_size(self) -> int:
        """Get current store size."""
        with self._lock:
            return len(self._store)


# Singleton instance
know = KNOW(enable_persistence=True)