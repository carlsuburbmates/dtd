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

Firebase CLI project inventory under the authenticated account lists the production DTD Firebase project and a separate Suburbmates project; it does not list `dogtrainersdirectory-dev`. A Hosting-site inventory request against the dev project returns HTTP 403 for `firebasehosting.sites.list`. A separate read-only custom-domain API request via local gcloud ADC was denied because that credential has no quota project, so the production custom-domain mapping was not re-read from Firebase control plane during this turn. Therefore no developer Firebase Hosting site or release is verified. The repository's Firebase default must not be used for sandbox deployment. See DF-007 and DF-053.

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
| Cloud Run web | Existing revision `dtd-web-dev-00023-phd`, 100% traffic, image digest `sha256:5eba05c8ed409087498edcb18533e6b34b2b782cffd4f98827a705acaf7505d5`; root returned HTTP 200 and the served bundle targets the developer API. R3 made no frontend application-code change, so web was not redeployed. |
| Runtime identity/database | `dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`; database `dtd_sandbox`. Secret values were not read. The revision references Secret Manager by name/version. |
| Safety flags | Autonomy disabled; startup seeds disabled; billing checkout disabled; Ops self-healing disabled; matching enabled. Trainer-ingestion Scheduler remains PAUSED. |

Live `/api/health` returned HTTP 200 with database available. `/health/deep` returned HTTP 200 with database and collections accessible. AI diagnostics show only `ops_ai_investigation` degraded: zero unrecovered events, five recovered fallback events in the last hour, and 24 in the 24-hour persistence window. Cloud Logging shows Vertex AI `429 RESOURCE_EXHAUSTED`; deterministic fallback ran. This is an R7/R12 operational and cost-control issue under DF-052, not a matching or R1 safety failure. The separate `dtd-engine-tick-cron` remains ENABLED on its routine 10-minute schedule; it was not invoked by this release.

The same developer API's read-only `/api/config` returned canonical suburb catalogue version `v1`, count 539, source `static_catalogue_fallback`, with matching enabled. The repository loader validates the static 539-row asset and intentionally uses it when stored catalogue data is absent, unavailable or incomplete. This preserves locality controls and is not an R1 safety blocker; database-backed parity and trainer coverage remain unverified and are assigned to R4/R6. The fallback is geography only and does not mean 539 suburbs have available trainers.

## 3. Recovery procedure and limits

The immediately preceding revision `dtd-api-dev-00055-kbm` has `Ready=True` but is now inactive (`Active=False`, reason `Retired`); it was the pre-deployment 100% target. It contains the accepted ingestion-suppression and webhook retry fixes, but predates the R3 dependency and health-classifier changes. Treat it only as a **potential qualified emergency traffic return**: the post-deployment reactivation command has not been exercised, and the revision is not a universal known-good or current security baseline. It reintroduces the reported dependency alerts and old health interpretation. The trainer-ingestion Scheduler must remain PAUSED throughout.

For a candidate startup or service regression, first inspect the exact revision and scheduler state. The bounded traffic-return command is:

```sh
gcloud run services update-traffic dtd-api-dev \
  --project dogtrainersdirectory-dev \
  --region australia-southeast1 \
  --to-revisions dtd-api-dev-00055-kbm=100
```

Then confirm `latestReadyRevisionName`, the 100% traffic target, `/api/health`, `/health/deep`, and that `dtd-trainer-ingest-cron` is still PAUSED. Restore the candidate with `--to-revisions dtd-api-dev-r3-76e8a010=100` only after the regression cause is corrected and verified. Do not invoke `dtd-engine-tick-cron`, activate ingestion, restore the old Firebase target, or route any production traffic as part of recovery. This exact traffic-return procedure has **not** been rehearsed for the new R3 revision; prior R1 rollback evidence remains separately recorded.

## 4. Provider dependency registry (sanitised)

| Provider / purpose | Runtime vs. management identity; latest verification | Degraded behavior | Independent alert, recovery owner and next review |
|---|---|---|---|
| Cloud Run / Cloud Build — API hosting and release | Runtime identity is the dedicated developer service account. Build and deployment passed 22 Oct. | Readiness/health gates fail the deployment script; prior revision remains an emergency traffic-return target with limitations. | Release evidence is Cloud Build plus Cloud Run health/traffic checks; recovery owner is the project operator. Recheck before every release. Production is not a recovery target. |
| MongoDB Atlas — developer persistence | Runtime uses secret reference `dtd-mongo-url`; `dtd_sandbox` ping/health passed 22 Oct. Separate management identity/recovery path is not verified. | API reports database unavailable; affected operations must fail through their existing error paths. | GCP API 5xx alert is configured, but mailbox delivery is not verified; no Atlas-specific independent alert is proven. Recheck before R8 data acceptance. Owner/operator is recovery owner; DF-001 tracks identity/perimeter gaps. |
| Vertex AI / Gemini — Ops analysis and matching assistance | Runtime uses developer Cloud Run identity/region. 22 Oct logs show Ops analyst `429 RESOURCE_EXHAUSTED`; matching degradation is not present in health. | Ops analyst returns deterministic fallback. | No independent quota alert or exact reset/limit is verified. Owner/operator is recovery owner; review before R7/R12 AI acceptance under DF-052. No quota setting was changed. |
| Resend — transactional email and webhook | Runtime uses developer Secret Manager references. Last documented safe test-recipient delivery: 15 Oct. Prior audit found no provider webhook endpoint. Provider-management identity is unverified. | Notification/fallback state records failure; provider-originated webhook retry remains unverified. | GCP API 5xx alert exists but mailbox delivery is unverified; no separate Resend alert is proven. Owner/operator is recovery owner; review at R7 email acceptance. DF-001/DF-050 remain open. No real recipient was contacted. |
| Stripe — test/live billing integration | Sandbox has Secret Manager references; checkout flag was verified disabled 22 Oct. Provider management identity was not exercised. | Checkout is disabled. | No independent billing alert or recovery path was tested in R3. Owner/operator is recovery owner; review at the separate R9 billing gate. No live payment/refund occurred. |
| ABR — statutory trainer identity verification | Runtime reference `dtd-abr-guid`; no ABR request or successful response was verified in R3. | Existing failure paths should retain pending/held state; current provider behavior was not re-tested. | Independent alert and current management/recovery path are not verified. Owner/operator follows ABR's official recovery process; recheck before R4 statutory-verification acceptance. |
| Sentry — error reporting | Runtime reference `dtd-sentry-dsn`; no test event was emitted or verified in R3. | Core API remains available; DSN presence alone does not prove event delivery. | Independent alert delivery, mailbox verification and recovery path remain open under DF-001. Owner/operator; recheck before R3 observability closure. |
| Firebase Hosting — production website | Repo defaults select production site `gen-lang-client-0028123502`; CLI reports live release 15 Oct. No dev target is visible to current Firebase identity. | No sandbox effect; config rewrites `/api/**` to production service `dtd-api`. | Hosting deploy alert/recovery was not tested; project operator is owner. Recheck only before any intended Firebase release; DF-053 blocks use of defaults for sandbox. |
| Vercel — PR preview only | GitHub created Preview deployment `7227055232` for PR #17, `production_environment=false`; Vercel management settings were not inspected. | No public-domain or developer Cloud Run traffic change was observed. | Preview access and independent alerts are unaudited. Owner/operator must decide retain vs. retire before the next PR update; see DF-007. Expiry policy not established. |

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
