"""
Specialists — LLM-based compound construction for SYMBOL.

Each specialist receives spaCy-analyzed token data and produces a
near-compound candidate using a local LLM via Ollama (OpenAI-compatible API).

Architecture (per SYMBOL_ARCHITECTURE.md):
  - Specialists are proposal engines — they produce candidates, never write to KNOW.
  - All output follows the symbolicifier contract (candidate_primes, roles, confidence, provenance).
  - Specialists are invoked ONLY when cheaper heuristics (KNOW lookup, lemmatization,
    family member creation) fail. They are the fallback, not the default.

Model requirements (user spec):
  - Small, local, trainable, free-to-use models
  - Must run on GTX 1070 (8GB VRAM)
  - Served via Ollama (OpenAI-compatible endpoint)
  - Good at English semantic analysis and structured JSON output

Recommended models:
  - phi3:mini          (3.8B, Microsoft, MIT, strong English reasoning)
  - qwen2.5:3b         (3B, Alibaba, Apache 2.0, excellent structured output)
  - gemma2:2b          (2B, Google, small but capable)

Usage:
    specialist = TextGrounder(model="phi3:mini")
    candidate = specialist.ground("cat", {"lemma": "cat", "pos": "NOUN", ...})
    # → {"prime": "BODY", "score": 0.82, ...}
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SpecialistConfig:
    """Configuration for LLM specialist endpoints."""
    base_url:     str   = "http://localhost:11434/v1"  # Ollama OpenAI-compat
    model:        str   = "phi3:mini"                  # default model
    temperature:  float = 0.1                          # low temp for structured output
    max_tokens:   int   = 512                          # keep responses tight
    timeout:      float = 30.0                         # seconds
    api_key:      str   = "ollama"                     # Ollama doesn't need a key

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpecialistConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# Default config — can be overridden via SYMBOL's settings
DEFAULT_CONFIG = SpecialistConfig()


# ══════════════════════════════════════════════════════════════════════════════
# The 63 primes (for system prompt)
# ══════════════════════════════════════════════════════════════════════════════

PRIME_LIST = """The 63 canonical primes (use ONLY these names):
AFTER, ALL, AT, BAD, BE, BECAUSE, BEFORE, BETWEEN, BODY, CAN, CAUSE,
CHANGE, DATA, DO, DOWN, ENTITY, FAR, FEEL, FROM, GOOD, HAVE, HEAR,
HEAT, HERE, IN, KIND, KNOW, LAST, LEFT, LESS, LIFE, LIGHT, MAKE,
MANY, MORE, MOVE, NEAR, NEED, NONE, NOW, ONE, OPEN, OTHER, PART,
READ, RIGHT, SAY, SEE, SELF, SIDE, SOME, SYMBOL, THINK, THIS, TIME,
TO, TOUCH, UP, USE, WANT, WITH, WRITE, YOU"""


# ══════════════════════════════════════════════════════════════════════════════
# Base specialist
# ══════════════════════════════════════════════════════════════════════════════

class Specialist(ABC):
    """
    Abstract base for all LLM specialists.

    Each specialist handles a specific modality or grounding task.
    All share the same output contract (symbolicifier schema).
    """

    def __init__(self, config: Optional[SpecialistConfig] = None, name: str = "specialist"):
        self.config = config or DEFAULT_CONFIG
        self.name = name
        self._client = None
        self.stats = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "avg_latency_ms": 0.0,
        }

    def _get_client(self):
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=self.config.base_url,
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client

    @abstractmethod
    def _build_prompt(self, word: str, token_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build the chat messages for the LLM. Subclasses implement this."""
        ...

    @abstractmethod
    def _parse_response(self, raw: str, word: str) -> Optional[Dict[str, Any]]:
        """Parse the LLM response into a structured result. Subclasses implement this."""
        ...

    def ground(self, word: str, token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Invoke the LLM specialist to ground a word.

        Args:
            word:       the surface form to ground
            token_data: additional context {lemma, pos, grammatical_primes, context}

        Returns:
            {"prime": str, "score": float, "candidate_primes": [...], "provenance": {...}}
            or None on failure.
        """
        self.stats["calls"] += 1
        start = time.time()

        try:
            client = self._get_client()
            messages = self._build_prompt(word, token_data)

            response = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            raw_text = response.choices[0].message.content.strip()
            result = self._parse_response(raw_text, word)

            elapsed_ms = (time.time() - start) * 1000
            self._update_latency(elapsed_ms)

            if result is not None:
                self.stats["successes"] += 1
                result["provenance"] = {
                    "model": self.config.model,
                    "specialist": self.name,
                    "latency_ms": round(elapsed_ms, 1),
                }
                return result
            else:
                self.stats["failures"] += 1
                log.warning(f"{self.name}: could not parse LLM response for '{word}': {raw_text[:100]}")
                return None

        except Exception as e:
            self.stats["failures"] += 1
            elapsed_ms = (time.time() - start) * 1000
            self._update_latency(elapsed_ms)
            log.error(f"{self.name}: LLM call failed for '{word}': {e}")
            return None

    def _update_latency(self, elapsed_ms: float):
        """EMA of latency."""
        alpha = 0.1
        self.stats["avg_latency_ms"] = (
            self.stats["avg_latency_ms"] * (1 - alpha) + elapsed_ms * alpha
        )

    def is_available(self) -> bool:
        """Quick check if the LLM endpoint is reachable."""
        try:
            client = self._get_client()
            # Ollama lists models at /v1/models
            client.models.list()
            return True
        except Exception:
            return False


# ══════════════════════════════════════════════════════════════════════════════
# TextGrounder — the primary specialist for text grounding
# ══════════════════════════════════════════════════════════════════════════════

class TextGrounder(Specialist):
    """
    Grounds English words/tokens to PABLO's 63 primes.

    Given a word and its spaCy analysis (lemma, POS, morph features),
    the TextGrounder asks a local LLM to identify the most relevant
    primes that describe the word's meaning.

    This is SYMBOL's LLM fallback — only called when KNOW lookup,
    lemmatization, and family member creation all fail.
    """

    def __init__(self, config: Optional[SpecialistConfig] = None):
        super().__init__(config=config, name="text-grounder")

    def _build_prompt(self, word: str, token_data: Dict[str, Any]) -> List[Dict[str, str]]:
        lemma = token_data.get("lemma", word)
        pos = token_data.get("pos", "UNKNOWN")
        activation_context = token_data.get("activation_cloud", "")

        system_prompt = f"""You are a semantic decomposition engine for an AI system called PABLO.
Your task: given an English word, identify which of PABLO's 63 primitive concepts (primes) best describe its core meaning.

{PRIME_LIST}

Rules:
1. Choose 1-5 primes that capture the CORE meaning of the word.
2. The first prime should be the MOST relevant (highest score).
3. Score each prime 0.0-1.0 based on how central it is to the word's meaning.
4. Think about what the word fundamentally IS or DOES, not surface associations.
5. Respond with ONLY valid JSON — no explanation text.

Response format (strict JSON):
{{"primes": [{{"prime": "PRIME_NAME", "score": 0.95}}, ...], "reasoning": "brief"}}

Examples:
- "cat" → {{"primes": [{{"prime": "BODY", "score": 0.9}}, {{"prime": "LIFE", "score": 0.85}}, {{"prime": "FEEL", "score": 0.7}}, {{"prime": "MOVE", "score": 0.65}}], "reasoning": "living body that moves and feels"}}
- "table" → {{"primes": [{{"prime": "ENTITY", "score": 0.9}}, {{"prime": "MAKE", "score": 0.7}}, {{"prime": "HAVE", "score": 0.6}}], "reasoning": "a made entity that has/holds things"}}
- "quickly" → {{"primes": [{{"prime": "MOVE", "score": 0.8}}, {{"prime": "TIME", "score": 0.7}}, {{"prime": "LESS", "score": 0.6}}], "reasoning": "moving in less time"}}"""

        if activation_context:
            user_prompt = (
                f"Activation context from PABLO's memory:\n"
                f"{activation_context}\n"
                f"Given this context, assign primes to the word:\n"
                f'Word: "{word}" (lemma: "{lemma}", POS: {pos})\n'
                f"Decompose into primes:"
            )
        else:
            user_prompt = f'Word: "{word}" (lemma: "{lemma}", POS: {pos})\nDecompose into primes:'

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_response(self, raw: str, word: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from LLM into structured result."""
        try:
            # Handle markdown code fences
            text = raw.strip()
            if text.startswith("```"):
                # Strip ```json ... ```
                lines = text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines).strip()

            data = json.loads(text)
            primes_list = data.get("primes", [])

            if not primes_list:
                return None

            # Validate prime names against the canonical set
            from core.primebit import PRIME_INDEX
            valid_primes = set(PRIME_INDEX)

            candidate_primes = []
            for entry in primes_list:
                prime_name = entry.get("prime", "").upper()
                score = float(entry.get("score", 0.5))
                if prime_name in valid_primes:
                    candidate_primes.append({
                        "prime": prime_name,
                        "score": round(min(max(score, 0.0), 1.0), 3),
                    })

            if not candidate_primes:
                return None

            # Top prime is the primary grounding
            top = candidate_primes[0]

            return {
                "prime": top["prime"],
                "score": top["score"],
                "candidate_primes": candidate_primes,
                "reasoning": data.get("reasoning", ""),
            }

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            log.warning(f"TextGrounder: JSON parse failed for '{word}': {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# ObservationGrounder — grounds full observations (multi-token)
# ══════════════════════════════════════════════════════════════════════════════

class ObservationGrounder(Specialist):
    """
    Grounds an entire observation text into a structured near-compound candidate.

    Unlike TextGrounder (which handles individual tokens), this specialist
    receives a full sentence/observation and produces role assignments,
    structural analysis, and prime decomposition for all tokens at once.

    This is invoked for complex observations where per-token grounding
    is insufficient — e.g., identifying agent/patient roles, event structure.
    """

    def __init__(self, config: Optional[SpecialistConfig] = None):
        super().__init__(config=config, name="observation-grounder")

    def _build_prompt(self, text: str, token_data: Dict[str, Any]) -> List[Dict[str, str]]:
        # token_data here contains the full spaCy analysis for all tokens
        tokens_info = token_data.get("tokens", [])
        tokens_desc = "\n".join(
            f"  {t.get('surface', '?'):12s} lemma={t.get('lemma', '?'):12s} "
            f"pos={t.get('pos', '?'):6s} dep={t.get('dep', '?')}"
            for t in tokens_info
        )

        system_prompt = f"""You are a semantic analyzer for PABLO, an AI system with 63 primitive concepts.

{PRIME_LIST}

Your task: analyze the full observation text and produce a structured compound candidate.
For each content word (not function words like "the", "a", "is"), assign 1-3 primes.
Identify semantic roles: agent (who does), patient (what is done to), action, modifier.

Respond with ONLY valid JSON:
{{
  "tokens": [
    {{"token": "word", "primes": [{{"prime": "NAME", "score": 0.9}}], "role": "agent|patient|action|modifier|function"}}
  ],
  "overall_confidence": 0.85,
  "structure": "brief description of semantic structure"
}}"""

        user_prompt = f'Observation: "{text}"\n\nspaCy analysis:\n{tokens_desc}\n\nDecompose:'

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_response(self, raw: str, text: str) -> Optional[Dict[str, Any]]:
        """Parse observation-level grounding response."""
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                clean = "\n".join(lines).strip()

            data = json.loads(clean)
            tokens = data.get("tokens", [])

            if not tokens:
                return None

            from core.primebit import PRIME_INDEX
            valid_primes = set(PRIME_INDEX)

            candidate_primes = []
            roles = []
            for i, tok_entry in enumerate(tokens):
                token_text = tok_entry.get("token", "")
                primes = tok_entry.get("primes", [])
                role = tok_entry.get("role", "function")

                # Validate primes
                valid = []
                for p in primes:
                    name = p.get("prime", "").upper()
                    score = float(p.get("score", 0.5))
                    if name in valid_primes:
                        valid.append({"prime": name, "score": round(score, 3)})

                top_prime = valid[0]["prime"] if valid else None
                top_score = valid[0]["score"] if valid else 0.0

                candidate_primes.append({
                    "token": token_text,
                    "prime": top_prime,
                    "score": top_score,
                    "position": i,
                    "all_primes": valid,
                })

                if role in ("agent", "patient", "action", "modifier"):
                    roles.append({
                        "span": [i, i + 1],
                        "role": role,
                        "score": top_score,
                    })

            return {
                "candidate_primes": candidate_primes,
                "roles": roles,
                "confidence": data.get("overall_confidence", 0.5),
                "prime": candidate_primes[0]["prime"] if candidate_primes else None,
                "score": candidate_primes[0]["score"] if candidate_primes else 0.0,
            }

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            log.warning(f"ObservationGrounder: JSON parse failed: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# Specialist registry
# ══════════════════════════════════════════════════════════════════════════════

class SpecialistRegistry:
    """
    Registry of available specialists.

    The router uses this to dispatch to the right specialist based on
    modality and task type.
    """

    def __init__(self, config: Optional[SpecialistConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._specialists: Dict[str, Specialist] = {}
        self._default: Optional[Specialist] = None

    def register(self, name: str, specialist: Specialist) -> None:
        self._specialists[name] = specialist

    def set_default(self, specialist: Specialist) -> None:
        self._default = specialist

    def get(self, name: str) -> Optional[Specialist]:
        return self._specialists.get(name)

    def get_default(self) -> Optional[Specialist]:
        return self._default

    def ground_token(self, word: str, token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ground a single token using the appropriate specialist.

        This is the callable the Router uses as specialist_fn.
        """
        # For now, use the default text grounder for all tokens
        specialist = self._default
        if specialist is None:
            return None
        return specialist.ground(word, token_data)

    def ground_observation(self, text: str, tokens_data: List[Dict]) -> Optional[Dict[str, Any]]:
        """Ground a full observation using the observation specialist."""
        obs_specialist = self._specialists.get("observation-grounder")
        if obs_specialist is None:
            return None
        return obs_specialist.ground(text, {"tokens": tokens_data})

    @classmethod
    def create_default(cls, config: Optional[SpecialistConfig] = None) -> "SpecialistRegistry":
        """Create a registry with the default specialists."""
        cfg = config or DEFAULT_CONFIG
        registry = cls(config=cfg)

        text_grounder = TextGrounder(config=cfg)
        obs_grounder = ObservationGrounder(config=cfg)

        registry.register("text-grounder", text_grounder)
        registry.register("observation-grounder", obs_grounder)
        registry.set_default(text_grounder)

        return registry
