# MEGATHON'26 — Project Guide

Read this first. It tells Claude Code how to work in this repo.

## What this is

Hackathon workspace for MEGATHON'26. **The official problem statement has not been released yet.**
Until it is, this repo holds planning documents only — no application code.

## Ground rules

1. **Never invent the problem statement.** `docs/PROBLEM.md` is filled only with the organisers' verbatim text.
2. **No framework or dependency until the stack decision is made** and recorded in `docs/DECISIONS.md`.
3. **Docs are the source of truth.** Before starting work, read `docs/STATE.md`. After finishing a unit of work, update it.
4. **Decisions are append-only.** Supersede entries in `docs/DECISIONS.md`; do not rewrite them.
5. **Scope is the enemy.** This is a timeboxed hackathon — prefer one flow that works end to end over four that half-work.
6. Keep `docs/TODO.md` current. It is the shared queue.

## Documents

| File | Purpose |
| --- | --- |
| `docs/PROBLEM.md` | Official statement, constraints, judging criteria, our restatement |
| `docs/RESEARCH.md` | Prior art, datasets, APIs, feasibility notes |
| `docs/ARCHITECTURE.md` | System design, stack, data model, contracts |
| `docs/STATE.md` | Where the project stands right now — read on every session start |
| `docs/DECISIONS.md` | Append-only decision log |
| `docs/TODO.md` | Task queue |

## Layout

```
megathon26/
├── .claude/   # Claude Code project config
├── docs/      # planning documents
├── src/       # application code (empty until stack is chosen)
└── tests/     # tests (empty until there is code)
```

## Commands

None yet — no build tooling exists. Add them here the moment a stack is chosen.

## Conventions

- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`)
- Branch: `main`
- Write commit messages that say what changed and why.
