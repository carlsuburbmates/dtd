# DTD Full Project Completion Plan

**Status:** active execution plan — refreshed 22 October 2026. This is the single cross-project completion sequence. It supersedes treating matching, acquisition, website, automation and `/ops` as isolated finish lines; their detailed contracts remain authoritative.

## Current verified baseline — 22 October 2026

- R0 remains accepted only at exact SHA `1ac4138e4d82991501139298cc624be732661119`. PR #12 consolidation merged at `704c830`; explicit developer deploy gates merged at `f24cc49`. Current R2 release details and recovery evidence are in [R2_RELEASE_RECONCILIATION.md](R2_RELEASE_RECONCILIATION.md).
- Developer web revision uses `dtd-web-dev-runtime`; canary and promoted API-backed catalogue flow passed. DF-042 is DONE within the verified direct-permission and flow scope; inherited organization permissions remain NOT_VERIFIED.
- Developer trainer-ingest Scheduler is PAUSED with its original schedule, OIDC, deadline, URL and `{}` body. DF-045 robots fail-open and DF-044 URL/domain source approval remain open R4 controls. The enabled engine-tick path does not invoke ingestion. Keep the ingestion job paused until those controls and source execution scope are independently resolved.
- R2 now aligns `main` to the isolated developer runtime: API `dtd-api-dev-00055-kbm` at 100% (`sha256:d0846a21e73642376c3e5f145f0791fb1456b185624bd8c12ab773f64fc3b764`), web `dtd-web-dev-00023-phd` at 100% (`sha256:5eba05c8ed409087498edcb18533e6b34b2b782cffd4f98827a705acaf7505d5`), source `f24cc49723840028bbe4ea35f6787eed03c440ba`. Checkout and self-healing are explicitly disabled; API uses `dtd_sandbox`. Full CI, scenario pointers and recovery: `R2_RELEASE_RECONCILIATION.md`.
- R1 runtime acceptance was DONE WITH NAMED BLOCKED FOLLOW-UPS on API revision `dtd-api-dev-00054-rvl` before R2 deployment. Its synthetic webhook, claim success/negative cases, privacy denial, suppression, delisting, fraud, support intake/concurrency/closure and protected Ops have scenario outcomes and cleanup evidence. DF-051 and positive trainer/privacy/publication journeys remain R5; acquisition-dedup regression is required in R4 before activation; notifier fallback and scoped obligation completeness remain R7; provider-originated webhook verification and webhook-enabled recovery remain R3. Conditional rollback to `00059-hex` was rehearsed and the service restored to `00054-rvl`; ingestion remains PAUSED under the separate R4 gate.
- DF-038 source retirement and developer passcode rotation are remotely integrated in the accepted R2 stack. R1 permits ingestion to remain PAUSED; DF-044/045 remain separate R4 activation dependencies.
- The targeted R1 release evidence and cleanup record are [R1_SANDBOX_RELEASE_EVIDENCE.md](R1_SANDBOX_RELEASE_EVIDENCE.md) and [R1_FIXTURE_CLEANUP.md](R1_FIXTURE_CLEANUP.md).
- Roadmap execution is sequential: R0–R2 are complete and R3 is finishing its final dependency follow-up. DF-046, PR #17 integration/main CI and Cloud Run sandbox identity are accepted. Current evidence is in [R3_RELEASE_FOUNDATION.md](R3_RELEASE_FOUNDATION.md) and [DTD_ROADMAP_EXECUTION_REGISTER.md](DTD_ROADMAP_EXECUTION_REGISTER.md). The owner requested a handover after current work; do not start R4 in this session.
- Per owner direction, R0–R8 end in delivery of the independently verified developer sandbox and evidence packet for owner audit. R9 production work is separate and requires that audit plus specific authority; R10–R12 need post-release evidence. See [CDR-026](DTD_CONFLICT_AND_DECISION_REGISTER.md).

## Evidence carried forward from 7 October


