# DTD Dedicated Automation & Platform Integration Specification

**Document Identifier:** `DTD-SPEC-AUTOMATION-2026`  
**Status:** Canonical Implementation & Backend Architecture Specification (SSOT)  
**Date:** September 2026  
**Location Scope:** Greater Melbourne, Victoria, Australia  
**Runtime Environment:** Google Cloud Platform (`australia-southeast1`) & Firebase Multi-Site  

> **Cross-Specification Authority:**  
> • **Runtime & Infrastructure:** Governed by [DTD_GOOGLE_CLOUD_MIGRATION_RUNBOOK.md](DTD_GOOGLE_CLOUD_MIGRATION_RUNBOOK.md) (Cloud Run, Cloud Tasks, Cloud Scheduler, Firebase).  
> • **Data Sourcing & Ingestion:** Governed by [DTD_ACQUISITION_AND_INGESTION_PIPELINE.md](DTD_ACQUISITION_AND_INGESTION_PIPELINE.md) (Launch supply, ABR checks, legal boundaries).  
> • **Product Vision & Pricing:** Governed by [DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md](DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md) (Tiers, ACL compliance, ranking).

---

## Table of Contents
1. [Executive Summary & Architectural Posture](#1-executive-summary--architectural-posture)
2. [Automation Audit & Lifecycle Decisions](#2-automation-audit--lifecycle-decisions)
3. [The 6 Clean Autonomous Background Engines](#3-the-6-clean-autonomous-background-engines)
4. [3rd-Party Integrations & Cost Breakdown](#4-3rd-party-integrations--cost-breakdown)
5. [Third-Party Integration Hardening Contracts](#5-third-party-integration-hardening-contracts)
6. [Automated ABN Lookup Pipeline & Trigger User Flows](#6-automated-abn-lookup-pipeline--trigger-user-flows)
7. [Automated Communication Triggers & Message Lifecycles](#7-automated-communication-triggers--message-lifecycles)
8. [Database State Machine, Indexes & Edge-Case Contracts](#8-database-state-machine-indexes--edge-case-contracts)
9. [Operator Exception Handling & Bounded Oversight in `/ops`](#9-operator-exception-handling--bounded-oversight-in-ops)
10. [Step-by-Step Implementation & Verification Plan](#10-step-by-step-implementation--verification-plan)
11. [24/7 High-Availability, Automated Backups & Disaster Recovery Architecture](#11-247-high-availability-automated-backups--disaster-recovery-architecture)

---

## 1. Executive Summary & Architectural Posture

Dog Trainers Directory (DTD) is engineered as an **automation-first, single-operator platform** for Greater Melbourne. Over 95% of routine operations—data harvesting, profile enrichment, claiming, matching, communications, subscriptions, and renewals—run autonomously without human intervention.

Human oversight is strictly **bounded to exceptions** via the Operations Console (`/ops`), requiring approximately 10–15 minutes of operator attention per week.

---

## 2. Automation Audit & Lifecycle Decisions

### 2.1 What Stays (Keep & Preserve)
1. **Managed Task Orchestration & Queue Dispatch:**
   - Background execution logic is preserved and hosted via **Google Cloud Scheduler** (cron webhooks) and **Google Cloud Tasks** (asynchronous outbox queue), replacing unmonitored Python asyncio while-loops.
2. **T+7 Automated Outcome Outreach Engine (`services/automation.py`, `services/follow_up_tokens.py`):**
   - Automated post-intro follow-ups with HMAC-signed single-use tokens to record client outcomes (`hired`, `still_deciding`, `need_another_match`).
3. **Resend Transactional Email Engine (`services/notifications.py`):**
   - Fail-soft HTTP retries, exponential backoff, SHA-1 deduplication keys, and event logging in `db.notification_events`.
4. **Fraud & Anti-Gaming Guardrails (`services/fraud.py`):**
   - IP rate-limiting (max 6/hr), duplicate detection (same IP + same trainer in 24h; same email + same trainer in 7d).
5. **System Health & Anomaly Monitor (`engine.update_health`):**
   - Continuous anomaly detection monitoring intro/conversion cliff drops and logging snapshots in `db.system_state`.

### 2.2 What to Change (Refactor & Upgrade)
1. **`services/stripe_billing.py`:**
   - *From:* Standalone $5 one-off Stripe invoices per intro (`collection_method="send_invoice"`).
   - *To:* **Stripe Subscriptions & Checkout Sessions** for Pro ($19 AUD/mo), Suburb Sponsorship ($39 AUD/mo), and Melbourne-Wide ($199 AUD/mo). Handle recurring subscription webhooks (`customer.subscription.created/deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`) and 1-click refunds.
2. **`engine.recompute_ranking`:**
   - *From:* Ranking trainers purely based on $5 intro conversion rates.
   - *To:* **Multi-Surface Tiered Ranking**:
     - Melbourne-Wide Sponsors $\rightarrow$ Regional / Suburb Sponsors $\rightarrow$ Pro Verified $\rightarrow$ Claimed Free $\rightarrow$ Ingested Base.
     - Factor in review ratings, review volume, profile completeness, response latency, and verified client outcomes.
3. **`services/ai.py`:**
   - *From:* Keyword-split heuristic matching and basic website presence scoring.
   - *To:* **Google Gemini 1.5 Flash Engine**: Schema-bound JSON extraction of training philosophies, specialties, and service formats from lawful sources; multi-factor diagnostic matching evaluating dog age, behavioral issue, and method fit.
   - *Sensitive Enum Grounding Tokens (`training_philosophy`):* Because training philosophy is contentious in the dog training industry, Gemini extraction must be cross-verified by strict regex keyword grounding against explicit physical tokens in source text: `"PPG Member"`, `"Force-Free"`, `"LIMA"`, `"IAABC"`, or `"Balanced"`. Ambiguous or ungrounded cases must fall back to `training_philosophy: null` ("Unspecified"), requiring the trainer to claim and set it themselves.
   - *Deterministic Taxonomy Quarantine (`unmapped_tags`):* Extracted terms that do not match DTD's canonical taxonomy (e.g. "K9 Life Coach", "Puppy Schooler") are quarantined into an explicit `unmapped_tags` array on the Trainer schema, rather than contaminating directory search filters or being lost.
4. **`services/notifications.py`:**
   - *From:* Technical emails displaying internal numbers (`Confidence score: 0.85`).
   - *To:* Customer-facing transactional templates: Unclaimed Lead Alerts ("A dog owner in [Suburb] enquired with you"), OTP magic links, and 48-hour Suburb Vacancy alerts.
5. **`engine.process_discovery_queue`:**
   - *From:* Regex-only URL link extraction.
   - *To:* **Structured Ingestion Pipeline**: Ingests approved official-business-website facts and ABR identity/status records with automated deduplication, evidence capture, suppression, and quality gating. Google Maps/Places content is excluded from directory inventory.

### 2.3 What to Add (New Automation Pipelines)
1. **Autonomous Claim & OTP Verification Engine (`services/claim_engine.py`):**
   - Dispatches 6-digit OTP codes via **Firebase Phone Authentication** (SMS) or Email (Resend). Validates OTP $\rightarrow$ sets `claim_status="claimed"` and unlocks Trainer Portal instantly. Handles `CLAIM_DISPUTED` state lock if multiple claims collide.
2. **Suburb Vacancy & Waterfall Succession Engine (`services/suburb_inventory.py`):**
   - Live availability tracking across ~300 Melbourne suburbs (capped at max 2/suburb). Automated succession queue: When a sponsor cancels, generates a 48-hour priority purchase link for Waitlist Position #1, auto-cascading to Position #2 if unpurchased.
3. **Multi-Source Deduplication & Entity Merger (`services/deduplication.py`):**
   - Normalizes Australian phone numbers (E.164 `+614...`), website domains, and ABNs to merge overlapping scraped sources into single rich profiles.
4. **Dynamic SEO & XML Sitemap Pipeline (`services/seo_generator.py`):**
   - Dynamically serves `/sitemap.xml` containing all ~300 suburb landing pages and human-readable trainer slugs (`/t/k9-balance-richmond`) with canonical tags and JSON-LD schema.
   - **Programmatic SEO (pSEO) Thin-Content Gate:** To prevent Google search index quality penalties on low-inventory suburb pages:
     - *Internal Directory Search:* Published listings are immediately searchable by dog owners on DTD (`published: true`).
     - *External Search Engines:* Suburb landing pages dynamically render `<meta name="robots" content="noindex, follow" />` until the suburb reaches at least **3 active listings OR >500 words of localized editorial content**. Once either threshold is achieved, the page switches to `index, follow` and is automatically added to `/sitemap.xml`.
5. **Verified Client Review Pipeline (`services/review_engine.py`):**
   - Dispatches T+14 review invites to owners with verified introductions, preventing fake reviews or unverified review-bombing.

### 2.4 What to Abandon (Remove & Decommission)
1. **ABANDON `engine.recompute_pricing` (90-second loop):**
   - *Why:* Updates dynamic per-suburb $5 intro fees in `pricing_state`. Obsolete under flat SaaS subscriptions ($19/mo, $39/mo, $199/mo).
2. **ABANDON `engine.run_billing_recovery` (30-minute loop):**
   - *Why:* Manually retried failed $5 email invoices. Stripe Subscriptions handles recurring payment retries and dunning natively via Smart Retries.
3. **ABANDON `engine.promote_inferred_conversions` ($65 conversion fee):**
   - *Why:* DTD does not charge a $65 commission on hires. Conversions are tracked purely as quality/reputation signals.
4. **ABANDON `services/claim_state.py` (Marketing Claims `STATE_0` to `STATE_4`):**
   - *Why:* Enforced bureaucratic gates on whether copy could mention "Melbourne-wide". Pure governance friction.
5. **ABANDON Artificial Code Gates in `backend/server.py`:**
   - *Why:* Remove `PUBLIC_MATCHING_ENABLED=false` 403 blocks and legacy intro-fee toggles so the platform operates openly.

---

## 3. The 6 Clean Autonomous Background Engines

Orchestrated via **Google Cloud Scheduler** invoking authenticated endpoints on Cloud Run:

```
                       CLEAN AUTONOMOUS ENGINE ARCHITECTURE
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION & DEDUPLICATION ENGINE (Cadence set per approved source contract) │
│ • Reads an approved feed, official website facts, and ABR identity evidence    │
│ • Identifies as `DTD-Bot/1.0` with strict rate-limit (max 1 req / 2s per domain)│
│ • Normalizes phone, domain, and ABN → merges duplicate candidate records       │
│ • Checks db.delisted_entities suppression table to prevent re-ingestion        │
│ • AI structures supported facts; separate evidence gate publishes or holds    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 2. RANKING & REPUTATION ENGINE (Runs every 5 minutes)                           │
│ • Recomputes composite ranking across Melbourne & Suburb pages:                 │
│   Score = Tier Weight + (Review Rating × log(Review Count + 1)) + Latency Score │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 3. SUBURB VACANCY & SUCCESSION ENGINE (Runs every 15 minutes)                   │
│ • Monitors expired or cancelled Suburb Sponsorships (cap: 2 per suburb)        │
│ • Triggers 48h priority purchase emails to Waitlist Position #1                 │
│ • Cascades unpurchased slots to Waitlist Position #2 after 48 hours             │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 4. OUTCOME OUTREACH & REVIEW ENGINE (Runs hourly)                               │
│ • Queries introductions reaching T+7 days → sends outcome check-in emails       │
│ • Queries confirmed hires reaching T+14 days → sends verified review invites    │
│ • Evaluates sponsor response rate SLA (>75% acknowledgment via relay/portal)    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 5. VERIFICATION & STALENESS ENGINE (Runs every 12 hours)                        │
│ • Checks domain health and website status of published listings                 │
│ • Re-verifies ABN status on ABR; auto-revokes badges on business cancellation   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 6. PLATFORM HEALTH, ANOMALY & DATA QUALITY ENGINE (Cloud Monitoring & Crons)    │
│ • Evaluates traffic flow, conversion drops, and unhandled exceptions            │
│ • Scheduled Daily Data Quality (DQ) Audit across 3 explicit integrity rules:   │
│   1. Completeness: Zero published listings missing suburb, name, or services.    │
│   2. Validity: Australian E.164 phone format (+61 4xx... or +61 3...), URLs      │
│      returning HTTP 200/301.                                                     │
│   3. Uniqueness: Zero duplicate place_id or abn records in db.trainers.          │
│ • Emits real-time alert cards to the /ops Work Queue and P1 SMS pager           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 3rd-Party Integrations & Cost Breakdown

### 4.1 Integration Inventory Status & Credentials Mapping

| Platform / Service | Status in Project | Credentials & Env Mapping | Primary Function |
| :--- | :---: | :--- | :--- |
| **Google Cloud Run** | **Configured** | `GCP_PROJECT_ID=gen-lang-client-0028123502` | • Containerized backend compute in Sydney (`australia-southeast1`). |
| **Cloud Scheduler & Tasks** | **Configured** | `X_CLOUD_SCHEDULER_SECRET` | • 24/7 cron triggers and resilient transactional outbox queue. |
| **Firebase Phone Auth** | **Configured** | `FIREBASE_API_KEY`<br>`FIREBASE_AUTH_DOMAIN` | • 10,000 free AU mobile SMS OTP claims per month (`+614...`). |
| **Firebase Hosting** | **Configured** | Multi-site: `default` & `dtd-first-leash` | • Edge hosting for directory SPA and education hub. |
| **Google Gemini API** | **Configured** | `GEMINI_API_KEY` (Pay-As-You-Go) | • Structured fact extraction & diagnostic matching (APPs compliant). |
| **Stripe Australia** | **Confirmed** | `STRIPE_SECRET_KEY`<br>`STRIPE_WEBHOOK_SECRET`<br>`STRIPE_DEFAULT_CURRENCY=aud` | • Subscriptions ($19/mo, $39/mo, $199/mo), Checkout, Customer portal, and refunds. |
| **Resend** | **Confirmed** | `RESEND_API_KEY`<br>`RESEND_FROM=no-reply@dogtrainersdirectory.com.au` | • Transactional emails: lead alerts, OTP magic links, T+7 follow-ups, review invites. |
| **MongoDB Atlas** | **Confirmed** | `MONGO_URL=mongodb+srv://dtd...`<br>`DB_NAME=dtd` | • Managed cluster in GCP Sydney (`australia-southeast1`) with pool ceiling. |
| **ABR Lookup API** | **Configured** | `ABR_GUID` | • Statutory ABN/name identity and active-status verification. |
| **Sentry** | **Confirmed** | `SENTRY_DSN`<br>`SENTRY_ENVIRONMENT=production` | • Deep exception tracking for Python backend and React frontend. |
| **PostHog** | **Confirmed** | Client snippet in `frontend/public/index.html` | • Client-side event telemetry & session capture. |

### 4.2 Complete Itemized Cost Breakdown (Google Cloud Architecture)

```
                               MONTHLY COST BREAKDOWN (AUD)
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ PLATFORM / SERVICE           │ PRICING MODEL & FREE TIER    │ ESTIMATED COST (LAUNCH / MO) │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Google Cloud Run**         │ 2M requests/mo free          │ **$0.00** (Under free tier)  │
│ **Cloud Tasks & Scheduler**  │ 1M tasks free; 3 jobs free   │ **~$0.45 AUD**               │
│ **Firebase Hosting (Multi)** │ 10 GB storage free           │ **$0.00** (Under free tier)  │
│ **Firebase Phone Auth**      │ **10,000 free SMS OTPs / mo**│ **$0.00** (Free perpetual)   │
│ **Google Gemini 1.5 Flash**  │ 1,500 free requests / day    │ **~$0.50 AUD**               │
│ **Google Maps Platform**     │ **$200 USD/mo free credit**  │ **$0.00** (Covered by credit)│
│ **MongoDB Atlas (GCP Sydney)│ Free M0 / Serverless         │ **$0.00 - $15.00 AUD**       │
│ **Resend (Email)**           │ Free 3,000 emails / month    │ **$0.00** (Under free tier)  │
│ **Stripe Australia**         │ 1.75% + 30¢ per AU card sale │ **$0 fixed** (Pay-per-sale)  │
│ **ABR Government API**       │ **100% Free** (ATO Gov API)  │ **$0.00** (Free perpetual)   │
│ **.com.au Domain Name**      │ $20 AUD / year               │ **~$1.70 AUD / month**       │
├──────────────────────────────┴──────────────────────────────┼──────────────────────────────┤
│ **TOTAL ESTIMATED FIXED RUNNING COST**                      │ **~$2.65 - $17.00 AUD / mo** │
│ **WITH GOOGLE FOR STARTUPS CREDITS ($2,000 - $200,000 USD)**│ **$0.00 AUD / month**        │
└─────────────────────────────────────────────────────────────┴──────────────────────────────┘
```

---

## 5. Third-Party Integration Hardening Contracts

Every third-party integration follows strict engineering contracts:

```
                       INTEGRATION HARDENING CONTRACTS
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. TURNKEY BOOKING EMBED CONTRACT (Calendly / Acuity / Custom Schedulers)       │
│ • Protocol Validation: Enforce strict `https://` URLs; reject `javascript:`/raw │
│ • Sandboxing: `sandbox="allow-scripts allow-same-origin allow-popups allow-forms"`│
│ • Referrer Policy: `referrerpolicy="no-referrer-when-downgrade"`                │
│ • Graceful Fallback: If URL is non-embeddable, auto-render verified CTA:       │
│   `[Book Consultation with Trainer ↗]` opening via `target="_blank" rel="noopener"`│
├─────────────────────────────────────────────────────────────────────────────────┤
│ 2. SMS OTP & ANTI-FRAUD RATE-LIMIT CONTRACT (Firebase Phone Auth)               │
│ • Regional Guard: Enforce Australian E.164 (`+614...`) before API call.         │
│ • Toll-Fraud Defense: reCAPTCHA Enterprise + Firebase App Check verification.   │
│ • Dual-Channel Fallback: If SMS fails or times out (10s), UI offers instant     │
│   fallback: "Didn't receive SMS? Send verification code to email".              │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 3. GOVERNMENT BUSINESS REGISTER CONTRACT (ABR Web Services)                     │
│ • Offline Mathematical Pre-Filter: ATO Modulus 89 checksum (0ms offline check). │
│ • JSONP Unwrapping: Built-in regex parser unwraps `callback({...})` to raw JSON.│
│ • Government Quota Guard: 30-day cache (`db.abn_cache`) drops API calls by >95%.│
│ • Trading Name Sunsetting: Fall back to Sole Trader legal name token matching   │
│   when post-October 2025 `business_names` array is empty.                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 4. STRIPE WEBHOOK & B2B TAX CONTRACT (Stripe Australia)                         │
│ • Cryptographic Verification: `stripe.Webhook.construct_event()` with raw body. │
│ • Replay Protection: Dedup events against `db.stripe_events` via `event.id`.    │
│ • Australian Tax Provisioning: `stripe.Customer.create_tax_id(type="au_abn")`   │
│   attaches verified ABN to generate ATO-compliant 10% GST tax invoices.         │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 5. MEDIA OPTIMIZATION & CDN CONTRACT (Firebase Storage / GCS)                   │
│ • Client Validation: Max 5MB per upload; accept strictly `image/jpeg,png,webp`. │
│ • CDN Caching: Assets served with `Cache-Control: public, max-age=31536000`.    │
│ • Core Web Vitals: All portfolio images render with `loading="lazy"` & width/ht.│
├─────────────────────────────────────────────────────────────────────────────────┤
│ 6. MODERN UI COMPONENT CONTRACTS (`vaul`, `input-otp`, `embla-carousel-react`)  │
│ • Responsive Drawer Switch: `< 768px` renders tactile bottom-sheet drawer       │
│   (`vaul`); `≥ 768px` renders centered Radix Dialog modal.                      │
│ • Accessible OTP: Strict numeric `inputMode="numeric"` with clipboard paste and │
│   auto-focus progression across all 6 slots.                                    │
│ • Smooth Carousel: Touch-drag physics with keyboard navigation & aria labels.   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Automated ABN Lookup Pipeline & Trigger User Flows

```
                             ABN TRIGGER WORKFLOWS MAP
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ FLOW 1: Supply Ingestion & Seeding Flow (System Triggered)                                │
│ • Trigger: Background crawler discovers public listing with an ABN.                       │
│ • Execution: Modulus 89 Checksum (0ms) → ABR API Lookup → db.abn_cache write.             │
│ • Outcome: If Active & VIC → Auto-provisions "ABN Verified" badge with popover metadata.  │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ FLOW 2: Trainer Self-Submission Flow (`/submit`) (Trainer Triggered)                      │
│ • Trigger: Trainer submits new listing on `/submit` and inputs their 11-digit ABN.        │
│ • Execution: Instant client-side validation → Backend queries ABR via GUID.               │
│ • Outcome: Auto-populates legal entity name, trading name, and registered postcode.       │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ FLOW 3: Profile Claiming & Landline Flow (`/t/:slug`) (Trainer Triggered)                 │
│ • Trigger: Trainer clicks "Claim this business" on an unclaimed profile.                  │
│ • Execution: If mobile → Instant SMS OTP. If landline (03) → Claimant enters ABN.        │
│ • Outcome: Name matches ABR sole-trader/company records → Instant claim approval.         │
│   Discrepancy (e.g. maiden name) → Emits 1-click review ticket to /ops Work Queue.        │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ FLOW 4: Stripe B2B Subscription Checkout (`/pricing`) (Trainer Triggered)                 │
│ • Trigger: Trainer upgrades to Pro ($19/mo) or Suburb Sponsorship ($39/mo).              │
│ • Execution: System provisions `stripe.Customer.create_tax_id(type="au_abn", value=abn)`. │
│ • Outcome: Generates ATO-compliant tax invoices with itemized 10% GST and trainer's ABN.  │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ FLOW 5: 14-Day Periodic Re-Verification Loop (System Triggered - Worker Engine 5)          │
│ • Trigger: Scheduled background worker sweeps all published profiles every 14 days.       │
│ • Execution: Re-queries ABN against ABR API.                                              │
│ • Outcome: If ABN is Cancelled/Deregistered → Automatically revokes "ABN Verified" badge   │
│   and alerts operator in /ops.                                                            │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Automated Communication Triggers & Message Lifecycles

```
                               COMMUNICATION TRIGGERS MAP
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. TRAINER LIFECYCLE (AUTOMATED)                                                          │
│ • Unclaimed Lead Alert (Email): "A dog owner in [Suburb] requested a consultation. Claim   │
│   your profile to view details & reply."                                                  │
│ • Claim Verification OTP (SMS/Email): 6-digit one-time code for instant identity proof.   │
│ • Claim Welcome & Access (Email): Magic login link + guide to customizing their profile.  │
│ • Claimed Lead Notification (Email + SMS): Instant ping when an owner sends an inquiry.   │
│ • 30-Day Pro Trial Expiry Warning (Email - Day 23): "Your trial ends in 7 days."          │
│ • Suburb Sponsorship Vacancy Alert (Email): "Spot opened in [Suburb]. 48h priority window"│
│ • Stripe Tax Invoices & Receipts (Email): Monthly/annual receipts with ABN & GST details. │
│ • Payment Failed Warning (Email): Card failure alert with 14-day update grace period.     │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. DOG OWNER LIFECYCLE (AUTOMATED)                                                        │
│ • Diagnostic Match Summary (Email): Copy of matched trainers, diagnostic notes & links.   │
│ • Consultation Sent Confirmation (Email): "Your message was delivered to [Trainer Name]." │
│ • T+7 Outcome Check-in (Email): "Did you connect with [Trainer]?" (Records conversions).  │
│ • T+14 Verified Review Invite (Email): "Share your feedback for [Trainer Name]."           │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. OPERATOR EXCEPTION ALERTS (/ops Real-Time Notifications)                               │
│ • Ingestion Anomaly Alert: Low confidence score (<80%) or conflicting business data.     │
│ • Unmatched Claim / Dispute Exception: Multiple claimants or ABN document uploaded.      │
│ • Stalled Introduction Alert: Intro with 0 trainer response after 7 days.                 │
│ • Stripe Dispute / Chargeback Alert: Immediate alert if a payment is disputed.            │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.1 Anchor Business "Launch Selection" Outreach Copy

To convert passive seeded inventory into active platform relationships with 10–15 high-reputation, well-reviewed trainers across key Melbourne quadrants (e.g. Richmond, Brunswick, Brighton), the following standardized outreach email copy is dispatched via Resend:

```text
Subject: Featured Launch Listing on Dog Trainers Directory: [Business Name] ([Suburb])

Hi [Trainer Name],

We are launching Dog Trainers Directory—an independent, curated Melbourne guide connecting dog owners with vetted, method-transparent local professionals.

We have selected [Business Name] as one of our featured launch listings for [Suburb]. Your business profile is live and receiving local search traffic:
[Link to https://dogtrainersdirectory.com.au/t/your-slug]

We invite you to review your free profile and verify that your service formats, methods, and contact details are accurate so local owners can reach you directly.

Warm regards,
The DTD Melbourne Team
```

---

## 8. Database State Machine, Indexes & Edge-Case Contracts

### 8.1 Database Collections Schema
```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. db.trainers                                                                            │
│    { id, slug, name, suburb, region, phone, email, website, services, categories, bio,    │
│      training_philosophy, specialties, service_formats, unmapped_tags: [], price_range,    │
│      review_summary, claim_status, tier, sponsored_suburbs, booking_url, gallery_images,   │
│      outcome_score, verified_at, last_scraped_at, details_confirmed_at, abn, abn_status,   │
│      abn_verified, abn_badge_payload, response_rate_30d, published }                       │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. db.abn_cache (Government API Cache with 30-Day TTL)                                    │
│    { abn, entity_name, business_names, entity_type_name, address_state, address_postcode, │
│      gst_status, is_active, is_victoria, retrieved_at, _cached_at_ts }                    │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. db.claim_events                                                                        │
│    { id, trainer_id, claimant_email, claimant_phone, method, otp_hash, status,             │
│      verified_at, proof_document_url, dispute_state, operator_id, created_at }             │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. db.suburb_inventory                                                                    │
│    { suburb, active_sponsor_count, max_slots (2), active_trainer_ids, waitlist_queue: [   │
│      { trainer_id, joined_at, offer_sent_at, offer_expires_at, status }                   │
│    ], last_vacancy_opened_at, updated_at }                                                │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. db.delisted_entities (Scraper Suppression Table)                                       │
│    { abn, normalized_phone, website_domain, delisted_at, reason, delisted_by }            │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. db.match_events                                                                        │
│    { id, query_text, dog_age, dog_issue, suburb, method_pref, result_ids, scores,         │
│      campaign, source, session_id, created_at }                                           │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 7. db.intros                                                                              │
│    { id, match_id, trainer_id, user_name, user_email, user_phone, description, suburb,    │
│      consent_contact_release, relay_email, relay_expires_at (30d), acknowledged_at,       │
│      status, created_at }                                                                 │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 8. db.conversions                                                                         │
│    { id, intro_id, trainer_id, outcome (hired/deciding/other), confirmed_at, source }        │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 9. db.stripe_events (Webhook Idempotency & Replay Protection)                             │
│    { stripe_event_id, event_type, processed_at, payload_summary }                         │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 10. db.audit_log (Immutable System Ledger)                                                │
│    { id, action, target, before, after, actor (system/trainer/operator), ts }             │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

*Key Ingestion & Hygiene Fields on `db.trainers`:*
- `unmapped_tags` `[String]`: Quarantines extracted industry terms that do not match canonical DTD taxonomy (e.g. "K9 Life Coach", "Puppy Schooler") to prevent corrupting public search filters while preserving raw source nuance.
- `last_scraped_at` `ISO8601 Timestamp`: Records the timestamp of the last successful crawler sweep. Drives the 180-day unclaimed profile recheck loop to detect closures, dead domains, or disconnected phone numbers.
- `details_confirmed_at` `ISO8601 Timestamp`: Records when a claimed profile owner last verified or updated their business facts. Drives the rolling 12-month reconfirmation email loop via Resend.

### 8.2 Database Indexing & Performance Plan
To ensure sub-millisecond query responses across ~300 suburbs and 1,000+ trainer records:
1. `db.trainers.create_index([("slug", 1)], unique=True)`
2. `db.trainers.create_index([("suburb", 1), ("tier", 1), ("outcome_score", -1)])`
3. `db.trainers.create_index([("sponsored_suburbs", 1), ("tier", 1)])`
4. `db.trainers.create_index([("claim_status", 1)])`
5. `db.trainers.create_index([("abn", 1)])`
6. `db.abn_cache.create_index([("abn", 1)], unique=True)`
7. `db.suburb_inventory.create_index([("suburb", 1)], unique=True)`
8. `db.delisted_entities.create_index([("normalized_phone", 1), ("website_domain", 1)])`
9. `db.stripe_events.create_index([("stripe_event_id", 1)], unique=True)`

### 8.3 Edge-Case Engineering Contracts
* **Delisting / Re-ingestion Prevention**: When a trainer delists, their phone, domain, and ABN are recorded in `db.delisted_entities`. Background ingestion checks this table before evaluating or publishing any candidate profile.
* **Ownership Dispute Protocol**: If a second party attempts to claim an already-claimed profile, status locks to `CLAIM_DISPUTED` and routes to `/ops` for ASIC extract or identity verification.
* **Masked Relay Email Expiration**: Masked lead proxy addresses (`lead-xxx@dogtrainersdirectory.com.au`) expire automatically after 30 days of inactivity.
* **Stripe Webhook Idempotency**: Stripe webhook events are deduplicated by checking `db.stripe_events` before applying mutations.

---

## 9. Operator Exception Handling & Bounded Oversight in `/ops`

The operator only acts when an automated threshold is breached:
1. **Unmatched Claim & Dispute Verification (1-Click Action):**
   - Action: Operator views doc preview in `/ops` $\rightarrow$ clicks `[Approve Claim]` or `[Reject]`.
2. **Data Ingestion Anomaly Triage (1-Click Action):**
   - When an ingested profile has conflicting addresses or phone mismatch.
   - Action: Operator clicks `[Merge]` or `[Delist]`.
3. **1-Click Stripe Refunds:**
   - 14-day/30-day money-back guarantee requests executed directly via `/ops` using `stripe.Refund.create()`.
4. **1-Click VIP Founding Partner Grants:**
   - Operator can grant 6–12 months of Pro/Sponsorship to strategic anchor trainers.

---

## 10. Step-by-Step Implementation & Verification Plan

1. **Prune Obsolete Loops & Scaffolding:**
   - Decommission `pricing_loop`, `billing_recovery`, and `claim_state.py`.
   - Remove `PUBLIC_MATCHING_ENABLED=false` blocks from `backend/server.py`.
2. **Build New Pipeline Modules:**
   - Implement `services/claim_engine.py` (OTP verification & dispute locks).
   - Implement `services/suburb_inventory.py` (suburb availability & waterfall succession).
   - Implement `services/deduplication.py` (multi-source deduplication & delisting suppression).
   - Implement `services/abr_client.py` & `services/abn_validator.py` (automated ABN verification).
3. **Refactor Stripe & Notifications:**
   - Upgrade `services/stripe_billing.py` to handle Pro and Suburb Sponsorship subscriptions.
   - Update `services/notifications.py` with the complete transactional template suite.
4. **Wire Clean Schedule in `backend/server.py`:**
   - Expose the 6 authenticated job routes for Google Cloud Scheduler.

---

## 11. 24/7 High-Availability, Automated Backups & Disaster Recovery Architecture

To guarantee unattended commercial 24/7 operation with zero data loss and automated self-healing, the platform implements the following operational safeguards:

### 11.1 Automated Off-Site Database Backup Pipeline
* **Daily Cold Snapshots**: Automated cron triggers `mongodump` daily at 02:00 AEST.
* **Encryption & Off-Site Storage**: Compresses and AES-256 encrypts the BSON archive, uploading directly to an off-site versioned Google Cloud Storage (GCS) Coldline bucket.
* **Retention Schedule**: 7 daily snapshots, 4 weekly snapshots, 12 monthly archives.
* **Target Recovery Metrics**:
  - **RTO (Recovery Time Objective)**: < 30 minutes to restore database from cold snapshot.
  - **RPO (Recovery Point Objective)**: < 24 hours maximum data exposure.

### 11.2 The Worker Process Watchdog (Dead-Man's Switch)
* **External Uptime Heartbeat**: The background loop runner pings an external monitor (Healthchecks.io / Sentry Cron Monitor) every 10 minutes.
* **Silent Failure Detection**: If the worker container freezes or crashes, the external monitor triggers an immediate SMS alert after missing two pings (20 minutes).
* **Loop Isolation**: Each background task in `engine.py` is wrapped in an isolated `try/except` block with exponential backoff so that a single failed iteration never crashes the container.

### 11.3 Transactional Outbox Pattern & Resilient Queues
* **`db.outbox` Decoupling**: All outgoing emails (Resend), SMS OTPs (Firebase Phone Auth), and webhooks (Stripe) are written first to `db.outbox` with status `pending`.
* **Asynchronous Dispatch**: The dispatcher drains the queue every 30 seconds via Cloud Tasks. On third-party outage (HTTP 5xx / timeout), items are retried with exponential backoff up to 72 hours. No client inquiry or OTP is ever lost.
* **ABR Maintenance Degradation**: If ABR Web Services is down for scheduled ATO maintenance, claims enter `CLAIM_PENDING_ABR` without blocking the user, retrying every 2 hours until the registry recovers.

### 11.4 Backend Deep Health & Diagnostic APIs
* `GET /api/health/deep`: Probes MongoDB latency, outbox queue lag, and external API connectivity. Returns HTTP 200 (Healthy) or HTTP 503 (Degraded).
* `POST /api/ops/maintenance-mode`: Emergency circuit breaker to safely display a graceful maintenance screen during major schema migrations.
* `POST /api/ops/outbox/flush`: 1-click administrative queue drain for stuck notifications after an outage.

### 11.5 Automated P1 Emergency Incident Escalation
Google Cloud Monitoring and Sentry trigger immediate P1 alerts (dispatched via SMS and high-priority email) if:
1. MongoDB connectivity is lost for > 2 minutes.
2. Stripe webhook payment processing failure rate exceeds 5%.
3. Outbox queue age exceeds 15 minutes.
4. Directory search or matching returns 0 results across all suburbs for > 15 minutes.
