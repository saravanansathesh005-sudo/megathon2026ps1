# Decision Log

Append-only. One entry per decision. Never rewrite history — supersede instead.

```
## NNN — <title>
- **Date:** / **Status:** proposed | accepted | superseded by NNN
- **Context / Decision / Alternatives / Consequences**
```

---

## 001 — Start from an empty, documentation-first workspace
- **Date:** 2026-09-10 · **Status:** accepted
- **Context:** Problem statement not yet released. Picking a stack early risks a rewrite.
- **Decision:** Directory skeleton and planning docs only. No framework, no dependencies.
- **Alternatives:** Pre-scaffold a starter — rejected; a wrong guess costs more than it saves.
- **Consequences:** `src/` and `tests/` stay empty until the stack decision.

---

## 002 — Do not run the strategy pipeline against a guessed problem statement
- **Date:** 2026-09-10 · **Status:** accepted, resolved by 005
- **Context:** A full eight-phase pass was requested on the stated basis that the statement had been received. It had not — `docs/PROBLEM.md` was byte-identical to the scaffold.
- **Decision:** Refuse to generate Phases 1–7; spend the time on domain-independent work instead.
- **Alternatives:** Guess a plausible domain — rejected; output would be indistinguishable in form from real strategy while being worthless, and the team would rehearse the wrong pitch.
- **Consequences:** Phases deferred one day. Hour-0 playbook written in the meantime.

---

## 003 — Optimize for readiness, not a pre-built solution
- **Date:** 2026-09-10 · **Status:** **superseded by 005**
- **Context:** Megathon 2025 released statements on the spot, so pre-building a solution looked impossible.
- **Decision:** Invest only in domain-independent readiness.
- **Consequences:** **Superseded** — the statement is now in hand ahead of the event, so targeted pre-build is possible. The readiness reasoning still holds for anything not covered by 005.

---

## 004 — Verify the organizer identity before trusting the intelligence
- **Date:** 2026-09-10 · **Status:** **proposed — still unconfirmed, action required**
- **Context:** All organizer research assumes E-Cell IIIT Hyderabad's Megathon. A same-named 2026 protein-design event exists (Rosetta Commons, Puerto Rico).
- **Decision:** Treat Part 2 of `docs/RESEARCH.md` as provisional until someone confirms from the registration email.
- **Consequences:** Five minutes either promotes the whole section to FACT or invalidates it cleanly. **Nobody has done this yet.**

---

## 005 — Attack Track 1, PS 1: Runtime Security Harness for AI Agents
- **Date:** 2026-09-10 · **Status:** accepted, pending team ratification

### Context

13 statements across 4 tracks. Ten distinct concepts were generated spanning different tracks,
architectures, AI techniques and user models, then scored /10 on ten axes (innovation, real-world
impact, technical feasibility, 24h feasibility, demo strength, scalability, UX, AI necessity,
differentiation, jury defensibility).

| # | Concept | PS | One line | Total |
| --- | --- | --- | --- | ---: |
| **1** | **Warrant** | T1-PS1 | Runtime harness reframed from threat detection to **mandate drift** | **85** |
| 2 | Provenance | T1-PS2 | MCP proxy: TOFU-pin tool manifests, semantic diff on reconnect, sanitize outputs | 72 |
| 3 | Anchor | T3-PS2 | Dementia companion over a biographical memory graph with stage calibration | 72 |
| 4 | Chorus | T3-PS3 | Caregiver burnout prediction + shift-handover intelligence, voice-first | 71 |
| 5 | Airlock | T1-PS3 | RAG defence with authorization scoping as an index-partition primitive | 69 |
| 6 | Kisan-Grounded | T4-PS4 | Region-aware agri advisory; deterministic rules layer owns every number | 69 |
| 7 | DarkWater | T4-PS3B | Coastal console; dark-vessel detection = visual track with no AIS match | 67 |
| 8 | Tripwire | T1-PS1 | Shadow-environment dry-run; gate on simulated blast radius instead of monitoring | 66 |
| 9 | Chain-of-Custody | T2-PS3 | Pharma batch ledger with expired-drug re-entry detection | 65 |
| 10 | Ledger-Loop | T2-PS2 | Four-layer offline-first e-waste EPR chain | 60 |

