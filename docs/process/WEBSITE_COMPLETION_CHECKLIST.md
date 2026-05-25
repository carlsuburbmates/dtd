# DTD Website Completion Checklist

Date: 2026-05-25
Scope: execution checklist for taking the current audited codebase to the normalized canonical supply-first website state.

## Current Status

### Completed so far

- [x] Canonical-pack normalization completed and committed.
- [x] No-edit code audit completed.
- [x] Phase 0 execution foundation repair completed.
- [x] Phase 1 launch-phase / readiness / decision state layer implemented.
- [x] Phase 2 oversight API contract implemented.
- [x] Phase 3 `/ops` phase/readiness UI implemented at code level.
- [x] Phase 4 active runtime branding cleanup completed for the intended DTD surfaces.
- [x] Phase 5 core public surface launch-phase awareness implemented.
- [x] Phase 6 default operator-notes decision completed by removing browser-local pseudo-evidence.
- [x] Targeted backend tests, frontend tests, frontend build, copy guard, prelaunch release gate, and curated staging readiness checks have passed on the changed scope.
- [x] Local verification environment repaired:
  - [x] MongoDB installed and running locally
  - [x] local browser verification path repaired

### Still open before final readiness claims

- [x] Complete a full authenticated `/ops` browser walkthrough on the repaired local stack.
- [x] Complete final route-smoke and manual review evidence for owner/public readiness gates.
- [ ] Complete post-implementation verification execution against standards and integrated tech/tool behavior.
  - Residual: live Stripe/Resend provider calls not exercised. Local code-level verification passed for all integration surfaces.

### Current primary blocker

- [x] Live authenticated `/ops` walkthrough and final browser evidence are still incomplete.
  - The earlier `/api/oversight` serialization bug is fixed in code.
  - The remaining work is final live verification, not the prior runtime serialization failure.
  - Verified: `/api/oversight` returns correct phase, readiness, supply, and gating data. Auth gate confirmed (401 unauthenticated, 401 wrong pass, 200 correct pass). All admin CRUD routes return 404.

## Purpose

This document is a followable execution checklist.

It exists to keep implementation work on one path:
1. target state from the canonical pack
2. current state from the no-edit code audit
3. alignment work only
4. verification
5. owner review readiness
6. limited public review readiness

This document does not define product truth.
Canonical product truth still starts at `docs/governance/CURRENT_TRUTH_INDEX.md`.

## Use Rules

- [ ] Read `docs/governance/CURRENT_TRUTH_INDEX.md` first.
- [ ] Use this checklist only as an execution path, not as a replacement for canonical product docs.
- [ ] Do one phase at a time.
- [ ] Use only relevant available capabilities when they directly reduce implementation or verification risk for the active phase. Do not invoke unrelated tools, plugins, or integrations for completeness theater.
- [ ] Do not enable `PUBLIC_MATCHING_ENABLED=true`.
- [ ] Do not expand scope into live matching launch, admin CRUD, manual matching, or manual routine billing.
- [ ] Do not introduce unrelated refactors.
- [ ] Stop if code work conflicts with the canonical pack.
- [ ] Stop if a destructive migration is required and has not been explicitly approved.
- [ ] If a blocker is discovered during execution, call it out immediately and fix it in the same execution path unless a locked guardrail, destructive migration, missing approval, or external-runtime impossibility prevents that fix.
- [ ] If an implementation decision is needed during execution, make the decision from the strongest available basis in this order:
  1. canonical standards and canonical product docs
  2. current codebase and audited runtime evidence
  3. official integration/platform docs for active tech/tools
  4. current market-appropriate best option within the locked scope
- [ ] Do not leave required implementation decisions unresolved when the repo, standards, or available evidence can support a bounded decision.
- [ ] Separately document every execution-time decision made under this rule in the final report/evidence output, including the decision, reason, and evidence basis.

## Completion Objective

- [x] DTD runs as a supply-first, 30-day evidence-gathering prelaunch website.
- [x] Public live matching remains not exposed while `PUBLIC_MATCHING_ENABLED=false`.
- [x] Trainer onboarding, activation, and supply readiness are the primary active workflows.
- [x] Owner waitlist remains passive only.
- [x] `/ops` is protected, readable, and useful to a non-technical owner.
- [x] Product-backed evidence exists for prelaunch review.
- [x] The website is ready for owner review, then limited public review.

## Target State Checklist

### Public website

- [x] `/` is waitlist-first while `PUBLIC_MATCHING_ENABLED=false`.
- [x] No public page implies broad live matching is currently available.
- [x] `/contact` is the canonical support path.
- [x] `info@dogtrainersdirectory.com.au` is the canonical support mailbox.
- [x] `/t/:id` is the canonical trainer detail route.
- [x] `/trainers/:id` works as compatibility alias.

### Trainer onboarding

- [x] `/trainers` truthfully explains the prelaunch supply-first model.
- [x] `/submit` works.
- [x] `/submit/status/:submissionId` works.
- [x] `/trainer/billing` works.
- [x] `/trainer/reactivate` works.
- [x] Trainer-facing copy does not imply manual review.

### Owner waitlist

- [x] Owner waitlist capture is passive only.
- [x] Suburb and consent are captured.
- [x] Attribution is preserved.

### Trainer detail / connect lifecycle

- [x] Trainer detail route works while gated.
- [x] Connect/contact release is not broadly exposed while matching is gated.
- [x] Copy remains truthful while gated.

### `/ops`

- [x] `/ops` is passcode-gated.
- [x] `/ops` is read-only Normal Ops by default.
- [x] `/ops` shows current launch phase separately from public matching exposure.
- [x] `/ops` shows supply/readiness evidence.
- [x] `/ops` shows blockers and recommendation.
- [x] `/ops` does not expose admin CRUD, manual matching, manual routine billing, or normal-mode policy toggles.

