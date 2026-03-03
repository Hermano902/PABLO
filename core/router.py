"""
Router — SYMBOL's resolution cascade.

Implements the documented resolution order per SYMBOL_CONCEPT.md:

  1. KNOW exact lookup    — by_symbol(surface_form) → existing compound? → done
  2. Lemmatize (spaCy)    — surface → (lemma, POS, grammatical primes)
  3. KNOW lemma lookup    — by_symbol(lemma) → root found?
  4. Family member create  — new compound with KIND→root, primebit ∪ gram primes
  5. LLM specialist        — invoke specialist for new root creation
  6. Heuristic fallback    — prime-name match (score 1.0) or placeholder (score 0.0)

The router is deterministic. Rule dispatch is minimal overhead (sub-ms).
Specialist invocations are the fallback, not the default.

Dependencies:
  - core/lemmatizer.py    — spaCy-based morphological analysis
  - core/specialists.py   — LLM specialist interface
  - primes/KNOW.py        — compound storage (lazy import to avoid circular deps)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.primebit import PrimeBit, PRIME_INDEX

log = logging.getLogger(__name__)

# Canonical prime names for heuristic matching
_PRIME_NAME_SET: set[str] = {name.lower() for name in PRIME_INDEX}
_LOWER_TO_CANONICAL: Dict[str, str] = {name.lower(): name for name in PRIME_INDEX}


# ══════════════════════════════════════════════════════════════════════════════
# Resolution result
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TokenResolution:
    """
    Resolution result for a single token from the router cascade.

    This is what the router returns for each token. SYMBOL uses these to
    build the near-compound candidate that DATA receives.
    """
    token:        str                 # original surface form
    prime:        Optional[str]       # resolved prime name (or None)
    score:        float               # confidence 0.0-1.0
    position:     int                 # token index in the observation
    method:       str                 # how it was resolved
    compound_id:  Optional[int]       # existing compound ID if found in KNOW
    lemma:        Optional[str]       # spaCy lemma (if lemmatization ran)
    pos:          Optional[str]       # spaCy POS tag
    grammatical_primes: set[str]      # gram primes from morphology
    is_family_member: bool = False    # True if this token created a family member
    family_root_id: Optional[int] = None  # root compound ID for family members

    def to_candidate_entry(self) -> Dict[str, Any]:
        """Convert to the near-compound candidate_primes entry shape."""
        entry: Dict[str, Any] = {
            "token":       self.token,
            "prime":       self.prime,
            "score":       self.score,
            "position":    self.position,
            "method":      self.method,
        }
        if self.compound_id is not None:
            entry["compound_id"] = self.compound_id
        if self.lemma is not None:
            entry["lemma"] = self.lemma
        if self.pos is not None:
            entry["pos"] = self.pos
        if self.grammatical_primes:
            entry["grammatical_primes"] = list(self.grammatical_primes)
        if self.is_family_member:
            entry["is_family_member"] = True
            entry["family_root_id"] = self.family_root_id
        return entry


# ══════════════════════════════════════════════════════════════════════════════
# Router stats
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RouterStats:
    """Routing counters exposed via KNOW.get_router_stats()."""
    know_exact_hits:     int = 0    # resolved by exact KNOW lookup
    know_lemma_hits:     int = 0    # resolved by lemma KNOW lookup
    family_members_created: int = 0 # new family member compounds created
    specialist_calls:    int = 0    # LLM specialist invocations
    specialist_failures: int = 0    # specialist errors / timeouts
    heuristic_hits:      int = 0    # prime-name exact match
    unresolved:          int = 0    # could not resolve at all (placeholder)
    total_tokens:        int = 0    # total tokens processed
    fast_path_skips:     int = 0    # cloud.fast_path=True → specialist skipped

    def to_dict(self) -> Dict[str, int]:
        return {
            "know_exact_hits":        self.know_exact_hits,
            "know_lemma_hits":        self.know_lemma_hits,
            "family_members_created": self.family_members_created,
            "specialist_calls":       self.specialist_calls,
            "specialist_failures":    self.specialist_failures,
            "heuristic_hits":         self.heuristic_hits,
            "unresolved":             self.unresolved,
            "total_tokens":           self.total_tokens,
            "fast_path_skips":        self.fast_path_skips,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Router
# ══════════════════════════════════════════════════════════════════════════════

class Router:
    """
    SYMBOL's resolution cascade.

    Resolves raw observation tokens into grounded or candidate compound
    references, following the documented priority order:

      KNOW exact → lemmatize + KNOW lemma → family member creation →
      LLM specialist → prime-name heuristic → placeholder

    The router never writes directly to KNOW. It produces TokenResolution
    objects that SYMBOL assembles into near-compound candidates for DATA.

    Exception: family member creation calls KNOW.store_batch() because
    the family member compound must exist in KNOW before subsequent tokens
    that reference it. This is the only write path from the router.

    Usage:
        router = Router()
        resolutions = router.resolve_observation(obs_dict)
        # → list[TokenResolution], one per token
    """

    def __init__(
        self,
        specialist_fn: Optional[Callable] = None,
        enable_specialist: bool = True,
    ):
        """
        Args:
            specialist_fn:    callable(text, tokens_data) → near-compound candidate dict.
                              If None, specialist step is skipped (Phase 1 mode).
            enable_specialist: master switch for specialist invocations.
        """
        self._specialist_fn = specialist_fn
        self._enable_specialist = enable_specialist
        self.stats = RouterStats()

        # Utterance compound tracking — cleared at start of each resolve_observation()
        # Used to build activation cloud utterance context for subsequent tokens.
        self._current_utterance_compounds: List = []

        # Lazy-loaded spaCy model and lemmatizer
        self._nlp = None
        self._lemmatizer_ready = False

    def _ensure_lemmatizer(self):
        """Lazy-load spaCy to avoid import-time cost."""
        if not self._lemmatizer_ready:
            try:
                from core.lemmatizer import get_nlp
                self._nlp = get_nlp()
                self._lemmatizer_ready = True
            except Exception as e:
                log.warning(f"Router: spaCy not available, skipping lemmatization: {e}")
                self._lemmatizer_ready = True  # don't retry

    def _get_know(self):
        """Lazy import of KNOW singleton to avoid circular deps."""
        from primes.KNOW import know
        return know

    # ══════════════════════════════════════════════════════════════════════
    # Main entry point
    # ══════════════════════════════════════════════════════════════════════

    def resolve_observation(
        self,
        observation: Dict[str, Any],
    ) -> List[TokenResolution]:
        """
        Resolve all tokens in an observation through the cascade.

        Args:
            observation: raw observation dict from READ with
                         {data: {text: str}, timestamp, modality, ...}

        Returns:
            List of TokenResolution, one per token.
        """
        data = observation.get("data", {})
        raw_text = data.get("text") or observation.get("raw_input", "")

        if not raw_text:
            return []

        # Run spaCy analysis on the full text (sentence context matters)
        self._ensure_lemmatizer()
        spacy_tokens = None
        if self._nlp is not None:
            try:
                from core.lemmatizer import analyze
                spacy_tokens = analyze(raw_text, nlp=self._nlp)
            except Exception as e:
                log.warning(f"Router: spaCy analysis failed: {e}")

        # If spaCy unavailable, fall back to whitespace split
        if spacy_tokens is None:
            tokens = raw_text.split()
            return [self._resolve_single_fallback(tok, i) for i, tok in enumerate(tokens)]

        # Resolve each spaCy token through the cascade
        resolutions: List[TokenResolution] = []
        self._current_utterance_compounds = []   # reset per utterance
        know = self._get_know()

        for tok_analysis in spacy_tokens:
            resolution = self._resolve_token(tok_analysis)
            resolutions.append(resolution)
            # Track resolved compounds for activation cloud utterance context
            if resolution.compound_id is not None:
                compound = know.by_id(resolution.compound_id)
                if compound is not None:
                    self._current_utterance_compounds.append(compound)

        return resolutions

    def resolve_single(self, token_text: str) -> TokenResolution:
        """
        On-demand resolution of a single token (used by THINK/KNOW).

        Note: single-word analysis is less accurate than full-sentence
        because spaCy loses context. Prefer resolve_observation() for
        full text.
        """
        self._ensure_lemmatizer()
        if self._nlp is not None:
            try:
                from core.lemmatizer import analyze_token
                tok_analysis = analyze_token(token_text, nlp=self._nlp)
                if tok_analysis is not None:
                    return self._resolve_token(tok_analysis)
            except Exception:
                pass
        return self._resolve_single_fallback(token_text, 0)

    # ══════════════════════════════════════════════════════════════════════
    # Resolution cascade (per token)
    # ══════════════════════════════════════════════════════════════════════

    def _resolve_token(self, tok) -> TokenResolution:
        """
        Full resolution cascade for a single spaCy-analyzed token.

        Steps per SYMBOL_CONCEPT.md:
          1. KNOW.by_symbol(surface)    → exact hit?
          2. KNOW.by_symbol(lemma)      → root found?
          3. Create family member        → if root exists and surface ≠ lemma
          4. LLM specialist              → if enabled and no resolution yet
          5. Prime-name heuristic        → last resort
          6. Unresolved                  → placeholder
        """
        self.stats.total_tokens += 1
        surface = tok.surface
        lemma = tok.lemma
        pos = tok.pos
        gram_primes = tok.grammatical_primes
        idx = tok.idx

        know = self._get_know()

        # ── Step 1: Exact KNOW lookup by surface form ─────────────────
        existing = know.by_symbol(surface)
        if existing is not None:
            self.stats.know_exact_hits += 1
            return TokenResolution(
                token=surface, prime=None, score=1.0, position=idx,
                method="know_exact", compound_id=existing.id,
                lemma=lemma, pos=pos, grammatical_primes=gram_primes,
            )

        # Also try lowercased surface (KNOW stores lowercase symbols typically)
        if surface != surface.lower():
            existing = know.by_symbol(surface.lower())
            if existing is not None:
                self.stats.know_exact_hits += 1
                return TokenResolution(
                    token=surface, prime=None, score=1.0, position=idx,
                    method="know_exact", compound_id=existing.id,
                    lemma=lemma, pos=pos, grammatical_primes=gram_primes,
                )

        # ── Step 2: Lemma lookup in KNOW ──────────────────────────────
        is_inflected = (surface.lower() != lemma) and lemma != surface.lower()

        if is_inflected:
            root_compound = know.by_symbol(lemma)
            if root_compound is not None:
                self.stats.know_lemma_hits += 1

                # ── Step 3: Create family member ──────────────────────
                family_compound = self._create_family_member(
                    surface=surface.lower(),
                    root=root_compound,
                    gram_primes=gram_primes,
                    know=know,
                )
                if family_compound is not None:
                    self.stats.family_members_created += 1
                    return TokenResolution(
                        token=surface, prime=None, score=0.95, position=idx,
                        method="family_member", compound_id=family_compound.id,
                        lemma=lemma, pos=pos, grammatical_primes=gram_primes,
                        is_family_member=True, family_root_id=root_compound.id,
                    )

        # ── Step 4: LLM specialist (with activation cloud context) ───────
        if self._enable_specialist and self._specialist_fn is not None:
            try:
                # Build activation cloud for rich context to the specialist
                try:
                    from core.activation_cloud import build_activation_cloud, serialise_cloud
                    cloud = build_activation_cloud(
                        token=surface,
                        position=idx,
                        lemma=lemma,
                        pos=pos,
                        utterance_so_far=list(self._current_utterance_compounds),
                        active_narrative=self._get_narrative_context(),
                    )
                    if cloud.fast_path:
                        # Compound found with high confidence — skip specialist
                        self.stats.fast_path_skips += 1
                        self.stats.know_exact_hits += 1
                        return TokenResolution(
                            token=surface, prime=None, score=1.0, position=idx,
                            method="know_exact", compound_id=cloud.exact_match.id,
                            lemma=lemma, pos=pos, grammatical_primes=gram_primes,
                        )
                    cloud_context = serialise_cloud(cloud)
                except Exception:
                    cloud_context = ""

                self.stats.specialist_calls += 1
                specialist_result = self._specialist_fn(surface, {
                    "lemma": lemma,
                    "pos": pos,
                    "grammatical_primes": list(gram_primes),
                    "context": "ingestion",
                    "activation_cloud": cloud_context,
                })
                if specialist_result and specialist_result.get("prime"):
                    return TokenResolution(
                        token=surface,
                        prime=specialist_result["prime"],
                        score=specialist_result.get("score", 0.7),
                        position=idx,
                        method="specialist",
                        compound_id=None,
                        lemma=lemma, pos=pos, grammatical_primes=gram_primes,
                    )
            except Exception as e:
                self.stats.specialist_failures += 1
                log.warning(f"Router: specialist failed for '{surface}': {e}")

        # ── Step 5: Prime-name heuristic ──────────────────────────────
        lower = surface.lower()
        if lower in _PRIME_NAME_SET:
            self.stats.heuristic_hits += 1
            return TokenResolution(
                token=surface,
                prime=_LOWER_TO_CANONICAL[lower],
                score=1.0,
                position=idx,
                method="heuristic",
                compound_id=None,
                lemma=lemma, pos=pos, grammatical_primes=gram_primes,
            )

        # ── Step 6: Unresolved (placeholder) ──────────────────────────
        self.stats.unresolved += 1
        return TokenResolution(
            token=surface, prime=None, score=0.0, position=idx,
            method="unresolved", compound_id=None,
            lemma=lemma, pos=pos, grammatical_primes=gram_primes,
        )

    def _get_narrative_context(self, n: int = 5) -> List:
        """Return recent compounds from KNOW for narrative context.

        Phase 1 proxy using recent_compounds(). Phase 2+: replaced by
        narrative-thread-aware retrieval.
        """
        try:
            know = self._get_know()
            return know.recent_compounds(n)
        except Exception:
            return []

    def _resolve_single_fallback(self, token_text: str, position: int) -> TokenResolution:
        """Fallback when spaCy is unavailable — just prime-name heuristic + KNOW."""
        self.stats.total_tokens += 1
        know = self._get_know()

        # KNOW lookup
        existing = know.by_symbol(token_text)
        if existing is None:
            existing = know.by_symbol(token_text.lower())
        if existing is not None:
            self.stats.know_exact_hits += 1
            return TokenResolution(
                token=token_text, prime=None, score=1.0, position=position,
                method="know_exact", compound_id=existing.id,
                lemma=None, pos=None, grammatical_primes=set(),
            )

        # Prime-name check
        lower = token_text.lower()
        if lower in _PRIME_NAME_SET:
            self.stats.heuristic_hits += 1
            return TokenResolution(
                token=token_text, prime=_LOWER_TO_CANONICAL[lower],
                score=1.0, position=position, method="heuristic",
                compound_id=None, lemma=None, pos=None, grammatical_primes=set(),
            )

        # Unresolved
        self.stats.unresolved += 1
        return TokenResolution(
            token=token_text, prime=None, score=0.0, position=position,
            method="unresolved", compound_id=None,
            lemma=None, pos=None, grammatical_primes=set(),
        )

    # ══════════════════════════════════════════════════════════════════════
    # Family member creation
    # ══════════════════════════════════════════════════════════════════════

    def _create_family_member(
        self,
        surface: str,
        root,
        gram_primes: set[str],
        know,
    ):
        """
        Create a family member compound for an inflected form.

        Family member contract (from compound_concept.md):
          symbol   = surface form (e.g. "ran")
          primebit = root.primebit ∪ grammatical primes
          nested   = [root.id]
          relations = [Relation("KIND", root.id)]
          grounded = root.grounded
        """
        from core.compound import Compound, Relation

        # Build primebit: root primebit ∪ grammatical primes
        member_pb = root.primebit
        if gram_primes:
            gram_pb = PrimeBit.from_prime_names(list(gram_primes))
            member_pb = member_pb | gram_pb

        member = Compound.concept(
            temp_id=-9999,  # KNOW assigns permanent ID
            symbol=surface,
            primebit=member_pb,
            confidence=root.confidence if hasattr(root, 'confidence') else 0.9,
            grounded=root.grounded,
        )
        # Set family structure (not accepted by concept() factory)
        member.nested = [root.id]
        member.relations = [Relation(predicate="KIND", target_id=root.id)]

        # Store in KNOW immediately so subsequent tokens can find it
        try:
            id_map = know.store_batch([member])
            # Get the permanent ID
            new_id = id_map.get(member.id, member.id)
            member.id = new_id
            log.info(f"Router: created family member '{surface}' → '{root.symbol}' "
                     f"(id={new_id}, primes={gram_primes})")
            return member
        except Exception as e:
            log.error(f"Router: failed to create family member '{surface}': {e}")
            return None
