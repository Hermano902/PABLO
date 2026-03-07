"""
llm_enricher.py - LLM-based dictionary enricher for PABLO.

Reads each word folder under data/out/, sends each sense to DeepSeek,
and gets back triples + a narrative template.

Output: data/enriched/<word>/<word>_enriched.json  (one file per headword)

Each enriched sense has the shape:
{
  "sense_key":  "place for money",
  "pos":        "NOUN",
  "definition": "a business that keeps and lends money...",
  "triples": [
    {"s": "THIS",    "p": "KIND", "o": "business"},
    {"s": "THIS",    "p": "DO",   "o": "keep"},
    {"s": "keep",    "p": "BE",   "o": "SOMETHING"},
    ...
  ],
  "narrative": [
    {"s": "THIS",    "p": "KIND", "o": "business"},
    {"s": "SOMEONE", "p": "DO",   "o": "keep"},
    {"s": "keep",    "p": "FROM", "o": "THIS"},
    {"s": "keep",    "p": "BE",   "o": "SOMETHING"},
    ...
  ],
  "primebit": ["BE", "DO", "FROM", "KIND"],
  "nested":   ["business", "keep", "SOMETHING"]
}

Slot conventions (reserved words - uppercase):
  THIS      = the headword itself
  SOMEONE   = unbound person/agent slot
  SOMETHING = unbound object/patient slot
  SOMEWHERE = unbound location slot

Usage:
    python utils/llm_enricher.py --api-key sk-... [--model deepseek-chat]
                                  [--concurrency 8] [--limit 100]
                                  [--resume] [--dry-run]

Config (env vars also accepted):
    DEEPSEEK_API_KEY  -- DeepSeek API key
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ==============================================================================
# CONFIG
# ==============================================================================

_ROOT        = Path(__file__).resolve().parent.parent
DICT_DIR     = Path("G:/AI/PABLO V0002/data/out")
ENRICHED_DIR = _ROOT / "data" / "enriched"

DEEPSEEK_BASE_URL   = "https://api.deepseek.com/v1"
DEFAULT_MODEL       = "deepseek-chat"
DEFAULT_CONCURRENCY = 8
MAX_RETRIES         = 3
RETRY_DELAY         = 2.0  # seconds

# ==============================================================================
# Primes
# ==============================================================================

PRIME_INDEX: list[str] = [
    "AFTER", "ALL", "AT", "BAD", "BE", "BECAUSE", "BEFORE", "BETWEEN",
    "BODY", "CAN", "CAUSE", "CHANGE", "DATA", "DO", "DOWN", "ENTITY",
    "FAR", "FEEL", "FROM", "GOOD", "HAVE", "HEAR", "HEAT", "HERE",
    "IN", "KIND", "KNOW", "LAST", "LEFT", "LESS", "LIFE", "LIGHT",
    "MAKE", "MANY", "MORE", "MOVE", "NEAR", "NEED", "NONE", "NOW",
    "ONE", "OPEN", "OTHER", "PART", "READ", "RIGHT", "SAY", "SEE",
    "SELF", "SIDE", "SOME", "SYMBOL", "THINK", "THIS", "TIME", "TO",
    "TOUCH", "UP", "USE", "WANT", "WITH", "WRITE", "YOU",
]

PRIME_SET = set(PRIME_INDEX)

# Logic pseudo-primes — allowed as predicates alongside real primes,
# but NOT included in primebit (which is prime-indexed only).
LOGIC_INDEX: list[str] = ["NOT", "AND", "OR", "IF", "XOR"]
LOGIC_SET   = set(LOGIC_INDEX)

# Full allowed predicate set
ALLOWED_PREDICATES = PRIME_SET | LOGIC_SET

# Reserved slot words - treated as valid nodes, not filtered out
SLOT_WORDS = {"THIS", "SOMEONE", "SOMETHING", "SOMEWHERE"}

# ==============================================================================
# Prompt
# ==============================================================================

_SYSTEM_PROMPT = """\
You are a semantic decomposition engine for a neurosymbolic AI.

You will receive a word (the headword), its part-of-speech, its sense label,
and its definition text. Produce two outputs:

1. triples - the timeless semantic graph of this concept.
2. narrative - a situated event sequence showing how this concept plays out
   in time, with open slots for unbound participants.

Both use the same triple format: {{"s": subject, "p": PRIME, "o": object}}

PRIME must always be one of the semantic primes:
{primes}

