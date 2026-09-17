# Feature Workflow Fix Backlog

Date locked: 2026-07-08
Scope: current known workflow-completion gaps identified during the DTD docs-to-code audit.

## Purpose

This file keeps the current fix backlog separate from the reusable feature-implementation skill.

It does not redefine product truth.
Canonical truth still comes from:
1. `docs/standards/DTD_PROJECT_CONTEXT.md`
2. `docs/governance/WORKFLOW_COMPLETION_SPEC.md`
3. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`
4. `docs/governance/WORKFLOW_SURFACE_MATRIX.md`
5. `docs/governance/OPERATIONS_CONSOLE_SPEC.md`
6. `docs/design/WIREFRAME_STATE_MAP.md`
7. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`

## Backlog Rules

1. A backlog item is not resolved because UI copy changed or one endpoint passes.
2. Resolve each item only when route behavior, stored records, downstream automation, and `/ops` evidence are coherent where required.
3. If a fix changes workflow semantics, re-check the canonical pack before implementation.
4. Do not use this file to expand scope into unapproved posture changes such as public matching enablement.

## Locked Backlog

## Recommended Execution Order

Address the current backlog in this order:
1. T+7 follow-up visibility in `/ops`
2. `/follow-up/:token` invalid versus expired state separation
3. trainer lifecycle token-state separation on billing and reactivation routes
4. engagement and connect-click operator visibility

Reasoning:
1. item 1 is the clearest end-to-end workflow-completion gap and affects operator awareness directly
2. item 2 completes the owner follow-up lifecycle after item 1 makes that lifecycle visible
3. item 3 applies the same state-discipline to trainer lifecycle routes
4. item 4 is important, but likely depends on the desired final `/ops` evidence shape and is less sharply bounded than the first three

### 1. T+7 follow-up is not fully visible in `/ops`

- Status: addressed in code on 2026-07-08
- Severity: `high`
- Workflows affected:
  - `W-DO-6 T+7 Follow-Up`
  - `W-AU-2 Outbound Message And Notification Logging`
- Current gap:
  - T+7 outreach writes to `outreach_events`
  - `/ops` message visibility currently reads from `notification_events`
  - result: owner follow-up outreach can occur without appearing in the main `/ops` messages surface
- Fix outcome required:
  - T+7 sends and failures must become visible in `/ops` messages
  - message-related queue or review evidence must stay coherent with that visibility
- Completion evidence required:
  - sent case visible
  - failed case visible
  - no duplicate-log regression for existing notification flows

### 2. `/follow-up/:token` does not distinguish invalid vs expired states

- Status: addressed in code on 2026-07-08
- Severity: `medium`
- Workflows affected:
  - `W-DO-5 Explicit Outcome Confirmation`
  - `W-DO-6 T+7 Follow-Up`
- Current gap:
  - invalid and expired paths collapse into one generic unavailable state
- Fix outcome required:
  - backend and frontend must support distinct invalid and expired states if the route remains token-based
- Completion evidence required:
  - valid token path still works
  - invalid token state is distinct
  - expired token state is distinct
  - outcome persistence remains intact

### 3. Trainer lifecycle token routes flatten meaningful error states

- Status: addressed in code on 2026-07-08
- Severity: `medium`
- Workflows affected:
  - `W-TR-5 Trainer Billing Remediation`
  - `W-TR-6 Trainer Reactivation`
- Current gap:
  - backend distinguishes invalid, expired, and wrong-context trainer action token cases
  - frontend collapses those into generic unavailable states
- Fix outcome required:
  - lifecycle pages must expose the canonical invalid/expired state model without weakening token protections
- Completion evidence required:
  - valid route path still works
  - invalid token state is distinct
  - expired token state is distinct
  - stale or wrong-context state remains bounded and truthful

### 4. Engagement and connect-click operator visibility is weaker than intended

- Status: addressed in code on 2026-07-08
- Severity: `medium`
- Workflows affected:
  - `W-DO-4 Post-Connect Engagement Capture`
  - match-quality monitoring responsibilities in `/ops`
- Current gap:
  - engagement events and connect-click signals are stored
  - `/ops` exposes some aggregates
  - operator-facing evidence is weaker than the docs imply
- Fix outcome required:
  - operator visibility must be explicit enough to review engagement continuity and signal health without database inspection
- Completion evidence required:
  - at least one readable `/ops` surface shows the required engagement evidence
  - signal visibility remains aligned with current Normal Ops boundaries

## Usage Note

This backlog is a current execution artifact.
The reusable implementation skill should enforce workflow completeness generally, not bake these four items in as permanent product truth.
