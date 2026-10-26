# R8 Integrated Developer-Sandbox Product Acceptance Evidence

> **26 October reconciliation:** PR #20 integrated reviewed source `79b8165` as `4e54968`; the old isolated/remote-branch instructions in this dated packet are historical. The separately approved 25 October developer credential containment reused the previous image, so corrected R4–R8 runtime acceptance remains PARTIAL. Use `DTD_CURRENT_STATE.md` and `DTD_ROADMAP_EXECUTION_REGISTER.md` for current source/runtime, safe credentials and the remaining exact-SHA acceptance package; do not repeat merged implementation. CDR-028 and the revised commercial strategy integrate the two Antigravity sessions without granting new production or billing authority. The observations and test evidence below retain their original date and scope.

**Evidence date:** 24 October 2026 (Australia/Melbourne).

**Disposition: PARTIAL — integrated runtime acceptance remains open.**

The prior implementation-authored `ACCEPTED` statement is superseded. Source provenance is established for the earlier deployment, but independent review found additional workflow defects. Local corrections and passing tests do not establish their deployment or full R8 acceptance.

## Exact source and environment boundaries

- Accepted R0–R3 checkpoints remain closed at their recorded scope.
- Original candidate range: `a20687e60ffbad9384f78c88b42956dccde9cfe6..1022ad5c668713e6b44f5c4a505f898bc87bd223`.
- Separate-session handover `0701d09` and the independently reviewed corrections are integrated through PR #20: reviewed source `79b8165`, merge `4e54968`. The commercial reconciliation is governed by CDR-028. These are accepted source/history boundaries, not proof that the later source is deployed. Resolve the current exact source/image before the remaining runtime checks.
- Independently inspected developer snapshot on 23 October: API `dtd-api-dev-00060-x5r` at 100%, digest `sha256:d9852ad8d4139352c58761ebef10bc1e2309d92ecb2a4c975eb2d29c1f64c27c`; web `dtd-web-dev-00024-nlj` at 100%, digest `sha256:21eac44a12f887357700997a4bbde7ab1d46ac2ceca98363db38037cbfa3dba8`, bundle `index-DTQYOF7F.js`.
- All 46 tracked API and 122 tracked frontend source files in those build archives matched `1022ad5` byte-for-byte. This proves that deployed source, not later local corrections.
- Project `dogtrainersdirectory-dev`, Atlas database `dtd_sandbox`; checkout, startup seeds and self-healing were disabled, trainer-ingest Scheduler PAUSED. Refresh before mutation.
- No push, deployment, runtime business fixture, customer email or provider mutation was performed by this correction checkpoint. The separate handover reports an owner-authorized production frontend crawlability release; that is not authority for R9 API/product promotion and was not independently reverified here.

## Independently reviewed local corrections

| Requirement | Correction and evidence | Remaining boundary |
|---|---|---|
| DF-044 source authority | Exact accepted initial-20/evidence URLs; unsupported association approval disabled; no wildcard, implicit subdomain or unlisted path admission; discovery redirects held. Independent localhost reproduction confirms no redirect fetch. | Keep ingestion paused; no new source rights granted. |
| DF-045 robots policy | HTML, unusable plaintext, retrieval errors and redirects fail closed; valid empty/comment/sitemap policy preserved; target-fetch negatives pass. | Current corrected runtime not verified. |
| DF-051 durable protection | Earlier durable ownership/submission/billing protection correction retained; expanded acquisition/claim suites pass. | Complete scoped runtime lifecycle evidence. |
| DF-030 trainer renewal | Current-owner/latest-challenge binding, atomic consume/replay guard and delayed-delivery status protection. UI invalidates expired auth, retains drafts/paid tier and rejects stale responses across trainer navigation. | Deployed browser recovery proof required. |
| DF-047 support | Selection/version-correlated requests, truthful dispatch feedback, failed-draft retention, pagination, protected listing link and delisting/privacy category actions with existing identity guards. | Deployed UI/API/data/audit/provider proof required. |
| DF-052 AI attempt ceiling | Atomic Mongo UTC-day ledger across processes, conservative legacy count, failure slots retained, fail closed without storage and bounded output tokens. Real ephemeral Mongo: 40 concurrent requests across two independently loaded modules/clients, legacy use 2, limit 5 → exactly 3 provider mocks. | Drain old-code work at cutover; verify runtime configuration/recovery. This bounds attempts, not monetary spend. |
| Acceptance cleanup | ContextVar correlates matching diagnostics with opaque request ID; runners delete only returned owned IDs. Independent concurrent/nested/exception/reset and cleanup tests pass. | A lost HTTP response may leave an unknown request artifact; preserve it and mark unverified rather than delete unrelated activity. |

