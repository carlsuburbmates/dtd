# DTD / Dog Trainers Directory

Orientation only. This README is not implementation authority.

Canonical truth starts at `docs/governance/CURRENT_TRUTH_INDEX.md`.

## What this project is

DTD / Dog Trainers Directory is a Greater Melbourne dog-trainer match-and-intro product with automation-first operations and bounded human oversight.

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
cd backend && pytest -q
```

Frontend:

```bash
cd frontend && yarn test --watch=false
cd frontend && yarn build
```

## Repo shape

- `backend/` FastAPI app, runtime services, tests
- `frontend/` React app and public/operator pages
- `docs/standards/` canonical standards
- `docs/governance/` canonical governance and audit-support docs
- `docs/process/` runbooks, execution playbooks, handoff/process material
- `docs/design/` design continuity material

## Where truth lives

Read in this order:
1. `docs/governance/CURRENT_TRUTH_INDEX.md`
2. canonical implementation docs listed there
3. `docs/governance/ROADMAP.md` and `docs/governance/RUNTIME_EVIDENCE_ALIGNMENT_MATRIX.md` for no-edit code audit support

Process and design docs are non-authoritative.

## Next docs to read

- `docs/governance/CURRENT_TRUTH_INDEX.md`
- `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`
- `docs/governance/ROADMAP.md`
- `docs/governance/RUNTIME_EVIDENCE_ALIGNMENT_MATRIX.md`
