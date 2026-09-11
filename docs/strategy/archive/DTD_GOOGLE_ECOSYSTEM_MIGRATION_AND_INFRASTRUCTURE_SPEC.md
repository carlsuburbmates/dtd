# DTD: Google Cloud & Firebase Ecosystem Migration Specification
**Document ID:** `DTD-SPEC-GCP-001`  
**Version:** `1.0.0 (Production Architecture)`  
**Status:** `Approved Architecture Specification`  
**Target Environment:** `Google Cloud Platform (australia-southeast1) + Firebase`

> **Acquisition boundary:** Google infrastructure hosts and processes DTD, but
> Google Places and Gemini Search Grounding do not supply persistent trainer
> inventory. Source truth is defined by
> `DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`; the licensed Sensis/Thryv feed is
> pending supplier confirmation and is not implemented.

---

## 1. Executive Architecture & Strategic Posture

To achieve **24/7 autonomous reliability**, eliminate silent worker failures, and drastically reduce operational overhead, Dog Trainers Directory (DTD) consolidates its compute, hosting, background scheduling, AI intelligence, and mobile verification into a unified **Google Cloud & Firebase Ecosystem**.

### The 3 Core Architectural Principles
1. **Zero-Downtime Serverless Compute**: Replace single-instance container hosting (Render) with **Google Cloud Run**, providing instant auto-healing, health probes, and scale-to-zero efficiency.
2. **Decoupled Task Orchestration**: Replace the long-running Python background process (`worker.py`) with managed **Google Cloud Scheduler** (cron triggers) and **Google Cloud Tasks** (reliable outbox queue with native exponential backoff and dead-letter queues).
3. **Friction-Free Free-Tier Utilization**: Leverage Google's generous recurring free tiers (Firebase Phone Auth 10k free SMS/mo, Google Maps $200/mo credit, Cloud Run 2M free requests/mo) to keep fixed baseline operating costs **under $5 AUD/month**.

```
                           UNIFIED GOOGLE ECOSYSTEM TOPOLOGY
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. EDGE & FRONTEND (Firebase Hosting)                                                     │
│ • Main Directory: `dogtrainersdirectory.com.au` (React SPA)                               │
│ • Education Platform: `learn.dogtrainersdirectory.com.au` (Standalone Learning Hub)       │
│ • Zero DNS drift, automatic SSL provisioning, and global SSD CDN edge caching.            │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. COMPUTE & SERVING (Google Cloud Run - Sydney: `australia-southeast1`)                  │
│ • FastAPI Backend (`server.py`) packaged in lightweight multi-stage Docker container.      │
│ • Auto-scaling (0 to 10 instances), auto-healing restart in <2s, and scale-to-zero.       │
│ • Latency across Melbourne: <30ms via Google's direct Australian fiber backbone.          │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. ASYNCHRONOUS ORCHESTRATION (Cloud Scheduler & Cloud Tasks)                             │
│ • Cloud Scheduler: Fires authenticated HTTPS triggers to Cloud Run on exact cron schedules│
│   (Ingestion every 6h, Ranking every 5m, Outcome Outreach hourly, Vacancy every 15m).     │
│ • Cloud Tasks: Transactional outbox queue managing email & webhook dispatches with        │
│   automatic exponential retries and dead-letter queues (DLQ).                             │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. IDENTITY & MOBILE CLAIMING (Firebase Phone Authentication)                             │
│ • Replaces Twilio. Delivers 6-digit SMS OTP codes to Australian mobiles (`+614...`).      │
│ • 10,000 free verifications/month on Blaze/Spark tier. Built-in reCAPTCHA bot defense.    │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. INTELLIGENCE & APPROVED SOURCE PROCESSING (Gemini + licensed supplier)                 │
│ • Gemini: Schema-bound factual structuring from URLs DTD already obtained lawfully.       │
│ • Sensis/Thryv feed: Pending written rights and adapter; not yet an active source.         │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. SPECIALIST IRREPLACEABLE INTEGRATIONS (Kept External)                                  │
│ • Stripe Australia: Subscriptions ($19/$39/$199), Tax Invoices, and Google Pay wallet.    │
│ • ABR Web Services: Official Australian Government ABN legal entity validation.           │
│ • MongoDB Atlas: Existing document store (hosted in GCP Sydney region; zero rewrite).     │
│ • Resend: Transactional email (DKIM/SPF verified on `dogtrainersdirectory.com.au`).      │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Migration Matrix & Work Division

| Subsystem | Previous State | Target Google Service | Division of Labor |
| :--- | :--- | :--- | :--- |
| **API Compute** | Render (`dtd-api`) | **Google Cloud Run** | Anti-Gravity writes Dockerfile; User deploys via Git connect. |
| **Background Loops** | `worker.py` (Single server) | **Cloud Scheduler + Cloud Tasks** | Anti-Gravity adds HTTP trigger endpoints; Scheduler calls them. |
| **SMS Verification** | Twilio / MessageMedia | **Firebase Phone Auth** | Anti-Gravity implements `input-otp` + Firebase Auth SDK. |
| **Web Hosting** | Vercel | **Firebase Hosting** | Anti-Gravity creates `firebase.json`; 1-command deploy. |
| **AI Intelligence** | Keyword heuristics | **Google Gemini 1.5 Flash** | Anti-Gravity updates `services/ai.py` with `google-genai` SDK. |
| **Media Storage** | Cloudinary / S3 | **Firebase Storage (GCS)** | Anti-Gravity implements client-side image upload component. |
| **Uptime Monitoring** | Internal `system_state` | **Cloud Monitoring Uptime** | Automated 24/7 probe with SMS/email pager on failure. |
| **Billing / SaaS** | Stripe Australia | **Stripe Australia** *(Kept)* | Keep existing Stripe subscription & invoice contracts. |
| **Government ABN** | ABR Web Services | **ABR Web Services** *(Kept)* | Keep verified Modulus 89 and ABR GUID integration. |
| **Database** | MongoDB Atlas | **MongoDB Atlas** *(Kept)* | Keep existing Motor queries; run inside GCP Sydney region. |

---

## 3. Concrete Implementation Details for Anti-Gravity

### 3.1 Google Cloud Run Dockerfile (`backend/Dockerfile`)
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

# Cloud Run injects the PORT environment variable (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers 2
```

