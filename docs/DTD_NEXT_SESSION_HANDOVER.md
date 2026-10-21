# DTD next-session handover

**Prepared:** 22 October 2026. The owner requested completion of the current R3 work and a handover for later roadmap completion. R0–R3 developer checkpoints are complete; R4 has not started in this session.

## Objective and authority

Complete R0–R8 sequentially, verify the developer sandbox as a complete product, then hand that sandbox to the owner for their audit. R9 production requires that owner audit and specific subsequent authority. R10–R12 need genuine post-release observations; R13 is optional. Do not claim future business validation from sandbox results. CDR-026 and CDR-027 govern these boundaries.

Standing authority covers investigation, ordinary implementation/tests/docs/commits and independently accepted GitHub/developer-sandbox advancement. Preserve the exact-commit independent audit gate. Production changes, live charges/refunds, source-rights changes, credential mutations and destructive real-data actions retain their separate owner gates. The single authorized Firebase CLI logout in this session grants no blanket credential authority.

## Where to resume

- Repository: `carlsuburbmates/dtd`.
- Active worktree: `/Users/carlg/.codex/worktrees/r3-health-parity-fix/dtd`.
- Resume worktree branch: `codex/r3-handover`; preserve the prior patch branch `codex/r3-target-reconciliation`.
- The primary checkout `/Users/carlg/Documents/AI-Coding/dtd` intentionally remains on frozen R0 `1ac4138` with the Clerk skill deletion. Do not reset it, switch its branch, or overwrite its unrelated work. The reviewed main tree also preserves the Clerk deletion.
- Keep other worktrees/remote PR history until individually classified; do not force-push or clean unknown files.
- Before editing: inspect actual worktree status, fetch remote state, check exact main ancestry/CI and current Cloud Run revisions. Reuse the already accepted evidence where the code/configuration is unchanged.
- Read `AGENTS.md`, `.codex/skill-policy.toml`, `docs/README.md`, [execution register](DTD_ROADMAP_EXECUTION_REGISTER.md), [gap register](DTD_CODEX_GAP_REGISTER.md), [R3 evidence](R3_RELEASE_FOUNDATION.md), applicable invariants/decisions/specs. The original owner mandate is `/Users/carlg/Documents/AI-Coding/dtd - external files/DTD_CODEX_MASTER_MANDATE_2026-10-20.md`; later explicit owner directions and CDR-026/027 reconcile its historical starting state. Do not read `archive/` as active policy.

## Exact checkpoint

- PR #17 merged as `ca7444348c413b750e1b58b64167192934f8fbf4`. Main Verify `39640422472`, Push on main `39640422236` and dependency graph `39640436353` passed.
- DF-046 is DONE: exact API source `9dd53ed62d5dd87abd70430e12e79d9d39d3133a`, independently accepted, five live synthetic API/Ops scenarios passed; 14 fixture records deleted and direct absence verified.
- Original Dependabot alerts #253–#256 and #258 are fixed. The resulting rescan exposed #259/#260 for transitive follow-redirects 1.16.0. Independently accepted correction `d0f409664e453d0f9cb7339f0a66073a356745a0` changes only three lockfile values to 1.16.1, plus reconciled documentation. PR #18 merged as `48f68f4bb49ac1e8641e515b7a6a0f6713a024da`; main Verify `39642567639` and Push `39642567225` passed. The supported GitHub browser refresh completed: graph run `39643359491` passed, SBOM resolves follow-redirects 1.16.1, #259/#260 are fixed, and zero Dependabot alerts remain open. R3 is DONE for its developer platform checkpoint; no refresh/reimplementation is pending.
- Patch verification: official registry/tarball integrity, frozen install, 74 frontend tests and build passed. All 18 generated files had identical paths and SHA256 hashes before/after (sorted manifest SHA256 `f3af48657ae8f3f9eb6cef8761158862f023c51761993e840d50f269024f46ef`). The package is in Axios's excluded Node HTTP adapter; the final frontend image serves static files from nginx. No runtime replacement is needed for this lock correction, and no deployed-image scan is claimed.
- DF-053 is SUPERSEDED: owner explicitly confirmed Cloud Run is the sandbox and Firebase Hosting is production-only. There is no missing developer Firebase Hosting site to provision or permission grant to request.
- Vercel's DTD Git connection was removed and verified before main integration. It has no DTD custom domain, is non-live, and historical deployments remain protected records. It is not a delivery/acceptance path. DF-007's remaining `.com` ownership ambiguity is conditional R9 research only if a proposed production domain change makes it relevant.
- The owner specifically approved account-scoped Firebase CLI logout after diagnostic output disclosed local OAuth fields. The official logout succeeded, a fresh login list had zero accounts, and a separate gcloud project read still worked. No credential values belong in logs, documentation or handoff. No runtime secret was changed.

## Verified developer environment

| Surface | Identity / state |
|---|---|
| Project / region | `dogtrainersdirectory-dev` / `australia-southeast1` |
| Web / owner-audit URL | `dtd-web-dev-00023-phd`, 100%; https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/ |
| Ops | https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/ops |
| API | `dtd-api-dev-r3-9dd53ed6`, 100%; https://dtd-api-dev-x2kdoaemtq-ts.a.run.app/ |
| API image | `sha256:10398ce474bd4835377454619714f4fc6d0b2e25d895567564f5764f406c6d36` |
| API health | https://dtd-api-dev-x2kdoaemtq-ts.a.run.app/api/health |
| Database | Isolated Atlas `dtd-sandbox` / database `dtd_sandbox` |
| Ingestion Scheduler | `dtd-trainer-ingest-cron` PAUSED, daily 02:00 Melbourne |
| Routine engine tick | `dtd-engine-tick-cron` ENABLED every 10 minutes, `profile=routine`; do not invoke it as a synthetic acceptance test |
| Recovery | `00055-kbm` traffic return rehearsed and candidate restored; conditional emergency fallback only, since it predates the R3 classifier/dependency changes. Use the full R3 runbook and inspect preconditions first. |

