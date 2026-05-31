# Integration Credentials Runbook

Purpose: keep credentials and infra verification simple for a one-man workflow.

Agent routing reference: `.codex/skill-policy.toml` is the live routing policy source; use it together with the current task context and native capabilities when picking a plugin, skill, or fallback.

## Local env file inventory (current repo)

These are the env files currently present in the repo layout:
1. root `.env` — local-only shared verification/operator secrets and repo-level script inputs
2. root `.env.example` — committed placeholder map for the root `.env`
3. `backend/.env` — local-only backend runtime secrets and defaults
4. `backend/.env.example` — committed placeholder map for backend runtime
5. `frontend/.env` — local-only frontend runtime values
6. `frontend/.env.example` — committed placeholder map for frontend runtime

Rules:
1. Real `.env` files stay local only and remain gitignored.
2. Committed `*.env.example` files must contain placeholders/defaults only.
3. If a current code-path env var exists in runtime code or repo verification scripts, it must be represented in either the relevant `*.env.example` file or this runbook.
4. Legacy local-only keys may exist in untracked `.env` files, but they must not be treated as required unless current code or current verification scripts still use them.

## Env ownership standard

Use this split consistently:
1. `backend/.env` — authoritative backend runtime config
2. `frontend/.env` — frontend-only runtime config
3. root `.env` — repo-level verification and operator tooling config

Ownership rule:
1. if backend code reads it, put it in `backend/.env`
2. if frontend code reads it, put it in `frontend/.env`
3. if repo scripts or operator verification use it, put it in root `.env`

## Local env contract refresh (2026-05-25)

Presence-only local audit completed across all env files in the repo.

Result:
1. root `.env`, `backend/.env`, and `frontend/.env` all exist locally
2. backend local env was missing several current-runtime keys and has been patched locally with safe defaults/placeholders
3. current committed examples were incomplete and are now aligned to the env-ownership standard and current runtime/verification contract
4. extra local keys still exist in some untracked env files, but several are legacy/non-blocking and are not current codebase requirements
5. live integration verification confirms the active custom domains point at Vercel project `dtd`; a separate `dogtrainersdirectory` Vercel project still exists in account inventory and should be treated as historical/drift-risk inventory, not the active custom-domain target

Current known legacy/non-required local env noise:
1. `NEXT_PUBLIC_BACKEND_URL` in `frontend/.env` is not the current frontend runtime key; current code uses `REACT_APP_BACKEND_URL`
2. `REACT_APP_POSTHOG_*`, `NEXT_PUBLIC_POSTHOG_*`, and `NEXT_PUBLIC_SENTRY_*` may exist locally for historical or deferred integration work, but they are not required by the current frontend code path
3. `STRIPE_API_KEY_ID`, `STRIPE_PUBLISHABLE_KEY`, lowercase `resend_api_key`, `MONGO_API_KEY`, and `MONGODB_ATLAS_API_KEY` may exist locally, but they are not current codebase requirements

## Current lock (2026-05-31)

1. Accounts/keys created: Sentry, PostHog, Resend, Render, MongoDB Atlas, Vercel.
2. Evidence captured previously:
- Stage A runtime baseline: remote verifier pass recorded.
- Stage B observability baseline: Sentry/PostHog capture checks recorded.
- Stage C outbound baseline: Resend controlled send recorded.
3. Stage D evidence captured:
- New Vercel project `dtd` created and deployed from `frontend` root.
- `REACT_APP_BACKEND_URL` configured to `https://dtd-api.onrender.com` in prod/preview.
- Core route and backend-config validations recorded during migration.
- Custom domains reattached to the live `dtd` deployment; public hostnames now return `307` apex redirect to `www` and `200` on `www` and `/trainers`.
- Live-domain verification confirms `dogtrainersdirectory.com.au` and `www.dogtrainersdirectory.com.au` resolve to a production deployment of project `dtd`.
4. Stage E evidence captured:
- Repeatable deploy automation/recovery evidence recorded.
- Authenticated route smoke confirms required routes render on the production deployment.
5. Current live-state correction:
- The stale hosted frontend incident was traced to production aliases serving an older Vercel deployment.
- The active `dtd` deployment was promoted and live domains now serve the current DTD frontend.
- A separate `dogtrainersdirectory` Vercel project still exists in account inventory and should be treated as drift-risk inventory, not the active custom-domain target.

