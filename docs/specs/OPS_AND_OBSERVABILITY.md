# Operations and Observability

## Operator model

**OWNER BY EXCEPTION. AUTOMATION BY DEFAULT. AI ANALYSIS WHEN NEEDED.**

DTD has one non-technical operator. `/ops` is the single action and evidence surface. It prioritises exceptions, explains impact and provides the smallest safe next action. AI analysis remains advisory.

This specification defines required behaviour, not a live implementation certificate. Use [the execution register](../DTD_ROADMAP_EXECUTION_REGISTER.md) for accepted stage status and [current state](../DTD_CURRENT_STATE.md) for dated runtime evidence, open findings and the current recovery boundary. Accepted Ops phases remain accepted at their recorded scope; deployment, provider configuration and end-to-end behaviour require separate evidence. Required domain coverage below does not mean every loop is enabled or every workflow has passed acceptance.

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

### Case review semantics, occurrence fingerprinting and invariants

1. **Read-Only Oversight Contract (DF-032):**
   `GET /api/oversight` is strictly side-effect free. It reads system state, loop health, message logs, and existing review cases without creating, updating, or deleting any database records (e.g. `_read_launch_phase_state()` and `_read_phase_transition_decisions()` replace all former snapshot upsert logic).
2. **Domain Entity Immutability:**
   Operator triage actions (Resolve, Acknowledge, Dismiss via `POST /api/oversight/cases/{case_id}`) persist state strictly in `ops_case_states` and `audit_log`. They never mutate underlying business tables (`submissions`, `trainers`, `subscriptions`, `message_log`).
3. **Occurrence Fingerprinting & Recurrence Prevention:**
   Recurrence detection is evaluated strictly against authoritative occurrence fingerprints (`_case_occurrence_fingerprint`), NOT fragile read timestamps or query re-runs. Snapshot rewrites or re-reads with identical fingerprints remain dismissed or resolved. Where occurrence identity is absent or unmodeled, recurrence tracking is explicitly marked `recurrence_tracking: "deferred_to_phase2"` to guarantee review integrity without false alerts.

## Automation contract

Each loop exposes owner, cadence/trigger, input cohort, last run, last success, failure count, next action and retry/fallback. A deployed function without scheduling evidence is not an active automation. Repeated failures become an operator case rather than disappearing into logs.

### Background loop freshness and scheduling contract

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

### Database and external provider health verification

1. **MongoDB Atlas Health:**
   Operational status is never inferred from client object instantiation. It requires active operation telemetry within the past 300 seconds (`_record_db_op_success()`). If unobserved, it reports `unknown`; on recent database errors, it reports `unavailable`.
2. **Resend Email Delivery:**
   Status is derived from actual outbound dispatches recorded in `message_log`. Routine successful dispatches (HTTP 202) remain in message history for auditability, but never generate Ops cases. Delivery failures, bounces, or 4xx/5xx responses generate actionable incident cases.
3. **Sentry Error Tracking:**
   Defaults to `unknown` with known gap `"production canary event unverified"` until verified event delivery to the Sentry ingestion endpoint is confirmed.
4. **Deep Health & Scheduler Observability (`/api/health/deep`):**
   Provides deep dependency diagnostics including database connectivity, system state collection access, Cloud Run environment profile, maintenance mode posture, and background scheduler freshness. The freshness threshold is strictly unified with `/ops` loop monitoring at 750 seconds (600s engine-tick cadence + 150s bounded grace). If `engine_tick` age > 750s, it flags `"delayed_or_stale"`; if `last_status != "ok"` (e.g. `partial_error`), it flags `"failing_or_degraded"`.
