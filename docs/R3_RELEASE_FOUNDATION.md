# R3 Release Foundation and Sandbox Evidence

**Evidence date:** 22 October 2026

**Status:** PARTIAL — API release and health verification are complete; recovery, provider, default-branch and hosting-target gates remain open.
**Scope:** Developer sandbox only. This record does not authorise production deployment, provider credential changes, payments, or ingestion activation.

## 1. Environment and deployment identity

| Surface | Verified target | Current disposition |
|---|---|---|
| DTD public production site | Cloudflare fronts the public domain; repo Firebase defaults select project/site `gen-lang-client-0028123502` (`dogtrainersdirectory`). `firebase.json` routes `/api/**` to `dtd-api` in `australia-southeast1`. | Production-scoped configuration. No Firebase deployment was run. |
| DTD developer sandbox | Google Cloud project `dogtrainersdirectory-dev`, Cloud Run API `dtd-api-dev`, web `dtd-web-dev`, Atlas database `dtd_sandbox`. | This is the verified sandbox release path used for R3. |
| PR preview | GitHub reports Vercel Preview deployment `7227055232` for PR #17 head `76e8a010`; `production_environment=false`. | Separate from the public domain and developer sandbox. The preview integration is still active and needs owner disposition. |

Firebase CLI project inventory under the authenticated account lists the production DTD Firebase project and a separate Suburbmates project; it does not list `dogtrainersdirectory-dev`. A Hosting-site inventory request against the dev project returns HTTP 403 for `firebasehosting.sites.list`. Therefore no developer Firebase Hosting site or release is verified. The repository's Firebase default must not be used for sandbox deployment. See DF-007 and DF-053.

## 2. Accepted candidate and live API release

| Evidence | Result |
|---|---|
| Git source | `76e8a0100046662e823805eff799f8a987691dad` (`PR #17`, draft) |
| Independent delta review | Accepted the health classifier, compatible dependency updates, and deployment provenance preflight. |
| GitHub checks | Exact-head Verify passed; Actions, JavaScript/TypeScript and Python CodeQL passed. A previous Verify attempt failed only on npm registry HTTP 502 and was rerun successfully. |
| Local tests | Isolated backend integration 637 passed; frontend 74 passed; production frontend build passed. |
| Sandbox release gate | `PRELAUNCH_RELEASE_GATE=PASS`; deployment contract and actual Google upload manifest checks passed. |
| Cloud Build | `eec53d5c-3644-4064-94db-7aa0e1c6d083`, SUCCESS. Installed `pymongo==4.18.3` and compatible `motor==3.7.1`. |
| Source archive | 46 backend files; no extra entries or content mismatches against the tracked deployable backend subset at the validated commit. Test files intentionally excluded from the deployment archive. |
| Cloud Run API | `dtd-api-dev-r3-76e8a010`, 100% traffic, image digest `sha256:41fbfa3437c7c394d90da4943a967334fe15a4eaeeb34f2c3b167e00065753f1`. |
| Runtime identity/database | `dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`; database `dtd_sandbox`. Secret values were not read. The revision references Secret Manager by name/version. |
| Safety flags | Autonomy disabled; startup seeds disabled; billing checkout disabled; Ops self-healing disabled; matching enabled. Trainer-ingestion Scheduler remains PAUSED. |

Live `/api/health` returned HTTP 200 with database available. `/health/deep` returned HTTP 200 with database and collections accessible. AI diagnostics show only `ops_ai_investigation` degraded: zero unrecovered events, five recovered fallback events in the last hour, and 24 in the 24-hour persistence window. Cloud Logging shows Vertex AI `429 RESOURCE_EXHAUSTED`; deterministic fallback ran. This is an R7/R12 operational and cost-control issue under DF-052, not a matching or R1 safety failure. The separate `dtd-engine-tick-cron` remains ENABLED on its routine 10-minute schedule; it was not invoked by this release.

## 3. Recovery procedure and limits

The immediately preceding revision `dtd-api-dev-00055-kbm` remains Ready and was the pre-deployment 100% target. It contains the accepted ingestion-suppression and webhook retry fixes, but it predates the R3 dependency and health-classifier changes. Treat it as a **qualified emergency traffic return**, not as universally known-good or current security baseline. It reintroduces the reported dependency alerts and the old health interpretation. The trainer-ingestion Scheduler must remain PAUSED throughout.

For a candidate startup or service regression, first inspect the exact revision and scheduler state. The bounded traffic-return command is:

```sh
gcloud run services update-traffic dtd-api-dev \
  --project dogtrainersdirectory-dev \
  --region australia-southeast1 \
  --to-revisions dtd-api-dev-00055-kbm=100
```

Then confirm `latestReadyRevisionName`, the 100% traffic target, `/api/health`, `/health/deep`, and that `dtd-trainer-ingest-cron` is still PAUSED. Restore the candidate with `--to-revisions dtd-api-dev-r3-76e8a010=100` only after the regression cause is corrected and verified. Do not invoke `dtd-engine-tick-cron`, activate ingestion, restore the old Firebase target, or route any production traffic as part of recovery. This exact traffic-return procedure has **not** been rehearsed for the new R3 revision; prior R1 rollback evidence remains separately recorded.

