# Sandbox Verification Matrix

**Purpose:** Defines the mandatory pre-flight checklist and domain-specific verification gates required in the staging sandbox (`dogtrainersdirectory-dev` + `dtd-sandbox`) before promoting any code, configuration, or data migration to production (`gen-lang-client-0028123502` + live `DTD`).

**Use:** Apply the affected workflow gates to the exact accepted source/configuration delta. Checked historical evidence retains its stated date and SHA; an unchecked gate is a required scenario, not a claim of an observed defect. Preserve accepted checkpoints and reuse unchanged evidence. The [R8 acceptance record](../R8_END_TO_END_SANDBOX_ACCEPTANCE.md#named-srcf-follow-ups-retained-for-r8) carries named SR/CF outcomes and remaining runtime proof.

**Authority:** Governed by [`docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`](../DTD_INVARIANTS_AND_CONSTRAINTS.md), [`docs/specs/OPS_AND_OBSERVABILITY.md`](OPS_AND_OBSERVABILITY.md), and Decision Record **`CDR-017`**.

---

## 1. Sandbox Environment Contracts

Every verification step executes within the isolated developer staging sandbox:

| Resource | Sandbox Specification | Production Equivalent (Must Never Touch) |
| :--- | :--- | :--- |
| **GCP Project** | `dogtrainersdirectory-dev` (625222421634) | `gen-lang-client-0028123502` |
| **Cloud Run API** | `dtd-api-dev` (`australia-southeast1`) | `dtd-api` (`australia-southeast1`) |
| **MongoDB Atlas** | Cluster `dtd-sandbox` (`dtd_sandbox` db) | Cluster `DTD` (`dtd` live db) |
| **Stripe Engine** | Test Mode (`sk_test_...`) | Live Mode (`sk_live_...`) |
| **Email Sinks** | Test sinks / admin addresses only | Live trainer / dog owner addresses |
| **Scheduler / Jobs** | Dedicated sandbox OIDC identity; verify current job state and use only bounded owned fixtures | Production jobs require separate authority |
| **Capacity / Cost** | Inspect current scaling and billable dependencies; scale-to-zero does not prove zero total cost | Verify production configuration separately |

---

## 2. Domain-Specific Verification Checklists

Any modification touching the following 7 core functional areas must satisfy its verification gate in the sandbox before requesting production promotion:

### Domain 1: Autonomous Acquisition & Data Ingestion
*Targets: `scripts/enrich_profiles_gemini.py`, web scraping loops, ABR lookup services, trainer deduplication.*

- [ ] **Database Isolation:** All writes target `dtd_sandbox.trainers` or staging collections; zero connection attempts to live `DTD`.
- [ ] **Provenance & Evidence:** Every ingested profile contains source URL, retrieval timestamp, extraction confidence, and raw snapshot evidence per [`docs/specs/ACQUISITION_AND_INGESTION.md`](ACQUISITION_AND_INGESTION.md).
- [ ] **Suppression & Claim Rights:** Suppression list checks execute prior to record insertion; blacklisted or opted-out trainers are dropped.
- [ ] **Rate Limits & Fail-Safe:** Scraper loops handle HTTP 429 / CAPTCHAs gracefully and back off without crashing the worker or loop process.

### Domain 2: Stripe Billing & Monetisation Lifecycle
*Targets: Checkout sessions, webhook consumers, 30-day Pro trials, subscription renewals, cancellation, refunds.*

- [ ] **Key Isolation:** Confirmed via runtime inspection that `STRIPE_SECRET_KEY` starts with `sk_test_`.
- [ ] **Webhook Idempotency:** Duplicate delivery of identical webhook event IDs (simulated via Stripe CLI or test payload) returns HTTP 200 without creating duplicate subscriptions or audit logs. Label synthetic versus provider-originated evidence explicitly.
- [ ] **Trial Anchor Preserved:** Pro trial creation honours the explicit cohort anchor logic; day-23 warning calculation passes without regression.
- [ ] **Terms, Checkout and Entitlement:** Where separately authorised, versioned terms acceptance persists before test Checkout; verify the actual Stripe subscription state through webhook persistence to entitlements and inventory. An eligible Pro trial begins on provider subscription creation, not profile claim; test mode does not establish live-cohort eligibility.
- [ ] **Subscription State Machine:** Verify provider-authoritative active/trial, payment-failure and terminal states, plus self-service portal cancellation → downgrade/inventory release under the [pricing contract](MONETISATION_AND_PRICING.md). A refund is a separate workflow, not cancellation.
- [ ] **Refund Safeguards:** Refund execution fails closed on invalid intervals or non-eligible transactions. Separately authorised test refunds require authenticated confirmation, idempotency, persisted provider result, inventory release and audit evidence; a success banner alone is insufficient.

### Domain 3: Transactional Communications & Notifications
*Targets: Resend integration, claim token dispatch, owner enquiry routing, trial expiry notices.*

- [ ] **Recipient Containment:** Email dispatch routes strictly to designated test mailboxes (e.g. `admin@dogtrainersdirectory.com.au` or sandbox test sinks). Zero emails sent to real Melbourne trainers.
- [ ] **Claim and Action-Token Safety:** Verify current-owner/latest-challenge binding, expiry, single-use consumption, replay/concurrency and stale ownership denial against the managed sandbox secret. OTPs and signing values must not appear in API responses, Ops, logs or documentation; use only the approved test-sink challenge delivery. Verify session renewal, expired-auth recovery, draft/tier preservation and stale trainer-route response rejection. Claimed/profile capability changes must persist and invalidate/rebuild matching projections as specified. *(28 October 2026: bounded API claim initiation, email mismatch 403, SMS fail-closed 503, bad OTP 400, replay rejection 409, fresh prefill, sequential renewal, and specific/melbourne-wide catchment confirmation observed in run 4462bde68906; delivered OTP receipt, browser expired-auth recovery, and atomic/current-owner lifecycle remain unverified).*
- [ ] **Delivery Fallback:** Safely scoped Resend API failure or timeout produces the documented database fallback and truthful `/ops` state. Distinguish accepted local mocks from live failure injection.
- [ ] **Provider Receipt and Retry (SR-01):** Verify provider-originated delivery separately from synthetic signed API events. A persisted receipt followed by notification-write failure must reconcile on retry; stale terminal events cannot overwrite newer state, ambiguous legacy receipts fail closed, and invalid signatures create no receipt. See named remaining proof in [R8](../R8_END_TO_END_SANDBOX_ACCEPTANCE.md#named-srcf-follow-ups-retained-for-r8).

### Domain 4: Database Migrations & Data Backfills
*Targets: Index modifications, collection schema transforms, canonical suburb scripts (`seed_suburbs.py`, `build_suburb_list.py`).*

- [ ] **Pre-Migration Snapshot:** Sandbox collection is exported or verified disposable before mutation.
- [ ] **Non-Destructive Execution:** The script runs to completion without dropping unrelated collections or unmapped fields.
- [ ] **Idempotent Re-Run:** Running the migration script a second time produces zero duplicate records and zero unintended state changes.
- [ ] **Index Verification:** Query execution plans (`explain()`) confirm new queries utilize appropriate compound indexes without full collection scans.

### Domain 5: Dynamic SEO & Catchment Landing Pages
*Targets: Suburb SEO page generator, `/api/seo/`, sitemap builder, canonical slug resolvers.*

- [ ] **Eligibility Thresholds:** Suburbs with fewer than 3 verified trainers (`SEO_MIN_PUBLISHED_TRAINERS=3`) or under 500 content words (`SEO_MIN_CONTENT_WORDS=500`) return `noindex,follow` and status `not_eligible`.
- [ ] **Canonical Slugs:** Unregistered, legacy, or non-Melbourne suburb slugs return HTTP 404 with standard error contract (`Unknown canonical suburb`).
- [ ] **Sitemap Exclusion:** Ineligible and non-canonical pages are excluded from the generated sitemap XML.

### Domain 6: Operator Action Layer & `/ops` Control Plane
*Targets: Admin endpoints, batch sync routines, manual warning triggers, health diagnostics.*

- [x] **Authentication Enforcement:** Requests lacking valid `ADMIN_PASS` or authorization bearer token return HTTP 401/403. Verified on 28 October 2026 for `/api/oversight` and `/api/oversight/support/threads` (anonymous 401, authenticated 200). Broader admin endpoints remain unexercised by this runner.
- [ ] **Idempotent Actions:** Operator buttons and actions accept idempotent request tokens to prevent double-execution on button double-clicks.
- [ ] **Audit Trail:** Every mutating `/ops` action writes an audit entry containing action name, operator identifier, timestamp, and payload diff.
- [ ] **Sanitized Reporting:** Diagnostic and health outputs disclose system state (`database: available`, queue counts) without exposing credentials, connection strings, OTPs or customer PII.
- [ ] **Truthful Operator Surface:** Supply, commercial gates, job state and provider health reflect measured evidence; missing monitoring proof is unverified, not healthy. High-severity dismissal requires confirmation; advanced diagnostics remain subordinate to actionable exceptions.
- [ ] **Support, Privacy and Obligations (SR-02–06 / CF-01–05):** Use the [R8 named matrix](../R8_END_TO_END_SANDBOX_ACCEPTANCE.md#named-srcf-follow-ups-retained-for-r8) for consented publication/races, conflicting verified owners, trusted privacy proof, support selection/concurrency/fallback/closure and bounded obligation completeness/waiting/read-only/terminal resolution. Require UI/API/data/audit evidence as applicable; never run global engine-tick as a fixture test. *(28 October 2026: bounded API support complaint intake, protected list/detail, reply guard 400, operator reply dispatch, duplicate reply prevention, short-note close rejection, ordinary complaint closure, and browser contact submit + Ops list view observed in run 4462bde68906; selected thread detail interaction, category-specific delisting/privacy workflows, truthful browser duplicate/failure feedback, notifier failure fallback, trusted privacy scrub, and durable obligations live sync remain unverified).*
- [ ] **Read-Only AI Analyst:** Sanitised evidence and structured advisory output cannot mutate business state. Verify durable cross-process daily attempt claims, failure-slot retention, storage fail-closed behaviour and truthful provider failure; an attempt ceiling does not prove a monetary spending cap.

### Domain 7: Owner-to-Trainer Matching & Urgent Support
*Targets: owner questionnaire and result states, match-ready capability projection, Gemini/fallback decision service, protected enquiry, urgent-support provider directory and optional session-only Maps/Places surface.*

- [ ] **Decision-State Contract:** Validate required inputs, derived age/life-stage boundaries, method/service-format choices, consent capture, clarification, weak-evidence/degraded responses and approved urgent-route states on mobile and desktop against [Decision Contract v2](OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md). Behavioural descriptions never appear in URLs, logs exposed to operators or trainer-facing profile data. Do not invent response latency or provider-coverage guarantees.
- [ ] **Public Journey and Accessibility:** Verify navigation, canonical suburb/method/specialty directory filters, profile links, questionnaire loading/error recovery, visible fonts/assets, keyboard/mobile and applicable assistive-technology behaviour; console/network errors must be explained or corrected. Verify crawlable static HTML when the JavaScript bundle is unavailable, plus sitemap/robots/canonical responses by meaning rather than an obsolete byte count or route total.
- [ ] **Protected Enquiry:** Result/profile handoff uses an opaque context and separate referral/contact consent. Verify truthful submission feedback, owned test-sink/provider persistence, notification failure/retry, and sanitised Ops evidence; a confirmation banner alone does not prove delivery.
- [ ] **Eligibility and Capability Evidence:** Published/suppressed/contact/freshness/geography/service-format/capability gates fail closed. Trainer onboarding, acquisition refresh, correction and suppression correctly create or invalidate the match-ready projection.
- [x] **AI/Fallback Parity:** `scripts/run_sandbox_matching_parity.sh` passed against the live developer sandbox on 7 October 2026. Its single immutable fixture produced the same candidate and capability reason through normal Gemini, a deliberately invalid-model deterministic fallback, and restored Gemini; protected Ops exposed the degradation during the run, `gemini-3.5-flash` was restored, and all fixtures/evidence were removed. Local fixtures additionally cover timeout, rate-limit and invalid JSON.
- [ ] **Fair Presentation:** Paid tier cannot change eligibility or raw fit. Tests cover the exact `0.05` boundary, stable non-commercial ties, fewer than three suitable candidates and disclosed expansion only when fewer than three trainers pass the local eligibility gates.
- [ ] **Urgent Support Boundaries:** Approved urgent routes use versioned copy and official-source provider facts with freshness/correction handling. If the optional Maps/Places surface is enabled, test attribution, user initiation, session-only data handling, no AI/ranking input, no DTD-provider persistence and a truthful provider-outage route.
- [ ] **Ops and Follow-up Evidence:** `/ops` exposes sanitised decision, degradation, provider freshness, capability invalidation and follow-up retry/terminal states without private owner data.
- [ ] **Retention and Cleanup:** Matching context and event expiry fields are BSON dates, each collection has its TTL index, a forced-expiry context rejects access, and every UUID-namespaced acceptance fixture is removed from persistence and public routes after the run.

---

## 3. Review-before-environment promotion protocol

Follow locked `AGENTS.md` §6A for the exact source/configuration package:

1. **Local implementation:** The delegated coding agent inspects and implements in isolation, records base/HEAD, affected workflows and proportionate local checks. Before independent acceptance it must not push, open/merge a promotion PR, deploy, mutate providers or enable gated features.
2. **Independent code acceptance:** An independent reviewer inspects the cumulative diff, persistence, privacy, fallback, Ops and relevant scenario evidence. Return only a proven failing requirement for correction. Passing tests alone are not acceptance; accepted R0–R3 checkpoints remain closed unless new evidence warrants reopening them.
3. **Governed remote and developer advancement:** After exact-SHA code acceptance, Codex performs the authorised push/PR/merge/CI and developer deployment steps needed for that package. Verify resulting source/image/bundle, managed credentials and safe flags, current environment, health, affected live workflows, fixture teardown and a safe recovery path. A health response proves neither the business flow nor an unchanged runtime identity. Use current tooling and service discovery rather than copied historical revision URLs or traffic commands.
4. **Record runtime disposition:** Mark each relevant scenario DONE, PARTIAL, OPEN, REGRESSED, NOT_VERIFIED or SUPERSEDED with its date/environment/SHA and accepted inherited evidence. An unavailable safe provider/failure-injection check leaves that claim unverified; it does not revoke independently accepted code or require a global rerun. Keep ingestion paused and gated features disabled unless their own activation requirements and authority are satisfied.
5. **Separate production authority:** R9/M10 requires owner audit and applicable production authority before any production deployment or traffic promotion. Verify the accepted exact source, no-traffic/canary behaviour, safe credential bindings and recovery before a traffic switch. Live billing/refunds, credential/authentication changes, licensed sources and destructive real-data actions retain their separate gates.

### Four recovery domains retained from the former full-project plan

The former Phase 5 requirement for **four recovery drills** is carried into these existing scenario domains. This mapping preserves the coverage requirement; it neither claims all four complete nor requires four fresh runs when dated accepted evidence still applies.

| Recovery domain | Existing evidence and remaining scope |
| --- | --- |
| Deployment / traffic recovery | R1/R3 rehearsed conditional recovery retains its historical acceptance. Reassess only changed source/configuration and current safe recovery bindings; never restore a revision with disabled/exposed credential versions. Use the current Ops recovery contract and exact-image proof, not historical traffic commands. |
| Scheduled-job disable / recovery | Accepted R1/R2 evidence establishes inspected PAUSED ingestion, bounded temporary-job execution and removal, and separate routine-job configuration. This does not prove safe ingestion reactivation; DF-044/045 runtime/source gates and current recovery controls remain prerequisites. Do not resume jobs merely to produce a new drill timestamp. |
| Notification retry / fallback | R1 synthetic webhook replay and local receipt-write retry evidence remain accepted at their scope. SR-01 provider-originated and live failure/retry evidence, plus SR-04/CF-04 notifier fallback, remain as named in R8. |
| Provider / AI degradation and restoration | Domain 7 records accepted 7 October Gemini → deterministic fallback → restored Gemini parity and teardown. Preserve that evidence; corrected R8 provider/AI-budget/runtime changes still need only their affected checks. Provider outage, Monitoring receipt and recovery-control gaps remain explicitly unverified until independently observed. |

### Fixture and evidence contract

Use only owned disposable sandbox identities and test recipients. Record expected/actual UI, API, persisted state, notification/provider/fallback and Ops evidence for the affected scenario. Remove by exact returned IDs; verify absence from every touched application collection and public route. Preserve unknown artifacts if a response is lost; do not delete unrelated activity. Distinguish retained provider-side test-sink metadata from application cleanup. Never use real trainer profiles, production records, global engine ticks or fabricated identity proof to complete this checklist.
