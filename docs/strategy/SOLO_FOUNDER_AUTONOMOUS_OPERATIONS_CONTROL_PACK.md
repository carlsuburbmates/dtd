# Solo-Founder Autonomous Operations & Control Pack (Final)
**Project:** Melbourne Dog Trainers Directory  
**Purpose:** Control document for future coding agents.  
**Mode:** Autonomous-by-default, minimal human intervention, strict risk controls.

## Status label legend
- `LOCKED` = approved, must not drift
- `READY` = safe to implement now
- `VERIFY FIRST` = confirm against repo before implementation
- `APPROVAL REQUIRED` = owner must approve first
- `LEGAL/PRIVACY REVIEW REQUIRED` = owner + legal/privacy review
- `DO NOT BUILD YET` = blocked by strategy/risk
- `OPTIONAL LATER` = intentionally deferred, non-critical for current phase

---

## 1) Project summary
- **What this is:** Education-first prelaunch platform for Melbourne dog trainer supply growth, with deterministic state gates and controlled public claims.
- **What this is not:** Live public matching product yet; enterprise multi-team platform.
- **Current phase:** Prelaunch readiness + automation hardening.
- **Main objective:** Build verified trainer supply and trust signals safely until matching-live eligibility is reached.

---

## 2) Locked decisions (`LOCKED`)
1. Education-first prelaunch.
2. Public matching deferred until gate eligibility.
3. Canonical suburb dataset is fixed:
   - `list_id`: `melb_suburbs_abs_asgs_ed3_gccsa_2gmel_v1`
   - `count`: `613`
   - `hash`: `72beb762ee5c7daac20bf6a89ae822085bab5656d45fbd4ed72104754c6670e6`
4. VATC is primary north-star metric.
5. Public claims are state-gated (`STATE_0..STATE_4`).
6. “Melbourne-wide” claim only at `STATE_2+`.
7. Monetization now: intro-first billing path with launch default `CONVERSION_BILLING_MODE=track_only`; optional subscription experiments require explicit owner approval and feature gating.
8. No conversion/success fees billed until post-gate reliability and explicit owner approval.
9. Automation-first with minimal human exception loop.
10. No guaranteed leads/bookings claims.
11. Canonical suburb list changes require versioned migration + rollback.

---

## 3) Automation-first operating model

### System can do automatically (`READY`)
- Data integrity checks (suburb count/hash drift).
- Deterministic lead validation/qualification.
- Verification expiry checks and reminders.
- Gate metric calculations and state evaluation.
- Claim enforcement (block invalid copy/state combinations).
- Scheduled monitoring and reports.
- Alert generation and routing.

### AI can do (`READY`)
- Explain anomalies, summarize status, recommend actions, propose optimizations.

### Owner must approve (`APPROVAL REQUIRED`)
- Gate threshold changes.
- Claim policy/copy rule changes.
- Billing model changes/activation/cutover.
- Auth model replacement.
- Overrides of gate/claim controls.

### Legal/privacy review required (`LEGAL/PRIVACY REVIEW REQUIRED`)
- Terms/Privacy final text.
- Automated decision disclosure wording.
- Retention/deletion policy durations.
- Review moderation policy wording.

### Must never happen automatically (`DO NOT BUILD YET`)
- Unlocking public matching in production, even if gate calculations are implemented.
- Publishing “Melbourne-wide” below `STATE_2`.
- Enabling paid subscription in production without approved migration.
- Changing consent semantics silently.

---

## 4) Risk-based control matrix

| Risk | Rule |
|---|---|
| Low | Automate |
| Medium | AI recommends, owner can approve |
| High | Owner approval required |
| Legal/privacy | Owner approval + legal/privacy review |
| Unknown | Verify first |

---

## 5) Build-permission matrix

| Work area | Status |
|---|---|
| Canonical suburb ingestion + hash checks | `READY` |
| Waitlist schema + deterministic validation | `READY` |
| VATC + gate snapshots (read-only first) | `READY` |
| Claim guardrails (blocking invalid claims) | `READY` |
| Read-only operator insights improvements | `READY` |
| Event contract + validation | `READY` |
| Market monitoring jobs | `READY` |
| Auth/RBAC replacement | `VERIFY FIRST` |
| Subscription activation in production | `APPROVAL REQUIRED` |
| Billing model cutover away from intro-first launch defaults | `APPROVAL REQUIRED` |
| Legal policy final copy | `LEGAL/PRIVACY REVIEW REQUIRED` |
| Public matching unlock / production activation | `DO NOT BUILD YET` |
| SMS expansion | `OPTIONAL LATER` |

---

## 6) Final workstreams (lightweight control view)

