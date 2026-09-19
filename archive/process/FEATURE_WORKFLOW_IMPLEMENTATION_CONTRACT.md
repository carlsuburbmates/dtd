# Feature Workflow Implementation Contract

Date: 2026-07-08
Scope: reusable implementation and validation contract for DTD features that affect users, operators, or autonomous workflow branches.

## Purpose

This file defines the process contract that implementation work must follow.

It does not redefine product truth.
It structures how to apply the canonical DTD workflow model during feature work so route changes do not drift away from data, automation, and `/ops` visibility.

## Required Inputs

Read these before using this contract for implementation or validation:
1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
4. `docs/governance/CURRENT_TRUTH_INDEX.md`
5. `docs/standards/DTD_PROJECT_CONTEXT.md`
6. `docs/governance/WORKFLOW_COMPLETION_SPEC.md`
7. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`
8. `docs/governance/WORKFLOW_SURFACE_MATRIX.md`
9. `docs/design/WIREFRAME_STATE_MAP.md`
10. `docs/governance/OPERATIONS_CONSOLE_SPEC.md`
11. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`

Read lower-authority support docs only after the canonical pack is clear.

## When This Contract Is Required

Use this contract when a task affects any of:
1. dog owner workflow behavior
2. trainer or business-submitter workflow behavior
3. lifecycle routes
4. automation, notification, billing-remediation, or reactivation flows
5. `/ops` evidence, queue, message, review, or monitoring visibility
6. autonomous triggers that branch from user activity
7. validation of a feature that claims to be complete end to end

Do not skip the contract because a change looks small at the route level.

## Core Rule

Implement features as workflows, not isolated pages.

A feature is not complete because:
1. a page renders
2. a form submits
3. an endpoint returns `200`
4. one record is stored

A feature is complete only when:
1. the initiating user path works
2. product-backed state is coherent
3. downstream branches and automations are handled
4. degraded and fallback states are explicit
5. operator visibility exists where the workflow requires it

## Non-Negotiable Checks

### 1. Actor Coverage

Identify every actor touched by the feature:
1. Dog owner
2. Trainer / business submitter
3. Oversight operator
4. External contributor / ecosystem actor
5. Autonomous system actor

If the feature starts with one actor but creates downstream work for another actor, both actors are in scope.

### 2. Migration Baseline Versus Target-State Requirements

Separate:
1. current code and runtime behaviour that forms the migration baseline
2. target-state behaviour required by the canonical implementation pack
3. explicit compatibility or rollout behaviour required during replacement

Do not retain a legacy gate, fee loop, waitlist-only path, or old posture merely
because it exists in the baseline. Do not remove a valid route, record, link,
or provider integration without an explicit compatibility, migration, or
rollback treatment.

### 3. Branch Completeness

For the initiating workflow, trace:
1. success path
2. duplicate path
3. invalid or rejected path
4. blocked or gated path
5. fallback or fail-soft path
6. downstream automation or notification branch
7. operator-awareness branch

### 4. `/ops` Visibility Contract

If the workflow can:
1. send
2. fail
3. retry
4. suppress
5. hold
6. escalate
7. degrade
8. await review

then the implementation must identify the exact `/ops` surface that proves that state.

### 5. No Hidden Automation

If the feature triggers automation, messaging, billing follow-up, reactivation, outreach, or review cases, that work must be explicit in code and explicit in validation.

## Required Contract For Each Feature

Before editing, write or reason through these fields:

1. Feature goal
2. Canonical workflow(s) affected
3. Migration baseline and target-state relevance
4. Actor map
5. Trigger or entry surface
6. Route or screen surfaces touched
7. Backend/API/services touched
8. Product-backed records created or updated
9. Downstream automations, notifications, or loops triggered
10. Fallback, fail-soft, or degraded states
11. Required `/ops` evidence
12. Exact completion rule
13. Exact verification plan

## Implementation Workflow

1. Identify the initiating workflow from the canonical pack.
2. Identify the target-state requirement and the baseline behaviour to replace, retain, or bridge.
3. Trace the current route, API, service, storage, and `/ops` evidence path before editing.
4. List branch states that must remain explicit.
5. Make the smallest set of changes that closes the whole workflow, not just the visible route.
6. Re-check adjacent workflow branches that could silently drift.
7. Validate success, degraded, and operator-visibility states.

## Completion Gate

Do not call the feature complete unless all applicable checks pass:

1. route or UI behavior is coherent
2. API or service behavior is coherent
3. stored product-backed evidence is coherent
4. downstream automation and notification behavior is coherent
5. `/ops` evidence exists where required
6. target-state behaviour is achieved, or the remaining external rollout action is explicit
7. invalid, duplicate, blocked, expired, or degraded states are still truthful

## Validation Minimums

Choose the smallest bundle that fits the task, but include the full workflow:

1. route or interaction verification
2. backend or service verification for touched logic
3. stored-data verification when records are part of the workflow
4. `/ops` verification when the workflow requires operator awareness
5. adjacent-branch regression check for the same lifecycle

## Anti-Patterns

Do not:
1. stop at the first successful UI state
2. assume a message sent unless the log path is visible
3. assume operator awareness because a database row exists
4. treat baseline launch posture as permission to ignore target-state workflow branches
5. create a parallel workflow document that redefines the canonical pack

## Expected Output Shape For Feature Work

When using this contract, final implementation reporting should state:
1. workflow(s) used
2. actor coverage
3. branches covered
4. `/ops` visibility handled
5. validation performed
6. remaining gaps or deferred items
