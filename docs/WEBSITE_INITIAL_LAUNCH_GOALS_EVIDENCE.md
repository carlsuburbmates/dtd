# Website Initial Launch Goals Evidence

## Purpose

This document defines the ideal proof and dashboard standard for the initial website launch.

It is not a technical audit.
It describes what the founder should be able to see in a clean, simple dashboard view inside the `/ops` cockpit so that each launch goal is visibly supported.

## Core rule

Every important launch goal should have visible proof.

The founder should not need to guess whether the website is working.
The dashboard view inside `/ops` should make the answer obvious.

## Evidence model

For each launch goal, the founder dashboard view inside the `/ops` cockpit should show:
1. the main number
2. the recent trend
3. the current health state
4. the next action if attention is needed

The launch setup should prefer a small number of strong signals over a large number of noisy metrics.

## Where launch evidence should come from

The launch proof model should be based on the website's own persisted data first.

The main evidence path should be:
1. website action or system action occurs
2. backend records it in product data
3. backend summaries prepare it for founder monitoring
4. `/ops` shows the business meaning of that data

This means the `/ops` cockpit should usually be reading product-backed summaries, not live third-party dashboards.

The dashboard is the top-level summary view inside the cockpit.
It is not a separate surface from `/ops`.

## Main places the owner should look for evidence

The owner should look in this order:

1. `/ops`
- the default founder-facing evidence surface and planned ops cockpit
- should contain the top-level dashboard view with summary numbers, trends, health, and next actions

2. product-backed evidence rows and investigation views
- used when the founder needs to confirm what is behind a number
- should come from persisted business records created by the product itself

3. provider tools only when deeper investigation is needed
- Stripe for provider-level billing and invoice investigation
- Resend for provider-level email delivery investigation
- Sentry for technical error investigation
- Render and Vercel for runtime and deployment investigation

## Where each kind of launch evidence should be found

1. Demand evidence
- primary source: `owner_waitlist`, `owner_waitlist_events`, `attribution_entries`, `growth_attribution`
- founder view: `/ops` demand and growth summaries

2. Intro and funnel evidence
- primary source: `match_events`, `engagements`, `intros`, `conversions`
- founder view: `/ops` throughput, engagement, intro, and outcome summaries

3. Supply evidence
- primary source: `trainers`, `submissions`, `reactivation_candidates`
- founder view: `/ops` supply health, submission summary, reactivation summary, and top-trainer visibility

4. Revenue evidence
- primary source: `intros`, `conversions`, `stripe_events`, trainer billing-profile state
- founder view: `/ops` booked, collected, at-risk, billing-state, and remediation visibility
- provider follow-up: Stripe when invoice-level or provider-level investigation is required

5. Growth evidence
- primary source: `attribution_entries`, `growth_attribution`, landing-page handoff data, and downstream intro/outcome linkage
- founder view: `/ops` growth attribution summary and cohort visibility

6. Operational health evidence
- primary source: `system_state`, `audit_log`, `source_ingestion_state`, `config_snapshots`
- founder view: `/ops` alerts, loop freshness, discovery/source-ingestion detail, and recent system actions

## Sync rule for founder evidence

The founder dashboard view inside the cockpit should use this sync rule:
1. sync into the product the provider state that affects founder decisions
2. keep specialist provider detail in the provider's own dashboard

For the initial launch this means:
1. Stripe billing state should be reflected into product records so revenue health can be seen in `/ops`
2. Resend delivery outcomes should be reflected into product records so notification health can be seen in `/ops`
3. product events and app-owned records should stay the main source for demand, funnel, supply, growth, and health reporting
4. Sentry, Render, and Vercel should remain secondary investigation surfaces, not the founder's normal reporting surface

## Export and proof rule

When the founder needs to go deeper than the top-level dashboard cards, the proof model should be simple:
1. open the supporting investigation view
2. review the row-level records behind the summary
3. export simple row-level proof if needed

The most useful proof exports for launch are:
1. owner demand rows
2. match, engagement, intro, and outcome rows
3. trainer supply and reactivation rows
4. billing and revenue-risk rows
5. alert and operations exception rows

The evidence standard should make it easy to answer both:
1. what number am I looking at?
2. where did that number come from?

## Goal 1. Lead generation and owner demand capture

