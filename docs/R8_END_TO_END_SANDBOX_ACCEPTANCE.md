# R8 Developer-Sandbox Independent Audit

**Current evidence date:** 23 October 2026 (Australia/Melbourne).

**Current disposition: NOT ACCEPTED.** The 22 October implementation handover is superseded as an acceptance decision; its original assertions remain in git history. Local suites pass, but the candidate is undeployed and material workflow failures are reproducible. R0–R3 retain their accepted checkpoints. R9 remains separately gated by completed sandbox acceptance, the owner's audit and specific production authority.

## Independent audit boundary

- Exact cumulative candidate: `a20687e60ffbad9384f78c88b42956dccde9cfe6..4a5fe84403f9908c20ab8562552919feccf9513e`, branch `feature/r4-trainer-supply`; four local commits and 18 changed files.
- Remote `refs/heads/main` remains `a20687e60ffbad9384f78c88b42956dccde9cfe6`; the candidate branch was not found remotely.
- Independent backend/frontend reviewers inspected actual source. The coordinating reviewer inspected and reran their isolated reproductions, separately reproduced capability-prefill and claimed-owner recovery failures, ran the maintained suites, and inspected authenticated developer Cloud Run/Scheduler and browser state.
- Actors covered: dog owner, trainer, operator, acquisition automation and AI analyst. Authority is `AGENTS.md` §6A, existing DF/M contracts and the R4–R8 roadmap exits. The review does not grant new product, source-use or production authority.

## Current deployment and safety evidence

| Surface | Observed state on 23 October | Meaning |
| --- | --- | --- |
| API | `dtd-api-dev-r3-9dd53ed6`, 100%; image `sha256:10398ce474bd4835377454619714f4fc6d0b2e25d895567564f5764f406c6d36` | Serving R3 revision was created before the candidate commits. |
| Web | `dtd-web-dev-00023-phd`, 100%; image `sha256:5eba05c8ed409087498edcb18533e6b34b2b782cffd4f98827a705acaf7505d5` | Live `/assets/index-B7QXYDjb.js` lacks Support Cases and `receipt_delivered`; local candidate builds `/assets/index-DvtJ-eS4.js`. |
| Health / database | `/api/health` HTTP 200, database available; deployed `DB_NAME=dtd_sandbox` | Availability and configured database name verified, not candidate workflow completion. |
| Safety | `ENABLE_TRAINER_BILLING_CHECKOUT=0`; `OPS_SELF_HEALING_ENABLED=0`; trainer-ingest PAUSED on `0 2 * * *`, Australia/Melbourne | Retain these gates. |
| Ops | Sign-in works; expanded navigation has no Support Cases. Overview reports action required, five high-priority items, 2/11 healthy loops and nine warnings. | New support workflow cannot be exercised live. Loop warnings need interpretation against the existing routine scheduler profile; no new root cause is inferred from counts alone. |
| Recovery | `dtd-api-dev-00055-kbm` exists, Ready=True, Active=False/Retired | Preserve its conditional emergency limits in `R3_RELEASE_FOUNDATION.md`; existence does not prove candidate-equivalent or security-remediated rollback. |

Supported authenticated Google Cloud reads succeeded after owner reauthentication. No deployment, traffic, flag or Scheduler change occurred. Production was not mutated or freshly audited; this review cannot prove every historical action asserted by the earlier author.

## Proven failures and required corrections

| Priority / existing ID | Observation and impact | Required acceptance |
| --- | --- | --- |
| P1 / DF-006, R8 | Packet claims complete sandbox acceptance, but serving API/web predate the candidate. No candidate revision/image mapping or case-level runtime/cleanup evidence is supplied. | Independently accept corrected exact code SHA, then deploy it to developer sandbox and prove the integrated matrix. |
| P1 / DF-047 | `Ops.jsx:3677–3690` changes selected case ID while retaining old displayed detail. Actual React reproduction: A remains displayed after B's detail load fails, but reply targets B. Close uses the same inconsistent selection. No real message was sent. | Clear/correlate detail, discard stale responses, and require displayed identity to equal the mutation target; verify failed and out-of-order loads. |
| P1 / DF-051 | `trainer_quality.py:375–385` returns unprotected on expired pending challenges before durable paid/ownership/submission/billing checks. All four protected fixtures returned false. The 900-second fallback also overrides a future explicit expiry. | Preserve durable protection and authoritative expiry; verify acquisition rerun/publication/suppression invariants. |
| P2 / DF-044 | `source_approvals.py:141` admits any path/subdomain despite exact approved index URLs. Registry adds `example.com`; candidate wildcard permits non-trainer directory/aggregator URLs. Evidence for newly asserted association-source approval was not found in reviewed active records. No external acquisition request occurred. | Enforce documented source scope, remove test-domain authority, verify existing source-use evidence and leave unapproved sources disabled. |
| P2 / DF-045 | Parser silently accepts mocked HTTP-200 HTML as robots policy and target fetch proceeds. Exception-only malformed handling at `ingestion_manager.py:110` is insufficient. | Defer on unusable policy; verify valid/missing/denied/unavailable/malformed branches before target fetch. |
| P2 / DF-047 | `Ops.jsx:3707` reports success for API `ok:true, dispatched:false, status:reply_delivery_failed`. Both success notices appeared in actual component reproduction. Persisted message delivery state is omitted from the view. | Distinguish accepted/duplicate/skipped/failed outcomes and expose bounded retry/evidence. |
| P2 / DF-030, M1 | `TrainerDetail.jsx:35–43` reads nonexistent `declared_value`, whereas facts use `canonical_value`/`value`. A structured fixture reopens with empty formats/stages, base suburb and false/zero delivery constraints. Saving can replace valid matching capacity. | Use existing protected prefill/canonical facts and verify load/edit/save without duplicated top-level fields. |
| P2 / DF-030 | Missing-session editor offers email verification, but the actual claim-start handler rejects already-claimed owners with HTTP 409. Expired stored sessions yield 401 without renewal. | Complete bounded returning-owner recovery under existing auth policy, including absent/expired sessions and edit/billing authorization. |
| P2 / DF-052 | Query errors now fail closed, but accounting counts upserted documents and is non-atomic. Four repeated mocked provider calls under limit two left one investigation and continued allowance; two concurrent requests under limit one both called the provider. | Atomically reserve/count provider attempts and bound concurrency; retain the valid query-failure fix. |
| P2 / DF-047, R7 | Delisting intake sends a name without the trainer ID required by closure; Support Cases lacks linking/delisting actions. Privacy closure requires processed state but has no processing action in this view. | Connect existing bounded category actions and verified outcomes through `/ops`, preserving backend safeguards. |
| P2 / DF-041, DF-050, M1–M6/M8, R8 | Terms-rejection tests do not prove successful public onboarding. Release-specific provider, follow-up, alert receipt and integrated workflow evidence remain missing. `Ops.test.jsx` has no Support Cases interaction tests despite the packet citing its 27 passing tests. | Fill the existing missing clauses with owned fixtures, approved sinks, mobile/keyboard/screen-reader captures and verified teardown; preserve valid earlier evidence. |

