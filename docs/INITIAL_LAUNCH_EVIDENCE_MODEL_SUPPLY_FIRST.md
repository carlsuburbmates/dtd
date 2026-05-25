# Initial Launch Evidence Model - Supply-First

## Purpose

This document defines the proof model for DTD's supply-first initial launch.

It explains what evidence the founder should be able to see in `/ops`, supporting investigation views, and proof exports during the 30-day supply-first prelaunch evidence window.

This is not a technical audit.
It is the evidence standard for a supply-first launch.

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

## Core rule

Evidence must make the 30-day supply-first prelaunch readable first.

The founder should not need to guess what happened during prelaunch, where supply formed, what blocked activation, or what should happen next.
The evidence model should make that answer visible.

This evidence window does not require a hard trainer-count cap or intro-ready-count cap before prelaunch begins.
Those later decisions can be made from the recorded evidence.

## Core evidence model

For each important launch goal, the founder-facing evidence surface should show:
1. the main number
2. the recent trend
3. the current health state
4. the next action if attention is needed

The next action section must be exception-driven only.
Normal automated events should remain metrics, not founder tasks.

## Source-of-truth rule

```text
Database = truth
/ops = readable operating view
audit_log = decision trail
CSV/export = proof only
```

CSV and export files are proof artifacts only.
They must not become the operating source of truth.

## Where evidence should come from

The evidence model should be based on product-backed persisted data first.

The normal path should be:
1. website action or system action occurs
2. backend records it in product data
3. backend summaries prepare it for founder monitoring
4. `/ops` shows the business meaning of that data

This means `/ops` should usually read product-backed summaries, not depend on live provider dashboards.

## Role of `/ops`

`/ops` is the default founder-facing evidence surface.
`/ops` is Normal Ops by default.

The dashboard is the top-level summary view inside the `/ops` cockpit.
It is not a separate product.
It is not the launch goal itself.
It is the readable evidence surface for launch goals.

## Evidence priority for supply-first launch

The evidence model must prioritise:
1. trainer submissions
2. intro-ready trainers
3. blocked trainers
4. activation blockers
5. billing readiness
6. reactivation candidates
7. supply by target geography
8. current launch phase
9. readiness status
10. blockers to next phase

Passive owner demand evidence is still useful, but secondary.

## Main places the owner should look for evidence

The owner should look in this order:

1. `/ops`
- top-level summary view
- readiness and blockers
- supply, revenue, loop, and alert visibility

2. product-backed investigation views and evidence rows
- used to confirm what is behind a number
- used to inspect blockers and case detail

3. provider tools only when deeper investigation is required
- Stripe for provider-level billing detail
- Resend for provider-level delivery detail
- Sentry for technical diagnostics
- Render and Vercel for runtime and deployment diagnostics

## Required evidence categories

### 1. Supply evidence

Primary source:
1. `submissions`
2. `trainers`
3. trainer activation state
4. trainer billing readiness
5. trainer remediation state
6. `reactivation_candidates`

Founder view:
1. trainer acquisition trend
2. publish and hold split
3. intro-ready trainers
4. blocked trainers
5. blocker reasons
6. recovered and reactivated supply
7. supply by target geography or suburb when available

### 2. Passive owner demand evidence

Primary source:
1. `owner_waitlist`
2. `owner_waitlist_events`
3. `attribution_entries`
4. `growth_attribution`

Founder view:
1. passive waitlist entries
2. suburb demand
3. source and campaign attribution
4. duplicate and rejected waitlist events
5. demand trend over time

### 3. Intro-path readiness evidence

Primary source:
1. `match_events`
2. `intros`
3. `engagements`
4. `conversions`
5. outreach and follow-up records where relevant

Founder view:
1. credible ranked results exist
2. connect flow works
3. intro record creation works
4. contact reveal works after valid intro creation
5. engagement capture exists
6. follow-up and outcome path exists

This evidence proves technical readiness for the path without requiring broad public owner launch.