5. **Independent Alerting (Monitoring the Monitor):**
   API downtime must have an external alert route that does not depend on the failed API or its email provider. The repository contains `scripts/setup_edge_monitoring.sh` and `scripts/test_edge_monitoring_delivery.py`; their existence does not prove deployed configuration or delivery. Record the actual check/policy scope, threshold, notification destination, mailbox verification and received-alert evidence separately. DF-001 retains the configured Google Cloud Monitoring 5xx policy and unverified mailbox delivery. Do not claim an uptime probe, full database/provider coverage, or a five-minute end-to-end alert guarantee without that evidence.
   - Internal watchdogs and the durable ledger must cover scheduler stalls, held submissions, claim locks, failed delivery and provider auth/quota errors according to their explicit SLA policies. Missing telemetry remains unverified rather than healthy.
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
   - `profile="monitoring"` (or `"readonly"`): **Strictly ZERO customer/trainer/derived entity mutations.** No profile edits, ranking score updates, conversion promotions, sponsor inventory changes, nurture sequences, reactivation routing, external emails, or self-healing routines. Unlike the strictly read-only `GET /api/oversight`, this execution profile permits internal operational-state writes only: `system_state` (telemetry/leases), `ops_obligations` (durable ledger sync), and `ops_ai_investigations` (advisory analysis).
   - `profile="routine"`: Core operational pipeline executing ranking recalculation, conversion promotions, sponsor inventory maintenance, health checks, obligations sync, and AI analysis. It does not run trainer nurture, reactivation-email or recovery loops. Derived/Ops writes and possible provider calls mean it must not be invoked as an unscoped acceptance test; configuration evidence is separate from fixture-scoped execution acceptance.
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

### AI degradation telemetry and temporal contracts

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

The system maintains strict isolation between production and developer sandbox environments:

- **Production Environment:**
  - Google Cloud Project: `gen-lang-client-0028123502`
  - Database: MongoDB Atlas cluster `DTD` (`dtd` database)
  - Purpose: Live dog owners, registered trainers and the separately gated commercial runtime on production domain (`dogtrainersdirectory.com.au`).
  - Access & Mutations: Zero-downtime rolling/canary deployments; strict production change control; gated commercial/refund activations.

- **Staging / Sandbox Environment:**
  - Google Cloud Project: `dogtrainersdirectory-dev`
  - Database: MongoDB Atlas cluster `dtd-sandbox` (`dtd_sandbox` database, AWS Sydney `ap-southeast-2`)
  - Purpose: Developer experimentation, AI-assisted development, feature testing, and automated build verification.
  - Guardrails: any authorised Stripe testing uses Test Mode; transactional emails target dummy/test sinks; directory data is non-production; serverless scale-to-zero where configured (not proof of zero provider cost).
  - Promotion Gate: Features, data migrations, or infrastructure changes must pass verification in the sandbox before promotion to production.
  - Deployment Automation: Executable via `bash scripts/deploy_sandbox.sh`. It runs mandatory preflight compilation and release-gate checks, deploys `dtd-api-dev` with Secret Manager bindings, sets `DB_NAME=dtd_sandbox`, and fails unless `/api/health` confirms database availability. That response alone does not prove the selected database identity; verify deployed configuration and fixture scope separately. It may be run only by an authenticated, authorised operator or assistant; it is not an authority for arbitrary agents or for production promotion.

## Incident correlation, lifecycle and compatibility

1. **Incident Correlation & Noise Elimination:**
   - Multi-attempt message delivery retries collapse into a single correlated incident keyed by `message:{dispatch_id}`.
   - Distinct IDs are preserved across event, dispatch, attempt, and incident layers.
   - Correlated provider outage incidents group concurrent failures with root cause tokens (e.g. `provider_outage:resend:5xx`).
   - Conservative fallback for legacy message events without explicit dispatch IDs correlates identical message types and targets within 1-hour windows.
2. **Incident Lifecycle & State Decoupling:**
   - Machine `operational_state` (`detected`, `recovering`, `resolved`, `reopened`) is strictly separated from human operator `review.state` (`detected`, `investigating`, `resolved`, `dismissed`).
   - High-severity incident dismissal requires an explanatory review note of at least 5 characters (`HTTP 400` safeguard).
   - Dismissal and investigation notes persist auditably in `ops_case_states` and `audit_log`.
