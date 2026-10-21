# R1 Developer Sandbox Release Evidence

**Date:** 21 October 2026
**Frozen baseline:** R0 `1ac4138e4d82991501139298cc624be732661119`
**Accepted delta:** DF-043 `50f3c594d611bede8b7a610d7b09fb3fd8680f23` (parent is frozen R0)
**Developer API:** `dtd-api-dev-00054-rvl`, 100% traffic; image `sha256:23f75593957e64c305dc6ac7364a0e53192a120c6ff018192595a0d1f2c27df3`, built from `fdd2c45431dfeccf405a14ebdb46b45d545fa6ca`
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

### Targeted retry-reconciliation correction

- PR #13 review identified a partial-write case: the webhook receipt could be stored before the notification status update, causing a legitimate retry to be acknowledged as a duplicate without finishing the notification update.
- Commit `fdd2c45431dfeccf405a14ebdb46b45d545fa6ca` reconciles notification state from a persisted receipt on retry, validates receipt identity and payload, prevents an older terminal event from overwriting a newer state, and fails closed with HTTP 503 for ambiguous legacy receipt keys.
- Independent delta review: **ACCEPT**. Targeted tests: **20 passed** (`tests/test_ops_workflow_reconciliation.py` and `tests/test_resend_webhook_idempotency_index.py`); `git diff --check` passed.
- Cloud Build `a96fab06-c09c-4637-85f7-7f69787851ac` succeeded; image digest is `sha256:23f75593957e64c305dc6ac7364a0e53192a120c6ff018192595a0d1f2c27df3`. Current revision `00054-rvl` is Ready at 100%. Its effective runtime configuration matches the previous revision, including runtime identity and secret references.
- On `00054-rvl`, signed synthetic delivery updated the notification to `delivered`; replay returned `duplicate=true` with one receipt. Invalid signature returned HTTP 401 without a receipt. Direct database queries after cleanup found zero synthetic receipt and notification rows.

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

Current API revision `dtd-api-dev-00054-rvl` serves reviewed commit `fdd2c45` and is Ready at 100%. Previous revision `dtd-api-dev-00059-hex` carries DF-043 suppression, the unique receipt index and the same runtime identity, environment names, secret bindings and non-secret container settings, but predates the retry-reconciliation correction. It is a **conditional emergency recovery target only** while trainer-ingest remains paused and no Resend webhook endpoint is configured; it is not fully known-good for webhook processing. Revisions `00049` and `00027` predate DF-043 and are unsafe rollback targets. The conditional recovery was rehearsed on 21 October: traffic moved to `00059-hex`, `/api/health` returned HTTP 200 with database available, `/api/trainers` returned HTTP 200, then traffic was restored to `00054-rvl` and health returned HTTP 200. Final traffic is 100% on `00054-rvl`; trainer-ingest is PAUSED; the authenticated Resend dashboard showed “No webhooks yet.” No application data or provider message was created during the rehearsal. To repeat a recovery, first verify those conditions still hold, assign 100% to `dtd-api-dev-00059-hex` in `australia-southeast1` with `gcloud run services update-traffic dtd-api-dev --project=dogtrainersdirectory-dev --region=australia-southeast1 --to-revisions=dtd-api-dev-00059-hex=100`, then verify revision/image, health/database, DF-043 suppression and Ops authentication. Restore `00054-rvl` after the incident is resolved and webhook reconciliation is confirmed. Conditional recovery readiness is **VERIFIED**; a generally safe rollback while webhook delivery is configured remains a later R3 requirement.

## 21 October targeted runtime acceptance refresh

The current refresh confirms API revision `dtd-api-dev-00054-rvl` and web revision `dtd-web-dev-webidentity`, Ready on 100% developer traffic. `/api/health` and `/` returned HTTP 200. The API image was built from reviewed commit `fdd2c45`. All temporary application records were removed. One support email used Resend's documented test sink; its provider-side test metadata remains. No production action occurred.

