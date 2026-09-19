---
name: dtd-feature-workflow-completion
description: Implement or validate DTD features as complete workflows instead of isolated routes. Use when a task affects dog owners, trainers, lifecycle routes, automations, notifications, billing or reactivation flows, or `/ops` visibility, and the work must stay aligned with the repo's canonical workflow, screen-state, and operator-evidence requirements.
---

# DTD Feature Workflow Completion

## Overview

Use this skill to implement or validate DTD features that affect real workflows.
Treat the initiating user step, stored records, downstream automations, fallback paths, and `/ops` evidence as one completion unit.

## Source Of Truth

Read these in order before editing workflow-affecting features:
1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/README.md` (active documentation map)
4. `docs/DTD_CURRENT_STATE.md` and `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`
5. `docs/DTD_TARGETED_POST_LAUNCH_STATE.md` for next-build targets
6. The relevant active topic file under `docs/specs/`
7. `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` if a prior decision is disputed

`archive/` is historical, outside the active documentation tree. Do not read or search it during ordinary work, even if a stale reference points there. Only inspect it on explicit user request for archival research.

## When To Use

Use this skill when the task is about:
1. implementing a new feature that affects a user or operator workflow
2. validating whether a feature is truly complete end to end
3. lifecycle route work such as `/submit/status/:submissionId`, `/trainer/billing`, `/trainer/reactivate`, `/follow-up/:token`, `/t/:id`, or `/ops`
4. automation, notification, billing-remediation, reactivation, or follow-up behavior triggered by user actions
5. ensuring `/ops` shows enough evidence for Normal Ops to understand what happened
6. fixing drift where UI, API, stored state, automation, and `/ops` visibility are no longer aligned

## When Not To Use

Do not use this skill when the task is mainly:
1. premium visual polish on public marketing pages
2. copy cleanup without workflow impact
3. isolated static docs editing that does not affect feature behavior
4. infrastructure-only work with no workflow or operator-evidence consequence
5. a posture change such as enabling public matching, changing billing policy, or broadening product scope without explicit approval

For those cases, use a more specific workflow or skill.

## Target Operating Context

Assume these truths unless the active task includes an approved change:
1. DTD is a Greater Melbourne directory and matching platform with public discovery, rich trainer storefronts, protected enquiries, and optional flat SaaS upgrades.
2. Supply-building means real trainer supply, verified claims, and useful public discovery, not a waitlist-first public posture.
3. Existing gates, intro-fee loops, passive-owner paths, and prelaunch lifecycle states are migration baseline unless explicitly retained by a blueprint.
4. Every workflow must preserve explicit data, automation, degraded-state, and `/ops` evidence requirements.
5. `/ops` remains protected and evidence-led; it is not broad admin CRUD.

Distinguish migration baseline, target-state behaviour, and explicit external
rollout actions. Do not use baseline behaviour to weaken target requirements.

## Core Rule

A feature is not complete because:
1. a page renders
2. a form submits
3. an endpoint returns `200`
4. one database record exists

A feature is complete only when:
1. the initiating user path works
2. product-backed state is coherent
3. downstream branches and automations are handled
4. degraded and fallback states are explicit
5. `/ops` evidence exists where the workflow requires operator awareness

## Required Workflow

1. Identify the canonical workflow or workflows first.
2. Identify every actor touched by the feature:
   - Dog owner
   - Trainer / business submitter
   - Oversight operator
   - External contributor / ecosystem actor
   - Autonomous system actor
3. Trace the current route, API, service, storage, automation, and `/ops` path before editing.
4. Separate the migration baseline from target-state behaviour and explicit rollout actions.
5. Cover all relevant branches:
   - success
   - duplicate
   - invalid or rejected
   - blocked or gated
   - fallback or fail-soft
   - downstream automation or notification
   - operator-awareness branch
6. Make the smallest set of changes that closes the whole workflow, not just the visible route.
7. Re-check adjacent lifecycle paths that could silently drift.
8. Validate success, degraded, and `/ops` visibility states before calling the task complete.

## Required Feature Contract

Before editing, write or reason through these fields against the relevant active spec in `docs/specs/`:
1. feature goal
2. canonical workflow(s) affected
3. migration baseline and target-state relevance
4. actor map
5. trigger or entry surface
6. route or screen surfaces touched
7. backend/API/services touched
8. product-backed records created or updated
9. downstream automations, notifications, or loops triggered
10. fallback, fail-soft, or degraded states
11. required `/ops` evidence
12. exact completion rule
13. exact verification plan

If any of these are unknown, inspect until the gap is resolved before implementing.

## `/ops` Visibility Rule

If the workflow can:
1. send
2. fail
3. retry
4. suppress
5. hold
6. escalate
7. degrade
8. await review

then identify the exact `/ops` surface that proves that state.

Do not assume a workflow is operator-visible because a raw row exists in storage.

## Implementation Rules

1. Prefer modifying existing workflow paths over creating parallel paths.
2. Keep automation fail-soft where the product requires continuity, but never hide the failure from validation or `/ops`.
3. Do not unlock public matching, billing activation, or policy-changing behavior unless explicitly approved.
4. Do not flatten invalid, expired, duplicate, blocked, or stale states into one generic state when canon requires distinction.
5. If the user asked for review only, stop at findings and do not edit.

## Validation Rules

Run the smallest useful validation bundle that still proves the workflow:
1. route or interaction verification for touched surfaces
2. backend or service verification for touched logic
3. stored-data verification when records are part of the workflow
4. `/ops` verification when the workflow requires operator awareness
5. adjacent-branch regression check for the same lifecycle

Use browser or visual verification when the task changes UI behavior.

## Final Report Format

Report in this order:
1. workflow(s) used
2. actor coverage
3. branches covered
4. changes made
5. `/ops` visibility handled
6. validation performed and results
7. remaining gaps or deferred items

If no files were changed, say so explicitly.

## Acceptance Criteria

Treat the pass as successful only if:
1. route or UI behavior is coherent
2. API or service behavior is coherent
3. stored product-backed evidence is coherent
4. downstream automation and notification behavior is coherent
5. `/ops` evidence exists where required
6. target-state behaviour is achieved, or the remaining external rollout action is explicit
7. invalid, duplicate, blocked, expired, stale, or degraded states remain explicit where canon requires them
