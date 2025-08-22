import requests
from bs4 import BeautifulSoup, Tag
import re
from typing import Dict, List, Tuple
import json
from collections import defaultdict
import os
import datetime
from pathlib import Path
from bisect import bisect_left

# Optional per-word label enrichment (offline pass)
try:
    from dictionary_label_enricher import enrich_dictionary as _enrich_labels_batch
except Exception:
    _enrich_labels_batch = None

# ───────────────── pablopath (use your paths exactly) ─────────────────
from pablopath import DICTIONARY_DIR, MANIFEST_DIR  # L0 dictionary tree + per-lemma manifest dir  fileciteturn5file1
try:
    # Prefer wiktionary-specific raw dump dir in WM buffers if present
    from pablopath import WM_WIKT_UNSORTED as RAW_DIR  # cognition/wm/buffers/eyes/raw_dumps/wiktionary/unsorted  fileciteturn5file6
except Exception:
    from pablopath import UNSORTED_DIR as RAW_DIR  # legacy unsorted buffer  fileciteturn5file9

# Ensure base dirs exist (no-ops if already present)
for _p in (DICTIONARY_DIR, MANIFEST_DIR, RAW_DIR):
    os.makedirs(_p, exist_ok=True)

WIKTIONARY_URL = "https://en.wiktionary.org/wiki/"

# Keep your existing POS mapping exactly
LEXICAL_POS_MAPPING: Dict[str, str] = {
    "noun": "N",
    "proper noun": "N",  # keep as N to match your foldering
    "verb": "V",
    "adjective": "ADJ",
    "adverb": "ADV",
    "pronoun": "PRON",
    "preposition": "PREP",
    "conjunction": "CONJ",
    "interjection": "INTJ",
    "determiner": "DET",
    "article": "DET",
    "numeral": "NUM",
    "particle": "PART",
    "letter": "LETTER",
}

# ───────────────── fetch & english section isolate ─────────────────
def fetch_wiktionary_page(word: str) -> BeautifulSoup:
    """
    Return a BeautifulSoup **containing only the English section** for `word`.
    Robustly finds the <h2><span class="mw-headline" id="English">English</span></h2>
    and slices content **until the next language <h2>**. Tries case variants.
    If the env var WIKT_DEBUG is set, dumps the full page and the fragment to RAW_DIR.
    """
    DEBUG = bool(os.environ.get("WIKT_DEBUG"))

    def _find_english_h2(content_div: Tag) -> Tag | None:
        # 1) Preferred: id="English" on mw-headline
        span = content_div.select_one('h2 > span.mw-headline#English')
        if span:
            return span.find_parent('h2')
        # 2) Fallback: exact text match on the mw-headline
        for sp in content_div.select('h2 > span.mw-headline'):
            if sp.get_text(strip=True) == 'English':
                return sp.find_parent('h2')
        # 3) Last resort: plain h2 whose visible text reduces to 'English'
        for h2 in content_div.find_all('h2'):
            txt = h2.get_text(" ", strip=True)
            txt = txt.replace('[edit]', '').replace('Edit', '').strip()
            if txt == 'English':
                return h2
        return None

    def _dump_debug(name: str, text: str):
        if not DEBUG:
            return
        try:
            p = Path(RAW_DIR) / f"{name}"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding='utf-8')
        except Exception:
            pass

    def _fetch_and_trim(w: str) -> BeautifulSoup | None:
        url = f"{WIKTIONARY_URL}{w}"
        r = requests.get(url, headers={"User-Agent": "PabloDictBot/1.0"})
        if r.status_code != 200:
            return None
        full = BeautifulSoup(r.text, "html.parser")
        content_div = full.find("div", class_="mw-parser-output")
        if not content_div:
            return None

        # (debug) list all language H2s
        if DEBUG:
            langs = [sp.get_text(strip=True) for sp in content_div.select('h2 > span.mw-headline')]
            print(f"[DEBUG] H2 mw-headlines for {w}: {langs}")
            _dump_debug(f"{w}_FULL.html", r.text)

        eng_h2 = _find_english_h2(content_div)
        if not eng_h2:
            return None

        # Some skins wrap the h2 in <div class="mw-heading mw-heading2">…</div>
        wrapper = eng_h2
        parent = eng_h2.parent
        if (
            parent and parent.name == "div"
            and "mw-heading" in (parent.get("class") or [])
            and "mw-heading2" in (parent.get("class") or [])
        ):
            wrapper = parent

        # Collect siblings until the next language heading (next <h2> or wrapped h2)
        buf: List[str] = []
        for sib in wrapper.next_siblings:
            name = getattr(sib, "name", None)
            if name == "h2":
                break
            if (
                name == "div"
                and "mw-heading" in (sib.get("class") or [])
                and "mw-heading2" in (sib.get("class") or [])
            ):
                break
            buf.append(str(sib))

        fragment_html = '<section id="english-section"\n>' + "".join(buf) + '<\n/section>'
        frag = BeautifulSoup(fragment_html, "html.parser")
        # Safety: if we accidentally captured a following language <h2>, drop everything from that <h2> onward
        rogue_h2 = frag.find("h2")
        if rogue_h2:
            for el in list(rogue_h2.find_all_next()):
                el.decompose()
            rogue_h2.decompose()
        return frag

    # Try variants to reach the English section that actually exists on-page
    for v in (word, word.lower(), word[:1].upper() + word[1:].lower(), word.upper()):
        trimmed = _fetch_and_trim(v)
        if trimmed is not None:
            return trimmed

    raise ValueError(f"[ERROR] No English section found for '{word}' (tried case variants)")

