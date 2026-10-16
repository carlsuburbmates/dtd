# Operations and Observability

## Operator model

DTD has one non-technical operator. `/ops` is the single action and evidence surface. It should prioritise exceptions, explain impact and provide the smallest safe next action.

## Operations Console Transformation Roadmap

The approved Operations Console transformation sequence operates under the governing principle:
**OWNER BY EXCEPTION. AUTOMATION BY DEFAULT. AI ANALYSIS WHEN NEEDED.**

The agreed multi-phase roadmap is:
- **Phase 1 — Noise Elimination & Classification (Implemented & Verified in Developer Sandbox):**
  Eliminates operational noise at its source. Distinguishes routine informational telemetry (e.g. successful HTTP 202 transactional emails, benign initial crawl 404s, expected cold starts) from actionable operational incidents. Enforces cadence-aware bounded grace curves for background loops, evidence-first provider operational status, occurrence fingerprinting for recurrence suppression, and temporal validation for AI degradation events.
- **Phase 2 — Incident Correlation, Lifecycle Integrity, & Verified Recovery (Implemented & Verified in Developer Sandbox):**
  Transforms fragmented operational events into correlated incidents. Groups retry dispatches, isolates root-cause provider outages, and distinguishes machine `operational_state` (`detected`, `recovering`, `resolved`, `reopened`) from human `review.state`. Implements verified automated recovery (terminal successes clear transient failures, alias resolution for event IDs), robust occurrence identity with genuine recurrence detection, and serverless loop orchestration via Cloud Scheduler `dtd-engine-tick-cron` solving DF-029.
- **Phase 3 — Minimal Owner-Facing Operations Console (Implemented & Verified):**
  Transforms `/ops` into a decision-first, mobile-responsive Operations Console for a single non-technical owner. Features a 3-Level hierarchy: Level 1 System Status (plain English headline + 3 supporting metrics: Supply, Commercial Gate, Background loops), Level 2 Needs Your Attention (filtering only genuine actionable cases with 3-question breakdowns: What happened?, Why does it matter?, What can I do?, and 1-click triage actions with high-severity dismissal safeguards), Level 3 Handled Automatically (compact telemetry feed of background engine ticks, Guardian audits, fraud suppressions, and delivery recoveries), and a collapsible Secondary Advanced Diagnostics disclosure preserving 10 deep technical views and all existing test IDs. Mobile touch ergonomics and responsive layouts verified at 390px, 768px, and 1440px.
- **Phase 4 — Read-Only, Event-Triggered AI Operations Analyst (Planned next):**
  Integrates a bounded, read-only AI diagnostic advisor triggered solely by operational exceptions. Synthesizes error logs, telemetry diffs, and historical remediations to present concise root-cause hypotheses and recommended operator actions in `/ops`. Performs zero autonomous database mutations.
- **Phase 5 — Separately Approved Controlled Automation & Self-Healing Recovery (Planned):**
  Introduces strictly gated, idempotent automated recovery routines for well-understood transient faults (e.g., automated cache flushing, bounded task retries, stale claim expirations), requiring prior operator review and explicit feature-flag gating.

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

1. **Exception-Driven Review:** Never poll or guess. Only intervene when `/ops` surfaces an exception, degrade flag, or held case.
2. **Fresh Authenticated State:** Always click `[Refresh]` (`data-testid="ops-refresh"`) before making an operational decision. Never act on stale browser memory.
3. **Bounded 1-Click Mutations:** Use the rapid triage buttons (`Resolve`, `Acknowledge`, `Dismiss`) or specific control triggers. Every mutation records an immutable audit log with reviewer ID, timestamp, and before/after diffs.
4. **Fail-Closed Safety:** Commercial checkouts remain disabled (`ENABLE_TRAINER_BILLING_CHECKOUT=0`) and matching degrades to deterministic fallback upon any provider fault. Never override safety gates without explicit verification.

### Daily Operator Responsibilities Checklist

#### Phase 1: Morning Posture & Circuit Safety (P0 - Immediate)
- **Check Readiness & Posture:**
  - View `Overview` (`ops-nav-overview`): inspect the 4 top cards (`Needs review`, `Intro-ready`, `Blocked supply`, `Health watch`) and the `Operational Posture & Safety Gates` summary.
  - Confirm `Commercial Gate`: verify `ENABLE_TRAINER_BILLING_CHECKOUT=0` is reported as inactive and fail-closed until live charging authorization.
