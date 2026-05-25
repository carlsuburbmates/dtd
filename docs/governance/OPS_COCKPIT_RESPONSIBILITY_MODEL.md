# DTD Ops Cockpit Responsibility Model

**File:** `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`  
**Project:** Dog Trainers Directory / DTD  
**Purpose:** Governance model for the owner-facing `/ops` cockpit, autonomous system responsibilities, owner override boundaries, and technical-owner escalation paths.  
**Status:** Canonical governance standard  

---

## 1. Control Principle

DTD is operated by the same human owner, but responsibilities must be separated by operational risk.

> **Same human. Different danger level.**

The system should be organised into four responsibility labels:

1. **Automated System**
   - Handles routine product behaviour, recurring loops, scoring, matching, billing lifecycle, signal processing, normal remediation, and self-healing where safe.

2. **Layer 1 — Normal Ops**
   - Read-only monitoring, daily checks, triage, notes, and decisioning: `Monitor`, `Investigate`, `Escalate`.

3. **Layer 2 — Owner Override**
   - Bounded, reversible, policy-safe owner intervention from `/ops`.

4. **Layer 3 — Technical-Owner Mode**
   - Infra, runtime, config, policy, provider, deployment, legal, refund, and direct-data intervention requiring explicit escalation, reason capture, confirmation, and audit trail.

Hard boundary:

- If an action changes locked runtime policy, billing policy, launch phase/public emphasis, public matching exposure, infrastructure, provider state, direct data, or production behaviour, it is **Technical-Owner Mode**.
- If an action is reversible, bounded, and policy-safe, it may be **Owner Override**.
- If the system can handle it safely without affecting the website, public trust, money, or continuity, it should stay **Automated System**.

---

## 2. Product Entry and Launch-Phase Responsibilities

### 2.1 Public home exposure state

**Responsibility label:** Automated System

The system enforces the public entry state through `PUBLIC_MATCHING_ENABLED`.

- `PUBLIC_MATCHING_ENABLED=false`: public home shows the waitlist-first owner surface.
- `PUBLIC_MATCHING_ENABLED=true`: public home exposes live matching.
- Trainer onboarding remains open in both exposure states.

The owner should not manually swap pages, hide buttons, or edit public copy each time public exposure changes. The home page should consume config and render the correct state automatically.

### 2.2 Launch phase and exposure visibility

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show the current launch phase and public exposure state separately:

- current launch phase
- matching enabled/disabled
- current public emphasis
- trainer onboarding open
- lifecycle routes active
- supply readiness
- intro-ready trainers
- blocked trainers
- readiness recommendation
- blockers to next phase
- active region/suburb configuration where relevant

This is read-only monitoring.

### 2.3 Launch phase readiness snapshots

**Responsibility label:** Automated System for calculation, Layer 1 for review

The system should prepare phase-readiness evidence so `/ops` can show whether the current phase is healthy and whether a later phase is recommended.

`/ops` should be able to surface:

- current readiness status
- intro-ready trainer count
- blocked trainer count
- billing/activation blockers where relevant
- unresolved high-severity issues
- recommended next phase
- blockers to next phase

Normal Ops reviews this evidence but does not approve phase changes.

### 2.4 Phase transition decisions

**Responsibility label:** Layer 3 — Technical-Owner Mode

Any phase transition decision should be explicit and evidence-backed.

This includes:

- transition from `supply_first` to `owner_waitlist`
- transition from `owner_waitlist` to `live_matching`
- transition from `live_matching` to `growth`
- deferral or rejection of a proposed transition

The decision should require:

- current readiness snapshot
- reason
- confirmation
- audit trail
- rollback note where relevant

Do not treat recommendation as approval.

### 2.5 Changing public matching exposure

**Responsibility label:** Layer 3 — Technical-Owner Mode

Changing `PUBLIC_MATCHING_ENABLED` changes public product behaviour. It should require:

- explicit technical-owner mode switch
- reason
- confirmation
- audit log
- rollback note
- current config snapshot
- warning that public matching exposure will change

Do not expose this as a normal `/ops` toggle.

---

## 3. Dog Owner Lifecycle Responsibilities

### 3.1 Owner waitlist enrollment

**Responsibility label:** Automated System

When matching is gated, the system handles owner waitlist enrollment through `POST /api/owner-waitlist`, including:

- email
- suburb
- consent
- campaign/source metadata
- normalized lifecycle events such as `started`, `submitted`, `duplicate`, and `rejected`

The owner should not manually collect waitlist entries.

### 3.2 Waitlist monitoring

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show waitlist volume and trend where useful:

- total waitlist signups
- recent waitlist signups
- duplicate/rejected volume
- suburb demand concentration
- campaign/source attribution

This remains monitoring unless abnormal behaviour appears.

### 3.3 Waitlist abnormality

