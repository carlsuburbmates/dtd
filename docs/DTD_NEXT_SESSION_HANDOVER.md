# DTD Next-Session Handover: Roadmap Completion & Commercial Integration

**Prepared:** 24 October 2026.
**Purpose:** Handover from the Google for Startups / Commercial Strategy session to the companion Antigravity session responsible for DTD roadmap execution (R0–R13).
**Repository:** `carlsuburbmates/dtd`
**Active Worktree / Branch:** `/Users/carlg/Documents/AI-Coding/dtd` on `feature/r4-trainer-supply`
**Authoritative Context:** Aligned with [`AGENTS.md`](../AGENTS.md), [`docs/DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md`](DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md), [`docs/DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md`](DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md), and [`docs/GOOGLE_FOR_STARTUPS_PROGRAM_BASELINE.md`](GOOGLE_FOR_STARTUPS_PROGRAM_BASELINE.md).

---

## 1. Executive Summary & Starting Checkpoint

This session completed a critical external and commercial enablement package while preserving all repository safety boundaries:
1. **Google for Startups Cloud Program Start-Tier Application:**
   - Researched official program rules, verified Australian Sole Trader ABN criteria, confirmed 24-month founding window, and validated zero prior credits.
   - Audited the Google Cloud billing account IAM: confirmed `user:admin@dogtrainersdirectory.com.au` has `roles/billing.admin` on billing account `0104B3-AB5AF0-8F0A01`, satisfying Google's domain-matching requirement (`@dogtrainersdirectory.com.au`).
   - Prepared, peer-audited with Codex, and user dispatched the audited reply to `cloudstartupsupport@google.com` from `info@dogtrainersdirectory.com.au`.
   - **Status:** **NOT VERIFIED / PENDING WRITTEN CONFIRMATION**. Do NOT treat the $2,000 USD credit as awarded until Google replies in writing (CDR-014).
2. **DF-054 Website Crawlability & Production Deployment:**
   - Injected semantic, crawlable HTML inside `<div id="root">` of [`frontend/index.html`](../frontend/index.html), ensuring search engine crawlers and non-JavaScript reviewers see full platform capabilities, owner/trainer value propositions, and infrastructure details.
   - Expanded [`frontend/public/sitemap.xml`](../frontend/public/sitemap.xml) from 1 root URL to all 10 core public routes.
   - Curated meta description in [`frontend/index.html`](../frontend/index.html) to eliminate unevidenced verification claims (resolving DF-016 copy risk).
   - Deployed frontend to production Firebase Hosting (`gen-lang-client-0028123502`) under explicit owner authorization.
   - Verified live in production via curl: `https://dogtrainersdirectory.com.au/` returns HTTP 200 with 6,163-byte static fallback; `https://dogtrainersdirectory.com.au/api/health` returns `{"ok":true,"service":"dog-trainers-directory-match-engine","database":"available"}`; sitemap returns 10 valid URLs.
3. **Established the Commercial Scaling & Funding Strategy:**
   - Produced [`docs/DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md`](DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md) outlining the 4 growth/revenue engines and 3-phase capital roadmap.
   - Reconciled roadmap stages R10, R11, R12, and R13 with clear commercial alignment boundaries.
4. **Current Test Integrity:**
   - **Backend:** 663 / 663 passed in 21.27s (`.venv/bin/python backend/scripts/run_isolated_integration_suite.py`).
   - **Frontend:** 81 / 81 passed in 2.20s across 11 test files (`npm test` in `frontend/`).
   - Contracts: `COPY_GUARD_CHECK=PASS`, `PRELAUNCH_RELEASE_GATE=PASS`, `SANDBOX_DEPLOY_CONTRACT=PASS`.

---

## 2. Objective, Authority & Execution Scope

- **North Star:** Establish DTD as a trustworthy, automated dog-trainer discovery and matching service in Greater Melbourne operating predominantly through automation with high margins (90–95%) and founder effort limited to exception-handling (< 2 hrs/week).
- **Sequential Roadmap Execution:** Complete stages **R4 → R5 → R6 → R7 → R8** in the developer sandbox (`dogtrainersdirectory-dev`, Cloud Run `dtd-api-dev` / `dtd-web-dev`, Atlas `dtd_sandbox`), verify the developer sandbox as a complete product, and deliver the audit packet to the owner.
- **Authority Boundaries:**
  - Ordinary implementation, testing, docs, commits, and sandbox advancements have continuing standing authority under `AGENTS.md`.
  - **R9 Production Promotion:** Requires explicit owner authority following the completed R8 owner audit.
  - **R11 Live Billing:** `ENABLE_TRAINER_BILLING_CHECKOUT=0` remains fail-closed. Activating Stripe live checkout or charging real cards requires separate explicit owner authority.
  - **No Data Deletion / Credential Mutation:** No live database destruction or secret exposure.

