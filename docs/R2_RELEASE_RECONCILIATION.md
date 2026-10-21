# R2 Release Reconciliation

**Evidence date:** 21 October 2026
**Scope:** R2 GitHub/document consolidation and developer-sandbox deployment. This closes the R2 remediation package only; it does not declare DTD product completion or authorize production release.

## Accepted source and GitHub state

| Item | Verified result |
|---|---|
| Frozen R0 baseline | `1ac4138e4d82991501139298cc624be732661119` preserved. |
| PR #13 | Merged to `main` as `2db0e92807d9e36e0cbdf516aaddeba1a6475188`; DF-050 retry reconciliation remains accepted and is not reopened. |
| PR #12 | Independent exact-delta review ACCEPT; merge commit `704c8301676792d488faada56a7b9cc6fab702b5`; exact-head Verify, CodeQL and preview checks passed. The intentional Clerk skill deletion remains in the merge. |
| PR #15 | Independent exact-delta review ACCEPT; explicit sandbox billing/self-healing gates merged as `f24cc49723840028bbe4ea35f6787eed03c440ba`; exact-head Verify, CodeQL and preview checks passed. |
| Deployed runtime source | `f24cc49723840028bbe4ea35f6787eed03c440ba`. PR #16 changes release tooling and documentation only; it does not change the deployed runtime. No force push was used. |

## Developer sandbox deployment

The project is `dogtrainersdirectory-dev` in `australia-southeast1`. Both services use Cloud Run. The public production route remains Firebase Hosting plus Cloud Run and was not changed.

The developer sandbox is verified as a Google Cloud project with isolated Cloud Run API and web services. Current Firebase CLI project inventory lists the public `dogtrainersdirectory` project but not `dogtrainersdirectory-dev`; a read-only Firebase Hosting site query for the developer project returned HTTP 403. A separate Firebase Hosting sandbox is therefore **NOT_VERIFIED**. No Firebase Hosting release or production Firebase change was made for this sandbox deployment.

| Surface | Revision | Image | Traffic / verification |
|---|---|---|---|
| API `dtd-api-dev` | `dtd-api-dev-00055-kbm` | `sha256:d0846a21e73642376c3e5f145f0791fb1456b185624bd8c12ab773f64fc3b764` | 100%; `/api/health` returned `ok=true`, database `available`. |
| Web `dtd-web-dev` | `dtd-web-dev-00023-phd` | `sha256:5eba05c8ed409087498edcb18533e6b34b2b782cffd4f98827a705acaf7505d5` | 100%; browser rendered the home page with no console errors; served JS `index-B7QXYDjb.js` and CSS `index-DxHjLe4X.css`; bundle targets the developer API. |

The API runs as `dtd-api-dev-runtime`, uses database `dtd_sandbox`, explicitly sets `ENABLE_TRAINER_BILLING_CHECKOUT=0` and `OPS_SELF_HEALING_ENABLED=0`, and keeps `DISABLE_AUTONOMY=1`. The web runs as `dtd-web-dev-runtime`. The web revision was first created without receiving traffic because the prior service route was pinned by name; its zero-traffic tag served the expected built bundle and developer API origin, then revision `00023-phd` was explicitly promoted to 100%. This was verified manually against the live service and local build. A follow-up corrects the deployment verifier so future runs explicitly promote the latest revision and compare the served asset with the checkout build.

## Scheduler and activation gates

- `dtd-trainer-ingest-cron` remains **PAUSED** on `0 2 * * *` Melbourne time. No ingestion invocation occurred; DF-044 and DF-045 remain R4 activation gates.
- `dtd-engine-tick-cron` remains **ENABLED**, every 10 minutes in Melbourne, POST `{}` to `.../api/internal/jobs/engine-tick?profile=routine`, with the dedicated developer runtime OIDC identity and canonical regional audience. It was inspected read-only and never invoked.
- `routine` may write derived and Ops state and call Vertex AI. It does not run trainer nurture, reactivation-email or recovery loops. Fixture-scoped execution and strict AI cost controls remain blocked under DF-052.

## Checks, scenarios, cleanup and recovery

- Local isolated backend suite: **633 passed**, 429 warnings. Frontend: **74 passed**; production build passed (large JavaScript chunk warning). Release gate and sandbox deploy contract passed.
- PR #12 exact-head checks: Verify runs `39596694807` and `39596705949`; CodeQL `119210818080`; Vercel preview check passed. PR #15 exact-head checks: Verify runs `39597233300` and `39597252993`; CodeQL `119212742320`; Vercel preview check passed. Vercel is only a PR preview integration, not DTD hosting.
- No database fixtures, provider messages, live payments, or scheduler executions were created for R2 deployment. R1 synthetic scenario cleanup remains recorded in `R1_FIXTURE_CLEANUP.md`.
- API recovery target `dtd-api-dev-00054-rvl` is conditional while trainer ingestion remains paused and no Resend webhook endpoint is configured; it includes DF-043 suppression and DF-050 retry reconciliation. Web recovery target is the previously serving `dtd-web-dev-webidentity`. Verify those conditions and health before any recovery traffic switch.
- Production Cloud Run, Firebase Hosting, production data, credentials and billing configuration were not changed.

## Roadmap disposition

R2 consolidation and developer-sandbox deployment are **DONE**. The future frontend deployment-verification correction is a separately tracked release-tool follow-up, not a condition of the already verified R2 runtime deployment. DF-044/045 remain R4; DF-051 remains R5 with an R4 acquisition-dedup check; DF-046 remains R3; DF-047/048 remain R7; DF-052 remains R7/R12. Their assignments are not R2 blockers and they remain open for their stages. DF-042/043 and the accepted R0 review remain preserved.