**Responsibility label:** Owner Override if bounded; Technical-Owner Mode if policy/config changes

Examples:

- spike in rejected waitlist submissions
- spammy duplicate pattern
- campaign attribution broken
- suburb field repeatedly malformed

Owner Override may include:

- mark reviewed
- add note
- suppress obvious spam cohort if supported and reversible
- route issue to technical-owner investigation

Technical-Owner Mode is required if fixing the issue needs:

- API validation changes
- config changes
- deployment
- DB repair
- anti-abuse policy changes

### 3.4 Owner match request

**Responsibility label:** Automated System

In live matching mode, the system handles:

- owner problem statement
- consent
- optional suburb
- `POST /api/match`
- match event creation
- return of up to 3 ranked trainer results

The owner/operator should not manually match dog owners to trainers.

### 3.5 Match quality monitoring

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should expose enough signal to know whether matching is healthy:

- match request volume
- intro conversion from matches
- connect-click signals
- engagement events
- top trainers
- ranking stability
- low/no result patterns where available

No intervention unless matching continuity or trust is at risk.

### 3.6 Match failure or result collapse

**Responsibility label:** Layer 1 → Layer 3 depending cause

Layer 1 detects and classifies:

- demand exists but engagement collapses
- zero results appear unexpectedly
- owner reports broken matching
- abnormal ranking instability

Technical-Owner Mode is required if resolution needs:

- backend logs
- algorithm changes
- config changes
- deployment
- data repair
- loop restart
- database inspection beyond safe read-only views

---

## 4. Trainer Detail, Connect, and Intro Responsibilities

### 4.1 Trainer detail page

**Responsibility label:** Automated System

Trainer detail pages should use `/t/:id` as the canonical public route, with `/trainers/:id` allowed as a compatibility alias to the same lifecycle surface:

- load trainer data
- show connect form
- enforce required fields and consents
- reveal contact details after successful connect
- track contact actions

The owner should not manually release trainer details.

### 4.2 Connect/introduction creation

**Responsibility label:** Automated System

`POST /api/intros` should:

- validate contact request and consents
- create intro record
- run fraud evaluation
- mark intro as billed, suppressed, or trial-free as appropriate
- reveal trainer contact details
- feed intro signal into ranking and billing lifecycle

### 4.3 Normal intro visibility

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show:

- intros in last 24h and 7d
- trial-free intros
- suppressed intros
- valid/billed intros
- engagement after intro
- conversion quality

No owner action is needed for normal intro flow.

### 4.4 Intro fraud suppression

**Responsibility label:** Automated System by default

The system should automatically suppress suspicious or fraud-like intros from billing and ranking influence.

Normal suppressed intros should not become owner tasks.

### 4.5 Suppressed intro spike

**Responsibility label:** Layer 1 → Owner Override → Technical-Owner Mode if persistent

Layer 1:

- identify spike
- compare against recent baseline
- inspect source/IP/trainer clustering if surfaced
- mark `Monitor`, `Investigate`, or `Escalate`

Owner Override:

- acknowledge alert
- add note
- mark reviewed
- optionally suppress or review cohort if bounded and reversible

Technical-Owner Mode:

- create or modify blocklist
- alter fraud thresholds
- inspect MongoDB manually
- patch fraud logic
- deploy changes

---

## 5. Engagement and Outcome Responsibilities

### 5.1 Contact action tracking

**Responsibility label:** Automated System

Website, phone, email, and return-visit engagement events should be recorded automatically through `POST /api/engagements`.

The owner should not manually interpret routine engagement.

### 5.2 Engagement visibility

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show engagement events and connect-click signals.

Owner monitors:

- activity collapse
- unexpected zero engagement while demand exists
- mismatch between matches and connects
- suspiciously concentrated engagement

### 5.3 Explicit outcome confirmation

**Responsibility label:** Automated System + Dog Owner

The dog owner provides the outcome through `/follow-up/:token` or a conversion API call.

The system records first confirmation and idempotently ignores repeats.

The platform owner should not manually chase every outcome.

### 5.4 T+7 follow-up outreach

**Responsibility label:** Automated System

The system should automatically send outreach after 7 days where there is no conversion signal and user email exists.

This should not be a daily owner task.

### 5.5 Failed outreach

**Responsibility label:** Automated System first; Layer 1 if threshold breached; Owner Override if resend is safe

Routine outreach failures should be logged automatically.

`/ops` should surface only:

- repeated failure
- high failure rate
- provider issue
- specific high-value follow-up failure
- backlog of unsent follow-ups

Owner Override may allow:

- resend existing follow-up
- mark reviewed
- route to support email
- add note

Technical-Owner Mode is required for:

- provider configuration
- API key/domain/authentication issues
- email template logic changes
- deployment issues

---

## 6. Conversion Inference and Ranking Responsibilities

### 6.1 Inferred conversion creation

**Responsibility label:** Automated System

