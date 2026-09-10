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
