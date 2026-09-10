# Architecture

> Status: **NOT YET DESIGNED** — no framework or stack chosen until the problem statement lands.
>
> **2026-09-10:** A full architecture was requested but cannot honestly be produced — the problem
> statement has not been received (see `docs/STATE.md`). System design follows from the domain, and
> inventing one would produce a diagram that survives exactly until the real statement contradicts it.
> The domain-independent parts that *can* be fixed now are listed at the bottom of this file; the
> rest is filled in Phase 6, in one pass, once `docs/PROBLEM.md` is complete.

## System overview

_(diagram or description)_

## Component breakdown

| Component | Responsibility | Owner |
| --- | --- | --- |
|  |  |  |

## Data flow

1. 

## Data model

_(entities and relationships)_

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | TBD |  |
| Backend | TBD |  |
| Data store | TBD |  |
| ML / AI | TBD |  |
| Hosting | TBD |  |

## Interfaces / contracts

_(API endpoints, message shapes, CLI surface)_

## Directory layout

```
megathon26/
├── .claude/   # Claude Code project config
├── docs/      # problem, research, architecture, state, decisions, todo
├── src/       # application code (empty until stack is chosen)
└── tests/     # tests (empty until there is code)
```

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
|  |  |  |

---

## Non-functional requirements (domain-independent — answer these whatever we build)

Every one of these maps to a judging criterion, and every one is a question a jury asks. Drafting
them before the domain is known costs nothing and removes them from the critical path.

| Requirement | The question to answer | Criterion it serves |
| --- | --- | --- |
| Latency budget | What is the p95 for the main user action, and where does the time go? | Technical Excellence |
| Failure path — AI | What does the user see when the model is wrong or unavailable? | Jury Q&A, UX |
| Failure path — API | What does the demo do when the venue wifi dies? | Prototype Functionality |
| Bad input | Empty, malformed, adversarial, wrong-language input — what happens? | Technical Excellence |
| Offline mode | Can the core flow run with no internet at all? | Feasibility, Q&A |
| Cost per action | Token/API cost of one user action, and at 10k users/day | Scalability |
| Data provenance | Where does every piece of data come from, and under what licence? | Feasibility |
| Privacy | What personal data do we touch, where does it live, can we avoid holding it? | Real-World Impact |
| Scale bottleneck | The *first* thing that breaks at 10×, named specifically | Scalability |
| Demo reliability | Seeded data + recorded fallback + a rehearsed happy path | Presentation |

**Standing rule:** no external dependency enters the build without a named offline fallback.

## Domain-independent stack (choose before the event, per decision 003)

| Layer | Choice | Status |
| --- | --- | --- |
| Auth | Managed provider — never hand-rolled | TBD, decide pre-event |
| Database | Managed Postgres free tier | TBD, decide pre-event |
| Deploy | Push-to-deploy host; live by hour 12 | TBD, decide pre-event |
| LLM access | Primary + fallback on a *different* provider + response cache | TBD, decide pre-event |
| CI | Minimal — build + typecheck on push | TBD, decide pre-event |
