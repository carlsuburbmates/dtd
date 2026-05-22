# Roadmap

Rule: current-state only. Keep this file aligned to the code and infra that actually exist.
Execution handoff reference: `docs/governance/NEXT_SESSION_HANDOFF.md`.
Status updates in this file must include evidence references.
Authority index: `docs/governance/CURRENT_TRUTH_INDEX.md`.

## Goal

Launch DTD / Dog Trainers Directory in Greater Melbourne with:
1. One input -> best matches.
2. Intro-first commercial model.
3. Automation-first operations with minimal manual overhead.

Standards target rule:
1. this roadmap remains current-state only
2. the committed Standards Set now defines the supply-first launch target
3. this roadmap must distinguish current state from that supply-first target until runtime/code alignment is complete

## Launch Definition Of Done (authoritative)

A launch-ready, robustly autonomous state is reached only when all criteria below are satisfied with evidence in-repo.

| Area | Done criterion | Evidence source |
|---|---|---|
| Supply readiness | Trainer supply readiness is proven for the current launch phase. | `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`, `/ops` evidence, governance logs |
| Intro-ready threshold | Intro-ready trainer threshold is defined and evidenced. | readiness evidence + `/ops` visibility |
| Blocked trainer visibility | Blocked trainer count and blocker reasons are visible. | `/ops` evidence |
| Launch phase state | Current launch phase is explicit and separate from public live matching exposure. | phase state evidence |
| Readiness snapshots | `phase_readiness_snapshots` exist and are current enough for decisions. | readiness records + governance evidence |
| Transition decisions | `phase_transition_decisions` exist for any claimed phase transition. | governance evidence + audit history |
| `/ops` phase and readiness view | `/ops` shows phase, readiness, recommendation, and blockers to next phase. | `/ops` evidence |
| Data sufficiency | Launch-critical records are product-backed and sufficient for decisions. | product-backed evidence |
| CSV/export rule | CSV/export is available for proof only and is not the operating source of truth. | standards and evidence model alignment |
| Runtime autonomy | Loop ownership is single-owner and lease-guarded, and active loops remain fresh (no stale loop beyond 2x interval during evidence window). | `/api/oversight` snapshot evidence + `docs/governance/NEXT_SESSION_HANDOFF.md` log |
| Operational health | No unresolved high-severity health alerts in the launch evidence window. | `/api/oversight` health/alerts evidence |
| Commercial reliability | Intro billing lifecycle is proven end-to-end (send, paid/failed, retry, webhook reconciliation) with explicit at-risk visibility. | `docs/OPERATIONS.md` KPI semantics + test/runtime evidence |
| Product path reliability | Home mode behavior is explicit (`PUBLIC_MATCHING_ENABLED`), launch phase is separate from matching exposure, and owner/trainer lifecycle paths are non-dead and consistent. | `frontend/src/pages/*`, `frontend/src/App.js`, route smoke evidence |
| Security controls | Oversight auth protection, webhook idempotency, intro idempotency, and trainer action-token controls are active and tested. | backend tests + `backend/server.py` |
| Quality gates | Backend tests pass, frontend tests pass, frontend build passes for the release candidate. | `docs/governance/LOCK_STATE.md` verification evidence |
| Doc-code sync | README/Architecture/Operations/Workflows/Governance docs reflect current runtime truth without contradictions. | `docs/governance/CURRENT_TRUTH_INDEX.md` + doc consistency pass |
| Governance gates | H-01..H-04 are completed and Final Go/No-Go remains an explicit, recorded decision. | `docs/governance/LOCK_STATE.md`, `docs/governance/NEXT_SESSION_HANDOFF.md` |

Rule: if any criterion above is not met, status remains `not launch-ready`.

## Completion Decisions (populated from current code/docs)

These defaults are the active completion contract unless explicitly superseded in this file.

1. Scope confirmation:
- Completion scope included closing previously non-complete workflows `W8` and `W13`; this scope is now satisfied with objective evidence.

2. Pass criteria source:
- Workflow pass criteria and closure evidence are recorded in `docs/WORKFLOW_TRACE_SHEET.md` and synchronized in governance evidence logs.

3. Operator ownership and response times:
- Primary operator owner: solo founder/owner (`carlg`) per one-man operating model.
- Response-time standard:
  - `Monitor`: same day logging.
  - `Investigate`: begin within 4 hours of trigger.
  - `Escalate`: immediate (same check window) into `technical-owner mode` for the same owner.