# ───────────────── headings → pos sections (with etym & index) ─────────────────

def extract_pos_sections_with_etymology(section_soup: BeautifulSoup) -> List[Dict]:
    """
    Returns a list of dicts, one per POS-heading under the English section,
    annotated with pos_index so repeated POS (e.g. Verb_1, Verb_2) get unique indices.
    Scans all h3-h6 tags, so it catches both Etymology (h3) and POS (often h4).
    """
    valid_raw = set(LEXICAL_POS_MAPPING.keys())
    sections: List[Dict] = []
    current_etym = None
    pos_counter = defaultdict(int)

    # look at every heading from <h3> through <h6>
    for tag in section_soup.find_all(re.compile(r"^h[3-6]$")):
        # visible label
        span = tag.find("span", class_="mw-headline")
        raw = (span.text if span else tag.get_text()).strip()
        low = raw.lower()

        # etymology headers
        if low.startswith("etymology"):
            current_etym = raw
            continue

        # normalize for matching, e.g. "proper noun"
        key = low.replace("_", " ")
        if key in valid_raw:
            pos_code = LEXICAL_POS_MAPPING[key]
            pos_counter[pos_code] += 1
            sections.append({
                "pos": pos_code,
                "raw_label": raw,
                "etymology": current_etym,
                "pos_index": pos_counter[pos_code],
                "heading": tag,
            })

    return sections

# ───────────────── section fragment after a heading ─────────────────
def get_section_fragment(heading_tag: Tag) -> BeautifulSoup:
    """
    Given a POS heading (<h3>–<h6>), find its wrapper if present and
    collect siblings until the next heading (same/higher level).
    """
    wrapper = heading_tag
    parent = heading_tag.parent
    if (
        parent.name == "div"
        and "mw-heading" in parent.get("class", [])
        and any(c.startswith("mw-heading") for c in parent.get("class", []))
    ):
        wrapper = parent

    buf: List[str] = []
    for sib in wrapper.next_siblings:
        if getattr(sib, "name", None) and re.match(r"^h[3-6]$", sib.name):
            break
        if (
            getattr(sib, "name", None) == "div"
            and "mw-heading" in sib.get("class", [])
            and any(c.startswith("mw-heading") for c in sib.get("class", []))
        ):
            break
        buf.append(str(sib))

    return BeautifulSoup("".join(buf), "html.parser")

