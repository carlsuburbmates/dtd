# Prelaunch Checks Runbook

Purpose: deterministic prelaunch verification sequence with exact commands and PASS criteria.

## Command order

1. Backend targeted tests
   - Command:
     - `cd backend && ../.venv/bin/python -m pytest -q tests/test_claim_state_unit.py tests/test_public_mode_unit.py`
   - PASS criteria:
     - Exit code `0`
     - Output contains `passed`
     - Output does not contain `failed` or `error`

2. Frontend build
   - Command:
     - `cd frontend && npm run build`
   - PASS criteria:
     - Exit code `0`
     - Output contains `Compiled successfully.`

3. Frontend copy guard
   - Command:
     - `node scripts/check_frontend_copy_guard.js`
   - PASS criteria:
     - Exit code `0`
     - Output contains `COPY_GUARD_CHECK=PASS`

4. Release gate verification
   - Command:
     - `node scripts/check_prelaunch_release_gate.js`
   - PASS criteria:
     - Exit code `0`
     - Output contains `PRELAUNCH_RELEASE_GATE=PASS`
   - Note:
     - This is the deterministic code/config gate. Run `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` separately before any release/cutover decision.

## Failure handling

If any step fails:
- Stop the run.
- Record the failing command and failing token.
- Do not proceed to release/cutover decisions.

## Pre-sync readiness check command

- `node scripts/check_curated_staging_readiness.js`
