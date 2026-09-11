# GOOGLE ECOSYSTEM MIGRATION & 24/7 AUTONOMOUS ARCHITECTURE SPECIFICATION
**Canonical Technical Architecture & Deployment Blueprint**  
*Document Version: 1.0.0 • Published: September 2026 • Environment: Google Cloud Platform (GCP) & Firebase*

> **DTD acquisition correction:** Do not implement any Google Places harvest or
> AI-confidence auto-publication described below. For DTD, the canonical source
> and publication contract is
> `docs/strategy/DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`. A licensed
> Sensis/Thryv discovery feed is pending written approval and an adapter.

---

## 1. Executive Summary & Strategic Rationale

This specification details the comprehensive transition of the directory platform from fragmented, crash-vulnerable infrastructure (Render single-server worker, Vercel standalone hosting, manual Twilio top-ups) into a unified, enterprise-grade **Google Cloud & Firebase Ecosystem**.

### The 3 Core Architectural Objectives:
1. **True 24/7 Autonomous Reliability**: Replacing single-process Python background loops with managed **Google Cloud Scheduler** and **Google Cloud Tasks** (automatic retries, outbox queues, dead-letter queues, and zero silent process deaths).
2. **Zero-Idle-Cost Serverless Compute**: Deploying the containerized FastAPI backend to **Google Cloud Run** with automatic auto-healing, health probes, and scale-to-zero capability during off-peak hours.
3. **Non-Dilutive Capital Coverage**: Qualifying for the **Google for Startups Cloud Program** ($2,000 to $200,000 USD in cloud credits), effectively reducing all hosting, SMS verification, map queries, and AI compute costs to **$0 AUD/month** for the first 12–24 months.

---

## 2. Complete Component-by-Component Mapping