# ───────────────── definitions parser (your current logic kept) ─────────────────
def definition_parser(ol_block) -> list:
    import re as _re

    for ul in ol_block.find_all("ul"):
        ul.decompose()

    def clean_definition_text(text):
        text = _re.sub(r"\[\d+\]", "", text)  # remove numbered refs like [1], [2]
        text = _re.sub(r"{{[^{}]*}}", "", text)   # remove template syntax like {{.}}
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
            sub_li.extract()
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
        for sup in li.find_all("sup"):
            sup.decompose()
        for tag in li.select(".citation-whole, .cited-source, .citation"):
            tag.decompose()
        for tag in li.select("ul:has(.citation-whole), li:has(.citation-whole)"):
            tag.decompose()
        subdefinitions = extract_nested_ol_definitions(li)
        examples = extract_examples_from_li(li)
        synonyms, antonyms = extract_syn_ant_from_li(li)
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

# ───────────────── forms (kept as in your file) ─────────────────
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
            # scan <p> lines for compact patterns
            for p in soup.find_all("p"):
                txt = p.get_text().lower()
                m = re.search(r"\b(present participle)\b.*?\b(past participle)\b", txt)
                if m:
                    b_tags = p.find_all("b")
                    if len(b_tags) >= 2:
                        prp = b_tags[0].get_text(strip=True)
                        pap = b_tags[1].get_text(strip=True)
                        if prp and prp not in seen_values:
                            inflections["PRP"] = prp; seen_values.add(prp)
                        if pap and pap not in seen_values:
                            inflections["PAP"] = pap; seen_values.add(pap)
            return inflections
        forms["FORM"]["INFLECTION"].update(extract_verbal_forms())
    elif pos == "N":
        def extract_noun_forms() -> dict:
            data = {"countability": "BOTH", "plural": None, "countable_variant": False}
            seen_values = set()
            for p in soup.find_all("p"):
                txt = p.get_text().lower()
                if "uncountable" in txt and "countable" not in txt:
                    data["countability"] = "UN"
                elif "countable" in txt and "uncountable" not in txt:
                    data["countability"] = "CT"
                if "plural" in txt and "[[" in txt:
                    m = re.search(r"plural:?\s*\[\[(.*?)\]\]", txt)
                    if m:
                        value = m.group(1)
                        if value not in seen_values:
                            data["plural"] = value; seen_values.add(value)
                    break
            definition_tag = soup.find("ol")
            if definition_tag:
                first_li = definition_tag.find("li")
                if first_li:
                    first_text = first_li.get_text().lower()
                    if "(uncountable)" in first_text and data["countability"] == "BOTH":
                        data["countability"] = "UN"
            for li in soup.find_all("li"):
                txt = li.get_text().lower()
                if "plural" in txt:
                    m = re.search(r"plural:?\s*\[\[(.*?)\]\]", txt)
                    if m:
                        value = m.group(1)
                        if value not in seen_values:
                            data["plural"] = value; seen_values.add(value)
                    break
            for i_tag in soup.find_all("i"):
                if i_tag.get_text(strip=True).lower() == "plural":
                    b_tag = i_tag.find_next_sibling("b")
                    if b_tag:
                        a_tag = b_tag.find("a")
                        if a_tag:
                            value = a_tag.get_text(strip=True)
                            if value and value not in seen_values:
                                data["plural"] = value; seen_values.add(value)
                    break
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
                            comp_data["COMP"] = value; seen_values.add(value)
                elif "superlative-form-of" in classes:
                    a_tag = b_tag.find("a")
                    value = a_tag.get_text(strip=True) if a_tag else b_tag.get_text(strip=True)
                    if value:
                        if value.lower() == f"most{word.lower()}":
                            value = f"most {word}"
                        if value not in seen_values:
                            comp_data["SUP"] = value; seen_values.add(value)
            if not comp_data["COMP"] or not comp_data["SUP"]:
                for p in soup.find_all("p"):
                    text = p.get_text().lower()
                    if "comparative" in text and "superlative" in text:
                        match = re.findall(r"comparative ([a-zA-Z]+) and superlative ([a-zA-Z]+)", text)
                        if match:
                            comp, sup = match[0]
                            if not comp_data["COMP"] and comp not in seen_values:
                                comp_data["COMP"] = comp; seen_values.add(comp)
                            if not comp_data["SUP"] and sup not in seen_values:
                                comp_data["SUP"] = sup; seen_values.add(sup)
                        break
            return comp_data
        comp_data = extract_comparatives()
        forms["FORM"]["INFLECTION"].update(comp_data)
    else:
        forms["FORM"]["INFLECTION"] = {}
    return forms

