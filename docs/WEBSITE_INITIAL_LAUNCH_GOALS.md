# Website Initial Launch Goals

## Purpose

This document defines the ideal initial launch goals for the Bark&Bond website.

It describes the setup the project should deliver for a simple one-man launch.
It is written to be clear, visual, and easy to turn into product and dashboard work.

## Launch model

The website launch should be built around a simple model:
1. attract owner demand
2. convert owner demand into intros
3. attract and activate trainer supply
4. measure what is working
5. let one founder monitor the business from one clear ops cockpit

The website should feel like a guided marketplace system, not a generic directory and not a complicated admin tool.

## Goal 1. Capture owner demand

The website should make it easy for dog owners to raise their hand.

This means:
1. the home page should give owners one clear action
2. the action should work in both waitlist mode and matching mode
3. owner interest should be captured with clear suburb and source context
4. the owner should receive a clear success outcome

Why it matters:
1. no demand means no business
2. the launch needs real signal from real owners
3. the founder should be able to see where owner demand is coming from

## Goal 2. Turn owner intent into intros

The website should move beyond lead capture and create trainer introductions.

This means:
1. one owner input should lead to best-fit trainer options
2. the owner should be able to review trainers with low friction
3. the connect flow should feel direct and clear
4. contact release should happen only after the required trust and consent steps

Why it matters:
1. intros are the core marketplace action
2. the site should produce outcomes, not just traffic
3. the business model depends on turning intent into contact events

## Goal 3. Build trust quickly

The website should help owners feel safe enough to act.

This means:
1. the value proposition should be easy to understand
2. trust, pricing, FAQ, contact, privacy, and terms should be easy to find
3. the connect flow should feel protected and deliberate
4. the platform should clearly look like a guided and verified system, not an open listings board

Why it matters:
1. owner action depends on trust
2. trainer quality depends on trust
3. launch credibility depends on trust

## Goal 4. Acquire trainer supply

The website should attract trainers who want leads and can serve demand.

This means:
1. the trainer value proposition should be simple and compelling
2. trainers should understand the intro-first commercial model
3. trainer submission should be easy to complete
4. qualified trainers should be able to enter the live supply pool quickly

Why it matters:
1. demand without supply fails the marketplace
2. launch quality depends on enough usable trainers being available
3. the founder should not need to manually source every trainer

## Goal 5. Keep trainer supply usable

The website should not stop at trainer signup.

This means:
1. trainer activation should be clear
2. billing blockers should have a simple remediation path
3. inactive or blocked trainers should have a recovery path
4. the founder should be able to see supply health at a glance

Why it matters:
1. supply quality decays if it is not maintained
2. a usable marketplace depends on active trainers, not just submissions
3. launch reliability depends on recovering blocked supply quickly

## Goal 6. Support intro-first monetization

The website should support the business model without damaging the user journey.

This means:
1. intros should be the main commercial event
2. pricing should be clear enough for the founder to monitor
3. billing should not break the owner experience
4. at-risk revenue should be visible

Why it matters:
1. launch should validate the economic model early
2. monetization should feel connected to real value delivered
3. the founder should be able to understand revenue health without technical digging

## Goal 7. Show what marketing is working

The website should make acquisition measurable.

This means:
1. the founder should be able to see where traffic comes from
2. the founder should be able to see which campaigns produce demand
3. the founder should be able to see which channels lead to intros and outcomes
4. the system should preserve source context from entry through the funnel

Why it matters:
1. launch marketing should be judged by outcomes, not vanity traffic
2. the founder should know what to keep, stop, or improve
3. growth should be visible without needing an analytics team

## Goal 8. Improve quality over time

The website should become more useful as real usage happens.

This means:
1. the system should learn from engagement and outcomes
2. good trainers should become easier to surface
3. weak or stale supply should be corrected over time
4. follow-up and re-engagement should help recover missing outcome signal

Why it matters:
1. launch quality should improve with real use
2. better matching supports both owner trust and revenue quality
3. the product should get smarter without manual constant tuning

## Goal 9. Stay simple for a one-man operation

The website should be operable by one founder without a heavy internal process.

This means:
1. the operating model should stay simple
2. the founder should not need multiple back-office systems to understand the business
3. routine monitoring should be lightweight
4. the product should automate as much recurring work as possible

Why it matters:
1. complexity kills solo execution
2. the launch setup should reduce founder overhead, not add to it
3. the project should support focus, not admin burden

## Goal 10. Provide one clear founder ops cockpit

The website should give the founder one clear visual ops cockpit.

