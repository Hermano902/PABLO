import requests
from bs4 import BeautifulSoup,Tag
import re
from typing import Dict,List, Tuple
import json
from collections import defaultdict
import os

from pablopath import UNSORTED_DIR, MANIFEST_DIR

WIKTIONARY_URL = "https://en.wiktionary.org/wiki/"

LEXICAL_POS_MAPPING = {
    "noun": "N",
    "proper noun": "N",
    "verb": "V",
    "adjective": "ADJ",
    "adverb": "ADV",
    "pronoun": "PRON",
    "preposition": "PREP",
    "conjunction": "CONJ",
    "interjection": "INTJ",
    "determiner": "DET",
    "article" : "DET",
    "numeral": "NUM",
    "particle": "PART",
    "letter": "LETTER",
}

def fetch_wiktionary_page(word: str) -> BeautifulSoup:
    """
    Fetch the live Wiktionary page for `word` and return a BeautifulSoup
    object whose root is a <section id="english-section"> containing
    everything from the Modern English <h2> down to the next <h2>.
    """
    url = f"{WIKTIONARY_URL}{word}"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch page for '{word}' (status {response.status_code})")

    full_soup = BeautifulSoup(response.text, "html.parser")
    content_div = full_soup.find("div", class_="mw-parser-output")
    if not content_div:
        return full_soup  # fallback to whole page

    # ——— Inline locator for the Modern English <h2> ———
    eng_h2 = None
    for h2 in content_div.find_all("h2"):
        if h2.get_text(strip=True).lower() == "english":
            eng_h2 = h2
            break
    if eng_h2 is None:
        raise ValueError(f"[ERROR] No English section found for '{word}'")

    # 2) If it's wrapped in a div.mw-heading2, use that as the slicing root:
    wrapper = eng_h2
    parent = eng_h2.parent
    if (
        parent.name == "div"
        and "mw-heading" in parent.get("class", [])
        and "mw-heading2" in parent.get("class", [])
    ):
        wrapper = parent

    # 3) Slice siblings of wrapper until next H2‐level marker
    buffer = []
    for sib in wrapper.next_siblings:
        # break on raw <h2> (unlikely in the new skin, but safe)
        if getattr(sib, "name", None) == "h2":
            break
        # break on the next div.mw-heading2 wrapper
        if (
            sib.name == "div"
            and "mw-heading" in sib.get("class", [])
            and "mw-heading2" in sib.get("class", [])
        ):
            break
        buffer.append(str(sib))

    # 4) Wrap & re‐parse so you get one root node for downstream parsing
    fragment_html = "<section id=\"english-section\">\n" + "".join(buffer) + "\n</section>"
    trimmed_soup = BeautifulSoup(fragment_html, "html.parser")
    return trimmed_soup

# Maps raw POS text to internal POS tag if valid
def is_valid_pos_tag(pos_text: str, valid_pos: list) -> str:
    if pos_text in valid_pos:
        return LEXICAL_POS_MAPPING.get(pos_text)
    return None


# Locates the English language section and extracts POS headers like noun, verb, etc.
def extract_pos_sections_with_etymology(
    section_soup: BeautifulSoup
) -> List[Dict]:
    """
    Returns a list of dicts, one per POS-heading under the English section,
    annotated with pos_index so repeated POS (e.g. Verb_1, Verb_2) get unique indices.
    Scans all h3-h6 tags, so it catches both Etymology (h3) and POS (often h4).
    """
    valid_raw = set(LEXICAL_POS_MAPPING.keys())
    sections   = []
    current_etym = None
    pos_counter  = defaultdict(int)

    # look at every heading from <h3> through <h6>
    for tag in section_soup.find_all(re.compile(r"^h[3-6]$")):
        # pull the visible label
        span = tag.find("span", class_="mw-headline")
        raw  = (span.text if span else tag.get_text()).strip()
        low  = raw.lower()

        # if it’s an etymology header, remember it
        if low.startswith("etymology"):
            current_etym = raw
            continue

        # normalize for matching, e.g. "proper noun"
        key = low.replace("_", " ")
        if key in valid_raw:
            pos_code = LEXICAL_POS_MAPPING[key]
            pos_counter[pos_code] += 1

            sections.append({
                "pos":        pos_code,          # e.g. "N" or "V"
                "raw_label":  raw,               # e.g. "Noun" or "Verb"
                "etymology":  current_etym,      # e.g. "Etymology 1"
                "pos_index":  pos_counter[pos_code],  # 1,2,3…
                "heading":    tag
            })

    return sections