# ───────────────── core scrape (logic intact; only NEW fields added) ─────────────────
def scrape_word(word: str) -> List[Dict]:
    """
    Scrape all POS sections for `word`, scoping forms and definitions
    to each local POS fragment. Returns a list of entries.
    """
    sec_root = fetch_wiktionary_page(word)
    sec = sec_root.find("section", id="english-section")
    if not sec:
        raise ValueError(f"[ERROR] English section isolate failed for '{word}'")
    ipa_tag = sec.find("span", class_="IPA")
    pronunciation = ipa_tag.text.strip() if ipa_tag else None

    entries: List[Dict] = []
    sections = extract_pos_sections_with_etymology(sec)

    for info in sections:
        pos = info["pos"]
        raw_label = info["raw_label"]
        etym = info["etymology"]
        idx = info["pos_index"]
        heading = info["heading"]

        frag = get_section_fragment(heading)
        forms = enrich_forms_by_pos(pos, frag, word, raw_label)

        ol = frag.find("ol")
        definitions = definition_parser(ol) if ol else []

        # ── NEW: split into main + secondary (kept inside each entry)
        main_def = definitions[0]["definition"] if definitions else None
        secondary_defs = [d.get("definition") for d in definitions[1:] if d.get("definition")]

        entry = {
            "word": word,
            "lemma": word,
            "etymology": etym,
            "pos": pos,
            "raw_label": raw_label,
            "pos_index": idx,
            "pronunciation": pronunciation,
            "forms": forms,
            "definitions": definitions,
            "main_definition": main_def,               # NEW
            "secondary_definitions": secondary_defs    # NEW
        }
        entries.append(entry)

    return entries

# ───────────────── manifest + batch rebuild (new, additive) ─────────────────
_POS_DIRS = {"ADJ","ADV","CONJ","DET","INTJ","LETTER","N","NUM","PART","PREP","PRON","PROPN","V"}  # per structure.json  fileciteturn5file3

def _default_backup_root() -> Path:
    """Sibling to DICTIONARY_DIR, named 'dictionarybak'."""
    return Path(DICTIONARY_DIR).parent / "dictionarybak"

def _purge_lemma_files(lemma: str, backup_dir: str | None = None, backup_overwrite: bool = False):
    """Delete existing per-POS files for `lemma` before rewrite.
    If backup_dir is provided (or None → default), mirror the originals to the backup tree,
    preserving POS/filename. If a backup exists and backup_overwrite=False, keep it.
    """
    bak_root = Path(backup_dir) if backup_dir else _default_backup_root()
    base = Path(DICTIONARY_DIR)
    for pos in _POS_DIRS:
        jf = base / pos / f"{lemma}.json"
        if jf.exists():
            try:
                # Mirror backup
                dest = bak_root / jf.relative_to(base)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if (not dest.exists()) or backup_overwrite:
                    dest.write_text(jf.read_text(encoding="utf-8"), encoding="utf-8")
                    print(f"[BAK] {dest}")
                else:
                    print(f"[BAK] exists {dest}")
            except Exception as e:
                print(f"[WARN] backup failed for {jf}: {e}")
            try:
                jf.unlink()
                print(f"[PURGE] {jf}")
            except Exception as e:
                print(f"[WARN] purge failed for {jf}: {e}")

def _bucket_by_pos(entries: List[Dict]) -> Dict[str, List[Dict]]:
    buckets = defaultdict(list)
    for e in entries:
        buckets[e["pos"]].append(e)
    for pos in buckets:
        buckets[pos].sort(key=lambda x: x.get("pos_index", 1))
    return buckets

def _count_inflections(e: Dict) -> int:
    try:
        inf = e.get("forms", {}).get("FORM", {}).get("INFLECTION", {})
        return sum(1 for _, v in inf.items() if v)
    except Exception:
        return 0

