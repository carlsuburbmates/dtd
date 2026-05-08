# Workflow Gap Review

Date: 2026-05-08

## Purpose

Review the documented workflow model against the stated product goal of an autonomous website with:

1. demand capture,
2. supply acquisition and onboarding,
3. intro-first monetisation,
4. automation-first operations.

This review uses current repo docs and public trainer-facing surfaces as the source of truth.

## Inputs reviewed

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/WORKFLOW_TRACE_SHEET.md`
3. `/Users/carlg/Documents/AI-Coding/dtd/docs/ARCHITECTURE.md`
4. `/Users/carlg/Documents/AI-Coding/dtd/docs/governance/ROADMAP.md`
5. `/Users/carlg/Documents/AI-Coding/dtd/docs/OPERATIONS.md`
6. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Trainers.jsx`
7. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Submit.jsx`
8. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Pricing.jsx`
9. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/About.jsx`

## Result first

The current workflow model is strong for matching, trust, and autonomous operations, but incomplete as a full business system.

The main gaps are:

1. marketing is missing as a workflow family,
2. trainer onboarding stops at submission instead of covering activation and recovery,
3. monetisation is documented as billing mechanics, not as a full revenue lifecycle,
4. the roadmap's website-complete claim is true for routes, but easy to misread as workflow-complete.

## Current-state findings

### 1. "Acquisition" is mislabeled

`W1` is labeled "core acquisition flow" even though it begins after the owner has already arrived on the site and decided to engage. `W6` is also grouped under `Acquisition`, but it is a trainer information/intent page, not a true acquisition engine.

Evidence:

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:15`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:69`
3. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:165`

Impact:

The docs overstate demand-generation completeness. The website currently models on-site conversion, not traffic acquisition.

### 2. Marketing workflows are absent

There is no documented workflow for:

1. traffic acquisition,
2. source attribution,
3. SEO landing-page generation as a growth engine,
4. remarketing or nurture,
5. referral or partner loops,
6. conversion optimization experiments.

`seo_pages` exists in the architecture and `/melbourne/:suburb` exists in the frontend, but that capability is not represented as a workflow in the catalog.

Evidence:

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/ARCHITECTURE.md:90`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:13`
3. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/About.jsx:15`

Impact:

The product can react to demand, but the documented autonomous system does not explain how demand is created or expanded.

### 3. Trainer onboarding is only partially modeled

The current trainer journey is effectively:

1. read `/trainers`,
2. submit on `/submit`,
3. get auto-published or held,
4. receive intros.

That is not a complete onboarding lifecycle. Missing states include:

1. held-listing recovery,
2. unverified-to-verified improvement,
3. billing-profile completion or repair,
4. publication confirmation and first-intro activation,
5. listing enrichment after initial submission,
6. inactivity or failed-billing reactivation.

Evidence:

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:69`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:78`
3. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:92`
4. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Trainers.jsx:28`
5. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Submit.jsx:42`
6. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Submit.jsx:123`

Impact:

The site promises fast onboarding, but the workflow docs stop at submission and passive billing. That is insufficient for an autonomous trainer marketplace.

### 4. Monetisation is modeled as transport, not lifecycle

The architecture clearly defines intro-first charging and Stripe reconciliation, but the workflow layer only exposes a narrow passive billing path. The current model does not fully describe:

1. billing readiness,
2. invoice delivery success/failure branches,
3. retry and recovery policy,
4. payment-failed consequences,
5. revenue suppression causes,
6. progression from `track_only` conversion mode to bill-mode,
7. refund/dispute handling as business workflows.

Evidence:

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/ARCHITECTURE.md:7`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/ARCHITECTURE.md:34`
3. `/Users/carlg/Documents/AI-Coding/dtd/docs/WORKFLOW_TRACE_SHEET.md:22`
4. `/Users/carlg/Documents/AI-Coding/dtd/docs/OPERATIONS.md:11`
5. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Pricing.jsx:15`

Impact:

The platform has commercial plumbing, but not a complete documented revenue-operating model.

### 5. The roadmap's website-complete status is narrower than it sounds

The roadmap marks website completion as done based on routes, CTAs, and build verification. That is valid as a frontend completeness statement, but not as evidence that the business workflow system is complete.

Evidence:

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/governance/ROADMAP.md:94`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/governance/ROADMAP.md:122`