| Scenario | Result | Runtime evidence |
|---|---|---|
| API/web basic compatibility | **DONE** | API health/database and web root returned HTTP 200. |
| SR-01 signed Resend webhook, replay and duplicate idempotency | **DONE for synthetic API path; provider delivery NOT_VERIFIED** | On `00054-rvl`, signed delivery updated the synthetic notification to `delivered`; replay returned `duplicate=true`; one receipt remained. Cleanup left zero synthetic receipt or notification rows. No provider endpoint is configured. |
| SR-02 durable receipt recovery after notification-write failure | **DONE locally; live failure injection NOT_VERIFIED** | Regression tests inject notification update failure after receipt persistence, then verify a retry reconciles state. Live sandbox verified successful delivery/replay and invalid-signature rejection; no safe live failure injection was available. |
| Signed event ordering and legacy receipt ambiguity | **DONE locally** | Targeted regression suite verifies stale terminal events do not overwrite newer state and ambiguous legacy receipt keys fail closed. |
| Unsigned/tampered Resend webhook negative paths | **DONE in developer sandbox** | Invalid signature returned HTTP 401 and created no receipt; cleanup confirmed zero remain. |
| Ordinary trainer claim and delivery | **DONE** | Browser claim on current web/API reached “Identity claimed”; `claim_events` reached `verified`, trainer claim/tier persisted, start/verify audit rows existed, and Resend returned HTTP 200 with provider message ID. |
| Claim exception: valid address does not match listing | **DONE in developer sandbox** | Synthetic mismatch returned HTTP 403, wrote one `needs_review` claim event with mismatch reason, and created no notification; fixture and event were removed and verified absent. |
| Claim challenge negative cases | **DONE in developer sandbox; DF-051 OPEN for state reconciliation** | Invalid OTP returned HTTP 400 and incremented attempts; expired OTP returned HTTP 410 and persisted `expired`; max-attempt challenge returned HTTP 429 and persisted `locked`; disputed profile returned HTTP 409 and event `stale`; missing claim email returned HTTP 409 and `needs_review`; unavailable SMS returned HTTP 503 and `provider_unavailable`; replay of a verified event returned HTTP 409 without undoing the verified claim. Each fixture was removed and queried absent. The expired case left the unclaimed trainer `pending_verification`; see DF-051. |
| Privacy request without trusted subject proof | **DONE** | Authenticated synthetic `authorise_scrub` returned HTTP 403; request document was byte-for-byte unchanged and no case audit row was written. |
| Verified privacy scrub / positive-resolution completion | **NOT_VERIFIED; mapped to R5** | No trusted synthetic subject-verification flow was available; no scrub was attempted. |
| Compliance suppression and attempted republication | **DONE** | Synthetic public trainer was suppressed; authoritative delisted identity was written, public API returned 404, matching held submission approval returned HTTP 403 and stayed held, and suppression audit evidence existed. |
| Trainer delisting, notification and public removal | **DONE** | Synthetic trainer delist returned HTTP 200; trainer was inactive/unpublished, authoritative suppression row and audit were present, public API returned 404, and test-sink notification was recorded `sent` with HTTP 200/provider ID. |
| Fraud quarantine confirm-spam negative path | **DONE in developer sandbox** | Synthetic quarantined intro returned HTTP 200 with blacklisted state and one Ops audit row; no notification was created. Fixture and auth-limiter state were removed and verified absent. |
| Support reply concurrency and idempotency | **DONE in developer sandbox** | Five concurrent duplicate operator replies resulted in one outbound dispatch, one persisted message, one notification and one audit row. Destination was Resend's test sink. All application fixture rows were removed and verified absent. |
| Support intake persistence and notification | **DONE in developer sandbox** | POST returned HTTP 200; one open synthetic support thread, one `support_inquiry_created` audit row and one `sent` notification with provider ID were observed. Fixture rows were removed and verified absent. The Resend test-sink metadata remains provider-side. |
| Support reply delivery failure/fallback | **NOT_VERIFIED; mapped to R7** | Local mocked failure coverage exists; live safe failure injection is unavailable. No real recipient was contacted and no notifier credentials were changed. |
| Specialised support closure | **DONE in developer sandbox** | Synthetic thread closed with a truthful synthetic note, resolved state and one Ops audit row; all fixture rows were removed and verified absent. |
| Durable obligations completeness and positive terminal resolution | **NOT_VERIFIED; mapped to R7** | Only local mocked evidence exists. No bounded per-fixture live sync path was available; broad engine-tick execution was avoided. |
| Protected Ops authentication / DF-038 | **DONE in developer runtime; remote source integration pending R2** | No passcode returned HTTP 401; current developer passcode returned HTTP 200; previous version was rejected. Synthetic auth-limiter state was removed. Fail-closed runner retirement is independently accepted in local commit `85bb608`; historical Git retains the disabled value. |

### Required SR/CF scenario disposition on the current release

The accepted R0 code matrix remains accepted; the table below records current developer-runtime coverage and carries forward only evidence for paths unchanged by `fdd2c45`. **PARTIAL** means some subcases passed but the full scenario is not runtime-accepted.

