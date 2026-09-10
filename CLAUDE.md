# MEGATHON'26 — Project Guide

Read this first. It tells Claude Code how to work in this repo.

## What this is

Hackathon workspace for MEGATHON'26. Building **AEGIS** — Autonomous Execution Guard & Impact Safety — against Track 1, PS 1.
See [docs/SOLUTION.md](docs/SOLUTION.md) for the design and [README.md](README.md) to run it.

## Ground rules

1. **Never invent the problem statement.** `docs/PROBLEM.md` holds the organisers' verbatim text. Do not edit it.
2. **Phases are sequential.** Do not start the next phase until the current one is accepted.
3. **Docs are the source of truth.** Before starting work, read `docs/STATE.md`. After finishing a unit of work, update it.
4. **Decisions are append-only.** Supersede entries in `docs/DECISIONS.md`; do not rewrite them.
5. **Scope is the enemy.** This is a timeboxed hackathon — prefer one flow that works end to end over four that half-work.
6. Keep `docs/TODO.md` current. It is the shared queue.

## Documents

| File | Purpose |
| --- | --- |
| `docs/PROBLEM.md` | Official statement, constraints, judging criteria, our restatement |
| `docs/RESEARCH.md` | Prior art, datasets, APIs, feasibility notes |
| `docs/SOLUTION.md` | What we are building and why |
| `docs/ARCHITECTURE.md` | System architecture and target pipeline |
| `docs/API.md` | Endpoint reference |
| `docs/STATE.md` | Where the project stands right now — read on every session start |
| `docs/DECISIONS.md` | Append-only decision log |
| `docs/TODO.md` | Task queue |

## Layout

```
megathon26/
├── .claude/    # Claude Code project config
├── backend/    # FastAPI application (app/, tests/)
├── frontend/   # operator console - not implemented yet
└── docs/       # planning and reference documents
```

## Commands

Run from `backend/`:

| Command | Purpose |
| --- | --- |
| `python -m pip install -r requirements.txt` | Install dependencies |
| `python -m uvicorn app.main:app --reload` | Run the dev server |
| `python -m pytest` | Run the test suite |

Stack: Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite.

## Conventions

- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`)
- Branch: `main`
- Write commit messages that say what changed and why.
