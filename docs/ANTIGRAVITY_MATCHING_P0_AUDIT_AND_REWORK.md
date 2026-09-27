# Codex Independent Audit — Matching P0 Acquisition Dependency Repair

**Audited commit:** `f4b5f25938f044dbfc257088b147e9fc9b4e5073`  
**Base:** `e7a990e2a85182b170967bf4dffd6002d27b7aa4`  
**Classification:** `PARTIAL` — do not advance to P1 or any environment.

## Independently accepted P0 items

1. **Manual ingestion mutation route:** `POST /api/oversight/jobs/trainer-ingest` and the associated Ops action are absent. The authenticated internal scheduler boundary remains.
2. **Claim-session protection:** `GET /api/trainers/{id}/capabilities/prefill` now requires a valid, trainer-bound claim session or the existing administrative path; missing and mismatched session tests pass.
3. **Source-evidence invalidation:** refresh failure now checks `source_evidence_url` as well as legacy source fields; the focused regression test passes.
4. **Projection cutover:** default `ENABLE_MATCH_READY_PROJECTION_FILTER` evaluates to `False` in the audited checkout. This is not live-runtime verification and does not authorise cutover.

## Rework required before acceptance

### R1 — truthful scheduler and Operations language

`frontend/src/pages/Ops.jsx` still states “Scheduled execution via Cloud Scheduler”, despite the active current-state and acquisition specifications correctly stating that live scheduler configuration is unverified. `docs/specs/SANDBOX_VERIFICATION_MATRIX.md` also still says the sandbox scheduler/jobs path is triggered through `/ops`, although the mutation route has been removed.

Change both surfaces to distinguish repository capability from verified runtime state. The Ops panel may show read-only ingestion telemetry, but it must not imply a live schedule. Update or add frontend coverage for the revised operator-visible copy; update the verification matrix so it does not direct an operator to a removed `/ops` action.

### R2 — actual trainer control of delivery constraints

The confirmation form initialises and submits `delivery_constraints`, but provides no input, checkbox or other control that can change it. It therefore always submits an empty object. `delivery_constraints` is an explicit matchable capability category with `in_home_available`, `facility_available`, `travel_distance_km` and bounded `notes` in `trainer_quality.py`.

Add a clear, mobile-accessible declaration control for those supported fields, preserve prefill values, and test that an edited value reaches `POST /api/trainers/{id}/capabilities/confirm` and is stored as a validated trainer declaration. Do not introduce a new free-text capability taxonomy or enable radius matching; this is only the existing structured constraints object.

## Audit evidence

- Exact commit is a child of the required matching-contract base and has a clean diff check.
- Re-run on the exact Antigravity checkout: 61 focused backend tests passed; 280 backend unit tests passed; 35 frontend tests passed; production frontend build passed.
- Browser visual acceptance was not run because the changed trainer declaration workflow is already functionally incomplete. It is required after R2, alongside the existing test/build checks.
- No provider, deployment, billing, authentication, data or remote-Git mutation was performed by this audit.

## Required Antigravity return

Commit only the two corrections above on `feature/matching-implementation`. Return the commit SHA, changed-file list, exact tests, browser evidence for the trainer declaration UI, data/migration effects (expected: none) and confirmation of no external mutations. Codex will then re-audit P0 before authorising P1.