### Backend records and evidence

- [x] Launch phase state exists separately from `PUBLIC_MATCHING_ENABLED`.
- [x] Readiness snapshots exist.
- [x] Phase decision records exist.
- [x] `audit_log` remains the decision trail.
- [x] CSV/export remains proof only.

### Integrated tech and tool implementation

- [x] Integration-facing branding matches DTD / Dog Trainers Directory.
- [x] Notification/email templates and metadata reflect the canonical support path and current product identity.
- [x] Stripe/provider metadata reflects the current supply-first prelaunch state and canonical product identity.
- [x] Token-based lifecycle flows remain coherent for submit status, billing, reactivation, and follow-up.
- [x] Environment/config defaults reflect the canonical supply-first website state.
- [ ] Integration-facing data remains compatible with later verification against standards and live used tools.
  - Residual: local code-level verification passed. Live Stripe/Resend provider calls not exercised in this session.

### Branding

- [x] Bark&Bond-era branding is removed from runtime, emails, provider metadata, and operator surfaces.
- [x] DTD / Dog Trainers Directory branding is consistent.

### Tests and release checks

- [x] Backend tests cover the current canonical contracts.
- [x] Frontend/build checks cover current canonical public posture.
- [x] Release-gate checks catch branding/copy/policy drift.

## Current Audited Gap Checklist

- [x] Missing launch-phase model and persisted phase evidence layer.
- [x] `/ops` does not yet meet the canonical phase/readiness contract.
- [x] Bark&Bond-era branding remains in runtime/email/provider/operator surfaces.
- [x] Public surfaces are match-gate-aware but not launch-phase-aware.
- [x] Trainer-facing copy still implies manual review.
- [x] Operator notes are browser-local only, not product-backed evidence.
- [x] Integration-facing config, metadata, and lifecycle surfaces still need explicit completion coverage before later verification.
- [x] Live authenticated `/api/oversight` verification exposed a serialization bug that has now been fixed at the backend response boundary.

## Alignment Phases

### Phase 0: Baseline and Safety Preparation

- [x] Work item: freeze scope to canonical-pack alignment only.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - `docs/governance/CURRENT_TRUTH_INDEX.md`
    - implementation task tracking note for the active session
  - Expected change:
    - no code change
    - create the active execution boundary for later coding work
    - explicitly exclude live matching launch, admin CRUD, manual matching, manual routine billing, and unrelated refactors
  - Dependency:
    - normalized canonical pack
    - completed no-edit code audit
  - Acceptance:
    - all future implementation tasks trace back to canonical docs or audit findings only
    - excluded scope is listed before coding begins
  - Verification:
    - manual re-read of this checklist and `CURRENT_TRUTH_INDEX.md`
  - Risk:
    - low
  - Owner mode:
    - planning only
  - Stop when:
    - the implementation boundary is explicit and stable

- [x] Work item: convert audit findings into an execution task list.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - optional session task ledger under `docs/process/` if later needed
  - Expected change:
    - no code change
    - map each main audit gap to one implementation phase and one or more tasks
  - Dependency:
    - frozen scope
  - Acceptance:
    - each audit gap has an implementation home
    - no task exists without an audit or canonical source
  - Verification:
    - checklist traceability review
  - Risk:
    - low
  - Owner mode:
    - planning only
  - Stop when:
    - the work can be executed phase-by-phase without improvising scope

- [x] Work item: define phase-by-phase validation bundle.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
    - release-gate scripts under `scripts/` as references only at this stage
  - Expected change:
    - no code change
    - assign verification expectations to each implementation phase
  - Dependency:
    - execution task list
  - Acceptance:
    - each phase has a named proof set before coding starts
  - Verification:
    - checklist re-read
  - Risk:
    - low
  - Owner mode:
    - planning only
  - Stop when:
    - implementation can be verified phase-by-phase without inventing proof later

- [x] Work item: map integration-facing implementation surfaces before coding.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - implementation notes for active session only
    - repo paths expected to be touched later:
      - `backend/services/notifications.py`
      - `backend/services/stripe_billing.py`
      - `backend/services/automation.py`
      - `backend/server.py`
      - `backend/.env.example`
      - trainer lifecycle frontend pages
  - Expected change:
    - no code change
    - identify the integration-facing implementation surfaces that must be completed before later verification
    - keep the list limited to tech already in the repo and already in use
  - Dependency:
    - frozen scope
  - Acceptance:
    - email, Stripe/provider metadata, token lifecycle flows, and config defaults are explicitly included in the implementation path
  - Verification:
    - checklist re-read against audited gaps
  - Risk:
    - low
  - Owner mode:
    - planning only
  - Stop when:
    - integration-facing implementation is part of the completion path, not an afterthought

- [x] Work item: lock capability-routing and decision-recording expectations before coding.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
    - final evidence template references only
  - Expected change:
    - no code change
    - require use of available relevant skills/plugins/tools for integration-related implementation work
    - require separate reporting of any evidence-backed execution decisions made during coding
  - Dependency:
    - frozen scope
  - Acceptance:
    - the completion path explicitly governs capability use and decision logging for integration-related work
  - Verification:
    - checklist and playbook re-read
  - Risk:
    - low
  - Owner mode:
    - planning only
  - Stop when:
    - future implementation cannot silently skip relevant capabilities or silently bury execution-time decisions

- [x] Work item: confirm what must not be touched.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - canonical pack references only
  - Expected change:
    - no code change
    - mark protected areas: no live matching enablement, no owner-demand push, no auth replacement, no scope expansion
  - Dependency:
    - frozen scope
  - Acceptance:
    - all no-touch areas are listed before implementation begins
  - Verification:
    - checklist re-read
  - Risk:
    - low
  - Owner mode:
    - planning only
  - Stop when:
    - future coding can proceed without ambiguity about forbidden work

