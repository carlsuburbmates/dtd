# Operations and Observability

## Operator model

DTD has one non-technical operator. `/ops` is the single action and evidence surface. It should prioritise exceptions, explain impact and provide the smallest safe next action.

## Operations Console Transformation Roadmap

The approved Operations Console transformation sequence operates under the governing principle:
**OWNER BY EXCEPTION. AUTOMATION BY DEFAULT. AI ANALYSIS WHEN NEEDED.**

The agreed multi-phase roadmap is:
- **Phase 1 — Noise Elimination & Classification (Implemented & Verified in Developer Sandbox):**
  Eliminates operational noise at its source. Distinguishes routine informational telemetry (e.g. successful HTTP 202 transactional emails, benign initial crawl 404s, expected cold starts) from actionable operational incidents. Enforces cadence-aware bounded grace curves for background loops, evidence-first provider operational status, occurrence fingerprinting for recurrence suppression, and temporal validation for AI degradation events.
- **Phase 2 — Incident Correlation, Lifecycle Integrity, & Verified Recovery (PARTIAL; side-effect-safe engine-tick acceptance blocked):**
  Correlation, lifecycle separation, alias/idempotency, recurrence and read-only oversight have code and sandbox evidence. The developer Scheduler configuration is provisioned and independently inspectable read-only; its `profile=routine` run performs derived and Ops writes and may call Vertex AI, but does not run trainer nurture, reactivation-email or recovery loops. Those effects are not fixture-scoped, so never invoke the scheduled job as a test. Fixture-scoped execution and strict AI budget controls remain open as DF-052; do not claim execution acceptance from Scheduler presence alone.
- **Phase 3 — Minimal Owner-Facing Operations Console (Implemented & Verified):**
  Transforms `/ops` into a decision-first, mobile-responsive Operations Console for a single non-technical owner. Features a 3-Level hierarchy: Level 1 System Status (plain English headline + 3 supporting metrics: Supply, Commercial Gate, Background loops), Level 2 Needs Your Attention (filtering only genuine actionable cases with 3-question breakdowns: What happened?, Why does it matter?, What can I do?, and 1-click triage actions with high-severity dismissal safeguards), Level 3 Handled Automatically (compact telemetry feed of background engine ticks, Guardian audits, fraud suppressions, and delivery recoveries), and a collapsible Secondary Advanced Diagnostics disclosure preserving 10 deep technical views and all existing test IDs. Mobile touch ergonomics and responsive layouts verified at 390px, 768px, and 1440px.
- **Phase 4 — Read-Only, Event-Triggered AI Operations Analyst (IMPLEMENTED; cost-control acceptance PARTIAL):**
  Integrates a read-only AI Operations Analyst powered by Gemini on Vertex AI (`gemini-3.5-flash`). It investigates operational exceptions on demand or during scheduled routine engine ticks. Evidence sanitization, structured output validation, per-occurrence deduplication, cooldowns and a read-only data boundary have code and sandbox evidence. DF-052 remains open: the daily count check is not atomic and fails open on a database query error, so a strict daily cost ceiling is not established.
- **Phase 5 — Separately Approved Controlled Automation & Self-Healing Recovery (Implemented & Verified in Developer Sandbox):**
  Introduces strictly controlled, bounded, deterministic automatic recovery routines for safe operational failures under strict multi-layer safeguards (default-disabled posture `OPS_SELF_HEALING_ENABLED=0`, production hard-block, separate per-routine feature flags, atomic distributed claiming preventing concurrent execution, downstream verified recovery, daily budget ceilings, cooldowns, zero business data mutations, and strict isolation from the read-only Gemini AI Analyst).
- **Phase 5A — Owner Experience Consolidation & Operational Acceptance (Implemented & Verified):**
  Consolidates Phases 1–5 into a unified, exceptionally simple, noise-free mobile-first interface for a single non-technical founder. Reconciles the outdated 11-view daily manual checklist with an exception-driven operating model. Enforces 10-second owner scannability: Level 1 System Status (single plain English headline, zero decorative gauges, calm healthy posture), Level 2 Needs Your Attention (actionable exceptions only, priority-first sorting, bounded pagination and compact filter tabs for 20–30 cases, progressive disclosure for AI analyst and self-healing telemetry, high-severity dismissal protection), Level 3 Handled Automatically (collapsed-by-default truthful aggregate summary of routine passes and verified recoveries, expandable on demand), and Secondary Advanced Diagnostics (collapsed by default, preserving all 10 diagnostic views). Explicitly documents automated coverage across all 14 operational domains and notes residual manual gates.

## Required operating picture

- Public posture and commercial gates.
- Trainer acquisition, review, publication and suppression state.
- Enquiry/matching cases and follow-up state.
- Matching decision-state distribution, AI/fallback degradation, thin-supply expansion, capability-data freshness and urgent-support directory/provider exceptions.
- Message delivery failures, retries and fallbacks.
- Billing, trial, webhook, refund and reactivation exceptions.
- Suburb and sponsor inventory source/capacity.
- Background-loop last success/failure and authenticated schedule evidence.
- Recent immutable audit events.

## Action contract

An action shown in `/ops` must exist end to end. Mutating actions require:

1. authenticated and authorised API boundary;
2. explicit target and confirmation for consequential changes;
3. idempotency or safe duplicate handling;
4. persisted before/after or provider result;
5. audit event with actor, reason and timestamp;
6. notification or fallback where the affected user needs one;
7. truthful success/failure feedback in `/ops`.

Old specifications that list approve/reject/merge/delist/cancel/refund as available do not make those controls real. Implement the approved bounded action or remove the claim.

### Case review semantics, occurrence fingerprinting and invariants (Phase 1)

1. **Read-Only Oversight Contract (DF-032):**
   `GET /api/oversight` is strictly side-effect free. It reads system state, loop health, message logs, and existing review cases without creating, updating, or deleting any database records (e.g. `_read_launch_phase_state()` and `_read_phase_transition_decisions()` replace all former snapshot upsert logic).
2. **Domain Entity Immutability:**
   Operator triage actions (Resolve, Acknowledge, Dismiss via `POST /ops/cases/{case_id}/review`) persist state strictly in `ops_case_states` and `audit_log`. They never mutate underlying business tables (`submissions`, `trainers`, `subscriptions`, `message_log`).
3. **Occurrence Fingerprinting & Recurrence Prevention:**
   Recurrence detection is evaluated strictly against authoritative occurrence fingerprints (`_case_occurrence_fingerprint`), NOT fragile read timestamps or query re-runs. Snapshot rewrites or re-reads with identical fingerprints remain dismissed or resolved. Where occurrence identity is absent or unmodeled in Phase 1, recurrence tracking is explicitly marked `recurrence_tracking: "deferred_to_phase2"` to guarantee review integrity without false alerts.

## Automation contract

Each loop exposes owner, cadence/trigger, input cohort, last run, last success, failure count, next action and retry/fallback. A deployed function without scheduling evidence is not an active automation. Repeated failures become an operator case rather than disappearing into logs.

### Background loop freshness and scheduling contract (Phase 1)

1. **Cadence-Aware Bounded Grace Curves:**
   Blanket 24-hour thresholds are eliminated. Grace periods are derived as a bounded function of the authoritative loop interval (`bounded_grace_seconds()`):
   - 45s health / metrics loops: 30s grace (stale at >75s).
   - 60s ranking / scoring loops: 30s grace (stale at >90s).
   - 10m (600s) engine_tick / master cron loop: 150s grace (stale at >12.5m / 750s).
   - 10m discovery / feed loops: 150s grace (stale at >12.5m).
   - 6h verification / ingestion / reactivation loops: 2,160s (36m) grace (stale at >6.6h).
   - 24h pro trial warnings: 3,600s (1h) grace (stale at >25h).
