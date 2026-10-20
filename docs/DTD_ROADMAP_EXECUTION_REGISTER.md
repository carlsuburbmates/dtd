# DTD Roadmap Execution Register

**Updated:** 21 October 2026
**Purpose:** navigation between approved R stages and existing source-of-truth documents; this is not a duplicate finding ledger or product contract.

| Stage | State | Current gate / accepted evidence | Next authorized action | Review checkpoint |
|---|---|---|---|---|
| R0 | DONE | Exact accepted SHA `1ac4138e4d82991501139298cc624be732661119`; CI run 39240506209 | Preserve frozen baseline | No blanket re-audit |
| R1 | PARTIAL (privileged Ops and webhook acceptance gated; ingestion activation remains R4) | DF-043 fix is independently accepted/deployed; DF-042 web identity remediation is live. Claim, privacy-denial, suppression/republication and delisting passed on current releases. Signed webhook/replay, claim exceptions, support, fraud, obligations and verified privacy remain `NOT_VERIFIED`; DF-038 blocks further privileged Ops actions pending owner-authorised rotation/source retirement. | Continue only bounded non-privileged scenarios. Defer authenticated Ops scenarios until DF-038 is resolved; keep trainer-ingest paused. R1 exit permits ingestion to remain explicitly disabled. | Scenario-level runtime evidence, exact source/image, scoped rollback readiness and fixture cleanup |
| R2 | NOT_VERIFIED / NOT READY | Remote `main` is `d83c7f4`; accepted branch `1ac4138` is six commits ahead and DF-043 `50f3c594` is seven commits ahead. PR #11 is merged and retained. PR #12 remains open and conflicting (`mergeable_state=dirty`) against its recorded base; current governance commit is still pending. | After R1 gates, reconcile PR #12 and current remote ancestry without force push; independently review and commit the governance package based on `50f3c594`. Do not merge conflicting PRs. | Exact-commit GitHub CI and docs/current-state consistency |
| R3 | PARTIAL | DF-042 developer web identity remediation DONE; DF-046 telemetry accuracy remains OPEN; API traffic rollback target exists but rollback-to-known-good is PARTIAL | Preserve web identity evidence; correct telemetry and improve rollback evidence within their scoped work | Runtime identity, health recovery semantics and recovery runbook |
| R4 | PARTIAL (scheduler activation BLOCKED) | DF-043 publisher suppression DONE; DF-044 URL/source approval and DF-045 robots fail-open remain OPEN; DF-026 partial | Resolve DF-045/DF-044 and verify source allowlist/execution profile before scheduler activation | Synthetic allow/deny, no-fetch-on-policy-error, provenance and `/ops` evidence |
| R5 | PARTIAL | DF-030 open, DF-021 partial, DF-041 partial | Complete protected owner/trainer journeys and truthful communication | Browser/API/persistence/provider fallback, desktop/mobile and cleanup |
| R6 | PARTIAL | M0 DONE; prior M9 parity; current matching status not freshly rerun | Resume existing matching criteria after safe runtime; urgent-provider freshness remains scoped | Exact contract outcomes, eligible capabilities, AI fallback, no false coverage |
| R7 | PARTIAL | Ops Phases 1–5A preserved; DF-029 dev engine-tick DONE; support/contact affected paths need scoped acceptance | Resolve exact existing finding IDs for support view and notification receipts; do not reopen completed phases | Failure/retry/idempotency/closure and zero unauthorized effects |
| R8 | OPEN | Full integrated lifecycle not accepted | Combine accepted R4–R7 workflows | Integrated sandbox evidence and complete fixture cleanup |
| R9 | OPEN / separately gated | Production release not authorized by this task | None until applicable explicit owner production gate | Production manifest/canary and protected action gates |
| R10 | OPEN | No real marketplace value baseline | Observe consented owner/trainer outcomes after safe launch | Measured baseline and owner-approved evaluation rules |
| R11 | OPEN / separately gated | Billing authority unchanged | Preserve test/no-charge gates; no live activation | Separate explicit billing approval and end-to-end payment evidence |
| R12 | OPEN | Sustainable cost, retention and founder workload not measured | Establish privacy-bounded operating baseline | Approved thresholds based on observed data |
| R13 | OPTIONAL | Expansion is not a launch requirement | Wait for evidence and owner decision | Rights, demand, cost/capacity and updated contracts |

## Operating notes

- Finding status and detailed evidence live in [DTD_CURRENT_STATE.md](DTD_CURRENT_STATE.md) and [DTD_CODEX_GAP_REGISTER.md](DTD_CODEX_GAP_REGISTER.md).
- Matching package status remains in [DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md](DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md) and its mandatory remaining criteria. M0 is not restarted.
- The accepted Ops history remains in current-state and existing phase artifacts. Only changed or failed workflows are rechecked.
- The DF-043 patch and governance package remain separate worktrees; the DF-043 code delta is deployed, while governance changes remain uncommitted and unpromoted. Governance changes are prepared on top of `50f3c594`, not only R0.
- Specific owner action is needed before further privileged Ops acceptance: authorise developer-only `dtd-admin-pass` replacement because tracked public source contains a literal matching its enabled version, then verify old-value rejection and replacement acceptance. The trainer-ingest job remains paused because DF-045/DF-044 are unresolved R4 activation dependencies. Firebase Hosting Viewer access is needed only for Firebase site inventory and is not an R1 dependency.
