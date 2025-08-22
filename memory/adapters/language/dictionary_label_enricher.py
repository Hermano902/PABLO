"""
Dictionary Label Enricher — FLAT LABELS (L0)
-------------------------------------------
Offline post-processor for per-POS dictionary JSON files.

For each definition/subdefinition:
- Pull *leading* parenthetical groups (e.g., "(transitive, obsolete)").
- Tokenize them minimally into a `labels` **array** (preserve original case).
- Keep the original groups in `label_groups`.
- Capture *trailing* bracket notes into `dating_raw` (e.g., "[mid 16th – early 19th c.]").
- Optionally remove these from the visible gloss (default).

Idempotent: if `labels` already exists (list), we leave it unless `--overwrite`.

Usage:
  # Dry-run (see what would change)
  python dictionary_label_enricher.py

  # Write in place (with .bak backups)
  python dictionary_label_enricher.py --write --backup

  # Only verbs; start from a lemma
  python dictionary_label_enricher.py --pos V --from acclaim --write

  # Keep the text in the gloss (don't strip the parentheses/brackets)
  python dictionary_label_enricher.py --keep-in-gloss --write
"""
from __future__ import annotations

import json, re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Iterable
from dataclasses import dataclass
from collections import defaultdict
from bisect import bisect_left
import copy, json
from pablopath import DICTIONARY_DIR

POS_DIRS = {"ADJ","ADV","CONJ","DET","INTJ","LETTER","N","NUM","PART","PREP","PRON","PROPN","V"}

# ---------------------- label extraction (flat) ----------------------
_LEAD_PAREN_RE = re.compile(r"^\(\s*([^)]*?)\s*\)\s*")
_TRAIL_BRACKET_RE = re.compile(r"\s*\[([^\]]+)\]\s*$")
_SPLIT_RE = re.compile(r"\s*(?:,|;|/|\band\b)\s*", re.IGNORECASE)

def _extract_leading_groups(text: str) -> Tuple[str, List[str]]:
    """Repeatedly strip leading '( ... )' groups; return (rest, groups)."""
    rest = text.strip()
    groups: List[str] = []
    while True:
        m = _LEAD_PAREN_RE.match(rest)
        if not m: break
        groups.append(m.group(1))
        rest = rest[m.end():]
    return rest, groups

def _extract_trailing_bracket(text: str) -> Tuple[str, Optional[str]]:
    """Strip one trailing '[ ... ]' from the end; return (rest, dating_raw)."""
    m = _TRAIL_BRACKET_RE.search(text)
    if not m:
        return text, None
    rest = text[:m.start()].rstrip()
    return rest, m.group(1).strip()

def _tokenize_groups(groups: List[str]) -> List[str]:
    """Turn groups into a flat list of labels, preserving original case."""
    tokens: List[str] = []
    for g in groups:
        parts = [p.strip() for p in _SPLIT_RE.split(g) if p.strip()]
        tokens.extend(parts if parts else [g.strip()])
    return tokens

def _enrich_def_obj_in_place(d: Dict, remove_from_gloss: bool, overwrite: bool) -> Dict:
    # Skip if already enriched and not overwriting
    already_list = isinstance(d.get("labels"), list)
    if already_list and not overwrite:
        # still recurse into subdefs
        if d.get("subdefinitions"):
            d["subdefinitions"] = [_enrich_def_obj_in_place(sd, remove_from_gloss, overwrite) for sd in d["subdefinitions"]]
        return d

    raw = (d.get("definition") or "").strip()
    if not raw:
        if d.get("subdefinitions"):
            d["subdefinitions"] = [_enrich_def_obj_in_place(sd, remove_from_gloss, overwrite) for sd in d["subdefinitions"]]
        return d

    # 1) peel off leading parens, 2) peel off trailing bracket
    after_groups, groups = _extract_leading_groups(raw)
    after_bracket, dating_raw = _extract_trailing_bracket(after_groups)
    tokens = _tokenize_groups(groups)

    # Assign fields
    if tokens:
        d["labels"] = tokens   # <<—— L0 flat labels (preferred key)
        d["label_groups"] = groups if len(groups) > 1 else (groups[0] if groups else None)
    if dating_raw:
        d["dating_raw"] = dating_raw

    if remove_from_gloss and (groups or dating_raw):
        d["definition"] = after_bracket

    # Recurse into subdefs
    if d.get("subdefinitions"):
        d["subdefinitions"] = [_enrich_def_obj_in_place(sd, remove_from_gloss, overwrite) for sd in d["subdefinitions"]]
    return d

