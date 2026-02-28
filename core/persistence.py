"""
Persistence layer for KNOW storage.
Simple JSON-based file storage for Phase 1.
Will be replaced with SQLite in Phase 2.
"""

import json
import os
import time
from typing import Dict, Any, Optional
import threading


class JSONPersistence:
    """JSON-based persistence layer for KNOW."""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = storage_dir
        self.data_file = os.path.join(storage_dir, "compounds.json")
        self.metadata_file = os.path.join(storage_dir, "metadata.json")
        self._lock = threading.RLock()
        
        # Create storage directory if it doesn't exist
        os.makedirs(storage_dir, exist_ok=True)
    
    def save_compounds(self, compounds: Dict[int, Dict[str, Any]]) -> bool:
        """
        Save compounds to disk.
        
        Args:
            compounds: Dict of compound_id -> compound_dict
            
        Returns:
            True if successful
        """
        with self._lock:
            try:
                # Prepare data for JSON serialization
                data = {}
                for compound_id, compound_data in compounds.items():
                    # Ensure all data is JSON-serializable
                    serializable_data = self._make_serializable(compound_data)
                    data[str(compound_id)] = serializable_data
                
                # Write to file with pretty formatting for readability
                with open(self.data_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                # Also save metadata
                metadata = {
                    "last_saved": time.time(),
                    "compound_count": len(compounds),
                    "max_id": max(compounds.keys()) if compounds else 0
                }
                
                with open(self.metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
                
                print(f"Persistence: Saved {len(compounds)} compounds to {self.data_file}")
                return True
                
            except Exception as e:
                print(f"Persistence: Error saving compounds: {e}")
                return False
    
    def load_compounds(self) -> Dict[int, Dict[str, Any]]:
        """
        Load compounds from disk.
        
        Returns:
            Dict of compound_id -> compound_dict
        """
        with self._lock:
            compounds = {}
            
            if not os.path.exists(self.data_file):
                print(f"Persistence: No existing data file at {self.data_file}")
                return compounds
            
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                # Convert string keys back to integers
                for str_id, compound_data in data.items():
                    compound_id = int(str_id)
                    compounds[compound_id] = compound_data
                
                print(f"Persistence: Loaded {len(compounds)} compounds from {self.data_file}")
                return compounds
                
            except Exception as e:
                print(f"Persistence: Error loading compounds: {e}")
                return compounds
    
    def save_state(self, next_id: int, stats: Dict[str, Any]) -> bool:
        """
        Save system state (next_id and statistics).
        
        Args:
            next_id: Next compound ID to use
            stats: Statistics dictionary
            
        Returns:
            True if successful
        """
        with self._lock:
            try:
                state = {
                    "next_id": next_id,
                    "stats": stats,
                    "saved_at": time.time(),
                    "saved_at_human": time.ctime()
                }
                
                state_file = os.path.join(self.storage_dir, "state.json")
                with open(state_file, 'w') as f:
                    json.dump(state, f, indent=2, default=str)
                
                return True
                
            except Exception as e:
                print(f"Persistence: Error saving state: {e}")
                return False
    
    def load_state(self) -> tuple[int, Dict[str, Any]]:
        """
        Load system state.
        
        Returns:
            Tuple of (next_id, stats)
        """
        with self._lock:
            state_file = os.path.join(self.storage_dir, "state.json")
            
            if not os.path.exists(state_file):
                return 0, {}
            
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                next_id = state.get("next_id", 0)
                stats = state.get("stats", {})
                
                print(f"Persistence: Loaded state - next_id: {next_id}")
                return next_id, stats
                
            except Exception as e:
                print(f"Persistence: Error loading state: {e}")
                return 0, {}
    
    def _make_serializable(self, data: Any) -> Any:
        """
        Convert data to JSON-serializable format.
        """
        if isinstance(data, dict):
            return {k: self._make_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._make_serializable(item) for item in data]
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        else:
            # Convert to string representation
            return str(data)
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about storage."""
        info = {
            "storage_dir": self.storage_dir,
            "data_file": self.data_file,
            "data_file_exists": os.path.exists(self.data_file),
            "metadata_file_exists": os.path.exists(self.metadata_file),
            "state_file_exists": os.path.exists(os.path.join(self.storage_dir, "state.json"))
        }
        
        if os.path.exists(self.data_file):
            info["data_file_size"] = os.path.getsize(self.data_file)
        
        return info


# Global persistence instance
persistence = JSONPersistence()