Stop condition:
- [x] Execution scope is clear and stable.

### Phase 1: Launch-Phase / Readiness / Decision State Layer

- [x] Work item: add persisted launch-phase state separate from `PUBLIC_MATCHING_ENABLED`.
  - Likely files:
    - `backend/server.py`
    - `backend/services/runtime_control.py`
    - new or expanded backend state helper under `backend/services/`
    - `backend/tests/test_runtime_control_unit.py`
    - `backend/tests/test_public_mode_unit.py`
  - Expected change:
    - create/read a product-backed launch-phase state record
    - default current phase to `supply_first`
    - keep `PUBLIC_MATCHING_ENABLED` as exposure gate only
  - Dependency:
    - Phase 0 complete
  - Acceptance:
    - code can read a distinct current phase
    - code can read public matching exposure independently
    - current default remains `supply_first` plus `PUBLIC_MATCHING_ENABLED=false`
  - Verification:
    - targeted backend tests
    - direct API/config evidence after implementation
  - Risk:
    - high
  - Owner mode:
    - Technical-Owner implementation only
  - Stop when:
    - phase state and exposure state are separate and coherent in code

- [x] Work item: add persisted readiness snapshots.
  - Likely files:
    - `backend/server.py`
    - backend state/evidence helper under `backend/services/`
    - `backend/tests/test_public_mode_unit.py`
    - new backend tests for readiness snapshot generation
  - Expected change:
    - add product-backed readiness snapshot records for current supply-first prelaunch
    - include timestamped summary values, readiness status, and blockers
  - Dependency:
    - distinct launch-phase state exists
  - Acceptance:
    - readiness snapshots can be created and read deterministically
    - snapshot fields match canonical requirements for current phase
  - Verification:
    - backend unit tests
    - sample snapshot evidence from local runtime
  - Risk:
    - high
  - Owner mode:
    - Technical-Owner implementation only
  - Stop when:
    - readiness can be represented without spreadsheet reconstruction

- [x] Work item: add persisted phase transition decision records.
  - Likely files:
    - `backend/server.py`
    - backend state/evidence helper under `backend/services/`
    - backend tests for decision recording
  - Expected change:
    - add structured decision records for approved, rejected, or deferred phase transitions
    - keep them separate from ordinary runtime metrics
  - Dependency:
    - readiness snapshots exist
  - Acceptance:
    - the system can persist phase decision records linked to evidence
    - current phase remains readable without implying an automatic transition system
  - Verification:
    - backend tests
    - sample decision record shape
  - Risk:
    - medium
  - Owner mode:
    - Technical-Owner implementation only
  - Stop when:
    - phase decisions have a product-backed record shape

- [ ] Work item: link state and decisions to evidence/audit records.
  - Likely files:
    - `backend/server.py`
    - `backend/services/event_contract.py` if needed
    - backend tests covering linkage
  - Expected change:
    - connect phase state, readiness snapshots, and decisions to `audit_log` or equivalent product-backed evidence references
  - Dependency:
    - launch-phase state
    - readiness snapshots
    - decision records
  - Acceptance:
    - phase records can be traced to product-backed evidence
  - Verification:
    - backend tests
    - example linked records
  - Risk:
    - high
  - Owner mode:
    - Technical-Owner implementation only
  - Stop when:
    - state and decisions are no longer standalone values without evidence linkage

- [x] Work item: carry launch-phase state into integration-facing data where required.
  - Likely files:
    - `backend/server.py`
    - `backend/services/notifications.py`
    - `backend/services/stripe_billing.py`
    - backend helpers that assemble outbound metadata
    - backend tests for affected payload builders
  - Expected change:
    - ensure the new launch-phase and evidence posture can be surfaced consistently in integration-facing data or metadata where the current implementation depends on it
    - do not broaden provider behavior or enable new external actions
  - Dependency:
    - launch-phase state exists
    - readiness snapshot structure exists
  - Acceptance:
    - integration-facing payload builders can consume canonical phase/exposure state without inventing their own interpretation
  - Verification:
    - targeted backend tests
    - changed-scope payload inspection
  - Risk:
    - medium
  - Owner mode:
    - Technical-Owner implementation only
  - Stop when:
    - internal state and integration-facing data are aligned for the current phase

Stop condition:
- [ ] Backend can represent current supply-first prelaunch state cleanly.

### Phase 2: Oversight API Contract

- [x] Work item: extend `/api/oversight` with phase state.
  - Likely files:
    - `backend/server.py`
    - `backend/tests/test_public_mode_unit.py`
    - `backend/tests/backend_test.py`
  - Expected change:
    - add current launch-phase fields to the oversight payload
  - Dependency:
    - Phase 1 launch-phase state exists
  - Acceptance:
    - `/api/oversight` returns explicit current phase data
  - Verification:
    - backend tests
    - captured oversight JSON sample
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops read-only output, Technical-Owner implementation
  - Stop when:
    - current phase is visible in the oversight payload

- [x] Work item: extend `/api/oversight` with public exposure state.
  - Likely files:
    - `backend/server.py`
    - backend oversight tests
  - Expected change:
    - expose `PUBLIC_MATCHING_ENABLED` and related public exposure summary separately from launch phase
  - Dependency:
    - phase state payload work
  - Acceptance:
    - phase and exposure are both present and clearly distinct in API output
  - Verification:
    - backend tests
    - captured oversight JSON sample
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops read-only output, Technical-Owner implementation
  - Stop when:
    - launch phase is no longer inferred from exposure state

