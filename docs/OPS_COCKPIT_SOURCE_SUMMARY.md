# Ops Cockpit Source Summary

Historical source-summary. Not normative.

## Purpose

This document consolidates the original repo documentation about owner responsibilities, the existing `/ops` oversight surface, linked operational flows, and actions that remain outside the product.

It is intended as the source-summary input for designing a future ops cockpit.

This file summarizes what the original docs already define.
It does not invent new product behavior.

Current authority references:
1. `docs/standards/SSOT.md`
2. `docs/standards/BUILD_CHECKLIST.md`
3. `docs/standards/LAUNCH_GATE.md`
4. `docs/standards/INTEGRITY_AUDIT.md`
5. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`
6. `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`
7. `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`

Current responsibility boundary is `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`.

## Canonical ownership model

The documented operating model is single-owner and mode-based.

The same human owner operates in two modes:
1. `operator mode`
2. `technical-owner mode`

Canonical source references:
- `docs/OPERATIONS.md`
- `docs/governance/LOCK_STATE.md`

Core rule:
1. reversible, bounded, policy-safe actions may be handled in `operator mode`
2. any action that changes locked runtime policy or requires infra/provider/runtime intervention is `technical-owner mode`

This section reflects the original source summary only.
Current canonical terminology is `Normal Ops`, `Owner Override`, and `Technical-Owner Mode` per `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`.

## What the original docs say `/ops` is

The original docs define `/ops` as the primary owner-facing oversight surface, but not as an all-in-one operational cockpit.

Canonical source references:
- `docs/USER_WORKFLOWS.md` W9-W10
- `docs/OPERATIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/WORKFLOW_TRACE_SHEET.md` W9-W10

Documented definition:
1. `/ops` is passcode-gated through `POST /api/oversight/login`
2. `/ops` uses `GET /api/oversight` polling for the operational snapshot
3. `/ops` is read-only oversight
4. `/ops` provides operational visibility, not direct mutation controls
5. `/ops` is the default daily control view for the owner in `operator mode`

## What `/ops` currently covers in the original docs

The original docs explicitly place these responsibilities inside `/ops`:

1. Daily monitoring and triage
- start-of-day, midday, and end-of-day checks
- same-day logging of what changed and whether follow-up is needed
- `Monitor` / `Investigate` / `Escalate` decision framing

2. Core oversight tiles and snapshot visibility
- revenue booked
- revenue collected
- revenue at risk
- trial-free intros
- intros 24 h / 7 d
- conversions 24 h
- engagement events
- connect-click signals
- suppressed intros
- suspicious conversions
- inferred pending
- loop cards
- growth attribution summary
- reactivation summary
- pricing state
- top trainers
- recent system actions

3. Investigation support inside `/ops`
- investigation queue for billing recovery and reactivation cases
- source-ingestion detail for repeated suppression/failure checks
- local operator-note logging

4. Read-only business and system monitoring
- health and alert visibility
- loop freshness visibility
- throughput and trust-signal visibility
- billing and revenue visibility
- pricing visibility
- top-trainer visibility
- audit-feed visibility

Primary source references:
- `docs/OPERATIONS.md:29-99`
- `docs/USER_WORKFLOWS.md:219-227`

## What the owner is expected to do from `/ops`

The original docs make `/ops` the place where the owner:
1. notices whether the system is healthy
2. identifies stale loops, alerts, and revenue risk
3. distinguishes routine monitoring from investigation
4. decides whether the issue can stay in `operator mode`
5. decides when to switch into `technical-owner mode`

In other words, `/ops` is documented as the main situational-awareness and triage surface.

## What is linked from `/ops` rather than solved entirely inside `/ops`

The original docs split several owner responsibilities into linked workflow surfaces instead of embedding full case handling inside `/ops`.

### 1. Trainer billing remediation

Documented flow:
1. owner notices billing recovery issues in `/ops`
2. owner inspects billing retry/remediation state
3. owner routes the trainer into `/trainer/billing` or support email when remediation is required

Canonical sources:
- `docs/OPERATIONS.md:148-175`
- `docs/WORKFLOW_TRACE_SHEET.md:33-34`
- `docs/ARCHITECTURE.md:10`

### 2. Trainer reactivation

Documented flow:
1. owner notices weak reactivation performance or blocked trainers in `/ops`
2. owner reviews reactivation summary and thresholds
3. owner directs the trainer into `/trainer/reactivate` or support follow-up

Canonical sources:
- `docs/OPERATIONS.md:183-195`
- `docs/WORKFLOW_TRACE_SHEET.md:35`
- `docs/ARCHITECTURE.md:10`

### 3. Support handling

Documented flow:
1. owner uses `/ops` for context and diagnosis
2. owner uses the canonical support mailbox for outbound handling

Canonical support mailbox:
- `info@dogtrainersdirectory.com.au`

Canonical sources:
- `docs/OPERATIONS.md:197-205`

### 4. Submission and trainer lifecycle context

Documented flow:
1. `/ops` provides visibility into system state and blockers
2. trainer lifecycle remediation occurs through dedicated trainer-facing flows such as submission status, billing reconnect, and reactivation

Canonical sources:
- `docs/ARCHITECTURE.md:10`
- `docs/WORKFLOW_TRACE_SHEET.md:33-35`

## What remains outside the product and requires `technical-owner mode`

The original docs do not place these responsibilities inside `/ops`.
They remain out-of-band actions for the same owner acting in `technical-owner mode`.

### Runtime and infrastructure intervention
- restart backend/runtime processes
- inspect supervisor/service logs
- diagnose loop stoppage at runtime level
- restore loop ownership process

Primary sources:
- `docs/OPERATIONS.md:101-108`
- `docs/ARCHITECTURE.md:73-79`

### Configuration and policy intervention
- change locked runtime flags
- change launch mode or billing mode
- adjust env vars such as pricing/trial settings
- re-apply or leave reverted config after health-loop auto-rollback

Primary sources:
- `docs/OPERATIONS.md:110-121`
- `docs/OPERATIONS.md:177-181`
- `docs/governance/LOCK_STATE.md:21-27`

### Provider and platform intervention
- secret rotation
- provider account changes
- domain, TLS, hosting, and deployment recovery
- billing-provider configuration recovery

Primary sources:
- `docs/governance/LOCK_STATE.md:21-27`
- reflected operationally in `docs/OPERATIONS.md`

### Direct data intervention
- legal takedown of a listing
- refunding a billed intro/conversion
- wiping a poisoned discovery batch
- pairing every direct write with an `audit_log` reason record

Primary sources:
- `docs/OPERATIONS.md:207-214`

## Responsibilities explicitly documented as read-only visibility in `/ops`

The original docs are clear that `/ops` is not an admin mutation panel.

Documented read-only boundaries:
1. W10 exit outcome is operational visibility only, with no mutation controls
2. `/ops` is an observation and triage surface in practice
3. policy-changing and infra-changing actions are outside routine operator mode

Canonical sources:
- `docs/USER_WORKFLOWS.md:219-227`
- `docs/OPERATIONS.md:18-27`
- `docs/governance/LOCK_STATE.md:21-27`

## Owner responsibility map from the original docs

### Inside `/ops`
1. Observe business and runtime health
2. Monitor alerts, loops, revenue, attribution, and reactivation state
3. Review recent system actions and trust signals
4. Use investigation queue and source-ingestion detail
5. Record routine daily notes
6. Decide `Monitor` vs `Investigate` vs `Escalate`

### Linked from `/ops` into other product surfaces
1. route billing blockers into `/trainer/billing`
2. route reactivation cases into `/trainer/reactivate`
3. use submission-status and trainer lifecycle flows for context/remediation
4. use support mailbox for support-driven follow-up

### Outside the product in `technical-owner mode`
1. restart services
2. inspect logs and runtime crashes
3. change env/config/runtime flags
4. recover provider/platform issues
5. deploy/redeploy/rollback
6. perform direct DB repair or legal/manual writes

## Documented gaps that a future ops cockpit could address

The original docs already imply several cockpit gaps.

### Gap 1. `/ops` is primary, but not complete

The owner can see the system, but cannot resolve everything from one place.

Evidence:
- `docs/USER_WORKFLOWS.md` defines visibility-only oversight
- `docs/OPERATIONS.md` routes several problems into other pages, support, logs, or runtime actions

### Gap 2. Case handling is split across multiple surfaces

The owner must move between:
1. `/ops`
2. `/trainer/billing`
3. `/trainer/reactivate`
4. support mailbox
5. runtime/log/deploy environments

### Gap 3. Investigation depth is limited

The roadmap already calls for:
1. better first-check ordering in `/ops`
2. in-product `Monitor` / `Investigate` / `Escalate` thresholds
3. better case-level investigation depth for billing recovery, reactivation, discovery/source-ingestion, and alert context
4. clearer bounded remediation paths from `/ops`

Primary source:
- `docs/governance/ROADMAP.md:178-193`

### Gap 4. Notes and case management are weak

The original operational model uses local operator notes in `/ops`, but not shared or durable in-product case management.

Primary source:
- `docs/OPERATIONS.md:86-89`

### Gap 5. Technical-owner actions are still out-of-band

The most important founder responsibilities in incidents still happen outside `/ops`.

Examples:
1. service restart
2. log inspection
3. env changes
4. deployment recovery
5. provider repair
6. direct DB intervention

### Gap 6. Supply-first launch visibility is not defined in the original summary

The current supply-first Standards Set now requires launch-phase and readiness evidence that the original source summary did not define.

Current gaps relative to the committed supply-first standards are:
1. no current launch phase view
2. no readiness snapshot view
3. no phase transition decision trail
4. no supply-first `/ops` priority ordering
5. no data sufficiency evidence view

## Design implication for a future ops cockpit

If a future ops cockpit is derived from the original docs, it should be treated as an expansion of the existing `/ops` concept, not as a replacement of the operating model.

The original docs support designing a cockpit that:
1. keeps `/ops` as the owner's main operational surface
2. preserves the read-only and bounded-action boundary for `operator mode`
3. centralizes links, context, and case progression across billing, reactivation, support, and source-ingestion issues
4. makes the switch into `technical-owner mode` explicit when the action leaves safe operator scope

The original docs do not support silently turning `/ops` into an unrestricted admin console.

Newer standards also do not support:
1. unrestricted admin CRUD
2. manual trainer matching as routine work
3. manual routine billing
4. automatic phase switching
5. automatic enabling of `PUBLIC_MATCHING_ENABLED`

## Source index

Primary source docs used for this summary:
1. `docs/OPERATIONS.md`
2. `docs/USER_WORKFLOWS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/WORKFLOW_TRACE_SHEET.md`
5. `docs/governance/LOCK_STATE.md`
6. `docs/governance/ROADMAP.md`
