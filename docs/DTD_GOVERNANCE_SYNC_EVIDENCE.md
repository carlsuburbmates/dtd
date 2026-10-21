# Governance Package Reconciliation Evidence

**Audit date:** 20 October 2026
**Preparation worktree:** separate isolated R0-based governance worktree
**Base:** frozen accepted R0 SHA `1ac4138e4d82991501139298cc624be732661119`
**Supplied archive:** `DTD_SKILL_GOVERNANCE_ROADMAP_ALIGNED_2026-10-20.zip`
**Archive SHA-256:** `0e58c177f64278aa5d92ad867fd923c29ed44b339a384d22b00d80d425fc0451`

## Integrity and comparison

- ZIP integrity and extracted-file hash comparison passed. The package includes `AGENTS.md`, `skill-policy.toml`, the proposed R0–R13 roadmap, governance report, and three repo-local skill definitions with metadata.
- Repository comparison was made against the frozen R0 tree, the dirty primary checkout and authenticated GitHub `main`/PR #12. Local and remote baseline copies of `AGENTS.md`, `.codex/skill-policy.toml` and `dtd-proactive-owner-assistance/SKILL.md` matched by blob. The proposed governance files have different blobs; the proposed roadmap is absent from both current GitHub `main` and PR #12.
- The package incorporates the R0/R1/R2 checkpoint, R-stage routing, distinct engineering/product/operational/business completion states, explicit capability routing, user-authority carry-forward, and independent review for new diffs. Its policy retains `suggest_then_auto_use`, no allowlist/blocked list, repo-first preference and explicit `$composio-...` gate.
- Existing authoritative controls remain higher priority: AGENTS/invariants/CDR/specs/contracts. The roadmap coordinates work and does not grant production, billing, credential, new-source, destructive-data or policy authority. Old completion plans and matching criteria remain intact.

## Prepared changes

- Reconciled the supplied `AGENTS.md`, skill policy, all three skill files and metadata into this isolated worktree, with no changes in the root checkout.
- Added `docs/DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md` and four audit artifacts: current reality, gap register, roadmap reconciliation, and this governance evidence. The fifth artifact, roadmap execution register, is tracked separately.
- Added DF-042–DF-048 to `docs/DTD_CURRENT_STATE.md` with evidence, impact, uncertainty, deferral and next action.
- Preserved the existing intentional deletion of `.agents/skills/clerk/SKILL.md` in this worktree. The primary checkout's deletion remains untouched; no Clerk skill was restored.
- No application code, remote branch, provider, scheduler, database, production service, credentials, billing or authentication configuration was changed by the governance package.

## Contradictions and decisions

1. **R0 and R1:** R0 remains accepted at exact SHA only. The preparation-time R1 snapshot found API revision `00049-brd` based on `d83c7f4` and reproduced the R0 suppression bypass. Superseding execution evidence records DF-043 accepted/deployed and DF-042 web identity remediation complete. R1 remains partial pending broader sandbox runtime acceptance; the separate scheduled-ingestion activation is blocked by DF-044/045.
2. **Current state freshness:** dated 7/16 October runtime revisions are historical. New current-reality audit records 20 October state without deleting past evidence.
3. **Scheduler containment:** `DISABLE_AUTONOMY=1` is not a direct ingestion-job guard. The ingestion scheduler was paused after a synthetic P1 reproduction; the engine tick remains enabled.
4. **Authentication/permissions:** the developer web identity has since been replaced under the explicit authorization and passed canary and promoted API-flow checks. Direct project roles and Secret Manager bindings were absent; inherited permissions remain `NOT_VERIFIED` because Policy Troubleshooter is disabled. Firebase Hosting inventory still lacks `firebasehosting.sites.list` and is not an R1 dependency.
5. **Clerk deletion:** intentional user change is retained as a deletion, not treated as ZIP drift.

## Review and promotion status

These governance files are prepared in a separate R0-based worktree and remain uncommitted, unpushed and unmerged. The independent actual-diff governance review returned **ACCEPT** after two review rounds and the final scheduler disclosure refresh. R0 remains unchanged; governance docs are not mixed with the suppression patch. Promotion to main remains part of R2 reconciliation and has not occurred.

### Independent governance review result

The reviewer compared the actual worktree diff with R0 and accepted the following: authority hierarchy and Codex-only promotion; policy routing and explicit Composio invocation gate; R0 exact-SHA scope; preserved Clerk deletion; unique, evidence-bounded DF-042–DF-048 findings; no expanded production/billing/credential/provider authority; corrected R1 partial status and separate ingestion reactivation gate; public-artifact privacy; and consistent historical/current scheduler status. No governance review blocker remains.


## Execution refresh — 20 October 2026

- The separate DF-043 code delta is independently accepted, committed and deployed; its commit is `50f3c594d611bede8b7a610d7b09fb3fd8680f23`. It is not mixed into this governance worktree. The current developer API runtime is revision `dtd-api-dev-00050-7r7`; evidence is recorded in `R1_SANDBOX_RELEASE_EVIDENCE.md`.
- DF-042 developer web identity change is complete under the user’s explicit authorization. `dtd-web-dev` uses `dtd-web-dev-runtime`; the exact canary and promoted API-backed browser checks are recorded in the current-reality audit. Direct project roles and secret bindings are absent; inherited organization-level effective permissions remain `NOT_VERIFIED` because Policy Troubleshooter is disabled.
- The ingestion Scheduler is currently `PAUSED` with the original target, body, OIDC audience, schedule and deadline. A separate DF-045 robots fail-open finding was confirmed in code and is a direct R4 activation dependency; DF-044 source URL/domain approvals also remain open. The enabled engine-tick does not call ingestion.
- This worktree’s Clerk deletion remains intentional. The five agreed baseline artifacts are present alongside separate R1 release and fixture-cleanup records. Governance review is ACCEPTED; commit/push/merge remain pending R2 reconciliation.

## Execution refresh — 21 October 2026

- Independently refreshed the deployed API and web image identities. The API build archive matches all 46 included backend source files at `50f3c594`; the web archive matches 122 tracked frontend source files. Exact revisions, digests and build IDs are recorded in `R1_SANDBOX_RELEASE_EVIDENCE.md`.
- Ran bounded, namespaced developer fixtures for claim, privacy denial, suppression/republication protection and delisting. Application records were removed and verified absent; only Resend test-sink delivery metadata remains.
- Confirmed the R1 contract permits trainer ingestion to stay PAUSED. DF-044/045 remain R4 activation dependencies; engine-tick remains enabled and separate.
- Reconciled DF-038 against current source and Secret Manager metadata: the tracked script literal in the accepted branch matches enabled developer admin secret version 2, contrary to the earlier current-state statement that this branch had retired it. The script was not run; no production or provider credential was changed. Further privileged acceptance and promotion remain gated on explicit owner-authorised developer credential rotation plus reviewed source retirement.
- The newly appended R1/DF-038 evidence changes are a fresh documentation delta and require independent review before governance commit. The intentional Clerk deletion remains preserved.