Additional DF-047 inconsistencies: reply UI offers `in_progress` while the API always persists `awaiting_customer_reply`; the newest-50 case list has no pagination/truncation notice.

## Owner guide coverage: expected versus actual

| Guide step | Expected | Actual / classification |
| --- | --- | --- |
| 1. Evidence / Git | Independently accepted R4–R8 and current deployments | Four local commits verified; acceptance and blanket closure claims rejected. |
| 2A. Matching / urgent / thin supply | Current candidate's complete mobile/desktop ordinary and negative journeys | Live questionnaire renders; local matching scenarios pass within full suite. Candidate browser/provider journey NOT_VERIFIED because candidate is undeployed. Earlier M9 evidence remains supporting, time-bounded evidence. |
| 2B. Profile / claim | Saved declaration, authorization and later recovery | Same-tab storage tests pass; canonical-prefill and returning-owner failures reproduced. Candidate runtime NOT_VERIFIED. |
| 2C. Contact | Truthful feedback, persisted case and notification/fallback | Local tests pass; live form renders but bundle lacks new receipt logic. No live inquiry submitted. |
| 3. Ops | Queue, reply, category resolution, health and evidence | Live sign-in/overview/navigation/System Activity inspected; no Support Cases. Candidate wrong-case and false-dispatch failures reproduced with mocks. No real reply/closure executed. |
| 4. Tests / safety / cleanup | Disabled gates, isolated checks and clean teardown | Developer safety posture verified; suites/build/guards pass. No sandbox business fixtures created by this audit. |
| 5. Go/no-go | Accepted candidate basis for owner decision | NO-GO for R8 acceptance; R9 remains separately gated. |

## Independent validation and cleanup

- Maintained isolated backend runner: **657 passed**, 17.91s pytest time; disposable loopback MongoDB/API, successful exit through teardown.
- Frontend: **79 passed / 11 files**; Vite build PASS with existing large-chunk warning; copy guard and prelaunch release gate PASS.
- Backend reproductions: source scope, malformed robots, protected expired/future-expiry claims, repeated budget calls and concurrent budget overshoot; mocked outbound calls and in-memory storage only.
- Frontend reproductions: actual React component confirms wrong-case target and false success; actual capability helper confirms canonical-fact loss; actual handler with in-memory lookup confirms claimed-owner recovery rejection.
- Browser: developer homepage/contact/Ops inspected using in-app browser after Playwright MCP reported a missing browser executable. Google Cloud service/revision/Scheduler reads verified runtime facts. No broader plugin was needed for these source/provider reads.
- Candidate mobile/screen-reader acceptance, successful onboarding, browser-submitted protected enquiry, provider-originated notification/recovery, opt-in follow-up and integrated `/ops` clearing/teardown remain NOT_VERIFIED.
- Local runner completed disposable database/process teardown; Ops sign-out was verified. Temporary reproduction scripts and a sanitized screenshot remain outside the repository. No sandbox business fixture, provider message, production mutation, push or deployment was performed by this audit. Documentation corrections are the only tracked edits.

**Next authorized package:** correct proven R4 source/robots/protection failures, followed by bounded trainer and support/budget failures under existing DF/M contracts. Return exact cumulative SHA and targeted regression evidence for independent acceptance. After code acceptance, execute authorized GitHub/developer-sandbox advancement and missing R4–R8 runtime evidence with safe sinks and cleanup. Preserve R0–R3 and separate source-rights/credentials/production/billing gates.