Or one of the logic pseudo-primes (act as predicates, same as primes):
NOT  AND  OR  IF  XOR

== SLOT WORDS ==
Use these as nodes (never as predicates):
  THIS      = the headword itself
  SOMEONE   = unbound person or agent
  SOMETHING = unbound object or patient
  SOMEWHERE = unbound location

All other nodes are lowercase English lemmas from or implied by the definition.

== NODE RULES ==
- Verbs are always object nodes, never predicates. Attach them with DO:
    THIS DO keep
    keep BE SOMETHING        (what is kept)
    keep FROM THIS           (kept by the bank)
- Decompose compound phrases recursively:
    financial services -> services KIND financial
- Every node must be a single lowercase lemma — NO spaces allowed in a node.
  If you need to express a phrase, decompose it into linked triples instead.
  CORRECT: record KIND personal, SOMEONE HAVE record
  WRONG:   SOMEONE HAVE "personal record"
- Never use a word that appears in the PRIME list as a node.
  If the definition contains a word that is also a prime name (e.g. "be", "do",
  "kind", "have"), rephrase it as a lemma: "be" -> "exist", "have" -> "possess".
  Prepositions that are primes (in, to, from, at, with, near, far, between,
  after, before, up, down, left, right, side) must also be rephrased or
  absorbed into a more specific verb: "move in" -> "enter", "go to" -> "reach".

== LOGIC PSEUDO-PRIME RULES ==
Use NOT, AND, OR, IF, XOR as predicates when meaning requires it:

NOT — negation: something is explicitly absent or prohibited
  THIS NOT possible        (this concept is not possible)
  SOMEONE NOT DO           (someone does not do something)
  manner NOT satisfactory  (the manner is unsatisfactory)

AND — conjunction: two things that hold simultaneously
  quality AND condition    (both apply together)

OR — disjunction: alternatives, one or more hold
  SOMETHING OR SOMETHING   (either works)

IF — conditional: one thing holds only when another does
  SOMEONE IF condition     (agent acts if condition is met)
  result IF action         (result follows if action is taken)

XOR — exclusive: exactly one of two alternatives
  Use sparingly — only when the definition explicitly says "either but not both".

Prefer NOT over expressing negation as a noun node:
  CORRECT: THIS NOT possible
  WRONG:   THIS BE impossibility

== POS RULES ==

NOUN / VERB senses:
- THIS is the concept, not the thing it acts on.
- Start with THIS KIND <category> to classify the concept.
- For verb senses: the action IS the concept.
    CORRECT:   THIS KIND action, SOMEONE DO THIS, THIS BE <what happens>
    WRONG:     THIS KIND <object-of-the-verb>
  Example for "run a business":
    THIS KIND action
    THIS DO manage
    manage BE SOMETHING
    SOMEONE DO THIS
    THIS BE SOMETHING
  NOT: THIS KIND business  (business is the object, not the concept)

ADJECTIVE / ADVERB senses:
- THIS is a property or manner, not a doer.
- Use THIS KIND manner or THIS KIND property.
- Encode what quality THIS asserts and what it applies to.
- Do NOT add DO triples unless the modifier clearly implies a concrete action.
  Example for "well" (satisfactorily):
    THIS KIND manner
    manner BE satisfactory
    SOMETHING DO SOMETHING
    SOMETHING BE THIS        (the action is done in this manner)
  NOT: THIS DO satisfy  (well does not itself perform satisfaction)

FUNCTION WORD senses (conjunctions, prepositions, particles, contractions):
- Encode the structural role: what two things THIS connects or relates.
- Use THIS KIND relation or THIS KIND connector.
- Avoid meta-labels like THIS KIND adverb / THIS KIND suffix.

== triples vs narrative ==
triples:
  Timeless facts. Compact (4-8 triples). Always start with THIS KIND <category>.
  Encode what the concept IS and what it structurally entails.

narrative:
  Ordered event sequence (4-10 frames). Show who does what to whom over time.
  Use SOMEONE/THIS/SOMETHING/SOMEWHERE to fill agent, action, patient, location.
  Each frame is one triple. Order matters: cause before effect, action before result.

