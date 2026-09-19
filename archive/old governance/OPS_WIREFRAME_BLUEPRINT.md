# DTD Ops Wireframe Blueprint

Date: 2026-06-09
Scope: structural wireframe blueprint for the owner-facing `/ops` console.

## Purpose

This document defines how `/ops` should be structured on screen so the owner can
read it calmly, quickly, and decisively.

It exists to answer:

> What should the `/ops` screen look like structurally, in what order should
> sections appear, and which modules must stay visually grouped so the owner can
> make safe decisions?

It does not define:
1. workflow completion rules
2. route existence or route intent
3. all screen-state variants
4. responsibility boundaries
5. future high-power controls

## Authority And Role Boundaries

This file is part of the canonical implementation pack for the structural shape
of `/ops`.

Role boundaries:
1. `docs/design/WEBSITE_WIREFRAME_SPEC.md` defines the broader website-wide
   structural model outside the detailed `/ops` blueprint.
2. `docs/governance/OPERATIONS_CONSOLE_SPEC.md` defines what `/ops` is and what
   each section means.
3. `docs/governance/OPS_DAILY_OPERATING_MANUAL.md` defines how the owner uses
   `/ops` day to day and in what reading order.
4. `docs/design/WIREFRAME_STATE_MAP.md` defines canonical `/ops` screen states.
5. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md` defines responsibility
   and escalation boundaries.
6. this file defines the structural layout, section grouping, and visual
   reading hierarchy of `/ops`.

If this file conflicts with higher-authority workflow, page, or `/ops` product
truth, the higher-authority document governs.

## Blueprint Principles

1. decision surfaces come before supporting health surfaces
2. the owner should understand current posture before scrolling deeply
3. modules that explain the same decision should stay visually adjacent
4. supporting monitoring should be visible but should not dominate the first
   read
5. the screen should reduce mental stitching, not require it
6. a one-man operator should be able to scan `/ops` daily without hunting for
   the next safe action

## Shell Structure

Authenticated `/ops` should use one stable console shell:
1. auth gate
2. left-side section navigation
3. slim top utility/context bar
4. one main content region for the active section
5. supporting side or lower region for secondary panels when needed

The section order inside that shell should be:
1. overview / decision surface
2. work queue / action surface
3. trainer supply / readiness support
4. messages / trust support
5. billing and reactivation / lifecycle blocker support
6. recent changes / explanation support
7. system activity / health surveillance support

This is a deliberate reading order, not a generic dashboard ordering.

## Auth Gate Blueprint

The auth gate should be structurally simple:
1. page title
2. one-sentence explanation of what `/ops` is for
3. passcode entry
4. error state area
5. confirm / enter action

The auth gate should not:
1. preview sensitive operational data
2. imply broader admin power than the console actually has
3. feel like a developer tool

## Left Navigation

The left-side navigation should:
1. stay stable while the owner moves across sections
2. make the current section obvious
3. reduce the feeling of moving through one long report
4. keep the section order identical to the daily operating manual

The left-side navigation should not:
1. compete with the active section content
2. carry dense metric content
3. imply broader admin power than Normal Ops actually allows

## Header And Context Frame

The top frame of the authenticated console should always contain:
1. page title
2. current phase and public posture context
3. last refreshed / currentness context if shown
4. quiet utility actions such as refresh and sign out if shown

The top frame should not:
1. compete visually with the decision summary
2. introduce dense health detail before the owner sees current posture
3. read like a large hero block

## Above-The-Fold Rule

Above the fold on desktop should answer these questions without requiring the
owner to scroll into supporting sections:
1. what phase are we in?
2. what is the current recommendation?
3. is anything blocked?
4. what needs attention now?
5. should I proceed, hold, review, monitor, or escalate?

The modules that should dominate above the fold are:
1. compact summary strip
2. decision summary
3. recommendation
4. blocker summary
5. attention-needed summary
6. direct handoff into the highest-priority work queue item or queue state

System health charts or loop detail must not be the first visual emphasis.

## Overview Blueprint

The Overview section is the primary decision surface.

It should be composed in this order:
1. compact summary strip
2. decision summary card
3. phase and readiness card
4. recommendation card
5. blocker card or blocker summary block
6. attention-needed block
7. compact supporting counts

The Overview should make these outputs visually obvious:
1. ready vs not ready
2. blocked vs not blocked
3. action needed now vs safe to continue monitoring
4. next safest step

The Overview should avoid:
1. repeating the same status text in multiple cards
2. scattering key posture signals across distant modules
3. presenting monitoring detail before decision meaning

## Work Queue Blueprint

The Work Queue is the primary action surface after Overview.

Desktop structure:
1. grouped queue list on the left or first column
2. selected item detail panel on the right or second column
3. keep the queue itself as the dominant visual object for the section

Mobile structure:
1. grouped queue list first
2. selected item detail below, or navigated into clearly

Each queue row should visually prioritize:
1. priority
2. workflow
3. item title
4. current state
5. decision needed
6. last updated

The detail panel should keep these blocks together:
1. why this exists
2. what decision is needed
3. recommended next step
4. evidence
5. review state
6. owner note
7. review history

The detail panel should not bury the decision ask beneath historical detail.

## Trainer Supply Blueprint

Trainer Supply is a decision-support surface, not just a data table.

It should be composed in this order:
1. top summary for supply sufficiency
2. geography and coverage support
3. blocked-supply support
4. pace and trend support
5. trainer inventory detail table
6. supporting notes or secondary context only after the table if needed

The first visual layer should answer:
1. do we have enough intro-ready supply?
2. where is supply thin?
3. what is blocked from becoming usable?
4. are we moving in the right direction?

The trainer detail table should not appear before the owner sees the supply
judgment layer.

## Messages Blueprint

Messages is a trust-support surface.

It should be composed in this order:
1. message health summary
2. failure or warning emphasis when relevant
3. recent message log
4. supporting context only if it adds trust meaning

The first read should answer:
1. are messages succeeding?
2. is there a trust-impacting delivery problem?
3. which workflow is affected?

## Billing And Reactivation Blueprint

This section should present trainer lifecycle blockers clearly.

It should be composed in this order:
1. lifecycle exception summary
2. active exception list
3. safe recovery path links where they exist
4. supporting notes only after the exception surfaces

The first read should answer:
1. is supply being blocked by lifecycle issues?
2. is this recoverable?
3. should this be reviewed now or monitored?

## Recent Changes Blueprint

Recent Changes is an explanation surface.

It should be composed simply:
1. short section framing
2. recent event list

Its purpose is to help the owner answer:
1. what changed recently that explains the current picture?
2. did something important move without requiring a deep audit search?

It should stay compact and readable.

## System Activity Blueprint

System Activity is a supporting health surface.

It should be visually separated from the first decision surfaces.

It should be composed in this order:
1. health summary
2. stale or severity-high emphasis
3. loop/activity detail
4. supporting context blocks after the main health read if needed

It should answer:
1. is runtime freshness threatening trust?
2. is a stale loop undermining the current picture?
3. does anything here require escalation?

It should not visually dominate the Overview or Work Queue.

## Desktop Layout Rules

On desktop:
1. keep the left-side navigation visible and stable
2. keep Overview and Work Queue visually prominent
3. keep queue list and queue detail visible together where practical
4. keep decision summary and blockers close together
5. keep system activity in a later or clearly separated region
6. avoid a flat single-column wall when two-column comparison improves review

## Mobile Layout Rules

On mobile:
1. preserve the same reading order as desktop
2. keep the decision summary before any deep detail
3. keep the queue state understandable before opening item detail
4. ensure supporting health sections stay later in the stack
5. avoid pushing the recommendation or blocker summary below noisy modules

## Must-Stay-Together Groupings

These items should remain visually grouped:
1. phase, readiness, recommendation, blockers
2. queue row selection and detail explanation
3. supply sufficiency summary and geography/trend support
4. message failures and message log context
5. billing/reactivation exceptions and their safe recovery paths

## Must-Stay-Separate Groupings

These items should remain visually separated:
1. decision summary vs low-level health detail
2. work queue action surfaces vs historical change logs
3. supporting monitoring vs first-read proceed/hold decisions

## Acceptance Rules

The `/ops` blueprint is structurally complete only when:
1. the owner can read posture before deep scrolling
2. the owner can see what needs action before reviewing supporting health
3. the work queue supports review without mental stitching
4. trainer supply supports proceed/hold decisions rather than only record
   inspection
5. monitoring and system health are visible, but not visually prioritized above
   decision surfaces
6. the screen structure matches the reading order in
   `docs/governance/OPS_DAILY_OPERATING_MANUAL.md`
