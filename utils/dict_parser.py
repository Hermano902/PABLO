"""
dict_parser.py — Recursive Lapping Dictionary Parser for PABLO

Model: reverse pyramid / nested compounds with multi-sense support.

Each headword may have multiple senses (POS x SENSE from dictionary entries).
Each sense becomes a SEPARATE Compound with:
  - its own primebit (ONLY primes that literally appear as tokens — no inheritance)
  - its own nested list (compound IDs of grounded non-prime words in the definition)
  - same symbol string — sibling senses share a symbol but are independent meanings
    retrieved at runtime via KNOW.by_symbol()

The primebit captures the DIRECT prime fingerprint — not a union of all nested
compounds' bits.  Full prime resolution requires graph traversal of the nested
chain (the reverse pyramid).  This prevents primebit collapse where transitive
unions cause all compounds to converge to the same dense bitfield.

Each lap expands the grounded set, so more tokens in each definition become
resolvable, enriching the nested list of every compound.

Grounded dict structure:
  grounded[symbol.lower()] = {
      "primary_compound_id": int | None,   # best-confidence sense ID (for nesting)
      "senses": [
          {
              "compound_id": int | None,
              "primebit":    int,
              "nested_ids":  [int],
              "confidence":  float,
              "sense_key":   str,           # e.g. "place for money", "river/lake"
              "pos":         str,           # e.g. "NOUN", "VERB"
              "_resolved":   int,
          },
          ...
      ]
  }

Usage:
    python dict_parser.py

Configure DICT_DIR and STORAGE_DIR below before running.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

DICT_DIR    = r"G:\AI\PABLO V0002\data\out"
STORAGE_DIR = r"G:\AI\PABLO V0002\storage"

MAX_LAPS = 20

# ══════════════════════════════════════════════════════════════════════════════
# Primes
# ══════════════════════════════════════════════════════════════════════════════

PRIME_INDEX: list[str] = [
    "AFTER", "ALL", "AT", "BAD", "BE", "BECAUSE", "BEFORE", "BETWEEN",
    "BODY", "CAN", "CAUSE", "CHANGE", "DATA", "DO", "DOWN", "ENTITY",
    "FAR", "FEEL", "FROM", "GOOD", "HAVE", "HEAR", "HEAT", "HERE",
    "IN", "KIND", "KNOW", "LAST", "LEFT", "LESS", "LIFE", "LIGHT",
    "MAKE", "MANY", "MORE", "MOVE", "NEAR", "NEED", "NONE", "NOW",
    "ONE", "OPEN", "OTHER", "PART", "READ", "RIGHT", "SAY", "SEE",
    "SELF", "SIDE", "SOME", "SYMBOL", "THINK", "THIS", "TIME", "TO",
    "TOUCH", "UP", "USE", "WANT", "WITH", "WRITE", "YOU",
]

PRIME_TO_BIT: dict[str, int]   = {name: idx for idx, name in enumerate(PRIME_INDEX)}
PRIME_SET_LOWER: set[str]      = {p.lower() for p in PRIME_INDEX}
LOWER_TO_PRIME: dict[str, str] = {p.lower(): p for p in PRIME_INDEX}

# ══════════════════════════════════════════════════════════════════════════════
# Logic compounds (IF, AND, OR, NOT, …)
# ══════════════════════════════════════════════════════════════════════════════

LOGIC_COMPOUNDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "logic_compounds.json",
)

def _load_logic_compounds() -> tuple[list[dict], dict[str, int]]:
    """Load logic_compounds.json → (compound list, token_variant→compound_id map)."""
    if not os.path.exists(LOGIC_COMPOUNDS_PATH):
        return [], {}
    with open(LOGIC_COMPOUNDS_PATH, encoding="utf-8") as f:
        compounds = json.load(f)
    variant_map: dict[str, int] = {}
    for c in compounds:
        cid = c["id"]
        for variant in c.get("token_variants", []):
            variant_map[variant.lower()] = cid
    return compounds, variant_map

LOGIC_COMPOUNDS, LOGIC_VARIANT_TO_ID = _load_logic_compounds()


# ══════════════════════════════════════════════════════════════════════════════
# PrimeBit helpers
# ══════════════════════════════════════════════════════════════════════════════

def primebit_union(bits: list[int]) -> int:
    value = 0
    for b in bits:
        value |= b
    return value


def primebit_to_names(primebit_value: int) -> list[str]:
    return [name for idx, name in enumerate(PRIME_INDEX) if (primebit_value >> idx) & 1]


# ══════════════════════════════════════════════════════════════════════════════
# Dictionary loader
# ══════════════════════════════════════════════════════════════════════════════

def load_entry(folder_path: Path) -> dict[str, Any] | None:
    folder_name = folder_path.name
    candidate   = folder_path / f"{folder_name}_v4.json"
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


def extract_senses(entry: dict[str, Any]) -> list[dict]:
    """Extract per-sense data from a dictionary entry.

    Each POS x SENSE combination becomes a separate sense record.
    Only main DEFINITION texts are used — subdefinitions are ignored
    (they restate the same meaning and dilute the primebit signal).
    Returns list of {sense_key, pos, texts}.
    """
    senses: list[dict] = []
    for pos, pos_data in entry.get("POS", {}).items():
        for sense_key, sense_data in pos_data.get("SENSE", {}).items():
            texts: list[str] = []
            for defn in sense_data.get("DEFINITIONS", []):
                if defn.get("TEXT"):
                    texts.append(defn["TEXT"])
            if texts:
                senses.append({
                    "sense_key": sense_key,
                    "pos":       pos,
                    "texts":     texts,
                })
    return senses


def extract_pos_tags(entry: dict[str, Any]) -> list[str]:
    return list(entry.get("POS", {}).keys())


def tokenise(text: str) -> list[str]:
    return re.findall(r"[\w''\u2019\-]+", text.lower())


# ══════════════════════════════════════════════════════════════════════════════
# Core: resolve definition tokens into nested compound IDs + direct primebit
# ══════════════════════════════════════════════════════════════════════════════

def resolve_definition(
    texts: list[str],
    grounded: dict[str, dict],
    skip_symbol: str = "",
) -> dict:
    """
    Walk every token in the definition texts.
    - prime name     → contribute its bit to primebit directly
    - grounded word  → contribute its primary compound_id to nested
                       (NO primebit inheritance — only direct primes get bits)
    - skip_symbol    → the headword being defined; skipped to prevent
                       self-referential nesting (a word cannot nest itself)

    Returns:
      nested_ids  — ordered unique compound IDs found in definition
      primebit    — ONLY bits for primes that appear directly as tokens
      confidence  — resolved_tokens / total_tokens
      total       — total token count
      resolved    — how many tokens were resolved
    """
    seen_ids:   list[int] = []
    seen_set:   set[int]  = set()
    prime_bits: list[int] = []
    total    = 0
    resolved = 0

    for text in texts:
        tokens = tokenise(text)
        total += len(tokens)
        for token in tokens:
            if token == skip_symbol:
                continue  # never nest a word inside its own definition
            if token in PRIME_SET_LOWER:
                prime = LOWER_TO_PRIME[token]
                prime_bits.append(1 << PRIME_TO_BIT[prime])
                resolved += 1
            elif token in LOGIC_VARIANT_TO_ID:
                # Logic compound (IF, AND, OR, NOT, …) — nest its ID
                lcid = LOGIC_VARIANT_TO_ID[token]
                if lcid not in seen_set:
                    seen_ids.append(lcid)
                    seen_set.add(lcid)
                resolved += 1
            elif token in grounded:
                cid = grounded[token].get("primary_compound_id")
                if cid is not None and cid not in seen_set:
                    seen_ids.append(cid)
                    seen_set.add(cid)
                resolved += 1

    return {
        "nested_ids": seen_ids,
        "primebit":   primebit_union(prime_bits),
        "confidence": round(resolved / total, 4) if total > 0 else 0.0,
        "total":      total,
        "resolved":   resolved,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Storage helpers
# ══════════════════════════════════════════════════════════════════════════════

def load_storage(storage_dir: str) -> tuple[dict, dict, dict, dict, dict]:
    def load_json(path: str) -> dict:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}
    return (
        load_json(os.path.join(storage_dir, "compounds.json")),
        load_json(os.path.join(storage_dir, "definitions.json")),
        load_json(os.path.join(storage_dir, "narratives.json")),
        load_json(os.path.join(storage_dir, "refinement.json")),
        load_json(os.path.join(storage_dir, "metadata.json")),
    )


def save_storage(storage_dir, compounds, definitions, narratives, refinement, metadata):
    os.makedirs(storage_dir, exist_ok=True)
    for filename, data in [
        ("compounds.json",   compounds),
        ("definitions.json", definitions),
        ("narratives.json",  narratives),
        ("refinement.json",  refinement),
        ("metadata.json",    metadata),
    ]:
        path = os.path.join(storage_dir, filename)
        tmp  = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    # Ensure triples.json exists (KNOW expects it on load)
    triples_path = os.path.join(storage_dir, "triples.json")
    if not os.path.exists(triples_path):
        with open(triples_path, "w", encoding="utf-8") as f:
            json.dump({}, f)


def build_symbol_index(compounds: dict) -> dict[str, list[int]]:
    """Map symbol.lower() -> list of compound IDs (supports multi-sense)."""
    index: dict[str, list[int]] = {}
    for cid, c in compounds.items():
        sym = c.get("symbol", "").lower()
        if sym:
            index.setdefault(sym, []).append(int(cid))
    return index


# ══════════════════════════════════════════════════════════════════════════════
# Upsert grounded senses to storage
# ══════════════════════════════════════════════════════════════════════════════

def write_grounded(
    grounded:     dict,
    all_entries:  dict,
    compounds:    dict,
    definitions:  dict,
    refinement:   dict,
    symbol_index: dict,
    next_id:      int,
    next_def_id:  int,
) -> tuple[int, int]:
    """Write all grounded senses to storage.

    Each sense in grounded[key]["senses"] becomes a separate compound.
    Senses sharing a symbol are independent meanings — no relations between
    them.  KNOW.by_symbol() retrieves the best-confidence compound by symbol
    at runtime.
    """

    for key, data in grounded.items():
        if key in PRIME_SET_LOWER:
            continue

        headword_entry = all_entries.get(key)
        headword       = headword_entry["headword"] if headword_entry else key
        pos_tags       = headword_entry.get("pos_tags", []) if headword_entry else []

        sense_compound_ids: list[int] = []

        for sense in data["senses"]:
            primebit   = sense.get("primebit", 0)
            nested_ids = sense.get("nested_ids", [])
            confidence = sense.get("confidence", 0.0)
            sense_key  = sense.get("sense_key", "")
            pos        = sense.get("pos", "")

            if primebit == 0 and not nested_ids:
                continue

            existing_id = sense.get("compound_id")

            if existing_id is not None and str(existing_id) in compounds:
                # ── Update existing compound ────────────────────────────
                c = compounds[str(existing_id)]
                c["primebit"]    = primebit
                c["nested"]      = nested_ids
                c["confidence"]  = confidence
                c["grounded"]    = True
                sense_compound_ids.append(existing_id)

                def_id = c.get("narrative_id")
                if def_id and str(def_id) in definitions:
                    definitions[str(def_id)]["thread"].append({
                        "timestamp":  time.time(),
                        "type":       "lap_refinement",
                        "nested_ids": nested_ids,
                        "primebit":   primebit,
                        "confidence": confidence,
                    })

            else:
                # ── Create new compound for this sense ──────────────────
                cid      = next_id
                next_id += 1

                compounds[str(cid)] = {
                    "id":           cid,
                    "symbol":       headword,
                    "sense_key":    sense_key,
                    "pos":          pos,
                    "primebit":     primebit,
                    "nested":       nested_ids,
                    "relations":    [],
                    "narrative_id": next_def_id,
                    "grounded":     True,
                    "version":      0,
                    "confidence":   confidence,
                    "executable":   False,
                    "trigger_condition": None,
                    "arity":        0,
                    "slots":        [],
                    "source":       "recursive_lap_parser",
                    "created_at":   time.time(),
                    "compound_type": "concept",
                }

                definitions[str(next_def_id)] = {
                    "id":          next_def_id,
                    "compound_id": cid,
                    "symbol":      headword,
                    "sense_key":   sense_key,
                    "pos":         pos,
                    "relations":   [],
                    "thread": [{
                        "timestamp":  time.time(),
                        "type":       "initial_grounding",
                        "provenance": {
                            "method":    "recursive_lap_parser",
                            "sense_key": sense_key,
                            "pos":       pos,
                            "pos_tags":  pos_tags,
                        },
                        "nested_ids": nested_ids,
                        "primebit":   primebit,
                        "confidence": confidence,
                    }],
                    "constraints": [],
                    "created_at":  time.time(),
                }

                refinement[str(cid)] = {
                    "compound_id":  cid,
                    "usage_count":  0,
                    "success_rate": 0.0,
                    "query_count":  0,
                }

                sense["compound_id"] = cid
                sense_compound_ids.append(cid)
                symbol_index.setdefault(key, []).append(cid)
                next_def_id += 1

        # ── Update primary_compound_id to best-confidence sense ─────────
        assigned = [s for s in data["senses"] if s.get("compound_id") is not None]
        if assigned:
            best = max(assigned, key=lambda s: s.get("confidence", 0.0))
            data["primary_compound_id"] = best["compound_id"]

    return next_id, next_def_id


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def run_laps(dict_dir: str, storage_dir: str) -> None:
    print(f"Loading storage from: {storage_dir}")
    compounds, definitions, narratives, refinement, metadata = load_storage(storage_dir)

    next_id        = metadata.get("next_id", 211)
    next_def_id    = metadata.get("next_def_id", 8)
    next_nar_id    = metadata.get("next_nar_id", 3)
    next_triple_id = metadata.get("next_triple_id", 1)

    symbol_index = build_symbol_index(compounds)

    # ── grounded: symbol.lower() -> {primary_compound_id, senses: [...]} ──
    grounded: dict[str, dict] = {}

    # Seed: 63 primes as roots (no compound IDs — they ARE the primes)
    for prime in PRIME_INDEX:
        grounded[prime.lower()] = {
            "primary_compound_id": None,
            "senses": [{
                "compound_id": None,
                "primebit":    1 << PRIME_TO_BIT[prime],
                "nested_ids":  [],
                "confidence":  1.0,
                "sense_key":   "prime",
                "pos":         "PRIME",
                "_resolved":   0,
            }],
        }

    # Seed: logic compounds (IF, AND, OR, NOT, …) via their token_variants
    for lc in LOGIC_COMPOUNDS:
        for variant in lc.get("token_variants", []):
            vkey = variant.lower()
            if vkey not in grounded and vkey not in PRIME_SET_LOWER:
                grounded[vkey] = {
                    "primary_compound_id": lc["id"],
                    "senses": [{
                        "compound_id": lc["id"],
                        "primebit":    lc.get("primebit", 0),
                        "nested_ids":  [],
                        "confidence":  1.0,
                        "sense_key":   "logic",
                        "pos":         "LOGIC",
                        "_resolved":   0,
                    }],
                }
    print(f"Seeded {len(LOGIC_COMPOUNDS)} logic compounds "
          f"({len(LOGIC_VARIANT_TO_ID)} token variants)")

    # Seed: already-stored grounded compounds (grouped by symbol)
    for cid, c in compounds.items():
        if c.get("grounded") and c.get("primebit", 0):
            sym = c.get("symbol", "").lower()
            if not sym:
                continue
            sense_entry = {
                "compound_id": int(cid),
                "primebit":    c["primebit"],
                "nested_ids":  c.get("nested", []),
                "confidence":  c.get("confidence", 0.0),
                "sense_key":   c.get("sense_key", ""),
                "pos":         c.get("pos", ""),
                "_resolved":   0,
            }
            if sym not in grounded:
                grounded[sym] = {
                    "primary_compound_id": int(cid),
                    "senses": [sense_entry],
                }
            else:
                grounded[sym]["senses"].append(sense_entry)
                # Update primary to highest confidence sense
                best = max(
                    grounded[sym]["senses"],
                    key=lambda s: s.get("confidence", 0.0),
                )
                if best.get("compound_id") is not None:
                    grounded[sym]["primary_compound_id"] = best["compound_id"]

    # Scan folders lazily
    print(f"Scanning dictionary: {dict_dir}")
    dict_path   = Path(dict_dir)
    all_folders = [f for f in dict_path.iterdir() if f.is_dir()]
    print(f"Found {len(all_folders)} folders")

    all_entries: dict[str, dict] = {}

    def ensure_loaded(folder: Path) -> str | None:
        entry = load_entry(folder)
        if not entry:
            return None
        headword = entry.get("HEADWORD", "").strip()
        if not headword:
            return None
        key = headword.lower()
        if key not in all_entries:
            all_entries[key] = {
                "headword": headword,
                "senses":   extract_senses(entry),
                "pos_tags": extract_pos_tags(entry),
            }
        return key

    # ── Lapping ───────────────────────────────────────────────────────────────
    lap = 0
    while lap < MAX_LAPS:
        lap            += 1
        new_senses      = 0
        updated_senses  = 0
        new_words       = 0

        total_sense_count = sum(len(g["senses"]) for g in grounded.values())
        print(f"\n== Lap {lap} == words: {len(grounded)}  senses: {total_sense_count}")

        for i, folder in enumerate(all_folders):
            if i % 5000 == 0:
                print(f"   {i}/{len(all_folders)}...", end="\r", flush=True)

            key = ensure_loaded(folder)
            if key is None or key in PRIME_SET_LOWER:
                continue

            entry_senses = all_entries[key]["senses"]
            if not entry_senses:
                continue

            already      = grounded.get(key)
            word_is_new  = already is None

            for sense_info in entry_senses:
                result = resolve_definition(sense_info["texts"], grounded, skip_symbol=key)
                if result["resolved"] == 0:
                    continue

                sk  = sense_info["sense_key"]
                pos = sense_info["pos"]

                if already is None:
                    # First sense grounds this word
                    grounded[key] = {
                        "primary_compound_id": None,
                        "senses": [{
                            "compound_id": None,
                            "primebit":    result["primebit"],
                            "nested_ids":  result["nested_ids"],
                            "confidence":  result["confidence"],
                            "sense_key":   sk,
                            "pos":         pos,
                            "_resolved":   result["resolved"],
                        }],
                    }
                    already = grounded[key]
                    new_senses += 1
                    if word_is_new:
                        new_words  += 1
                        word_is_new = False
                else:
                    # Find existing sense with same sense_key + pos
                    existing_sense = None
                    for s in already["senses"]:
                        if s["sense_key"] == sk and s["pos"] == pos:
                            existing_sense = s
                            break

                    if existing_sense is None:
                        # New sense for this word
                        already["senses"].append({
                            "compound_id": None,
                            "primebit":    result["primebit"],
                            "nested_ids":  result["nested_ids"],
                            "confidence":  result["confidence"],
                            "sense_key":   sk,
                            "pos":         pos,
                            "_resolved":   result["resolved"],
                        })
                        new_senses += 1
                    elif (result["resolved"] > existing_sense.get("_resolved", 0)
                          or result["primebit"] != existing_sense["primebit"]):
                        existing_sense["primebit"]   = result["primebit"]
                        existing_sense["nested_ids"] = result["nested_ids"]
                        existing_sense["confidence"] = result["confidence"]
                        existing_sense["_resolved"]  = result["resolved"]
                        updated_senses += 1

        print(f"   New words: {new_words}  |  New senses: {new_senses}  "
              f"|  Updated: {updated_senses}        ")

        next_id, next_def_id = write_grounded(
            grounded, all_entries, compounds, definitions,
            refinement, symbol_index, next_id, next_def_id,
        )
        metadata.update({
            "next_id":        next_id,
            "next_def_id":    next_def_id,
            "next_nar_id":    next_nar_id,
            "next_triple_id": next_triple_id,
            "saved_at":       time.time(),
        })
        save_storage(storage_dir, compounds, definitions, narratives, refinement, metadata)
        print(f"   Saved. Compounds in storage: {len(compounds)}")

        if new_senses == 0 and updated_senses == 0:
            print(f"   Converged at lap {lap}.")
            break

    # ── Summary ───────────────────────────────────────────────────────────────
    multi = sum(1 for g in grounded.values() if len(g["senses"]) > 1)
    total_senses = sum(len(g["senses"]) for g in grounded.values())
    print(f"\nDone. {len(grounded)} words, {total_senses} senses "
          f"({multi} multi-sense). Next compound ID: {next_id}")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_laps(DICT_DIR, STORAGE_DIR)
