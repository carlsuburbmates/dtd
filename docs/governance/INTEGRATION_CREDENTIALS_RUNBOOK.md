# Integration Credentials Runbook

Purpose: keep account ownership and login material explicit, minimal, and recoverable.

## Current completion lock (2026-05-01)
1. Completed (accounts/keys): Clerk, Sentry, PostHog, Resend, Render, MongoDB Atlas, Vercel.
2. Completed with evidence:
- Stage A runtime baseline: `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` => `RESULT=PASS` (Render API/worker live, Atlas checks pass, remote `/api/config` 200).
- Stage B observability baseline:
  - Sentry API + web DSN ingest checks returned HTTP 200 and probe events visible via Sentry API project events endpoint.
  - PostHog key event capture checks for `match_submit`, `connect_submit`, `submission_submit` returned `Ok` via EU capture endpoint.
- Stage C outbound comms baseline:
  - Resend domains endpoint reachable (`HTTP 200`).
  - Controlled send returned message id and delivery state (`last_event=delivered`).
3. Still pending for full staged readiness:
- Stage D (edge/domain) evidence pack.
- Stage E (deploy automation/recovery) evidence pack.

## Storage rule
1. Save all credentials in your password manager under vault folder `BarkBond`.
2. Do not store secrets in git, local notes, or chat logs.
3. Use `.env` files only for local runtime injection.

## Accounts and required saved items

### 1. Clerk (Auth + `/ops` access control)
Save:
1. Clerk dashboard URL
2. Account owner email
3. MFA recovery codes
4. Publishable key (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`)
5. Secret key (dashboard only; not committed)
6. JWKS URL (`CLERK_JWKS_URL`)
7. Issuer (`CLERK_ISSUER`, if enforced)
8. Allowed ops user IDs list (`OPS_ALLOWED_USER_IDS`)
9. Allowed ops roles list (`OPS_ALLOWED_ROLES`)

### 2. Sentry (Error monitoring)
Save:
1. Organization slug
2. Project slugs (`barkbond-api`, `barkbond-web`)
3. Backend DSN (`SENTRY_DSN`)
4. Frontend DSN (`NEXT_PUBLIC_SENTRY_DSN`)
5. Personal access token (if API automation is used)

### 3. PostHog (Product analytics)
Save:
1. Project ID / name
2. Project API key (`NEXT_PUBLIC_POSTHOG_KEY`)
3. Host URL (`NEXT_PUBLIC_POSTHOG_HOST`)
4. Workspace owner email

### 4. Resend (Email/notifications)
Save:
1. Account owner email
2. API key (`RESEND_API_KEY`)
3. Sending domain status (verified/unverified)
4. Sender identities used by the app

### 5. Render (App/worker hosting)
Save:
1. Team/account owner
2. Service names (api/worker/web)
3. Environment groups or service env references
4. Deployment webhook/API token (if automation used)

### 6. MongoDB Atlas (Database)
Save:
1. Organization + project name
2. Cluster name/region/tier
3. DB user name(s) and auth method
4. Connection URI source and IP access policy
5. Atlas API credential material used by your workflow (`MONGO_API_KEY` and/or service account/client credentials)

### 7. Vercel (Frontend + domain/TLS/edge)
Save:
1. Account owner email
2. Team ID
3. Project ID
4. Production domain mappings (`www` and apex)
5. API token (if API automation used)

### 8. Cloudflare (optional/non-launch)
Save:
1. Account owner email
2. Zone name
3. DNS records for app domains
4. WAF/rate-limit rule IDs (if configured)

## Environment mapping

### Project root `.env` (docker compose wiring)
- `OPS_AUTH_MODE=clerk`
- `CLERK_JWKS_URL=...`
- `CLERK_ISSUER=...` (optional strict check)
- `CLERK_AUDIENCE=...` (optional strict check)
- `OPS_ALLOWED_USER_IDS=...`
- `OPS_ALLOWED_ROLES=founder,admin,ops`
- `OPS_ALLOW_ANY_SIGNED_IN=0|1` (dev convenience switch, must be `0` before launch)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...`
- `CLERK_SECRET_KEY=...`
- `RENDER_API_KEY=...` (optional for API-based Render verification/automation)
- `MONGO_API_KEY=...` (if using Atlas API key workflow)
- `MONGODB_ATLAS_API_KEY=...` (normalized alias for automation scripts)
- `VERCEL_TOKEN=...` (if using API-based verification/automation)
- `VERCEL_TEAM_ID=...`
- `VERCEL_PROJECT_ID=...`
- `CLOUDFLARE_ACCOUNT_ID=...` (optional/non-launch)
- `CLOUDFLARE_API_TOKEN=...` (optional/non-launch)

### Backend `.env`
- `OPS_AUTH_MODE=clerk`
- `CLERK_JWKS_URL=...`
- `CLERK_ISSUER=...` (optional strict check)
- `CLERK_AUDIENCE=...` (optional strict check)
- `OPS_ALLOWED_USER_IDS=...`
- `OPS_ALLOWED_ROLES=founder,admin,ops`
- `SENTRY_DSN=...`

### Frontend `.env`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...`
- `NEXT_PUBLIC_POSTHOG_KEY=...`
- `NEXT_PUBLIC_POSTHOG_HOST=...`
- `NEXT_PUBLIC_SENTRY_DSN=...`

## Operational verification
1. Sign in via Clerk and open `/ops`; confirm 200 response and metrics render.
2. Trigger a handled backend exception in dev; confirm Sentry receives event.
3. Trigger frontend route interactions; confirm PostHog events appear (`match_submit`, `connect_submit`, `submission_submit`).

## Stage A unblock checks (runtime baseline)
1. Atlas network+TLS validation from runtime host/container:
- confirm DB user `dtd_app` exists,
- confirm project access list includes active runtime egress IP,
- confirm `MONGO_URL` ping succeeds from the same runtime environment that runs backend/worker.
2. Re-run `scripts/verify_stage_a_runtime.sh` and keep output as evidence.
3. If local Docker is constrained, run remote mode:
- `STAGE_A_MODE=remote REMOTE_BACKEND_URL=https://<backend-host> ./scripts/verify_stage_a_runtime.sh`
- This validates account/runtime baseline without requiring local containers.

## Evidence snapshots (2026-05-01 UTC)
1. Stage A
- Command: `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh`
- Result: PASS
2. Stage B
- Sentry: DSN ingest API responses `200` for backend and frontend probes; probe titles present in recent project events.
- PostHog: `match_submit`, `connect_submit`, `submission_submit` capture responses `Ok` at `https://eu.i.posthog.com/capture/`.
3. Stage C
- Resend send API response `200`, message id created, message fetch shows `last_event=delivered`.

## Fast automation commands
1. `./scripts/ops_auth_preflight.sh`
2. `./scripts/ops_auth_mode.sh dev`
3. `./scripts/ops_auth_allowlist_by_email.sh you@example.com` (or no arg to use latest signed-in user)
4. `./scripts/ops_auth_mode.sh strict`
