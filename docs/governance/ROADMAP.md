# Roadmap

Rule: current-state only. Update this file in place when plans change.

## Goal

Launch Bark&Bond in Greater Melbourne with a region-based, intro-credit model, heavy consent UX, and automation-first operations.

## Current Status Snapshot (2026-04-30)

Completed foundations:
1. Platform hardening baseline complete (vendor lock-out removal, reproducible local verification, CI verify workflow, protected `main` branch controls).
2. P0 baseline implementation present for:
- Region enforcement checks.
- Intro idempotency + immutable event path.
- Shadow credits deduction path.
- Consent checkpoints in public/trainer flows.
3. Ops auth runtime stabilized under Clerk + strict allowlist mode with automated preflight/allowlist scripts.
4. External account/platform setup status:
- Account creation/keys: complete for Clerk, Sentry, PostHog, Resend, Render, MongoDB Atlas, and Vercel.
- Runtime activation: not complete (Stage A blocked; see blockers below).
5. Deployment IaC baseline created: `render.yaml` defines `dtd-api` and `dtd-worker` services for deterministic rollout once billing gate is cleared.

Pending P0 before Beta gate:
1. Billing/dispute reason code implementation verification at API and audit-log level.
2. Control-plane auth migration finalization: hard-remove `OPS_ALLOW_ANY_SIGNED_IN` path once launch provisioning is complete.
3. Worker/queue separation of autonomous loops from API process.
4. Observability baseline (alerts, thresholds, safe-mode trigger wiring).
5. Staged infrastructure activation completion with evidence (runtime, observability, outbound comms, edge, deploy automation).

Current blockers (must be cleared before Stage A can pass):
1. Render service creation via API is blocked by billing gate (`HTTP 402 payment information required` on create service).
2. Local Docker runtime is constrained on founder machine; Stage A must run in remote-backend mode until local capacity is restored.
3. Atlas runtime connectivity must be validated from the active remote backend runtime (local-only TLS outcomes are not a release blocker while remote mode is active).

Locked execution hold (do not deviate):
1. External account creation is complete; gate advancement remains blocked until staged infrastructure activation is completed and verified.
2. No all-at-once infrastructure rollout; activation must follow the locked sequence below.

Execution policy (locked):
1. Local-first development.
2. One short-lived working branch at a time (`codex/*`), PR merge to protected `main`.
3. `scripts/verify_local.sh` and CI `Verify / verify` are required before merge.

Execution governance (efficiency-first):
1. Default route is native capabilities first (local edits, shell verification, local tests), then skills/plugins only when they materially reduce cycle time or reduce risk.
2. Skill/plugin fan-out must stay minimal and task-scoped; do not run broad exploratory stacks for narrow tasks.
3. External mutations (remote repo settings, third-party writes, paid API actions) remain explicit-gate actions.
4. Every roadmap work package must carry evidence links/commands in the same change that updates status.

Roadmap adherence status:
1. Process adherence: 100% (all active work is tied to documented decisions, gates, and verification steps).
2. Delivery completion: P0 partially complete; Beta gate not yet satisfied; Stage A currently FAIL.

## P0 Adherence Scorecard (current truth)

| Work package | Status | Evidence |
|---|---|---|
| Region enforcement | Complete | `backend/services/region_scope.py`, `backend/tests/test_p0_backend.py::test_region_scope_rules` |
| Intro ledger + idempotency | Complete | `backend/server.py` (`Idempotency-Key` flow + unique index), `backend/tests/test_p0_backend.py::test_intro_idempotency_returns_existing_and_no_duplicate_credit` |
| Shadow credits engine | Complete | `backend/services/credits.py`, `backend/tests/test_p0_backend.py::test_shadow_credits_record_once_and_do_not_change_balance` |
| Billing/dispute reason codes | Pending | Policy locked in `BILLING_AND_DISPUTES.md`; API reason-code implementation not yet present |
| Control-plane auth migration | In progress | Clerk RBAC + allowlist active; temporary bypass toggle still exists for dev bootstrap |
| Worker/queue separation | In progress | Dedicated `backend/worker.py` exists; queue/scheduler hardening still required by roadmap definition |
| Observability baseline | In progress | Stage B event evidence captured (Sentry probe events + PostHog key-event capture ACK); alert/safe-mode wiring still pending |
| Consent checkpoints UX | Complete | Consent gates in `backend/server.py` for match/intros/submissions + P0 tests |

