# AEGIS — Architecture

**Autonomous Execution Guard & Impact Safety**
Runtime security harness for AI agents · MEGATHON'26 Track 1, PS 1

> **Supersedes** the earlier "Warrant" / mandate-drift architecture. That design is preserved in git
> history (commit `4034931`). Design rationale and the research behind this document live in
> [SOLUTION.md](SOLUTION.md); this file describes the system as built.

**Current phase: 0 — foundation.** Application skeleton, configuration, persistence, structured
logging and health endpoints. No enforcement, no agent, no LLM, no frontend.

---

## 1. Principle

> **Capability is not authority.** An agent may be *able* to delete a production database. That
> capability must not automatically carry the *authority* to do so.

AEGIS is middleware on the **tool-call boundary**. The agent proposes actions; AEGIS decides whether
they execute. It is model-agnostic by construction — it inspects proposed actions on the wire, never
model internals — so any agent framework can sit above it and any tool below it.

**The enforcement point sits between the agent and the tools, never between the user and the agent.**
An agent that can reach a tool without crossing this boundary is unprotected.

```
USER ──▶ AI AGENT ──▶ [proposed action] ──▶ AEGIS ──▶ TOOLS ──▶ EXTERNAL SYSTEMS
                                              │
                                              └──▶ AUDIT LOG
```

## 2. Current state (Phase 0)

```
                    ┌──────────────────────────────┐
   HTTP ──────────▶ │  TraceIdMiddleware           │  binds X-Trace-Id
                    ├──────────────────────────────┤
                    │  FastAPI (app/main.py)       │
                    │    GET /api/health           │
                    │    GET /api/version          │
                    ├──────────────────────────────┤
                    │  Schemas (Pydantic)          │
                    │  Config (pydantic-settings)  │
                    │  Logging (JSON, UTC)         │
                    ├──────────────────────────────┤
                    │  SQLAlchemy ORM              │
                    └──────────────┬───────────────┘
                                   ▼
                            SQLite (aegis.db)
                            └─ schema_version
```

Empty-but-declared packages mark where later phases land: `security/`, `execution/`, `agent/`,
`services/`.

## 3. Target pipeline

Every proposed action passes through one deterministic sequence.

```
ACTION PROPOSAL
      │
      ▼
┌─────────────────────────────────────────────────┐
│ 1. ACTION INTERCEPTOR            app/agent/     │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│ ANALYSIS  (independent checks)   app/security/  │
│                                                 │
│   2. Identity & Authorization    who, permitted │
│   3. Intent Boundary             fits the task? │
│   4. Blast Radius                what is hit?   │
│   5. Reversibility               can we undo?   │
│   6. Execution Invariants        hard rules     │
│   7. Trajectory                  where heading? │
└──────────────────────┬──────────────────────────┘
                       ▼  evidence bundle
┌─────────────────────────────────────────────────┐
│ 8. DETERMINISTIC POLICY ENGINE   app/security/  │
│    pure function — no ML on this path           │
└───────┬───────────────┬───────────────┬─────────┘
        ▼               ▼               ▼
      BLOCK          CONFIRM          ALLOW
        │               │               │
        │               ▼               │
        │    ┌────────────────────┐     │
        │    │ 9. HUMAN APPROVAL  │     │
        │    │    with evidence   │     │
        │    └─────────┬──────────┘     │
        │              └────────┬───────┘
        │                       ▼
        │    ┌──────────────────────────────────┐
        │    │ 10. TRANSACTIONAL EXECUTOR       │  app/execution/
        │    │  SNAPSHOT → EXECUTE → VERIFY     │
        │    └────────┬──────────────┬──────────┘
        │             ▼              ▼
        │          COMMIT        ROLLBACK
        │             │              │
        ▼             ▼              ▼
┌─────────────────────────────────────────────────┐
│ 11. TAMPER-EVIDENT AUDIT LOG (hash-chained)     │
└─────────────────────────────────────────────────┘
```

### Decision function

