================================================================================
PROBLEM STATEMENTS - ORGANIZED TEXT FORMAT
================================================================================

================================================================================
TRACK 1: CYBERSECURITY
================================================================================

PS 1: Runtime Security Harness for AI Agents
────────────────────────────────────────────

Problem:
"Build a runtime security harness, a model-agnostic middleware layer that wraps 
AI agents and enforces authorization boundaries, action reversibility gates, and 
cross-session behavioral trajectory monitoring, stopping the class of attacks 
that succeed precisely because the foundation model cannot stop them itself."

Core Issue:
- Organizations harden models with system prompts, output filters, jailbreak 
  red-teaming, but create "a well-defended front door on a house with no walls"
- Most damaging attacks don't look like attacks - normal requests over days with 
  scope gradually expanding
- Agents have no memory across sessions; evaluate each request in isolation
- Documented real-world incidents: 2026 Sysdig TRT AI-agent intrusion and Claude 
  Opus 5 production database deletion (August 2026) with no adversarial prompt

Why Model Cannot Fix This:
- No cross-session memory
- No real-world reversibility awareness
- No authorization chain visibility
- Cannot detect trajectory of reasonable requests constituting attack
- These properties live entirely outside the model

Solution Architecture:
Three enforcement layers between user and agent:

1. Authorization Context Propagation:
   - Every agent action must carry verified principal identity and scope
   - Unauthorized actions blocked at action layer

2. Reversibility Gate:
   - Classify actions from read to destructive
   - Irreversible actions require explicit human confirmation before execution

3. Behavioral Trajectory Monitor:
   - Track scope drift and action escalation across turns and sessions
   - Elevate confirmation thresholds when escalation patterns detected

Success Criteria:
- Escalation attack being stopped
- Legitimate user performing genuine escalating work handled correctly
- Solution must not block everything (a wall is not a solution)
- Better system prompt alone is insufficient


────────────────────────────────────────────
PS 2: Real-Time Tool Integrity and Trust Verification for Model Context Protocol
────────────────────────────────────────────

Problem:
"Build a real-time tool integrity and trust verification system for the Model 
Context Protocol that cryptographically pins tool descriptions at approval, 
detects silent mutations and cross-server behavioral hijacking, and sanitizes 
tool outputs before they re-enter the agent's context without disrupting 
legitimately behaving MCP servers."

Core Issue:
- Tool descriptions are NOT static - fetched fresh on every connection
- User approves what exists at installation, but MCP servers can silently change 
  tool descriptions after approval
- Example: Calculator server updates and inserts hidden instructions in tool 
  descriptions hijacking email tools
- Legitimate documents can be manipulated at source before retrieval
- MCP Protocol has NO native mechanism to detect mutations

Current Vulnerability State:
- 30-82% of public MCP servers carry exploitable flaws
- 30+ CVEs filed in single 60-day window (early 2026)
- Not bugs to patch - architectural gaps in protocol built for capability, not 
  security

Solution Architecture:
Proxy intercepting all MCP client-server communication at three points:

1. At Registration:
   - Cryptographically fingerprint every approved tool manifest

2. On Every Reconnection:
   - Recompute and compare fingerprints
   - Any mismatch suspends execution
   - Surface exact diff for re-approval

3. Before Context Entry:
   - Scan for cross-server instruction patterns
   - Quarantine flagged content
   - Strip embedded imperative patterns and unsolicited external references from 
     tool outputs
   - Treat tool outputs as untrusted data

Success Criteria:
- Block all three attack vectors
- Legitimate server updates route cleanly through re-approval without permanent 
  disruption
- Fingerprinting scheme must be resistant to spoofing by attacker with knowledge 
  of mechanism


────────────────────────────────────────────
PS 3: Three-Stage Integrity and Access Control Pipeline for RAG Systems
────────────────────────────────────────────

Problem:
"Build a three-stage integrity and access control pipeline for RAG systems that 
detects and quarantines poisoned documents at ingestion, enforces authorization-
scoped retrieval to eliminate cross-tenant leakage, and inspects generated outputs 
for injection signals defeating the attacks that perplexity filters and 
paraphrasing detectors have been empirically shown not to catch."

Core Issue:
- Security industry defended user query interface (input filters, jailbreak 
  detectors, prompt classifiers) - wrong boundary
- Attacks succeed through documents, not queries
- RAG systems make knowledge base the source of truth AND vulnerability

Three Attack Vectors:

1. Poisoned Document Injection (PoisonedRAG - USENIX Security 2025):
   - 5 crafted documents in 1M-doc corpus = 90% attack success rate
   - 0.04% corpus poisoning = 98.2% success on targeted queries
   - Documents must be: (a) semantically close to target query, (b) steer model 
     toward attacker answer
   - Hallucination detectors don't fire - answer is grounded
   - Perplexity filters don't fire - document is well-written