Firebase production frontend is `dogtrainersdirectory.com.au`, site/project `gen-lang-client-0028123502`, with `/api/**` routed to production Cloud Run `dtd-api`. Repository Firebase defaults intentionally address production. Do not use them for sandbox delivery. No production release occurred during this session.

Existing gcloud and GitHub access worked. Firebase CLI intentionally has no logged-in account after containment; normal sandbox work uses gcloud and needs no Firebase login. Do not print tokens or JSON credential inventories. Test provider-management access at the relevant stage without assuming a browser/CLI session is available or that runtime secrets grant management authority.

## Security findings retained for the next session

DF-001 includes open GitHub secret alerts #1 (Google key) and #2 (Atlas credential URI), each marked publicly leaked with validity unknown. Their equivalence to previously revoked credentials is NOT_VERIFIED. At R4 preflight, prioritize a secret-safe identity comparison and provider revocation-state verification before asserting containment; obtain separate credential authority if an active replacement/revocation is required. Do not retrieve or print raw alert secret fields. Completed Firebase CLI logout and the Ops passcode replacement do not close these separate alerts.

TD-002 records ten existing CodeQL observations for stage-specific triage, not confirmed defects: acquisition/POC URL/HTML checks at R4; sensitive demo/script logging under DF-001; notification hashing and disclosure checks at R7. The missing-workflow-permissions alert is explicit hardening: the actual repository token default is read-only and cannot approve PRs. Do not claim a globally clean security scan from dependency closure or reopen completed R0–R2 from scanner counts alone.

## Next authorized work, in order

| Stage | Current disposition and remaining work |
|---|---|
| R0–R2 | Preserve accepted DONE checkpoints, R1's named follow-ups, governance integration and R0 SHA. Historical pending wording must not reopen these stages; consult their release evidence and current main. |
| R3 | DONE: accepted integration, main CI/graph and alert closure are verified. Reuse this checkpoint; do not reimplement or repeatedly test the same patch. |
| R4 | First next stage on owner resumption. DF-044 must bind configured source and candidate URLs/domains to explicit source approvals; DF-045 must fail closed/defer on unavailable/error/malformed robots policy. Exercise synthetic allow/deny/no-target-fetch-on-policy-error and idempotent reruns. Preserve DF-043 suppression. Include the DF-051 acquisition-dedup regression for expired unclaimed profiles. Complete DF-026/M1 field provenance, confirmation/freshness/invalidation and match-ready projection; verify Atlas/ABR recovery relevant to that workflow. No unauthorized source requests or scheduler activation. |
| R5 | DF-030 claim-session restoration; DF-041 remaining public submission/consent evidence; DF-051 claim lifecycle; owner/trainer journeys, protected enquiry, mobile/keyboard/accessibility, truthful trust/contact/SEO copy. Preserve accepted visual work. |
| R6 | Complete remaining Decision Contract v2 / M1–M6/M8 evidence, current eligible capability projection, paid-neutral fit and exact 0.05 presentation rule, thin-supply/AI fallback and urgent-support truth. M0 stays DONE and M7 optional. |
| R7 | DF-047 usable Ops support queue/reply/close path; DF-048 truthful receipt/delivery status; DF-050 provider-originated webhook/notification recovery; DF-052 atomic fail-closed AI budget/concurrency and quota visibility; controlled Monitoring alert receipt and Resend/Sentry recovery. Preserve Ops Phases 1–5A. |
| R8 | Full supply-to-owner-to-notification-to-Ops loop, negative/degraded cases, current exact deployments, mobile/desktop evidence, independent acceptance and verified fixture cleanup. Produce `R8_END_TO_END_SANDBOX_ACCEPTANCE.md` and the owner-audit packet. |
| R9–R12 | Post-owner-audit release/real-use/commerce/observed sustainability stages, with separate production/billing/pilot authority. Do not simulate completion. |
| R13 / To Do | Expansion optional. TD-001 tracks Motor-to-PyMongo Async maintenance before 14 May 2027. Keep any new gap assigned; use the existing To Do section for work outside R stages. |

The stage table is navigation; current gap/decision/spec records remain authoritative. For R4, inspect current `ingestion_manager.py`, `source_approvals`, `automation`/scheduler path, canonical deduplication, actual publisher and source evidence. Existing historical acquisition handoff describes scope but its old statements about still-open matching policy do not override current Decision Contract v2 or CDR-018–027.

## Evidence and cleanup boundaries

No trainer/customer fixture, message, scheduler invocation or database mutation was created by the final dependency/hosting reconciliation. Reuse earlier R1/R3 fixture-cleanup evidence while it remains applicable. Build output is ignored; the temporary static-file manifest is comparison evidence, not a repository/runtime dependency. Do not clean shared worktrees, unrelated browser tabs or unknown files.

Resume without another general alignment approval when the owner asks. Use one scoped implementation package, its relevant tests, independent exact-delta review, then authorized GitHub/sandbox advancement and outcome verification. Stop only for a specific authentication, source-rights, independent-review or separately gated consequential action. Do not proceed to the next R while the active R has unresolved exit requirements.
