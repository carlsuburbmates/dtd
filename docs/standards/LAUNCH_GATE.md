# Launch Gate

## Purpose

This document defines the required launch gate for the platform.

It specifies what must be true before a launch can be approved.
It does not record whether those conditions are currently satisfied.

## Gate Rule

Launch approval requires all gate sections below to pass.

If any gate is not satisfied, launch must not be declared approved.

## 1. Launch Phase Gate

The launch candidate must define and expose a coherent launch-phase model.

Required conditions:
1. the current launch phase is explicitly represented
2. launch phase is separate from public live matching exposure state
3. the system supports `supply_first`, `owner_waitlist`, `live_matching`, and `growth` as canonical phases
4. the current phase may be represented by `PUBLIC_LAUNCH_PHASE` or equivalent persisted phase state
5. public posture and launch evidence align with the approved current phase
6. automatic phase switching is not permitted

## 2. Product Gate

The launch candidate must provide:
1. an exposure-gated and phase-aware home entry surface
2. an owner waitlist path
3. a live matching path
4. a trainer detail path
5. a connect/contact-release path
6. a trainer submission path
7. a submission status path
8. a trainer billing remediation path
9. a trainer reactivation path
10. a follow-up outcome path
11. a Normal Ops oversight path by default

The live matching path must exist as a product capability.
However, supply-first launch does not require broad public live matching emphasis before supply readiness is proven and approved.

## 3. Workflow Gate

The launch candidate must support the following end-to-end workflow families:
1. demand capture
2. contact release
3. engagement capture
4. outcome capture
5. trainer submission and activation
6. intro billing and webhook reconciliation
7. billing recovery
8. discovery ingestion and verification
9. growth attribution and nurture
10. trainer reactivation
11. claim validation

## 4. Runtime Gate

The launch candidate must demonstrate:
1. exactly one active loop owner by intended topology
2. lease protection against duplicate active owners
3. loop freshness visibility
4. health alert generation
5. source-ingestion visibility
6. billing recovery visibility
7. reactivation routing visibility

## 5. Security Gate

The launch candidate must provide:
1. oversight protection
2. failed-auth lockout or equivalent brute-force protection
3. trainer action-token protection for trainer lifecycle routes
4. intro idempotency protection
5. webhook idempotency protection
6. explicit consent checkpoints where required
7. environment-secret separation from git-tracked files

## 6. Supply Gate

The launch candidate must provide evidence-backed supply readiness controls.

Required conditions:
1. a minimum trainer supply threshold is defined
2. a minimum intro-ready trainer threshold is defined
3. target geography coverage is defined and inspectable
4. trainer publish, hold, blocked, and intro-ready states are visible in product-backed evidence
5. trainer remediation and reactivation paths exist
6. supply readiness can be judged without spreadsheet reconstruction or direct database queries

## 7. Revenue Gate

The launch candidate must provide:
1. explicit intro metering
2. explicit trial-free and collectible state handling
3. fail-soft billing behavior that preserves user-path clarity
4. webhook reconciliation for billing lifecycle changes
5. explicit at-risk, collected, waived, refunded, disputed, and non-billable state visibility
6. bounded billing recovery behavior

## 8. Data Sufficiency Gate

The launch candidate must provide launch-critical product-backed records.

Required conditions:
1. launch-critical operational records persist in product-owned data
2. launch phase is persisted separately from public live matching exposure, using `PUBLIC_LAUNCH_PHASE` or equivalent persisted phase state
3. phase readiness snapshots exist
4. phase transition decisions exist
5. readiness and transition records can be linked to audit evidence
6. `/ops` summaries are backed by product data
7. CSV/export is available for proof only and is not the primary operating record

## 9. Operator Gate

The launch candidate must provide a non-technical operator path for:
1. reading current system health
2. reading current revenue state
3. reading alerts
4. identifying stale loops
5. identifying discovery/source-ingestion issues
6. identifying trainer billing blockers
7. identifying trainer reactivation blockers
8. knowing when to monitor, investigate, or escalate
9. reading current launch phase
10. reading public live matching exposure state
11. reading supply readiness and readiness recommendation
12. identifying blockers to next phase

`/ops` must remain Normal Ops by default.

## 10. Support Gate

The launch candidate must provide:
1. a canonical support mailbox or support path
2. trainer billing remediation routing
3. trainer reactivation routing
4. a documented escalation path for broken user workflows

## 11. Observability Gate

The launch candidate must expose:
1. oversight snapshot data
2. loop freshness state
3. alert state
4. billing summary state
5. notification delivery summary
6. growth attribution summary
7. reactivation summary
8. source-ingestion state
9. recent system actions
10. current launch phase
11. public live matching exposure state
12. supply readiness
13. intro-ready trainer count or equivalent supply-readiness signal
14. blocked trainer count or equivalent supply-blocker signal
15. readiness recommendation
16. blockers to next phase

## 12. Deployment Gate

The launch candidate must have:
1. documented frontend deployment process
2. documented backend deployment process
3. documented environment-variable inventory
4. documented loop-owner deployment topology
5. documented domain and TLS ownership
6. documented redeploy path
7. documented rollback path

## 13. Validation Gate

The launch candidate must pass:
1. backend compile/import sanity
2. backend critical-path test suite
3. frontend production build
4. frontend critical-path validation
5. release-gate or policy/copy checks where applicable
6. route smoke for primary public and oversight surfaces

## 14. Documentation Gate

The launch candidate must have a coherent documentation set covering:
1. system architecture
2. workflows
3. operations
4. deployment
5. launch gate
6. post-build integrity audit
7. supply-first launch goals and evidence alignment
8. ops responsibility boundaries

## 15. Launch Evidence Requirement

Launch approval must be based on explicit evidence, not only implementation intent.

Required evidence categories:
1. local validation evidence
2. release-candidate validation evidence
3. runtime evidence window
4. domain and route evidence
5. operator-surface evidence
6. payment and notification evidence where applicable
7. supply-readiness evidence
8. phase-readiness evidence
9. phase-decision evidence where a transition claim is involved

## 16. Phase Transition Approval Gate

Any transition affecting launch phase, public exposure, or production behavior requires explicit owner approval.

Required conditions:
1. a current readiness snapshot has been reviewed
2. the decision is recorded as approved, rejected, or deferred
3. the decision includes a reason
4. the decision is linked to audit evidence
5. rollback intent or note exists where relevant
6. `technical-owner mode` is required when the transition changes public exposure, locked runtime policy, or production behavior

## 17. Approval Requirement

Launch requires an explicit approval decision by the designated launch authority.

Implicit confidence, partial evidence, or general progress must not be treated as launch approval.