def _definition_stats(plist: List[Dict]) -> Dict[str, int]:
    defs = exs = syns = ants = infl = 0
    for e in plist:
        infl += _count_inflections(e)
        dlist = e.get("definitions", []) or []
        defs += len(dlist)
        for d in dlist:
            exs += len(d.get("examples", []) or [])
            syns += len(d.get("synonyms", []) or [])
            ants += len(d.get("antonyms", []) or [])
            for sd in d.get("subdefinitions", []) or []:
                defs += 1
                exs += len(sd.get("examples", []) or [])
                syns += len(sd.get("synonyms", []) or [])
                ants += len(sd.get("antonyms", []) or [])
    return {"definitions": defs, "examples": exs, "synonyms": syns, "antonyms": ants, "inflections": infl}

def _format_pos_order(entries: List[Dict]) -> List[str]:
    seen = defaultdict(int); out = []
    for e in entries:
        p = e["pos"]; seen[p] += 1
        out.append(p if seen[p] == 1 else f"{p}:{seen[p]}")
    return out

def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_raw_dump(lemma: str, entries: List[Dict]):
    _write_json(Path(RAW_DIR) / f"{lemma}_wiktionary_dump.json", entries)

def write_pos_files(lemma: str, entries: List[Dict]):
    buckets = _bucket_by_pos(entries)
    for pos, plist in buckets.items():
        if pos not in _POS_DIRS:
            continue
        _write_json(Path(DICTIONARY_DIR) / pos / f"{lemma}.json", plist)

