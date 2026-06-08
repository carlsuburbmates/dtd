# Workflow Surface Matrix

Date: 2026-06-08
Scope: canonical bridge between workflow truth, page/route truth, screen-state
coverage, and `/ops` observability expectations.

## Purpose

This document exists to prevent drift between:
1. user workflows
2. page and route implementation
3. screen-state and wireframe coverage
4. operator-facing evidence in `/ops`

It answers one question:

> For each canonical workflow, what surface path serves it and what `/ops`
> evidence must exist so failure does not stay invisible?

## Authority

This file is part of the canonical implementation pack.

Role boundaries:
1. `docs/standards/SSOT.md` defines user types, workflow families, and product
   model.
2. `docs/governance/WORKFLOW_COMPLETION_SPEC.md` defines E2E workflow completion
   rules.
3. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` defines route purpose and page-level
   behavior.
4. this file maps workflows to routes, screen states, and `/ops` evidence.
5. `docs/governance/OPERATIONS_CONSOLE_SPEC.md` defines the owner-facing `/ops`
   console surface and section semantics.
6. `docs/design/WIREFRAME_STATE_MAP.md` defines the canonical screen-state
   inventory for the workflow-serving routes.

If this file conflicts with a higher-authority workflow, page, or `/ops`
document, the higher-authority document governs.

## Mapping Rules

1. Every launch-relevant workflow must map to one or more canonical routes or
   named product surfaces.
2. Every named route or product surface must support at least one canonical
   workflow.
3. If a workflow has no user-facing route, its monitoring surface must still be
   explicit.
4. Every launch-critical workflow must identify the `/ops` evidence that proves
   it is healthy, degraded, or failing.
5. `docs/design/WIREFRAME_STATE_MAP.md` must not invent routes or workflows that
   do not appear here.

## Workflow-To-Surface Matrix

| Workflow | User type | Trigger / entry | Primary route or surface | Required screen-state coverage | Required `/ops` evidence | Launch-critical now |
|---|---|---|---|---|---|---|
| `W-DO-1 Owner Waitlist Capture` | Dog owner | passive owner demand capture | `/`, `/lp/:campaign`, `/melbourne/:suburb` | default form, valid submit, duplicate, rejection, consent-missing | waitlist summary, duplicate/rejection abnormality visibility, attribution summary | Yes |
| `W-DO-2 Live Owner Matching` | Dog owner | public matching mode only | `/` in matching mode | prompt entry, valid results, zero results, gated/disabled, invalid input | launch phase and exposure state; downstream demand quality where implemented | No |
| `W-DO-3 Trainer Detail Contact Release` | Dog owner | trainer lifecycle detail route | `/t/:id`, `/trainers/:id` | profile load, consent gate, contact reveal success, gated state, invalid trainer | downstream visibility in queue/messages/billing/follow-up where applicable | No |
| `W-DO-4 Post-Connect Engagement Capture` | Dog owner | post-detail engagement action | trainer detail lifecycle surface | click/engagement success, attribution continuity, failure-safe no-drop state | engagement or quality signals where implemented | No |
| `W-DO-5 Explicit Outcome Confirmation` | Dog owner | outcome confirmation path | `/follow-up/:token` or equivalent outcome surface | valid token, confirm outcome, decline outcome, invalid token, expired token | follow-up and downstream revenue/trust consequence visibility | No |
| `W-DO-6 T+7 Follow-Up` | Dog owner | automated unresolved-outcome follow-up | `/follow-up/:token` | message sent, token open, valid response, expired token, persistence failure | message log, lifecycle visibility, outcome persistence evidence | No |
| `W-TR-1 Trainer Acquisition Path` | Trainer / business submitter | trainer learns and proceeds to submit | `/trainers` | truthful primary state, clear CTA to submit, no dead-end state | none directly required | Yes |
| `W-TR-2 Trainer Submission` | Trainer / business submitter | submission start | `/submit` | form load, valid submit, invalid payload, consent/billing-precondition failure, success/result state | queue visibility, trainer inventory visibility, message visibility if notifications send | Yes |
| `W-TR-3 Publish-Or-Hold Decision` | Trainer / business submitter | system decision after submission or update | `/submit/status/:submissionId`, trainer lifecycle surfaces | publish, hold, blocked, hidden-blocker prevention, downstream reflection | work queue state, inventory status, blocker visibility | Yes |
| `W-TR-4 Trainer Activation Readiness` | Trainer / business submitter | lifecycle state after submission | `/submit/status/:submissionId` | intro-ready, blocked, missing-data, dead-end prevention, next-step guidance | trainer supply table, readiness blockers, queue cases | Yes |
| `W-TR-5 Trainer Billing Remediation` | Trainer / business submitter | billing-lifecycle issue | `/trainer/billing` | valid token/state, billing problem summary, recovery action, expired/invalid token | billing and reactivation section, related queue cases | Yes |
| `W-TR-6 Trainer Reactivation` | Trainer / business submitter | inactive trainer recovery | `/trainer/reactivate` | valid reactivation, stale state, invalid token, recovery checklist | billing and reactivation visibility, related queue cases | Yes |
| `W-OP-1 Passcode-Gated Oversight Authentication` | Oversight operator | ops entry | `/ops` auth gate | login idle, success, invalid passcode, lockout/throttle | not applicable inside `/ops`; this is the gate to console access | Yes |
| `W-OP-2 Continuous Oversight Monitoring` | Oversight operator | authenticated console review | `/ops` overview and page sections | readable overview, stale snapshot handling, section continuity, empty-safe states | overview, work queue, trainer supply, messages, billing/reactivation, system activity, recent changes | Yes |
| `W-OP-3 Monitor / Investigate / Escalate Review Flow` | Oversight operator | queue case review | `/ops` work queue and detail panel | grouped queue states, detail readability, review save, reload persistence, bounded history | `ops_cases`, review state, owner note, review history, responsibility layer | Yes |
| `W-EX-1 Discovery Queue Contribution` | External contributor / ecosystem actor | discovery ingestion | autonomous ingestion surface, no public route required | accepted contribution, duplicate handling, malformed-source handling, silent-failure prevention | system activity, source-ingestion issues, queue visibility where abnormal | No |
| `W-AU-1 Runtime Loop Health And Freshness` | Autonomous system actor | continuous loop execution | `/ops` system activity | healthy, aging, stale, alerting, recovery visibility | loop status, freshness, thresholds, alerts, ingestion issues | Yes |
| `W-AU-2 Outbound Message And Notification Logging` | Autonomous system actor | automated messaging path | `/ops` messages | sent, failed, delayed, missing-log prevention | message log with workflow, target, provider, status, detail | Yes |

## Surface Coverage Rules

1. `/` serves both current waitlist-mode demand capture and future matching-mode
   demand capture. The active state must match `PUBLIC_MATCHING_ENABLED` and the
   launch phase.
2. `/follow-up/:token` serves both explicit outcome confirmation and the T+7
   unresolved-outcome path. Token validity and response persistence must be
   surfaced as distinct states.
3. `/ops` serves three workflow groups at once:
   - access control
   - monitoring visibility
   - bounded Layer 1 review-state persistence
4. Route-less workflows still require named operator visibility surfaces. No
   autonomous or ingestion workflow may rely on hidden backend behavior only.

## Known Bridge Gaps Still Open

These are structurally known gaps, not missing workflow definitions:

1. supply-by-geography visibility in `/ops` is still thinner than the supply
   decision standard requires
2. trainer acquisition and activation trend visibility in `/ops` is still
   count-oriented instead of trend-oriented

These gaps do not invalidate the matrix. They identify where the existing
workflow-to-ops mapping is thinner than the desired operator evidence depth.