def get_section_fragment(heading_tag: Tag) -> BeautifulSoup:
    """
    Given a POS heading (<h3>–<h6>), find the 
    <div class="mw-heading mw-headingN"> wrapper if present,
    then collect all siblings from that point until the next
    heading (div.mw-headingN or h3–h6). Return as a new soup.
    """
    # 1) Find the “true” wrapper
    wrapper = heading_tag
    parent = heading_tag.parent
    if (
        parent.name == "div"
        and "mw-heading" in parent.get("class", [])
        and any(c.startswith("mw-heading") for c in parent.get("class", []))
    ):
        wrapper = parent

    # 2) Collect everything until the next same-level wrapper or heading
    buf = []
    for sib in wrapper.next_siblings:
        # raw heading tags
        if getattr(sib, "name", None) and re.match(r"^h[3-6]$", sib.name):
            break
        # div wrapper for next heading
        if (
            sib.name == "div"
            and "mw-heading" in sib.get("class", [])
            and any(c.startswith("mw-heading") for c in sib.get("class", []))
        ):
            break
        buf.append(str(sib))

    # 3) Re-parse the fragment so we get a proper tree
    return BeautifulSoup("".join(buf), "html.parser")

# Finds and returns the IPA pronunciation if present
def extract_pronunciation(soup: BeautifulSoup) -> str:
    ipa_tag = soup.find("span", class_="IPA")
    return ipa_tag.text.strip() if ipa_tag else None
# Updated extract_structured_senses to return flat list of definitions

import datetime

# Prefer pablopath if it exposes DICT_MANIFEST_DIR; otherwise fall back to structure.json path

# ---- manifest helpers ----
def _flatten_definitions(defs: list) -> list:
    """Return a flat list of definition dicts, including nested subdefinitions."""
    flat = []
    for d in defs or []:
        flat.append(d)
        for sd in d.get("subdefinitions", []) or []:
            flat.append(sd)
    return flat


def _count_inflections(forms: dict) -> int:
    """Count how many inflection values we actually have (exclude empty/None and 'SIMPLE')."""
    try:
        inf = forms.get("FORM", {}).get("INFLECTION", {})
        if not isinstance(inf, dict):
            return 0
        return sum(1 for k, v in inf.items() if v and k.upper() != "SIMPLE")
    except Exception:
        return 0


def summarize_entry_for_manifest(entry: dict) -> dict:
    """Build one POS summary: counts + main/secondary definitions."""
    flat_defs = _flatten_definitions(entry.get("definitions", []))


    examples = sum(len(d.get("examples", []) or []) for d in flat_defs)
    synonyms = sum(len(d.get("synonyms", []) or []) for d in flat_defs)
    antonyms = sum(len(d.get("antonyms", []) or []) for d in flat_defs)

    return {
        "pos": entry.get("pos"),
        "pos_index": entry.get("pos_index"),
        "raw_label": entry.get("raw_label"),
        "etymology": entry.get("etymology"),
        "counts": {
            "inflections": _count_inflections(entry.get("forms", {})),
            "definitions": len(flat_defs),
            "examples": examples,
            "synonyms": synonyms,
            "antonyms": antonyms,
        },
    }


def build_manifest(word: str, entries: list) -> dict:
    """Assemble the manifest payload for a word."""
    pos_order = [f"{e.get('pos')}:{e.get('pos_index')}" for e in entries]
    return {
        "word": word,
        "pos_order": pos_order,
        "summary": [summarize_entry_for_manifest(e) for e in entries],
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }


