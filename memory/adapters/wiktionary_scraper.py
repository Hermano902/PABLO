#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Fully-patched Wiktionary scraper (English-only) with SQLite output.

- Wrapper-safe heading detection (handles <div class="mw-heading">).
- Subdefinitions captured (1.1, 1.2, ...), kept separate from main-sense examples.
- Examples cleaned (citations stripped, punctuation normalized), deduped, lemma highlighted with « ».
- POS mapping per spec; PROPN for proper noun; LETTER kept.
- Verb forms exported to concept tags ONLY: 1PSP,2PSP,3PSP,PLSP,1PST,2PST,3PST,PLPT,SIMPLE,PAP,PRP,INF,GER.
  * Only values explicitly present on the head paragraph are filled.
  * "simple past (and past participle) X" fills 1PST/2PST/3PST/PLPT (and PAP when stated).
- ADJ/ADV degrees read from the head <p> (comparative/superlative), robust stop tokens.
- Noun plural read from head <p>.
- Label enrichment: leading parentheses → labels + label_groups, removed from gloss text.
- SQLite schema: l0_entry, l0_variant, l0_def (+FTS), l0_def_label, l0_example, l0_forms_*.

Usage examples (PowerShell):
  python G:\PABLO\tools\wiktionary_scraper.py --word do --db G:\PABLO\l0.sqlite3 --no-files --debug --pos-dump --rawdir G:\PABLO\_raw
  python G:\PABLO\tools\wiktionary_scraper.py --list G:\PABLO\words.txt --db G:\PABLO\l0.sqlite3 --sleep 0.6