- **Verify Matching Health & Fallbacks:**
  - View `Matching Engine` (`ops-nav-matching`): check AI degradation telemetry.
  - If AI degradation or timeout events are detected, inspect the reason codes (e.g. `rate_limit`, `timeout`, `json_malformed`).
  - If degraded state is confirmed stable under deterministic fallback, trigger `[Acknowledge degradation]` (`ops-ack-degradation`) to register operator acknowledgement.

#### Phase 2: Work Queue & Triage Processing (P1 - Priority Daily)
- **Open Work Queue:**
  - Navigate to `Work Queue` (`ops-nav-work_queue`) or click `[Review Top Cases]` on the Operator Daily Action Hub (`ops-action-hub`).
  - Focus on the `Needs review` queue bucket (states `detected` and `notified`).
- **Trainer Submissions & Claims Triage:**
  - Select each submission or claim case in the queue.
  - Review statutory verification items (ABN, business registry match, location match).
  - Use **1-Click Rapid Triage** in the Case Detail panel:
    - `[Resolve]` (`ops-case-quick-resolve`): Marks case `resolved` with a standard statutory verification note (`Verified statutory facts and resolved in daily ops review.`).
    - `[Acknowledge]` (`ops-case-quick-acknowledge`): Marks case `acknowledged` (`Acknowledged in daily ops triage; monitoring.`) if waiting on third-party verification.
    - `[Dismiss]` (`ops-case-quick-dismiss`): Marks case `dismissed` if duplicate or non-actionable test fixture.
- **Urgent-Support Directory Review:**
  - In `Matching Engine` view, inspect pending provider correction/removal submissions.
  - Click `[Approve & publish correction]` or `[Reject correction]` after verifying Google Places / public directory facts.

#### Phase 3: Outbound Communications & Delivery Verification (P2 - Midday)
- **Review Message Logs:**
  - Navigate to `Messages` (`ops-nav-messages`).
  - Filter for delivery errors (`failed`, `error`, HTTP 4xx/5xx).
- **Retry Failed Customer Touchpoints:**
  - For failed outcome follow-ups, click `[Retry follow-up]` (`ops-retry-follow-up-{id}`).
  - Document provider communication failures without rotating live API keys unless containment is required.

#### Phase 4: Supply, Capability Freshness & Demand Gaps (P3 - Afternoon)
- **Supply Balance & Demand Gaps:**
  - Navigate to `Trainer Supply` (`ops-nav-trainer_supply`) and `Pipeline Flow` (`ops-nav-pipeline_flow`).
  - Review `Intro-ready` vs `Blocked supply` counts.
  - Identify top suburb demand gaps where dog owner waitlist count exceeds verified trainer coverage.
- **Trainer Capability Refresh:**
  - If a trainer has updated behavioural declarations, insurance, or council registrations, click `[Re-check capability]` (`ops-recheck-capability-{id}`) to refresh matchable capacity immediately without waiting for scheduled nightly pipelines.

#### Phase 5: Financial Health, Audits & Close (P4 - End of Day)
- **Lifecycle & Billing Verification:**
  - Navigate to `Billing & Reactivation` (`ops-nav-billing_reactivation`).
  - Verify zero unhandled webhook errors, trial grace-period anomalies, or stale reactivation cases.
- **Audit Verification:**
  - Navigate to `Recent Changes` (`ops-nav-recent_changes`).
  - Confirm every mutation performed during the day has a corresponding immutable audit event (`actor`, `action`, `entity_id`, `ts`).
- **Background Loop Health:**
  - Navigate to `System Activity` (`ops-nav-system_activity`).
  - Confirm all active automation loops (`pipeline_guardian`, `matching_retention`, `waitlist_dispatch`) show healthy recent execution (`status: ok`) and non-stale timestamps.

### Weekly Responsibilities
- **Catalogue & SEO Drift:** Review `SEO & Indexation` (`ops-nav-seo_indexation`) against minimum eligible trainer count thresholds (>=3 intro-ready trainers per suburb) before publishing suburb landing pages.
- **Provider Registry & Costs:** Check `System Activity` provider registry records (MongoDB Atlas, Firebase Hosting, Cloud Run, Resend, Sentry) for upcoming certificate/key review dates and runtime health.

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