| Scenario | Status | Current evidence and remaining subcase |
|---|---|---|
| SR-01 — Resend webhook delivery/status reconciliation | **PARTIAL; remaining provider and injected-failure checks assigned to R3** | Synthetic signed delivery, replay, signature denial and cleanup passed on `00054-rvl`; write-failure retry recovery passed in local regression tests but was not injected live. Provider-originated delivery is `NOT_VERIFIED` because no endpoint is configured. |
| SR-02 — Held trainer submission review | **PARTIAL; positive journey assigned to R5** | Live held-submission suppression denial passed; positive review/publication with statutory consents, provenance and ABN rules was not rerun on this release. |
| SR-03 — Claim adjudication | **PARTIAL; DF-051 and remaining positive/conflict journeys assigned to R5** | Ordinary claim success carries forward because `fdd2c45` changes only webhook handling. Email mismatch, invalid OTP, expiry, lock, disputed profile, missing claim email, unavailable SMS and verified-event replay were tested live. Expired claim leaves stale `pending_verification` profile state (DF-051); conflicting verified-owner acceptance remains. |
| SR-04 — Support intake/reply/closure | **PARTIAL; safe failure/fallback assigned to R7** | Live intake produced one thread, one audit, and one successful test-sink notification; duplicate concurrency produced one dispatch; closure was audited. Failure/fallback injection remains unverified. |
| SR-05 — Privacy scrub | **PARTIAL** | Current unverified-subject request returned 403 with zero mutation/audit. Positive scrub after trusted identity proof was not attempted and remains assigned to R5. |
| SR-06 — Durable obligation reconciliation | **NOT_VERIFIED live; positive scoped path assigned to R7** | Current code tests/mock evidence remain accepted; no bounded live sync, completeness scan or positive terminal resolution was run. |
| CF-01 — Privacy proof provenance/fail closed | **PARTIAL** | Unverified scrub denial passed live; the full verified-proof and error-provenance matrix was not run live. Positive privacy flow is R5. |
| CF-02 — Publication authority/deduplication/concurrency | **PARTIAL; positive consented publication assigned to R5** | Suppression, republish denial and delisting passed live; positive publication and publication race cases were not rerun live. |
| CF-03 — Claim proof/expiry/conflicts | **PARTIAL; DF-051 and remaining conflict acceptance assigned to R5** | Invalid, expired, locked, disputed, missing-email, unavailable-SMS and verified-event replay cases were exercised. Expiry left the trainer at `pending_verification` after the event reached terminal `expired`; see DF-051. Conflicting verified-owner acceptance remains. |
| CF-04 — Support message concurrency/closure safeguards | **PARTIAL** | Live five-way duplicate reply and specialised closure passed; provider failure/fallback remains unverified and is assigned to R7 for safe delivery-path acceptance. |
| CF-05 — Obligation completeness/waiting/read-only invariant | **NOT_VERIFIED live** | Local tests cover large scans, waiting states and zero writes; no bounded current-release live fixture path exists. Positive obligation resolution/completeness remains open for R7. |

R1 runtime acceptance is **DONE WITH NAMED BLOCKED FOLLOW-UPS under the written exit contract**. Each remaining item is assigned to its roadmap stage below; this status does not claim those workflows are complete. Trainer-ingest is explicitly **PAUSED**, as permitted by the R1 contract. DF-044/045 remain R4 activation dependencies and must be resolved before any later ingestion reactivation. DF-051 is a newly verified R5 claim-state defect. Positive trainer/privacy journeys and publication acceptance are assigned to R5; support notifier failure/fallback and scoped obligation resolution/completeness are assigned to R7; provider-originated webhook verification and recovery safe when webhook delivery is configured are assigned to R3. Conditional recovery to `00059-hex` was rehearsed and `00054-rvl` restored. DF-042/043 and the accepted R0 review remain preserved.

### DF-051 — Expired claim challenge leaves stale pending profile state

On `dtd-api-dev-00054-rvl`, an isolated synthetic expired-claim challenge returned HTTP 410 and persisted its `claim_events` row as `expired`, while the trainer remained `claim_status=pending_verification` and `is_claimed=false`. `backend/services/trainer_quality.py:is_claimed_profile()` treats `pending_verification` as claimed for acquisition deduplication. An expired, unclaimed profile may therefore be treated as claimed by later acquisition/update workflows. All synthetic trainer, claim-event and notification rows were removed and direct queries confirmed zero leftovers. Assign the smallest correction and regression coverage to R5; no live profile was changed.

## DF-038 credential discrepancy discovered during R1

The frozen accepted branch `1ac4138` still contains the historical Ops verification script and its now-disabled developer passcode. The script was not run. Local commit `85bb608` replaces it with a fail-closed stub and passed independent source review, but remote branch `fix/ops-security-integrity-d83c7f4` has not yet received that commit. The current API image archive excludes the root-level script. Developer Secret Manager version 2 is disabled and version 3 is active. The value is not recorded. Production secrets were not queried or changed.

## Newly confirmed webhook idempotency gap

The initial 0%-traffic developer probe accepted the same signed synthetic event twice and persisted two rows because `resend_webhook_events` had no unique index. The issue was fixed in independently accepted local commit `e207dbef`, built as `fe4e210b`, and deployed to current developer revision `00059-hex`. The unique `id_1` index exists; replay returned `duplicate: true` with one persisted row. The event was deleted and a direct query confirmed zero leftovers. Invalid-signature paths returned HTTP 401. Resend has no configured webhook endpoint, so provider-originated delivery remains unverified.
