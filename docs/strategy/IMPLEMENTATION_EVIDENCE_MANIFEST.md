# Implementation Evidence Manifest

Purpose: concise operational manifest for verification evidence and curated staging boundaries.

## Executed verification stack

1. Backend tests
   - Command: `cd backend && ../.venv/bin/python -m pytest -q tests/test_claim_state_unit.py tests/test_public_mode_unit.py`
   - Required PASS tokens:
     - Exit code `0`
     - Output contains `passed`
     - Output does not contain `failed` or `error`

2. Frontend build
   - Command: `cd frontend && npm run build`
   - Required PASS tokens:
     - Exit code `0`
     - Output contains `Compiled successfully.`

3. Frontend copy guard
   - Command: `node scripts/check_frontend_copy_guard.js`
   - Required PASS tokens:
     - Exit code `0`
     - Output contains `COPY_GUARD_CHECK=PASS`

4. Prelaunch release gate (deterministic)
   - Command: `node scripts/check_prelaunch_release_gate.js`
   - Required PASS tokens:
     - Exit code `0`
     - Output contains `PRELAUNCH_RELEASE_GATE=PASS`

5. Stage-A runtime verifier (environment gate before release/cutover)
   - Command: `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh`
   - Required PASS tokens:
     - Exit code `0`
     - Output contains `[stage-a] RESULT=PASS`

## Guarded files/groups for curated staging

Stage only approved slice-owned files. Keep unrelated dirty-tree changes out of commits.

- Backend runtime/control group:
  - `backend/server.py`
  - `backend/services/claim_state.py`
- Backend test group:
  - `backend/tests/test_claim_state_unit.py`
  - `backend/tests/test_public_mode_unit.py`
- Frontend policy/copy group:
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
- Frontend Ops visibility group:
  - `frontend/src/pages/Ops.jsx`
- Strategy/docs group:
  - `docs/strategy/SOLO_FOUNDER_AUTONOMOUS_OPERATIONS_CONTROL_PACK.md`
  - `docs/strategy/PRELAUNCH_CHECKS_RUNBOOK.md`
  - `docs/strategy/melb_suburbs_abs_asgs_ed3_gccsa_2gmel_v1.meta.json`
  - `docs/strategy/IMPLEMENTATION_EVIDENCE_MANIFEST.md`
- Tooling guard group:
  - `scripts/check_frontend_copy_guard.js`
  - `scripts/check_prelaunch_release_gate.js`

## Approval gate

Do not sync, push, or merge until explicit owner approval is recorded for the curated staged set.

## Pre-sync readiness check command

- `node scripts/check_curated_staging_readiness.js`

## Pre-sync blockers (status-only)

- Curated files currently marked untracked must be intentionally staged before any approved sync.
- Current runtime baseline check target is `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` -> `RESULT=PASS` before sync.