## H-02 readiness snapshot (2026-05-02)

1. Render service-level secret presence verified and patched:
- `dtd-api` (`srv-d7plat9kh4rs73e92qcg`)
- `dtd-worker` (`srv-d7platpf9bms73alk5u0`)
2. Verified keys present in both Render services:
- `RESEND_API_KEY`
- `RESEND_FROM`
- `RESEND_REPLY_TO`
- `DISCOVERY_SOURCE_URLS`
- `SENTRY_DSN`
3. Vercel project env presence verified and patched:
- project `dtd` (`prj_TviWWkrOzNENkY4cazM3XsRHyIR1`)
- `REACT_APP_BACKEND_URL`
- `REACT_APP_POSTHOG_KEY`
- `REACT_APP_POSTHOG_HOST`
- `NEXT_PUBLIC_POSTHOG_KEY`
- `NEXT_PUBLIC_POSTHOG_HOST`
4. Post-patch deploy evidence:
- Render latest deploys live for API + worker.
- Vercel production redeploy completed: `dpl_H8gcahxzuwLfEmf66VL3v9MnoWno`.
5. Current live deployment note:
- the active production deployment later advanced to `dpl_AL1UMMUptY9LBvcKCS4sY9cAKEAa` (`fix: render authenticated ops cockpit`)
- production aliases now serve the current `dtd` deployment after the stale-alias correction

## H-04 platform readiness snapshot (2026-05-02)

1. Command-level evidence refresh executed at `2026-05-01T19:43:05Z` (`2026-05-02` local):
- `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` -> exit `0` (`RESULT=PASS`)
- `vercel api "/v9/projects/prj_TviWWkrOzNENkY4cazM3XsRHyIR1?teamId=team_5Jzh8VcbTjO5MNniKHpivsCY" --raw` -> exit `0`
- `curl -H "Authorization: Bearer $RENDER_API_KEY" https://api.render.com/v1/services?limit=100` -> HTTP `200`
- `curl ... /v1/services/srv-d7plat9kh4rs73e92qcg/deploys?limit=1` -> HTTP `200`, latest `dep-d7qfl9sm0tmc73dcree0` status `live`
- `curl ... /v1/services/srv-d7platpf9bms73alk5u0/deploys?limit=1` -> HTTP `200`, latest `dep-d7qfl9sm0tmc73dcreq0` status `live`
- `curl --digest -u "$MONGODB_ATLAS_PUBLIC_KEY:$MONGODB_ATLAS_PRIVATE_KEY" https://cloud.mongodb.com/api/atlas/v2/groups/$MONGODB_ATLAS_PROJECT_ID/clusters` -> HTTP `200`
- `curl -H "Authorization: Bearer $RESEND_API_KEY" https://api.resend.com/domains` -> HTTP `200`
- `curl -H "Authorization: Bearer $SENTRY_ACCESS_TOKEN" https://sentry.io/api/0/organizations/` -> HTTP `200`
- `curl -X POST "$NEXT_PUBLIC_POSTHOG_HOST/capture/" ...` -> HTTP `200`
2. Drift/failure flags from refresh:
- **Failure observed**: Sentry org check returned HTTP `401` when command used `SENTRY_AUTH_TOKEN`/`SENTRY_API_TOKEN` aliases.
- **Resolution**: switching command to `SENTRY_ACCESS_TOKEN` restored HTTP `200`.
- Render deploy response shape is nested (`response[0].deploy.status`), so flat parsers can misreport deploy status as null.
- Vercel production deployment advanced from `dpl_H8gcahxzuwLfEmf66VL3v9MnoWno` to `dpl_AD5Kghob4aQNHcAFVQyWwNoq373K`.
- later live routing drift was observed when production aliases pointed at an older deployment; that issue was corrected by promoting `dpl_AL1UMMUptY9LBvcKCS4sY9cAKEAa`.
3. Result:
- No active platform block detected at refresh time; one credential-variable naming drift and one response-shape drift require command hygiene.
- current active live domains serve DTD correctly, but duplicate Vercel project/domain inventory remains an account-hygiene risk.

