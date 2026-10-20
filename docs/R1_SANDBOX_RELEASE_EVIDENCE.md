# R1 Developer Sandbox Release Evidence

**Date:** 21 October 2026
**Frozen baseline:** R0 `1ac4138e4d82991501139298cc624be732661119`
**Accepted delta:** DF-043 `50f3c594d611bede8b7a610d7b09fb3fd8680f23` (parent is frozen R0)
**Developer API:** `dtd-api-dev-00050-7r7`, 100% traffic
**Developer web:** `dtd-web-dev-webidentity`, 100% traffic

## Code review and build

- Independent delta review: **ACCEPT**; review covered canonical suppression identity, stale identity fields, key coverage, existing and new candidate paths.
- Targeted regression command was rerun from the patch worktree after commit: `17 passed, 15 deselected`; `git show --check` passed.
- Cloud Build `60b33ff5-d5d0-41f6-a32d-3d36ff8686b3` in `australia-southeast1`: `SUCCESS` (2026-10-20 10:18–10:20 UTC). All 46 API source files in its immutable archive matched the corresponding tracked backend files at `50f3c594`; no archived backend file was untracked or mismatched.
- Image digest: `sha256:c0611310f825b453162a2b8c8392b0b220cb256c5dfce58b2507b452506404b1`.
- API identity: `dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`; revision Ready and 100% traffic.
- `/api/health` and `/api/trainers` returned HTTP 200; database health was available; trainer response contained 20 public records.
- Web revision `dtd-web-dev-webidentity`, image `sha256:30cac8e4d00807f37c1d88c66dbc92019a5f40b21fe04db351356beb7c17c01a`, runtime identity `dtd-web-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`, Ready and 100% traffic. Build `638f12ff-03f6-49a9-bafa-d87740aac1d7` succeeded on 18 October; 122 tracked frontend source files in its archive matched commit `50f3c594`, with no mismatches. `/` returned HTTP 200.

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

Current API revision `dtd-api-dev-00050-7r7` (the `50f3c594` image) is the safe traffic-recovery target for future regressions in this release line. The immediate previous revision `dtd-api-dev-00049-brd` is the vulnerable pre-DF-043 image and must not be used as a known-good rollback while republishing can reach it. To restore service traffic after a later bad revision, assign 100% to `dtd-api-dev-00050-7r7` in `australia-southeast1` and verify health, database availability, image digest and suppression behavior. Traffic rollback was not exercised. This is code-path recovery readiness, not a claim that all R1 workflows are accepted. Overall rollback readiness remains **PARTIAL**.

## 21 October targeted runtime acceptance refresh

These checks used current developer API revision `dtd-api-dev-00050-7r7` and current web revision `dtd-web-dev-webidentity`. They used UUID-namespaced records and the Resend test sink only; all application fixtures were removed and checked after use. No further privileged `/ops` action was attempted after the DF-038 credential discrepancy below was confirmed.

| Scenario | Result | Runtime evidence |
|---|---|---|
| API/web basic compatibility | **DONE** | API health/database and web root returned HTTP 200. |
| Signed Resend webhook, replay and duplicate idempotency | **NOT_VERIFIED** | Revision `00050` has no `RESEND_WEBHOOK_SECRET`; signed delivery and replay cannot be exercised without a separately authorised developer secret change. |
| Unsigned Resend webhook negative path | **DONE** | Synthetic unsigned event returned HTTP 500 (`Webhook signing secret not configured`) and created no `resend_webhook_events` row. This is fail-closed, but does not substitute for signed/replay acceptance. |
| Ordinary trainer claim and delivery | **DONE** | Browser claim on current web/API reached “Identity claimed”; `claim_events` reached `verified`, trainer claim/tier persisted, start/verify audit rows existed, and Resend returned HTTP 200 with provider message ID. |
| Claim exception cases (invalid/expired/replayed challenge) | **NOT_VERIFIED** | Current deployment was not exercised for these negative challenge cases. |
| Privacy request without trusted subject proof | **DONE** | Authenticated synthetic `authorise_scrub` returned HTTP 403; request document was byte-for-byte unchanged and no case audit row was written. |
| Verified privacy scrub / positive-resolution completion | **NOT_VERIFIED** | No trusted synthetic subject-verification flow was available; no scrub was attempted. |
| Compliance suppression and attempted republication | **DONE** | Synthetic public trainer was suppressed; authoritative delisted identity was written, public API returned 404, matching held submission approval returned HTTP 403 and stayed held, and suppression audit evidence existed. |
| Trainer delisting, notification and public removal | **DONE** | Synthetic trainer delist returned HTTP 200; trainer was inactive/unpublished, authoritative suppression row and audit were present, public API returned 404, and test-sink notification was recorded `sent` with HTTP 200/provider ID. |
| Fraud quarantine release/spam confirmation | **NOT_VERIFIED** | No live synthetic fraud case was run on this revision. |
| Support concurrency, delivery failure/fallback and specialised closure | **NOT_VERIFIED** | Not rerun against the current revision; protected admin credential source requires resolution before further privileged Ops requests. |
| Durable obligations completeness and positive terminal resolution | **NOT_VERIFIED** | Code tests remain accepted R0 evidence; no current-revision synthetic Ops obligation lifecycle was run. |
| Protected Ops authentication | **PARTIAL** | `/api/oversight` returned 401 without a passcode and 200 with the then-current sandbox passcode. A source-to-secret match discovered afterward means no further privileged action should use that value until owner-authorised rotation and source cleanup; see DF-038. |

R1 remains **PARTIAL**. The scheduler may remain disabled under the R1 exit contract, but signed webhook/replay, claim exceptions, support, fraud, obligations, verified privacy, and the credential gate are outstanding. The API has no `RESEND_WEBHOOK_SECRET`. This checkpoint does not reopen DF-042/043 or the accepted SR/CF code review.

## DF-038 credential discrepancy discovered during R1

The frozen accepted branch `1ac4138` and current DF-043 branch still contain a tracked historical Ops verification script with a literal that matches enabled developer Secret Manager version 2. The script was not run. This contradicts the current-state description that the unsafe runner was replaced on the branch; remote branch `fix/ops-security-integrity-d83c7f4` still points to `1ac4138`. The current API build source archive did not include that root-level script, so no claim is made that the value is present in the API container. The developer secret nevertheless remains exposed in public Git source/history and active; owner-authorised credential rotation and reviewed source retirement are required before additional authenticated Ops acceptance. No value is recorded here. Production secrets were not queried or changed.
