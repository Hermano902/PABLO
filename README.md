# Pablo Operating Manual — Rule‑Guided Curiosity

*Version 0.1 — 2025‑08‑19*

This manual explains how Pablo behaves and how to operate him in different environments. It’s written in human terms: what Pablo pays attention to, how he learns, how he explains himself, and how to steer his curiosity without boxing him in.

---

## 1) What Pablo is (one‑paragraph)

Pablo is a neuro‑symbolic, model‑based cognitive agent. He thinks with **concepts, rules, and plans**, learns through **curiosity and experiments**, and acts within a **safety envelope**. Rules act as **mentors** (priors and critics), not cages. He builds a **concept graph** with living **concept cards**, upgrades **associations → causes** when interventions confirm them, and promotes repeated success into reusable **skills**. He explains every important decision with **proofs, witnesses, and provenance**.

---

## 2) Core principles

* **Curiosity first.** Surprise, novelty, and contradictions generate questions and research tasks.
* **Rules as accelerators.** Use rules to guide, critique, and regularize; keep hard walls only at effectors (filesystem/network/speech).
* **Concept‑centric memory.** Concepts and their cards are the unit of knowledge, planning, and teaching.
* **Anytime planning.** Always keep a best‑so‑far plan; balance exploitation and exploration within a risk budget.
* **Provenance everywhere.** Every claim carries its witnesses (episodes, sources) and the rules involved.
* **Deterministic when it counts.** Same situation + same settings ⇒ same plan; exploration adds controlled variability.

---

## 3) Pablo’s mental loop (human view)

1. **Perception** → “What’s here?” Objects, text, and relations are proposed—often with alternatives.
2. **Context Frame** → “What matters now?” A small working set under the spotlight.
3. **Prediction** → “What should happen next?” Expectations compared with reality → **surprise** where they diverge.
4. **Attention & Gating** → Spotlight flows to what’s surprising, novel, or goal‑relevant.
5. **Concept Graph & Cards** → Knowledge is organized; each card has definition, facets, constraints, examples, open questions, links.
6. **Chunking → Skills** → Repeated success becomes a named skill with typed slots.
7. **Grounding Words** → Words bind to referents and actions across scenes.
8. **Association → Causality** → Co‑occurs → precedes → causes (after interventions and no counterexamples).
9. **Affordances** → “What can I do with this?” Object types suggest skills with learned success conditions.
10. **Researcher Loop** → Generate questions, gather evidence, synthesize, test safely, update cards.
11. **Reasoner (rule‑guided)** → Keep interpretations coherent; allow minimal, justified slack when novel.
12. **Planner (anytime)** → Rank plans by goal fit, expected value, learning value, and values/personality.
13. **Values & Personality** → Curiosity vs. mastery vs. efficiency balance; drifts slowly with outcomes.
14. **Memory Systems** → WM (few slots), Episodic (append‑only traces), Semantic (consolidated cards/skills/rules).
15. **Safety Envelope** → Think freely; act safely (dry‑run, sandbox, rate‑limit, whitelists, confirmations).

---

## 4) Operating modes

Two top‑level modes balance reliability and growth. You can change these at runtime.

### A) Production mode (reliability first)

* **Risk budget:** Low
* **Learning mode:** Observe + sandbox only; manual confirm for real effects
* **Rule strictness:** “Mentor‑strict” (soft everywhere, hard at effectors + core invariants)
* **Exploration:** Opportunistic (when idle), bounded depth
* **Consolidation:** Frequent but conservative
* **Logging:** Full proofs and witnesses; operator prompts on deviations

### B) Exploration mode (learning first)

* **Risk budget:** Medium → High (still within safety envelope)
* **Learning mode:** Sandbox + limited real trials with auto‑confirm on reversible actions
* **Rule strictness:** “Mentor‑flex” (more slack for novelty; heavier critique after)
* **Exploration:** Intentional; prioritize high information‑gain topics
* **Consolidation:** Aggressive; try/learn/prune daily
* **Logging:** Full proofs, extra ablations, curiosity traces

---

## 5) Operator dials (with suggested defaults)

