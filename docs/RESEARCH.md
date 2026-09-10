# Research

**Updated:** 2026-09-10 — full pass, post-statement.

Claims are tagged **FACT** (sourced), **INFERENCE** (reasoned), **ASSUMPTION** (unverified working
belief), **PREDICTION** (a bet). Nothing here is invented. Source URLs at the bottom of each part.

---

## Part 0 — Fact-check of the problem statement itself

The brief cites incidents and statistics. We will be tempted to quote them on stage. **A judge in a
cybersecurity track will know these numbers.** Verified before use:

| Claim in brief | Verdict | Notes |
| --- | --- | --- |
| PoisonedRAG, USENIX Security 2025; 5 docs → 90% ASR | ✅ **FACT** | Zou, Geng, Wang, Jia. 90% ASR injecting 5 texts into a corpus of millions. [USENIX](https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag) |
| CVE-2025-32711 "EchoLeak", M365 Copilot zero-click | ✅ **FACT** | CVSS 9.3, found by Aim Labs. "LLM Scope Violation." Server-side patch; class of risk persists. [SOC Prime](https://socprime.com/blog/cve-2025-32711-zero-click-ai-vulnerability/), [arXiv 2509.10540](https://arxiv.org/abs/2509.10540) |
| Sysdig TRT AI-agent intrusion, 2026 | ✅ **FACT** | 10 May 2026: CVE-2026-39987 → internal DB exfiltration in under an hour. Also JadePuffer (June 2026), first documented end-to-end agentic ransomware — 600+ commands, 1,342 items encrypted. [Sysdig](https://www.sysdig.com/blog/ai-agent-at-the-wheel-how-an-attacker-used-llms-to-move-from-a-cve-to-an-internal-database-in-4-pivots), [CyberScoop](https://cyberscoop.com/sysdig-judepuffer-ai-agentic-ransomware-attack/) |
| Claude Opus 5 production DB deletion, Aug 2026, no adversarial prompt | ✅ **FACT** | Agent in Ultracode mode wired to production Supabase with unrestricted access; migration meant for a disposable test DB hit production. Compare PocketOS (April 2026), production DB destroyed in 9 seconds. [The Register](https://www.theregister.com/2026/04/27/cursoropus_agent_snuffs_out_pocketos/), [Euronews](https://www.euronews.com/next/2026/04/28/an-ai-agent-deleted-a-companys-entire-database-in-9-seconds-then-wrote-an-apology) |
| 30–82% of public MCP servers carry exploitable flaws | ✅ **FACT** | Corroborated across independent scans; 82% path traversal / 34% command injection across 2,614 servers surveyed. [Practical DevSecOps](https://www.practical-devsecops.com/mcp-security-statistics-2026-report/), [CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-security-crisis-20260504-csa-styled/) |
| 30+ MCP CVEs in a 60-day window, early 2026 | ✅ **FACT** | Incl. CVE-2025-6514 in `mcp-remote`, CVSS 9.6, 437k+ downloads before disclosure. [Practical DevSecOps](https://www.practical-devsecops.com/mcp-security-statistics-2026-report/) |
| **"2026 Pinecone failure: 200,000 healthcare records exposed"** | ❌ **UNVERIFIED — DO NOT CITE** | No public report of this incident found. Searches return only Pinecone product/architecture pages. It may be non-public, garbled, or illustrative. |
| $101bn annual US return fraud | ⚠️ **PLAUSIBLE, verify before use** | Matches the widely-quoted NRF figure but we have not confirmed the primary source or year. |
| 53M+ US informal caregivers | ⚠️ **PLAUSIBLE, verify before use** | Consistent with AARP/NAC "Caregiving in the US"; confirm edition before quoting. |

**INFERENCE — act on this.** If we take a Track 1 statement, we will cite incidents. Use the four
verified ones. **Strike the Pinecone claim from every slide and every sentence.** The cross-tenant
risk it illustrates is still real and defensible on architecture alone — metadata-filter-based
tenant isolation leaves you "one wrong query away from cross-tenant exposure"
([IronCore Labs](https://ironcorelabs.com/vectordbs/pinecone-security/)) — so make the architectural
argument, not the incident claim. Being the team that *removed* an unverifiable number, and says so,
is a credibility gain in Q&A, not a loss.

---

## Part 1 — What the organizer is actually asking

13 problem statements across 4 tracks. Read together, they are **one question asked thirteen ways.**

Look at the constraint clause in each — the sentence that says what a *wrong* solution looks like:

| PS | The anti-pattern the organizer pre-emptively kills |
| --- | --- |
| T1-PS1 | "A better system prompt alone is insufficient." "A wall is not a solution." |
| T1-PS2 | Legitimate server updates must "route cleanly through re-approval without permanent disruption." |
| T1-PS3 | "Blocking all imperative language at ingestion is not a solution — makes the knowledge base unusable." |
| T2-PS1 | Cost of blocking one legitimate customer **exceeds** the value of one fraudulent return. |
| T2-PS2 | "Solving only one layer is not a solution." |
| T2-PS3 | "Tracking a return request without closing the destruction loop is insufficient." |
| T3-PS2 | Must not reinforce delusions, must not contradict into distress. "Must know own boundary of competence." |
| T4-PS1 | Must output **"unknown"** rather than force-fit. "A decision, not just a label." |
| T4-PS2 | "System recommends only — never closes a search area automatically." FPs/minute reported explicitly. |
| T4-PS4 | "The language model must NEVER generate a quantity." "Honest refusal is the correct answer." |

**INFERENCE — the unifying thesis.** Every statement is about **putting deterministic, auditable
constraints around a probabilistic system.** The organizer is not asking teams to *use* AI. They are
saying: AI is already in production, it fails in ways the model itself cannot fix, and the missing
artifact is the **control plane**.

**INFERENCE — the hidden rubric.** Every single PS pairs "catch the bad case" with "and do not break
the good case." Precision, not recall, is the graded axis. Any team that demos only the block is
demoing half the assignment. **The winning demo shows the false-positive case passing cleanly.**

**INFERENCE — track difficulty vs. crowding.** Tracks 3 and 4-PS4 are approachable by any team that
can wire an LLM to a UI; expect them to be heavily contested with near-identical submissions. Track 1
demands understanding of agent internals, MCP wire format, and retrieval security — most student
teams will avoid it. **Thin field, high ceiling.** With ~1,100 participants, the size of the judges'
comparison set for our PS is itself a strategic variable.

---

## Part 2 — Competitive intelligence: the organizer

**ASSUMPTION** (decision 004, still unconfirmed): this is E-Cell IIIT Hyderabad's Megathon.

| Item | Detail | Source |
| --- | --- | --- |
| Format | 24h onsite; teams ≤5; Indian college students | [megathon.in](https://megathon.in/) |
| Scale | 1,100+ participants, 62 colleges (2025) | [indtoday](https://indtoday.com/e-cell-iiit-hyderabads-megathon-2025-the-deccan-edition-concludes-with-massive-turnout/) |
| Judging | Filtering round → top ~20 pitch in "lightning sessions" to domain experts | [businessnewsthisweek](https://businessnewsthisweek.com/education/megathon-2025-deccan-edition-wraps-up-showcases-hyderabads-student-innovators/) |
| Statements | Sponsor-authored; narrow and vertical (2023: edge-LLM medical query; ML candidate profiling; satellite paddy tracking) | [IIIT blog](https://blogs.iiit.ac.in/monthly_news/megathon-2023/) |
| AI-tool policy | Usage must be explicitly mentioned and cited | [megathon.in](https://megathon.in/) |

**Two games, in order.** (1) Survive the filter — needs a *working* demo; most teams die on a broken
build. (2) Win the lightning pitch — short, expert-judged, Q&A-heavy; narrative and defensibility
dominate. Nothing wins game 2 if we lose game 1.

**Rubric decode** — what each stated criterion actually rewards:

| Criterion | Really testing | Common failure |
| --- | --- | --- |
| Innovation | Is the *insight* novel, not the stack | "We used an LLM" as the innovation |
| Problem Understanding | Did you model the real user | Restating the brief back |
| Technical Excellence | Depth under the demo | Thin wrapper over an API |
| Feasibility | Survives contact with reality | Needs data nobody has |
| Prototype Functionality | Does it run, live | Slideware, or a crash on stage |
| Scalability | Thought past the demo | "We'll add Kubernetes" |
| Real-World Impact | Who is measurably better off | Vague social good |
| UX | Stranger-usable in 30s | Dev-only UI, no empty states |
| Presentation | Story, not feature tour | Reading the diagram aloud |
| Jury Q&A | Do you know your own weaknesses | Bluffing |

---

## Part 3 — Track A: GitHub / open source prior art

Scoped to the selected problem (T1-PS1) and its nearest neighbours.

| Project | What it is | Relevance | Reuse / avoid |
| --- | --- | --- | --- |
| **APort / Open Agent Passport** (Apache-2.0) | Reference impl of an agent-identity + declarative capability policy spec; runtime check inside the framework tool hook returns ALLOW/DENY; signed audit record per decision. [aport.io](https://aport.io/blog/best-ai-agent-guardrails-2026-pre-action-authorization-compared/) | **Closest prior art to our Layer 1.** Confirms authorization-context propagation is a solved, specified problem. | **Reuse the mental model and vocabulary** (passport, capability, signed decision record). **Do not** reimplement identity plumbing — cite it and move up the stack. Its decisions are **stateless per call** — that gap is our wedge. |
| **Lasso MCP Gateway** (open source) | Gateway that embeds a detection engine in the request pipeline to catch adversarial patterns before they reach high-permission tools. | Proves the proxy interception point is viable and is the industry's chosen seam. | Reuse the architectural pattern (proxy at the tool boundary). Avoid competing on prompt-attack detection — that is their moat, not ours. |
| **Ant Group SingGuard-NSFA** (open source) | Agentic-AI security framework, pre-action threat interception. [OSFY](https://www.opensourceforu.com/2026/07/new-open-source-ai-security-guardrails/) | Another pre-action enforcement point. | Comparison baseline for Q&A. |
| `github.com/topics/runtime-guardrails` | Live topic cluster | Sweep at hour 0 for anything newer. | — |
| **PoisonedRAG** (`thisxyz/PoisonedRAG`) | Official USENIX'25 attack implementation | Only if we take T1-PS3 — gives a real attack to defend against rather than a hand-made one. | Reuse as **red-team input**; do not vendor. |

**INFERENCE — the reuse boundary.** Layers 1 and 2 of T1-PS1 (authorization propagation,
reversibility gating) have credible open-source and commercial implementations. Building them from
scratch and claiming novelty would be caught instantly in Q&A. **Build them competently, cite the
prior art, and put every innovation claim on Layer 3.**

---

## Part 4 — Track D: commercial competitors (T1-PS1)

This space is **funded and crowded**. A judge may well name one of these.

| Product | What it does | Weakness we exploit |
| --- | --- | --- |
| **Zenity** | Discover agents, assess posture, detect risky behaviour, enforce controls in real time; explicitly "deterministic enforcement… inline, in real time" | Inline = **per-action**. The framing is threat detection. A sequence of individually-benign actions produces no signal. |
| **Lasso Security** | Build-time red-teaming + runtime protection for prompt attacks, data leaks, unsafe outputs; MCP Gateway; "intent security" | Optimised for **adversarial input**. Silent on the no-attacker failure mode. |
| **Noma Security** | Data+AI lifecycle protection, build → production runtime (Series B, $132M) | Enterprise posture/governance platform; not a per-session mandate enforcer. |
| **WitnessAI** | Enterprise AI guardrails, on-prem for regulated environments | Policy/observability layer, same per-request framing. |

**INFERENCE — the gap, stated precisely.** Every one of these asks *"is this action malicious?"*
None asks *"is this action still inside the envelope of the mandate this session was opened under?"*
The first question has no answer when there is no attacker. The second always has one.

**FACT that makes this a real gap, not a rhetorical one:** a substantial share of documented
enterprise AI incidents involve **no attacker at all** — an authorized agent acting on permissions
that outlived their purpose. The Aug 2026 Opus-5/Supabase deletion and the April 2026 PocketOS
9-second wipe are both of this type: no adversarial prompt, no intrusion, catastrophic outcome.
*(A widely-repeated figure puts it at 188 of 344 verified enterprise AI incidents 2023–2026, but the
primary source is a secondary blog aggregation — **treat as ASSUMPTION and do not quote the number
on stage** unless we find the primary. The two named incidents are enough to make the point.)*

---

## Part 5 — Track E: resources for the 24 hours

| Resource | Use | Cost / limits | Offline fallback |
| --- | --- | --- | --- |
| Claude / OpenAI API | Reversibility classification of unknown tools; mandate summarisation | Per-token; budget before first call | **Required:** deterministic tool registry covers all demo tools; unknown → default R2 (confirm). Demo never depends on a live model call. |
| Local embedding model (`all-MiniLM-L6-v2` class, ~90MB) | Mandate-vs-action drift vector | Free, runs on CPU, ~10ms | Is itself the offline path — **prefer local over an embedding API for exactly this reason** |
| Postgres + `pgvector` | Session state, trajectory history, append-only audit | Managed free tier | Local Docker Postgres; seed script |
| MCP Python/TS SDK | Proxy sits on the wire between client and server | Open source | — |
| Prerecorded demo capture | Insurance | — | **Record the moment it first works** |

**Hard rule (unchanged): no external dependency enters the build without a named offline fallback.**
Venue wifi at a 1,100-person event is a genuine failure mode, and "our demo needs the internet" is a
losing answer in Q&A.

---

## Part 6 — Jury attack surface: the 20 questions

Answers are our current honest positions. Rehearse aloud; do not read.

**1. Why does this need AI at all?**
Most of it deliberately doesn't. Authorization and reversibility gating are pure deterministic code —
that is a design choice, because security controls you cannot predict are security controls you
cannot trust. AI appears in exactly two places: semantic drift scoring between a session's mandate
and its action sequence, and first-pass reversibility classification of tools we have never seen.
Both are advisory inputs to a deterministic decision function.

**2. Why not just write a better system prompt?**
Because the properties being enforced do not exist inside the model. The model has no cross-session
memory, no view of the authorization chain, and no knowledge of which actions are reversible in the
real world. A prompt is a request; this is a gate. The Aug 2026 production-database deletion involved
no adversarial prompt at all — there was nothing for a better prompt to defend against.

**3. Zenity and Lasso already do runtime enforcement. What is left for you?**
They enforce per action, and they frame the problem as threat detection. Ask either "is this action
malicious?" about a sequence of individually reasonable requests and the answer is no, every time.
We ask a different question — is this still inside the mandate this session opened under? — which is
answerable even when there is no attacker. We are complementary to them, not a replacement.

**4. Isn't this just RBAC with extra steps?**
RBAC answers "may this principal ever do this?" We answer "should this principal do this *now*,
given what they have already done this session and last session?" RBAC is static and per-principal;
the mandate envelope is dynamic and per-session. We sit on top of RBAC and assume it exists.

**5. Where does the mandate come from? Isn't that circular?**
Captured at session open — either declared explicitly by the calling system, or inferred from the
first request and then **shown to the user for confirmation**. Inference is never silent. If we
cannot establish a mandate, we degrade to reversibility gating only, and say so in the console.

**6. What happens when your drift model is wrong?**
Two directions. False high drift raises a confirmation prompt — annoying, recoverable, and we measure
the rate. False low drift means we fall back on the reversibility gate, which is deterministic and
does not depend on the model being right. **No irreversible action is ever authorised by an ML
judgement alone.** That is the single most important line in our design.

**7. So it's a wall. Doesn't it block legitimate work?**
That is the failure mode the brief calls out, and it is the scenario we demo second on purpose. A
legitimate engineer doing genuinely escalating work also accumulates drift — they hit the gate once,
confirm, and the mandate **widens**. We report false-gate rate on legitimate trajectories as a
first-class metric, next to attack-stop rate. A number, not a claim.

**8. What is your false positive rate?**
Measured on our evaluation suite of hand-built trajectories — attack and legitimate-escalation — and
reported per class. We will state the exact figure and the suite size on the slide. It is a small
suite built by us in 24 hours; we will say that too rather than imply it generalises.

**9. Where does your evaluation data come from — did you make it up?**
Yes, and we will say so. The trajectories are hand-authored from documented incident patterns
(Sysdig's 2026 agentic intrusion chain, the Opus-5 migration case). There is no public benchmark for
cross-session agent escalation; building one is arguably part of the contribution, and its absence is
the honest limitation.

**10. What's the latency cost?**
Deterministic path — authorization + reversibility lookup — is a hash lookup and a policy evaluation,
sub-10ms, on the synchronous path. Drift scoring runs asynchronously against session state; the gate
reads the last computed score. We report p50/p95 added latency measured, not estimated.

**11. What does it cost to run?**
The deterministic path is free. Local embeddings cost CPU, not tokens. The LLM classifier fires only
on tools not in the registry — once per new tool, then cached. Per-action marginal cost at steady
state is effectively zero, which is the point: a security control priced per action does not survive
production traffic.

**12. Does the harness itself become the attack surface?**
Yes, and it is the highest-value target in the system — it holds the audit log and the policy. We
treat it accordingly: append-only audit, no policy mutation from the agent path, fail-closed on
irreversible actions if the policy store is unreachable. We are not claiming we have hardened it to
production standard in 24 hours.

**13. What if the agent bypasses your proxy?**
Then it is unprotected, and this is an honest limitation. We enforce at the tool-call boundary, which
means deployment has to route tool traffic through us — same trust assumption as any egress proxy or
service mesh. Enforcement below that boundary is an OS/network problem, not ours.

**14. What happens with no internet?**
The whole enforcement path runs locally: deterministic policy, local embeddings, local Postgres. We
will demo it with wifi off if you want. That is a design requirement, not a convenience.

**15. What breaks at 10× scale?**
Embedding computation first. The proxy is stateless and scales horizontally; session state is keyed
by principal in Postgres. At 10× we batch embeddings and move drift scoring to a worker queue — which
is why it is already asynchronous in the design rather than retrofitted later.

**16. Privacy — you're logging every agent action.**
Yes, and that is a real obligation. Audit records store action metadata and resource identifiers, not
payloads, by default. Retention is configurable with automatic purge. In a regulated deployment this
would need a DPIA; we have not done one.

**17. Who buys this, and why not build it in-house?**
Platform and security teams at organisations putting agents near production systems. In-house is a
genuine alternative for large firms — the same was true of secrets management before Vault. The
argument is the same: the policy primitives and the incident-derived trajectory patterns are the
product, not the proxy.

**18. Why would a developer accept the friction?**
Because the friction is targeted. Read and reversible actions pass untouched — that is the large
majority of traffic. Confirmation is demanded only for irreversible actions, and demanded *more*
insistently when drift is high. A control that fires constantly gets disabled in a week; we designed
against that outcome explicitly.

**19. What is genuinely novel here, in one sentence?**
Reframing agent runtime security from threat detection to **mandate drift** — which makes the
no-attacker failure mode, currently the majority of real incidents, detectable by the same mechanism
that catches the deliberate attacker.

**20. What would you do with another month?**
Three things, in order: a real evaluation benchmark for cross-session escalation, because ours is
too small to generalise; reversibility classification learned from actual rollback telemetry rather
than a hand-built registry; and a hardened policy store with formal verification of the fail-closed
property.

---

## Sources

**Organizer:** megathon.in · ecell.iiit.ac.in/hackathons · blogs.iiit.ac.in/monthly_news/megathon-2023 · indtoday.com · businessnewsthisweek.com

**Incidents & vulnerabilities:**
- https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag
- https://arxiv.org/abs/2509.10540 (EchoLeak)
- https://socprime.com/blog/cve-2025-32711-zero-click-ai-vulnerability/
- https://www.sysdig.com/blog/ai-agent-at-the-wheel-how-an-attacker-used-llms-to-move-from-a-cve-to-an-internal-database-in-4-pivots
- https://cyberscoop.com/sysdig-judepuffer-ai-agentic-ransomware-attack/
- https://www.theregister.com/2026/04/27/cursoropus_agent_snuffs_out_pocketos/
- https://www.euronews.com/next/2026/04/28/an-ai-agent-deleted-a-companys-entire-database-in-9-seconds-then-wrote-an-apology
- https://www.practical-devsecops.com/mcp-security-statistics-2026-report/
- https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-security-crisis-20260504-csa-styled/
- https://ironcorelabs.com/vectordbs/pinecone-security/

**Prior art & competitors:**
- https://aport.io/blog/best-ai-agent-guardrails-2026-pre-action-authorization-compared/
- https://www.opensourceforu.com/2026/07/new-open-source-ai-security-guardrails/
- https://www.linx.security/blog/top-agentic-ai-security-solutions
- https://www.apono.io/blog/top-agentic-ai-security-solutions/
- https://github.com/topics/runtime-guardrails
- https://github.com/thisxyz/PoisonedRAG

**Alternative-PS research (unselected, kept for pivot):**
- https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi · https://api.imd.gov.in/ (T4-PS4 data sources, both real and usable)
- https://elliq.com/ · https://blog.rendever.com/rendever-launches-ai-companion-for-personalized-reminiscence-therapy · https://pmc.ncbi.nlm.nih.gov/articles/PMC13246264/ (T3-PS2 competitors)