The system should infer conversions from engagement signals and only promote high-confidence inferred conversions after maturity rules are satisfied.

### 6.2 Inferred pending visibility

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show inferred pending volume.

Owner action:

- monitor normal backlog
- investigate if stuck high
- escalate if inference pipeline appears stalled

### 6.3 Fast/suspicious manual conversions

**Responsibility label:** Automated System by default

Manual conversions confirmed too quickly should be tagged suspicious, stored, excluded from conversion fee charging, and excluded from ranking benefit.

The system should absorb this without owner review unless suspicious conversions spike.

### 6.4 Suspicious conversion spike

**Responsibility label:** Layer 1 → Owner Override → Technical-Owner Mode

Layer 1:

- investigate trend
- inspect trainer/source clustering if surfaced
- check recent system actions

Owner Override:

- acknowledge alert
- mark reviewed
- add note
- close/reopen case
- route to technical-owner mode

Technical-Owner Mode:

- alter fraud logic
- add blocklist
- direct DB repair
- change billing/ranking treatment
- deploy patch

---

## 7. Trainer Acquisition, Submission, and Activation Responsibilities

### 7.1 Trainer acquisition page

**Responsibility label:** Automated System + Trainer Self-Service

The `/trainers` page should explain the commercial model and route trainers to `/submit` or support email.

The owner should not manually onboard trainers by default.

### 7.2 Trainer submission

**Responsibility label:** Automated System + Trainer Self-Service

The trainer submits through `/submit`; the system scores confidence and automatically:

- publishes verified if score is high enough
- publishes unverified if score is acceptable but not verified
- holds if confidence is too low
- attempts billing profile provisioning if published

### 7.3 Submission visibility

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show high-level supply health:

- submissions
- held submissions
- publish/hold ratio
- billing readiness blockers
- confidence drift
- verification failures
- source ingestion flow into trainer supply

Normal submissions should not generate owner tasks.

### 7.4 Held submission

**Responsibility label:** Automated System by default; Layer 1 only if pattern emerges

Individual low-confidence submissions should be held automatically.

Owner should only be alerted if:

- held submissions spike
- all submissions are held
- source quality collapses
- legitimate trainers appear repeatedly blocked
- launch supply falls below threshold

Owner Override may safely:

- mark reviewed
- add note
- route trainer to support/remediation
- request profile update if supported

Technical-Owner Mode is required for:

- changing score thresholds
- changing confidence policy
- direct publish/unpublish of trainer
- editing trainer data directly
- altering verification rules

### 7.5 Trainer activation status

**Responsibility label:** Automated System + Trainer Self-Service

The `/submit/status/:submissionId` page should expose activation state and blockers.

The trainer should be able to move into `/trainer/billing`, and billing state should feed back into submission status.

### 7.6 Activation blockers

**Responsibility label:** Automated System first; Layer 1 if unresolved; Owner Override for routing

The system should detect blockers and direct trainers into remediation.

Layer 1 should monitor unresolved blocker volume.

Owner Override may:

- resend remediation notification
- route trainer to billing remediation
- route to support email
- add note
- mark case monitored/investigated/escalated

Technical-Owner Mode is required if blocker is caused by:

- Stripe/provider failure
- API issue
- broken page
- broken backend route
- database inconsistency
- policy/config mismatch

---

## 8. Billing, Collection, and Revenue Responsibilities

### 8.1 Trial-free period

**Responsibility label:** Automated System

Submission-registered trainers receive trial-free intros for the defined launch period.

The owner should monitor trial-free volume only.

### 8.2 Valid intro billing

**Responsibility label:** Automated System

After the trial-free window, valid intros should be metered and billed through Stripe invoice collection.

The owner should not manually invoice routine intros.

### 8.3 Stripe webhook reconciliation

**Responsibility label:** Automated System

Stripe events should reconcile intro billing collection status automatically.

### 8.4 Revenue oversight

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show:

- revenue booked
- revenue collected
- revenue at risk
- trial-free intros
- billing recovery states
- disputes
- retry states

### 8.5 Normal invoice sent

**Responsibility label:** Automated System + Layer 1 visibility only

`invoice_sent` should be monitored for later settlement.

No immediate owner action.

### 8.6 Paid invoice

**Responsibility label:** Automated System

Mark paid, update revenue collected, no owner action.

### 8.7 Payment failed / uncollectible

**Responsibility label:** Automated System first; Layer 1 monitor/investigate

The billing recovery loop should retry failed or uncollectible states with bounded backoff.

### 8.8 Retry sent

**Responsibility label:** Automated System + Layer 1 visibility

`retry_sent` means retry is awaiting outcome.

No manual owner action unless it stalls.

### 8.9 Retry failed

**Responsibility label:** Layer 1 — Investigate

Owner should inspect trainer billing health and retry budget.

Owner Override may:

- add note
- route trainer to billing remediation
- resend billing remediation notification if supported
- mark case investigated

### 8.10 Retry exhausted

**Responsibility label:** Layer 2 — Owner Override

Automatic retry budget is spent.

Owner should escalate and route trainer through `/trainer/billing` remediation or support.

Allowed owner actions:

- open trainer billing context
- send/remind trainer
- mark remediation required
- add note
- close only with reason
- reopen if payment later resumes

### 8.11 Needs remediation

**Responsibility label:** Layer 2 — Owner Override

When missing consent/profile/integration blocker prevents collection, the owner should route trainer to `/trainer/billing` or support email.

This should not require raw DB work.

### 8.12 Disputed payment

**Responsibility label:** Layer 2 initially; Layer 3 if refund/provider/direct-write needed

Owner Override:

- mark escalated
- add note
- open Stripe/provider link
- track dispute status
- communicate via support mailbox

Technical-Owner Mode:

- refund
- manual billing status change
- provider account intervention
- policy change

### 8.13 Refunded intro/conversion

**Responsibility label:** Layer 3 — Technical-Owner Mode

Refunding a billed intro or conversion must require:

- technical-owner mode
- reason
- confirmation
- before/after
- linked intro/conversion
- audit log
- Stripe/provider confirmation where relevant

This should not be a normal button.

### 8.14 Waived collection

**Responsibility label:** Layer 1 visibility; Layer 3 if owner creates waiver

If already waived, monitor only.

If the owner creates a waiver, that changes revenue treatment and should be technical-owner mode with audit reason.

---

## 9. Reactivation and Retention Responsibilities

### 9.1 Reactivation candidate detection

**Responsibility label:** Automated System

The reactivation routing loop should detect:

- low activity
- billing blockers
- confidence drift
- publication drift

It should create or update reactivation candidates automatically.

### 9.2 Reactivation remediation sequence

**Responsibility label:** Automated System + Trainer Self-Service

The system should trigger remediation sequence, listing refresh, billing repair, outreach, and track return-to-active outcomes.

### 9.3 Reactivation summary

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show:

- open candidates
- resolved candidates
- returned-to-active
- active-after-resolution 7d
- return-to-active rate

### 9.4 Weak return-to-active

**Responsibility label:** Layer 1 → Layer 2 → Layer 3 depending severity

Layer 1:

- monitor threshold
- investigate weak return-to-active
- escalate where recovery remains poor

Owner Override may:

- route trainer to `/trainer/reactivate`
- send/remind trainer
- add note
- mark investigated/escalated
- close/reopen case

Technical-Owner Mode is required if issue needs:

- reactivation logic change
- scoring threshold change
- billing policy change
- direct trainer data mutation
- source/pipeline repair

---

## 10. Discovery and Source Ingestion Responsibilities

### 10.1 Public discovery queue contribution

**Responsibility label:** Automated System + External Contributor

External actors can submit candidate trainer URLs through `POST /api/discovery`, which enter `discovery_queue` as pending.

### 10.2 Discovery queue processing

**Responsibility label:** Automated System

The discovery loop processes pending queue items and promotes, discards, or deduplicates trainers.

### 10.3 Source ingestion

**Responsibility label:** Automated System

Source ingestion should:

- run on cadence
- queue candidate URLs
- suppress repeatedly failing sources
- emit alerts when needed

### 10.4 Normal discovery backlog

**Responsibility label:** Layer 1 — Normal Ops

Monitor only if pending queue trends down.

### 10.5 Discovery backlog rising continuously

**Responsibility label:** Layer 1 → Technical-Owner Mode if loop/runtime issue

Layer 1:

- inspect pending count
- inspect loop freshness
- inspect source-ingestion detail
- mark `Investigate` or `Escalate`

Owner Override:

- acknowledge alert
- add note
- mark case reviewed
- wait for suppression window if source recovered

Technical-Owner Mode:

- inspect logs
- restart backend/worker
- change source URLs
- repair ingestion logic
- wipe poisoned batch
- deploy patch

### 10.6 Source suppression

**Responsibility label:** Automated System first; Layer 1 if recurring

The system should suppress repeatedly failing sources and track failure counters/suppression windows.

Layer 1 should monitor suppressed sources and investigate if sticky.

Owner Override can:

- mark reviewed
- add note
- open source detail
- schedule recheck if bounded and safe

Technical-Owner Mode is needed for:

- changing source list
- changing suppression policy
- direct cleanup
- poisoned batch wipe

### 10.7 Poisoned discovery batch

**Responsibility label:** Layer 3 — Technical-Owner Mode

Wiping a poisoned discovery batch must require:

- technical-owner mode
- reason
- confirmation
- audit log
- rollback consideration where possible

---

## 11. Verification and Trainer Quality Responsibilities

### 11.1 Reverification cadence

**Responsibility label:** Automated System

