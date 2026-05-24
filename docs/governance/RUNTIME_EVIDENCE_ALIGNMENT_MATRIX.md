# Runtime Evidence Alignment Matrix

Date: 2026-05-24  
Scope: docs-only mapping from canonical supply-first standards to current runtime/code evidence, current docs/evidence references, concrete gaps, and next actions.  
Change boundary: no code changes, no runtime changes, no `/ops` implementation changes.

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

2. Main current gaps:
- no separate persisted launch-phase runtime mechanism was found
- no `launch_phase_state` evidence was found
- no `phase_readiness_snapshots` evidence was found
- no `phase_transition_decisions` evidence was found
- `/ops` does not currently surface phase, readiness, recommendation, intro-ready count, blocked-trainer count, or blockers-to-next-phase

3. Conclusion:
- docs/governance alignment is ahead of runtime/evidence alignment
- the current launch posture is documented as `supply_first`, but that posture is not yet product-backed by the inspected runtime surfaces

## 1. Public Exposure And Launch Posture

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Public live matching exposure is runtime-controlled | `SSOT.md`, `LAUNCH_GATE.md`, `LOCK_STATE.md` | Home exposure must be explicitly gated and consistent across backend, frontend, tests, and public copy | `backend/server.py` defines `PUBLIC_MATCHING_ENABLED`, exposes it from `GET /api/config`, gates `POST /api/match` and `POST /api/intros`; `frontend/src/pages/Home.jsx` consumes `/config`; `backend/tests/test_public_mode_unit.py` asserts config and gate behavior | `docs/governance/LOCK_STATE.md`, `docs/governance/ROADMAP.md`, `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` | Implemented | Low | Keep as-is and preserve doc/runtime sync | Normal Ops for monitoring; Technical-Owner Mode for changes | No |
| Launch phase remains separate from matching exposure | `SSOT.md`, `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Runtime should represent launch phase separately from `PUBLIC_MATCHING_ENABLED` | No `PUBLIC_LAUNCH_PHASE`, `launch_phase_state`, or equivalent persisted phase-state mechanism was found in inspected runtime/code surfaces | Docs repeatedly state the separation rule, especially `LOCK_STATE.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `BUILD_CHECKLIST.md` | Missing | High: docs can claim `supply_first` while runtime only knows matching on/off | Add explicit phase-state mechanism and expose it in API and `/ops` | Technical-Owner Mode | Yes |
| Current approved posture is supply-first with public matching off | `LOCK_STATE.md`, `ROADMAP.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Runtime should make the current approved posture inspectable in product-backed evidence | Live evidence in docs records `public_matching_enabled=false`, but inspected code does not expose current launch phase/public emphasis as product-backed state | `docs/governance/LOCK_STATE.md`, `docs/process/NEXT_SESSION_HANDOFF.md` | Partial | Medium: current posture is documented, not product-backed | Persist current phase/public emphasis and link it to audit evidence | Technical-Owner Mode | Yes |

## 2. Phase Records

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| `launch_phase_state` or equivalent exists | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Persist current phase, exposure state, onboarding state, waitlist state, public emphasis, updated-by, updated-at, reason, and audit linkage | No runtime collection, endpoint field, env example, or oversight payload for `launch_phase_state` or equivalent was found | Docs define the requirement and field set | Missing | High: no product-backed phase truth | Add persisted phase-state record and expose read-only snapshot in oversight | Technical-Owner Mode | Yes |
| `phase_readiness_snapshots` exist | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Persist readiness snapshots with supply, blockers, alert state, loop health, recommendation, and evidence timestamp | No runtime collection, writer, reader, or oversight field for readiness snapshots was found | Docs define readiness-snapshot requirement and use it as a launch gate | Missing | High: no product-backed readiness evidence | Add readiness snapshot generation and storage tied to current phase | Technical-Owner Mode | Yes |
| `phase_transition_decisions` exist and link to audit evidence | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Persist approved/rejected/deferred phase decisions with reason, decision maker, snapshot ref, timestamp, rollback note, and audit linkage | No transition-decision record, endpoint, or audit-linked phase decision flow was found | Docs define the approval gate and required decision fields | Missing | High: no evidence trail for future phase change decisions | Add explicit phase-decision recording and audit linkage | Technical-Owner Mode | Yes |

## 3. Supply-First Readiness

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Supply readiness is visible from product-backed evidence | `SSOT.md`, `LAUNCH_GATE.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | `/ops` should show enough product-backed data to judge supply readiness without DB inspection | `backend/server.py` exposes `kpi_prelaunch`, `submissions_summary`, `integrity`, `reactivation_summary`; `frontend/src/pages/Ops.jsx` renders those surfaces | `docs/governance/ROADMAP.md`, `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`, `docs/governance/LOCK_STATE.md` | Partial | Medium: some supply evidence exists, but not a clear readiness decision surface | Add explicit supply-readiness status, recommendation, and blocker rows | Normal Ops for review; Technical-Owner Mode for changing underlying policy | Yes |
| Intro-ready trainer count is visible | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | `/ops` should expose intro-ready trainer count or equivalent direct signal | Individual submission status derives `activation_state`, including `intro_ready`, in `GET /api/submissions/{id}/status`; no aggregate intro-ready count was found in oversight or `/ops` | Docs require intro-ready visibility in `/ops` | Partial | High: supply can look healthier than it is | Add aggregate intro-ready count to oversight and `/ops` | Normal Ops | Yes |
| Blocked trainer count and blocker reasons are visible | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | `/ops` should show blocked count and why supply is blocked | Individual blocker logic exists in submission/billing/reactivation flows; `/ops` shows `auto_held`, billing cases, and reactivation cases, but no aggregate blocked-trainer count or blocker summary was found | Docs require blocked-trainer visibility and blocker reasons | Partial | High: founder still needs interpretation instead of a direct answer | Add blocked-trainer aggregate and blocker buckets to oversight and `/ops` | Normal Ops | Yes |
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
| `/ops` shows phase, exposure, supply readiness, intro-ready, blocked, recommendation, and blockers | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Required launch-governance visibility should be directly readable in `/ops` | Exposure-adjacent signals exist, but no explicit phase, readiness status, intro-ready count, blocked-trainer count, recommendation, or blockers-to-next-phase panel was found in `backend/server.py` or `frontend/src/pages/Ops.jsx` | Docs require these as first-check fields | Missing | High: `/ops` cannot yet answer “are we ready for the next phase?” | Add explicit oversight payload fields and `/ops` panels for these items | Normal Ops for reading; Technical-Owner Mode for changing state | Yes |
| `/ops` note logging is product-backed and audit-safe | `LOCK_STATE.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Daily ops notes should support operating evidence | `frontend/src/lib/api.js` stores notes in browser `localStorage`; no backend persistence or audit linkage was found | `docs/governance/LOCK_STATE.md` says log one short note in `/ops` | Partial | Medium: notes are local/browser-scoped, not shared evidence | Decide whether ops notes should remain local convenience only or become product-backed evidence | Technical-Owner Mode for changing evidence policy | No |

## 9. Audit Logging And Decision Trail

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| State-changing actions write to `audit_log` | `BUILD_CHECKLIST.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` | Mutating flows should record actor/action/target/timestamp evidence | `_audit()` writes to `db.audit_log`; intro, conversion, follow-up, submission decision, billing reconnect, reactivation, and connect-click paths call it; `/api/oversight` returns `audit_recent` | `docs/governance/LOCK_STATE.md`, `docs/governance/LOCK_STATE.md` | Implemented | Low | Keep as-is | Normal Ops | No |
| Audit trail supports launch-phase decisions | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Phase changes and approvals should have linked audit evidence | No phase-state or phase-decision audit linkage was found because those records were not found | Docs require it for transitions and launch evidence | Missing | High: later phase changes would not have product-backed governance trail | Add audit-linked phase-decision flow | Technical-Owner Mode | Yes |

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
| No automatic phase switching or automatic public-matching enablement | `SSOT.md`, `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `LOCK_STATE.md` | System must not silently move phases or enable live matching | No automatic phase-transition code was found; `PUBLIC_MATCHING_ENABLED` is read from env/startup and used as a runtime gate; however no explicit product-backed phase system exists yet | `docs/governance/LOCK_STATE.md`, `docs/governance/ROADMAP.md` | Partial | Medium: no silent automation found, but no product-backed guard layer exists either | Add explicit phase model before later phase work | Technical-Owner Mode | No |