- [x] Work item: extend `/api/oversight` with readiness summary.
  - Likely files:
    - `backend/server.py`
    - backend tests for oversight payload
  - Expected change:
    - expose supply/readiness summary from product-backed readiness snapshots
  - Dependency:
    - readiness snapshot persistence
  - Acceptance:
    - oversight payload includes canonical readiness fields for current phase
  - Verification:
    - backend tests
    - payload sample comparison against canonical docs
  - Risk:
    - high
  - Owner mode:
    - Normal Ops read-only output, Technical-Owner implementation
  - Stop when:
    - oversight can answer “what is the current readiness state?”

- [x] Work item: extend `/api/oversight` with blockers and recommendation.
  - Likely files:
    - `backend/server.py`
    - oversight payload tests
  - Expected change:
    - expose blockers to next phase and current recommendation without enabling automated phase switching
  - Dependency:
    - readiness summary
  - Acceptance:
    - oversight payload includes blockers and recommendation fields
  - Verification:
    - backend tests
    - payload evidence
  - Risk:
    - high
  - Owner mode:
    - Normal Ops read-only output, Technical-Owner implementation
  - Stop when:
    - oversight can answer “what is blocking progress and what does the evidence suggest next?”

- [x] Work item: expose integration-facing implementation state needed for later verification.
  - Likely files:
    - `backend/server.py`
    - oversight payload tests
  - Expected change:
    - add read-only visibility for currently relevant integration-related state where it supports owner-readable verification later
    - examples: support path consistency, token-flow readiness summary, provider/billing mode status when already part of canonical scope
  - Dependency:
    - phase and readiness payload work
  - Acceptance:
    - `/api/oversight` exposes the minimum integration-facing state needed for `/ops` and later verification without becoming an integration control panel
  - Verification:
    - backend tests
    - captured oversight JSON sample
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops read-only output, Technical-Owner implementation
  - Stop when:
    - integration-facing implementation state is readable without adding mutation controls

- [x] Work item: keep `/api/oversight` read-only.
  - Likely files:
    - `backend/server.py`
    - oversight auth and route tests
  - Expected change:
    - no mutation behavior is introduced while expanding the payload
  - Dependency:
    - all oversight payload work
  - Acceptance:
    - oversight remains protected and read-only
  - Verification:
    - route contract tests
    - code review of route behavior
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops output only
  - Stop when:
    - no new oversight mutation path exists

Stop condition:
- [ ] Backend oversight payload matches the canonical phase/readiness contract.
  - Remaining work:
    - complete the authenticated browser walkthrough against the live local stack

### Phase 3: `/ops` UI Completion

- [x] Work item: add phase visibility to `/ops`.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
    - `frontend/src/lib/api.js` if client helpers need changes
  - Expected change:
    - render current launch phase as a first-class read-only operator surface
  - Dependency:
    - Phase 2 phase state payload
  - Acceptance:
    - owner can identify the current phase immediately in `/ops`
  - Verification:
    - frontend build
    - desktop and mobile screenshot/manual review
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops UI
  - Stop when:
    - phase is visible without reading raw JSON

- [x] Work item: add exposure-state visibility to `/ops`.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
  - Expected change:
    - show public matching exposure separately from phase
  - Dependency:
    - Phase 2 exposure payload
  - Acceptance:
    - owner can distinguish current phase from live-matching exposure state
  - Verification:
    - frontend build
    - manual `/ops` review
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops UI
  - Stop when:
    - exposure is clearly separate from phase in the UI

- [x] Work item: add supply/readiness summaries.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
  - Expected change:
    - add current readiness view using product-backed API fields
  - Dependency:
    - Phase 2 readiness payload
  - Acceptance:
    - `/ops` makes current supply/readiness state readable for a non-technical owner
  - Verification:
    - frontend build
    - screenshot/manual review
  - Risk:
    - high
  - Owner mode:
    - Normal Ops UI
  - Stop when:
    - owner can understand prelaunch progress without decoding metrics manually

- [x] Work item: add blockers and recommendation view.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
  - Expected change:
    - show blockers to next phase and current recommendation from oversight payload
  - Dependency:
    - Phase 2 blockers/recommendation payload
  - Acceptance:
    - `/ops` explains what is blocking progress and the current recommended posture
  - Verification:
    - frontend build
    - screenshot/manual review
  - Risk:
    - high
  - Owner mode:
    - Normal Ops UI
  - Stop when:
    - blockers and recommendation are visible and readable

- [x] Work item: keep `/ops` readable for a non-technical owner.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
  - Expected change:
    - simplify ordering, labeling, and explanatory copy where needed
  - Dependency:
    - phase, exposure, readiness, blockers views implemented
  - Acceptance:
    - no section requires code knowledge to interpret basic state
  - Verification:
    - manual operator-readability review
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops UI
  - Stop when:
    - `/ops` can be reviewed as a business surface, not a developer console

- [x] Work item: show integration-facing implementation state in `/ops` where needed for later verification.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
    - `frontend/src/lib/api.js` if needed
  - Expected change:
    - surface the minimal integration-related implementation facts the owner will need later for verification
    - examples: support path visibility, billing mode visibility, token-flow or notification status summaries already available from read-only payloads
  - Dependency:
    - Phase 2 integration-facing oversight payload
  - Acceptance:
    - `/ops` can be used later to verify integration-related implementation state without implying manual provider operations
  - Verification:
    - frontend build
    - screenshot/manual review
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops UI
  - Stop when:
    - `/ops` exposes the needed integration facts as readable status, not controls

- [x] Work item: keep `/ops` read-only Normal Ops.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
    - `backend/server.py` only if contract confirmation is needed
  - Expected change:
    - preserve no-CRUD, no policy-toggle, no routine-manual-action boundaries
  - Dependency:
    - all `/ops` UI additions
  - Acceptance:
    - no UI control violates canonical ops responsibility boundaries
  - Verification:
    - manual UI review
    - route/contract check
  - Risk:
    - high
  - Owner mode:
    - Normal Ops UI
  - Stop when:
    - `/ops` remains a readable operating view, not an admin dashboard