Respond with a single JSON object, no explanation, no markdown:
{{
  "triples": [
    {{"s": "THIS",    "p": "KIND", "o": "business"}},
    {{"s": "THIS",    "p": "DO",   "o": "keep"}},
    {{"s": "keep",    "p": "BE",   "o": "SOMETHING"}},
    ...
  ],
  "narrative": [
    {{"s": "SOMEONE", "p": "DO",   "o": "deposit"}},
    {{"s": "deposit", "p": "FROM", "o": "SOMEONE"}},
    {{"s": "deposit", "p": "TO",   "o": "THIS"}},
    {{"s": "THIS",    "p": "DO",   "o": "keep"}},
    {{"s": "keep",    "p": "BE",   "o": "deposit"}},
    ...
  ]
}}
"""

_USER_TEMPLATE = """\
Headword: {headword}
POS: {pos}
Sense: {sense_key}
Definition: {definition}
"""


def _build_system_prompt() -> str:
    primes_str = ", ".join(PRIME_INDEX)
    return _SYSTEM_PROMPT.format(primes=primes_str)


# ==============================================================================
# Dict entry loader
# ==============================================================================

def _first_definition_text(definitions: list[dict]) -> str:
    for d in definitions:
        text = d.get("TEXT", "").strip()
        if text:
            return text
    return ""


def load_senses(folder: Path) -> list[dict]:
    headword = folder.name
    combined = folder / f"{headword}_v4.json"
    if not combined.exists():
        matches = list(folder.glob("*_v4.json"))
        non_pos = [
            m for m in matches
            if not any(tag in m.stem for tag in ("_NOUN", "_VERB", "_ADJ", "_ADV"))
        ]
        combined = non_pos[0] if non_pos else (matches[0] if matches else None)

    if combined is None or not combined.exists():
        return []

    try:
        with open(combined, encoding="utf-8") as f:
            entry = json.load(f)
    except Exception:
        return []

    senses = []
    for pos_label, pos_data in entry.get("POS", {}).items():
        for sense_key, sense_data in pos_data.get("SENSE", {}).items():
            definition = _first_definition_text(sense_data.get("DEFINITIONS", []))
            if not definition:
                continue
            senses.append({
                "headword":   headword,
                "pos":        pos_label,
                "sense_key":  sense_key,
                "definition": definition,
            })

    return senses


# ==============================================================================
# LLM call
# ==============================================================================

# Lowercase forms of all reserved predicate words — blocked as nodes
_BLOCKED_NODES = {w.lower() for w in ALLOWED_PREDICATES}


def _validate_triple_list(raw_list: list) -> list[dict]:
    """Filter a list of raw triple dicts - predicate must be a prime or logic pseudo-prime."""
    result = []
    for t in raw_list:
        s = t.get("s", "").strip()
        p = t.get("p", "").upper().strip()
        o = t.get("o", "").strip()
        if not s or not o:
            continue
        if p not in ALLOWED_PREDICATES:
            continue
        # Normalise case: slot words uppercase, everything else lowercase
        s = s.upper() if s.upper() in SLOT_WORDS else s.lower()
        o = o.upper() if o.upper() in SLOT_WORDS else o.lower()
        # Drop triples where a node is a prime or logic pseudo-prime word
        if s in _BLOCKED_NODES or o in _BLOCKED_NODES:
            continue
        # Drop triples with multiword nodes (spaces not allowed in lemma nodes)
        if ' ' in s or ' ' in o:
            continue
        result.append({"s": s, "p": p, "o": o})
    return result


def _validate_enrichment(raw: dict) -> dict:
    """
    Validate and clean enrichment from the LLM.
    Derives primebit and nested from the triples list.
    primebit: only real semantic primes (not logic pseudo-primes).
    """
    triples   = _validate_triple_list(raw.get("triples", []))
    narrative = _validate_triple_list(raw.get("narrative", []))

    # Derive primebit: unique SEMANTIC primes used as predicates (logic excluded)
    primebit = sorted(
        {t["p"] for t in triples if t["p"] in PRIME_SET},
        key=lambda x: PRIME_INDEX.index(x),
    )

    # Derive nested: unique object nodes from triples (excluding slot words)
    nested = list(dict.fromkeys(
        t["o"] for t in triples if t["o"] not in SLOT_WORDS
    ))

    return {
        "triples":   triples,
        "narrative": narrative,
        "primebit":  primebit,
        "nested":    nested,
    }


async def _call_llm(
    client,
    model: str,
    system_prompt: str,
    sense: dict,
) -> dict | None:
    user_msg = _USER_TEMPLATE.format(
        headword=sense["headword"],
        pos=sense["pos"],
        sense_key=sense["sense_key"],
        definition=sense["definition"],
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.0,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            result = json.loads(raw)
            return _validate_enrichment(result)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(
                    f"  ERROR {sense['headword']}:{sense['sense_key']}: {e}",
                    file=sys.stderr,
                )
                return None

    return None


# ==============================================================================
# Per-word processing
# ==============================================================================

async def process_word(
    folder: Path,
    client,
    model: str,
    system_prompt: str,
    semaphore: asyncio.Semaphore,
    dry_run: bool = False,
) -> dict | None:
    headword = folder.name
    out_path = ENRICHED_DIR / headword / f"{headword}_enriched.json"

    senses_raw = load_senses(folder)
    if not senses_raw:
        return None

    if dry_run:
        print(f"[dry-run] {headword}: {len(senses_raw)} senses")
        return {"headword": headword, "senses": []}

    async def _enrich_sense(sense: dict) -> dict:
        async with semaphore:
            enrichment = await _call_llm(client, model, system_prompt, sense)
        if enrichment is None:
            enrichment = {"triples": [], "narrative": [], "primebit": [], "nested": []}
        return {
            "sense_key":  sense["sense_key"],
            "pos":        sense["pos"],
            "definition": sense["definition"],
            "triples":    enrichment["triples"],
            "narrative":  enrichment["narrative"],
            "primebit":   enrichment["primebit"],
            "nested":     enrichment["nested"],
        }

    results = await asyncio.gather(*[_enrich_sense(s) for s in senses_raw], return_exceptions=True)
    enriched_senses = [
        r if isinstance(r, dict) else {
            "sense_key":  senses_raw[i]["sense_key"],
            "pos":        senses_raw[i]["pos"],
            "definition": senses_raw[i]["definition"],
            "triples": [], "narrative": [], "primebit": [], "nested": [],
        }
        for i, r in enumerate(results)
    ]

    result = {"headword": headword, "senses": enriched_senses}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


# ==============================================================================
# Main
# ==============================================================================

async def run(
    api_key: str,
    model: str,
    concurrency: int,
    limit: int | None,
    resume: bool,
    dry_run: bool,
    words: list[str] | None = None,
) -> None:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("ERROR: openai package required. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    client        = AsyncOpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    system_prompt = _build_system_prompt()
    semaphore     = asyncio.Semaphore(concurrency)

    folders = sorted(DICT_DIR.iterdir()) if DICT_DIR.exists() else []
    if words:
        folders = [f for f in folders if f.name in words]
    if limit:
        folders = folders[:limit]
    if resume:
        folders = [
            f for f in folders
            if not (ENRICHED_DIR / f.name / f"{f.name}_enriched.json").exists()
        ]

    total = len(folders)
    print(f"Words to process: {total}  (concurrency={concurrency}, model={model})")
    if dry_run:
        print("[dry-run mode - no API calls will be made]")

    done   = 0
    errors = 0
    t0     = time.time()

    for folder in folders:
        result = await process_word(folder, client, model, system_prompt, semaphore, dry_run)
        done += 1
        if result is None:
            errors += 1
        elapsed = time.time() - t0
        rate    = done / elapsed if elapsed > 0 else 0
        eta     = (total - done) / rate if rate > 0 else 0
        print(
            f"  {done}/{total}  {folder.name}  errors={errors}  "
            f"{rate:.1f} words/s  ETA {eta/60:.1f} min"
        )

    print(f"\nDone. {done} words processed, {errors} errors/skipped.")
    print(f"Output: {ENRICHED_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM enricher for PABLO dictionary compounds")
    parser.add_argument(
        "--api-key", default=os.environ.get("DEEPSEEK_API_KEY", ""),
        help="DeepSeek API key (or set DEEPSEEK_API_KEY env var)",
    )
    parser.add_argument("--model",       default=DEFAULT_MODEL)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--limit",       type=int, default=None,
                        help="Process only first N words (for testing)")
    parser.add_argument("--resume",      action="store_true",
                        help="Skip words that already have an enriched file")
    parser.add_argument("--dry-run",     action="store_true",
                        help="List what would be processed without calling the API")
    parser.add_argument("--word",        action="append", dest="words", metavar="WORD",
                        help="Process only this word (repeatable: --word well --word run)")
    args = parser.parse_args()

    if not args.api_key and not args.dry_run:
        print("ERROR: --api-key or DEEPSEEK_API_KEY env var required.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run(
        api_key=args.api_key,
        model=args.model,
        concurrency=args.concurrency,
        limit=args.limit,
        resume=args.resume,
        dry_run=args.dry_run,
        words=args.words,
    ))


if __name__ == "__main__":
    main()