## 12. Deployment / Runtime Config Evidence

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Loop-owner topology is explicit and lease-guarded | `LAUNCH_GATE.md`, `LOCK_STATE.md`, `BUILD_CHECKLIST.md` | Exactly one intended loop owner should run, with duplicate-executor protection | `backend/services/runtime_control.py` resolves `AUTONOMY_LOOP_OWNER`; startup uses DB lease guard; `engine.py` defines cadence and `system_state` writes | `docs/governance/LOCK_STATE.md`, `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` | Implemented | Low | Keep as-is | Technical-Owner Mode for changes | No |
| Env examples support current launch runtime | `BUILD_CHECKLIST.md` | `.env.example` files should expose current runtime expectations | `.env.example` and `backend/.env.example` include `ADMIN_PASS`, `AUTONOMY_LOOP_OWNER`, `PUBLIC_MATCHING_ENABLED`, billing defaults, and integrations | `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md` | Implemented | Low | Keep as-is | Technical-Owner Mode for changes | No |
| Launch-phase runtime configuration is evidenced | `BUILD_CHECKLIST.md`, `SSOT.md`, `BUILD_CHECKLIST.md` | Runtime config should support separate launch phase/public emphasis | No `PUBLIC_LAUNCH_PHASE` or equivalent persisted phase-state config was found in env examples or inspected runtime code | Docs define it as required or equivalent | Missing | High: deployment/runtime layer cannot currently carry phase truth | Add phase config/state mechanism and deployment evidence | Technical-Owner Mode | Yes |
| Release-gate automation checks phase/readiness requirements | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md` | Release-gate checks should cover critical launch-governance evidence where implemented | `scripts/check_prelaunch_release_gate.js` checks matching gate, intro gate, waitlist endpoint, claims endpoint, and copy/meta requirements; no phase/readiness checks were found | `docs/governance/LOCK_STATE.md` records separate manual evidence | Partial | Medium | Extend release-gate automation after phase/readiness implementation exists | Technical-Owner Mode | No |

## 13. Tests / Evidence Gaps

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Core runtime and workflow paths are tested | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md` | Matching gate, waitlist, oversight, lifecycle, billing, and security paths should be test-backed | `backend/tests/test_public_mode_unit.py`, `test_lifecycle_endpoints_unit.py`, and billing tests cover matching gate, waitlist, oversight auth, lifecycle status, and billing semantics | `docs/governance/LOCK_STATE.md` records passing test evidence | Implemented | Low | Keep as-is | Normal Ops | No |
| Phase-state/readiness/decision layer is tested | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md` | New governance runtime surfaces should be test-backed | No tests were found for `launch_phase_state`, readiness snapshots, transition decisions, or `/ops` phase-readiness visibility | Docs define these as required launch evidence | Missing | High: later implementation could drift without guardrails | Add backend and `/ops` tests once the phase/readiness layer exists | Technical-Owner Mode | Yes |
| Final supply-first evidence window is complete | `ROADMAP.md`, `LOCK_STATE.md`, `LAUNCH_GATE.md` | Final supply-readiness and Go/No-Go evidence should be explicit | Docs record passing local validation and live runtime snapshots, but also explicitly state supply-first phase/readiness/decision evidence is still open and Final Go/No-Go is pending | `docs/governance/LOCK_STATE.md`, `docs/process/NEXT_SESSION_HANDOFF.md`, `docs/governance/ROADMAP.md` | Partial | High: launch-governance closeout remains open | Complete phase/readiness evidence layer before final Go/No-Go | Technical-Owner Mode | Yes |

## 14. Implementation Backlog Candidates

| Requirement | Source authority | Required runtime behaviour | Current code/runtime evidence | Current docs/evidence reference | Status | Risk if unresolved | Required next action | Suggested owner mode | Blocks runtime/evidence alignment? |
|---|---|---|---|---|---|---|---|---|---|
| Product-backed launch phase truth | `SSOT.md`, `LAUNCH_GATE.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Runtime needs a separate launch-phase truth source | Not found | All major governance docs require it | Missing | High | Implement `PUBLIC_LAUNCH_PHASE` or equivalent persisted phase-state mechanism | Technical-Owner Mode | Yes |
| Product-backed readiness snapshots | `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Runtime needs current, inspectable readiness records | Not found | Docs require them for supply-first approval and phase change review | Missing | High | Implement snapshot writer, schema, and read-only oversight exposure | Technical-Owner Mode | Yes |
| Product-backed phase decision records | `LAUNCH_GATE.md`, `OPS_COCKPIT_RESPONSIBILITY_MODEL.md` | Runtime needs explicit decision evidence with audit linkage | Not found | Docs require approved/rejected/deferred records | Missing | High | Implement decision-record persistence and audit linkage | Technical-Owner Mode | Yes |
| `/ops` phase-readiness panels | `BUILD_CHECKLIST.md`, `LAUNCH_GATE.md`, `INTEGRITY_AUDIT.md` | `/ops` should answer phase/readiness questions directly | Not found in current `/ops` implementation | Docs require these as first-check panels | Missing | High | Add phase, exposure, readiness, intro-ready, blocked, recommendation, blocker panels | Normal Ops | Yes |
| Aggregate intro-ready and blocked-trainer metrics | `INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` | Oversight should expose usable supply and blocked supply directly | Per-trainer activation logic exists; aggregate metrics not found | Docs require these metrics | Partial | High | Add aggregate supply-state rollups to oversight and `/ops` | Normal Ops | Yes |
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

Implementation planning can start after this matrix.

Recommended planning order:

1. add separate launch-phase runtime truth
2. add readiness snapshots
3. add phase-decision records with audit linkage
4. expose phase/readiness/blocker visibility in `/api/oversight` and `/ops`
5. add aggregate intro-ready and blocked-trainer metrics
6. add tests and release-gate checks for the new phase/readiness layer

Do not treat controlled live-matching release evidence as the first implementation target.
The immediate runtime/evidence alignment gap is the missing phase/readiness/decision layer for the current supply-first posture.
