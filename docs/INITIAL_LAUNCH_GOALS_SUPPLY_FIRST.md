# Initial Launch Goals - Supply-First

## Purpose

This document defines the approved initial launch standard for DTD.

The initial launch is supply-first.
It defines what the website and operating model should prove before broader dog-owner launch and live matching exposure.

This is a supply-first launch companion standard.
It defines target-state launch goals for this phase and must conform to the Standards Set.
It does not claim that the current system already satisfies every requirement.

## Authority and Alignment

This document is a launch companion standard for the supply-first phase.

It must conform to:
1. `docs/standards/SSOT.md`
2. `docs/standards/BUILD_CHECKLIST.md`
3. `docs/standards/LAUNCH_GATE.md`
4. `docs/standards/INTEGRITY_AUDIT.md`
5. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`

If this document conflicts with the Standards Set or the Ops Cockpit Responsibility Model, those documents govern.

This document must not be interpreted as approval to build:
1. a generic directory
2. a traditional marketplace
3. unrestricted admin CRUD
4. manual trainer matching
5. manual routine billing
6. automatic phase switching
7. broad owner-demand launch before supply readiness is proven

## Core launch thesis

DTD's initial launch should not primarily be a dog-owner demand launch.

The initial launch should prove:

> DTD can attract, onboard, verify, activate, and monitor enough usable dog-trainer supply to justify controlled dog-owner matching later.

Dog-owner demand should remain passive at this stage through education-first content and waitlist capture.
Live matching should remain gated until supply readiness is proven.

DTD should be described as:
1. a guided match-and-intro system
2. a guided demand-routing and intro platform
3. an automation-first platform with bounded human oversight

DTD should not be described as:
1. a generic directory launch
2. a manual matchmaking service
3. a full marketplace launch
4. a trainer CRM
5. an unrestricted admin dashboard
6. an analytics dashboard product
7. a founder-operated back-office workflow

## Non-negotiable strategic frame

The initial launch is supply-first.

This means:
1. dog trainers are the primary launch audience
2. dog owners are a secondary passive audience during this phase
3. trainer onboarding remains open even when public matching is gated
4. dog-owner demand remains passive until supply readiness is proven
5. live matching must not be enabled automatically
6. routine platform work remains automated
7. `/ops` is Normal Ops by default

## Initial launch phase

Phase name:

```text
supply_first
```

Primary audience:

```text
Dog trainers
```

Secondary/passive audience:

```text
Dog owners
```

## Public website posture

During the supply-first launch, the website should primarily speak to trainers.

Primary trainer posture:
1. register your dog-training business
2. understand the intro-first model
3. submit your profile
4. become intro-ready
5. resolve blockers
6. prepare to receive suitable local intros

Owner posture during this phase:
1. education-first content is allowed
2. passive owner waitlist is allowed
3. no aggressive owner launch should happen
4. no public copy should imply full live matching availability before readiness

## Initial launch success definition

Initial launch succeeds when:

> DTD has enough qualified, activated, intro-ready trainer supply, with clear data evidence, to justify a controlled transition toward dog-owner demand capture and later live matching.

Initial launch does not succeed merely because:
1. the website is live
2. trainers can submit a form
3. `/ops` has dashboard cards
4. owner waitlist exists
5. there is a polished homepage

The launch must prove:
1. supply readiness
2. data sufficiency
3. one-owner operability

## Goal 1. Attract trainer supply

### Goal

Get relevant dog trainers to register interest or submit their business.

### Why this is first

Demand without supply damages trust.
If owners arrive and receive weak, sparse, or irrelevant trainer options, the product loses credibility before it has a chance.

### Required website behaviour

The public website must make trainer onboarding obvious and compelling.

Required surfaces:
1. `/trainers`
2. `/submit`
3. `/submit/status/:submissionId`
4. `/trainer/billing`
5. `/trainer/reactivate`
6. support/contact path

### Required message

Trainer-facing copy must clearly explain:
1. what DTD is
2. how trainers get introduced to dog owners
3. what a valid intro means
4. trial-free period if applicable
5. billing and remediation expectations
6. how to submit
7. what happens after submission

### Non-negotiable requirements

1. Trainer onboarding must remain open even when public owner matching is gated.
2. Trainer CTA must be visible during supply-first launch.
3. Submission must not require founder manual intake.
4. Trainers must receive a clear next-step or status outcome.
5. Trainer registration and submission data must persist in product-owned records.
6. The founder must be able to see trainer acquisition trend in `/ops`.

### Minimum evidence

`/ops` must show:
1. new trainer submissions
2. submission trend
3. publish and hold split
4. active trainers
5. intro-ready trainers
6. blocked trainers
7. supply by target geography or suburb if available

## Goal 2. Activate usable trainer supply

### Goal

Convert trainer registrations into usable, intro-ready supply.

A trainer in the database is not enough.
The trainer must be capable of receiving an intro.

### Required system behaviour

The system should support:
1. trainer submission
2. confidence-based publish or hold decision
3. submission status
4. billing readiness
5. remediation path
6. reactivation path
7. supply health visibility

### Non-negotiable requirements

1. Submission status must be understandable.
2. Billing and profile blockers must be explicit.
3. Blocked trainers must have a remediation path.
4. Trainer activation state must be persisted.
5. Founder must not manually track activation in a spreadsheet.
6. Founder must not manually inspect the database to know who is intro-ready.

### Minimum evidence

Product records must answer:
1. how many trainers submitted?
2. how many were published?
3. how many were held?
4. how many are intro-ready?
5. how many are blocked?
6. why are they blocked?
7. how many were recovered or reactivated?

## Goal 3. Keep dog-owner demand passive until supply is ready

### Goal

Avoid premature owner launch.

Dog owners can be educated and waitlisted, but active owner acquisition and live matching should not be the primary launch emphasis yet.

### Required behaviour

When public matching is not enabled:
1. home should be education-first or supply-first depending phase emphasis
2. owner waitlist may be available
3. trainer onboarding remains open
4. live matching is not the main public home path

### Non-negotiable requirements

1. No active dog-owner marketing push before supply threshold.
2. No public copy implying full matching availability before readiness.
3. No uncontrolled live matching exposure.
4. Owner waitlist records must still be captured cleanly if owners arrive.
5. Owner demand data must preserve suburb, source, and campaign context.

### Minimum evidence

If owners interact passively, `/ops` should show:
1. owner waitlist entries
2. suburb demand
3. source and campaign attribution
4. duplicate and rejected waitlist events
5. trend over time

## Goal 4. Prepare the intro path without forcing owner demand

### Goal

The core owner-to-intro path should be technically ready, but not publicly emphasised until supply is ready.

### Required system behaviour

The path should exist:

```text
owner problem -> ranked trainers -> trainer detail -> connect -> intro record -> contact reveal
```

### Non-negotiable requirements

1. Matching route and API can exist while public exposure is gated.
2. Trainer detail and connect flow must enforce consent.
3. Contact reveal must happen only after valid intro creation.
4. Intro creation must persist.
5. Fraud and suppression logic must protect billing and ranking.
6. This must not become manual matching by the founder.

### Minimum evidence

Before live owner launch, the system must prove:
1. test match can return credible trainers
2. connect flow works
3. intro record is created
4. contact reveal works
5. engagement events are captured
6. outcome and follow-up path exists

## Goal 5. Make intro-first monetisation ready

### Goal

The commercial model must be ready before owner demand is actively pushed.

### Required system behaviour

DTD uses intro-first monetisation.
Valid intro is the commercial trigger.

### Non-negotiable requirements

1. Valid intro must be the commercial trigger.
2. Trial-free state must be explicit.
3. Billable vs non-billable states must be explicit.
4. Stripe and billing state must sync back into product data.
5. Billing recovery must be visible.
6. At-risk revenue must be visible.
7. Founder must not manually invoice routine intros.
8. Refunds, waivers, disputes, and provider intervention remain Technical-Owner Mode.

### Minimum evidence

`/ops` must show:
1. revenue booked
2. revenue collected
3. revenue at risk
4. trial-free intros
5. billing issues
6. retry and remediation states

## Goal 6. Record enough launch data from day one

### Goal

Do not scramble on launch day because records are incomplete, ambiguous, or not analysis-ready.

### Core rule

```text
Database = truth
/ops = readable operating view
audit_log = decision trail
CSV/export = proof only
```

Data sufficiency is a launch requirement, not an afterthought.
CSV and export files are proof artifacts only.

### Required product-owned records

DTD must persist clear records for:
1. trainer submissions
2. trainer activation state
3. trainer billing readiness
4. trainer remediation state
5. trainer reactivation state
6. owner waitlist entries
7. owner waitlist events
8. attribution entries
9. growth attribution
10. match events
11. intros
12. engagements
13. conversions
14. Stripe events
15. outreach events
16. system state
17. source-ingestion state
18. audit log
19. config snapshots

### Additional phase records required

Add or confirm equivalent records for:
1. `launch_phase_state`
2. `phase_readiness_snapshots`
3. `phase_transition_decisions`

### Required fields for `launch_phase_state`

Must record:
1. current phase
2. public matching enabled or disabled
3. trainer onboarding enabled or disabled
4. owner waitlist enabled or disabled
5. current public emphasis
6. updated by
7. updated at
8. reason
9. related audit log entry

### Required fields for `phase_readiness_snapshots`

Must record:
1. current phase
2. readiness status: `not_ready`, `nearly_ready`, `ready`
3. readiness score if used
4. trainer supply count
5. intro-ready trainer count
6. blocked trainer count
7. billing blocker count
8. activation blocker count
9. unresolved high-severity alerts
10. loop health
11. source-ingestion health
12. recommended next phase
13. blockers
14. evidence timestamp

### Required fields for `phase_transition_decisions`

Must record:
1. from phase
2. to phase
3. decision: approved, rejected, or deferred
4. decision maker
5. reason
6. evidence snapshot ID
7. timestamp
8. rollback note if relevant
9. related audit log entry

## Goal 7. Build one phase-aware website, not multiple rebuilds

### Goal

Avoid rebuilding the site at each launch stage.

### Required model

The website should have:

```text
stable routes
phase-aware public emphasis
config-driven CTA priority
feature exposure gates
reusable page sections
```

### Required config concepts

Keep:

```text
PUBLIC_MATCHING_ENABLED
```

Add or define equivalent:

```text
PUBLIC_LAUNCH_PHASE=supply_first | owner_waitlist | live_matching | growth
```

### Required behaviour by phase

#### `supply_first`

Primary:
1. trainer registration
2. trainer value proposition
3. trainer submission

Secondary:
1. owner education
2. passive owner waitlist

Hidden or de-emphasised:
1. live matching CTA

#### `owner_waitlist`

Primary:
1. owner waitlist
2. demand capture

Still open:
1. trainer onboarding

#### `live_matching`

Primary:
1. owner problem input
2. ranked trainers
3. connect and intro

Still open:
1. trainer onboarding

#### `growth`

Primary:
1. broader owner acquisition
2. SEO and campaign scaling
3. attribution improvement

### Non-negotiable requirements

1. Do not build separate homepages per phase.
2. Do not duplicate route logic.
3. Do not hardcode phase copy in many places.
4. Do not require code edits for normal phase emphasis changes.
5. Changing live matching exposure remains Technical-Owner Mode.

## Goal 8. Let the system recommend phase transitions, but never silently transition

### Goal

Automate readiness analysis, not launch authority.

### Required model

The system may calculate:
1. current phase
2. supply readiness
3. demand readiness
4. operational readiness
5. revenue readiness
6. blockers
7. recommended next phase

But the owner must approve any transition affecting:
1. public launch phase
2. public matching exposure
3. billing policy
4. pricing policy
5. trial policy
6. public claims
7. production behaviour

### Responsibility labels

1. Readiness calculation: Automated System
2. Readiness display: Normal Ops
3. Bounded note and review: Owner Override
4. Phase transition approval: Technical-Owner Mode

### Non-negotiable requirements

1. No automatic transition from supply-first to live matching.
2. No automatic enabling of `PUBLIC_MATCHING_ENABLED`.
3. No automatic change to billing, pricing, or trial policy.
4. No automatic public copy or claim escalation from waitlist to live.
5. Every phase decision must have an evidence snapshot and audit trail.
6. Phase transitions require owner approval when they affect public exposure or production behaviour.

## Goal 9. Keep founder workload exception-only

### Goal

The system must reduce founder workload, not manufacture daily admin work.

### Required operating rule

Routine work belongs to the Automated System.

Founder attention is required only when:
1. threshold is breached
2. automation cannot safely resolve the issue
3. money is at risk
4. trust is at risk
5. supply health is at risk
6. matching continuity is at risk
7. system health is at risk
8. owner judgement is required

### Non-negotiable requirements

Do not turn these into manual founder tasks:
1. trainer submission processing
2. routine verification
3. routine matching
4. routine intro creation
5. routine billing reconciliation
6. routine billing retry
7. fraud suppression
8. source ingestion
9. ranking and pricing updates
10. reactivation detection
11. health checks
12. audit logging

Routine platform work remains automated.

## Goal 10. Make `/ops` the readable operating view

### Goal

The founder should understand launch health from `/ops` first.

### Required role of `/ops`

`/ops` is:

```text
Normal Ops surface by default
```

The dashboard is the top-level summary view inside the `/ops` cockpit.
The dashboard is not the launch goal.
It is the evidence surface for the launch goal.

`/ops` should show:
1. supply health
2. trainer acquisition trend
3. intro-ready trainers
4. blocked trainers
5. reactivation candidates
6. passive owner demand signal
7. revenue readiness
8. billing blockers
9. loop health
10. alerts
11. current phase
12. readiness recommendation
13. blockers to next phase

### Non-negotiable requirements

1. `/ops` must not become unrestricted admin CRUD.
2. `/ops` must not become a manual CRM.
3. `/ops` must not become a raw developer console.
4. `/ops` must not expose dangerous actions as casual buttons.
5. Provider tools remain secondary investigation surfaces.
6. Product database remains the source of truth.
7. Owner Override actions must be bounded, reversible, reason-captured, and audited.
8. Technical-Owner Mode is required for launch mode, public matching exposure, billing and pricing and trial policy, provider, deployment, legal, refund, direct-data, or runtime changes.

## Non-negotiable launch gates before owner-facing live matching

Before live owner matching is exposed, DTD must pass these gates.

### Supply gate

1. Minimum trainer supply threshold defined.
2. Minimum intro-ready trainer threshold defined.
3. Target geography covered.
4. Trainer profiles complete enough.
5. Publish and hold logic working.
6. Held and blocked trainers visible.
7. Reactivation and remediation path working.

### Data gate

1. All launch-critical records persist.
2. `/ops` summaries are backed by product data.
3. Phase readiness snapshot exists.
4. Phase decision records exist.
5. Audit log captures owner decisions.
6. CSV and export are available for proof, not as primary record.

### Operational gate

1. `/ops` shows current phase.
2. `/ops` shows supply readiness.
3. `/ops` shows blocker count.
4. `/ops` shows loop health.
5. `/ops` shows unresolved high-severity alerts.
6. Founder can answer "are we ready for owners?" without database queries.

### Revenue gate

1. Trial-free state works.
2. Billable state works.
3. Stripe state syncs into product records.
4. Billing remediation path exists.
5. At-risk revenue visibility exists.

### Safety and trust gate

1. Consent enforced.
2. Contact release controlled.
3. Fraud suppression working.
4. Suspicious signals visible.
5. Public copy does not overpromise.

### Technical-owner approval gate

1. Owner reviews readiness snapshot.
2. Owner records decision.
3. Owner gives reason.
4. Transition is audit logged.
5. Rollback path exists.

## Out of scope for initial supply-first launch

Do not build or prioritise:
1. full admin dashboard
2. manual trainer CRM
3. manual owner matchmaking
4. public reviews
5. owner booking system
6. trainer calendar or scheduling
7. owner payments
8. broad dog-owner marketing
9. multi-city expansion
10. automatic phase switching
11. analytics-heavy cockpit
12. unrestricted data editing
13. complex internal permissions system

## Summary

DTD initial launch is approved only when:

> The platform has enough qualified, activated, intro-ready trainer supply; records that supply clearly; exposes readiness and blockers in `/ops`; keeps dog-owner demand passive until supply is ready; and requires owner-approved Technical-Owner Mode for any public phase transition.

That is the supply-first initial launch standard.
