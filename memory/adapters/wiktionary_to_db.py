# G:\PABLO\tools\wiktionary_to_db.py
from __future__ import annotations
import argparse, sys, time, json, re
from pathlib import Path
from typing import Dict, Any, List, Optional

# 1) bring your scraper
sys.path.insert(0, str(Path(__file__).parent))
from wiktionary_scraper import scrape_word  # expects the function you’ve been using

# 2) DB writer
import l0_db

# 3) minimal label enricher (same logic as your dictionary_label_enricher.py)
_LEAD_PAREN_RE = re.compile(r"^\(\s*([^)]*?)\s*\)\s*")
_TRAIL_BRACKET_RE = re.compile(r"\s*\[([^\]]+)\]\s*$")
_SPLIT_RE = re.compile(r"\s*(?:,|;|/|\band\b)\s*", re.IGNORECASE)

def _extract_leading_groups(text: str):
    rest = (text or "").strip()
    groups: List[str] = []
    while True:
        m = _LEAD_PAREN_RE.match(rest)
        if not m: break
        groups.append(m.group(1))
        rest = rest[m.end():]
    return rest, groups

def _extract_trailing_bracket(text: str):
    m = _TRAIL_BRACKET_RE.search(text or "")
    if not m: return text, None
    return (text[:m.start()].rstrip(), m.group(1).strip())

def _tokenize_groups(groups: List[str]) -> List[str]:
    toks: List[str] = []
    for g in groups:
        parts = [p.strip() for p in _SPLIT_RE.split(g) if p.strip()]
        toks.extend(parts if parts else [g.strip()])
    return toks

def _enrich_def_inplace(d: Dict, remove_from_gloss: bool = True):
    if not isinstance(d, dict): return d
    raw = (d.get("definition") or "").strip()
    if not raw:
        # recurse into subdefs anyway
        if d.get("subdefinitions"):
            d["subdefinitions"] = [_enrich_def_inplace(sd, remove_from_gloss) for sd in d["subdefinitions"]]
        return d
    after_groups, groups = _extract_leading_groups(raw)
    after_bracket, dating_raw = _extract_trailing_bracket(after_groups)
    tokens = _tokenize_groups(groups)
    if tokens: d["labels"] = tokens
    if groups: d["label_groups"] = groups
    if dating_raw: d["dating_raw"] = dating_raw
    if remove_from_gloss and (groups or dating_raw):
        d["definition"] = after_bracket
    if d.get("subdefinitions"):
        d["subdefinitions"] = [_enrich_def_inplace(sd, remove_from_gloss) for sd in d["subdefinitions"]]
    return d

def _enrich_lemma_inplace(lemma_obj: Dict[str, Any]):
    for ent in lemma_obj.get("entries") or []:
        pos_map = ent.get("pos") or {}
        for blocks in pos_map.values():
            if not isinstance(blocks, list): continue
            for b in blocks:
                defs = b.get("definitions") or []
                b["definitions"] = [_enrich_def_inplace(d, True) for d in defs]
    return lemma_obj

def parse_args():
    ap = argparse.ArgumentParser(description="Scrape Wiktionary and write to l0 DB")
    ag = ap.add_mutually_exclusive_group(required=True)
    ag.add_argument("--word", help="single lemma")
    ag.add_argument("--list", help="path to words.txt (one per line)")
    ap.add_argument("--db", required=True, help="path to sqlite db")
    ap.add_argument("--sleep", type=float, default=0.0)
    ap.add_argument("--retries", type=int, default=0)
    ap.add_argument("--no-files", action="store_true", help="(ignored here; always DB)")
    return ap.parse_args()

def main():
    args = parse_args()
    conn = l0_db.connect(args.db)

    words = [args.word] if args.word else [w.strip() for w in Path(args.list).read_text(encoding="utf-8").splitlines() if w.strip()]
    total = len(words)
    for i, w in enumerate(words, 1):
        try:
            lemma_obj = scrape_word(w)  # your scraper returns the approved JSON
            _enrich_lemma_inplace(lemma_obj)  # add labels/label_groups in memory
            l0_db.upsert_lemma(conn, lemma_obj)
            print(f"[OK] {w}   ({i}/{total})")
        except Exception as e:
            if args.retries > 0:
                ok = False
                for k in range(1, args.retries+1):
                    try:
                        lemma_obj = scrape_word(w)
                        _enrich_lemma_inplace(lemma_obj)
                        l0_db.upsert_lemma(conn, lemma_obj)
                        print(f"[OK] {w}   ({i}/{total})  after retry {k}")
                        ok = True
                        break
                    except Exception:
                        pass
                if not ok:
                    print(f"[FAIL] {w}: {e}")
            else:
                print(f"[FAIL] {w}: {e}")
        if args.sleep and i < total:
            time.sleep(args.sleep)

if __name__ == "__main__":
    main()