4. Final Go/No-Go authority:
- Final launch approval authority is the owner (`carlg`), recorded in governance evidence (`LOCK_STATE.md` + `NEXT_SESSION_HANDOFF.md` execution log).

5. Guarded policy defaults (no approval required to keep defaults):
- `CONVERSION_BILLING_MODE=track_only` remains default.
- `PUBLIC_MATCHING_ENABLED` remains mode-gated by current launch state.
- No auth replacement.
- No billing model cutover away from intro-first defaults.
- Any change to the above remains approval-required by existing guardrails.

6. Runtime verification access assumption:
- Local completion evidence can be produced from code/tests/docs.
- Live verification evidence uses existing runbook + platform checks when available; missing live credentials/access blocks only live-go decision, not local completion readiness assessment.

## Operating Model (locked for now)

1. One-man workflow.
2. One branch only: `main`.
3. Local project is the source of truth for development: `/Users/carlg/Documents/AI-Coding/dtd`.
4. Remote `main` stays synced to local `main`.
5. No required PR review gate.
6. No archive docs. Update or delete in place when truth changes.

## Current System Truth (2026-05-20)
Public home-entry mode is enforced by `PUBLIC_MATCHING_ENABLED` (`/api/config` consumed by `Home.jsx`):
- `false` => owner waitlist on `/`.
- `true` => live matching on `/`.
Matching/contact lifecycle routes and APIs remain implemented in both modes.

Current-state note:
1. the Standards Set now defines a supply-first launch target
2. this roadmap must not treat matching-enabled public release evidence as the immediate supply-first launch requirement
3. controlled live matching evidence belongs to a later phase after supply-first verification

### Code reality

1. Backend oversight auth currently uses `ADMIN_PASS` (`X-Admin-Pass`) in `backend/server.py`.
2. Loop ownership is explicit:
- `AUTONOMY_LOOP_OWNER=api` = API owns loops.
- `AUTONOMY_LOOP_OWNER=worker` = worker owns loops.
- `AUTONOMY_LOOP_OWNER=none` = loops disabled by ownership contract.
- Legacy `RUN_AUTONOMY_IN_API=1|0` is supported but cannot conflict with `AUTONOMY_LOOP_OWNER`.
3. Loop execution is lease-guarded in DB (`system_state.autonomy_loop_lease`) so only one live process executes loops at a time.
4. Active scope is region-gated via `ACTIVE_REGION` / `ACTIVE_REGIONS`.
5. Consent checkpoints are enforced on `/match`, `/intros`, and `/submissions`.
6. Intro idempotency is enforced via `Idempotency-Key` / `client_token`.
7. Conversion billing defaults to `CONVERSION_BILLING_MODE=track_only` (bill-mode is feature-flagged).
8. Intro billing collection path is Stripe invoice-based when configured (`STRIPE_SECRET_KEY` + webhook reconciliation).
9. Matching/scoring is deterministic heuristic in `backend/services/ai.py`.
10. Source-ingestion loop and T+7 outreach loop are implemented in `backend/services/automation.py` and scheduled by engine.
11. Stage A verifier exists at `scripts/verify_stage_a_runtime.sh`.

### Infrastructure reality

1. Accounts/keys exist for Clerk, Sentry, PostHog, Resend, Render, Atlas, Vercel.
2. Runtime and evidence snapshots for Stage A/B/C were captured in prior runbook entries.
3. Vercel project migration to `dtd` is complete and frontend runtime vars are set for prod/preview (`REACT_APP_BACKEND_URL`, `REACT_APP_POSTHOG_KEY`, `REACT_APP_POSTHOG_HOST`, plus `NEXT_PUBLIC_POSTHOG_*` parity keys).
4. Custom domains are attached and live; public hostnames return `307` apex redirect to `www` and `200` on `www` and `/trainers`.
5. Stage D evidence is complete (migration + routing + domain reattach/TLS/edge validation).
6. Stage E (deploy automation evidence) is complete; repeatable deploy/redeploy evidence and authenticated route smoke both pass.
7. H-03 legal copy sign-off and H-04 platform readiness verification are completed and recorded in governance docs/runbook.
8. Latest live runtime snapshot has cleared loop reasons after secret verification/redeploys; `source_ingestion.failed_sources=1` remains only as a historical count until the next successful ingestion cycle.

