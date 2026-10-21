# R1 Developer Sandbox Release Evidence

**Date:** 21 October 2026
**Frozen baseline:** R0 `1ac4138e4d82991501139298cc624be732661119`
**Accepted delta:** DF-043 `50f3c594d611bede8b7a610d7b09fb3fd8680f23` (parent is frozen R0)
**Developer API:** `dtd-api-dev-00059-hex`, 100% traffic; image `sha256:891a4abb9f4119a13579a76a4b9269414bc1f30a87cf71f99acf200831bbbfe9`, built from `e207dbef8472e89be208ca6be0e631d4e72649e9`
**Developer web:** `dtd-web-dev-webidentity`, 100% traffic

## Code review and build

- Independent delta review: **ACCEPT**; review covered canonical suppression identity, stale identity fields, key coverage, existing and new candidate paths.
- Targeted regression command was rerun from the patch worktree after commit: `17 passed, 15 deselected`; `git show --check` passed.
- Cloud Build `60b33ff5-d5d0-41f6-a32d-3d36ff8686b3` in `australia-southeast1`: `SUCCESS` (2026-10-20 10:18–10:20 UTC). All 46 API source files in its immutable archive matched the corresponding tracked backend files at `50f3c594`; no archived backend file was untracked or mismatched.
- DF-043 baseline image digest: `sha256:c0611310f825b453162a2b8c8392b0b220cb256c5dfce58b2507b452506404b1` (superseded on developer API by the SR-01 delta below).
- API identity: `dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`; revision Ready and 100% traffic.
- `/api/health` and `/api/trainers` returned HTTP 200; database health was available; trainer response contained 20 public records.
- Web revision `dtd-web-dev-webidentity`, image `sha256:30cac8e4d00807f37c1d88c66dbc92019a5f40b21fe04db351356beb7c17c01a`, runtime identity `dtd-web-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`, Ready and 100% traffic. Build `638f12ff-03f6-49a9-bafa-d87740aac1d7` succeeded on 18 October; 122 tracked frontend source files in its archive matched commit `50f3c594`, with no mismatches. `/` returned HTTP 200.

### R1 webhook delta

- Independent delta review: **ACCEPT** for `e207dbef8472e89be208ca6be0e631d4e72649e9`; the change creates a unique sparse index for Resend event IDs and fails closed before writes if index readiness fails.
- Targeted local regression checks: **PASS**, `2 passed, 15 deselected`; `py_compile` and `git diff --check` passed.
- Cloud Build `fe4e210b-028a-483f-9818-953c0ad8b208`: **SUCCESS**. Archived runtime source matched the tracked backend files at `e207dbef`; no extra or changed files were present.
- Current revision `dtd-api-dev-00059-hex` is Ready at 100% with image `sha256:891a4abb9f4119a13579a76a4b9269414bc1f30a87cf71f99acf200831bbbfe9`. `RESEND_WEBHOOK_SECRET` is pinned to developer Secret Manager version 2. Generated version 1 was disabled after candidate checks.
- The database has unique index `id_1`. One valid synthetic signed event returned HTTP 200; its replay returned HTTP 200 with `duplicate: true`, while exactly one row remained. Tampered-body and missing-header requests returned HTTP 401. Cleanup deleted one event and a direct query confirmed zero remained.
- Resend's authenticated dashboard showed no webhook endpoints. Provider-originated delivery and downstream provider retry behavior are therefore `NOT_VERIFIED`; these checks establish the signed API path and database idempotency only.

## Bounded live suppression verification

A temporary, separately named Cloud Scheduler job invoked the deployed route using its configured OIDC identity. The original `dtd-trainer-ingest-cron` stayed paused. Synthetic fixtures used `.invalid` URLs to ensure suppression happened before fetch.

| Scenario | Result |
|---|---|
| Existing unclaimed trainer with canonical delisted website/trainer identity | Remained unchanged; not republished |
| Newly discovered candidate matching a delisted identity | Not inserted |
| Run result | 2 processed, 2 suppressed, 0 errors |
| Guardian | Disabled for this bounded live fixture run; earlier baseline reproduction had shown Guardian could report clean despite the bypass |

