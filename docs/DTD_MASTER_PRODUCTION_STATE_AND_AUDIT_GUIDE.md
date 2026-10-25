# DTD Master Expected Production State & Sandbox Audit Guide

> **25 October independent containment checkpoint:** owner-approved developer credential replacement is complete. API `dtd-api-dev-contain-1025111028` serves 100% traffic with numeric replacement secret references, checkout/refunds/self-healing all `0`, and no canary tags. Exposed versions are disabled; health, new/old authentication and claim-session rejection checks passed. Trainer ingestion remains PAUSED. The image was reused; this does not deploy the later main source corrections or accept R8. Production was unchanged. DF-055/056 are closed for this containment scope; historical access and DF-001's broader findings remain unresolved. See `DTD_CURRENT_STATE.md`. The table below is a historical implementation report. This guide does not authorise activation; the read-only page inventory cannot certify the write flows below.

**Evidence Date:** 24 October 2026 (Australia/Melbourne)  
**Authority:** Consolidates and updates all prior target documents:
- [`docs/DTD_TARGETED_POST_LAUNCH_STATE.md`](DTD_TARGETED_POST_LAUNCH_STATE.md)
- [`docs/DTD_TARGETED_MATCHING_PIPELINE_STATE.md`](DTD_TARGETED_MATCHING_PIPELINE_STATE.md)
- [`docs/DTD_VISIONISED_TARGET_STATE.md`](DTD_VISIONISED_TARGET_STATE.md)
- [`docs/specs/SANDBOX_VERIFICATION_MATRIX.md`](specs/SANDBOX_VERIFICATION_MATRIX.md)
- [`docs/specs/OPS_AND_OBSERVABILITY.md`](specs/OPS_AND_OBSERVABILITY.md)
- [`docs/specs/MONETISATION_AND_PRICING.md`](specs/MONETISATION_AND_PRICING.md)
- [`docs/specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md`](specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md)
- [`docs/DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md`](DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md)

---

## 1. Executive Summary & Active Sandbox Topology

This document establishes the **single unified benchmark** for the expected production state of Dog Trainers Directory (DTD). It defines the complete, production-grade operating model and serves as your **practical, step-by-step Audit Checklist** for testing the three live developer sandbox surfaces.

### Implementation-reported Sandbox Environment — 24 October 2026 (historical):
| Surface | Reported Endpoint / Service | Reported Revision | Reported Configuration |
|---|---|---|---|
| **Frontend Web** | `https://dtd-web-dev-x2kdoaemtq-ts.a.run.app` | `dtd-web-dev-00025-6z2` | Clean Vite production build; 6,163-byte static fallback HTML in `<div id="root">`; 10-route sitemap; verified origin binding to `dtd-api-dev`. |
| **Backend API** | `https://dtd-api-dev-x2kdoaemtq-ts.a.run.app` | `dtd-api-dev-00062-jxv` | `DB_NAME=dtd_sandbox`; `ENABLE_TRAINER_BILLING_CHECKOUT=1` (Active); `ENABLE_OPS_STRIPE_REFUNDS=1` (Active); `STRIPE_LIVE_ANCHOR_AT=2026-10-24T00:00:00Z` (Active); `OPS_SELF_HEALING_ENABLED=1` (Active). |
| **Database** | MongoDB Atlas Cluster `dtd-sandbox` | Database `dtd_sandbox` | 22 published Melbourne trainers; canonical 539-suburb catalogue; zero production data. |
| **Payments** | Stripe Test Mode (`sk_test_...`) | Webhook `whsec_...` | Real hosted test checkout; official test cards supported ($0 cost, 0 risk). |
| **Communications**| Resend Test Sinks | Sender `no-reply@...` | Containment to test email addresses only. |

---

## 2. Core Operating Model & Non-Negotiable Invariants

