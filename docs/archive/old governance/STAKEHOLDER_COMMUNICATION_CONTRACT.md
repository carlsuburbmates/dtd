# DTD Stakeholder Communication Contract

Date: 2026-08-09
Scope: canonical communication rules for DTD lifecycle events and exceptions.

## Purpose

This contract defines how DTD keeps people informed without turning communication
into routine manual work for the single owner.

The governing rule is:

> Automate expected lifecycle messages. Surface only communication exceptions
> that require human judgment.

This contract does not:
1. enable public matching
2. activate a new billing mode
3. create a CRM or shared support team
4. require the owner to review successful routine messages
5. replace workflow, page, privacy, or responsibility rules in higher-authority documents

## Authority

This file sits under:
1. `docs/standards/DTD_PROJECT_CONTEXT.md` for product, actor, launch, and operating truth
2. `docs/governance/WORKFLOW_COMPLETION_SPEC.md` for workflow completion
3. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` for route and page behavior

It governs communication semantics across those workflows.

Related operator behavior remains governed by:
1. `docs/governance/OPERATIONS_CONSOLE_SPEC.md`
2. `docs/governance/OPS_DAILY_OPERATING_MANUAL.md`
3. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`

## Stakeholders

The communication model covers:
1. Dog owner
2. Trainer / business submitter
3. Oversight operator
4. External contributor / ecosystem actor
5. Autonomous system actor as the sender, recorder, and failure detector

The canonical support and reply path is:
1. route: `/contact`
2. mailbox: `info@dogtrainersdirectory.com.au`

No second routine support inbox or parallel communication system should be introduced.

## Communication Principles

1. Communicate only when a stakeholder's state, expected action, or trust position changes.
2. Use automation for acknowledgements, status updates, reminders, and routine recovery.
3. Do not ask the owner to approve or send routine lifecycle messages.
4. Do not expose internal scores, raw states, provider errors, or operator terminology to public recipients.
5. Every message must explain what happened, what it means, and the next safe action.
6. Every outbound message must use the canonical reply-to mailbox.
7. A provider accepting a message means `sent`; it does not prove `delivered`.
8. Communication failure must never silently change publication, matching, billing, or consent state.
9. Personal contact details must be minimised in logs and masked in `/ops`.
10. Current supply-first communication must remain separate from later live-matching communication.

## Stakeholder Event Matrix

| Event | Recipient | Channel | Required outcome | Operator involvement |
|---|---|---|---|---|
| Owner waitlist accepted or duplicate recognised | Dog owner | Page result; email acknowledgement when configured | Confirm receipt and set a truthful expectation | None unless repeated failures or a reply needs judgment |
| Trainer submission received and classified | Trainer / submitter | Result page and email | Confirm receipt, current status, and status-route link | None for normal publish or hold |
| Trainer submission held or blocked | Trainer / submitter | Status route and email | Explain the missing requirement and next safe step | Only when the issue cannot be resolved through the documented route |
| Trainer becomes intro-ready | Trainer / submitter | Status route; email when a material state change occurs | Confirm readiness without promising introductions | None |
| Billing profile needs remediation | Trainer / submitter | Billing route and bounded email reminder | Explain the blocker and provide the protected remediation path | Only after retries are exhausted or the trainer replies for help |
| Reactivation is available | Trainer | Reactivation route and bounded email reminder | Explain why action is needed and provide the protected path | Only when recovery remains blocked |
| Introduction is created | Trainer; dog owner receives the contact-release result | Trainer notification and owner result surface | Tell each party what happened and what to do next | Only on permanent notification failure or trust complaint |
| T+7 outcome follow-up becomes due | Dog owner | Email with protected follow-up link | Capture outcome or no-outcome without pressure | Only on systemic delivery failure or a reply needing judgment |
| Payment collection changes state | Trainer when action is required | Provider notice and/or DTD remediation message | Explain only the action-requiring state and recovery path | Only for dispute, exhausted recovery, or provider failure |
| A public lifecycle action fails after submission | Affected stakeholder | Page failure state; email only when an earlier success must be corrected | Give a truthful state and support route | Create `/ops` work only when trust, money, access, or data continuity is affected |
| Messaging or provider health degrades | Oversight operator | `/ops` only | Show scope, impact, retry state, and safe next step | Investigate or escalate under the responsibility model |
| External discovery contribution is processed | External contributor | No individual message required by default | Keep processing outcome product-backed and observable | Only abnormal source or ingestion behavior appears in `/ops` |