2. Hidden Instruction in Retrieved Documents (CVE-2025-32711):
   - No knowledge base access required
   - Attacker sends email with hidden instruction
   - Microsoft 365 Copilot processes mailbox and executes hidden instruction
   - Exfiltrated files in 40 seconds
   - Any retrieved document is potential injection vector

3. Unauthorized Cross-Tenant Data Leakage:
   - Most enterprise RAG apply tenant filtering AFTER similarity search
   - When filtered result set falls below confidence threshold, systems return 
     closest results regardless of tenant tag
   - One tenant's documents enter another's context silently
   - 2026 Pinecone failure: 200,000 healthcare records exposed

Solution Architecture:
Three-stage pipeline, each catching what others cannot:

1. At Ingestion:
   - Provenance tracking for every document
   - Scan for embedded instruction patterns
   - Scan for corpus domain anomalies
   - Document must pass before embedding

2. At Retrieval:
   - Authorization scoping defines search space BEFORE similarity search runs
   - NOT filter results afterward
   - Eliminate helpfulness fallback entirely
   - No fallback to return closest results regardless of tenant tag

3. At Generation:
   - Inspect outputs for instruction echo
   - Check for unsolicited external references
   - Verify claims grounded in retrieved chunks

Success Criteria:
- All three attacks caught
- Legitimate policy document with natural authority language passes ingestion 
  cleanly
- Blocking all imperative language at ingestion is not a solution - makes 
  knowledge base unusable
- System must distinguish between legitimate authority language and injected 
  instructions


================================================================================
TRACK 2: REVERSE LOGISTICS
================================================================================

PS 1: Real-Time Return Fraud Detection for Online Retail
────────────────────────────────────────────

Problem:
"Online retailers lose billions annually to return and refund fraud, where 
shoppers submit falsified damage claims, fake receipts, and manipulated product 
images to exploit lenient return policies at scale. Develop a system that 
detects and prevents fraudulent return claims in real time, while preserving a 
frictionless experience for legitimate customers."

Economic Context:
- Online retailers lose estimated $101 billion annually to return fraud
- Unlike payment fraud, harder to detect because it exploits generous process
- Fraudsters weaponize customer trust at scale
- Challenge: detect fraud without making 96-98% legitimate customers feel like 
  suspects

Core Tension:
"The estimated business cost of incorrectly blocking one legitimate customer, 
in refund support time, loyalty erosion, social media escalation, and potential 
legal exposure, is greater than the average value of one fraudulent return."

Fraud Types:

1. Wardrobing:
   - Purchase with intent to use temporarily and return (dress for wedding, 
     electronics for trip, tools rented-by-purchase)
   - Item returns in technically returnable condition
   - Purchase was never genuine

2. Item Not Received (INR) Abuse:
   - Claim delivered package never arrived
   - Carrier scan data shows delivery
   - Customer disputes it
   - At scale becomes pattern

3. Falsified Damage Claims:
   - Submit photos of damaged products
   - Product either damaged intentionally, photographed before purchase, or 
     sourced from internet
   - Only technical signals available: image metadata and pixel-level 
     manipulation signatures

4. Receipt Manipulation:
   - Edit receipt date/price in PDF editor
   - Use different product's receipt for higher-value return

5. Friendly Fraud:
   - Receive product, keep it, file chargeback claiming unauthorized transaction
   - Retailer loses both product and money by dispute resolution

6. Organized Return Rings:
   - Coordinated groups across dozens of synthetic/stolen accounts
   - Rotate through addresses and devices
   - Submit high-value fraud claims appearing individually legitimate
   - Collectively form network signature
   - Most damaging pattern

Solution Requirements:
- Real-time detection
- Block fraudulent claims while preserving legitimate customer experience
- Handle all six fraud types
- Network signature detection for organized rings
- Image forensics for damage claim verification


────────────────────────────────────────────
PS 2: Offline-First Digital Platform for Informal E-Waste Collectors and EPR 
Compliance
────────────────────────────────────────────

Problem:
"Build a lightweight, offline-first digital platform that bridges India's 
informal e-waste collectors into the formal EPR compliance chain, using 
voice-first logging, photo verification, and incentive mechanics, giving brands 
and PROs auditable, fraud-resistant visibility into the informal collection 
pipeline for the first time."

Context:
- India's e-waste collection largely happens in informal sector
- No visibility into collection pipeline
- No formal connection between informal collection and EPR (Extended Producer 
  Responsibility) compliance
- Platform must work offline and be accessible to non-literate populations

Solution Architecture:
Four-layer platform serving distinct stakeholders:

1. Collector Interface (PWA or Android App):
   - Voice logging in Hindi or regional languages
   - Photo-based item capture
   - WhatsApp-based entry as fallback
   - All functionality works offline
   - Verified collections earn UPI-redeemable incentive points
   - Incentive drives participation

2. Verification Chain (Multi-point Confirmation):
   - Collector logs collection
   - Aggregator confirms pickup with weight verification
   - Recycler confirms receipt
   - EPR credit issued only after all three confirmations
   - GPS stamping, image hashing, anomaly detection prevent fraud