### 4. Revenue-readiness evidence

Primary source:
1. `intros`
2. `conversions`
3. `stripe_events`
4. trainer billing-profile state

Founder view:
1. revenue booked
2. revenue collected
3. revenue at risk
4. trial-free intros
5. billable vs non-billable states
6. retry and remediation states
7. billing blocker visibility

### 5. Operational health evidence

Primary source:
1. `system_state`
2. `audit_log`
3. `source_ingestion_state`
4. `config_snapshots`

Founder view:
1. loop health
2. alerts
3. unresolved high-severity issues
4. discovery and source-ingestion health
5. recent system actions
6. current blockers to next phase

## Phase evidence

Phase evidence must exist explicitly.

Required records:
1. `launch_phase_state`
2. `phase_readiness_snapshots`
3. `phase_transition_decisions`

### `launch_phase_state` must prove

1. current phase
2. public matching enabled or disabled
3. trainer onboarding enabled or disabled
4. owner waitlist enabled or disabled
5. current public emphasis
6. who changed it
7. when it changed
8. why it changed
9. which audit record supports it

### `phase_readiness_snapshots` must prove

1. current phase
2. readiness status
3. trainer supply count
4. intro-ready trainer count
5. blocked trainer count
6. billing blocker count
7. activation blocker count
8. unresolved high-severity alerts
9. loop health
10. source-ingestion health
11. recommended next phase
12. blockers
13. evidence timestamp

### `phase_transition_decisions` must prove

1. from phase
2. to phase
3. decision: approved, rejected, or deferred
4. decision maker
5. reason
6. evidence snapshot reference
7. timestamp
8. rollback note if relevant
9. related audit trail

## Sync rule for founder evidence

Use this sync rule:
1. sync into product data the provider state that affects founder decisions
2. keep specialist provider detail in provider dashboards

For the supply-first launch this means:
1. Stripe billing state should be reflected into product records so revenue readiness can be seen in `/ops`
2. Resend delivery outcomes should be reflected into product records so notification and outreach health can be seen in `/ops`
3. app-owned records should remain the main source for supply, passive demand, intro readiness, and operational reporting
4. provider tools should remain secondary investigation surfaces

## Goal-by-goal evidence model

## Goal 1. Attract trainer supply

The top-level dashboard view should show:
1. new trainer submissions
2. submission trend
3. publish and hold split
4. active trainer count
5. supply by target geography if available

The founder should be able to answer:
1. are trainers arriving?
2. are the right trainers arriving?
3. is trainer acquisition building usable supply?

## Goal 2. Activate usable trainer supply

The top-level dashboard view should show:
1. intro-ready trainers
2. blocked trainers
3. activation blockers
4. billing readiness
5. reactivation candidates
6. recovered or reactivated trainers

The founder should be able to answer:
1. how much supply is actually usable now?
2. what is blocked?
3. what is stopping supply from becoming intro-ready?

## Goal 3. Keep dog-owner demand passive until supply is ready

The top-level dashboard view should show:
1. passive owner waitlist entries
2. suburb demand
3. source and campaign attribution
4. duplicate and rejected waitlist events
5. current public phase and matching exposure state

The founder should be able to answer:
1. are owners arriving passively?
2. are we preserving useful demand signals without overexposing live matching?
3. is public posture still aligned with supply-first launch?

## Goal 4. Prepare the intro path without forcing owner demand

The top-level dashboard view should show:
1. testable match-to-intro readiness signal
2. connect and intro activity where exercised
3. contact reveal readiness
4. engagement capture signal
5. follow-up and outcome readiness

The founder should be able to answer:
1. is the intro path technically ready?
2. can it be trusted when live exposure is eventually approved?
3. is the system prepared without needing a broad owner launch today?

## Goal 5. Make intro-first monetisation ready

The top-level dashboard view should show:
1. revenue booked
2. revenue collected
3. revenue at risk
4. trial-free intros
5. billing issues
6. retry and remediation states