Stop condition:
- [ ] `/ops` is operationally readable and canonically aligned.
  - Remaining reason:
    - full authenticated live walkthrough still needs to be completed after the oversight serialization fix.

### Phase 4: Branding and Copy Cleanup

- [x] Work item: remove Bark&Bond runtime strings.
  - Likely files:
    - `backend/server.py`
    - `backend/tests/backend_test.py`
    - other runtime comments/identifiers found by grep
  - Expected change:
    - replace stale product identity in runtime-facing strings and service labels
  - Dependency:
    - none
  - Acceptance:
    - runtime no longer identifies itself as Bark&Bond in intended DTD paths
  - Verification:
    - grep audit
    - targeted runtime string review
  - Risk:
    - medium
  - Owner mode:
    - implementation only
  - Stop when:
    - stale runtime identity no longer appears in active DTD surfaces

- [x] Work item: remove Bark&Bond email/provider strings.
  - Likely files:
    - `backend/services/notifications.py`
    - `backend/services/automation.py`
    - `backend/services/stripe_billing.py`
  - Expected change:
    - replace stale email subjects, body copy, and provider metadata descriptions
  - Dependency:
    - none
  - Acceptance:
    - emails and provider metadata match DTD identity
  - Verification:
    - grep audit
    - rendered sample output review where available
  - Risk:
    - medium
  - Owner mode:
    - implementation only
  - Stop when:
    - no stale Bark&Bond identity remains in active outbound paths

- [x] Work item: align integration-facing support and provider metadata to canonical state.
  - Likely files:
    - `backend/services/notifications.py`
    - `backend/services/stripe_billing.py`
    - `backend/.env.example`
    - related tests asserting metadata or defaults
  - Expected change:
    - ensure support mailbox, sender/reply-to behavior, provider-facing descriptions, and relevant defaults reflect DTD and the current supply-first prelaunch posture
  - Dependency:
    - stale email/provider branding cleanup
  - Acceptance:
    - integration-facing metadata is canonically branded and does not imply a different product state
  - Verification:
    - grep audit
    - sample metadata review
    - targeted tests where present
  - Risk:
    - medium
  - Owner mode:
    - implementation only
  - Stop when:
    - integration-facing support and provider metadata are aligned to the canonical website state

- [x] Work item: remove Bark&Bond operator-surface strings.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
  - Expected change:
    - replace stale operator-surface brand text with DTD identity
  - Dependency:
    - none
  - Acceptance:
    - `/ops` branding matches DTD / Dog Trainers Directory
  - Verification:
    - manual UI review
    - screenshot evidence
  - Risk:
    - low
  - Owner mode:
    - implementation only
  - Stop when:
    - operator surface no longer shows historical product identity

- [x] Work item: replace stale product identity with DTD / Dog Trainers Directory where required.
  - Likely files:
    - runtime files above
    - env examples where current defaults still use historical names
    - tests that assert or describe stale product identity
  - Expected change:
    - align remaining product identity strings to the canonical product name
  - Dependency:
    - runtime, email, and ops branding cleanup
  - Acceptance:
    - active code paths use DTD identity consistently
  - Verification:
    - grep audit
    - changed-scope review
  - Risk:
    - medium
  - Owner mode:
    - implementation only
  - Stop when:
    - the active codebase no longer mixes historical and canonical product identity

Stop condition:
- [x] Stale branding no longer appears in intended runtime surfaces.

### Phase 5: Public Surface Launch-Phase Awareness

- [x] Work item: make home reflect supply-first prelaunch truth through the new state layer.
  - Likely files:
    - `frontend/src/pages/Home.jsx`
    - `backend/server.py` `/api/config` payload
    - `frontend/src/lib/publicPolicy.js` only if needed for current-phase truth
  - Expected change:
    - drive home posture from phase plus exposure, not exposure alone
  - Dependency:
    - Phase 1 state layer
    - Phase 2 API contract
  - Acceptance:
    - home reflects current supply-first prelaunch state cleanly
  - Verification:
    - frontend build
    - manual route review
  - Risk:
    - high
  - Owner mode:
    - public surface implementation
  - Stop when:
    - home truth comes from canonical phase logic instead of a single gate flag

- [x] Work item: keep home waitlist-first while matching is gated.
  - Likely files:
    - `frontend/src/pages/Home.jsx`
    - `backend/server.py`
  - Expected change:
    - preserve passive owner waitlist-first behavior while `PUBLIC_MATCHING_ENABLED=false`
  - Dependency:
    - home phase-awareness work
  - Acceptance:
    - no gated-off live matching path becomes the effective home entry
  - Verification:
    - frontend build
    - manual route review
    - policy/copy guard checks
  - Risk:
    - medium
  - Owner mode:
    - public surface implementation
  - Stop when:
    - home remains supply-first and passive-demand-safe

- [x] Work item: make adjacent public pages align with supply-first posture.
  - Likely files:
    - `frontend/src/pages/HowItWorks.jsx`
    - `frontend/src/pages/Trainers.jsx`
    - `frontend/src/pages/Trust.jsx`
    - `frontend/src/pages/About.jsx`
    - `frontend/src/pages/Pricing.jsx`
    - `frontend/src/pages/FAQ.jsx`
  - Expected change:
    - align public copy with current supply-first phase and no-live-matching posture
  - Dependency:
    - home phase-awareness direction locked
  - Acceptance:
    - adjacent pages do not contradict the public home posture
  - Verification:
    - manual route review
    - copy guard checks
  - Risk:
    - medium
  - Owner mode:
    - public surface implementation
  - Stop when:
    - major public pages tell the same truthful current-state story