- Developer sandbox: Cloud Run API `dtd-api-dev-00021-dfd` and isolated frontend `dtd-web-dev-00006-qqx`, both at 100% traffic; the API `/api/health` reports an available database. Both live frontend hostnames were browser-checked against the sandbox API after the canonical-host routing repair in `6957c69`.
- The sandbox ingestion scheduler `dtd-trainer-ingest-cron` is enabled at 02:00 Australia/Melbourne. Its OIDC subject, canonical regional audience and JSON content type now match the service contract. A real Cloud Scheduler dry-run returned HTTP 200, wrote a zero-mutation run record, and that record was deleted; a real acquisition run remains intentionally unaccepted.
- Sandbox runtime now uses `dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`, with only Vertex AI User and Secret Manager accessor roles required by the current runtime. The prior default Compute identity is no longer attached to Cloud Run runtime traffic (DF-013 resolved for sandbox).
- Matching local release gate passes with 532 isolated backend tests. The runner starts an isolated loopback MongoDB instance when one is not supplied, creates a UUID-named database, and removes both in `finally`. A focused follow-up test now makes its no-provider precondition explicit rather than inheriting a developer's sandbox email secret.
- The disposable M9 API/Ops runner has passed live validation, emergency/urgent triage, no-confirmed-match, expanded scope, live non-degraded Gemini, redacted/opaque context, forced context expiry, public profile, terminal follow-up/idempotency, protected Ops evidence, and public-fixture removal. It created only UUID-prefixed fixtures, used no recipient email, and removed every created record. Matching events and contexts now write BSON expiry dates; sandbox TTL indexes exist and the sandbox-only legacy conversion found no strings to convert.
- `run_sandbox_matching_parity.sh` now proves the live AI/fallback boundary with one immutable, UUID-namespaced fixture: normal Gemini, a temporary developer-sandbox invalid-model fallback and restored Gemini all produced the same candidate and capability reason. The fallback was visible in protected Ops, `gemini-3.5-flash` was restored, and every record created by the run was removed.
- The isolated frontend has passed its 51-test/build gate at the deployed commit and a browser submission of the live questionnaire to a disposable matching result and profile handoff. Both sandbox hostnames now present the guided owner path and reach only the sandbox API. The fixture and all associated match records were removed and verified absent. The final protected-enquiry submission remains unexercised.

## Completion rule

The pre-production delivery is complete only when R0–R8 and their applicable open findings are independently evidenced in the developer sandbox, the required fixtures and provider effects are clean, and the complete evidence packet is handed to the owner for audit. Passing code tests, a Cloud Run health response, a scheduler job, or a rendered screen alone is insufficient. R9 production, R10 marketplace value, R11 commercial validation and R12 sustainable operation remain later roadmap outcomes; they require owner audit/authority and, where relevant, post-release observation. Do not mark them done to make the sandbox handoff appear complete.

## Execution order

| Phase | Scope and work | Exit evidence |
| --- | --- | --- |
| 0 | Establish one current-state register; reconcile stale matching records, current sandbox revision, scheduler/IAM and code branch. | This document, current-state entries and a clean exact commit map agree. |
| 1 | Release safety: dedicated sandbox runtime identity, least privilege, provider recovery registry, Cloud Build/Actions modernisation, dependency remediation plan, repeatable safe deploy with no hidden scheduler/IAM mutation. | Sandbox deploy/recovery drill, remote CI, dependency evidence, no use of default runtime identity. **Runtime identity and deployment/scheduler split are complete; CI, dependency and recovery work remains.** |
| 2 | Trainer supply and acquisition: match-ready declaration/onboarding, claim/correction/suppression lifecycle, lawful source evidence, scheduler observability, capacity freshness and query/index proof. | Disposable ingestion run and rerun; trainer declaration→projection→correction→exclusion journey; `/ops` evidence. |
| 3 | Owner website: one mobile-first owner entry route, accessible structured questionnaire, config failure state, truthful public copy, navigation/header/metadata/SEO repair, profile and enquiry handoff. | Desktop/mobile browser paths, keyboard/accessibility checks, failure states, rendered metadata and no private URL content. |
| 4 | Matching and safety: deterministic eligibility, paid-neutral AI/fallback parity, exact 0.05 presentation, thin-supply disclosure, urgent routes/provider freshness, notification retry and anti-gaming. | All M0–M6/M8 fixtures plus sandbox responses/records and truthful `/ops` states. |
| 5 | Operations and automation: protected `/ops` controls, audit records, delivery retry, scheduler execution/disable/recovery, SEO/tier/revenue evidence and exception-led operator workflows. | Four recovery drills, sanitised read models, data retention/cleanup proof, no unattended failing loop. |
| 6 | Sandbox acceptance: create uniquely prefixed disposable records only; trace owner→match→profile→enquiry→notification/failure→`/ops`; delete every fixture and verify zero remaining records/UI exposure. | M9 matrix completed, before/after counts, cleanup audit evidence, mobile/desktop captures and independent audit. |
| 7 | Production gate: only after the owner separately authorises it. Use zero-traffic revision, safe smoke tests, recovery/rotation evidence and no-charge commercial checks. | M10 canary, live-safe acceptance and explicit owner production authority. |

## Non-negotiable controls

