# DTD / Dog Trainers Directory

Orientation only. This README is not implementation authority.

Canonical truth starts at `docs/README.md`. Read its active authority map before
loading the state, invariants, decision register and relevant topic specification.
Historical documentation is kept outside the checkout and in Git history; it is not an active instruction source.

## What this project is

DTD / Dog Trainers Directory is a Greater Melbourne dog-training discovery and
matching platform: real supply, rich trainer storefronts, guided owner matching,
flat SaaS upgrades, and automation-first operations with bounded oversight.

## Quick start

Use the example environment files only for synthetic local development. Runtime/provider credentials belong in managed secret stores and must not be copied into local `.env` files.

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
python3 backend/scripts/run_isolated_integration_suite.py
```

This is the maintained full backend command. It starts a local API and a
disposable loopback-only MongoDB instance, then removes the entire temporary
database directory afterwards. Pass `--mongo-url` only to use an existing
loopback MongoDB service.
It never uses the production canonical trainer seed or external providers.

Frontend:

```bash
cd frontend && yarn test
cd frontend && yarn build
```

## Repo shape

- `backend/` FastAPI app, runtime services, tests
- `frontend/` React app and public/operator pages
- `docs/` authoritative roadmap, current evidence, decisions, invariants and focused specs

## Where truth lives

Read `docs/README.md`, then `docs/DTD_CURRENT_STATE.md` and
`docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`. Use the relevant file in `docs/specs/`
and `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` for disputed decisions.
Consult historical Git versions or the external documentation archive only for explicitly requested historical research.

## Next docs to read

- `docs/README.md`
- `docs/DTD_CURRENT_STATE.md`
- `docs/DTD_ROADMAP_EXECUTION_REGISTER.md`
- `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`