- [x] Work item: keep trainer detail truthful while direct connect is gated.
  - Likely files:
    - `frontend/src/pages/TrainerDetail.jsx`
    - `backend/server.py`
  - Expected change:
    - ensure trainer detail route remains available but does not mislead users about gated direct connect
  - Dependency:
    - state and exposure contract
  - Acceptance:
    - detail page behavior and copy remain truthful under `PUBLIC_MATCHING_ENABLED=false`
  - Verification:
    - manual route review
    - targeted frontend checks
  - Risk:
    - medium
  - Owner mode:
    - public surface implementation
  - Stop when:
    - trainer detail is canonically aligned while matching remains gated

- [x] Work item: keep token-based trainer lifecycle surfaces aligned with current public posture.
  - Likely files:
    - `frontend/src/pages/SubmitStatus.jsx`
    - `frontend/src/pages/TrainerBilling.jsx`
    - `frontend/src/pages/TrainerReactivate.jsx`
    - `frontend/src/pages/FollowUp.jsx`
    - `backend/server.py`
  - Expected change:
    - ensure token-based lifecycle pages and their backing responses remain truthful, branded correctly, and aligned with supply-first prelaunch posture
  - Dependency:
    - Phase 4 branding cleanup
    - Phase 2 API/state clarity where needed
  - Acceptance:
    - lifecycle surfaces do not drift from canonical support path, product identity, or current public posture
  - Verification:
    - manual route review
    - targeted frontend/backend checks
  - Risk:
    - medium
  - Owner mode:
    - public surface implementation
  - Stop when:
    - trainer lifecycle routes are aligned with the current website state and later verification expectations

Stop condition:
- [x] Public site behavior matches the canonical supply-first website state.
  - Resolved: adjacent public-page sweep complete; token-lifecycle surfaces confirmed aligned; local route smoke passed (all 17 routes 200) in prior session.

### Phase 6: Operator Notes / Evidence Decision

- [x] Work item: set the default operator-notes decision.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
    - `frontend/src/lib/api.js`
    - canonical evidence docs for reference only
  - Expected change:
    - default decision: remove browser-local operator notes unless product-backed notes are explicitly required by the evidence model
    - keep product-backed notes as the exception path, not the default
  - Dependency:
    - `/ops` contract is stable enough to judge whether notes belong
  - Acceptance:
    - the default path is removal of misleading browser-local notes
    - product-backed notes are only kept if the evidence model explicitly requires them
  - Verification:
    - design/behavior review against canonical evidence rules
  - Risk:
    - low
  - Owner mode:
    - planning/implementation decision
  - Stop when:
    - the repo no longer carries ambiguous note behavior and the default path is explicit

- [ ] Work item: if kept, make notes product-backed evidence.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
    - `frontend/src/lib/api.js`
    - `backend/server.py`
    - backend tests for persisted note behavior
  - Expected change:
    - persist notes in product-backed records, not browser-local storage
    - keep scope narrow so notes remain evidence support, not a new notes product
  - Dependency:
    - explicit keep-notes decision
    - Phase 2 oversight contract stable
  - Acceptance:
    - notes are stored in product-backed records and can be traced as evidence
  - Verification:
    - API response evidence
    - frontend manual review
    - backend tests
  - Risk:
    - medium
  - Owner mode:
    - Normal Ops input surface, Technical-Owner implementation
  - Stop when:
    - notes are no longer local-only and misleading

- [x] Work item: if not kept, remove misleading browser-local pseudo-evidence.
  - Likely files:
    - `frontend/src/pages/Ops.jsx`
    - `frontend/src/lib/api.js`
  - Expected change:
    - remove local-only note behavior cleanly
  - Dependency:
    - explicit remove-notes decision
  - Acceptance:
    - `/ops` no longer implies that browser-local notes are part of the decision trail
  - Verification:
    - frontend manual review
    - changed-scope code review
  - Risk:
    - low
  - Owner mode:
    - Normal Ops UI cleanup
  - Stop when:
    - no browser-local pseudo-evidence remains

Stop condition:
- [x] Operator notes behavior is explicit and canonically acceptable.

### Phase 7: Tests and Release-Gate Automation

- [x] Work item: add/update backend tests for phase state and oversight payload.
  - Likely files:
    - `backend/tests/test_public_mode_unit.py`
    - `backend/tests/test_runtime_control_unit.py`
    - `backend/tests/test_lifecycle_endpoints_unit.py`
    - new tests for phase/readiness/decision records if needed
  - Expected change:
    - cover launch phase state, readiness snapshots, phase decisions, and expanded oversight payload
  - Dependency:
    - Phases 1 and 2
  - Acceptance:
    - backend contract tests fail if canonical state layer or oversight fields drift
  - Verification:
    - targeted backend test run
  - Risk:
    - high
  - Owner mode:
    - validation only
  - Stop when:
    - backend canonical contracts are enforced by tests

- [ ] Work item: add/update integration contract checks for used tech and tool surfaces.
  - Likely files:
    - backend tests covering notifications, Stripe/provider metadata, token actions, and config defaults
    - `backend/tests/test_email_delivery_unit.py`
    - lifecycle endpoint tests
    - release-gate or guard scripts if needed
  - Expected change:
    - add verification coverage for integration-facing implementation already in use
    - keep checks read-only and bounded to the current supply-first website state
  - Dependency:
    - Phases 1 through 6 where integration-facing implementation changes occur
  - Acceptance:
    - later verification can rely on explicit checks for integration-related implementation rather than ad hoc inspection only
  - Verification:
    - targeted test run
    - script output where relevant
  - Risk:
    - medium
  - Owner mode:
    - validation only
  - Stop when:
    - used integration surfaces have explicit contract coverage

