# SSOT

## Purpose

This document is the canonical blueprint for the website, platform, runtime model, operator model, and launch operating standard.

It defines what the system is supposed to be.
It does not describe whether those requirements are already satisfied.

## Authority And Alignment

This document is the canonical Standards Set authority for product definition, launch sequencing, launch gating, and operating model boundaries.

Companion launch documents may define phase-specific goals and evidence expectations, but they must conform to this Standards Set.

Key aligned companion documents are:
1. `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`
2. `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`
3. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`

If a companion launch document conflicts with this Standards Set, this Standards Set governs.

## Product Definition

`DTD` / `Dog Trainers Directory` is a dog-training match-and-intro platform for Greater Melbourne.

The product promise is:
1. one owner input
2. best trainer matches
3. explicit consent before contact release
4. intro-first commercial model
5. automation-first operations with bounded human oversight

The platform is not a generic directory.
It is a guided demand-routing system with trainer acquisition, trainer activation, intro metering, outcome tracking, and oversight.

The mature product promise remains owner-to-trainer matching.
However, initial launch sequencing is supply-first.

This means the standard must preserve both truths:
1. the end-state product is a guided owner-to-trainer match platform
2. the initial launch must first prove trainer supply readiness, data sufficiency, and operating readiness before broader dog-owner live matching is publicly emphasized

## Initial Launch Sequencing Standard

The initial launch standard is supply-first.

Rules:
1. the initial launch must prioritize trainer acquisition, trainer activation, and supply readiness
2. dog-owner demand may remain passive through education-first content and waitlist capture during the supply-first phase
3. public live matching exposure must remain gated until supply readiness is proven and explicitly approved
4. trainer onboarding must remain available during supply-first launch even when public live matching is gated
5. the mature product promise remains valid, but launch sequencing must not be treated as demand-first by default
6. the supply-first prelaunch is a 30-day evidence-gathering window starting from the date the owner explicitly declares launch start
7. no hard trainer-count or intro-ready-count cap is required before that 30-day window begins
8. the output of the prelaunch window is an owner review of product-backed evidence and a recorded next-step decision
9. the prelaunch geography scope is Greater Melbourne

## Target User Types

1. Dog owner
2. Trainer / business submitter
3. Oversight operator
4. External contributor / ecosystem actor
5. Autonomous system actor

`Oversight operator` is the human operating actor.
In the single-owner model, the same person also acts in `technical-owner mode` when an action crosses the hard boundary rule.
This does not create a separate product user type.

## Actor-To-Workflow Map

The canonical actor-to-workflow mapping must be:

1. Dog owner
- owner waitlist capture
- live owner matching
- trainer-detail contact release
- post-connect engagement capture
- explicit outcome confirmation
- T+7 follow-up response

2. Trainer / business submitter
- trainer acquisition path
- trainer submission
- automated publish-or-hold decision
- trainer activation readiness
- trainer billing remediation
- trainer reactivation

3. Oversight operator
- passcode-gated oversight authentication
- continuous oversight monitoring
- monitor / investigate / escalate operating decisions
- same-owner transition into `technical-owner mode` for runtime, provider, infrastructure, or policy intervention

4. External contributor / ecosystem actor
- discovery queue contribution

5. Autonomous system actor
- ranking and pricing adaptation
- verification and discovery ingestion
- conversion inference, outreach, and health protection

## Product Modes

### Home-entry modes

The public home entry must support exactly two modes:

1. Waitlist mode
- the owner-facing home surface captures demand through an owner waitlist flow
- direct public matching is not the primary home path

2. Matching mode
- the owner-facing home surface runs the live matching flow
- ranked results are returned from the owner problem input

Mode selection must be explicit, runtime-controlled, and consistent across backend, frontend, tests, and public copy.

`PUBLIC_MATCHING_ENABLED` remains the live matching exposure control.
Home-entry mode must remain separate from launch phase.

### Launch phases

The website and operating model must support a separate launch-phase concept for public emphasis.

Canonical launch phases are:
1. `supply_first`
2. `owner_waitlist`
3. `live_matching`
4. `growth`

Launch phase must be represented through `PUBLIC_LAUNCH_PHASE` or equivalent persisted phase state.
The standard requires a distinct launch-phase concept, but does not require a specific implementation mechanism when an equivalent persisted or config-backed phase mechanism already exists.

Rules:
1. launch phase must remain separate from `PUBLIC_MATCHING_ENABLED`
2. launch phase controls public emphasis, not merely route existence
3. phase changes affecting public exposure or production behavior require explicit owner approval in `technical-owner mode`
4. normal phase visibility belongs in `/ops`
5. automatic phase switching is forbidden

## Core Product Surfaces

### Public website surfaces

The public website must contain:
1. `/`
2. `/how-it-works`
3. `/about`
4. `/pricing`
5. `/trust`
6. `/faq`
7. `/contact`
8. `/privacy`
9. `/terms`
10. `/trainers`
11. `/submit`
12. `/t/:id` as the canonical trainer-detail route
13. `/trainers/:id` as a compatibility alias to the trainer-detail route
14. `/lp/:campaign`
15. `/melbourne/:suburb`
16. `/follow-up/:token`
17. `/submit/status/:submissionId`
18. `/trainer/billing`
19. `/trainer/reactivate`

### Protected oversight surface

The protected oversight website must contain:
1. `/ops`

`/ops` is a passcode-gated oversight route, not a public user-marketing route.

### Canonical support path

The canonical support/contact path must be:
1. route: `/contact`
2. mailbox: `info@dogtrainersdirectory.com.au`

The project may change that mailbox later, but docs and code must be updated together.

### Legacy/admin rule

There must be no legacy admin CRUD control surface presented as an active operational requirement.

If legacy routes exist for compatibility, they must not define the operating model.

## Core Business Workflows

The platform standard must include the following workflow families:

### Demand

1. owner waitlist capture
2. live owner matching
3. trainer-detail contact release
4. post-connect engagement capture
5. explicit outcome confirmation
6. T+7 follow-up for unresolved outcomes

### Supply

1. trainer information page and acquisition path
2. trainer submission
3. automated publish-or-hold decision
4. trainer activation readiness state
5. trainer billing remediation
6. trainer reactivation

### Revenue

1. intro metering
2. intro billing collection
3. billing webhook reconciliation
4. billing recovery and retry handling
5. explicit non-billable and at-risk classification

### Growth

1. attribution capture
2. campaign landing capture
3. SEO landing capture
4. nurture cohort generation

### Oversight

1. passcode-gated oversight console with Normal Ops defaults
2. loop freshness visibility
3. billing and revenue visibility
4. alerts and health state visibility
5. investigation queue visibility
6. source-ingestion visibility
7. growth attribution visibility
8. reactivation visibility
9. launch phase and readiness visibility

### Autonomous runtime

1. ranking loop
2. pricing loop
3. verification loop
4. discovery queue processing loop
5. inferred conversion promotion loop
6. source ingestion loop
7. outreach loop
8. billing recovery loop
9. nurture loop
10. reactivation routing loop
11. health loop

## Commercial Model

The default commercial model must be intro-first.

Rules:
1. contact release is tied to intro creation
2. intro billing is invoice-based when payment configuration is present
3. conversion tracking must be available independently from conversion billing
4. launch baseline must allow a non-bill conversion tracking mode
5. billing, retry, dispute, refund, waived, and non-billable states must be explicitly represented

## Trust, Verification, And Ranking Model

The platform must use a deterministic runtime decision model.

Requirements:
1. no runtime dependency on an external LLM for matching or verification
2. trainer verification must be confidence-based
3. ranking must incorporate performance and outcome signals
4. fraud suppression must exist at intro level
5. inferred conversions must be delayed and threshold-controlled

## Oversight Model

The oversight model must be Normal Ops by default.

Requirements:
1. `/ops` is an observation and triage surface by default
2. `/ops` may persist bounded Layer 1 review state, owner note, and audit history during Normal Ops
3. `/ops` must not directly mutate locked runtime policy during Normal Ops
4. any future Owner Override actions surfaced from `/ops` must stay within reversible, bounded, reason-captured, audit-logged, policy-safe workflows
5. any policy-altering, launch-phase-altering, public-exposure-altering, direct-data, provider, deployment, or infrastructure action is reserved to the same owner acting in `technical-owner mode`
6. `/ops` must not drift into unrestricted admin CRUD, manual trainer matching, or manual routine billing

## Operating Model

The operating model is single-owner and mode-based.

Rules:
1. `Monitor`, `Investigate`, and `Escalate` are operating modes, not separate departments
2. `Oversight operator` and `technical-owner` refer to the same single human owner operating in different modes
3. the default operator path must be non-technical for routine monitoring
4. `technical-owner mode` must be explicit for runtime, provider, policy, launch phase, public matching exposure, billing policy, pricing policy, or direct-data intervention
5. the support mailbox must be singular and canonical across operator-facing flows

## Runtime Topology Standard

The runtime must support exactly one active loop owner at a time.

Requirements:
1. loop ownership is explicit
2. lease protection exists to prevent duplicate active owners
3. loop ownership may reside in API or worker runtime
4. ownership topology must be environment-controlled and inspectable

## Data Model Standard

The system must persist at least the following logical entities:
1. trainers
2. submissions
3. intros
4. engagements
5. conversions
6. match events
7. discovery queue
8. outreach events
9. pricing state
10. system state
11. stripe events
12. audit log
13. owner waitlist
14. owner waitlist events
15. attribution entries
16. growth attribution
17. reactivation candidates
18. SEO pages
19. source-ingestion state
20. auth attempts
21. config snapshots
22. launch phase state or equivalent persisted phase state
23. phase readiness snapshots
24. phase transition decisions

## Launch Evidence And Data Sufficiency Standard

The launch standard requires product-backed data sufficiency from day one.

Core rule:
1. `Database = truth`
2. `/ops = readable operating view`
3. `audit_log = decision trail`
4. `CSV/export = proof only`

Rules:
1. launch readiness must be judged from product-backed records, not spreadsheet reconstruction
2. CSV and export artifacts may support proof, but must not become the operating source of truth
3. readiness recommendations and launch decisions must be traceable to persisted records and audit history

## Security Standard

The launch security baseline must include:
1. protection for oversight access
2. lockout or rate-limiting for repeated auth failure
3. tokenized protection for trainer lifecycle actions
4. explicit consent checkpoints before contact release and submission publication flows
5. webhook idempotency protection
6. intro idempotency protection
7. secret handling outside git

The platform standard assumes stronger operator identity can be added later, but launch quality still requires explicit protective controls at the current auth layer.

## Observability Standard

The platform must expose a unified oversight truth surface.

The oversight truth surface must show:
1. loop freshness
2. alerts
3. health state
4. revenue booked
5. revenue collected
6. revenue at risk
7. billing lifecycle state
8. notification summary
9. growth attribution summary
10. reactivation summary
11. source-ingestion state
12. recent system actions
13. current launch phase
14. public matching exposure state
15. supply readiness
16. intro-ready trainer count or equivalent supply-readiness signal
17. blocked trainer count or equivalent supply-blocker signal
18. readiness recommendation
19. blockers to next phase

## Deployment Standard

The deployment standard must support:
1. local runnable environment
2. production frontend hosting
3. production backend hosting
4. explicit loop-owner runtime configuration
5. custom domain and TLS
6. environment-variable based runtime configuration
7. repeatable deployment and redeployment procedure

## Quality Standard

The platform standard requires:
1. backend compile/import sanity
2. backend tests for critical billing, auth, loop, and public-mode behavior
3. frontend tests for critical helpers and user flows
4. frontend production build pass
5. consistency between the canonical implementation pack, runtime/code audit support docs, and runtime behavior

## Non-Goals

This standard does not require:
1. a browse-style directory as the primary product
2. a traditional admin CRUD console
3. runtime LLM dependence
4. multi-team enterprise operating structure
5. feature sprawl beyond the defined workflows above
6. a demand-first initial launch posture
7. unrestricted admin-dashboard expansion inside `/ops`
8. manual trainer matching as routine operation
9. manual routine billing as routine operation
10. automatic phase switching
11. automatic enabling of `PUBLIC_MATCHING_ENABLED`
12. CSV/export files as the primary operating record
