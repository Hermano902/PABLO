"""
Persistence layer for KNOW storage — Phase 1.

Four separate JSON files per the KNOW architecture:
  storage/compounds.json    — runtime compounds (200+), not logic compounds
  storage/definitions.json  — DefinitionNarrative records
  storage/narratives.json   — Instance Narrative records (non-archived)
  storage/refinement.json   — RefinementRecord per compound
  storage/metadata.json     — ID counters and save timestamp
"""

import json
import os
import time
import threading
from typing import Any


class JSONPersistence:
    """JSON-based persistence layer for KNOW.

    KNOW calls save_all / load_all with pre-serialised dicts.
    This class handles only file I/O — no knowledge of Compound schema.
    """

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = storage_dir
        self._lock = threading.RLock()
        os.makedirs(storage_dir, exist_ok=True)

    # ── Paths ─────────────────────────────────────────────────────────────

    @property
    def compounds_path(self) -> str:
        return os.path.join(self.storage_dir, "compounds.json")

    @property
    def definitions_path(self) -> str:
        return os.path.join(self.storage_dir, "definitions.json")

    @property
    def narratives_path(self) -> str:
        return os.path.join(self.storage_dir, "narratives.json")

    @property
    def refinement_path(self) -> str:
        return os.path.join(self.storage_dir, "refinement.json")

    @property
    def metadata_path(self) -> str:
        return os.path.join(self.storage_dir, "metadata.json")

    # ── Save all stores ───────────────────────────────────────────────────

    def save_all(
        self,
        compounds:   dict[str, Any],
        definitions: dict[str, Any],
        narratives:  dict[str, Any],
        refinement:  dict[str, Any],
        metadata:    dict[str, Any],
    ) -> bool:
        """Write all four data files + metadata atomically (best-effort)."""
        with self._lock:
            try:
                for path, data in [
                    (self.compounds_path,   compounds),
                    (self.definitions_path, definitions),
                    (self.narratives_path,  narratives),
                    (self.refinement_path,  refinement),
                    (self.metadata_path,    metadata),
                ]:
                    with open(path, "w") as f:
                        json.dump(data, f, indent=2, default=str)
                return True
            except Exception as e:
                print(f"Persistence: Error saving: {e}")
                return False

    # ── Load individual stores ────────────────────────────────────────────

    def _load_json(self, path: str) -> dict:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Persistence: Error loading {path}: {e}")
            return {}

    def load_compounds(self) -> dict:
        return self._load_json(self.compounds_path)

    def load_definitions(self) -> dict:
        return self._load_json(self.definitions_path)

    def load_narratives(self) -> dict:
        return self._load_json(self.narratives_path)

    def load_refinement(self) -> dict:
        return self._load_json(self.refinement_path)

    def load_metadata(self) -> dict:
        return self._load_json(self.metadata_path)

    # ── Convenience ───────────────────────────────────────────────────────

    def get_storage_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "storage_dir":          self.storage_dir,
            "compounds_exists":     os.path.exists(self.compounds_path),
            "definitions_exists":   os.path.exists(self.definitions_path),
            "narratives_exists":    os.path.exists(self.narratives_path),
            "refinement_exists":    os.path.exists(self.refinement_path),
            "metadata_exists":      os.path.exists(self.metadata_path),
        }
        for name in ("compounds", "definitions", "narratives", "refinement", "metadata"):
            path = getattr(self, f"{name}_path")
            if os.path.exists(path):
                info[f"{name}_size"] = os.path.getsize(path)
        return info


# Global persistence instance
persistence = JSONPersistence()