Independent specialist review accepted backend source/OTP/support and root correlation/cleanup deltas. The frontend review identified a route-response race; root independently reviewed the final route-generation guards and six deferred-response regressions, then repeated the full 100-test frontend suite. Root also independently reviewed the datastore budget implementation and repeated its focused tests. No implementation author certifies their own delta.

## Verification at this local checkpoint

- Maintained isolated backend suite: **710 passed**, disposable loopback API/Mongo; database cleanup completed by runner.
- Full frontend suite after preserving `0701d09`: **100 passed** across 11 files.
- Focused cleanup/context and AI-budget tests: **36 passed**; includes real local Mongo cross-worker evidence and mocked providers, no charge.
- Combined candidate Vite build, copy guard, prelaunch release gate and sandbox deployment contract passed. Build retains the static fallback (6.16 kB HTML). Remote CI remains unverified before promotion.
- Existing deprecation warnings and the frontend bundle-size warning are not represented as clean security or performance acceptance.

## Remaining R8 acceptance and next package

R4–R7 corrections have accepted source evidence; R8 remains PARTIAL. Use the execution register for current integration, then advance only the accepted exact SHA under the existing sandbox gate. Verify owner questionnaire → results/profile → protected enquiry → sink/provider persistence → trainer recovery/edit → support outcome, desktop/mobile/keyboard and applicable assistive-technology evidence, provider-originated receipt/recovery and controlled Monitoring alert receipt. Public positive onboarding remains DF-041; a synthetic invalid-ABN held intake does not prove statutory verification or publication.

Use only owned disposable fixtures and exact-ID teardown. Never invoke the global routine engine tick as a test. Preserve static fallback/sitemap and named security/provider uncertainties (including DF-001). Google credits remain pending written confirmation; commercial/funding/margin/workload targets are not measured outcomes or extra release blockers. Existing pricing starts an eligible Pro trial on Stripe subscription creation, not merely profile claim.

R9 requires owner audit and specific production authority. R11 live billing, credential actions, new source rights and real-data destruction retain their separate gates.


## Preserved R1/R2 checkpoint and cleanup scope

R1 is **DONE WITH NAMED BLOCKED FOLLOW-UPS**; R2 is **DONE**. Retiring their dated evidence files does not reopen these checkpoints or erase their limitations. Full original packets and cleanup records remain in Git at the pre-cleanup commit and the hash-verified external archive:

