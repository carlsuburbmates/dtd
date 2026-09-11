# DTD Google Ecosystem Migration & 24/7 Autonomous Reliability Specification

*Document Identifier:* `DTD-SPEC-GOOGLE-MIGRATION-2026`  
*Target Release:* Greater Melbourne Launch  
*Author:* AI Strategy & Architecture Team  
*Status:* Canonical Target Architecture Specification  
*Governing Documents:* `DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md`, `DTD_AUTOMATION_AND_INTEGRATION_SPEC.md`

> **Acquisition boundary:** Google services remain the runtime and enrichment
> ecosystem, not the persistent listing-discovery source. Follow
> `DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`; Sensis/Thryv remains a pending
> licensed-feed option, and Google Places/Gemini Search Grounding remain excluded
> from autonomous directory acquisition.

---

## 1. Executive Summary & Objective

This document defines the comprehensive engineering and operational roadmap to migrate Dog Trainers Directory (DTD) from a fragmented multi-cloud setup (Vercel, Render, custom long-running Python workers, Twilio) into a unified, enterprise-grade **Google Cloud Platform (GCP) + Firebase** ecosystem.

### Primary Objectives:
1. **24/7 Autonomous High Availability**: Eliminate single-point-of-failure worker crashes by replacing unmonitored Python background loops with managed Google Cloud Scheduler and Cloud Tasks.
2. **Auto-Healing Serverless Compute**: Replace Render with Google Cloud Run (containerized FastAPI with automated health checks, scale-to-zero cost efficiency, and $<2$ second crash recovery).
3. **Friction-Free Australian Mobile Auth**: Replace expensive, high-maintenance Twilio SMS with Firebase Phone Authentication, unlocking 10,000 free monthly SMS OTP verifications for Australian mobile numbers (`+61 4xx xxx xxx`).
4. **Unified Domain & Asset Delivery**: Consolidate main directory hosting (`dogtrainersdirectory.com.au`) and the isolated education hub (`learn.dogtrainersdirectory.com.au`) under high-speed Firebase Hosting edge CDN.
5. **Pragmatic Non-Disruption Boundary**: Retain MongoDB Atlas (hosted directly in Google Cloud Sydney `australia-southeast1`) to eliminate the risk of a multi-week database rewrite before launch.

---