def save_manifest(word: str, entries: list, out_dir: str = MANIFEST_DIR) -> str:
    """Write manifest JSON to disk and return its path."""
    os.makedirs(out_dir, exist_ok=True)
    payload = build_manifest(word, entries)
    out_path = os.path.join(out_dir, f"{word}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path

def definition_parser(ol_block) -> list:
    import re

    for ul in ol_block.find_all("ul"):
        ul.decompose()
    def clean_definition_text(text):
        text = re.sub(r"\[\d+\]", "", text)  # remove numbered refs like [1], [2]
        text = re.sub(r"{{[^{}]*}}", "", text)   # remove template syntax like {{...}}
        return text.strip()

    def extract_examples_from_li(li):
        examples = []
        for dd in li.find_all("dd"):
            if dd.find("span", class_=lambda c: c and "term" in c):
                continue
            label = dd.find("span", class_="ib-content-label")
            label_text = label.text.strip().lower() if label else ""
            if "example" in label_text:
                ex = dd.get_text(" ", strip=True).replace(label.text if label else '', '').strip()
                if ex:
                    examples.append(clean_definition_text(ex))
        for div in li.find_all("div", class_="h-usage-example"):
            for i_tag in div.find_all("i"):
                text = i_tag.get_text(" ", strip=True)
                if text:
                    examples.append(clean_definition_text(text))
        return examples

    def extract_syn_ant_from_li(li):
        synonyms, antonyms = [], []
        for dd in li.find_all("dd"):
            nyms_span = dd.find("span", class_=lambda c: c and "nyms" in c.split())
            if not nyms_span:
                continue
            relation = nyms_span.get("data-relation-class", "").lower()
            if not relation:
                classes = nyms_span.get("class", [])
                if "synonym" in classes:
                    relation = "synonym"
                elif "antonym" in classes:
                    relation = "antonym"
            entries = [
                a.get_text(" ", strip=True)
                for a in nyms_span.select("a[href]")
                if a.get("href")
                and not a.get("title", "").startswith("Thesaurus:")
                and not a.get("title", "").lower().startswith("citation:")
            ]

            if relation == "synonym":
                synonyms.extend(entries)
            elif relation == "antonym":
                antonyms.extend(entries)
        return synonyms, antonyms

    def extract_nested_ol_definitions(li):
        nested_ol = li.find("ol")
        if not nested_ol:
            return []

        subdefinitions = []
        for sub_li in nested_ol.find_all("li", recursive=False):
            sub_li.extract()  # remove sub_li from parent tree to avoid duplication
            # Decompose citation containers in sub_li
            for tag in sub_li.select(".citation-whole, .cited-source, .citation"):
                tag.decompose()
            for tag in sub_li.select("ul:has(.citation-whole), li:has(.citation-whole)"):
                tag.decompose()

            sub_examples = extract_examples_from_li(sub_li)
            sub_synonyms, sub_antonyms = extract_syn_ant_from_li(sub_li)

            for dd in sub_li.find_all("dd"):
                dd.decompose()
            for div in sub_li.find_all("div", class_="h-usage-example"):
                div.decompose()

            raw_text = sub_li.get_text(" ", strip=True)
            cleaned = clean_definition_text(raw_text)

            if cleaned:
                subdefinitions.append({
                    "definition": cleaned,
                    "examples": sub_examples,
                    "synonyms": sub_synonyms,
                    "antonyms": sub_antonyms,
                    "subdefinitions": [],
                    "senses": []
                })

        return subdefinitions
    
    def remove_all_nested_uls(li):
        for ul in li.find_all("ul", recursive=False):
            ul.decompose()

    definitions = []

    for li in ol_block.find_all("li", recursive=False):
        if li.get("class") and "mw-empty-elt" in li["class"]:
            continue

        remove_all_nested_uls(li)
        # 🔹 Remove inline superscript citation references like [1]
        for sup in li.find_all("sup"):
            sup.decompose()

        # === Decompose citation blocks that pollute definitions
        for tag in li.select(".citation-whole, .cited-source, .citation"):
            tag.decompose()

        # === Decompose citation <li> or <ul> blocks that pollute sense structure
        for tag in li.select("ul:has(.citation-whole), li:has(.citation-whole)"):
            tag.decompose()

        subdefinitions = extract_nested_ol_definitions(li)
        examples = extract_examples_from_li(li)
        synonyms, antonyms = extract_syn_ant_from_li(li)

        # Clean raw text (excluding dd/example blocks)
        for dd in li.find_all("dd"):
            dd.decompose()
        for div in li.find_all("div", class_="h-usage-example"):
            div.decompose()

        raw_text = li.get_text(" ", strip=True)
        cleaned_def = clean_definition_text(raw_text)

        if cleaned_def:
            definitions.append({
                "definition": cleaned_def,
                "examples": examples,
                "synonyms": synonyms,
                "antonyms": antonyms,
                "subdefinitions": subdefinitions,
                "senses": []
            })

    return definitions

# Gathers inflectional or comparative forms based on part of speech
def enrich_forms_by_pos(pos: str, soup: BeautifulSoup, word: str, raw_label: str) -> dict:

    forms = defaultdict(lambda: defaultdict(lambda: defaultdict(str)))

    if pos == "V":
        def extract_verbal_forms() -> dict:
            inflections = {k: None for k in ["INF", "3PSP", "PT", "PAP", "PRP", "N3PP", "GER"]}
            seen_values = set()

            for i_tag in soup.find_all("i"):
                label = i_tag.get_text(strip=True).lower()
                b_tag = i_tag.find_next_sibling("b")
                if not b_tag:
                    continue

                a_tag = b_tag.find("a")
                value = a_tag.get_text(strip=True) if a_tag else b_tag.get_text(strip=True)
                if not value:
                    continue

                if "infinitive" in label:
                    inflections["INF"] = value
                if "third-person singular" in label:
                    inflections["3PSP"] = value
                if "simple past" in label and "past participle" in label:
                    inflections["PT"] = value
                    inflections["PAP"] = value
                elif "simple past" in label:
                    inflections["PT"] = value
                elif "past participle" in label:
                    inflections["PAP"] = value
                if "present participle" in label:
                    inflections["PRP"] = value
                if "non-3rd person singular" in label:
                    inflections["N3PP"] = value
                if "gerund" in label:
                    inflections["GER"] = value

                seen_values.add(value)

            for b_tag in soup.find_all("b"):
                classes = " ".join(b_tag.get("class", []))
                a_tag = b_tag.find("a")
                value = a_tag.get_text(strip=True) if a_tag else b_tag.get_text(strip=True)
                if not value:
                    continue

                if "s-verb-form-form-of" in classes:
                    inflections["3PSP"] = value
                elif "ing-form-form-of" in classes:
                    inflections["PRP"] = value
                elif "ed-form-form-of" in classes:
                    if not inflections["PT"]:
                        inflections["PT"] = value
                    elif not inflections["PAP"] or inflections["PAP"] == inflections["PT"]:
                        inflections["PAP"] = value
                elif "infinitive-form-of" in classes:
                    inflections["INF"] = value
                elif "gerund-form-of" in classes:
                    inflections["GER"] = value
                elif "non-3rd-person-form-of" in classes:
                    inflections["N3PP"] = value
                seen_values.add(value)

            inflections["SIMPLE"] = word
            if not inflections["INF"]:
                inflections["INF"] = word

            return inflections

        forms["FORM"]["INFLECTION"] = extract_verbal_forms()
    elif pos == "N":
        if "proper" in raw_label.lower():
            forms["N.TYPE"] = "PROPER"
            return forms
        def extract_noun_forms() -> dict:
            data = {"countability": "COUNT", "plural": None, "countable_variant": False}
            seen_values = set()

            for line in soup.find_all("p"):
                txt = line.get_text().lower()
                if "uncountable and countable" in txt or "countable and uncountable" in txt:
                    data["countability"] = "BOTH"
                elif "usually uncountable" in txt or "uncountable" in txt:
                    data["countability"] = "UN"

                if "plural of" in txt:
                    match = re.search(r"plural of ([a-zA-Z]+)", txt)
                    if match:
                        value = match.group(1)
                        if value not in seen_values:
                            data["plural"] = value
                            seen_values.add(value)
                    break
                elif "plurals:" in txt or "plural" in txt:
                    match = re.findall(r"\bplural\b(?:\s+is\s+|\s+are\+)?\[\[(.*?)\]\]", txt)
                    if match:
                        value = match[0]
                        if value not in seen_values:
                            data["plural"] = value
                            seen_values.add(value)
                    break

            definition_tag = soup.find("ol")
            if definition_tag:
                first_li = definition_tag.find("li")
                if first_li:
                    first_text = first_li.get_text().lower()
                    if "(uncountable)" in first_text and data["countability"] == "BOTH":
                        data["countability"] = "UN"

            # Also scan <li> elements for plural info
            for li in soup.find_all("li"):
                txt = li.get_text().lower()
                if "plural" in txt:
                    match = re.search(r"plural:?[ 	]*\[\[(.*?)\]\]", txt)
                    if match:
                        value = match.group(1)
                        if value not in seen_values:
                            data["plural"] = value
                            seen_values.add(value)
                    break
                            # Handle <i>plural</i> followed by <b><a>plural_form</a></b>
            for i_tag in soup.find_all("i"):
                if i_tag.get_text(strip=True).lower() == "plural":
                    b_tag = i_tag.find_next_sibling("b")
                    if b_tag:
                        a_tag = b_tag.find("a")
                        if a_tag:
                            value = a_tag.get_text(strip=True)
                            if value and value not in seen_values:
                                data["plural"] = value
                                seen_values.add(value)
                    break

            # Handle uncountable nouns that accept plural variants
            if data["countability"] == "UN" and data["plural"]:
                data["countable_variant"] = True

            return data


        noun_data = extract_noun_forms()
        forms["COUNTABILITY"] = noun_data["countability"]
        if noun_data["plural"]:
            forms["FORM"]["INFLECTION"]["PL"] = noun_data["plural"]
            if noun_data["countability"] == "UN":
                forms["countable_variant"] = True
    elif pos in ["ADJ", "ADV"]:
        def extract_comparatives() -> dict:
            comp_data = {"COMP": None, "SUP": None}
            seen_values = set()

            for b_tag in soup.find_all("b"):
                classes = " ".join(b_tag.get("class", []))
                if "comparative-form-of" in classes:
                    a_tag = b_tag.find("a")
                    value = a_tag.get_text(strip=True) if a_tag else b_tag.get_text(strip=True)
                    if value:
                        if value.lower() == f"more{word.lower()}":
                            value = f"more {word}"
                        if value not in seen_values:
                            comp_data["COMP"] = value
                            seen_values.add(value)
                elif "superlative-form-of" in classes:
                    a_tag = b_tag.find("a")
                    value = a_tag.get_text(strip=True) if a_tag else b_tag.get_text(strip=True)
                    if value:
                        if value.lower() == f"most{word.lower()}":
                            value = f"most {word}"
                        if value not in seen_values:
                            comp_data["SUP"] = value
                            seen_values.add(value)

            if not comp_data["COMP"] or not comp_data["SUP"]:
                for p in soup.find_all("p"):
                    text = p.get_text().lower()
                    if "comparative" in text and "superlative" in text:
                        match = re.findall(r"comparative ([a-zA-Z]+) and superlative ([a-zA-Z]+)", text)
                        if match:
                            comp, sup = match[0]
                            if not comp_data["COMP"] and comp not in seen_values:
                                comp_data["COMP"] = comp
                                seen_values.add(comp)
                            if not comp_data["SUP"] and sup not in seen_values:
                                comp_data["SUP"] = sup
                                seen_values.add(sup)
                        break

            return comp_data

        comp_data = extract_comparatives()
        forms["FORM"]["INFLECTION"].update(comp_data)
    else:
        forms["FORM"]["INFLECTION"] = {}
        
    return forms

# Main function that builds a complete lexical entry for all detected POS tags
def scrape_word(word: str) -> List[Dict]:
    """
    Scrape all POS sections for `word`, scoping forms and definitions
    to each local POS fragment. Returns a list of entries, one per
    POS section, each with its own forms and definitions.
    """
    # 1) Fetch and slice out the English section
    sec = fetch_wiktionary_page(word).find("section", id="english-section")
    
    # 2) Extract pronunciation once per word
    ipa_tag = sec.find("span", class_="IPA")
    pronunciation = ipa_tag.text.strip() if ipa_tag else None

    entries = []
    # 3) Get every POS section with etymology and pos_index
    sections = extract_pos_sections_with_etymology(sec)

    for info in sections:
        pos       = info["pos"]
        raw_label = info["raw_label"]
        etym      = info["etymology"]
        idx       = info["pos_index"]
        heading   = info["heading"]

        # 4) Scope forms to the local POS fragment
        frag = get_section_fragment(heading)
        forms = enrich_forms_by_pos(pos, frag, word, raw_label)

         # 5) Parse definitions from the first <ol> inside this fragment
        ol = frag.find("ol")
        definitions = definition_parser(ol) if ol else []

        # >>> NEW: split into main + secondary (inside the word entry)
        main_def = definitions[0]["definition"] if definitions else None
        secondary_defs = [
            d.get("definition") for d in (definitions[1:] if len(definitions) > 1 else [])
            if d.get("definition")
        ]

        # 6) Assemble the entry
        entry = {
            "word":          word,
            "lemma":         word,
            "etymology":     etym,
            "pos":           pos,
            "raw_label":     raw_label,
            "pos_index":     idx,
            "pronunciation": pronunciation,
            "forms":         forms,
            "definitions":   definitions,              # full objects preserved
            "main_definition": main_def,               # <<< added
            "secondary_definitions": secondary_defs    # <<< added
        }
        entries.append(entry)

    return entries

# Example usage
# Script entry point: scrapes a test word and saves the result to JSON
if __name__ == "__main__":
    # 1) Specify the single word to scrape
    word = "an"

    # 2) Scrape all POS sections for this word
    entries = scrape_word(word)

    # 3) Save the raw dump (existing behavior)
    out_path = os.path.join(UNSORTED_DIR, f"{word}_wiktionary_dump.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    # 4) NEW: Save the manifest (POS order + per-POS summary and main/secondary defs)
    manifest_path = save_manifest(word, entries)

    # (Optional) print for quick visibility when running as a script
    print(f"[OK] Dump: {out_path}")
    print(f"[OK] Manifest: {manifest_path}")
