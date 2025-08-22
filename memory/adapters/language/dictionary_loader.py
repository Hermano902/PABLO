import os
import json
from typing import Dict

def load_dictionary(DICTIONARY_DIR: str) -> Dict[str, Dict[str, dict]]:
    full_dict: Dict[str, Dict[str, dict]] = {}
    print(f"[DEBUG] Loading dictionary from: {DICTIONARY_DIR}")

    for pos_folder in os.listdir(DICTIONARY_DIR):
        pos_path = os.path.join(DICTIONARY_DIR, pos_folder)
        if not os.path.isdir(pos_path):
            continue

        for fname in os.listdir(pos_path):
            if not fname.endswith(".json"):
                continue

            lemma = fname[:-5].lower()
            with open(os.path.join(pos_path, fname), "r", encoding="utf-8") as f:
                entry = json.load(f)

            # Flatten definitions across all variants
            all_defs = []
            for v in entry.get("variants", []):
                all_defs.extend(v.get("definitions", []))
            entry["_flattened_definitions"] = all_defs

            # Register under lemma
            full_dict.setdefault(lemma, {})[pos_folder.upper()] = entry
            # Register under each inflected form as before
            for v in entry.get("variants", []):
                inflections = v.get("forms", {}) \
                                .get("FORM", {}) \
                                .get("INFLECTION", {})
                for form in inflections.values():
                    if isinstance(form, str) and form:
                        full_dict.setdefault(form.lower(), {})[pos_folder.upper()] = entry

    print(f"[DEBUG] Loaded {len(full_dict)} word_forms from dictionary.")
    return full_dict
