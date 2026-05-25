# Runtime Evidence Alignment Matrix

Date: 2026-05-24 (re-verified 2026-05-25)
Scope: docs-only mapping from canonical supply-first standards to current runtime/code evidence, current docs/evidence references, concrete gaps, and next actions.
Re-verification scope: all previously-Missing rows re-checked against `backend/server.py`, `backend/services/engine.py`, `frontend/src/pages/Ops.jsx`, and `backend/tests/test_public_mode_unit.py` at commit `a180b12`+.

## Purpose

This matrix answers one question:

> Where do the current standards already have runtime/code evidence, and where are they still only documented targets?

It is intentionally evidence-first.
If a requirement is documented but no current runtime/code evidence was found in the inspected surfaces, this matrix marks that gap explicitly.

## Primary Authorities Used

1. `docs/governance/CURRENT_TRUTH_INDEX.md`
2. `docs/standards/SSOT.md`
3. `docs/standards/BUILD_CHECKLIST.md`
4. `docs/standards/LAUNCH_GATE.md`
5. `docs/standards/INTEGRITY_AUDIT.md`
6. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`
7. `docs/governance/LOCK_STATE.md`
8. `docs/governance/ROADMAP.md`
9. `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`
10. `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`

## Runtime / Code Surfaces Inspected

1. `backend/server.py`
2. `backend/services/runtime_control.py`
3. `backend/services/engine.py`
4. `backend/services/automation.py`
5. `backend/tests/test_public_mode_unit.py`
6. `backend/tests/test_lifecycle_endpoints_unit.py`
7. `frontend/src/pages/Home.jsx`
8. `frontend/src/pages/Ops.jsx`
9. `frontend/src/App.js`
10. `frontend/src/lib/api.js`
11. `scripts/check_prelaunch_release_gate.js`
12. `.env.example`
13. `backend/.env.example`

## Status Legend

- `Implemented`: current runtime/code evidence was found for the requirement.
- `Partial`: some runtime/code evidence exists, but the full standards requirement is not yet evidenced.
- `Missing`: no current runtime/code evidence was found in the inspected surfaces.
- `Deferred later phase`: intentionally not a current supply-first blocker; belongs to later controlled live-matching work.

## Highest-Confidence Alignment Summary

1. Implemented now:
- public matching exposure gate
- owner waitlist capture
- trainer acquisition/submission/activation paths
- intro/contact-release path behind gate
- intro-first billing and revenue visibility
- lease-guarded loop ownership
- read-only `/ops`
- audit logging for many state-changing actions

2. Phase/readiness layer — confirmed implemented (re-verified 2026-05-25):
- `PUBLIC_LAUNCH_PHASE` env var and `PUBLIC_LAUNCH_PHASE` runtime symbol: `backend/server.py:104`
- `_get_or_create_launch_phase_state()` persists `launch_phase_state` to `system_state` collection: `backend/server.py:832-852`
- `_build_phase_readiness_snapshot()` and `_upsert_latest_phase_readiness_snapshot()`: `backend/server.py:900-961`
- `phase_transition_decisions` collection writes with audit linkage: `backend/server.py:968-994`
- `/ops` surfaces phase, exposure gate, supply readiness, intro-ready count, blocked-trainer count, recommendation, and blockers-to-next-phase: `frontend/src/pages/Ops.jsx:255-270`, `backend/server.py:920-946`
- Phase-state/readiness/decision tests: `backend/tests/test_public_mode_unit.py:582`

3. Main remaining gaps (non-blocking for supply-first):
- waitlist duplicate/rejected rollup not yet in `_owner_waitlist_summary()` (events persisted, no aggregate exposed)
- ops note logging is browser-local only — not backend-persisted or audit-safe
- trainer acquisition trend series is current-count only — no historical series
- release-gate script does not yet assert phase/readiness symbols (addressed in `scripts/check_prelaunch_release_gate.js` re-verification 2026-05-25)

4. Conclusion (re-verified 2026-05-25):
- docs/governance alignment and runtime/evidence alignment are now consistent for supply-first posture
- all previously-Missing High-risk blocking items have been implemented
- remaining gaps are Medium or Low risk and are not supply-first blockers

## 1. Public Exposure And Launch Posture

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Public live matching exposure is runtime-controlled | `SSOT.md`, `LAUNCH_GATE.md`, `LOCK_STATE.md` | Home exposure must be explicitly gated and consistent across backend, frontend, tests, and public copy | `backend/server.py` defines `PUBLIC_MATCHING_ENABLED`, exposes it from `GET /api/config`, gates `POST /api/match` and `POST /api/intros`; `frontend/src/pages/Home.jsx` consumes `/config`; `backend/tests/test_public_mode_unit.py` asserts config and gate behavior | `docs/governance/LOCK_STATE.md`, `docs/governance/ROADMAP.md`, `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` | Implemented | Low | Keep as-is and preserve doc/runtime sync | Normal Ops for monitoring; Technical-Owner Mode for changes | No |
| Launch phase remains separate from matching exposure | `SSOT.md`, `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Runtime should represent launch phase separately from `PUBLIC_MATCHING_ENABLED` | `PUBLIC_LAUNCH_PHASE` env var read at `backend/server.py:104`; `_get_or_create_launch_phase_state()` persists phase state to `system_state` at `server.py:832-852`; oversight exposes `launch_phase_state` at `server.py:2406`; `/ops` surfaces phase separately from matching gate | Docs repeatedly state the separation rule, especially `LOCK_STATE.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `BUILD_CHECKLIST.md` | Implemented | Low | Keep as-is | Normal Ops for monitoring; Technical-Owner Mode for changes | No |
| Current approved posture is supply-first with public matching off | `LOCK_STATE.md`, `ROADMAP.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Runtime should make the current approved posture inspectable in product-backed evidence | `launch_phase_state` persisted with `current_phase=supply_first`, `public_matching_enabled=false`, `public_emphasis=waitlist_first` at `server.py:810-852`; exposed in oversight and `/ops` | `docs/governance/LOCK_STATE.md`, `docs/process/NEXT_SESSION_HANDOFF.md` | Implemented | Low | Keep as-is | Normal Ops for reading; Technical-Owner Mode for changes | No |

