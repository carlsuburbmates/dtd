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
2. API process currently schedules autonomy loops at startup in `backend/server.py`.
3. Dedicated worker exists in `backend/worker.py`.
4. Matching/scoring is deterministic heuristic in `backend/services/ai.py`.
5. Stage A verifier exists at `scripts/verify_stage_a_runtime.sh`.

### Infrastructure reality

1. Accounts/keys exist for Clerk, Sentry, PostHog, Resend, Render, Atlas, Vercel.
2. Runtime and evidence snapshots for Stage A/B/C were captured in prior runbook entries.
3. Stage D (edge/domain evidence) and Stage E (deploy automation evidence) are still open.

## Priority Order (next work)

### P0 - Governance and architecture alignment

1. Confirm auth target for launch:
- Option A: keep passcode-only oversight for launch.
- Option B: migrate to Clerk-backed oversight before launch.

2. Confirm loop ownership model:
- Option A: API-only loop ownership.
- Option B: worker-only loop ownership.
- Option C: dual process with explicit partitioning.

3. Lock launch billing behavior in code:
- Intro-first billing behavior only.
- Conversion billing remains disabled or track-only unless explicitly enabled.

Done when:
1. Docs and code describe the same auth model.
2. Docs and code describe the same loop ownership model.
3. Billing behavior is explicit and test-verified.

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

## Gate Rule

No launch gate advancement claims unless the required evidence for the current stage is documented in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.

## Verification Requirements

1. No roadmap item is complete without objective pass/fail criteria.
2. No policy claim without code or command evidence.
3. No doc references to non-existent files.
