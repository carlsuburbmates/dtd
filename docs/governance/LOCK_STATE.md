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

1. Public custom domains are intentionally detached and currently return `404 DEPLOYMENT_NOT_FOUND`; reattach decision + evidence is required before launch.
2. Stage D evidence pack completion (post-reattach domain/TLS/edge) in runbook.
3. Stage E evidence pack (repeatable deploy/redeploy) in runbook.
4. Configure and verify:
- `DISCOVERY_SOURCE_URLS`
- `RESEND_API_KEY`
- `RESEND_FROM`

## Update rule

If any governance, runtime, or route truth changes, update this file and `ROADMAP.md` in the same commit.