The founder should be able to answer:
1. is the intro-first commercial model ready?
2. is routine billing being handled by the system?
3. where is money getting stuck?

## Goal 6. Record enough launch data from day one

The top-level dashboard view should show:
1. current phase
2. evidence freshness
3. readiness status
4. data completeness for core launch records
5. blocker visibility

The founder should be able to answer:
1. do we have enough trustworthy product data to judge readiness?
2. are decisions backed by records rather than memory or spreadsheets?
3. can we defend the launch decision with evidence?

## Goal 7. Build one phase-aware website, not multiple rebuilds

The top-level dashboard view should show:
1. current launch phase
2. matching enabled or disabled
3. owner waitlist enabled or disabled
4. trainer onboarding enabled or disabled
5. current public emphasis

The founder should be able to answer:
1. what phase are we in now?
2. what is the public site currently emphasising?
3. can we progress phases without rebuilding the whole site?

## Goal 8. Let the system recommend phase transitions, but never silently transition

The top-level dashboard view should show:
1. readiness recommendation
2. blockers to next phase
3. current readiness snapshot
4. latest phase decision status
5. whether owner approval is still required

The founder should be able to answer:
1. what is the system recommending?
2. are we actually ready to move?
3. has any public phase transition been explicitly approved?

## Goal 9. Keep founder workload exception-only

The top-level dashboard view should show:
1. a short daily summary
2. only important exceptions
3. healthy vs warning vs urgent split
4. clear next actions only where attention is needed

The founder should be able to answer:
1. do I need to act?
2. what is genuinely exceptional?
3. what is being handled automatically already?

## Goal 10. Make `/ops` the readable operating view

The top-level dashboard view should show:
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

The founder should be able to answer:
1. is the launch healthy?
2. are we ready for broader owner exposure?
3. what needs attention first?

## Recommended top-level dashboard layout

The supply-first `/ops` cockpit should have a top-level dashboard view with this structure:

1. Top row
- trainer submissions
- intro-ready trainers
- blocked trainers
- revenue at risk
- current phase

2. Supply section
- submission trend
- publish and hold split
- supply by geography
- reactivation queue

3. Activation section
- intro-ready trainers
- billing readiness
- activation blockers
- recently recovered trainers

4. Passive demand section
- owner waitlist trend
- top suburbs
- top sources and campaigns

5. Revenue readiness section
- booked vs collected
- at-risk revenue
- billing issues
- trial-free state

6. Phase readiness section
- readiness status
- recommended next phase
- blockers to next phase
- last readiness snapshot

7. Alerts and operations section
- urgent issues
- warnings
- loop health
- what changed today

8. Action section
- do now
- watch
- no action needed

## Export and proof rule

When the founder needs to go deeper than a summary card, the proof model should be simple:
1. open the supporting investigation view
2. review the row-level records behind the summary
3. export simple row-level proof if needed

The most useful proof exports for the supply-first launch are:
1. trainer submission rows
2. trainer activation and blocker rows
3. reactivation rows
4. passive owner waitlist and attribution rows
5. match, intro, engagement, and outcome rows
6. billing and revenue-risk rows
7. phase readiness and phase decision rows
8. alert and operations exception rows

## Simplicity rule

This evidence model should stay simple enough for one founder.

That means:
1. one main `/ops` cockpit with one clear dashboard view at the top
2. visible supply readiness first
3. visible blockers second
4. passive owner demand evidence available but not dominant
5. obvious health states
6. obvious next actions only when exceptions exist

It should not require database queries, spreadsheet reconstruction, or deep technical debugging for routine launch decisions.

## Summary

The supply-first evidence standard is simple:
1. prove trainer supply readiness first
2. keep passive owner demand visible but secondary
3. show phase, readiness, and blockers explicitly
4. keep `/ops` readable and product-backed
5. keep routine events automated and founder actions exception-driven

That is the evidence model the project should use for a supply-first initial launch.