3. **Verified Terminal Resolution & Alias Resolution:**
   - Terminal success events automatically resolve and clear transient delivery failure incidents.
   - Case reviews submitted against constituent event IDs (aliases) resolve seamlessly to primary correlated incident IDs.
   - Idempotent review updates with identical state, owner, and note execute safely without creating duplicate audit records.
4. **Occurrence Identity & Genuine Recurrence:**
   - Authoritative occurrence fingerprints (`_case_occurrence_fingerprint`) across all case types prevent false recurrence on browser refresh or snapshot re-reads.
   - When a new failure occurs with distinct error telemetry or higher failure counts, previously dismissed cases reopen automatically to `operational_state: "reopened"` with an explicit `(Recurred)` badge.
5. **Frontend Compatibility:**
   - `/ops` Work Queue correctly maps `reopened` into `Needs review` and `recovering` into `In progress`.
   - Message log rows display `Recovering` badges when dispatches are actively recovering.

## Required domain coverage

These are required operating responsibilities, not a claim that all automation is implemented, scheduled or accepted. Each domain needs truthful exception evidence and the existing action/authority contract. Disabled or unverified paths must remain explicit.

| Domain | Required operational coverage and owner exception |
|---|---|
| Submissions | Lawful ingestion provenance, duplicate/risk outcomes, statutory verification and publication holds; approval only through the authorised workflow. |
| Claims | Challenge dispatch/expiry, ownership conflicts and claim-lock state; stale-lock recovery only under its disabled-by-default recovery gate. |
| Matching | Paid-neutral fit, deterministic gates/fallback, search expansion and urgent-support state; persistent AI or supply failures surface as exceptions. |
| Directory corrections | Receipt, provenance, correction/removal review and bounded authorised publication changes. Places content must not become persistent DTD facts. |
| Notifications | Dispatch attempts, provider receipts, retries/fallback and terminal failures; re-dispatch requires the applicable recipient/sink and recovery authority. |
| Trainer supply | Eligible/intro-ready inventory and geographic coverage gaps; no unsupported assertion of trainer availability. |
| Capability | Evidence/freshness/suppression of trainer capability fields; bounded on-demand refresh where authorised. |
| Demand and waitlists | Consented intake, location grouping and unfulfilled demand; retention and follow-up remain governed by matching/privacy contracts. |
| Commercial and billing | Webhooks, trials, capacity, refund and reactivation exceptions; checkout/refunds remain disabled until their separate gates pass. |
| SEO and indexation | Canonical locality and supply/content eligibility under the SEO specification; no automatic indexation from catalogue existence. |
| Audit and security | Immutable action evidence, administrative authentication/expiry and protected high-severity review. |
| Providers and background loops | Identity, scheduler/profile, cadence, leases, failures and genuinely observed last success; missing owner/telemetry is not healthy. |
| AI Operations Analyst | Sanitised read-only investigations, attempt/cooldown limits, uncertainty and fallback; corrected runtime/provider acceptance remains DF-052. |
| Recovery | Approved deterministic routine, gate, lease, attempts, verification and exhausted-case escalation; self-healing stays disabled by default and production hard-blocked. |

## Owner-facing console and operating cadence

The console must support an approximately 10-second scan, with advanced detail available only when needed. Refresh authenticated state before an operational decision (`data-testid="ops-refresh"`); stale browser memory is not evidence. Healthy routine work requires no manual traversal of every diagnostic view. Missing telemetry must prevent a healthy headline, even when the case queue is empty.

