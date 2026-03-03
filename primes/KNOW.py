"""
KNOW — Knowledge Management Prime

Central storage and retrieval for all compounds, definition narratives,
instance narratives, and refinement tracking.

Pipeline position: DATA → KNOW (storage)  |  THINK → KNOW (intent storage)
Other primes query KNOW to access stored compounds.

Authoritative doc: docs/PRIMES/KNOW/KNOW_ARCHITECTURE.md
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.prime_base import Prime, PrimeError
from core.compound import Compound, Relation
from core.narrative import DefinitionNarrative, Narrative
from core.primebit import PrimeBit, PRIME_INDEX
from core.triple import Triple


# ══════════════════════════════════════════════════════════════════════════════
# RefinementRecord
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RefinementRecord:
    """Usage / outcome tracking for a single compound."""
    compound_id:  int
    usage_count:  int   = 0
    success_rate: float = 0.0
    query_count:  int   = 0


# ══════════════════════════════════════════════════════════════════════════════
# KNOW Prime
# ══════════════════════════════════════════════════════════════════════════════

class KNOW(Prime):
    """
    Knowledge storage and retrieval prime.

    Four in-memory stores with separate locks:
      _compounds    — all Compound objects (logic + runtime)
      _definitions  — DefinitionNarrative per concept compound
      _narratives   — Instance Narratives (episodic / relational)
      _refinement   — RefinementRecord per compound

    Hot LRU cache over compound records (OrderedDict, configurable max).

    Singleton: ``know = KNOW()`` exported at module level.
    """

    def __init__(self, enable_persistence: bool = True):
        super().__init__("KNOW", metadata={
            "role":        "storage",
            "description": "Central compound storage and retrieval",
        })

        # ── Compound store ────────────────────────────────────────────────
        self._compounds:   Dict[int, Compound] = {}
        self._symbol_index: Dict[str, int] = {}   # symbol → compound_id (O(1) lookup)
        # NOTE: self._lock is already created by Prime.__init__ (RLock)
        self._next_id:     int = 200   # 0-99 reserved, 100-199 logic, 200+ runtime

        # ── Definition Narrative store ────────────────────────────────────
        self._definitions: Dict[int, DefinitionNarrative] = {}
        self._def_lock     = threading.RLock()
        self._next_def_id: int = 1

        # ── Instance Narrative store ──────────────────────────────────────
        self._narratives:  Dict[int, Narrative] = {}
        self._nar_lock     = threading.RLock()
        self._next_nar_id: int = 1

        # ── Refinement tracking ───────────────────────────────────────────
        self._refinement:  Dict[int, RefinementRecord] = {}
        self._ref_lock     = threading.RLock()

        # ── Triple store ──────────────────────────────────────────────────
        self._triples:        Dict[int, Triple]      = {}   # triple_id → Triple
        self._triple_index:   Dict[int, List[int]]   = {}   # source_id → [triple_id, ...]
        self._tri_lock        = threading.RLock()
        self._next_triple_id: int = 1

        # ── Hot cache (LRU) ───────────────────────────────────────────────
        self._cache: OrderedDict[int, Compound] = OrderedDict()
        self._cache_max_size: int = 1000

        # ── Layer 1 commit listeners ──────────────────────────────────────
        self._layer1_listeners: List[Callable] = []

        # ── Maintenance / enrichment ──────────────────────────────────────
        self._enrichment_queue: queue.Queue = queue.Queue()

        # ── Persistence ───────────────────────────────────────────────────
        self._enable_persistence = enable_persistence
        self._autosave_interval  = 30   # seconds

        # ── Threading bookkeeping ─────────────────────────────────────────
        self._running = False
        self._threads: List[threading.Thread] = []

        # ── Statistics ────────────────────────────────────────────────────
        self.stats: Dict[str, int] = {
            "compounds_stored":    0,
            "compounds_retrieved": 0,
            "definitions_loaded":  0,
            "narratives_stored":   0,
            "triples_stored":      0,
            "triples_retrieved":   0,
            "queries_processed":   0,
            "cache_hits":          0,
            "enrichment_queued":   0,
            "errors":              0,
            "loads_from_disk":     0,
            "saves_to_disk":       0,
        }

    # ══════════════════════════════════════════════════════════════════════
    # Initialization / Shutdown
    # ══════════════════════════════════════════════════════════════════════

    def _on_initialize(self) -> None:
        self._running = True
        self._load_logic_compounds()
        self._load_from_disk()
        self._bootstrap_relational_narrative()
        self._start_autosave_thread()
        self._start_maintenance_thread()
        print(f"KNOW: Initialized with {len(self._compounds)} compounds")

    def _on_shutdown(self) -> None:
        self._running = False
        if self._enable_persistence:
            self._save_to_disk()
        for t in self._threads:
            t.join(timeout=2.0)
        print("KNOW: Shutdown complete")

    # ── Logic compound loading ────────────────────────────────────────────

    def _load_logic_compounds(self) -> None:
        """Load IDs 100-199 from core/logic_compounds.json and pre-cache."""
        try:
            json_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "core", "logic_compounds.json",
            )
            with open(json_path, "r") as f:
                entries = json.load(f)
            for entry in entries:
                c = Compound.from_dict(entry)
                self._compounds[c.id] = c
                self._symbol_index[c.symbol] = c.id
                self._cache_put(c)
                self._refinement[c.id] = RefinementRecord(compound_id=c.id)
            print(f"KNOW: Loaded {len(entries)} logic compounds (100-{99 + len(entries)})")
        except FileNotFoundError:
            print("KNOW: Warning — logic_compounds.json not found")
        except Exception as e:
            print(f"KNOW: Error loading logic compounds: {e}")

    # ── Relational narrative bootstrap ────────────────────────────────────

    def _bootstrap_relational_narrative(self) -> None:
        """Create the primary user relational narrative on first run.

        Per NARRATIVES_ARCHITECTURE §7 — creates THIS_USER binding backed
        by the pre-seeded USER compound (ID 110) with default social state.
        Only runs if no relational narrative named 'relationship_user_primary'
        already exists (e.g. loaded from disk).
        """
        with self._nar_lock:
            for n in self._narratives.values():
                if (n.narrative_type == "relational"
                        and n.name == "relationship_user_primary"):
                    return  # already exists

        USER_COMPOUND_ID = 110  # pre-seeded in logic_compounds.json
        n = Narrative(
            name="relationship_user_primary",
            narrative_type="relational",
            status="open",
        )
        n.bind("THIS_USER", USER_COMPOUND_ID, initial_state={
            "relationship_quality": 0.0,
            "trust":                0.0,
            "curiosity":            0.2,
            "emotional_register":   "neutral",
            "last_tone":            "unknown",
            "interaction_count":    0,
            "notable_traits":       [],
        })
        self.store_narrative(n)
        print("KNOW: Bootstrapped relational narrative for THIS_USER")

    # ── Background threads ────────────────────────────────────────────────

    def _start_autosave_thread(self) -> None:
        if not self._enable_persistence:
            return
        t = threading.Thread(target=self._autosave_loop, daemon=True, name="KNOW-autosave")
        t.start()
        self._threads.append(t)

    def _start_maintenance_thread(self) -> None:
        t = threading.Thread(target=self._maintenance_loop, daemon=True, name="KNOW-maintenance")
        t.start()
        self._threads.append(t)

    # ══════════════════════════════════════════════════════════════════════
    # Hot Cache (LRU)
    # ══════════════════════════════════════════════════════════════════════

    def _cache_get(self, cid: int) -> Optional[Compound]:
        if cid in self._cache:
            self._cache.move_to_end(cid)
            self.stats["cache_hits"] += 1
            return self._cache[cid]
        return None

    def _cache_put(self, compound: Compound) -> None:
        self._cache[compound.id] = compound
        self._cache.move_to_end(compound.id)
        if len(self._cache) > self._cache_max_size:
            # Never evict logic compounds (100-199)
            evicted_id, _ = self._cache.popitem(last=False)
            if 100 <= evicted_id <= 199:
                # Put it back and try again (skip it)
                self._cache[evicted_id] = self._compounds[evicted_id]
                self._cache.move_to_end(evicted_id, last=False)

    # ══════════════════════════════════════════════════════════════════════
    # __call__  (Prime ABC requirement — thin dispatcher)
    # ══════════════════════════════════════════════════════════════════════

    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        Dispatch context-based calls.  Named methods (store_batch, by_id, …)
        are the preferred interface.  __call__ exists for backward compat and
        the generic Prime calling convention.
        """
        self.stats["queries_processed"] += 1
        try:
            if "id" in context:
                return self.by_id(context["id"])
            if "compounds" in context:
                return self.store_batch(context["compounds"])
            if "compound" in context:
                return self.store(context["compound"])
            if "query" in context:
                return self._handle_query(context)
            raise PrimeError("KNOW: Invalid context — need id, compounds, compound, or query")
        except Exception as e:
            self.stats["errors"] += 1
            raise

    def _handle_query(self, context: Dict[str, Any]) -> Any:
        q = context.get("query", "")
        if q == "stats":
            return self._get_stats()
        if q == "save" and self._enable_persistence:
            self._save_to_disk()
            return {"status": "saved", "compound_count": len(self._compounds)}
        if q == "find":
            return self.search(context.get("filter", {}))
        return {"error": f"Unknown query: {q}"}

    def _get_stats(self) -> Dict[str, Any]:
        return {
            "store_stats": {
                "total_compounds":    len(self._compounds),
                "total_definitions":  len(self._definitions),
                "total_narratives":   len(self._narratives),
                "total_triples":      len(self._triples),
                "next_id":            self._next_id,
                "next_def_id":        self._next_def_id,
                "next_nar_id":        self._next_nar_id,
                "next_triple_id":     self._next_triple_id,
                "cache_size":         len(self._cache),
                "persistence_enabled": self._enable_persistence,
            },
            "operation_stats": dict(self.stats),
        }

    # ══════════════════════════════════════════════════════════════════════
    # 6. Compound Store API
    # ══════════════════════════════════════════════════════════════════════

    def store_batch(self, compounds: List[Compound]) -> Dict[int, int]:
        """
        Primary write path — called by DATA.

        1. Assign permanent IDs to all compounds in batch order.
        2. Sweep all nested / relation target_ids from temp → permanent.
        3. Create a DefinitionNarrative for each new concept compound.
        4. Emit Layer 1 commit event for any utterance compound.
        5. Enqueue ungrounded compounds for enrichment.
        6. Return {temp_id: permanent_id} map.
        """
        id_map: Dict[int, int] = {}

        with self._lock:
            # assign permanent IDs
            for compound in compounds:
                temp_id = compound.id
                compound.id = self._next_id
                self._next_id += 1
                id_map[temp_id] = compound.id

            # sweep temp references
            for compound in compounds:
                compound.nested = [
                    id_map.get(nid, nid) for nid in compound.nested
                ]
                for relation in compound.relations:
                    if relation.target_id in id_map:
                        relation.target_id = id_map[relation.target_id]

            # persist into store + cache + refinement
            for compound in compounds:
                self._compounds[compound.id] = compound
                self._symbol_index[compound.symbol] = compound.id   # O(1) index
                self._cache_put(compound)
                self._refinement[compound.id] = RefinementRecord(compound_id=compound.id)
                self.stats["compounds_stored"] += 1

        # create definition narratives (outside compound lock)
        for compound in compounds:
            if compound.compound_type == "concept":
                def_id = self._create_definition_narrative(compound.id, compound.symbol)
                with self._lock:
                    self._compounds[compound.id].definition_narrative_id = def_id

        # emit Layer 1 commit event
        for compound in compounds:
            if compound.compound_type == "utterance":
                src = (compound.provenance_data or {}).get("source", "unknown")
                self._emit_layer1_event(compound.id, src)

        # enqueue ungrounded for enrichment
        for compound in compounds:
            if not compound.grounded:
                self.enqueue_enrichment(compound.id)

        return id_map

    def store(self, compound: Compound) -> int:
        """
        Store a single compound (used by THINK for intent / action / macro).
        Assigns a permanent ID, stores, returns the assigned ID.
        """
        with self._lock:
            compound.id = self._next_id
            self._next_id += 1
            self._compounds[compound.id] = compound
            self._symbol_index[compound.symbol] = compound.id
            self._cache_put(compound)
            self._refinement[compound.id] = RefinementRecord(compound_id=compound.id)
            self.stats["compounds_stored"] += 1
        if compound.compound_type == "utterance":
            src = (compound.provenance_data or {}).get("source", "unknown")
            self._emit_layer1_event(compound.id, src)
        return compound.id

    # ══════════════════════════════════════════════════════════════════════
    # 7. Compound Retrieval API
    # ══════════════════════════════════════════════════════════════════════

    def by_id(self, cid: int) -> Optional[Compound]:
        cached = self._cache_get(cid)
        if cached is not None:
            self._increment_query_count(cid)
            self.stats["compounds_retrieved"] += 1
            return cached
        with self._lock:
            compound = self._compounds.get(cid)
            if compound is not None:
                self._cache_put(compound)
                self._increment_query_count(cid)
                self.stats["compounds_retrieved"] += 1
            return compound

    def by_ids(self, ids: List[int]) -> List[Compound]:
        return [c for c in (self.by_id(i) for i in ids) if c is not None]

    def by_symbol(self, symbol: str) -> Optional[Compound]:
        """Find compound by exact surface form string.

        O(1) lookup via _symbol_index.  "ran" finds "ran", not "run".
        Used by DATA to check for existing compounds before creating new ones.
        Used by SYMBOL for exact lookup before lemmatization.
        Used by the activation cloud for exact_match assembly.
        """
        with self._lock:
            cid = self._symbol_index.get(symbol)
            if cid is None:
                return None
            compound = self._compounds.get(cid)
            if compound is not None:
                self._increment_query_count(cid)
                self.stats["compounds_retrieved"] += 1
            return compound

    def by_prime(self, prime_name: str) -> List[Compound]:
        """Return all compounds whose primebit includes *prime_name*."""
        with self._lock:
            return [c for c in self._compounds.values()
                    if c.primebit.has_prime(prime_name)]

    def by_type(self, compound_type: str) -> List[Compound]:
        with self._lock:
            return [c for c in self._compounds.values()
                    if c.compound_type == compound_type]

    def by_trigger(self, primebit: PrimeBit) -> List[Compound]:
        """Return action/macro compounds whose trigger_condition matches."""
        with self._lock:
            return [
                c for c in self._compounds.values()
                if c.executable
                and c.trigger_condition is not None
                and (c.trigger_condition & primebit) == c.trigger_condition
            ]

    def search(self, query: dict) -> List[Compound]:
        """Return compounds matching all field conditions in *query* dict."""
        with self._lock:
            results = list(self._compounds.values())
            for field_name, value in query.items():
                results = [c for c in results if getattr(c, field_name, None) == value]
            return results

    def recent_compounds(self, n: int = 5) -> List[Compound]:
        """Return the last n concept/utterance compounds stored (by ID, descending).

        Phase 1 proxy for narrative context used by the activation cloud.
        Returns only concept and utterance compounds (not logic or internal).
        Phase 2+: replaced by narrative-thread-aware retrieval.
        """
        with self._lock:
            runtime = [
                c for cid, c in sorted(self._compounds.items(), reverse=True)
                if cid >= 200 and c.compound_type in ("concept", "utterance")
            ]
        return runtime[:n]

    # ══════════════════════════════════════════════════════════════════════
    # 16. Triple Store API
    # ══════════════════════════════════════════════════════════════════════

    def store_triple(
        self,
        source_id:    int,
        predicate:    str,
        target_id:    Optional[int] = None,
        target_prime: Optional[str] = None,
        confidence:   float = 1.0,
        source:       str = "definition",
        observation_id: Optional[str] = None,
    ) -> int:
        """Store one triple. Validates predicate in PRIME_INDEX.

        Exactly one of target_id or target_prime should be set.
        Returns the assigned triple_id.
        Raises ValueError if predicate is not a known prime.
        """
        _valid_predicates = set(PRIME_INDEX)
        # Also allow logic compound names (IF, AND, OR, NOT, etc.)
        _logic_predicates = {"IF", "AND", "OR", "NOT", "XOR", "NAND", "NOR", "XNOR", "TRUE", "FALSE"}
        if predicate not in _valid_predicates and predicate not in _logic_predicates:
            raise ValueError(f"Invalid predicate '{predicate}' — not in 63-prime set or logic set")

        with self._tri_lock:
            triple = Triple(
                id=self._next_triple_id,
                source_id=source_id,
                predicate=predicate,
                target_id=target_id,
                target_prime=target_prime,
                confidence=confidence,
                source=source,
                observation_id=observation_id,
                created_at=time.time(),
            )
            self._next_triple_id += 1
            self._triples[triple.id] = triple
            self._triple_index.setdefault(source_id, []).append(triple.id)
            self.stats["triples_stored"] += 1
        return triple.id

    def get_triple(self, triple_id: int) -> Optional[Triple]:
        """Return a single triple by ID."""
        with self._tri_lock:
            t = self._triples.get(triple_id)
            if t is not None:
                self.stats["triples_retrieved"] += 1
            return t

    def get_triples(self, source_id: int) -> List[Triple]:
        """Return all outgoing triples for a compound. O(1) index lookup."""
        with self._tri_lock:
            ids = self._triple_index.get(source_id, [])
            result = [self._triples[tid] for tid in ids if tid in self._triples]
            self.stats["triples_retrieved"] += len(result)
            return result

    def get_triples_by_predicate(self, source_id: int, predicate: str) -> List[Triple]:
        """Return outgoing triples filtered by predicate."""
        return [t for t in self.get_triples(source_id) if t.predicate == predicate]

    def get_triples_by_observation(self, observation_id: str) -> List[Triple]:
        """Return all triples from one observation (Phase 1 grouping key).

        O(n) linear scan — used only by THINK once per reasoning cycle,
        not in the hot path. Replaced by proposition store in Phase 2.
        """
        with self._tri_lock:
            return [t for t in self._triples.values()
                    if t.observation_id == observation_id]

    # ══════════════════════════════════════════════════════════════════════
    # 8. Definition Narrative API
    # ══════════════════════════════════════════════════════════════════════

    def _create_definition_narrative(self, compound_id: int, symbol: str) -> int:
        """Create an empty DefinitionNarrative for a new concept compound."""
        with self._def_lock:
            def_id = self._next_def_id
            self._next_def_id += 1
            self._definitions[def_id] = DefinitionNarrative(
                id=def_id,
                compound_id=compound_id,
                symbol=symbol,
                relations=[],
                thread=[],
                constraints=[],
                created_at=time.time(),
            )
            self.stats["definitions_loaded"] += 1
        return def_id

    def get_definition(self, compound_id: int) -> Optional[DefinitionNarrative]:
        """Load DefinitionNarrative for a compound (on-demand, not cached)."""
        compound = self.by_id(compound_id)
        if compound is None or compound.definition_narrative_id is None:
            return None
        with self._def_lock:
            return self._definitions.get(compound.definition_narrative_id)

    def refine_definition(
        self,
        compound_id:      int,
        new_relations:    Optional[List[Relation]] = None,
        updated_primebit: Optional[PrimeBit] = None,
        confidence:       Optional[float] = None,
        provenance:       Optional[dict] = None,
        triples:          Optional[List[dict]] = None,
    ) -> bool:
        """
        Update a compound's definition.  Called by SYMBOL after enrichment.
        Increments compound version, appends to DefinitionNarrative thread.

        triples: optional list of triple dicts to store alongside the refinement.
        Each dict: {"predicate": str, "target_id": int|None, "target_prime": str|None,
                    "confidence": float, "source": str}.
        Stored via store_triple() after compound update.

        This is the ONLY permitted path for modifying primebit, relations,
        or confidence on a stored compound.
        """
        compound = self.by_id(compound_id)
        if compound is None:
            return False

        with self._lock:
            if updated_primebit is not None:
                compound.primebit = updated_primebit
            if confidence is not None:
                compound.confidence = confidence
            if new_relations:
                compound.relations.extend(new_relations)
            compound.version += 1

        definition = self.get_definition(compound_id)
        if definition is not None:
            with self._def_lock:
                definition.thread.append({
                    "timestamp":  time.time(),
                    "type":       "refinement",
                    "provenance": provenance or {},
                    "primebit":   updated_primebit.value if updated_primebit else None,
                    "relations":  [
                        {"predicate": r.predicate, "target_id": r.target_id}
                        for r in (new_relations or [])
                    ],
                    "confidence": confidence,
                    "version":    compound.version,
                })

        # Store triples from this refinement
        if triples:
            for t in triples:
                try:
                    self.store_triple(
                        source_id=compound_id,
                        predicate=t["predicate"],
                        target_id=t.get("target_id"),
                        target_prime=t.get("target_prime"),
                        confidence=t.get("confidence", 1.0),
                        source=t.get("source", "definition"),
                    )
                except (ValueError, KeyError):
                    pass   # skip invalid triples silently

        return True

    # ══════════════════════════════════════════════════════════════════════
    # 9. Instance Narrative API
    # ══════════════════════════════════════════════════════════════════════

    def store_narrative(self, narrative: Narrative) -> int:
        with self._nar_lock:
            narrative.id = self._next_nar_id
            self._next_nar_id += 1
            self._narratives[narrative.id] = narrative
            self.stats["narratives_stored"] += 1
        return narrative.id

    def get_narrative(self, nid: int) -> Optional[Narrative]:
        with self._nar_lock:
            return self._narratives.get(nid)

    def open_narratives(self) -> List[Narrative]:
        with self._nar_lock:
            return [n for n in self._narratives.values() if n.status == "open"]

    def narrative_by_source(self, source: str) -> Optional[Narrative]:
        with self._nar_lock:
            for n in self._narratives.values():
                if n.status == "open" and n.name.endswith(source):
                    return n
        return None

    def close_narrative(self, nid: int) -> None:
        with self._nar_lock:
            n = self._narratives.get(nid)
            if n:
                n.status = "closed"
                n.closed_at = time.time()

    def archive_narrative(self, nid: int) -> None:
        with self._nar_lock:
            n = self._narratives.get(nid)
            if n:
                n.status = "archived"

    # ══════════════════════════════════════════════════════════════════════
    # 10. Refinement Tracking API
    # ══════════════════════════════════════════════════════════════════════

    def _increment_query_count(self, compound_id: int) -> None:
        with self._ref_lock:
            rec = self._refinement.get(compound_id)
            if rec:
                rec.query_count += 1

    def record_usage(self, compound_id: int) -> None:
        """Called by THINK when a compound is used in reasoning."""
        with self._ref_lock:
            rec = self._refinement.get(compound_id)
            if rec:
                rec.usage_count += 1

    def record_outcome(self, compound_id: int, success: bool) -> None:
        """Called by THINK after execution outcome is known."""
        with self._ref_lock:
            rec = self._refinement.get(compound_id)
            if rec and rec.usage_count > 0:
                rec.success_rate = (
                    (rec.success_rate * (rec.usage_count - 1) + (1.0 if success else 0.0))
                    / rec.usage_count
                )

    def get_refinement(self, compound_id: int) -> Optional[RefinementRecord]:
        with self._ref_lock:
            return self._refinement.get(compound_id)

    # ══════════════════════════════════════════════════════════════════════
    # 11. Layer 1 Commit Event
    # ══════════════════════════════════════════════════════════════════════

    def register_layer1_listener(self, callback: Callable) -> None:
        self._layer1_listeners.append(callback)

    def _emit_layer1_event(self, compound_id: int, source: str) -> None:
        for cb in self._layer1_listeners:
            try:
                cb(compound_id, source)
            except Exception:
                self.stats["errors"] += 1

    # ══════════════════════════════════════════════════════════════════════
    # 12. Maintenance Thread
    # ══════════════════════════════════════════════════════════════════════

    def enqueue_enrichment(self, compound_id: int) -> None:
        """Called by store_batch for any compound stored with grounded=False."""
        self._enrichment_queue.put(compound_id)

    def _maintenance_loop(self) -> None:
        while self._running:
            try:
                compound_id = self._enrichment_queue.get(timeout=1.0)
                self._request_enrichment(compound_id)
            except queue.Empty:
                continue

    def _request_enrichment(self, compound_id: int) -> None:
        """Signal SYMBOL to enrich.  Phase 1: log only."""
        compound = self.by_id(compound_id)
        if compound and not compound.grounded:
            self.stats["enrichment_queued"] += 1

    # ══════════════════════════════════════════════════════════════════════
    # 13. Persistence
    # ══════════════════════════════════════════════════════════════════════

    def _autosave_loop(self) -> None:
        while self._running:
            time.sleep(self._autosave_interval)
            if self._running:
                self._save_to_disk()

    def _save_to_disk(self) -> None:
        """Snapshot under locks, write outside locks."""
        with self._lock:
            compounds_snapshot = {
                str(k): v.to_dict()
                for k, v in self._compounds.items()
                if v.id >= 200   # skip logic compounds
            }
        with self._def_lock:
            definitions_snapshot = {
                str(k): v.to_dict() for k, v in self._definitions.items()
            }
        with self._nar_lock:
            narratives_snapshot = {
                str(k): v.to_dict()
                for k, v in self._narratives.items()
                if v.status != "archived"
            }
        with self._ref_lock:
            refinement_snapshot = {
                str(k): v.__dict__ for k, v in self._refinement.items()
            }
        with self._tri_lock:
            triples_snapshot = {
                str(k): v.to_dict() for k, v in self._triples.items()
            }
        meta = {
            "next_id":        self._next_id,
            "next_def_id":    self._next_def_id,
            "next_nar_id":    self._next_nar_id,
            "next_triple_id": self._next_triple_id,
            "saved_at":       time.time(),
        }

        os.makedirs("storage", exist_ok=True)
        try:
            with open("storage/compounds.json",   "w") as f: json.dump(compounds_snapshot,   f, indent=2, default=str)
            with open("storage/definitions.json", "w") as f: json.dump(definitions_snapshot, f, indent=2, default=str)
            with open("storage/narratives.json",  "w") as f: json.dump(narratives_snapshot,  f, indent=2, default=str)
            with open("storage/refinement.json",  "w") as f: json.dump(refinement_snapshot,  f, indent=2, default=str)
            with open("storage/triples.json",     "w") as f: json.dump(triples_snapshot,     f, indent=2, default=str)
            with open("storage/metadata.json",    "w") as f: json.dump(meta,                 f, indent=2, default=str)
            self.stats["saves_to_disk"] += 1
        except Exception as e:
            print(f"KNOW: Error saving to disk: {e}")
            self.stats["errors"] += 1

    def _load_from_disk(self) -> None:
        """Restore all four stores + metadata from storage/ directory."""
        if not self._enable_persistence:
            return

        try:
            # metadata first — restores ID counters
            if os.path.exists("storage/metadata.json"):
                with open("storage/metadata.json") as f:
                    meta = json.load(f)
                self._next_id        = meta.get("next_id",        200)
                self._next_def_id    = meta.get("next_def_id",    1)
                self._next_nar_id    = meta.get("next_nar_id",    1)
                self._next_triple_id = meta.get("next_triple_id", 1)

            # compounds — rebuild _symbol_index
            if os.path.exists("storage/compounds.json"):
                with open("storage/compounds.json") as f:
                    data = json.load(f)
                for raw in data.values():
                    c = Compound.from_dict(raw)
                    self._compounds[c.id] = c
                    self._symbol_index[c.symbol] = c.id   # rebuild O(1) index
                    self._cache_put(c)
                    # ensure refinement record exists
                    if c.id not in self._refinement:
                        self._refinement[c.id] = RefinementRecord(compound_id=c.id)

            # definitions
            if os.path.exists("storage/definitions.json"):
                with open("storage/definitions.json") as f:
                    data = json.load(f)
                for raw in data.values():
                    d = DefinitionNarrative.from_dict(raw)
                    self._definitions[d.id] = d

            # narratives
            if os.path.exists("storage/narratives.json"):
                with open("storage/narratives.json") as f:
                    data = json.load(f)
                for raw in data.values():
                    n = Narrative.from_dict(raw)
                    self._narratives[n.id] = n

            # refinement
            if os.path.exists("storage/refinement.json"):
                with open("storage/refinement.json") as f:
                    data = json.load(f)
                for k, v in data.items():
                    self._refinement[int(k)] = RefinementRecord(**v)

            # triples — rebuild _triple_index
            if os.path.exists("storage/triples.json"):
                with open("storage/triples.json") as f:
                    data = json.load(f)
                with self._tri_lock:
                    for raw in data.values():
                        t = Triple.from_dict(raw)
                        self._triples[t.id] = t
                        self._triple_index.setdefault(t.source_id, []).append(t.id)

            self.stats["loads_from_disk"] += 1

        except Exception as e:
            print(f"KNOW: Error loading from disk: {e}")
            self.stats["errors"] += 1

    # ══════════════════════════════════════════════════════════════════════
    # Convenience helpers
    # ══════════════════════════════════════════════════════════════════════

    def get_store_size(self) -> int:
        with self._lock:
            return len(self._compounds)


# ══════════════════════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════════════════════

know = KNOW(enable_persistence=True)