| Dial                      | What it controls                                |                         Prod default |                      Explore default |
| ------------------------- | ----------------------------------------------- | -----------------------------------: | -----------------------------------: |
| **Risk budget**           | How far plans can deviate from known safe paths |                                  1/5 |         3/5 (up to 4/5 in sandboxes) |
| **Learning mode**         | Observe / Sandbox / Real                        |                              Sandbox |     Sandbox→Real on reversible steps |
| **Rule strictness**       | Weight of rule critic vs. slack                 |                                 High |                               Medium |
| **Exploration ratio**     | Explore vs. exploit plan mix                    |                                  10% |                                  40% |
| **Consolidation cadence** | How often cards/skills/rules are updated        |                            Every 24h |                          Every 8–12h |
| **Curiosity emphasis**    | Novelty vs. mastery vs. contradiction repair    | Mastery=0.5, Novelty=0.2, Repair=0.3 | Mastery=0.3, Novelty=0.5, Repair=0.2 |
| **WM capacity**           | Active slots under attention                    |                                    5 |                                    7 |
| **Proof verbosity**       | Detail in explanations                          |                  High for exceptions |                         High for all |

*Tip:* Treat **Rule strictness** and **Risk budget** as the primary safety levers.

---

## 6) Component deep‑dives (human explanations)

### 6.1 Perception (“Multiple plausible takes”)

Pablo prefers to keep several reasonable interpretations alive rather than bet early. This is how he stays flexible: he lets **later context** and **rules as mentors** choose among candidates.

### 6.2 Context Frame (“Stage, not warehouse”)

Like keeping a few items on your desk, Pablo keeps only what he needs in mind—objects, their relations, the sentence at hand, and current goals. Everything else can be recalled from memory, but it doesn’t crowd thinking.

### 6.3 Predictive brain (“Surprise is the teacher”)

Pablo carries simple expectations (“If focus changes, a focus‑change event should exist”). Any mismatch becomes **surprise**, which powers curiosity, attention, and research priorities.

### 6.4 Attention & gating (“Spotlight management”)

Surprise, novelty, and goal relevance pull items into the spotlight. The RAS limits how many things he can juggle; the thalamus lets only the winners through. This keeps him sharp, not scattered.

### 6.5 Concept graph & cards (“Living notes with hooks”)

Every idea gets a card: definition, knobs that matter, what it’s good for, constraints, examples with citations, open questions, and links to neighbors. The graph is the map; the cards are the pages.

### 6.6 Chunking → Skills (“From steps to moves”)

When a sequence works repeatedly, Pablo names it and gives it slots. Next time, he can apply the whole move in one go—unless the scene differs in a way that matters.

### 6.7 Grounding words (“Language as handles on the world”)

Words are tied to things and actions across many scenes. Grammar and context help narrow meanings; conflicts are resolved with gentle biases (e.g., mutual exclusivity), not dogma.

### 6.8 Association → Causality (“Earn the arrow”)

Pablo won’t call something causal just because it’s nearby. He looks for the **do**: when an action consistently leads to an outcome and clean counterexamples are rare, the link is promoted to **causes**.

### 6.9 Affordances (“See actions, not just objects”)

Objects come with invitations. A PDF affords **Open → Parse**. An icon affords **Click**. Pablo remembers what worked where, so suggestions feel smart, not random.

### 6.10 Researcher loop (“Curiosity with a job to do”)

Gaps, contradictions, and dangling references turn into **questions**. Pablo gathers evidence (docs, files, later the web), synthesizes an answer, proposes a hypothesis, runs a safe test when possible, and updates the concept card—always with citations.

### 6.11 Reasoner (“Coherence without handcuffs”)

Rules act like an expert mentor at Pablo’s shoulder. They nudge interpretations toward sanity and, after the fact, **critique** what didn’t fit. Only the outermost safety layer is hard; inside, he may bend a rule if the novelty is worth it and the slack is minimal and logged.

### 6.12 Planner (anytime) (“Best now, better soon”)

Pablo keeps a best plan on hand and keeps improving it as time allows. He balances the sure path with a learning‑rich path, limited by a risk budget and shaped by his values.

### 6.13 Values & personality (“Why this choice?”)

Pablo’s temperament lives in a small set of dials: coherence, mastery, efficiency, novelty, affiliation. Over time, results nudge these gently, creating a stable style (“curious but careful”).

### 6.14 Memory systems (“Keep the right things”)

* **WM:** a small staging area for roles and fillers.
* **Episodic:** a diary of what happened, with outcomes and surprises.
* **Semantic:** distilled, tidy knowledge—concept cards, rules, skills.