## 2. Master System Topology: Current vs. Target Google Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   TARGET GOOGLE ARCHITECTURE                                     │
├────────────────────────────────┬────────────────────────────────┬────────────────────────────────┤
│ 1. EDGE & CLIENT LAYER         │ 2. COMPUTE & QUEUE LAYER       │ 3. DATA & EXTERNAL APIS        │
│ • Firebase Hosting (Global Edge│ • Google Cloud Run             │ • MongoDB Atlas (GCP Sydney)   │
│   - dogtrainersdirectory.com.au│   - Containerized FastAPI      │   - Existing Document Store    │
│   - learn.dogtrainersdirectory │   - Auto-scaling (0 to 10 inst)│   - Continuous daily snapshots │
│ • Firebase Phone Authentication│   - Port 8080, <30ms VIC ping  │ • Google Gemini 1.5 Flash API  │
│   - 10,000 Free AU SMS OTPs/mo │ • Google Cloud Scheduler       │   - Structured source parser   │
│   - Native reCAPTCHA anti-bot  │   - Replaces custom loops      │   - Diagnostic match fit       │
│ • Firebase / GCS Storage       │   - Authenticated cron webhooks│ • Licensed feed (pending)      │
│   - Trainer photo galleries    │ • Google Cloud Tasks           │   - Trainer discovery contract │
│   - Auto CDN transforms        │   - Managed outbox delivery    │ • ABR Web Services API (ATO)   │
│ • Google Cloud Monitoring      │   - Auto-retries & dead-letter │ • Stripe Australia (Google Pay)│
│   - 24/7 Uptime & SMS pager    │   - Prevents lost lead emails  │ • Resend Transactional Email   │
└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘
```

---

## 3. Service-by-Service Component Architecture

### 3.1 Frontend Hosting (Vercel → Firebase Hosting)
* **Configuration**: Managed via `firebase.json` in the root repository.
* **Multi-Site Architecture**:
  * Site Target 1 (`dtd-main`): Serves `frontend/build` for `dogtrainersdirectory.com.au` and `www`.
  * Site Target 2 (`dtd-learn`): Serves the isolated education artifact for `learn.dogtrainersdirectory.com.au`.
* **SPA Routing**: Automatic single-page-app rewrite rules (`"source": "**", "destination": "/index.html"`).
* **SSL & Caching**: Automatic Google-managed SSL certificates and global SSD edge caching.

### 3.2 Backend Compute (Render → Google Cloud Run)
* **Packaging**: Standard multi-stage container build defined in `backend/Dockerfile`:
  ```dockerfile
  FROM python:3.11-slim as builder
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  EXPOSE 8080
  CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
  ```
* **Region**: `australia-southeast1` (Sydney, low-latency link to Melbourne users).
* **Scaling Rules**:
  * Minimum instances: `0` (scales to zero during overnight inactivity for $0 cost).
  * Maximum instances: `10` (absorbs sudden traffic spikes from media or viral campaigns).
  * Concurrency: `80` requests per container.
* **Health Probes**: Configured to probe `/api/health/deep` every 15 seconds. Unhealthy containers are terminated and replaced automatically in $<2$ seconds.

### 3.3 Autonomous Background Loops (Custom `worker.py` → Cloud Scheduler & Cloud Tasks)
* **The Problem Solved**: Eliminates the risk of a single Python process crashing silently in production.
* **Cloud Scheduler (The Triggers)**:
  * Replaces long-running sleep loops with managed HTTP POST requests to authenticated internal endpoints:
    1. `POST /api/internal/jobs/ingestion` (Every 6 hours)
    2. `POST /api/internal/jobs/ranking` (Every 5 minutes)
    3. `POST /api/internal/jobs/suburb-inventory` (Every 15 minutes)
    4. `POST /api/internal/jobs/outreach-t7` (Hourly)
    5. `POST /api/internal/jobs/verification-staleness` (Every 12 hours)
    6. `POST /api/internal/jobs/health-check` (Every 60 seconds)
  * Authentication: Cloud Scheduler requests sign OIDC bearer tokens validated by `server.py` using Google Auth credentials.
* **Cloud Tasks (The Transactional Outbox & Reliable Dispatcher)**:
  * When an owner requests a consultation, the lead notification email is queued into a Google Cloud Task queue (`dtd-lead-outbox`).
  * Cloud Tasks dispatches the payload to Resend.
  * If Resend returns HTTP 5xx or times out, Cloud Tasks manages exponential backoff retries (up to 72 hours). Zero client leads are ever lost due to downstream provider outages.

### 3.4 Trainer Verification (Twilio SMS → Firebase Phone Authentication)
* **The Problem Solved**: Eliminates Twilio account maintenance, credit pre-funding, and custom SMS rate-limiting logic.
* **Implementation**:
  * Integrated into `frontend/src/pages/TrainerDetail.jsx` using Firebase Web SDK (`signInWithPhoneNumber`).
  * Enforces Australian mobile format (`+61 4xx xxx xxx`).
  * Free Tier: Includes **10,000 free phone verifications every month** under Google Identity Platform.
  * Built-in security: Automatic Google invisible reCAPTCHA prevents automated toll fraud and SMS bombing.

### 3.5 AI Extraction & Diagnostic Matching (Heuristics → Google Gemini 1.5 Flash)
* **Configuration**: Managed via `backend/services/ai.py` using official `google-genai` SDK.
* **Model Choice**: `gemini-1.5-flash` for $<500\text{ms}$ latency and ultra-low cost ($0.075 USD / 1M input tokens).
* **Capabilities**:
  * Structured JSON schema enforcement for raw public website extraction (`training_philosophy`, `specialties`, `service_formats`, `serviced_suburbs`).
  * Transparent diagnostic matching: Evaluates dog age, behavioral issue, and method fit to produce clear plain-English matching rationale for owners.
  * Hard Commercial Neutrality: Commercial tier is stripped from candidate payloads before model evaluation to prevent pay-to-win algorithm bias.

### 3.6 Media Storage (Cloudinary/S3 → Firebase Storage)
* **Configuration**: Cloud Storage for Firebase in `australia-southeast1`.
* **Usage**: Direct authenticated client-side upload from the Trainer Portal for portfolio transformation photos, logos, and business certificates.
* **Free Tier**: 5 GB storage and 1 GB/day download bandwidth included free.

### 3.7 Database Retention (MongoDB Atlas in GCP Sydney)
* **Zero-Rewrite Policy**: The FastAPI backend continues using Motor/PyMongo without modifying any database schemas or queries.
* **Google Cloud Alignment**: MongoDB Atlas cluster is hosted in Google Cloud Sydney (`gcp-australia-southeast1`), ensuring private VPC peering / intra-region low latency ($<2\text{ms}$).
* **Automated Daily Backups**: Atlas automated continuous cloud backup snapshots enabled (7-day point-in-time recovery).

---

## 4. Itemized 3-Phase Financial Forecast & Unit Economics

| Service / Component | Free Tier Allowance | Launch Baseline (Mo 1–3) | Growth Phase (Mo 4–6) | Mature Melbourne (Mo 7–12+) |
| :--- | :--- | :---: | :---: | :---: |
| **Google Cloud Run** | 2M requests, 360k GB-s/mo | **$0.00** | **~$5.00 AUD** | **~$25.00 AUD** |
| **Cloud Scheduler & Tasks** | 3 jobs free; 1M tasks free | **~$0.45 AUD** | **~$0.50 AUD** | **~$2.00 AUD** |
| **Firebase Hosting** | 10 GB storage, 10 GB/mo transfer | **$0.00** | **$0.00** | **~$5.00 AUD** |
| **Firebase Phone Auth** | 10,000 verifications/month | **$0.00** | **$0.00** | **$0.00** |
| **Firebase Storage** | 5 GB storage | **$0.00** | **$0.00** | **~$2.00 AUD** |
| **Google Gemini API** | 15 RPM / 1,500 RPD free | **$0.00** | **~$1.00 AUD** | **~$3.00 AUD** |
| **Google Maps Platform** | $200 USD (~$300 AUD) credit/mo | **$0.00** | **$0.00** | **$0.00** |
| **MongoDB Atlas** | M0 Free / Serverless | **$0.00** | **~$15.00 AUD** | **~$85.00 AUD** (M10 PITR) |
| **Resend (Email)** | 3,000 emails/month free | **$0.00** | **$0.00** | **~$30.00 AUD** (Pro 50k) |
| **ABR Government API** | 5,000 queries/day free | **$0.00** | **$0.00** | **$0.00** |
| **Domain (.com.au)** | $20 AUD / year | **~$1.70 AUD** | **~$1.70 AUD** | **~$1.70 AUD** |
| **Stripe Australia** | 1.75% + $0.30 per AU sale | **$0 fixed** | **~$28.00 AUD** | **~$135.00 AUD** |
| **TOTAL RUNNING COST** | | **~$2.15 AUD / mo** | **~$51.20 AUD / mo** | **~$288.70 AUD / mo** |
| **GROSS REVENUE (MRR)** | | **$78.00 AUD** | **$943.00 AUD** | **$4,447.00 AUD** |
| **NET OPERATING MARGIN** | | **+97% Margin** | **+94% Margin** | **+93% Margin** |

### Google for Startups Credit Multiplier
Upon acceptance into the **Google for Startups Cloud Program**, DTD receives **$2,000 USD (~$3,000 AUD)** in non-dilutive cloud credits. This grant covers all Cloud Run, Cloud Tasks, Cloud Scheduler, Gemini API, and Firebase Storage charges, making all Google infrastructure costs **$0.00 AUD for the first 12 to 24 months**.

---

## 5. Step-by-Step Migration Roadmap for Anti-Gravity & Codex

The migration is executed in **5 non-disruptive, sequential packets**:

### Packet 1: Google Project & Firebase Configuration
* Create Google Cloud Project: `dtd-production`.
* Enable APIs: Cloud Run, Cloud Scheduler, Cloud Tasks, Gemini API (AI Studio), Identity Platform (Phone Auth).
* Generate `firebase.json` and `.firebaserc` in root directory.

### Packet 2: Containerization & Cloud Run Staging
* Add `backend/Dockerfile` and `backend/.dockerignore`.
* Deploy container to Google Cloud Run staging endpoint (`https://dtd-api-staging-...a.run.app`).
* Run automated health probe: verify `/api/health/deep` returns `HTTP 200 OK`.

### Packet 3: Firebase Phone Auth Client Implementation
* Integrate Firebase Web SDK into `frontend/src/pages/TrainerDetail.jsx`.
* Wire `input-otp` component to `confirmationResult.confirm(otp)`.
* Add fallback to existing email magic-link OTP if SMS delivery fails.

### Packet 4: Cloud Scheduler & Cloud Tasks Integration
* Create authenticated internal router in `backend/server.py` (`/api/internal/jobs/*`).
* Configure 6 Cloud Scheduler jobs to trigger the autonomous loops.
* Wire outbound email notifications into Cloud Tasks outbox queue.

### Packet 5: Production DNS Cutover & Uptime Verification
* Add custom domains in Firebase Hosting: `dogtrainersdirectory.com.au` and `www`.
* Update DNS A and CNAME records at domain registrar.
* Configure Google Cloud Monitoring 24/7 uptime check on `https://dogtrainersdirectory.com.au/api/health/deep`.
* Verify end-to-end journey: Browse $\rightarrow$ Search $\rightarrow$ Claim OTP $\rightarrow$ Consultation Inquiry $\rightarrow$ Cloud Task Dispatch $\rightarrow$ /ops Visibility.

---

## 6. Disaster Recovery & Failover Protocol

* **RTO (Recovery Time Objective)**: $< 15\text{ minutes}$ for complete container re-deployment; $< 30\text{ minutes}$ for database restoration.
* **RPO (Recovery Point Objective)**: $< 24\text{ hours}$ maximum data loss threshold.
* **Automatic Rollback**: If a new Cloud Run revision fails health probes, Cloud Run automatically routes 100% of live traffic to the previous healthy revision with zero downtime.
* **Database Restoration**: One-click restore from automated Atlas daily snapshots to a recovery cluster in under 20 minutes.
