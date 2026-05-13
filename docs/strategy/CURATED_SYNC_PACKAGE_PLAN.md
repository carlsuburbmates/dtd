# Curated Sync Package Plan

Purpose: define the exact curated staging groups for an eventual sync package, with pre-stage checks and risk labels only.

No sync executed in this slice.

## Group A — Backend Runtime and Guardrails
- Files:
  - `backend/server.py`
  - `backend/services/claim_state.py`
- Purpose: core prelaunch runtime controls, claim-state enforcement surfaces, waitlist/oversight read-only contracts.
- Risk level: high
- Must-pass checks before staging:
  - `cd backend && ../.venv/bin/python -m pytest -q tests/test_claim_state_unit.py tests/test_public_mode_unit.py`
  - `node scripts/check_prelaunch_release_gate.js`

## Group B — Backend Test Contracts
- Files:
  - `backend/tests/test_claim_state_unit.py`
  - `backend/tests/test_public_mode_unit.py`
- Purpose: deterministic contract coverage for claim validation, guardrails, waitlist, oversight payloads.
- Risk level: medium
- Must-pass checks before staging:
  - `cd backend && ../.venv/bin/python -m pytest -q tests/test_claim_state_unit.py tests/test_public_mode_unit.py`

## Group C — Frontend Policy and Public Copy
- Files:
  - `frontend/src/lib/publicPolicy.js`
  - `frontend/src/pages/About.jsx`
  - `frontend/src/pages/FAQ.jsx`
  - `frontend/src/pages/Home.jsx`
  - `frontend/src/pages/Pricing.jsx`
  - `frontend/src/pages/Submit.jsx`
  - `frontend/src/pages/Terms.jsx`
  - `frontend/src/pages/TrainerDetail.jsx`
  - `frontend/src/pages/Trainers.jsx`
  - `frontend/src/pages/Trust.jsx`
- Purpose: policy-driven prelaunch copy, legacy-copy isolation, and waitlist-safe messaging.
- Risk level: medium
- Must-pass checks before staging:
  - `node scripts/check_frontend_copy_guard.js`
  - `cd frontend && npm run build`

## Group D — Ops Read-Only Visibility
- Files:
  - `frontend/src/pages/Ops.jsx`
- Purpose: non-technical read-only visibility for claim policy, data integrity, waitlist, and KPI surfaces.
- Risk level: low
- Must-pass checks before staging:
  - `cd frontend && npm run build`
  - `node scripts/check_prelaunch_release_gate.js`

## Group E — Strategy and Evidence Documents
- Files:
  - `docs/strategy/SOLO_FOUNDER_AUTONOMOUS_OPERATIONS_CONTROL_PACK.md`
  - `docs/strategy/PRELAUNCH_CHECKS_RUNBOOK.md`
  - `docs/strategy/melb_suburbs_abs_asgs_ed3_gccsa_2gmel_v1.meta.json`
  - `docs/strategy/IMPLEMENTATION_EVIDENCE_MANIFEST.md`
  - `docs/strategy/CURATED_SYNC_PACKAGE_PLAN.md`
- Purpose: controlled operational documentation, evidence manifesting, and canonical data metadata continuity.
- Risk level: low
- Must-pass checks before staging:
  - `node scripts/check_prelaunch_release_gate.js`
  - `node scripts/check_curated_staging_readiness.js`

## Group F — Guard Scripts
- Files:
  - `scripts/check_frontend_copy_guard.js`
  - `scripts/check_prelaunch_release_gate.js`
  - `scripts/check_curated_staging_readiness.js`
- Purpose: deterministic local guard checks for copy constraints, release gate conditions, and curated staging readiness.
- Risk level: medium
- Must-pass checks before staging:
  - `node scripts/check_frontend_copy_guard.js`
  - `node scripts/check_prelaunch_release_gate.js`
  - `node scripts/check_curated_staging_readiness.js`

## Staging Discipline
- Stage only files from one approved group at a time unless explicitly combining groups.
- Confirm tracked/untracked status per file before staging.
- Do not include unrelated dirty-tree files in the same staged set.
