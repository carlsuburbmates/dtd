# Integration Credentials Runbook

Purpose: keep credentials and infra verification simple for a one-man workflow.

## Current lock (2026-05-02)

1. Accounts/keys created: Clerk, Sentry, PostHog, Resend, Render, MongoDB Atlas, Vercel.
2. Evidence captured previously:
- Stage A runtime baseline: remote verifier pass recorded.
- Stage B observability baseline: Sentry/PostHog capture checks recorded.
- Stage C outbound baseline: Resend controlled send recorded.
3. Stage D evidence captured:
- New Vercel project `dtd` created and deployed from `frontend` root.
- `REACT_APP_BACKEND_URL` configured to `https://dtd-api.onrender.com` in prod/preview.
- Core route and backend-config validations recorded during migration.
- Custom domains reattached to the live `dtd` deployment; public hostnames now return `307` apex redirect to `www` and `200` on `www` and `/trainers`.
4. Stage E evidence captured:
- Repeatable deploy automation/recovery evidence recorded.
- Authenticated route smoke confirms required routes render on the production deployment.

## H-02 readiness snapshot (2026-05-02)

1. Render service-level secret presence verified and patched:
- `dtd-api` (`srv-d7plat9kh4rs73e92qcg`)
- `dtd-worker` (`srv-d7platpf9bms73alk5u0`)
2. Verified keys present in both Render services:
- `RESEND_API_KEY`
- `RESEND_FROM`
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

## H-04 platform readiness snapshot (2026-05-02)

1. Full platform check report:
- `docs/governance/H04_VERIFICATION_REPORT.json`
2. Command-level evidence refresh executed at `2026-05-01T19:43:05Z` (`2026-05-02` local):
- `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` -> exit `0` (`RESULT=PASS`)
- `vercel api "/v9/projects/prj_TviWWkrOzNENkY4cazM3XsRHyIR1?teamId=team_5Jzh8VcbTjO5MNniKHpivsCY" --raw` -> exit `0`
- `curl -H "Authorization: Bearer $RENDER_API_KEY" https://api.render.com/v1/services?limit=100` -> HTTP `200`
- `curl ... /v1/services/srv-d7plat9kh4rs73e92qcg/deploys?limit=1` -> HTTP `200`, latest `dep-d7qfl9sm0tmc73dcree0` status `live`
- `curl ... /v1/services/srv-d7platpf9bms73alk5u0/deploys?limit=1` -> HTTP `200`, latest `dep-d7qfl9sm0tmc73dcreq0` status `live`
- `curl --digest -u "$MONGODB_ATLAS_PUBLIC_KEY:$MONGODB_ATLAS_PRIVATE_KEY" https://cloud.mongodb.com/api/atlas/v2/groups/$MONGODB_ATLAS_PROJECT_ID/clusters` -> HTTP `200`
- `curl -H "Authorization: Bearer $RESEND_API_KEY" https://api.resend.com/domains` -> HTTP `200`
- `curl -H "Authorization: Bearer $SENTRY_ACCESS_TOKEN" https://sentry.io/api/0/organizations/` -> HTTP `200`
- `curl -X POST "$NEXT_PUBLIC_POSTHOG_HOST/capture/" ...` -> HTTP `200`
3. Drift/failure flags from refresh:
- **Failure observed**: Sentry org check returned HTTP `401` when command used `SENTRY_AUTH_TOKEN`/`SENTRY_API_TOKEN` aliases.
- **Resolution**: switching command to `SENTRY_ACCESS_TOKEN` restored HTTP `200`.
- Render deploy response shape is nested (`response[0].deploy.status`), so flat parsers can misreport deploy status as null.
- Vercel production deployment advanced from `dpl_H8gcahxzuwLfEmf66VL3v9MnoWno` to `dpl_AD5Kghob4aQNHcAFVQyWwNoq373K`.
4. Result:
- No active platform block detected at refresh time; one credential-variable naming drift and one response-shape drift require command hygiene.

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
4. `ACTIVE_REGION`
5. `ACTIVE_REGIONS`
6. `RUN_AUTONOMY_IN_API` (important when running worker)
7. `CONVERSION_BILLING_MODE` (`track_only` for launch)

### Optional monitoring/email vars currently used by supporting workflows
1. `SENTRY_DSN`
2. `SENTRY_ACCESS_TOKEN` (used for org-level API verification)
3. `SENTRY_ENVIRONMENT`
4. `SENTRY_TRACES_SAMPLE_RATE`
5. `NEXT_PUBLIC_POSTHOG_KEY`
6. `NEXT_PUBLIC_POSTHOG_HOST`
7. `RESEND_API_KEY`
8. `RENDER_API_KEY`
9. `MONGODB_ATLAS_PUBLIC_KEY`
10. `MONGODB_ATLAS_PRIVATE_KEY`
11. `MONGODB_ATLAS_PROJECT_ID`
12. `REMOTE_BACKEND_URL`
13. `DISCOVERY_SOURCE_URLS`
14. `RESEND_FROM`

### Frontend
1. `REACT_APP_BACKEND_URL`
2. `REACT_APP_POSTHOG_KEY`
3. `REACT_APP_POSTHOG_HOST`
4. `NEXT_PUBLIC_POSTHOG_KEY` (compat/migration parity)
5. `NEXT_PUBLIC_POSTHOG_HOST` (compat/migration parity)

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
