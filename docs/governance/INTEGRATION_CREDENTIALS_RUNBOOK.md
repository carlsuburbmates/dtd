# Integration Credentials Runbook

Purpose: keep credentials and infra verification simple for a one-man workflow.

## Current lock (2026-05-01)

1. Accounts/keys created: Clerk, Sentry, PostHog, Resend, Render, MongoDB Atlas, Vercel.
2. Evidence captured previously:
- Stage A runtime baseline: remote verifier pass recorded.
- Stage B observability baseline: Sentry/PostHog capture checks recorded.
- Stage C outbound baseline: Resend controlled send recorded.
3. Open evidence stages:
- Stage D: edge/domain evidence pack.
- Stage E: deploy automation/recovery evidence pack.

## Storage rules

1. Keep secrets in your password manager (`BarkBond` vault/folder).
2. Do not commit secrets to git.
3. Use `.env` only for local/runtime injection.

## Required saved items per platform

### Clerk
1. Dashboard URL.
2. Owner email.
3. API keys (publishable/secret if used).
4. JWKS/issuer values if you later enforce Clerk on backend.

### Sentry
1. Org slug.
2. Project slugs.
3. DSNs in use.
4. API token used for automation (if used).

### PostHog
1. Project ID/name.
2. Project key.
3. Host URL.

### Resend
1. API key.
2. Sending identity/domain status.

### Render
1. Account/team owner.
2. Service IDs/names.
3. API key (if API operations are used).

### MongoDB Atlas
1. Org/project name.
2. Cluster name and region.
3. DB user and connection URI source.
4. Atlas API credential(s) if used.

### Vercel
1. Owner/team.
2. Project ID.
3. Domain mapping and TLS state.
4. API token if used.

## Environment mapping (current codebase)

### Backend/runtime-critical
1. `MONGO_URL`
2. `DB_NAME`
3. `ADMIN_PASS`
4. `RUN_AUTONOMY_IN_API` (important when running worker)

### Optional monitoring/email vars currently used by supporting workflows
1. `SENTRY_DSN`
2. `SENTRY_ENVIRONMENT`
3. `SENTRY_TRACES_SAMPLE_RATE`
4. `NEXT_PUBLIC_POSTHOG_KEY`
5. `NEXT_PUBLIC_POSTHOG_HOST`
6. `RESEND_API_KEY`
7. `RENDER_API_KEY`
8. `MONGODB_ATLAS_PUBLIC_KEY`
9. `MONGODB_ATLAS_PRIVATE_KEY`
10. `MONGODB_ATLAS_PROJECT_ID`
11. `REMOTE_BACKEND_URL`

### Frontend
1. `REACT_APP_BACKEND_URL`

## Verification commands

### Stage A runtime baseline
1. `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh`

### Stage B observability baseline
1. Sentry probe ingest and event visibility checks.
2. PostHog key event capture checks.

### Stage C outbound communications baseline
1. Resend controlled send and delivery-state check.

### Stage D/E (open)
1. Record exact command outputs for Vercel edge/domain setup.
2. Record exact command outputs for repeatable deploy/redeploy procedure.

## Update rule

If integration behavior changes, update this file in place the same day.