1. Test data is namespaced, has an expiry/cleanup owner, is removed from every affected collection, and is checked absent from public UI and `/ops` before a sandbox run closes.
2. Matching remains eligibility → paid-neutral fit → deterministic presentation. Commercial state cannot influence eligibility or fit.
3. AI receives only permitted structured facts and sanitised owner input. It cannot invent capability, override safety or provide clinical/veterinary advice.
4. Scheduler, provider, IAM, billing and deployment actions are independently observable in `/ops` or their control plane; no deployment helper may silently mutate another workstream.
5. Public copy names its actual evidence basis; generic verified/vetted/reviewed/availability/safety claims are prohibited unless the exact displayed fact supports them.
6. Production, live charges, irreversible credential revocation, legal-policy changes and destructive real-data actions remain explicit owner gates.

## Immediate active sequence

1. Finish R3 follow-redirects integration/rescan, then record the accepted checkpoint and hand over. DF-046 and the original five dependency alerts are resolved; retain the two newly discovered alerts until rescan proves closure.
2. CDR-027 confirms Cloud Run `dtd-api-dev` + `dtd-web-dev` with Atlas `dtd_sandbox` as the final developer sandbox. Firebase Hosting is production-only. Preserve provider work at R4/R7/R9, and keep ingestion PAUSED.
3. After an explicit R3 exit checkpoint, start R4; then proceed R5, R6, R7 and R8 in order. Do not skip unfinished work: assign newly found items to an existing stage or the To Do register and carry them forward.
4. At R8, deliver the full verified sandbox and evidence packet to the owner for audit. Do not start R9 or deploy production before that audit and separate owner authority.

## Cross-project finding ledger

This is a working completion ledger, not a claim that every repository statement has been freshly audited. `DONE` has direct 6 October evidence; `PARTIAL` means code or a bounded sandbox segment works but the full workflow is not accepted; `OPEN` needs implementation or acceptance evidence.

| Finding(s) | Phase | State | Completion evidence still required |
| --- | --- | --- | --- |
| DF-001 | 1, 7 | OPEN | Provider credential/recovery controls remain assigned to R4/R7/R9; preserve their separate authority gates. |
| DF-007 | 1, 7 | PARTIAL | Canonical production routing and Vercel disconnection are accepted at R3; `.com` ownership remains conditional research at R9 only if a production domain change makes it relevant. |
| DF-003, DF-011, DF-020 | 3 | PARTIAL | The isolated `dtd-web-dev` frontend deploys the guided path, has browser-submitted result/profile evidence, and its bundle calls only the sandbox API. Only the confirmation-gated browser protected-enquiry submission remains. |
| DF-004, DF-008 | 2, 5 | OPEN | Controlled SEO publication and attribution evidence; preserve the fail-closed legacy corpus until evidence supports a disposition. |
| DF-005 | 5, 7 | OPEN | No-charge payment-provider acceptance only after the owner authorises commercial testing. |
| DF-006 | 1, 6 | PARTIAL | The self-contained local isolated suite and live API/Ops M9 matrix pass; expand to browser-submitted journey, automation/recovery and remote-CI acceptance. |
| DF-009 | 1 | DONE | Toolchain migrated from CRA/craco to Vite 8 and Vitest 5; 0 dependencies vulnerabilities across 190 audited packages; all 52 tests and production build pass. |
| DF-010 | 1 | PARTIAL | Remote Verify run `37551814408` passed for exact deployed commit `6957c69` (532 backend and 51 frontend tests, build, sandbox deploy contract). Newer shared-branch commits require their own independent audit and remote run before advancement. |
| DF-012 | 1 | DONE | Retain the scoped build-identity evidence; recheck only when source deployment identity changes. |
| DF-013 | 1 | DONE | Dedicated sandbox runtime identity deployed and live-health checked; keep default Compute identity out of runtime traffic. |
| DF-014 | 2 | PARTIAL | Read-only production corpus audit before any production promotion. |
| DF-015 through DF-019, DF-021, DF-022, DF-026 | 4, 6 | PARTIAL | Disposable M9 now passes API/Ops triage, expansion, live Gemini, expiry, protected follow-up and cleanup; controlled same-fixture Gemini/fallback parity and browser result/profile evidence now pass. Supply completeness, provider freshness and final confirmation-gated browser enquiry work remain. |
| DF-027 | 1, 4 | DONE | The v2-aware isolated release suite now passes all 532 tests and starts its own disposable loopback MongoDB instance. Keep the suite in the deploy preflight. |
| DF-028 | 4, 5, 6 | PARTIAL | Sandbox writes BSON expiry dates, has TTL indexes, completed a no-op legacy conversion and passed forced-expiry M9 evidence. Any production conversion remains a separate owner gate. |
| DF-024, DF-025 | 4 | OPEN | Verified urgent-provider data freshness/correction lifecycle, safety UI, and decision on the constrained Maps/Places emergency-discovery exception before implementation. |
| DF-017 | 5, 6 | PARTIAL | Provider-safe notification failure/retry test that cannot send to a real trainer, with Ops and idempotency evidence. |