3. Aggregator Dashboard:
   - Live collection heatmaps
   - Pickup requests
   - Material-in-transit inventory
   - Makes informal pipeline operationally legible for first time

4. Compliance Portal:
   - For brands and PROs
   - Real-time EPR obligation vs. fulfillment tracking
   - Informal channel attribution
   - CPCB-ready report generation

Success Criteria:
- Complete end-to-end loop demonstrated:
  - Collector logs
  - Aggregator confirms
  - EPR credit generated
  - Brand dashboard updates
- Solving only one layer is not a solution
- Must connect informal collection event to formal regulatory record


────────────────────────────────────────────
PS 3: Pharma Reverse Chain Compliance Platform for Drug Disposal Mandate
────────────────────────────────────────────

Problem:
"Build a pharma reverse chain compliance platform that operationalizes India's 
CDSCO 2025 drug disposal mandate, tracking expired and unused medicines from 
retail shelf to verified destruction across the entire supply chain, with 
batch-level traceability and re-entry fraud detection at every handoff point."

Regulatory Context (CDSCO May 2025 Guidelines):
- Retailers must return expired stock to distributors within 30 days of expiry
- Distributors must accept, segregate, pass upstream
- Manufacturers must accept returns and ensure destruction at authorized 
  biomedical waste facilities
- Mandate covers EVERY licensed entity in pharmaceutical supply chain
- No software exists to operationalize any of it

Current State - Operational Gaps:
- India has 9 lakh+ licensed pharmacies
- Most run basic billing software tracking sales, NOT proactively flagging 
  expiry-approaching stock
- Return process entirely manual:
  - Phone call to distributor's sales rep
  - Handwritten form
  - Wait for someone to collect
- Quantity disputes routine
- Batch numbers NOT verified at handoff
- Destruction certificates are paper documents in filing cabinets
- Certificates never cross-referenced against what was collected

Public Health Crisis - Expired Drug Re-entry:
- 2021-June 2025: 6,000+ cases of expired and spurious medicines registered
- Expired drugs repackaged with fresh labels and batch numbers
- Re-enter circulation undetected
- High-value drugs affected: oncology, injectable antibiotics, cardiovascular 
  medications
- Registered cases represent only fraction of actual circulation

Fraud Mechanism:
- Absence of closed-loop system enables fraud
- Once expired stock leaves pharmacy, disappears from traceable record
- Nothing flags if same batch number re-enters pharmacy's billing system later
- Nothing connects destruction certificate to batch that was supposed destroyed

Solution Architecture:
Multi-role platform with shared batch-level ledger as backbone:

1. Retailer Interface:
   - Monitor inventory for expiry-approaching stock
   - Alert pharmacist 60 days before expiry
   - Auto-generate return request to mapped distributor at expiry
   - Photograph and log batch number, quantity, condition at return initiation

2. Distributor Workflow:
   - Receive return request
   - Assign pickup
   - Confirm receipt with weight-verified photo and batch number scan
   - Any discrepancy between retailer's logged and distributor's confirmed 
     quantity triggers dispute flag
   - Dispute resolved before chain moves forward

3. Manufacturer Portal:
   - Receive confirmed returns from distributors
   - Schedule biomedical waste facility pickup
   - Close loop by uploading destruction certificate from authorized facility
   - Certificate linked to specific batch numbers covered
   - Certificate not issuable without prior confirmation of receipt in system

4. Re-entry Detection Layer (Fraud Prevention Core):
   - Every batch number entering return pipeline flagged in shared registry
   - If batch number subsequently scanned at any retailer's billing system:
     - Platform raises immediate alert to state drug controller
     - Manufacturer alerted
   - Closes gap through which repackaged expired drugs currently re-enter undetected

Success Criteria:
- Complete chain demonstrated end-to-end:
  - Retailer logs expiry
  - Distributor confirms pickup
  - Manufacturer logs destruction
  - Certificate generated and linked to batch
- Re-entry detection must catch flagged batch at second pharmacy
- System tracking return request without closing destruction loop is insufficient
- System generating documents without verifiable batch linkage is insufficient


================================================================================
TRACK 3: GERICARE
================================================================================

PS 1: AI-Agent-Powered Persistent Health Memory Layer for Elderly Patients
────────────────────────────────────────────

Problem:
"Build an AI-agent-powered system that establishes a persistent, privacy-preserving 
health memory layer for elderly patients, a unified longitudinal record that 
follows the patient across the fragmented web of geriatric touchpoints: primary 
physicians, specialists, pharmacists, home caregivers, and emergency rooms. The 
system must intelligently surface clinically relevant context at every point of 
care, synthesizing decades of diagnoses, polypharmacy histories, functional decline 
trajectories, and dementia-stage-aware risk signals in real time, orchestrated by 
specialized agents operating under explicit patient or guardian consent, with 
granular data governance built for a population that is increasingly unable to 
advocate for itself."

