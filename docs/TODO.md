# TODO

> **Nothing in P1 or below starts until decision 005 is ratified.** No application code before then.

## P0 — Ratify and confirm (today)

- [ ] **Verify CSTM-Bench access** (arXiv:2604.21131) — licence, download, does it run? This is now
      our evaluation story (decision 009). If it fails, we fall back to hand-authored trajectories
      and say so. **Find out before the event, not at hour 20.**
- [ ] **Learn five names cold:** Akeyless (Agentic Runtime Authority), Zenity, AgentPort, OneCLI,
      APort. One sentence each on how we differ. Decision 010.
- [ ] **Read the two primary post-mortems**, not the summaries: the [HF technical timeline](https://huggingface.co/blog/agent-intrusion-technical-timeline)
      and [Simon Willison's write-up](https://simonwillison.net/2026/Jul/22/openai-cyberattack/).
      We must discuss these, not just cite them.
- [ ] Pull the TRACE numbers (F1 0.713 / recall 0.844) into the comparison slide skeleton.

- [ ] **Ratify Track 1 / PS 1 ("Warrant").** Read decision 005 and 006. If anyone on the team cannot
      state the wedge in one sentence, we have not ratified — we have acquiesced.
- [ ] **Confirm the organizer** — decision 004, open since yesterday. Registration email.
- [ ] **Confirm the format:** statement in advance (evidently yes this time) or on the spot? How long
      is the pitch, is there a filtering round, what is the submission artifact?
- [ ] **Assign roles now, not at hour 3:** proxy/policy · trajectory worker · console · demo+deck owner.
- [ ] Strike the Pinecone statistic from any material anyone has already drafted.

## P1 — Pre-event build (domain-independent *within this PS*)

Legitimate to build before the clock, because it is substrate, not solution.

- [ ] Repo scaffold + Docker Compose (FastAPI, Postgres+pgvector, React) — one command to running
- [ ] Push-to-deploy pipeline, green, before the event
- [ ] MCP proxy skeleton that passes traffic through unmodified
- [ ] Append-only audit log schema with an insert-only grant
- [ ] Local embedding model downloaded and pinned **offline**
- [ ] Scenario harness: replay a scripted tool-call sequence from a file
- [ ] Q&A drill — every member answers Q1–Q5 from `RESEARCH.md` Part 6 aloud, no notes
- [ ] Read the four verified incident write-ups so we can discuss them, not just cite them

## P2 — The 24 hours

Full hour-by-hour table in `docs/ARCHITECTURE.md` § T. Non-negotiables:

- [ ] **Hour 10 — scenario 3 works end-to-end and is screen-recorded.** Recording before features.
- [ ] **Hour 12 checkpoint — is drift scoring producing a usable signal?** If no, pivot to concept 2
      (Provenance, T1-PS2) on the same proxy substrate. Survivable at hour 12; fatal at hour 20.
- [ ] **Hour 20 — evaluation script produces real numbers:** attack-stop rate, false-gate rate,
      p50/p95 latency. Numbers on the slide, not adjectives.
- [ ] **Hour 21 — feature freeze.** Two clean full runs from a reset state.
- [ ] **Hour 22–24 — deck and Q&A drill.** Not more code.

## P3 — Demo must-haves

- [ ] Scene 2 (legitimate escalation passing) — the scene that proves it is not a wall
- [ ] Scene 3 (no attacker at all) — the scene that separates us from Zenity/Lasso/Noma
- [ ] Gate block messages readable by a non-specialist
- [ ] Console legible from the back of the room
- [ ] Runs with wifi off, and we say so on stage
- [ ] AI tool usage cited in the submission, per organizer policy

## P4 — Deliberately not building

Recorded so nobody relitigates at hour 15: real IdP/OIDC · multi-tenancy · full MCP spec coverage ·
Kubernetes/HA · mobile · policy DSL editor · learned reversibility from telemetry · anything needing
an external dataset.

## Done

- [x] Workspace skeleton (2026-09-10)
- [x] Organizer intelligence, rubric decode, hour-0 playbook (2026-09-10)
- [x] Phases 1–8: decomposition, research, 10 scored concepts, adversarial review, selection,
      blueprint, jury set (2026-09-10)
- [x] Fact-check of the brief's claims — one struck as unverifiable (2026-09-10)