# ---------------------- file iteration & IO ----------------------
def _normalize_payload(obj, path: Path):
    """
    Return (entries_list, rehydrate_fn) for list/dict payloads or (None, None) if unknown.
    - list[entry]            -> (list, lambda lst: lst)
    - dict single entry      -> ([entry], lambda lst: lst[0] if lst else obj)
    - dict with 'entries'    -> (obj['entries'],  lambda lst: {**base, 'entries': lst})
    - dict with 'variants'   -> (obj['variants'], lambda lst: {**base, 'variants': lst})
    """
    if isinstance(obj, list):
        return obj, (lambda lst: lst)

    if isinstance(obj, dict):
        # single entry?
        if "definitions" in obj and "pos" in obj:
            return [obj], (lambda lst: (lst[0] if lst else obj))

        # wrapper with 'entries'
        if isinstance(obj.get("entries"), list):
            base = obj
            return base["entries"], (lambda lst: {**base, "entries": lst})

        # wrapper with 'variants' (PROPN/N shapes)
        if isinstance(obj.get("variants"), list):
            base = obj
            return base["variants"], (lambda lst: {**base, "variants": lst})

    print(f"[SKIP] {path}: unrecognized payload shape ({type(obj).__name__})")
    return None, None

def _iter_lemma_files(pos_dirs: Iterable[str]) -> Iterable[Tuple[str, Path]]:
    base = Path(DICTIONARY_DIR)
    for pos in pos_dirs:
        pdir = base / pos
        if not pdir.exists():
            continue
        for jf in pdir.glob("*.json"):
            yield jf.stem, jf
  # at top with other imports

def _default_backup_root() -> Path:
    # Sibling to DICTIONARY_DIR, named 'dictionarybak'
    return Path(DICTIONARY_DIR).parent / "dictionarybak"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _dump(path: Path, obj):
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def _collect_lemmas(pos: Optional[List[str]], word: Optional[str]) -> List[Tuple[str, Path]]:
    pos_set = set(pos) if pos else POS_DIRS
    items = list(_iter_lemma_files(pos_set))
    if word:
        wlow = word.lower()
        items = [it for it in items if it[0].lower() == wlow]
    items.sort(key=lambda t: t[0].lower())
    return items

def _find_start_index(items: List[Tuple[str, Path]], from_lemma: Optional[str], after_lemma: Optional[str]) -> int:
    if not items: return 0
    keys = [x[0].lower() for x in items]
    if from_lemma:
        key = from_lemma.lower()
        try: return keys.index(key)
        except ValueError: return bisect_left(keys, key)
    if after_lemma:
        key = after_lemma.lower()
        try: return keys.index(key) + 1
        except ValueError: return bisect_left(keys, key)
    return 0

@dataclass
class Stats:
    files_seen: int = 0
    files_changed: int = 0
    defs_changed: int = 0

