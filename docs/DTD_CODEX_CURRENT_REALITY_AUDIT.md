# DTD Independent Current-Reality Audit

**Evidence date:** 20 October 2026
**Frozen baseline:** R0 accepted code `1ac4138e4d82991501139298cc624be732661119`
**Scope:** source, GitHub, developer Cloud Run/Scheduler, sandbox database, public config/health, current skill governance and available authenticated provider access. Production was inspected only where stated; no production mutation or credential retrieval was performed.

## Executive disposition

**R1 remains BLOCKED for scheduled ingestion activation.** DF-043 was fixed in a separately reviewed commit parented on frozen R0, deployed to the developer API, and verified by targeted tests and bounded live synthetic cases. DF-042 was addressed by attaching the dedicated zero-direct-role `dtd-web-dev-runtime` identity to the public developer web service; canary and promoted web/API flows passed. A newly confirmed DF-045 robots fail-open remains a direct scheduled acquisition safety gap, while DF-044 source URL/domain approval remains unresolved. The original trainer-ingest job is therefore verified **PAUSED**. Engine-tick remains enabled and does not call ingestion. This is a scoped R4 dependency, not a restart of the roadmap.

The accepted R0 remains `1ac4138e4d82991501139298cc624be732661119`. The exact DF-043 delta is `50f3c594d611bede8b7a610d7b09fb3fd8680f23`; deployed API revision `dtd-api-dev-00050-7r7` serves 100% traffic. Revision `dtd-api-dev-00049-brd` remains Ready as a traffic rollback target, but a rollback-to-known-good exercise was not performed.

## Verified current state

| Area | Evidence | Result |
|---|---|---|
| R0 | Exact local baseline SHA and accepted checkpoint evidence | `DONE` for code acceptance only; not runtime or business acceptance |
| Git | Local branch `fix/ops-security-integrity-d83c7f4` is six commits ahead of `main`/`origin/main` `d83c7f4`; PR #11 merged; PR #12 remains open with dirty merge state | No push/merge performed; preserve existing tree |
| API sandbox | Cloud Run `dtd-api-dev-00050-7r7`, 100%; Cloud Build `60b33ff5-d5d0-41f6-a32d-3d36ff8686b3`; exact accepted patch `50f3c594d611bede8b7a610d7b09fb3fd8680f23` | Health/database and trainer API returned 200; rollback target `00049-brd` remains Ready |
| Web sandbox | 100% on dedicated `dtd-web-dev-webidentity` revision; service runs as `dtd-web-dev-runtime` | Canary and promoted `/api/config`, `/api/trainers` calls returned 200; 20 cards rendered; previous revision `00021-pzw` remains available |
| Production API | Cloud Run `dtd-api-00058-ter`, 100%; uses dedicated `dtd-runtime`; two older revisions retain audit tags | No production change; exact source SHA and live health `NOT_VERIFIED` in this snapshot |
| Production Scheduler | `dtd-pro-trial-warnings` is the only listed job in the region, enabled daily 09:00 Melbourne | No trainer-ingestion job observed; production job not invoked |
| Production Firebase | Authenticated site inventory lists the DTD and First Leash sites | Read-only visibility confirmed; no hosting deploy or site mutation |
| Data isolation | API Secret Manager binding resolves to `dtd_sandbox` on isolated Atlas `dtd-sandbox`; in-memory ping passed | Developer isolation `DONE`; no production data touched |
| Ingestion scheduler | PAUSED; original daily 02:00 Melbourne, OIDC audience, 180-second deadline, `{}` body preserved | DF-043 path fixed and tested; activation remains blocked by DF-045 and DF-044 source-scope controls |
| `DISABLE_AUTONOMY` | Gates background runtime loops, not the direct Cloud Scheduler ingestion endpoint | Not an ingestion safety switch |
| Guardian | Audits duplicates/statutory/schema conditions, not delisted entities | Clean Guardian status does not prove suppression |
| Engine tick | `dtd-engine-tick-cron` remains enabled and separately targets engine loops | Preserved; not changed by containment |
| Rollback | Previous API revision `dtd-api-dev-00048-z2q` remains available but source differs from both R0 and current `main` | Mechanism `PARTIAL`; known-good rollback `NOT_VERIFIED` |
| Suburbs | DB has zero active v1 suburb rows; public config returned static 539-suburb catalogue | Public fallback works; DB seed parity `NOT_VERIFIED`, not an R1 blocker |
| AI health | Six recent events, all recovered fallback events from `ops_ai_investigation`; none from matching or trainer-source extraction | Telemetry defect DF-046; not an R1 blocker |
| Firebase | CLI authenticated principal (email omitted); project listing succeeds, Hosting site list returns 403 | `firebasehosting.sites.list` is missing/not granted; Hosting inventory `NOT_VERIFIED`; Cloud Run web is current target |

