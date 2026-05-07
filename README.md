# Bark&Bond — pay-on-outcome dog-training match engine

> **Product principle:** one input → best matches → real outcomes.
> **System principle:** the engine runs without humans. Humans observe; they do not operate.

## What this is

Bark&Bond is **not a directory**. It is a Melbourne-focused match engine that:
- accepts a one-line problem from a dog owner (`/`),
- returns 3 ranked trainer matches (deterministic relevance + outcome score),
- records an intro on **Connect** and issues Stripe invoice collection when trainer billing profile is ready,
- launch defaults to `track_only` conversion tracking,
- tracks conversions as quality signals by default, with bill-mode available later,
- ingests new trainers, re-verifies them, prices them, and detects fraud — all without a human in the loop.

There is **no admin panel** to operate the business. There is `/ops`, a read-only oversight surface.

## Quick links
- **Architecture** → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Operations / troubleshooting** → [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- **Deployment + portability** → [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- **Design continuity (start here for UI/design sessions)** → [`docs/design/README.md`](docs/design/README.md)

## Public website routes

- `/` match flow
- `/how-it-works`
- `/about`
- `/pricing`
- `/trust`
- `/faq`
- `/contact`
- `/privacy`
- `/terms`
- `/trainers` trainer model page
- `/submit` trainer submission

## Repo layout

```
/app
├── backend/            FastAPI app + autonomous engine
│   ├── server.py       HTTP surface (/api/*)
│   ├── services/
│   │   ├── ai.py       Deterministic verifier/matcher/copy generator
│   │   ├── engine.py   Autonomous loops (ranking, pricing, discovery, outreach, …)
│   │   ├── fraud.py    Anti-gaming / suppression rules
│   │   ├── automation.py Discovery source ingestion + T+7 outreach mailer
│   │   └── seed.py     Real Melbourne seed listings
│   ├── .env.example    Required env keys
│   └── requirements.txt
├── frontend/           React 19 + Tailwind + shadcn/ui
│   └── src/pages/      Home (matcher), TrainerDetail (Connect), Submit, Ops, …
├── docs/               Architecture, Operations, Deployment
├── docker-compose.yml  Mongo + backend + frontend for local / portable runs
└── memory/             PRD + test credentials
```

## Run locally (without Docker)

```bash
# 1. Backend
cd backend
cp .env.example .env                # then edit MONGO_URL / ADMIN_PASS
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# 2. Frontend
cd ../frontend
cp .env.example .env                # set REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
yarn start
```

Visit `http://localhost:3000`.

## Run locally (with Docker)

```bash
docker compose up --build
# UI on http://localhost:3000, API on http://localhost:8001/api
```

## Required environment

| Var | Where | What |
|---|---|---|
| `MONGO_URL` | backend | MongoDB connection string |
| `DB_NAME` | backend | Database name |
| `ADMIN_PASS` | backend | Passcode for `/api/oversight/login` |
| `ACTIVE_REGION` | backend | Launch scope region (default `Greater Melbourne`) |
| `ACTIVE_REGIONS` | backend | Comma-separated allowed regions |
| `RUN_AUTONOMY_IN_API` | backend | `1` = API owns loops, `0` = worker owns loops |
| `CONVERSION_BILLING_MODE` | backend | `track_only` (default) or `bill` |
| `DISCOVERY_SOURCE_URLS` | backend | Comma-separated source pages scanned for candidate trainer links |
| `RESEND_API_KEY` | backend | Required for T+7 outreach delivery |
| `RESEND_FROM` | backend | From-address for outreach emails |
| `STRIPE_SECRET_KEY` | backend | Enables intro invoice creation/sending in Stripe |
| `STRIPE_WEBHOOK_SECRET` | backend | Verifies `/api/stripe/webhook` events for reconciliation |
| `STRIPE_INVOICE_DAYS_UNTIL_DUE` | backend | Due window for intro invoices (default 7) |
| `STRIPE_REQUIRE_BILLING_CONSENT` | backend | Set `1` to require explicit trainer billing consent before invoicing |
| `REACT_APP_BACKEND_URL` | frontend | Public URL of the backend (`/api` is appended client-side) |

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for service-by-service setup.

## Tests

```bash
# Backend (pytest)
cd backend && pytest -q

# Frontend smoke tests
# Use the testing playbook in docs/OPERATIONS.md or your preferred Playwright runner.
```

The latest iteration's report lives at `/app/test_reports/iteration_<n>.json`.

## Production checklist

1. Keep `CONVERSION_BILLING_MODE=track_only` during soft-live while validating intro quality and fraud suppression behavior.
2. Configure `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` and register the webhook endpoint `/api/stripe/webhook`.
3. Set `DISCOVERY_SOURCE_URLS` so the autonomous source-ingestion loop continuously feeds real candidates into `discovery_queue`.
4. Configure `RESEND_API_KEY` + `RESEND_FROM` for automated **T+7d hire-confirmation** outreach.
5. Configure `CORS_ORIGINS` to your real domain(s).
6. Front the API with HTTPS at the platform layer.

The system is designed to keep working at every step — none of these are blockers for revenue.