2. **Execution Priority & Status Matrix:**
   - **Failing loops:** Alert immediately (`status: "fail"` / `health: "failing"`), bypassing grace periods.
   - **Maintenance pause:** `maintenance_paused` when maintenance mode is active.
   - **Unknown cadences:** Flagged as `unknown_cadence` requiring cadence definition.
   - **Serverless Missing Owner (DF-029):** When in-process daemons are disabled (`DISABLE_AUTONOMY=1` or `AUTONOMY_LOOP_OWNER=none`), loops without external scheduled runs report `missing_owner` (not crashed or stale).
   - **Startup Grace:** In-process daemon loops receive a 60s startup grace window from process boot (`startup_pending`).
   - **Clock Skew:** Future timestamps beyond 60s are caught and isolated as `clock_skew`.
   - **Daemon vs External Schedulers:** External schedulers with elapsed runs within bounded grace show `ok`, transitioning to `investigate` and `escalate` as grace multiplies.

## Financial safety

- Stripe mutations fail closed when live mode, permission or feature gate is absent.
- Refund execution remains disabled until live-payment, operator-confirmation, idempotency, inventory-release and audit paths pass production acceptance.
- Trial day-23 warnings run once per eligible provider-backed trial and persist outcome evidence.

## Observability

- API health includes dependency status without exposing secrets.
- Sentry must initialise in the process actually serving production requests before being called active.
- First-party attribution remains privacy-bounded and is not operational authority; Stripe and DTD persistence remain the sources of truth for monetisation reporting.
- Add charts only where they reduce operator effort; a second operator system is not allowed.

### Database and external provider health verification (Phase 1)

1. **MongoDB Atlas Health:**
   Operational status is never inferred from client object instantiation. It requires active operation telemetry within the past 300 seconds (`_record_db_op_success()`). If unobserved, it reports `unknown`; on recent database errors, it reports `unavailable`.
2. **Resend Email Delivery:**
   Status is derived from actual outbound dispatches recorded in `message_log`. Routine successful dispatches (HTTP 202) remain in message history for auditability, but never generate Ops cases. Delivery failures, bounces, or 4xx/5xx responses generate actionable incident cases.
3. **Sentry Error Tracking:**
   Defaults to `unknown` with known gap `"production canary event unverified"` until verified event delivery to the Sentry ingestion endpoint is confirmed.
4. **Deep Health & Scheduler Observability (`/api/health/deep`):**
   Provides deep dependency diagnostics including database connectivity, system state collection access, Cloud Run environment profile, maintenance mode posture, and background scheduler freshness. The freshness threshold is strictly unified with `/ops` loop monitoring at 750 seconds (600s engine-tick cadence + 150s bounded grace). If `engine_tick` age > 750s, it flags `"delayed_or_stale"`; if `last_status != "ok"` (e.g. `partial_error`), it flags `"failing_or_degraded"`.
5. **Decoupled Edge Observability & Coverage Matrix (Monitoring the Monitor):**
   Eliminates circular dependency where a crashed Cloud Run API cannot display an in-console incident. An external Google Cloud Monitoring uptime check probes `https://dogtrainersdirectory.com.au/api/health` from multiple global edge probes every 5 minutes with zero container compute overhead, firing an external alert directly to `admin@dogtrainersdirectory.com.au` on outage. Provisioned idempotently via `scripts/setup_edge_monitoring.sh` and verified end-to-end via `scripts/test_edge_monitoring_delivery.py`.
   - **Covered by Edge Probe:** Total Cloud Run container crashes (HTTP 502/503), process OOM, network routing/NAT failures, and total MongoDB Atlas outages/unreachability (latency < 5m).
   - **Covered by Internal Watchdogs & Durable Ledger (in `/ops`):** Background scheduler stalls (>750s threshold, 1h SLA), unverified/overdue trainer submissions (48h SLA), stuck profile claim locks (4h SLA), failed message deliveries (12h SLA), and external provider auth/quota errors (6h SLA).
6. **Level 1 Honest Status Contract:**
   `/ops` Level 1 guarantees honest state reporting: if background loop telemetry is missing or unobserved, it refuses to report "All Running Normally" and instead displays `monitoring_unverified` ("Monitoring telemetry unverified or stale").
7. **Durable Owner Responsibility Ledger (`db.ops_obligations`):**
   To uphold the non-negotiable invariant that *"no owner-required job can silently disappear in the background"*, DTD persists all owner responsibilities in a dedicated MongoDB collection `db.ops_obligations`.
   - **Indexed Durability:** Unique index on `obligation_id` and compound index on `(status, is_overdue)`.
   - **SLA Policy Matrix:** Authoritative SLA windows per operational domain:
     - `scheduler`: 1 hour (cron stall / missing execution)
     - `claim_lock`: 4 hours (stale or contested listing claim lock)
     - `provider`: 6 hours (critical upstream service outage or credential failure)
     - `client_enquiry`: 12 hours (unmatched or unacknowledged customer dog enquiry)
     - `directory_guardian`: 24 hours (statutory/compliance audit anomaly)
     - `trainer_verification`: 48 hours (held trainer submission needing ABN/statutory check)
     - `billing`: 72 hours (unresolved webhook failure, dispute, or reactivation)
   - **Automatic Escalation Levels:**
     - `Level 0`: Within SLA window.
     - `Level 1` (Overdue): Automatically sets `is_overdue = True`, status `"escalated"`, severity `"high"`, prepending `[OVERDUE ESCALATION]` badge to the summary.
     - `Level 2` (Critical): Escalates priority to highest tier (sorting rank -1 or -2), forcing the case to the very top of `/ops` Work Queue.
   - **Positive-Evidence Terminal Resolution Invariant:** Absence from a scan NEVER resolves an obligation. Query exceptions, collection timeouts, missing source rows, and scan truncations preserve the obligation in its pending/escalated state. An obligation is resolved ONLY when:
     1. Dedicated verifier `verify_obligation_terminal_state(db, obl)` queries the specific underlying entity and finds verified positive evidence that it reached a terminal state (e.g. submission is published or rejected; claim is verified or expired with lock released; message retry succeeded); OR
     2. An explicitly authorised owner action legitimately resolves the case (`state: "resolved"`), creating an immutable audit record with reviewer notes.
   - **Review State Decoupling:** Review acknowledgment (`state: "investigating"`) or dismissal (`state: "dismissed"`) updates `review.review_state` but does NOT resolve the obligation or falsely certify business completion. The obligation remains tracked in `/ops` until verified resolved.
   - **Recurrence Safety:** If an entity re-fails after being resolved (e.g. a new delivery failure, or a stalled scheduler), sync detects recurrence, increments `recurrence_count`, prepends `(Recurred xN)` badge, and reopens the obligation without flapping or history deletion.
8. **Truthful Scheduler Execution Contract & Profile Mutation Boundaries:**
   The master orchestrator `/api/internal/jobs/engine-tick` mandates explicit execution profiles (`profile=monitoring|routine|maintenance|all`). Unknown or malformed profiles fail closed with `HTTP 400`.
   - `profile="monitoring"` (or `"readonly"`): **Strictly ZERO customer/trainer/derived entity mutations.** No profile edits, ranking score updates, conversion promotions, sponsor inventory changes, nurture sequences, reactivation routing, external emails, or self-healing routines. Permitted internal operational-state writes only: `system_state` (telemetry/leases), `ops_obligations` (durable ledger sync), and `ops_ai_investigations` (advisory analysis).
   - `profile="routine"`: Core operational pipeline executing ranking recalculation, conversion promotions, sponsor inventory maintenance, health checks, obligations sync, and AI analysis.
   - `profile="maintenance"`: Routine profile plus trainer nurture and reactivation routing (safely gated with `ENABLE_REACTIVATION_NOTIFICATIONS=0`).
   - `profile="all"`: Full execution profile including recovery evaluation (hard-blocked in production via `is_production_environment() == True`, and default-disabled in sandbox via `OPS_SELF_HEALING_ENABLED=0`).
   - **Subtask Error & Consecutive Failure Tracking:** Captures subtask exceptions without aborting subsequent checks, records `last_status: "partial_error"`, persists `last_error: error_summary`, and increments `consecutive_failures`. Any `partial_error` immediately triggers loop status `"investigate"` or `"escalate"`, regardless of timestamp freshness.
   - **Unified Freshness Policy:** Aligned strictly at 750 seconds (600s interval + 150s grace) across `/ops` and `/health/deep`.