## 4. Provider dependency registry (sanitised)

| Provider / purpose | Runtime reference and latest evidence | Degraded behavior | Recovery / alert disposition |
|---|---|---|---|
| Cloud Run / Cloud Build — API hosting and release | Developer project and dedicated runtime service account. R3 build and deployment succeeded 22 Oct. | Revision readiness and health gates fail the release script; zero traffic can be restored to the qualified prior revision. | Cloud Build/Cloud Run control-plane access is available in the current session. Production is not a recovery target. |
| MongoDB Atlas — developer persistence | Secret reference `dtd-mongo-url`; database `dtd_sandbox`. Ping and health passed on R3 revision 22 Oct. | Health reports database unavailable; API paths retain their existing failure handling. | Atlas management/recovery identity and least-privilege posture remain under DF-001; no credential was read or changed. |
| Vertex AI / Gemini — Ops analysis and matching assistance | Developer project/region configuration. R3 logs show Ops analyst `429 RESOURCE_EXHAUSTED`; matching degradation is not present in health. | Ops analyst returns deterministic fallback. | Quota dimension/reset and an independent quota alert route are not verified; DF-052 is assigned to R7/R12. No provider setting was changed. |
| Resend — transactional email and webhook | Developer Secret Manager references exist. Last documented safe test-recipient delivery succeeded 15 Oct; no provider webhook endpoint was configured in the prior audit. | Existing notification/fallback state records failures; provider-originated webhook retry remains unverified. | Provider-management recovery and least-privilege sending-key posture remain unverified under DF-001/DF-050. No real recipient was contacted. |
| Stripe — test/live billing integration | Secret references are present in the sandbox revision; `ENABLE_TRAINER_BILLING_CHECKOUT=0`. No payment action occurred. | Checkout is disabled. | Provider credential recovery and production acceptance are separately gated; no live payment/refund occurred. |
| ABR — statutory trainer identity verification | Secret reference `dtd-abr-guid`; no ABR request was made in this R3 release. | Existing verification paths retain their documented pending/held outcomes on failure. | No new credential or identity change; current provider response/recovery was not re-tested. |
| Sentry — error reporting | Secret reference `dtd-sentry-dsn`; no test event was emitted in this R3 release. | Application's core API remains available; independent alert delivery is not established by the DSN alone. | Provider-signed event and independent mailbox/alert verification remain open under DF-001. |
| Firebase Hosting — production website | Repo defaults target production site `gen-lang-client-0028123502`; live channel last released 15 Oct per Firebase CLI. | No sandbox effect; configuration contains production rewrite to `dtd-api`. | Developer Hosting site inventory is not available to the current identity. Do not deploy using these defaults; see DF-053. |
| Vercel — PR preview only | GitHub created Preview deployment `7227055232` for PR #17, non-production. | No public production domain or developer Cloud Run traffic change was observed. | Vercel project settings and preview access controls are unaudited. Owner disposition is needed before disabling or retaining this integration; see DF-007. |

Provider status statements above distinguish a successful runtime probe from provider-management recovery. They do not establish production readiness. No secrets, credentials, personal data, payments or production configuration were changed in this release.

## 5. Dependency and hosting risk register

- **DF-037 — PARTIAL:** candidate API image uses patched compatible PyMongo/Motor versions; frontend lock resolves PostCSS selector parser to 7.1.7. Five Dependabot alerts remain on default `main` until reviewed integration and rescan. Motor reached end of life on 14 May 2026 and receives only critical fixes through 14 May 2027; track PyMongo Async migration separately.
- **DF-006 — PARTIAL:** exact-head CI, deployment manifest and live source/image identity are verified. Product workflow acceptance remains R8.
- **DF-007 — PARTIAL:** public-domain ownership is not Vercel, but PR previews still deploy there. The Vercel preview is not the DTD sandbox.
- **DF-042 — DONE:** developer web runtime identity fix remains accepted.
- **DF-046 — DONE:** health classifier now distinguishes stale/recovered history and reports current per-operation threshold state accurately.
- **DF-053 — OPEN:** repository-default Firebase deployment is production-scoped; no developer Firebase Hosting target is verified.
- **DF-001 — PARTIAL:** provider recovery/rotation, historical archive and independent alert-path items remain individually open as recorded in `DTD_CURRENT_STATE.md`; no credential rotation is part of R3.
- **DF-052 — OPEN, R7/R12:** non-atomic scheduled AI budget and currently observed Vertex AI quota exhaustion require fail-closed reservation, concurrency bounds, and quota/alert evidence.
- SEO/publication eligibility, canonical metadata, sitemap and public journey acceptance remain assigned to R5/R8; no public content was changed in R3.

## 6. R3 exit disposition

R3 is **PARTIAL**. The accepted API candidate is deployed and verified in the developer Cloud Run sandbox. Completion still requires a written recovery exercise/qualification, a consolidated CI/dependency manifest, a reconciled provider recovery/alert registry, owner disposition for the active Vercel preview, and an unambiguous statement of whether Cloud Run is the intended sandbox deliverable or a separate Firebase Hosting sandbox is expected. Default-branch Dependabot alerts close only after accepted integration. No R4 work has been started, ingestion remains PAUSED, and production remains untouched.