```
decide(authorization, intent_match, impact, reversibility,
       invariants_violated, escalation_score) → ALLOW | CONFIRM | BLOCK
```

- Any **invariant violation** → `BLOCK`, non-overridable.
- **Unauthorized**, or **intent mismatch** on a non-read action → `BLOCK`.
- **Irreversible** with non-trivial impact → `CONFIRM`, never silent `ALLOW`.
- **High blast radius** → `CONFIRM` with evidence, regardless of action category.
- Rising **escalation score** lowers the threshold at which `CONFIRM` applies.
- Otherwise → `ALLOW`.

**Fail-safe direction:** if an analyzer is unavailable, the decision degrades toward `CONFIRM` —
never toward `ALLOW`. No irreversible action is ever authorised by a machine-learning judgement alone.

### Blast radius is measured, not estimated

Classification by *action category* is the flaw that let real incidents through — `delete_records`
scores the same whether it removes 3 rows or 3 million. AEGIS measures the resolved target set:

| Class | Method | Fidelity |
| --- | --- | --- |
| Database | `SELECT COUNT(*)` with the action's own predicate before executing | measured |
| Filesystem | Resolve glob, `~`, and quoting ourselves; enumerate actual targets | measured |
| External / API | Declared effect model from the tool registry | declared, irreversible by default |

## 4. Layout

```
backend/
  app/
    main.py             FastAPI app, middleware, system routes
    config.py           pydantic-settings; env-driven
    db.py               engine, session factory, init_db
    models.py           ORM models
    schemas.py          request/response contracts
    logging_config.py   JSON logging, trace context, UTC helpers
    security/           analysis + policy engine     (Phase 1)
    execution/          transactional execution      (Phase 2)
    agent/              interceptor, tool adapters   (Phase 3)
    services/           orchestration                (Phase 1)
    tests/              pytest suite
frontend/
  app/ components/ lib/   operator console           (later phase)
docs/
```

## 5. Cross-cutting

**Configuration** — environment only, via `pydantic-settings`. `.env` is gitignored; `.env.example`
documents every key. No secrets in code, and none required in Phase 0.

**Logging** — one JSON object per line, always carrying `timestamp`, `level`, `service`, `trace_id`,
`event`. The message *is* the event name (`db.initialized`); variable data goes in `context`. UTC
throughout, ISO-8601 with a `Z` suffix. This is the substrate the audit chain is built on.

**Tracing** — a `ContextVar` holds the request's trace id; middleware adopts an inbound `X-Trace-Id`
or generates one, and echoes it on the response. Every log line for that request carries it.

**Persistence** — SQLAlchemy 2.0 declarative ORM. SQLite for development and the demo; the engine
layer is dialect-agnostic so Postgres is a config change. `init_db()` is idempotent.

**Testing** — pytest. The suite redirects `DATABASE_URL` to a temporary file before importing the
app, so tests never touch `aegis.db`.

## 6. Constraints

| Constraint | Rule |
| --- | --- |
| Determinism | The security decision contains no ML. The LLM proposes and explains only |
| Model agnosticism | Enforce at the tool-call boundary; no dependency on any agent framework |
| Fail-safe | Degrade toward `CONFIRM`, never toward `ALLOW` |
| Agent identity | The agent carries its own scoped identity; never inherits an operator's privileges |
| Audit integrity | Append-only, hash-chained, not writable from the agent path |
| Offline capable | The decision path runs locally with no network dependency |
| Approval quality | Every confirmation carries evidence — approval fatigue is a security failure |
| Time | UTC internally, always |

## 7. Phases

| Phase | Scope | Status |
| --- | --- | --- |
| **0** | Foundation: app skeleton, config, DB, logging, health/version, tests | ✅ complete |
| 1 | Action model, identity/authorization, invariants, policy engine, audit log | planned |
| 2 | Blast radius, reversibility, transactional execution, approvals | planned |
| 3 | Agent integration, interceptor, trajectory analysis | planned |
| 4 | Operator console | planned |