1. **Owner-by-Exception:** DTD is built for a solo, non-technical operator. Routine operations (matching, billing, notifications, trial expiry, inventory locking) run autonomously. The founder interacts **only** via `/ops` when genuine human decisions are required.
2. **100% Free for Dog Owners:** No paywalls, no commissions, no introduction fees, and no per-lead charging.
3. **Transparent Fixed Pricing:**
   - **Free Core Listing:** A$0 (Public directory profile, direct owner leads).
   - **DTD Pro:** A$19/month (or A$149/year) with an automatic 30-day free trial.
   - **Suburb Sponsorship:** A$39/month per suburb (strict scarcity: **maximum 2 sponsors per suburb**).
   - **Melbourne-Wide:** A$199/month (strict scarcity: maximum 5 positions).
4. **Paid-Neutral Matching Integrity:**
   - Matching is strictly based on canine needs, behavioral specialty, training philosophy, and geography.
   - Commercial priority (Sponsored/Pro) applies **only within a 0.05 (5 percentage point) comparable-fit band**. A paying trainer can never leapfrog an unpaid trainer who is a materially better fit.
5. **Privacy-First Matching:** Dog behavioural descriptions are minimized, sanitized, never logged to URL query strings, and never sold.
6. **Automated Trial Management:** Claimed trainers entering Stripe Checkout receive a 30-day Pro trial. A scheduled background job sends an automated Day-23 warning email before any card is charged.

---

## 3. Surface 1 Audit Guide: Public Frontend Web App