- [R1 evidence](https://github.com/carlsuburbmates/dtd/blob/1a0b0ff0cdffaeb753dc6ae53e0ef09ae653f188/docs/R1_SANDBOX_RELEASE_EVIDENCE.md): 21 October API `dtd-api-dev-00054-rvl`, reviewed source `fdd2c45431dfeccf405a14ebdb46b45d545fa6ca`, image `sha256:23f75593957e64c305dc6ac7364a0e53192a120c6ff018192595a0d1f2c27df3`; developer web `dtd-web-dev-webidentity`. DF-042/043 and R0 acceptance remain preserved. Inherited effective web-identity permissions were not fully verified.
- [R1 cleanup](https://github.com/carlsuburbmates/dtd/blob/1a0b0ff0cdffaeb753dc6ae53e0ef09ae653f188/docs/R1_FIXTURE_CLEANUP.md): temporary Scheduler job, owned trainer/submission/suppression/claim/support/privacy/fraud/webhook rows and synthetic auth-limiter state were removed and queried absent; public fixture lookups returned 404 where applicable. Original ingestion stayed paused. Provider-side test-sink message metadata remained at Resend; application cleanup does not claim provider deletion.
- [R2 reconciliation](https://github.com/carlsuburbmates/dtd/blob/1a0b0ff0cdffaeb753dc6ae53e0ef09ae653f188/docs/R2_RELEASE_RECONCILIATION.md): accepted merge `f24cc49723840028bbe4ea35f6787eed03c440ba`, API `dtd-api-dev-00055-kbm`, web `dtd-web-dev-00023-phd`; exact-head CI and source/runtime verification passed at that checkpoint. No new fixture, provider message, payment or Scheduler execution was created by R2. The then-unverified separate developer Firebase Hosting requirement was subsequently SUPERSEDED by owner decision CDR-027; Cloud Run is the developer sandbox, so no such provisioning gap remains.

These dated revisions and secret bindings are historical evidence, **not recovery targets**. Current safe recovery requirements live in the [Ops specification](specs/OPS_AND_OBSERVABILITY.md); credential containment must not be undone by selecting an older image/revision.

### Named SR/CF follow-ups retained for R8

The table preserves the 21 October accepted subcases and the still-unverified scenarios carried through R5/R7 into integrated R8 acceptance. It does not assert later runtime completion. Refresh only the affected scenario after an accepted delta; do not rerun all accepted R0–R3 evidence merely because documentation moved.

| Scenario | Preserved developer evidence (21 October scope) | Remaining scoped runtime proof |
| --- | --- | --- |
| SR-01 — provider webhook reconciliation | Signed synthetic delivery, replay/single persisted receipt, signature denial and exact-ID cleanup passed. Persisted-receipt/notification-write-failure retry, stale terminal-event ordering and ambiguous legacy-receipt rejection passed locally. | Provider-originated delivery and downstream retry; safely bounded live database-write failure after receipt persistence followed by successful reconciliation. Synthetic signed events do not prove provider delivery; unavailable safe failure injection remains NOT_VERIFIED. DF-050/R7. |
| SR-02 / CF-02 — submission/publication authority | Held-submission suppression denial, suppression/republish denial, delisting/public 404, notification and audit passed. | Positive publication with statutory/ABN evidence, required consents and provenance; deduplication and concurrent publication races. An invalid-ABN held intake is not positive publication proof. R5/DF-041. |
| SR-03 / CF-03 — claim proof/lifecycle | Ordinary browser claim persisted verified claim/tier/audit with test-sink delivery. Mismatch, invalid OTP, expiry, lock, disputed profile, missing claim email, unavailable SMS and verified-event replay negatives passed. | Conflicting verified-owner adjudication and corrected expiry/renewal/current-owner lifecycle, including acquisition-update protection after an expired challenge; preserve DF-030/051 runtime gaps. R5, plus R4 before ingestion activation. |
| SR-04 / CF-04 — support intake/reply/closure | Intake persisted one thread/audit/test-sink notification; five concurrent duplicate replies produced one dispatch/message/notification/audit; specialised closure and fraud confirm-spam negative path passed with cleanup. | Safe notifier failure/fallback, truthful failed/duplicate feedback, selected-thread correlation and guarded closure/category outcomes across UI/API/data/audit. DF-047/R7. |
| SR-05 / CF-01 — privacy proof and scrub | Unverified-subject scrub returned 403 with unchanged record and no case audit mutation. | Positive scrub using trusted synthetic subject proof, proof provenance and error-provenance matrix, terminal resolution and evidence of the intended scoped data changes. Never manufacture trusted proof or scrub real subjects for acceptance. R5. |
| SR-06 / CF-05 — durable obligations | Local tests cover large scans, waiting states and read-only zero-write invariants; no live bounded positive sync path was established. | Fixture-scoped completeness scan, waiting/read-only invariants, bounded retry and positive terminal resolution with persistence and Ops evidence. Never substitute a global engine tick. R7. |

No permission to enable checkout/refunds/self-healing, resume ingestion, contact real trainers, replace credentials or promote production is created by this matrix. A missing safe fixture or provider check blocks only its named claim.