def build_and_save_manifest(lemma: str, entries: List[Dict]):
    buckets = _bucket_by_pos(entries)
    files_map = {pos: str((Path(DICTIONARY_DIR) / pos / f"{lemma}.json").resolve()) for pos in buckets}
    pos_summary = {pos: _definition_stats(plist) for pos, plist in buckets.items()}
    manifest = {
        "word": lemma,
        "pos_order": _format_pos_order(entries),
        "pos": pos_summary,
        "files": files_map,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    _write_json(Path(MANIFEST_DIR) / f"{lemma}.json", manifest)

def _enrich_labels_for_lemma(lemma: str, verbose: bool = False) -> bool:
    """Run dictionary_label_enricher for just this lemma, if available."""
    if _enrich_labels_batch is None:
        if verbose:
            print("[ENRICH] dictionary_label_enricher not available; skipping.")
        return False
    try:
        _enrich_labels_batch(word=lemma, write=True)
        if verbose:
            print(f"[ENRICH] labels updated for {lemma}")
        return True
    except Exception as e:
        if verbose:
            print(f"[ENRICH] failed for {lemma}: {e}")
        return False


def rebuild_word(lemma: str, enrich_labels: bool = True, enricher_verbose: bool = False):
    entries = scrape_word(lemma)
    save_raw_dump(lemma, entries)
    write_pos_files(lemma, entries)
    if enrich_labels:
        _enrich_labels_for_lemma(lemma, verbose=enricher_verbose)
    build_and_save_manifest(lemma, entries)

def _iter_lemmas_from_dictionary() -> List[str]:
    lemmas = set()
    base = Path(DICTIONARY_DIR)
    for pos in _POS_DIRS:
        pos_dir = base / pos
        if not pos_dir.exists():
            continue
        for jf in pos_dir.glob("*.json"):
            lemmas.add(jf.stem)
    return sorted(lemmas)

def _progress_path() -> Path:
    return Path(RAW_DIR) / "wiktionary_batch_progress.json"

def _save_progress(lemma: str):
    try:
        data = {"last_lemma": lemma, "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}
        p = _progress_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _load_progress() -> str | None:
    try:
        p = _progress_path()
        if not p.exists():
            return None
        with p.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj.get("last_lemma")
    except Exception:
        return None

def _find_start_index(lemmas: List[str], from_lemma: str | None, after_lemma: str | None) -> int:
    """Return the start index in `lemmas` given from/after controls (case-insensitive).
    If exact match is not found, start at the insertion point for the normalized key.
    """
    if not lemmas:
        return 0
    if from_lemma:
        key = from_lemma.lower()
        lows = [x.lower() for x in lemmas]
        try:
            return lows.index(key)  # exact match inclusive
        except ValueError:
            # insertion point
            idx = bisect_left(lows, key)
            return max(0, min(idx, len(lemmas)))
    if after_lemma:
        key = after_lemma.lower()
        lows = [x.lower() for x in lemmas]
        try:
            return lows.index(key) + 1  # exclusive
        except ValueError:
            idx = bisect_left(lows, key)
            return max(0, min(idx, len(lemmas)))
    return 0

def rebuild_entire_dictionary(from_lemma: str | None = None,
                             after_lemma: str | None = None,
                             resume: bool = False,
                             progress: bool = False,
                             purge_first: bool = False,
                             backup_dir: str | None = None,
                             backup_overwrite: bool = False,
                             enrich_labels: bool = True,
                             enricher_verbose: bool = False):
    # resolve resume -> from_lemma if no explicit start provided
    if resume and not from_lemma and not after_lemma:
        last = _load_progress()
        if last:
            from_lemma = last
    lemmas = _iter_lemmas_from_dictionary()
    start_idx = _find_start_index(lemmas, from_lemma, after_lemma)
    total = len(lemmas)
    for i, lemma in enumerate(lemmas[start_idx:], start_idx + 1):
        try:
            if purge_first:
                _purge_lemma_files(lemma, backup_dir=backup_dir, backup_overwrite=backup_overwrite)
            rebuild_word(lemma, enrich_labels=enrich_labels, enricher_verbose=enricher_verbose)
            if progress:
                _save_progress(lemma)
        except Exception as e:
            print(f"[{i}/{total}] {lemma}: ERROR {e}")
        else:
            print(f"[{i}/{total}] {lemma}: OK")

# ───────────────── CLI ─────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", type=str, help="Rebuild just one lemma")
    ap.add_argument("--all", action="store_true", help="Rebuild the entire dictionary")
    ap.add_argument("--from", dest="from_lemma", type=str, help="Start from this lemma (inclusive)")
    ap.add_argument("--after", dest="after_lemma", type=str, help="Start after this lemma (exclusive)")
    ap.add_argument("--resume", action="store_true", help="Resume from last saved progress in RAW_DIR")
    ap.add_argument("--progress", action="store_true", help="Save progress after each lemma")
    ap.add_argument("--debug", action="store_true", help="Dump English fragment/full HTML to RAW_DIR and print H2 list")
    ap.add_argument("--purge-first", action="store_true", help="Delete existing POS files for lemma(s) before writing")
    ap.add_argument("--backup-dir", type=str, help="Mirror purged files to this backup root (default: sibling 'dictionarybak')")
    ap.add_argument("--backup-overwrite", action="store_true", help="Overwrite existing backup files in backup dir")
    ap.add_argument("--no-enrich", action="store_true", help="Do NOT run label enricher after each lemma")
    ap.add_argument("--enricher-verbose", action="store_true", help="Verbose logging for per-word label enrichment")
    args = ap.parse_args()

    # optional debug: set env var for fetch_wiktionary_page
    if args.debug:
        os.environ["WIKT_DEBUG"] = "1"

    if args.word:
        if args.purge_first:
            _purge_lemma_files(args.word, backup_dir=args.backup_dir, backup_overwrite=args.backup_overwrite)
        rebuild_word(args.word, enrich_labels=(not args.no_enrich), enricher_verbose=args.enricher_verbose)
    elif args.all:
        rebuild_entire_dictionary(from_lemma=args.from_lemma,
                                  after_lemma=args.after_lemma,
                                  resume=args.resume,
                                  progress=args.progress,
                                  purge_first=args.purge_first,
                                  backup_dir=args.backup_dir,
                                  backup_overwrite=args.backup_overwrite,
                                  enrich_labels=(not args.no_enrich),
                                  enricher_verbose=args.enricher_verbose)
    else:
        # default: simple demo raw dump so you can sanity-check quickly
        demo = "an"
        entries = scrape_word(demo)
        out_path = Path(RAW_DIR) / f"{demo}_wiktionary_dump.json"
        _write_json(out_path, entries)
        print(f"Demo raw dump → {out_path}")