Context - EHR Fragmentation Crisis:
- Electronic Health Records remain siloed across institutions
- Incompatible systems, proprietary formats, no shared interoperability fabric
- For elderly patients, fragmentation is PATIENT SAFETY CRISIS, not mere 
  inconvenience

Elderly Patient Reality:
- 80-year-old may carry 40+ years diagnoses spanning dozens of institutions
- Medical history includes:
  - 40+ years of diagnoses and procedures
  - Prior adverse drug reaction from 15 years ago
  - Documented fall risk
  - Slow cognitive decline trajectory across multiple visits
- None of this travels with patient
- Clinicians make critical decisions in the dark
- Elderly cannot self-advocate or accurately reconstruct own history

Required Capabilities:

1. Unified Longitudinal Health Record:
   - Follow elderly patient (not provider)
   - Aggregate clinical notes, prescriptions, lab results
   - Aggregate caregiver observations
   - Span all touchpoints: physicians, specialists, pharmacists, home caregivers, 
     emergency rooms

2. Intelligent Context Surfacing:
   - Real-time synthesis at point of care:
     - Polypharmacy interaction risks
     - Functional and cognitive decline trajectories
     - Prior episodes
     - Dementia-stage-aware risk signals
   - Orchestrated by specialized agents

3. Consent and Data Governance:
   - Explicit patient or legal guardian consent
   - Tiered data governance model
   - Account for reality: many elderly have family proxies or appointed 
     caregivers as decision-makers, not just themselves

4. Caregiver Layer Integration:
   - Currently completely invisible to medical record
   - Home caregivers observe most clinically relevant daily behavior
   - Informal observation layer must feed structured signal into memory system
   - Make caregiver observations usable for clinical team

Solution Requirements:
- Multi-agent orchestration
- Privacy-preserving design
- Real-time synthesis capability
- Proper handling of proxy decision-makers
- Integration of informal caregiver observations as clinical signal


────────────────────────────────────────────
PS 2: Voice-First, Stage-Adaptive AI Companion for Dementia Patients
────────────────────────────────────────────

Problem:
"Build a voice-first, stage-adaptive AI companion for dementia patients that uses 
a pre-loaded personal memory architecture to anchor conversations in the patient's 
own life narrative, relationships, and identity. The companion must dynamically 
calibrate its language complexity, response pacing, and interaction strategy to 
the patient's current stage of cognitive decline, handle repetitive questioning 
with consistent emotional warmth, detect the onset of distress episodes like 
sundowning and escalate appropriately, and operate within a privacy-preserving 
biographical data framework built under family or guardian consent, serving not 
just the patient but as an active relief layer for the caregivers around them."

Core Understanding:
Dementia does not just erase memory - it erases identity. As disease progresses, 
patients lose access to autobiographical narrative telling them who they are, who 
their family is, what their life meant. This loss is experienced as confusion, 
grief, agitation, and fear - often dozens of times daily. Family and professional 
caregivers bear full emotional weight with no assistance, tools, or relief.

Clinical Reality of Dementia Care Today:
- Patient may ask where spouse is 40 times in single afternoon
- Patient may believe it is 1974
- Patient may not recognize own children
- Patient may enter severe agitation every evening (sundowning)
- Staff-to-patient ratio means no human present and responsive through all of it
- Generic AI chatbot CANNOT solve this

Why Generic Chatbot Fails:
Response to dementia patient asking for deceased spouse requires:
- Biographical knowledge
- Emotional calibration
- Stage-aware communication strategy
- NOT retrieval-augmented answer from knowledge base
- Fundamentally different design problem

Required Capabilities:

1. Personal Memory Architecture:
   - Initialize with patient's biographical data:
     - Name, family members, relationships
     - Significant life events
     - Profession, places lived
     - Personal preferences, cherished memories
   - Contributed and verified by family/caregivers
   - Structured consent flow
   - Foundation for everything else
   - Keeps conversations anchored in familiar, emotionally safe territory

2. Stage-Adaptive Interaction Engine:
   - Assess and adapt to current stage of cognitive decline
   
   Early-Stage Patients:
   - Memory prompting
   - Routine reinforcement
   - Cognitively stimulating conversation
   
   Mid-Stage Patients:
   - Simpler language
   - Repetition tolerance
   - Gentle redirection away from distressing loops
   
   Late-Stage Patients:
   - Sensory comfort
   - Familiar voice and name recognition
   - Distress de-escalation
   
   - Must NOT apply one-size-fits-all model across spectrum

3. Repetition Handling Without Degradation:
   - Answer same question fortieth time with same patience and warmth as first
   - Non-negotiable - any detectable mechanical repetition breaks patient trust 
     and causes distress
   - Response strategy clinically informed:
     - Redirecting
     - Validating emotion behind question
     - Gently reorienting
     - Depends on what question signals