## Scope Baseline

1. Region: Greater Melbourne (LGA allowlist in `REGION_SCOPE.md`).
2. Billing: intro-event credits only at launch (`1 credit = 1 valid intro`).
3. Launch mode: shadow credits first, paid stage later under soft-live caps.
4. Support: one-man, minimal support posture.

## Platform Baseline

1. App/worker hosting: Render.
2. Database: MongoDB Atlas.
3. Edge hosting + domain/TLS: Vercel.
4. Auth provider: Clerk + backend RBAC checks.
5. Email: Resend.
6. Observability: Sentry + PostHog + logs/metrics/alerts.
7. CI: GitHub Actions.

## Infrastructure Activation Sequence (locked)

Rule: account creation does not equal operational readiness. Activate infrastructure in strict order.

1. Runtime baseline (Stage A)
- Render API service + worker process + MongoDB Atlas connection established and stable.
- `/api/config`, `/ops`, and worker loop scheduling verified after restart.

2. Observability baseline (Stage B)
- Sentry backend/frontend DSNs wired and test events visible in both projects.
- PostHog event capture verified for key product events.

3. Outbound communications baseline (Stage C)
- Resend sender/domain verified.
- Controlled send test + delivery confirmation captured.

4. Edge and domain baseline (Stage D)
- Vercel project/domain/TLS/edge protections configured for target domains.
- Security posture validated (TLS active, intended DNS records live).

5. Deploy automation baseline (Stage E)
- Render backend/worker deployment + Vercel frontend deployment workflow repeatable with documented env mapping.
- Recovery/redeploy path validated without manual patching.

Gate rule:
1. No Beta/Soft-live gate claims until Stages A-E are complete with evidence logs.

Evidence update (2026-05-01 UTC):
1. Stage A: `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` => `RESULT=PASS`.
2. Stage B:
- Sentry backend/frontend DSN probes ingested (HTTP 200) and visible via Sentry project events API.
- PostHog capture ACK confirmed for `match_submit`, `connect_submit`, `submission_submit` via EU capture endpoint.
3. Stage C:
- Resend controlled send succeeded and message state reached `last_event=delivered`.

## Phase Plan

### P0 Foundations (build controls and truth)

Outcome: system can run safely in proof mode with immutable event evidence.

Work packages:
1. Region enforcement
- Implement strict LGA allowlist gating for all intake/connect flows.
- Done when out-of-region requests are consistently non-billable/rejected per policy.

2. Intro ledger + idempotency
- Implement immutable intro event ledger with idempotency key on each billable path.
- Done when duplicate delivery/retry does not create double deductions.

3. Shadow credits engine
- Implement credit ledger and shadow deduction flow (`1 valid intro = 1 shadow credit`).
- Done when all valid intros deduct exactly once and invalid intros deduct zero.

4. Billing/dispute reason codes
- Implement dispute reason model matching policy categories.
- Done when each dispute maps to a single allowed reason and audit trail.

5. Control-plane auth migration
- Migrate legacy passcode usage to Clerk-backed auth + RBAC checks.
- Done when sensitive controls are inaccessible without role authorization.

6. Worker/queue separation
- Move loops to dedicated worker service with queue/scheduler execution.
- Done when API process can restart without losing scheduled control loops.

7. Observability baseline
- Install alerts for P1/P2/P3 thresholds and safe-mode triggers.
- Done when synthetic incidents trigger expected alerts/actions.

8. Consent checkpoints UX
- Implement required public and trainer consent checkpoints.
- Done when consent events are logged and required before contact sharing.

Gate to enter P1 (Beta): all P0 packages complete.