Scoring detail for the winner — Innovation 9, Impact 9, Tech feasibility 8, 24h feasibility 8,
Demo 10, Scalability 8, UX 7, AI necessity 8, Differentiation 9, Jury defensibility 9.

### Decision

**Build concept 1 — "Warrant" — against Track 1, PS 1.**

### Why it beats the other nine

- **Zero data dependency.** The single largest killer of 24-hour builds is data acquisition. T4-PS1
  needs ≥1,000 annotated images across 3 backgrounds; T4-PS2 needs occluded aerial survivor imagery
  and ≥90% recall, which is a research problem; T4-PS4 depends on Indian government APIs that may be
  slow or down on the day; T2-PS1 needs fraud data. Warrant's evaluation data is **trajectories we
  author ourselves**. Nothing external can fail on the day.
- **The demo is the argument.** Attack runs → damage. Harness on → blocked, with a readable reason.
  Binary, visceral, no accuracy hand-waving. Contrast T3-PS2, where "did the companion respond well?"
  is a judgement call, or T4-PS1, where everything rides on hitting ≥92% macro-F1 live.
- **Thinnest field.** Track 1 requires understanding agent internals and the MCP wire format; most
  student teams will avoid it. Tracks 3 and 4-PS4 will be contested by dozens of near-identical
  LLM-plus-UI submissions. Our work gets compared against a smaller, weaker set.
- **A genuine, defensible wedge** (decision 006), rather than a better execution of a known idea.
- **AI necessity survives inspection.** The honest answer — most of it is deliberately deterministic,
  AI does exactly two advisory jobs — is *stronger* than claiming AI everywhere, and Track 1 judges
  will reward the restraint.

### Alternatives rejected

- **Concept 2 (Provenance, 72)** — the safest build in the set and a crisp rug-pull demo, but the
  core is manifest hashing and diffing. "Why is this AI?" has no good answer, and innovation ceiling
  is low. **Keep as the fallback if Warrant's Layer 3 fails by hour 12** — it shares the proxy
  substrate, so the pivot is cheap. This is our insurance policy.
- **Concept 3 (Anchor, 72)** — the most emotionally powerful demo available and the one the team will
  be most tempted by. Rejected on differentiation and defensibility: ElliQ, Rendever's Nova, Mentia
  and KindredMind already ship in this space, clinical efficacy cannot be shown in 24 hours, and the
  hardest requirement (never reinforce a delusion, never contradict into distress) is exactly where a
  judge will probe and where we would have nothing but assertions.
- **Concept 6 (Kisan-Grounded, 69)** — best real-world impact story and a genuinely excellent
  architectural idea in "the LLM never generates a number." Rejected on crowding and data fragility:
  agri-RAG is a well-worn hackathon genre and judges have seen many.
- **Concept 10 (Ledger-Loop, 60)** — the brief demands all four layers end-to-end; that is a
  two-week build, and a partial submission is explicitly disqualified by the success criteria.

### Consequences

Committed to a security-infrastructure build with an operator-console UX rather than a consumer one.
UX scores 7, not 9 — accepted, and mitigated by investing real design effort in the console
(decision 008). We must be able to name Zenity, Lasso, Noma and APort on stage and say precisely how
we differ; a team that has not heard of them will be destroyed by the first Q&A question.

---

## 006 — The wedge: mandate drift, not threat detection
- **Date:** 2026-09-10 · **Status:** accepted

### Context

Layers 1 and 2 of the brief (authorization propagation, reversibility gating) already exist. APort
ships an Apache-2.0 agent-passport implementation with per-decision ALLOW/DENY and signed audit
records; Zenity advertises deterministic inline enforcement; Lasso ships an open-source MCP gateway.
Claiming novelty on those layers would be caught in the first minute of Q&A.

Meanwhile, the documented incidents that actually caused damage in 2026 — the August Opus-5/Supabase
production deletion, the April PocketOS 9-second wipe — involved **no adversarial prompt and no
attacker**. An authorized agent used permissions that had outlived their purpose.

### Decision

Reframe the problem from **"is this action malicious?"** to **"is this action still inside the
envelope of the mandate this session was opened under?"**