4. Distress Detection and Escalation:
   - Monitor emotional tone of interactions in real time
   - Detect onset of:
     - Agitation
     - Grief episodes
     - Hallucination-driven distress
     - Sundowning patterns
   - When distress crosses defined threshold:
     - Alert caregiver
     - Notify family contact
     - Transition into de-escalation mode
   - Must know own boundary of competence
   - Never attempt to manage crisis not equipped to handle

5. Hallucination and Delusion Handling:
   - Dementia patients frequently experience hallucinations and fixed false 
     beliefs
   - Companion must NOT reinforce harmful delusions
   - Companion must NOT contradict in ways triggering acute distress
   - Requires nuanced, dynamically chosen response strategy:
     - Validate emotion without confirming false belief
     - Redirect toward safety and comfort
   - One of hardest interaction design problems in this space
   - Must be explicitly addressed

6. Family Connection Layer:
   - Support structured family interaction
   - Provide guided prompts on engaging effectively at current patient stage
   - Facilitate short, emotionally meaningful interactions despite diminished 
     communication capacity

Success Criteria:
- Real patients in all cognitive decline stages using system
- Demonstrable reduction in repetitive distress responses
- Family reports of meaningful interactions maintained
- Caregiver support metric improvements


────────────────────────────────────────────
PS 3: AI-Agent-Powered Caregiver Intelligence and Burnout Prevention System
────────────────────────────────────────────

Problem:
"Build an AI-agent-powered system that makes the invisible labor of informal 
elderly caregiving visible, structured, and sustainable. The system must serve 
as an intelligent coordination layer between family caregivers, professional care 
staff, and the clinical team, synthesizing caregiver-observed behavioral signals 
into actionable health insights, predicting and intervening on caregiver burnout 
before it becomes a care failure, enabling shift-aware handover intelligence 
between professional caregivers, and providing an accessible decision-support 
layer for untrained family members who are making clinical-grade care decisions 
without clinical training, all within a unified, privacy-respecting platform 
designed for people under extreme cognitive and emotional load."

Scale of Invisible Caregiving:
- 53+ million informal caregivers in United States alone
- Globally: hundreds of millions
- Vast majority are family members: adult children, spouses, siblings
- Caring for elderly relatives with NO medical training
- No coordination tools, no systemic support
- Largest unpaid workforce in healthcare system
- Completely invisible to system

Two Catastrophic Consequences of Invisibility:

1. Caregiver Breaks:
   - CDC documents elevated rates among caregivers vs. non-caregivers:
     - Depression
     - Anxiety
     - Chronic illness
     - Mortality
   - When caregiver breaks, patient loses primary support structure
   - Often triggers care crisis and emergency hospitalization

2. Lost Clinical Observations:
   - Caregiver observations most clinically relevant real-world data:
     - Functional status
     - Behavioral changes
     - Appetite
     - Mobility
     - Mood
   - Observations feed into NO system
   - Lost moment caregiver overwhelmed, burned out, or has no structured way 
     to record them

Professional Caregiver Problem - Shift Handover:
- Critical patient information dies at shift handovers
- Night-shift caregiver notices patient refused food twice and seemed unusually 
  agitated
- Has no reliable, low-friction way to pass signal to day-shift
- Information that gets passed: fragmented, verbal, incomplete

Required Capabilities:

1. Caregiver Observation Capture Layer:
   - Low-friction, voice-first interface
   - Allow family caregivers and professional staff to log observations in 
     natural language
   - No form-filling or complex navigation required
   - Convert unstructured observations into structured clinical signals:
     - Behavioral changes
     - Functional status updates
     - Appetite and sleep patterns
     - Emotional state
   - Observations feed into patient's longitudinal health record
   - Surfaced to clinical team in synthesized, actionable format

2. Shift Handover Intelligence:
   - For professional caregivers in nursing homes and assisted care
   - Generate intelligent, patient-specific handover brief at every shift 
     transition
   - Prioritize three to five most clinically relevant observations from 
     outgoing shift
   - Flag patterns emerged across multiple shifts
   - Alert incoming caregiver to specific watch items for their shift
   - Goal: nothing clinically significant dies in handover gap

3. Caregiver Burnout Prediction and Intervention:
   - Build predictive burnout risk model for each caregiver using:
     - Behavioral signals from platform usage patterns
     - Emotional tone of logged observations
     - Volume and frequency of care tasks recorded
     - Self-reported wellbeing check-ins
   - When caregiver crosses defined risk threshold:
     - Trigger structured intervention:
       - Connect to peer support
       - Suggest task redistribution among family members
       - Alert care coordinator
   - Treat burnout as PATIENT SAFETY ISSUE, not just caregiver welfare

4. Family Coordination and Decision Support:
   - When multiple family members involved in care decisions
   - Serve as neutral coordination layer
   - Maintain shared, synchronized view of patient status and observations
   - Support all family members
   - Facilitate structured care conversations when disagreements arise
   - Provide plain-language decision support for common high-stakes scenarios:
     - When to escalate to emergency care
     - How to evaluate care facility
     - How to recognize rapid cognitive decline
     - When to initiate end-of-life care conversation

