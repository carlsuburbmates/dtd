# Roadmap

Rule: current-state only. Keep this file aligned to the code and infra that actually exist.
Execution handoff reference: `docs/governance/NEXT_SESSION_HANDOFF.md`.
Status updates in this file must include evidence references.

## Goal

Launch Bark&Bond in Greater Melbourne with:
1. One input -> best matches.
2. Intro-first commercial model.
3. Automation-first operations with minimal manual overhead.

## Operating Model (locked for now)

1. One-man workflow.
2. One branch only: `main`.
3. Local project is the source of truth for development: `/Users/carlg/Documents/AI-Coding/dtd`.
4. Remote `main` stays synced to local `main`.
5. No required PR review gate.
6. No archive docs. Update or delete in place when truth changes.

## Current System Truth (2026-05-02)

### Code reality

1. Backend oversight auth currently uses `ADMIN_PASS` (`X-Admin-Pass`) in `backend/server.py`.
2. Loop ownership is explicit:
- `AUTONOMY_LOOP_OWNER=api` = API owns loops.
- `AUTONOMY_LOOP_OWNER=worker` = worker owns loops.
- `AUTONOMY_LOOP_OWNER=none` = loops disabled by ownership contract.
- Legacy `RUN_AUTONOMY_IN_API=1|0` is supported but cannot conflict with `AUTONOMY_LOOP_OWNER`.
3. Loop execution is lease-guarded in DB (`system_state.autonomy_loop_lease`) so only one live process executes loops at a time.
4. Active scope is region-gated via `ACTIVE_REGION` / `ACTIVE_REGIONS`.
5. Consent checkpoints are enforced on `/match`, `/intros`, and `/submissions`.
6. Intro idempotency is enforced via `Idempotency-Key` / `client_token`.
7. Conversion billing defaults to `CONVERSION_BILLING_MODE=track_only` (bill-mode is feature-flagged).
8. Intro billing collection path is Stripe invoice-based when configured (`STRIPE_SECRET_KEY` + webhook reconciliation).
9. Matching/scoring is deterministic heuristic in `backend/services/ai.py`.
10. Source-ingestion loop and T+7 outreach loop are implemented in `backend/services/automation.py` and scheduled by engine.
11. Stage A verifier exists at `scripts/verify_stage_a_runtime.sh`.

### Infrastructure reality

1. Accounts/keys exist for Clerk, Sentry, PostHog, Resend, Render, Atlas, Vercel.
2. Runtime and evidence snapshots for Stage A/B/C were captured in prior runbook entries.
3. Vercel project migration to `dtd` is complete and frontend runtime vars are set for prod/preview (`REACT_APP_BACKEND_URL`, `REACT_APP_POSTHOG_KEY`, `REACT_APP_POSTHOG_HOST`, plus `NEXT_PUBLIC_POSTHOG_*` parity keys).
4. Custom domains are attached and live; public hostnames return `307` apex redirect to `www` and `200` on `www` and `/trainers`.
5. Stage D evidence is complete (migration + routing + domain reattach/TLS/edge validation).
6. Stage E (deploy automation evidence) is complete; repeatable deploy/redeploy evidence and authenticated route smoke both pass.
7. H-03 legal copy sign-off and H-04 platform readiness verification are completed and recorded in governance docs/runbook.
8. Latest live runtime snapshot has cleared loop reasons after secret verification/redeploys; `source_ingestion.failed_sources=1` remains only as a historical count until the next successful ingestion cycle.