## 2. Phase Records

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| `launch_phase_state` or equivalent exists | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Persist current phase, exposure state, onboarding state, waitlist state, public emphasis, updated-by, updated-at, reason, and audit linkage | `_default_launch_phase_state()` defines schema at `server.py:810`; `_get_or_create_launch_phase_state()` persists/reads from `system_state` collection at `server.py:832-852`; oversight exposes snapshot at `server.py:2406`; `test_public_mode_unit.py:582` asserts contract | Docs define the requirement and field set | Implemented | Low | Keep as-is | Normal Ops for reading; Technical-Owner Mode for changes | No |
| `phase_readiness_snapshots` exist | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Persist readiness snapshots with supply, blockers, alert state, loop health, recommendation, and evidence timestamp | `_build_phase_readiness_snapshot()` at `server.py:900`; `_upsert_latest_phase_readiness_snapshot()` writes to `phase_readiness_snapshots` collection at `server.py:951`; oversight exposes snapshot; tests assert shape | Docs define readiness-snapshot requirement and use it as a launch gate | Implemented | Low | Keep as-is | Normal Ops for reading; Technical-Owner Mode for changes | No |
| `phase_transition_decisions` exist and link to audit evidence | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Persist approved/rejected/deferred phase decisions with reason, decision maker, snapshot ref, timestamp, rollback note, and audit linkage | `phase_transition_decisions` collection writer at `server.py:968-994`; records `from_phase`, `to_phase`, `reason`, `decision_maker`, `snapshot_ref`, `audit_id`, and `timestamp`; audit-linked via `_audit()` | Docs define the approval gate and required decision fields | Implemented | Low | Keep as-is | Normal Ops for reading; Technical-Owner Mode for changes | No |

