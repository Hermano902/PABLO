"""Tests for core/specialists.py — LLM specialist infrastructure."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch
import json

from core.specialists import (
    SpecialistConfig, Specialist, TextGrounder, ObservationGrounder,
    SpecialistRegistry, DEFAULT_CONFIG, PRIME_LIST,
)


# ══════════════════════════════════════════════════════════════════════════════
# SpecialistConfig
# ══════════════════════════════════════════════════════════════════════════════

class TestSpecialistConfig:
    def test_defaults(self):
        cfg = SpecialistConfig()
        assert cfg.base_url == "http://localhost:11434/v1"
        assert cfg.model == "phi3:mini"
        assert cfg.temperature == 0.1
        assert cfg.max_tokens == 512
        assert cfg.timeout == 30.0
        assert cfg.api_key == "ollama"

    def test_from_dict(self):
        d = {"model": "qwen2.5:3b", "temperature": 0.2, "extra_field": "ignored"}
        cfg = SpecialistConfig.from_dict(d)
        assert cfg.model == "qwen2.5:3b"
        assert cfg.temperature == 0.2
        # base_url should keep default
        assert cfg.base_url == "http://localhost:11434/v1"

    def test_custom_config(self):
        cfg = SpecialistConfig(model="gemma2:2b", max_tokens=256)
        assert cfg.model == "gemma2:2b"
        assert cfg.max_tokens == 256


# ══════════════════════════════════════════════════════════════════════════════
# PRIME_LIST
# ══════════════════════════════════════════════════════════════════════════════

class TestPrimeList:
    def test_contains_all_63(self):
        """The PRIME_LIST string should mention all 63 primes."""
        from core.primebit import PRIME_INDEX
        for name in PRIME_INDEX:
            assert name in PRIME_LIST, f"Missing prime in PRIME_LIST: {name}"


# ══════════════════════════════════════════════════════════════════════════════
# TextGrounder prompts & parsing
# ══════════════════════════════════════════════════════════════════════════════

class TestTextGrounder:
    def test_build_prompt(self):
        """Prompt should contain the word and prime list."""
        tg = TextGrounder()
        messages = tg._build_prompt("cat", {"lemma": "cat", "pos": "NOUN"})
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "cat" in messages[1]["content"]
        assert "NOUN" in messages[1]["content"]
        assert "BODY" in messages[0]["content"]  # prime list present

    def test_parse_valid_response(self):
        """Successfully parse a well-formed JSON response."""
        tg = TextGrounder()
        response = json.dumps({
            "primes": [
                {"prime": "BODY", "score": 0.9},
                {"prime": "LIFE", "score": 0.8},
                {"prime": "FEEL", "score": 0.7},
            ],
            "reasoning": "a living body"
        })
        result = tg._parse_response(response, "cat")
        assert result is not None
        assert result["prime"] == "BODY"
        assert result["score"] == 0.9
        assert len(result["candidate_primes"]) == 3

    def test_parse_code_fenced_response(self):
        """Handle markdown code fences in LLM output."""
        tg = TextGrounder()
        response = '```json\n{"primes": [{"prime": "ENTITY", "score": 0.9}], "reasoning": "an entity"}\n```'
        result = tg._parse_response(response, "table")
        assert result is not None
        assert result["prime"] == "ENTITY"

    def test_parse_invalid_json(self):
        """Return None for unparseable responses."""
        tg = TextGrounder()
        result = tg._parse_response("This is not JSON at all", "cat")
        assert result is None

    def test_parse_empty_primes(self):
        """Return None when primes list is empty."""
        tg = TextGrounder()
        response = json.dumps({"primes": [], "reasoning": "no idea"})
        result = tg._parse_response(response, "unknown")
        assert result is None

    def test_parse_invalid_prime_names_filtered(self):
        """Invalid prime names are filtered out."""
        tg = TextGrounder()
        response = json.dumps({
            "primes": [
                {"prime": "BODY", "score": 0.9},
                {"prime": "INVALID_PRIME", "score": 0.5},
                {"prime": "LIFE", "score": 0.7},
            ],
            "reasoning": "test"
        })
        result = tg._parse_response(response, "cat")
        assert result is not None
        # Only BODY and LIFE should survive
        prime_names = [p["prime"] for p in result["candidate_primes"]]
        assert "BODY" in prime_names
        assert "LIFE" in prime_names
        assert "INVALID_PRIME" not in prime_names

    def test_parse_score_clamping(self):
        """Scores should be clamped to [0.0, 1.0]."""
        tg = TextGrounder()
        response = json.dumps({
            "primes": [{"prime": "ENTITY", "score": 1.5}],
            "reasoning": "very entity"
        })
        result = tg._parse_response(response, "test")
        assert result is not None
        assert result["score"] <= 1.0

    def test_ground_with_mock_llm(self):
        """Test the full ground() path with a mocked LLM client."""
        tg = TextGrounder()

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "primes": [
                {"prime": "BODY", "score": 0.9},
                {"prime": "LIFE", "score": 0.8},
            ],
            "reasoning": "living body"
        })
        mock_client.chat.completions.create.return_value = mock_response
        tg._client = mock_client

        result = tg.ground("cat", {"lemma": "cat", "pos": "NOUN"})
        assert result is not None
        assert result["prime"] == "BODY"
        assert "provenance" in result
        assert result["provenance"]["specialist"] == "text-grounder"
        assert tg.stats["successes"] == 1

    def test_ground_llm_failure(self):
        """ground() returns None and increments failures on LLM error."""
        tg = TextGrounder()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Connection refused")
        tg._client = mock_client

        result = tg.ground("cat", {"lemma": "cat", "pos": "NOUN"})
        assert result is None
        assert tg.stats["failures"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# ObservationGrounder prompts & parsing
# ══════════════════════════════════════════════════════════════════════════════

class TestObservationGrounder:
    def test_build_prompt(self):
        og = ObservationGrounder()
        messages = og._build_prompt("the cat sat on the mat", {"tokens": [
            {"surface": "the", "lemma": "the", "pos": "DET", "dep": "det"},
            {"surface": "cat", "lemma": "cat", "pos": "NOUN", "dep": "nsubj"},
        ]})
        assert len(messages) == 2
        assert "cat" in messages[1]["content"]

    def test_parse_valid_response(self):
        og = ObservationGrounder()
        response = json.dumps({
            "tokens": [
                {"token": "cat", "primes": [{"prime": "BODY", "score": 0.9}], "role": "agent"},
                {"token": "sat", "primes": [{"prime": "MOVE", "score": 0.8}], "role": "action"},
            ],
            "overall_confidence": 0.85,
            "structure": "agent does action"
        })
        result = og._parse_response(response, "the cat sat")
        assert result is not None
        assert len(result["candidate_primes"]) == 2
        assert len(result["roles"]) == 2
        assert result["confidence"] == 0.85

    def test_parse_invalid_json(self):
        og = ObservationGrounder()
        result = og._parse_response("garbage", "test")
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# SpecialistRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestSpecialistRegistry:
    def test_create_default(self):
        reg = SpecialistRegistry.create_default()
        assert reg.get("text-grounder") is not None
        assert reg.get("observation-grounder") is not None
        assert reg.get_default() is not None

    def test_create_default_with_config(self):
        cfg = SpecialistConfig(model="qwen2.5:3b")
        reg = SpecialistRegistry.create_default(cfg)
        tg = reg.get("text-grounder")
        assert tg.config.model == "qwen2.5:3b"

    def test_register_custom(self):
        reg = SpecialistRegistry()
        mock_spec = MagicMock()
        reg.register("custom", mock_spec)
        assert reg.get("custom") is mock_spec

    def test_ground_token_delegates(self):
        """ground_token should call the default specialist."""
        reg = SpecialistRegistry()
        mock_spec = MagicMock()
        mock_spec.ground.return_value = {"prime": "BODY", "score": 0.9}
        reg.set_default(mock_spec)

        result = reg.ground_token("cat", {"lemma": "cat"})
        assert result["prime"] == "BODY"
        mock_spec.ground.assert_called_once_with("cat", {"lemma": "cat"})

    def test_ground_token_no_default(self):
        """ground_token returns None when no default specialist."""
        reg = SpecialistRegistry()
        result = reg.ground_token("cat", {})
        assert result is None

    def test_ground_observation_delegates(self):
        reg = SpecialistRegistry()
        mock_obs = MagicMock()
        mock_obs.ground.return_value = {"candidate_primes": [], "confidence": 0.5}
        reg.register("observation-grounder", mock_obs)

        result = reg.ground_observation("the cat sat", [])
        assert result is not None
        mock_obs.ground.assert_called_once()

    def test_specialist_stats(self):
        """Specialists should track call counts."""
        tg = TextGrounder()
        assert tg.stats["calls"] == 0
        assert tg.stats["successes"] == 0
        assert tg.stats["failures"] == 0
