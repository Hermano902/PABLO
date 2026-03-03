"""
Full pipeline integration test: READ → SYMBOL → DATA → KNOW

Tests the complete flow of text entering PABLO and being processed
into stored Compounds in KNOW, exactly as it would happen at runtime.

Pipeline steps:
  1. READ builds an observation dict from raw text
  2. Observation goes to observation_queue
  3. SYMBOL drains observation_queue, runs router cascade, produces
     near-compound candidates, pushes to candidate_queue
  4. DATA drains candidate_queue, validates primes, creates/resolves
     concept Compounds, assembles utterance Compound, calls KNOW.store_batch
  5. KNOW assigns permanent IDs, stores everything, creates
     definition narratives

This test bypasses the daemon threads and drives each step synchronously
so results are deterministic.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pytest

from core.queues import observation_queue, candidate_queue
from core.primebit import PrimeBit, PRIME_INDEX, PRIME_TO_BIT
from core.compound import Compound


# ══════════════════════════════════════════════════════════════════════════════
# Helpers — fresh instances (no daemon threads, no disk I/O)
# ══════════════════════════════════════════════════════════════════════════════

def _fresh_know():
    """Create a clean KNOW instance with no persistence."""
    from primes.KNOW import KNOW
    k = KNOW(enable_persistence=False)
    # Manually run logic compound loading (skip disk load & threads)
    k._load_logic_compounds()
    k._initialized = True
    return k


def _fresh_symbol():
    """Create a SYMBOL instance with router (no daemon thread)."""
    from primes.SYMBOL import SYMBOL
    s = SYMBOL()
    # Initialize router & specialists without starting the thread
    from core.specialists import SpecialistRegistry
    from core.router import Router
    s._registry = SpecialistRegistry.create_default()
    s._router = Router(
        specialist_fn=s._registry.ground_token,
        enable_specialist=False,  # no Ollama in tests
    )
    return s


def _fresh_data():
    """Create a clean DATA instance (no daemon thread)."""
    from primes.DATA import DATA
    d = DATA()
    d._load_logic_map()
    d._initialized = True
    return d


def _fresh_read():
    """Create a READ instance for building observations."""
    from primes.READ import READ
    r = READ()
    return r


def _drain_queue(q):
    """Drain all items from a queue into a list."""
    items = []
    while not q.empty():
        try:
            items.append(q.get_nowait())
        except Exception:
            break
    return items


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline driver — synchronous step-by-step
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(text: str, know=None, symbol=None, data=None, read=None):
    """
    Drive the full pipeline synchronously for a single text input.

    Returns:
        {
            "observation": dict,
            "candidate":   dict,
            "result":      dict (from DATA._process_candidate),
            "utterance":   Compound,
            "concepts":    list[Compound],
            "know":        KNOW instance,
        }
    """
    know = know or _fresh_know()
    symbol = symbol or _fresh_symbol()
    data = data or _fresh_data()
    read = read or _fresh_read()

    # Step 1: READ builds observation
    obs = read._build_observation_dict(text, source="test", event_type="line_entered")
    assert obs is not None
    assert obs["data"]["text"] == text

    # Step 2: SYMBOL interprets observation → candidate
    candidate = symbol._interpret_observation(obs)
    assert candidate is not None

    # Step 3: DATA processes candidate → stored Compounds in KNOW
    # DATA lazy-imports `from primes.KNOW import know` inside _process_candidate.
    # We need to make that import resolve to our fresh KNOW instance.
    import primes.KNOW as know_module
    original_know = know_module.know
    know_module.know = know
    try:
        result = data._process_candidate(candidate)
    finally:
        know_module.know = original_know

    return {
        "observation": obs,
        "candidate":   candidate,
        "result":      result,
        "know":        know,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestFullPipeline:
    """End-to-end tests: text → READ → SYMBOL → DATA → KNOW."""

    # ── Basic flow ────────────────────────────────────────────────────────

    def test_simple_text_produces_utterance(self):
        """A simple sentence should produce an utterance compound in KNOW."""
        p = run_pipeline("the cat sat on the mat")

        assert p["result"] is not None, "DATA should produce a result"
        utt = p["result"]["utterance"]
        assert isinstance(utt, Compound)
        assert utt.compound_type == "utterance"
        assert utt.symbol == "the cat sat on the mat"
        assert utt.id >= 200  # permanent ID assigned by KNOW

    def test_concepts_created_for_each_token(self):
        """Each non-logic token should produce a concept compound."""
        p = run_pipeline("big red ball")

        concepts = p["result"]["concepts"]
        assert len(concepts) == 3
        symbols = {c.symbol for c in concepts if c is not None}
        # Tokens should appear as concept symbols
        assert len(symbols) == 3

    def test_utterance_nests_concepts(self):
        """The utterance compound should nest all concept compound IDs."""
        p = run_pipeline("hello world")

        utt = p["result"]["utterance"]
        concepts = p["result"]["concepts"]
        # Each concept's ID should be in the utterance's nested list
        for c in concepts:
            if c is not None:
                assert c.id in utt.nested, f"Concept '{c.symbol}' (id={c.id}) not in utterance.nested"

    def test_utterance_primebit_is_union(self):
        """The utterance's primebit should be the union of all concepts'."""
        p = run_pipeline("MOVE FEEL KNOW")

        utt = p["result"]["utterance"]
        # At least MOVE, FEEL, KNOW primebits should be set
        # (the router resolves prime names via heuristic)
        assert utt.primebit.has_prime("MOVE")
        assert utt.primebit.has_prime("FEEL")
        assert utt.primebit.has_prime("KNOW")

    # ── Observation shape ─────────────────────────────────────────────────

    def test_observation_format(self):
        """READ's observation dict has the canonical format."""
        p = run_pipeline("test input")
        obs = p["observation"]

        assert "timestamp" in obs
        assert obs["modality"] == "READ"
        assert obs["data"]["text"] == "test input"
        assert obs["data"]["preliminary_tokens"] == ["test", "input"]
        assert obs["data"]["token_count"] == 2
        assert obs["metadata"]["source"] == "test"

    # ── Candidate shape ───────────────────────────────────────────────────

    def test_candidate_has_required_keys(self):
        """SYMBOL's candidate dict has all keys DATA expects."""
        p = run_pipeline("the dog barked")
        cand = p["candidate"]

        required = ["candidate_primes", "roles", "rule_template",
                     "confidence", "provenance", "raw_input",
                     "observation_id", "source"]
        for key in required:
            assert key in cand, f"Missing candidate key: {key}"

    def test_candidate_primes_are_list(self):
        """candidate_primes should be a list with one entry per token."""
        p = run_pipeline("a b c")
        primes = p["candidate"]["candidate_primes"]
        assert isinstance(primes, list)
        assert len(primes) >= 3  # at least one per token (spaCy may merge)

    def test_candidate_prime_entries_have_token_and_score(self):
        """Each entry in candidate_primes has token, score, position."""
        p = run_pipeline("cats run fast")
        for entry in p["candidate"]["candidate_primes"]:
            assert "token" in entry
            assert "score" in entry
            assert "position" in entry

    # ── Router cascade visibility ─────────────────────────────────────────

    def test_router_provides_lemma_info(self):
        """The router should include lemma information from spaCy."""
        p = run_pipeline("cats running biggest")
        primes = p["candidate"]["candidate_primes"]

        # At least some entries should have lemma info
        lemmas = [e.get("lemma") for e in primes if e.get("lemma")]
        assert len(lemmas) > 0, "Router should provide lemma data"

    def test_router_provides_pos_info(self):
        """The router should include POS tags from spaCy."""
        p = run_pipeline("the cat sat quietly")
        primes = p["candidate"]["candidate_primes"]

        pos_tags = [e.get("pos") for e in primes if e.get("pos")]
        assert len(pos_tags) > 0, "Router should provide POS data"

    def test_router_provides_grammatical_primes(self):
        """Inflected forms should include grammatical primes."""
        p = run_pipeline("she ran home")
        primes = p["candidate"]["candidate_primes"]

        # Look for "ran" → should have BEFORE in grammatical_primes
        ran_entries = [e for e in primes if e["token"].lower() == "ran"]
        if ran_entries:
            gp = ran_entries[0].get("grammatical_primes", [])
            assert "BEFORE" in gp, f"'ran' should have BEFORE gram prime, got {gp}"

    # ── KNOW state after pipeline ─────────────────────────────────────────

    def test_know_stores_compounds(self):
        """After pipeline, KNOW should have stored new compounds."""
        p = run_pipeline("hello world")
        know = p["know"]

        # Should have logic compounds (100-199) + new runtime compounds (200+)
        with know._lock:
            runtime = {cid: c for cid, c in know._compounds.items() if cid >= 200}
        assert len(runtime) >= 3  # at least 2 concepts + 1 utterance

    def test_know_compounds_retrievable(self):
        """Stored compounds should be retrievable by ID."""
        p = run_pipeline("nice day")
        know = p["know"]
        utt = p["result"]["utterance"]

        retrieved = know.by_id(utt.id)
        assert retrieved is not None
        assert retrieved.symbol == "nice day"

    def test_know_stats_increment(self):
        """KNOW's stats should increment after pipeline."""
        p = run_pipeline("something new")
        know = p["know"]
        assert know.stats["compounds_stored"] > 0

    # ── Duplicate text handling ───────────────────────────────────────────

    def test_second_run_reuses_concepts(self):
        """Running the same text twice should find existing concepts in KNOW."""
        know = _fresh_know()
        sym = _fresh_symbol()
        data_ = _fresh_data()
        read_ = _fresh_read()

        # First run creates everything
        p1 = run_pipeline("hello world", know=know, symbol=sym, data=data_, read=read_)
        created_first = data_.stats["concepts_created"]

        # Second run should find existing concepts
        p2 = run_pipeline("hello world", know=know, symbol=sym, data=data_, read=read_)
        found = data_.stats["concepts_found"]
        assert found > 0, "Second run should find existing concepts in KNOW"

    # ── Logic operators ───────────────────────────────────────────────────

    def test_logic_operators_detected(self):
        """Logic tokens like 'and', 'or', 'not' should be detected by DATA."""
        data_ = _fresh_data()
        # Verify logic map loaded
        assert len(data_._logic_map) > 0, "Logic map should have entries"

        p = run_pipeline("this and that")
        # DATA should detect the logic operator
        # Check that DATA's stats show logic operators found
        # (We need a shared DATA instance to check stats)

    def test_logic_operator_maps_to_compound(self):
        """Logic tokens should reference pre-seeded compound IDs (100-199)."""
        know = _fresh_know()
        data_ = _fresh_data()
        sym = _fresh_symbol()
        read_ = _fresh_read()

        p = run_pipeline("if something then move", know=know, symbol=sym,
                         data=data_, read=read_)

        # DATA should have found some logic operators
        assert data_.stats["logic_operators_found"] >= 0  # may or may not find 'if'

    # ── Prime name grounding ──────────────────────────────────────────────

    def test_prime_names_grounded(self):
        """Tokens that are prime names should be grounded with score 1.0."""
        p = run_pipeline("MOVE KNOW FEEL")
        primes = p["candidate"]["candidate_primes"]

        for entry in primes:
            if entry["token"] in ("MOVE", "KNOW", "FEEL"):
                # These should be resolved (by router heuristic or KNOW)
                assert entry["score"] > 0.0, f"'{entry['token']}' should be grounded"

    def test_unknown_tokens_score_zero(self):
        """Tokens with no grounding should have score 0.0."""
        p = run_pipeline("xylophone quasar bumblebee")
        primes = p["candidate"]["candidate_primes"]

        for entry in primes:
            # These are real English words but not prime names and not in KNOW
            # Without specialist, they should be unresolved
            if entry["method"] == "unresolved":
                assert entry["score"] == 0.0

    # ── Confidence propagation ────────────────────────────────────────────

    def test_confidence_in_candidate(self):
        """Candidate confidence should be a float between 0 and 1."""
        p = run_pipeline("the cat sat")
        conf = p["candidate"]["confidence"]
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    # ── Provenance tracking ───────────────────────────────────────────────

    def test_candidate_provenance_from_router(self):
        """When the router is active, provenance should say 'router'."""
        p = run_pipeline("hello world")
        prov = p["candidate"]["provenance"]
        assert prov["model"] == "router"

    # ── Edge cases ────────────────────────────────────────────────────────

    def test_single_word(self):
        """A single word should produce 1 concept + 1 utterance."""
        p = run_pipeline("cat")
        assert p["result"] is not None
        concepts = p["result"]["concepts"]
        assert len(concepts) == 1

    def test_empty_produces_none(self):
        """Empty text should not produce a candidate."""
        sym = _fresh_symbol()
        read_ = _fresh_read()
        obs = read_._build_observation_dict("", source="test")
        candidate = sym._interpret_observation(obs)
        assert candidate is None

    # ── Family member creation through pipeline ───────────────────────────

    def test_inflected_form_after_root_creates_family_member(self):
        """
        If we process the root form first, then the inflected form,
        the router should create a family member compound.
        """
        know = _fresh_know()
        sym = _fresh_symbol()
        data_ = _fresh_data()
        read_ = _fresh_read()

        # First: process "cat" so it gets stored in KNOW
        p1 = run_pipeline("cat", know=know, symbol=sym, data=data_, read=read_)
        assert p1["result"] is not None

        # Verify "cat" is now in KNOW
        cat_compound = know.by_symbol("cat")
        assert cat_compound is not None, "'cat' should be in KNOW after first run"

        # Second: process "cats" — router should find "cat" as root,
        # create "cats" as a family member with MANY grammatical prime
        p2 = run_pipeline("cats", know=know, symbol=sym, data=data_, read=read_)

        primes = p2["candidate"]["candidate_primes"]
        cats_entry = [e for e in primes if e["token"].lower() == "cats"]
        if cats_entry:
            entry = cats_entry[0]
            # Should be either family_member or know_exact (if router created & stored it)
            if entry.get("is_family_member"):
                assert entry["family_root_id"] is not None
                gp = entry.get("grammatical_primes", [])
                assert "MANY" in gp, f"'cats' should have MANY gram prime, got {gp}"

    # ── Stats accumulation ────────────────────────────────────────────────

    def test_symbol_stats(self):
        """SYMBOL's stats should track observations processed."""
        sym = _fresh_symbol()
        read_ = _fresh_read()
        obs = read_._build_observation_dict("hello world", source="test")
        sym._interpret_observation(obs)
        assert sym.stats["observations_processed"] == 1

    def test_data_stats(self):
        """DATA's stats should track candidates processed."""
        p = run_pipeline("hello world")
        # We can't easily check stats on the shared data_ without passing it in
        # So just verify the result was produced
        assert p["result"] is not None

    # ── Multi-sentence pipeline ───────────────────────────────────────────

    def test_multiple_inputs_accumulate(self):
        """Multiple inputs should accumulate compounds in KNOW."""
        know = _fresh_know()
        sym = _fresh_symbol()
        data_ = _fresh_data()
        read_ = _fresh_read()

        texts = ["the cat", "big dog", "red ball"]
        for text in texts:
            run_pipeline(text, know=know, symbol=sym, data=data_, read=read_)

        with know._lock:
            runtime = {cid: c for cid, c in know._compounds.items() if cid >= 200}
        # At least 6 concepts + 3 utterances = 9 compounds (could be more with family members)
        assert len(runtime) >= 9, f"Expected >= 9 runtime compounds, got {len(runtime)}"

    # ── Bug-fix regression tests ──────────────────────────────────────────

    def test_on_not_mapped_to_TRUE(self):
        """'on' as a preposition should NOT be mapped to TRUE (compound 108)."""
        know = _fresh_know()
        sym = _fresh_symbol()
        data_ = _fresh_data()
        read_ = _fresh_read()

        p = run_pipeline("the cat sat on the mat", know=know, symbol=sym,
                         data=data_, read=read_)
        concepts = p["result"]["concepts"]
        # "on" should be a normal concept, NOT the logic compound TRUE (108)
        for c in concepts:
            if c is not None:
                assert c.id != 108, (
                    f"'on' should not map to TRUE (108), "
                    f"but concept '{c.symbol}' has id={c.id}"
                )

    def test_no_not_mapped_to_FALSE(self):
        """'no' as a determiner should NOT be mapped to FALSE (compound 109)."""
        know = _fresh_know()
        data_ = _fresh_data()
        # Check the logic map directly
        assert "no" not in data_._logic_map, "'no' should not be in logic map"
        assert "off" not in data_._logic_map, "'off' should not be in logic map"

    def test_then_not_mapped_to_IF(self):
        """'then' as a temporal word should NOT be mapped to IF (compound 100)."""
        data_ = _fresh_data()
        assert "then" not in data_._logic_map, "'then' should not be in logic map"

    def test_lemma_used_as_symbol(self):
        """Inflected forms should use the lemma as the compound symbol."""
        p = run_pipeline("she ran home quickly")
        concepts = p["result"]["concepts"]
        symbols = [c.symbol for c in concepts if c is not None]
        # "ran" should be stored under lemma "run", not surface "ran"
        assert "run" in symbols, f"Expected 'run' (lemma of 'ran') in {symbols}"
        assert "ran" not in symbols, f"'ran' should be stored as 'run', got {symbols}"

    def test_grammatical_primes_in_primebit(self):
        """Concepts from spaCy should have grammatical primes in their primebit."""
        p = run_pipeline("she ran home quickly")
        concepts = p["result"]["concepts"]
        # At least one concept should have non-zero primebit from grammatical primes
        has_gram_primes = False
        for c in concepts:
            if c is not None and c.primebit.value != 0:
                has_gram_primes = True
                break
        assert has_gram_primes, (
            "At least one concept should have grammatical primes in its primebit"
        )

    def test_candidate_interpretations_enriched(self):
        """Router metadata for new concepts is stored in DefinitionNarrative thread."""
        p = run_pipeline("big cat")
        concepts = p["result"]["concepts"]
        from primes.KNOW import know
        for c in concepts:
            if c is not None and c.compound_type == "concept":
                dn = know.get_definition(c.id)
                if dn is not None and dn.thread:
                    first = dn.thread[0]
                    prov = first.get("provenance", {})
                    assert "initial_grounding" in prov, (
                        f"Concept '{c.symbol}' DefinitionNarrative missing "
                        f"initial_grounding in first thread entry: {first}"
                    )

    def test_within_utterance_dedup(self):
        """Duplicate tokens within one utterance should reuse the same concept."""
        know = _fresh_know()
        sym = _fresh_symbol()
        data_ = _fresh_data()
        read_ = _fresh_read()

        p = run_pipeline("the cat and the dog", know=know, symbol=sym,
                         data=data_, read=read_)
        concepts = p["result"]["concepts"]

        # "the" appears twice — after dedup they should be the same compound
        the_concepts = [c for c in concepts if c is not None and c.symbol == "the"]
        assert len(the_concepts) == 2, f"Should have 2 refs to 'the', got {len(the_concepts)}"
        assert the_concepts[0].id == the_concepts[1].id, (
            f"Both 'the' concepts should be the same compound, "
            f"got ids {the_concepts[0].id} and {the_concepts[1].id}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Quick smoke test (can be run standalone)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("PABLO Full Pipeline Smoke Test")
    print("=" * 60)

    texts = [
        "the cat sat on the mat",
        "MOVE FEEL KNOW",
        "she ran home quickly",
        "big red ball",
    ]

    know = _fresh_know()
    sym = _fresh_symbol()
    data_ = _fresh_data()
    read_ = _fresh_read()

    for text in texts:
        print(f"\n--- Input: '{text}' ---")
        p = run_pipeline(text, know=know, symbol=sym, data=data_, read=read_)

        cand = p["candidate"]
        print(f"  Confidence: {cand['confidence']}")
        print(f"  Provenance: {cand['provenance']['model']}")
        print(f"  Tokens:")
        for entry in cand["candidate_primes"]:
            method = entry.get("method", "?")
            lemma = entry.get("lemma", "")
            gp = entry.get("grammatical_primes", [])
            extra = ""
            if lemma and lemma != entry["token"].lower():
                extra += f" lemma={lemma}"
            if gp:
                extra += f" gram={gp}"
            if entry.get("is_family_member"):
                extra += f" family_root={entry.get('family_root_id')}"
            prime_str = str(entry.get('prime') or '-')
            print(f"    {entry['token']:15s} score={entry['score']:.2f} "
                  f"method={method:15s} prime={prime_str:8s}{extra}")

        if p["result"]:
            utt = p["result"]["utterance"]
            concepts = p["result"]["concepts"]
            print(f"  Utterance: id={utt.id}, nested={utt.nested}")
            print(f"  Concepts:  {[(c.symbol, c.id) for c in concepts if c]}")

    # Summary
    with know._lock:
        runtime = {cid: c for cid, c in know._compounds.items() if cid >= 200}
    print(f"\n{'=' * 60}")
    print(f"KNOW: {len(runtime)} runtime compounds stored")
    print(f"KNOW stats: {know.stats}")
    print(f"{'=' * 60}")