## 3. Supply-First Readiness

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Supply readiness is visible from product-backed evidence | `SSOT.md`, `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | `/ops` should show enough product-backed data to judge supply readiness without DB inspection | `backend/server.py` exposes `kpi_prelaunch`, `submissions_summary`, `integrity`, `reactivation_summary`; `frontend/src/pages/Ops.jsx` renders those surfaces | `docs/governance/ROADMAP.md`, `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`, `docs/governance/LOCK_STATE.md` | Partial | Medium: some supply evidence exists, but not a clear readiness decision surface | Add explicit supply-readiness status, recommendation, and blocker rows | Normal Ops for review; Technical-Owner Mode for changing underlying policy | Yes |
| Intro-ready trainer count is visible | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | `/ops` should expose intro-ready trainer count or equivalent direct signal | `_build_phase_readiness_snapshot()` queries `intro_ready_trainer_count` and persists it at `server.py:865-893`; oversight exposes it at `server.py:932`; `Ops.jsx:264` renders count in the supply-readiness section | Docs require intro-ready visibility in `/ops` | Implemented | Low | Keep as-is | Normal Ops | No |
| Blocked trainer count and blocker reasons are visible | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | `/ops` should show blocked count and why supply is blocked | `blocked_trainer_count` and `blockers_to_next_phase` included in readiness snapshot at `server.py:933`; `Ops.jsx:266-268` renders blocked count and blockers list | Docs require blocked-trainer visibility and blocker reasons | Implemented | Low | Keep as-is | Normal Ops | No |
| Geography coverage is inspectable for supply decisions | `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Supply evidence should expose target geography coverage | `backend/server.py` exposes active regions via `/api/config`, and `kpi_prelaunch` includes trainer/waitlist suburb coverage counts | `docs/governance/LOCK_STATE.md`, `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` | Partial | Medium: count exists, but not enough locality detail for phase decisions | Add clearer supply-by-geo visibility in oversight and `/ops` | Normal Ops | No |

## 4. Trainer Acquisition And Activation

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Trainer acquisition path stays open during supply-first launch | `SSOT.md`, `BUILD_CHECKLIST.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Trainer onboarding remains available even when public live matching is gated | Routes exist in `frontend/src/App.js`; `Home.jsx` always links to `/trainers`; `PUBLIC_MATCHING_ENABLED` gates owner match/contact path only | `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Trainer submission, publish/hold decision, and activation start are implemented | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `COMPLETE_WEBSITE_PAGE_SPEC.md` | Submission must persist, auto-publish/hold, and start activation state | `POST /api/submissions` path and decision logic exist in `backend/server.py`; tests back the status path | `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep tests/docs aligned | Normal Ops | No |
| Activation and remediation are understandable to trainers | `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `LAUNCH_GATE.md`, `COMPLETE_WEBSITE_PAGE_SPEC.md` | Submission status, billing remediation, and reactivation path must expose blockers and next actions | `GET /api/submissions/{id}/status`, `GET/POST /api/trainer/billing*`, and `/api/trainer/reactivate*` exist; `test_lifecycle_endpoints_unit.py` covers activation states and token-protected remediation | `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Founder can see trainer acquisition and activation trend in `/ops` | `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | `/ops` should expose trend and usable supply, not just route existence | `/ops` shows `submissions_summary` and reactivation summary, but no explicit trainer acquisition trend series or intro-ready trend was found | Docs require trend visibility | Partial | Medium | Add trend-backed supply cards and readiness summary | Normal Ops | No |

## 5. Passive Owner Waitlist

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Passive owner waitlist capture exists | `SSOT.md`, `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md` | Owners can join waitlist when live matching is gated | `POST /api/owner-waitlist` persists records; `Home.jsx` renders waitlist-first form when `public_matching_enabled=false` | `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Waitlist records preserve suburb and attribution context | `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Waitlist row should preserve suburb, campaign/source, and attribution context | `backend/server.py` stores suburb, campaign, source, `utm_*`; updates `growth_attribution.waitlist_joins_30d` | `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Normalized waitlist event trail exists | `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Started/submitted/duplicate/rejected events should be persisted | `_record_owner_waitlist_event()` writes `owner_waitlist_events`; `test_public_mode_unit.py` covers event shape and duplicate/reject handling | `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| `/ops` shows enough passive-demand evidence | `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | `/ops` should show volume, trend, duplicates/rejections, suburb demand, and attribution | `/ops` shows waitlist size, joins 24h, top suburbs, and growth cohorts; no dedicated duplicate/rejected waitlist counts were found in oversight or `/ops` | `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`, `docs/governance/LOCK_STATE.md` | Partial | Medium | Add duplicate/rejected waitlist monitoring and clearer demand trend visibility | Normal Ops | No |

