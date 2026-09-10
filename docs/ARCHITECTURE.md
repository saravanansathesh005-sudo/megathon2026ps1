# Architecture — Warrant

**Target:** Track 1, PS 1 — Runtime Security Harness for AI Agents (decision 005)
**Status:** designed, not built. No code exists. Ratify before implementing.

---

## A. One-line pitch

> **Warrant is a model-agnostic runtime harness that stops agent actions not by asking whether they
> look malicious, but by asking whether they are still inside the mandate the session was opened
> under — which is the only question that has an answer when there is no attacker.**

## B. Problem

Organisations harden models — system prompts, output filters, jailbreak red-teaming — and build,
in the brief's words, a well-defended front door on a house with no walls. The damaging failures
do not look like attacks. They are sequences of individually reasonable requests whose scope widens
over days, or authorized agents acting on permissions nobody revoked. In August 2026 an agent wired
to a production Supabase ran a migration meant for a disposable test database. There was no
adversarial prompt. There was nothing for a prompt filter to catch.

## C. Target users

**Primary:** platform and security engineers at organisations running agents with write access to
production systems. **Secondary:** the developer who gets the confirmation prompt. **Tertiary:** the
compliance function that needs an auditable record of what an agent did and under whose authority.

## D. User pain

Today the choice is binary: give the agent broad credentials and hope, or restrict it until it
cannot do useful work. There is no instrument that distinguishes an agent doing its job from the
same agent doing far more than its job, because from the tool boundary both look like valid calls
from an authorized principal.

## E. Weaknesses of existing solutions

Zenity, Lasso, Noma and WitnessAI all enforce **per action**, framed as threat detection. APort
(Apache-2.0) specifies agent identity and per-call ALLOW/DENY with signed decision records — good
prior art, and **stateless across calls by design**. Ask any of them "is this action malicious?"
about a slow escalation and the answer is no, every time, correctly. None carries session state
forward, so none can see a trajectory. See `docs/RESEARCH.md` Part 4.

## F. Unique insight

**Mandate drift, not threat detection** (decision 006). Every session opens under a mandate. Damage
correlates with the *distance* between that mandate and what the agent is actually doing now — a
quantity that exists whether or not an attacker does. One mechanism catches both the patient
adversary and the well-meaning agent with stale permissions.

## G. Proposed solution

Middleware on the tool-call boundary. Three enforcement layers, unified by one primitive: the
**Warrant** — a scoped, expiring, signed capability grant derived from the session's mandate.

## H. Key features

1. **Warrant issuance** — every action carries verified principal, scope and expiry.
2. **Reversibility gate** — actions classified R0–R3; R3 requires explicit human confirmation.
3. **Trajectory monitor** — cross-session drift scoring; confirmation thresholds rise with drift.
4. **Operator console** — live drift graph, gate queue with human-readable reasons, audit trail.
5. **Mandate widening** — a legitimate user who confirms at the gate *expands* the envelope rather
   than fighting it. This is what makes it not a wall.
6. **Replayable scenario harness** — attack and legitimate trajectories runnable on demand.

## I. AI architecture

| Component | Technique | Authority |
| --- | --- | --- |
| Drift scorer | Local sentence embeddings; cosine distance between mandate vector and rolling action-sequence vector, combined with deterministic features (new resource classes touched, privilege delta, blast-radius delta) | **Advisory** — moves a threshold, never decides |
| Reversibility classifier | LLM, first-pass only, for tools absent from the registry; result cached and human-reviewable | **Advisory** — unavailable ⇒ default R2 |
| Everything else | Deterministic code | **Authoritative** |

Per decision 007: **no irreversible action is ever authorised by an ML judgement alone.**

## J–K. Technical architecture and components

```
   agent runtime
        │  tool call (MCP wire protocol)
        ▼
┌───────────────────────────────────────────────┐
│  WARRANT PROXY            (FastAPI, stateless)│
│  1 authorization  → warrant valid? in scope?  │  ~2ms   deterministic
│  2 reversibility  → registry lookup → R0..R3  │  ~1ms   deterministic
│  3 gate decision  → f(class, drift, policy)   │  ~1ms   deterministic
└───────┬───────────────────────────────┬───────┘
        │ allow                         │ gate
        ▼                               ▼
    tool server              confirmation queue → operator console
        │                               │
        └──────────► append-only audit log ◄──┘
                            │
                  ┌─────────┴──────────┐
                  │ TRAJECTORY WORKER  │  async, off the hot path
                  │ embeddings + drift │
                  └────────────────────┘
                            ▼
                  Postgres + pgvector
```

Model-agnostic by construction: we sit on the MCP wire, not inside any model or framework. A thin
SDK decorator covers direct (non-MCP) tool calls.

## L. Data flow