"""

from __future__ import annotations
import os, re, time, json, argparse, sys, hashlib, sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, Tag

WIKTIONARY_URL = "https://en.wiktionary.org/wiki/"
USER_AGENT = "PabloDictBot/1.0 (+https://example.invalid)"
DEFAULT_RAWDIR = Path("./_raw")

# ===== POS mapping per your spec =====
POS_HEADINGS = {
    "noun": "N",
    "proper noun": "PROPN",
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

# === verb concept tags (only these are emitted) ===
VERB_CONCEPTS = [
    "1PSP","2PSP","3PSP","PLSP",
    "1PST","2PST","3PST","PLPT",
    "SIMPLE","PAP","PRP","INF","GER",
]

# ---- flags / debug ----
DBG = False
POS_DUMP = False
INCLUDE_EXAMPLES = True

def dprint(*msg):
    if DBG:
        print("[DBG]", *msg, file=sys.stderr)

def dump_text(rawdir: Path, name: str, text: str):
    if not (DBG or os.environ.get("WIKT_DEBUG")):
        return
    rawdir.mkdir(parents=True, exist_ok=True)
    (rawdir / name).write_text(text, encoding="utf-8")

# ---------- heading blocks (wrapper-safe) ----------
@dataclass
class HeadingBlock:
    level: int          # 2..6
    node: Tag           # wrapper or bare heading
    text: str
    span_id: Optional[str]

def iter_heading_blocks(root: Tag, levels=(2,3,4,5,6)):
    for el in root.find_all(["div","h2","h3","h4","h5","h6"], recursive=True):
        if el.name == "div" and "mw-heading" in (el.get("class") or []):
            h = el.find(re.compile(r"^h[2-6]$"), recursive=False)
            if not isinstance(h, Tag):
                continue
            lvl = int(h.name[1])
            if lvl not in levels:
                continue
            span = h.find("span", class_="mw-headline")
            text = (span.get_text(" ", strip=True) if span else h.get_text(" ", strip=True)).strip()
            span_id = span.get("id") if span else None
            yield HeadingBlock(lvl, el, text, span_id)
        elif el.name and re.fullmatch(r"h[2-6]", el.name):
            if el.parent and el.parent.name == "div" and "mw-heading" in (el.parent.get("class") or []):
                continue
            lvl = int(el.name[1])
            if lvl not in levels:
                continue
            span = el.find("span", class_="mw-headline")
            text = (span.get_text(" ", strip=True) if span else el.get_text(" ", strip=True)).strip()
            span_id = span.get("id") if span else None
            yield HeadingBlock(lvl, el, text, span_id)

def slice_between_blocks(start: HeadingBlock,
                         end: Optional[HeadingBlock],
                         stop_levels: set[int],
                         purge_levels: set[int]) -> BeautifulSoup:
    buf, nodes = [], 0
    for sib in start.node.next_siblings:
        if end is not None and sib is end.node:
            break
        name = getattr(sib, "name", None)
        if name and re.fullmatch(r"h([2-6])", name):
            lvl = int(name[1])
            if lvl in stop_levels:
                break
        if name == "div" and "mw-heading" in (sib.get("class") or []):
            h = sib.find(re.compile(r"^h[2-6]$"), recursive=False)
            if h:
                lvl = int(h.name[1])
                if lvl in stop_levels:
                    break
        buf.append(str(sib)); nodes += 1

    html = "<section id='slice'>" + "".join(buf) + "</section>"
    frag = BeautifulSoup(html, "html.parser")

    for lvl in sorted(purge_levels):
        rogue = frag.find(f"h{lvl}")
        while rogue:
            for el in list(rogue.find_all_next()):
                el.decompose()
            rogue.decompose()
            rogue = frag.find(f"h{lvl}")

    dprint(f"[slice_between_blocks] kept_nodes={nodes}, bytes={len(html.encode('utf-8'))}")
    return frag

def get_content_div(soup: BeautifulSoup) -> Optional[Tag]:
    return soup.find("div", class_="mw-parser-output")

def find_english_block(content_div: Tag) -> Tuple[Optional[HeadingBlock], Optional[HeadingBlock], List[str]]:
    blocks = list(iter_heading_blocks(content_div, levels=(2,)))
    langs = [b.text for b in blocks]
    dprint(f"H2 language blocks: {langs}")
    eng = None
    for b in blocks:
        if (b.span_id == "English") or (b.text.strip() == "English"):
            eng = b
            break
    nxt = None
    if eng:
        idx = blocks.index(eng)
        nxt = blocks[idx+1] if idx+1 < len(blocks) else None
        dprint(f"English block found at index {idx}. Next H2 block: {'yes' if nxt else 'none'}")
    return eng, nxt, langs

# --- POS header order (fast path: headings only) -----------------------------

def extract_pos_header_order_from_english(eng: BeautifulSoup):
    """
    Returns:
      raw_rows: [(header_idx, header_text, mapped_tag_or_None), ...]
      order:    [mapped_tag, ...] first occurrence per POS, deduped, page order
    """
    raw_rows, order = [], []
    idx = 0
    for b in iter_heading_blocks(eng, levels=(3,4)):   # only h3/h4 inside English
        t  = (b.text or "").strip()
        tl = t.lower()
        # skip non-POS headings you don’t want in order
        if tl.startswith("etymology"):       # multiple etymologies
            continue
        if tl in {"pronunciation", "alternative forms", "alternative form"}:
            continue

        tag = is_pos_from_block(b)           # maps via POS_HEADINGS
        raw_rows.append((idx, t, tag))
        if tag and tag not in order:
            order.append(tag)
        idx += 1
    return raw_rows, order


def upsert_lemma_pos_order(conn: sqlite3.Connection, lemma_text: str,
                           raw_rows, order, lang="en", source="wiktionary"):
    cur = conn.cursor()
    # Ensure needed tables exist
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS LEMMA_POS_HEADER_RAW (
      raw_id     INTEGER PRIMARY KEY,
      lemma_id   INTEGER NOT NULL REFERENCES LEMMA(lemma_id) ON DELETE CASCADE,
      lang       TEXT NOT NULL DEFAULT 'en',
      header_idx INTEGER NOT NULL,
      header_txt TEXT NOT NULL,
      mapped_tag TEXT,
      source     TEXT,
      fetched_at TEXT DEFAULT (datetime('now')),
      UNIQUE(lemma_id, lang, header_idx)
    );
    CREATE TABLE IF NOT EXISTS LEMMA_POS_ORDER (
      lemma_id   INTEGER NOT NULL REFERENCES LEMMA(lemma_id) ON DELETE CASCADE,
      lang       TEXT NOT NULL DEFAULT 'en',
      pos_tag    TEXT NOT NULL,
      rank       INTEGER NOT NULL,
      source     TEXT,
      fetched_at TEXT DEFAULT (datetime('now')),
      PRIMARY KEY (lemma_id, lang, pos_tag)
    );
    """)

    row = cur.execute(
        "SELECT lemma_id FROM LEMMA WHERE lemma = ? COLLATE NOCASE LIMIT 1;",
        (lemma_text,)
    ).fetchone()
    if not row:
        return
    lemma_id = row[0]
    cur.execute("DELETE FROM LEMMA_POS_HEADER_RAW WHERE lemma_id=? AND lang=?;", (lemma_id, lang))
    cur.execute("DELETE FROM LEMMA_POS_ORDER       WHERE lemma_id=? AND lang=?;", (lemma_id, lang))

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for hdr_idx, hdr_txt, mapped in raw_rows:
        cur.execute("""              INSERT OR REPLACE INTO LEMMA_POS_HEADER_RAW
          (lemma_id, lang, header_idx, header_txt, mapped_tag, source, fetched_at)
          VALUES (?,?,?,?,?,?,?)
        """, (lemma_id, lang, hdr_idx, hdr_txt, mapped, source, now))

    for i, tag in enumerate(order):
        cur.execute("""              INSERT OR REPLACE INTO LEMMA_POS_ORDER
          (lemma_id, lang, pos_tag, rank, source, fetched_at)
          VALUES (?,?,?,?,?,?)
        """, (lemma_id, lang, tag, i*10, source, now))

    conn.commit()

