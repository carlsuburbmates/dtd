# DTD / Dog Trainers Directory

> **Product principle:** one input -> best matches -> real outcomes.
> **System principle:** automation-first operations with bounded human oversight.

## What this is

DTD / Dog Trainers Directory is **not a generic directory**. It is a Greater Melbourne match-and-intro platform that:
- follows a supply-first launch posture,
- keeps `PUBLIC_MATCHING_ENABLED=false` in the current locked posture,
- treats `PUBLIC_MATCHING_ENABLED` as the public live-matching exposure gate only,
- keeps the public home entry waitlist-first while live matching remains deferred,
- accepts a one-line problem from a dog owner and returns ranked trainer matches only in the controlled lifecycle surfaces where matching is still implemented,
- records an intro on **Connect** and issues Stripe invoice collection when trainer billing profile is ready,
- launch defaults to `track_only` conversion tracking,
- tracks conversions as quality signals by default, with bill-mode available later,
- ingests new trainers, re-verifies them, prices them, and detects fraud — all without a human in the loop.

There is **no admin dashboard** to operate the business. There is `/ops`, the readable operating view and Normal Ops surface by default.

## Quick links
- **Current truth index** → [`docs/governance/CURRENT_TRUTH_INDEX.md`](docs/governance/CURRENT_TRUTH_INDEX.md)
- **Canonical page spec** → [`docs/COMPLETE_WEBSITE_PAGE_SPEC.md`](docs/COMPLETE_WEBSITE_PAGE_SPEC.md)
- **Roadmap** → [`docs/governance/ROADMAP.md`](docs/governance/ROADMAP.md)
- **Runtime evidence matrix** → [`docs/governance/RUNTIME_EVIDENCE_ALIGNMENT_MATRIX.md`](docs/governance/RUNTIME_EVIDENCE_ALIGNMENT_MATRIX.md)
- **Codex execution playbook** → [`docs/process/CODEX_EXECUTION_PLAYBOOK.md`](docs/process/CODEX_EXECUTION_PLAYBOOK.md)
- **Skill routing policy** → [`.codex/skill-policy.toml`](.codex/skill-policy.toml)
- **Design continuity (start here for UI/design sessions)** → [`docs/design/README.md`](docs/design/README.md)

## Public website routes

- `/` owner waitlist home entry in the current locked posture
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
.
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
| `AUTONOMY_LOOP_OWNER` | backend | Primary loop-owner selector: `api`, `worker`, or `none` |
| `RUN_AUTONOMY_IN_API` | backend | Legacy compatibility flag; must not conflict with `AUTONOMY_LOOP_OWNER` |
| `PUBLIC_MATCHING_ENABLED` | backend | Live matching exposure gate; `1` exposes live matching, `0` keeps owner waitlist as the primary home entry |
| `TRAINER_ACTION_TOKEN_SECRET` | backend | HMAC secret for trainer billing/reactivation action tokens |
| `CONVERSION_BILLING_MODE` | backend | `track_only` (default) or `bill` |
| `DISCOVERY_SOURCE_URLS` | backend | Comma-separated source pages scanned for candidate trainer links |
| `RESEND_API_KEY` | backend | Required for T+7 outreach delivery |
| `RESEND_FROM` | backend | From-address for outreach emails |
| `STRIPE_SECRET_KEY` | backend | Enables intro invoice creation/sending in Stripe |
| `STRIPE_WEBHOOK_SECRET` | backend | Verifies `/api/stripe/webhook` events for reconciliation |
| `STRIPE_INVOICE_DAYS_UNTIL_DUE` | backend | Due window for intro invoices (default 7) |
| `STRIPE_REQUIRE_BILLING_CONSENT` | backend | Set `1` to require explicit trainer billing consent before invoicing |
| `REACT_APP_BACKEND_URL` | frontend | Public URL of the backend (`/api` is appended client-side) |

See the environment examples and the canonical docs for current runtime expectations.

## Tests

```bash
# Backend (pytest)
cd backend && pytest -q

# Frontend smoke tests
# Use your preferred Playwright runner.
```

Use the current test suite and canonical docs as the source of verification.

## Production checklist

1. Keep `CONVERSION_BILLING_MODE=track_only` during soft-live while validating intro quality and fraud suppression behavior.
2. Configure `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` and register the webhook endpoint `/api/stripe/webhook`.
3. Set `DISCOVERY_SOURCE_URLS` so the autonomous source-ingestion loop continuously feeds real candidates into `discovery_queue`.
4. Configure `RESEND_API_KEY` + `RESEND_FROM` for automated **T+7d hire-confirmation** outreach.
5. Configure `CORS_ORIGINS` to your real domain(s).
6. Front the API with HTTPS at the platform layer.

Core operating rule:
- `Database = truth`
- `/ops = readable operating view`
- `audit_log = decision trail`
- `CSV/export = proof only`

The runtime is fail-soft, but launch progression remains governed by explicit owner-approved decisions in [`docs/governance/LOCK_STATE.md`](docs/governance/LOCK_STATE.md), [`docs/process/NEXT_SESSION_HANDOFF.md`](docs/process/NEXT_SESSION_HANDOFF.md), and the canonical standards under `docs/standards/`.