## 6. Intro Path Readiness Without Public Live Exposure

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Matching path exists as a product capability | `LAUNCH_GATE.md`, `COMPLETE_WEBSITE_PAGE_SPEC.md`, `LOCK_STATE.md` | Owner match path exists even if not currently exposed from home | `/api/match`, trainer detail, intro, engagement, conversion, and follow-up paths exist; `frontend/src/App.js` routes remain active | `docs/governance/LOCK_STATE.md`, `docs/governance/ROADMAP.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Public live exposure is still gated during supply-first | `LOCK_STATE.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md` | Matching and contact release should be unavailable from public path when exposure is off | `backend/server.py` calls `_require_public_matching()` for match and intro/contact release; tests assert gated behavior | `docs/governance/LOCK_STATE.md`, `docs/governance/ROADMAP.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Connect flow enforces consent, idempotency, and persists intro | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Valid connect should create intro and reveal contact only after consent | `POST /api/intros` enforces consent, idempotency, fraud evaluation, intro persistence, billing metadata, and contact reveal | `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| `/ops` shows explicit intro-path readiness signal while still gated | `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Founder should be able to inspect intro-path readiness without enabling broad live exposure | No dedicated intro-path-readiness or contact-reveal-readiness panel was found in oversight or `/ops` | Docs require this signal for supply-first evidence | Missing | Medium | Add explicit intro-path readiness summary to oversight and `/ops` | Normal Ops | No |

## 7. Billing / Revenue Readiness

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Intro-first monetization is explicit and config-backed | `LOCK_STATE.md`, `ROADMAP.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Runtime should expose intro-first defaults and current conversion mode | `/api/config` exposes `trainer_free_intro_days`, `conversion_billing_mode`, Stripe-enabled flags; env examples default to `track_only` | `docs/governance/LOCK_STATE.md`, `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Billing collection, webhook reconciliation, and retry lifecycle are product-backed | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `LOCK_STATE.md` | Intro billing should persist lifecycle state and recovery state | `backend/server.py` and Stripe services persist billing states, recovery state, and webhook receipts; tests cover billing semantics and retry states | `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| `/ops` shows booked, collected, at-risk, trial-free, and remediation states | `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Founder can see where money is booked, collected, or stuck | `GET /api/oversight` returns revenue, `billing_summary`, `non_billable_causes`, recovery cases; `frontend/src/pages/Ops.jsx` renders those sections | `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |

## 8. `/ops` Visibility And Normal Ops Boundary

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| `/ops` is read-only and passcode-gated | `SSOT.md`, `LAUNCH_GATE.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | `/ops` should be a Normal Ops surface by default, protected by oversight auth, without mutation controls | `POST /api/oversight/login`, `GET /api/oversight` with `require_oversight`; `Ops.jsx` shows read-only snapshot and no runtime mutation buttons | `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| `/ops` stays outside unrestricted admin CRUD | `SSOT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | No unrestricted admin surface should be active | `frontend/src/App.js` redirects legacy admin routes; `Ops.jsx` is read-only; no admin CRUD endpoint was found in inspected runtime surfaces | `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| `/ops` shows phase, exposure, supply readiness, intro-ready, blocked, recommendation, and blockers | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Required launch-governance visibility should be directly readable in `/ops` | `Ops.jsx` launch-posture section surfaces `launch_phase`, `public_matching_enabled`, `recommendation`, `intro_ready_trainer_count`, `blocked_trainer_count`, `blockers_to_next_phase` (lines 255–270); backed by oversight payload at `server.py:920-946` | Docs require these as first-check fields | Implemented | Low | Keep as-is | Normal Ops for reading; Technical-Owner Mode for changing state | No |
| `/ops` note logging is product-backed and audit-safe | `LOCK_STATE.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Daily ops notes should support operating evidence | `frontend/src/lib/api.js` stores notes in browser `localStorage`; no backend persistence or audit linkage was found | `docs/governance/LOCK_STATE.md` says log one short note in `/ops` | Partial | Medium: notes are local/browser-scoped, not shared evidence | Decide whether ops notes should remain local convenience only or become product-backed evidence | Technical-Owner Mode for changing evidence policy | No |

