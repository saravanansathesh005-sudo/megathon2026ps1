# Decision Log

Append-only. One entry per decision. Never rewrite history — supersede instead.

Format:

```
## NNN — <title>
- **Date:**
- **Status:** proposed | accepted | superseded by NNN
- **Context:** what forced the decision
- **Decision:** what we chose
- **Alternatives:** what we rejected and why
- **Consequences:** what this locks us into
```

---

## 001 — Start from an empty, documentation-first workspace
- **Date:** 2026-09-10
- **Status:** accepted
- **Context:** MEGATHON'26 problem statement is not released yet. Picking a stack now risks building the wrong thing and wasting hackathon hours on a rewrite.
- **Decision:** Create only the directory skeleton and planning docs. No framework, no dependencies, no scaffolding, no invented problem statement.
- **Alternatives:** Pre-scaffold a Next.js/FastAPI starter "to save time" — rejected, since a wrong guess costs more than it saves and biases the solution toward the tool.
- **Consequences:** Day-1 work starts with a stack decision. `src/` and `tests/` stay empty until then.

---

## 002 — Do not run the strategy pipeline against a guessed problem statement
- **Date:** 2026-09-10
- **Status:** accepted
- **Context:** A full eight-phase strategy pass (decomposition, five research tracks, ten scored solution concepts, adversarial review, blueprint, twenty jury answers) was requested on the stated basis that the official statement had been received. It had not: `docs/PROBLEM.md` was byte-identical to the scaffold from commit `d457a0a`, the working tree was clean, and no statement file existed anywhere on disk.
- **Decision:** Refuse to generate Phases 1–7. Report the blocker, and spend the time instead on the work that is genuinely domain-independent: organizer intelligence, rubric decode, and the hour-0 research playbook.
- **Alternatives:**
  - *Guess a plausible domain (AI for healthcare / agri / civic) and run the pipeline on it.* Rejected. The output would be indistinguishable in form from real strategy while being worthless, and would be actively harmful — the team would rehearse the wrong pitch and arrive over-confident. It also directly violates rule 1 of `CLAUDE.md`.
  - *Return only "you forgot to paste it" and stop.* Rejected as needlessly thin: a meaningful slice of the work does not depend on the domain.
- **Consequences:** Phases 1–7 remain undone until the statement arrives. In exchange, hour 0 of the hackathon starts with the search strategy, rubric model and readiness backlog already written.

---

## 003 — Optimize for readiness, not for a pre-built solution
- **Date:** 2026-09-10
- **Status:** accepted
- **Context:** Megathon 2025's official site states **"The problem statement will be given on the spot"** ([megathon.in](https://megathon.in/)). Statements are sponsor-authored, narrow and vertical — e.g. 2023's "LLM-based medical query system for edge devices" ([src](https://blogs.iiit.ac.in/monthly_news/megathon-2023/)). PREDICTION (high confidence): '26 follows the same pattern.
- **Decision:** Treat pre-event work as building *readiness*, not a solution. Invest only in assets that hold regardless of domain: a domain-independent scaffold (auth, DB, deploy, CI, component library, LLM wrapper with caching + provider fallback, seed-data loader), a rehearsed hour-0 decomposition drill, and a reusable pitch skeleton.
- **Alternatives:**
  - *Pre-build a full solution for the most likely domain.* Rejected — with 3–4 sponsor statements to choose from, the hit probability is low and a wrong bet burns the whole runway.
  - *Prepare nothing and improvise on the day.* Rejected — the domain-independent 3–5 hours are free money against 1,100 competitors.
- **Consequences:** We accept that the *problem-specific* work all happens inside the 24 hours. Success therefore depends disproportionately on decomposition speed in the first 90 minutes and on demo reliability, which is where the readiness backlog in `docs/TODO.md` is aimed. One bounded exception is allowed: pre-reading Bhashini API docs and one on-device inference runtime, because both sponsor archetypes recur.

---

## 004 — Verify the organizer identity before trusting the intelligence
- **Date:** 2026-09-10
- **Status:** proposed *(needs team confirmation)*
- **Context:** All organizer research assumes this is E-Cell IIIT Hyderabad's Megathon, inferred from the 24-hour format, Grand Finale framing, jury Q&A and Indian context. A different "Megathon 2026" exists — a Rosetta Commons protein-design event in Puerto Rico ([src](https://rosettacommons.org/2026/03/19/megathon-2026-one-week-two-hackathons-10-tutorials-and-16-curated-datasets/)).
- **Decision:** Treat Part 1 of `docs/RESEARCH.md` as provisional until a team member confirms the organizer from the registration email or event page.
- **Alternatives:** Assume it silently — rejected; every downstream inference about sponsors, format and judging would inherit an unexamined error.
- **Consequences:** A five-minute confirmation either promotes the whole of Part 1 from ASSUMPTION to FACT, or invalidates it cleanly before we act on it.
