# DTD / Dog Trainers Directory

Orientation only. This README is not implementation authority.

Canonical truth starts at `docs/README.md`. Read its active authority map before
loading the state, invariants, decision register and relevant topic specification.
The repository-root `archive/` is historical and excluded from ordinary tasks.

## What this project is

DTD / Dog Trainers Directory is a Greater Melbourne dog-training discovery and
matching platform: real supply, rich trainer storefronts, guided owner matching,
flat SaaS upgrades, and automation-first operations with bounded oversight.

## Quick start

Backend:

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Frontend:

```bash
cd frontend
cp .env.example .env
yarn install
yarn start
```

Optional local stack:

```bash
docker compose up --build
```

Default local URLs:
- frontend: `http://localhost:3000`
- backend: `http://localhost:8001`

## Tests

Backend:

```bash
python backend/scripts/run_isolated_integration_suite.py
```

This is the maintained full backend command. It starts a local API with a
disposable loopback-only MongoDB database and removes that database afterwards.
It never uses the production canonical trainer seed or external providers.

Frontend:

```bash
cd frontend && yarn test --watch=false
cd frontend && yarn build
```

## Repo shape

- `backend/` FastAPI app, runtime services, tests
- `frontend/` React app and public/operator pages
- `docs/` current, target and vision state, invariant rules, decisions and focused specs
- `archive/` historical documents, separate from active docs and excluded from routine searches

## Where truth lives

Read `docs/README.md`, then `docs/DTD_CURRENT_STATE.md` and
`docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`. Use the relevant file in `docs/specs/`
and `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` for disputed decisions.
Do not consult `archive/` unless the user explicitly requests historical research.

## Next docs to read

- `docs/README.md`
- `docs/DTD_CURRENT_STATE.md`
- `docs/DTD_TARGETED_POST_LAUNCH_STATE.md`
- `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`