Later-phase rows do not activate live matching. They apply only when the relevant
workflow is explicitly enabled.

## Delivery State Contract

Every outbound communication must record one of these states:
1. `queued`: accepted by DTD but not yet submitted to the provider
2. `sent`: accepted by the provider; delivery is not yet proven
3. `delivered`: confirmed by the provider when that evidence is available
4. `failed`: the current attempt failed and may be retried
5. `suppressed`: intentionally not sent because consent, address, duplication, or policy prevents it
6. `permanent_failure`: retry is unsafe, impossible, or exhausted
7. `unknown`: provider outcome cannot be determined

Rules:
1. retry only transient failures
2. use the configured bounded retry policy; do not create unbounded resend loops
3. do not retry invalid recipients, consent failures, complaints, or permanent provider rejection
4. create operator work only for `permanent_failure`, repeated `unknown`, systemic failure, or a trust-sensitive missed message
5. a later provider update may advance `sent` to `delivered` or `permanent_failure`
6. duplicate workflow events must not create duplicate stakeholder messages

## Inbound Reply Contract

1. All automated messages must direct replies to the canonical support mailbox.
2. The subject or message metadata must retain a safe workflow reference so the owner can identify the related submission, trainer, intro, billing case, or follow-up.
3. Sensitive tokens and full private payloads must not appear in email subjects or `/ops` rows.
4. Routine acknowledgements do not require a reply.
5. A stakeholder reply becomes operator work only when it requests a decision, reports a broken path, disputes money or consent, or cannot be resolved through an existing lifecycle route.
6. Provider auto-replies, spam, and delivery notices should not become manual cases unless they indicate a systemic problem.
7. DTD does not require an inbound CRM for launch; the support mailbox remains the reply surface and `/ops` remains the decision-evidence surface.

## Message Content Contract

Every stakeholder message must include:
1. DTD identity
2. the workflow reason for contact
3. the stakeholder's current plain-language state
4. one primary next action, or a clear statement that no action is needed
5. a protected lifecycle link when action is required
6. the canonical support path
7. a truthful timing statement only when the system can meet it

Every message must avoid:
1. guaranteed outcomes
2. claims that matching is live during the supply-first posture
3. internal confidence scores or raw status names
4. unnecessary personal data
5. urgency that is not supported by a real deadline
6. multiple competing calls to action

Each message kind must have a stable template key and version so `/ops` can show
what type of message was sent without storing the full private body.

## `/ops` Evidence Contract

The `Messages` section must expose enough information to answer:
1. which workflow communicated
2. which stakeholder type was targeted
3. which message kind and template version were used
4. whether the provider accepted or delivered it
5. how many attempts occurred
6. whether another retry is scheduled
7. why delivery failed or was suppressed
8. whether owner action is required
9. which lifecycle record or case provides safe context

The operator-facing record should contain:
1. event time
2. workflow
3. masked target
4. message kind
5. template version
6. provider
7. delivery state
8. attempt count
9. next retry time when applicable
10. concise delivery detail
11. related safe lifecycle reference
12. `action_required` as an explicit boolean

Normal successful messages remain evidence, not work-queue cases.

## Escalation Rules

The system should create or elevate an `/ops` case only when:
1. a trust-sensitive message reaches `permanent_failure`
2. failures affect multiple stakeholders or indicate provider degradation
3. a stakeholder reports a broken lifecycle path
4. a reply disputes consent, publication, contact release, or money
5. communication state conflicts with the underlying product state

Normal Ops may:
1. review the evidence
2. record a note or review state
3. direct the stakeholder to an existing safe lifecycle route
4. escalate under `OPS_COCKPIT_RESPONSIBILITY_MODEL.md`

Provider repair, policy changes, direct data changes, refunds, publication
changes, and runtime intervention remain Technical-Owner Mode.

## Completion Standard

A stakeholder communication path is complete only when:
1. its trigger and recipient are explicit
2. success, suppression, retry, and permanent-failure states are product-backed
3. the stakeholder receives a plain-language state and one safe next action
4. replies route to the canonical support mailbox with usable context
5. `/ops` shows the communication outcome without exposing unnecessary private data
6. only genuine exceptions create owner work
7. duplicate events cannot create duplicate messages
8. current launch posture and consent boundaries remain truthful

## Implementation Priority

Apply this contract in the smallest useful order:
1. trainer submission and status communication
2. billing remediation and reactivation communication
3. provider delivery-state and retry visibility in `/ops`
4. inbound reply context and exception routing
5. later-phase introduction and T+7 communication when live matching is approved

