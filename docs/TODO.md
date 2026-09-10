# TODO

> Ordered by what unblocks the most. Everything under "Blocked" stays blocked until the statement lands.

## P0 — Unblock (do today)

- [ ] **Paste the official MEGATHON'26 statement verbatim into `docs/PROBLEM.md`** — or confirm it is released on the spot
- [ ] **Confirm the organizer is E-Cell IIIT Hyderabad** (registration email / event page) → resolves decision 004
- [ ] Confirm the rules we currently only have from the 2025 edition: duration, team size, eligibility, submission format, AI-tool citation policy
- [ ] Confirm the judging format: is there a filtering round before the pitch, and how long is the pitch + Q&A?
- [ ] Get the official judging rubric with weightings, if published

## P1 — Readiness backlog (domain-independent, safe to build now)

Rationale in decision 003. Every hour spent here is an hour not spent on setup during the 24.

- [ ] **Hour-0 drill.** Run a timed dry run on a *past* statement (2023's edge-LLM medical query system works well): statement → decomposition → wedge → scope cut, in 90 minutes. Practise the thing that actually decides the outcome.
- [ ] **Scaffold, unbuilt but chosen.** Lock the domain-independent stack in a decision entry: auth provider, Postgres host, deploy target, CI. Do not write app code — just remove the decisions from the critical path.
- [ ] **LLM wrapper design.** Sketch the contract: primary provider, fallback key on a *different* provider, response cache, deterministic replay mode for the demo. This is the single highest-value pre-built component.
- [ ] **Seed + demo harness plan.** How we load fake-but-plausible data fast, and how we screen-record the demo the moment it works.
- [ ] **Pitch skeleton.** Problem → stakes → live demo → proof → ask. Domain-agnostic; only the nouns change on the day.
- [ ] **Jury Q&A rehearsal set.** The twenty standard questions (why AI, why not a normal app, data source, accuracy, hallucination, cost, latency, security, privacy, scale, competitors, offline, adoption, failure modes) — draft the *structure* of each answer now, fill the specifics on the day.
- [ ] **Role assignment.** Who decomposes, who builds backend, who builds UI, who owns the demo and the deck. Decide before the clock, not at hour 3.
- [ ] *(Bounded exception, decision 003)* Skim Bhashini API docs and one on-device inference runtime — the two recurring sponsor archetypes.

## P2 — Blocked on the problem statement

Runs as a single pass once `docs/PROBLEM.md` is filled.

- [ ] Phase 1 — decomposition (16 points, FACT/INFERENCE/ASSUMPTION/PREDICTION separated)
- [ ] Phase 2 — research Tracks A–E, per the playbook in `docs/RESEARCH.md` Part 3
- [ ] Phase 3 — 10 substantially different concepts, each scored /100 across the 10 criteria
- [ ] Phase 4 — adversarial review of the top 3 (15 attack questions each)
- [ ] Phase 5 — select the winner, with an explicit argument against the other nine
- [ ] Phase 6 — full blueprint A–Z
- [ ] Phase 7 — top 20 jury questions with honest answers
- [ ] Phase 8 — write results into `ARCHITECTURE.md`, and update `RESEARCH.md` Part 4, `STATE.md`, `DECISIONS.md`, `TODO.md`

## P3 — During the 24 hours

- [ ] Deploy something end-to-end by hour 12, however thin
- [ ] Record the demo the first time it works — before adding anything else
- [ ] Freeze features at hour 18; hours 18–24 are integration, rehearsal and the deck
- [ ] Cite AI tool usage in the submission, per the organizer's policy

## Done

- [x] Create workspace skeleton and planning docs (2026-09-10)
- [x] Organizer + format intelligence, sourced (2026-09-10) — `docs/RESEARCH.md` Part 1
- [x] Judging rubric decode (2026-09-10) — `docs/RESEARCH.md` Part 2
- [x] Hour-0 research playbook for Tracks A–E (2026-09-10) — `docs/RESEARCH.md` Part 3