Evidence references for infrastructure status:
1. Stage D/E complete state: `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("Current lock", items 3-4 and "Stage D/E (complete)").
2. H-04 completion: `docs/governance/H04_VERIFICATION_REPORT.json`.
3. Current live-domain state: `docs/governance/NEXT_SESSION_HANDOFF.md` ("Execution log", current session alias mapping + `curl -I` checks).

## Priority Order (next work)

### P0A - Standards Set alignment

Status: completed.
Evidence references:
1. Oversight auth and scope/consent enforcement: `backend/server.py`.
2. Loop-ownership guard + lease contract: `backend/services/runtime_control.py`, `backend/worker.py`, `backend/services/engine.py`.
3. Launch billing default and conversion handling: `backend/services/engine.py` (`CONVERSION_BILLING_MODE` default) and `backend/server.py` (`/api/conversions`).

Locked decisions now implemented:
1. Launch auth: passcode-only oversight (`ADMIN_PASS`), no Clerk enforcement on backend.
2. Loop ownership: explicit env-controlled ownership to prevent duplicate loop scheduling.
3. Launch billing: intro-first; conversions tracked by default.
4. Scope: region-based enforcement with one active region set.
5. Consent: required before matching, contact reveal, and submission publish path.

### P0B - Derivative-doc alignment

Status: in progress.

Scope:
1. align derivative docs to the committed supply-first Standards Set
2. align derivative docs to `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`
3. remove stale demand-first and legacy naming drift where not historical

### P0C - Runtime/code alignment

Status: pending.

Scope:
1. align runtime and code surfaces to the committed supply-first standards where not already aligned
2. align `/ops` evidence views, phase records, and readiness visibility where implemented
3. keep `PUBLIC_MATCHING_ENABLED` separate from launch phase or equivalent persisted phase state

### P1 - Supply-first launch verification

Status: pending.

Done when:
1. supply readiness is evidenced for the current phase.
2. intro-ready threshold is evidenced.
3. blocked trainer visibility is evidenced.
4. launch phase state is explicit.
5. readiness snapshots exist.
6. phase transition decisions exist when needed.
7. `/ops` phase/readiness/blocker visibility is evidenced.
8. data sufficiency is evidenced.

### P2 - Owner waitlist push

Status: later.

Purpose:
1. increase passive owner demand only after supply-first evidence is sufficient
2. keep owner demand passive and phase-aware
3. avoid implying broad live matching before approved transition

### P3 - Controlled live matching

Status: later.

1. Run production in intro-first mode with conservative safeguards.
2. Observe intro event quality, suppression patterns, and incident trends.
3. Tune thresholds/policies only with explicit evidence updates in docs.

### Remaining Completion Checklist (strict order)

This checklist is the canonical execution order for the remaining project work after workflow closure. Items in `Must-Finish Before Launch` are implementation or closeout blockers that must be finished before the final live-verification phase begins. `Post-Feature Launch Verification` is the final evidence-and-decision block and should start only after the feature/completion work is confirmed done. `Should-Finish For Operator Takeover` improves the non-technical operating model but does not override the launch gate unless a checklist item also maps to the Launch Definition Of Done above.

#### Must-Finish Before Launch

Status: no open implementation or closeout blockers remain after the `2026-05-21` local closeout pass. Final launch readiness still depends on the `Post-Feature Launch Verification` block below.

Closure evidence:
1. Security-control evidence gaps were closed locally on `2026-05-21` with oversight lockout and trainer action-token negative-path coverage in `backend/tests/test_lifecycle_endpoints_unit.py`, with targeted validation recorded in governance evidence.
2. Roadmap-authority alignment closeout was completed on `2026-05-21` by normalizing `ROADMAP.md` to carry the canonical execution order, current authority references, and the deferred final-verification block as the only remaining launch-work phase.

#### Post-Feature Launch Verification

Do not start this block until the project’s feature/completion work is confirmed finished.

1. Capture a launch evidence window proving both:
   - no stale core loop beyond `2x` interval; and
   - no unresolved `severity:high` alerts during that window.
   - Evidence anchors: `/api/oversight` snapshot evidence, `docs/governance/NEXT_SESSION_HANDOFF.md` execution log.
2. Complete `P1 - Supply-first launch verification` with explicit evidence.
3. Defer release-level evidence for the matching-enabled public path (`PUBLIC_MATCHING_ENABLED=true`) to `P3 - Controlled live matching`.
   - Matching-enabled public-path release evidence is not the immediate supply-first launch gate.
   - It becomes relevant only for the later controlled live-matching phase.
4. Record the explicit `Final Go/No-Go` decision in governance evidence.
   - Evidence anchors: `docs/governance/NEXT_SESSION_HANDOFF.md`, `docs/governance/LOCK_STATE.md`.

#### Should-Finish For Operator Takeover

1. Reorder `/ops` so the documented first-check sequence is reflected in the UI:
    - current launch phase
    - public matching exposure state
    - supply readiness
    - trainer submissions
    - intro-ready trainers
    - blocked trainers
    - readiness recommendation
    - blockers to next phase
    - then revenue, loops, alerts, discovery/source-ingestion
2. Surface `Monitor` / `Investigate` / `Escalate` thresholds directly in `/ops`, not only in docs.
3. Improve case-level investigation depth from `/ops` for:
   - billing recovery,
   - reactivation,
   - discovery/source-ingestion, and
   - alert context.
4. Add clearer bounded remediation paths from `/ops` into operator-safe flows.
5. Replace misleading resubmission/update CTAs so trainer lifecycle flows are contextual rather than pseudo-new submissions.
6. Unify support routing language across public and trainer-support surfaces.

#### Nice-To-Have Cleanup

1. Add in-product operator note logging for daily checks.
2. Improve `/ops` severity visuals for stale loops and aging alerts.
3. Clean stale evidence artifacts that can confuse current-proof review.
4. Tighten deployment/runtime docs so single-owner loop topology is completely unambiguous.
5. Expand submission-status UI clarity for activation state and next-step guidance.

### P4 - Website completion (public + trainer UX only)

Status: completed (IA/routes/UX baseline complete; does not imply workflow completeness or that all routes are publicly promoted in current mode lock).
Evidence references:
1. Route map: `frontend/src/App.js`.
2. Build-pass record: `docs/governance/LOCK_STATE.md` ("Verification evidence", compileall + frontend build pass).

1. Public information architecture must be complete and navigable:
- `/` (education-first hub with gated matching entry)
- `/how-it-works`
- `/about`
- `/pricing`
- `/trust`
- `/faq`
- `/contact`
- `/privacy`
- `/terms`

2. Trainer-facing architecture must be complete:
- `/trainers` (model, economics, process)
- `/submit` (consented submission flow)
- `/t/:id` (consented contact-release flow)

3. Cross-surface UX consistency:
- Shared public header/footer/nav and legal links.
- Readable mobile + desktop layout.
- Data-testids present for key interactive controls.

Done when:
1. All listed routes exist and render.
2. Primary CTAs are wired and non-dead.
3. Frontend build passes in CI/local.

### P5 - Business workflow completeness (demand/supply/revenue lifecycle)

Status: completed.

Evidence gates:
1. `docs/USER_WORKFLOWS.md` includes `W1-W21` with demand generation, owner waitlist capture, onboarding completion, revenue recovery, and claim-policy control workflows.
2. `docs/WORKFLOW_TRACE_SHEET.md` assigns explicit status (`complete|partial|planned|missing`) for each workflow.
3. Oversight KPI semantics separate booked revenue from collected/at-risk collection outcomes.
4. Operations runbook defines KPI meanings with no terminology conflicts.
5. Non-technical operator routine is documented with clear monitor/investigate/escalate actions.

Done when:
1. All `R1-R6` recommendations in `SESSION_IMPLEMENTATION_REPORT_2026-05-08.md` are implemented or explicitly closed with evidence.
2. No remaining contradictions between roadmap claims and workflow/operations evidence.

Completion evidence (2026-05-20):
1. `docs/WORKFLOW_TRACE_SHEET.md` now reports W1-W21 all `complete`.
2. `docs/USER_WORKFLOWS.md` and `docs/OPERATIONS.md` are synchronized to the closed workflow state and operator action model.
3. Verification evidence recorded in `docs/governance/LOCK_STATE.md` includes backend tests, frontend tests, frontend build, and targeted W8/W13 closure tests.

## Repo Task Backlog (codebase-derived)

1. Stage D evidence capture: completed and recorded in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.
2. Stage E deploy/redeploy evidence capture: completed and recorded in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.
3. Public custom domains: reattached and verified live; no open domain/TLS evidence task remains.
4. Remaining launch work is non-domain only and should be driven by new evidence, not by stale backlog entries.

## Gate Rule

No launch gate advancement claims unless the required evidence for the current stage is documented in `INTEGRATION_CREDENTIALS_RUNBOOK.md`.
Current lock snapshot must also be reflected in `LOCK_STATE.md`.
Any gate status change in this roadmap must also include a matching execution-log evidence entry in `NEXT_SESSION_HANDOFF.md`.

## Verification Requirements

1. No roadmap item is complete without objective pass/fail criteria.
2. No policy claim without code or command evidence.
3. No doc references to non-existent files.
