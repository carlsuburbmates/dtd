# Lock State Snapshot

Date: 2026-05-02  
Project: `/Users/carlg/Documents/AI-Coding/dtd`

## Locked decisions (active)

1. One-branch workflow on `main`, local-first with auto-sync.
2. Oversight auth is passcode-based (`ADMIN_PASS`) for launch.
3. Launch billing model is intro-first; conversions default to `track_only`.
4. Region enforcement is active (`ACTIVE_REGION` / `ACTIVE_REGIONS`).
5. Consent checkpoints are required on match, intro, and submission flows.
6. Loop ownership is env-controlled:
- `RUN_AUTONOMY_IN_API=1`: API owns loops
- `RUN_AUTONOMY_IN_API=0`: worker owns loops

## Implemented completion blocks

1. Public/trainer website IA routes:
- `/`, `/how-it-works`, `/about`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`
- `/trainers`, `/submit`, `/t/:id`, `/ops`
2. Discovery source ingestion loop (`ingest_sources`) implemented.
3. T+7 outreach loop (`send_outreach`) implemented.

## Verification evidence (latest local run)

1. `python3 -m compileall backend` → pass.
2. `npm --prefix frontend run build` → pass.
3. Backend pytest is not runnable in this host runtime unless `pytest` is installed in the active Python environment.

## Open completion gates (non-code configuration/evidence)

1. Public custom domains are intentionally detached and currently return `404 DEPLOYMENT_NOT_FOUND`; this is an intentional development hold and is not a blocker for ongoing build work. Reattach evidence is required before public launch.
2. Stage D evidence pack completion (post-reattach domain/TLS/edge) in runbook.
3. Stage E evidence pack is partially complete: redeploy repeatability is evidenced, but anonymous route checks are blocked by Vercel deployment protection (`HTTP 401`) and must be verified once protection is relaxed for smoke checks.

## Human gate snapshot (synced 2026-05-02)

1. `H-01` Domain + DNS + TLS finalization: `open` (final cutover step).
2. `H-02` Platform secret readiness: `completed`.
3. `H-03` Legal copy sign-off: `completed`.
4. `H-04` Account/billing readiness: `completed`.

Evidence references:
1. `H-01` open + intentional detached-domain hold:
- `docs/governance/NEXT_SESSION_HANDOFF.md` ("Execution log", current session `curl -I` checks on apex + `www` returning `404` with `x-vercel-error: DEPLOYMENT_NOT_FOUND`).
- `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("Current lock", item 3 and open stages item 4).
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

If any governance, runtime, or route truth changes, update this file and `ROADMAP.md` in the same commit.
If any gate/status value changes, append a matching command/file evidence entry in `docs/governance/NEXT_SESSION_HANDOFF.md` execution log in the same session.
