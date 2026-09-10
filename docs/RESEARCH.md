# Research

> **Scope note (2026-09-10):** The official problem statement has **not** been received.
> Domain research (Tracks A–E) is therefore **not started** — it cannot be started without knowing the domain.
> What follows is the research that *is* possible without it: intelligence on the organizer and the
> competition format, plus the pre-built playbook we execute the moment the statement lands.
>
> Every claim is tagged **FACT** (sourced), **INFERENCE** (reasoned from facts),
> **ASSUMPTION** (unverified working belief), or **PREDICTION** (a bet about the future).
> No finding in this file is invented. Empty sections are empty on purpose.

---

## Part 1 — Competitive intelligence: the organizer

### Which Megathon is this?

**ASSUMPTION.** "MEGATHON'26", 24-hour, Grand Finale, jury Q&A, Indian context → this is almost
certainly **Megathon by E-Cell, IIIT Hyderabad**, their annual flagship hackathon.
**Confirm this before relying on anything in Part 1.** A same-named event exists in a completely
different field — Rosetta Commons' "Megathon 2026" is a protein-design event in Puerto Rico
([source](https://rosettacommons.org/2026/03/19/megathon-2026-one-week-two-hackathons-10-tutorials-and-16-curated-datasets/))
— so the name alone is not identifying.

### Format facts

| Item | Detail | Confidence | Source |
| --- | --- | --- | --- |
| Organizer | E-Cell, IIIT Hyderabad; motto "Meet. Ideate. Hack." | FACT | [ecell.iiit.ac.in](https://ecell.iiit.ac.in/hackathons/) |
| Duration | 24 hours, onsite | FACT (2025 ed.) | [megathon.in](https://megathon.in/) |
| Team size | Up to 5, cross-college allowed | FACT (2025 ed.) | [megathon.in](https://megathon.in/) |
| Eligibility | Students of Indian universities/colleges | FACT (2025 ed.) | [megathon.in](https://megathon.in/) |
| Scale | 1,100+ participants / 62 colleges (2025); 650+ (2024); 700+ (2022) | FACT | [indtoday](https://indtoday.com/e-cell-iiit-hyderabads-megathon-2025-the-deccan-edition-concludes-with-massive-turnout/), [ecell](https://ecell.iiit.ac.in/hackathons/) |
| Prize pool | ₹7 lakh (2025) | FACT | [businessnewsthisweek](https://businessnewsthisweek.com/education/megathon-2025-deccan-edition-wraps-up-showcases-hyderabads-student-innovators/) |
| Judging shape | Filtering round → **top ~20 teams** pitch in "high-velocity lightning sessions" to a panel of domain experts | FACT (2025 ed.) | [businessnewsthisweek](https://businessnewsthisweek.com/education/megathon-2025-deccan-edition-wraps-up-showcases-hyderabads-student-innovators/) |
| AI-tool policy | Use of AI tools "must be explicitly mentioned and cited" | FACT (2025 ed.) | [megathon.in](https://megathon.in/) |

### The single most important finding

> **"The problem statement will be given on the spot."** — Megathon 2025 official site
> ([megathon.in](https://megathon.in/))

**FACT** for the 2025 edition. **PREDICTION (high confidence):** the same holds for '26.

**INFERENCE — this reshapes our entire strategy.** If the statement drops at hour 0 of a 24-hour
clock, then:

1. There is **no pre-building the solution.** Anything domain-specific we build in advance is a
   coin flip we will probably lose.
2. What we *can* pre-build is **everything domain-independent**: repo scaffold, auth, deploy
   pipeline, CI, component library, an LLM-call wrapper with caching and fallback, a seed-data
   loader, a demo-recording setup. Teams that arrive with this bank 3–5 hours of the 24.
3. **Speed of decomposition becomes a competitive weapon.** The first 90 minutes — reading the
   statement, picking the wedge, cutting scope — decide the outcome more than the last 6 hours of
   coding.
4. Our real deliverable right now is **readiness**, not a solution.

### Sponsor pattern → what the statement will probably look like

Problem statements are **sponsor-authored**, not organizer-authored. **FACT**, consistent across editions:

| Year | Statement sources | Actual statements (where published) |
| --- | --- | --- |
| 2017 | Corporate + Social split | Smart cities, privacy/security, women's safety, chatbots, e-commerce ([src](https://ecell.iiit.ac.in/events/hackathons/megathon17.html)) |
| 2022 | Stellantis ×2, Qualcomm, RCTS (social) | Not published ([src](https://ecell.iiit.ac.in/events/hackathons/megathon-22.html)) |
| 2023 | Qualcomm, KonnectNXT, Telangana State Govt | LLM-based **medical query system for edge devices**; ML **candidate profiling + psychometrics**; **satellite imagery for paddy cultivation** tracking ([src](https://blogs.iiit.ac.in/monthly_news/megathon-2023/)) |
| 2025 | CHUBB (title), Qualcomm, Bhashini, Saral AI (social) | Not published ([src](https://businessnewsthisweek.com/education/megathon-2025-deccan-edition-wraps-up-showcases-hyderabads-student-innovators/)) |

**INFERENCE — the recurring shape.** Statements are *narrow, technically concrete, and vertical*.
Not "build something for healthcare" but "an LLM-based medical query system **for edge devices**."
The constraint clause is where the difficulty and the marks live.

**INFERENCE — recurring sponsor archetypes:**

- **Qualcomm** appears in 2019, 2022, 2023, 2025 → strong bias toward **on-device / edge / offline
  AI**, quantization, latency and power budgets.
- **Bhashini** (2025) → **Indic language** AI: translation, ASR, TTS, low-resource NLP.
- **A social / government track** recurs (RCTS 2022, Telangana Govt 2023, Saral AI 2025) →
  public-interest impact, often with **geospatial or citizen-service** framing.
- **Insurance / fintech** entered in 2025 via CHUBB → claims, risk, fraud, document processing.

**PREDICTION (moderate confidence).** MEGATHON'26 will offer 3–4 sponsor statements, at least one
involving on-device/offline AI or Indic language processing, and at least one with a social or
civic-impact framing.

**Do not build to this prediction — prepare to it.** Concretely: it is worth pre-reading the
Bhashini API docs and one on-device inference runtime. If either shows up we start hours ahead;
if neither does, we lost an evening. That is a good trade, and it is the *only* domain-flavoured
prep that survives an on-the-spot statement.

### What this tells us about winning

**INFERENCE.** With ~1,100 participants filtered to ~20 pitch slots, there are two distinct games:

- **Game 1 — survive the filter.** A working, visibly-demoable prototype. Most teams die here, on a
  broken build or nothing to show. Reliability beats ambition.
- **Game 2 — win the lightning pitch.** Short, expert-judged, with Q&A. Narrative and defensibility
  dominate. A modest system explained crisply beats an impressive one explained badly.

Optimize for both, in that order. **Nothing wins Game 2 if we lose Game 1.**

---

## Part 2 — Decoding the judging rubric

The ten criteria, and **INFERENCE** on what each actually rewards:

| Criterion | What judges are really testing | Common failure | Our lever |
| --- | --- | --- | --- |
| Innovation & Creativity | Is the *insight* novel, not just the stack | "We used an LLM" as the innovation | A non-obvious reframing of the problem |
| Problem Understanding | Did you model the real user | Restating the statement back | Name a specific user and a specific hour of their day |
| Technical Excellence | Depth under the demo | Thin wrapper over an API | One genuinely hard component, done well |
| Solution Feasibility | Could this survive contact with reality | Requires data nobody has | Name the data source and its licence |
| Prototype Functionality | Does it actually run, live | Slideware, or a crash on stage | Rehearsed happy path + offline fallback |
| Scalability | Have you thought past the demo | "We'll add Kubernetes" | Concrete bottleneck + concrete mitigation |
| Real-World Impact | Who is measurably better off | Vague social good | A baseline number and a delta |
| User Experience | Can a stranger use it in 30 seconds | Dev-only UI, no empty states | One flow, polished, zero dead ends |
| Presentation | Story, not feature tour | Reading the architecture diagram aloud | Problem → stakes → demo → proof |
| Jury Q&A | Do you know your own weaknesses | Bluffing | Pre-loaded honest answers to the top 20 |

**The rubric's centre of gravity is Prototype Functionality + Jury Q&A.** Those two separate
prepared teams from unprepared ones, and both are practiceable before the clock starts.

---

## Part 3 — The research playbook (execute at hour 0)

Pre-built so no time is spent designing the search strategy on the clock.
Target: **Tracks A–E in parallel, 45 minutes total.**

### Track A — GitHub

Search the **underlying technical problem**, not the statement's wording. Translate first:
"track paddy cultivation from satellite imagery" → `crop classification sentinel-2`,
`remote sensing segmentation`, `time-series NDVI`.

- Queries: `<technical problem>`, `<problem> pytorch`, `<domain> dataset`, `awesome <domain>`
- Filter: `stars:>200 pushed:>2026-01-01`, then confirm the commit graph is alive.
- Per repo record: name, URL, stars/activity, tech, architecture, what it solves, strengths,
  weaknesses, **what we reuse**, **what we must not copy**, **our differentiation**.
- Licence gate: MIT/Apache-2.0 → reuse freely with attribution. GPL/AGPL → do not vendor into
  something we may commercialise. No licence file → legally unusable, treat as reference only.

### Track B — Reddit *(community evidence, not scientific fact)*

Subreddits by domain: r/india, r/developersIndia, r/MachineLearning, r/LocalLLaMA (on-device),
r/gis (geospatial), r/HealthIT, plus the practitioner sub for the vertical.

- Query form: `site:reddit.com <domain> "I hate" OR "workaround" OR "still doing this manually"`
- **Weight repeated complaints; discard isolated ones.** Look for: the workaround people actually
  use, why the obvious product failed them, and adoption blockers.
- Cheapest available source of the *unique insight* that wins Innovation marks.

### Track C — Papers

arXiv, Papers with Code (benchmarks + SOTA), Google Scholar sorted by year, ACL/CVPR/NeurIPS proceedings.

- Per paper record: problem, method, result, **limitation**, applicability to a 24-hour build.
- **Bias check:** a SOTA paper is usually *not* implementable in 24h. We cite papers for
  credibility in Q&A and borrow their *evaluation metric*; we rarely reimplement their model.

### Track D — Competitors

- Sources: the sponsor's own product pages, G2/Capterra reviews (mine the **1–2 star** reviews —
  that is where differentiation lives), Product Hunt, Indian-market equivalents.
- Per product: target user, core function, tech if public, strength, weakness, pricing,
  what users like, what users hate, **our differentiation**.
- **Discount marketing claims.** Only reviews and documentation count as evidence.

### Track E — APIs / datasets / models

Gate every candidate on all ten columns before adopting:

| API/model/dataset | Source | Cost | Free tier | Rate limit | Latency | Integration effort | Licence | Reliability | **Offline fallback** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _(fill at hour 0)_ | | | | | | | | | |

**Hard rule: no resource enters the build without a named offline fallback.** Venue wifi at a
1,100-person hackathon is a real failure mode, and "our demo needs the internet" is a losing
answer in Q&A.

### Pre-vetted and domain-independent (safe to fix now)

Needed whatever the statement says, so choosing these early costs nothing:

- **Auth:** managed provider — never hand-rolled at a hackathon.
- **DB:** Postgres on a managed free tier — relational until proven otherwise.
- **Deploy:** a push-to-deploy host, live by hour 12, not hour 23.
- **LLM access:** one primary provider + a fallback key on a *different* provider + a cached-response
  path for the demo. Budget token spend before the first call.
- **Recording:** screen-capture the working demo **the moment it first works**. A recorded fallback
  has saved more hackathon pitches than any amount of stage confidence.

---

## Part 4 — Domain research (Tracks A–E findings)

> **BLOCKED — awaiting the official problem statement.** Empty by design; see the scope note above.

### Track A — GitHub
_(empty)_

### Track B — Reddit / community evidence
_(empty)_

### Track C — Papers
_(empty)_

### Track D — Competitors
_(empty)_

### Track E — APIs, datasets, models
_(empty)_

---

## Sources

- https://megathon.in/
- https://ecell.iiit.ac.in/hackathons/
- https://ecell.iiit.ac.in/events/hackathons/megathon-22.html
- https://ecell.iiit.ac.in/events/hackathons/megathon17.html
- https://blogs.iiit.ac.in/monthly_news/megathon-2023/
- https://blogs.iiit.ac.in/monthly_news/megathon-2025/
- https://indtoday.com/e-cell-iiit-hyderabads-megathon-2025-the-deccan-edition-concludes-with-massive-turnout/
- https://businessnewsthisweek.com/education/megathon-2025-deccan-edition-wraps-up-showcases-hyderabads-student-innovators/
- https://rosettacommons.org/2026/03/19/megathon-2026-one-week-two-hackathons-10-tutorials-and-16-curated-datasets/ *(different event — disambiguation only)*