def enrich_dictionary(pos: Optional[List[str]] = None,
                      word: Optional[str] = None,
                      from_lemma: Optional[str] = None,
                      after_lemma: Optional[str] = None,
                      write: bool = False,
                      backup: bool = False,
                      keep_in_gloss: bool = False,
                      overwrite: bool = False,
                      verbose: bool = False,
                      backup_dir: Optional[str] = None,
                      backup_overwrite: bool = False) -> Stats:
    items = _collect_lemmas(pos, word)
    start = _find_start_index(items, from_lemma, after_lemma)
    items = items[start:]

    if verbose:
        try:
            from pablopath import DICTIONARY_DIR as _DDIR
        except Exception:
            _DDIR = "<unknown DICTIONARY_DIR>"
        print(f"[INFO] matched {len(items)} file(s) under { _DDIR }")

    stats = Stats()
    for lemma, jf in items:
        stats.files_seen += 1
        try:
            data = _load(jf)
        except Exception as e:
            print(f"[SKIP] {jf}: read error: {e}")
            continue

        entries, rehydrate = _normalize_payload(data, jf)
        if entries is None:
            continue

        changed = False
        local_defs_changed = 0

        for entry in entries:
            defs = entry.get("definitions") or []
            if not defs:
                continue

            # snapshot BEFORE
            before = json.dumps(defs, ensure_ascii=False, sort_keys=True)

        # enrich on deep copies (avoid in-place mutation of 'defs')
            new_defs = [
            _enrich_def_obj_in_place(copy.deepcopy(d), not keep_in_gloss, overwrite)
            for d in defs
            ]

        # snapshot AFTER
        after = json.dumps(new_defs, ensure_ascii=False, sort_keys=True)

        if after != before:
            entry["definitions"] = new_defs
            changed = True
            # rough per-def difference count
            local_defs_changed += sum(
                1 for a, b in zip(defs, new_defs)
                if json.dumps(a, ensure_ascii=False, sort_keys=True)
                != json.dumps(b, ensure_ascii=False, sort_keys=True)
            ) or 1  # at least 1 if structure changed (len etc.)

        if changed:
            stats.files_changed += 1
            stats.defs_changed += local_defs_changed or 1
            if write:
        # ── Mirror backup into dictionarybak/… (or custom --backup-dir)
                if backup or backup_dir:
                    try:
                        bak_root = Path(backup_dir) if backup_dir else _default_backup_root()
                        rel_path = jf.relative_to(Path(DICTIONARY_DIR))
                        bak_file = bak_root / rel_path
                        bak_file.parent.mkdir(parents=True, exist_ok=True)
                        if not bak_file.exists() or backup_overwrite:
                            # copy original BEFORE we overwrite jf
                            bak_file.write_text(jf.read_text(encoding="utf-8"), encoding="utf-8")
                            print(f"[BAK] {bak_file}")
                        else:
                            print(f"[BAK] exists {bak_file} (use --backup-overwrite to replace)")
                    except Exception as e:
                        print(f"[WARN] backup failed for {jf}: {e}")
                try:
                    _dump(jf, rehydrate(entries))   # write back in the original shape
                    print(f"[WRITE] {jf}")
                except Exception as e:
                    print(f"[ERROR] write failed for {jf}: {e}")
            else:
                print(f"[DRY] would write {jf}")
        else:
            if not write and verbose:
                print(f"[DRY] unchanged {jf}")
    return stats

# ---------------------- CLI ----------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Offline enrichment: add flat labels array to definitions.")
    ap.add_argument("--pos", nargs="*", help="Restrict to these POS (e.g., V N ADJ)")
    ap.add_argument("--word", type=str, help="Only this lemma")
    ap.add_argument("--from", dest="from_lemma", type=str, help="Start from this lemma (inclusive)")
    ap.add_argument("--after", dest="after_lemma", type=str, help="Start after this lemma (exclusive)")
    ap.add_argument("--write", action="store_true", help="Apply changes (otherwise dry-run)")
    ap.add_argument("--backup", action="store_true", help="Write .bak backups before saving")
    ap.add_argument("--keep-in-gloss", action="store_true", help="Keep parentheses/brackets in definition text")
    ap.add_argument("--overwrite", action="store_true", help="Recompute labels even if already present")
    ap.add_argument("--verbose", action="store_true", help="Print unchanged files in dry-run")
    ap.add_argument("--backup-dir", type=str, help="Root folder for mirrored backups (preserves POS/file structure). Default: <DICTIONARY_DIR>/../dictionarybak")
    ap.add_argument("--backup-overwrite", action="store_true", help="Overwrite existing backup files in the backup dir")
    args = ap.parse_args()

    stats = enrich_dictionary(pos=args.pos,
                              word=args.word,
                              from_lemma=args.from_lemma,
                              after_lemma=args.after_lemma,
                              write=args.write,
                              backup=args.backup,
                              keep_in_gloss=args.keep_in_gloss,
                              overwrite=args.overwrite,
                              verbose=args.verbose,
                              backup_dir=args.backup_dir,
                              backup_overwrite=args.backup_overwrite)
    mode = "WRITE" if args.write else "DRY"
    print(f"[{mode}] files_seen={stats.files_seen} files_changed={stats.files_changed} defs_changed={stats.defs_changed}")