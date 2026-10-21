# R1 Sandbox Fixture Cleanup Record

**Date:** 21 October 2026
**Scope:** bounded DF-043 verification and targeted SR/CF runtime checks on the developer sandbox only.

- The original `dtd-trainer-ingest-cron` was kept paused throughout the live fixture run.
- A temporary separately named Cloud Scheduler job used the configured OIDC identity and was deleted after the run; job listing confirmed it absent.
- The existing unclaimed synthetic trainer fixture and newly discovered suppressed candidate were removed after checks; corresponding suppression/delisting fixture records were removed.
- The isolated ingestion run record was removed.
- Post-cleanup database checks found no remaining synthetic trainer, queue item, delisting record or run record. Public trainer count remained 20 and no synthetic identity appeared.
- The candidate URLs used the reserved `.invalid` domain and were suppressed before external fetch.
- No production records, real trainer profiles, provider messages or billing state were changed.

Cleanup status: **DONE** for the bounded fixture set. Exact identifiers are omitted from this public repository artifact because fixtures used transient synthetic identifiers; session/tool output retained the execution trace.

## 21 October cleanup verification

- Ordinary browser claim fixture: deleted 1 trainer, 1 claim event, 1 notification event and 2 claim audit rows. The runner verified no matching leftovers and public trainer lookup HTTP 404 before exit. The UI displayed the claimed state before cleanup. Resend's provider log retains test-sink delivery metadata; no real mailbox was used.
- Unverified privacy fixture: deleted 1 synthetic support thread; a post-delete query found 0. The attempted scrub returned 403 without mutating the document or adding a case audit row.
- Compliance suppression/republication fixture: removed the synthetic trainer, held submission, authoritative and legacy suppression rows, and suppression audit. Post-cleanup counts were all 0.
- Trainer delisting fixture: removed the synthetic trainer, authoritative/legacy delist rows, notification row and audit. Post-cleanup counts were all 0. The Resend test-sink provider log retains delivery metadata only.
- Protected Ops passcode checks: synthetic authentication-limiter row was deleted; a direct database query confirmed zero matching rows. Developer Secret Manager v2 was disabled after replacement v3 was validated; no passcode value is recorded here.
- Resend webhook idempotency checks: the initial failing probe's three synthetic event rows were removed and verified absent. After the fix was deployed, the successful replay fixture persisted one event row; cleanup deleted it and a direct query confirmed zero remained. The temporary signing key v1 was disabled; current developer revision uses generated developer-only version 2. Resend's authenticated dashboard showed no webhook endpoints, and no production/provider event was sent.
- No real trainer, customer, production record, live payment or production provider state was changed. The original trainer-ingest Scheduler remained paused.

Cleanup status for the four workflow fixtures, synthetic auth state and webhook events: **DONE**. Provider-side test-sink message metadata is intentionally retained by Resend; application database rows and public profiles were removed and verified absent.
