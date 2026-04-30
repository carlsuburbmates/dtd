# Deployment & migration

The system is intentionally portable and vendor-neutral.

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

### Matching and verification

Current matching and verification run through deterministic heuristics in `services/ai.py` with no external model key requirement.

## 6. Connecting required services in production

| Service | What to wire | Where |
|---|---|---|
| **Stripe** | Optional for later conversion billing. Keep launch mode on `CONVERSION_BILLING_MODE=track_only` first, then enable `bill` mode when ready. | `backend/server.py` |
| **Resend / SendGrid** | T+7 d "Did you hire?" outreach to `intros.user_email` is implemented via `send_outreach` loop. Provide `RESEND_API_KEY` and `RESEND_FROM`. Returning answers should call `POST /api/conversions` (manual) or `POST /api/engagements` (kind=`return_visit`). | `backend/services/automation.py` |
| **Real ingestion** | Source-page ingestion is implemented via `ingest_sources` loop. Provide `DISCOVERY_SOURCE_URLS` and monitor `system_state.source_ingestion`. | `backend/services/automation.py` + `engine.py` |

## 7. CORS / domains

Set `CORS_ORIGINS` in backend `.env` to a comma-separated list of allowed front-end origins (e.g. `https://barkbond.app,https://www.barkbond.app`). The default `*` is fine for development.

## 8. Migration checklist (preview → prod)

1. Provision Atlas; copy the SRV URI into `MONGO_URL`.
2. Provision domain + HTTPS at the platform layer (Cloudflare, Vercel, etc.).
3. Keep conversion billing disabled during launch (`CONVERSION_BILLING_MODE=track_only`), and only enable bill-mode after intro quality metrics are stable.
4. Move the seed file aside or empty `MELBOURNE_TRAINERS` once your real ingestion is producing volume.
5. Bump `ADMIN_PASS` to a strong secret; document it only in the password manager.
6. Verify all configured loops surface in `/ops` after deploy.

## 9. Code ownership / portability

- All business logic lives in `backend/services/*.py`. There are no proprietary serverless wrappers.
- The frontend uses only open-source packages from npm. No vendor SDKs are required to render the product.
- The compose file + `.env.example` files form the entire local-runnable surface. Anyone can clone the repo, copy `.env.example → .env`, and `docker compose up`.