1. Session opens → mandate declared or inferred-then-confirmed → warrant minted (principal, scope, expiry).
2. Tool call intercepted. Warrant validated; out-of-scope → deny.
3. Action classified R0–R3 from the registry; unknown → classifier → cache; classifier down → R2.
4. Gate: `decide(class, drift_score, policy)`. R0/R1 pass. R3 always confirms. R2 confirms iff drift ≥ θ.
5. Decision + rationale appended to the audit log. Action forwarded or queued.
6. Worker updates the session's drift vector asynchronously; next call reads the new score.
7. Human confirmation at a gate **widens the mandate** and re-mints the warrant.

## M. Database design

- `principals`, `sessions` (mandate text + vector, opened_at, warrant), `actions` (session_id, tool,
  resource, class, drift_at_time, decision, rationale), `tool_registry` (tool → class, source:
  manual | classified | confirmed), `gates` (action_id, state, resolver, resolved_at),
  `audit_log` (append-only; insert-only grant, no UPDATE/DELETE).
- pgvector on `sessions.mandate_vec` and a rolling `sessions.action_vec`.

## N. API design

`POST /v1/session` · `POST /v1/action` (the hot path; returns `allow` | `deny` | `gate`) ·
`POST /v1/gate/{id}/resolve` · `GET /v1/session/{id}/trajectory` · `GET /v1/audit`.

## O. Model selection

Local embedding model (`all-MiniLM-L6-v2` class, ~90MB, CPU, ~10ms) — chosen **because** it removes
the network from the enforcement path. Hosted LLM for reversibility classification only, off the hot
path, cached, with a deterministic fallback. See `docs/RESEARCH.md` Part 5.

## P. Security considerations

The harness is the highest-value target in the deployment: it holds the policy and the audit log.
Append-only audit (insert-only DB grant). No policy mutation reachable from the agent path. Warrants
signed and expiring. Fail-closed for R3 if the policy store is unreachable. **Not claimed:** hardened
to production standard in 24 hours.

## Q. Failure handling

| Failure | Behaviour |
| --- | --- |
| Drift scorer down | Reversibility gate still authoritative; R3 still confirms; console shows degraded |
| Classifier down / unknown tool | Default **R2** (confirm). Never allow-by-default |
| Policy store unreachable | Fail-closed for R3, fail-open + log for R0/R1 |
| No mandate establishable | Degrade to reversibility gating only, and say so in the console |
| No network | Everything above runs locally. This is a requirement, not a convenience |
| Agent bypasses the proxy | Unprotected — stated honestly. Same trust assumption as an egress proxy |

## R. MVP scope (24 hours)

MCP proxy intercepting tool calls · warrant issuance + scope check · reversibility registry
hand-authored for ~15 demo tools + LLM fallback · drift scorer (deterministic features + embedding
distance) · console with drift graph, gate queue, audit trail · three scripted replayable scenarios ·
evaluation script reporting attack-stop rate and false-gate rate.

## S. Features we will NOT build

Real IdP/OIDC integration · multi-tenancy · full MCP spec coverage · Kubernetes/HA · mobile · policy
DSL with a UI editor · learned reversibility from rollback telemetry · anything requiring an external
dataset. Each of these is a legitimate future item and a fatal 24-hour distraction.

## T. 24-hour plan

| Hours | Work | Gate |
| ---: | --- | --- |
| 0–1 | Ratify PS. Roles assigned. Repo + deploy skeleton pushed | Deploy pipeline green |
| 1–3 | MCP proxy passing traffic through, unmodified | A tool call round-trips through us |
| 3–5 | Warrant issuance + scope check + audit log writing | Layer 1 blocks an out-of-scope call |
| 5–8 | Reversibility registry + gate; confirmation queue | Layer 2 gates a DROP |
| 8–10 | **Scenario 3 (no-attacker) end-to-end. Screen-record it.** | **First recorded fallback exists** |
| 10–14 | Trajectory worker: embeddings, drift score, threshold coupling | Drift rises across a scripted session |
| 14–17 | Scenarios 1 and 2; mandate widening on confirm | Legit escalation passes without a block |
| 17–20 | Console: drift graph, gate queue, audit view (decision 008) | Readable from the back of a room |
| 20–21 | Evaluation script; measure both rates; measure p50/p95 latency | **Real numbers on the slide** |
| 21–22 | **Feature freeze.** Integration, seed reset, re-record demo | Full run from clean state, twice |
| 22–24 | Deck, pitch rehearsal, Q&A drill against `RESEARCH.md` Part 6 | Every member can answer Q1–Q5 |

**Hour 12 checkpoint:** if Layer 3 drift scoring is not producing a usable signal, cut it and pivot
to concept 2 (Provenance, T1-PS2) on the same proxy substrate — decision 005 names this as the
insurance policy. Deciding this at hour 12 is survivable; at hour 20 it is not.

