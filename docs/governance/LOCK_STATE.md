# Lock State Snapshot

Date: 2026-05-07
Project: `/Users/carlg/Documents/AI-Coding/dtd`

## Locked decisions (active)

1. One-branch workflow on `main`, local-first with auto-sync.
2. Oversight auth is passcode-based (`ADMIN_PASS`) for launch.
3. Launch billing model is intro-first; conversions default to `track_only`; Stripe invoice collection is enabled when configured.
4. Region enforcement is active (`ACTIVE_REGION` / `ACTIVE_REGIONS`).
5. Consent checkpoints are required on match, intro, and submission flows.
6. Loop ownership is env-controlled:
- `AUTONOMY_LOOP_OWNER=api`: API owns loops
- `AUTONOMY_LOOP_OWNER=worker`: worker owns loops
- `AUTONOMY_LOOP_OWNER=none`: no process owns loops
- Legacy `RUN_AUTONOMY_IN_API=1|0` remains supported but cannot conflict with `AUTONOMY_LOOP_OWNER`
- DB lease lock `system_state.autonomy_loop_lease` ensures a single active executor across processes
7. Codex platform-interaction sync rules are governed by:
- `docs/governance/CODEX_PLATFORM_SYNC.md`

## Implemented completion blocks

1. Public/trainer website IA routes:
- `/`, `/how-it-works`, `/about`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`
- `/trainers`, `/submit`, `/t/:id`, `/ops`
2. Discovery source ingestion loop (`ingest_sources`) implemented.
3. T+7 outreach loop (`send_outreach`) implemented.

## Verification evidence (latest local run)

1. `python3 -m compileall backend` → pass.
2. `npm --prefix frontend run build` → pass.
3. `python -m pytest -q backend/tests` → pass (`45 passed`).

## Launch evidence status (non-code configuration/evidence)

1. Public custom domains are attached and live. Reattach evidence is recorded in the execution log and runbook.
2. Stage D evidence pack is complete (domain/TLS/edge).
3. Stage E evidence pack is complete (repeatable deploy/redeploy and route smoke are evidenced).
4. Runtime loop-output reasons are cleared in live checks; `source_ingestion.failed_sources=1` remains only as historical count until the next successful cycle.

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

If any governance, runtime, or route truth changes, update this file and `ROADMAP.md` in the same commit.
If any gate/status value changes, append a matching command/file evidence entry in `docs/governance/NEXT_SESSION_HANDOFF.md` execution log in the same session.
If Codex interaction protocols are updated from the global feed, update `docs/governance/CODEX_PLATFORM_SYNC.md` in the same commit.
