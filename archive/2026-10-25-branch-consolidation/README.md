# Git consolidation and preservation — 25 October 2026

## Scope and preflight

Owner requested audit of uncommitted work, commit/sync, and safe branch merging/deletion. Main checkout started clean on `feature/r4-trainer-supply` at `4f47fea`; `origin/main` was `a20687e`. Feature remote head was `10c8879`, with PR20 open and green existing checks. No production or provider mutation is part of this Git task.

A private, verified all-ref bundle preserves39 refs, including the stash. The obsolete R2 automatic merge is separately preserved as `refs/archive/2026-10-25/r2-auto-merge`, with raw index and merge metadata stored privately. Snapshot commit: `ec7fc2fcdfc32b43f9f85ee7c5a5010b5c8b2793`. Private raw artifacts/credentials are not committed in this record.

## Uncommitted work

- Main checkout had no uncommitted changes initially. The source-audit corrections below are new task changes to commit before sync.
- R2 reconciliation worktree: HEAD/ORIG_HEAD `a5f167c`, MERGE_HEAD `d83c7f4`; both already belong to main. Every stage0 index blob and all working files equal `AUTO_MERGE`; four conflicts retain their original three stages. No manual edits, untracked or ignored files exist. Preserve the snapshot, abort only this stale automatic merge and keep the resulting checkout detached; do not replay superseded implementation.
- Suppression worktree: one untracked [historical handoff](SUPPRESSION_DELTA_REVIEW_HANDOFF.md), now preserved with its superseded status explicit. Source implementation already belongs to accepted `50f3c594`; it is not new pending code. Original payload is also preserved privately.
- Dependency symlinks in two worktrees are retained. Existing stash is preserved unchanged. Worktree directories remain available as detached historical checkouts after branch retirement.

## Branch audit decisions

| Ref/group | Evidence | Decision |
|---|---|---|
| Branch tips already ancestors of main | Exact merge-base ancestry checked after fetch; original refs preserved in bundle | Retire obsolete local/remote operational refs; detach clean checked-out tips first. |
| `codex/dtd-governance-r2` | `dd90590` patch-equivalent to integrated `bac696e`; all20 postimages in `11c764a` equal integrated `1ee8168` | Archive original chain; retire without merging old state. |
| `codex/matching-pipeline` |13/15 patch-equivalent; remaining audit blobs equal integrated `f6a7182`/`d30333f`; intermediate current-state claims superseded later | Archive original chain; retire without replaying intermediate status. |
| Remote `codex/dtd-live-audit-remediation` extra commit | `8bd3985` patch-equivalent to integrated `493aae4`, then hardened further | Retire after preservation; no missing code to merge. |
| `codex/r8-audit-completion` | Entire tip `336df0a` belongs to current feature branch | Retire after exact-head feature integration. |
| Feature branch / PR20 | Prior accepted corrections and cleanup retained; new audit findings corrected with independent source review | Push reviewed exact head; require its CI before source-only main merge. Runtime R8 remains PARTIAL. |
| Stale Dependabot PR7 | Requested axios1.16/postcss8.5.14; current axios1.20 and lockfile-resolved postcss8.5.29 supersede them; provider reports zero open Dependabot alerts | Close as superseded after current lockfile verification; preserve its commit in bundle. |

## Source correction boundary

Independent review of the latest storefront package found embedded authentication values/forged tokens and URL logs, a hostname-check regression, unstable combobox default-array state, missing keyboard dismissal/ARIA reset and missing alternate canonical postcodes. Corrections remove the unsafe signing/credential pattern and unscoped write flows from audit scripts, constrain the checkout inspector to an already existing test URL on the exact HTTPS host, restore fail-closed deployment defaults and repair the combobox. Core claimed-owner management remains protected by its existing API/session path.

Root independently reviewed the frontend correction; a separate reviewer accepted root's security/default corrections for source sync. Canonical539 names/primary postcodes/regions were compared to the backend catalogue. Runtime equivalence of historical authentication literals remains DF-055 / NEEDS_AUTH. Existing master-guide enabled flags are dated/unverified, not release evidence.

No tests added or run locally during this Git audit. Existing CI is reused for the previous exact remote head; the corrected new exact head must pass its own automatic checks before merge. Final Git/CI/ref outcomes will be appended after execution. Branch deletion is not production promotion, credential containment, or deletion of the retained private archives/worktree directories.