1. **Level 1 — System Status (10-Second Readability):**
   - **Headline & Status Derivation:** Computes plain-English operational states based on authoritative telemetry:
     - `All running normally` (emerald): 0 active high/medium cases, 0 failing loops, database connected, engine tick fresh.
     - `Some services need attention` (amber): non-critical degraded loop, medium-severity case, or thin supply warning.
     - `Action required` (rose): 1 or more high-severity cases in `Needs review` or critical database/connectivity failure.
     - `Status unavailable` (slate): disconnected database or unparseable telemetry snapshot.
     - `monitoring_unverified`: required telemetry is missing, stale or unobserved; never present this state as all running normally.
   - **Decision Summary:** Clear, concise prompt on whether action is needed or normal monitoring should continue.
   - **Three Supporting Metrics:**
     - *Directory Supply:* Intro-ready trainers vs blocked/pending verification.
     - *Commercial Gate:* Strict verification of fail-closed posture (`ENABLE_TRAINER_BILLING_CHECKOUT=0`); a disabled flag is not proof of every financial safeguard.
     - *Background Systems:* Count of healthy autonomous loops (e.g. 10/10) with serverless engine-tick status.

2. **Level 2 — Needs Your Attention (Actionable Exceptions Only):**
   - **Strict Exception Filtering:** Provide priority-first sorting, compact severity filters and bounded pagination for 20–30 cases. Displays only genuine owner-actionable cases (`detected`, `notified`, `reopened`). Dismissed, investigating, or recovered cases are excluded from the primary view.
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
     - Cloud Scheduler engine ticks and their actually executed profile tasks; routine execution excludes nurture, reactivation-email and recovery loops.
     - Guardian supervisory compliance audits.
     - Fraud and duplicate submission suppressions.
     - Transactional delivery recoveries and retries.
     - Auto-resolved transient incidents.
   - Includes timestamp, task name, and count; truthful neutral empty state if zero automated tasks ran in the last 24h. Display only persisted evidence of completed work, never all configured domains as automatically handled. Keep this level collapsed by default with an expandable aggregate summary.

4. **Secondary — Collapsible Advanced Diagnostics Disclosure:**
   - Hidden by default behind a clean disclosure toggle (`data-testid="ops-diagnostics-toggle"`).
   - Preserves 100% of underlying diagnostic capabilities, views (`pipeline_flow`, `matching`, `trainer_supply`, `messages`, `billing_reactivation`, `seo_indexation`, `attribution`, `system_activity`, `recent_changes`, `work_queue`), and automated test IDs.
   - Expandable on demand for deep inspection without polluting the primary executive console.

5. **Mobile-First Ergonomics & Accessibility:**
   - Touch targets designed for fingers ($\ge 44\text{px}$ button height/padding).
   - Responsive grid (`sm:grid-cols-3` adapting cleanly down to single-column on mobile).
   - Require zero horizontal overflow at 390px (mobile), 768px (tablet), and 1440px (desktop); a historical capture is not current visual verification.

## Read-only AI Operations Analyst

The read-only diagnostic assistant helps the operator understand operational exceptions. Model configuration belongs to the implementation; a configured model name is not evidence of provider availability.

### 1. Architecture & Core Boundaries
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
  - **Daily Attempt Limit:** `OPS_AI_DAILY_BUDGET` configures a bounded daily attempt allowance (documented default 50). The contract requires an atomic shared reservation before inference, concurrency bounds and failure-closed behaviour when storage cannot reserve capacity. Failed or interrupted attempts retain their slots. This bounds attempts, not monetary spend. DF-052 records the accepted local atomic-ledger correction and still-unverified corrected runtime/provider-recovery acceptance; do not describe the historical count-then-call implementation as the current source or claim its replacement is deployed.
  - **Manual Request Cooldown:** `OPS_AI_MANUAL_COOLDOWN_SECONDS=60` enforces a 60-second debounce per case, returning HTTP 429 to prevent rapid-click budget exhaustion.
  - **Evidence, Token & Batch Bounding:** Bound and sanitise evidence before inference; the configured evidence payload limit is 4,000 characters. Output tokens are bounded (`max_output_tokens=1024`), and batch size is capped (`max_batch=3` per loop iteration). Limits must be checked at their actual input boundary; a configured constant alone is not proof of enforcement.
