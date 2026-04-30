# Roadmap

Rule: current-state only. Keep this file aligned to the code and infra that actually exist.

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

## Current System Truth (2026-05-01)

### Code reality

1. Backend oversight auth currently uses `ADMIN_PASS` (`X-Admin-Pass`) in `backend/server.py`.
2. Loop ownership is explicit:
- `RUN_AUTONOMY_IN_API=1` = API owns loops.
- `RUN_AUTONOMY_IN_API=0` = worker owns loops.
3. Active scope is region-gated via `ACTIVE_REGION` / `ACTIVE_REGIONS`.
4. Consent checkpoints are enforced on `/match`, `/intros`, and `/submissions`.
5. Intro idempotency is enforced via `Idempotency-Key` / `client_token`.
6. Conversion billing defaults to `CONVERSION_BILLING_MODE=track_only` (bill-mode is feature-flagged).
7. Matching/scoring is deterministic heuristic in `backend/services/ai.py`.
8. Stage A verifier exists at `scripts/verify_stage_a_runtime.sh`.

### Infrastructure reality

1. Accounts/keys exist for Clerk, Sentry, PostHog, Resend, Render, Atlas, Vercel.
2. Runtime and evidence snapshots for Stage A/B/C were captured in prior runbook entries.
3. Stage D (edge/domain evidence) and Stage E (deploy automation evidence) are still open.

## Priority Order (next work)

### P0 - Governance and architecture alignment

Status: completed.

Locked decisions now implemented:
1. Launch auth: passcode-only oversight (`ADMIN_PASS`), no Clerk enforcement on backend.
2. Loop ownership: explicit env-controlled ownership to prevent duplicate loop scheduling.
3. Launch billing: intro-first; conversions tracked by default.
4. Scope: region-based enforcement with one active region set.
5. Consent: required before matching, contact reveal, and submission publish path.

### P1 - Launch-readiness evidence completion

1. Stage D evidence pack:
- Vercel domain/TLS/edge controls configured and recorded.

2. Stage E evidence pack:
- Repeatable deploy/redeploy path documented and test-run.

Done when:
1. Stage D and Stage E both have command-level evidence in runbook.

### P2 - Controlled go-live

1. Run production in intro-first mode with conservative safeguards.
2. Observe intro event quality, suppression patterns, and incident trends.
3. Tune thresholds/policies only with explicit evidence updates in docs.

## Repo Task Backlog (codebase-derived)

1. Implement Stage D evidence capture in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.
2. Implement Stage E deploy/redeploy evidence capture in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.
3. Add real discovery ingestion worker input source (currently seeded queue + public endpoint only).
4. Add outbound T+7d conversion-prompt workflow (Resend pipeline).

## Gate Rule

No launch gate advancement claims unless the required evidence for the current stage is documented in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.

## Verification Requirements

1. No roadmap item is complete without objective pass/fail criteria.
2. No policy claim without code or command evidence.
3. No doc references to non-existent files.
