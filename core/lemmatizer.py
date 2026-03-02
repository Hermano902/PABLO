"""
Lemmatizer — spaCy-based morphological analysis for PABLO's pipeline.

This module is the first stage of SYMBOL's interpretation pipeline:

  raw text  →  spaCy (lemmatize + POS + morph)  →  LLM (build compound)  →  DATA (validate)

spaCy provides:
  - Tokenization
  - Lemmatization  ("ran" → "run", "mice" → "mouse", "bigger" → "big")
  - POS tagging    (NOUN, VERB, ADJ, ADV, PRON, DET, ADP, CONJ, ...)
  - Morphological features  (Tense=Past, Number=Plur, Degree=Cmp, ...)

This module maps spaCy's morph features to PABLO's grammatical primes:

  Tense=Past                          → BEFORE
  Aspect=Perf + Tense=Past            → BEFORE + LAST
  Aspect=Prog + Tense=Pres            → NOW
  Number=Plur (NOUN)                  → MANY
  Number=Sing (NOUN)                  → ONE
  Degree=Cmp                          → MORE
  Degree=Sup                          → MORE + ALL
  Person=1                            → SELF
  Person=2                            → YOU
  Person=3                            → OTHER

The output (TokenAnalysis list) is what SYMBOL uses to:
  1. Look up exact surface forms in KNOW
  2. Look up lemma (root form) in KNOW
  3. Create family members (KIND relation + grammatical primes)
  4. Feed to LLM specialist for new compound construction
  5. Pass compound candidate to DATA for validation

This module has zero dependencies on KNOW, SYMBOL, or any prime.
It is a pure NLP utility.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import spacy
from spacy.tokens import Doc, Token

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# spaCy model singleton
# ══════════════════════════════════════════════════════════════════════════════

_nlp: Optional[spacy.language.Language] = None


def get_nlp(model: str = "en_core_web_sm") -> spacy.language.Language:
    """
    Load and cache the spaCy model.

    Uses a module-level singleton to avoid reloading on every call.
    The model is loaded once and reused for all subsequent calls.
    """
    global _nlp
    if _nlp is None:
        log.info(f"Loading spaCy model: {model}")
        _nlp = spacy.load(model)
        log.info(f"spaCy model loaded: {model} ({len(_nlp.pipe_names)} pipes)")
    return _nlp


# ══════════════════════════════════════════════════════════════════════════════
# Morph feature → grammatical prime mapping
# ══════════════════════════════════════════════════════════════════════════════

# These match the mappings documented in compound_concept.md and symbol_concept.md
MORPH_TO_PRIMES: dict[str, set[str]] = {
    # Tense / Aspect
    "past":                 {"BEFORE"},
    "past_participle":      {"BEFORE", "LAST"},
    "present_participle":   {"NOW"},
    "future":               {"AFTER"},

    # Number
    "plural":               {"MANY"},
    "singular":             {"ONE"},

    # Degree
    "comparative":          {"MORE"},
    "superlative":          {"MORE", "ALL"},

    # Person
    "first_person":         {"SELF"},
    "second_person":        {"YOU"},
    "third_person":         {"OTHER"},
}


# ══════════════════════════════════════════════════════════════════════════════
# Token analysis result
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TokenAnalysis:
    """
    Morphological analysis of a single token from spaCy.

    This is what SYMBOL receives from the lemmatizer and uses for:
    - KNOW lookup (surface → exact match, lemma → root match)
    - Family member creation (surface ≠ lemma → KIND relation + grammatical_primes)
    - LLM specialist input (structured token data for compound construction)
    """
    surface:            str             # original token text ("ran", "cats")
    lemma:              str             # root form ("run", "cat")
    pos:                str             # spaCy POS tag ("VERB", "NOUN", "ADJ", ...)
    morph_features:     dict[str, str]  # raw spaCy morph {"Tense": "Past", "VerbForm": "Fin"}
    grammatical_primes: set[str]        # PABLO primes derived from morph ({"BEFORE"})
    inflection_type:    str             # human-readable inflection label ("past", "plural", ...)
    is_inflected:       bool            # True if surface ≠ lemma (family member candidate)
    is_stop:            bool            # True for function words (the, a, is, ...)
    dep:                str             # dependency relation ("nsubj", "dobj", "ROOT", ...)
    head_idx:           int             # index of syntactic head in the doc
    idx:                int             # token position in the doc

    def __repr__(self) -> str:
        primes_str = ",".join(sorted(self.grammatical_primes)) if self.grammatical_primes else "—"
        inflected = " *" if self.is_inflected else ""
        return (f"TokenAnalysis({self.surface!r} → {self.lemma!r} "
                f"[{self.pos}/{self.inflection_type}] primes={{{primes_str}}}{inflected})")


# ══════════════════════════════════════════════════════════════════════════════
# Core morph → prime mapping logic
# ══════════════════════════════════════════════════════════════════════════════

def _extract_grammatical_primes(token: Token) -> tuple[set[str], str]:
    """
    Map a spaCy token's morph features to PABLO grammatical primes.

    Returns (prime_set, inflection_type_label).

    spaCy morph features used:
      Tense=Past|Pres|Fut    Aspect=Perf|Prog    Number=Sing|Plur
      Degree=Pos|Cmp|Sup     Person=1|2|3         VerbForm=Fin|Part|Inf
    """
    morph = token.morph
    primes: set[str] = set()
    labels: list[str] = []

    tense = morph.get("Tense")
    aspect = morph.get("Aspect")
    verb_form = morph.get("VerbForm")
    number = morph.get("Number")
    degree = morph.get("Degree")
    person = morph.get("Person")

    # ── Tense / Aspect primes ─────────────────────────────────────────
    if tense:
        tense_val = tense[0] if isinstance(tense, list) else tense
        aspect_val = aspect[0] if aspect and isinstance(aspect, list) else (aspect if aspect else None)
        vf_val = verb_form[0] if verb_form and isinstance(verb_form, list) else (verb_form if verb_form else None)

        if tense_val == "Past":
            if aspect_val == "Perf" or vf_val == "Part":
                # "eaten", "broken" — past participle
                primes.update(MORPH_TO_PRIMES["past_participle"])
                labels.append("past_participle")
            else:
                # "ran", "played" — simple past
                primes.update(MORPH_TO_PRIMES["past"])
                labels.append("past")
        elif tense_val == "Pres":
            if aspect_val == "Prog" and vf_val == "Part":
                # "running", "thinking" — present participle / progressive
                primes.update(MORPH_TO_PRIMES["present_participle"])
                labels.append("present_participle")
            # base present tense is the root form — no grammatical prime needed
        elif tense_val == "Fut":
            primes.update(MORPH_TO_PRIMES["future"])
            labels.append("future")

    # ── Number primes (primarily for nouns) ───────────────────────────
    if number:
        number_val = number[0] if isinstance(number, list) else number
        if token.pos_ in ("NOUN", "PROPN"):
            if number_val == "Plur":
                primes.update(MORPH_TO_PRIMES["plural"])
                labels.append("plural")
            elif number_val == "Sing":
                primes.update(MORPH_TO_PRIMES["singular"])
                labels.append("singular")

    # ── Degree primes (adjectives / adverbs) ──────────────────────────
    if degree:
        degree_val = degree[0] if isinstance(degree, list) else degree
        if degree_val == "Cmp":
            primes.update(MORPH_TO_PRIMES["comparative"])
            labels.append("comparative")
        elif degree_val == "Sup":
            primes.update(MORPH_TO_PRIMES["superlative"])
            labels.append("superlative")

    # ── Person primes (pronouns, verb agreement) ──────────────────────
    if person:
        person_val = person[0] if isinstance(person, list) else person
        if person_val == "1":
            primes.update(MORPH_TO_PRIMES["first_person"])
            labels.append("first_person")
        elif person_val == "2":
            primes.update(MORPH_TO_PRIMES["second_person"])
            labels.append("second_person")
        elif person_val == "3":
            primes.update(MORPH_TO_PRIMES["third_person"])
            labels.append("third_person")

    inflection_type = "+".join(labels) if labels else "base"
    return primes, inflection_type


# ══════════════════════════════════════════════════════════════════════════════
# Main analysis function
# ══════════════════════════════════════════════════════════════════════════════

def analyze(text: str, nlp: Optional[spacy.language.Language] = None) -> list[TokenAnalysis]:
    """
    Analyze raw text using spaCy and return structured token analyses.

    This is the primary entry point for SYMBOL's lemmatization step.

    Args:
        text: raw input text to analyze
        nlp:  optional pre-loaded spaCy model (uses singleton if None)

    Returns:
        List of TokenAnalysis, one per token. SYMBOL uses these to:
        - Check KNOW for existing compounds (exact surface, then lemma)
        - Create family members for inflected forms of known roots
        - Build structured input for LLM specialist compound construction
    """
    if nlp is None:
        nlp = get_nlp()

    doc = nlp(text)
    results: list[TokenAnalysis] = []

    for token in doc:
        # Skip whitespace-only tokens
        if token.is_space:
            continue

        surface = token.text
        lemma = token.lemma_.lower()

        # Extract grammatical primes from morph features
        primes, inflection_type = _extract_grammatical_primes(token)

        # Build raw morph feature dict for downstream consumers
        morph_dict: dict[str, str] = {}
        for feat in token.morph:
            key, _, val = feat.partition("=")
            morph_dict[key] = val

        # Is this an inflected form? (surface differs from lemma)
        is_inflected = surface.lower() != lemma and lemma != surface.lower()

        results.append(TokenAnalysis(
            surface=surface,
            lemma=lemma,
            pos=token.pos_,
            morph_features=morph_dict,
            grammatical_primes=primes,
            inflection_type=inflection_type,
            is_inflected=is_inflected,
            is_stop=token.is_stop,
            dep=token.dep_,
            head_idx=token.head.i,
            idx=token.i,
        ))

    return results


def analyze_token(word: str, nlp: Optional[spacy.language.Language] = None) -> Optional[TokenAnalysis]:
    """
    Analyze a single word in isolation.

    Convenience wrapper when you have one word rather than a full sentence.
    Note: single-word analysis may be less accurate than full-sentence analysis
    because spaCy uses context for POS disambiguation.
    """
    results = analyze(word, nlp=nlp)
    return results[0] if results else None


# ══════════════════════════════════════════════════════════════════════════════
# Batch analysis for pipeline use
# ══════════════════════════════════════════════════════════════════════════════

def analyze_batch(texts: list[str], nlp: Optional[spacy.language.Language] = None) -> list[list[TokenAnalysis]]:
    """
    Analyze multiple texts efficiently using spaCy's pipe().

    Uses spaCy's batched processing for better throughput on large inputs.
    """
    if nlp is None:
        nlp = get_nlp()

    results: list[list[TokenAnalysis]] = []
    for doc in nlp.pipe(texts, batch_size=64):
        doc_results: list[TokenAnalysis] = []
        for token in doc:
            if token.is_space:
                continue

            surface = token.text
            lemma = token.lemma_.lower()
            primes, inflection_type = _extract_grammatical_primes(token)

            morph_dict: dict[str, str] = {}
            for feat in token.morph:
                key, _, val = feat.partition("=")
                morph_dict[key] = val

            is_inflected = surface.lower() != lemma

            doc_results.append(TokenAnalysis(
                surface=surface,
                lemma=lemma,
                pos=token.pos_,
                morph_features=morph_dict,
                grammatical_primes=primes,
                inflection_type=inflection_type,
                is_inflected=is_inflected,
                is_stop=token.is_stop,
                dep=token.dep_,
                head_idx=token.head.i,
                idx=token.i,
            ))
        results.append(doc_results)

    return results


# ══════════════════════════════════════════════════════════════════════════════
# CLI demo
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_sentences = [
        "The cats were running faster than the dogs",
        "She ran to the biggest store yesterday",
        "He has eaten the broken cookies",
        "The children played happily in the garden",
        "I am thinking about better solutions",
        "They will have been swimming for hours",
        "The mice were caught by the oldest cat",
    ]

    print("PABLO Lemmatizer — spaCy-based morphological analysis")
    print("=" * 70)

    for sent in test_sentences:
        print(f"\n  \"{sent}\"")
        print(f"  {'TOKEN':<14s} {'LEMMA':<12s} {'POS':<6s} {'INFLECTION':<22s} {'PRIMES':<20s} {'FAMILY?'}")
        print(f"  {'─'*14} {'─'*12} {'─'*6} {'─'*22} {'─'*20} {'─'*7}")

        tokens = analyze(sent)
        for t in tokens:
            primes_str = ",".join(sorted(t.grammatical_primes)) if t.grammatical_primes else "—"
            family = "  ✓" if t.is_inflected else ""
            print(f"  {t.surface:<14s} {t.lemma:<12s} {t.pos:<6s} {t.inflection_type:<22s} {primes_str:<20s} {family}")

    # Summary stats
    all_tokens = [t for sent in test_sentences for t in analyze(sent)]
    inflected = [t for t in all_tokens if t.is_inflected]
    with_primes = [t for t in all_tokens if t.grammatical_primes]
    print(f"\n{'=' * 70}")
    print(f"Total tokens:    {len(all_tokens)}")
    print(f"Inflected:       {len(inflected)} (family member candidates)")
    print(f"With gram primes: {len(with_primes)}")
    print(f"Unique POS tags: {sorted(set(t.pos for t in all_tokens))}")