## Suppression reproduction and proposed delta

The baseline synthetic reproduction invoked the same `server.run_trainer_ingest_job()` route as Scheduler, with only the OIDC boundary and external data providers mocked. It enabled Guardian and isolated all persistence in a fake DB:

| Case on R0 | Observed result |
|---|---|
| Existing unclaimed trainer with `delisted_entities.trainer_id` record; identity fields intentionally changed | Trainer became `published=true`; queue became `promoted`; one trainer remained; Guardian `clean` |
| New candidate matching a synthetic delisted identity | Inserted `published=true`; queue became `promoted`; trainer count 1; Guardian `clean` |

**Finding:** DF-043, P1, R1 release-safety blocker, confirmed on isolated fixtures only. This does not prove any real trainer was republished.

The exact delta adds canonical suppression lookup (including trainer-ID references), pre-fetch and extracted-identity checks, suppression queue disposition and regression coverage. Independent review accepted the exact patch. Commit `50f3c594d611bede8b7a610d7b09fb3fd8680f23` is parented directly on R0 and was pushed to `codex/df043-ingestion-suppression`. Targeted rerun: 17 passed, 15 deselected; `git show --check` passed. Cloud Build `60b33ff5-d5d0-41f6-a32d-3d36ff8686b3` succeeded and produced revision `dtd-api-dev-00050-7r7`, image digest `sha256:c0611310f825b453162a2b8c8392b0b220cb256c5dfce58b2507b452506404b1`. API health and trainer-list routes returned 200.

A temporary OIDC Scheduler job exercised the deployed route without resuming the original job. Existing unclaimed delisted identity remained unchanged; a newly discovered suppressed identity was not inserted. Both were counted suppressed, no fetch occurred for `.invalid` fixtures, Guardian was disabled in this live fixture run, and synthetic documents/run record/job were removed and verified. Details are in `R1_SANDBOX_RELEASE_EVIDENCE.md` and `R1_FIXTURE_CLEANUP.md`.

## Authentication and access matrix

| Surface | Principal / identity | Verified access | Boundary / unresolved item |
|---|---|---|---|
| GitHub | Existing authenticated integration | Read current branches, PRs and CI evidence; R0 Verify run 39240506209 passed | No new push or merge |
| GCP project | Existing `gcloud` session | Read Cloud Run, Scheduler, logs, project IAM, Secret Manager binding metadata; authorized developer web identity created/attached | No production IAM change; no default Compute role removal |
| API runtime | `dtd-api-dev-runtime` | Cloud Run runtime; Secret Manager accessor and Vertex AI User | Appropriate dedicated API identity; exact deployed code is not R0 |
| Web runtime | `dtd-web-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com` | Attached to public developer web; no direct project role or secret-level binding found; live canary and promoted API flows passed | Inherited effective permissions not simulated because Policy Troubleshooter is disabled. DF-042 DONE within verified scope |
| Sandbox DB | Runtime secret reference, read in process only | `dtd_sandbox` on `dtd-sandbox`; ping verified | Secret value not emitted or persisted |
| Firebase CLI | Authenticated principal (email omitted) | Production DTD/First Leash site inventory succeeds | Developer project `firebase hosting:sites:list` returns 403: missing/not granted `firebasehosting.sites.list`; not required for current Cloud Run R1 |
| Composio | None | No `$composio-...` invocation | Repo policy requires explicit user invocation |