- **Graceful Failure Isolation & Deterministic Fallback:**
  - Network timeouts (15s ceiling), quota exhaustion, or Vertex AI provider errors degrade gracefully to `deterministic_analyst_fallback` based on known system architecture, and must not interrupt unrelated directory operations.

### 2. Structured JSON Output Schema
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

### 3. API & Console Integration
- `POST /api/oversight/cases/{case_id:path}/investigate`: Authenticated endpoint (`require_oversight`) for owner-requested investigation.
- `GET /api/oversight`: Includes `ops_ai_analyst` status object in root payload (`enabled`, `model`, `daily_budget`, `total_investigations`), and attaches `ai_investigation_status`, `ai_investigation_id`, and `ai_analysis` to case items.
- `/ops` Console UI (`AiAnalysisCard`):
  - Displays classification badge (`Confirmed Cause`, `Likely Cause`, `Unknown Cause`).
  - Summarizes hypothesis and operational impact in plain language.
  - Lists supporting evidence bullets.
  - Highlights recommended operator next steps.
  - Provides a 1-click "Request Updated Analysis" button with cooldown and loading state.

## Controlled automation and self-healing recovery

### Safety and authorisation boundaries

The recovery framework permits strictly bounded, idempotent automatic recovery ("self-healing") for operational failures that can be corrected deterministically, safely, and with verifiable outcomes.

**Current posture:** self-healing remains disabled; registry inclusion grants no execution authority.

**Safety Invariants & Governance Principles:**
1. **Owner by Exception, Automation by Default:** The owner should not spend time manually intervening in trivial, mechanical faults (e.g. expired background job locks or transient HTTP 429 backpressure).
2. **Safe Defaults (Default-Disabled Posture):** All self-healing routines are disabled by default (`OPS_SELF_HEALING_ENABLED=0`).
3. **Production Hard-Block:** In production (`is_production_environment() == True`), all automatic recovery routines are unconditionally hard-blocked. Production activation requires explicit, separate future owner authorization.
4. **Separate Routine Gating:** Each recovery routine is governed by its own independent feature flag (`OPS_RECOVERY_LEASE_ENABLED`, `OPS_RECOVERY_CLAIM_LOCK_ENABLED`, `OPS_RECOVERY_NOTIFICATION_ENABLED`).
5. **No Business Mutations:** Self-healing never alters listing ownership, ABN verification status, public directory visibility, or customer billing.
6. **Atomic Distributed Claiming:** Every recovery execution claims an atomic lease in `ops_recovery_executions` with TTL, preventing race conditions or duplicate concurrent executions.
7. **Downstream Verified Recovery:** A recovery is not declared successful until a dedicated verification function (`fn_verify`) inspects downstream state and confirms the problem is genuinely resolved.
8. **Failure Isolation, Cooldown & Ceilings:** Max 2 attempts ceiling per incident, 300s cooldown between attempts, and a global daily budget limit (20 recoveries/day).
9. **Strict AI Isolation:** The AI Operations Analyst is advisory-only with zero mutation authority and cannot execute self-healing routines.
10. **Recovery Observability:** Verified recoveries automatically surface in the Operations Console Level 3 "Handled Automatically" feed, providing clear transparency to the owner.

---

### Approved recovery routines registry

| Routine ID | Title | Scope | Feature Flag | Max Attempts | Cooldown | Invariant & Mutation Boundaries |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `routine:background_job_lease_recovery` | Engine-Tick Lease Recovery | Loop health & background job stalls | `OPS_RECOVERY_LEASE_ENABLED` | 2 | 300s | CAS clear of expired `engine_tick_lease` in `system_state`. Never steals active lease (`expires_at > now`). |
| `routine:stale_claim_lock_recovery` | Stale Claim Lock Recovery | Abandoned OTP claims | `OPS_RECOVERY_CLAIM_LOCK_ENABLED` | 2 | 300s | Marks expired OTP claim as `expired` and clears transient `claim_in_progress` lock. Never transfers listing ownership or edits statutory records. |
| `routine:transient_notification_retry` | Transient Notification Delivery Retry | Transient delivery failures (429, 503, timeout) | `OPS_RECOVERY_NOTIFICATION_ENABLED` | 2 | 300s | Bounded re-dispatch for transient backpressure. Permanent errors (401, 400, 404, 422) strictly rejected. Sandbox-only. |

