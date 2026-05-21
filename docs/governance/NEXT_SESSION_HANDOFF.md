# Next Session Handoff

Date: 2026-05-20
Repo: `/Users/carlg/Documents/AI-Coding/dtd`

## Objective

Continue development and launch-readiness work without reopening resolved governance decisions or relying on stale historical notes.

## Authority Order (current)

1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/governance/CURRENT_TRUTH_INDEX.md`
4. `docs/governance/LOCK_STATE.md`
5. `docs/governance/ROADMAP.md`
6. current repository state on `main`

If any conflict appears, follow this order.

## Live Gate Table (current truth)

Last updated: 2026-05-20

| Gate | Status | Source of truth |
|---|---|---|
| H-01 Domain + DNS + TLS | completed | `docs/governance/LOCK_STATE.md` |
| H-02 Platform secret readiness | completed | `docs/governance/LOCK_STATE.md` |
| H-03 Legal copy sign-off | completed | `docs/governance/LOCK_STATE.md` |
| H-04 Account/billing readiness | completed | `docs/governance/LOCK_STATE.md` |
| Final Go/No-Go | pending | current release-evidence session |

Final Go/No-Go approver: owner (`carlg`).

## Current Runtime Truth

1. Public home entry is mode-gated by `PUBLIC_MATCHING_ENABLED`:
- `false`: owner waitlist flow is primary on `/`.
- `true`: live matching flow is primary on `/`.
2. Matching/contact lifecycle APIs remain implemented regardless of home-entry mode gate.
3. Loop ownership is controlled by `AUTONOMY_LOOP_OWNER` (`api|worker|none`) with DB lease guard (`system_state.autonomy_loop_lease`).
4. Intro billing path is Stripe-backed when configured; launch conversion mode defaults to `track_only`.

## Mandatory Session-Start Protocol

1. Capture HEAD: `git rev-parse --short HEAD`.
2. Confirm branch and working-tree intent (`main` plus any local staged/unstaged scope).
3. Re-read authority docs listed above.
4. If a gate/status is changed, update all three in the same session:
- `docs/governance/LOCK_STATE.md`
- `docs/governance/ROADMAP.md`
- this file
5. Record evidence for each status change (command result and/or file reference).

## Evidence Logging Standard

For each status-affecting session entry, append:
1. UTC timestamp.
2. session-start HEAD.
3. what status changed.
4. evidence reference.

## Active Risks / Open Work

1. Final Go/No-Go remains pending by policy.
2. Workflow completeness is closed at trace-sheet level; maintain via regression checks and evidence sync:
- `docs/WORKFLOW_TRACE_SHEET.md`
- `docs/USER_WORKFLOWS.md`
3. Keep monetization copy and runtime model aligned to ADR:
- `docs/governance/ADR-0001-runtime-canonical-mode.md`
4. Remaining launch and operator-takeover work is tracked in the strict ordered checklist in `docs/governance/ROADMAP.md` (`Remaining Completion Checklist (strict order)`); as of `2026-05-21`, `Must-Finish Before Launch` has no open implementation blockers and remaining launch work begins at `Post-Feature Launch Verification`.
5. The final live-verification and `Final Go/No-Go` steps are intentionally deferred to the `Post-Feature Launch Verification` block in `docs/governance/ROADMAP.md`; do not treat them as current feature work.
6. Local code/test/doc gaps for operator-takeover, security coverage, and roadmap-authority alignment were closed on `2026-05-21`; remaining launch blockers are now live-evidence / mode-lock / owner-decision items.

## Append-Only Execution Log (current era)

1. `2026-05-20` — Governance handoff canonicalized to current-truth format.
- Removed stale mixed-era gate logs that contradicted current completed gate table.
- Evidence: rewrite of this file + authority-order alignment with `CURRENT_TRUTH_INDEX.md` and `LOCK_STATE.md`.
2. `2026-05-20` — Workflow evidence updated for W17 and W18.
- Promoted `W17` and `W18` to `complete` after adding deterministic billing-recovery/status-path coverage and aligning workflow/operations docs.
- Evidence: `backend/server.py`, `backend/tests/test_lifecycle_endpoints_unit.py`, `backend/tests/test_gap_closure_unit.py`, `docs/WORKFLOW_TRACE_SHEET.md`, `docs/USER_WORKFLOWS.md`, `docs/OPERATIONS.md`, targeted pytest pass recorded in `LOCK_STATE.md`.
3. `2026-05-20` — Workflow evidence updated for W3, W15, W16, and W19.
- Promoted `W3`, `W15`, `W16`, and `W19` to `complete` after adding engagement/attribution/reporting evidence, exposing growth and reactivation summaries in `/ops`, and formalizing reactivation success thresholds.
- Evidence: `backend/tests/test_gap_closure_unit.py`, `backend/tests/test_public_mode_unit.py`, `frontend/src/lib/api.js`, `frontend/src/lib/api.test.js`, `frontend/src/pages/CampaignLanding.jsx`, `frontend/src/pages/SuburbSEO.jsx`, `frontend/src/pages/Ops.jsx`, `docs/WORKFLOW_TRACE_SHEET.md`, `docs/USER_WORKFLOWS.md`, `docs/OPERATIONS.md`, `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, updated test/build results in `LOCK_STATE.md`.
4. `2026-05-20T13:16:32Z` — Workflow evidence updated for W8 and W13; workflow trace fully closed.
- Session-start HEAD: `8b9dc81`.
- Promoted `W8` and `W13` to `complete` after adding explicit webhook/oversight lifecycle evidence for billing and heartbeat/recovery evidence for discovery/source-ingestion.
- Evidence: `backend/tests/test_w8_billing_unit.py`, `backend/tests/test_public_mode_unit.py`, `backend/tests/test_gap_closure_unit.py`, `backend/services/automation.py`, `backend/services/engine.py`, `docs/WORKFLOW_TRACE_SHEET.md`, `docs/USER_WORKFLOWS.md`, `docs/governance/ROADMAP.md`, `docs/governance/LOCK_STATE.md`.
5. `2026-05-21T07:08:57Z` — Launch-checklist local implementation pass completed; live runtime sampled.
- Session-start HEAD: `8b9dc81`.
- Status changes in this entry:
  - closed local security-test gaps for oversight lockout and trainer action-token negative paths,
  - upgraded `/ops` and trainer lifecycle surfaces toward the bounded operator-takeover model,
  - aligned support routing to the single-mailbox policy,
  - refreshed live runtime evidence for current prelaunch mode.
