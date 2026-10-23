# Historical handover and audit inventory — 24 October 2026

This directory preserves historical evidence moved out of the active `docs/` tree. It is not an instruction source. The cleanup follows invariant22 and the documentation maintenance rule: useful requirements remain in current specs, the M0–M10 roadmap/criteria, tests, decisions and current-state/R8 records. Accepted checkpoints are unchanged; unresolved findings are not closed by a file move.

## Scope and verification

- Source checkout: `codex/r8-audit-completion`, pre-cleanup SHA `389130ee2b480aabb3e3452438652ac5fa380782`.
- 12 tracked documents relocated; no file content permanently deleted. Eleven payloads are byte-identical; one rendered relative link is repaired. File/SHA manifest recorded locally during cleanup; Git records the complete before/after change.
- References in active documentation and two test-module provenance comments updated. No runtime, fixtures, provider state, dependencies or existing archives modified. Active `0701d09` Antigravity/Google handovers, static HTML fallback and sitemap preserved.
- Generated caches/builds, dependencies, worktrees, scripts and unmanifested artifacts remain preserved. The session-manifest dry run has zero eligible deletions. This is documentation consolidation, not a disk-space or whole-codebase cleanup certification.
- No test suite run for this documentation-only relocation. Structural link/reference, payload-integrity and Git whitespace checks verify the changed surface.

## Moved documents

| Document | Why historical / current authority | Payload |
|---|---|---|
| [ANTIGRAVITY_ACQUISITION_MATCH_READINESS_HANDOFF.md](ANTIGRAVITY_ACQUISITION_MATCH_READINESS_HANDOFF.md) | Original acquisition assignment; current acquisition spec, target state and DF-026 tests retain its requirements. | Byte-identical move |
| [ANTIGRAVITY_ACQUISITION_MATCH_READINESS_REWORK.md](ANTIGRAVITY_ACQUISITION_MATCH_READINESS_REWORK.md) | Earlier e60c830 rework brief; current source/claim findings and matching criteria retain unresolved work. | Byte-identical move |
| [ANTIGRAVITY_MATCHING_P0_AUDIT_AND_REWORK.md](ANTIGRAVITY_MATCHING_P0_AUDIT_AND_REWORK.md) | Accepted historical P0 checkpoint; M0 roadmap and versioned contract retain current authority. | Byte-identical move |
| [ANTIGRAVITY_MATCHING_P1_AUDIT_AND_REWORK.md](ANTIGRAVITY_MATCHING_P1_AUDIT_AND_REWORK.md) | Initial P1 partial verdict predates accepted 5161a2b baseline recorded in M0. | Byte-identical move |
| [ANTIGRAVITY_MATCHING_PIPELINE_IMPLEMENTATION_HANDOFF.md](ANTIGRAVITY_MATCHING_PIPELINE_IMPLEMENTATION_HANDOFF.md) | Original staged assignment; active roadmap/remaining criteria and AGENTS §6A retain its contracts. | Byte-identical move |
| [MATCHING_PIPELINE_1CDD88D_INDEPENDENT_AUDIT_2026-10-05.md](MATCHING_PIPELINE_1CDD88D_INDEPENDENT_AUDIT_2026-10-05.md) | Dated 4–5 October exact-SHA matching audit; references retained in active matching criteria/current-state history. | Byte-identical move |
| [MATCHING_PIPELINE_7DD99FA_INDEPENDENT_AUDIT_2026-10-05.md](MATCHING_PIPELINE_7DD99FA_INDEPENDENT_AUDIT_2026-10-05.md) | Dated 4–5 October exact-SHA matching audit; references retained in active matching criteria/current-state history. | Byte-identical move |
| [MATCHING_PIPELINE_8E03F6C_INDEPENDENT_AUDIT_2026-10-05.md](MATCHING_PIPELINE_8E03F6C_INDEPENDENT_AUDIT_2026-10-05.md) | Dated 4–5 October exact-SHA matching audit; references retained in active matching criteria/current-state history. | Byte-identical move |
| [MATCHING_PIPELINE_C7AFB07_INDEPENDENT_AUDIT_2026-10-05.md](MATCHING_PIPELINE_C7AFB07_INDEPENDENT_AUDIT_2026-10-05.md) | Dated 4–5 October exact-SHA matching audit; references retained in active matching criteria/current-state history. | Relative link to active criteria repaired |
| [MATCHING_PIPELINE_P2_P6_INDEPENDENT_AUDIT_2026-10-04.md](MATCHING_PIPELINE_P2_P6_INDEPENDENT_AUDIT_2026-10-04.md) | Dated 4–5 October exact-SHA matching audit; references retained in active matching criteria/current-state history. | Byte-identical move |
| [DTD_CODEX_CURRENT_REALITY_AUDIT.md](DTD_CODEX_CURRENT_REALITY_AUDIT.md) | 20 October baseline snapshot; current-state/execution/R8 records govern later state. | Byte-identical move |
| [DTD_GOVERNANCE_SYNC_EVIDENCE.md](DTD_GOVERNANCE_SYNC_EVIDENCE.md) | Completed governance package reconciliation evidence, not a current implementation brief. | Byte-identical move |