## 9. Audit Logging And Decision Trail

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| State-changing actions write to `audit_log` | `BUILD_CHECKLIST.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Mutating flows should record actor/action/target/timestamp evidence | `_audit()` writes to `db.audit_log`; intro, conversion, follow-up, submission decision, billing reconnect, reactivation, and connect-click paths call it; `/api/oversight` returns `audit_recent` | `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Audit trail supports launch-phase decisions | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Phase changes and approvals should have linked audit evidence | `phase_transition_decisions` writer at `server.py:968-994` calls `_audit()` to persist `audit_id`; decisions record `from_phase`, `to_phase`, `reason`, `decision_maker`, `snapshot_ref`, and timestamp | Docs require it for transitions and launch evidence | Implemented | Low | Keep as-is | Technical-Owner Mode | No |

## 10. Data Sufficiency

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Launch-critical workflow data persists in product-owned records | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Core demand, supply, billing, growth, ops, and audit records should persist | Inspected runtime uses product-backed collections for trainers, submissions, intros, conversions, engagements, owner waitlist, attribution, growth attribution, system state, source ingestion state, reactivation candidates, stripe events, and audit log; startup creates key indexes | `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Launch-critical data is sufficient for phase decisions | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Product data should be sufficient to support readiness and transition decisions | Most underlying workflow data exists, but explicit phase/readiness/decision records are absent | Docs define these as required launch-critical records | Partial | High: operational data exists, but launch-governance evidence layer is incomplete | Add phase-state, readiness, and decision records | Technical-Owner Mode | Yes |
| `Database = truth`, `/ops = readable operating view`, `audit_log = decision trail`, `CSV/export = proof only` | `LOCK_STATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Runtime should reflect this data hierarchy | Database-backed oversight and audit trail are visible; no explicit CSV/export runtime surface was found in inspected code, and no evidence was found that CSV/export is being used as operating truth | `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md` | Partial | Medium: data hierarchy is mostly real, but export-proof surface is not evidenced | Keep current hierarchy and document/export proof approach when implemented | Normal Ops | No |

## 11. Safety / Non-Goals

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| No unrestricted admin CRUD | `SSOT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `LOCK_STATE.md` | Product should not expose admin CRUD as the operating model | Legacy admin routes redirect to `/`; `/ops` is read-only; no active admin CRUD endpoint was found in inspected surfaces | `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| No routine manual trainer matching or billing | `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `LOCK_STATE.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Core matching and billing should remain automated | Match, intro, billing, webhook, retry, and recovery logic are automated; `/ops` only exposes investigation links, not routine manual execution controls | `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| No automatic phase switching or automatic public-matching enablement | `SSOT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `LOCK_STATE.md` | System must not silently move phases or enable live matching | No automatic phase-transition code found; `PUBLIC_MATCHING_ENABLED` is env-controlled; explicit `launch_phase_state` and `phase_transition_decisions` model now exists and requires deliberate owner action to change | `docs/governance/LOCK_STATE.md`, `docs/governance/ROADMAP.md` | Implemented | Low | Keep as-is | Technical-Owner Mode for changes | No |

