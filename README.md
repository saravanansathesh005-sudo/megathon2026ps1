# AEGIS

**Autonomous Execution Guard & Impact Safety** — a runtime security harness for AI agents.

MEGATHON'26 · Track 1, PS 1

> AI proposes. AEGIS evaluates. Humans decide. Systems execute safely.

Existing agent security asks whether an agent is *allowed* to perform an action.
AEGIS asks what that action will **cause** — before allowing it to happen.

---

## Status: working mini prototype

Deterministic security engine, controlled execution, and a console that renders only
backend values. 104 tests passing.

## Run it

Backend:

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Frontend (separate terminal):

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000> and sign in as `viewer`, `editor`, `admin` or `secadmin`
(passwords are `<name>123`, e.g. `admin123`). API docs at <http://localhost:8000/docs>.

## Tests

```bash
cd backend
python -m pytest
```

## Demo

| Scenario | Sign in as | Type | Expect |
| --- | --- | --- | --- |
| 1. Privilege escalation | `viewer` | `Delete all users` | authorization DENIED, intent OUT_OF_SCOPE, INV-001/003/004 fail, blast 7.1 HIGH → **BLOCK** |
| 2. Legitimate work | `admin` | `Clean the disposable test table` | **REQUIRE_CONFIRMATION** → approve → snapshot → execute → VERIFIED → committed |
| 3. Trajectory attack | `editor` | `Show me users`, `Show me orders`, `Export the users table`, `Drop the users table` ×2 | score climbs 0 → 12 → 19, decisions harden to **BLOCK** |

`reset demo` in the sidebar restores the dataset.

## Configuration

Every setting comes from the environment. See [`backend/.env.example`](backend/.env.example).

| Variable | Default | Purpose |
| --- | --- | --- |
| `SERVICE_NAME` | `aegis-backend` | Service identifier in logs |
| `VERSION` | `0.1.0` | Reported by `/api/version` |
| `ENVIRONMENT` | `development` | Deployment environment |
| `DATABASE_URL` | `sqlite:///./aegis.db` | SQLAlchemy connection URL |
| `LOG_LEVEL` | `INFO` | Root log level |
| `API_PREFIX` | `/api` | Route prefix |

`.env` is gitignored. **No secrets are required in Phase 0, and none are committed.**

## Layout

```
backend/
  app/
    main.py            FastAPI app, middleware, system routes
    config.py          settings
    db.py              engine, sessions, init_db
    models.py          ORM models
    schemas.py         request/response contracts
    logging_config.py  JSON logging, trace context, UTC helpers
    security/          analysis + policy engine    (Phase 1)
    execution/         transactional execution     (Phase 2)
    agent/             interceptor, tool adapters  (Phase 3)
    services/          orchestration               (Phase 1)
    tests/             pytest suite
frontend/              operator console            (later phase)
docs/
```

## Logging

One JSON object per line. Every record carries `timestamp`, `level`, `service`, `trace_id`, `event`.
Times are UTC, ISO-8601, `Z`-suffixed.

```json
{"timestamp":"2026-09-10T11:43:07.501940Z","level":"INFO","service":"aegis-backend","trace_id":"e911bf75d2cc4a25a3402090acf8e772","event":"db.initialized","context":{"tables":["schema_version"],"schema_version":1}}
```

Pass `X-Trace-Id` on a request to correlate it end to end; AEGIS echoes it on the response.

## Documentation

| Document | Contents |
| --- | --- |
| [docs/SOLUTION.md](docs/SOLUTION.md) | What we are building and why |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture and target pipeline |
| [docs/API.md](docs/API.md) | Endpoint reference |
| [docs/PROBLEM.md](docs/PROBLEM.md) | Official problem statement (verbatim) |
| [docs/RESEARCH.md](docs/RESEARCH.md) | Incident case file, prior art, competitors |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Append-only decision log |
| [docs/STATE.md](docs/STATE.md) | Current project state |
| [docs/TODO.md](docs/TODO.md) | Task queue |

## Roadmap

| Phase | Scope | Status |
| --- | --- | --- |
| **0** | Foundation | ✅ complete |
| 1 | Action model, authorization, invariants, policy engine, audit log | planned |
| 2 | Blast radius, reversibility, transactional execution, approvals | planned |
| 3 | Agent integration, interceptor, trajectory analysis | planned |
| 4 | Operator console | planned |