Evidence references for infrastructure status:
1. Stage D/E complete state: `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("Current lock", items 3-4 and "Stage D/E (complete)").
2. H-04 completion: `docs/governance/H04_VERIFICATION_REPORT.json`.
3. Current live-domain state: `docs/governance/NEXT_SESSION_HANDOFF.md` ("Execution log", current session alias mapping + `curl -I` checks).

## Priority Order (next work)

### P0 - Governance and architecture alignment

Status: completed.
Evidence references:
1. Oversight auth and scope/consent enforcement: `backend/server.py`.
2. Loop-ownership guard + lease contract: `backend/services/runtime_control.py`, `backend/worker.py`, `backend/services/engine.py`.
3. Launch billing default and conversion handling: `backend/services/engine.py` (`CONVERSION_BILLING_MODE` default) and `backend/server.py` (`/api/conversions`).

Locked decisions now implemented:
1. Launch auth: passcode-only oversight (`ADMIN_PASS`), no Clerk enforcement on backend.
2. Loop ownership: explicit env-controlled ownership to prevent duplicate loop scheduling.
3. Launch billing: intro-first; conversions tracked by default.
4. Scope: region-based enforcement with one active region set.
5. Consent: required before matching, contact reveal, and submission publish path.

### P1 - Launch-readiness evidence completion

Status: completed.

1. Stage D evidence pack:
- Command-level domain/TLS/edge proof is recorded in the runbook and execution log.

2. Stage E evidence pack:
- Repeatable deploy/redeploy path has command-level proof (`dpl_CBoYcSJxiJprePuwDjUaQaLp9k5H` then `dpl_AD5Kghob4aQNHcAFVQyWwNoq373K`), and authenticated deployment-route smoke verifies required routes render (`HTTP 200` via `vercel curl`).

Done when:
1. Stage D and Stage E both have command-level evidence in runbook.
2. Public domains are attached and return live launch responses.
3. The session that changed P1 status appended matching evidence entries in `docs/governance/NEXT_SESSION_HANDOFF.md` execution log.

### P2 - Controlled go-live

1. Run production in intro-first mode with conservative safeguards.
2. Observe intro event quality, suppression patterns, and incident trends.
3. Tune thresholds/policies only with explicit evidence updates in docs.

### P3 - Website completion (public + trainer UX only)

Status: completed (IA/routes/UX baseline complete; does not imply business workflow completeness).
Evidence references:
1. Route map: `frontend/src/App.js`.
2. Build-pass record: `docs/governance/LOCK_STATE.md` ("Verification evidence", compileall + frontend build pass).

1. Public information architecture must be complete and navigable:
- `/` (match flow + product pillars)
- `/how-it-works`
- `/about`
- `/pricing`
- `/trust`
- `/faq`
- `/contact`
- `/privacy`
- `/terms`

2. Trainer-facing architecture must be complete:
- `/trainers` (model, economics, process)
- `/submit` (consented submission flow)
- `/t/:id` (consented contact-release flow)

3. Cross-surface UX consistency:
- Shared public header/footer/nav and legal links.
- Readable mobile + desktop layout.
- Data-testids present for key interactive controls.

Done when:
1. All listed routes exist and render.
2. Primary CTAs are wired and non-dead.
3. Frontend build passes in CI/local.

### P4 - Business workflow completeness (demand/supply/revenue lifecycle)

Status: in progress.

Evidence gates:
1. `docs/USER_WORKFLOWS.md` includes `W1-W19` with demand generation, onboarding completion, and revenue recovery workflows.
2. `docs/WORKFLOW_TRACE_SHEET.md` assigns explicit status (`complete|partial|planned|missing`) for each workflow.
3. Oversight KPI semantics separate booked revenue from collected/at-risk collection outcomes.
4. Operations runbook defines KPI meanings with no terminology conflicts.

Done when:
1. All `R1-R6` recommendations in `SESSION_IMPLEMENTATION_REPORT_2026-05-08.md` are implemented or explicitly closed with evidence.
2. No remaining contradictions between roadmap claims and workflow/operations evidence.

## Repo Task Backlog (codebase-derived)

1. Stage D evidence capture: completed and recorded in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.
2. Stage E deploy/redeploy evidence capture: completed and recorded in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.
3. Public custom domains: reattached and verified live; no open domain/TLS evidence task remains.
4. Remaining launch work is non-domain only and should be driven by new evidence, not by stale backlog entries.

## Gate Rule

No launch gate advancement claims unless the required evidence for the current stage is documented in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.
Current lock snapshot must also be reflected in `LOCK_STATE.md`.
Any gate status change in this roadmap must also include a matching execution-log evidence entry in `NEXT_SESSION_HANDOFF.md`.

## Verification Requirements

1. No roadmap item is complete without objective pass/fail criteria.
2. No policy claim without code or command evidence.
3. No doc references to non-existent files.
