# DTD Website Completion Checklist

Date: 2026-06-08
Scope: execution checklist for taking the current DTD website and operator
surface through the remaining activation and final approval work.

## Purpose

This document is the active execution checklist.

It exists to:
1. sequence work
2. define execution boundaries
3. hold route/workflow/verification tasks in one place
4. point to the authoritative docs that define what complete means

It does not define:
1. current project status
2. current blockers
3. current priority order outside execution sequencing
4. product truth
5. workflow completion truth
6. `/ops` product behavior

Use these authorities first:
1. `docs/governance/CURRENT_TRUTH_INDEX.md`
2. `docs/standards/SSOT.md`
3. `docs/governance/WORKFLOW_COMPLETION_SPEC.md`
4. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`
5. `docs/governance/OPERATIONS_CONSOLE_SPEC.md`
6. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`
7. `docs/governance/EXECUTION_STATUS.md`

Use `docs/governance/EXECUTION_STATUS.md` for the active phase and current
decision state. This file holds the executable sequence only.

## Use Rules

- [ ] Use this checklist as execution control only.
- [ ] Do one execution phase at a time.
- [ ] Use relevant available capabilities only when they reduce implementation or verification risk for the active phase.
- [ ] Do not enable `PUBLIC_MATCHING_ENABLED=true` unless the active phase explicitly requires it and approval exists.
- [ ] Do not expand scope into broad admin CRUD, manual matching, manual routine billing, or unrelated refactors.
- [ ] Do not let this file redefine workflow completion or `/ops` behavior.
- [ ] If an execution-time decision is needed, decide from the strongest available basis in this order:
  1. canonical standards and product docs
  2. workflow completion truth
  3. current codebase and runtime evidence
  4. official integration/platform docs for active tools
- [ ] Record every bounded execution-time decision separately in the final evidence output.

## Completion Objective

- [ ] DTD operates as a supply-first, 30-day evidence-gathering prelaunch website.
- [ ] Public live matching remains governed by the approved current launch posture.
- [ ] Trainer onboarding, activation, and supply readiness remain the primary active workflows.
- [ ] Owner waitlist behavior remains passive during the current launch phase.
- [ ] `/ops` remains protected, readable, useful to a non-technical owner, and bounded to Normal Ops by default.
- [ ] Workflow completion is judged from `docs/governance/WORKFLOW_COMPLETION_SPEC.md`, not from page existence alone.
- [ ] Launch approval is judged from `docs/standards/LAUNCH_GATE.md`, not from implementation momentum alone.

## Target State Checklist

### Public website

- [ ] `/` matches the approved current launch posture.
- [ ] No public page implies broader live matching than is actually approved.
- [ ] `/contact` remains the canonical support path.
- [ ] `info@dogtrainersdirectory.com.au` remains the canonical support mailbox.
- [ ] `/t/:id` remains the canonical trainer-detail route.
- [ ] `/trainers/:id` remains a compatibility alias.

### Trainer lifecycle

- [ ] `/trainers` truthfully explains the supply-first model.
- [ ] `/submit` remains usable.
- [ ] `/submit/status/:submissionId` remains usable.
- [ ] `/trainer/billing` remains usable.
- [ ] `/trainer/reactivate` remains usable.
- [ ] Trainer-facing copy does not imply manual review where the workflow is automated.

### Owner waitlist

- [ ] Waitlist capture remains passive during the current phase.
- [ ] Suburb and consent remain captured.
- [ ] Attribution remains preserved.

### Trainer detail / connect lifecycle

- [ ] Trainer detail route remains coherent under the current launch posture.
- [ ] Connect/contact release behavior remains truthful under the current gate.
- [ ] Downstream engagement and follow-up lifecycle remains coherent.

### `/ops`

- [ ] `/ops` remains passcode-gated.
- [ ] `/ops` remains visibility-first and Normal Ops by default.
- [ ] `/ops` preserves bounded Layer 1 review-state persistence, owner note, and review history.
- [ ] `/ops` continues to show current launch phase separately from public matching exposure.
- [ ] `/ops` continues to show supply/readiness evidence, blockers, and recommendation.
- [ ] `/ops` does not expose admin CRUD, manual routine billing, manual matching, or public-exposure toggles in Normal Ops.
- [ ] `/ops` preserves the current page structure:
  - `Overview`
  - `Work Queue`
  - `Trainer Supply`
  - `Messages`
  - `Billing & Reactivation`
  - `System Activity`
  - `Recent Changes`

