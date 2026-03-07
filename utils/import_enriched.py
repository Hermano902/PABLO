"""
import_enriched.py - Import enriched dictionary senses into PABLO storage.

Reads all *_enriched.json files from data/enriched/ and writes them directly
into the storage/ JSON files (compounds, triples, narratives, metadata).

Each sense becomes one compound:
  symbol   = "headword/sense_key"  (e.g. "run/race")
  primebit = bitmask from sense's primebit list
  nested   = [] (word strings not yet resolved to IDs)
  triples  = stored in triples.json, keyed by compound ID
  narrative = stored as a Narrative in narratives.json

Usage:
    python utils/import_enriched.py [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_ROOT        = Path(__file__).resolve().parent.parent
ENRICHED_DIR = _ROOT / "data" / "enriched"
STORAGE_DIR  = _ROOT / "storage"

# Prime name -> bit index (must match core/primebit.py)
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
PRIME_TO_BIT = {name: idx for idx, name in enumerate(PRIME_INDEX)}


def primes_to_mask(prime_names: list[str]) -> int:
    value = 0
    for name in prime_names:
        bit = PRIME_TO_BIT.get(name.upper())
        if bit is not None:
            value |= (1 << bit)
    return value


def load_storage() -> tuple[dict, dict, dict, dict, dict]:
    """Load all five storage files. Return (compounds, definitions, narratives, refinement, triples)."""
    def load(name: str) -> dict:
        path = STORAGE_DIR / name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    return (
        load("compounds.json"),
        load("definitions.json"),
        load("narratives.json"),
        load("refinement.json"),
        load("triples.json"),
    )


def load_metadata() -> dict:
    path = STORAGE_DIR / "metadata.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"next_id": 200, "next_def_id": 1, "next_nar_id": 1, "next_triple_id": 1}


def save_storage(
    compounds: dict,
    definitions: dict,
    narratives: dict,
    refinement: dict,
    triples: dict,
    metadata: dict,
) -> None:
    STORAGE_DIR.mkdir(exist_ok=True)
    (STORAGE_DIR / "compounds.json").write_text(
        json.dumps(compounds, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (STORAGE_DIR / "definitions.json").write_text(
        json.dumps(definitions, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (STORAGE_DIR / "narratives.json").write_text(
        json.dumps(narratives, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (STORAGE_DIR / "refinement.json").write_text(
        json.dumps(refinement, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (STORAGE_DIR / "triples.json").write_text(
        json.dumps(triples, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (STORAGE_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def symbol_key(headword: str, sense_key: str) -> str:
    """Canonical symbol for a sense compound."""
    # sanitise sense_key: strip newlines, truncate
    key = sense_key.strip().replace("\n", " ")[:80]
    return f"{headword}/{key}"


def import_enriched(dry_run: bool = False, limit: int | None = None) -> None:
    compounds, definitions, narratives, refinement, triples = load_storage()
    metadata = load_metadata()

    next_id        = metadata["next_id"]
    next_def_id    = metadata["next_def_id"]
    next_nar_id    = metadata["next_nar_id"]
    next_triple_id = metadata["next_triple_id"]

    # Build existing symbol set to skip re-imports
    existing_symbols: set[str] = {v["symbol"] for v in compounds.values()}

    files = sorted(ENRICHED_DIR.rglob("*_enriched.json"))
    if limit:
        files = files[:limit]

    added_compounds  = 0
    added_triples    = 0
    added_narratives = 0
    skipped          = 0

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        headword = data["headword"]

        for sense in data.get("senses", []):
            sense_key  = sense.get("sense_key", "sense_1")
            pos        = sense.get("pos", "UNKNOWN")
            definition = sense.get("definition", "")
            raw_triples   = sense.get("triples", [])
            raw_narrative = sense.get("narrative", [])
            prime_names   = sense.get("primebit", [])
            nested_words  = sense.get("nested", [])

            sym = symbol_key(headword, sense_key)

            if sym in existing_symbols:
                skipped += 1
                continue

            if not raw_triples:
                # No triples — skip empty senses
                skipped += 1
                continue

            compound_id = next_id
            def_id      = next_def_id
            nar_id      = next_nar_id
            next_id     += 1
            next_def_id += 1
            next_nar_id += 1

            primebit_value = primes_to_mask(prime_names)
            now = time.time()

            # -- Compound --
            compound = {
                "id":               compound_id,
                "symbol":           sym,
                "primebit":         primebit_value,
                "nested":           [],          # word strings not resolved to IDs yet
                "relations":        [],
                "narrative_id":     def_id,      # points to DefinitionNarrative in definitions.json
                "grounded":         True,
                "version":          1,
                "confidence":       1.0,
                "executable":       False,
                "trigger_condition": None,
                "arity":            0,
                "slots":            [],
                "source":           f"enriched:{headword}",
                "compound_type":    "concept",
                "created_at":       now,
                # extra retrieval metadata (not part of Compound schema, used by comprehension)
                "headword":         headword,
                "sense_key":        sense_key,
                "pos":              pos,
                "definition":       definition,
                "nested_words":     nested_words,
            }
            compounds[str(compound_id)] = compound
            existing_symbols.add(sym)
            refinement[str(compound_id)] = {"compound_id": compound_id}
            added_compounds += 1

            # -- Triples (semantic graph) — stored in triples.json, type="semantic" --
            triple_ids = []
            for t in raw_triples:
                tid = next_triple_id
                next_triple_id += 1
                triples[str(tid)] = {
                    "id":          tid,
                    "source_id":   compound_id,
                    "predicate":   t["p"],
                    "target":      t["o"],
                    "subject":     t["s"],
                    "triple_type": "semantic",
                    "created_at":  now,
                }
                triple_ids.append(tid)
                added_triples += 1

            # -- DefinitionNarrative — thread holds the semantic triple IDs --
            definitions[str(def_id)] = {
                "id":          def_id,
                "compound_id": compound_id,
                "symbol":      sym,
                "relations":   [],
                "thread":      triple_ids,       # semantic triple IDs
                "constraints": [],
                "created_at":  now,
            }

            # -- Narrative (situational event sequence) — stored in narratives.json --
            narrative_frame_ids = []
            for t in raw_narrative:
                tid = next_triple_id
                next_triple_id += 1
                triples[str(tid)] = {
                    "id":          tid,
                    "source_id":   compound_id,
                    "predicate":   t["p"],
                    "target":      t["o"],
                    "subject":     t["s"],
                    "triple_type": "narrative",
                    "created_at":  now,
                }
                narrative_frame_ids.append(tid)
                added_triples += 1

            narratives[str(nar_id)] = {
                "id":          nar_id,
                "compound_id": compound_id,
                "thread":      narrative_frame_ids,
                "created_at":  now,
            }
            added_narratives += 1

    metadata["next_id"]        = next_id
    metadata["next_def_id"]    = next_def_id
    metadata["next_nar_id"]    = next_nar_id
    metadata["next_triple_id"] = next_triple_id

    print(f"Compounds added:  {added_compounds}")
    print(f"Triples added:    {added_triples}")
    print(f"Narratives added: {added_narratives}")
    print(f"Skipped:          {skipped}")
    print(f"Total compounds:  {len(compounds)}")

    if not dry_run:
        save_storage(compounds, definitions, narratives, refinement, triples, metadata)
        print(f"Saved to {STORAGE_DIR}")
    else:
        print("[dry-run — nothing written]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import enriched senses into PABLO storage")
    parser.add_argument("--dry-run", action="store_true", help="Count without writing")
    parser.add_argument("--limit",   type=int, default=None, help="Process only first N files")
    args = parser.parse_args()
    import_enriched(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
