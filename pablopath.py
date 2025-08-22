# pablopath.py — neuro-aligned paths for Pablo
# - Senses: organs → nerves → thalamus → primary_cortex → association
# - Motor: output execution
# - Memory: semantic (L0/L1), episodic, vector
# - WM buffers (ephemeral) for raw dumps
# Legacy constants preserved for compatibility.

import os
import sys
import glob

# ─────────────────────────── basics ───────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def _add(p: str):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

# Top-level import roots
for _p in ("brain", "senses", "motor", "cognition", "memory", "daemons"):
    _add(os.path.join(ROOT_DIR, _p))

# ─────────────────────────── brain ────────────────────────────
BRAIN_DIR     = os.path.join(ROOT_DIR, "brain")
THALAMUS_DIR  = os.path.join(BRAIN_DIR, "thalamus")
RAS_DIR       = os.path.join(BRAIN_DIR, "ras")
BRAIN_ATTN_DIR= os.path.join(BRAIN_DIR, "attention")  # attention controller
SCHEDULER_DIR = os.path.join(BRAIN_DIR, "scheduler")  # if you keep one

# ────────────────────────── senses ────────────────────────────
SENSES_DIR    = os.path.join(ROOT_DIR, "senses")

# Eyes
EYES_DIR           = os.path.join(SENSES_DIR, "eyes")
EYES_ORGANS_DIR    = os.path.join(EYES_DIR, "organs")
EYES_NERVES_DIR    = os.path.join(EYES_DIR, "nerves")
EYES_V1_DIR        = os.path.join(EYES_DIR, "primary_cortex")
EYES_ASSOC_DIR     = os.path.join(EYES_DIR, "association")

# Ears
EARS_DIR           = os.path.join(SENSES_DIR, "ears")
EARS_ORGANS_DIR    = os.path.join(EARS_DIR, "organs")
EARS_NERVES_DIR    = os.path.join(EARS_DIR, "nerves")
EARS_V1_DIR        = os.path.join(EARS_DIR, "primary_cortex")
EARS_ASSOC_DIR     = os.path.join(EARS_DIR, "association")

# System (proprioception/interoception for a computer body)
SYSTEM_DIR         = os.path.join(SENSES_DIR, "system")
SYSTEM_ORGANS_DIR  = os.path.join(SYSTEM_DIR, "organs")
SYSTEM_NERVES_DIR  = os.path.join(SYSTEM_DIR, "nerves")
SYSTEM_V1_DIR      = os.path.join(SYSTEM_DIR, "primary_cortex")
SYSTEM_ASSOC_DIR   = os.path.join(SYSTEM_DIR, "association")

# Touch (optional, future)
TOUCH_DIR          = os.path.join(SENSES_DIR, "touch")
TOUCH_ORGANS_DIR   = os.path.join(TOUCH_DIR, "organs")
TOUCH_NERVES_DIR   = os.path.join(TOUCH_DIR, "nerves")
TOUCH_V1_DIR       = os.path.join(TOUCH_DIR, "primary_cortex")
TOUCH_ASSOC_DIR    = os.path.join(TOUCH_DIR, "association")

# ─────────────────────────── motor ────────────────────────────
MOTOR_DIR      = os.path.join(ROOT_DIR, "motor")
MOTOR_UI_DIR   = os.path.join(MOTOR_DIR, "ui")
MOTOR_FS_DIR   = os.path.join(MOTOR_DIR, "filesystem")
MOTOR_NET_DIR  = os.path.join(MOTOR_DIR, "network")
MOTOR_SPEECH_DIR = os.path.join(MOTOR_DIR, "speech")

# ───────────────────────── cognition ──────────────────────────
COGNITION_DIR    = os.path.join(ROOT_DIR, "cognition")
CONTEXT_DIR      = os.path.join(COGNITION_DIR, "context")
WM_DIR           = os.path.join(COGNITION_DIR, "wm")
REASON_DIR       = os.path.join(COGNITION_DIR, "reason")
PLANNER_DIR      = os.path.join(COGNITION_DIR, "planner")
SKILLS_DIR       = os.path.join(COGNITION_DIR, "skills")

# Skills (domain-agnostic)
SKILL_LANGUAGE_DIR   = os.path.join(SKILLS_DIR, "language")
SKILL_MATH_DIR       = os.path.join(SKILLS_DIR, "math")
SKILL_VISION_DIR     = os.path.join(SKILLS_DIR, "vision")
SKILL_FILES_DIR      = os.path.join(SKILLS_DIR, "files")
SKILL_SEARCH_DIR     = os.path.join(SKILLS_DIR, "search")
SKILL_AUTOMATION_DIR = os.path.join(SKILLS_DIR, "automation")

# Working Memory buffers (ephemeral; raw dumps live here)
BUFFERS_DIR       = os.path.join(WM_DIR, "buffers")
RAW_DUMPS_DIR     = os.path.join(BUFFERS_DIR, "eyes", "raw_dumps")  # legacy name preserved
UNSORTED_DIR      = os.path.join(RAW_DUMPS_DIR, "unsorted")
SORTED_DIR        = os.path.join(RAW_DUMPS_DIR, "sorted")
WM_WIKT_RAW_DIR   = os.path.join(RAW_DUMPS_DIR, "wiktionary")
WM_WIKT_UNSORTED  = os.path.join(WM_WIKT_RAW_DIR, "unsorted")
WM_WIKT_SORTED    = os.path.join(WM_WIKT_RAW_DIR, "sorted")

