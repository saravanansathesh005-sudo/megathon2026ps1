# AEGIS — Autonomous Execution Guard & Impact Safety

**Target:** MEGATHON'26 · Track 1, PS 1 — Runtime Security Harness for AI Agents
**Status:** design agreed, prototype not started

> **AI proposes. AEGIS evaluates. Humans decide. Systems execute safely.**
>
> Existing agent security asks whether an agent is *allowed* to perform an action.
> AEGIS asks what that action will *cause* — before allowing it to happen.

---

## 1. Team Discussion Summary

### What we investigated

The team surveyed the current research landscape to test whether our intended contribution was
actually novel. Three findings mattered, and all three were verified against primary sources:

| Work | What it does | Consequence for us |
| --- | --- | --- |
| **AgentSpec** — [arXiv:2503.18666](https://arxiv.org/abs/2503.18666) (Wang, Poskitt, Sun — SMU) | DSL for runtime constraints on LLM agents: triggers, predicates, enforcement (stop / human inspect / replace action / reconsider). Evaluated on code agents, embodied agents, autonomous driving. Prevents >90% of unsafe code-agent executions | **Runtime policy enforcement is solved research.** Our ALLOW/CONFIRM/BLOCK gate is not novel on its own |
| **Securing Agentic AI: From Per-Action Checks to Trajectory Assurance** (2026) | Argues an individual action can be safe while the sequence is unsafe (READ → MODIFY → EXPORT → DELETE). Calls this *behavioral containment* | **Trajectory monitoring is not our unique idea** |
| **TrajGuard / TrajRed** — [arXiv:2608.04018](https://arxiv.org/abs/2608.04018) (Jun 2026) | Runtime governance layer using high-risk trajectories found in red teaming to intervene in live workflows. On AgentDojo, reduces attack success to near zero while preserving benign task utility | Trajectory-based runtime intervention **already ships as research, with strong numbers** |
| **CSTM-Bench** — [arXiv:2604.21131](https://arxiv.org/abs/2604.21131) | Benchmark for cross-session threats; slow-drip injections across 50+ sessions, one innocuous fragment each | Cross-session monitoring is **not** unique either. Useful to us as evaluation data |

### What we decided

1. **Abandon the claim that trajectory monitoring is our innovation.** It is prior art. Our earlier
   working thesis ("mandate drift") is retained only as *one input signal*, not as the core idea.
2. **Move from permission-centric to consequence-centric security.** The question changes from
   *"is this action allowed?"* to *"what will this action affect, how far does the damage reach,
   and can we undo it?"*
3. **Keep the security decision deterministic.** The LLM proposes actions and explains them. It does
   not make the security decision. AEGIS must work even when the agent is compromised or simply wrong.
4. **Claim novelty at the level of composition, not components.** Runtime enforcement, trajectory
   monitoring, authorization, sandboxing and rollback all have prior work. Our defensible claim is
   the integration of **pre-execution consequence analysis + dependency-aware blast radius +
   execution invariants + transactional execution with rollback + evidence-based human approval**
   into a single model-agnostic runtime layer.
5. **Do not build a wall.** PS1 explicitly rejects blanket blocking. Malicious escalation must be
   blocked while legitimate high-impact work proceeds through informed confirmation.

### Why consequence-centric is the right reframe

The public record of agent failures is dominated by incidents with **no attacker at all** — nine
documented destructive incidents across seven vendors between June 2025 and July 2026. Three of them
were not reasoning failures but *mechanical* ones:

- `rm -rf tests/ patches/ plan/ ~/` — the trailing tilde expanded to the home directory
- `rmdir /s /q d:\` — an unquoted path with spaces was truncated, wiping a partition
- A failed `mkdir` misread as success, then files overwritten one by one

No permission model based on *action category* catches these, because the action category is correct.
In Claude Code issue [#10077](https://github.com/anthropics/claude-code/issues/10077) the default
permission system was **on** and did not fire. Only evaluating the **resolved target set and its
consequences** catches this class — which is precisely what AEGIS does.

---

## 2. Proposed Solution

AEGIS is a **model-agnostic runtime security layer that sits between an AI agent and the real tools
it acts on.** Every action the agent proposes is intercepted before execution, analysed for its
predicted consequences, and resolved into exactly one deterministic decision: **ALLOW**, **CONFIRM**
or **BLOCK**. Approved high-impact actions execute transactionally, so they can be verified and
rolled back.

### The shift

| | Existing approach | AEGIS |
| --- | --- | --- |
| Core question | Is this action allowed? | What will this action cause? |
| Authorization | Who can act (RBAC/ABAC) | Who can act **+ does it fit the current task** |
| Risk | Derived from action category | Derived from **predicted impact** |
| Trajectory | Final decision signal | **One input** among several |
| Dependencies | Rarely modelled | **Explicit environment graph** |
| Blast radius | Not a central mechanism | **Core security signal** |
| Human approval | "Approve / Reject" | **Evidence-based**: affected resources, dependencies, recoverability |
| Execution | Isolated or direct | **Snapshot → execute → verify → commit / rollback** |
| Prompt injection | Detect the malicious prompt | **Evaluate the resulting action** — the agent need not detect the attack |
| Decision engine | Sometimes an LLM guard | **Deterministic policy engine**; the LLM only explains |

### The eight questions AEGIS asks before any action

```
        Who requested this?              → Identity
        Are they permitted?              → Authorization
        Does it match the task?          → Intent boundary
        What depends on the target?      → Dependency graph
        What else will be affected?      → Blast radius
        Can we undo it?                  → Reversibility
        Does it break a hard rule?       → Execution invariants
        Where is this sequence heading?  → Trajectory
```

### Core principle

> **Capability is not authority.** An AI agent may be capable of deleting a production database.
> That capability must not automatically carry the authority to do so.

AEGIS does not require the agent to be trustworthy. It makes the system safer **even when the agent
makes the wrong decision** — whether through compromise, misjudgement, or a mis-expanded shell path.

---

## 3. Prototype Plan

### Scope discipline

The full AEGIS design has fifteen components. **All fifteen cannot be built to depth in a hackathon
window.** The prototype builds every component thin enough to complete the pipeline end to end, and
invests depth only in the four that carry the novelty claim.

| Priority | Components | Depth |
| --- | --- | --- |
| **Core — the differentiator** | Dependency graph · Blast-radius analyzer · Reversibility analyzer · Transactional executor with rollback | Full |
| **Essential — completes the pipeline** | Action interceptor · Policy engine · Invariant checker · Evidence-based approval UI · Hash-chained audit log | Working |
| **Thin — table stakes, prior art** | Identity/authorization · Intent boundary check · Trajectory analyzer | Minimal but real |
| **Not building** | General-purpose sandbox · discovered (vs. declared) dependency graph · real IdP integration · multi-tenancy · policy DSL editor | — |

### How consequence analysis is actually implemented

This is the claim most likely to be challenged, so the prototype must be precise about it. **We do
not claim general-purpose simulation.** Consequence analysis is tiered by action class:

| Action class | Method | Fidelity |
| --- | --- | --- |
| **Database** | Execute inside a transaction, measure **actual** affected row counts, then `ROLLBACK` | **Real measurement**, not estimation |
| **Filesystem** | Resolve the command ourselves — glob expansion, `~` expansion, quoting — and enumerate the **actual** target set | **Real measurement.** This is what catches the tilde and truncation cases |
| **External / API** | Declared effect model from a tool registry; no simulation possible | **Declared**, and classified irreversible by default |

The dependency graph in the prototype is **declared and seeded**, not discovered from a live
environment. We state this openly; discovery is future work.

### Demo scenarios

Each maps to a real documented incident, and each exercises a different part of the pipeline.

| # | Scenario | Based on | Proves |
| --- | --- | --- | --- |
| 1 | `rm -rf tests/ patches/ plan/ ~/` — target resolution reveals the home directory, thousands of files, irreversible | Claude Code #10077 / Dec 2025 tilde incident | Permission systems miss this; **resolved-target analysis catches it** |
| 2 | Agent proposes "delete and recreate the production environment"; user asked only to fix an issue. Intent mismatch + production invariant + 23 dependent services | Amazon Kiro, Dec 2025 | **Intent boundary + blast radius**, and privilege inheritance defeated |
| 3 | Authorised DBA performs a genuine production migration. Backup verified → CONFIRM with evidence → snapshot → execute → verify → commit | The "not a wall" requirement in PS1 | **Legitimate high-impact work succeeds** |
| 4 | READ → MODIFY → EXPORT → DELETE escalation across sessions | Trajectory-assurance literature | Trajectory as a **contributing signal**, not the whole decision |

### Evaluation

Report both directions, always together:

- **Block rate** on unsafe scenarios
- **False-confirm / false-block rate** on legitimate work — the number that proves it is not a wall
- **Blast-radius accuracy**: predicted affected resources vs. actual
- **Rollback success rate** on compensatable actions
- **Added latency** (p50/p95) on the synchronous decision path

Where possible, evaluate against **AgentDojo** (used by TrajGuard) and **CSTM-Bench** for the
cross-session case, so numbers sit next to published baselines rather than standing alone.

---

## 4. Architecture

### 4.1 Position in the system

AEGIS is middleware on the **tool-call boundary**. It is model-agnostic by construction: it inspects
proposed actions on the wire, not model internals, so any agent framework can sit above it and any
tool below it.

```
   USER
     │  request
     ▼
   AI AGENT ──────────── proposes, explains; has no execution authority
     │  action proposal
     ▼
╔════════════════════════════════════════════════════════════╗
║                      A E G I S                             ║
║                                                            ║
║   ┌──────────────────────────────────────────────────┐     ║
║   │  1. ACTION INTERCEPTOR                           │     ║
║   └───────────────────────┬──────────────────────────┘     ║
║                           ▼                                ║
║   ┌──────────────────────────────────────────────────┐     ║
║   │  ANALYSIS STAGE   (parallel where independent)   │     ║
║   │                                                  │     ║
║   │   2. Identity & Authorization                    │     ║
║   │   3. Intent Boundary Check                       │     ║
║   │   4. Dependency / Environment Graph              │     ║
║   │   5. Impact & Blast-Radius Analyzer              │     ║
║   │   6. Reversibility Analyzer                      │     ║
║   │   7. Execution Invariant Checker                 │     ║
║   │   8. Trajectory Analyzer                         │     ║
║   └───────────────────────┬──────────────────────────┘     ║
║                           ▼                                ║
║   ┌──────────────────────────────────────────────────┐     ║
║   │  9. DETERMINISTIC POLICY ENGINE                  │     ║
║   │     exactly one verdict, no ML in the decision   │     ║
║   └───────┬─────────────┬────────────────┬───────────┘     ║
║           ▼             ▼                ▼                 ║
║        BLOCK         CONFIRM           ALLOW               ║
║           │             │                │                 ║
║           │             ▼                │                 ║
║           │   ┌──────────────────────┐   │                 ║
║           │   │ 10. HUMAN APPROVAL   │   │                 ║
║           │   │     (with evidence)  │   │                 ║
║           │   └──────────┬───────────┘   │                 ║
║           │       approved│              │                 ║
║           │              └───────┬───────┘                 ║
║           │                      ▼                         ║
║           │   ┌──────────────────────────────────────┐     ║
║           │   │ 11. TRANSACTIONAL EXECUTOR           │     ║
║           │   │   SNAPSHOT → EXECUTE → VERIFY        │     ║
║           │   └──────────┬───────────────┬───────────┘     ║
║           │              ▼               ▼                 ║
║           │        12. COMMIT      13. ROLLBACK            ║
║           │              │               │                 ║
║           │              ▼               │                 ║
║           │   ┌──────────────────────┐   │                 ║
║           │   │ 14. POST-EXECUTION   │   │                 ║
║           │   │     VERIFICATION     │   │                 ║
║           │   └──────────┬───────────┘   │                 ║
║           │              │               │                 ║
║           ▼              ▼               ▼                 ║
║   ┌──────────────────────────────────────────────────┐     ║
║   │  15. TAMPER-EVIDENT AUDIT LOG  (hash-chained)    │     ║
║   └──────────────────────────────────────────────────┘     ║
╚════════════════════════════════════════════════════════════╝
     │  only approved actions
     ▼
   REAL TOOLS / APIs / DATABASE / FILESYSTEM
```

### 4.2 Components

| # | Component | Responsibility | Output |
| --- | --- | --- | --- |
| 1 | **Action Interceptor** | Captures every proposed action before it reaches a tool. The single enforcement seam | Normalised action object |
| 2 | **Identity & Authorization** | Verifies the requesting principal and whether they hold the permission. The **agent carries its own identity** rather than inheriting the operator's | `principal`, `permitted: bool` |
| 3 | **Intent Boundary Check** | Compares the proposed action against the original task. Detects actions exceeding the request ("clean test DB" → "delete production DB") | `intent_match`, divergence reason |
| 4 | **Dependency / Environment Graph** | Models resources and their relationships. Answers *what else touches this?* | Affected resource set |
| 5 | **Impact & Blast-Radius Analyzer** | Computes affected resources, dependency count, data sensitivity, projected damage | `impact_level`, evidence bundle |
| 6 | **Reversibility Analyzer** | Classifies: **Reversible** / **Compensatable** / **Irreversible** | `reversibility_class` |
| 7 | **Execution Invariant Checker** | Hard, non-negotiable rules: never touch production, never access sensitive data, resource-count ceilings, protected paths | `invariants_violated[]` |
| 8 | **Trajectory Analyzer** | Reviews prior actions in this and previous sessions for escalation patterns (READ → MODIFY → EXPORT → DELETE) | `escalation_score` |
| 9 | **Deterministic Policy Engine** | Combines every signal into exactly one verdict. **No ML in this path** | `ALLOW` / `CONFIRM` / `BLOCK` + rationale |
| 10 | **Human Approval Interface** | Presents the action *with evidence*: affected resources, dependency count, sensitivity, recoverability, reason for risk | Approve / Reject + approver identity |
| 11 | **Transactional Executor** | For compensatable actions: `SNAPSHOT → EXECUTE → VERIFY` | Execution result + snapshot handle |
| 12/13 | **Commit / Rollback** | Commit on successful verification; roll back on failure or invariant violation | Final state |
| 14 | **Post-Execution Verification** | Compares actual outcome against predicted outcome | `match: bool`, deviation report |
| 15 | **Tamper-Evident Audit Log** | Append-only, **hash-chained** record of the whole decision trail | Verifiable chain |

### 4.3 Data flow

```
USER REQUEST
   ↓
AI AGENT  →  ACTION PROPOSAL
   ↓
ACTION INTERCEPTOR
   ↓
IDENTITY + AUTHORIZATION ──┐
INTENT CHECK ──────────────┤
DEPENDENCY ANALYSIS ───────┤
BLAST-RADIUS ANALYSIS ─────┼──→  EVIDENCE BUNDLE
REVERSIBILITY CHECK ───────┤
INVARIANT CHECK ───────────┤
TRAJECTORY CHECK ──────────┘
   ↓
DETERMINISTIC POLICY ENGINE
   ↓
 ┌────────────┬──────────────┬────────────┐
 ↓            ↓              ↓
BLOCK      CONFIRM         ALLOW
 │            ↓              │
 │      HUMAN APPROVAL       │
 │      (with evidence)      │
 │            ↓              │
 │        approved           │
 │            └──────┬───────┘
 │                   ↓
 │        TRANSACTIONAL EXECUTOR
 │           SNAPSHOT → EXECUTE → VERIFY
 │                   ↓
 │            ┌──────┴──────┐
 │            ↓             ↓
 │         COMMIT       ROLLBACK
 │            ↓             │
 │   POST-EXECUTION VERIFY  │
 │            │             │
 └────────────┴──────┬──────┘
                     ↓
        TAMPER-EVIDENT AUDIT LOG
   user → proposal → analysis → decision → execution → verification
```

### 4.4 Decision logic

The policy engine is a pure function. Same inputs, same verdict, every time.

```
decide(authorization, intent_match, impact_level,
       reversibility_class, invariants_violated, escalation_score)
  → ALLOW | CONFIRM | BLOCK
```

Governing rules:

- Any **invariant violation** → `BLOCK`. Non-overridable.
- **Not authorized**, or **intent mismatch** on a non-read action → `BLOCK`.
- **Irreversible** + non-trivial impact → `CONFIRM` (never silent ALLOW).
- **High blast radius** → `CONFIRM` with full evidence, regardless of action category.
- **Rising escalation score** lowers the threshold at which `CONFIRM` is required.
- Everything else → `ALLOW`.

**Fail-safe:** if any analyzer is unavailable, the action degrades toward `CONFIRM`, never toward
`ALLOW`. No irreversible action is ever authorised by a machine-learning judgement alone.

### 4.5 Module layout

```
src/
├── interceptor/      action capture, normalisation, tool-boundary adapters
├── analysis/
│   ├── identity/     principal resolution, permission check
│   ├── intent/       task-vs-action divergence
│   ├── graph/        dependency / environment model
│   ├── impact/       blast-radius computation, evidence bundle
│   ├── reversibility/ action classification
│   ├── invariants/   hard rule evaluation
│   └── trajectory/   sequence and escalation analysis
├── policy/           deterministic decision engine
├── execution/        snapshot, execute, verify, commit, rollback
├── audit/            hash-chained append-only log
├── console/          approval UI with evidence, live decision view, audit viewer
└── scenarios/        replayable demo scenarios
tests/                policy unit tests, evaluation suite
```

### 4.6 Design constraints

| Constraint | Rule |
| --- | --- |
| **Determinism** | The security decision contains no ML. The LLM proposes and explains only |
| **Model agnosticism** | Enforcement at the tool-call boundary; no dependence on any agent framework or model |
| **Fail-safe direction** | Degrade toward `CONFIRM`, never toward `ALLOW` |
| **Agent identity** | The agent carries its own scoped identity; it must never inherit an operator's privileges |
| **Audit integrity** | Append-only and hash-chained; not writable from the agent path |
| **Offline capable** | The whole decision path runs locally, with no network dependency |
| **Approval quality** | Every confirmation carries evidence. Approval fatigue is a security failure, not a UX one |
