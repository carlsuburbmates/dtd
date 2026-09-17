# Integrity Audit

## Purpose

This document defines the post-build verification and audit checklist.

It is used to verify that a built system matches the standard, remains internally consistent, and is operationally trustworthy.

It does not record whether an audit has already been passed.

## 1. Scope Of Audit

The integrity audit must cover:
1. product behavior
2. launch-phase integrity
3. workflow continuity
4. route integrity
5. runtime integrity
6. data integrity
7. access-control integrity
8. billing integrity
9. monitoring integrity
10. deployment integrity
11. documentation integrity
12. phase-transition integrity

## 2. Product Integrity Checks

Verify:
1. all required public routes render
2. home mode behavior matches the configured mode
3. home posture matches the configured launch phase
4. trainer-detail behavior matches configured public mode
5. trainer onboarding remains available where required by the current phase
6. public live matching exposure remains gated when the approved phase does not support broad live exposure
7. public copy does not imply live matching availability before readiness is proven and approved
8. trainer lifecycle routes are reachable and coherent
9. follow-up path is coherent and idempotent where required
10. support routing is consistent across surfaces

## 3. Workflow Integrity Checks

Verify each workflow family end-to-end:
1. owner waitlist
2. owner match
3. contact release
4. engagement capture
5. explicit conversion capture
6. follow-up outcome capture
7. trainer submission
8. activation status
9. trainer billing remediation
10. trainer reactivation
11. attribution capture
12. SEO/campaign handoff
13. discovery queue contribution
14. oversight login and monitoring
15. phase readiness snapshot creation or equivalent persisted readiness recording
16. phase transition decision recording and audit linkage

## 4. Runtime Integrity Checks

Verify:
1. intended loop-owner topology is active
2. no duplicate active loop owner is executing loops
3. loop heartbeats are fresh relative to configured cadence
4. health alerts are structurally valid
5. source-ingestion state is present and interpretable
6. billing recovery state is present and interpretable
7. reactivation routing state is present and interpretable

## 5. Data Integrity Checks

Verify:
1. critical collections exist
2. critical indexes exist
3. idempotency-sensitive paths do not create uncontrolled duplicates
4. relationship keys are coherent across intros, conversions, submissions, and trainers
5. audit logging exists for required state-changing actions
6. seed or demo behavior cannot pollute production data unexpectedly
7. generated content paths do not introduce uncontrolled storage abuse
8. launch phase state, or equivalent persisted phase state, exists and is coherent
9. phase readiness snapshots exist and are interpretable
10. phase transition decisions exist and are interpretable
11. launch phase state, readiness records, and transition decisions remain coherent with each other
12. CSV/export outputs are not treated as the primary operating record

## 6. Security Integrity Checks

Verify:
1. oversight access is protected
2. failed-auth lockout is enforced
3. trainer action tokens reject invalid, tampered, expired, and wrong-context inputs
4. webhook idempotency is enforced
5. intro idempotency is enforced
6. public mutation endpoints have explicit abuse-risk acknowledgement and controls
7. secrets are not present in tracked files or frontend bundles

## 7. Billing Integrity Checks

Verify:
1. intro billing behavior is explicit for billable and non-billable paths
2. trial-free behavior is explicit and bounded
3. invoice lifecycle states reconcile correctly
4. retry-state transitions are explicit
5. at-risk revenue state is visible
6. remediation-required states are visible and actionable

## 8. Monitoring Integrity Checks

Verify:
1. `/api/oversight` payload is internally coherent
2. `/ops` renders and interprets oversight payload correctly
3. alert severity semantics are clear
4. loop cards reflect actual freshness logic
5. source-ingestion and billing summaries are not orphaned from operator-facing interpretation
6. notification delivery visibility exists where notification flows exist
7. current launch phase is visible
8. public live matching exposure state is visible
9. supply readiness is visible
10. intro-ready trainer count or equivalent supply-readiness signal is visible
11. blocked trainer count or equivalent supply-blocker signal is visible
12. readiness recommendation is visible
13. blockers to next phase are visible

## 9. Deployment Integrity Checks

Verify:
1. documented deployment commands match actual repo/runtime behavior
2. documented environment variables match actual runtime expectations
3. frontend build artifacts align with configured hosting assumptions
4. backend runtime assumptions align with loop-owner topology assumptions
5. rollback steps are explicit and executable

## 10. Documentation Integrity Checks

Verify:
1. the canonical implementation pack does not contradict itself
2. product copy does not contradict actual runtime policy
3. environment examples do not contradict canonical auth or monetization decisions
4. historical status documents do not override normative standards
5. all referenced files and paths exist
6. standards docs do not contradict `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`
7. standards docs do not contradict `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`
8. standards docs do not contradict `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`

## 11. Non-Technical Operator Audit

Verify that a non-technical operator can:
1. open `/ops`
2. understand priority cards
3. distinguish monitor vs investigate vs escalate
4. identify billing recovery issues
5. identify source-ingestion issues
6. identify reactivation issues
7. route support correctly
8. avoid policy-changing actions from the operator path
9. identify the current launch phase
10. understand current readiness status and recommendation
11. identify blockers to the next phase
12. understand when owner approval in `technical-owner mode` is still required

## 12. Business Continuity Audit

Verify:
1. owner of each critical service is known
2. access recovery path exists for each critical provider
3. support mailbox ownership is known
4. deployment/runtime recovery path is documented
5. data-restore path is documented
6. founder-only knowledge is explicitly identified where it still exists

## 13. Failure-Mode Audit

Audit the following classes of failure:
1. API outage
2. frontend outage
3. loop staleness
4. payment failure
5. webhook failure
6. email failure
7. discovery/source-ingestion failure
8. queue lag
9. auth failure
10. domain/TLS failure
11. database outage or corruption
12. silent degradation in ranking or conversion quality
13. accidental live matching exposure during a non-live phase
14. stale or missing readiness snapshots
15. contradictory or missing launch phase state
16. overstated readiness despite blocked or insufficient supply

For each audited failure mode, verify:
1. detection path
2. user impact
3. recovery path
4. operator mode versus `technical-owner mode` for the same owner
5. expected evidence source

## 14. Release-Candidate Audit Bundle

The post-build audit bundle must include:
1. backend validation results
2. frontend validation results
3. route smoke evidence
4. oversight snapshot evidence
5. billing-path evidence where applicable
6. deployment evidence
7. doc-consistency pass
8. supply-readiness evidence
9. phase-readiness evidence
10. phase-decision and audit evidence where transition claims are made

## 15. Audit Rule

No system should be described as launch-ready, production-ready, or operationally ready unless it passes the integrity audit against the standard set.