The system re-scores listings on a cadence weighted by staleness and threshold proximity.

### 11.2 Verification drift visibility

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should expose trust and verification signals where relevant:

- sudden hidden listing spike
- unverified/verified balance
- confidence drift
- recent system actions
- audit feed
- top trainer instability

### 11.3 Manual listing verification override

**Responsibility label:** Layer 3 — Technical-Owner Mode

Changing a trainer’s verification or publication status manually affects trust policy and public supply.

Recommended default: keep manual verification overrides out of normal ops.

### 11.4 Legal takedown

**Responsibility label:** Layer 3 — Technical-Owner Mode

Legal takedown of a real listing requires technical-owner mode and an audit reason.

### 11.5 Temporary hide pending review

**Responsibility label:** Layer 2 — Owner Override for target-state implementation only

If implemented, it must be:

- reversible
- reason required
- audit logged
- does not change locked policy
- does not delete trainer data
- clearly distinct from legal takedown

This is a target-state Owner Override boundary, not a current-runtime completeness claim.

---

## 12. Ranking, Pricing, and System Optimisation Responsibilities

### 12.1 Ranking recomputation

**Responsibility label:** Automated System

The ranking loop should recompute trainer outcome score from relevant signals.

No owner action in routine ranking.

### 12.2 Ranking instability

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should allow the owner to notice sudden top-trainer or ranking instability.

Owner should:

- monitor distribution
- investigate sudden instability
- check recent system actions/audit feed
- escalate if matching trust is affected

### 12.3 Manual ranking change

**Responsibility label:** Layer 3 — Technical-Owner Mode

Manual ranking intervention changes platform trust and matching fairness.

It should not be a normal owner override.

### 12.4 Pricing recomputation

**Responsibility label:** Automated System

Pricing should be recomputed by the system according to the current policy.

### 12.5 Pricing state visibility

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show pricing state.

The owner investigates mismatch versus launch policy.

### 12.6 Pricing mismatch correction

**Responsibility label:** Layer 3 — Technical-Owner Mode

Correcting pricing mismatch requires checking runtime config and possibly restarting runtime.

This is not a normal `/ops` action.

---

## 13. Growth, Attribution, SEO, and Nurture Responsibilities

### 13.1 Attribution entry tracking

**Responsibility label:** Automated System

The system should track:

- external traffic sources
- campaign pages
- suburb SEO pages
- query attribution
- campaign/source metadata forwarded into waitlist or match flows

### 13.2 Growth attribution summary

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should expose growth attribution summary totals and top cohorts.

Owner monitors:

- dead channels
- growing remarketing cohorts
- conversion-gap cohorts
- SEO cohort underperformance

### 13.3 Programmatic SEO page generation/cache

**Responsibility label:** Automated System

SEO copy should be generated or cached on demand.

Attribution should survive the path from landing page to home to match/waitlist to intro/conversion reporting.

### 13.4 Growth nurture loop

**Responsibility label:** Automated System

The growth nurture loop should update remarketing and conversion-gap cohorts.

### 13.5 Growth underperformance

**Responsibility label:** Layer 1 — Normal Ops

Owner monitors.

No automatic need for intervention unless a technical failure is suspected.

Owner Override may:

- note channel underperformance
- mark cohort for review
- export/open context if supported

Technical-Owner Mode applies if changing:

- SEO generation logic
- attribution rules
- campaign routes
- deployment

---

## 14. Claims, Policy Wording, and Public Claims Validation

### 14.1 Public claim validation

**Responsibility label:** Automated System

Claim validation should evaluate claim wording against the current state and enforcement mode.

### 14.2 Claim validation visibility

**Responsibility label:** Layer 1 — Normal Ops

Owner may monitor claim validation blocks, especially if public copy or launch claims are being revised.

### 14.3 Changing claim enforcement mode or public policy wording

**Responsibility label:** Layer 3 — Technical-Owner Mode

Changing enforcement mode, claim policy, or public claim logic can alter legal and trust posture.

It should not be normal ops.

---

## 15. `/ops` Cockpit Responsibilities

### 15.1 Oversight authentication

**Responsibility label:** Automated System

`/ops` should require passcode authentication.

### 15.2 Continuous polling

**Responsibility label:** Automated System

`/ops` should poll the oversight API on cadence.

### 15.3 Daily use of `/ops`

**Responsibility label:** Layer 1 — Normal Ops

The owner should open `/ops` at start of day, check core cards, then re-check midday and end of day.

### 15.4 Weekly use of `/ops`

**Responsibility label:** Layer 1 — Normal Ops

The owner should review trends, stale loops, high-severity alerts, and unresolved remediation items.

### 15.5 Decisioning: Monitor / Investigate / Escalate

**Responsibility label:** Layer 1 — Normal Ops

The owner must choose one:

- `Monitor`
- `Investigate`
- `Escalate`