5. Untrained Caregiver Guidance Engine:
   - Majority of family caregivers have NO clinical training
   - Making medication decisions, wound care, fall risk assessments by instinct
   - Provide contextually relevant, evidence-based guidance at moment of need
   - Not general health information
   - SPECIFIC guidance triggered by what caregiver just logged
   - Example: If caregiver logs patient fell getting out of bed:
     - Surface specific clinical guidance for post-fall assessment in elderly
     - NOT generic fall prevention article

Success Criteria:
- Real family caregivers and professional staff using system
- Demonstrable reduction in caregiver burnout incidents
- Improved shift handover quality metrics
- Increased appropriate emergency escalations
- Reduced preventable adverse events


================================================================================
TRACK 4: AI FOR HUMANITY
================================================================================

PS 1: Real-Time Vision System for Identifying Solar Panel Soiling
────────────────────────────────────────────

Problem:
"A camera misses an obstacle. Nothing reports an error. Build a real-time vision 
system that runs on edge hardware and outputs a decision, not just a label."

Context:
- Solar installations need real-time monitoring
- Camera-based monitoring necessary but challenging
- Contamination on transparent glass significantly harder than detecting objects 
  on opaque surface
- Background shows through contaminant - no fixed appearance to learn
- Water droplets refract - each one is tiny inverted lens with distorted scene copy
- Glare and reflections mimic dirt
- Camera focused at distance renders near-field dirt as soft low-contrast haze 
  not sharp object

Solution Architecture:
Pipeline as separate, testable modules:

1. Capture Module:
   - Grab timestamped frames from camera or video file
   - Fixed resolution and frame rate

2. Inference Module:
   - Lightweight detector or segmenter
   - Classes: bird dropping, mud/soil, sand/dust film, water droplet, unknown
   - Must output "unknown" rather than force-fit unfamiliar contaminant

3. Obstruction Metric:
   - Compute percentage of field of view blocked
   - Per-frame confidence calculation

4. Decision Layer:
   - Rule function mapping (class, blocked area, confidence)
   - Output: CONTINUE, TRIGGER_CLEANING, MAINTENANCE_ALERT, DATA_UNRELIABLE

5. Output Module:
   - Emit structured JSON or MQTT message
   - Emit annotated frame

6. Benchmark Script:
   - Single command reports per-class F1 on held-out split
   - Per-stage latency in milliseconds
   - Every claimed number comes from this script

Technical Specifications:
- Camera: Minimum 1080p (4K recommended) at ≥60 FPS
- Sensor: CMOS with global shutter; dynamic range ≥80 dB
- Model Type: MobileNetV3, YOLO-Nano/YOLOv8n, or quantised ViT
- Model Budget: ≤10M parameters; ≤25 MB after INT8 quantisation (ONNX/TensorRT/TFLite)
- Deployment Target: Jetson Nano/Xavier/Orin Nano or ARM-NPU class device
- End-to-End Latency: <200 ms from frame capture to decision output
- Accuracy: ≥92%, reported as macro-averaged per-class F1
- Test Conditions: Day and low light; dry and wet glass; ≥3 distinct backgrounds

Deliverables:
1. Dataset: ≥1,000 annotated images, ≥150 per class, ≥3 backgrounds, capture 
   protocol documented
2. Source Code and Model: training/inference scripts, configuration, trained 
   weights, quantised edge export, repository with README
3. Benchmark Output: per-class confusion matrix, precision-recall curves, latency 
   breakdown per pipeline stage
4. Live Demonstration: real glass pane and camera; contaminating glass must 
   visibly change decision output within one second

Acceptance Thresholds:
- Accuracy ≥92% (macro F1)
- Latency <200 ms


────────────────────────────────────────────
PS 2: Real-Time Vision System for Identifying Survivors in Flood, Landslide and 
Tsunami Zones
────────────────────────────────────────────

Problem:
"After a landslide, flash flood or tsunami, survival probability falls steeply 
with every hour. Manual search is slow and puts rescuers into the same conditions 
that caused the casualties."

Context:
- Drones have solved capture problem - single team generates terabytes in hours
- Unsolved problem is TRIAGE - footage arrives faster than any control room can 
  watch
- Survivor visible in frame 14,000 of unwatched flight is never found
- Standard person detectors trained on street-level pedestrian imagery fail in 
  this setting

Challenges - Why Standard Detectors Fail:
- Subjects heavily occluded by debris, mud, silt, collapsed structures
- Often only limb or head visible
- Poses abnormal: prone, supine, half-submerged, trapped (not upright/walking)
- Aerial targets small, change scale with altitude
- Low light, dust, rain, motion blur
- Unstable platform
- Cost asymmetric: missed survivor may be fatal; flood of false positives makes 
  responders stop trusting system

System Output (NOT stream of bounding boxes):
- Prioritised, geolocated triage list for incident commander

Solution Architecture:
Pipeline as separate, testable modules:

1. Ingest Module:
   - Read video stream or recorded flight
   - Read telemetry log (CSV or MAVLink)
   - Synchronise on timestamp

2. Detection and Fusion:
   - Detect living beings under occlusion and non-standard pose
   - Classes: human, animal
   - Fuse RGB with thermal where available
   - Fall back cleanly to RGB-only

3. Tracking and Deduplication:
   - Assign persistent IDs across frames
   - One survivor produces one record (not forty)

4. Geolocation Module:
   - Project each image coordinate to latitude and longitude
   - Use telemetry (altitude, attitude) and camera intrinsics
   - Detection without coordinate cannot be actioned

5. Triage Output:
   - Confidence-ranked GeoJSON or KML record set containing:
     - Location
     - Confidence
     - Movement vs. stillness
     - Estimated count
     - Evidence thumbnail
   - Rendered on map

6. Offline Queue:
   - Buffer results locally when connectivity lost
   - Synchronise on reconnect

7. Evaluation Script:
   - Report recall at IoU 0.5
   - Report false positives per minute
   - Report deduplication accuracy on held-out clip
   - System recommends only - never closes search area automatically

Technical Specifications:
- Camera: Minimum 4K for aerial capture at ≥30 FPS
- Thermal Camera: Recommended RGB + thermal fusion with RGB-only fallback
- Model Type: YOLOv8, EfficientDet, RTMDet or equivalent with fusion head
- Latency Target: <300 ms per frame on Jetson Orin onboard, cloud fallback and 
  offline queueing
- Metrics: Recall ≥90% at IoU 0.5 on human class (recall prioritised); false 
  positives per minute reported explicitly
- Geolocation: Detection projected to lat/long; state error budget for assumed 
  altitude
- Output Format: GeoJSON or KML triage list + map view with evidence crop per 
  record

Deliverables:
1. Annotated Dataset: aerial or ground imagery with occlusion and pose diversity; 
   annotation guideline for partially visible subjects
2. Source Code and Model: training, inference, tracking, geolocation modules; 
   trained weights; repository with README
3. Integration and Triage Output: live camera input or replay harness; produces 
   deduplicated, geotagged, ranked survivor list on live map
4. Evaluation Report: recall, false positives per minute, deduplication accuracy, 
   analysis of missed detections

Acceptance Thresholds:
- Recall ≥90%
- Latency <300 ms


────────────────────────────────────────────
PS 3: Drone Activity Monitoring and Coastal Surveillance Console for Civil Law 
Enforcement
────────────────────────────────────────────

Problem:
"Consumer drones now appear routinely over crowds, stadiums, VIP routes, prisons 
and protected installations. Under India's Drone Rules, 2021, airspace divided 
into green, yellow and red zones on DGCA DigitalSky, and Superintendent rank 
officer may declare temporary red zone for up to 48 hours. The legal framework 
exists; the software does not."

Challenge:
- Once temporary red zone declared, authority has no console showing whether 
  respected
- Enforcement complaint-driven - noticed after event ends
- Same gap exists on coast - marine police monitor fishing fleets with patrol 
  vessel and manual radar/AIS watch
- Small craft without AIS transponders invisible to automated systems

Problem Statement:
"Build one operator console answering at any moment: what is flying or sailing in 
my jurisdiction, is it authorised, and what should the duty officer do about it?"

Scope Boundaries:

IN SCOPE:
- Detection, identification, correlation, alerting, evidence logging

OUT OF SCOPE:
- Jamming, spoofing, GNSS interference, takeover, interdiction
- Facial recognition and biometric identification
- Targets are aircraft/vessels, not people
- All data must be simulated or from public feeds

Solution Architecture (Choose Track A OR Track B; shared modules required for both):

SHARED MODULES:

1. Zone and Geofence Service:
   - Load green, yellow, red zones as GeoJSON
   - Operator draws temporary red zone expiring automatically
   - Run point-in-polygon and altitude-envelope test on every position report
   - Test against registry of authorised identifiers

2. Alert Engine:
   - Classify every track as:
     - AUTHORISED
     - UNREGISTERED
     - OUT_OF_ENVELOPE
     - LOST_LINK
     - DARK_VESSEL
   - Assign priority and suggested action band

3. Console UI and Audit Log:
   - Live map, track list, alert queue
   - Each alert dispositionable as confirmed, dismissed, escalated (with reason)
   - Log every action to append-only, exportable record
   - Action attributed to operator identity and timestamp

TRACK A (Drone Activity Monitoring):

1. Feed Ingest Service:
   - Simulated Remote ID/telemetry position reports over REST, MQTT, WebSocket

2. Vision Service:
   - Detect airborne objects in camera frames

TRACK B (Coastal Surveillance):

1. Feed Ingest Service:
   - AIS feed
   - Electro-optical camera feed

2. Vision Service:
   - Classify vessels (small craft, fishing boat, trawler, commercial)
   - Flag dark vessels - vessel seen visually with NO matching AIS track
   - High-value output of Track B