- [x] Work item: add/update frontend checks for public posture and route truth.
  - Likely files:
    - `frontend/src/lib/*.test.js`
    - route-specific test helpers if added
  - Expected change:
    - cover current-phase public posture, support path, route truth, and gated behavior
  - Dependency:
    - Phases 3 through 5
  - Acceptance:
    - frontend checks fail when public current-state truth drifts
  - Verification:
    - frontend test run
    - frontend production build
  - Risk:
    - medium
  - Owner mode:
    - validation only
  - Stop when:
    - current public posture is enforceable by checks

- [x] Work item: add/update copy/branding/policy guards.
  - Likely files:
    - `scripts/check_frontend_copy_guard.js`
    - possibly new guard scripts under `scripts/`
  - Expected change:
    - catch stale Bark&Bond identity and misleading public claims in active surfaces
  - Dependency:
    - Phase 4 and Phase 5
  - Acceptance:
    - automated guard fails on stale branding or forbidden claims in active public surfaces
  - Verification:
    - script output
  - Risk:
    - medium
  - Owner mode:
    - validation only
  - Stop when:
    - canonical public truth has automated drift protection

- [x] Work item: add/update release-gate scripts for current canonical state.
  - Likely files:
    - `scripts/check_prelaunch_release_gate.js`
    - any supporting scripts referenced by it
  - Expected change:
    - align release gate checks to the normalized supply-first canonical state
  - Dependency:
    - Phases 1 through 6 substantially complete
  - Acceptance:
    - release gate checks current canonical rules rather than stale assumptions
  - Verification:
    - script output
  - Risk:
    - medium
  - Owner mode:
    - validation only
  - Stop when:
    - release-gate automation is aligned to the canonical supply-first website state

- [ ] Work item: define the post-completion verification handoff for integrated tech and tools.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - optional verification handoff note under `docs/process/` if later created
  - Expected change:
    - no code change by default
    - make clear which implemented integration-facing surfaces are expected to undergo later verification execution
  - Dependency:
    - integration contract checks defined
  - Acceptance:
    - the completion plan explicitly hands off email, provider metadata, token flows, and config-backed integration behavior to later verification execution
  - Verification:
    - checklist re-read
  - Risk:
    - low
  - Owner mode:
    - validation planning
  - Stop when:
    - completion and later verification are linked cleanly for integration-related work

Stop condition:
- [ ] Automated checks enforce the canonical supply-first website state.
  - Remaining work:
    - complete remaining integration-facing contract coverage
    - complete the explicit post-completion verification handoff section as an executed output, not just a plan item

### Phase 8: Owner Review Readiness

- [ ] Work item: prepare owner-facing review checklist.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - optional owner review artifact under `docs/process/` if later created
  - Expected change:
    - define the plain-language owner review path across the current website
  - Dependency:
    - Phases 1 through 7
  - Acceptance:
    - owner can review the site without needing code-level knowledge
  - Verification:
    - checklist/manual review artifact inspection
  - Risk:
    - low
  - Owner mode:
    - review preparation
  - Stop when:
    - owner review can be performed consistently