| Workstream | Purpose | Inputs | Outputs | Automation | Owner involvement | Acceptance | Blocked |
|---|---|---|---|---|---|---|---|
| Canonical suburb data | Geographic truth source | CSV + meta | active list + drift checks | High | Low | hash/count match | None |
| Owner waitlist | Demand capture | lead schema + consent + suburbs | qualified leads by suburb | High | Medium (policy edits) | step1/step2 deterministic | legal wording |
| Trainer onboarding/verification | Supply quality | verification criteria | verified active trainer counts | High | Medium/High | deterministic status transitions | external verification policy edge cases |
| Monetization | Sustainable launch/prelaunch revenue | intro billing + conversion tracking mode | billing states + audit | Medium/High | High | intro-first behavior must remain deterministic unless approved cutover | cutover approval |
| State gates/matching lock | Launch integrity | thresholds + metrics | state + lock status | High | High-risk overrides only | cannot unlock without criteria | override policy finalization |
| Public claim control | Prevent overclaiming | state->copy rules | allowed claims + blocked attempts | High | Medium | “Melbourne-wide” blocked below STATE_2 | final approved copy set |
| Admin/operator panel | Non-technical control | KPI + alerts + decisions | readable daily control UI | Medium | Medium/High | operator can act safely | auth migration |
| Analytics/events | Measurement integrity | event contract | KPIs + traceability | High | Medium (versioning) | contract compliance | None |
| Lifecycle automation | Nurture/recovery | triggers + caps + suppressions | sends + outcomes | High | Medium | unsubscribe/consent always enforced | legal wording |
| Market monitoring | External signals | sources + cadence | alerts + reports | High | Low/Medium | actionable scans | None |
| Privacy/security | Trust/compliance | consent + access + retention | enforced controls + logs | Medium/High | High | deterministic protections | legal signoff |
| Repo migration | Safe transition | current code/docs | reversible cutover | Medium | High | rollback-tested | cutover approval |

---

## 7) Dangerous areas that must not drift (hard guardrails)

### Billing guardrails
- Do not activate production subscription billing without owner approval.
- Do not remove legacy billing paths until migration + rollback are tested.
- No guaranteed leads/bookings in any paid plan text, API, or UI.
- Any pricing-mode migration away from intro-first must be isolated behind migration flags during transition.

### Matching guardrails
- Matching remains locked until eligibility gate pass.
- No manual unlock shortcut except explicit approved emergency protocol.

### Privacy guardrails
- Consent must be explicit, versioned, and auditable.
- Unsubscribe/suppression must be enforced before every send.
- No silent changes to retention/deletion behavior.

### Claim-control guardrails
- “Melbourne-wide” must be blocked below `STATE_2`.
- Claim state must be deterministic and auditable.
- Invalid claim attempts must be logged.

### Data guardrails
- Canonical suburb count/hash must be checked on schedule.
- Drift must trigger alert + state freeze behavior.

### Auth/admin guardrails
- No blind auth replacement.
- High-risk actions must require explicit owner-approved path + audit log.

---

## 8) Repo verification checklist (`VERIFY FIRST`)
1. Confirm frontend/backend/docs align on canonical monetization mode and migration state.
2. Confirm matching gate is currently enforced (`PUBLIC_MATCHING_ENABLED` + `403`).
3. Confirm `/ops` remains read-only + passcode-based.
4. Reconfirm canonical suburb CSV/meta hash and count.
5. Confirm loop ownership/lease behavior in runtime control.
6. Confirm Stripe webhook idempotency and notification paths.
7. Confirm tests with old billing assumptions are identified before migration.

---

## 9) What a future coding agent may do first (`READY`)
1. Add machine-readable suburb meta fields (see section 12 constraints).
2. Implement read-only gate snapshot computation and storage.
3. Implement waitlist step1/step2 deterministic schema + validators.
4. Implement event validation/versioning layer.
5. Add claim copy guard that blocks invalid claims only.
6. Add read-only operator cards for state/coverage/alerts/reports.
7. Add migration feature flags without behavior cutover.

These first tasks must be additive, reversible, and must not change production matching, billing, or auth behavior.

---

## 10) What a future coding agent must not do yet
- Do not replace auth blindly.
- Do not activate subscription billing blindly.
- Do not unlock matching.
- Do not publish “Melbourne-wide” claims below `STATE_2`.
- Do not delete legacy billing paths without approved migration + rollback.
- Do not add unrelated features or expand scope.

---

## 11) Acceptance gates

### Gate A — Planning readiness
- Locked decisions captured.
- Risk/control model clear.
- Workstreams and blockers explicit.

### Gate B — Repo verification readiness
- Verification checklist complete with file evidence.
- Conflicts logged (billing model, auth, gating linkage).

### Gate C — Safe implementation readiness
- Feature flags added.
- Deterministic validators active.
- Rollback path documented and tested.

### Gate D — Launch readiness
- Billing lifecycle tested in non-production.
- Privacy/consent/audit controls complete.
- Operator panel supports non-technical daily control.

