# Lock State Snapshot

Date: 2026-06-08
Project: `/Users/carlg/Documents/AI-Coding/dtd`

This file is runtime/governance snapshot evidence.
It does not override `docs/standards/SSOT.md` or `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`.
It must not be treated as the canonical route or page contract.

## Governance Locks

1. One-branch workflow on `main`, local-first with auto-sync.
2. Initial launch strategy is supply-first.
3. Launch phase/public emphasis must remain separate from `PUBLIC_MATCHING_ENABLED`; changes to public exposure or phase posture require explicit owner approval in `technical-owner mode`.
4. For the current supply-first launch phase, `PUBLIC_MATCHING_ENABLED` must remain `false`; enabling public live matching is deferred to a later controlled live-matching phase and is not part of the current launch scope.
5. `/ops` remains Normal Ops by default:
- no unrestricted admin CRUD
- no manual trainer matching as routine operation
- no manual routine billing
- no automatic phase switching
- no automatic enabling of `PUBLIC_MATCHING_ENABLED`
6. Core operating-data rule:
- `Database = truth`
- `/ops = readable operating view`
- `audit_log = decision trail`
- `CSV/export = proof only`
7. Operational ownership remains one-man and mode-based:
- primary operator owner is `carlg`
- `Monitor`, `Investigate`, and `Escalate` are operating modes within the same ownership model, not separate team roles
- escalation routes into `technical-owner mode` when the action crosses the hard boundary rule
8. Codex platform-interaction sync rules are governed by:
- `.codex/skill-policy.toml`
9. Operator-facing actions must satisfy the hard boundary rule in `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`:
- actions that can change locked runtime policy are always `technical-owner mode`
- only reversible, bounded, policy-safe actions may be treated as `operator mode`
10. The current prelaunch interpretation is locked as:
- a 30-day evidence-gathering window
- starting from the date the owner explicitly declares launch start
- `supply_first` throughout
- `PUBLIC_MATCHING_ENABLED=false` throughout
- no hard trainer-count or intro-ready-count cap required before the window starts

## Current Runtime / Implementation Locks

1. Oversight auth is passcode-based (`ADMIN_PASS`) for launch.
2. Public home-entry exposure is controlled by `PUBLIC_MATCHING_ENABLED`; latest live runtime evidence records `public_matching_enabled=false`.
3. Because the approved current launch phase is `supply_first`, public live matching remains intentionally unexposed in the current runtime.
4. Launch billing runtime defaults are intro-first with conversions on `track_only`; Stripe invoice collection is enabled when configured.
5. Region enforcement is active (`ACTIVE_REGION` / `ACTIVE_REGIONS`).
6. Consent checkpoints are required on match, intro, and submission flows.
7. Loop ownership is env-controlled:
- `AUTONOMY_LOOP_OWNER=api`: API owns loops
- `AUTONOMY_LOOP_OWNER=worker`: worker owns loops
- `AUTONOMY_LOOP_OWNER=none`: no process owns loops
- Legacy `RUN_AUTONOMY_IN_API=1|0` remains supported but cannot conflict with `AUTONOMY_LOOP_OWNER`
- DB lease lock `system_state.autonomy_loop_lease` ensures a single active executor across processes

## Current runtime evidence subset

This section records selected currently evidenced routes and loops only.
It is not a completeness claim and it is not the canonical route contract.

1. Selected currently evidenced surfaces:
- `/`
- `/trainers`
- `/ops`
2. Discovery source ingestion loop (`ingest_sources`) implemented.
3. T+7 outreach loop (`send_outreach`) implemented.

## Verification evidence (latest local run)

1. `python3 -m compileall backend` -> pass.
2. `cd backend && ../.venv/bin/pytest -q` -> pass (`115 passed, 12 skipped`).
3. `cd backend && ../.venv/bin/pytest -q tests/test_gap_closure_unit.py tests/test_w8_billing_unit.py tests/test_public_mode_unit.py` -> pass (`62 passed`).
4. `cd frontend && CI=true npm test -- --watch=false --runInBand` -> pass (`2 suites, 8 tests`).
5. `cd frontend && npm run build` -> pass (`Compiled successfully`).
6. `cd backend && ../.venv/bin/pytest -q tests/test_lifecycle_endpoints_unit.py tests/test_public_mode_unit.py` -> pass (`54 passed`).
7. `cd frontend && CI=true npm test -- --watch=false --runInBand` -> pass (`2 suites, 9 tests`).
8. `cd frontend && npm run build` -> pass (`Compiled successfully`) after operator-takeover UI updates.

