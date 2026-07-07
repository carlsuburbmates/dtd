# DTD Ops Daily Operating Manual

Date: 2026-06-09
Scope: canonical day-to-day operating manual for how a single owner should use
`/ops` to run DTD safely and decisively.

## Purpose

This document answers one practical question:

> What does the owner need to look at every day, in what order, and what
> decision should each `/ops` section help them make?

It exists so:
1. the owner has one clear operating method
2. `/ops` visuals and data stay prioritized by decision value
3. daily operating work does not drift into scattered interpretation
4. future `/ops` changes are judged against real owner use, not feature sprawl

It does not define:
1. product truth
2. workflow completion rules
3. route existence
4. high-power override behavior
5. final launch approval

## Authority And Precedence

This manual is part of the canonical implementation pack for operating use.

Role boundaries:
1. `docs/standards/SSOT.md` defines the product model and actor types.
2. `docs/governance/WORKFLOW_COMPLETION_SPEC.md` defines what workflows must do end to end.
3. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` defines route and page behavior.
4. `docs/governance/WORKFLOW_SURFACE_MATRIX.md` maps workflows to surfaces and `/ops` evidence.
5. `docs/governance/OPERATIONS_CONSOLE_SPEC.md` defines the `/ops` product surface.
6. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md` defines responsibility boundaries.
7. this file defines the owner’s day-to-day reading order, operating priorities, and decision use of `/ops`.

If this file conflicts with workflow truth, page truth, `/ops` product truth, or
responsibility boundaries, the higher-authority document governs.

## Operating Principle

DTD should be run from `/ops` in this order:
1. decide what needs action
2. decide whether supply is strong enough
3. decide whether any trainer-side lifecycle issue needs intervention
4. only then review supporting monitoring and system health

This means:
1. decision surfaces come first
2. supporting evidence comes second
3. technical health remains important, but must not dominate the owner’s first reading

The owner should not need to mentally stitch together five sections before
knowing whether to:
1. proceed
2. hold
3. review
4. monitor
5. escalate

## What The Website Needs Day To Day

On a day-to-day basis, the website needs these truths to stay visible:

1. whether the current launch phase is still the correct one
2. whether supply is becoming more usable or more blocked
3. whether any workflow exception now needs review
4. whether outgoing communication is succeeding or failing
5. whether billing or reactivation issues are preventing supply readiness
6. whether any autonomous loop has become stale enough to threaten trust
7. whether recorded changes explain what moved recently

Those truths should all be available from `/ops` without requiring:
1. provider dashboards
2. code reading
3. raw database inspection
4. memory of previous sessions

## Daily Operator Reading Order

The owner’s reading order should be:

1. `Overview`
2. `Work Queue`
3. `Trainer Supply`
4. `Messages`
5. `Billing & Reactivation`
6. `Recent Changes`
7. `System Activity`

Rationale:
1. `Overview` answers “is the website ready, blocked, or waiting?”
2. `Work Queue` answers “what exactly needs review right now?”
3. `Trainer Supply` answers “is supply sufficient or not?”
4. `Messages` answers “has the system contacted people successfully?”
5. `Billing & Reactivation` answers “are trainer-side lifecycle blockers accumulating?”
6. `Recent Changes` answers “what changed that explains the current state?”
7. `System Activity` answers “is system health quietly undermining trust?”

Shell rule:
1. the owner should move through these sections from a stable left-side navigation
2. the top bar should stay small and contextual
3. each section should have one main work surface
4. supporting panels should stay below or beside the main work
5. health reading should stay available without crowding the first decision surfaces

## Section-By-Section Operating Manual

### 1. Overview

Use this section first.

The owner should be able to answer:
1. what phase are we in?
2. is the website ready, blocked, or still collecting evidence?
3. what is the current recommendation?
4. what is the single safest next move?
5. does anything need attention now?

The highest-priority visuals/data here are:
1. decision summary
2. current phase
3. readiness state
4. recommendation
5. blockers
6. attention counts
7. supply decision support

The owner should leave this section with one of these conclusions:
1. proceed with the current posture
2. hold and review
3. review the work queue now
4. check supply before moving forward
5. inspect supporting health before trusting the current picture

### 2. Work Queue

Use this section immediately after Overview when action is needed.

The owner should be able to answer:
1. what item needs review first?
2. why does this item exist?
3. what decision is needed?
4. what is the recommended next step?
5. should this be reviewed, monitored, or escalated?

The highest-priority visuals/data here are:
1. priority
2. workflow
3. item summary
4. decision needed
5. current state
6. evidence
7. review history

The owner should not have to infer whether a case is:
1. informational only
2. actionable now
3. safe to monitor
4. serious enough to escalate

The case-detail panel should always make four things plain:
1. why this exists
2. what workflow it belongs to
3. what the next safe step is
4. what recording a review state does and does not change

### 3. Trainer Supply

Use this section to judge supply sufficiency.

The owner should be able to answer:
1. do we have enough usable trainer supply to move forward?
2. where is supply strong?
3. where is supply thin?
4. what is blocked?
5. are we moving in the right direction or not?