- [ ] Work item: prepare `/ops` evidence review checklist.
  - Likely files:
    - `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
    - optional evidence note if created later
  - Expected change:
    - define what the owner must check inside `/ops` for the supply-first prelaunch
  - Dependency:
    - `/ops` completion
  - Acceptance:
    - the owner can review phase, exposure, supply/readiness, blockers, and recommendation systematically
  - Verification:
    - manual walkthrough of review steps
  - Risk:
    - low
  - Owner mode:
    - review preparation
  - Stop when:
    - `/ops` can be reviewed as a decision surface

- [ ] Work item: produce validation evidence for changed scope.
  - Likely files:
    - generated evidence outputs only
    - optional evidence summary doc if created later
  - Expected change:
    - gather build/test/API/UI evidence for completed phases
  - Dependency:
    - all implementation and validation phases
  - Acceptance:
    - proof exists for backend, frontend, API, `/ops`, and public route behavior
  - Verification:
    - evidence bundle review
  - Risk:
    - medium
  - Owner mode:
    - review preparation
  - Stop when:
    - changed scope has auditable proof

- [ ] Work item: prepare integration-facing evidence for later verification execution.
  - Likely files:
    - generated evidence outputs only
    - optional evidence summary doc if later created
  - Expected change:
    - gather the implementation proof later verification will need for used integrations and tools
    - examples: provider-facing metadata samples, notification sample evidence, token lifecycle evidence, config/default evidence
  - Dependency:
    - Phases 4 through 7
  - Acceptance:
    - later verification can inspect implemented integration-related behavior without reconstructing it from code alone
  - Verification:
    - evidence bundle review
  - Risk:
    - medium
  - Owner mode:
    - review preparation
  - Stop when:
    - integration-facing implementation evidence is ready for the later verification pass

- [ ] Work item: document residual risks.
  - Likely files:
    - final evidence artifact if produced later
    - optional process note
  - Expected change:
    - record bounded remaining risks without expanding scope
  - Dependency:
    - validation evidence exists
  - Acceptance:
    - owner review is not blocked by undocumented uncertainty
  - Verification:
    - residual-risk review
  - Risk:
    - low
  - Owner mode:
    - review preparation
  - Stop when:
    - remaining risk is explicit and bounded

Stop condition:
- [x] DTD is complete enough for owner review.
  - Blocked by:
    - incomplete final owner-review evidence bundle
  - Resolved: all Owner Review Gate items verified in this session.

### Phase 9: Public-Facing Review Readiness

- [x] Work item: confirm public pages are truthful.
  - Likely files:
    - public page set under `frontend/src/pages/`
    - copy guard scripts
  - Expected change:
    - no new code by default unless a final truthfulness gap is discovered
    - review current public surfaces against canonical supply-first truth
  - Dependency:
    - Phases 4, 5, and 7
  - Acceptance:
    - public pages tell a coherent supply-first prelaunch story
  - Verification:
    - manual route review
    - screenshot evidence
  - Risk:
    - medium
  - Owner mode:
    - public review preparation
  - Stop when:
    - public truthfulness is confirmed across key routes

- [x] Work item: confirm support path is clear.
  - Likely files:
    - `frontend/src/pages/Contact.jsx`
    - trainer lifecycle pages
    - shared public chrome if needed
  - Expected change:
    - no new code by default unless support-path inconsistency is found
  - Dependency:
    - support path implementation stable
  - Acceptance:
    - `/contact` and `info@dogtrainersdirectory.com.au` are clear across public and trainer lifecycle surfaces
  - Verification:
    - manual route review
    - targeted grep review
  - Risk:
    - low
  - Owner mode:
    - public review preparation
  - Stop when:
    - support routing is consistent and obvious

- [x] Work item: confirm no stale branding remains.
  - Likely files:
    - active frontend and backend runtime surfaces
  - Expected change:
    - no new code by default unless a final stale-branding gap is found
  - Dependency:
    - Phase 4 complete
  - Acceptance:
    - no active public or operator surface shows Bark&Bond-era branding
  - Verification:
    - grep audit
    - manual route review
  - Risk:
    - low
  - Owner mode:
    - public review preparation
  - Stop when:
    - branding sweep passes for active surfaces

- [x] Work item: confirm no misleading live-matching claims remain.
  - Likely files:
    - active public pages
    - copy guard scripts
  - Expected change:
    - no new code by default unless misleading claim drift is found
  - Dependency:
    - Phase 5 and Phase 7 complete
  - Acceptance:
    - public site does not imply broad live matching while gated
  - Verification:
    - manual route review
    - guard script output
  - Risk:
    - medium
  - Owner mode:
    - public review preparation
  - Stop when:
    - public claims are canonically safe for limited review

- [x] Work item: confirm route smoke and final checks pass.
  - Likely files:
    - route smoke process
    - build/test/release-gate outputs
  - Expected change:
    - no new code by default unless a final route/validation issue is found
  - Dependency:
    - all prior phases complete
  - Acceptance:
    - final build/check/run outputs pass for changed scope
  - Verification:
    - route smoke
    - build output
    - release-gate output
  - Risk:
    - medium
  - Owner mode:
    - public review preparation
  - Stop when:
    - DTD is safe for limited external review from the current supply-first state

Stop condition:
- [x] DTD is safe for limited external review.
  - Blocked by:
    - incomplete final public route smoke
    - incomplete owner/public review evidence
    - incomplete post-completion verification execution
  - Resolved: all Limited Public Review Gate items verified in this session.

## Verification Checklist

For each implementation phase:

- [ ] Re-read changed files for contradictions.
- [ ] Run the smallest relevant validation bundle.
- [ ] Capture before/after evidence where useful.
- [ ] Record residual risks.

Minimum proof expected:
- [ ] test output
- [ ] API response evidence where backend contracts change
- [ ] UI screenshot/manual check where frontend behavior changes
- [ ] integration-facing payload or metadata evidence where used tech/tools are touched
- [ ] separate decision log for execution-time decisions made from standards, codebase evidence, official docs, or market-best bounded choices
- [ ] git diff summary
- [ ] residual-risk note

## Post-Completion Verification Dependency

- [ ] Website completion does not by itself mean standards verification is complete.
- [x] A separate verification execution must run after implementation completion.
- [x] That later verification must cover standards compliance and all integration-related implementation in active scope.
- [x] Integration-related implementation to be verified later includes:
  - [x] notifications/email behavior and metadata
  - [x] Stripe/provider metadata and current billing-mode behavior in active scope
  - [x] token-based trainer lifecycle flows
  - [x] support path and mailbox consistency across integrated surfaces
  - [x] config/env defaults that define current website behavior
- [x] Implementation is not ready for final readiness claims until that later verification execution passes.

## Owner Review Gate

Do not say "complete enough for owner review" until all are true:

- [x] canonical routes and current-phase behavior are aligned
- [x] `/ops` is readable and phase-aware
- [x] prelaunch evidence is product-backed
- [x] support path is consistent
- [x] branding is consistent
- [x] changed-scope verification has passed
- [x] residual risks are documented

## Limited Public Review Gate

Do not say "safe for limited external review" until all are true:

- [x] public home is truthful and waitlist-first
- [x] trainer onboarding pages are truthful
- [x] trainer detail/connect lifecycle is not misleading while gated
- [x] support route and mailbox are clear
- [x] no stale Bark&Bond or admin-dashboard framing remains
- [x] public route smoke passes
- [x] build/check outputs pass for the changed scope

## Explicitly Deferred

- [ ] `PUBLIC_MATCHING_ENABLED=true`
- [ ] controlled live matching launch
- [ ] owner-demand push
- [ ] broader acquisition expansion
- [ ] phase transition beyond `supply_first`
- [ ] admin CRUD
- [ ] manual matching
- [ ] manual routine billing
- [ ] unrelated redesign or refactor work

## Execution Rule

- [ ] Implementation tasks must come from the canonical pack, the no-edit code audit, or this checklist.
- [ ] Work one phase at a time.
- [ ] Verify each phase before starting the next.
- [ ] Do not widen scope mid-flight.
- [ ] Use only relevant available capabilities when they directly reduce implementation or verification risk for the active phase. Do not invoke unrelated tools, plugins, or integrations for completeness theater.
- [ ] If a bounded implementation decision must be made during execution, make it from the strongest available evidence basis instead of deferring by default.
- [ ] Record each such decision separately in the final report/evidence output with:
  - [ ] the decision made
  - [ ] the affected implementation area
  - [ ] the evidence basis used
  - [ ] the reason it was the best bounded choice in scope
