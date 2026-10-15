# Codex Independent Audit — Matching P0 Acquisition Dependency Repair

**Initial audited commit:** `f4b5f25938f044dbfc257088b147e9fc9b4e5073`
**Re-audited commit:** `d0098d124e0f4d6062e7e044971a38bf4b9da8cc`
**Final audited commit:** `ce14f4eeba6c675fce0997385800a8ec543d9ba9`
**Base:** `e7a990e2a85182b170967bf4dffd6002d27b7aa4`
**Current classification:** `DONE` — P0 acquisition-dependency remediation is accepted. P1 is authorised for local implementation only; matching cutover and every environment action remain blocked.

## Independently accepted P0 items

1. **Manual ingestion mutation route:** `POST /api/oversight/jobs/trainer-ingest` and the associated Ops action are absent. The authenticated internal scheduler boundary remains.
2. **Claim-session protection:** `GET /api/trainers/{id}/capabilities/prefill` now requires a valid, trainer-bound claim session or the existing administrative path; missing and mismatched session tests pass.
3. **Source-evidence invalidation:** refresh failure now checks `source_evidence_url` as well as legacy source fields; the focused regression test passes.
4. **Projection cutover:** default `ENABLE_MATCH_READY_PROJECTION_FILTER` evaluates to `False` in the audited checkout. This is not live-runtime verification and does not authorise cutover.

## Original rework required before acceptance

### R1 — truthful scheduler and Operations language

`frontend/src/pages/Ops.jsx` still states “Scheduled execution via Cloud Scheduler”, despite the active current-state and acquisition specifications correctly stating that live scheduler configuration is unverified. `docs/specs/SANDBOX_VERIFICATION_MATRIX.md` also still says the sandbox scheduler/jobs path is triggered through `/ops`, although the mutation route has been removed.

Change both surfaces to distinguish repository capability from verified runtime state. The Ops panel may show read-only ingestion telemetry, but it must not imply a live schedule. Update or add frontend coverage for the revised operator-visible copy; update the verification matrix so it does not direct an operator to a removed `/ops` action.

### R2 — actual trainer control of delivery constraints

The confirmation form initialises and submits `delivery_constraints`, but provides no input, checkbox or other control that can change it. It therefore always submits an empty object. `delivery_constraints` is an explicit matchable capability category with `in_home_available`, `facility_available`, `travel_distance_km` and bounded `notes` in `trainer_quality.py`.

Add a clear, mobile-accessible declaration control for those supported fields, preserve prefill values, and test that an edited value reaches `POST /api/trainers/{id}/capabilities/confirm` and is stored as a validated trainer declaration. Do not introduce a new free-text capability taxonomy or enable radius matching; this is only the existing structured constraints object.

## Initial audit evidence

- Exact commit is a child of the required matching-contract base and has a clean diff check.
- Re-run on the exact Antigravity checkout: 61 focused backend tests passed; 280 backend unit tests passed; 35 frontend tests passed; production frontend build passed.
- Browser visual acceptance was not run because the changed trainer declaration workflow is already functionally incomplete. It is required after R2, alongside the existing test/build checks.
- No provider, deployment, billing, authentication, data or remote-Git mutation was performed by this audit.

## First rework return

Commit only the two corrections above on `feature/matching-implementation`. Return the commit SHA, changed-file list, exact tests, browser evidence for the trainer declaration UI, data/migration effects (expected: none) and confirmation of no external mutations. Codex will then re-audit P0 before authorising P1.

## Re-audit of `d0098d1`

### Independently accepted in this re-audit