---

## 3. Verified Developer & Production Environments

| Surface | Environment | Identity / Current State | Verified Evidence |
|---|---|---|---|
| **Sandbox Project / Region** | Developer | `dogtrainersdirectory-dev` / `australia-southeast1` | Bounded test environment |
| **Sandbox Web** | Developer | `dtd-web-dev-00024-nlj` (or current revision) | `https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/` |
| **Sandbox Ops** | Developer | `/ops` console with v3 admin passcode | Passcode rotation verified |
| **Sandbox API** | Developer | `dtd-api-dev-00060-x5r` (or current revision) | `https://dtd-api-dev-x2kdoaemtq-ts.a.run.app/api/health` |
| **Sandbox Database** | Developer | Isolated MongoDB Atlas `dtd-sandbox` / db: `dtd_sandbox` | Zero production connection |
| **Production Project** | Production | `gen-lang-client-0028123502` | Live customer surface |
| **Production Frontend** | Production | Firebase Hosting on `dogtrainersdirectory.com.au` | HTTP 200, 6,163-byte static fallback verified |
| **Production API** | Production | Cloud Run `dtd-api` (routed via Firebase `/api/**`) | `/api/health` healthy |
| **Production Billing** | Production | GCP Billing Account `0104B3-AB5AF0-8F0A01` | Admin IAM verified for `admin@dogtrainersdirectory.com.au` |
| **Ingestion Scheduler** | Sandbox | `dtd-trainer-ingest-cron` daily 02:00 Melbourne | **PAUSED** pending R4 DF-044/045 gates |

---

## 4. Thorough Plan Integration: 4 Commercial Engines into the R0–R13 Roadmap

The companion Antigravity session MUST understand how the commercial engines in [`docs/DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md`](DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md) map into the technical milestones so that no revenue mechanism, conversion loop, or SEO requirement is omitted during implementation.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        4 REVENUE & GROWTH ENGINES                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Suburb SEO Landing Pages  │ 2. Guided Matching Pipeline             │
│    (Zero-CAC Organic Search) │    (High-Intent Owner Need Formulation) │
├──────────────────────────────┼─────────────────────────────────────────┤
│ 3. Profile Claim & Pro Trial │ 4. Suburb Sponsorship Scarcity          │
│    (A$19/mo Pro via Lead Gen)│    (Max 2/suburb @ A$39/mo High Margin) │
└──────────────────────────────┴─────────────────────────────────────────┘
```

### Engine 1: Programmatic Suburb SEO (Zero-CAC Organic Inflow)
- **Concept:** Dog owners search locally by suburb (e.g., *"dog trainer Camberwell"*, *"puppy training Richmond"*). DTD captures this intent with programmatic landing pages.
- **Roadmap Integration:**
  - **R5 (Frontend Journey):** Ensure `/trainers` and suburb filtering routes are fast, accessible, and crawler-friendly.
  - **R7 / R8 (Metadata & SEO):** Introduce structured JSON-LD schema (`LocalBusiness`, `FAQPage`, `BreadcrumbList`) and programmatic suburb pages (`/suburbs/:suburb_slug`). Expand [`frontend/public/sitemap.xml`](../frontend/public/sitemap.xml) dynamically to cover all 539 Greater Melbourne suburbs as trainer density expands.
  - **CRITICAL GUARD:** **NEVER remove the static semantic fallback HTML inside `<div id="root">` in [`frontend/index.html`](../frontend/index.html)**. Client-side-only SPAs that render an empty `#root` trigger Google crawler rejections and SEO penalties (DF-054).

### Engine 2: Guided Matching Pipeline (High-Intent Conversion)
- **Concept:** 4-step smart questionnaire (suburb, behavior/need, training format, budget/timeline) returning 1–3 best-fit trainers with explainable match rationale.
- **Roadmap Integration:**
  - **R5 (Owner Questionnaire UI):** Smooth, responsive, accessible questionnaire flow with progressive disclosure and zero private data leakage in URLs.
  - **R6 (Matching Engine & Decision Contract v2):**
    - Deterministic eligibility gating before AI.
    - AI-assisted fit scoring via Gemini (with deterministic rule-based fallback).
    - **LOCKED ANTI-GAMING INVARIANT:** **Paid-neutral presentation.** Sponsored/Pro status applies **ONLY within the approved 0.05 comparable-fit band**. A paying trainer can NEVER leapfrog a significantly better-fitting unpaid trainer.
    - Explainable match reasons displayed to the dog owner (e.g., *"Matched for in-home reactive dog rehabilitation within 5km of Hawthorn"*).

