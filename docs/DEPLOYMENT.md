# Deployment & migration

The system is intentionally portable and vendor-neutral.

## 1. Local-first baseline

Use this repo checkout as the source of truth. Keep runtime/env changes versioned with docs whenever behavior changes.

## 2. Optional host-specific operations

If your host uses Supervisor or similar process managers, apply host runbooks there. This document only covers portable project behavior.

## 3. Run locally — Docker

The included `docker-compose.yml` starts MongoDB, the FastAPI backend, and the React frontend in one command:

```bash
docker compose up --build
```

Open `http://localhost:3000`. The compose file passes through `ADMIN_PASS` from your shell environment.

## 4. Run locally — bare metal

```bash
# Mongo (any 6.x server works)
docker run -d -p 27017:27017 --name barkbond-mongo mongo:6

# Backend
cd backend && cp .env.example .env
# edit .env — set MONGO_URL=mongodb://localhost:27017, ADMIN_PASS
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd ../frontend && cp .env.example .env
# edit .env — set REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
yarn start
```

## 5. Deploy to external platforms

### Backend (FastAPI)

| Platform | Notes |
|---|---|
| **Railway / Render / Fly** | One-click Python service. Use `uvicorn server:app --host 0.0.0.0 --port $PORT` for API and run a separate long-lived worker when `AUTONOMY_LOOP_OWNER=worker`. |
| **Vercel** | Use Serverless Python with `@vercel/python` only for non-loop API hosting; autonomous loops still require a separate long-lived owner process. |
| **VPS** | systemd or supervisor units for API plus an optional separate worker process. |

Single-owner loop topology rule:
1. Exactly one process owns loops via `AUTONOMY_LOOP_OWNER`.
2. Allowed values: `api`, `worker`, `none`.
3. The DB lease is a safety guard, not the primary topology choice.
4. `/ops` remains read-only regardless of ownership topology.

### Frontend (Create React App)

| Platform | Notes |
|---|---|
| **Vercel** | `vercel --prod`. Set `REACT_APP_BACKEND_URL` in the project env. |
| **Cloudflare Pages / Netlify** | Build cmd: `yarn build`; output dir: `build`. |

### MongoDB

- **Atlas** (recommended for prod). Replace `MONGO_URL` with the Atlas SRV URI.
- A standalone Mongo instance also works.

### Matching and verification

Current matching and verification run through deterministic heuristics in `services/ai.py` with no external model key requirement.

## 6. Connecting required services in production

| Service | What to wire | Where |
|---|---|---|
| **Stripe** | Intro invoicing path on `POST /api/intros` uses Stripe Billing when `STRIPE_SECRET_KEY` is set. Submission-registered trainers are trial-free for `TRAINER_FREE_INTRO_DAYS` (default 30), then charged fixed `FIXED_INTRO_FEE_CENTS` (default 500 = A$5) per valid intro. Configure webhook endpoint `POST /api/stripe/webhook` with `STRIPE_WEBHOOK_SECRET` to reconcile `invoice.sent`, `invoice.paid`, and `invoice.payment_failed`. Keep conversion mode on `CONVERSION_BILLING_MODE=track_only` during launch. Also set Stripe Billing public contact/support email to `info@dogtrainersdirectory.com.au` so invoice-reply flow matches the single-mailbox policy. | `backend/server.py`, `backend/services/stripe_billing.py`, `backend/services/engine.py` |
| **Resend / SendGrid** | T+7 d "Did you hire?" outreach to `intros.user_email` is implemented via `send_outreach` loop. Provide `RESEND_API_KEY`, `RESEND_FROM` (recommended `no-reply@dogtrainersdirectory.com.au`), and `RESEND_REPLY_TO` (recommended `info@dogtrainersdirectory.com.au`). Returning answers should call `POST /api/conversions` (manual) or `POST /api/engagements` (kind=`return_visit`). | `backend/services/automation.py` |
| **Real ingestion** | Source-page ingestion is implemented via `ingest_sources` loop. Provide `DISCOVERY_SOURCE_URLS` and monitor `system_state.source_ingestion`. | `backend/services/automation.py` + `engine.py` |

## 7. CORS / domains

Set `CORS_ORIGINS` in backend `.env` to a comma-separated list of allowed front-end origins (e.g. `https://barkbond.app,https://www.barkbond.app`). The default `*` is fine for development.

## 8. Migration checklist (preview → prod)

1. Provision Atlas; copy the SRV URI into `MONGO_URL`.
2. Provision domain + HTTPS at the platform layer (Cloudflare, Vercel, etc.).
3. Keep conversion billing disabled during launch (`CONVERSION_BILLING_MODE=track_only`), and only enable bill-mode after intro quality metrics are stable.
4. Confirm launch intro policy env is set as intended:
   - `TRAINER_FREE_INTRO_DAYS=30`
   - `FIXED_INTRO_FEE_CENTS=500`
5. Move the seed file aside or empty `MELBOURNE_TRAINERS` once your real ingestion is producing volume.
6. Set `AUTONOMY_LOOP_OWNER` explicitly (`api` or `worker`) and keep `RUN_AUTONOMY_IN_API` consistent only if legacy compatibility is needed.
7. Set `PUBLIC_MATCHING_ENABLED` according to current mode lock (`0` for education-first prelaunch).
8. Bump `ADMIN_PASS` and `TRAINER_ACTION_TOKEN_SECRET` to strong secrets; document only in your password manager.
9. Verify all configured loops surface in `/ops` after deploy.

## 9. Code ownership / portability

- All business logic lives in `backend/services/*.py`. There are no proprietary serverless wrappers.
- The frontend uses only open-source packages from npm. No vendor SDKs are required to render the product.
- The compose file + `.env.example` files form the entire local-runnable surface. Anyone can clone the repo, copy `.env.example → .env`, and `docker compose up`.