9. **Practical Non-Technical Owner Escalation Hierarchy:**
   DTD is managed by a single non-technical operator. Operational cases in `/ops` must NEVER instruct the owner to modify Python code, run database queries, reconfigure MongoDB, or debug CLI tools. Instead, every case is mapped into:
   - **A. Automated Resolution:** Bounded, deterministic background routines for mechanical faults (e.g. transient locks).
   - **B. Guided In-Ops Action:** Plain-English, safe triage buttons (`Resolve`, `Acknowledge`, `Dismiss`) with structured 3-question guidance (*What happened? Why does it matter? What can I do?*).
   - **C. External Provider Action:** Clear step-by-step instructions and direct destination links for external dashboards (e.g. Stripe, Resend).
   - **D. Technical Specialist Escalation:** When infrastructure expertise is required:
     - Clear indicator: `"Technical assistance may be required."`
     - Reassurance: Explicit `safe_operating_state` (e.g. *"DTD public directory remains operational; routine background ranking and nurture updates are paused."*).
     - Sanitized Technical Handoff: Ready-to-copy diagnostic text summarizing errors, consecutive failure counts, and endpoints without exposing secrets.

### AI degradation telemetry and temporal contracts (Phase 1)

1. **Temporal Validation:**
   AI degradation events with missing or malformed timestamps are strictly prevented from entering rolling 1-hour burst or 24-hour persistent failure windows.
2. **Actionable Diagnostic Alerts:**
   Unrecovered degradation events with missing timestamps remain visible as actionable high-severity incidents with explicit `detected_at: "unknown"`, `Timestamp status: missing_or_malformed`, and `Age: unknown`.

## Matching and urgent-support operating contract

Matching must expose evidence rather than a black-box score: decision-policy version, consent/retention metadata, search scope, triage state, eligible-candidate count, AI or deterministic-fallback path, reason codes, presented result IDs and degraded status. The surface must not reveal behavioural descriptions or other private owner content.

- Capability exceptions show the affected trainer field, evidence basis, freshness state, suppression/invalidating event and the bounded recovery action; `/ops` must not silently turn stale or unsupported data into matchable capacity.
- AI timeout, rate-limit, malformed-output and parity-evaluation failures become visible exceptions. A fallback response is not evidence that the model path is healthy.
- Urgent-support operations show provider-directory freshness, declared coverage gaps, correction/removal requests, source failures and Maps/Places degradation separately from DTD directory facts. Google session content is never persisted in the operating record as a DTD provider fact.
- Outcome and follow-up operations show consent, retry, suppression and terminal failure states. Outcome data cannot be surfaced as a fit advantage until the separately specified attribution, sample, freshness, anti-gaming and appeal contract is accepted.

## Credential and provider resilience

The operator's browser session is an emergency recovery route, not an operating dependency. Runtime credentials and provider-management identities are separate, least-privileged managed secrets. No credential value belongs in source, local environment files, documentation or deployment literals.

- A rotation creates a replacement first, stores a new managed-secret version, verifies a no-traffic/canary or otherwise safe provider path, promotes it, observes it, then revokes the prior credential. Immediate revocation is reserved for active containment.
- The provider register records only sanitised operational metadata: provider/purpose, runtime or management scope, last verification, next expiry/review, degraded behaviour, independent alert route and recovery owner.
- `/ops` must surface a material provider's most recent verified status and failed/stale recovery cases. Health checks must not disclose secrets or become a public control plane.
- A provider integration is not accepted as autonomous until its runtime path, provider-management recovery path, safe verification and independent alert route have all been evidenced. If any is absent, it remains an explicit open finding.

## Environment isolation and staging sandbox contract

The system maintains strict isolation between live production and staging/sandbox environments:

- **Production Environment:**
  - Google Cloud Project: `gen-lang-client-0028123502`
  - Database: MongoDB Atlas cluster `DTD` (`dtd` database)
  - Purpose: Live dog owners, registered trainers, real Stripe subscriptions, and production domain (`dogtrainersdirectory.com.au`).
  - Access & Mutations: Zero-downtime rolling/canary deployments; strict production change control; gated commercial/refund activations.

- **Staging / Sandbox Environment:**
  - Google Cloud Project: `dogtrainersdirectory-dev`
  - Database: MongoDB Atlas cluster `dtd-sandbox` (`dtd_sandbox` database, AWS Sydney `ap-southeast-2`)
  - Purpose: Developer experimentation, AI-assisted development, feature testing, and automated build verification.
  - Guardrails: Stripe operates strictly in Test Mode (`sk_test_...`); transactional emails target dummy/test sinks; directory data is non-production; zero-cost idle state (serverless scale-to-zero).
  - Promotion Gate: Features, data migrations, or infrastructure changes must pass verification in the sandbox before promotion to production.
  - Deployment Automation: Executable via `bash scripts/deploy_sandbox.sh`. It runs mandatory preflight compilation and release-gate checks, deploys `dtd-api-dev` with Secret Manager bindings, and fails unless `/api/health` confirms an available `dtd-sandbox` database. It may be run only by an authenticated, authorised operator or assistant; it is not an authority for arbitrary agents or for production promotion.

## Operating cadence and daily responsibilities

DTD operates under a single solo operator model. The operator does not perform repetitive background monitoring or manual database manipulation; instead, `/ops` consolidates exceptions into prioritised actionable triggers with bounded mutations and immutable audit events.

### Operational Principles

1. **Owner by Exception (10-Second Scan):** Never poll or guess. The owner visits `/ops` once daily (or when alerted). In approximately 10 seconds:
   - *Is DTD operating normally?* (Level 1 Status headline)
   - *Does anything genuinely require my attention?* (Level 2 Needs Your Attention work queue)
   - *What has the system already handled automatically?* (Level 3 Handled Automatically summary)
   If Level 1 is green ("All systems running normally") and Level 2 shows "No action required", the operator's check is complete.
2. **Fresh Authenticated State:** Always click `[Refresh]` (`data-testid="ops-refresh"`) before making an operational decision. Never act on stale browser memory.
3. **Bounded 1-Click Mutations:** Use the rapid triage buttons (`Resolve`, `Acknowledge`, `Dismiss`) or specific control triggers. Every mutation records an immutable audit log with reviewer ID, timestamp, and before/after diffs. High-severity dismissal requires an explanatory review note.
4. **Fail-Closed Safety:** Commercial checkouts remain disabled (`ENABLE_TRAINER_BILLING_CHECKOUT=0`) and matching degrades to deterministic fallback upon any provider fault. Never override safety gates without explicit verification.
5. **Progressive Disclosure:** Action before explanation. Secondary diagnostic views (the 10 technical subsystems) remain collapsed by default and are opened only when investigating a specific anomaly.

### Operational Domain Coverage Map (14 Domains)

The Operations Console comprehensively accounts for all 14 core operational domains, distinguishing automated background handling from residual owner exception gates:

| # | Operational Domain | Automated Handling (Automation by Default) | Owner Exception Gate (Owner by Exception) |
|---|--------------------|--------------------------------------------|-------------------------------------------|
| 1 | **Submissions** | Automated ingestion pipeline, deduplication, and initial risk rule scoring. | Manual statutory verification (ABN, business registry) before publishing new trainer listings. |
| 2 | **Claims** | Automated OTP verification dispatch, claim expiration, and stale lock auto-recovery. | Contested claim review or manual identity escalation. |
| 3 | **Matching Engine** | Deterministic + Gemini AI fit scoring, search scope expansion, urgent vet triage. | Reviewing high AI degradation alerts or repeated fallback events. |
| 4 | **Directory Corrections** | Automated Google Places cross-referencing and submission receipt. | Owner approval/rejection of public directory phone/suburb modifications. |
| 5 | **Notifications** | Transactional delivery via Resend, retry backoffs, and auto-recovery of stalled dispatches. | Persistent delivery failure review (invalid customer email/SMS). |
| 6 | **Trainer Supply** | Live inventory accounting, intro-ready calculation, and suburb coverage metrics. | Targeted outreach when critical suburb supply is thin. |
| 7 | **Capability** | Automated profile capability tag indexing and health tracking. | Manual on-demand capability refresh (`ops-recheck-capability`). |
| 8 | **Demand & Waitlists** | Customer waitlist intake, location grouping, and demand gap computation. | Reviewing unfulfilled demand hotspots in pipeline flow. |
| 9 | **Commercial & Billing** | Stripe webhook processing, trial tracking, and fail-closed commercial gate enforcement. | Refund approval (`refundSubscription`) and billing reactivation cases. |
| 10 | **SEO & Indexation** | Canonical 539 Melbourne suburb page evaluation against supply and content thresholds. | Final indexation decision override when thresholds are met. |
| 11 | **Audit & Security** | Immutable append-only audit logging (`audit_recent`) and admin passcode session expiry. | High-severity dismissal justification note verification. |
| 12 | **Provider & Background Loops** | 10 background loops orchestrated via Cloud Scheduler `dtd-engine-tick-cron` with atomic leasing. | Provider outage acknowledgement (`ops-ack-degradation`) if upstream provider is degraded. |
| 13 | **AI Operations Analyst** | Read-only Gemini 3.5 Flash investigation with evidence sanitization and PII redaction; strict daily cost enforcement is open under DF-052. | Reviewing AI root-cause hypotheses and suggested remediation plans. |
| 14 | **Self-Healing & Recovery** | Bounded deterministic recovery routines (lease clearing, claim unlock, notification retry). | Reviewing exhausted recovery attempts escalated to Level 2. |

### Cadence Reconciliation: From Manual Checklist to Exception Triage

In earlier revisions, operational documentation specified an 11-step manual checklist requiring the operator to inspect six separate tabs daily (Overview, Matching Engine, Work Queue, Messages, Trainer Supply, Billing).

Under Phase 5A, this manual cadence is **fully superseded**:
- Routine healthy executions across all 14 domains are automatically verified by background guardians and consolidated into **Level 3 (Handled Automatically)**.
- Telemetry requiring intervention is automatically escalated and surfaced into **Level 2 (Needs Your Attention)** with 3-question structured guidance: *What happened? Why it matters? What to do?*
- The operator does not navigate across individual tabs during routine daily operations. The 10 secondary diagnostic views are preserved under **Advanced Diagnostics** strictly for deep investigation when an anomaly requires root-cause tracing.

## Operations Console Deployed State & Sandbox Acceptance

- **Production Cloud Run Revision:**
  The live production backend serving 100% of traffic remains pinned to `dtd-api-00058-ter` (deployed on 15 October 2026, Google Cloud project `gen-lang-client-0028123502` in `australia-southeast1`).
  - Runtime administrative passcode (`ADMIN_PASS`) is mounted to Secret Manager secret `dtd-admin-pass` version 3 (`enabled`), with version 2 (`disabled`).
  - Production datastore is MongoDB Atlas cluster `DTD` (`dtd` database).
  - Production frontend is Firebase Hosting serving assets `index-B0KVx6z6.js` and `index-CiXd5jGR.css`.
  - **Production deployment is NOT performed.** Production promotion remains a separate final gate requiring explicit owner authorisation.
- **Developer Sandbox Deployed Revision:**
  - Consolidated into `main` (`aa63d56`) and deployed to developer sandbox Cloud Run service `dtd-api-dev` on revision `dtd-api-dev-00034-kkv` (100% traffic, project `dogtrainersdirectory-dev`, `australia-southeast1`).
  - Live sandbox endpoint: `https://dtd-api-dev-x2kdoaemtq-ts.a.run.app`.
  - Live sandbox datastore: MongoDB Atlas `dtd_sandbox`.

### Phase 2 Architecture & Implemented Workstreams (Partial; sandbox tick gate blocked)

1. **Workstream A — Incident Correlation & Noise Elimination:**
   - Multi-attempt message delivery retries collapse into a single correlated incident keyed by `message:{dispatch_id}`.
   - Distinct IDs are preserved across event, dispatch, attempt, and incident layers.
   - Correlated provider outage incidents group concurrent failures with root cause tokens (e.g. `provider_outage:resend:5xx`).
   - Conservative fallback for legacy message events without explicit dispatch IDs correlates identical message types and targets within 1-hour windows.
2. **Workstream B — Incident Lifecycle & State Decoupling:**
   - Machine `operational_state` (`detected`, `recovering`, `resolved`, `reopened`) is strictly separated from human operator `review.state` (`detected`, `investigating`, `resolved`, `dismissed`).
   - High-severity incident dismissal requires an explanatory review note of at least 5 characters (`HTTP 400` safeguard).
   - Dismissal and investigation notes persist auditably in `ops_case_states` and `audit_log`.
3. **Workstream C — Verified Automatic Recovery & Alias Resolution:**
   - Terminal success events automatically resolve and clear transient delivery failure incidents.
   - Case reviews submitted against constituent event IDs (aliases) resolve seamlessly to primary correlated incident IDs.
   - Idempotent review updates with identical state, owner, and note execute safely without creating duplicate audit records.
4. **Workstream D — Serverless Background Scheduling & DF-029 (provisioning DONE; execution acceptance blocked):**
   - The developer Scheduler job and authenticated endpoint exist, and the distributed lease records execution telemetry.
   - The enabled `profile=routine` job runs ranking, inferred-conversion promotion, sponsor inventory, health checks, durable obligation synchronization and scheduled AI analysis. It does not run trainer nurture, reactivation-email or recovery loops. Its derived/Ops writes and possible Vertex AI call are not fixture-scoped, so the live verifier checks configuration read-only and never invokes the job. Fixture-scoped execution and strict AI cost controls remain open under DF-052.
5. **Workstream E — Occurrence Identity & Genuine Recurrence:**
   - Authoritative occurrence fingerprints (`_case_occurrence_fingerprint`) across all case types prevent false recurrence on browser refresh or snapshot re-reads.
   - When a new failure occurs with distinct error telemetry or higher failure counts, previously dismissed cases reopen automatically to `operational_state: "reopened"` with an explicit `(Recurred)` badge.
6. **Workstream F — Frontend Compatibility:**
   - `/ops` Work Queue correctly maps `reopened` into `Needs review` and `recovering` into `In progress`.
   - Message log rows display `Recovering` badges when dispatches are actively recovering.

### Phase 2 Sandbox Acceptance Gate (PARTIAL; Workstream D BLOCKED)

Historical isolated acceptance on revision `dtd-api-dev-00034-kkv` verified the following safe gates. The 21 October audit supersedes its previous Gate 5 result: `scripts/verify_sandbox_ops_phase2.py` reads Scheduler configuration only. Routine engine-tick effects are not fixture-scoped, so it does not invoke the job.
- **Gate 1 — Deployed Revision & Environment Isolation:** **PASS** (Active revision `dtd-api-dev-00034-kkv` verified; database available; production environment independently verified untouched and healthy).
- **Gate 2 — Workstream A: Incident Correlation:** **PASS** (3 retry attempts correctly grouped into exactly 1 incident; terminal success cleared prior transient failures).
- **Gate 3 — Workstream B & E: Lifecycle & Recurrence:** **PASS** (Dismissal safeguard verified rejecting note < 5 chars; valid dismissal verified; identical refresh produced no false recurrence; genuine failure reopened case with `(Recurred)` badge).
- **Gate 4 — Workstream C: Alias Resolution & Idempotency:** **PASS** (Alias lookup by constituent event ID resolved to primary case; repeat identical update created 0 duplicate audit records).
- **Gate 5a — Workstream D: Scheduler configuration (DF-029):** **PASS** when the read-only verifier confirms enabled state, cadence, timezone, URI/profile, POST method, `{}` body and exact OIDC service account/audience.
- **Gate 5b — Side-effect-safe engine-tick execution:** **BLOCKED** because routine effects are not fixture-scoped and scheduled AI cost controls are not strict (DF-052). The routine profile does not run trainer email or recovery loops.
- **Gate 6 — Read-Only Oversight Invariant (DF-032):** **PASS** (`GET /api/oversight` executed side-effect free with exactly zero database writes to snapshots, state, or audit log).
- **Gate 7 — Zero-Trace Fixture Disposal:** **PASS** (100% synthetic test fixtures cleaned up from `dtd_sandbox` collections).