Recommended execution order for remaining P0:
1. Stage A runtime baseline completion (Render + Atlas + worker reliability; currently blocked by billing and remote runtime evidence completion).
2. Control-plane auth migration finalization (remove temporary bypass path).
3. Stage B observability baseline completion (Sentry/PostHog evidence).
4. Stage C outbound communications baseline completion (Resend verified sender flow).
5. Stage D/E edge + deploy automation completion (Vercel + repeatable backend/frontend deploy path).
6. Billing/dispute reason code verification (commercial correctness lock-in).

Auth automation available now:
1. `scripts/ops_auth_preflight.sh` (readiness diagnostics).
2. `scripts/ops_auth_mode.sh dev|strict` (policy mode switch).
3. `scripts/ops_auth_allowlist_by_email.sh <email>` (auto-allowlist + strict mode cutover).

### P1 Beta (shadow-credit proof mode)

Outcome: production-like behavior without live charging, with measurable reliability.

Work packages:
1. Shadow run (minimum 14 days)
- Run live traffic in shadow-credit mode.
- Track would-have-billed totals, suppression rates, and dispute volume.

2. Threshold conformance checks
- Validate metrics against thresholds (`NUMERIC_THRESHOLDS.md`).
- Validate that P1 critical auto-freeze behavior works end-to-end.

3. Dispute flow rehearsal
- Run seeded dispute scenarios for each valid category.
- Confirm auto-credit behavior for objective categories.

4. Retention automation v1
- Enforce TTL/deletion/de-identification jobs per retention matrix.
- Confirm legal-hold override path works.

Gate to enter P2 (Soft-live):
1. Beta ran >=14 days.
2. No unresolved P1 incidents.
3. Billing mismatch <=0.8% over 7 consecutive days.
4. RBAC and consent logs verified.

### P2 Soft-Live (paid, capped)

Outcome: real intro-credit charging under strict financial/risk caps.

Work packages:
1. Enable paid credits
- Enable paid credit top-up flow and real credit deductions.
- Keep conversion billing disabled.

2. Enforce soft-live caps
- Apply max billed intros/day, revenue/day/week, and trainer/day caps.
- Hard stop additional deductions when caps are reached.

3. Paid-stage notifications
- Send trainer event notices and daily digests from live events.
- Ensure credit/reversal notices include reason codes.

4. Incident operations
- Run incident drills for 5xx surge, loop failures, and suppression spike.
- Verify auto-freeze and recovery procedure timing.

Gate to enter P3 (Full-live):
1. Soft-live ran >=30 days.
2. <=1 P1 incident in last 30 days.
3. Fraud/suppression behavior within policy thresholds.
4. Founder approves cap removal.

### P3 Full-Live (policy-governed scale)

Outcome: uncapped policy operation with ongoing governance and weekly tuning.

Work packages:
1. Remove soft-live caps (policy unlock)
- Remove only the temporary soft-live caps; keep threshold guardrails.

2. Weekly governance cycle
- Weekly review of threshold compliance, disputes, and anomaly trends.
- Update docs in place when approved changes occur.

3. Conversion billing review (future phase candidate)
- Keep conversion in track-only mode unless explicit policy update is approved.

## GitHub Execution Model (remote repo)

Milestones:
1. `P0 Foundations`
2. `P1 Beta`
3. `P2 Soft-Live`
4. `P3 Full-Live`

Issue template fields (required):
1. Decision refs (`D-*`, `C-*`, `T-*`).
2. Scope (`Region`, `Billing`, `Auth`, `Worker`, `UX`, `Legal`, `Observability`).
3. Done criteria (objective pass/fail).
4. Gate impact (Beta, Soft-live, Full-live).
5. Risk level (`low`, `medium`, `high`).

PR checklist (required):
1. Governance docs updated if policy/threshold/scope changed.
2. Tests added/updated for affected behavior.
3. Alerting impact reviewed.
4. Backward compatibility and migration notes included.

## Verification Requirements (always-on)

1. No roadmap item is complete without a testable done condition.
2. No gate advancement without metric evidence.
3. No policy change without in-place governance doc updates.
4. No production auth exceptions; legacy passcode path must be removed before full-live.

## Current Open Dependency

1. Final legal wording (`O-01`) must be completed before paid soft-live.
