# Integration Credentials Runbook

Purpose: keep credentials ownership, environment mapping, and integration
verification simple for the one-man DTD workflow.

This file owns:
1. env-file inventory
2. env ownership rules
3. required variable map
4. verification command set
5. durable integration caveats

It does not own:
1. current project status
2. live launch readiness claims
3. session handoff logic
4. dated execution logs
5. the canonical integration inventory

Canonical integration inventory:
1. `docs/governance/CANONICAL_INTEGRATIONS.md`

## Local Env File Inventory

These are the env files currently expected in the repo layout:
1. root `.env` — repo-level verification/operator values
2. root `.env.example` — committed placeholder map for root `.env`
3. `backend/.env` — local-only backend runtime values
4. `backend/.env.example` — committed placeholder map for backend runtime
5. `frontend/.env` — local-only frontend runtime values
6. `frontend/.env.example` — committed placeholder map for frontend runtime

Rules:
1. real `.env` files stay local only and remain gitignored
2. committed `*.env.example` files contain placeholders/defaults only
3. if current code or verification scripts use an env var, it must be represented in an example file or in this runbook
4. legacy local-only keys may exist, but they are not required unless current code or verification scripts still use them

## Env Ownership Standard

Use this split consistently:
1. `backend/.env` — authoritative backend runtime config
2. `frontend/.env` — frontend-only runtime config
3. root `.env` — repo-level verification and operator tooling config

Ownership rule:
1. if backend code reads it, put it in `backend/.env`
2. if frontend code reads it, put it in `frontend/.env`
3. if repo scripts or verification tooling use it, put it in root `.env`

## Canonical Platform Inventory Pointer

The platform inventory now lives in:
1. `docs/governance/CANONICAL_INTEGRATIONS.md`

Use this runbook for:
1. env ownership
2. credential storage rules
3. verification caveats
4. command-level verification workflow

Use the canonical integrations file for:
1. platform list
2. verified identifiers
3. account/project/service clues
4. integration status classification

## Known Verification Caveats

Retain these as durable integration caveats:
1. Sentry org-level verification should use `SENTRY_ACCESS_TOKEN`
2. Render deploy responses may be nested, so flat parsers can misread deploy status
3. a stale production-alias incident previously caused live domains to serve an older Vercel deployment; alias state must be checked when hosted/frontend drift is suspected
4. `REMOTE_BACKEND_URL` can drift to a stale or retired endpoint; when remote verification looks wrong, fall back to the current Render API URL before diagnosing application behavior

## Storage Rules

1. keep secrets in the current password manager/vault
2. do not commit secrets to git
3. use `.env` files only for local/runtime injection

## Required Saved Items Per Platform

### Sentry
1. org slug
2. project slugs
3. DSNs in use
4. automation/API token if used

### PostHog
1. project ID/name
2. project key
3. host URL

### Resend
1. API key
2. sending identity/domain status

### Render
1. owner/team
2. service IDs/names
3. API key if API operations are used

### MongoDB Atlas
1. org/project name
2. cluster name and region
3. DB user and connection URI source
4. Atlas API credentials if used

### Vercel
1. owner/team
2. project ID
3. domain mapping and TLS state
4. API token if used
5. active production project identity

### Stripe
1. secret key source
2. webhook secret source
3. invoice/reply-to support configuration reference

## Environment Mapping