- Evidence:
  - backend tests: `cd backend && ../.venv/bin/pytest -q tests/test_lifecycle_endpoints_unit.py tests/test_public_mode_unit.py` -> `54 passed`.
  - frontend tests: `cd frontend && CI=true npm test -- --watch=false --runInBand` -> `2 suites, 9 tests`.
  - frontend build: `cd frontend && npm run build` -> `Compiled successfully`.
  - live config: `curl -sS https://dtd-api.onrender.com/api/config` -> `public_matching_enabled=false`, `conversion_billing_mode=track_only`.
  - live oversight: `curl -sS -H "X-Admin-Pass: change-me" https://dtd-api.onrender.com/api/oversight` -> no `severity:high` alerts in sampled snapshot; loop heartbeats present.
  - Vercel route smoke: `vercel curl / --deployment dtd-oomq80e9u-carlitos-projects-a62ff78f.vercel.app`, `vercel curl /trainers --deployment dtd-oomq80e9u-carlitos-projects-a62ff78f.vercel.app`, `vercel curl /ops --deployment dtd-oomq80e9u-carlitos-projects-a62ff78f.vercel.app` -> HTML returned.
  - files: `backend/server.py`, `backend/tests/test_lifecycle_endpoints_unit.py`, `backend/tests/test_public_mode_unit.py`, `frontend/src/lib/api.js`, `frontend/src/lib/api.test.js`, `frontend/src/pages/Ops.jsx`, `frontend/src/pages/SubmitStatus.jsx`, `frontend/src/pages/TrainerBilling.jsx`, `frontend/src/pages/TrainerReactivate.jsx`, `frontend/src/pages/Contact.jsx`, `docs/OPERATIONS.md`, `docs/DEPLOYMENT.md`, `docs/governance/LOCK_STATE.md`, `docs/governance/ROADMAP.md`, this file.
6. `2026-05-21T08:12:31Z` — Roadmap-authority closeout completed; remaining open work reduced to final live verification.
- Session-start HEAD: `8b9dc81`.
- Status changes in this entry:
  - retired the obsolete roadmap-gap tracker after the roadmap was normalized to current authority order and current-state launch sequencing,
  - updated the handoff/open-work view so `Must-Finish Before Launch` is explicitly clear and the remaining launch work starts at `Post-Feature Launch Verification`.
- Evidence:
  - files: `docs/governance/ROADMAP.md`, `docs/governance/LOCK_STATE.md`, this file.
