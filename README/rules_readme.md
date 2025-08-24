# Pablo — Language Rules README (English)

This document describes how **English rules** are organized for Pablo’s language stack. It complements the root project README and the language module README; this file focuses only on the **conceptual structure** of English rules and how we’ll categorize them in the repo.

> POS tags and attributes referenced here come from the project’s **pos_schema** (source of truth). Do not hardcode POS ids; resolve them via the schema.

---

## Constitutive vs. Regulatory Rules

English has various rules governing its structure, including **grammatical** (sentence structure, agreement, tense), **orthographical** (capitalization, punctuation), **phonological** (sound patterns), and **semantic & pragmatic** (meaning and usage). We group these into:

- **Constitutive rules** — define the fundamental structure of the language. If violated, the result is ungrammatical (doesn’t function as a sentence).  
  *Example:* “Cat the dog chased.”

- **Regulatory rules** — guide correctness, clarity, and style. Violations don’t break grammaticality but may be marked incorrect or awkward.  
  *Example:* “He did good on the exam.”

---

## Key Types of Rules in English

### 1) Grammatical Rules
- **Sentence Structure:** A sentence needs (at minimum) a subject and a verb to express a complete thought.  
- **Subject–Verb Agreement:** Singular subjects take singular verbs; plural subjects take plural verbs.  
- **Verb Tense Consistency:** Keep tense consistent within a sentence (or tightly connected sentences).  
- **Pronoun Agreement:** Pronouns agree in number/gender with their antecedents.  
- **Modifier Placement:** Adjectives/adverbs should modify the intended words.  
- **Active Voice Preference:** Often clearer and more direct than passive (regulatory).

### 2) Orthographical (Spelling & Punctuation) Rules
- **Capitalization:** Capitalize the first word of a sentence and proper nouns (people, places, etc.).  
- **Punctuation:** Use periods, question marks, commas, semicolons, etc., to signal structure and meaning.  
- **Spelling:** Correct spelling supports clarity and credibility.

### 3) Phonological Rules (Sounds)
- Govern how sounds combine and alternate in words (relevant mainly to speech or grapheme–phoneme mapping).

### 4) Semantic Rules (Meaning)
- Support understanding of word meanings and sense distinctions.

### 5) Pragmatic Rules (Context & Usage)
- Guide appropriate use/interpretation in context (register, politeness, implicature, discourse coherence).

---

## Repository Categorization (where rules live)

To keep rules discoverable and testable, we categorize them as follows (language L0):

- **Word-level rules** — single-token properties and local constraints (e.g., POS tagging hints, orthography flags).  
  *Folder:* `memory/semantic/domains/language/l0/rules/word/`

- **Phrase/Clause rules** — multi-token patterns within a clause or phrase (e.g., DET→NOUN, AUX→VERB, ADJ→NOUN).  
  *Folder:* `memory/semantic/domains/language/l0/rules/phrases_clauses/`

- **Sentence-level rules** — sentence-shape constraints (root selection, sentence force, clause linking).  
  *Folder:* `memory/semantic/domains/language/l0/rules/sentences/`

> Some existing **POS-related rules** (currently under “word rules”) may later be reclassified into **phrases_clauses** as they assert relations between POS (POS→POS).

---

## Authoring Guidance

- **Source of truth:** JSON rule files in the folders above.  
- **POS & attributes:** Always reference POS via `pos_schema` tags (e.g., `"POS.NOUN"`, `"POS.VERB"`).  
- **Constitutive vs. regulatory:** When useful, annotate a rule with `"kind": "constitutive"` or `"kind": "regulatory"` to clarify its intent.  
- **Validation:** Keep rules machine-checkable (e.g., lints for unknown POS tags or dependency labels).  
- **Explainability:** Each applied rule should be traceable by `rule_id` in justifications.

---

## Examples (conceptual)

- **Constitutive (phrase):**  
  DET must attach to a following NOUN within a small window and without intervening punctuation.

- **Regulatory (sentence/style):**  
  Prefer active voice when both active and passive parses are available with equal plausibility.

---

_Last updated: this file documents the conceptual rule structure only; implementation details (matching, scoring, justification) live in the code and engine docs._