The top-level dashboard view inside that cockpit should answer:
1. are owners arriving?
2. are intros happening?
3. is supply healthy?
4. is revenue healthy?
5. are there urgent issues?
6. what needs attention today?

The dashboard view should feel simple and readable.
It should not feel like a developer console.

The dashboard is not a separate product surface.
It is the top-level summary view inside the founder's `/ops` cockpit.

## Founder monitoring data model

The launch should use a simple monitoring data model for the website owner.

The core rule should be:
1. the founder dashboard inside `/ops` should read from the product's own persisted business data first
2. the website should not depend on live third-party dashboards to answer everyday business questions
3. outside providers should support the system, but should not become the founder's main day-to-day reporting surface

In practice this means:
1. MongoDB-backed product data should act as the main source of truth for dashboard numbers
2. backend summaries should prepare that data for `/ops`
3. the founder should be able to monitor the business from the `/ops` cockpit first, and only go to provider tools when deeper technical or provider-specific investigation is needed

## Where the founder should find launch data

The founder should be able to find most launch monitoring data in these places:

1. `/ops`
- the main founder monitoring surface and the planned ops cockpit
- should contain the top-level dashboard view of demand, intros, supply, revenue, alerts, growth, and what needs attention now

2. backend persisted product data
- this is where the real business evidence should live
- the dashboard should be derived from records created by the website's own flows and loops

3. linked specialist/provider surfaces when needed
- Stripe for billing-provider detail
- Resend for email-provider detail
- Sentry for debugging detail
- Render and Vercel for runtime or deployment detail

Those linked tools should support investigation.
They should not be the normal first place the founder has to look.

## How launch data should sync into owner monitoring

The launch should prefer a simple sync model:
1. owner and trainer actions happen in the website
2. the backend records them into product collections
3. autonomous loops update business and health state over time
4. `/ops` reads backend summaries from those persisted records

The main monitoring path should therefore be:
1. website action
2. backend record
3. summary or state update
4. founder dashboard view inside the ops cockpit

This is important because it keeps the founder dashboard inside the ops cockpit:
1. fast
2. stable
3. readable
4. independent from needing many provider dashboards open at once

## Main launch data sources the dashboard should rely on

The founder dashboard inside the ops cockpit should primarily rely on product data such as:
1. owner waitlist records
2. owner waitlist events
3. attribution entries
4. growth attribution summaries
5. match events
6. engagements
7. intros
8. conversions
9. trainers and submissions
10. reactivation candidates
11. pricing state
12. system state
13. audit log
14. source-ingestion state

This means the dashboard view should mostly reflect what the website itself knows happened.

## Provider data rule for the initial launch

External provider data should be used in a bounded way.

The launch should treat provider data like this:
1. Stripe should supply billing and collection state that matters to revenue visibility
2. Resend should supply delivery and outreach state that matters to notification health
3. PostHog may help with deeper analytics, but the founder dashboard view should not require full analytics-tool usage for routine decisions
4. Sentry, Render, and Vercel should stay as specialist investigation tools for technical-owner use
5. Clerk should not be treated as a required dependency for the founder cockpit at launch

## Founder-friendly reporting rule

The founder should be able to answer most launch questions from:
1. `/ops` summary cards and top-level dashboard view
2. simple dashboard sections
3. supporting investigation views
4. exportable row-level proof when needed

The founder should not need to:
1. query the database manually for normal monitoring
2. cross-check five different provider dashboards for routine daily understanding
3. interpret raw engineering telemetry just to know whether the launch is healthy

## Dashboard sections the cockpit should support

The founder ops cockpit should include a top-level dashboard view with these sections:

1. Demand
- owner leads
- waitlist volume
- demand by suburb
- demand trend

2. Conversion
- matches
- connects
- intros
- outcomes

3. Supply
- new trainers
- active trainers
- blocked trainers
- reactivation needs

4. Revenue
- booked
- collected
- at risk
- billing issues

5. Growth
- top channels
- top campaigns
- top landing pages
- source-to-intro quality

6. Alerts
- stale loops
- broken flows
- unusual drops
- urgent follow-up items

7. Today
- what changed
- what matters now
- what needs action next

## Simplicity rule

The initial launch setup should avoid unnecessary complexity.

This means:
1. one founder ops cockpit, not many internal tools
2. simple business signals, not analytics overload
3. bounded actions, not a giant admin panel
4. clear next steps, not technical noise

## Summary

The ideal initial website launch should do four big things well:
1. bring in demand
2. create intros
3. keep supply and revenue healthy
4. let one founder understand the whole business from one ops cockpit, with one clear dashboard view at the top

That is the standard the project should be built to deliver.
