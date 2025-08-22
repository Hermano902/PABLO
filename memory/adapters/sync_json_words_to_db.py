#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse, json, re, sqlite3, sys, time, importlib.util, fnmatch, datetime
from pathlib import Path, PurePath
from typing import Any, Dict, List, Set, Iterable, Optional

# ---------- tokenization / config ----------
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{0,63}")
STOPWORDS: Set[str] = {
    "the","and","of","to","in","that","it","for","on","as","with","was","is","are","be",
    "by","an","at","from","or","this","which","but","not","have","has","had","were","their",
    "its","they","you","we","he","she","them","his","her","my","your","our","me","us",
}

def vprint(verbose: bool, *msg):
    if verbose:
        print(*msg)

# ---------- io helpers ----------
def load_json_any(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))

def load_word_list(p: Path) -> list[str]:
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(x) for x in data if str(x).strip()]
    except Exception:
        pass
    return []

def load_blacklist(p: Optional[Path]) -> Set[str]:
    if not p or not p.exists():
        return set()
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return {str(x).strip().lower() for x in data if str(x).strip()}
    except Exception:
        pass
    return {ln.strip().lower() for ln in text.splitlines() if ln.strip()}

def db_lemmas_lower(db_path: Path) -> Set[str]:
    if not db_path.exists():
        return set()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    try:
        cur.execute("SELECT lemma FROM l0_entry")
        rows = cur.fetchall()
    except sqlite3.DatabaseError:
        rows = []
    finally:
        conn.close()
    return {(r[0] or "").lower() for r in rows}

# ---------- collectors ----------
def is_word_candidate(s: str, min_len: int, max_len: int, stopwords: Set[str], use_stopwords: bool) -> bool:
    s = s.strip()
    if not s:
        return False
    if not (1 <= len(s) <= max_len):
        return False
    if len(s) < min_len:
        return False
    return not (use_stopwords and s.lower() in stopwords and s not in {"a","I"})

def collect_from_string(s: str, out: Dict[str,str], min_len: int, max_len: int, stopwords: Set[str], use_stopwords: bool):
    for tok in WORD_RE.findall(s):
        if is_word_candidate(tok, min_len, max_len, stopwords, use_stopwords):
            out.setdefault(tok.lower(), tok)

def collect_words_from_obj(obj: Any, out: Dict[str,str], min_len: int, max_len: int, stopwords: Set[str], use_stopwords: bool):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                for tok in WORD_RE.findall(k):
                    if is_word_candidate(tok, min_len, max_len, stopwords, use_stopwords):
                        out.setdefault(tok.lower(), tok)
            if isinstance(v, str):
                collect_from_string(v, out, min_len, max_len, stopwords, use_stopwords)
            elif isinstance(v, list):
                for it in v:
                    collect_words_from_obj(it, out, min_len, max_len, stopwords, use_stopwords)
            elif isinstance(v, dict):
                collect_words_from_obj(v, out, min_len, max_len, stopwords, use_stopwords)
    elif isinstance(obj, list):
        for it in obj:
            collect_words_from_obj(it, out, min_len, max_len, stopwords, use_stopwords)
    elif isinstance(obj, str):
        collect_from_string(obj, out, min_len, max_len, stopwords, use_stopwords)

