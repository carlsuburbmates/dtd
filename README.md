# Bark&Bond — pay-on-outcome dog-training match engine

> **Product principle:** one input → best matches → real outcomes.
> **System principle:** the engine runs without humans. Humans observe; they do not operate.

## What this is

Bark&Bond is **not a directory**. It is a Melbourne-focused match engine that:
- accepts a one-line problem from a dog owner (`/`),
- returns 3 ranked trainer matches (deterministic relevance + outcome score),
- charges a per-intro fee on **Connect** and a per-conversion fee on **hire**,
- ingests new trainers, re-verifies them, prices them, and detects fraud — all without a human in the loop.

There is **no admin panel** to operate the business. There is `/ops`, a read-only oversight surface.

## Quick links
- **Architecture** → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Operations / troubleshooting** → [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- **Deployment + portability** → [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

## Repo layout

```
/app
├── backend/            FastAPI app + autonomous engine
│   ├── server.py       HTTP surface (/api/*)
│   ├── services/
│   │   ├── ai.py       Deterministic verifier/matcher/copy generator
│   │   ├── engine.py   Six autonomous loops (ranking, pricing, …)
│   │   ├── fraud.py    Anti-gaming / suppression rules
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

1. Replace `billing_status="billed"` placeholder by wiring **Stripe** PaymentIntents (per intro + per conversion). Idempotency key = intro_id.
2. Connect an outbound email service (Resend / SendGrid) for the **T+7d hire-confirmation** email — without it, the per-conversion stream depends only on engagement-inference.
3. Replace the seeded `discovery_queue` entries with a real **autonomous scraper** (worker that walks public Melbourne sources and pushes to `POST /api/discovery`).
4. Configure `CORS_ORIGINS` to your real domain(s).
5. Front the API with HTTPS at the platform layer.

The system is designed to keep working at every step — none of these are blockers for revenue.