**Precise owner action currently needed:** none for the web identity or DF-043 delta; both have been executed under the supplied authorization. If the owner wants Firebase Hosting inventory, the Firebase principal needs `firebasehosting.sites.list`; that permission is not required for Cloud Run R1. No default Compute identity roles were removed.

## R1 acceptance not rerun in this refresh

The DF-043 deployment verification was bounded to health, public trainer read, the two suppression scenarios and fixture cleanup. This turn did not rerun the broader R1 SR/CF sandbox matrix: signed/replayed webhook and idempotency; held-trainer approval; claim OTP success/invalid/expired/conflict; support intake/reply/dedup/concurrency/closure; privacy scrub refusal; fraud release and delisting; durable obligations and read-only oversight; `/ops` auth/audit/UI compatibility. Their prior code acceptance remains intact; current sandbox runtime acceptance for those scenarios is **NOT_VERIFIED** here. DF-044/045 specifically block restarting scheduled ingestion, while those other scenarios retain their own verification status and do not reopen accepted work wholesale.

## Findings roll-up

- **R1:** DF-043 `DONE`; DF-042 `DONE` for developer web runtime identity; activation remains `BLOCKED` by direct acquisition safety DF-045 and source-scope DF-044. Rollback target exists but known-good rollback remains `PARTIAL`.
- **R3:** DF-046 recovered-event telemetry misclassification remains open. Current DF-043 API build/revision provenance is recorded; rollback-to-known-good and independent provider-management recovery remain incomplete.
- **R4:** DF-044 URL/domain approval and DF-045 robots fail-open remain `OPEN`; neither proves an actual unauthorized fetch. DF-045 directly blocks reactivation of the scheduled acquisition path.
- **R5:** DF-030 remains open: owner revisit loses claim session authorization. DF-021 evidence is partial; prior M9 event shows `empty_match_verified` while docs retain broader wording. DF-041 successful submission path remains unverified; preserve existing status.
- **R6:** Static fallback and prior non-degraded Gemini evidence exist. Six recent degradation events were recovered fallback events from unrelated operations, not matching. Do not elevate AI or static fallback to R1 blocker. Current full matching scenario parity was not rerun.
- **R7:** Existing Phase 1–5A Ops evidence is preserved. Do not reopen accepted phases. DF-047 support case `/ops` workflow and DF-048 inaccurate contact receipt wording are confirmed by code review; scope to affected transactions only.
- **R8:** Integrated end-to-end owner-to-ops workflow remains open until R4–R7 paths and cleanup are accepted together.
- The suspected candidate-cap mismatch was disproved: the v2 matching contract caps local/expanded scoring with `MAX_ELIGIBLE_CANDIDATES=15`. No finding opened.

## Skills and specialist work used

- Active skills: `dtd-proactive-owner-assistance`, `dtd-feature-workflow-completion`, and `session-cleanup` for task-scoped artifact handling. They guided evidence-first findings, end-to-end coverage and cleanup boundaries; they did not override project authority.
- Three read-only specialist reviews covered backend/matching, frontend/Ops and Git/provider state. They surfaced DF-030 and affected R5/R7 paths, helped identify acquisition controls for direct code verification, and checked provider/runtime evidence. Their output was treated as leads and independently checked against code/provider state; none accepted the new code delta.
- GCP, GitHub, Firebase CLI and public HTTP were used; the web identity and developer release actions used the explicit owner authorization. Firebase Hosting inventory remains unavailable due to the missing `firebasehosting.sites.list` permission. No production IAM or service change was made.
