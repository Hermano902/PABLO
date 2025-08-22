import os
import json
from collections import defaultdict
from pablopath import MANIFEST_DIR, SORTED_DIR, UNSORTED_DIR, DICTIONARY_DIR

# Windows‐reserved names need a suffix if they occur as filenames
RESERVED_WINDOWS_NAMES = {
    "con", "prn", "aux", "nul", "com1", "com2", "lpt1", "lpt2"
}

def save_entry(entry: dict, output_dir: str):
    """
    Merge one POS‐section entry into its JSON file under
    output_dir/<lemma>.json, preserving a 'variants' list.
    """
    os.makedirs(output_dir, exist_ok=True)
    # Determine the “base” lemma: use the INF slot if present (e.g. run ← running)
    inflections = entry.get("forms", {}) \
                    .get("FORM", {}) \
                    .get("INFLECTION", {})
    base = inflections.get("INF", entry["lemma"]) or entry["lemma"]
    raw = base.lower()
    fname = f"{raw}_lex" if raw in RESERVED_WINDOWS_NAMES else raw
    path = os.path.join(output_dir, f"{fname}.json")

    # Load or initialize
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                container = json.load(f)
        except json.JSONDecodeError:
            container = {
                "word": entry["word"],
                "lemma": entry["lemma"],
                "pos": entry["pos"],
                "variants": []
            }
    else:
        container = {
            "word": entry["word"],
            "lemma": entry["lemma"],
            "pos": entry["pos"],
            "variants": []
        }

    # Build a new “variant” for this section
    variant = {
        "etymology":     entry.get("etymology"),
        "pos_index":     entry.get("pos_index"),
        "forms":         entry.get("forms", {}),
        "pronunciation": entry.get("pronunciation", ""),
        "definitions":   entry.get("definitions", [])
    }

    # Dedupe identical definitions
    existing_defs = [v["definitions"] for v in container["variants"]]
    if variant["definitions"] in existing_defs:
        print(f"[DEBUG] Skipping duplicate variant for {fname}")
    else:
        container["variants"].append(variant)

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        json.dump(container, f, indent=2, ensure_ascii=False)


def sort_wiktionary_dumps(dump_dir: str, out_dir: str):
    """
    Process each <word>_wiktionary_dump.json in dump_dir (a list of entries),
    writing each entry into out_dir/<POS>/<lemma>.json via save_entry(),
    then move the processed dump into dump_dir/sorted/.
    """
    sorted_dir = SORTED_DIR

    for fname in os.listdir(dump_dir):
        if not fname.endswith("_wiktionary_dump.json"):
            continue
        path = os.path.join(dump_dir, fname)

        # Load the LIST of POS‐section entries
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)

         # Each entry → per-POS (or PROPN) save
        for entry in entries:
            # if this was a Proper noun, override the POS folder
            raw_label = entry.get("raw_label","").lower()
            if raw_label == "proper noun":
                pos_folder = "PROPN"       # or "ProperNoun"
            else:
                pos_folder = entry["pos"]

            pos_dir = os.path.join(out_dir, pos_folder)
            save_entry(entry, pos_dir)

        # Archive the dump
        os.remove(path)


def build_manifest(dict_dir: str):
    manifest = []
    for pos in os.listdir(dict_dir):
        pos_dir = os.path.join(dict_dir, pos)
        if not os.path.isdir(pos_dir):
            continue
        for fname in os.listdir(pos_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(pos_dir, fname)
            container = json.load(open(path, encoding="utf-8"))
            lemma    = container.get("lemma", fname[:-5])

            for variant in container.get("variants", []):
                # grab the full INFLECTION dict (might be empty)
                forms = variant.get("forms", {}).get("FORM", {}).get("INFLECTION", {})
                total_slots = len(forms)                   # e.g. 7 possible slots
                filled = {k: v for k, v in forms.items() if v}
                non_empty = len(filled)                    # e.g. 5 actually filled

                manifest.append({
                    "path":             os.path.relpath(path, start=dict_dir),
                    "lemma":            lemma,
                    "pos":              container["pos"],
                    "pos_index":        variant.get("pos_index"),
                    "etymology":        variant.get("etymology"),
                    "definition_count": len(variant.get("definitions", [])),
                    "example_count":    sum(len(d.get("examples", []))
                                            for d in variant.get("definitions", [])),
                    "form_slots":       total_slots,        # total fields scanned
                    "filled_slots":     non_empty,         # how many non‐empty
                })

    manifest_path = dict_dir + "/manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

def build_pos_manifests(dict_dir: str, manifest_dir: str):
    """
    Read the full manifest at dict_dir/manifest.json, 
    then write one file per POS code under manifest_dir.
    """
    full_path = os.path.join(dict_dir, "manifest.json")
    with open(full_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    # Group entries by POS
    by_pos = defaultdict(list)
    for e in entries:
        by_pos[e["pos"]].append(e)


    # Write one file per POS
    for pos, items in by_pos.items():
        out_file = os.path.join(manifest_dir, f"{pos}.json")
        with open(out_file, "w", encoding="utf-8") as fout:
            json.dump(items, fout, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Adjust these to your project layout

    sort_wiktionary_dumps(UNSORTED_DIR, DICTIONARY_DIR)
    build_manifest(DICTIONARY_DIR)
    build_pos_manifests(DICTIONARY_DIR, MANIFEST_DIR)