### Phase 2 Architecture & Implemented Workstreams (Verified Complete)

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
4. **Workstream D — Serverless Background Scheduling & DF-029 Resolution:**
   - Authenticated Cloud Scheduler cron `dtd-engine-tick-cron` (`*/10 * * * *`, Australia/Melbourne) triggers `/api/internal/jobs/engine-tick` under dedicated service account OIDC authentication (`dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`).
   - Distributed MongoDB lease `engine_tick_lease` in `system_state` (180s TTL) with atomic `find_one_and_update` prevents concurrent execution races.
   - Executes 6 core loops (`ranking`, `inference`, `health`, `sponsor_inventory`, `nurture`, `reactivation_route`).
   - Writes `execution_owner: "cloud_scheduler"`, `last_run`, duration, and overall status to `system_state.engine_tick` telemetry doc.
5. **Workstream E — Occurrence Identity & Genuine Recurrence:**
   - Authoritative occurrence fingerprints (`_case_occurrence_fingerprint`) across all case types prevent false recurrence on browser refresh or snapshot re-reads.
   - When a new failure occurs with distinct error telemetry or higher failure counts, previously dismissed cases reopen automatically to `operational_state: "reopened"` with an explicit `(Recurred)` badge.
6. **Workstream F — Frontend Compatibility:**
   - `/ops` Work Queue correctly maps `reopened` into `Needs review` and `recovering` into `In progress`.
   - Message log rows display `Recovering` badges when dispatches are actively recovering.

### Phase 2 Sandbox Acceptance Gate (VERIFIED COMPLETE)

Executed automated isolated acceptance suite (`scripts/verify_sandbox_ops_phase2.py`) against live sandbox deployment `dtd-api-dev-00034-kkv`:
- **Gate 1 — Deployed Revision & Environment Isolation:** **PASS** (Active revision `dtd-api-dev-00034-kkv` verified; database available; production environment independently verified untouched and healthy).
- **Gate 2 — Workstream A: Incident Correlation:** **PASS** (3 retry attempts correctly grouped into exactly 1 incident; terminal success cleared prior transient failures).
- **Gate 3 — Workstream B & E: Lifecycle & Recurrence:** **PASS** (Dismissal safeguard verified rejecting note < 5 chars; valid dismissal verified; identical refresh produced no false recurrence; genuine failure reopened case with `(Recurred)` badge).
- **Gate 4 — Workstream C: Alias Resolution & Idempotency:** **PASS** (Alias lookup by constituent event ID resolved to primary case; repeat identical update created 0 duplicate audit records).
- **Gate 5 — Workstream D: Serverless Scheduling & Engine Tick (DF-029):** **PASS** (`dtd-engine-tick-cron` invoked successfully; telemetry recorded in `system_state.engine_tick` with `execution_owner: cloud_scheduler` and `status: ok` in ~2.3s; autonomous loops executed; distributed lease released).
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
     - `[Resolve]`: transitions state to `resolved`, persisting note `"Verified statutory facts and resolved in daily ops review."`
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
- **Backend Pytest Suite:** 494/494 unit and ops tests passed across `test_ops_phase1_noise_elimination.py`, `test_ops_phase2_incident_lifecycle.py`, and all domain unit suites.
- **Visual Responsiveness Verification:** Automated headless Chrome CDP capture (`scripts/verify_ops_phase3_visuals.mjs`) verified:
  - `ops_phase3_mobile_390.png`: 390x844 mobile viewport, touch targets compliant, zero overflow.
  - `ops_phase3_tablet_768.png`: 768x1024 tablet viewport, clean 3-card metrics layout.
  - `ops_phase3_desktop_1440.png`: 1440x900 desktop viewport, decision-first reading order.
  - `ops_phase3_diagnostics_expanded.png`: 1440x900 expanded diagnostics, sidebar navigation and views accessible.

## Phase 4 Dependencies and Implementation Readiness

Phase 1, Phase 2, and Phase 3 are complete and verified. Phase 4 implementation (Read-Only, Event-Triggered AI Operations Analyst) remains blocked pending explicit owner authorization. The key technical objectives for Phase 4 are:

1. **Event-Triggered Invocation:**
   AI Analyst triggers only when an unhandled operational exception or degradation is detected; zero polling, zero continuous background consumption.
2. **Read-Only Invariant:**
   Analyst operates under strictly read-only tools and cannot write to or mutate database collections.
3. **Structured Hypotheses & Remediation Recommendations:**
   Synthesizes telemetry, recent diffs, and error logs into a concise hypothesis and recommended operator actions presented within `/ops`.
4. **Owner Review Gate:**
   Every proposed action requires manual owner review and confirmation before execution.

