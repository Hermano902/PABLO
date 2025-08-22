from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path

def read_state_idx(state: Path) -> tuple[int,int]:
    if not state.exists(): return (0, 0)
    try:
        s = json.loads(state.read_text(encoding="utf-8"))
        files = s.get("files") or []
        return int(s.get("idx", 0)), len(files)
    except Exception:
        return (0, 0)

def read_count(path: Path) -> int:
    try:
        return len(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return 0

def main():
    ap = argparse.ArgumentParser(description="Loop sync_json_words_to_db until no more new lemmas.")
    ap.add_argument("--script", required=True, help="Path to sync_json_words_to_db.py")
    ap.add_argument("--json-dir", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--scraper", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out-missing", required=True)
    ap.add_argument("--out-failed", required=True)
    ap.add_argument("--target-new", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--fast-keys-only", action="store_true")
    ap.add_argument("--no-stopwords", action="store_true")
    ap.add_argument("--progress", type=int, default=2000)
    ap.add_argument("--rawdir", default=str(Path("./_raw")))
    args = ap.parse_args()

    while True:
        idx_before, total = read_state_idx(Path(args.state))
        cmd = [
            sys.executable, args.script,
            "--json-dir", args.json_dir,
            "--db", args.db,
            "--scraper", args.scraper,
            "--state", args.state,
            "--out-missing", args.out_missing,
            "--out-failed", args.out_failed,
            "--target-new", str(args.target_new),
            "--batch-size", str(args.batch_size),
            "--sleep", str(args.sleep),
            "--retries", str(args.retries),
            "--progress", str(args.progress),
            "--rawdir", args.rawdir,
        ]
        if args.fast_keys_only: cmd.append("--fast-keys-only")
        if args.no_stopwords:   cmd.append("--no-stopwords")

        rc = subprocess.run(cmd).returncode
        if rc != 0:
            print(f"[loop] pass failed with exit code {rc}", file=sys.stderr)
            sys.exit(rc)

        new_count = read_count(Path(args.out_missing))
        idx_after, total_after = read_state_idx(Path(args.state))
        total = total_after or total

        print(f"[loop] pass: new={new_count} idx {idx_before}->{idx_after} / {total}")

        if new_count == 0 and (total and idx_after >= total):
            print("[loop] done (no new lemmas and reached end).")
            break
        if new_count == 0 and idx_after == idx_before:
            print("[loop] done (no new lemmas and no progress).")
            break

        time.sleep(1.0)

if __name__ == "__main__":
    main()
