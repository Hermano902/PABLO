# scripts/verify_setup.py
import os, json
import importlib

pp = importlib.import_module("pablopath")

CHECKS = {
    "THESAURUS_DIR": pp.THESAURUS_DIR,
    "sentence_rules_path": pp.sentence_rules_path,
    "phrases_clauses_path": pp.phrases_clauses_path,
    "pos_rules_path": pp.pos_rules_path,
    "word_rules_path": getattr(pp, "word_rules_path", None),   # optional but recommended
    "DICTIONARY_DIR": pp.DICTIONARY_DIR,
    "MANIFEST_DIR": pp.MANIFEST_DIR,
    "RAW_DUMPS_DIR (WM)": pp.RAW_DUMPS_DIR,
    "UNSORTED_DIR (WM)": pp.UNSORTED_DIR,
    "SORTED_DIR (WM)": pp.SORTED_DIR,
    "curiosity_path (L1)": pp.curiosity_path,
    # domain roots
    "LANG_L0_DIR": pp.LANG_L0_DIR,
    "LANG_L1_DIR": pp.LANG_L1_DIR,
    "MATH_L0_DIR": pp.MATH_L0_DIR,
    "VISION_L0_DIR": pp.VISION_L0_DIR,
    "SYSTEM_L0_DIR": pp.SYSTEM_L0_DIR,
}

def ok(p): 
    return p and (os.path.isdir(p) or os.path.isfile(p))

print("== Pablo path sanity check ==")
bad = []
for name, path in CHECKS.items():
    state = "OK " if ok(path) else "ERR"
    print(f"{state:3} {name:<22} → {path}")
    if not ok(path): bad.append((name, path))

# quick policy asserts
print("\n== Policy checks ==")
# L0 should be data-only: warn if we see .py in L0
l0_code = []
for root, _, files in os.walk(pp.LANG_L0_DIR):
    for f in files:
        if f.endswith(".py"):
            l0_code.append(os.path.join(root, f))
if l0_code:
    print("WARN: Python code found under L0 (should be data-only):")
    for p in l0_code: print("  -", p)
else:
    print("OK  L0 contains data only")

if bad:
    raise SystemExit("\nSome paths failed. Fix pablopath or folders above.")
print("\nAll good ✅")