def build_pos_orders_for_all_lemmas(db_path: str, sleep_s: float = 0.0, limit: int | None = None):
    conn = db_connect(db_path)
    try:
        words = [r[0] for r in conn.execute(
            "SELECT lemma FROM LEMMA ORDER BY lemma COLLATE NOCASE" + (f" LIMIT {int(limit)}" if limit else "")
        ).fetchall()]
    finally:
        conn.close()

    conn = db_connect(db_path)
    try:
        for i, w in enumerate(words, 1):
            try:
                eng = fetch_english_fragment(w, DEFAULT_RAWDIR)  # your existing helper
                raw_rows, order = extract_pos_header_order_from_english(eng)
                upsert_lemma_pos_order(conn, w, raw_rows, order)
                print(f"[POS-ORDER] {w}: {' '.join(order) if order else '(none)'}  ({i}/{len(words)})")
            except Exception as e:
                print(f"[POS-ORDER FAIL] {w}: {e}")
            if sleep_s and i < len(words):
                time.sleep(sleep_s)
    finally:
        conn.close()

# ---------- text helpers ----------
def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def text_clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def unique_preserve(seq: List[Any]) -> List[Any]:
    seen, out = set(), []
    for x in seq:
        k = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x,(dict,list)) else str(x)
        if k in seen: continue
        seen.add(k); out.append(x)
    return out

# invisible chars + punctuation normalizer
_ZW_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2066-\u2069\u00AD]")  # ZW, bidi, soft hyphen
def _strip_invisible(s: str) -> str:
    return _ZW_RE.sub("", s or "")