Put every innovation claim on **Layer 3, the cross-session trajectory monitor**, and implement Layers
1 and 2 competently while explicitly crediting the prior art.

### Why this is the right wedge

- The threat-detection question has **no answer** when there is no attacker, and no answer when a
  sequence of individually reasonable requests adds up to an attack. The mandate question always has
  one.
- One mechanism covers both failure modes — the deliberate slow-escalation attacker and the
  well-meaning agent with stale permissions. Judges reward a single idea that explains two problems.
- It maps exactly onto the brief's own reasoning for why the model cannot fix this: no cross-session
  memory, no authorization-chain visibility, no reversibility awareness. Mandate state lives outside
  the model by necessity, not by preference.

### Alternatives

- *Compete on better prompt-injection detection* — rejected; that is Lasso's moat and a losing fight.
- *Concept 8 (Tripwire), gate on simulated blast radius from a shadow-environment dry run* — a strong
  idea, rejected on 24-hour feasibility: a shadow environment faithful enough to trust is most of the
  build. **Retain the blast-radius concept as a scoring feature** inside the reversibility classifier.

### Consequences

The demo must include the no-attacker scenario, or the wedge is unproven. Scene 3 (a
migration command with no adversarial prompt, caught by the reversibility gate) is **not optional** —
it is the scenario that distinguishes us from every funded competitor in the space.

---

## 007 — Deterministic core, advisory AI — and never the reverse
- **Date:** 2026-09-10 · **Status:** accepted

- **Context:** A security control whose behaviour cannot be predicted cannot be trusted, and "what happens when your model is wrong?" is a guaranteed Q&A question. The brief itself repeatedly demands this shape — T4-PS4's "the language model must NEVER generate a quantity" is the same principle in another domain.
- **Decision:** Authorization checks, reversibility gating and the final allow/deny are **pure deterministic code**. AI is confined to two advisory inputs: semantic drift scoring, and first-pass reversibility classification of unregistered tools. **No irreversible action is ever authorised by an ML judgement alone.** Unknown tool + unavailable classifier → default to R2 (requires confirmation), never to allow.
- **Alternatives:** LLM-as-judge on every action — rejected: unpredictable, unauditable, expensive per action, and trivially destroyed in Q&A.
- **Consequences:** AI-necessity scores 8 rather than 10, and we accept that. In a security track the restraint is a strength, and it makes questions 6, 10, 11 and 14 in the jury set answerable with a straight face.

---

## 008 — Console design is a first-class deliverable, not a debug view
- **Date:** 2026-09-10 · **Status:** accepted

- **Context:** UX is a stated judging criterion and is this concept's weakest axis (7/10). Security tooling defaults to dense, developer-only interfaces. The judges see the console for perhaps 90 seconds.
- **Decision:** Budget explicit hours for the operator console: a live drift graph, a gate queue with human-readable reasons, and the audit trail. The gate's block message must explain *why* in a sentence a non-specialist understands.
- **Alternatives:** Ship a CLI and narrate it — rejected; forfeits a whole criterion and makes the demo harder to follow from the back of a room.
- **Consequences:** Roughly 3 of 24 hours go to interface work that adds no enforcement capability. Accepted deliberately.

---

## 009 — Evaluate on CSTM-Bench; retire the "nobody does cross-session" claim
- **Date:** 2026-09-10 · **Status:** accepted, conditional on access check