1. **R1 — truthful scheduler and Operations language:** `Ops.jsx` now describes a repository capability and explicitly says live cloud scheduling is unverified. The sandbox matrix now identifies the authenticated internal endpoint instead of a removed `/ops` action. The updated Ops test covers both the new copy and absence of the earlier claim.
2. **R2 — trainer delivery-constraint controls:** the authenticated prefill → claim form → confirmation endpoint → persisted capability fact → match-ready projection path now carries the four existing fields. Desktop and mobile artifacts show the controls render coherently; the focused frontend/backend tests exercise an edited payload and the stored projection.
3. **Regression boundary:** the exact commit is a child of `f4b5f25`, has a clean diff check and keeps `ENABLE_MATCH_READY_PROJECTION_FILTER` false by default. This does not verify a deployed runtime or authorise matching cutover.

### R3 — fail-closed delivery-constraint data contract

The new UI should not turn unknown or malformed data into a positive matching capability. Direct inspection of `d0098d1` shows that a trainer with no existing declared constraints is defaulted to `in_home_available: true`, while the API model accepts an arbitrary dictionary and the normaliser converts non-empty strings such as `"false"` to `true`. It also accepts negative or unbounded travel distance and silently truncates overlong notes. Those values are saved as a `trainer_declaration` fact permitted in the projection.

Make this a narrow data-contract repair, without changing matching cutover, adding taxonomy, enabling distance/radius matching, or changing any provider/runtime state:

1. Make `delivery_constraints` a server-owned, explicit schema. Boolean fields must be actual booleans; distance must be finite and within the UI's existing `0..200` constraint; notes must be a bounded, trimmed string and overlong input must be rejected rather than silently changed.
2. Where there is no already permitted, evidenced delivery declaration, do not preselect in-home availability as true. The conservative initial form and fallback value must not create a positive in-home capability merely because the trainer has not supplied one.
3. Preserve existing permitted prefill values exactly for correction. Do not alter the existing claim-session protection or historic invalidation behaviour.
4. Add regression coverage for: valid values flowing to the projection; string booleans, negative/out-of-range/non-finite distance and overlong notes being rejected before persistence; and an unprefilled claim not producing a positive in-home declaration by default.

### Re-audit evidence

- Direct reproduction on the exact commit: `TrainerCapabilitiesConfirmIn` accepted `{"in_home_available": "false", "facility_available": "false", "travel_distance_km": -1}` and the normaliser produced both availability values as `true`; `999999` was also accepted as a valid distance.
- Independently rerun from the exact checkout: 61 focused backend tests passed; 280 backend unit tests passed; 35 frontend tests passed from `frontend/`; and the production frontend build passed. Passing tests do not cover the malformed-input boundary above.
- The supplied Playwright desktop and mobile captures were visually inspected. They corroborate the R2 controls but do not change the server-side acceptance result.
- No provider, deployment, billing, authentication, data or remote-Git mutation was performed by this audit.

## Final re-audit of `ce14f4e`

### R3 accepted

1. **Fail-closed schema:** direct string boolean, numeric boolean, non-finite, negative and out-of-range distance, and overlong-note cases are rejected before capability persistence. Valid values are canonicalised and reach the match-ready projection.
2. **Conservative unknown state:** an unprefilled claim presents both delivery options as false and an untouched confirmation cannot create an in-home-positive fact.
3. **Correction path:** a permitted existing declaration is preserved for trainer review and correction.
4. **UI evidence:** supplied desktop captures were independently inspected for both the unprefilled and edited-prefill paths. They show the expected unchecked and populated states respectively.
5. **Regression verification:** on the exact commit, 65 focused backend tests, 284 backend unit tests, 36 frontend tests, and the frontend production build passed. `git diff --check d0098d1..ce14f4e` was clean.

### Acceptance boundary and next authorised package

P0 is an accepted prerequisite only. It does not make the match-ready foundation or matching pipeline complete, does not enable `ENABLE_MATCH_READY_PROJECTION_FILTER`, and does not verify any deployed runtime. Antigravity may now implement **P1 — Contract fixtures and test harness** exactly as specified in `ANTIGRAVITY_MATCHING_PIPELINE_IMPLEMENTATION_HANDOFF.md`. It must remain local-only and return the exact commit and evidence for a fresh Codex audit before P2.