```
                                SYSTEM ARCHITECTURE TOPOLOGY
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                 GOOGLE CLOUD & FIREBASE CORE                              │
├──────────────────────────┬──────────────────────────┬─────────────────────────────────────┤
│ 1. EDGE & FRONTEND       │ 2. COMPUTE & QUEUES      │ 3. DATA, AI & OBSERVABILITY         │
│ • Firebase Hosting       │ • Google Cloud Run       │ • Google Gemini API (1.5 Flash)     │
│   (Apex & Subdomains)    │   (Containerized FastAPI)│   (Extraction, Scoring, Matching)   │
│ • Firebase Phone Auth    │ • Cloud Scheduler        │ • Google Maps Platform              │
│   (Australian SMS OTPs)  │   (Managed Cron Triggers)│   (Permitted Maps UX only)          │
│ • Firebase Storage       │ • Cloud Tasks            │ • Google Cloud Monitoring           │
│   (Media & Image CDN)    │   (Transactional Outbox) │   (24/7 Uptime & Incident Alerting) │
└────────────┬─────────────┴────────────┬─────────────┴───────────────────┬─────────────────┘
             │                          │                                 │
             ▼                          ▼                                 ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                            RETAINED SPECIALIST EXTERNAL SERVICES                          │
│ • Stripe Australia: Recurring B2B SaaS Subscriptions ($19/$39/$199), Invoices & Google Pay│
│ • ABR Web Services: Statutory Australian Government ABN Validation & Entity Lookup        │
│ • Resend: Transactional Email Relay (DKIM/SPF Verified on custom domain)                  │
│ • MongoDB Atlas: Existing Document Store (Hosted directly in GCP Sydney Region)           │
│ • Sentry: Deep Python & React Exception Stack-Trace Tracking                              │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Deep Architectural Specifications

### 3.1 Backend Compute: Google Cloud Run
* **Runtime**: Containerized Python 3.11 / FastAPI running with Uvicorn.
* **Deployment Region**: `australia-southeast1` (Sydney) for sub-30ms latency across Melbourne and Australia.
* **Auto-Scaling Policy**:
  - `min-instances`: 0 (scales to zero when idle at night; $0 compute cost).
  - `max-instances`: 10 (auto-scales instantly under traffic spikes).
  - `concurrency`: 80 concurrent requests per container.
* **Self-Healing & Health Probes**:
  - **Liveness Probe**: `GET /api/health` checked every 15s.
  - **Readiness Probe**: `GET /api/health/deep` verifying database connectivity and outbox queue health before routing live traffic.
  - If a container crashes or encounters an Out-Of-Memory (OOM) error, Cloud Run terminates it and spins up a healthy replacement in $< 2\text{ seconds}$.

### 3.2 Autonomous Triggers: Google Cloud Scheduler
Replaces the fragile, continuous Python background while-loops (`backend/worker.py`) with managed HTTP cron triggers invoking authenticated endpoints on Cloud Run:

| Autonomous Engine | Frequency | Endpoint Trigger | Payload / Action |
| :--- | :--- | :--- | :--- |
| **Engine 1: Ingestion & Deduplication** | Per approved source contract | `POST /api/internal/jobs/ingest` | Reads an approved licensed feed, deduplicates, structures supported facts, and applies the separate publish-or-hold evidence gate. |
| **Engine 2: Ranking & Reputation** | Every 5 minutes | `POST /api/internal/jobs/rank` | Recomputes composite ranking across Melbourne and suburb hubs. |
| **Engine 3: Suburb Vacancy & Succession**| Every 15 minutes| `POST /api/internal/jobs/inventory`| Audits 2-slot caps and dispatches 48h priority links to waitlists. |
| **Engine 4: Outcome Outreach & Reviews** | Hourly | `POST /api/internal/jobs/outreach` | Sweeps T+7 outcome follow-ups and T+14 verified review invitations. |
| **Engine 5: Verification & Staleness**   | Every 12 hours | `POST /api/internal/jobs/verify` | Re-verifies ABNs via ABR API and flags dead domains. |
| **Engine 6: Platform Health & DLQ Drain**| Every 60 seconds| `POST /api/internal/jobs/health` | Drains pending outbox messages and verifies service latencies. |

*Security*: All internal job endpoints require an `OIDC` (OpenID Connect) service account authentication token or an internal secret header (`X-Cloud-Scheduler-Secret`), rejecting unauthorized public internet traffic.

### 3.3 Transactional Reliability: Google Cloud Tasks
Replaces unbuffered external API calls with an enterprise asynchronous queue:
* **Pattern**: When an owner requests a consultation, the API saves the record to `db.intros` and pushes a task to the `dtd-outbox-queue` in Cloud Tasks.
* **Retry Policy**:
  - Max Attempts: 10
  - Min Backoff: 10 seconds
  - Max Backoff: 1 hour
  - Max Doublings: 4
* **Benefit**: If Resend, Twilio, or ABR is temporarily down, Cloud Tasks retains the task and retries with exponential backoff for up to 72 hours. Zero leads or OTPs are lost.

### 3.4 Verification & Auth: Firebase Phone Authentication
* **Role**: 10-second frictionless profile claiming for Australian mobile numbers (`+61 4xx xxx xxx`).
* **Free Tier Allowance**: **10,000 free SMS verifications per month** on the Spark/Blaze plan.
* **Security**: Built-in reCAPTCHA verification, automated toll-fraud rate limiting, and native integration with the frontend `input-otp` component.

### 3.5 Web Hosting: Firebase Hosting
* **Architecture**: Global SSD-backed edge CDN with automatic HTTP/2 and SSL certificate provisioning.
* **Multi-Site Targets**:
  - Target 1: `dogtrainersdirectory.com.au` (Apex) and `www.dogtrainersdirectory.com.au` $\rightarrow$ Main Directory React SPA.
  - Target 2: `learn.dogtrainersdirectory.com.au` $\rightarrow$ "The First Leash" Education Handbook.
* **Cache Headers**: Static JS/CSS assets cached for 1 year (`max-age=31536000, immutable`), `index.html` configured with `no-cache` for instantaneous releases.

### 3.6 Intelligence: Google Gemini API (`gemini-1.5-flash`)
* **Role**: Structured parsing of unstructured web scraping data, training philosophy extraction, and multi-factor diagnostic match scoring.
* **Performance**: Sub-500ms latency, high structured JSON output fidelity (`response_mime_type="application/json"`).
* **Cost Efficiency**: 15 RPM / 1,500 requests/day free tier via Google AI Studio; paid overage is fractions of a cent ($0.075 / 1M input tokens).

### 3.7 Observability & P1 Alerting: Google Cloud Monitoring
* **Uptime Check**: Automated ping every 60 seconds to `https://api.dogtrainersdirectory.com.au/api/health/deep` from 3 international regions (Australia, US, Europe).
* **Alerting Policies**:
  - Cloud Run 5xx error rate $> 2\%$ over 5 minutes.
  - Uptime check failure for $> 2$ consecutive checks.
  - Cloud Tasks queue age $> 15\text{ minutes}$.
* **Notification Channels**: Immediate P1 SMS and push alert to operator mobile; non-critical anomalies routed to email and `/ops`.

---

## 4. Why We Retain Specific Non-Google Services

To prevent unnecessary engineering risk and launch delays:

1. **Stripe Australia (Retained)**: Google Pay is a wallet, not a merchant SaaS subscription platform. Stripe provides Australian GST invoicing, credit card vaulting, dunning retries, and customer billing portals. Google Pay is enabled with one click *inside* Stripe Checkout.
2. **ABR Web Services (Retained)**: The Australian Business Register is a statutory agency of the Australian Taxation Office. No commercial cloud provider offers this federal data.
3. **Resend (Retained)**: Google Cloud does not offer a native transactional email relay. Resend is already configured with verified DNS/DKIM on `dogtrainersdirectory.com.au`.
4. **MongoDB Atlas (Retained for Launch)**: Rewriting the entire database from MongoDB to Cloud Firestore or PostgreSQL would reset development progress by weeks. We keep MongoDB Atlas deployed in the **Google Cloud Sydney region (`australia-southeast1`)** to maintain sub-millisecond network latency between Cloud Run and the database.

---

## 5. Cost Forecast & Startup Credit Optimization

```
                               MONTHLY COST BREAKDOWN (AUD)
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ SERVICE                      │ FREE TIER / CREDIT LIMIT     │ LAUNCH (MO 1–3) │ MATURE (MO 12)│
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Google Cloud Run**         │ 2M req / 360k GB-sec free    │ $0.00 AUD       │ ~$25.00 AUD  │
│ **Cloud Scheduler & Tasks**  │ 3 free jobs; 1M tasks free   │ ~$0.45 AUD      │ ~$2.00 AUD   │
│ **Firebase Hosting**         │ 10 GB storage / 360 MB/day   │ $0.00 AUD       │ ~$5.00 AUD   │
│ **Firebase Phone Auth**      │ **10,000 free SMS / month**  │ $0.00 AUD       │ $0.00 AUD    │
│ **Firebase / Cloud Storage** │ 5 GB free storage            │ $0.00 AUD       │ ~$2.00 AUD   │
│ **Google Gemini 1.5 Flash**  │ 1,500 requests/day free      │ $0.00 AUD       │ ~$3.00 AUD   │
│ **Google Maps Platform**     │ **$200 USD/mo free credit**  │ $0.00 AUD       │ $0.00 AUD    │
│ **MongoDB Atlas**            │ Free M0 (512 MB) / Serverless│ $0.00 AUD       │ ~$85.00 AUD  │
│ **Resend Email**             │ 3,000 emails/month free      │ $0.00 AUD       │ ~$30.00 AUD  │
│ **ABR Government API**       │ 5,000 requests/day free      │ $0.00 AUD       │ $0.00 AUD    │
│ **Stripe Processing**        │ 1.75% + $0.30 (Variable)     │ $0.00 (Fixed)   │ ~$135.00 AUD │
├──────────────────────────────┴──────────────────────────────┼─────────────────┼──────────────┤
│ **TOTAL ESTIMATED FIXED OPERATING COST**                    │ **~$0.45 AUD/mo**│ **~$152 AUD** │
│ **WITH GOOGLE FOR STARTUPS CREDITS ($2,000 - $200,000 USD)**│ **$0.00 AUD/mo**│ **$0.00 AUD** │
└─────────────────────────────────────────────────────────────┴─────────────────┴──────────────┘
```

---

## 6. Implementation Runbook for Anti-Gravity

When tasking Anti-Gravity, execute the Google integration in these 4 discrete, verifiable tasks:

### Task 1: Containerization for Google Cloud Run
* Create a production-ready `Dockerfile` in `backend/`:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  ENV PORT=8080
  CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers 2
  ```
* Add health endpoints `GET /api/health` and `GET /api/health/deep` in `server.py`.

### Task 2: Firebase Hosting Multi-Site Setup
* Create `firebase.json` in the root directory:
  ```json
  {
    "hosting": [
      {
        "target": "main-app",
        "public": "frontend/build",
        "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
        "rewrites": [{ "source": "**", "destination": "/index.html" }]
      }
    ]
  }
  ```

### Task 3: Firebase Phone Auth Claiming Integration
* Implement Firebase Web SDK (`firebase/auth`) in `frontend/src/pages/TrainerDetail.jsx`.
* Wire `RecaptchaVerifier` and `signInWithPhoneNumber` to the 6-digit `input-otp` claim modal for Australian mobile numbers.

### Task 4: Google Gemini API Client Integration
* Implement `services/gemini_client.py` using `google-genai` or `google-generativeai`.
* Replace `_heuristic_score` in `backend/services/ai.py` with structured Gemini extraction for training philosophy and specialty tags.
