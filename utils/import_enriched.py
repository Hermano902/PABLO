"""
import_enriched.py - Import enriched dictionary senses into PABLO storage.

Reads all *_enriched.json files from data/enriched/ and writes them into:
  - storage/*.json  (compounds, triples, narratives, definitions, refinement, metadata)
  - storage/pablo.duckdb  (created if absent; skipped if duckdb is not installed)

Each sense becomes one compound:
  symbol   = headword  (bare, e.g. "run")
  primebit = bitmask from sense's primebit list
  nested   = [] (word strings not yet resolved to IDs)
  triples  = stored in triples store, keyed by compound ID
  narrative = stored as a Narrative

Usage:
    python utils/import_enriched.py [--dry-run] [--limit N] [--no-duckdb]
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
DB_PATH      = STORAGE_DIR / "pablo.duckdb"

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

DUCKDB_SCHEMA = """
CREATE TABLE IF NOT EXISTS compounds (
    id            BIGINT PRIMARY KEY,
    symbol        TEXT NOT NULL,
    headword      TEXT NOT NULL DEFAULT '',
    sense_key     TEXT NOT NULL DEFAULT '',
    pos           TEXT NOT NULL DEFAULT '',
    primebit      BIGINT NOT NULL DEFAULT 0,
    compound_type TEXT NOT NULL DEFAULT 'concept',
    depth         INTEGER NOT NULL DEFAULT 0,
    grounded      BOOLEAN NOT NULL DEFAULT false,
    narrative_id  BIGINT
);
CREATE TABLE IF NOT EXISTS definitions (
    compound_id  BIGINT PRIMARY KEY,
    definition   TEXT NOT NULL DEFAULT '',
    nested_words JSON NOT NULL DEFAULT '[]',
    relations    JSON NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS refinement (
    compound_id  BIGINT PRIMARY KEY,
    version      INTEGER NOT NULL DEFAULT 0,
    confidence   DOUBLE  NOT NULL DEFAULT 0.0,
    source       TEXT    NOT NULL DEFAULT '',
    created_at   DOUBLE  NOT NULL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS execution (
    compound_id       BIGINT PRIMARY KEY,
    executable        BOOLEAN NOT NULL DEFAULT false,
    trigger_condition BIGINT,
    arity             INTEGER NOT NULL DEFAULT 0,
    slots             JSON    NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS triples (
    id          BIGINT PRIMARY KEY,
    source_id   BIGINT NOT NULL,
    subject     TEXT   NOT NULL DEFAULT '',
    predicate   TEXT   NOT NULL DEFAULT '',
    target      TEXT   NOT NULL DEFAULT '',
    triple_type TEXT   NOT NULL DEFAULT 'semantic',
    created_at  DOUBLE NOT NULL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS narratives (
    id          BIGINT PRIMARY KEY,
    compound_id BIGINT NOT NULL,
    thread      JSON   NOT NULL DEFAULT '[]',
    created_at  DOUBLE NOT NULL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_compounds_depth    ON compounds(depth);
CREATE INDEX IF NOT EXISTS idx_compounds_symbol   ON compounds(symbol);
CREATE INDEX IF NOT EXISTS idx_compounds_headword ON compounds(headword);
CREATE INDEX IF NOT EXISTS idx_triples_source     ON triples(source_id);
CREATE INDEX IF NOT EXISTS idx_narratives_compound ON narratives(compound_id);
"""


def primes_to_mask(prime_names: list[str]) -> int:
    value = 0
    for name in prime_names:
        bit = PRIME_TO_BIT.get(name.upper())
        if bit is not None:
            value |= (1 << bit)
    return value


def estimate_depth(nested_words: list[str]) -> int:
    n = len(nested_words)
    if n == 0:  return 0
    if n <= 3:  return 1
    if n <= 7:  return 2
    if n <= 12: return 3
    return 4


# ── JSON storage helpers ──────────────────────────────────────────────────────

def load_storage() -> tuple[dict, dict, dict, dict, dict]:
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


def sense_dedup_key(headword: str, sense_key: str) -> str:
    """Unique key per sense — used for dedup in both JSON and DB."""
    return f"{headword}|{sense_key}"


# ── DuckDB helpers ────────────────────────────────────────────────────────────

def open_duckdb():
    try:
        import duckdb
    except ImportError:
        return None, None
    STORAGE_DIR.mkdir(exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    conn.execute(DUCKDB_SCHEMA)
    return duckdb, conn


def duckdb_existing_keys(conn) -> set[str]:
    return {
        f"{row[0]}|{row[1]}"
        for row in conn.execute("SELECT headword, sense_key FROM compounds").fetchall()
    }


def duckdb_next_ids(conn) -> tuple[int, int]:
    meta = {k: v for k, v in conn.execute("SELECT key, value FROM metadata").fetchall()}
    return int(meta.get("next_id", "200")), int(meta.get("next_triple_id", "1"))


def flush_to_duckdb(conn, compound_rows, def_rows, ref_rows, exec_rows, triple_rows, nar_rows,
                    next_id, next_triple_id) -> None:
    if compound_rows:
        conn.executemany("INSERT OR IGNORE INTO compounds VALUES (?,?,?,?,?,?,?,?,?,?)", compound_rows)
        conn.executemany("INSERT OR IGNORE INTO definitions VALUES (?,?,?,?)", def_rows)
        conn.executemany("INSERT OR IGNORE INTO refinement VALUES (?,?,?,?,?)", ref_rows)
        conn.executemany("INSERT OR IGNORE INTO execution VALUES (?,?,?,?,?)", exec_rows)
    if triple_rows:
        conn.executemany("INSERT OR IGNORE INTO triples VALUES (?,?,?,?,?,?,?)", triple_rows)
    if nar_rows:
        conn.executemany("INSERT OR IGNORE INTO narratives VALUES (?,?,?,?)", nar_rows)
    for key, val in [("next_id", next_id), ("next_triple_id", next_triple_id)]:
        conn.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", [key, str(val)])


# ── Main import ───────────────────────────────────────────────────────────────

def import_enriched(dry_run: bool = False, limit: int | None = None,
                    no_duckdb: bool = False, db_only: bool = False) -> None:
    # --- JSON storage ---
    compounds, definitions, narratives, refinement, triples = load_storage()
    metadata = load_metadata()

    next_id        = metadata["next_id"]
    next_def_id    = metadata["next_def_id"]
    next_nar_id    = metadata["next_nar_id"]
    next_triple_id = metadata["next_triple_id"]

    # Dedup per sense: use headword|sense_key so each sense is a distinct compound.
    # Falls back gracefully for hand-crafted compounds that have no sense_key.
    existing_symbols: set[str] = {
        sense_dedup_key(v.get("headword", v["symbol"]), v.get("sense_key", ""))
        for v in compounds.values()
    }

    # --- DuckDB ---
    duckdb_mod, conn = (None, None) if no_duckdb else open_duckdb()
    if conn is not None:
        db_existing = duckdb_existing_keys(conn)
        db_next_id, db_next_triple_id = duckdb_next_ids(conn)
        # Sync ID counters — use the higher of JSON vs DB
        next_id        = max(next_id, db_next_id)
        next_triple_id = max(next_triple_id, db_next_triple_id)
    else:
        db_existing = set()

    db_compound_rows: list = []
    db_def_rows:      list = []
    db_ref_rows:      list = []
    db_exec_rows:     list = []
    db_triple_rows:   list = []
    db_nar_rows:      list = []

    files = sorted(ENRICHED_DIR.rglob("*_enriched.json"))
    if limit:
        files = files[:limit]

    added_compounds  = 0
    added_triples    = 0
    added_narratives = 0
    skipped          = 0
    now = time.time()

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        headword = data["headword"]

        for sense in data.get("senses", []):
            sense_key     = sense.get("sense_key", "sense_1")
            pos           = sense.get("pos", "UNKNOWN")
            definition    = sense.get("definition", "")
            raw_triples   = sense.get("triples", [])
            raw_narrative = sense.get("narrative", [])
            prime_names   = sense.get("primebit", [])
            nested_words  = sense.get("nested", [])

            sym       = headword          # semantic label; same word, different senses share it
            dedup_key = sense_dedup_key(headword, sense_key)

            in_json = dedup_key in existing_symbols
            in_db   = dedup_key in db_existing

            if in_json and (conn is None or in_db):
                # Already in all active stores — skip
                skipped += 1
                continue

            if not raw_triples:
                skipped += 1
                continue

            # Reuse existing JSON compound_id if already there, else allocate new
            if in_json:
                existing_c = next(
                    c for c in compounds.values()
                    if sense_dedup_key(c.get("headword", c["symbol"]), c.get("sense_key", "")) == dedup_key
                )
                compound_id = existing_c["id"]
                def_id      = existing_c.get("narrative_id", next_def_id)
                nar_id      = next_nar_id
                next_nar_id += 1
            else:
                compound_id    = next_id
                def_id         = next_def_id
                nar_id         = next_nar_id
                next_id        += 1
                next_def_id    += 1
                next_nar_id    += 1

            primebit_value = primes_to_mask(prime_names)
            depth          = estimate_depth(nested_words)

            added_compounds += 1
            existing_symbols.add(dedup_key)
            db_existing.add(dedup_key)

            # -- JSON compound (skip if already there) --
            if not in_json:
                compound = {
                    "id":               compound_id,
                    "symbol":           sym,
                    "primebit":         primebit_value,
                    "nested":           [],
                    "relations":        [],
                    "narrative_id":     def_id,
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
                    "headword":         headword,
                    "sense_key":        sense_key,
                    "pos":              pos,
                    "definition":       definition,
                    "nested_words":     nested_words,
                }
                compounds[str(compound_id)] = compound
                refinement[str(compound_id)] = {"compound_id": compound_id}

            # -- DuckDB compound rows (skip if already in DB) --
            if conn is not None and not in_db:
                db_compound_rows.append((
                    compound_id, sym, headword, sense_key, pos,
                    primebit_value, "concept", depth, True, def_id,
                ))
                db_def_rows.append((
                    compound_id, definition,
                    json.dumps(nested_words),
                    json.dumps([]),
                ))
                db_ref_rows.append((compound_id, 1, 1.0, f"enriched:{headword}", now))
                db_exec_rows.append((compound_id, False, None, 0, "[]"))

            # -- Semantic triples --
            triple_ids = []
            for t in raw_triples:
                tid = next_triple_id
                next_triple_id += 1
                if not in_json:
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
                if conn is not None and not in_db:
                    db_triple_rows.append((tid, compound_id, t.get("s",""), t.get("p",""), t.get("o",""), "semantic", now))

            # -- DefinitionNarrative (JSON) --
            if not in_json:
                definitions[str(def_id)] = {
                    "id":          def_id,
                    "compound_id": compound_id,
                    "symbol":      sym,
                    "relations":   [],
                    "thread":      triple_ids,
                    "constraints": [],
                    "created_at":  now,
                }

            # -- Narrative triples --
            narrative_frame_ids = []
            for t in raw_narrative:
                tid = next_triple_id
                next_triple_id += 1
                if not in_json:
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
                if conn is not None and not in_db:
                    db_triple_rows.append((tid, compound_id, t.get("s",""), t.get("p",""), t.get("o",""), "narrative", now))

            if not in_json:
                narratives[str(nar_id)] = {
                    "id":          nar_id,
                    "compound_id": compound_id,
                    "thread":      narrative_frame_ids,
                    "created_at":  now,
                }
            added_narratives += 1
            if conn is not None and not in_db:
                db_nar_rows.append((nar_id, compound_id, json.dumps(narrative_frame_ids), now))

    metadata["next_id"]        = next_id
    metadata["next_def_id"]    = next_def_id
    metadata["next_nar_id"]    = next_nar_id
    metadata["next_triple_id"] = next_triple_id

    print(f"Compounds added:  {added_compounds}")
    print(f"Triples added:    {added_triples}")
    print(f"Narratives added: {added_narratives}")
    print(f"Skipped:          {skipped}")
    print(f"Total compounds:  {len(compounds)}")

    if dry_run:
        print("[dry-run — nothing written]")
        if conn is not None:
            conn.close()
        return

    if not db_only:
        save_storage(compounds, definitions, narratives, refinement, triples, metadata)
        print(f"JSON saved to {STORAGE_DIR}")

    if conn is not None:
        flush_to_duckdb(conn, db_compound_rows, db_def_rows, db_ref_rows, db_exec_rows,
                        db_triple_rows, db_nar_rows, next_id, next_triple_id)
        total = conn.execute("SELECT COUNT(*) FROM compounds").fetchone()[0]
        conn.close()
        print(f"DuckDB saved to {DB_PATH}  ({total} compounds)")
    elif db_only:
        print("WARNING: --db-only requested but DuckDB is unavailable — nothing written")
    else:
        if no_duckdb:
            print("DuckDB skipped (--no-duckdb)")
        else:
            print("DuckDB skipped (duckdb not installed)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import enriched senses into PABLO storage")
    parser.add_argument("--dry-run",   action="store_true", help="Count without writing")
    parser.add_argument("--limit",     type=int, default=None, help="Process only first N files")
    parser.add_argument("--no-duckdb", action="store_true", help="Skip DuckDB, write JSON only")
    parser.add_argument("--db-only",   action="store_true", help="Write DuckDB only, skip JSON files")
    args = parser.parse_args()
    import_enriched(dry_run=args.dry_run, limit=args.limit,
                    no_duckdb=args.no_duckdb, db_only=args.db_only)


if __name__ == "__main__":
    main()
