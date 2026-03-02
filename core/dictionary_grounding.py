"""
dictionary_grounding.py — Recursive Dictionary Grounding for PABLO

Builds a grounding index from data/out/ dictionary entries.

Strategy: direct-prime extraction + recursive confidence growth.

Phase 1 — Direct prime extraction:
   For each sense of each word, tokenise the definition TEXT.
   Only primes that literally appear in the definition contribute to the primebit.
   "consume" → "to use up" → primes {TO, USE, UP} → primebit = bits(55,58,57).
   No cascading union.  The primebit stays sparse and meaningful.

Phase 2 — Recursive confidence growth (lapping):
   In each lap, non-prime tokens that have been grounded in a previous lap
   increase the *confidence* of the current word (we understand more of its
   definition) and are recorded as nested compound references (structural
   linking).  But the PRIMEBIT DOES NOT cascade — it always reflects only
   the direct prime words in the definition text.

Phase 3 — Multi-sense:
   Each POS × sense produces a separate grounding entry.  "bank" as NOUN
   with sense "financial institution" grounds differently from "bank" as
   NOUN with sense "river bank".  SYMBOL returns all sense candidates.

Output: an in-memory index  word → [SenseGrounding, ...]  for SYMBOL lookup.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.primebit import PRIME_INDEX, PRIME_TO_BIT


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

_PRIME_SET_LOWER: Set[str] = {p.lower() for p in PRIME_INDEX}
_LOWER_TO_PRIME: Dict[str, str] = {p.lower(): p for p in PRIME_INDEX}

# Stop words that appear in definitions but carry no semantic weight.
# We exclude them from "unresolved" counts so confidence reflects real
# semantic coverage rather than articles/prepositions.
_STOP_WORDS: Set[str] = {
    "a", "an", "the", "or", "and", "is", "are", "was", "were",
    "not", "no", "of", "for", "that", "which", "who", "whom",
    "its", "it", "they", "them", "their", "he", "she", "his",
    "her", "has", "had", "been", "being", "by", "as", "etc",
    "very", "also", "when", "where", "how", "what", "than",
    "into", "on", "about", "used", "especially", "usually",
}


# ══════════════════════════════════════════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SenseGrounding:
    """Grounding for one POS × sense of a headword."""
    headword:       str
    pos:            str             # e.g. "ADJECTIVE", "VERB", "NOUN"
    sense_key:      str             # e.g. "of a high standard", "skilful"
    definition:     str             # raw TEXT from the dictionary
    primebit:       int     = 0     # direct-prime-only bits
    prime_names:    list    = field(default_factory=list)   # which primes
    nested_ids:     list    = field(default_factory=list)   # compound IDs from grounded def tokens
    confidence:     float   = 0.0   # resolved_tokens / semantic_tokens
    total_tokens:   int     = 0
    resolved_tokens: int    = 0
    compound_id:    Optional[int] = None  # assigned later when written to storage

    def score_key(self) -> float:
        """Sorting key — prefer more primes AND higher confidence."""
        return len(self.prime_names) + self.confidence


@dataclass
class WordGrounding:
    """All sense groundings for a headword."""
    headword: str
    senses:   List[SenseGrounding] = field(default_factory=list)

    @property
    def best(self) -> Optional[SenseGrounding]:
        """Return the highest-scoring sense."""
        if not self.senses:
            return None
        return max(self.senses, key=lambda s: s.score_key())


# ══════════════════════════════════════════════════════════════════════════════
# Tokeniser
# ══════════════════════════════════════════════════════════════════════════════

_TOKEN_RE = re.compile(r"[\w''\-]+")

def tokenise(text: str) -> List[str]:
    """Split definition text into lowercase word tokens."""
    return _TOKEN_RE.findall(text.lower())


# ══════════════════════════════════════════════════════════════════════════════
# Dictionary loader
# ══════════════════════════════════════════════════════════════════════════════

def _load_entry(folder_path: Path) -> Optional[Dict[str, Any]]:
    """Load the _v4.json entry from a dictionary folder."""
    folder_name = folder_path.name
    candidate = folder_path / f"{folder_name}_v4.json"
    if not candidate.exists():
        matches = list(folder_path.glob("*_v4.json"))
        if not matches:
            return None
        candidate = matches[0]
    try:
        with open(candidate, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _extract_senses(entry: Dict[str, Any]) -> List[dict]:
    """
    Extract all (pos, sense_key, definition_text) triples from an entry.

    Returns list of dicts with keys: pos, sense_key, texts
    Each dict may have multiple texts (main def + subdefinitions).
    """
    results = []
    headword = entry.get("HEADWORD", "")
    for pos_name, pos_data in entry.get("POS", {}).items():
        for sense_key, sense_data in pos_data.get("SENSE", {}).items():
            texts = []
            for defn in sense_data.get("DEFINITIONS", []):
                if defn.get("TEXT"):
                    texts.append(defn["TEXT"])
                # Include subdefinitions — they often have more precise wording
                for sub in defn.get("SUBDEFINITIONS", []):
                    if sub.get("TEXT"):
                        texts.append(sub["TEXT"])
            if texts:
                results.append({
                    "pos":       pos_name,
                    "sense_key": sense_key,
                    "texts":     texts,
                })
    return results


# ══════════════════════════════════════════════════════════════════════════════
# Core: direct prime extraction + confidence computation
# ══════════════════════════════════════════════════════════════════════════════

def _ground_sense(
    texts: List[str],
    grounded_words: Dict[str, int],  # word → compound_id (for nested refs)
) -> dict:
    """
    Ground a single sense's definition texts.

    primebit: only primes that literally appear in the definition.
    confidence: (prime_tokens + grounded_tokens) / semantic_tokens
    nested_ids: compound IDs of grounded non-prime words in the definition.

    'semantic_tokens' excludes stop words for a fairer confidence measure.
    """
    prime_bits: List[int] = []
    prime_names: List[str] = []
    prime_set: Set[str] = set()
    nested_ids: List[int] = []
    nested_set: Set[int] = set()

    total_tokens    = 0
    semantic_tokens = 0
    resolved        = 0

    for text in texts:
        tokens = tokenise(text)
        total_tokens += len(tokens)
        for tok in tokens:
            if tok in _STOP_WORDS:
                continue  # skip stop words entirely for confidence calc
            semantic_tokens += 1

            if tok in _PRIME_SET_LOWER:
                # Direct prime match → contributes to primebit
                prime = _LOWER_TO_PRIME[tok]
                if prime not in prime_set:
                    prime_set.add(prime)
                    prime_names.append(prime)
                    prime_bits.append(1 << PRIME_TO_BIT[prime])
                resolved += 1
            elif tok in grounded_words:
                # Non-prime grounded word → nested ref, NO primebit cascade
                cid = grounded_words[tok]
                if cid not in nested_set:
                    nested_ids.append(cid)
                    nested_set.add(cid)
                resolved += 1

    primebit = 0
    for b in prime_bits:
        primebit |= b

    confidence = round(resolved / semantic_tokens, 4) if semantic_tokens > 0 else 0.0

    return {
        "primebit":         primebit,
        "prime_names":      prime_names,
        "nested_ids":       nested_ids,
        "confidence":       confidence,
        "total_tokens":     total_tokens,
        "semantic_tokens":  semantic_tokens,
        "resolved_tokens":  resolved,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Recursive lapping engine
# ══════════════════════════════════════════════════════════════════════════════

class DictionaryGrounder:
    """
    Builds and maintains an in-memory grounding index from data/out/.

    Usage:
        grounder = DictionaryGrounder("data/out/")
        grounder.build()          # runs laps, populates index
        results = grounder.lookup("consume")  # → [SenseGrounding, ...]
    """

    def __init__(self, dict_dir: str, max_laps: int = 10):
        self.dict_dir = Path(dict_dir)
        self.max_laps = max_laps

        # Main index: lowercase headword → WordGrounding
        self.index: Dict[str, WordGrounding] = {}

        # Flat lookup of all grounded words → best compound_id (for nested refs)
        self._grounded_words: Dict[str, int] = {}

        # Internal ID counter for compound references
        self._next_id = 1000  # offset from logic_compounds range

        # Stats
        self.stats = {
            "total_entries":  0,
            "total_senses":   0,
            "grounded_words": 0,
            "laps_run":       0,
            "build_time_s":   0.0,
        }

    def build(self, progress_callback=None) -> None:
        """
        Run the full recursive grounding pipeline.

        1. Scan all folders, extract per-sense definition texts.
        2. Lap 1: direct prime extraction (no grounded_words available yet).
        3. Laps 2-N: re-resolve with expanding grounded_words set.
        4. Populate self.index with final WordGrounding objects.
        """
        t0 = time.time()

        # ── Step 1: Load all entries ──────────────────────────────────────
        raw_entries: Dict[str, List[dict]] = {}  # key → [{pos, sense_key, texts}, ...]
        headwords: Dict[str, str] = {}           # key → original headword

        folders = [f for f in self.dict_dir.iterdir() if f.is_dir()]
        self.stats["total_entries"] = len(folders)

        for i, folder in enumerate(folders):
            entry = _load_entry(folder)
            if not entry:
                continue
            hw = entry.get("HEADWORD", "").strip()
            if not hw:
                continue
            key = hw.lower()
            senses = _extract_senses(entry)
            if senses:
                raw_entries[key] = senses
                headwords[key] = hw

            if progress_callback and i % 2000 == 0:
                progress_callback(f"Loading: {i}/{len(folders)}")

        # ── Step 2: Seed grounded_words with primes ──────────────────────
        # Primes don't need compound IDs for nested refs — they ARE the atoms
        # They'll match via prime_set_lower in _ground_sense

        # ── Step 3: Lapping ──────────────────────────────────────────────
        # sense_results[key][sense_idx] = ground result dict
        sense_results: Dict[str, List[dict]] = {}

        for lap in range(1, self.max_laps + 1):
            new_grounded = 0
            updates = 0

            for key, senses in raw_entries.items():
                if key not in sense_results:
                    sense_results[key] = [None] * len(senses)

                for si, sense in enumerate(senses):
                    result = _ground_sense(sense["texts"], self._grounded_words)

                    prev = sense_results[key][si]
                    if prev is None:
                        sense_results[key][si] = result
                        if result["primebit"] > 0:
                            new_grounded += 1
                    elif (result["resolved_tokens"] > prev["resolved_tokens"]
                          or result["confidence"] > prev["confidence"]):
                        sense_results[key][si] = result
                        updates += 1

                # After processing all senses for this word, register it
                # as grounded if any sense has primes
                if key not in self._grounded_words:
                    best_result = None
                    for r in sense_results[key]:
                        if r and r["primebit"] > 0:
                            if best_result is None or r["confidence"] > best_result["confidence"]:
                                best_result = r
                    if best_result:
                        cid = self._next_id
                        self._next_id += 1
                        self._grounded_words[key] = cid

            self.stats["laps_run"] = lap

            if progress_callback:
                progress_callback(
                    f"Lap {lap}: new={new_grounded}, updates={updates}, "
                    f"grounded={len(self._grounded_words)}"
                )

            if new_grounded == 0 and updates == 0:
                break  # converged

        # ── Step 4: Build final index ─────────────────────────────────────
        for key, senses in raw_entries.items():
            hw = headwords[key]
            results = sense_results.get(key, [])
            wg = WordGrounding(headword=hw)

            for si, sense in enumerate(senses):
                r = results[si] if si < len(results) and results[si] else None
                if r is None or r["primebit"] == 0:
                    continue  # skip senses with no prime grounding

                sg = SenseGrounding(
                    headword=hw,
                    pos=sense["pos"],
                    sense_key=sense["sense_key"],
                    definition="; ".join(sense["texts"]),
                    primebit=r["primebit"],
                    prime_names=r["prime_names"],
                    nested_ids=r["nested_ids"],
                    confidence=r["confidence"],
                    total_tokens=r["total_tokens"],
                    resolved_tokens=r["resolved_tokens"],
                    compound_id=self._grounded_words.get(key),
                )
                wg.senses.append(sg)

            if wg.senses:
                self.index[key] = wg
                self.stats["total_senses"] += len(wg.senses)

        self.stats["grounded_words"] = len(self.index)
        self.stats["build_time_s"] = round(time.time() - t0, 2)

    def lookup(self, word: str) -> Optional[WordGrounding]:
        """Look up all sense groundings for a word."""
        return self.index.get(word.lower())

    def lookup_best(self, word: str) -> Optional[SenseGrounding]:
        """Return the highest-scoring sense grounding for a word."""
        wg = self.index.get(word.lower())
        return wg.best if wg else None

    def save_index(self, path: str) -> None:
        """Persist the grounding index as JSON for fast reload."""
        data = {}
        for key, wg in self.index.items():
            data[key] = {
                "headword": wg.headword,
                "senses": [
                    {
                        "pos":              s.pos,
                        "sense_key":        s.sense_key,
                        "definition":       s.definition,
                        "primebit":         s.primebit,
                        "prime_names":      s.prime_names,
                        "nested_ids":       s.nested_ids,
                        "confidence":       s.confidence,
                        "total_tokens":     s.total_tokens,
                        "resolved_tokens":  s.resolved_tokens,
                        "compound_id":      s.compound_id,
                    }
                    for s in wg.senses
                ],
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"DictionaryGrounder: saved {len(data)} entries to {path}")

    def load_index(self, path: str) -> bool:
        """Load a previously saved grounding index. Returns True on success."""
        p = Path(path)
        if not p.exists():
            return False
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False

        self.index.clear()
        self._grounded_words.clear()

        for key, wd in data.items():
            wg = WordGrounding(headword=wd["headword"])
            for sd in wd["senses"]:
                sg = SenseGrounding(
                    headword=wd["headword"],
                    pos=sd["pos"],
                    sense_key=sd["sense_key"],
                    definition=sd["definition"],
                    primebit=sd["primebit"],
                    prime_names=sd["prime_names"],
                    nested_ids=sd["nested_ids"],
                    confidence=sd["confidence"],
                    total_tokens=sd["total_tokens"],
                    resolved_tokens=sd["resolved_tokens"],
                    compound_id=sd.get("compound_id"),
                )
                wg.senses.append(sg)
            self.index[key] = wg
            if wg.best and wg.best.compound_id:
                self._grounded_words[key] = wg.best.compound_id

        self.stats["grounded_words"] = len(self.index)
        self.stats["total_senses"] = sum(len(wg.senses) for wg in self.index.values())
        return True


# ══════════════════════════════════════════════════════════════════════════════
# Convenience: build + save from CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    dict_dir = r"G:\AI\PABLO V0002\data\out"
    out_path = r"G:\AI\PABLO V0002\storage\grounding_index.json"

    if len(sys.argv) > 1:
        dict_dir = sys.argv[1]
    if len(sys.argv) > 2:
        out_path = sys.argv[2]

    grounder = DictionaryGrounder(dict_dir)
    grounder.build(progress_callback=print)

    print(f"\nStats: {grounder.stats}")

    # Show some sample groundings
    for word in ["good", "bad", "consume", "big", "want", "think", "happy",
                 "run", "water", "house", "love", "angry", "fast", "help"]:
        wg = grounder.lookup(word)
        if wg:
            best = wg.best
            print(f"  {word:12s} → {best.prime_names}  "
                  f"primebit={best.primebit}  conf={best.confidence:.3f}  "
                  f"senses={len(wg.senses)}")
        else:
            print(f"  {word:12s} → NOT FOUND")

    grounder.save_index(out_path)
    print(f"\nDone. Grounded {grounder.stats['grounded_words']} words "
          f"with {grounder.stats['total_senses']} senses "
          f"in {grounder.stats['build_time_s']}s.")