**Live Audit Link:** 👉 [`https://dtd-web-dev-x2kdoaemtq-ts.a.run.app`](https://dtd-web-dev-x2kdoaemtq-ts.a.run.app)

### Flow 1.1: Homepage Brand, Navigation & Accessibility
- [ ] **Initial Page Load:** Renders cleanly with zero layout shifts, using Barlow / Outfit typography and high-contrast accessible styling.
- [ ] **SEO & Crawlability Check:** View page source (`Ctrl+U` or `Cmd+Option+U`). Verify semantic HTML inside `<div id="root">` containing platform summary, owner/trainer guides, and cloud infrastructure information (DF-054 compliant).
- [ ] **Navigation Header:** Verify clickable links: *Home*, *Directory* (`/trainers`), *How It Works* (`/how-it-works`), *Pricing* (`/pricing`), *Trust* (`/trust`), *FAQ* (`/faq`), *Contact* (`/contact`).
- [ ] **Console Inspection:** Open DevTools (`F12`). Verify **0 JavaScript console errors** or uncaught exceptions.

### Flow 1.2: Trainer Directory & Suburb Filtering (`/trainers`)
- [ ] **Catalogue Rendering:** Displays active Melbourne trainer cards with business names, primary suburbs, specialties, and badges.
- [ ] **Suburb Filter:** Type or select a Greater Melbourne suburb (e.g. *Blackburn*, *Reservoir*, *Brunswick West*). Verify listings filter correctly without page reloads.
- [ ] **Philosophy & Specialty Filters:** Filter by training method (*Positive Reinforcement*, *Balanced*, *LIMA*) and behavioral concerns (*Puppy Foundations*, *Reactivity*, *Separation Anxiety*).
- [ ] **Trainer Profile Card:** Click on a trainer card to navigate to `/trainers/:slug` (e.g. `/trainers/thrive-canine`).

### Flow 1.3: 4-Step Smart Matching Questionnaire (Homepage Hero CTA)
- [ ] **Step 1 (Location):** Enter a Greater Melbourne suburb (e.g. *Richmond* or *Heidelberg*). Autocomplete suggests canonical suburbs from the 539-suburb catalogue.
- [ ] **Step 2 (Dog Details):** Enter dog age in months. Verify derived life stage displays (*Puppy < 6mo*, *Adolescent 6–18mo*, *Adult 18mo–7yr*, *Senior 7yr+*).
- [ ] **Step 3 (Behavioral Needs):** Select primary concerns (*Leash pulling*, *Aggression*, *Separation distress*, *Basic manners*).
- [ ] **Step 4 (Service Format & Consent):** Select preferred format (*In-home private*, *Facility/Group classes*, *No preference*). Enter an optional brief behavioral description. Check mandatory match-processing consent.
- [ ] **Submission & Latency:** Click "Find My Matches". Loading state renders smoothly within 2–4 seconds without screen flicker.

### Flow 1.4: Urgent-Support Triage Safety Routes
- [ ] **Immediate Danger Trigger:** Re-run questionnaire with high-risk phrases (e.g. *"dog bit a child severely"*, *"bleeding heavily"*). Verify system intercepts ordinary matching and renders immediate emergency veterinary/police guidance with 0 delay.
- [ ] **Urgent Animal Health Trigger:** Enter sudden physical distress. Verify system renders 24/7 emergency veterinary hospital options (e.g. *CARE Veterinary*, *Melbourne Vet Referral Hospital*).

### Flow 1.5: Match Results & Diagnostic Reasoning (`/matching/results`)
- [ ] **1–3 Best-Fit Recommendations:** Results page displays 1 to 3 curated trainer cards tailored to the questionnaire input.
- [ ] **Transparent Reason Badges:** Each card highlights explicit reasons for fit (e.g. *"Serves Heidelberg (3km)"*, *"Certified Separation Anxiety Specialist"*, *"In-Home Private Format"*).
- [ ] **Comparable Fit Integrity (0.05 Band):** If a Suburb Sponsor is present, verify they appear at the top **only** if their diagnostic fit score is within 0.05 of the highest organic match.
- [ ] **Thin-Supply Disclosure:** If testing a remote suburb with zero local listings, verify system expands catchment radius with transparent user disclosure.

### Flow 1.6: Protected Client Enquiry (`/trainers/:slug#enquire`)
- [ ] **Enquiry Form:** Enter owner name, email, phone number, and brief notes.
- [ ] **Privacy Guard:** Verify dog behavioral descriptions are stripped of sensitive tokens and never leaked in URL query parameters.
- [ ] **Submission Feedback:** Form displays immediate green confirmation banner (*"Enquiry sent directly to trainer"*).
- [ ] **Backend Automation:** The backend automatically generates a lead notification record and routes an email notification to the trainer.

---

## 4. Surface 2 Audit Guide: Trainer Self-Service, Claiming & Billing

**Live Audit Link:** 👉 [`https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/trainer/billing`](https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/trainer/billing)

### Flow 2.1: Profile Discovery & "Claim Profile" CTA
- [ ] **Locate Unclaimed Listing:** Open an unclaimed trainer profile in the sandbox (e.g. [`/trainers/thrive-canine`](https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/trainers/thrive-canine) or [`/trainers/kintala`](https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/trainers/kintala)).
- [ ] **Prominent CTA:** Verify prominent *"Is this your business? Claim your free profile"* trigger is visible on the card.
- [ ] **Claim Trigger:** Click "Claim Profile" -> Opens secure verification modal.

### Flow 2.2: OTP Claim Challenge & Session Recovery (DF-030)
- [ ] **Submit Business Email:** Enter the trainer's registered email address.
- [ ] **OTP Challenge:** System issues a 6-digit one-time passcode. (In sandbox, check `/ops` or inspect the response).
- [ ] **Enter OTP:** Enter OTP -> Verified. Profile status transitions to `claimed`.
- [ ] **Claim Session Token:** Verified token is stored in `sessionStorage` under `dtd-trainer-billing-auth:<trainer_id>`.
- [ ] **Returning Owner Recovery:** Revisit the profile later. Enter the same email address -> System safely renews the claim session token without returning a 409 conflict error.

### Flow 2.3: Trainer Capability & Listing Management
- [ ] **Edit Listing Modal:** Open edit listing. Verify form pre-fills existing declared values (*Fallback cascade: canonical_value ?? value ?? raw_value*).
- [ ] **Update Catchments:** Add or adjust service areas, in-home training flags, and specialty tags.
- [ ] **Save Changes:** Click "Save Profile" -> Immediate update with zero console errors.

### Flow 2.4: Subscription Checkout (`/trainer/billing?trainerId=<trainer_id>`)
- [ ] **Plan Matrix Display:**
  - **Free Core Listing:** A$0 (Active by default).
  - **DTD Pro:** A$19/month (Highlighted with *"Includes 30-Day Free Trial"*).
  - **Suburb Sponsorship:** A$39/month (Includes suburb dropdown and remaining capacity indicator).
  - **Melbourne-Wide:** A$199/month.
- [ ] **Terms Agreement:** Checkbox *"I accept the subscription billing terms (version 2026-09-24)"* is required.
- [ ] **Click "Continue to Stripe Checkout":** Click button -> Backend calls `POST /api/trainer/billing/checkout` -> Successfully redirects to Stripe Hosted Checkout.

### Flow 2.5: Stripe Hosted Checkout (Test Mode Walkthrough)
- [ ] **Orange Test Mode Banner:** Verify Stripe's page displays a clear banner: **`TEST MODE`**.
- [ ] **Line Items & Tax:** Verify plan name (*DTD Pro* or *Suburb Sponsor*), price (A$19.00 or A$39.00), and 30-day trial indicator (*"Free for 30 days, then A$19/mo"*).
- [ ] **Test Card Payment:**
  - Card Number: `4242 4242 4242 4242`
  - Expiry: Any future date (e.g. `10/28`)
  - CVC: Any 3 digits (e.g. `123`)
  - Name: `Test Trainer`
  - Country/Postal: `Australia` / `3121`
- [ ] **Submit Payment:** Click "Subscribe" -> Stripe processes payment ($0 charged) -> Automatically redirects back to:
  `https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/trainer/billing?trainerId=<id>&checkout=success`
- [ ] **Automatic Entitlement Activation:** The backend receives Stripe webhook `customer.subscription.created`, sets `subscription_status: active`, records the Stripe customer ID, and activates Pro badges automatically.
- [ ] **Suburb Inventory Lock (Engine 4):** If Suburb Sponsor was purchased, verify the selected suburb's remaining capacity decrements (max 2 sponsors).

### Flow 2.6: Self-Service Customer Billing Portal
- [ ] **Manage Subscription CTA:** On `/trainer/billing`, click "Manage Subscription".
- [ ] **Stripe Portal Redirect:** Redirects to Stripe's hosted customer portal in Test Mode.
- [ ] **Test Cancellation:** Click "Cancel Subscription" in Stripe Portal -> Redirects back.
- [ ] **Automated Downgrade:** Webhook `customer.subscription.deleted` arrives -> Backend automatically downgrades listing to Free Core and releases the suburb sponsorship slot for other trainers.

---

## 5. Surface 3 Audit Guide: Operations Console (`/ops`)

**Live Audit Link:** 👉 [`https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/ops`](https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/ops)

### Flow 3.1: Passcode Authentication & Security
- [ ] **Auth Challenge:** Visiting `/ops` displays an administrative password challenge.
- [ ] **Invalid Password:** Enter random text -> Returns HTTP 401 with clean error feedback.
- [ ] **Valid Password:** Enter Secret Manager `dtd-admin-pass` value -> Unlocks the Operations Console immediately.

### Flow 3.2: Level 1 System Status Dashboard
- [ ] **Headline Status:** Calm, green indicator: *"System Operational — Greater Melbourne"*.
- [ ] **3 Core Badges:**
  - **Supply:** Shows published vs. held trainer counts.
  - **Commercial Gate:** Shows **`Stripe Checkout: ACTIVE (Test Mode)`**.
  - **System Loops:** Shows automated background engine status.
- [ ] **10-Second Scannability:** No decorative clutter or fake vanity charts. Only operational truths.

### Flow 3.3: Level 2 "Needs Your Attention" Exception Queue
- [ ] **Actionable Queue:** Displays only genuine operational exceptions (e.g. unverified ABN submissions, claim disputes, email delivery alerts).
- [ ] **3-Question Breakdown:**
  1. *What happened?* (e.g. "ABN mismatch detected during submission").
  2. *Why does it matter?* (e.g. "Statutory verification requires legal business match").
  3. *What can I do?* (Clear 1-click safe action buttons: *Review*, *Approve*, *Hold*, *Dismiss*).
- [ ] **Dismissal Safeguard:** High-severity issues require confirmation before dismissal.

### Flow 3.4: Support Cases Queue & Thread Resolution (DF-047)
- [ ] **Case Queue Filtering:** Filter dropdowns for Status (*All*, *Open*, *In Progress*, *Closed*) and Category (*Delisting*, *Claim Conflict*, *Delivery Issue*, *General*).
- [ ] **Select Thread:** Click on case `sup_20261018_83b365b4`. Verify the thread history detail panel loads on the right with complete conversation history.
- [ ] **Case Desync Guard:** Switch rapidly between cases. Verify thread detail strictly matches the selected case ID without showing stale state.
- [ ] **Operator Reply Form:** Type a test reply to the customer. Click "Send Reply" -> Verifies delivery feedback truthfulness (`receipt_delivered`).
- [ ] **Case Closure Form:** Click "Close Case" -> Prompts for mandatory outcome notes -> Case transitions to `closed` in database.

### Flow 3.5: Read-Only AI Operations Analyst (DF-052)
- [ ] **On-Demand Investigation:** Click "Investigate with AI" on an operational exception card.
- [ ] **Gemini 1.5 Flash Inference:** Real-time AI analysis runs on Vertex AI (`gemini-3.5-flash`).
- [ ] **Structured Card Rendered:** AI card renders with Root-Cause Hypothesis, Supporting Evidence, and Non-Destructive Next Step.
- [ ] **Strict Read-Only Invariant:** AI does not mutate business data, alter listings, or execute refunds automatically.
- [ ] **Atomic Budget Ceiling:** Daily limit counter accurately claims slots in MongoDB (`_budget_lock`) without failing open.

### Flow 3.6: Commercial Subscriptions & Refund Management
- [ ] **Subscription Inventory View:** View active trainer subscriptions, Stripe Customer IDs, and Suburb Sponsor allocations.
- [ ] **Refund Execution (`ENABLE_OPS_STRIPE_REFUNDS=1`):** Select a test subscription -> Click "Issue Refund" -> Prompts for confirmation -> Dispatches refund via Stripe Test Mode -> Immediately releases suburb sponsorship slot and logs an immutable audit event.

### Flow 3.7: Collapsible Advanced Diagnostics
- [ ] **Secondary Diagnostics:** Expand the collapsible "Advanced Diagnostics" disclosure at the bottom.
- [ ] **Health & Telemetry:** Inspect deep health checks, database latency, Resend email dispatch logs, and recent immutable audit records.

---

## 6. Technical & SEO Release Gate Checklist

Before signing off on Stage R8 acceptance, verify these low-level technical contracts:

| Verification Probe | Command / URL | Expected Pass Outcome |
|---|---|---|
| **API Health** | `curl -s https://dtd-api-dev-x2kdoaemtq-ts.a.run.app/api/health` | `{"ok":true,"service":"dog-trainers-directory-match-engine","database":"available"}` |
| **API Config** | `curl -s https://dtd-api-dev-x2kdoaemtq-ts.a.run.app/api/config` | Returns 539 suburbs, `public_matching_enabled: true`, `flat_subscription` mode. |
| **Static HTML Fallback** | `curl -sI https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/` | `HTTP/2 200`, `content-length: 6163` (contains crawlable text in `<div id="root">`). |
| **Public Sitemap** | `curl -s https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/sitemap.xml` | Returns all 10 core public routes with valid XML headers. |
| **Robots.txt** | `curl -s https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/robots.txt` | Disallows `/ops`, allows public routes, references `/sitemap.xml`. |
| **Console Errors** | Browser DevTools on all 3 URLs | **0 errors**. No 404s for bundle assets, fonts, or APIs. |

---

## 7. Sign-Off & Production Promotion Sequence

Once you have completed auditing the 3 links above and confirm the platform meets your expectations:

1. **R8 Final Acceptance Sign-Off:** Confirm to Antigravity that the developer sandbox passes your audit.
2. **Main Branch Consolidation:** We merge `feature/r4-trainer-supply` into `main` via PR with all 810 passing tests.
3. **Stage R9 (Production Release):** Under your explicit production authority, we promote this exact audited release to:
   - Live Website: `https://dogtrainersdirectory.com.au`
   - Production Cloud Run: `dtd-api` (`gen-lang-client-0028123502`)
   - Production Database: MongoDB Atlas `DTD`