### Phase 3 Architecture & Operator Surface (Verified Complete)

Phase 3 transforms the `/ops` application from a dense technical debugging surface into an exception-driven, mobile-first Operations Console for a single non-technical owner:

1. **Level 1 — System Status (10-Second Readability):**
   - **Headline & Status Derivation:** Computes one of four plain-English operational states based on authoritative telemetry:
     - `All running normally` (emerald): 0 active high/medium cases, 0 failing loops, database connected, engine tick fresh.
     - `Some services need attention` (amber): non-critical degraded loop, medium-severity case, or thin supply warning.
     - `Action required` (rose): 1 or more high-severity cases in `Needs review` or critical database/connectivity failure.
     - `Status unavailable` (slate): disconnected database or unparseable telemetry snapshot.
   - **Decision Summary:** Clear, concise prompt on whether action is needed or normal monitoring should continue.
   - **Three Supporting Metrics:**
     - *Directory Supply:* Intro-ready trainers vs blocked/pending verification.
     - *Commercial Gate:* Strict verification of fail-closed posture (`ENABLE_TRAINER_BILLING_CHECKOUT=0`, $0 financial risk).
     - *Background Systems:* Count of healthy autonomous loops (e.g. 10/10) with serverless engine-tick status.

2. **Level 2 — Needs Your Attention (Actionable Exceptions Only):**
   - **Strict Exception Filtering:** Displays only genuine owner-actionable cases (`detected`, `notified`, `reopened`). Dismissed, investigating, or recovered cases are excluded from the primary view.
   - **Structured 3-Question Incident Breakdown:**
     - *What happened?* Clean summary or error description.
     - *Why does it matter?* Concrete business and operational impact explanation.
     - *What can I do?* Recommended operator intervention.
   - **One-Click Rapid Triage Actions:**
     - `[Acknowledge]`: transitions state to `investigating`, persisting note `"Acknowledged by owner in daily ops triage; monitoring."`
     - `[Resolve]`: transitions state to `resolved`, persisting truthful note `"Resolved by owner in daily console review."` or `"Resolved by owner in daily ops review."` (eliminating unperformed statutory verification claims).
     - `[Dismiss]`: transitions state to `dismissed`. Enforces explanatory note ($\ge 5$ characters) for high-severity incidents (`HTTP 400` safeguard).
     - `[Details]`: collapsible drawer revealing incident metadata (occurrences, recurrence count, constituent event IDs, affected entity).
     - `[Work Queue ->]`: direct deep-link into the full Work Queue view.
   - **Trustworthy Empty State:** Reassures the owner with a clean green checkmark when 0 cases require intervention (`"No action required - Your Work Queue is completely clear."`).

3. **Level 3 — Handled Automatically (Autonomous Feedback):**
   - Surfaces background autonomous actions that completed without requiring operator friction:
     - Cloud Scheduler engine ticks (ranking, inference, health, nurture, inventory).
     - Guardian supervisory compliance audits.
     - Fraud and duplicate submission suppressions.
     - Transactional delivery recoveries and retries.
     - Auto-resolved transient incidents.
   - Includes timestamp, task name, and count; truthful neutral empty state if zero automated tasks ran in the last 24h.

4. **Secondary — Collapsible Advanced Diagnostics Disclosure:**
   - Hidden by default behind a clean disclosure toggle (`data-testid="ops-diagnostics-toggle"`).
   - Preserves 100% of underlying diagnostic capabilities, views (`pipeline_flow`, `matching`, `trainer_supply`, `messages`, `billing_reactivation`, `seo_indexation`, `attribution`, `system_activity`, `recent_changes`, `work_queue`), and automated test IDs.
   - Expandable on demand for deep inspection without polluting the primary executive console.

5. **Mobile-First Ergonomics & Accessibility:**
   - Touch targets designed for fingers ($\ge 44\text{px}$ button height/padding).
   - Responsive grid (`sm:grid-cols-3` adapting cleanly down to single-column on mobile).
   - Zero horizontal overflow across 390px (mobile), 768px (tablet), and 1440px (desktop) verified via headless Chrome CDP capture.

### Phase 3 Verification & Test Coverage (VERIFIED COMPLETE)

- **Frontend Vitest Suite:** 66/66 tests passed across 10 test files (including 19/19 in `Ops.test.jsx` verifying 3-Level hierarchy, status derivation, triage handlers, dismissal safeguards, and diagnostics disclosure).
- **Frontend Production Build:** Vite 8 production build completed cleanly in <1s (`build/index.html` 1.45 kB, `build/assets/index-DxZkQIHU.js` 821 kB).
- **Backend Pytest Suite:** 497/497 unit and ops tests passed across `test_ops_phase1_noise_elimination.py`, `test_ops_phase2_incident_lifecycle.py`, and all domain unit suites.
- **Visual Responsiveness Verification:** Automated headless Chrome CDP capture (`scripts/verify_ops_phase3_visuals.mjs`) verified:
  - `ops_phase3_mobile_390.png`: 390x844 mobile viewport, touch targets compliant, zero overflow.
  - `ops_phase3_tablet_768.png`: 768x1024 tablet viewport, clean 3-card metrics layout.
  - `ops_phase3_desktop_1440.png`: 1440x900 desktop viewport, decision-first reading order.
  - `ops_phase3_diagnostics_expanded.png`: 1440x900 expanded diagnostics, sidebar navigation and views accessible.

### Phase 3 Developer Sandbox Live Deployment & Acceptance Verification (VERIFIED COMPLETE)

The Phase 3 Operations Console implementation was deployed to the isolated developer sandbox (`dogtrainersdirectory-dev`) and verified live end-to-end via headless Chrome CDP against the live URLs:
- **Sandbox Frontend Service:** `dtd-web-dev` serving Cloud Run revision `dtd-web-dev-00014-922` at 100% traffic (`https://dtd-web-dev-x2kdoaemtq-ts.a.run.app`). Bundle verified routing API requests to canonical sandbox backend.
- **Sandbox Backend Service:** `dtd-api-dev` serving Cloud Run revision `dtd-api-dev-00036-jqb` at 100% traffic (`https://dtd-api-dev-x2kdoaemtq-ts.a.run.app`). Preflight and database checks passed.
- **Production Isolation:** Production backend `dtd-api` remains strictly locked to revision `dtd-api-00058-ter` in project `gen-lang-client-0028123502`. Zero production mutations, zero external emails, zero live charges.

**Acceptance Gate Matrix (Live Sandbox):**
- **Gate A — System Status (Overall Operational Posture):** `PASS`. Non-technical owner banner accurately indicates `"Action required on high-priority items"` with decision summary and 3 clear metrics (Directory Supply: 20 intro-ready; Commercial Gate: Fail-Closed Enforced / $0 risk; Background Systems: 3/10 healthy).
- **Gate B — Needs Your Attention (Actionable Work Queue):** `PASS`. Displays genuine actionable exceptions only. Structured 3-question breakdown (*What happened?*, *Why does it matter?*, *What can I do?*) verified rendering live case cards.
- **Gate C — Handled Automatically (Autonomous Feedback):** `PASS`. Live telemetry feed displays verified background actions (Guardian audits, scheduled tasks, transient self-healing).
- **Gate D — Administrative Review & Actions:** `PASS`. Quick triage actions (`[Acknowledge]`, `[Resolve]`, `[Dismiss]`) function correctly. Note wording updated to truthful `"Resolved by owner in daily console review."` / `"Resolved by owner in daily ops review."` without unperformed statutory claims. High-severity dismissal reason safeguard verified.
- **Gate E — Advanced Diagnostics Disclosure:** `PASS`. Hidden by default (`sidebarVisibleByDefault: false`). Clean toggle button expands all 9 underlying diagnostic views on demand.
- **Gate F — Responsive Ergonomics & Visual Quality:** `PASS`. Live browser screenshots captured across viewports:
  - Mobile (390x844): `ops_live_phase3_mobile_390.png`
  - Tablet (768x1024): `ops_live_phase3_tablet_768.png`
  - Desktop (1440x900): `ops_live_phase3_desktop_1440.png`
  - Diagnostics Expanded (1440x1200): `ops_live_phase3_diagnostics_expanded.png`