### Gate E — Matching-live eligibility
- `STATE_4` criteria pass for required duration.
- No unresolved high-risk incidents.
- Explicit owner approval recorded.

---

## 12) Irrelevant tasks to avoid (do not spend time here)
- Enterprise SSO/SCIM/IdP rollout.
- Microservice decomposition.
- Multi-cloud portability redesign.
- Complex BI warehouse rebuild.
- Premature native apps.
- Advanced ML model retraining infrastructure.
- Replacing stable stack components without demonstrated need.
- Public matching UX expansion before gate eligibility.

---

## 13) Copy/paste block for future coding agent

**Objective**  
Implement only safe, approved, additive prelaunch controls for autonomous operations, preserving all locked decisions.

**Allowed actions**  
- Add deterministic checks, validators, gate snapshots, claim guards, read-only reporting, migration flags, and audit logging.
- Align docs/code with locked decisions.

**Forbidden actions**  
- No matching unlock.  
- No “Melbourne-wide” claim below `STATE_2`.  
- No production billing cutover without owner approval.  
- No blind auth replacement.  
- No legacy billing deletion without rollback-tested migration.  
- No scope expansion.

**Evidence requirements**  
- Every completion claim must cite repo files/tests/logs.
- Every risky migration must include rollback proof.
- High-risk changes require explicit approval artifact.

**Stop conditions**  
- Missing source truth.
- Conflict with locked decisions.
- Legal/privacy content needing review but not approved.

---

## 14) Execution checks (repo-enforced sync)

Run these checks during implementation slices before finalizing changes:

1. Frontend copy guard (deterministic):
   - `node scripts/check_frontend_copy_guard.js`
   - Must pass. This guard enforces banned hardcoded legacy phrases in targeted page components and allows legacy fallback wording only in `frontend/src/lib/publicPolicy.js`.
2. Prelaunch release gate verifier:
   - `node scripts/check_prelaunch_release_gate.js`
   - Must print `PRELAUNCH_RELEASE_GATE=PASS`.
3. Stage-A runtime verifier:
   - `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` (or `STAGE_A_MODE=local` when appropriate)
   - Must pass with `RESULT=PASS` before release/cutover decisions.
4. Dirty-tree staging protocol (mandatory):
   - Stage only slice-owned files.
   - For each candidate file, confirm tracked/untracked status before staging.
   - Always review `git status --short` before commit.
   - Never bundle unrelated modified/untracked files.
   - If unrelated dirty files exist, explicitly exclude them from this slice.

These checks are operational controls only and do not change locked strategy.

---

## 15) Implementation status ledger (operational)

### Completed slices (concise)
- Slice 01: Control alignment + repo verification + READY-only plan established.
- Slice 02: Monetization copy policy surfaces + deterministic claim-state scaffold (safe defaults).
- Slice 03: Ops read-only integrity visibility (dataset identity + claim policy + integrity status).
- Slice 04: Owner waitlist MVP (API + Home form + read-only summary + deterministic events).
- Slice 05: Event contract integration for prelaunch events + Ops waitlist read-only visibility.
- Slice 06: Ops read-only Prelaunch KPI panel wired to backend `kpi_prelaunch`.
- Slice 07: Deterministic frontend copy-guard script added and passing.
- Slice 08: Deterministic prelaunch release-gate script added (`check_prelaunch_release_gate.js`) and validated.
- Slice 09: Control-pack section numbering collision resolved; execution checks updated with explicit command references and dirty-tree staging protocol.
- Slice 10: Control-pack implementation ledger completed through Slice 10 with concise factual entries.

### Ready-next slices
- Extend read-only Ops/oversight contract tests for KPI and waitlist compatibility drift.
- Add release checklist run artifact capture (`copy guard` + `stage verifier`) to governance handoff.
- Continue additive prelaunch observability and validator hardening only (no matching/billing/auth unlock paths).
- Any change would weaken matching/billing/claim/privacy guardrails.

**Required final report format**  
1. Implemented changes  
2. Verification evidence  
3. Remaining blockers  
4. Risks introduced/mitigated  
5. Rollback status  
6. Approvals requested

---

## 16) Required metadata improvement (`READY`)
Add machine-readable control fields to the canonical suburb meta JSON:
- `alert_code`
- `active_list_id`
- `asgs_edition`
- `effective_from`
- `effective_to`
- `supersedes`
- `cutover_from_list_id`
- `state_freeze_flag`
- `validation_job_id`

---

## 17) Pre-sync blockers (status-only)
- Curated files currently marked untracked must be intentionally staged before any approved sync.
- Current runtime baseline check target is `STAGE_A_MODE=remote ./scripts/verify_stage_a_runtime.sh` -> `RESULT=PASS` before sync.
