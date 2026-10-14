# Operations and Observability

## Operator model

DTD has one non-technical operator. `/ops` is the single action and evidence surface. It should prioritise exceptions, explain impact and provide the smallest safe next action.

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

## Automation contract

Each loop exposes owner, cadence/trigger, input cohort, last run, last success, failure count, next action and retry/fallback. A deployed function without scheduling evidence is not an active automation. Repeated failures become an operator case rather than disappearing into logs.

## Financial safety

- Stripe mutations fail closed when live mode, permission or feature gate is absent.
- Refund execution remains disabled until live-payment, operator-confirmation, idempotency, inventory-release and audit paths pass production acceptance.
- Trial day-23 warnings run once per eligible provider-backed trial and persist outcome evidence.

## Observability

- API health includes dependency status without exposing secrets.
- Sentry must initialise in the process actually serving production requests before being called active.
- First-party attribution remains privacy-bounded and is not operational authority; Stripe and DTD persistence remain the sources of truth for monetisation reporting.
- Add charts only where they reduce operator effort; a second operator system is not allowed.

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