---

### Recovery API and console integration

- `GET /api/oversight/recovery/status`: Read-only configuration summary returning environment status, feature flags, registered routines, and limits.
- `POST /api/oversight/recovery/evaluate`: Dry-run evaluation endpoint checking if a specific incident is eligible for an approved recovery routine.
- `POST /api/oversight/cases/{case_id:path}/recover`: Authenticated endpoint executing recovery under atomic claiming, verification, and audit logging.
- `GET /api/oversight`: Handled Automatically summary includes verified recoveries at the top (`category: "auto_recovery"`, `status: "completed"`).
- `/ops` Console UI: Case cards display recovery badges (`Auto-Recovered`, `Recovering...`, `Recovery Exhausted`) and detailed execution history in the side drawer.

---

### Safe deployment recovery boundary

Before recovery, independently resolve the exact environment, source/image, revision configuration, secret versions, flags, Scheduler state, expected effects and health/workflow verification. Production changes remain separately gated. Developer recovery must preserve the 25 October replacement numeric secrets and checkout/refunds/self-healing `0`; create or validate a safe successor rather than routing an old revision with exposed bindings. Never re-enable ingestion or invoke a broad scheduled job as an incidental recovery check. The dated R3 traffic-return rehearsal remains accepted historical evidence at its original scope, not a reusable present-day rollback target.

A replacement invalidates old sandbox admin credentials, signed trainer sessions/links and fallback-key OTPs where applicable. Renew these through supported workflows; never restore exposed credentials to preserve access. Supported management access and unchanged integration bindings are distinct from complete provider workflow acceptance.

## Provider dependency registry (sanitised)

**Dated evidence:** R3 observations from 22 October, credential containment from 25 October, access-continuity checks from 26 October, and bounded backend/management verification from 28 October where stated. Each record retains its stated date and verification scope; refresh the affected provider state before operational action. Current state records subsequent observations and unresolved DF-001/DF-050/DF-052 findings. An unspecified expiry remains unknown; review before each affected release or incident, and at the assigned acceptance stage. Every provider must retain separate runtime and management scopes, last successful verification, next review/expiry, degraded behaviour, independent alert evidence and recovery owner.

