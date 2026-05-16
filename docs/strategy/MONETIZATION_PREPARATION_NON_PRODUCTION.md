# Monetization Preparation (Non-Production Only)

Date: 2026-05-17
Status: preparation only (activation blocked)

## Objective

Prepare a safe, reversible monetization transition path without enabling production charging.

## Explicitly blocked

1. Production subscription billing activation.
2. Deleting old intro-fee paths without migration/rollback.
3. Charging trainers as part of this phase.

## Current legacy fee path inventory

1. Runtime fee configuration references:
   - `backend/services/engine.py` (`FIXED_INTRO_FEE_CENTS`, pricing loop)
   - `backend/server.py` (intro fee snapshot fields)
2. Billing service references:
   - `backend/services/stripe_billing.py` (invoice descriptions and reconciliation)
3. Public policy language:
   - `frontend/src/lib/publicPolicy.js` (per-intro fee consent copy)
4. Governance/docs references:
   - `docs/OPERATIONS.md`, `docs/DEPLOYMENT.md`, `docs/ARCHITECTURE.md`, governance runbooks

## Preparation work completed

1. Inventory documented and retained (no deletion).
2. Public copy remains prelaunch-safe and non-activation oriented.
3. No backend mutation was performed in this phase.

## Safe next steps (when explicitly approved)

1. Define subscription lifecycle states and transitions in docs first.
2. Add migration flags for old/new billing paths before any cutover.
3. Add rollback criteria and rollback runbook.
4. Run non-production-only validation before any production decision.