### Engine 3: "Claim Your Profile" & 30-Day Free Pro Trial (A$19/mo Conversion)
- **Concept:** Free core listings give trainers value by emailing them direct owner enquiries. Unclaimed profiles have a prominent "Claim this business" badge. Claiming activates an instant 30-Day Free Pro Trial (`STRIPE_LIVE_ANCHOR_AT`) converting to A$19/month.
- **Roadmap Integration:**
  - **R4 (Trainer Supply):** Enforce field provenance, contact resolution, and canonical deduplication (DF-051) so that claimed profiles have verified identity and contact paths.
  - **R5 (Claiming Journey):** Front-and-centre "Claim Profile" CTA on unclaimed trainer cards, leading to secure business email/SMS verification (DF-030).
  - **R7 (Transactional Lead Notifications):** Protected enquiry submission triggers an immediate, beautifully structured lead email to the trainer. The email demonstrates concrete customer demand generated by DTD.
  - **R11 (Live Billing Activation):** Stripe checkout integration (`ENABLE_TRAINER_BILLING_CHECKOUT=1`), automated Day-23 trial expiry warning (`pro_trial_warning_job.py`), customer portal, and self-serve cancellation.

### Engine 4: Suburb Sponsorship Scarcity (A$39/mo High-Margin MRR)
- **Concept:** Trainers can sponsor their primary catchment area for A$39/month. Strict scarcity: **maximum 2 sponsors per suburb** (locked in `specs/MONETISATION_AND_PRICING.md`).
- **Roadmap Integration:**
  - **R6 (Matching Placement):** Within the 0.05 comparable-fit band, active Suburb Sponsors for the owner's requested suburb receive top placement with an honest "Featured Sponsor" badge.
  - **R11 (Inventory Control):** Concurrency-safe inventory reservations in MongoDB preventing more than 2 active subscriptions per suburb. Trainer dashboard shows live scarcity alerts (*"Only 1 sponsor spot remaining in Camberwell"*).

---

## 5. Next Authorized Work: Stage-by-Stage Guide (R4 → R13)

| Stage | Focus & Remaining Work | Commercial Strategy Requirement to Integrate | Exit Gate |
|---|---|---|---|
| **R4** | **Lawful Trainer Supply & Deduplication**<br>- Resolve DF-044 (exact source approval matching)<br>- Resolve DF-045 (RFC 9309 robots fail-closed)<br>- Resolve DF-051 (acquisition dedup for unclaimed profiles)<br>- Ingestion scheduler stays PAUSED | Ensure clean trainer catchment data and email contact fields so Engine 3 (Lead Notification & Claim flow) works reliably. | Independent code audit passes; synthetic allow/deny tests pass. |
| **R5** | **Owner & Trainer-Facing Journeys**<br>- Mobile/desktop guided questionnaire<br>- Protected enquiry submission & consent<br>- Trainer profile claim flow (DF-030)<br>- Accessible, truth-in-advertising UI (DF-016 resolved) | Maintain static fallback in `index.html`. Add clear "Claim Listing" trigger on trainer profile pages (Engine 3). | Browser testing across viewports; form submission verified in sandbox. |
| **R6** | **Matching Pipeline & Fairness**<br>- Mandatory Decision Contract v2 / M1–M6, M8<br>- Deterministic eligibility + AI fit parity<br>- Urgent triage & thin-supply handling | Enforce strict 0.05 paid-neutrality band (Engine 2). Wire suburb-sponsor ranking bonus inside the 0.05 band without distorting true fit (Engine 4). | 200+ matching tests pass; live sandbox matching scenario clean. |
| **R7** | **Ops Console & Communications**<br>- DF-047 Support cases queue & reply sync<br>- DF-048 Truthful email delivery status<br>- DF-052 Atomic fail-closed AI budget ceiling<br>- Monitoring alerts verified | Ensure instant lead enquiry notifications to trainers include direct DTD branding and Claim CTA (Engine 3). Zero manual founder overhead for lead routing. | `/ops` tested with synthetic scenarios; alert delivery confirmed. |
| **R8** | **Integrated Sandbox Acceptance**<br>- Master end-to-end sandbox walkthrough<br>- Discovery → Match → Enquiry → Email → Claim → Trial Simulator<br>- Clean teardown of all synthetic fixtures | Demonstrate the entire commercial loop (Engines 1–4) operating end-to-end in the developer sandbox with zero errors. | Produce `R8_END_TO_END_SANDBOX_ACCEPTANCE.md` and owner audit packet. |
| **R9** | **Production Promotion**<br>- Owner audit review & authorization<br>- Cloud Run & Firebase canary progression<br>- `ENABLE_TRAINER_BILLING_CHECKOUT=0` stays off | Verify production deployment preserves static fallback HTML in `index.html` and public sitemap. | Owner grants production authority; zero-traffic canary healthy. |
| **R10** | **Real Marketplace Value Observation**<br>- Organic owner search traffic & enquiry rates<br>- Trainer lead response & engagement rates<br>- Unmet suburb demand reporting in `/ops` | Measure baseline conversion rates and SEO organic inflow (Engine 1) before turning on paid billing. | Baseline KPI report established from real observation window. |
| **R11** | **Commercial Activation (Separate Gate)**<br>- Owner authorizes `ENABLE_TRAINER_BILLING_CHECKOUT=1`<br>- Activate Stripe live mode & `STRIPE_LIVE_ANCHOR_AT`<br>- Day-23 warning job, refund policies, billing portal | Launch 30-Day Pro Trial for claimed trainers (Engine 3) and open Suburb Sponsorships (Engine 4). | Stripe live payment, webhook idempotency, and refund flow verified. |
| **R12** | **Sustainable Solo-Operator Business**<br>- Measure MRR (~A$1,255/mo target on 25 Pro + 20 Sponsors)<br>- Gross margins verified at 90–95% ($30–$60/mo hosting)<br>- Founder time verified at < 2 hours/week in `/ops` | Validate high-margin unit economics and exception-led automation. | 2 consecutive reporting periods meet viability threshold. |
| **R13** | **Capital & Expansion Readiness**<br>- Evidence-triggered expansion (Sydney, Brisbane)<br>- Pre-seed funding acceleration ($250k–$500k at $2.5M–$3.5M)<br>- Corporate incorporation: Australian Pty Ltd | Formalize pitch deck with verified Melbourne metrics and transition from Sole Trader to Pty Ltd upon funding. | Owner decision and investor term sheet review. |

