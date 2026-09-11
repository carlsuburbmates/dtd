# DTD Google Ecosystem Migration, 24/7 Reliability & Seeding Architecture Specification

**Status:** Canonical Engineering Specification & Migration Blueprint  
**Date:** 2026-09-11  
**Location Scope:** Greater Melbourne, Victoria, Australia  
**File Path:** `docs/strategy/DTD_GOOGLE_ECOSYSTEM_MIGRATION_AND_ARCHITECTURE_SPEC.md`

> **Acquisition boundary:** This document governs Google runtime migration, not
> trainer-source rights. `DTD_ACQUISITION_AND_INGESTION_PIPELINE.md` governs all
> discovery and ingestion. Google Places/Maps content and Gemini Search
> Grounding are not persistent acquisition sources. The preferred post-launch
> discovery direction is a separately licensed Sensis/Thryv API/feed, currently
> awaiting written rights and an implementable interface.

---

## Table of Contents
1. [Executive Summary & Migration Posture](#1-executive-summary--migration-posture)
2. [Component-by-Component Mapping: What Moves to Google vs. What Stays](#2-component-by-component-mapping-what-moves-to-google-vs-what-stays)
3. [Verification & Integration of the NotebookLM Seeding Pipeline](#3-verification--integration-of-the-notebooklm-seeding-pipeline)
4. [24/7 High-Availability, Self-Healing & Disaster Recovery on GCP](#4-247-high-availability-self-healing--disaster-recovery-on-gcp)
5. [Anti-Gravity Implementation Runbook: Modular Tasks](#5-anti-gravity-implementation-runbook-modular-tasks)
6. [Complete Cost Forecast & Startup Credit Strategy](#6-complete-cost-forecast--startup-credit-strategy)

---

## 1. Executive Summary & Migration Posture

This document formalizes the strategic decision to migrate Dog Trainers Directory's runtime environment, task scheduling, authentication, and intelligence to the **Google Cloud Platform (GCP) and Firebase ecosystem**, while preserving DTD's core database models and specialist integrations.

### 1.1 The Core Strategic Objectives
1. **Solve 24/7 Autonomous Reliability:** Replace fragile single-server processes (Render containers, long-running Python asyncio while-loops) with Google Cloud Run (auto-scaling, self-healing containers) and Google Cloud Tasks/Scheduler (guaranteed message delivery and cron execution).
2. **Eliminate Operational Tool Noise:** Consolidate hosting, mobile SMS authentication, task scheduling, media storage, AI parsing, and geocoding under a single Google Cloud project and unified billing account.
3. **Zero-Delay Hybrid Migration (No Database Rewrite):** Keep the existing Python FastAPI application and MongoDB Atlas database (hosted in GCP Sydney `australia-southeast1`), preventing the weeks-long launch delays associated with rewriting to Firestore or relational SQL.
4. **Leverage Non-Dilutive Capital:** Qualify for the Google for Startups Cloud Program ($2,000 to $200,000 USD in cloud and AI credits), reducing early-stage compute, maps, and AI costs to $0.

---

## 2. Component-by-Component Mapping: What Moves to Google vs. What Stays

```
                           THE DTD GOOGLE-POWERED ECOSYSTEM
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                              GOOGLE CLOUD & FIREBASE RUNTIME                              │
├──────────────────────────┬──────────────────────────┬─────────────────────────────────────┤
│ FRONTEND & EDGE          │ COMPUTE & SCHEDULING     │ DATA & INTELLIGENCE                 │
│ • Firebase Hosting       │ • Google Cloud Run       │ • Google Gemini API (1.5 Flash)     │
│   (Main & Learn domains) │   (FastAPI Container)    │   (Ingestion & Diagnostic Matching) │
│ • Firebase Phone Auth    │ • Cloud Scheduler        │ • Google Maps Platform              │
│   (Australian SMS OTPs)  │   (Managed Cron Triggers)│   (Permitted Maps UX only)          │
│ • Firebase Storage       │ • Cloud Tasks            │ • Cloud Monitoring                  │
│   (Trainer photo CDN)    │   (Transactional Outbox) │   (24/7 Uptime Pings & P1 Alerts)   │
└────────────┬─────────────┴────────────┬─────────────┴──────────────────┬──────────────────┘
             │                          │                                │
             ▼                          ▼                                ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                       IRREPLACEABLE SPECIALIST INTEGRATIONS (KEPT)                        │
│ • Stripe Australia: Recurring subscriptions ($19, $39, $199 AUD), ABN tax invoices, dunning│
│ • ABR Web Services: Statutory Australian Government ABN validation (ATO API)              │
│ • Resend: Transactional email delivery with verified DNS/DKIM on dogtrainersdirectory.com.au│
│ • MongoDB Atlas: Existing document store running in GCP Sydney (australia-southeast1)    │
│ • Sentry: Application-level Python stack trace capture & telemetry                        │
│ • PostHog: Client-side event analytics & user session replay                              │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Detailed Component Justifications

| Subsystem | Legacy / Previous Plan | New Google Solution | Decision | Architectural Justification |
| :--- | :--- | :--- | :---: | :--- |
| **Backend Compute** | Render Web Service (`dtd-api`) | **Google Cloud Run** | 🔄 **CHANGE** | Auto-healing container environment. Replaces sleeping Render instances. Scales to zero when idle ($0 cost), auto-replaces crashed pods in $<2$s. |
| **Background Loops** | Custom `worker.py` asyncio loop | **Cloud Scheduler + Cloud Tasks** | 🔄 **CHANGE** | Eliminates the single-point-of-failure worker script. Cloud Tasks provides native retries, rate limits, and dead-letter queues (DLQ). |
| **SMS OTP Verification** | Twilio / MessageMedia | **Firebase Phone Authentication** | 🔄 **CHANGE** | Eliminates per-SMS toll costs. Includes 10,000 free Australian mobile SMS verifications per month, built-in reCAPTCHA, and anti-abuse limits. |
| **Web Hosting** | Vercel | **Firebase Hosting** | 🔄 **CHANGE** | Unifies the main directory (`dogtrainersdirectory.com.au`) and education (`learn.dogtrainersdirectory.com.au`) under one project with zero custom domain pricing. |
| **AI Intelligence** | Regex keyword scoring | **Google Gemini API (`gemini-1.5-flash`)** | 🔄 **CHANGE** | Sub-second structured JSON parsing of raw public web data and multi-variable diagnostic matching. Covers token costs via startup credits. |
| **Media CDN** | Cloudinary / AWS S3 | **Firebase Storage / Cloud Storage** | 🔄 **CHANGE** | Direct client uploads via Firebase SDK, 5 GB free storage, unified Google Cloud billing. |
| **Uptime & Incident Alerts** | Internal `system_state` only | **Google Cloud Monitoring** | 🔄 **CHANGE** | 24/7 automated external uptime health checks. Dispatches immediate alerts if HTTP status drops below 200. |
| **Payments & Invoicing** | Stripe Australia | **Stripe Australia (with Google Pay)** | 🛡️ **KEEP** | Google has no B2B recurring SaaS billing engine. Stripe remains the global standard for subscriptions, tax invoices, and customer portals. |
| **ABN Government Validation**| ABR Web Services | **ABR Web Services (ATO)** | 🛡️ **KEEP** | Official Australian federal statutory register; no commercial cloud equivalent exists. |
| **Transactional Email** | Resend | **Resend** | 🛡️ **KEEP** | Google Cloud has no native transactional email service (partners with SendGrid/Mailgun). Resend is already DNS/DKIM verified. |
| **Primary Database** | MongoDB Atlas | **MongoDB Atlas (GCP Sydney)** | 🛡️ **KEEP** | Prevents weeks of rewrite delay. Atlas connects directly to Cloud Run over GCP's Sydney network with sub-millisecond latency. |
| **Error Diagnostics** | Sentry | **Sentry** | 🛡️ **KEEP** | Unmatched Python/React deep stack trace diagnostics; paired with Google Cloud Monitoring for infra alerts. |

---

## 3. Verification & Integration of the NotebookLM Seeding Pipeline

The research retrieved from NotebookLM outlines a battle-tested **Discovery & Seeding Acquisition Pipeline** for local directories. We formally verify, endorse, and adopt its core principles into DTD.

### 3.1 Verification Analysis of the NotebookLM Research
* **Core Seeding Principle (Do Not Launch Empty):** Retained. DTD launches with its accepted attributable baseline and trainer-submission path; expansion toward 100+ profiles proceeds after launch through the separately approved licensed-feed pipeline.
* **5-Stage Pipeline Sequence:** Verified. Standard manual copy-pasting creates dirty, inconsistent data. Running public data through a governed, multi-stage pipeline guarantees structural uniformity.
* **Deterministic Taxonomy Alignment:** Verified. Ingestion pipelines must never invent categories dynamically (e.g. creating "K9 Coach" or "Puppy Schooler"). All scraped tags must map to DTD's strict canonical taxonomy.
* **Data Model Separation (`Seeded` vs. `Claimed`):** Verified. Inventory discovery must be structurally decoupled from owner account relationships.

---

### 3.2 Governed Acquisition And Ingestion Pipeline

The complete and controlling workflow is
`docs/strategy/DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`:

`approved source -> evidence capture -> factual extraction -> optional Gemini structuring -> ABR/geographic checks -> canonical dedupe and suppression -> evidence-based publish or hold -> /ops`

The accepted launch batch uses approved official trainer websites and ABR. The
post-launch discovery input is intended to be a licensed Sensis/Thryv API or
feed, but supplier rights and an interface are still pending. Google Places and
Gemini Search Grounding do not perform persistent discovery. Gemini confidence
alone never publishes a listing.

---

### 3.3 Data Model Separation: `Seeded` vs. `Claimed` Schema

In accordance with the NotebookLM research, the `Trainer` schema in MongoDB (`db.trainers`) strictly decouples inventory discovery from owner accounts:

```json
{
  "_id": "tr_melb_k9_richmond",
  "slug": "k9-balance-richmond",
  "name": "K9 Balance Dog Training",
  "trading_name": "K9 Balance Melbourne",
  
  "/* Ingestion & Discovery Metadata */": "",
  "is_seeded": true,
  "listing_source": "google_places_api",
  "source_record_id": "ChIJN1t_tDe1EmsRUsoyG83frY4",
  "details_confirmed_at": null,
  "confidence_score": 0.92,
  
  "/* Spatial Coordinates */": "",
  "suburb": "Richmond",
  "postcode": "3121",
  "region": "Inner East",
  "location": {
    "type": "Point",
    "coordinates": [144.9982, -37.8230]
  },
  "serviced_suburbs": ["Richmond", "Burnley", "Cremorne", "South Yarra"],
  "catchment_type": "hyper_local",

  "/* Entity Identity & Verification */": "",
  "abn": "51824753556",
  "abn_status": "Active",
  "abn_verified": true,
  "phone": "+61412345678",
  "email": "info@k9balance.com.au",
  "website": "https://k9balance.com.au",

  "/* Deterministic Taxonomy */": "",
  "training_philosophy": "Positive Reinforcement / Force-Free",
  "specialties": ["puppy_training", "leash_reactivity"],
  "service_formats": ["in_home", "one_on_one"],

  "/* Owner Relationship & Monetization */": "",
  "claim_status": "unclaimed",
  "claimed_by_user_id": null,
  "claimed_at": null,
  "tier": "basic",
  "sponsored_suburbs": [],
  "published": true
}
```

---

### 3.4 The Anchor Business Outreach Strategy (Melbourne Execution)

Once the initial 100 listings are seeded, we convert passive inventory into active platform relationships using the **Launch Selection Playbook**:

1. **Selection Criteria**: Identify 10–15 high-reputation, well-reviewed trainers across key Melbourne quadrants (e.g. Richmond, Brunswick, Brighton).
2. **Value-First "Launch Selection" Outreach (Email / DM)**:
   > *"Hi [Trainer Name],*  
   > *We are launching Dog Trainers Directory—an independent, curated Melbourne guide connecting dog owners with vetted, method-transparent local professionals.*  
   > *We have selected [Business Name] as one of our featured launch listings for [Suburb]. Your business profile is live and receiving local search traffic:*  
   > *[Link to https://dogtrainersdirectory.com.au/t/your-slug]*  
   > *We invite you to review your free profile and verify that your service formats, methods, and contact details are accurate so local owners can reach you directly.*  
   > *Warm regards,*  
   > *The DTD Melbourne Team"*
3. **Social Proof Leverage**: Once anchor trainers verify their profiles, their public confirmation establishes peer credibility, accelerating organic claims across Melbourne.

---

## 4. 24/7 High-Availability, Self-Healing & Disaster Recovery on GCP

Migrating compute and task orchestration to Google Cloud closes all 5 production resilience gaps:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Google Cloud Run (Container Auto-Healing)                                │
│ • Auto-Restart: If the FastAPI container hits an unhandled exception or OOM,│
│   Cloud Run terminates it and spins up a healthy replacement in < 2 seconds.│
│ • Health Probe: Configured with `livenessProbe: /api/health` and             │
│   `startupProbe: /api/health`.                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Cloud Tasks & Transactional Outbox (Guaranteed Delivery)                 │
│ • Asynchronous Outbox: Emails (Resend) and SMS OTPs (Firebase Auth) are     │
│   enqueued to Cloud Tasks.                                                  │
│ • Automatic Exponential Retries: If an external API is down, Cloud Tasks    │
│   retries over 72 hours with exponential backoff and dead-letter queue (DLQ)│
│   logging. Zero customer leads or OTPs are lost.                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Cloud Scheduler (Managed Background Jobs)                                │
│ • Replaces `worker.py` loops with HTTP webhook triggers to Cloud Run:       │
│   - `POST /api/jobs/ranking` (Every 5 minutes)                              │
│   - `POST /api/jobs/outbox-drain` (Every 1 minute)                          │
│   - `POST /api/jobs/outreach-t7` (Hourly)                                   │
│   - `POST /api/jobs/ingestion` (Every 6 hours)                              │
│   - `POST /api/jobs/abn-verification` (Every 14 days)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. MongoDB Atlas Automated Offsite Backups                                  │
│ • Automated Daily Snapshots: Retained for 30 days via Atlas Cloud Backup.   │
│ • Recovery Targets: RTO (Recovery Time) < 30 mins; RPO (Data Point) < 24h. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. Google Cloud Monitoring (24/7 External Watchdog)                         │
│ • Uptime Checks: Pings `https://dogtrainersdirectory.com.au/api/health`     │
│   every 60 seconds from global locations.                                   │
│ • P1 Alert Escalation: Dispatches automated SMS and email alerts if latency │
│   spikes or errors exceed 5% over 5 minutes.                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Anti-Gravity Implementation Runbook: Modular Tasks

To prevent the AI coding assistant ("Anti-Gravity") from getting overwhelmed or breaking working code, execute the migration across **5 isolated, sequential tasks**:

### Task 1: Containerization & Cloud Run Manifest
* **Mission**: Create a production-ready `Dockerfile` in `backend/` and verify local container execution.
* **Input Files**: `backend/server.py`, `backend/requirements.txt`.
* **Output Artifacts**: `backend/Dockerfile`, `.dockerignore`.
* **Specification**: Multi-stage build based on `python:3.11-slim`, running Uvicorn on port `8080` with `--workers 2`.

### Task 2: Firebase Hosting & Routing Configuration
* **Mission**: Configure Firebase Hosting to serve the React production build and map subdomains.
* **Output Artifacts**: `firebase.json`, `.firebaserc`.
* **Specification**: Single-page application rewrites (`"rewrites": [{"source": "**", "destination": "/index.html"}]`), caching headers for static assets (`/images/**`, `/files/**`), and site targets for `dogtrainersdirectory.com.au` and `learn.dogtrainersdirectory.com.au`.

### Task 3: Google Gemini API Integration (`services/ai.py`)
* **Mission**: Integrate `gemini-1.5-flash` for multi-source ingestion parsing and diagnostic matching.
* **Key Endpoints**: Replace keyword counters with Gemini structured JSON output via `google-genai` SDK using `GEMINI_API_KEY`.

### Task 4: Firebase Phone Auth for Mobile Claiming
* **Mission**: Integrate Firebase Phone Authentication in `frontend/src/pages/TrainerDetail.jsx`.
* **Specification**: Replace mock OTP modal with Firebase Phone Auth SDK (`RecaptchaVerifier` + `signInWithPhoneNumber`), verifying 6-digit SMS codes via the existing `input-otp` component.

### Task 5: Cloud Scheduler & Job Endpoints
* **Mission**: Create secure internal job endpoints in `backend/server.py` protected by `X-CloudScheduler-Key`.
* **Endpoints**:
  - `POST /api/jobs/ranking`
  - `POST /api/jobs/outreach-t7`
  - `POST /api/jobs/suburb-vacancy`
  - `POST /api/jobs/ingestion`

---

## 6. Complete Cost Forecast & Startup Credit Strategy

```
                               MONTHLY COST BREAKDOWN (AUD)
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ PLATFORM / SERVICE           │ PRICING MODEL & FREE TIER    │ ESTIMATED COST (LAUNCH / MO) │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Google Cloud Run**         │ 2M requests/mo free          │ **$0.00** (Under free tier)  │
│ **Cloud Tasks & Scheduler**  │ 1M tasks free; 3 jobs free   │ **~$0.45 AUD**               │
│ **Firebase Hosting**         │ 10 GB storage; 10 GB/mo bandw│ **$0.00** (Under free tier)  │
│ **Firebase Phone Auth**      │ **10,000 free SMS OTPs / mo**│ **$0.00** (Free perpetual)   │
│ **Google Gemini 1.5 Flash**  │ 1,500 free requests / day    │ **~$0.50 AUD**               │
│ **Google Maps Places API**   │ **$200 USD/mo free credit**  │ **$0.00** (Covered by credit)│
│ **MongoDB Atlas (GCP Sydney)│ Free M0 / Serverless         │ **$0.00 - $15.00 AUD**       │
│ **Resend (Email)**           │ Free 3,000 emails / month    │ **$0.00** (Under free tier)  │
│ **Stripe Australia**         │ Zero fixed fee; 1.75% + 30¢  │ **$0 fixed** (Pay-per-sale)  │
│ **ABR Government API**       │ **100% Free** (ATO Gov API)  │ **$0.00** (Free perpetual)   │
│ **.com.au Domain Name**      │ $20 AUD / year               │ **~$1.70 AUD / month**       │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **TOTAL LAUNCH COST**        │                              │ **~$2.65 - $17.00 AUD / mo** │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

### The Google for Startups Credit Accelerator
Upon deployment on Google Cloud, DTD qualifies for the **Google for Startups Cloud Program**:
* **Initial Award**: **$2,000 USD (~$3,000 AUD)** in Google Cloud credits valid for 2 years.
* **Coverage**: Directly offsets Cloud Run compute, Cloud Tasks, Cloud Scheduler, Gemini API tokens, and Firebase Storage.
* **Financial Bottom Line**: Your total infrastructure cost for running DTD 24/7 across Greater Melbourne is **$0 AUD for up to 24 months**.