The top-level dashboard view should show:
1. total owner leads
2. new owner leads in the last 24 hours
3. top suburbs by demand
4. top sources and campaigns
5. lead trend over time

The founder should be able to answer:
1. are owners arriving?
2. where are they coming from?
3. which suburbs show strongest demand?

## Goal 2. Intro generation

The top-level dashboard view should show:
1. match requests
2. connect actions
3. intros created
4. intro trend
5. drop-off between match, connect, and intro

The founder should be able to answer:
1. is demand turning into introductions?
2. where is the funnel weak?
3. is the owner path healthy?

## Goal 3. Trust and user confidence

The top-level dashboard view should show:
1. consent completion health
2. blocked or suspicious activity signals
3. trust-related alerts
4. broken-flow reports if any

The founder should be able to answer:
1. does the website look and behave safely?
2. are trust issues blocking user action?
3. is anything damaging launch confidence?

## Goal 4. Trainer acquisition

The top-level dashboard view should show:
1. new trainer submissions
2. publish / hold split
3. active trainer count
4. trainer acquisition trend

The founder should be able to answer:
1. is supply growing?
2. are enough trainers entering the system?
3. is trainer acquisition healthy enough for launch?

## Goal 5. Supply activation and recovery

The top-level dashboard view should show:
1. trainers ready for intros
2. trainers blocked by billing or profile issues
3. reactivation cases
4. recently recovered trainers

The founder should be able to answer:
1. is supply usable right now?
2. what is blocked?
3. what needs recovery attention?

## Goal 6. Revenue health

The top-level dashboard view should show:
1. revenue booked
2. revenue collected
3. revenue at risk
4. billing issues
5. retry and remediation states

The founder should be able to answer:
1. are intros producing revenue?
2. is money being collected?
3. where is revenue getting stuck?

## Goal 7. Marketing and channel quality

The top-level dashboard view should show:
1. top sources
2. top campaigns
3. top landing pages
4. waitlist joins by source
5. intros by source
6. outcome quality by source

The founder should be able to answer:
1. what marketing is working?
2. what is creating demand but not intros?
3. which channels are worth more attention?

## Goal 8. Match quality and learning

The top-level dashboard view should show:
1. engagement trend
2. conversion trend
3. suspicious or low-quality signals
4. top-performing trainers
5. quality shifts over time

The founder should be able to answer:
1. is the system getting better?
2. are good trainers being surfaced?
3. is quality holding or slipping?

## Goal 9. Solo founder simplicity

The top-level dashboard view should show:
1. a short daily summary
2. only the most important business signals
3. a clear split between healthy, warning, and urgent
4. clear next actions

The founder should be able to answer:
1. do I need to act today?
2. what matters most right now?
3. can I understand the state of the business in a few minutes?

## Goal 10. Safe operational visibility

The top-level dashboard view should show:
1. alerts
2. stale or broken system areas
3. blocked commercial or supply paths
4. urgent follow-up areas

The founder should be able to answer:
1. is anything broken?
2. is anything at risk?
3. what needs attention first?

## Recommended top-level dashboard layout

The ideal launch ops cockpit should have a top-level dashboard view with this structure:

1. Top row
- owner leads
- intros
- active trainers
- revenue booked
- revenue at risk

2. Demand section
- lead trend
- top suburbs
- top channels

3. Conversion section
- match to intro funnel
- connect trend
- outcome trend

4. Supply section
- trainer submissions
- intro-ready trainers
- blocked trainers
- reactivation queue

5. Revenue section
- booked vs collected
- at-risk revenue
- billing issues

6. Alerts section
- urgent issues
- warnings
- what changed today

7. Action section
- do now
- watch
- no action needed

## Simplicity rule

This evidence standard should stay simple enough for one founder.

That means:
1. one main ops cockpit with one clear dashboard view at the top
2. visually clear numbers
3. obvious trends
4. obvious alerts
5. obvious next steps

It should not require deep technical knowledge to understand.

## Summary

The ideal launch proof model is simple:
1. each goal should have a visible number
2. each number should have a visible trend
3. each trend should have a visible health state
4. each warning should have a clear next action

That is the standard the project should deliver for a one-man launch ops cockpit, with the dashboard as its top-level view.