---

## 6. Critical Guardrails & Invariants (DO NOT BREAK)

1. **Static Fallback HTML in `index.html`:**
   During any future frontend overhaul or build pipeline updates, **DO NOT delete or overwrite the semantic fallback content inside `<div id="root">` in [`frontend/index.html`](../frontend/index.html)**. This is required for search engines, non-JS reviewers, and Google for Startups re-review (DF-054).
2. **Paid-Neutral Matching Constraint:**
   Under no circumstances may a paid Pro or Sponsored trainer jump ahead of a significantly more qualified organic match. Sponsored priority is strictly capped to the **0.05 comparable-fit window** (Decision Contract v2).
3. **Google for Startups External State:**
   The email to `cloudstartupsupport@google.com` was sent on 24 October 2026. Status is **PENDING / NOT VERIFIED**. Do not mark DF-054 or credit funding as completed until official written confirmation is received.
4. **Stripe Live Billing Fail-Closed:**
   Production billing (`ENABLE_TRAINER_BILLING_CHECKOUT`) must remain `0` through stages R4–R8. Activation occurs strictly in R11 under explicit owner authorization.
5. **Solo-Operator Operating Invariant:**
   `/ops` is the sole administrative surface. Automation by default, owner by exception. Do not build features that require manual daily intervention or data reconciliation.

---

## 7. Immediate Next Steps for the Resuming Agent

1. **Verify git status & branch:** Ensure working on `feature/r4-trainer-supply` in `/Users/carlg/Documents/AI-Coding/dtd`.
2. **Recognize Completed R4–R8 Sandbox Acceptance:**
   - Tasks for R4 (DF-044, DF-045, DF-051), R5 (DF-030), R6 (Decision Contract v2 matching parity), R7 (DF-047, DF-052), and R8 (integrated developer sandbox acceptance) **have already been fully implemented, committed (`5953b20`, `0bc2bc4`, `62e3893`, `1022ad5`), deployed to Cloud Run (`dtd-api-dev-00060-x5r`, `dtd-web-dev-00024-nlj`), and verified live with zero database residue**.
   - See canonical evidence in [`docs/R8_END_TO_END_SANDBOX_ACCEPTANCE.md`](R8_END_TO_END_SANDBOX_ACCEPTANCE.md).
3. **Stage & Commit Handover and DF-054 Changes:**
   - Commit the DF-054 static root HTML, expanded sitemap, and updated commercial documentation.
4. **Deploy Updated Frontend to Developer Sandbox:**
   - Run `bash scripts/deploy_sandbox_frontend.sh` so `dtd-web-dev` in the developer sandbox serves the crawlable root HTML fallback inside `<div id="root">`.
5. **Prepare Branch Promotion PR to `main`:**
   - Push `feature/r4-trainer-supply` to remote and open a promotion PR to `main`.
6. **Owner Audit & R9 Release Gate:**
   - Present the finalized developer sandbox and evidence packet to the owner for formal independent audit. R9 production promotion proceeds only upon explicit owner authorization.
