# DTD Google Cloud Platform (GCP) & Firebase Migration Runbook

**Document Identifier:** `DTD-SPEC-GCP-RUNBOOK-2026`  
**Status:** Canonical Implementation & Architecture Specification (SSOT)  
**Target Environment:** Google Cloud Platform (`australia-southeast1`) & Firebase Multi-Site  
**Active GCP Project:** `gen-lang-client-0028123502` (`dogtrainersdirectory`)  
**Billing Account:** `012AD5-4A21F6-67F052`  
**Date:** September 2026  

> **Acquisition Boundary Contract:**  
> This specification governs runtime hosting, compute, scheduling, authentication, and enrichment infrastructure only. It does **not** authorize persistent trainer discovery via Google Places API or Gemini Search Grounding. All data sourcing, provider rights, and publication gating are strictly governed by [DTD_ACQUISITION_AND_INGESTION_PIPELINE.md](DTD_ACQUISITION_AND_INGESTION_PIPELINE.md).

---

## Table of Contents
1. [Executive Summary & Strategic Rationale](#1-executive-summary--strategic-rationale)
2. [Target System Architecture Topology](#2-target-system-architecture-topology)
3. [Master Service Migration Matrix](#3-master-service-migration-matrix)
4. [Deep Component Technical Specifications](#4-deep-component-technical-specifications)
   - 4.1 [Backend Compute: Google Cloud Run](#41-backend-compute-google-cloud-run)
   - 4.2 [Autonomous Orchestration: Cloud Scheduler + Cloud Tasks](#42-autonomous-orchestration-cloud-scheduler--cloud-tasks)
   - 4.3 [Mobile Verification: Firebase Phone Authentication](#43-mobile-verification-firebase-phone-authentication)
   - 4.4 [Edge Frontend: Firebase Multi-Site Decoupled Hosting](#44-edge-frontend-firebase-multi-site-decoupled-hosting)
   - 4.5 [AI Intelligence: Google Gemini 1.5 Flash (APPs Compliant)](#45-ai-intelligence-google-gemini-15-flash-apps-compliant)
   - 4.6 [Media Storage: Firebase Storage CDN](#46-media-storage-firebase-storage-cdn)
   - 4.7 [Primary Database: MongoDB Atlas (GCP Sydney)](#47-primary-database-mongodb-atlas-gcp-sydney)
5. [The 4 Modular Tasks for Anti-Gravity](#5-the-4-modular-tasks-for-anti-gravity)
6. [The 1-Time User Setup Guide](#6-the-1-time-user-setup-guide)
7. [24/7 Self-Healing Matrix & Disaster Recovery SLA](#7-247-self-healing-matrix--disaster-recovery-sla)
8. [Itemized Financial Forecast & Startup Credit Strategy](#8-itemized-financial-forecast--startup-credit-strategy)

---

## 1. Executive Summary & Strategic Rationale

This specification details the comprehensive consolidation of Dog Trainers Directory (DTD) from fragmented, crash-vulnerable infrastructure (single-server Render containers, standalone Vercel hosting, unmonitored Python asyncio while-loops, paid Twilio SMS) into a unified, enterprise-grade **Google Cloud Platform & Firebase Ecosystem**.

### The 4 Core Architectural Pillars
1. **24/7 Autonomous High Availability**: Replaces fragile single-process background loops (`backend/worker.py`) with managed **Google Cloud Scheduler** (authenticated cron triggers) and **Google Cloud Tasks** (transactional outbox queue with exponential backoff and dead-letter queueing), guaranteeing zero silent process deaths and zero lost client leads.
2. **Auto-Healing Serverless Compute**: Deploys containerized FastAPI to **Google Cloud Run** in Sydney (`australia-southeast1`), delivering sub-30ms latency across Melbourne, automatic container restart in $<2\text{s}$ upon any unhandled exception/OOM, and automatic scale-to-zero when idle ($0 idle compute cost).
3. **Friction-Free Mobile Verification**: Replaces per-SMS Twilio costs with **Firebase Phone Authentication**, providing **10,000 free SMS OTP verifications per month** for Australian mobile numbers (`+61 4xx xxx xxx`) with built-in reCAPTCHA bot defense.
4. **Decoupled Multi-Site Edge Delivery**: Unifies the main directory React SPA (`dogtrainersdirectory.com.au`) and the education handbook (`learn.dogtrainersdirectory.com.au`) under **Firebase Multi-Site Hosting**, preserving independent repository build chains (CRACO/Webpack vs Vite 6) while sharing a single SSL certificate and billing dashboard.

---

## 2. Target System Architecture Topology

```
                                SYSTEM ARCHITECTURE TOPOLOGY
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                 GOOGLE CLOUD & FIREBASE CORE                              │
├──────────────────────────┬──────────────────────────┬─────────────────────────────────────┤
│ 1. EDGE & FRONTEND       │ 2. COMPUTE & QUEUES      │ 3. DATA, AI & OBSERVABILITY         │
│ • Firebase Hosting       │ • Google Cloud Run       │ • Google Gemini API (1.5 Flash)     │
│   - dogtrainersdirectory │   - Containerized FastAPI│   - Structured Fact Extraction      │
│   - learn subdomain      │   - Port 8080, <30ms ping│   - Diagnostic Match Fit            │
│ • Firebase Phone Auth    │ • Cloud Scheduler        │ • Google Maps Platform              │
│   - 10,000 Free SMS/mo   │   - Authenticated Crons  │   - Permitted client UX only        │
│   - +61 AU Mobile Only   │ • Cloud Tasks            │ • Google Cloud Monitoring           │
│ • Firebase Storage       │   - Transactional Outbox │   - 24/7 External Edge Uptime Checks│
│   - Trainer media CDN    │   - 72h Exponential Retry│   - P1 SMS & Push Alerting          │
└────────────┬─────────────┴────────────┬─────────────┴───────────────────┬─────────────────┘
             │                          │                                 │
             ▼                          ▼                                 ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                            RETAINED SPECIALIST EXTERNAL SERVICES                          │
│ • Stripe Australia: Subscriptions ($19/$39/$199 AUD), Invoices & Google Pay wallet        │
│ • ABR Web Services: Statutory Australian Government ABN Validation (ATO API)              │
│ • Resend: Transactional Email Relay (DKIM/SPF Verified on dogtrainersdirectory.com.au)    │
│ • MongoDB Atlas: Primary Document Store (Hosted in GCP Sydney australia-southeast1)      │
│ • Sentry: Deep Python & React Exception Stack-Trace Tracking                              │
│ • PostHog: Client-side event analytics & user session replay                              │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Master Service Migration Matrix

| Subsystem | Legacy / Previous Plan | Target Google Solution | Action | Architectural Justification |
| :--- | :--- | :--- | :---: | :--- |
| **Backend Compute** | Render (`dtd-api`) | **Google Cloud Run** | 🔄 **MIGRATE** | Auto-healing container. Replaces sleeping Render instances. Scales to zero when idle ($0 cost), auto-replaces crashed pods in $<2$s. |
| **Background Loops**| `worker.py` asyncio loop | **Cloud Scheduler + Tasks** | 🔄 **MIGRATE** | Eliminates single-point-of-failure worker script. Cloud Tasks provides native retries, rate limits, and dead-letter queues. |
| **SMS OTP Auth** | Twilio / MessageMedia | **Firebase Phone Auth** | 🔄 **MIGRATE** | Eliminates per-SMS toll costs. Includes 10,000 free Australian mobile SMS verifications per month, built-in reCAPTCHA, and anti-toll-fraud limits. |
| **Frontend Hosting**| Vercel | **Firebase Multi-Site** | 🔄 **MIGRATE** | Eliminates Vercel commercial license requirement. Deploys main directory and education hub under single project with zero custom domain pricing. |
| **AI Intelligence** | Regex keyword scoring | **Google Gemini 1.5 Flash** | 🔄 **MIGRATE** | Sub-second structured JSON parsing of lawful source data and diagnostic matching. APPs compliant (zero prompt training on Pay-As-You-Go). |
| **Media Storage** | Cloudinary / AWS S3 | **Firebase Storage (GCS)** | 🔄 **MIGRATE** | Direct client uploads via Firebase SDK, 5 GB free storage, unified Google Cloud billing. |
| **Uptime Watchdog** | Internal `system_state` | **Cloud Monitoring** | 🔄 **MIGRATE** | 24/7 automated external uptime health checks from 3 global regions. P1 SMS/email alerts on downtime. |
| **Payments / SaaS** | Stripe Australia | **Stripe Australia (Kept)** | 🛡️ **RETAIN** | Google has no B2B recurring SaaS subscription engine. Stripe handles Australian GST invoices, credit card vaulting, and Google Pay wallet. |
| **Government ABN** | ABR Web Services | **ABR Web Services (Kept)** | 🛡️ **RETAIN** | Official statutory ATO business register; no commercial cloud equivalent exists. |
| **Transactional Email**| Resend | **Resend (Kept)** | 🛡️ **RETAIN** | Google Cloud has no native transactional email service. Resend is already DNS/DKIM verified on `dogtrainersdirectory.com.au`. |
| **Primary Database**| MongoDB Atlas | **MongoDB Atlas (Kept)** | 🛡️ **RETAIN** | Prevents weeks of rewrite delay. Atlas connects directly to Cloud Run over GCP Sydney (`australia-southeast1`) with sub-millisecond latency. |
| **Diagnostics** | Sentry | **Sentry (Kept)** | 🛡️ **RETAIN** | Unmatched Python/React deep stack trace diagnostics; paired with Google Cloud Monitoring for infra alerts. |

---

## 4. Deep Component Technical Specifications

### 4.1 Backend Compute: Google Cloud Run
* **Runtime**: Multi-stage container running Python 3.11 / FastAPI with Uvicorn.
* **Region**: `australia-southeast1` (Sydney) for $<30\text{ms}$ latency across Melbourne.
* **Auto-Scaling Configuration**:
  - `min-instances`: `0` (scales to zero when idle at night; $0 compute cost).
  - `max-instances`: `10` (absorbs sudden traffic spikes).
  - `concurrency`: `80` concurrent requests per container.
  - `memory`: `512 MiB`, `cpu`: `1`.
* **Health Probes**:
  - **Liveness Probe**: `GET /api/health` checked every 15s.
  - **Readiness Probe**: `GET /api/health/deep` verifying database connectivity and outbox queue health before routing traffic.
* **Database Connection Pool Guardrail**:
  - Motor / PyMongo client must explicitly set `maxPoolSize=15` and `minPoolSize=1`.
  - With Cloud Run scaling to 10 instances, maximum concurrent TCP connections peak at 150, safely below MongoDB Atlas M0's ceiling of 500 connections.
* **Production Dockerfile (`backend/Dockerfile`)**:
  ```dockerfile
  FROM python:3.11-slim as builder

  WORKDIR /app
  RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

  COPY requirements.txt .
  RUN pip install --no-cache-dir --user -r requirements.txt

  FROM python:3.11-slim
  WORKDIR /app
  COPY --from=builder /root/.local /root/.local
  ENV PATH=/root/.local/bin:$PATH
  ENV PYTHONUNBUFFERED=1

  COPY . .

  # Cloud Run injects PORT (default 8080)
  ENV PORT=8080
  EXPOSE 8080

  CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers 2
  ```

### 4.2 Autonomous Orchestration: Cloud Scheduler + Cloud Tasks
Replaces the unmonitored `backend/worker.py` while-loop with managed HTTP triggers:

| Autonomous Engine | Cadence | Trigger Endpoint | Action |
| :--- | :--- | :--- | :--- |
| **Engine 1: Ingestion & Deduplication** | Per source contract | `POST /api/internal/jobs/ingest` | Processes approved feed, normalizes entities, enforces suppression, applies quality gate. |
| **Engine 2: Ranking & Reputation** | Every 5 minutes | `POST /api/internal/jobs/rank` | Recomputes composite tiered ranking across Melbourne and suburb hubs. |
| **Engine 3: Suburb Vacancy & Succession**| Every 15 minutes | `POST /api/internal/jobs/inventory`| Audits 2-slot caps and dispatches 48h priority links to waitlists. |
| **Engine 4: Outcome Outreach & Reviews** | Hourly | `POST /api/internal/jobs/outreach` | Sweeps T+7 outcome follow-ups and T+14 verified review invitations. |
| **Engine 5: Verification & Staleness** | Every 12 hours | `POST /api/internal/jobs/verify` | Re-verifies ABNs via ABR API and flags dead domains. |

* **True Scale-to-Zero Guardrail**: 60-second internal health crons are **strictly prohibited** in Cloud Scheduler. Frequent 60s pings keep Cloud Run containers perpetually active. System health checks are instead offloaded to **Google Cloud Monitoring external uptime probes** (external edge nodes, zero container compute overhead).
* **Cloud Tasks Transactional Outbox (`dtd-outbox-queue`)**:
  - When an owner submits an inquiry, the backend writes to `db.intros` and queues a task to Cloud Tasks.
  - Retry Policy: 10 attempts, exponential backoff (10s to 1h), maximum retention 72 hours.
  - Ensures zero client leads or notification emails are lost during third-party email outages.
* **Security**: Internal job endpoints enforce Cloud Run Native IAM or check an `X-Cloud-Scheduler-Secret` header, rejecting public internet traffic.

### 4.3 Mobile Verification: Firebase Phone Authentication
* **Client Implementation**: Integrated into `frontend/src/pages/TrainerDetail.jsx` using `@firebase/auth` and `input-otp`.
* **Country Restriction**: Restrict SMS delivery strictly to `+61` (Australia) in the Firebase Console to prevent international SMS toll-fraud bots.
* **Firebase App Check**: Enable App Check on the web client with reCAPTCHA Enterprise to verify legitimate browser requests and protect the 10,000 monthly free SMS quota.
* **Email Fallback**: Provide automated email OTP fallback via Resend if a trainer's carrier filters virtual SMS.

### 4.4 Edge Frontend: Firebase Multi-Site Decoupled Hosting
* **Architecture Strategy (Decoupled Dual-Repo)**:
  - **Target 1: `dogtrainersdirectory.com.au` (and `www`)**: Serves the main directory React SPA built with CRACO/Tailwind v3 (`dtd/frontend`). Configured in `dtd/firebase.json`.
  - **Target 2: `learn.dogtrainersdirectory.com.au`**: Serves The First Leash education platform built with Vite 6/Tailwind v4 (`DTD-education-extended`). Configured in `DTD-education-extended/firebase.json` under target `learn`.
  - **Isolation Benefit**: Eliminates build and dependency conflicts (CRACO/Webpack vs Vite 6, Tailwind v3 vs v4). Both deploy independently under the same Google Cloud / Firebase project (`gen-lang-client-0028123502`).
* **Root `dtd/firebase.json`**:
  ```json
  {
    "hosting": {
      "site": "gen-lang-client-0028123502",
      "public": "frontend/build",
      "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
      "rewrites": [{ "source": "**", "destination": "/index.html" }],
      "headers": [{
        "source": "**/*.@(js|css)",
        "headers": [{ "key": "Cache-Control", "value": "max-age=31536000" }]
      }]
    }
  }
  ```
* **Education `DTD-education-extended/firebase.json`**:
  ```json
  {
    "hosting": {
      "target": "learn",
      "public": "dist",
      "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
      "rewrites": [{ "source": "**", "destination": "/index.html" }]
    }
  }
  ```

### 4.5 AI Intelligence: Google Gemini 1.5 Flash (APPs Compliant)
* **Configuration**: Managed via `backend/services/ai.py` using official `google-genai` SDK.
* **Australian Privacy Principles (APPs) Compliance**:
  - Connected to verified Pay-As-You-Go Google Cloud Billing Account (`012AD5-4A21F6-67F052`).
  - Google's commercial Pay-As-You-Go terms contractually guarantee that prompts and diagnostic intake data are **NEVER logged or used for model training**.
* **Model Choice**: `gemini-1.5-flash` for $<500\text{ms}$ latency and nominal cost ($0.075 USD / 1M input tokens, ~$0.20 AUD/mo).
* **Capabilities**: Structured JSON schema extraction for verified website facts (`training_philosophy`, `specialties`, `service_formats`, `serviced_suburbs`) and multi-variable diagnostic match fit.
* **Dual-Threshold Routing Model ($T_1, T_2$)**:
  - Operates strictly downstream of statutory ABN verification and lawful source validation; AI confidence alone never publishes or verifies a profile.
  - **Confidence $\ge 85\%$ ($T_1$)**: Auto-publish to internal directory search once statutory ABN and minimum-content checks pass.
  - **$50\% \le \text{Confidence} < 85\%$ ($T_2$)**: Route to `/ops` Work Queue for 1-click operator verification.
  - **Confidence $< 50\%$**: Auto-discard and log to quarantine to prevent operator alert fatigue.
* **Sensitive Enum Grounding Tokens (`training_philosophy`)**:
  - Gemini extraction must be cross-verified by strict regex keyword grounding against explicit physical tokens in source text: `"PPG Member"`, `"Force-Free"`, `"LIMA"`, `"IAABC"`, or `"Balanced"`.
  - Ambiguous or ungrounded extractions must fall back to `training_philosophy: null` ("Unspecified"), requiring the trainer to claim and set it directly.

### 4.6 Media Storage: Firebase Storage CDN
* **Storage Location**: `australia-southeast1` (Sydney).
* **Security Rules**: Restrict uploads to authenticated trainers, max file size 5MB, strictly image MIME types (`image/jpeg`, `image/png`, `image/webp`).
* **Free Allowance**: 5 GB storage and 1 GB/day transfer included free.

### 4.7 Primary Database: MongoDB Atlas (GCP Sydney)
* **Zero Rewrite Policy**: The FastAPI backend continues using Motor/PyMongo without schema conversion delays.
* **Latency Optimization**: Cluster is hosted directly in Google Cloud Sydney (`gcp-australia-southeast1`), ensuring private intra-region latency ($<2\text{ms}$) to Cloud Run.
* **Backups**: Continuous automated snapshots with point-in-time recovery.

---

## 5. The 4 Modular Tasks for Anti-Gravity

Execute the migration in 4 self-contained, verifiable tasks:

### Task 1: Google Gemini API Client Integration & Dual-Threshold Routing (formerly Task 3 in 5-task spec)
* **Target File:** `backend/services/ai.py`
* **Action:** Replace regex heuristics with `gemini-1.5-flash` using `GEMINI_API_KEY` (Pay-As-You-Go tier). Implement:
  1. **Dual-Threshold Routing ($T_1, T_2$)**: Route extracted candidates based on diagnostic confidence: $\ge 85\%$ ($T_1$) to internal directory search (post-ABN check), $50\% \le \text{Score} < 85\%$ ($T_2$) to `/ops` 1-click verification queue, and $<50\%$ to quarantine/discard log.
  2. **Strict Regex Grounding for `training_philosophy`**: Cross-verify extraction against explicit physical tokens (`"PPG Member"`, `"Force-Free"`, `"LIMA"`, `"IAABC"`, `"Balanced"`); fall back to `null` ("Unspecified") when ambiguous.
  3. **Safety Boundary**: Enforce that AI confidence alone never publishes or verifies a profile; publication strictly requires separately verified statutory ABN and lawful source evidence.
* **Exit Gate:** `pytest backend/tests/test_ai_scoring.py` passes with valid structured JSON extraction, dual-threshold routing, and regex grounding test cases.

### Task 2: Firebase Phone Auth for Profile Claiming
* **Target File:** `frontend/src/pages/TrainerDetail.jsx`
* **Action:** Wire up Firebase Phone Auth SDK (`RecaptchaVerifier` + `signInWithPhoneNumber`) to `input-otp` modal, enforcing AU `+61` mobile format with Resend email fallback.
* **Exit Gate:** Entering an Australian mobile number dispatches an SMS OTP and updates claim status.

### Task 3: Firebase Hosting Multi-Site Verification
* **Target Files:** `dtd/firebase.json`, `DTD-education-extended/firebase.json`
* **Action:** Verify independent build and deployment targets under Firebase project `gen-lang-client-0028123502`:
  - `dtd/frontend` deploys to default site: `firebase deploy --only hosting`
  - `DTD-education-extended` deploys to target `learn`: `firebase deploy --only hosting:learn`
* **Exit Gate:** Both sites compile cleanly and deploy to their respective domain targets.

### Task 4: Google Cloud Run Containerization & Health Endpoints
* **Target Files:** `backend/Dockerfile`, `backend/server.py`
* **Action:** Build multi-stage Dockerfile on port 8080, configure Motor connection pool (`maxPoolSize=15`), and implement `GET /api/health/deep`.
* **Exit Gate:** Container builds locally and responds `200 OK` on health probe.

---

## 6. The 1-Time User Setup Guide

Complete these 3 steps in the Firebase Console:

1. **Verify Firebase Project**:
   - Access project `gen-lang-client-0028123502` at [console.firebase.google.com](https://console.firebase.google.com).
2. **Create Secondary Hosting Site (`dtd-first-leash`)**:
   - In the Firebase Console, navigate to **Build → Hosting**.
   - Under the Dashboard, click **"Add another site"**.
   - Set Site ID: `dtd-first-leash` (serves `learn.dogtrainersdirectory.com.au`).
3. **Enable Phone Authentication**:
   - Navigate to **Build → Authentication → Sign-in method**.
   - Click **Phone** → Toggle **Enable** → Restrict to Australia (`+61`) → Click **Save**.

---

## 7. 24/7 Self-Healing Matrix & Disaster Recovery SLA

```
                           24/7 SELF-HEALING MATRIX
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ FAILURE SCENARIO                             │ AUTOMATED RECOVERY BEHAVIOR                  │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 1. Cloud Run container crashes (OOM/error)   │ Cloud Run terminates container and spins up  │
│                                              │ a healthy replacement in <2 seconds.         │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 2. Background Loop Fails                     │ Cloud Scheduler retries the HTTP request;    │
│                                              │ Cloud Tasks retries with exponential backoff │
│                                              │ for up to 72 hours before hitting DLQ.       │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 3. Resend Email Outage                       │ Leads are saved to `db.intros` and queued in │
│                                              │ Cloud Tasks; auto-drained when Resend is up. │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 4. ABR Government API Maintenance            │ Claim enters `CLAIM_PENDING_ABR`; background │
│                                              │ loop retries every 2h automatically.         │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 5. Bad Deployment Revision                   │ Health probe failure triggers automatic      │
│                                              │ rollback to previous healthy Cloud Run rev.  │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 6. Catastrophic Database Loss                │ Automated daily snapshot restored to fresh   │
│                                              │ cluster (RTO < 30 min, RPO < 24h).           │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

* **Recovery Time Objective (RTO)**: $<15\text{ minutes}$ for container redeployment; $<30\text{ minutes}$ for database restoration.
* **Recovery Point Objective (RPO)**: $<24\text{ hours}$ maximum data loss threshold.

---

## 8. Itemized Financial Forecast & Startup Credit Strategy

| Platform / Service | Free Allowance / Model | Launch Cost (Mo 1–3) | Mature Market (Mo 7–12+) |
| :--- | :--- | :---: | :---: |
| **Google Cloud Run** | 2M requests/mo free | **$0.00 AUD** | **~$25.00 AUD** |
| **Cloud Scheduler & Tasks** | 3 jobs free; 1M tasks free | **~$0.45 AUD** | **~$2.00 AUD** |
| **Firebase Hosting (Multi-Site)** | 10 GB storage free | **$0.00 AUD** | **~$5.00 AUD** |
| **Firebase Phone Auth** | **10,000 free SMS/month** | **$0.00 AUD** | **$0.00 AUD** |
| **Google Gemini 1.5 Flash** | 1,500 req/day free tier | **$0.00 AUD** | **~$3.00 AUD** |
| **Google Maps Platform** | **$200 USD/mo recurring credit** | **$0.00 AUD** | **$0.00 AUD** |
| **MongoDB Atlas** | M0 free cluster (GCP Sydney) | **$0.00 AUD** | **~$85.00 AUD** *(M10 PITR)* |
| **Resend Email** | 3,000 emails/mo free | **$0.00 AUD** | **~$30.00 AUD** |
| **Domain (.com.au)** | $20 AUD / year | **~$1.70 AUD** | **~$1.70 AUD** |
| **Stripe Australia** | 1.75% + $0.30 per AU sale | **$0 fixed** | **Variable (from sales)** |
| **TOTAL FIXED RUNNING COST** | | **~$2.15 AUD / month** | **~$151.70 AUD / month** |

### Google for Startups Credit Accelerator
Upon deployment on Google Cloud, DTD qualifies for the **Google for Startups Cloud Program**:
* **Initial Grant**: **$2,000 USD (~$3,000 AUD)** in Google Cloud credits valid for 2 years.
* **Coverage**: Directly offsets Cloud Run, Cloud Tasks, Cloud Scheduler, Gemini API tokens, and Firebase Storage.
* **Financial Bottom Line**: Fixed infrastructure operating costs are **$0.00 AUD/month for the first 12 to 24 months**.