### 6.15 Safety envelope (“Think free, act safe”)

Inside his head, Pablo can explore wildly. At the boundary with the world, everything goes through checks: dry‑runs, sandboxes, whitelists, confirmations, and rate limits.

---

## 7) Unknown Territory Protocol (step‑by‑step)

1. **Name the novelty.** What broke expectations?
2. **Borrow a neighbor.** Which known concept is closest?
3. **Hypothesize.** What facets likely control it?
4. **Micro‑test.** Safe, reversible probe; simulate if needed.
5. **Read & cross‑check.** Pull evidence; compare sources.
6. **Update the card.** Definition, facets, examples, links.
7. **Add soft rules.** As mentors with provenance.
8. **Reflect.** Did surprise drop? Did reliability rise?

---

## 8) Researcher Loop (checklist)

* [ ] Generate question (gap, contradiction, or link to test)
* [ ] Plan sources (local first; web later)
* [ ] Extract evidence (snippets + citations)
* [ ] Synthesize (draft card update + hypothesis)
* [ ] Safe test (if possible) and record episode
* [ ] Consolidate (promote stable findings; prune noise)
* [ ] Log deltas with witnesses

---

## 9) Safety Envelope (practical rules)

* **Dry‑run by default.** Show diffs/effects first.
* **Sandbox first.** Real world only on reversible, low‑impact actions.
* **Whitelists/blacklists.** Explicitly approved paths and networks.
* **Rate limits.** Prevent bursty actions.
* **Escalation.** Ask before irreversible changes.

---

## 10) Explanations & Logs

Every decision should answer:

1. **What did you believe?** (Context frame snapshot)
2. **Which rules/skills applied?** (Names + short natural language gloss)
3. **What surprised you?** (Violations, contradictions)
4. **Why this plan?** (Goal fit, learning value, values bias)
5. **What changed?** (Concept/skill/card updates with witnesses)

---

## 11) Health & KPIs

Track these over time:

* **Constraint satisfaction rate** (non‑safety rules) — trending up
* **Plan success rate** & **latency** per skill
* **Prediction surprise** — trending down per domain
* **Chunk/skill adoption** — fraction of tasks using macros
* **Causal promotions** — associations → causes with 0 contradictions
* **Explainability coverage** — % decisions with complete proofs
* **Knowledge churn** — add/remove ratio; aim for stability after learning phases

---

## 12) Troubleshooting quick map

* **“No plan found.”** Too strict or missing skill → lower rule strictness a notch; allow minimal slack; propose a micro‑skill.
* **“Weird but valid plan.”** Under‑constrained → add a missing constraint or prefer most‑specific schema.
* **Latency spikes.** Too many candidates/WM items → reduce spotlight width; cache partial results; set timeouts.
* **Rule conflicts (L0 vs L1).** L0 wins; demote or scope L1; record counterexamples.
* **Concept explosion.** Enable decay/pruning; keep top‑K per type by utility.

---

## 13) Change management & provenance

* **Version rules and cards** like code; review diffs.
* **Provenance on every edge** (which episodes/sources support it).
* **Nightly consolidation** writes a delta log: added, changed, pruned.
* **Rollback** is always possible by time or version tag.

---

## 14) Glossary (short)

* **Concept graph:** Network of ideas and relations.
* **Concept card:** The page for one concept (definition, facets, examples, questions).
* **Affordance:** What an object invites you to do.
* **Skill (chunk):** A named, reusable sequence with typed slots.
* **Slack:** A controlled rule bend allowed for novelty.
* **Witness:** An episode or citation supporting a claim.

---

## 15) Quick start runbook

1. Set **mode** (Production/Exploration) and tune **risk budget** + **rule strictness**.
2. Start a task; watch **attention** and **surprise** indicators.
3. Approve or adjust the **plan** (exploit vs explore mix).
4. Review **explanations**; accept card/skill updates or send back for more evidence.
5. Check **KPIs** after a session; schedule consolidation if needed.

---

## 16) Roadmap hints (what to add next)

* Web researcher integration with source reliability scoring.
* Small simulators for risky domains (cheap micro‑tests).
* Multi‑agent schemas (basic intent/theory‑of‑mind).
* Natural language **teaching mode** (“show me why,” “teach me this”).
* Visual dashboard for concept graph growth, KPIs, and personality drift.

---

*End of manual v0.1.*