## 12. Deployment / Runtime Config Evidence

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Loop-owner topology is explicit and lease-guarded | `LAUNCH_GATE.md`, `LOCK_STATE.md`, `BUILD_CHECKLIST.md` | Exactly one intended loop owner should run, with duplicate-executor protection | `backend/services/runtime_control.py` resolves `AUTONOMY_LOOP_OWNER`; startup uses DB lease guard; `engine.py` defines cadence and `system_state` writes | `docs/governance/LOCK_STATE.md`, `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` | Implemented | Low | Keep as-is | Technical-Owner Mode for changes | No |
| Env examples support current launch runtime | `BUILD_CHECKLIST.md` | `.env.example` files should expose current runtime expectations | `.env.example` and `backend/.env.example` include `ADMIN_PASS`, `AUTONOMY_LOOP_OWNER`, `PUBLIC_MATCHING_ENABLED`, billing defaults, and integrations | `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` | Implemented | Low | Keep as-is | Technical-Owner Mode for changes | No |
| Launch-phase runtime configuration is evidenced | `BUILD_CHECKLIST.md`, `SSOT.md`, `BUILD_CHECKLIST.md` | Runtime config should support separate launch phase/public emphasis | `PUBLIC_LAUNCH_PHASE` env var read at `server.py:104`; `launch_phase_state` persisted to DB at startup; `.env.example` documents the var | Docs define it as required or equivalent | Implemented | Low | Keep as-is | Technical-Owner Mode for changes | No |
| Release-gate automation checks phase/readiness requirements | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md` | Release-gate checks should cover critical launch-governance evidence where implemented | `scripts/check_prelaunch_release_gate.js` extended 2026-05-25 to assert `PUBLIC_LAUNCH_PHASE`, `_get_or_create_launch_phase_state`, `phase_readiness_snapshots`, and `phase_transition_decisions` symbols in `server.py` | `docs/governance/LOCK_STATE.md` records separate manual evidence | Implemented | Low | Keep as-is | Technical-Owner Mode | No |

## 13. Tests / Evidence Gaps

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Core runtime and workflow paths are tested | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md` | Matching gate, waitlist, oversight, lifecycle, billing, and security paths should be test-backed | `backend/tests/test_public_mode_unit.py`, `test_lifecycle_endpoints_unit.py`, and billing tests cover matching gate, waitlist, oversight auth, lifecycle status, and billing semantics | `docs/governance/LOCK_STATE.md` records passing test evidence | Implemented | Low | Keep as-is | Normal Ops | No |
| Phase-state/readiness/decision layer is tested | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md` | New governance runtime surfaces should be test-backed | `test_public_mode_unit.py:582` — `test_oversight_exposes_launch_phase_and_readiness_contract` asserts `launch_phase_state`, `phase_readiness_snapshot`, `phase_transition_decisions` shape and `supply_first` values | Docs define these as required launch evidence | Implemented | Low | Keep as-is | Normal Ops | No |
| Final supply-first evidence window is complete | `ROADMAP.md`, `LOCK_STATE.md`, `LAUNCH_GATE.md` | Final supply-readiness and Go/No-Go evidence should be explicit | Phase/readiness/decision layer is now product-backed and test-covered; local verification passes (124 backend tests pass, frontend build pass, all gate scripts pass); Final Go/No-Go is pending owner (`carlg`) walkthrough of live/staging stack | `docs/governance/LOCK_STATE.md`, `docs/process/NEXT_SESSION_HANDOFF.md`, `docs/governance/ROADMAP.md` | Partial | Medium: Final Go/No-Go is owner decision, not a technical gap | Owner walkthrough of live/staging stack; Final Go/No-Go sign-off | Owner decision | Yes |

## 14. Implementation Backlog Candidates

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Product-backed launch phase truth | `SSOT.md`, `LAUNCH_GATE.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Runtime needs a separate launch-phase truth source | `PUBLIC_LAUNCH_PHASE` env var, `launch_phase_state` persisted to `system_state`, oversight and `/ops` surface confirmed at `server.py:104, 832-852, 2406` | All major governance docs require it | Implemented | Low | Keep as-is | Normal Ops | No |
| Product-backed readiness snapshots | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Runtime needs current, inspectable readiness records | `_build_phase_readiness_snapshot()` and `_upsert_latest_phase_readiness_snapshot()` at `server.py:900-961`; `phase_readiness_snapshots` collection; read-only oversight exposure confirmed | Docs require them for supply-first approval and phase change review | Implemented | Low | Keep as-is | Normal Ops | No |
| Product-backed phase decision records | `LAUNCH_GATE.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Runtime needs explicit decision evidence with audit linkage | `phase_transition_decisions` writer at `server.py:968-994` with audit linkage via `_audit()`; confirmed | Docs require approved/rejected/deferred records | Implemented | Low | Keep as-is | Normal Ops | No |
| `/ops` phase-readiness panels | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md` | `/ops` should answer phase/readiness questions directly | Phase, exposure, readiness, intro-ready, blocked, recommendation, blockers-to-next-phase panels confirmed in `Ops.jsx:255-270` | Docs require these as first-check panels | Implemented | Low | Keep as-is | Normal Ops | No |
| Aggregate intro-ready and blocked-trainer metrics | `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Oversight should expose usable supply and blocked supply directly | `intro_ready_trainer_count` and `blocked_trainer_count` in readiness snapshot at `server.py:871-933`; exposed in oversight and rendered in `Ops.jsx:264-268` | Docs require these metrics | Implemented | Low | Keep as-is | Normal Ops | No |
| Waitlist abnormality visibility | `OPS_COCKPIT_RESPONSIBILITY_MODEL.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | `/ops` should show duplicate/rejected waitlist signals | Waitlist event persistence exists; no dedicated duplicate/rejected `/ops` rollup found | Docs expect monitoring for duplicates/rejections | Partial | Medium | Add waitlist abnormality summary to oversight and `/ops` | Normal Ops | No |