### 15.6 Current `/ops` read-only boundary

**Responsibility label:** Layer 1 — Normal Ops

Current `/ops` is operational visibility only.

Future materialisation should not silently convert it into unrestricted admin.

### 15.7 Investigation queue

**Responsibility label:** Layer 1, with Layer 2 actions if bounded

Layer 1:

- inspect case
- read evidence
- monitor/investigate/escalate
- record note

Layer 2:

- route to billing
- route to reactivation
- resend notification
- close/reopen case
- acknowledge alert

Layer 3:

- direct data edits
- runtime actions
- provider repair
- config/policy changes

---

## 16. Alerts, Health, and Recovery Responsibilities

### 16.1 Health loop

**Responsibility label:** Automated System

The health loop should:

- monitor rolling intro/conversion/suppression signals
- update system health
- emit alerts
- auto-rollback where safe and configured

### 16.2 Healthy state checks

**Responsibility label:** Layer 1 — Normal Ops

Owner checks:

- active loops are fresh
- no stale high-severity alerts
- discovery pending trends down
- billing retry exhaustion does not grow continuously
- source suppression remains low/non-sticky
- notes are current

### 16.3 Stale loop

**Responsibility label:** Layer 1 detects; Layer 3 resolves

Layer 1:

- detect stale loop via `/ops`
- classify `Escalate`

Technical-Owner Mode:

- inspect logs
- restart backend/worker if required
- verify oversight refresh after recovery

Restarting runtime is technical-owner mode.

### 16.4 Intro drop alert

**Responsibility label:** Layer 1 investigates; Layer 3 if config/data repair needed

Layer 1:

- confirm not a normal burst effect
- inspect audit history
- inspect pricing state

Technical-Owner Mode:

- write inverse config snapshot where required
- restart runtime if needed
- change config
- repair data

### 16.5 Auto-rollback alert

**Responsibility label:** Automated System first; Layer 1 review; Layer 3 for re-apply

The system performs rollback automatically.

Owner reviews the rolled-back snapshot and decides whether to re-apply adjusted parameters or leave reverted.

Re-applying config is technical-owner mode.

### 16.6 Persistent high-severity alert

**Responsibility label:** Layer 1 → Layer 3

Layer 1:

- detect persistent alert
- classify escalation
- add note

Actual repair depends on alert type and often becomes technical-owner mode.

---

## 17. Support Responsibilities

### 17.1 General support handling

**Responsibility label:** Layer 1 + Support mailbox

The support mailbox is used for:

- general support
- billing remediation
- trainer onboarding follow-up
- reactivation follow-up

### 17.2 Support context gathering

**Responsibility label:** Layer 1 — Normal Ops

Owner uses `/ops` for context and diagnosis, then support mailbox for outbound handling.

### 17.3 Support-triggered safe actions

**Responsibility label:** Layer 2 — Owner Override

If support issue maps to a safe action:

- resend existing notification
- route trainer to `/trainer/billing`
- route trainer to `/trainer/reactivate`
- mark issue reviewed
- add note
- close/reopen case

### 17.4 Support-triggered high-risk actions

**Responsibility label:** Layer 3 — Technical-Owner Mode

If support asks for:

- refund
- takedown
- publication change
- billing policy exception
- data correction
- account/provider recovery
- runtime investigation

then technical-owner mode applies.

---

## 18. Data, Audit, and Mutation Responsibilities

### 18.1 Routine data writes from product flows

**Responsibility label:** Automated System

The system writes routine product records such as:

- owner waitlist rows
- owner waitlist events
- match events
- intros
- engagements
- conversions
- outreach events
- Stripe events
- source ingestion state
- growth attribution
- reactivation candidates

### 18.2 Audit log on state changes

**Responsibility label:** Automated System

All state-changing actions should write audit records with actor and context.

Any future `/ops` action must preserve this.

### 18.3 Owner note

**Responsibility label:** Layer 1 or Layer 2 depending whether it mutates case state

If owner note is just operational note, it belongs in Layer 1.

If note changes case status or closes/remediates something, it becomes Layer 2 and must be audit logged.

### 18.4 Direct DB repair

**Responsibility label:** Layer 3 — Technical-Owner Mode

Direct DB repair is outside normal product operation.

Every direct write should include actor and reason.

---

## 19. Infrastructure, Runtime, Provider, and Deployment Responsibilities

### 19.1 Runtime loop ownership

**Responsibility label:** Automated System

The system should enforce safe loop ownership and prevent duplicate loop execution.

### 19.2 Runtime ownership visibility

**Responsibility label:** Layer 1 — Normal Ops

`/ops` should show enough to know:

- which process owns loops
- whether loops are stale
- whether lease is active
- whether autonomy is disabled
- whether system state is refreshing

### 19.3 Runtime intervention

**Responsibility label:** Layer 3 — Technical-Owner Mode