## U. Demo storyline

Three scenes, ~4 minutes, escalating in sophistication.

1. **The patient attacker.** Three sessions over "three days," each request individually reasonable —
   read logs, then read config, then export credentials. Baseline agent complies and exfiltrates.
   Warrant on: drift climbs visibly on the graph, the R3 export is gated, blocked with a readable
   reason. *Proves: cross-session trajectory is real.*
2. **The legitimate engineer.** Genuinely escalating incident-response work. Drift climbs the same
   way — the engineer confirms once at the gate, the mandate widens, work continues. *Proves: not a
   wall. This is the scene most teams will not have.*
3. **No attacker at all.** The Opus-5 case: a migration command against a production-tagged resource.
   No adversarial prompt, no intrusion, nothing to detect. The reversibility gate catches it anyway.
   *Proves: we cover the majority failure mode that every funded competitor's framing misses.*

Close on the evaluation numbers — attack-stop rate **and** false-gate rate, side by side.

## V. Impact metrics

Attack-stop rate on the scenario suite · **false-gate rate on legitimate escalating trajectories**
(the number that answers "is it just a wall?") · reversibility classification accuracy vs. the manual
registry · p50/p95 added latency on the synchronous path · marginal cost per action. Report suite
size alongside every rate; it is small and hand-built, and we say so.

## W. Scalability strategy

Proxy is stateless — scale horizontally. Session state keyed by principal in Postgres. First
bottleneck is embedding computation, which is why drift scoring is asynchronous by design rather
than retrofitted. At 10×: batch embeddings, move the worker to a queue, partition sessions by
principal hash. The synchronous path stays a hash lookup and a policy evaluation at any scale.

## X. Deployment strategy

Docker Compose for the judged demo — runs on a laptop with the wifi off. Managed Postgres + a
push-to-deploy host for the hosted instance, live by hour 12. On-prem is the realistic enterprise
shape and the design assumes it.

## Y. Cost estimation

Deterministic path: zero marginal cost. Embeddings: local CPU, no tokens. Classifier: once per new
tool, then cached — effectively zero at steady state. Hackathon spend: managed Postgres free tier,
hosting free tier, a small classifier budget. **A security control priced per action does not survive
production traffic** — that is a design constraint, not an afterthought.

## Z. Future scope

A real cross-session escalation benchmark (ours is too small to generalise — the honest limitation).
Reversibility learned from actual rollback telemetry instead of a hand-built registry. Formal
verification of the fail-closed property. Multi-agent trajectories, where the mandate is shared
across a fleet and drift is a property of the group.

---

## Non-functional requirements (checked against the brief)

| Requirement | Answer |
| --- | --- |
| Latency budget | Sync path <10ms p95; drift async |
| AI failure | Advisory only; deterministic fallback; never allow-by-default |
| API failure | Local-first; no network on the enforcement path |
| Bad input | Malformed call → deny + audit; unknown tool → R2 |
| Offline | Full enforcement runs offline. Demoable with wifi off |
| Cost per action | ~zero marginal at steady state |
| Data provenance | Self-authored trajectories from documented incident patterns; stated as such |
| Privacy | Action metadata and resource IDs, not payloads; configurable retention |
| Scale bottleneck | Embedding computation, named and already isolated |
| Demo reliability | Seeded state, replayable scenarios, recording made at hour 10 |

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Proxy / API | Python + FastAPI | MCP SDK maturity; team familiarity |
| Worker | Python, same image | No second runtime |
| Store | Postgres + pgvector | Relational audit + vectors in one engine |
| Embeddings | Local MiniLM-class | Removes the network from the hot path |
| Console | React + Vite | Fast; charting for the drift graph |
| Deploy | Docker Compose (demo) + managed host | Runs offline on a laptop |

## Directory layout (planned, not created)

```
src/proxy/       MCP interception, warrant validation, gate decision
src/policy/      deterministic rules, reversibility registry
src/trajectory/  embeddings, drift scoring worker
src/console/     React operator UI
src/scenarios/   the three demo trajectories, replayable
tests/           policy unit tests + the evaluation suite
```

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Drift scoring produces no usable signal | Kills the wedge | Hour-12 checkpoint; pivot to concept 2 on the same substrate |
| Judge names Zenity/Lasso/APort | Credibility | Every member can state the difference in one sentence (`RESEARCH.md` Part 6, Q3) |
| "It's just RBAC" | Undermines innovation | Rehearsed answer, Q4 |
| Console too dense to read on stage | Loses a criterion | Decision 008 budgets 3 hours |
| Scope creep into Layers 1–2 polish | Runs out the clock | Layers 1–2 are table stakes; hours go to Layer 3 and the console |
| Cited stat proves false | Fatal in a security track | Pinecone claim already struck (`RESEARCH.md` Part 0) |
