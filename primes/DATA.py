"""
DATA — Compound Construction and Validation Prime

Contract enforcer between SYMBOL's probabilistic proposals and KNOW's
authoritative store.  Takes near-compound candidates from candidate_queue,
validates prime assignments, detects logic operators, resolves or creates
Layer 0 concept Compounds, assembles a Layer 1 utterance Compound, and
pushes the batch to KNOW via store_batch.

Pipeline position: SYMBOL → candidate_queue → DATA → KNOW.store_batch
Authoritative docs: docs/PRIMES/DATA/data_architecture.md
                    docs/PRIMES/DATA/data_concept.md
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from typing import Any, Dict, List, Optional, Set

from core.compound import Compound, Relation
from core.prime_base import Prime, PrimeError
from core.primebit import PrimeBit, PRIME_INDEX
from core.queues import candidate_queue


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

GROUND_THRESHOLD = 0.6   # minimum confidence to accept a prime assignment
PRIME_SET: Set[str] = set(PRIME_INDEX)   # all 63 valid prime names


# ══════════════════════════════════════════════════════════════════════════════
# DATA Prime
# ══════════════════════════════════════════════════════════════════════════════

class DATA(Prime):
    """
    Compound construction and validation prime.

    Daemon thread drains candidate_queue.  Each candidate is validated,
    resolved against KNOW, and committed as a batch of real Compounds.

    Also supports consultation mode (synchronous via __call__).
    """

    def __init__(self):
        super().__init__("DATA", metadata={
            "role":        "structuring",
            "description": "Near-compound → real Compound validation and storage",
        })
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Temp ID counter (negative, decrements)
        self._temp_counter = 0

        # Logic token map: lowercase token → logic compound ID (100-199)
        self._logic_map: Dict[str, int] = {}

        # Statistics
        self.stats: Dict[str, int] = {
            "observations_processed": 0,
            "concepts_found":         0,
            "concepts_created":       0,
            "utterances_assembled":   0,
            "grounded_directly":      0,
            "placeholders_created":   0,
            "logic_operators_found":  0,
            "validation_failures":    0,
        }

    # ══════════════════════════════════════════════════════════════════════
    # Lifecycle
    # ══════════════════════════════════════════════════════════════════════

    def _on_initialize(self) -> None:
        self._running = True
        self._load_logic_map()
        self._thread = threading.Thread(
            target=self._candidate_loop,
            daemon=True,
            name="DATA-process",
        )
        self._thread.start()
        print(f"DATA: Initialized — {len(self._logic_map)} logic token mappings loaded")

    def _on_shutdown(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("DATA: Shutdown complete")

    def _load_logic_map(self) -> None:
        """Load core/logic_compounds.json → {lowercase_token: compound_id}."""
        try:
            json_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "core", "logic_compounds.json",
            )
            with open(json_path, "r") as f:
                entries = json.load(f)
            for entry in entries:
                cid = entry["id"]
                for token in entry.get("token_variants", []):
                    self._logic_map[token.lower()] = cid
        except Exception as e:
            print(f"DATA: Error loading logic map: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # Temp ID generator
    # ══════════════════════════════════════════════════════════════════════

    def _next_temp_id(self) -> int:
        self._temp_counter -= 1
        return self._temp_counter

    # ══════════════════════════════════════════════════════════════════════
    # __call__ — consultation mode
    # ══════════════════════════════════════════════════════════════════════

    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        Consultation mode — bypass candidate_queue.
        THINK calls this with {"candidate": dict} or {"symbol": str}.
        Returns the utterance Compound.
        """
        candidate = context.get("candidate")
        if candidate is None and "symbol" in context:
            candidate = self._text_to_candidate(context["symbol"])
        if candidate is None:
            raise PrimeError("DATA consultation: need 'candidate' or 'symbol'")
        result = self._process_candidate(candidate)
        if result is None:
            raise PrimeError("DATA consultation: candidate validation failed")
        return result.get("utterance")

    def _text_to_candidate(self, text: str) -> Dict[str, Any]:
        """Build a minimal heuristic candidate from raw text."""
        tokens = text.split()
        candidate_primes = []
        for i, tok in enumerate(tokens):
            lower = tok.lower()
            if lower in {p.lower() for p in PRIME_SET}:
                canonical = next(p for p in PRIME_SET if p.lower() == lower)
                candidate_primes.append({
                    "token": tok, "prime": canonical, "score": 0.8, "position": i,
                })
            else:
                candidate_primes.append({
                    "token": tok, "prime": None, "score": 0.0, "position": i,
                })
        return {
            "candidate_primes": candidate_primes,
            "roles":            [],
            "rule_template":    None,
            "confidence":       0.5,
            "provenance":       {"model": "heuristic", "adapter": None},
            "raw_input":        text,
            "observation_id":   f"obs_{int(time.time() * 1000)}",
            "source":           "consultation",
        }

    # ══════════════════════════════════════════════════════════════════════
    # Candidate loop (daemon thread)
    # ══════════════════════════════════════════════════════════════════════

    def _candidate_loop(self) -> None:
        """Drain candidate_queue; process each candidate."""
        while self._running:
            try:
                candidate = candidate_queue.get(timeout=0.5)
                self._process_candidate(candidate)
            except queue.Empty:
                continue
            except Exception as e:
                self._log_error(e)

    def _log_error(self, e: Exception) -> None:
        self.stats["validation_failures"] += 1
        print(f"DATA: Error processing candidate: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # Processing pipeline (per candidate)
    # ══════════════════════════════════════════════════════════════════════

    def _process_candidate(self, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Full processing pipeline per data_architecture.md §3:
          1. validate_primes
          2. detect_logic_operators
          3. assign_observation_id
          4. resolve_or_create_concept_compounds
          5. build_utterance_compound
          6. push_to_know
        Returns {"utterance": Compound, "concepts": list[Compound], "id_map": dict}
        or None on validation failure.
        """
        self.stats["observations_processed"] += 1

        # Lazy import to avoid circular dependency at module load
        from primes.KNOW import know

        tokens = candidate.get("candidate_primes", [])
        raw_input = candidate.get("raw_input", "")

        if not tokens:
            self.stats["validation_failures"] += 1
            return None

        # 1. Validate primes
        tokens = self._validate_primes(tokens)

        # 2. Detect logic operators
        tokens = self._detect_logic_operators(tokens)

        # 3. Observation ID
        obs_id = candidate.get("observation_id") or f"obs_{int(time.time() * 1000)}"

        # 4. Resolve or create concept Compounds
        concept_compounds: List[Compound] = []
        existing_ids: List[int] = []       # permanent IDs of existing concepts
        new_compounds: List[Compound] = []  # new concepts to push to KNOW
        batch_symbols: Dict[str, Compound] = {}  # within-utterance dedup
        concepts_with_interp: List[tuple] = []   # (concept, interp) for refine_definition

        for tok in tokens:
            token_text = tok["token"]
            logic_id = tok.get("logic_compound_id")

            # Logic operators reference pre-existing compounds
            if logic_id is not None:
                existing_ids.append(logic_id)
                concept_compounds.append(know.by_id(logic_id))
                continue

            # Prefer lemma as symbol when the router provides it
            symbol = tok.get("lemma") or token_text

            # Check within-utterance dedup (same symbol already created this batch)
            if symbol in batch_symbols:
                dup = batch_symbols[symbol]
                concept_compounds.append(dup)
                self.stats["concepts_found"] += 1
                continue

            # Check KNOW for existing concept (by lemma first, then surface)
            existing = know.by_symbol(symbol)
            if existing is None and symbol != token_text:
                existing = know.by_symbol(token_text)
            if existing is not None:
                existing_ids.append(existing.id)
                concept_compounds.append(existing)
                batch_symbols[symbol] = existing
                self.stats["concepts_found"] += 1
                continue

            # Create new concept compound
            prime_name = tok.get("prime")
            score = tok.get("score", 0.0)
            grounded = prime_name is not None and score >= GROUND_THRESHOLD

            # Build primebit: primary prime OR grammatical primes from spaCy
            gram_primes = tok.get("grammatical_primes", [])
            if grounded and prime_name is not None:
                prime_names = [prime_name]
                # Also include grammatical primes alongside the grounded prime
                for gp in gram_primes:
                    if gp in PRIME_SET and gp != prime_name:
                        prime_names.append(gp)
                pb = PrimeBit.from_prime_names(prime_names)
                self.stats["grounded_directly"] += 1
            elif gram_primes:
                # Not grounded to a semantic prime, but spaCy gave us
                # grammatical primes — use them for partial grounding
                valid_gp = [gp for gp in gram_primes if gp in PRIME_SET]
                if valid_gp:
                    pb = PrimeBit.from_prime_names(valid_gp)
                    score = max(score, 0.1)  # partial: low but non-zero
                else:
                    pb = PrimeBit(0)
                self.stats["placeholders_created"] += 1
            else:
                pb = PrimeBit(0)
                self.stats["placeholders_created"] += 1

            # Build router provenance for DefinitionNarrative (stored after batch commit)
            interp: List[Dict[str, Any]] = []
            if prime_name:
                interp.append({"prime": prime_name, "score": score})
            if gram_primes:
                interp.append({"grammatical_primes": list(gram_primes)})
            if tok.get("pos"):
                interp.append({"pos": tok["pos"]})
            if tok.get("method"):
                interp.append({"method": tok["method"]})
            if tok.get("lemma") and tok["lemma"] != token_text:
                interp.append({"surface_form": token_text, "lemma": tok["lemma"]})

            new_concept = Compound.concept(
                temp_id=self._next_temp_id(),
                symbol=symbol,
                primebit=pb,
                confidence=score,
                grounded=grounded,
            )
            new_compounds.append(new_concept)
            concept_compounds.append(new_concept)
            concepts_with_interp.append((new_concept, interp))
            batch_symbols[symbol] = new_concept
            self.stats["concepts_created"] += 1

        # 5. Build utterance compound
        # nested = ordered list of concept IDs (temp for new, permanent for existing)
        nested_ids: List[int] = []
        for c in concept_compounds:
            if c is not None:
                nested_ids.append(c.id)

        # Primebit union of all concepts
        union_pb = PrimeBit(0)
        for c in concept_compounds:
            if c is not None:
                union_pb = union_pb | c.primebit

        utterance = Compound.utterance(
            temp_id=self._next_temp_id(),
            symbol=raw_input,
            nested=nested_ids,
            primebit=union_pb,
            source=candidate.get("source", ""),
        )
        self.stats["utterances_assembled"] += 1

        # 6. Push to KNOW (only NEW concepts + utterance)
        batch = new_compounds + [utterance]
        id_map = know.store_batch(batch)

        # 7. Record initial grounding provenance in each new concept's DefinitionNarrative
        for concept, interp in concepts_with_interp:
            if interp:
                know.refine_definition(concept.id, provenance={"initial_grounding": interp})

        print(
            f"DATA: Processed '{raw_input[:40]}' — "
            f"{len(new_compounds)} new concepts, "
            f"{len(existing_ids)} existing, "
            f"utterance ID {utterance.id}"
        )

        return {
            "utterance": utterance,
            "concepts":  concept_compounds,
            "id_map":    id_map,
        }

    # ══════════════════════════════════════════════════════════════════════
    # Step helpers
    # ══════════════════════════════════════════════════════════════════════

    def _validate_primes(self, tokens: List[Dict]) -> List[Dict]:
        """Check each token's proposed prime against PRIME_SET."""
        for tok in tokens:
            prime = tok.get("prime")
            if prime is not None and prime not in PRIME_SET:
                tok["prime"] = None
                tok["score"] = 0.0
            if tok.get("score", 0.0) < GROUND_THRESHOLD:
                tok["prime"] = None
                tok["score"] = 0.0
        return tokens

    def _detect_logic_operators(self, tokens: List[Dict]) -> List[Dict]:
        """Substitute logic compound IDs for matching tokens."""
        for tok in tokens:
            lower = tok["token"].lower()
            logic_id = self._logic_map.get(lower)
            if logic_id is not None:
                tok["logic_compound_id"] = logic_id
                tok["prime"] = None  # skip SYMBOL grounding
                tok["score"] = 1.0
                self.stats["logic_operators_found"] += 1
        return tokens

    def _detect_logic(self, token_text: str) -> Optional[int]:
        """Single token logic lookup (convenience)."""
        return self._logic_map.get(token_text.lower())


# ══════════════════════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════════════════════

data = DATA()