- **Context:** Deep research found **CSTM-Bench** ([arXiv:2604.21131](https://arxiv.org/abs/2604.21131), Apr 2026) — a public benchmark for cross-session threats in AI agents, including slow-drip prompt injections distributed across 50+ sessions with one innocuous fragment per interaction. That is precisely our threat model. Also found **TRACE** ([arXiv:2606.07054](https://arxiv.org/abs/2606.07054), F1 0.713 / recall 0.844) and **Trajectory Guard** ([arXiv:2601.00516](https://arxiv.org/pdf/2601.00516)). This **contradicts** the earlier claim in `RESEARCH.md` that no public benchmark existed, on which jury answer Q9 was built.
- **Decision:**
  1. Evaluate on CSTM-Bench and report numbers against published baselines, including a comparison row against TRACE. **Verify licence and availability before the event**; if unavailable, fall back to hand-authored trajectories and say so plainly.
  2. Retire "nobody does cross-session monitoring." Replace with the narrower, true differentiation: (a) these are detectors, we are enforcement middleware with a deterministic gate on the wire; (b) they monitor for threats/injections, we monitor mandate distance, which fires on the **no-attacker** case that has no threat signal; (c) TRACE runs an LLM-in-the-loop judge, our synchronous path stays deterministic and sub-10ms.
- **Alternatives:** Keep the hand-authored suite and not mention the literature — rejected. A Track 1 judge who has read arXiv would end the Q&A in one question, and "did you invent your eval data?" was already our weakest answer.
- **Consequences:** Innovation claim narrows and gets **more** defensible. Evaluation strengthens from self-authored to public-benchmark. Adds a pre-event task: confirm CSTM-Bench access. **State the differentiation before a judge raises it.**

---

## 010 — Name the competitors first, unprompted
- **Date:** 2026-09-10 · **Status:** accepted

- **Context:** The space moved sharply in the weeks before the event. **Akeyless** shipped *Agentic Runtime Authority* (GA Sept 2026) — "real-time intent-based access control" that blocks policy-violating agent actions pre-execution, with Claude Enterprise / OpenAI Codex / Bedrock AgentCore integrations. **CrowdStrike** launched a "Verified Agent" certification the same week. On the OSS side, **AgentPort** (`yakkomajuri`) ships "2FA for destructive ops" — effectively our Layer 2 — and **OneCLI** (YC S26) enforces policy "at the network layer, outside the agent and the LLM."
- **Decision:** Open the competitive section of the pitch by naming Akeyless, Zenity, AgentPort, OneCLI and APort ourselves, with a one-sentence differentiation each. Every team member must be able to do this cold.
- **Alternatives:** Wait and respond if asked — rejected. Being told about a competitor by a judge reads as not having done the work; raising it first reads as command of the field.
- **Consequences:** Costs ~20 seconds of pitch time. Buys the entire Q&A framing. Layer 2 is now explicitly positioned as table stakes with prior art credited, which makes the Layer 3 claim credible rather than grandiose.

---

## 011 — Lead the pitch with the destruction ledger
- **Date:** 2026-09-10 · **Status:** accepted

- **Context:** The team supplied a table of nine destructive coding-agent incidents, Jun 2025 – Jul 2026, across seven vendors (Cursor, Replit, Claude Code, Gemini CLI, Google Antigravity, Amazon Kiro, Claude Opus 5). Two entries were spot-checked against primary sources and both confirmed with stronger detail than the summary: Claude Code [#10077](https://github.com/anthropics/claude-code/issues/10077) (filed by Mike Wolak, 21 Oct 2025 — `rm -rf` from `/`, **the default permission system was on and did not fire**), and Amazon Kiro (Dec 2025 — inherited an engineer's elevated permissions, **bypassed a mandatory two-person production approval**, ~13h AWS Cost Explorer outage, followed by a 90-day safety reset across 335 systems).
- **Decision:** Open the pitch with this ledger rather than with a single incident. Three claims follow from it and are stated in order: **(1)** nine incidents, zero attackers — the no-attacker mode is the dominant pattern, not an edge case; **(2)** seven vendors — architectural gap, not a vendor-quality problem, which pre-empts "just use a better agent"; **(3)** three of the nine are **mechanical** failures (trailing-tilde expansion, unquoted-path truncation, misread exit code), which no increase in model capability can fix, because they are shell semantics rather than reasoning.
- **Alternatives:** Open on Palisade alone — still used, but as the *second* beat. One incident invites "that's an outlier"; nine across seven vendors does not.
- **Consequences:** Amazon Kiro becomes our headline Layer 1 case (identity inheritance defeating a human control) and Claude Code #10077 our headline Layer 2 case (permissions on, still destroyed everything). Amazon's remediation — more human approvals — is the foil for automated, reversibility-based gating. **Pin the Opus-5 Supabase date before printing anything**: the team's table says Jul 2026, our earlier source says early Aug 2026.