- **Gate G — Production & Financial Isolation:** `PASS`. Sandbox runtime strictly isolated, commercial checkout gated off, production untouched.

### Phase 4 — Read-Only AI Operations Analyst (IMPLEMENTED & VERIFIED IN DEVELOPER SANDBOX)

The Phase 4 AI Operations Analyst introduces an intelligent, read-only diagnostic assistant inside `/ops` that helps the non-technical owner understand and resolve operational exceptions.

#### 1. Architecture & Core Boundaries
- **Advisory Only (Strict Read-Only Boundary):** The AI Operations Analyst has ZERO mutation authority. It cannot update case operational states, dismiss incidents, edit reviews, modify trainers or submissions, adjust billing states, rotate credentials, or trigger scheduler jobs. Its persisted artifacts reside solely in `ops_ai_investigations`.
- **Zero Polling & Event-Triggered Execution:**
  - Automated investigations trigger solely for eligible active incidents (actionable `high`-severity cases or persistent `medium`-severity symptoms) during scheduled serverless background execution (`/api/internal/jobs/engine-tick`).
  - On-demand investigations trigger solely upon explicit operator request via `POST /api/oversight/cases/{case_id}/investigate`.
  - Regular page loads or manual refreshes of `GET /api/oversight` perform ZERO external AI calls ($0 inference cost); they read pre-computed cached investigations from `ops_ai_investigations`.
- **Strict Evidence Minimization & PII Sanitization (`sanitize_text`):**
  - All raw inputs (error diagnostics, summaries, detail rows) undergo deterministic regex-based redaction before being passed to inference or persisted.
  - Redacts: Bearer tokens (`[REDACTED_TOKEN]`), Resend API keys (`[REDACTED_RESEND_KEY]`), Stripe secrets (`[REDACTED_STRIPE_KEY]`), generic API keys/secrets (`[REDACTED_SECRET]`), Mongo connection URIs (`[REDACTED_MONGO_URL]`), email addresses (`j***@example.com`), and Australian phone numbers (`[REDACTED_PHONE]`).
- **Cost-Containment & Abuse Safeguards:**
  - **Per-Occurrence Deduplication:** Investigations are cached against an evidence signature and `occurrence_fingerprint`. Repeat inquiries for identical occurrences return cached results without re-inference.
  - **Configured Daily Limit:** `OPS_AI_DAILY_BUDGET=50` is a nominal count of completed calls per calendar day. The current count-then-call path is non-atomic and fails open on database query errors; DF-052 means this is not a strict cost ceiling.
  - **Manual Request Cooldown:** `OPS_AI_MANUAL_COOLDOWN_SECONDS=60` enforces a 60-second debounce per case, returning HTTP 429 to prevent rapid-click budget exhaustion.
  - **Token & Batch Bounding:** Output tokens bounded (`max_output_tokens=1024`), batch size capped (`max_batch=3` per loop iteration).
- **Graceful Failure Isolation & Deterministic Fallback:**
  - Network timeouts (15s ceiling), quota exhaustion, or Vertex AI provider errors degrade gracefully to `deterministic_analyst_fallback` based on known system architecture, ensuring directory operations are never interrupted.

#### 2. Structured JSON Output Schema
Gemini inference is constrained to a strict JSON response schema:
```json
{
  "summary": "1-2 sentence plain-language summary of what failed",
  "root_cause_classification": "confirmed | likely | possible | unknown",
  "root_cause_hypothesis": "Technical hypothesis identifying likely cause",
  "supporting_evidence": ["Bullet points of verified evidence"],
  "evidence_gaps": ["Unverified aspects or missing data"],
  "confidence_score": 0.95,
  "operational_impact": "Plain-English description of business impact",
  "recommended_action": "Smallest safe action the owner should take",
  "requires_owner_intervention": true,
  "safety_and_governance_notes": "Advisory reminder of read-only scope"
}
```

#### 3. API & Console Integration
- `POST /api/oversight/cases/{case_id:path}/investigate`: Authenticated endpoint (`require_oversight`) for owner-requested investigation.
- `GET /api/oversight`: Includes `ops_ai_analyst` status object in root payload (`enabled`, `model`, `daily_budget`, `total_investigations`), and attaches `ai_investigation_status`, `ai_investigation_id`, and `ai_analysis` to case items.
- `/ops` Console UI (`AiAnalysisCard`):
  - Displays classification badge (`Confirmed Cause`, `Likely Cause`, `Unknown Cause`).
  - Summarizes hypothesis and operational impact in plain language.
  - Lists supporting evidence bullets.
  - Highlights recommended operator next steps.
  - Provides a 1-click "Request Updated Analysis" button with cooldown and loading state.

#### 4. Developer Sandbox Live Deployment & Acceptance Verification (VERIFIED COMPLETE)

Deployed to developer sandbox `dogtrainersdirectory-dev` and verified live end-to-end via automated acceptance suite (`scripts/verify_sandbox_ops_phase4.py` and `scripts/verify_sandbox_ops_phase4_live_ui.mjs`):
- **Sandbox Backend Service:** `dtd-api-dev` serving Cloud Run revision `dtd-api-dev-00038-s6w` at 100% traffic (`https://dtd-api-dev-625222421634.australia-southeast1.run.app`).
- **Sandbox Frontend Service:** `dtd-web-dev` serving Cloud Run revision `dtd-web-dev-00016-b2d` at 100% traffic (`https://dtd-web-dev-625222421634.australia-southeast1.run.app`).
- **Production Isolation:** Production backend `dtd-api` remains strictly locked to revision `dtd-api-00058-ter` in project `gen-lang-client-0028123502`. Zero production mutations, zero live charges, zero external communications.

**Acceptance Gate Matrix (Live Sandbox):**
- **Gate A — Real Incident Trigger:** `PASS`. Synthetic high-severity failure fixture (`test-p4-...`) successfully entered the pipeline and was detected in `/api/oversight`.
- **Gate B & D — Live Gemini Inference with Structured Schema:** `PASS`. Live Vertex AI inference (`gemini-3.5-flash`) returned valid structured JSON with `root_cause_classification: "confirmed"`, accurate hypothesis, supporting evidence list, and recommended action.
- **Gate C — Deduplication & Caching:** `PASS`. Verified that exactly 1 investigation document was persisted in MongoDB; repeat requests returned cached results without redundant inference ($0 extra cost).
- **Gate E — Evidence Minimization & Sanitization:** `PASS`. Verified that raw API keys, bearer tokens, and client email addresses were redacted (`[REDACTED_RESEND_KEY]`) before entering inference or storage.
- **Gate F — Strict Read-Only Invariant:** `PASS`. Zero mutations occurred in `ops_case_states`, `trainers`, `submissions`, or core directory collections.
- **Gate G — Manual Request Cooldown:** `PASS`. Rapid repeat requests within 60s cooldown returned HTTP 429 (`"Analysis recently requested. Please wait Xs before refreshing."`).
- **Gate H — /api/oversight Read-Only Enrichment:** `PASS`. `GET /api/oversight` automatically enriched eligible cases with cached AI analysis documents.
- **Gate I — Live UI Acceptance & Screenshots:** `PASS`. Headless Chrome CDP live inspection verified `AiAnalysisCard` DOM rendering, Confirmed Cause badge, hypothesis, recommendation, and action button across viewports:
  - Mobile (390x844): `ops_live_phase4_mobile_390.png`
  - Tablet (768x1024): `ops_live_phase4_tablet_768.png`
  - Desktop (1440x900): `ops_live_phase4_desktop_1440.png`
  - Expanded AI Analysis View (1440x1200): `ops_live_phase4_ai_analysis_expanded.png`
- **Zero-Trace Cleanup:** `PASS`. All disposable test fixtures and investigations were deleted completely from `dtd_sandbox`.

## Phase 5 — Controlled Automation & Self-Healing Recovery (Implemented & Verified in Developer Sandbox)

### 1. Architectural Philosophy & Governing Boundaries

Phase 5 introduces strictly bounded, idempotent automatic recovery ("self-healing") for operational failures that can be corrected deterministically, safely, and with verifiable outcomes.