## Email channel verification snapshot (2026-05-09)

1. Application + outreach email path (Resend) is aligned:
- Controlled app emails display `From: no-reply@dogtrainersdirectory.com.au`.
- Controlled app emails display `Reply-To: info@dogtrainersdirectory.com.au`.
- Backend unit coverage now asserts `from`, `reply_to`, and MIME `Reply-To` header for both submitter notifications and T+7 outreach payloads.
2. DNS/auth baseline is aligned:
- DMARC policy added at `_dmarc.dogtrainersdirectory.com.au` with quarantine policy and reporting to `info@dogtrainersdirectory.com.au`.
3. Stripe invoice email path is aligned to single-mailbox policy:
- Controlled Stripe invoice reminder preview shows `Reply-To` mapped to `info@dogtrainersdirectory.com.au`.
- Invoice body support contact resolves to `info@dogtrainersdirectory.com.au`.
- This remains Stripe-managed behavior (outside Resend/backend payload config), so it should be rechecked after Stripe account profile edits.
4. Detailed evidence/report:
- this runbook section is the retained email verification reference after documentation reduction.

## Storage rules

1. Keep secrets in your password manager (`DTD` / Dog Trainers Directory vault or equivalent current folder naming).
2. Do not commit secrets to git.
3. Use `.env` only for local/runtime injection.

## Required saved items per platform

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
5. Active project is `dtd` (`prj_TviWWkrOzNENkY4cazM3XsRHyIR1`).
6. Separate `dogtrainersdirectory` project remains in account inventory and should not be treated as the active production target.

## Environment mapping (current codebase)

### Backend/runtime-critical
1. `MONGO_URL`
2. `DB_NAME`
3. `ADMIN_PASS`
4. `ACTIVE_REGION`
5. `ACTIVE_REGIONS`
6. `AUTONOMY_LOOP_OWNER` (`api` / `worker` / `none`)
7. `RUN_AUTONOMY_IN_API` (legacy compatibility; must not conflict with `AUTONOMY_LOOP_OWNER`)
8. `AUTONOMY_LOOP_LEASE_ENABLED`
9. `AUTONOMY_LOOP_LEASE_TTL_S`
10. `AUTONOMY_LOOP_LEASE_RENEW_S`
11. `AUTONOMY_OWNER_ID` (optional explicit owner override)
12. `DISABLE_AUTONOMY`
13. `CONVERSION_BILLING_MODE` (`track_only` for launch)
14. `TRAINER_FREE_INTRO_DAYS` (launch default `30`)
15. `FIXED_INTRO_FEE_CENTS` (launch default `500`)
16. `PUBLIC_MATCHING_ENABLED`
17. `PUBLIC_LAUNCH_PHASE`
18. `PUBLIC_MONETIZATION_COPY_MODE`
19. `PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY`
20. `PUBLIC_SHOW_FOUNDING_PROFILE_COPY`
21. `TRAINER_ACTION_TOKEN_SECRET`
22. `TRAINER_ACTION_TOKEN_TTL_S`
23. `OVERSIGHT_AUTH_MAX_ATTEMPTS`
24. `OVERSIGHT_AUTH_WINDOW_S`
25. `OVERSIGHT_AUTH_LOCK_S`
26. `FRONTEND_BASE_URL`
27. `DISCOVERY_SOURCE_URLS`
28. `BILLABILITY_POLICY`
29. `CONTACT_READY_POLICY`
30. `NOTIFY_RETRY_ATTEMPTS`
31. `BILLING_RETRY_MAX_ATTEMPTS`
32. `BILLING_RETRY_BASE_DELAY_HOURS`
33. `REACTIVATION_NOTIFY_COOLDOWN_HOURS`
34. `CLAIM_STATE_MODEL_ENABLED`
35. `CLAIM_STATE_CURRENT`
36. `CLAIM_ENFORCEMENT_MODE`
37. `CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2`
38. `CORS_ORIGINS`