## Future Controlled-Live-Matching-Only Items

These items are intentionally not current supply-first runtime/evidence blockers.
They belong to later controlled live-matching work after supply-first readiness is product-backed and approved.

| Item | Why not a current blocker | Current evidence | Status | Required later trigger |
|---|---|---|---|---|
| Release-level evidence for `PUBLIC_MATCHING_ENABLED=true` public home path | Current approved phase keeps public live matching off | Matching path exists in code, but live runtime evidence remains `public_matching_enabled=false` | Deferred later phase | supply readiness proven, readiness snapshot reviewed, owner approval recorded |
| Public live-matching phase transition decision | Current launch scope is still `supply_first` | No transition-decision runtime record found yet | Deferred later phase | explicit move to `owner_waitlist` or `live_matching` |
| Broad owner-acquisition push tied to live matching | Current standards keep owner demand passive until supply readiness is proven | Waitlist and educational surfaces exist; live matching is gated | Deferred later phase | controlled-live-matching approval |

## Recommendation

Re-verified 2026-05-25: all items from the original implementation backlog (1–6 below) are now complete.

Original planning order (all now implemented):

1. ~~add separate launch-phase runtime truth~~ — Implemented (`server.py:104, 832-852`)
2. ~~add readiness snapshots~~ — Implemented (`server.py:900-961`)
3. ~~add phase-decision records with audit linkage~~ — Implemented (`server.py:968-994`)
4. ~~expose phase/readiness/blocker visibility in `/api/oversight` and `/ops`~~ — Implemented (`server.py:920-946`, `Ops.jsx:255-270`)
5. ~~add aggregate intro-ready and blocked-trainer metrics~~ — Implemented (`server.py:871-933`, `Ops.jsx:264-268`)
6. ~~add tests and release-gate checks for the new phase/readiness layer~~ — Implemented (`test_public_mode_unit.py:582`, `check_prelaunch_release_gate.js` extended 2026-05-25)

Remaining non-blocking gaps (owner decision on priority):

- Waitlist duplicate/rejected aggregate not yet in `_owner_waitlist_summary()` (events ARE persisted; no rollup)
- Ops note logging remains browser-local — not backend-persisted or audit-safe
- Trainer acquisition trend series is current-count only (no historical series)

Next required action: owner walkthrough of deployed `/ops` on live/staging stack and Final Go/No-Go sign-off (`carlg`).