**Safety Invariants & Governance Principles:**
1. **Owner by Exception, Automation by Default:** The owner should not spend time manually intervening in trivial, mechanical faults (e.g. expired background job locks or transient HTTP 429 backpressure).
2. **Safe Defaults (Default-Disabled Posture):** All self-healing routines are disabled by default (`OPS_SELF_HEALING_ENABLED=0`).
3. **Production Hard-Block:** In production (`is_production_environment() == True`), all automatic recovery routines are unconditionally hard-blocked. Production activation requires explicit, separate future owner authorization.
4. **Separate Routine Gating:** Each recovery routine is governed by its own independent feature flag (`OPS_RECOVERY_LEASE_ENABLED`, `OPS_RECOVERY_CLAIM_LOCK_ENABLED`, `OPS_RECOVERY_NOTIFICATION_ENABLED`).
5. **No Business Mutations:** Self-healing never alters listing ownership, ABN verification status, public directory visibility, or customer billing.
6. **Atomic Distributed Claiming:** Every recovery execution claims an atomic lease in `ops_recovery_executions` with TTL, preventing race conditions or duplicate concurrent executions.
7. **Downstream Verified Recovery:** A recovery is not declared successful until a dedicated verification function (`fn_verify`) inspects downstream state and confirms the problem is genuinely resolved.
8. **Failure Isolation, Cooldown & Ceilings:** Max 2 attempts ceiling per incident, 300s cooldown between attempts, and a global daily budget limit (20 recoveries/day).
9. **Strict AI Isolation:** The Gemini AI Analyst (Phase 4) is advisory-only with zero mutation authority and cannot execute self-healing routines.
10. **Zero-Trace Observability:** Verified recoveries automatically surface in the Operations Console Level 3 "Handled Automatically" feed, providing clear transparency to the owner.

---

### 2. Approved Recovery Routines Registry

| Routine ID | Title | Scope | Feature Flag | Max Attempts | Cooldown | Invariant & Mutation Boundaries |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `routine:background_job_lease_recovery` | Engine-Tick Lease Recovery | Loop health & background job stalls | `OPS_RECOVERY_LEASE_ENABLED` | 2 | 300s | CAS clear of expired `engine_tick_lease` in `system_state`. Never steals active lease (`expires_at > now`). |
| `routine:stale_claim_lock_recovery` | Stale Claim Lock Recovery | Abandoned OTP claims | `OPS_RECOVERY_CLAIM_LOCK_ENABLED` | 2 | 300s | Marks expired OTP claim as `expired` and clears transient `claim_in_progress` lock. Never transfers listing ownership or edits statutory records. |
| `routine:transient_notification_retry` | Transient Notification Delivery Retry | Transient delivery failures (429, 503, timeout) | `OPS_RECOVERY_NOTIFICATION_ENABLED` | 2 | 300s | Bounded re-dispatch for transient backpressure. Permanent errors (401, 400, 404, 422) strictly rejected. Sandbox-only. |

---

### 3. API & Console Integration

- `GET /api/oversight/recovery/status`: Read-only configuration summary returning environment status, feature flags, registered routines, and limits.
- `POST /api/oversight/recovery/evaluate`: Dry-run evaluation endpoint checking if a specific incident is eligible for an approved recovery routine.
- `POST /api/oversight/cases/{case_id:path}/recover`: Authenticated endpoint executing recovery under atomic claiming, verification, and audit logging.
- `GET /api/oversight`: Handled Automatically summary includes verified recoveries at the top (`category: "auto_recovery"`, `status: "completed"`).
- `/ops` Console UI: Case cards display recovery badges (`Auto-Recovered`, `Recovering...`, `Recovery Exhausted`) and detailed execution history in the side drawer.

---

### 4. Developer Sandbox Live Deployment & Acceptance Verification (VERIFIED COMPLETE)

Deployed to developer sandbox `dogtrainersdirectory-dev` and verified live end-to-end via automated acceptance suite (`scripts/verify_sandbox_ops_phase5.py` and `scripts/verify_sandbox_ops_phase5_live_ui.mjs`):
- **Sandbox Backend Service:** `dtd-api-dev` serving Cloud Run revision `dtd-api-dev-00047-kfd` at 100% traffic (`https://dtd-api-dev-625222421634.australia-southeast1.run.app`).
- **Sandbox Frontend Service:** `dtd-web-dev` serving Cloud Run revision `dtd-web-dev-00018-98h` at 100% traffic (`https://dtd-web-dev-625222421634.australia-southeast1.run.app`).
- **Production Isolation:** Production backend `dtd-api` remains strictly locked to revision `dtd-api-00058-ter` in project `gen-lang-client-0028123502`. Zero production mutations, zero live charges, zero external communications.

**Acceptance Gate Matrix (Live Sandbox):**
- **Gate A — Safe Default-Disabled Posture:** `PASS`. `self_healing_globally_enabled: False` by default; recovery evaluation while disabled returns `eligible: False`.
- **Gate B — Routine Eligibility Boundaries:** `PASS`. Permanent errors (HTTP 401 invalid credentials) are strictly rejected (`eligible: False`), and direct recovery requests return HTTP 422.
- **Gate C — Dry-Run & Idempotency:** `PASS`. Dry-run recovery returned `status: "dry_run"` with zero mutations to MongoDB.
- **Gate D — Distributed Concurrency Control:** `PASS`. Active worker lease in `ops_recovery_executions` correctly blocked concurrent execution with HTTP 409 (`"Another worker is currently executing recovery for this incident."`).
- **Gate E & F — Real Sandbox Recovery Execution & Verified Resolution:** `PASS`. Recovery execution returned `status: "verified_recovery"`. Downstream verification confirmed:
  - Claim marked `status: "expired"` with `recovered_by` execution ID.
  - Trainer transient `claim_in_progress` lock released; `owner_user_id` remained `None`; statutory verification untouched.
  - `ops_recovery_executions` record marked `status: "verified"` with immutable timestamp and evidence.
  - `ops_case_states` marked `state: "resolved"` with `auto_resolved: True`.
- **Gate G — Failure Handling, Cooldown & Max Attempts:** `PASS`. Cooldown active correctly returned HTTP 409 (`"Recovery in cooldown. Please wait 298s before retrying."`); max attempts ceiling (2/2) correctly returned HTTP 400 (`"Max recovery attempts reached (2/2). Owner escalation required."`).
- **Gate H — AI Separation (Zero Mutation Authority):** `PASS`. Verified that Gemini AI Analyst has zero mutation tools attached and is strictly read-only advisory.
- **Gate I — Operations Console UX & Handled Automatically Feed:** `PASS`. Verified recovery rendered in Level 3 Handled Automatically feed (`Self-Healed: Stale Claim Lock Recovery`, `status: "completed"`).
- **Gate J — Production Isolation:** `PASS`. Production revision `dtd-api-00058-ter` confirmed untouched.
- **Gate K — Zero-Trace Cleanup & Reset Posture:** `PASS`. All synthetic test records were removed from MongoDB Atlas; Cloud Run environment variables restored to default-disabled (`OPS_SELF_HEALING_ENABLED=0`); live status confirmed `self_healing_globally_enabled: False`.

---

## Consolidated Production-Readiness Assessment & Release Decision

- **Overall Assessment:** `CONDITIONALLY READY FOR OWNER APPROVAL`
- **Assessment Date:** 17 October 2026
- **Verified Baseline Commit SHA:** `2604eee0490bf51943f835ca9654f7d10f526636`
- **Governing Principle:** **OWNER BY EXCEPTION. AUTOMATION BY DEFAULT. AI ANALYSIS WHEN NEEDED.**

### 1. Release Scope & Payload (Phases 1–5A Consolidated)

