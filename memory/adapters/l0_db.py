# G:\PABLO\tools\l0_db.py
from __future__ import annotations
import json, sqlite3, hashlib, time
from typing import Any, Dict, List, Optional

PRAGMAS = [
    ("journal_mode", "WAL"),
    ("synchronous", "NORMAL"),
    ("temp_store", "MEMORY"),
    ("foreign_keys", "ON"),
    ("cache_size", "-200000"),  # ~200 MB page cache
]

SCHEMA = r"""
CREATE TABLE IF NOT EXISTS l0_entry (
  lemma       TEXT PRIMARY KEY,
  json        TEXT NOT NULL,
  checksum    TEXT,
  updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    for k, v in PRAGMAS:
        try: conn.execute(f"PRAGMA {k}={v}")
        except sqlite3.DatabaseError: pass
    conn.executescript(SCHEMA)
    return conn

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()

def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

def upsert_lemma(conn: sqlite3.Connection, lemma_obj: Dict[str, Any]) -> None:
    """
    Expects your approved shape:
      {
        "lemma": "...",
        "variants": [...],
        "entries": [
          {
            "word": "...",
            "pronunciation": ["..."],
            "pos": {
              "V": [ { "forms": {...}, "definitions": [ { "definition": "...", "labels": [...], "label_groups": ..., "examples": [...], "subdefinitions": [...] }, ... ] } ],
              "ADJ": [ ... ],
              ...
            }
          }
        ]
      }
    """
    lemma = lemma_obj["lemma"]
    raw = _json(lemma_obj)
    checksum = _sha(raw)
    cur = conn.cursor()
    cur.execute("BEGIN")
    # l0_entry
    cur.execute("""
        INSERT INTO l0_entry(lemma,json,checksum,updated_at)
        VALUES(?,?,?,datetime('now'))
        ON CONFLICT(lemma) DO UPDATE SET json=excluded.json, checksum=excluded.checksum, updated_at=excluded.updated_at
    """, (lemma, raw, checksum))

    # variants
    cur.execute("DELETE FROM l0_variant WHERE lemma=?", (lemma,))
    for v in (lemma_obj.get("variants") or []):
        if isinstance(v, str) and v.strip():
            cur.execute("INSERT OR IGNORE INTO l0_variant(lemma,variant) VALUES(?,?)", (lemma, v.strip()))

    # clear detail tables (we write everything fresh)
    cur.execute("DELETE FROM l0_def_label WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_example WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_def WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_forms_noun WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_forms_adjadv WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_forms_verb WHERE lemma=?", (lemma,))

    # gather & insert by walking entries/pos/defs
    entries = lemma_obj.get("entries") or []
    # FORMS (we store per-lemma, so we’ll merge forms from the first suitable POS block)
    noun_plural: Optional[str | List[str]] = None
    adj_forms = {"ADJ": {"comparative": None, "superlative": None}, "ADV": {"comparative": None, "superlative": None}}
    verb_forms = {k: None for k in ("1PSP","2PSP","3PSP","PLSP","1PST","2PST","3PST","PLPT","SIMPLE","PAP","PRP","INF","GER")}

    def _merge(a, b):
        return a if a else b

    sense_row_inserts = []
    label_row_inserts = []
    example_row_inserts = []

    for ent in entries:
        pos_map = (ent.get("pos") or {})
        for pos_code, blocks in pos_map.items():
            if not isinstance(blocks, list): continue
            for block in blocks:
                # FORMS harvest (first non-empty wins)
                forms = block.get("forms") or {}
                if pos_code in ("N","PROPN","LETTER"):
                    if noun_plural is None and forms.get("plural"):
                        noun_plural = forms.get("plural")
                if pos_code in ("ADJ","ADV"):
                    adj_forms[pos_code]["comparative"] = _merge(adj_forms[pos_code]["comparative"], forms.get("comparative"))
                    adj_forms[pos_code]["superlative"] = _merge(adj_forms[pos_code]["superlative"], forms.get("superlative"))
                if pos_code == "V":
                    vi = forms.get("verb_inflections") or {}
                    for k in verb_forms:
                        verb_forms[k] = _merge(verb_forms[k], vi.get(k))

                # DEFINITIONS + SUBDEFS
                defs = block.get("definitions") or []
                for i, d in enumerate(defs, 1):
                    gloss = (d.get("definition") or "").strip()
                    if not gloss:
                        continue
                    labels = d.get("labels") or []
                    label_groups = d.get("label_groups")
                    sense_row_inserts.append((
                        lemma, pos_code, i, None, gloss,
                        json.dumps(labels, ensure_ascii=False) if labels else None,
                        json.dumps(label_groups, ensure_ascii=False) if label_groups else None
                    ))
                    for lb in labels:
                        if isinstance(lb, str) and lb.strip():
                            label_row_inserts.append((lemma, pos_code, i, None, lb.strip()))
                    # examples
                    exs = d.get("examples") or []
                    for j, ex in enumerate(exs, 1):
                        if isinstance(ex, str) and ex.strip():
                            example_row_inserts.append((lemma, pos_code, i, None, j, ex.strip()))
                    # SUBDEFS
                    for k, sd in enumerate(d.get("subdefinitions") or [], 1):
                        sgloss = (sd.get("definition") or "").strip()
                        if not sgloss:
                            continue
                        slabels = sd.get("labels") or []
                        slabel_groups = sd.get("label_groups")
                        sense_row_inserts.append((
                            lemma, pos_code, i, k, sgloss,
                            json.dumps(slabels, ensure_ascii=False) if slabels else None,
                            json.dumps(slabel_groups, ensure_ascii=False) if slabel_groups else None
                        ))
                        for lb in slabels:
                            if isinstance(lb, str) and lb.strip():
                                label_row_inserts.append((lemma, pos_code, i, k, lb.strip()))
                        sexs = sd.get("examples") or []
                        for j, ex in enumerate(sexs, 1):
                            if isinstance(ex, str) and ex.strip():
                                example_row_inserts.append((lemma, pos_code, i, k, j, ex.strip()))

    # bulk inserts
    if sense_row_inserts:
        conn.executemany("""
            INSERT INTO l0_def(lemma,pos,sense_index,subsense_index,def,labels_json,label_groups_json)
            VALUES(?,?,?,?,?,?,?)
        """, sense_row_inserts)
    if label_row_inserts:
        conn.executemany("""
            INSERT OR IGNORE INTO l0_def_label(lemma,pos,sense_index,subsense_index,label)
            VALUES(?,?,?,?,?)
        """, label_row_inserts)
    if example_row_inserts:
        conn.executemany("""
            INSERT OR REPLACE INTO l0_example(lemma,pos,sense_index,subsense_index,ex_index,example)
            VALUES(?,?,?,?,?,?)
        """, example_row_inserts)

    # write FORMS tables
    if noun_plural is not None:
        conn.execute("INSERT OR REPLACE INTO l0_forms_noun(lemma,plural) VALUES(?,?)", (lemma, json.dumps(noun_plural, ensure_ascii=False) if isinstance(noun_plural, list) else noun_plural))
    for pos in ("ADJ","ADV"):
        comp = adj_forms[pos]["comparative"]; sup = adj_forms[pos]["superlative"]
        if comp or sup:
            conn.execute("INSERT OR REPLACE INTO l0_forms_adjadv(lemma,pos,comparative,superlative) VALUES(?,?,?,?)",
                         (lemma, pos, comp, sup))
    if any(verb_forms.values()):
        cols = ",".join([f'"{k}"' for k in verb_forms.keys()])
        qs   = ",".join(["?"]*len(verb_forms))
        conn.execute(f'INSERT OR REPLACE INTO l0_forms_verb(lemma,{cols}) VALUES(?,{qs})',
                     (lemma, *[verb_forms[k] for k in verb_forms.keys()]))

    conn.commit()