### Backend / runtime-critical
1. `MONGO_URL`
2. `DB_NAME`
3. `ADMIN_PASS`
4. `ACTIVE_REGION`
5. `ACTIVE_REGIONS`
6. `AUTONOMY_LOOP_OWNER`
7. `RUN_AUTONOMY_IN_API`
8. `AUTONOMY_LOOP_LEASE_ENABLED`
9. `AUTONOMY_LOOP_LEASE_TTL_S`
10. `AUTONOMY_LOOP_LEASE_RENEW_S`
11. `AUTONOMY_OWNER_ID`
12. `DISABLE_AUTONOMY`
13. `ENABLE_STARTUP_SEEDS`
14. `CONVERSION_BILLING_MODE`
15. `TRAINER_FREE_INTRO_DAYS`
16. `FIXED_INTRO_FEE_CENTS`
17. `PUBLIC_MATCHING_ENABLED`
18. `PUBLIC_LAUNCH_PHASE`
19. `PUBLIC_MONETIZATION_COPY_MODE`
20. `PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY`
21. `PUBLIC_SHOW_FOUNDING_PROFILE_COPY`
22. `TRAINER_ACTION_TOKEN_SECRET`
23. `TRAINER_ACTION_TOKEN_TTL_S`
24. `OVERSIGHT_AUTH_MAX_ATTEMPTS`
25. `OVERSIGHT_AUTH_WINDOW_S`
26. `OVERSIGHT_AUTH_LOCK_S`
27. `FRONTEND_BASE_URL`
28. `DISCOVERY_SOURCE_URLS`
29. `BILLABILITY_POLICY`
30. `CONTACT_READY_POLICY`
31. `NOTIFY_RETRY_ATTEMPTS`
32. `BILLING_RETRY_MAX_ATTEMPTS`
33. `BILLING_RETRY_BASE_DELAY_HOURS`
34. `REACTIVATION_NOTIFY_COOLDOWN_HOURS`
35. `CLAIM_STATE_MODEL_ENABLED`
36. `CLAIM_STATE_CURRENT`
37. `CLAIM_ENFORCEMENT_MODE`
38. `CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2`
39. `CORS_ORIGINS`

### Supporting integrations and verification vars currently used
1. `SENTRY_DSN`
2. `SENTRY_ENVIRONMENT`
3. `SENTRY_TRACES_SAMPLE_RATE`
4. `SENTRY_ACCESS_TOKEN`
5. `RESEND_API_KEY`
6. `RESEND_FROM`
7. `RESEND_REPLY_TO`
8. `STRIPE_SECRET_KEY`
9. `STRIPE_WEBHOOK_SECRET`
10. `STRIPE_DEFAULT_CURRENCY`
11. `STRIPE_INVOICE_DAYS_UNTIL_DUE`
12. `STRIPE_REQUIRE_BILLING_CONSENT`
13. `RENDER_API_KEY`
14. `MONGODB_ATLAS_PUBLIC_KEY`
15. `MONGODB_ATLAS_PRIVATE_KEY`
16. `MONGODB_ATLAS_PROJECT_ID`
17. `REMOTE_BACKEND_URL`

### Frontend
1. `REACT_APP_BACKEND_URL`

Current note:
1. the current frontend code path requires `REACT_APP_BACKEND_URL`
2. other provider keys should stay out of `frontend/.env` unless frontend code starts consuming them again

## Legacy / Non-Required Local Noise

These keys may exist locally but are not current codebase requirements by default:
1. `NEXT_PUBLIC_BACKEND_URL`
2. `REACT_APP_POSTHOG_*`
3. `NEXT_PUBLIC_POSTHOG_*`
4. `NEXT_PUBLIC_SENTRY_*`
5. `STRIPE_API_KEY_ID`
6. `STRIPE_PUBLISHABLE_KEY`
7. lowercase `resend_api_key`
8. `MONGO_API_KEY`
9. `MONGODB_ATLAS_API_KEY`

## Verification Commands

### Stage A runtime baseline
1. `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh`

### Stage B observability baseline
1. Sentry probe ingest and event visibility checks
2. PostHog key event capture checks

### Stage C outbound communications baseline
1. Resend controlled send and delivery-state check
2. validate `system_state.outreach` updates after loop run

### Discovery source baseline
1. set `DISCOVERY_SOURCE_URLS` with at least one source page
2. validate `system_state.source_ingestion.queued` increments and `discovery_queue` receives pending rows