# ─────────────────────────── memory ───────────────────────────
MEMORY_DIR         = os.path.join(ROOT_DIR, "memory")
EPISODIC_STORE_DIR = os.path.join(MEMORY_DIR, "episodic")
SEMANTIC_STORE_DIR = os.path.join(MEMORY_DIR, "semantic")
VECTOR_STORE_DIR   = os.path.join(MEMORY_DIR, "vector")
ADAPTERS_DIR       = os.path.join(MEMORY_DIR, "adapters")

# Domains live under semantic memory
DOMAINS_DIR     = os.path.join(SEMANTIC_STORE_DIR, "domains")

# ───── Language domain (L0 immutable truths, L1 experiential overlay)
LANG_DOMAIN_DIR = os.path.join(DOMAINS_DIR, "language")
LANG_L0_DIR     = os.path.join(LANG_DOMAIN_DIR, "L0")
LANG_L1_DIR     = os.path.join(LANG_DOMAIN_DIR, "L1")

# Reference rules (L0) — legacy names preserved
THESAURUS_DIR         = os.path.join(LANG_L0_DIR, "rules")
sentence_rules_path   = os.path.join(THESAURUS_DIR, "sentence_rules.json")
phrases_clauses_path  = os.path.join(THESAURUS_DIR, "phrases_clauses.json")
pos_rules_path        = os.path.join(THESAURUS_DIR, "pos_rules.json")
word_rules_path       = os.path.join(THESAURUS_DIR, "wordrules.json")
BLACKLIST_FILE        = os.path.join(THESAURUS_DIR, "blacklist.json")  # optional

# Reference dictionary (L0) — legacy names preserved
DICTIONARY_DIR   = os.path.join(LANG_L0_DIR, "dictionary")
MANIFEST_DIR     = os.path.join(DICTIONARY_DIR, "manifest")

# L0 manifest roots
L0_MANIFESTS_DIR      = os.path.join(LANG_L0_DIR, "manifests")
LEMMA_MANIFESTS_DIR   = os.path.join(L0_MANIFESTS_DIR, "lemmas")

# Experiential layer (L1)
LANG_L1_EXPERIENCE_DIR = os.path.join(LANG_L1_DIR, "experience")
LANG_L1_OVERLAYS_DIR   = os.path.join(LANG_L1_DIR, "overlays")
curiosity_path         = os.path.join(LANG_L1_EXPERIENCE_DIR, "curiosity_log.json")  # legacy name preserved


# L1 overlays for normalized entries
WIKT_OVERLAYS_DIR = os.path.join(LANG_L1_OVERLAYS_DIR, "wiktionary")

# ───── Math domain
MATH_DOMAIN_DIR  = os.path.join(DOMAINS_DIR, "math")
MATH_L0_DIR      = os.path.join(MATH_DOMAIN_DIR, "L0")
MATH_L1_DIR      = os.path.join(MATH_DOMAIN_DIR, "L1")
MATH_L0_AXIOMS_DIR       = os.path.join(MATH_L0_DIR, "axioms")
MATH_L0_THEOREMS_DIR     = os.path.join(MATH_L0_DIR, "theorems")
MATH_L0_DEFINITIONS_DIR  = os.path.join(MATH_L0_DIR, "definitions")
MATH_L1_EXPERIMENTS_DIR  = os.path.join(MATH_L1_DIR, "experiments")
MATH_L1_CONJECTURES_DIR  = os.path.join(MATH_L1_DIR, "conjectures")
MATH_L1_NOTES_DIR        = os.path.join(MATH_L1_DIR, "notes")

# ───── Vision domain
VISION_DOMAIN_DIR = os.path.join(DOMAINS_DIR, "vision")
VISION_L0_DIR     = os.path.join(VISION_DOMAIN_DIR, "L0")
VISION_L1_DIR     = os.path.join(VISION_DOMAIN_DIR, "L1")
VISION_L0_LABELS_DIR     = os.path.join(VISION_L0_DIR, "labels")
VISION_L0_ONTOLOGIES_DIR = os.path.join(VISION_L0_DIR, "ontologies")
VISION_L1_OBSERVATIONS_DIR = os.path.join(VISION_L1_DIR, "observations")

# ───── System domain
SYSTEM_DOMAIN_DIR2 = os.path.join(DOMAINS_DIR, "system")  # avoid name clash with senses/system
SYSTEM_L0_DIR      = os.path.join(SYSTEM_DOMAIN_DIR2, "L0")
SYSTEM_L1_DIR      = os.path.join(SYSTEM_DOMAIN_DIR2, "L1")
SYSTEM_L0_SCHEMAS_DIR  = os.path.join(SYSTEM_L0_DIR, "schemas")
SYSTEM_L1_EPISODES_DIR = os.path.join(SYSTEM_L1_DIR, "episodes")

# ────────────── manifests discovery (packs/skills/daemons) ──────────────
PACK_MANIFEST_FILES = ("__manifest__.json", "__pack__.json")

def discover_manifests():
    """
    Find all pack/skill/daemon manifests across the repo.
    Looks for __pack__.json (packs/nodes) and __manifest__.json (skills/daemons).
    """
    patterns = [
        os.path.join(ROOT_DIR, "senses", "**", "__pack__.json"),
        os.path.join(ROOT_DIR, "senses", "**", "__manifest__.json"),
        os.path.join(ROOT_DIR, "motor",  "**", "__pack__.json"),
        os.path.join(ROOT_DIR, "motor",  "**", "__manifest__.json"),
        os.path.join(SKILLS_DIR,        "**", "__manifest__.json"),
        os.path.join(ROOT_DIR, "daemons","**", "__manifest__.json"),
    ]
    found = []
    for pat in patterns:
        found.extend(glob.glob(pat, recursive=True))
    # Deduplicate (preserve order)
    seen, uniq = set(), []
    for p in found:
        if p not in seen:
            uniq.append(p); seen.add(p)
    return uniq