The candidate release payload brings the completed Operations Console transformation from the developer sandbox into DTD's production architecture:
1. **Phase 1 — Noise Elimination & Incident Triage:** Decoupled machine `operational_state` from human operator review, bounded incident deduplication, high-severity dismissal protection requiring explanatory review notes, and audit log persistence in `ops_case_states`.
2. **Phase 2 — Incident Correlation, Lifecycle & Background Orchestration:** Grouping of multi-attempt retries into single correlated cases (`message:{dispatch_id}`), terminal success auto-resolution, occurrence fingerprinting (`_case_occurrence_fingerprint`) preventing false recurrence on refresh, and `/api/internal/jobs/engine-tick` serverless execution boundary with distributed MongoDB leases (`system_state.engine_tick_lease`). Supports scoped execution profiles (`profile=readonly`, `profile=maintenance`, `profile=all`) and enforces safe outbound email gating (`ENABLE_REACTIVATION_NOTIFICATIONS=0` by default).
3. **Phase 3 — Minimal Owner-Facing Operations Console:** 10-second scan hierarchy, single plain-English status headline, and 1-click triage actions (`Acknowledge`, `Resolve`, `Dismiss`).
4. **Phase 4 — Read-Only Gemini AI Operations Analyst:** Advisory-only intelligence investigating genuine operational exceptions, bounded input payload (4,000 chars), nominal configured count limit (50/day; not a strict cost ceiling because of DF-052), 24h fingerprint deduplication, and strictly zero mutation tools or state authority.
5. **Phase 5 — Controlled Self-Healing Framework:** Bounded, deterministic automatic recovery routines (`lease_recovery`, `claim_lock_recovery`, `notification_retry`) with code-level production hard-block (`is_production_environment() == True`), ensuring self-healing remains **unconditionally disabled** in production.
6. **Phase 5A — Owner UX Consolidation & Operational Acceptance:** 10-second owner scannability: Level 1 System Status, Level 2 Needs Your Attention (priority-first sorting, compact severity filter pills, bounded 5-item pagination, progressive disclosure), Level 3 Handled Automatically (collapsed by default aggregate summary bar), and Secondary Advanced Diagnostics (collapsed by default, preserving all 10 diagnostic views).

### 2. Production vs. Sandbox Parity Analysis

| Dimension | Developer Sandbox (`dogtrainersdirectory-dev`) | Production (`gen-lang-client-0028123502`) | Parity Status & Release Notes |
| :--- | :--- | :--- | :--- |
| **Backend Service** | `dtd-api-dev` (Cloud Run, `australia-southeast1`) | `dtd-api` (Cloud Run, `australia-southeast1`) | **Full Parity.** Identical Python 3.14 / FastAPI runtime, 1 CPU, 1Gi memory, 300s timeout. |
| **Backend Revision** | `dtd-api-dev-00047-kfd` (100% traffic) | `dtd-api-00058-ter` (100% traffic) | **Ready for Promotion.** Candidate release deploys new revision with zero-traffic canary. |
| **Frontend Hosting** | Cloud Run (`dtd-web-dev`, Nginx container) | Firebase Hosting (`gen-lang-client-0028123502.web.app` / `dogtrainersdirectory.com.au`) | **Architecturally Reconciled.** Frontend `api.js` is polymorphic: routes to sandbox URL on `dtd-web-dev...run.app` and to same-origin `/api` rewrites on Firebase Hosting. |
| **Frontend Revision** | `dtd-web-dev-00019-ks5` (100% traffic) | Release `1792053117314000` (Version `f92934ec71003666`) | **Ready for Deployment.** Vite production build compiles clean in 813ms into `frontend/build`. |
| **Database** | MongoDB Atlas (`dtd_sandbox`) | MongoDB Atlas (`dtd`) | **Compatible.** Startup indexing in `server.py` defensively provisions indexes for `ops_case_states`, `system_state`, `ops_ai_investigations`, and `ops_recovery_executions` without manual migrations. |
| **Commercial Gate** | `ENABLE_TRAINER_BILLING_CHECKOUT=0` | `ENABLE_TRAINER_BILLING_CHECKOUT=0` | **Identical & Locked.** Zero live charging or refund exposure. |
| **Self-Healing Posture** | Default-disabled (`OPS_SELF_HEALING_ENABLED=0`) | Code-level hard-blocked (`is_production_environment() == True`) | **Zero Risk.** Self-healing cannot execute in production under any configuration. |
| **Gemini AI IAM** | `roles/aiplatform.user` on `dtd-api-dev-runtime` | Missing `roles/aiplatform.user` on `dtd-runtime` | **Prerequisite.** If live Vertex AI calls are desired in production, grant `roles/aiplatform.user` to `dtd-runtime`; otherwise fallback operates offline. |
| **Cloud Scheduler** | `dtd-engine-tick-cron` (`*/10 * * * *`) | `dtd-pro-trial-warnings` (`0 9 * * *`) | **Optional.** Engine-tick cron can be added post-release to automate background loops; absence is non-blocking. |

### 3. Production Rollback Procedures

#### A. Cloud Run Backend Rollback
- **Target Revision:** `dtd-api-00058-ter` (current healthy production revision serving 100% traffic).
- **Execution Command:**
  ```bash
  gcloud run services update-traffic dtd-api \
    --project gen-lang-client-0028123502 \
    --region australia-southeast1 \
    --to-revisions dtd-api-00058-ter=100
  ```
- **Verification:** `curl -s https://dogtrainersdirectory.com.au/api/health` returns `{"ok": true, "database": "available"}`.

#### B. Firebase Hosting Frontend Rollback
- **Target Version:** `f92934ec71003666` (Release ID: `1792053117314000`, released 2026-10-15T08:31:57Z).
- **Execution Procedures (3 Verified Routes):**
  1. **Firebase Console 1-Click Rollback (Fastest & Officially Recommended):**
     - Open Firebase Console -> Hosting (`gen-lang-client-0028123502`).
     - Navigate to **Release history**.
     - Locate Version `f92934ec71003666` (Release ID: `1792053117314000`).
     - Click the overflow menu (`⋮`) and select **Roll back**.
     - Instantaneous zero-downtime traffic shift to previous assets.
  2. **Firebase Hosting REST API Rollback (Automated / Headless):**
     ```bash
     curl -s -X POST \
       "https://firebasehosting.googleapis.com/v1beta1/sites/gen-lang-client-0028123502/releases?versionName=sites/gen-lang-client-0028123502/versions/f92934ec71003666" \
       -H "Authorization: Bearer $(gcloud auth print-access-token)" \
       -H "Content-Type: application/json"
     ```
  3. **Deterministic Git Source Re-Deploy (Offline / CLI Fallback):**
     ```bash
     # Restore previous audited frontend commit
     git checkout 5733d4d -- frontend/src frontend/package.json
     npm --prefix frontend run build
     firebase deploy --only hosting --project gen-lang-client-0028123502
     ```
- **Verification:** Inspect `https://dogtrainersdirectory.com.au/` in browser; verify HTTP 200 and previous asset bundle hash (`index-B0KVx6z6.js` and `index-CiXd5jGR.css`).

### 4. Operational Gaps and Prerequisites Matrix

1. **Gemini Vertex AI IAM Binding (Prerequisite for Live AI Inference):**
   - *Status:* Missing on production project `gen-lang-client-0028123502`.
   - *Operational Impact:* In production, if Gemini Vertex calls fail due to missing IAM, `services/ai.py` gracefully catches the exception and falls back to deterministic rule-based analysis without interrupting operations or user requests.
   - *Remediation (Optional Owner Decision):* Grant `roles/aiplatform.user` to `dtd-runtime@gen-lang-client-0028123502.iam.gserviceaccount.com`.
2. **Cloud Scheduler Engine-Tick (Optional Background Automation):**
   - *Status:* Provisioned in sandbox; not yet created in production.
   - *Operational Impact:* Background loops run when visitor traffic arrives or when manually triggered; DF-029 advisory remains visible in `/ops` Work Queue until scheduled cron is active.
   - *Remediation (Optional Owner Decision):* Create `dtd-engine-tick-cron` with OIDC auth via `dtd-scheduler-invoker@gen-lang-client-0028123502.iam.gserviceaccount.com`.
3. **Public Trainer Onboarding End-to-End Verification (DF-041):**
   - *Status:* Sandbox verified with synthetic test fixtures; public production `/submit` flow remains unexercised live.
   - *Remediation:* Handled in separate product workstream; not an Operations Console blocker.
