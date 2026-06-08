# Workflow Completion Spec

## Purpose

This document is the canonical completion authority for DTD workflows.

It defines what each launch-relevant workflow must do end to end before that
workflow can be called complete.

It does not define:
1. current project status
2. current blockers
3. current next steps
4. page-level layout or route copy
5. `/ops` page structure

## Authority And Precedence

This document sits under the authority order routed by
`docs/governance/CURRENT_TRUTH_INDEX.md`.

Role boundaries:
1. `docs/standards/SSOT.md` defines the product model, actor types, and workflow families.
2. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` defines page- and route-level behavior.
3. `docs/governance/WORKFLOW_SURFACE_MATRIX.md` maps workflows to routes, screen states, and required `/ops` evidence.
4. `docs/governance/OPERATIONS_CONSOLE_SPEC.md` defines the owner-facing `/ops` product surface.
5. `docs/design/WIREFRAME_STATE_MAP.md` defines canonical screen-state coverage for workflow-serving routes.
6. this document defines workflow-level completion and E2E verification requirements.
7. `docs/process/WEBSITE_COMPLETION_CHECKLIST.md` tracks execution work but must not redefine workflow completion.
8. `docs/governance/EXECUTION_STATUS.md` tracks current state but must not redefine workflow completion.

If workflow completion language in a lower-authority document conflicts with this
file, this file governs.

## User Types

Canonical user types:
1. Dog owner
2. Trainer / business submitter
3. Oversight operator
4. External contributor / ecosystem actor
5. Autonomous system actor

## Workflow Rules

Every workflow in scope must define:
1. objective
2. trigger / entry point
3. frontend surfaces
4. canonical route or surface path
5. backend/API/services
6. product-backed data created or updated
7. required `/ops` visibility, where relevant
8. success end state
9. degraded or failure states
10. evidence required
11. exact E2E verification rule
12. exact completion rule

Traceability rule:
1. every workflow must remain traceable into `docs/governance/WORKFLOW_SURFACE_MATRIX.md`
2. every route-serving workflow must remain traceable into `docs/design/WIREFRAME_STATE_MAP.md`
3. if a workflow has no user-facing route, its monitoring surface must still be explicit

A workflow must not be called complete because a page exists or an isolated API
passes. It is complete only when the workflow succeeds end to end according to
its completion rule.

## Workflow Catalog

### Dog owner

#### W-DO-1 Owner Waitlist Capture

Objective:
1. capture passive owner demand during the supply-first phase

Trigger / entry point:
1. `/`
2. campaign or SEO landing pages that route owners toward the waitlist posture

Frontend surfaces:
1. `/`
2. owner waitlist form and consent UI

Backend/API/services:
1. `POST /api/owner-waitlist`
2. waitlist event recording
3. attribution persistence

Data created or updated:
1. owner waitlist record
2. waitlist lifecycle event

Required `/ops` visibility:
1. waitlist summary metrics in overview/readiness areas
2. abnormality visibility when duplicates or rejections become notable

Success end state:
1. owner record is stored with suburb and consent
2. attribution is retained where present
3. duplicate handling is deterministic

Degraded or failure states:
1. invalid email
2. missing consent
3. duplicate active record
4. abnormal rejection pattern

Evidence required:
1. public route behavior
2. backend contract behavior
3. persisted product-backed record/event shape
4. `/ops` summary visibility where relevant

E2E verification rule:
1. a valid owner can submit through the public form, produce the expected backend result, and appear in product-backed waitlist evidence without manual reconstruction

Completion rule:
1. this workflow is complete only when success, duplicate, and rejection paths are all coherent across UI, API, stored data, and monitoring visibility

#### W-DO-2 Live Owner Matching

Objective:
1. accept an owner problem description and return ranked trainer matches when public matching exposure is enabled

Trigger / entry point:
1. `/` when `PUBLIC_MATCHING_ENABLED=true`

Frontend surfaces:
1. `/`
2. result cards and trainer-detail transition path

Backend/API/services:
1. `POST /api/match`
2. ranking logic
3. attribution and match event recording

Data created or updated:
1. match event
2. ranking result set

Required `/ops` visibility:
1. match-quality and demand health signals where implemented
2. launch phase and exposure state must remain visible separately

Success end state:
1. up to three ranked results are returned with coherent reasoning and route links

Degraded or failure states:
1. invalid input
2. consent missing
3. zero-result collapse
4. matching disabled by exposure gate

Evidence required:
1. API contract behavior
2. public UI behavior in matching mode
3. downstream trainer-detail transition continuity

E2E verification rule:
1. in matching-enabled mode, a valid request returns ranked results and preserves downstream navigation/attribution signals

Completion rule:
1. this workflow is not launch-critical for the current supply-first phase, but it remains product-critical for later matching-enabled phases

#### W-DO-3 Trainer Detail Contact Release

Objective:
1. let an owner progress from a trainer result or lifecycle route into explicit contact release

Trigger / entry point:
1. `/t/:id`
2. `/trainers/:id`

Frontend surfaces:
1. trainer detail page
2. connect/contact release UI

Backend/API/services:
1. trainer detail fetch
2. connect/contact release path
3. engagement tracking

Data created or updated:
1. intro or contact-release lifecycle record
2. engagement signals where applicable

Required `/ops` visibility:
1. downstream visibility in queue, messages, billing, and follow-up areas where applicable

Success end state:
1. consented owner can progress to contact release under the current policy

Degraded or failure states:
1. missing consent
2. public exposure is gated
3. invalid trainer or dead lifecycle path

Evidence required:
1. trainer detail route behavior
2. policy-aware gating behavior
3. lifecycle record creation

E2E verification rule:
1. trainer detail, consent, contact release, and downstream lifecycle state remain coherent under the active public posture

Completion rule:
1. workflow is complete only when the route, policy gate, lifecycle record, and downstream observability stay aligned

#### W-DO-4 Post-Connect Engagement Capture

Objective:
1. record owner engagement signals after trainer exposure or contact release

Trigger / entry point:
1. website click, phone click, email click, return visit, or equivalent signal path

Frontend surfaces:
1. trainer detail and downstream lifecycle surfaces

Backend/API/services:
1. engagement recording endpoints/services
2. attribution and signal processing

Data created or updated:
1. engagement event records

Required `/ops` visibility:
1. growth, engagement, or quality signals where implemented

Success end state:
1. engagement signals persist as product-backed evidence

Degraded or failure states:
1. event not stored
2. attribution disconnect

Evidence required:
1. stored event evidence
2. downstream reporting visibility

E2E verification rule:
1. a real engagement action creates the expected event and remains visible in product-backed evidence

Completion rule:
1. workflow is complete only when engagement capture is not merely front-end-visible but product-backed and reviewable

#### W-DO-5 Explicit Outcome Confirmation

Objective:
1. capture whether a trainer intro resulted in a meaningful outcome

Trigger / entry point:
1. post-intro outcome path
2. explicit owner confirmation path

Frontend surfaces:
1. follow-up flow or equivalent owner outcome surface

Backend/API/services:
1. outcome capture endpoints
2. billing/conversion logic where applicable

Data created or updated:
1. outcome or conversion records

Required `/ops` visibility:
1. relevant revenue, trust, and follow-up consequences

Success end state:
1. owner outcome can be recorded without ambiguity

Degraded or failure states:
1. invalid token
2. expired flow
3. conflicting outcome state

Evidence required:
1. outcome path behavior
2. persisted outcome/conversion state

E2E verification rule:
1. the owner can confirm or decline an outcome through the intended lifecycle path and the resulting state is persisted correctly

Completion rule:
1. workflow is complete only when valid and invalid outcome paths are both coherent and downstream state changes are visible

#### W-DO-6 T+7 Follow-Up

Objective:
1. gather outcome or no-outcome feedback when no conversion signal appears after intro

Trigger / entry point:
1. automated follow-up lifecycle
2. `/follow-up/:token`

Frontend surfaces:
1. follow-up page

Backend/API/services:
1. outreach automation
2. follow-up token validation
3. follow-up outcome recording

Data created or updated:
1. message event
2. follow-up response state
3. downstream conversion/no-conversion evidence

Required `/ops` visibility:
1. message log visibility
2. downstream work-queue or lifecycle visibility where relevant

Success end state:
1. follow-up message can be sent and acted on through a valid token path

Degraded or failure states:
1. invalid or expired token
2. delivery failure
3. follow-up response not persisted

Evidence required:
1. message-send behavior
2. follow-up route behavior
3. persisted response state

E2E verification rule:
1. a follow-up path can be generated, delivered, opened, and resolved into persisted outcome state

Completion rule:
1. workflow is complete only when message generation, route behavior, and stored response state remain coherent

### Trainer / business submitter

#### W-TR-1 Trainer Acquisition Path

Objective:
1. explain the supply-first trainer model and route trainers into submission

Trigger / entry point:
1. `/trainers`

Frontend surfaces:
1. trainer acquisition page

Backend/API/services:
1. none required beyond page delivery and linked CTA continuity

Data created or updated:
1. none directly

Required `/ops` visibility:
1. none directly

Success end state:
1. trainer sees a truthful model and a usable path to `/submit`

Degraded or failure states:
1. misleading copy
2. dead CTA

Evidence required:
1. page truthfulness against current supply-first posture
2. CTA continuity

E2E verification rule:
1. trainer can understand the offer and reach the submission path without contradictory copy or dead navigation

Completion rule:
1. workflow is complete only when the acquisition page and submission transition are truthful and usable

#### W-TR-2 Trainer Submission

Objective:
1. collect trainer/business submission data and start activation

Trigger / entry point:
1. `/submit`

Frontend surfaces:
1. trainer submission form
2. submission success path

Backend/API/services:
1. trainer submission endpoint
2. publish-or-hold decision path

Data created or updated:
1. trainer submission record
2. trainer record or equivalent activation candidate
3. submission events

Required `/ops` visibility:
1. queue visibility for relevant cases
2. trainer inventory visibility
3. messages visibility if notifications are sent

Success end state:
1. valid submission enters the system with deterministic status

Degraded or failure states:
1. invalid payload
2. consent/billing-precondition failure where relevant
3. hold path without coherent downstream status

Evidence required:
1. form behavior
2. backend submission contract
3. downstream inventory/queue visibility

E2E verification rule:
1. a valid trainer can submit, receive the expected resulting state, and remain visible in product-backed downstream views

Completion rule:
1. workflow is complete only when submission, downstream state, and visibility remain coherent

#### W-TR-3 Publish-Or-Hold Decision

Objective:
1. classify trainer submissions into publish/hold/blocked states under product rules

Trigger / entry point:
1. system evaluation after submission or downstream updates

Frontend surfaces:
1. submission status and trainer lifecycle surfaces where applicable

Backend/API/services:
1. publish-or-hold logic
2. scoring/verification logic

Data created or updated:
1. trainer status
2. blocker or readiness signals

Required `/ops` visibility:
1. work queue visibility
2. trainer inventory status and blockers

Success end state:
1. trainer state is classifiable without ad hoc manual decisioning

Degraded or failure states:
1. hidden hold
2. blocker not surfaced
3. status not reflected in inventory or queue

Evidence required:
1. product-backed state transitions
2. queue/inventory reflection

E2E verification rule:
1. submitter state and Ops visibility remain aligned after the publish-or-hold decision

Completion rule:
1. workflow is complete only when decision state is deterministic and visible to the system and operator

#### W-TR-4 Trainer Activation Readiness

Objective:
1. show whether the trainer is intro-ready, blocked, or needs lifecycle remediation

Trigger / entry point:
1. trainer lifecycle state after submission
2. `/submit/status/:submissionId`

Frontend surfaces:
1. submission status page

Backend/API/services:
1. readiness evaluation
2. trainer inventory/readiness summaries

Data created or updated:
1. readiness state and blocker evidence

Required `/ops` visibility:
1. trainer supply table
2. readiness blockers
3. queue cases where intervention/monitoring is required

Success end state:
1. trainer and operator can understand current activation state

Degraded or failure states:
1. blockers hidden
2. lifecycle route dead-ends

Evidence required:
1. submission status behavior
2. trainer inventory visibility

E2E verification rule:
1. readiness state, blockers, and next-step guidance remain aligned across status surfaces and Ops inventory

Completion rule:
1. workflow is complete only when activation readiness is understandable without database inspection

#### W-TR-5 Trainer Billing Remediation

Objective:
1. let a trainer resolve billing-profile or billing-lifecycle blockers safely

Trigger / entry point:
1. `/trainer/billing`

Frontend surfaces:
1. billing remediation route

Backend/API/services:
1. billing status fetch
2. reconnect/remediation path

Data created or updated:
1. trainer billing-profile state
2. remediation events

Required `/ops` visibility:
1. billing & reactivation section
2. related queue cases where applicable

Success end state:
1. trainer can understand and progress billing remediation through the intended route

Degraded or failure states:
1. invalid or expired action token
2. status mismatch
3. dead remediation path

Evidence required:
1. billing route behavior
2. token-path protection
3. downstream Ops visibility

E2E verification rule:
1. a billing-remediation case can progress through the intended lifecycle route without breaking trust, visibility, or state coherence

Completion rule:
1. workflow is complete only when the route, token control, state update, and Ops visibility all remain coherent

#### W-TR-6 Trainer Reactivation

Objective:
1. let an inactive trainer re-enter the active lifecycle through the intended route

Trigger / entry point:
1. `/trainer/reactivate`

Frontend surfaces:
1. trainer reactivation route

Backend/API/services:
1. reactivation fetch and update paths
2. downstream state/routing logic

Data created or updated:
1. reactivation candidate state
2. trainer readiness state

Required `/ops` visibility:
1. billing & reactivation visibility
2. queue cases where applicable

Success end state:
1. reactivation can be attempted safely through the intended lifecycle path

Degraded or failure states:
1. invalid token
2. stale candidate state
3. invisible reactivation blocker

Evidence required:
1. reactivation route behavior
2. product-backed state transition
3. Ops visibility

E2E verification rule:
1. reactivation state and its operator visibility remain coherent from route entry to stored result

Completion rule:
1. workflow is complete only when reactivation can be understood, attempted, and reviewed through product-backed state

### Oversight operator

#### W-OP-1 Passcode-Gated Oversight Authentication

Objective:
1. protect `/ops` while preserving owner usability

Trigger / entry point:
1. `/ops`

Frontend surfaces:
1. Ops login screen
2. authenticated console

Backend/API/services:
1. `/api/oversight/login`
2. oversight auth guard
3. auth attempt lockout logic

Data created or updated:
1. auth-attempt records where applicable

Required `/ops` visibility:
1. not applicable; this is the gate to `/ops`

Success end state:
1. valid passcode grants access
2. invalid passcodes are rejected
3. brute-force protection exists

Degraded or failure states:
1. invalid pass accepted
2. valid pass rejected incorrectly
3. no lockout protection

Evidence required:
1. login behavior
2. auth-protection test coverage

E2E verification rule:
1. access control must be enforceable from login UI through protected backend snapshot routes

Completion rule:
1. workflow is complete only when the gate protects the console without bypass or dead-end failure

#### W-OP-2 Continuous Oversight Monitoring

Objective:
1. let the owner understand the website state quickly through `/ops`

Trigger / entry point:
1. authenticated `/ops`

Frontend surfaces:
1. overview
2. work queue
3. trainer supply
4. messages
5. billing & reactivation
6. system activity
7. recent changes

Backend/API/services:
1. `/api/oversight`
2. read models for queue, trainer inventory, messages, system activity, and audit visibility

Data created or updated:
1. none required for pure read visibility

Required `/ops` visibility:
1. all current implemented sections and plain-language scan path

Success end state:
1. owner can understand website status, risks, and next review points quickly

Degraded or failure states:
1. stale or malformed snapshot
2. section mismatch
3. invisible blockers

Evidence required:
1. UI render behavior
2. snapshot contract
3. code-backed read-model support

E2E verification rule:
1. the owner can authenticate, load the snapshot, and use the intended scan order to understand current state without external dashboards

Completion rule:
1. workflow is complete only when the console is readable, coherent, and backed by current product data

#### W-OP-3 Monitor / Investigate / Escalate Review Flow

Objective:
1. let the owner triage and track Layer 1 work safely without turning `/ops` into admin CRUD

Trigger / entry point:
1. work queue case review flow

Frontend surfaces:
1. `/ops` work queue
2. case detail panel

Backend/API/services:
1. `ops_cases` read model
2. persisted `ops_case_states`
3. bounded review update endpoint

Data created or updated:
1. review state
2. owner note
3. review history

Required `/ops` visibility:
1. case row grouping
2. review state
3. owner note
4. review history
5. recommended next step
6. responsibility layer

Success end state:
1. owner can record bounded Layer 1 review progress without changing live policy, provider state, or direct data

Degraded or failure states:
1. no persistence
2. history lost
3. review semantics imply broader override power than intended

Evidence required:
1. queue UI behavior
2. bounded review write behavior
3. persisted state merge behavior

E2E verification rule:
1. a queue case can be reviewed, saved, reloaded, and remain visible as bounded Layer 1 history

Completion rule:
1. workflow is complete only when review-state persistence is durable, auditable, and still bounded inside Normal Ops

Operating response expectations for the current one-owner model:
1. `Monitor`: same-day logging
2. `Investigate`: begin within 4 hours of trigger
3. `Escalate`: immediate transition into Technical-Owner Mode when the trigger crosses the hard boundary

### External contributor / ecosystem actor

#### W-EX-1 Discovery Queue Contribution

Objective:
1. admit external discovery/source contributions into the product pipeline safely

Trigger / entry point:
1. discovery source ingestion or equivalent contribution path

Frontend surfaces:
1. none required in the public website

Backend/API/services:
1. discovery queue ingestion
2. verification and normalization paths

Data created or updated:
1. discovery queue records
2. source-ingestion state

Required `/ops` visibility:
1. system activity and source-ingestion issues
2. queue visibility where contribution health becomes operator-relevant

Success end state:
1. external contributions enter the intended autonomous pipeline and become reviewable if abnormal

Degraded or failure states:
1. source ingestion stalls
2. unsafe or malformed source remains invisible

Evidence required:
1. source-ingestion/runtime evidence
2. operator visibility where failures occur

E2E verification rule:
1. a source contribution path must be observable from ingestion into monitoring state without silent failure

Completion rule:
1. workflow is complete only when contribution health is observable and abnormalities are surfaced

### Autonomous system actor

#### W-AU-1 Runtime Loop Health And Freshness

Objective:
1. keep autonomous loops observable and healthy under the one-owner operating model

Trigger / entry point:
1. continuous runtime operation

Frontend surfaces:
1. `/ops` system activity

Backend/API/services:
1. runtime loops
2. health monitoring
3. oversight snapshot build

Data created or updated:
1. system-state loop freshness and alert records

Required `/ops` visibility:
1. loop name
2. status
3. freshness
4. stale/escalation threshold
5. current alerts

Success end state:
1. stale or unhealthy autonomous behavior becomes visible without code inspection

Degraded or failure states:
1. stale loops hidden
2. alerting silent

Evidence required:
1. runtime/system-state evidence
2. oversight snapshot visibility

E2E verification rule:
1. loop health must remain visible from runtime records through `/ops` system activity

Completion rule:
1. workflow is complete only when autonomous health can be monitored through product-backed evidence

#### W-AU-2 Outbound Message And Notification Logging

Objective:
1. make trust-impacting outbound communications visible and reviewable

Trigger / entry point:
1. automated messaging paths such as trainer submission notices and follow-up messages

Frontend surfaces:
1. `/ops` messages section

Backend/API/services:
1. notification services
2. message logging

Data created or updated:
1. message log records

Required `/ops` visibility:
1. time
2. workflow
3. target
4. message kind
5. delivery status
6. provider
7. delivery detail

Success end state:
1. the operator can review what the system sent and whether delivery succeeded

Degraded or failure states:
1. silent messaging
2. missing delivery result

Evidence required:
1. message log persistence
2. Ops messages visibility

E2E verification rule:
1. an automated message path must leave product-backed message evidence that becomes visible in `/ops`

Completion rule:
1. workflow is complete only when messaging is no longer invisible to the operator

## Cross-Workflow Dependencies

1. Trainer submission, publish-or-hold, activation readiness, billing remediation,
   and reactivation form a single trainer lifecycle chain and must remain coherent.
2. Trainer detail contact release, engagement capture, outcome confirmation, and
   T+7 follow-up form a single owner intro/outcome chain.
3. `/ops` oversight workflows depend on current read models for queue, inventory,
   messages, billing/reactivation, system activity, and recent changes.
4. Launch-phase monitoring depends on supply-readiness, waitlist evidence, loop
   health, and readiness snapshots remaining visible through product-backed data.

## Launch-Critical Workflows

For the current supply-first launch posture, the minimum launch-critical workflows are:
1. owner waitlist capture
2. trainer acquisition path
3. trainer submission
4. publish-or-hold decision
5. trainer activation readiness
6. trainer billing remediation
7. trainer reactivation
8. passcode-gated oversight authentication
9. continuous oversight monitoring
10. Layer 1 monitor / investigate / escalate review flow
11. runtime loop health and freshness
12. outbound message and notification logging

Live owner matching remains product-critical but is not part of the current
supply-first public launch gate while `PUBLIC_MATCHING_ENABLED=false`.
