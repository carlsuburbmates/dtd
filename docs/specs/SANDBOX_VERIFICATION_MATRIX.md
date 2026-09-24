# Sandbox Verification Matrix

**Purpose:** Defines the mandatory pre-flight checklist and domain-specific verification gates required in the staging sandbox (`dogtrainersdirectory-dev` + `dtd-sandbox`) before promoting any code, configuration, or data migration to production (`gen-lang-client-0028123502` + live `DTD`).

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
| **Scheduler / Jobs** | Triggered on-demand via `/ops` or manual curl | Automated Google Cloud Scheduler |
| **Idle Cost** | Scale-to-zero ($0 idle cost baseline) | Highly-available minimum instances |

---

## 2. Domain-Specific Verification Checklists

Any modification touching the following 6 core functional areas must satisfy its verification gate in the sandbox before requesting production promotion:

### Domain 1: Autonomous Acquisition & Data Ingestion
*Targets: `scripts/enrich_profiles_gemini.py`, web scraping loops, ABR lookup services, trainer deduplication.*

- [ ] **Database Isolation:** All writes target `dtd_sandbox.trainers` or staging collections; zero connection attempts to live `DTD`.
- [ ] **Provenance & Evidence:** Every ingested profile contains source URL, retrieval timestamp, extraction confidence, and raw snapshot evidence per [`docs/specs/ACQUISITION_AND_INGESTION.md`](ACQUISITION_AND_INGESTION.md).
- [ ] **Suppression & Claim Rights:** Suppression list checks execute prior to record insertion; blacklisted or opted-out trainers are dropped.
- [ ] **Rate Limits & Fail-Safe:** Scraper loops handle HTTP 429 / CAPTCHAs gracefully and back off without crashing the worker or loop process.

### Domain 2: Stripe Billing & Monetisation Lifecycle
*Targets: Checkout sessions, webhook consumers, 30-day Pro trials, subscription renewals, cancellation, refunds.*

- [ ] **Key Isolation:** Confirmed via runtime inspection that `STRIPE_SECRET_KEY` starts with `sk_test_`.
- [ ] **Webhook Idempotency:** Duplicate delivery of identical webhook event IDs (simulated via Stripe CLI or test payload) returns HTTP 200 without creating duplicate subscriptions or audit logs.
- [ ] **Trial Anchor Preserved:** Pro trial creation honours the explicit cohort anchor logic; day-23 warning calculation passes without regression.
- [ ] **Subscription State Machine:** Test card checkouts correctly transition trainer state: `active` → `past_due` → `canceled` as expected.
- [ ] **Refund Safeguards:** Refund execution fails closed on invalid intervals or non-eligible transactions.

### Domain 3: Transactional Communications & Notifications
*Targets: Resend integration, claim token dispatch, owner enquiry routing, trial expiry notices.*

- [ ] **Recipient Containment:** Email dispatch routes strictly to designated test mailboxes (e.g. `admin@dogtrainersdirectory.com.au` or sandbox test sinks). Zero emails sent to real Melbourne trainers.
- [ ] **Token Expiration & Single-Use:** Trainer action tokens (claim, edit, unsubscribe) validate against sandbox secret `dtd-trainer-action-token-secret`, expire within TTL, and invalidate upon first use.
- [ ] **Delivery Fallback:** Simulated Resend API failure or network timeout triggers the documented fallback record in the database and surfaces in `/ops`.

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

- [ ] **Authentication Enforcement:** Requests lacking valid `ADMIN_PASS` or authorization bearer token return HTTP 401/403.
- [ ] **Idempotent Actions:** Operator buttons and actions accept idempotent request tokens to prevent double-execution on button double-clicks.
- [ ] **Audit Trail:** Every mutating `/ops` action writes an audit entry containing action name, operator identifier, timestamp, and payload diff.
- [ ] **Sanitized Reporting:** Diagnostic and health outputs disclose system state (`database: available`, queue counts) without exposing credentials, connection strings, or customer PII.

---

## 3. Pre-Production Promotion Protocol (4-Step Gate)

Before any code on a development or feature branch is merged into `main` and deployed to production, the operator or AI assistant must complete this sequence:

```text
 1. Automated Suite       2. Sandbox Verification      3. Git PR Review        4. Canary Deploy
┌────────────────────┐    ┌──────────────────────┐    ┌───────────────────┐    ┌──────────────────┐
│ py_compile         │    │ bash                 │    │ Pull Request      │    │ Zero-traffic     │
│ check_prelaunch... │───►│ scripts/             │───►│ from dev to main  │───►│ canary smoke     │
│ 315 isolated tests │    │ deploy_sandbox.sh    │    │ (Operator Gate)   │    │ 100% promotion   │
└────────────────────┘    └──────────────────────┘    └───────────────────┘    └──────────────────┘
```

1. **Step 1: Automated Local Suite**
   - Run `python3 -m py_compile backend/server.py backend/worker.py backend/services/*.py`
   - Run `node scripts/check_prelaunch_release_gate.js`
   - Run `.venv/bin/python backend/scripts/run_isolated_integration_suite.py` (315 passing tests).
2. **Step 2: Live Sandbox Execution**
   - Execute `bash scripts/deploy_sandbox.sh`.
   - Verify `https://dtd-api-dev-x2kdoaemtq-ts.a.run.app/api/health` returns HTTP 200 with `database: "available"`.
   - Test the relevant domain checklist above on the live sandbox service.
3. **Step 3: Operator PR Review & Approval**
   - Commit changes cleanly and push to GitHub.
   - Open Pull Request to `main`.
   - Per DTD locked safety policy (*"no production deploy unless approved"*), production requires operator confirmation.
4. **Step 4: Controlled Production Canary Release**
   - Deploy zero-traffic revision to `gen-lang-client-0028123502`.
   - Smoke-test the tagged revision (`/api/health`, `/api/config`).
   - Shift 100% traffic with zero downtime.