| Provider / purpose | Runtime vs. management identity; latest verification | Degraded behavior | Independent alert, recovery owner and next review |
|---|---|---|---|
| Cloud Run / Cloud Build — API hosting and release | Runtime uses the dedicated developer service account; management uses a separately authorised Google control-plane identity, whose device-independent recovery is not established by the runtime probe. Source `9dd53ed` was R3 verified on 22 Oct. On 28 Oct, accepted backend `171a1d7` was independently source/archive/image verified, deployed through a no-traffic candidate and observed at 100%; the R8 checkpoint records exact revision/digest and remaining integrated limits. Existing-account official CLI/browser renewal, management reads and governed deployment succeeded; this is not device-independent recovery proof. | Readiness/health gates fail the deployment script; recovery requires a verified successor preserving replacement credentials and disabled flags; older exposed bindings must not receive traffic. | The dated inventory records one enabled API alert policy with an attached email channel; this is configuration evidence only. Mailbox verification and alert delivery remain unverified; no induced outage was used because it would notify the owner. Recovery owner is the project operator. Recheck before each release. Production is not a recovery target. |
| Secret Manager — developer admin and trainer signing | Runtime identity `dtd-api-dev-runtime` reads pinned admin version 4 and action-signing version 2. Authorised management account successfully created, read-verified and disabled predecessor versions on 25 Oct; values remained in memory. Independent metadata review verifies the separate runtime identity and version state, not inherited least-privilege permissions or device-independent recovery. | Old admin access and signed sessions/links fail after replacement; pending OTPs using the shared fallback key need renewal. Health and protected auth checks passed. | Recovery owner is the project operator through the supported Google management login. Review before the next sandbox release or on a credential incident; no automatic expiry was established. Independent alert delivery and management-recovery resilience remain existing DF-001/R7 limitations, not certified autonomous operation. |
| MongoDB Atlas — developer persistence | Runtime uses preserved secret reference `dtd-mongo-url`; `dtd_sandbox` health and one disposable API match/persistence/Ops/owned-cleanup path passed 28 Oct. Separate Atlas management identity/recovery path remains unverified. | API reports database unavailable; affected operations must fail through their existing error paths. | GCP API 5xx alert is configured, but mailbox delivery is not verified; no Atlas-specific independent alert is proven. Verify acquisition-relevant Atlas management/recovery controls at R4; confirm integrated data recovery separately at R8. Owner/operator is recovery owner; DF-001 tracks identity/perimeter gaps. |
| Vertex AI / Gemini — Ops analysis and matching assistance | Runtime uses developer Cloud Run identity/region. 22 Oct logs show Ops analyst `429 RESOURCE_EXHAUSTED`; matching degradation is not present in health. | Ops analyst returns deterministic fallback. | No independent quota alert or exact reset/limit is verified. Owner/operator is recovery owner; review before R7/R12 AI acceptance under DF-052. No quota setting was changed. |
| Resend — transactional email and webhook | Runtime uses developer Secret Manager references. Last documented safe test-recipient delivery: 15 Oct. Prior audit found no provider webhook endpoint. Provider-management identity is unverified. | Notification/fallback state records failure; provider-originated webhook retry remains unverified. | GCP API 5xx alert exists but mailbox delivery is unverified; no separate Resend alert is proven. Owner/operator is recovery owner; review at R7 email acceptance. DF-001/DF-050 remain open. No real recipient was contacted. |
| Stripe — test/live billing integration | Sandbox has Secret Manager references; checkout flag was verified disabled 22 Oct. Provider management identity was not exercised. | Checkout is disabled. | No independent billing alert or recovery path was tested in R3. Owner/operator is recovery owner; review at the separately authorised production/commercial gates. No live payment/refund occurred. |
| ABR — statutory trainer identity verification | Runtime reference `dtd-abr-guid`; no ABR request or successful response was verified in R3. | Existing failure paths should retain pending/held state; current provider behavior was not re-tested. | Independent alert and current management/recovery path are not verified. Owner/operator follows ABR's official recovery process; recheck before R4 statutory-verification acceptance. |
| Sentry — error reporting | Runtime reference `dtd-sentry-dsn`; no test event was emitted or verified in R3. | Core API remains available; DSN presence alone does not prove event delivery. | Independent alert delivery, mailbox verification and recovery path remain open under DF-001 and are assigned to R7 operational acceptance. |
| Firebase Hosting — production website | 22 Oct authenticated REST reads confirmed the then-live 15 October release on site `gen-lang-client-0028123502`; no dev Hosting site exists. | Production rewrite targets `dtd-api`; sandbox uses Cloud Run under CDR-027. | Production operator is recovery owner; Hosting release/recovery work remains R9 after owner sandbox audit. No Firebase deployment occurred. |
| Vercel — retired GitHub deployment integration | Project `dtd` Git connection to `carlsuburbmates/dtd` was removed in authenticated settings on 22 Oct; the settings page confirms no Git repository is connected. Project remains non-live, has no custom domain, and protects its default domains with SSO. | Historical preview for `906d3bed` predates disconnection; later PR #17 head `509d051` has no deployment record. Historical project deployments are retained in Vercel. | PR #17 integration is complete; no Vercel action remains for R3. Do not use Vercel as public-host or sandbox evidence; see DF-007. |

Provider status statements above distinguish a successful runtime probe from provider-management recovery. They do not establish production readiness. These records do not authorise credential changes, provider mutation, live billing or production promotion.
