# Deployment & migration

The system is intentionally portable. The current build runs on the Emergent platform but contains nothing that locks it there.

## 1. Run on the current preview environment

You don't need to do anything — the project is wired into supervisor:

```bash
sudo supervisorctl status backend frontend
sudo supervisorctl restart backend       # if you change .env or install deps
```

Hot reload is enabled for both services.

## 2. Export to GitHub

```bash
cd /app
git init
git add .
git commit -m "Bark&Bond v2.1"
git remote add origin git@github.com:YOUR_ORG/barkbond.git
git push -u origin main
```

Nothing in this repo depends on the build environment.

## 3. Run locally — Docker

The included `docker-compose.yml` starts MongoDB, the FastAPI backend, and the React frontend in one command:

```bash
docker compose up --build
```

Open `http://localhost:3000`. The compose file passes through `EMERGENT_LLM_KEY` and `ADMIN_PASS` from your shell environment.

## 4. Run locally — bare metal

```bash
# Mongo (any 6.x server works)
docker run -d -p 27017:27017 --name barkbond-mongo mongo:6

# Backend
cd backend && cp .env.example .env
# edit .env — set MONGO_URL=mongodb://localhost:27017, EMERGENT_LLM_KEY, ADMIN_PASS
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
| **Railway / Render / Fly** | One-click Python service. Use `uvicorn server:app --host 0.0.0.0 --port $PORT`. |
| **Vercel** | Use Serverless Python with `@vercel/python`. Background loops require a long-lived worker — switch to Railway/Fly for autonomy, OR run the loops on a tiny Cron-like worker that calls `engine.recompute_*` every N seconds. |
| **VPS** | systemd unit running `uvicorn`. |

### Frontend (Create React App)

| Platform | Notes |
|---|---|
| **Vercel** | `vercel --prod`. Set `REACT_APP_BACKEND_URL` in the project env. |
| **Cloudflare Pages / Netlify** | Build cmd: `yarn build`; output dir: `build`. |

### MongoDB

- **Atlas** (recommended for prod). Replace `MONGO_URL` with the Atlas SRV URI.
- A standalone Mongo instance also works.

### LLM

`EMERGENT_LLM_KEY` works with Claude Sonnet 4.5 via the bundled `emergentintegrations` package. To swap the provider, edit `services/ai.py` (`MODEL_PROVIDER`, `MODEL_NAME`, and the `LlmChat` import).

## 6. Connecting required services in production

| Service | What to wire | Where |
|---|---|---|
| **Stripe** | Replace `billing_status="billed"` placeholder in `POST /api/intros` and `POST /api/conversions` with `PaymentIntent.create(...)` (idempotency key = intro_id). | `backend/server.py` |
| **Resend / SendGrid** | T+7 d "Did you hire?" outreach to `intros.user_email`. Returning answers should call `POST /api/conversions` (manual) or `POST /api/engagements` (kind=`return_visit`). | New worker (background task) |
| **Real ingestion** | Replace the seeded `discovery_queue` rows with a scheduled crawler that calls `POST /api/discovery` for each candidate URL. | New worker; the engine will handle dedup, scoring, and publishing. |

## 7. CORS / domains

Set `CORS_ORIGINS` in backend `.env` to a comma-separated list of allowed front-end origins (e.g. `https://barkbond.app,https://www.barkbond.app`). The default `*` is fine for development.

## 8. Migration checklist (preview → prod)

1. Provision Atlas; copy the SRV URI into `MONGO_URL`.
2. Provision domain + HTTPS at the platform layer (Cloudflare, Vercel, etc.).
3. Stripe: create products *Per-intro* and *Per-conversion*; wire webhooks for refunds → flip `billing_status` to `refunded`.
4. Move the seed file aside or empty `MELBOURNE_TRAINERS` once your real ingestion is producing volume.
5. Bump `ADMIN_PASS` to a strong secret; document it only in the password manager.
6. Verify all six loops surface in `/ops` after deploy.

## 9. Code ownership / portability

- All business logic lives in `backend/services/*.py`. There are no proprietary serverless wrappers.
- The frontend uses only open-source packages from npm. No vendor SDKs are required to render the product.
- The compose file + `.env.example` files form the entire local-runnable surface. Anyone can clone the repo, copy `.env.example → .env`, and `docker compose up`.
