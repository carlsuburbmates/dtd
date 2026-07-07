# Wireframe State Map

Date: 2026-06-09
Scope: canonical screen-state inventory for workflow-serving routes and
operator-facing surfaces.

## Purpose

This document makes wireframe coverage explicit.

It exists so that:
1. every workflow has a route and screen-state path
2. every wireframe state exists to serve a workflow
3. design, page truth, and workflow truth stay aligned

It does not define:
1. product workflow completion rules
2. route existence or route intent
3. `/ops` responsibility boundaries
4. visual design tokens or component APIs

## Authority

This file is part of the canonical implementation pack for screen-state mapping.

Role boundaries:
1. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` owns route purpose and required sections.
2. `docs/governance/WORKFLOW_SURFACE_MATRIX.md` owns the workflow-to-surface
   mapping.
3. `docs/design/WEBSITE_WIREFRAME_SPEC.md` owns the structural layout of public
   and lifecycle routes.
4. `docs/governance/OPS_WIREFRAME_BLUEPRINT.md` owns the structural layout of
   `/ops`.
5. this file owns canonical screen-state coverage for those routes.
6. `docs/design/FIGMA_COMPONENT_MAP.md` owns component naming and component-code
   mapping only.

If this file conflicts with workflow truth, page truth, or `/ops` truth, the
higher-authority document governs.

## State Rules

1. Every listed route must define its primary state plus all launch-relevant
   degraded or abnormal states.
2. Screen states must be named by workflow purpose, not by arbitrary visual
   variants.
3. Empty states are valid only when they still preserve workflow meaning.
4. Token-based lifecycle routes must always define invalid and expired states.
5. `/ops` states must preserve readability first and never imply broader control
   power than the current console boundary allows.

## Public And Lifecycle Routes

| Route | Supports workflow(s) | Canonical screen states |
|---|---|---|
| `/` | `W-DO-1`, future `W-DO-2`, trainer signpost into `W-TR-1` | waitlist-mode default, waitlist submit success, duplicate, rejection, consent missing, matching-mode idle, matching-mode results, matching disabled |
| `/how-it-works` | supports owner/trainer understanding before `W-DO-1` and `W-TR-1` | standard explainer, posture clarification, support fallback |
| `/about` | supports product framing for owner/trainer trust | standard framing, trust boundary clarification |
| `/pricing` | supports trainer-side commercial understanding before `W-TR-1`/`W-TR-2` | standard pricing explanation, billing-readiness clarification |
| `/trust` | supports owner consent and trust framing before `W-DO-1` and `W-DO-3` | trust explainer, consent/boundary clarification |
| `/faq` | supports owner/trainer pre-action clarification | standard FAQ, support fallback |
| `/contact` | support path for all workflows | standard support state |
| `/privacy` | legal support for consent-heavy workflows | standard legal state |
| `/terms` | legal support for consent-heavy workflows | standard legal state |
| `/trainers` | `W-TR-1` | standard acquisition state, truthful supply-first explanation, CTA continuity to `/submit` |
| `/submit` | `W-TR-2` | form idle, validation error, consent/billing-precondition failure, successful submit/result state |
| `/submit/status/:submissionId` | `W-TR-3`, `W-TR-4` | intro-ready, publish/pending, hold, blocked, missing token/invalid id, dead-end prevention state |
| `/trainer/billing` | `W-TR-5` | current issue summary, recover/reconnect state, resolved state, invalid token, expired token |
| `/trainer/reactivate` | `W-TR-6` | reactivation context, recovery checklist, success/next-step state, invalid token, stale state |
| `/t/:id` | `W-DO-3`, `W-DO-4` | trainer profile, consent gate, contact reveal success, gated state, invalid trainer, unavailable trainer |
| `/trainers/:id` | alias for `W-DO-3`, `W-DO-4` | same state inventory as `/t/:id` |
| `/lp/:campaign` | `W-DO-1` attribution entry | campaign-specific entry, waitlist handoff, trainer-path handoff, no-broad-matching posture preserved |
| `/melbourne/:suburb` | `W-DO-1` SEO entry | suburb-specific entry, waitlist handoff, trainer-path handoff, no-broad-matching posture preserved |
| `/follow-up/:token` | `W-DO-5`, `W-DO-6` | valid token idle, confirm positive outcome, confirm no outcome, response saved, invalid token, expired token |

## `/ops` Route

| Surface | Supports workflow(s) | Canonical screen states |
|---|---|---|
| `/ops` auth gate | `W-OP-1` | idle login, invalid passcode, locked/throttled, success transition |
| `/ops` overview | `W-OP-2` | healthy snapshot, blockers present, stale snapshot, empty-safe state |
| `/ops` work queue | `W-OP-2`, `W-OP-3` | grouped case list, selected detail, empty queue, review save success, persistence failure |
| `/ops` trainer supply | `W-TR-2`, `W-TR-3`, `W-TR-4` | active supply table, blocked-state emphasis, empty-safe inventory, stale-data warning |
| `/ops` messages | `W-AU-2`, `W-DO-6` | recent messages, delivery failure emphasis, empty-safe log |
| `/ops` billing & reactivation | `W-TR-5`, `W-TR-6` | active exceptions, resolved/recently resolved, empty-safe state |
| `/ops` system activity | `W-EX-1`, `W-AU-1` | healthy loops, aging loop warning, stale loop alert, ingestion issue emphasis |
| `/ops` recent changes | `W-OP-3` plus audit review support | recent event list, empty-safe state |

## Route-Less Workflow Surfaces

These workflows do not require public page routes, but they still require named
operator-visible evidence surfaces:

1. `W-EX-1 Discovery Queue Contribution`
   - operator surface: `/ops` system activity and queue visibility when abnormal
2. `W-AU-1 Runtime Loop Health And Freshness`
   - operator surface: `/ops` system activity
3. `W-AU-2 Outbound Message And Notification Logging`
   - operator surface: `/ops` messages

## Daily-Use Alignment Rule

The `/ops` screen-state system is aligned only when:
1. `Overview` states answer posture and immediate action first
2. `Work Queue` states make review decisions explicit
3. `Trainer Supply` states make supply sufficiency and coverage readable
4. `Messages`, `Billing & Reactivation`, `Recent Changes`, and `System Activity`
   remain supporting surfaces in that order

That operating order is defined in
`docs/governance/OPS_DAILY_OPERATING_MANUAL.md`.