## Launch evidence status (non-code configuration/evidence)

1. Public custom domains are intentionally withheld from final live use until launch trust is restored; they are not the current proof target.
2. The current safe hosted proof surface is `https://dtd-ten.vercel.app`.
3. Trust-restoration Phase 1 is complete:
- startup seeds are explicit opt-in and API-only
- `main` auto-sync is active again
- the hosted backend and safe frontend alias now reflect commit `12b049b8fb6ef06728a4dd6bd3f966f5e475ea4b`
4. Live runtime snapshot refreshed on `2026-06-08`:
- `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` -> `PASS`
- `https://dtd-api.onrender.com/api/config` -> `public_matching_enabled=false`, `public_launch_phase=supply_first`, `public_emphasis=waitlist_first`, `owner_waitlist_mode=passive_only`
- `https://dtd-api.onrender.com/api/oversight` -> current `/ops` read-model contract present, including:
  - `trainer_inventory`
  - `message_log`
  - `ops_cases`
  - `launch_phase_state`
  - `phase_readiness_snapshot`
- `https://dtd-ten.vercel.app/` -> `200`
- `https://dtd-ten.vercel.app/trainers` -> `200`
- `https://dtd-ten.vercel.app/ops` -> `200`
5. Hosted Phase 2 non-provider proof completed on `2026-06-08`:
- browser-driven landing and waitlist proof on `https://dtd-ten.vercel.app/lp/phase2-proof` persisted a hosted attribution cohort with:
  - `campaign=phase2-proof`
  - `source=lp`
  - `entry_events_30d=3`
  - `waitlist_joins_30d=1`
- hosted duplicate-path discovery proof accepted a pending candidate for `https://www.dogforce1.com.au`, then later moved hosted oversight from:
  - `pending=1, duplicate=0`
  - to `pending=0, duplicate=1`
- hosted discovery heartbeat then recorded:
  - `duplicates=1`
  - `handled=1`
  - `last_run=2026-06-07T18:44:10.935161+00:00`
- repeated hosted samples also showed elapsed-window loop continuity for:
  - `ranking`
  - `pricing`
  - `health`
  - `discovery`
6. Supply-first authority alignment is reflected across the current-truth docs listed in `docs/governance/CURRENT_TRUTH_INDEX.md`.
7. Matching-enabled release evidence remains intentionally open for later controlled live-matching work because the live runtime still reports `public_matching_enabled=false`.
8. Final Go/No-Go remains pending; this file does not record owner approval yet.

## Human gate snapshot (synced 2026-05-07)

1. `H-01` Domain + DNS + TLS finalization: `completed`.
2. `H-02` Platform secret readiness: `completed`.
3. `H-03` Legal copy sign-off: `completed`.
4. `H-04` Account/billing readiness: `completed`.

Evidence references:
1. `H-01` completed + live-domain state:
- `docs/governance/EXECUTION_STATUS.md` (append-only execution log and current runtime/infrastructure truth).
- `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` (active Vercel project identity and durable integration caveats).
2. `H-02` completed:
- `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` (platform inventory, environment mapping, verification command set).
3. `H-03` completed:
- this file ("Legal copy sign-off (H-03)" section below).
4. `H-04` completed:
- `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` (durable platform inventory and verification command set).

## Legal copy sign-off (H-03)

1. Approver: `carlg` (owner)
2. Date: `2026-05-02`
3. Scope approved:
- `/privacy`
- `/terms`
- `/trust`
- `/pricing`

## Update rule

If any governance, runtime, or route truth changes materially, update this file and `docs/governance/EXECUTION_STATUS.md` in the same commit.
If the authority hierarchy changes, update `docs/governance/CURRENT_TRUTH_INDEX.md` and `docs/governance/EXECUTION_STATUS.md` in the same session.
If any gate/status value changes, append a matching command/file evidence entry in `docs/governance/EXECUTION_STATUS.md` execution log in the same session.
If Codex interaction protocols are updated, update `.codex/skill-policy.toml` in the same commit.
