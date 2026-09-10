# AEGIS API

**Base URL:** `http://localhost:8000`
**Prefix:** `/api` (configurable via `API_PREFIX`)
**Content type:** `application/json`
**Interactive docs:** `/docs` (Swagger UI) · `/redoc` · `/openapi.json`

All timestamps are **UTC**, ISO-8601, with a trailing `Z`.

---

## Tracing

Every request is assigned a correlation id.

| Header | Direction | Behaviour |
| --- | --- | --- |
| `X-Trace-Id` | Request *(optional)* | If supplied, AEGIS adopts it for the request |
| `X-Trace-Id` | Response *(always)* | The id used, generated if none was supplied |

The same id appears in every log line emitted while handling the request, and
will key the audit chain in later phases.

---

## Endpoints

### `GET /api/health`

Liveness plus dependency status. Use for readiness probes.

**Response `200 OK`**

```json
{
  "status": "ok",
  "service": "aegis-backend",
  "database": "ok",
  "timestamp": "2026-09-10T11:43:07.926470Z",
  "trace_id": "f843ae1816fd41ee9ac1f733c9288446"
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `status` | `"ok"` \| `"degraded"` | `degraded` when a dependency is unavailable |
| `service` | string | Service identifier |
| `database` | `"ok"` \| `"unavailable"` | Result of a `SELECT 1` probe |
| `timestamp` | string | UTC ISO-8601, `Z` suffix |
| `trace_id` | string \| null | Matches the `X-Trace-Id` response header |

The endpoint returns `200` even when degraded — the body carries the detail, so
a probe can distinguish "process alive" from "dependencies healthy".

```bash
curl -i http://localhost:8000/api/health
```

---

### `GET /api/version`

Build and deployment identity.

**Response `200 OK`**

```json
{
  "service": "aegis-backend",
  "version": "0.1.0",
  "phase": "0 - foundation",
  "environment": "development",
  "schema_version": 1
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `service` | string | Service identifier |
| `version` | string | Semantic version |
| `phase` | string | Project phase |
| `environment` | string | `development` \| `test` \| `production` |
| `schema_version` | int \| null | Applied DB schema version; `null` if uninitialised |

```bash
curl http://localhost:8000/api/version
```

---

## Errors

FastAPI defaults apply in Phase 0.

| Status | Meaning |
| --- | --- |
| `404` | Unknown route |
| `422` | Request validation failed (Pydantic detail body) |
| `500` | Unhandled server error — logged with the request's `trace_id` |

A uniform error envelope arrives with the enforcement endpoints.

---

## Planned (not implemented)

Listed so the surface is predictable; none of these exist yet.

| Phase | Endpoint | Purpose |
| --- | --- | --- |
| 1 | `POST /api/actions/evaluate` | Submit a proposed action, receive `ALLOW` / `CONFIRM` / `BLOCK` with evidence |
| 1 | `GET /api/actions` | Action history with decisions |
| 2 | `POST /api/approvals/{id}/decide` | Resolve a pending confirmation |
| 2 | `GET /api/approvals` | Pending approval queue |
| 3 | `GET /api/audit` | Hash-chained audit trail |
| 3 | `GET /api/audit/verify` | Verify chain integrity |
