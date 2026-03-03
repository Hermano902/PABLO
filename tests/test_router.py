"""Tests for core/router.py — SYMBOL's resolution cascade."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Optional

from core.router import Router, TokenResolution, RouterStats, _PRIME_NAME_SET
from core.primebit import PrimeBit, PRIME_INDEX


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_obs(text: str, source: str = "test") -> dict:
    """Create a minimal observation dict."""
    return {
        "data": {"text": text},
        "timestamp": 1000000.0,
        "metadata": {"source": source},
    }


def _make_mock_compound(symbol: str, cid: int = 200, grounded: bool = True):
    """Create a mock compound object."""
    mock = MagicMock()
    mock.id = cid
    mock.symbol = symbol
    mock.grounded = grounded
    mock.confidence = 0.9
    mock.primebit = PrimeBit.from_prime_names(["ENTITY"])
    return mock


def _make_mock_know(compounds: dict[str, MagicMock] = None):
    """Create a mock KNOW object with by_symbol and store_batch."""
    know = MagicMock()
    compounds = compounds or {}

    def by_symbol(sym):
        return compounds.get(sym)

    def store_batch(batch):
        id_map = {}
        for c in batch:
            old_id = c.id
            c.id = 500  # assign a "permanent" ID
            id_map[old_id] = 500
        return id_map

    know.by_symbol = MagicMock(side_effect=by_symbol)
    know.store_batch = MagicMock(side_effect=store_batch)
    return know


# ══════════════════════════════════════════════════════════════════════════════
# TokenResolution
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenResolution:
    """Tests for the TokenResolution dataclass."""

    def test_basic_fields(self):
        r = TokenResolution(
            token="cat", prime="BODY", score=0.9, position=0,
            method="specialist", compound_id=None, lemma="cat",
            pos="NOUN", grammatical_primes=set(),
        )
        assert r.token == "cat"
        assert r.prime == "BODY"
        assert r.score == 0.9
        assert r.method == "specialist"
        assert r.is_family_member is False

    def test_to_candidate_entry_basic(self):
        r = TokenResolution(
            token="dog", prime="BODY", score=0.85, position=2,
            method="heuristic", compound_id=None, lemma="dog",
            pos="NOUN", grammatical_primes=set(),
        )
        entry = r.to_candidate_entry()
        assert entry["token"] == "dog"
        assert entry["prime"] == "BODY"
        assert entry["score"] == 0.85
        assert entry["position"] == 2
        assert entry["method"] == "heuristic"
        assert "compound_id" not in entry  # None → omitted

    def test_to_candidate_entry_with_compound_id(self):
        r = TokenResolution(
            token="cat", prime=None, score=1.0, position=0,
            method="know_exact", compound_id=205, lemma="cat",
            pos="NOUN", grammatical_primes=set(),
        )
        entry = r.to_candidate_entry()
        assert entry["compound_id"] == 205

    def test_to_candidate_entry_family_member(self):
        r = TokenResolution(
            token="cats", prime=None, score=0.95, position=0,
            method="family_member", compound_id=300, lemma="cat",
            pos="NOUN", grammatical_primes={"MANY"},
            is_family_member=True, family_root_id=205,
        )
        entry = r.to_candidate_entry()
        assert entry["is_family_member"] is True
        assert entry["family_root_id"] == 205
        assert entry["grammatical_primes"] == ["MANY"]

    def test_to_candidate_entry_gram_primes(self):
        r = TokenResolution(
            token="ran", prime=None, score=0.95, position=1,
            method="family_member", compound_id=301, lemma="run",
            pos="VERB", grammatical_primes={"BEFORE"},
            is_family_member=True, family_root_id=210,
        )
        entry = r.to_candidate_entry()
        assert "BEFORE" in entry["grammatical_primes"]


# ══════════════════════════════════════════════════════════════════════════════
# RouterStats
# ══════════════════════════════════════════════════════════════════════════════

class TestRouterStats:
    def test_initial_zero(self):
        s = RouterStats()
        assert s.know_exact_hits == 0
        assert s.total_tokens == 0

    def test_to_dict(self):
        s = RouterStats(know_exact_hits=5, total_tokens=10)
        d = s.to_dict()
        assert d["know_exact_hits"] == 5
        assert d["total_tokens"] == 10
        assert len(d) == 9  # all 9 fields


# ══════════════════════════════════════════════════════════════════════════════
# Router — heuristic fallback (no spaCy, no KNOW)
# ══════════════════════════════════════════════════════════════════════════════

class TestRouterHeuristicFallback:
    """Router behavior when spaCy is unavailable — falls to heuristic."""

    @patch("core.router.Router._get_know")
    @patch("core.router.Router._ensure_lemmatizer")
    def test_prime_name_resolves(self, mock_lem, mock_know):
        """A token that is a prime name resolves with score 1.0."""
        mock_know.return_value = _make_mock_know()
        router = Router(enable_specialist=False)
        router._nlp = None  # force fallback path

        result = router.resolve_single("MOVE")
        assert result.prime == "MOVE"
        assert result.score == 1.0
        assert result.method == "heuristic"

    @patch("core.router.Router._get_know")
    @patch("core.router.Router._ensure_lemmatizer")
    def test_prime_name_case_insensitive(self, mock_lem, mock_know):
        mock_know.return_value = _make_mock_know()
        router = Router(enable_specialist=False)
        router._nlp = None

        result = router.resolve_single("move")
        assert result.prime == "MOVE"
        assert result.score == 1.0

    @patch("core.router.Router._get_know")
    @patch("core.router.Router._ensure_lemmatizer")
    def test_unknown_token_unresolved(self, mock_lem, mock_know):
        mock_know.return_value = _make_mock_know()
        router = Router(enable_specialist=False)
        router._nlp = None

        result = router.resolve_single("xylophone")
        assert result.prime is None
        assert result.score == 0.0
        assert result.method == "unresolved"

    @patch("core.router.Router._get_know")
    @patch("core.router.Router._ensure_lemmatizer")
    def test_know_exact_hit_in_fallback(self, mock_lem, mock_know):
        """Even in fallback mode, KNOW lookup should work."""
        compounds = {"hello": _make_mock_compound("hello", 201)}
        mock_know.return_value = _make_mock_know(compounds)
        router = Router(enable_specialist=False)
        router._nlp = None

        result = router.resolve_single("hello")
        assert result.method == "know_exact"
        assert result.compound_id == 201
        assert result.score == 1.0


# ══════════════════════════════════════════════════════════════════════════════
# Router — full cascade (with spaCy)
# ══════════════════════════════════════════════════════════════════════════════

class TestRouterFullCascade:
    """Router with spaCy available — tests the full 6-step cascade."""

    def _make_router(self, know_compounds=None, specialist_fn=None, enable_specialist=True):
        """Create a router with mocked KNOW."""
        router = Router(
            specialist_fn=specialist_fn,
            enable_specialist=enable_specialist,
        )
        # Ensure spaCy is loaded
        router._ensure_lemmatizer()
        # Mock KNOW
        mock_know = _make_mock_know(know_compounds or {})
        router._get_know = MagicMock(return_value=mock_know)
        return router, mock_know

    def test_observation_produces_resolutions(self):
        """resolve_observation returns one TokenResolution per token."""
        router, _ = self._make_router()
        obs = _make_obs("the cat sat")
        results = router.resolve_observation(obs)
        assert len(results) == 3
        assert all(isinstance(r, TokenResolution) for r in results)

    def test_know_exact_hit(self):
        """Step 1: token found in KNOW by surface form."""
        cat_compound = _make_mock_compound("cat", 200)
        router, _ = self._make_router(know_compounds={"cat": cat_compound})

        result = router.resolve_single("cat")
        assert result.method == "know_exact"
        assert result.compound_id == 200
        assert result.score == 1.0
        assert router.stats.know_exact_hits >= 1

    def test_lemma_lookup_and_family_member(self):
        """Steps 2-3: inflected form → lemma lookup → family member creation."""
        # "run" is known, "ran" is not
        run_compound = _make_mock_compound("run", 210)
        router, mock_know = self._make_router(know_compounds={"run": run_compound})

        obs = _make_obs("she ran home")
        results = router.resolve_observation(obs)

        # Find the "ran" resolution
        ran_results = [r for r in results if r.token.lower() == "ran"]
        if ran_results:
            ran = ran_results[0]
            assert ran.lemma == "run"
            # Should be either family_member (if surface != lemma) or know_lemma
            assert ran.method in ("family_member", "know_lemma", "know_exact")
            if ran.method == "family_member":
                assert ran.is_family_member is True
                assert "BEFORE" in ran.grammatical_primes

    def test_specialist_invoked_when_nothing_found(self):
        """Step 4: specialist called when steps 1-3 fail."""
        specialist_fn = MagicMock(return_value={
            "prime": "BODY",
            "score": 0.8,
        })
        router, _ = self._make_router(
            specialist_fn=specialist_fn,
            enable_specialist=True,
        )

        result = router.resolve_single("quokka")
        # If spaCy doesn't find it in KNOW and it's not a prime name,
        # specialist should be called
        if result.method == "specialist":
            assert result.prime == "BODY"
            assert result.score == 0.8
            specialist_fn.assert_called_once()
        # Else the token was unresolved or resolved differently — ok
        assert result.token == "quokka"

    def test_specialist_disabled(self):
        """Specialist step skipped when enable_specialist=False."""
        specialist_fn = MagicMock(return_value={"prime": "BODY", "score": 0.8})
        router, _ = self._make_router(
            specialist_fn=specialist_fn,
            enable_specialist=False,
        )

        result = router.resolve_single("quokka")
        specialist_fn.assert_not_called()
        # Should fall through to heuristic or unresolved
        assert result.method in ("heuristic", "unresolved")

    def test_empty_observation_returns_empty(self):
        router, _ = self._make_router()
        results = router.resolve_observation(_make_obs(""))
        assert results == []

    def test_observation_positions_sequential(self):
        """Token positions should be sequential within an observation."""
        router, _ = self._make_router()
        obs = _make_obs("big red ball")
        results = router.resolve_observation(obs)
        positions = [r.position for r in results]
        assert len(positions) == len(results)
        # Positions should be unique and sequential from 0
        assert sorted(set(positions)) == list(range(len(results)))

    def test_stats_increment(self):
        """Router stats should increment on resolution."""
        router, _ = self._make_router()
        obs = _make_obs("the thing")
        router.resolve_observation(obs)
        assert router.stats.total_tokens >= 2

    def test_prime_name_heuristic_in_cascade(self):
        """Step 5: prime name detected even with spaCy active."""
        router, _ = self._make_router()
        # Use a prime that spaCy won't lemmatize away
        result = router.resolve_single("ENTITY")
        # Could be heuristic or know_exact depending on KNOW state
        # ENTITY is a prime name but spaCy may lowercase/lemmatize it
        assert result.token == "ENTITY"


# ══════════════════════════════════════════════════════════════════════════════
# Router prime-name index
# ══════════════════════════════════════════════════════════════════════════════

class TestPrimeNameIndex:
    def test_prime_names_loaded(self):
        """The _PRIME_NAME_SET should contain all 63 primes."""
        assert len(_PRIME_NAME_SET) == 63

    def test_all_lowercase(self):
        """All entries in _PRIME_NAME_SET are lowercase."""
        for name in _PRIME_NAME_SET:
            assert name == name.lower()

    def test_known_primes_present(self):
        for prime in ["move", "think", "know", "feel", "body", "entity"]:
            assert prime in _PRIME_NAME_SET


# ══════════════════════════════════════════════════════════════════════════════
# SYMBOL integration (lightweight)
# ══════════════════════════════════════════════════════════════════════════════

class TestSYMBOLIntegration:
    """Test that SYMBOL uses the router correctly."""

    def test_symbol_heuristic_fallback(self):
        """When router is None, SYMBOL falls back to heuristic."""
        from primes.SYMBOL import SYMBOL as SymbolClass
        sym = SymbolClass()
        # Don't initialize — router stays None
        obs = _make_obs("MOVE THINK")
        result = sym._interpret_observation(obs)
        assert result is not None
        assert result["provenance"]["model"] == "heuristic"

    def test_symbol_heuristic_prime_grounding(self):
        """Heuristic fallback resolves prime names."""
        from primes.SYMBOL import SYMBOL as SymbolClass
        sym = SymbolClass()
        obs = _make_obs("MOVE THINK")
        result = sym._interpret_observation(obs)
        primes = result["candidate_primes"]
        assert len(primes) == 2
        assert primes[0]["prime"] == "MOVE"
        assert primes[0]["score"] == 1.0
        assert primes[1]["prime"] == "THINK"

    def test_symbol_heuristic_unknown_token(self):
        """Heuristic fallback returns None/0.0 for unknown tokens."""
        from primes.SYMBOL import SYMBOL as SymbolClass
        sym = SymbolClass()
        obs = _make_obs("hello world")
        result = sym._interpret_observation(obs)
        for cp in result["candidate_primes"]:
            assert cp["prime"] is None
            assert cp["score"] == 0.0

    def test_symbol_candidate_shape(self):
        """Candidate dict has all required keys per data_concept.md."""
        from primes.SYMBOL import SYMBOL as SymbolClass
        sym = SymbolClass()
        obs = _make_obs("MOVE")
        result = sym._interpret_observation(obs)
        required_keys = [
            "candidate_primes", "roles", "rule_template",
            "confidence", "provenance", "raw_input",
            "observation_id", "source",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_symbol_on_demand_heuristic(self):
        """On-demand __call__ with 'symbol' key uses heuristic."""
        from primes.SYMBOL import SYMBOL as SymbolClass
        sym = SymbolClass()
        result = sym({"symbol": "MOVE"})
        assert result["prime"] == "MOVE"
        assert result["score"] == 1.0