### Backend records and evidence

- [ ] Launch phase state remains separate from `PUBLIC_MATCHING_ENABLED`.
- [ ] Readiness snapshots remain available.
- [ ] Phase decision records remain available.
- [ ] `audit_log` remains the decision trail.
- [ ] CSV/export remains proof only, not the operating source of truth.

### Integrated tech and tool implementation

- [ ] Integration-facing branding matches DTD / Dog Trainers Directory.
- [ ] Notification/email templates and metadata remain aligned to the canonical support path and current product identity.
- [ ] Token-based lifecycle flows remain coherent for submit status, billing, reactivation, and follow-up.
- [ ] Environment/config defaults remain aligned to the approved current website state.

### Branding

- [ ] Legacy Bark&Bond-era runtime/operator/provider branding does not reappear in active surfaces.

### Tests and release checks

- [ ] Backend tests cover the current canonical contracts.
- [ ] Frontend/build checks cover the current approved public posture.
- [ ] Release-gate checks catch branding/copy/policy drift.

## Execution Phases

### Phase 1: Trust And Environment Recovery

- [x] clean up contaminated/reset-era drift
- [x] lock seed behavior
- [x] sync local with the real deployment path
- [x] make verification meaningful again against one trusted behavior path

### Phase 2: Workflow Verification Against Clean State

- [x] verify launch-critical workflows from `WORKFLOW_COMPLETION_SPEC.md`
- [x] verify route- and page-level behavior from `COMPLETE_WEBSITE_PAGE_SPEC.md`
- [x] verify `/ops` against the clean synced state without degrading current operator behavior

### Phase 3: Launch Readiness Proof

- [x] capture the required launch evidence window
- [x] satisfy `LAUNCH_GATE.md` for the hosted-path non-provider scope
- [x] record the bounded Phase 3 Go/No-Go outcome with explicit evidence

### Phase 4: Actual-Domain Activation Slice

- [ ] complete live trainer submission E2E on the actual-domain path
- [ ] complete live provider exercise for notification and billing-coupled paths
- [ ] verify `/ops` and runtime evidence remain coherent after the provider-coupled activation checks

### Phase 5: Final Launch Approval

- [ ] confirm `LAUNCH_GATE.md` is satisfied with the actual-domain activation evidence
- [ ] record the final explicit owner Go/No-Go decision in governance evidence
- [ ] keep deferred Ops power out of scope unless final launch approval exists

## Final Activation Verification

Do not treat this block as complete until feature and workflow completion are already established.

- [ ] capture a final activation evidence window proving:
  - no stale core loop beyond `2x` interval
  - no unresolved `severity:high` alerts during that window
- [ ] complete supply-first launch verification with explicit activation evidence
- [ ] defer matching-enabled public release evidence to the later controlled live-matching phase
- [ ] record the explicit final Go/No-Go decision in governance evidence

## Should-Finish For Operator Takeover

- [ ] verify the current `/ops` clarity pass in real owner use and tighten labels only where genuine confusion remains
- [ ] replace misleading trainer lifecycle CTAs where they imply pseudo-new submissions instead of contextual lifecycle recovery
- [ ] unify support-routing language across public and trainer-support surfaces
- [ ] keep Owner Override and Technical-Owner controls deferred until the visibility model and trust model remain stable under real use

## Nice-To-Have Cleanup

- [ ] add in-product operator note logging for daily checks if it improves the one-man operating model without changing responsibility boundaries
- [ ] improve `/ops` severity visuals for stale loops and aging alerts
- [ ] clean stale evidence artifacts that can confuse current-proof review
- [ ] tighten deployment/runtime docs so single-owner loop topology is completely unambiguous

## Verification Checklist

- [ ] Re-read changed docs for contradictions.
- [ ] Verify all referenced files and routes still exist.
- [ ] Verify `CURRENT_TRUTH_INDEX.md` reflects the actual surviving documentation set.
- [ ] Verify `EXECUTION_STATUS.md` is the sole current-state controller.
- [ ] Verify `WORKFLOW_COMPLETION_SPEC.md` is the sole workflow-completion authority.
- [ ] Verify `/ops` wording still preserves bounded Layer 1 review-state persistence.
- [ ] Verify no surviving doc implies broader live matching than the approved current posture.
