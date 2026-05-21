# ADR-0001: Runtime Canonical Mode
Date: 2026-05-20
Status: accepted
Approver: owner (`carlg`)

## Context
Active docs had drifted across monetization, auth defaults, and loop-owner configuration, creating repeated redesign cycles.

## Decision
1. Canonical monetization runtime is intro-first billing with `CONVERSION_BILLING_MODE=track_only` as launch default.
2. Canonical oversight auth runtime is passcode-based (`ADMIN_PASS`) in current lock state.
3. Canonical loop-owner control is `AUTONOMY_LOOP_OWNER`; `RUN_AUTONOMY_IN_API` is legacy compatibility only.
4. Public matching exposure is controlled by `PUBLIC_MATCHING_ENABLED` and must align across backend, frontend, and tests.

## Consequences
1. Docs and examples must treat this ADR as current truth until superseded.
2. Any migration to subscription-first billing or auth replacement requires explicit owner approval and a new ADR.

## Supersedes
1. Stale strategy references to subscription-first prelaunch as active canonical mode.
2. Legacy setup guidance that treated `RUN_AUTONOMY_IN_API` as primary owner control.