### Supporting integrations and verification vars currently used
1. `SENTRY_DSN`
2. `SENTRY_ENVIRONMENT`
3. `SENTRY_TRACES_SAMPLE_RATE`
4. `SENTRY_ACCESS_TOKEN` (used for org-level API verification)
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
1. The current frontend code path requires `REACT_APP_BACKEND_URL`.
2. Other frontend-facing provider keys should stay out of `frontend/.env` unless frontend code starts consuming them again.

## Verification commands

### Stage A runtime baseline
1. `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh`

### Stage B observability baseline
1. Sentry probe ingest and event visibility checks.
2. PostHog key event capture checks.

### Stage C outbound communications baseline
1. Resend controlled send and delivery-state check.
2. Validate `system_state.outreach` updates after loop run.

### Discovery source baseline
1. Set `DISCOVERY_SOURCE_URLS` with at least one source page.
2. Validate `system_state.source_ingestion.queued` increments and `discovery_queue` receives pending rows.

### Stage D/E (complete)
1. Record exact command outputs for Vercel edge/domain setup.
2. Record exact command outputs for repeatable deploy/redeploy procedure.
3. Latest Stage D/E command evidence (2026-05-07 local):
- `vercel alias ls` -> `dogtrainersdirectory.com.au` and `www.dogtrainersdirectory.com.au` both aliased to `dtd-mv0os58gf-carlitos-projects-a62ff78f.vercel.app`.
- `vercel domains ls` -> domain present in Vercel account inventory (`dogtrainersdirectory.com.au`).
- `curl -I https://dogtrainersdirectory.com.au` -> `HTTP/2 307`, redirecting to `https://www.dogtrainersdirectory.com.au/`.
- `curl -I https://www.dogtrainersdirectory.com.au` -> `HTTP/2 200`.
- `curl -I https://www.dogtrainersdirectory.com.au/trainers` -> `HTTP/2 200`.
- `vercel curl <route> --deployment dpl_AD5Kghob4aQNHcAFVQyWwNoq373K` for required public/trainer/ops paths -> all `HTTP=200` with authenticated deployment access.
4. Current interpretation:
- Stage D evidence pack is complete.
- Stage E deploy repeatability is evidenced.
- Public anonymous checks now return live domain responses; protected route smoke remains available for deployment-level verification.

### A-05 operational proof refresh (2026-05-02 local)
1. Created intro `70c9efee-1cc3-41f8-b1bb-eae0365979f0`, backdated to T+8d eligibility in runtime DB, and executed `send_t7_outreach` once.
2. Observed runtime result:
- `outreach_events_total=1`
- latest row status `sent`, `http_status=200`
3. Interpretation:
- Loop-output proof for outreach is now concrete (not just code presence/system-state metadata).

### H-02 verification commands (completed)
1. Render env presence by service:
- `GET /v1/services/{serviceId}/env-vars` (API key auth; keys-only checklist)
2. Render deploy state check:
- `GET /v1/services/{serviceId}/deploys`
3. Vercel env presence by project:
- `vercel api /v10/projects/prj_TviWWkrOzNENkY4cazM3XsRHyIR1/env?teamId=team_5Jzh8VcbTjO5MNniKHpivsCY --raw`
4. Vercel production redeploy:
- `vercel --prod --yes`

## Update rule

If integration behavior changes, update this file in place the same day.
This file is a credentials/runbook artifact, not the canonical source of launch-phase governance or current product truth.
