# Lock State Snapshot

Date: 2026-05-22
Project: `/Users/carlg/Documents/AI-Coding/dtd`

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
- `docs/governance/CODEX_PLATFORM_SYNC.md`
9. Operator-facing actions must satisfy the hard boundary rule in `docs/OPERATIONS.md`:
- actions that can change locked runtime policy are always `technical-owner mode`
- only reversible, bounded, policy-safe actions may be treated as `operator mode`

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

## Implemented completion blocks

1. Public/trainer website IA routes:
- `/`, `/how-it-works`, `/about`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`
- `/trainers`, `/submit`, `/t/:id`, `/ops`
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

1. Public custom domains are attached and live. Reattach evidence is recorded in the execution log and runbook.
2. Stage D evidence pack is complete (domain/TLS/edge).
3. Stage E evidence pack is complete (repeatable deploy/redeploy and route smoke are evidenced).
4. Runtime loop-output reasons are cleared in live checks; `source_ingestion.failed_sources=1` remains only as historical count until the next successful cycle.
5. Live runtime snapshot refreshed on `2026-05-21T07:08:57Z`:
- `curl -sS https://dtd-api.onrender.com/api/config` -> `public_matching_enabled=false`, `conversion_billing_mode=track_only`.
- `curl -sS -H "X-Admin-Pass: change-me" https://dtd-api.onrender.com/api/oversight` -> loops present and current; no unresolved `severity:high` alerts in the sampled snapshot; one medium `fraud_suppressed` alert remains.
- `vercel curl / --deployment dtd-oomq80e9u-carlitos-projects-a62ff78f.vercel.app` -> HTML returned.
- `vercel curl /trainers --deployment dtd-oomq80e9u-carlitos-projects-a62ff78f.vercel.app` -> HTML returned.
- `vercel curl /ops --deployment dtd-oomq80e9u-carlitos-projects-a62ff78f.vercel.app` -> HTML returned.
6. Local implementation/closeout work is currently clear: roadmap-authority alignment is closed and `docs/governance/ROADMAP.md` no longer carries open `Must-Finish Before Launch` blockers.
7. Supply-first authority alignment is now reflected across the current-truth docs listed in `docs/governance/CURRENT_TRUTH_INDEX.md`; this docs-only pass did not change runtime behavior.
8. Supply-first launch verification still requires explicit phase/readiness/decision evidence, or clearly documented equivalent persisted phase-state evidence, where that is not yet shown in runtime evidence.
9. Matching-enabled release evidence remains intentionally open for later controlled live-matching work because the live runtime still reports `public_matching_enabled=false`.
10. Final Go/No-Go remains pending; this file does not record owner approval yet.

## Human gate snapshot (synced 2026-05-07)

1. `H-01` Domain + DNS + TLS finalization: `completed`.
2. `H-02` Platform secret readiness: `completed`.
3. `H-03` Legal copy sign-off: `completed`.
4. `H-04` Account/billing readiness: `completed`.

Evidence references:
1. `H-01` completed + live-domain state:
- `docs/governance/NEXT_SESSION_HANDOFF.md` ("Execution log", current session `vercel alias ls` and `curl -I` checks on apex + `www` returning `307`/`200`).
- `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("Current lock", item 3 and Stage D/E complete evidence).
2. `H-02` completed:
- `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("H-02 readiness snapshot", items 1-4).
3. `H-03` completed:
- this file ("Legal copy sign-off (H-03)" section below).
4. `H-04` completed:
- `docs/governance/H04_VERIFICATION_REPORT.json`.
- `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("H-04 platform readiness snapshot").

## Legal copy sign-off (H-03)

1. Approver: `carlg` (owner)
2. Date: `2026-05-02`
3. Scope approved:
- `/privacy`
- `/terms`
- `/trust`
- `/pricing`

## Update rule

If any governance, runtime, or route truth changes materially, update this file and `ROADMAP.md` in the same commit.
If the authority hierarchy changes, update `docs/governance/CURRENT_TRUTH_INDEX.md` and `docs/governance/NEXT_SESSION_HANDOFF.md` in the same session.
If any gate/status value changes, append a matching command/file evidence entry in `docs/governance/NEXT_SESSION_HANDOFF.md` execution log in the same session.
If Codex interaction protocols are updated from the global feed, update `docs/governance/CODEX_PLATFORM_SYNC.md` in the same commit.