Impact:

This creates a documentation trap: UI completeness can be mistaken for operating-model completeness.

## Keep / modify / create / delete

### Keep

Keep these workflows as the core of the autonomous platform:

1. `W1-W5` owner-side match, connect, engagement, outcome, and follow-up
2. `W9-W14` oversight, discovery intake, and autonomy loops

These are directionally correct and already grounded in implemented system behavior.

### Modify

1. Modify `W1` from "core acquisition flow" to "core demand-capture flow".
2. Modify `W6` from trainer education only to trainer acquisition and qualification entry.
3. Modify `W7` from submission-only to submission plus onboarding decision and activation.
4. Modify `W8` from passive billing to active revenue lifecycle.
5. Modify the scope map so `Acquisition` is not used for post-arrival flows.
6. Modify execution-readiness wording so "artifact complete" does not imply business-workflow complete.

### Create

Create these missing workflow families:

1. `W15. Demand acquisition and attribution`
Description: traffic source -> landing page -> CTA -> attributed match request.

2. `W16. Programmatic SEO and nurture loop`
Description: suburb/category page generation -> entry capture -> remarketing or follow-up CTA paths.

3. `W17. Trainer onboarding completion and activation`
Description: submission result -> billing readiness -> profile completion -> live confirmation -> first intro readiness.

4. `W18. Revenue recovery and billing remediation`
Description: invoice sent -> paid/failed/unconfigured/profile-incomplete -> retry, notify, suppress, or reactivate.

5. `W19. Trainer reactivation and retention`
Description: low-activity or failed-billing trainer -> notify -> repair listing/billing -> restore intro eligibility.

### Delete or replace

1. Delete the current `Acquisition: W1, W6` grouping and replace it with:
   - `Demand capture`: W1
   - `Supply capture`: W6
   - `Demand generation`: W15-W16
2. Delete the word `Passive` from `W8`; monetisation is not passive from the platform's point of view.

## Proposed target-state workflow map

### Demand side

1. `W15` Demand acquisition and attribution
2. `W16` Programmatic SEO and nurture loop
3. `W1` Match request
4. `W2` Connect to trainer
5. `W3` Post-connect engagement
6. `W4` Outcome confirmation
7. `W5` T+7 follow-up

### Supply side

1. `W6` Trainer acquisition landing
2. `W7` Submission, decision, and publish path
3. `W17` Onboarding completion and activation
4. `W19` Trainer reactivation and retention
5. `W11` External discovery contribution
6. `W13` Verification and discovery ingestion

### Revenue side

1. `W8` Intro and conversion monetisation lifecycle
2. `W18` Revenue recovery and billing remediation
3. `W12` Pricing adaptation

### Trust and platform operations

1. `W9` Oversight authentication
2. `W10` Continuous oversight monitoring
3. `W14` Conversion inference, outreach, and health protection

## Architectural review

### What is architecturally sound

1. The autonomous-core design is coherent: signal-driven ranking, pricing, discovery, outreach, and health loops all reinforce the product.
2. The site correctly avoids paid-placement distortion and keeps trust tied to outcomes.
3. Read-only oversight is consistent with the one-man, low-mutation operating model.

### What is architecturally weak

1. Growth is under-modeled relative to trust and operations.
2. Supply onboarding has no explicit recovery states.
3. Revenue operations are treated as side effects instead of a first-class bounded workflow area.
4. The documentation taxonomy mixes user lifecycle stages with technical implementation state.

### Architectural impact

Impact of fixing these gaps: `medium`

Reason:

The codebase does not need a large redesign to support the missing workflow docs, but the documentation model does need a more complete operating taxonomy. Without that change, the autonomous-website story remains operationally incomplete even if the backend keeps functioning.

## Recommended next actions

1. Update `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md` to add `W15-W19` and reclassify `W1`, `W6`, and `W8`.
2. Update `/Users/carlg/Documents/AI-Coding/dtd/docs/WORKFLOW_TRACE_SHEET.md` with placeholder rows for new workflows, marking them `missing` or `planned` until implemented.
3. Tighten `/Users/carlg/Documents/AI-Coding/dtd/docs/governance/ROADMAP.md` so website completion is explicitly scoped to IA/routes/UX, not full business workflow completeness.