The first attempted direct service-account impersonation was denied for missing `iam.serviceAccounts.getAccessToken` / TokenCreator; no database write occurred. The bounded test proceeded through a temporary OIDC Scheduler job using its configured identity. The temporary job and all fixtures/run records were removed and verified; see `R1_FIXTURE_CLEANUP.md`.

## Web runtime identity boundary

Dedicated zero-direct-role service account `dtd-web-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com` is attached to `dtd-web-dev`. Canary revision passed API config/trainers requests and rendered 20 trainer cards; the identity was then promoted to 100% traffic. Previous web revision `dtd-web-dev-00021-pzw` remains available. Direct project role inventory, secret-level binding inventory and organization policy binding scan found no grant. Effective permission simulation through Policy Troubleshooter was unavailable because that API is disabled, so inherited permission absence is `NOT_VERIFIED`. No production IAM was changed and no default Compute roles were removed.

## Scheduler, engine-tick and R1 disposition

The original trainer-ingest job is currently verified `PAUSED`; original URL, `{}` request body, canonical OIDC audience, 180-second deadline, `0 2 * * *` schedule and `Australia/Melbourne` timezone are unchanged. After DF-043 deployment, the job was briefly enabled administratively during the activation assessment, then paused again once DF-045 was recognized as a direct acquisition-safety gap. No scheduled invocation occurred during that interval. Engine-tick remains enabled at `*/10 * * * *`; code-path inspection confirms it invokes ranking, inference, health, inventory, nurture, reactivation, analyst and recovery loops, but not ingestion.

**DF-043: DONE** for reviewed code and bounded sandbox suppression verification. **DF-042: DONE** for the developer web runtime attachment and tested public flow, with inherited effective permissions `NOT_VERIFIED`. R1's written exit contract requires scheduler status and safety evidence; it does not require scheduled ingestion to be enabled. Therefore R1 may close with ingestion explicitly **PAUSED**, while DF-044/045 remain a separate R4 activation dependency. Do not resume the job until both controls are repaired, independently accepted and verified. No production deployment or mutation occurred.

## Rollback

Current API revision `dtd-api-dev-00059-hex` serves the reviewed `e207dbef` image and is Ready at 100%. The corrected-code recovery target `dtd-api-dev-00055-mez` carries the same `50f3c594` suppression fix and active admin passcode version 3, but has no Resend webhook signing secret; webhook requests fail closed there. Revisions `00049` and `00027` are not safe rollback targets because they predate DF-043; their stale direct tags were removed. To restore corrected API code after a later regression, assign 100% to `dtd-api-dev-00055-mez` in `australia-southeast1` with `gcloud run services update-traffic dtd-api-dev --project=dogtrainersdirectory-dev --region=australia-southeast1 --to-revisions=dtd-api-dev-00055-mez=100`, then verify health, database availability, image digest, suppression behavior, Ops authentication and expected webhook fail-closed behavior. The traffic-update procedure was exercised during promotions, but rollback to `00055` itself was not. Overall rollback readiness is **PARTIAL** pending that controlled recovery exercise.

## 21 October targeted runtime acceptance refresh

The initial checks used API revision `dtd-api-dev-00050-7r7`; the current refresh confirms `dtd-api-dev-00059-hex` and web revision `dtd-web-dev-webidentity`, Ready on 100% developer traffic. `/api/health` and `/` returned HTTP 200. The API image is source-verified to local reviewed commit `e207dbef`; trainer fixtures used the Resend test sink only and were removed. No production action occurred.