Restarting backend/runtime, inspecting logs, diagnosing loop stoppage, and restoring loop ownership are technical-owner actions.

### 19.4 Provider/platform intervention

**Responsibility label:** Layer 3 — Technical-Owner Mode

Secret rotation, provider account changes, domain/TLS/hosting/deployment recovery, and billing-provider configuration recovery are technical-owner actions.

### 19.5 Deployment/rollback

**Responsibility label:** Layer 3 — Technical-Owner Mode

Deploy, redeploy, rollback, environment changes, and runtime flags change public/system behaviour.

Do not make them default `/ops` buttons.

### 19.6 Runbook links

**Responsibility label:** Layer 1 visibility; Layer 3 execution

`/ops` should expose technical-owner runbook links when escalation is required.

Execution remains technical-owner mode.

---

## 20. Website and Page Completeness Responsibilities

### 20.1 Public page rendering

**Responsibility label:** Automated System + Build/Test Process

All listed routes should render, controls should exist, primary outcomes should occur, error states should be explicit, and build/route smoke checks should pass.

This is not an owner daily operation.

### 20.2 Dead buttons/dead links

**Responsibility label:** Automated System detection where possible; Layer 1 if user-reported

Best materialisation:

- automated route smoke tests
- link checks
- frontend error monitoring
- `/ops` alert only if route/control failures are detected or reported

Fixing broken page code is technical-owner mode.

### 20.3 Legal pages

**Responsibility label:** Technical-Owner Mode for content change; Automated System for availability

Privacy and terms pages must remain available.

Changing legal content is technical-owner mode because it affects public/legal posture.

---

## 21. External Contributor Responsibilities

### 21.1 Discovery contribution

**Responsibility label:** External Contributor + Automated System

External actor submits URL and hints via discovery endpoint.

The system accepts valid input into the queue.

### 21.2 Bad external contribution

**Responsibility label:** Automated System first

The system should discard duplicates or low-quality items and suppress problematic sources.

Owner only sees trends or persistent failures.

---

## 22. Responsibilities That Must Stay Automated

These should not become owner tasks:

- owner waitlist enrollment
- match request processing
- ranked trainer result generation
- intro creation
- fraud suppression
- contact reveal
- engagement tracking
- inferred conversion creation
- inferred conversion maturity rules
- T+7 outreach
- trainer submission scoring
- auto-publish/hold decision
- billing profile provisioning attempt
- valid intro metering
- Stripe invoice sending
- Stripe webhook reconciliation
- billing retry/backoff
- ranking recomputation
- pricing snapshot recomputation
- listing reverification
- discovery queue processing
- source ingestion/suppression
- growth attribution tracking
- growth nurture cohorts
- reactivation candidate detection
- health alerts
- health auto-rollback
- audit logging

Turning these into manual owner work would contradict the autonomous-system model.

---

## 23. Responsibilities That Belong in Normal `/ops`

These are Layer 1:

- open `/ops`
- authenticate
- view snapshot
- refresh/poll
- inspect revenue booked/collected/at risk
- inspect trial-free intros
- inspect intros/conversions/engagement
- inspect suppressed intros
- inspect suspicious conversions
- inspect inferred pending
- inspect loop cards
- inspect alerts
- inspect discovery pending
- inspect growth attribution
- inspect reactivation summary
- inspect pricing state
- inspect current launch phase
- inspect public matching exposure
- inspect supply readiness
- inspect intro-ready trainers
- inspect blocked trainers
- inspect readiness recommendation
- inspect blockers to next phase
- inspect top trainers
- inspect recent system actions
- inspect audit feed
- inspect investigation queue
- inspect source-ingestion detail
- write daily note
- choose `Monitor`, `Investigate`, or `Escalate`
- follow daily and weekly routine

---

## 24. Responsibilities That Belong in Owner Override

These are Layer 2, only if implemented with reason capture and audit logging:

- acknowledge alert
- mark reviewed
- add owner note
- mark monitor
- mark investigate
- mark escalate
- close case
- reopen case
- resend existing notification
- retry bounded non-policy job
- route trainer to `/trainer/billing`
- route trainer to `/trainer/reactivate`
- open support email context
- mark billing remediation required
- mark reactivation follow-up required
- mark case as waiting on trainer
- mark case as waiting on provider
- request recheck of source if bounded and safe
- request recheck of broken lifecycle item if bounded and safe

These actions should not change locked runtime policy and should generally be reversible or bounded.

---

## 25. Responsibilities That Belong in Technical-Owner Mode

These are Layer 3:

- change `PUBLIC_MATCHING_ENABLED`
- change launch phase or public emphasis
- change billing mode
- change conversion billing mode
- change fixed intro fee
- change trainer free intro days
- change fraud thresholds
- change confidence thresholds
- change verification policy
- change source URLs
- change launch policy
- change environment variables
- re-apply config after auto-rollback
- restart backend/runtime
- inspect supervisor/runtime logs
- restore loop ownership process
- disable autonomy
- change autonomy loop owner
- rotate secrets
- fix provider account
- fix domain/TLS/hosting
- deploy/redeploy/rollback
- direct DB repair
- legal takedown
- refund billed intro/conversion
- wipe poisoned discovery batch
- manually publish/unpublish trainer
- manually alter ranking
- manually alter pricing state
- manually alter billing status
- manually repair Stripe events
- manually alter audit-sensitive records

These can be accessible from the owner cockpit as guided escalation paths, but not as normal controls.

---

## 26. Materialised `/ops` Design

This section describes the intended target-state materialisation of the `/ops` cockpit.
It is not a claim that every surface below already exists in the current runtime.

### 26.1 Normal Ops zone

Purpose:

> Is the autonomous system healthy?

Must show:

- current launch phase
- public matching exposure
- supply readiness
- intro-ready trainers
- blocked trainers
- readiness recommendation
- blockers to next phase
- loop health
- revenue booked/collected/at risk
- trial-free intros
- intros 24h/7d
- conversions 24h
- engagement events
- suppressed intros
- suspicious conversions
- inferred pending
- discovery pending
- source ingestion state
- reactivation summary
- pricing state
- top trainers
- growth attribution
- recent system actions
- audit feed
- notes

No mutation required except note-taking and triage classification.

### 26.2 Exception Inbox zone

Purpose:

> What needs my attention?

Should include only threshold-breached or unresolved cases:

- stale core loop
- persistent high-severity alert
- at-risk revenue rising
- retry exhausted
- needs remediation
- disputed invoice
- source repeatedly suppressed
- discovery backlog rising
- suspicious conversion spike
- suppressed intro spike
- reactivation return-to-active below threshold
- owner/trainer path reported broken
- failed outreach above threshold
- Stripe invoice error
- pricing mismatch

Do not create cases for:

- normal paid invoices
- normal trial-free intros
- normal inferred pending
- normal reactivation candidate
- normal retry sent
- normal source suppression within limits

### 26.3 Case Detail zone

Purpose:

> What happened, why does it matter, and what can I safely do?

Each case should show:

- case type
- severity
- status
- related entity
- current evidence
- latest system action
- owner note history
- recommended action
- mode required: Normal Ops / Owner Override / Technical-Owner Mode
- linked route: `/trainer/billing`, `/trainer/reactivate`, `/submit/status`, support mailbox, runbook
- audit trail

### 26.4 Owner Override zone

Purpose:

> Safe bounded action.

Allowed actions:

- acknowledge
- add note
- mark monitor/investigate/escalate
- resend notification
- retry bounded job
- route to billing
- route to reactivation
- close/reopen with reason

Every action:

- writes audit log
- records actor
- records before/after if state changes
- records reason
- is reversible where possible

### 26.5 Technical-Owner Mode zone

Purpose:

> Dangerous action guidance, not casual control.

For each technical-owner case, `/ops` should show:

- why this cannot be normal ops
- what system area is affected
- runbook link
- required checks
- command/provider surface if relevant
- required audit reason
- rollback consideration
- confirmation that this is technical-owner mode

The cockpit may link to technical-owner procedures. It should not hide danger behind a casual button.

---

## 27. Completeness Check

Based on the canonical DTD operating model, every responsibility should fall into one of these labels:

### Automated System

- routine product flows
- autonomous loops
- normal signal processing
- billing retry/recovery
- fraud suppression
- attribution/nurture
- reactivation detection
- health checks and auto-rollback
- audit logging

### Layer 1 — Normal Ops

- read-only monitoring
- daily/weekly review
- triage
- notes
- case observation
- decisioning
- threshold-based investigation
- review current launch phase
- review public matching exposure
- review supply readiness and next-phase blockers

### Layer 2 — Owner Override

- safe bounded interventions
- routing/remediation
- resend/retry
- case closure/reopen
- alert acknowledgement
- support-context actions

### Layer 3 — Technical-Owner Mode

- infra/runtime/provider/config/policy/direct-data actions
- refunds
- legal takedowns
- poisoned batch wipe
- deployment/restart/env changes
- manual data repair
- threshold/policy changes

### User / Trainer / External Actor

- dog owner submits match/waitlist/connect/outcome
- trainer submits profile/fixes billing/reactivates
- external contributor submits discovery URL

---

## 28. Final Build Implication

DTD `/ops` should not become an admin dashboard.

It should become a **mode-aware owner cockpit** where:

- automation does routine work
- Normal Ops detects issues
- Owner Override handles safe exceptions
- Technical-Owner Mode is explicitly invoked only when the action can affect policy, infrastructure, money, trust, or production state

The governing rule remains:

> Automate routine work. Surface exceptions. Gate dangerous actions. Audit every mutation.