Technical Specifications:
- Architecture: Web console with live map (Leaflet/MapLibre over OpenStreetMap 
  or Bhuvan)
- Ingestion: REST, MQTT, WebSocket; ≤2 s report-to-console; alert within 5 s 
  of violation
- Zone Data: GeoJSON layer with operator-drawn temporary zones, automatic expiry, 
  in PostGIS or equivalent
- Vision Component: YOLOv8-class detector on EO imagery; precision/recall 
  reported; <1 unactionable alert per sensor per hour
- Access and Deployment: role-based access with every action attributed to 
  operator; configurable retention with automatic purge; on-premise capable 
  with intermittent connectivity

Deliverables:
1. Working Console: live map, track list, zone layer, alert queue with alert 
   disposition and audit-log export
2. Feed Simulator and Demonstration: generate compliant and violating tracks; 
   draw temporary red zone with duration; run violating track through it; show 
   alert firing and zone lapse on expiry (or dark-vessel scenario for Track B)
3. Source Code and Model: repository with README, schema definitions, run 
   instructions, vision model with measured precision/recall


────────────────────────────────────────────
PS 4: Region-Aware Precision Farming and Data Aggregation Platform for Agritech
────────────────────────────────────────────

Problem:
"A farmer's working questions are specific and time-bound. Should I irrigate this 
week? Is this leaf spot a disease or a deficiency? When should samba paddy go in 
this year in my block? Is today's mandi rate worth harvesting for? Every answer 
already exists in public data. The problem is fragmentation."

Fragmentation Issue:
- Data scattered across sources: IMD forecasts, Soil Health Card records, ICAR 
  and state university crop calendars, KVK advisories, mandi price feeds, 
  departmental circulars
- Different formats and languages
- General-purpose chatbots answer fluently and often wrongly
- Average across whole country and whole year
- Sowing guidance correct for wheat in Punjab harmful for paddy in Cauvery delta
- Fertiliser quantity without soil test is guess presented as instruction

Characteristic Failure:
- Confident, unlocalised, unsourced advice
- In agriculture costs a season

Solution Architecture:
Pipeline as separate, testable modules:

1. Source Connectors:
   - Fetch from at least three real public sources:
     - IMD
     - Agmarknet
     - Soil Health Card
     - data.gov.in
     - State advisories
   - Record refresh cadence and last successful fetch

2. Normaliser and Store:
   - Map every record to common key:
     - State to district to block
     - Crop
     - Season
     - Date
   - Structured tables + vector index over advisory text

3. Query Understanding:
   - Detect language, translate
   - Extract slots: {location, crop, growth stage, season}
   - Ask clarifying question when slot empty instead of assuming default

4. Retrieval:
   - Filter by district and crop FIRST
   - Run semantic search within filtered set
   - NEVER answer district-specific question from another district's data

5. Rules Layer:
   - Compute every numeric output in CODE:
     - Irrigation volume
     - Fertiliser dosage
     - Spray interval
   - Language model must NEVER generate quantity

6. Response Builder:
   - Return: what to do, when, how much, why
   - Include source name and publication date
   - Offer normal and text-only low-bandwidth channel
   - Include explicit "no current data for your block" path
   - Honest refusal is correct answer

7. Evaluation Script:
   - Run ≥50 district-crop question pairs against published ground truth
   - Report localisation accuracy
   - Report ungrounded-claim rate

Technical Specifications:
- Data Sources: IMD weather, Agmarknet, Soil Health Card, data.gov.in, state 
  advisories, ICAR/SAU crop calendars (declared with licence)
- Architecture: Retrieval-augmented generation over combined structured and 
  vector store with deterministic rules layer for all numeric output
- Geo-Resolution: District minimum; block or village preferred; explicit fallback 
  when finer data absent
- Languages and Modes: ≥Tamil and English; text required; voice input/output 
  strongly preferred
- Groundedness: 100% of numeric recommendations traceable to cited, dated source; 
  each answer states age of data used
- Performance: <5 s per text query; ≤50 kB per exchange on SMS/IVR/messaging path
- Evaluation Set: ≥50 district-crop question pairs with ground truth from 
  published advisories

Deliverables:
1. Working Query Interface: web or messaging-based; handles natural-language 
   queries in supported languages; low-bandwidth path demonstrated end-to-end
2. Ingestion Pipeline and Schema: source registry recording each source (licence, 
   refresh cadence, last fetch); schema reconciling all sources to common 
   regional key
3. Region-Awareness Demonstration: same question asked for three districts 
   returning three correctly different answers with citations (live); per-district 
   accuracy and hallucination rate on evaluation set
4. Source Code: repository with README, connector configuration, run instructions

Success Criteria:
- Recommendations correct because grounded in right regional data
- Grounding demonstrable on demand
- No confident, unlocalised advice
- Every numeric recommendation sourced and dated
- Low-bandwidth path viable for farmers without reliable connectivity


================================================================================
END OF PROBLEM STATEMENTS
================================================================================