def collect_words_from_obj_fast(obj: Any, out: Dict[str,str]):
    if isinstance(obj, dict):
        for k in ("lemma","word"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                out.setdefault(v.lower(), v)
        for k in ("variants","forms","alternatives","alt"):
            v = obj.get(k)
            if isinstance(v, list):
                for s in v:
                    if isinstance(s, str) and s.strip():
                        out.setdefault(s.lower(), s)
        for k, v in obj.items():
            if isinstance(k, str) and k.strip():
                out.setdefault(k.lower(), k)
            if isinstance(v, (dict, list)):
                collect_words_from_obj_fast(v, out)
    elif isinstance(obj, list):
        for it in obj:
            collect_words_from_obj_fast(it, out)

# ---------- scraper dynamic import (dataclass-safe) ----------
def load_scraper(scraper_path: Path):
    mod_name = f"wiktionary_scraper_{abs(hash(scraper_path.resolve()))}"
    spec = importlib.util.spec_from_file_location(mod_name, str(scraper_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import scraper from {scraper_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod  # register BEFORE exec_module (dataclasses needs it)
    spec.loader.exec_module(mod)  # type: ignore
    for name in ("scrape_word","_enrich_lemma_inplace","db_connect","upsert_lemma"):
        if not hasattr(mod, name):
            raise RuntimeError(f"Scraper missing required function: {name}")
    return mod

# ---------- state ----------
def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_state(state_path: Path, state: dict) -> None:
    state["last_time"] = datetime.datetime.utcnow().isoformat() + "Z"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def build_file_list(root: Path, file_glob: Optional[str]) -> List[str]:
    files = [str(p) for p in root.rglob("*.json")]
    if file_glob:
        files = [f for f in files if fnmatch.fnmatch(str(PurePath(f)), file_glob)]
    files.sort(key=lambda s: s.lower())
    return files

# ---------- batching ----------
def chunks(seq: List[str], n: int):
    if n <= 0:
        yield seq; return
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Incremental scan → scrape N new lemmas → resume next run. Skips previously failed words.")
    ap.add_argument("--json-dir", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--scraper", required=True)
    ap.add_argument("--state", default=str(Path("./sync_state.json")), help="Path to progress state JSON.")
    ap.add_argument("--out-missing", default=str(Path("./missing_words.json")))
    ap.add_argument("--out-failed",  default=str(Path("./failed_words.json")))
    ap.add_argument("--blacklist", help="Optional extra blacklist (.json or .txt).")
    ap.add_argument("--min-len", type=int, default=1)
    ap.add_argument("--max-len", type=int, default=64)
    ap.add_argument("--no-stopwords", action="store_true")
    ap.add_argument("--fast-keys-only", dest="fast_keys_only", action="store_true",
                    help="Skip full string tokenization; only obvious fields.")
    ap.add_argument("--file-glob", help="Only scan files matching this glob (e.g., *\\a*.json or */PROPN/*.json).")
    ap.add_argument("--refresh-files", dest="refresh_files", action="store_true",
                    help="Rebuild file list instead of using cached state.")
    ap.add_argument("--progress", type=int, default=1000, help="Print progress every N files.")
    ap.add_argument("--target-new", type=int, default=10, help="Stop scanning when this many NEW lemmas are found.")
    ap.add_argument("--batch-size", type=int, default=10, help="Scrape in batches of this size.")
    ap.add_argument("--sleep", type=float, default=0.5, help="Sleep between scrapes.")
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--limit-scan-files", dest="limit_scan_files", type=int, default=0,
                    help="Optional cap on files visited this run (0 = no cap).")
    ap.add_argument("--rawdir", default=str(Path("./_raw")))
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.json_dir)
    db_path = Path(args.db)
    state_path = Path(args.state)
    out_missing = Path(args.out_missing)
    out_failed  = Path(args.out_failed)
    use_stop = not args.no_stopwords

    # Load / build file list
    state = load_state(state_path)
    need_build = args.refresh_files or ("files" not in state) or (state.get("root") != str(root)) or (state.get("file_glob") != (args.file_glob or ""))
    if need_build:
        files = build_file_list(root, args.file_glob)
        state = {"version": 3, "root": str(root), "file_glob": args.file_glob or "", "files": files, "idx": 0, "runs": 0}
    else:
        files = state.get("files", [])
    idx = int(state.get("idx", 0))
    files_total = len(files)
    if idx >= files_total:
        print("[INFO] State is at end of file list. Rebuilding…")
        files = build_file_list(root, args.file_glob)
        state.update({"files": files, "idx": 0})
        idx = 0
        files_total = len(files)
    print(f"[STATE] {files_total:,} files total, resuming at index {idx:,}.")

    # DB + lists
    have = db_lemmas_lower(db_path)
    print(f"[DB] Current lemmas in DB: {len(have):,}")
    blacklist = load_blacklist(Path(args.blacklist)) if args.blacklist else set()
    if blacklist:
        print(f"[BL] Extra blacklist loaded: {len(blacklist):,} words")

    # Treat previous failures as PERMANENT SKIP
    prev_failed = load_word_list(out_failed)
    failed_prev_lower = {w.lower() for w in prev_failed}
    if prev_failed:
        print(f"[FAIL-SKIP] Loaded {len(prev_failed):,} previously failed words — they will be skipped.")

    # Scan forward until target_new collected (skipping have/blacklist/failed)
    found_map: Dict[str,str] = {}
    visited = 0
    while idx < files_total and len(found_map) < args.target_new:
        p = Path(files[idx])
        try:
            data = load_json_any(p)
        except Exception:
            idx += 1; visited += 1
            continue

        cand: Dict[str,str] = {}
        if args.fast_keys_only:
            collect_words_from_obj_fast(data, cand)
        else:
            collect_words_from_obj(data, cand, args.min_len, args.max_len, STOPWORDS, use_stop)

        # Filter to "new" words and not blacklisted or previously failed
        for low, orig in list(cand.items()):
            if low in have:
                cand.pop(low, None); continue
            if blacklist and low in blacklist:
                cand.pop(low, None); continue
            if low in failed_prev_lower:
                cand.pop(low, None); continue

        for low, orig in cand.items():
            if low not in found_map:
                found_map[low] = orig
                if len(found_map) >= args.target_new:
                    break

        visited += 1
        if args.progress and (visited % args.progress == 0):
            print(f"  … scanned {visited:,} files @ idx {idx:,} | collected {len(found_map)}/{args.target_new} new")
        idx += 1
        if args.limit_scan_files and visited >= args.limit_scan_files:
            print(f"[SCAN] Reached --limit-scan-files={args.limit_scan_files}.")
            break

    new_list = list(found_map.values())
    out_missing.parent.mkdir(parents=True, exist_ok=True)
    out_missing.write_text(json.dumps(new_list, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[MISSING] This run discovered {len(new_list)} new lemmas → {out_missing}")

    # Save state (advance past the last fully visited file)
    state["idx"] = idx
    state["runs"] = int(state.get("runs", 0)) + 1
    save_state(state_path, state)
    print(f"[STATE] Saved → {state_path} (next idx {idx:,}/{files_total:,})")

    if args.dry_run or not new_list:
        if not new_list:
            print("[NOTE] No new lemmas found this pass.")
        return

    # Scrape & upsert
    print(f"[SCRAPE] Importing scraper: {args.scraper}")
    scraper = load_scraper(Path(args.scraper))
    conn = scraper.db_connect(str(db_path))
    rawdir = Path(args.rawdir)

    failed: List[str] = []
    total = len(new_list)

    def scrape_one(w: str) -> bool:
        for attempt in range(1, args.retries + 2):
            try:
                lemma_obj = scraper.scrape_word(w, rawdir)
                scraper._enrich_lemma_inplace(lemma_obj)
                scraper.upsert_lemma(conn, lemma_obj)
                return True
            except Exception as e:
                if attempt <= args.retries:
                    time.sleep(0.6)
                    continue
                print(f"[FAIL] {w}: {e}")
                return False

    processed = 0
    for batch in chunks(new_list, args.batch_size or len(new_list)):
        for w in batch:
            ok = scrape_one(w)
            if not ok:
                failed.append(w)
            processed += 1
            if args.sleep and processed < total:
                time.sleep(args.sleep)
        print(f"[SCRAPE] Batch complete: {processed}/{total}")

    conn.close()

    # Merge previous and new failures (case-insensitive), then write
    merged_failed_map = {w.lower(): w for w in prev_failed}
    for w in failed:
        lw = w.lower()
        if lw not in merged_failed_map:
            merged_failed_map[lw] = w
    updated_failed = list(merged_failed_map.values())
    out_failed.parent.mkdir(parents=True, exist_ok=True)
    out_failed.write_text(json.dumps(updated_failed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[RESULT] Failed now: {len(updated_failed)} → {out_failed}")

    # Rewrite missing_words.json WITHOUT the failed ones (so they aren't re-scraped)
    failed_now_lower = {w.lower() for w in failed}
    successes = [w for w in new_list if w.lower() not in failed_now_lower]
    out_missing.write_text(json.dumps(successes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[RESULT] Missing (cleaned): {len(successes)} (failed removed) → {out_missing}")

if __name__ == "__main__":
    main()