The highest-priority visuals/data here are:
1. intro-ready now
2. blocked supply
3. trainer suburb coverage
4. waitlist suburb coverage
5. demand gaps
6. submission pace
7. published pace
8. per-trainer blockers

This section exists to support:
1. proceed vs hold decisions
2. readiness interpretation
3. suburb coverage review
4. trainer-side blocker review

The owner should not need to guess whether a low number means:
1. quiet but acceptable
2. demand without supply
3. supply blocked by billing or activation issues

### 4. Messages

Use this section when a workflow likely touched a person.

The owner should be able to answer:
1. did the system send the message?
2. did the provider succeed or fail?
3. which workflow generated the message?
4. does a failure create a trust problem?

The highest-priority visuals/data here are:
1. delivery status
2. workflow
3. target
4. provider
5. delivery detail

This section is especially important when:
1. trainer submission notifications fail
2. follow-up messages fail
3. reactivation notifications fail

### 5. Billing & Reactivation

Use this section to understand trainer-side recovery blockers.

The owner should be able to answer:
1. which trainer lifecycle issues are blocking readiness?
2. is this a billing issue or a reactivation issue?
3. does the trainer have a safe next path already?
4. does this need review now or only monitoring?

The highest-priority visuals/data here are:
1. trainer/business label
2. current state
3. reason
4. lifecycle link
5. last update

This section should help the owner distinguish:
1. recoverable trainer-side issues
2. system-side issues
3. cases that matter to readiness vs cases that can wait

### 6. Recent Changes

Use this section to explain movement.

The owner should be able to answer:
1. what changed recently?
2. who or what changed it?
3. does the current state make sense in light of those changes?

The highest-priority visuals/data here are:
1. time
2. event
3. entity
4. actor

This section is not the first decision surface.
It is the reconciliation surface after a question already exists.

### 7. System Activity

Use this section last in the normal daily reading order.

The owner should be able to answer:
1. is any loop stale?
2. is any loop unhealthy enough to threaten trust?
3. is there a high-severity condition hiding behind a calm overview?
4. is source ingestion behaving?

The highest-priority visuals/data here are:
1. loop status
2. freshness
3. escalation threshold
4. active alerts
5. source-ingestion failures

This section matters, but it should remain a supporting section because:
1. most daily operator decisions are about readiness, review, or hold
2. health surveillance should support those decisions, not replace them

## Daily Operating Rhythm

### Opening check

Start with:
1. Overview
2. Work Queue
3. Trainer Supply

Goal:
1. know whether today is a proceed, hold, review, or monitor day

### Active review block

Then use:
1. Work Queue
2. Messages
3. Billing & Reactivation

Goal:
1. resolve or classify items that now need attention

### Trust check

Then use:
1. Recent Changes
2. System Activity

Goal:
1. confirm the picture is trustworthy
2. catch hidden health drift before it becomes public damage

### End-of-window review

When judging launch or readiness progression, use:
1. Overview
2. Trainer Supply
3. Work Queue
4. Messages
5. Billing & Reactivation
6. System Activity

Goal:
1. decide whether evidence supports proceed, hold, or defer

## What Counts As A Daily Decision

The owner’s normal daily decisions should stay inside Layer 1 — Normal Ops.

That means:
1. review
2. monitor
3. acknowledge
4. record what happened
5. escalate when needed

It does not mean:
1. changing public exposure
2. changing launch phase
3. changing billing policy
4. changing provider state
5. direct data repair
6. deployment/runtime mutation

## Mapping The Website’s Daily Needs To `/ops`

| Daily need | Main `/ops` section | Supporting section | Decision output |
|---|---|---|---|
| Readiness and current posture | Overview | Trainer Supply | proceed / hold |
| Review exceptions | Work Queue | Messages, Billing & Reactivation | review / monitor / escalate |
| Supply sufficiency | Trainer Supply | Overview | sufficient / insufficient |
| Trainer-side recovery blockers | Billing & Reactivation | Work Queue | review / hold |
| Messaging trust | Messages | Work Queue | safe / needs review |
| Change explanation | Recent Changes | Work Queue | understood / needs follow-up |
| Health surveillance | System Activity | Overview | healthy / watch / escalate |

## Current Gaps And Improvement Rule

The manual should not pretend the console is finished forever.

Future `/ops` work is valid only if it improves one of these:
1. decision clarity
2. supply sufficiency reading
3. workflow exception handling
4. trust-preserving health visibility

Future `/ops` work is not valid if it mainly adds:
1. visual noise
2. admin-like control power
3. duplicate metrics without clearer decisions
4. monitoring detail that crowds out the owner’s first reading

## Acceptance Standard For Ops Manual Alignment

The `/ops` UI and the day-to-day manual are aligned only when:
1. the owner can start in Overview and know the current posture quickly
2. the queue tells the owner what decision is needed without guesswork
3. trainer supply answers sufficiency and coverage questions directly
4. messages and billing/reactivation reveal trust-impacting exceptions
5. recent changes and system activity support the main decision flow rather than replacing it
6. no section quietly suggests broader operator power than the current boundary allows
