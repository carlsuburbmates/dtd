# DTD Google Ecosystem Migration & 24/7 Autonomous Architecture Specification

**Status:** Canonical Implementation & Migration Blueprint  
**Date:** 2026-09-08  
**Location Scope:** Greater Melbourne, Victoria, Australia (`australia-southeast1`)  
**Target Execution Agent:** Anti-Gravity (Local AI Coding Agent)  
**File Path:** `docs/strategy/DTD_GOOGLE_ECOSYSTEM_MIGRATION_SPEC.md`  

> **Acquisition boundary:** This task spec may implement Google runtime services
> but must not use Google Places or Gemini Search Grounding as persistent trainer
> acquisition. Follow `DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`; the preferred
> Sensis/Thryv feed remains pending written rights, schema, credentials, and an
> adapter.

---

## Table of Contents
1. [Executive Summary & Strategic Rationale](#1-executive-summary--strategic-rationale)
2. [Target System Topology](#2-target-system-topology)
3. [Master Service Migration Matrix](#3-master-service-migration-matrix)
4. [Component-by-Component Technical Contracts](#4-component-by-component-technical-contracts)
   - 4.1 [Backend Compute: Render → Google Cloud Run](#41-backend-compute-render--google-cloud-run)
   - 4.2 [Autonomous Loops: worker.py → Cloud Scheduler + Cloud Tasks](#42-autonomous-loops-workerpy--cloud-scheduler--cloud-tasks)
   - 4.3 [SMS Verification: Twilio → Firebase Phone Authentication](#43-sms-verification-twilio--firebase-phone-authentication)
   - 4.4 [Web & Frontend Edge: Vercel → Firebase Hosting (Multi-Site)](#44-web--frontend-edge-vercel--firebase-hosting-multi-site)
   - 4.5 [AI Scoring & Diagnostic Matching: Heuristics → Google Gemini API](#45-ai-scoring--diagnostic-matching-heuristics--google-gemini-api)
   - 4.6 [Media Storage: Cloudinary/S3 → Firebase Storage](#46-media-storage-cloudinarys3--firebase-storage)
5. [The 4 Modular Tasks for Anti-Gravity](#5-the-4-modular-tasks-for-anti-gravity)
6. [The 1-Time User Setup Guide (Bypassing Console Noise)](#6-the-1-time-user-setup-guide-bypassing-console-noise)
7. [24/7 High-Availability, Backups & Disaster Recovery SLA](#7-247-high-availability-backups--disaster-recovery-sla)
8. [Itemized Cost Forecast & Google Startup Credits](#8-itemized-cost-forecast--google-startup-credits)

---

## 1. Executive Summary & Strategic Rationale

This specification defines the complete consolidation of Dog Trainers Directory (DTD) into the **Google Cloud & Firebase ecosystem**, paired with **Stripe Australia**, **ABR Web Services**, and **MongoDB Atlas** (hosted in GCP Sydney).

### Why Migrate?
1. **Eliminate 24/7 Single-Point-of-Failure**: Moving from a standalone Python `worker.py` script to **Google Cloud Scheduler + Cloud Tasks** guarantees that background loops never die silently.
2. **Auto-Healing Serverless Compute**: Moving from Render's sleeping containers to **Google Cloud Run** ensures automatic container restarts in $<2\text{s}$, zero downtime during traffic spikes, and scale-to-zero at 3:00 AM ($0 idle compute).
3. **Drastic Cost Reduction on SMS**: Replacing Twilio ($0.08/SMS) with **Firebase Phone Auth** unlocks **10,000 free SMS OTP verifications every month**, reducing claiming costs to $0.
4. **Google for Startups Cloud Credits**: Unlocks eligibility for **$2,000 to $200,000 USD** in non-dilutive Google Cloud credits.

---

## 2. Target System Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GOOGLE CLOUD / FIREBASE CORE                       │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│ FRONTEND & EDGE          │ COMPUTE & AUTOMATION     │ DATA & INTELLIGENCE   │
│ • Firebase Hosting       │ • Google Cloud Run       │ • Google Gemini API   │
│   (dogtrainersdirectory  │   (FastAPI Backend)      │   (gemini-1.5-flash)  │
│    and learn subdomain)  │ • Cloud Scheduler        │ • Google Maps API     │
│ • Firebase Phone Auth    │   (Cron job triggers)    │   (Places & Geocode)  │
│   (10k Free SMS OTPs)    │ • Cloud Tasks            │ • Cloud Monitoring    │
│ • Firebase Storage       │   (Reliable Outbox queue)│   (24/7 Uptime/Alerts)│
└────────────┬─────────────┴────────────┬─────────────┴───────────┬───────────┘
             │                          │                         │
             ▼                          ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       IRREPLACEABLE SPECIALIST SERVICES                     │
│ • Stripe Australia: Subscriptions ($19/$39/$199), Invoices & Google Pay     │
│ • ABR Web Services: Official Australian Government ABN Entity Verification  │
│ • Resend: Transactional Email Delivery (DKIM/SPF Verified)                  │
│ • MongoDB Atlas: Primary Document Store (GCP Sydney australia-southeast1)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Master Service Migration Matrix

| Functional Area | Current Service | Target Service | Rationale |
| :--- | :--- | :--- | :--- |
| **Backend Compute** | Render (`dtd-api`) | **Google Cloud Run** | 24/7 auto-healing, zero idle cost, scales on demand. |
| **Autonomous Loops** | `worker.py` script | **Cloud Scheduler + Cloud Tasks** | Eliminates process deadlocks; native exponential retries. |
| **SMS OTP Verification** | Twilio / MessageMedia | **Firebase Phone Auth** | 10,000 free SMS/mo; built-in Australian mobile handling. |
| **Web & Edge Hosting** | Vercel | **Firebase Hosting** | Unifies apex domain and `learn` subdomain under 1 SSL project. |
| **AI Scoring & Matching**| Heuristic counters | **Google Gemini API** | Rapid structured JSON extraction (`gemini-1.5-flash`). |
| **Media & Portfolio CDN**| Cloudinary / AWS S3 | **Firebase Storage** | 5 GB free tier, unified client-side upload SDK. |
| **24/7 Uptime Alerts** | Internal state table | **Google Cloud Monitoring** | Automated external HTTP checks with SMS/pager alerts. |
| **Payments & Billing** | Stripe Australia | **KEEP STRIPE** | Irreplaceable for Australian B2B SaaS invoicing & tax IDs. |
| **ABN Government Lookup**| ABR Web Services | **KEEP ABR** | Official statutory ATO business register. |
| **Transactional Email** | Resend | **KEEP RESEND** | Already verified for `dogtrainersdirectory.com.au`. |
| **Primary Database** | MongoDB Atlas | **KEEP MONGODB ATLAS** | Prevents rewrite delay; runs in GCP Sydney region. |
| **Error Monitoring** | Sentry | **KEEP SENTRY** | Unmatched Python/React deep stack trace tracking. |

---

## 4. Component-by-Component Technical Contracts

### 4.1 Backend Compute: Render → Google Cloud Run
* **Containerization**: Packaged via a multi-stage `Dockerfile` running Uvicorn on port `8080`.
* **Execution Flags**:
  - Min instances: `0` (scales to zero when idle).
  - Max instances: `10` (handles Melbourne traffic spikes).
  - Memory: `512 MiB`, vCPU: `1`.
  - Region: `australia-southeast1` (Sydney, $<30\text{ms}$ to Melbourne).
* **Health Probe**: Configured to `GET /api/health/deep`.
* **Database Connection Pool Guardrail**:
  - Motor / PyMongo client must explicitly set `maxPoolSize=15` and `minPoolSize=1`.
  - With Cloud Run scaling to 10 instances, maximum concurrent TCP connections peak at 150, safely below MongoDB Atlas M0's hard ceiling of 500 concurrent connections.

### 4.2 Autonomous Loops: worker.py → Cloud Scheduler + Cloud Tasks
* **Cloud Scheduler Endpoints**:
  1. `POST /api/internal/cron/ingestion` (Every 6 hours)
  2. `POST /api/internal/cron/ranking` (Every 5 minutes)
  3. `POST /api/internal/cron/suburb-inventory` (Every 15 minutes)
  4. `POST /api/internal/cron/outreach` (Every 1 hour)
  5. `POST /api/internal/cron/verification` (Every 12 hours)
* **True Scale-to-Zero Preservation**:
  - Internal 60s health crons are **strictly prohibited** in Cloud Scheduler to allow Cloud Run containers to scale to zero at 3:00 AM for $0.00 idle compute.
  - Health probing is offloaded to **Google Cloud Monitoring external uptime checks** (free, external edge nodes, zero compute overhead).
* **Authentication & Edge Security**:
  - Rely on **Cloud Run Native IAM Authorization** at the edge: Cloud Run routes for internal crons require IAM authorization, validating Cloud Scheduler / Cloud Tasks service account tokens before FastAPI code executes (avoiding runtime JWKS certificate parsing in Python).
* **Cloud Tasks Outbox**: When an email or lead is queued, backend enqueues a Cloud Task with 5 retries and exponential backoff over 72 hours.

### 4.3 SMS Verification: Twilio → Firebase Phone Authentication
* **Client Implementation**: Integrated into [src/pages/TrainerDetail.jsx](file:///Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/TrainerDetail.jsx) using `@firebase/auth` and `input-otp`.
* **Flow**:
  1. Trainer clicks "Claim this business".
  2. Enters Australian mobile number (`04xx xxx xxx`).
  3. Firebase sends 6-digit SMS code with invisible reCAPTCHA bot guard.
  4. Trainer enters code in the 6-slot OTP input.
  5. Firebase issues auth token -> Backend verifies token -> Sets `claim_status="claimed"`.
* **Carrier & Fraud Defense**:
  - **Country Restriction**: In Firebase Console, restrict SMS delivery strictly to `+61` (Australia) to block international SMS toll-fraud bots.
  - **Firebase App Check**: Enable App Check on the web client with reCAPTCHA Enterprise to verify legitimate browser requests and protect the 10,000 free monthly SMS quota.
  - **Email Fallback**: Provide an automated email OTP fallback via Resend if a trainer's Australian mobile carrier delays or filters virtual SMS.

### 4.4 Web & Frontend Edge: Firebase Hosting (Decoupled Multi-Repo & Multi-Site)
* **Architecture Strategy (Decoupled Dual-Repo)**:
  - **Target 1: `dogtrainersdirectory.com.au` (and `www`)**: Serves the main directory React SPA built with CRACO/Tailwind v3 (`dtd/frontend`). Configured in `dtd/firebase.json` under default hosting.
  - **Target 2: `learn.dogtrainersdirectory.com.au`**: Serves The First Leash education platform built with Vite 6/Tailwind v4 (`DTD-education-extended`). Configured in `DTD-education-extended/firebase.json` under hosting target `learn`.
  - **Rationale**: Keeping repos independent eliminates catastrophic build and dependency conflicts (CRACO/Webpack vs Vite 6, Tailwind v3 vs v4), preserves sub-second Vite builds, and isolates directory operations from education updates. Both deploy under the same Google Cloud / Firebase project (`gen-lang-client-0028123502` / `dogtrainersdirectory`).
* **SPA Rewrite**: Standard `{"source": "**", "destination": "/index.html"}`.

### 4.5 AI Scoring & Diagnostic Matching: Heuristics → Google Gemini API
* **Model**: `gemini-1.5-flash` via `google-genai` SDK.
* **Account Tier & Australian Privacy Compliance**:
  - Attached to verified Pay-As-You-Go Google Cloud Billing Account (`012AD5-4A21F6-67F052` under project `gen-lang-client-0028123502`).
  - **Contractual Privacy**: Unlike the Free Tier, Google's Pay-As-You-Go API terms contractually guarantee that prompts and diagnostic intake data are **NEVER logged or used for model training**, ensuring full compliance with Australian Privacy Principles (APPs). Cost is nominal (~$0.075 / 1M tokens, or ~$0.20 AUD/month).
* **Schema Enforcement**: Structured JSON output extracting:
  - `training_philosophy` ("Positive Reinforcement / Force-Free" or "Balanced")
  - `specialties` (array of dog behavior categories)
  - `service_formats` ("in_home", "facility", "board_and_train", "online")
  - `serviced_suburbs` (geographic catchment list)

### 4.6 Media Storage: Cloudinary/S3 → Firebase Storage
* **Rules**: Restrict uploads to authenticated trainers, max file size 5MB, image types only (`image/jpeg`, `image/png`, `image/webp`).
* **CDN Caching**: Stored with `Cache-Control: public, max-age=31536000`.

---

## 5. The 4 Modular Tasks for Anti-Gravity

Give Anti-Gravity these four self-contained, sequential tasks:

### Task 1: Google Gemini API Client Integration
* **Target File:** `backend/services/ai.py`
* **Action:** Replace heuristic counters with `gemini-1.5-flash` using `GEMINI_API_KEY` (Pay-As-You-Go tier).
* **Exit Gate:** `pytest backend/tests/test_ai_scoring.py` passes with valid JSON extraction.

### Task 2: Firebase Phone Auth for Profile Claiming
* **Target File:** `frontend/src/pages/TrainerDetail.jsx`
* **Action:** Wire up Firebase Phone Auth with `input-otp` component, AU `+61` constraint, App Check, and Resend email fallback.
* **Exit Gate:** Entering an Australian mobile number dispatches an SMS OTP and resolves profile ownership.

### Task 3: Firebase Hosting Multi-Site Configuration
* **Target Files:** `dtd/firebase.json`, `DTD-education-extended/firebase.json`, `.firebaserc`
* **Action:** Configure build targets in Firebase project `gen-lang-client-0028123502`:
  - `dtd/frontend` deploys to default site: `firebase deploy --only hosting`
  - `DTD-education-extended` deploys to target `learn`: `firebase deploy --only hosting:learn`
* **Exit Gate:** Both sites build independently and deploy to their respective domains (`dogtrainersdirectory.com.au` and `learn.dogtrainersdirectory.com.au`).

### Task 4: Google Cloud Run Dockerfile, Connection Pool & Health Endpoints
* **Target Files:** `backend/Dockerfile`, `backend/server.py`
* **Action:** Build multi-stage Dockerfile listening on port 8080, cap Motor connection pool (`maxPoolSize=15`), implement Cloud Run IAM ingress, and implement `GET /api/health/deep`.
* **Exit Gate:** Docker container builds locally and responds `200 OK` on health probe.

---

## 6. The 1-Time User Setup Guide (Bypassing Console Noise)

You only need to complete these 3 browser steps once:

1. **Create Firebase Project**:
   - Go to [console.firebase.google.com](https://console.firebase.google.com) -> Click "Add Project" (e.g. `dtd-melbourne`).
2. **Enable Phone Authentication**:
   - In the Firebase Console, navigate to **Build -> Authentication -> Sign-in method**.
   - Click **Phone** -> Toggle **Enable** -> Click **Save**.
3. **Generate Gemini API Key**:
   - Go to [aistudio.google.com](https://aistudio.google.com) -> Click **Get API Key** -> Copy key.
   - Add `GEMINI_API_KEY=AIzaSy...` to your local `backend/.env`.

---

## 7. 24/7 High-Availability, Backups & Disaster Recovery SLA

* **Database Backups (RPO < 24h, RTO < 30m)**:
  - Daily snapshot cron job exports compressed BSON from MongoDB Atlas to encrypted Cloud Storage.
* **Self-Healing Containers**:
  - Google Cloud Run automatically replaces crashed instances in $<2\text{ seconds}$.
* **Dead-Man's Watchdog**:
  - Google Cloud Monitoring pings `/api/health/deep` every 60 seconds from external edge nodes.
  - If 3 consecutive checks fail, an automated SMS/Pager alert is dispatched to the operator.

---

## 8. Itemized Cost Forecast & Google Startup Credits

| Platform | Free Allowance | Launch Cost (Mo 1–3) | Mature Market (Mo 7–12+) |
| :--- | :--- | :---: | :---: |
| **Google Cloud Run** | 2M req/mo free | **$0.00 AUD** | **~$25.00 AUD** |
| **Cloud Scheduler & Tasks** | 3 free jobs; 1M tasks free | **~$0.45 AUD** | **~$2.00 AUD** |
| **Firebase Hosting** | 10 GB storage free | **$0.00 AUD** | **~$5.00 AUD** |
| **Firebase Phone Auth** | **10,000 free SMS/month** | **$0.00 AUD** | **$0.00 AUD** |
| **Google Gemini API** | 15 RPM / 1,500 req/day free | **$0.00 AUD** | **~$3.00 AUD** |
| **Google Maps API** | **$200 USD/mo recurring credit** | **$0.00 AUD** | **$0.00 AUD** |
| **MongoDB Atlas** | M0 free cluster | **$0.00 AUD** | **~$85.00 AUD** *(M10 PITR)* |
| **Resend Email** | 3,000 emails/mo free | **$0.00 AUD** | **~$30.00 AUD** |
| **Domain (.com.au)** | $20 AUD / year | **~$1.70 AUD** | **~$1.70 AUD** |
| **Stripe Australia** | 1.75% + $0.30 per sale | **$0 fixed** | **Variable (from sales)** |
| **TOTAL FIXED COST** | | **~$2.15 AUD / month** | **~$150.00 AUD / month** |

* **Google for Startups Multiplier**: Once accepted into the Google for Startups Cloud Program, **$2,000 to $200,000 USD** in credits covers Cloud Run, Cloud Tasks, Gemini, and Maps, reducing cloud costs to **$0 AUD for up to 24 months**.
