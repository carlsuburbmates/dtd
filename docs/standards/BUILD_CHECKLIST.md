# Build Checklist

## Purpose

This document defines the execution checklist for building the platform to the standard.

It is a normative build checklist.
It does not describe whether each item is already complete.

## A. Foundation

1. Establish repository structure for frontend, backend, docs, tests, and deployment assets.
2. Define canonical environment variables for backend, frontend, payments, email, monitoring, and runtime ownership.
3. Define the launch-phase representation model, keeping launch phase separate from live matching exposure.
4. Support `PUBLIC_LAUNCH_PHASE` or equivalent persisted phase state without hardcoding one implementation mechanism as mandatory when an equivalent persisted or config-backed phase mechanism already exists.
5. Define a local runnable baseline using Docker and/or bare metal.
6. Provide `.env.example` files that are sufficient for local setup.
7. Ensure real `.env` files are ignored by git.
8. Define the evidence and audit linkage needed for launch-phase visibility and transition decisions.

## B. Public Product Surfaces

1. Build the mode-gated and phase-aware home surface.
2. Build informational public pages:
- about
- how it works
- pricing
- trust
- faq
- contact
- privacy
- terms
3. Build trainer acquisition surface.
4. Build trainer detail surface with contact-release workflow.
5. Build campaign and SEO landing surfaces.
6. Ensure public phase emphasis can shift without requiring separate homepage rebuilds.
7. Keep trainer onboarding open during supply-first launch even when public live matching is gated.

## C. Demand Workflows

1. Implement owner waitlist workflow.
2. Implement owner match workflow.
3. Implement contact-release intro workflow.
4. Implement engagement capture workflow.
5. Implement explicit outcome confirmation workflow.
6. Implement T+7 follow-up workflow.

## D. Supply Workflows

1. Implement trainer submission workflow.
2. Implement automated publish / unverified publish / hold decision logic.
3. Implement submission status workflow.
4. Implement trainer billing remediation workflow.
5. Implement trainer reactivation workflow.
6. Ensure trainer supply workflows support supply-first launch monitoring and intro-readiness visibility.

## E. Revenue Workflows

1. Implement intro metering.
2. Implement fail-soft intro billing.
3. Implement billing-profile provisioning.
4. Implement webhook reconciliation.
5. Implement billing retry and recovery loop.
6. Implement explicit billing-state classification.

## F. Growth Workflows

1. Implement attribution entry capture.
2. Implement campaign handoff into owner flows.
3. Implement SEO landing handoff into owner flows.
4. Implement growth cohort persistence.
5. Implement nurture cohort generation.

## G. Oversight Workflows

1. Implement oversight login.
2. Implement read-only oversight snapshot endpoint.
3. Build `/ops` UI for:
- loop visibility
- alerts
- revenue visibility
- billing visibility
- growth visibility
- reactivation visibility
- source-ingestion visibility
- recent system actions
- current launch phase
- public matching exposure state
- supply readiness
- intro-ready trainers
- blocked trainers
- readiness recommendation
- blockers to next phase
4. Ensure `/ops` remains Normal Ops by default and does not expose direct policy-changing controls.
5. Keep `/ops` aligned with the responsibility boundaries in `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`.

## H. Autonomous Runtime

1. Implement ranking loop.
2. Implement pricing loop.
3. Implement verification loop.
4. Implement discovery queue processing loop.
5. Implement inferred conversion promotion loop.
6. Implement source ingestion loop.
7. Implement outreach loop.
8. Implement billing recovery loop.
9. Implement nurture loop.
10. Implement reactivation routing loop.
11. Implement health loop.
12. Implement lease-guarded single-owner scheduling.

## I. Data And Integrity

1. Define core collections/entities.
2. Add required unique indexes and critical read/write indexes.
3. Implement intro idempotency.
4. Implement webhook idempotency.
5. Implement auth-attempt tracking for oversight lockout.
6. Implement audit logging for state-changing actions.
7. Prevent demo/seed behavior from contaminating production runtime.
8. Persist launch phase state, or equivalent persisted phase state, separately from public matching exposure state.
9. Persist phase readiness snapshots.
10. Persist phase transition decisions.
11. Ensure readiness snapshots and phase decisions can be linked to audit evidence.
12. Ensure CSV/export remains proof output only, not the primary operating record.

## J. Security And Access Control

1. Protect oversight access.
2. Protect trainer lifecycle routes with context-bound tokens.
3. Require consent before match/contact/submission actions where mandated.
4. Restrict runtime policy changes to the same owner's `technical-owner mode`.
5. Keep secrets out of git and front-end bundles.
6. Define operator-safe actions versus same-owner `technical-owner mode` actions.

## K. Observability

1. Persist loop heartbeats.
2. Persist health alerts.
3. Persist billing recovery state.
4. Persist source-ingestion state.
5. Persist reactivation routing state.
6. Persist launch phase and readiness state, or equivalent persisted phase state and readiness records.
7. Persist evidence freshness for launch-critical readiness views where applicable.
8. Expose these via oversight.
9. Define external telemetry wiring for error tracking and analytics.

## L. Deployment

1. Define frontend hosting target.
2. Define backend hosting target.
3. Define database hosting target.
4. Define domain and TLS ownership.
5. Define loop-owner topology in production.
6. Define environment-variable inventory for production.
7. Define repeatable deploy and redeploy process.
8. Define rollback process.

## M. Testing And Validation

1. Add backend unit tests for auth, billing, runtime control, and public-mode behavior.
2. Add backend tests for negative paths and recovery paths.
3. Add frontend tests for critical helper logic and user-path behavior.
4. Add CI checks that cover backend verification and frontend build/test validation.
5. Add release-gate scripts for copy/policy and critical runtime checks.
6. Validate phase-aware public posture and launch-readiness visibility where implemented.

## N. Documentation

1. Maintain architecture document.
2. Maintain operations runbook.
3. Maintain deployment document.
4. Maintain workflow catalog.
5. Maintain workflow trace sheet.
6. Maintain canonical standards set.

## O. Human/Operator Enablement

1. Define non-technical monitoring routine.
2. Define escalation thresholds.
3. Define support routing.
4. Define billing remediation procedure.
5. Define discovery/source-ingestion triage procedure.
6. Define reactivation triage procedure.
7. Define manual intervention boundaries.
8. Define supply-first launch monitoring routine.
9. Define readiness review procedure using product-backed evidence.
10. Define owner-approved phase transition procedure.
11. Define when launch-phase and public-exposure changes require `technical-owner mode`.