def _normalize_punct(s: str) -> str:
    s = _strip_invisible(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:!?%])", r"\1", s)
    s = re.sub(r"([,.;:!?%])(?!\s|$)", r"\1 ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# ---------- POS helpers ----------
def is_pos_from_block(b: HeadingBlock) -> Optional[str]:
    txt = norm_space((b.text or "").lower())
    return POS_HEADINGS.get(txt)

def slice_pos_section(start: HeadingBlock, end: Optional[HeadingBlock]) -> BeautifulSoup:
    return slice_between_blocks(start, end, stop_levels={2,3,4,5,6}, purge_levels=set())

# ---------- pronunciation (IPA only; prefer UK/US) ----------
def extract_pronunciations(eng: BeautifulSoup) -> List[str]:
    uk_list: List[str] = []
    us_list: List[str] = []
    generic: List[str] = []

    blocks = [b for b in iter_heading_blocks(eng, levels=(3,4))]
    for i, b in enumerate(blocks):
        if norm_space((b.text or "").lower()) != "pronunciation":
            continue
        nxt = blocks[i+1] if i+1 < len(blocks) else None
        sec = slice_pos_section(b, nxt)
        for li in sec.find_all("li", recursive=True):
            li_text = li.get_text(" ", strip=True).lower()
            ipas = [text_clean(sp.get_text(" ", strip=True)) for sp in li.select(".IPA")]
            if not ipas: continue
            if "uk" in li_text or "british" in li_text:
                uk_list.extend(ipas)
            elif "us" in li_text or "american" in li_text:
                us_list.extend(ipas)
            else:
                generic.extend(ipas)
        if not (uk_list or us_list or generic):
            generic = [text_clean(sp.get_text(" ", strip=True)) for sp in sec.select(".IPA")]
        break

    return unique_preserve(uk_list + us_list + generic)

# ---------- Alternative forms → variants ----------
def extract_alternative_forms(eng: BeautifulSoup) -> List[str]:
    alts: List[str] = []
    blocks = [b for b in iter_heading_blocks(eng, levels=(3,4))]
    for i, b in enumerate(blocks):
        if norm_space((b.text or "").lower()) not in {"alternative forms", "alternative form"}:
            continue
        nxt = blocks[i+1] if i+1 < len(blocks) else None
        sec = slice_pos_section(b, nxt)
        for li in sec.find_all("li"):
            t = li.get_text(" ", strip=True)
            t = re.sub(r"\s*\(.*?\)\s*$", "", t).strip()
            if t:
                alts.append(t)
    return unique_preserve(alts)

# ---------- degree (comparative/superlative) extraction ----------
_DEGREE_STOP = re.compile(
    r'(?:[,.;:()—–]|'
    r'\b(?:superlative|comparative|used|meaning|sense|usually|often)\b)',
    re.I
)
def _extract_degree(segment: str, keyword: str) -> Optional[str]:
    if not segment:
        return None
    if re.search(r'\bnot\s+comparable\b', segment, re.I):
        return None
    m = re.search(rf'\b{keyword}\b[:\s]*([^\n]+)', segment, flags=re.I)
    if not m:
        return None
    s = m.group(1)
    s = _DEGREE_STOP.split(s, maxsplit=1)[0]
    s = re.sub(r'\s+', ' ', s).strip(' ,.;:()—–')
    s = re.sub(r'\s+(or|and)\s+', r' \1 ', s, flags=re.I)
    return s or None
def _extract_degree_forms(segment: str) -> tuple[Optional[str], Optional[str]]:
    return _extract_degree(segment, 'comparative'), _extract_degree(segment, 'superlative')

# ---------- forms ----------
def parse_forms_from_pos_section(sec: BeautifulSoup, pos_code: str, lemma: str) -> Dict[str, Any]:
    # Head paragraph only (most reliable)
    head_p = None
    for child in sec.children:
        if isinstance(child, Tag) and child.name == "ol":
            break
        if isinstance(child, Tag) and child.name == "p":
            head_p = child
            break
    if head_p is not None:
        head_text = head_p.get_text(" ", strip=True)
    else:
        text_chunks: List[str] = []
        for child in sec.children:
            if isinstance(child, Tag) and child.name == "ol":
                break
            if isinstance(child, Tag):
                text_chunks.append(child.get_text(" ", strip=True))
        head_text = " ".join(text_chunks)

    forms: Dict[str, Any] = {
        "plural": None,
        "comparative": None,
        "superlative": None,
        "verb_inflections": None
    }

    if pos_code in ("N", "PROPN", "LETTER"):
        m = re.search(r"\bplural\b[:\s]\s*([^.;()]+)", head_text, flags=re.I)
        if m:
            vals = [v.strip() for v in re.split(r"[,/]| or ", m.group(1)) if v.strip()]
            forms["plural"] = unique_preserve(vals) or None

    if pos_code in ("ADJ","ADV"):
        comp, sup = _extract_degree_forms(head_text)
        if comp: forms["comparative"] = comp
        if sup:  forms["superlative"] = sup

    if pos_code == "V":
        vi = {k: None for k in VERB_CONCEPTS}

        # stop at comma in each capture
        m3   = re.search(r"\bthird-?person singular(?: simple present)?\b[:\s]\s*([^,.;()]+)", head_text, re.I)
        mprp = re.search(r"\bpresent participle\b[:\s]\s*([^,.;()]+)",                  head_text, re.I)
        mpap = re.search(r"\bpast participle\b[:\s]\s*([^,.;()]+)",                     head_text, re.I)

        msp2 = re.search(r"\bsimple past and past participle\b[:\s]\s*([^,.;()]+)",      head_text, re.I)
        msp  = re.search(r"\bsimple past\b[:\s]\s*([^,.;()]+)",                          head_text, re.I)

        minf = re.search(r"\binfinitive\b[:\s]\s*([^,.;()]+)",                            head_text, re.I)
        mger = re.search(r"\bgerund\b[:\s]\s*([^,.;()]+)",                                head_text, re.I)

        if m3:   vi["3PSP"] = text_clean(m3.group(1))
        if mprp: vi["PRP"]  = text_clean(mprp.group(1))
        if mpap: vi["PAP"]  = text_clean(mpap.group(1))
        if msp2:
            val = text_clean(msp2.group(1))
            for k in ("1PST","2PST","3PST","PLPT","PAP"):
                vi[k] = val
        elif msp:
            val = text_clean(msp.group(1))
            for k in ("1PST","2PST","3PST","PLPT"):
                vi[k] = val
        if minf: vi["INF"] = text_clean(minf.group(1))
        if mger: vi["GER"] = text_clean(mger.group(1))

        forms["verb_inflections"] = vi if any(vi.values()) else None

    return forms

# ---------- citations/coord filters ----------
def _strip_citation_like_nodes(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["sup", "cite"], recursive=True):
        tag.decompose()
    for sp in soup.find_all("span", recursive=True):
        cls = sp.get("class") or []
        if any(c in {"reference","citation","ref"} for c in cls):
            sp.decompose()

_COORD_BLACKLIST = re.compile(
    r"^(coordinate terms?|synonyms?|antonyms?|hypernyms?|hyponyms?|"
    r"meronyms?|holonyms?|related terms?|derived terms?|descendants?|translations?)\b",
    re.I
)

# ---------- examples ----------
def _clean_example_text(t: str) -> str:
    t = _strip_invisible(t)
    t = text_clean(t)
    t = re.sub(r"\[\d+\]", "", t).strip()
    if ":" in t:
        left, right = t.rsplit(":", 1)
        if len(right.strip()) >= 15 and re.search(r"\b\d{3,4}\b", left):
            t = right.strip()
    m = re.search(r"“([^”]{8,})”", t)
    if m:
        t = m.group(1).strip()
    else:
        m2 = re.search(r"\"([^\"\n]{8,})\"", t)
        if m2:
            t = m2.group(1).strip()
    if "—" in t:
        left, right = t.split("—", 1)
        if len(left.strip()) >= 15:
            t = left.strip()
    t = _normalize_punct(t)
    return t

def _canon_for_dedupe(s: str) -> str:
    s = _strip_invisible(s).lower()
    s = _normalize_punct(s)
    s = re.sub(r"[ .,:;–—-]+$", "", s)
    return s

def _is_in_nested_subsense(node: Tag, root_li: Tag) -> bool:
    ol = node.find_parent("ol")
    return bool(ol and ol.find_parent("li") is root_li)

_LEAD_DEFINITION_HINTS = re.compile(
    r"\b(auxiliary|marker|used|meaning|denoting|indicates?|forms?|"
    r"syntax|syntactic|function|grammar|grammatical)\b",
    re.I
)
def _clip_to_lemma_sentence(t: str, lemma: str) -> str:
    if not lemma:
        return t
    m = re.search(rf"\b{re.escape(lemma)}\b", t, flags=re.I)
    if not m:
        return t
    left = t[:m.start()]
    if len(left) >= 12 and _LEAD_DEFINITION_HINTS.search(left):
        return t[m.start():].lstrip(" .,:;—–-")
    return t

def _examples_from_li(li: Tag, lemma: str) -> List[str]:
    if not INCLUDE_EXAMPLES:
        return []

    found: List[str] = []

    for q in li.select("span.quotation, span.quote, blockquote"):
        if _is_in_nested_subsense(q, li):
            continue
        txt = _clean_example_text(q.get_text(" ", strip=True))
        if txt and 5 <= len(txt) <= 400:
            txt = _clip_to_lemma_sentence(txt, lemma)
            found.append(txt)

    for dd in li.find_all("dd", recursive=True):
        if _is_in_nested_subsense(dd, li):
            continue
        dt = dd.find_previous_sibling("dt")
        label = dt.get_text(" ", strip=True) if dt else ""
        if _COORD_BLACKLIST.search(label or ""):
            continue
        txt = _clean_example_text(dd.get_text(" ", strip=True))
        if txt and 5 <= len(txt) <= 400 and not _COORD_BLACKLIST.search(txt):
            txt = _clip_to_lemma_sentence(txt, lemma)
            found.append(txt)

    for exlist in li.find_all(["ul","ol"], recursive=False):
        for exli in exlist.find_all("li", recursive=False):
            txt = _clean_example_text(exli.get_text(" ", strip=True))
            if txt and 5 <= len(txt) <= 400 and not _COORD_BLACKLIST.search(txt):
                txt = _clip_to_lemma_sentence(txt, lemma)
                found.append(txt)

    deduped: List[str] = []
    seen = set()
    for s in found:
        key = _canon_for_dedupe(s)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(s)

    if lemma:
        pat = re.compile(rf"(?<!\w)({re.escape(lemma)})(?!\w)", re.IGNORECASE)
        deduped = [pat.sub(r"«\1»", s) for s in deduped]

    return deduped

# ---------- definitions + subdefinitions ----------
def _extract_subdefinitions_from_li(li: Tag, lemma: str) -> List[Dict[str, Any]]:
    subdefs: List[Dict[str, Any]] = []
    nested_ol = li.find("ol", recursive=False)  # one nested level
    if not nested_ol:
        return subdefs

    for sub_li in nested_ol.find_all("li", recursive=False):
        sub_clone = BeautifulSoup(str(sub_li), "html.parser")
        for nested in sub_clone.find_all(["ul","dl","ol"]):
            nested.decompose()
        _strip_citation_like_nodes(sub_clone)
        subdef_txt = _normalize_punct(text_clean(sub_clone.get_text(" ", strip=True)))
        if not subdef_txt:
            continue
        sub_examples = _examples_from_li(sub_li, lemma)
        subdefs.append({
            "definition": subdef_txt,
            "labels": [],
            "label_groups": [],
            "synonyms": [],
            "antonyms": [],
            "examples": sub_examples,
            "subdefinitions": []
        })
    return subdefs

def extract_definitions_from_section(sec: BeautifulSoup, lemma: str, pos_code: str, rawdir: Path, idx: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    ol = sec.find("ol")
    if not ol:
        dprint(f"[{lemma}/{pos_code}] No <ol> in POS section.")
        if POS_DUMP:
            dump_text(rawdir, f"{lemma}_POS{idx}_{pos_code}_NO_OL.html", sec.prettify())
        return out

    lis = ol.find_all("li", recursive=False)
    dprint(f"[{lemma}/{pos_code}] <ol> with {len(lis)} top-level <li> items.")
    if POS_DUMP:
        dump_text(rawdir, f"{lemma}_POS{idx}_{pos_code}.html", sec.prettify())

    for k, li in enumerate(lis, 1):
        li_clone = BeautifulSoup(str(li), "html.parser")
        for nested in li_clone.find_all(["ul","dl","ol"]):
            nested.decompose()
        _strip_citation_like_nodes(li_clone)

        definition = _normalize_punct(text_clean(li_clone.get_text(" ", strip=True)))
        if not definition:
            dprint(f"[{lemma}/{pos_code}] li#{k}: empty after cleaning (skipped).")
            continue

        examples = _examples_from_li(li, lemma)
        subdefs  = _extract_subdefinitions_from_li(li, lemma)

        out.append({
            "definition": definition,
            "labels": [],
            "label_groups": [],
            "synonyms": [],
            "antonyms": [],
            "examples": examples,
            "subdefinitions": subdefs
        })

    dprint(f"[{lemma}/{pos_code}] extracted {len(out)} definitions (+ subdefs).")
    return out

# ---------- scraping ----------
def fetch_english_fragment(word: str, rawdir: Path) -> BeautifulSoup:
    variants = (word, word.lower(), word[:1].upper() + word[1:].lower(), word.upper())
    last_err = None
    for v in variants:
        url = f"{WIKTIONARY_URL}{v}"
        dprint(f"GET {url}")
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        except Exception as e:
            last_err = f"request error: {e}"; dprint(last_err); continue
        dprint(f"HTTP {r.status_code}, bytes={len(r.content)}")
        if r.status_code != 200:
            last_err = f"HTTP {r.status_code}"; continue

        full = BeautifulSoup(r.text, "html.parser")
        dump_text(rawdir, f"{v}_FULL.html", r.text)

        content = get_content_div(full)
        if not content:
            last_err = "no content div"; dprint(last_err); continue

        eng, nxt, _langs = find_english_block(content)
        if not eng:
            last_err = "no English h2 block"; dprint(last_err); continue

        frag = slice_between_blocks(eng, nxt, stop_levels={2}, purge_levels={2})
        dump_text(rawdir, f"{v}_ENGLISH.html", frag.prettify())
        return frag

    raise RuntimeError(f"No English section for {word!r} ({last_err})")

def scrape_word(word: str, rawdir: Optional[Path] = None) -> Dict[str, Any]:
    rawdir = rawdir or DEFAULT_RAWDIR
    eng = fetch_english_fragment(word, rawdir)

    prons    = extract_pronunciations(eng)
    alt_forms= extract_alternative_forms(eng)

    blocks = [b for b in iter_heading_blocks(eng, levels=(3,4))]
    dprint(f"{word}: found {len(blocks)} heading blocks at levels 3/4 inside English.")

    pos_dict: Dict[str, List[Dict[str, Any]]] = {}
    for i, b in enumerate(blocks):
        code = is_pos_from_block(b)
        heading_txt = (b.text or "").strip()
        if heading_txt.lower().startswith("etymology"):
            continue
        if heading_txt.lower() in {"alternative forms", "alternative form"}:
            continue
        if not code:
            continue

        nxt = blocks[i+1] if i+1 < len(blocks) else None
        section = slice_pos_section(b, nxt)
        if POS_DUMP:
            dump_text(rawdir, f"{word}_POS{i+1}_{code}.html", section.prettify())

        forms = parse_forms_from_pos_section(section, code, word)
        defs  = extract_definitions_from_section(section, word, code, rawdir, i+1)
        if not defs:
            dprint(f"{word}: POS {code} had 0 definitions (skipped).")
            continue

        pos_block = {"forms": forms, "definitions": defs}
        pos_dict.setdefault(code, []).append(pos_block)

    variants = unique_preserve([word, word.capitalize()] + alt_forms)

    entry = {
        "word": word,
        "pronunciation": prons,
        "pos": pos_dict
    }

    return {
        "lemma": word,
        "variants": variants,
        "entries": [entry]
    }

# ---------- Label enrichment (inline) ----------
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
        rest = m.string[m.end():]
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
    if raw:
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

# ---------- SQLite (embedded schema + upsert) ----------
PRAGMAS = [
    ("journal_mode", "WAL"),
    ("synchronous", "NORMAL"),
    ("temp_store", "MEMORY"),
    ("foreign_keys", "ON"),
    ("busy_timeout", "60000"),
    ("cache_size", "-200000"),
]

SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS l0_entry (
  lemma       TEXT PRIMARY KEY,
  json        TEXT NOT NULL,
  checksum    TEXT,
  updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

def db_connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    for k, v in PRAGMAS:
        try:
            if k == "busy_timeout":
                conn.execute(f"PRAGMA {k}={int(v)}")
            else:
                conn.execute(f"PRAGMA {k}={v}")
        except sqlite3.DatabaseError:
            pass
    conn.executescript(SCHEMA_SQL)
    return conn

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()

def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

def upsert_lemma(conn: sqlite3.Connection, lemma_obj: Dict[str, Any]) -> None:
    lemma = lemma_obj["lemma"]
    raw = _json(lemma_obj)
    checksum = _sha(raw)
    cur = conn.cursor()
    cur.execute("BEGIN")
    cur.execute("""
        INSERT INTO l0_entry(lemma,json,checksum,updated_at)
        VALUES(?,?,?,datetime('now'))
        ON CONFLICT(lemma) DO UPDATE SET json=excluded.json, checksum=excluded.checksum, updated_at=excluded.updated_at
    """, (lemma, raw, checksum))

    cur.execute("DELETE FROM l0_variant WHERE lemma=?", (lemma,))
    for v in (lemma_obj.get("variants") or []):
        if isinstance(v, str) and v.strip():
            cur.execute("INSERT OR IGNORE INTO l0_variant(lemma,variant) VALUES(?,?)", (lemma, v.strip()))

    cur.execute("DELETE FROM l0_def_label WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_example WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_def WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_forms_noun WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_forms_adjadv WHERE lemma=?", (lemma,))
    cur.execute("DELETE FROM l0_forms_verb WHERE lemma=?", (lemma,))

    entries = lemma_obj.get("entries") or []
    noun_plural = None
    adj_forms = {"ADJ": {"comparative": None, "superlative": None}, "ADV": {"comparative": None, "superlative": None}}
    verb_forms = {k: None for k in VERB_CONCEPTS}

    def _merge(a, b): return a if a else b

    sense_rows, label_rows, example_rows = [], [], []

    for ent in entries:
        pos_map = ent.get("pos") or {}
        for pos_code, blocks in pos_map.items():
            if not isinstance(blocks, list): continue
            for block in blocks:
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

                defs = block.get("definitions") or []
                for i, d in enumerate(defs, 1):
                    gloss = (d.get("definition") or "").strip()
                    if not gloss:
                        continue
                    labels = d.get("labels") or []
                    label_groups = d.get("label_groups")
                    sense_rows.append((
                        lemma, pos_code, i, None, gloss,
                        json.dumps(labels, ensure_ascii=False) if labels else None,
                        json.dumps(label_groups, ensure_ascii=False) if label_groups else None
                    ))
                    for lb in labels:
                        if isinstance(lb, str) and lb.strip():
                            label_rows.append((lemma, pos_code, i, None, lb.strip()))
                    exs = d.get("examples") or []
                    for j, ex in enumerate(exs, 1):
                        if isinstance(ex, str) and ex.strip():
                            example_rows.append((lemma, pos_code, i, None, j, ex.strip()))
                    for k, sd in enumerate(d.get("subdefinitions") or [], 1):
                        sgloss = (sd.get("definition") or "").strip()
                        if not sgloss:
                            continue
                        slabels = sd.get("labels") or []
                        slabel_groups = sd.get("label_groups")
                        sense_rows.append((
                            lemma, pos_code, i, k, sgloss,
                            json.dumps(slabels, ensure_ascii=False) if slabels else None,
                            json.dumps(slabel_groups, ensure_ascii=False) if slabel_groups else None
                        ))
                        for lb in slabels:
                            if isinstance(lb, str) and lb.strip():
                                label_rows.append((lemma, pos_code, i, k, lb.strip()))
                        sexs = sd.get("examples") or []
                        for j, ex in enumerate(sexs, 1):
                            if isinstance(ex, str) and ex.strip():
                                example_rows.append((lemma, pos_code, i, k, j, ex.strip()))

    if sense_rows:
        conn.executemany("""
            INSERT INTO l0_def(lemma,pos,sense_index,subsense_index,def,labels_json,label_groups_json)
            VALUES(?,?,?,?,?,?,?)
        """, sense_rows)
    if label_rows:
        conn.executemany("""
            INSERT OR IGNORE INTO l0_def_label(lemma,pos,sense_index,subsense_index,label)
            VALUES(?,?,?,?,?)
        """, label_rows)
    if example_rows:
        conn.executemany("""
            INSERT OR REPLACE INTO l0_example(lemma,pos,sense_index,subsense_index,ex_index,example)
            VALUES(?,?,?,?,?,?)
        """, example_rows)

    if noun_plural is not None:
        conn.execute("INSERT OR REPLACE INTO l0_forms_noun(lemma,plural) VALUES(?,?)",
                     (lemma, json.dumps(noun_plural, ensure_ascii=False) if isinstance(noun_plural, list) else noun_plural))
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

# ---------- IO / driver ----------
def write_lemma_json(outdir: Path, lemma: str, lemma_obj: Dict[str, Any], overwrite: bool) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / f"{lemma}.json"
    out_path.write_text(json.dumps(lemma_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path

def run(words: List[str], outdir: Path, sleep_s: float, overwrite: bool,
        rawdir: Path, retry: int, db_conn: Optional[sqlite3.Connection],
        no_files: bool):
    total = len(words)
    for i, w in enumerate(words, 1):
        w = w.strip()
        if not w:
            continue
        try:
            lemma_obj = scrape_word(w, rawdir)
            _enrich_lemma_inplace(lemma_obj)
            if db_conn is not None:
                upsert_lemma(db_conn, lemma_obj)
            if not no_files:
                path = write_lemma_json(outdir, w, lemma_obj, overwrite=True)
                print(f"[OK] {w}  ({i}/{total})  -> {path}")
            else:
                print(f"[OK] {w}  ({i}/{total})  -> (DB)")
        except Exception as e:
            if retry > 0:
                ok = False
                for k in range(1, retry+1):
                    time.sleep(0.8)
                    try:
                        lemma_obj = scrape_word(w, rawdir)
                        _enrich_lemma_inplace(lemma_obj)
                        if db_conn is not None:
                            upsert_lemma(db_conn, lemma_obj)
                        if not no_files:
                            path = write_lemma_json(outdir, w, lemma_obj, overwrite=True)
                            print(f"[OK] {w}  ({i}/{total})  -> {path} (after retry {k})")
                        else:
                            print(f"[OK] {w}  ({i}/{total})  -> (DB) (after retry {k})")
                        ok = True
                        break
                    except Exception:
                        continue
                if not ok:
                    print(f"[FAIL] {w}: {e}")
            else:
                print(f"[FAIL] {w}: {e}")
        if sleep_s and i < total:
            time.sleep(sleep_s)


def main():
    global DBG, POS_DUMP, INCLUDE_EXAMPLES
    ap = argparse.ArgumentParser(description="Wiktionary (English) scraper → JSON/SQLite")
    ag = ap.add_mutually_exclusive_group(required=False)
    ag.add_argument("--word", help="Single word to scrape")
    ag.add_argument("--list", help="Path to file with words (one per line)")
    ap.add_argument("--outdir", default=str(Path("./scraped")), help="Output directory for lemma JSON files")
    ap.add_argument("--sleep", type=float, default=0.0, help="Sleep between requests (seconds)")
    ap.add_argument("--overwrite", action="store_true", help="(kept for API parity)")
    ap.add_argument("--rawdir", default=str(DEFAULT_RAWDIR), help="Directory for debug HTML dumps")
    ap.add_argument("--retries", type=int, default=0, help="Retries per word on failure")

    ap.add_argument("--debug", action="store_true", help="Verbose debug logging to stderr")
    ap.add_argument("--pos-dump", action="store_true", help="Dump each POS section HTML to --rawdir")
    ap.add_argument("--no-examples", action="store_true", help="Disable examples entirely")

    ap.add_argument("--db", help="Write scraped lemmas into this SQLite DB (l0 schema)")
    ap.add_argument("--no-files", action="store_true", help="Skip writing per-lemma JSON files")
    ap.add_argument("--build-pos-order", action="store_true",
                help="Scrape only headings to build lemma POS order (English).")

    args = ap.parse_args()

    DBG = bool(args.debug or os.environ.get("WIKT_DEBUG"))
    POS_DUMP = bool(args.pos_dump)
    INCLUDE_EXAMPLES = not bool(args.no_examples)

    # Fast path: build per-lemma POS order for ALL lemmas in DB; no --word/--list required
    if args.build_pos_order:
        if not args.db:
            ap.error("--build-pos-order requires --db")
        build_pos_orders_for_all_lemmas(args.db, sleep_s=args.sleep)
        return

    # Otherwise, require a word or a file list
    if not (args.word or args.list):
        ap.error("one of the arguments --word --list is required (unless --build-pos-order is used)")

    outdir = Path(args.outdir)
    rawdir = Path(args.rawdir)

    if args.word:
        words = [args.word]
    else:
        with open(args.list, "r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]

    db_conn = None
    if args.db:
        db_conn = db_connect(args.db)

    try:
        run(words, outdir, sleep_s=args.sleep, overwrite=args.overwrite,
            rawdir=rawdir, retry=args.retries, db_conn=db_conn, no_files=args.no_files)
    finally:
        if db_conn is not None:
            db_conn.close()

if __name__ == "__main__":
    main()
