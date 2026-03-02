"""Tests for core/lemmatizer.py — spaCy-based morphological analysis."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.lemmatizer import (
    analyze, analyze_token, analyze_batch,
    TokenAnalysis, MORPH_TO_PRIMES,
    _extract_grammatical_primes, get_nlp,
)


# ══════════════════════════════════════════════════════════════════════════════
# Prime mapping completeness
# ══════════════════════════════════════════════════════════════════════════════

def test_morph_to_primes_complete():
    """All morph-to-prime entries have valid non-empty prime sets."""
    for morph_type, primes in MORPH_TO_PRIMES.items():
        assert isinstance(primes, set), f"{morph_type} primes not a set"
        assert len(primes) > 0, f"{morph_type} has empty primes"
        for p in primes:
            assert isinstance(p, str), f"{morph_type} has non-string prime: {p}"


def test_documented_prime_mappings():
    """Verify the prime mappings match compound_concept.md documentation."""
    assert MORPH_TO_PRIMES["past"] == {"BEFORE"}
    assert MORPH_TO_PRIMES["past_participle"] == {"BEFORE", "LAST"}
    assert MORPH_TO_PRIMES["present_participle"] == {"NOW"}
    assert MORPH_TO_PRIMES["future"] == {"AFTER"}
    assert MORPH_TO_PRIMES["plural"] == {"MANY"}
    assert MORPH_TO_PRIMES["singular"] == {"ONE"}
    assert MORPH_TO_PRIMES["comparative"] == {"MORE"}
    assert MORPH_TO_PRIMES["superlative"] == {"MORE", "ALL"}
    assert MORPH_TO_PRIMES["first_person"] == {"SELF"}
    assert MORPH_TO_PRIMES["second_person"] == {"YOU"}
    assert MORPH_TO_PRIMES["third_person"] == {"OTHER"}


# ══════════════════════════════════════════════════════════════════════════════
# TokenAnalysis structure
# ══════════════════════════════════════════════════════════════════════════════

def test_token_analysis_fields():
    """TokenAnalysis has all required fields."""
    result = analyze("cats")
    assert len(result) == 1
    t = result[0]
    assert hasattr(t, "surface")
    assert hasattr(t, "lemma")
    assert hasattr(t, "pos")
    assert hasattr(t, "morph_features")
    assert hasattr(t, "grammatical_primes")
    assert hasattr(t, "inflection_type")
    assert hasattr(t, "is_inflected")
    assert hasattr(t, "is_stop")
    assert hasattr(t, "dep")
    assert hasattr(t, "head_idx")
    assert hasattr(t, "idx")


# ══════════════════════════════════════════════════════════════════════════════
# Lemmatization via spaCy
# ══════════════════════════════════════════════════════════════════════════════

def test_past_tense_verb():
    """'ran' → lemma='run', primes include BEFORE."""
    tokens = analyze("She ran home")
    ran = [t for t in tokens if t.surface == "ran"][0]
    assert ran.lemma == "run"
    assert "BEFORE" in ran.grammatical_primes
    assert ran.is_inflected is True


def test_present_participle():
    """'running' → lemma='run', primes include NOW."""
    tokens = analyze("He was running fast")
    running = [t for t in tokens if t.surface == "running"][0]
    assert running.lemma == "run"
    assert "NOW" in running.grammatical_primes
    assert running.is_inflected is True


def test_plural_noun():
    """'cats' → lemma='cat', primes include MANY."""
    tokens = analyze("The cats sat")
    cats = [t for t in tokens if t.surface == "cats"][0]
    assert cats.lemma == "cat"
    assert "MANY" in cats.grammatical_primes
    assert cats.is_inflected is True


def test_comparative_adjective():
    """'bigger' → lemma='big', primes include MORE."""
    tokens = analyze("The bigger dog won")
    bigger = [t for t in tokens if t.surface == "bigger"][0]
    assert bigger.lemma == "big"
    assert "MORE" in bigger.grammatical_primes
    assert bigger.is_inflected is True


def test_superlative_adjective():
    """'biggest' → lemma='big', primes include MORE and ALL."""
    tokens = analyze("The biggest dog won")
    biggest = [t for t in tokens if t.surface == "biggest"][0]
    assert biggest.lemma == "big"
    assert "MORE" in biggest.grammatical_primes
    assert "ALL" in biggest.grammatical_primes


def test_past_participle():
    """'eaten' → lemma='eat', primes include BEFORE and LAST."""
    tokens = analyze("He has eaten lunch")
    eaten = [t for t in tokens if t.surface == "eaten"][0]
    assert eaten.lemma == "eat"
    assert "BEFORE" in eaten.grammatical_primes
    assert "LAST" in eaten.grammatical_primes


def test_irregular_plural():
    """'children' → lemma='child', primes include MANY."""
    tokens = analyze("The children played")
    children = [t for t in tokens if t.surface == "children"][0]
    assert children.lemma == "child"
    assert "MANY" in children.grammatical_primes
    assert children.is_inflected is True


def test_base_form_no_primes():
    """Root forms should have no tense/number grammatical primes."""
    tokens = analyze("I run fast")
    run = [t for t in tokens if t.surface == "run"][0]
    assert run.lemma == "run"
    # Base present tense — no BEFORE, no NOW
    assert "BEFORE" not in run.grammatical_primes
    assert "NOW" not in run.grammatical_primes


def test_pronoun_person():
    """Pronouns get person primes."""
    tokens = analyze("I see")
    i_tok = [t for t in tokens if t.surface == "I"][0]
    assert "SELF" in i_tok.grammatical_primes

    tokens = analyze("She runs")
    she_tok = [t for t in tokens if t.surface == "She"][0]
    assert "OTHER" in she_tok.grammatical_primes


# ══════════════════════════════════════════════════════════════════════════════
# Convenience functions
# ══════════════════════════════════════════════════════════════════════════════

def test_analyze_token_single_word():
    """analyze_token works for a single word."""
    t = analyze_token("running")
    assert t is not None
    assert t.lemma == "run"


def test_analyze_batch():
    """analyze_batch processes multiple texts efficiently."""
    texts = ["The cats ran", "She is thinking"]
    results = analyze_batch(texts)
    assert len(results) == 2
    assert any(t.lemma == "cat" for t in results[0])
    assert any(t.lemma == "think" for t in results[1])


# ══════════════════════════════════════════════════════════════════════════════
# POS tagging
# ══════════════════════════════════════════════════════════════════════════════

def test_pos_tags_present():
    """All tokens get POS tags from spaCy."""
    tokens = analyze("The cat sat on the mat")
    pos_tags = {t.pos for t in tokens}
    assert "NOUN" in pos_tags
    assert "DET" in pos_tags
    assert "VERB" in pos_tags


def test_dependency_info():
    """Tokens include dependency parse info for LLM input."""
    tokens = analyze("The cat sat")
    for t in tokens:
        assert isinstance(t.dep, str) and len(t.dep) > 0
        assert isinstance(t.head_idx, int)


# ══════════════════════════════════════════════════════════════════════════════
# Model singleton
# ══════════════════════════════════════════════════════════════════════════════

def test_model_singleton():
    """get_nlp returns the same model instance."""
    nlp1 = get_nlp()
    nlp2 = get_nlp()
    assert nlp1 is nlp2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