| Scenario | Result | Runtime evidence |
|---|---|---|
| API/web basic compatibility | **DONE** | API health/database and web root returned HTTP 200. |
| SR-01 signed Resend webhook, replay and duplicate idempotency | **DONE in developer sandbox; provider delivery NOT_VERIFIED** | On current revision `00059`, the unique event index exists; first valid synthetic delivery returned HTTP 200, replay returned `duplicate: true`, and only one row persisted. Tampered body and missing headers returned HTTP 401. Cleanup deleted the event and a direct query confirmed zero remain. The authenticated Resend dashboard showed no webhook endpoints, so no provider-originated event was tested. |
| Unsigned/tampered Resend webhook negative paths | **DONE** | On the current configured developer candidate, missing signature headers and a body altered after signing returned HTTP 401 and created no event row. This is fail-closed and complements the signed/replay check. |
| Ordinary trainer claim and delivery | **DONE** | Browser claim on current web/API reached “Identity claimed”; `claim_events` reached `verified`, trainer claim/tier persisted, start/verify audit rows existed, and Resend returned HTTP 200 with provider message ID. |
| Claim exception cases (invalid/expired/replayed challenge) | **NOT_VERIFIED** | Current deployment was not exercised for these negative challenge cases. |
| Privacy request without trusted subject proof | **DONE** | Authenticated synthetic `authorise_scrub` returned HTTP 403; request document was byte-for-byte unchanged and no case audit row was written. |
| Verified privacy scrub / positive-resolution completion | **NOT_VERIFIED** | No trusted synthetic subject-verification flow was available; no scrub was attempted. |
| Compliance suppression and attempted republication | **DONE** | Synthetic public trainer was suppressed; authoritative delisted identity was written, public API returned 404, matching held submission approval returned HTTP 403 and stayed held, and suppression audit evidence existed. |
| Trainer delisting, notification and public removal | **DONE** | Synthetic trainer delist returned HTTP 200; trainer was inactive/unpublished, authoritative suppression row and audit were present, public API returned 404, and test-sink notification was recorded `sent` with HTTP 200/provider ID. |
| Fraud quarantine release/spam confirmation | **NOT_VERIFIED** | No live synthetic fraud case was run on this revision. |
| SR-04 / CF-04 support concurrency, delivery failure/fallback and specialised closure | **NOT_VERIFIED** | Not rerun against current revision; the live fixture must cover concurrency, notifier failure/fallback and closure evidence. |
| Durable obligations completeness and positive terminal resolution | **NOT_VERIFIED** | Code tests remain accepted R0 evidence; no current-revision synthetic Ops obligation lifecycle was run. |
| Protected Ops authentication / DF-038 | **DONE in developer runtime; source integration PARTIAL** | No passcode returned HTTP 401. Developer Secret Manager version 3 returned HTTP 200; the previous version-2 passcode returned HTTP 401. Current revision `00059` pins version 3; version 2 is disabled. Synthetic auth-limiter state was deleted and verified absent. Fail-closed runner retirement is independently accepted in local commit `85bb608`, but awaits remote integration; historical Git retains the disabled value. |

R1 remains **PARTIAL**. The R1 exit contract permits ingestion explicitly **PAUSED**. SR-01 synthetic API acceptance is complete on the developer sandbox; actual Resend provider delivery is `NOT_VERIFIED`. Claim exceptions, positive verified privacy, fraud, support, and obligations also remain `NOT_VERIFIED`. DF-044/045 remain the separate R4 acquisition-activation dependency. This checkpoint does not reopen DF-042/043 or the accepted R0 code review.

## DF-038 credential discrepancy discovered during R1

The frozen accepted branch `1ac4138` still contains the historical Ops verification script and its now-disabled developer passcode. The script was not run. Local commit `85bb608` replaces it with a fail-closed stub and passed independent source review, but remote branch `fix/ops-security-integrity-d83c7f4` has not yet received that commit. The current API image archive excludes the root-level script. Developer Secret Manager version 2 is disabled and version 3 is active. The value is not recorded. Production secrets were not queried or changed.

## Newly confirmed webhook idempotency gap

The initial 0%-traffic developer probe accepted the same signed synthetic event twice and persisted two rows because `resend_webhook_events` had no unique index. The issue was fixed in independently accepted local commit `e207dbef`, built as `fe4e210b`, and deployed to current developer revision `00059-hex`. The unique `id_1` index exists; replay returned `duplicate: true` with one persisted row. The event was deleted and a direct query confirmed zero leftovers. Invalid-signature paths returned HTTP 401. Resend has no configured webhook endpoint, so provider-originated delivery remains unverified.