### 3.2 Firebase Hosting Configuration (`firebase.json`)
```json
{
  "hosting": [
    {
      "target": "main",
      "public": "frontend/build",
      "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
      "rewrites": [
        {
          "source": "/api/**",
          "run": {
            "serviceId": "dtd-api",
            "region": "australia-southeast1"
          }
        },
        {
          "source": "**",
          "destination": "/index.html"
        }
      ]
    },
    {
      "target": "learn",
      "public": "frontend/build-learn",
      "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
      "rewrites": [
        {
          "source": "**",
          "destination": "/index.html"
        }
      ]
    }
  ]
}
```

### 3.3 Google Gemini AI Client (`backend/services/ai_gemini.py`)
```python
import os
import json
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

async def enrich_trainer_with_gemini(raw_text: str) -> dict:
    prompt = f"""
    You are an expert canine behavioral taxonomy engine. Extract structured business information from the following public trainer text:
    ---
    {raw_text}
    ---
    Return strictly a JSON object with:
    - training_philosophy: "Positive Reinforcement / Force-Free" or "Balanced"
    - specialties: array of ["puppy_training", "leash_reactivity", "separation_anxiety", "obedience", "aggression", "agility"]
    - service_formats: array of ["in_home", "facility", "board_and_train", "group_classes"]
    - bio_summary: a concise, engaging 2-sentence professional bio.
    """
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)
```

### 3.4 Firebase Phone Auth Setup (`frontend/src/lib/firebase.js`)
```javascript
import { initializeApp } from "firebase/app";
import { getAuth, RecaptchaVerifier, signInWithPhoneNumber } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  appId: process.env.REACT_APP_FIREBASE_APP_ID
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

---

## 4. 24/7 High-Availability, Failover & Self-Healing Contract

```
                           24/7 SELF-HEALING MATRIX
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ FAILURE SCENARIO                             │ AUTOMATED RECOVERY BEHAVIOR                  │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 1. Cloud Run container crashes (OOM or error)│ Cloud Run spins up a healthy replacement in  │
│                                              │ <2 seconds. Zero human intervention needed.  │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 2. Background Loop Fails                     │ Cloud Scheduler retries the HTTP request;    │
│                                              │ Cloud Tasks retries with exponential backoff │
│                                              │ for up to 72 hours before hitting the DLQ.   │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 3. Resend Email Outage                       │ Messages are queued in `db.outbox`. Cloud    │
│                                              │ Tasks drains the queue once Resend recovers. │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 4. ABR Government API Weekend Maintenance    │ Claim enters `CLAIM_PENDING_ABR`. Background │
│                                              │ verification retries every 2h automatically. │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 5. Catastrophic Database Loss                │ Automated daily mongodump backup restored to │
│                                              │ fresh cluster (RTO < 30 min, RPO < 24h).     │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 5. Google for Startups Cloud Credits Strategy

By consolidating onto Google Cloud, DTD qualifies for the **Google for Startups Cloud Program**:
* **Initial Grant**: **$2,000 USD (~$3,000 AUD)** in free cloud credits valid for 2 years.
* **Eligible Services**: Cloud Run, Cloud Tasks, Cloud Scheduler, Firebase Storage, Google Gemini API, and Google Maps usage.
* **Operating Runway**: Because DTD's monthly cloud consumption is estimated at ~$5–$25 AUD/month, this credit provides **over 24 months of 100% free cloud infrastructure**.
