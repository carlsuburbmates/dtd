# Execution Status

## Purpose

This file is the sole current-state controller for DTD execution.

It owns:
1. current objective
2. current blocker
3. current priority order
4. current accepted scope
5. explicitly deferred items
6. current verification status
7. current risks
8. restart protocol
9. concise append-only execution log

It does not define:
1. product truth
2. workflow completion rules
3. page-level behavior
4. `/ops` product behavior
5. standards or launch gates

## Current Objective

Phase 1 trust restoration is complete.

The current objective is now post-Phase-2 review inside the locked
supply-first posture.

The current project execution priority is:
1. preserve the completed non-provider launch evidence set on the current trusted hosted path
2. prepare owner review against `LAUNCH_GATE.md`
3. reserve provider-coupled live proof for the final actual-domain activation decision
4. confirm launch readiness before any deferred Ops power is reconsidered
5. only after 1 to 4 are complete may deferred Ops power be reconsidered

Current Ops objective:
1. preserve the current Operations Console direction and trust boundary
2. use `/ops` as the human review surface for launch-readiness proof
3. do not start deferred high-power Ops controls

## Current Blocker

No active Phase 1 blocker remains.

No active non-provider Phase 2 blocker remains.

Current remaining gates are deferred final-activation gates:
1. live trainer submission E2E remains reserved for the final actual-domain activation decision
2. live provider exercise for notification and billing-coupled paths remains reserved for the final actual-domain activation decision

## Current Priority Order

1. preserve the completed hosted-path launch evidence against `LAUNCH_GATE.md`
2. confirm the Operations Console remains stable, readable, and accurate enough for launch-review work
3. hold provider-coupled proof for the final actual-domain activation decision
4. only after 1 to 3 are complete may bounded owner controls be reconsidered
5. only after 4 is proven safe may technical-owner controls be reconsidered

## Current Accepted Scope

In scope now:
1. launch-readiness proof within the locked current posture
2. non-provider runtime verification on the current trusted hosted path
3. `/ops` review of launch-critical workflow evidence

Out of scope now:
1. Owner Override controls
2. Technical-Owner controls
3. public live matching enablement
4. broad admin CRUD
5. unrelated code refactors
6. public custom-domain activation
7. provider-coupled live trainer submission, notification, and billing exercise before the final actual-domain decision

Guarded defaults that remain in force:
1. `CONVERSION_BILLING_MODE=track_only`
2. `PUBLIC_MATCHING_ENABLED=false` for the current supply-first phase
3. no auth replacement
4. no billing-model cutover away from intro-first defaults

## Explicitly Deferred Items

Do not implement yet:
1. bounded owner controls
2. technical-owner controls
3. public matching launch enablement
4. broad Ops mutation controls
5. provider-coupled live proof before the actual-domain activation decision

## Current Verification Status

Established from current repo and hosted-runtime evidence:
1. `/ops` is materially implemented and not merely aspirational
2. bounded Layer 1 review-state persistence exists in code and tests
3. the public route set materially matches the canonical page spec
4. the supply-first, passive owner waitlist posture is materially reflected in current code paths
5. startup seeds are explicit opt-in and API-only through `ENABLE_STARTUP_SEEDS`
6. the safe hosted frontend alias is serving the latest synced `main` deployment
7. the live backend oversight contract now exposes the current Operations Console read models:
   - `trainer_inventory`
   - `message_log`
   - `ops_cases`
8. local, remote, and live are re-synced to the same trusted execution path for the current locked posture
9. hosted campaign landing proof now persists a retained attribution cohort on the trusted hosted path:
   - `campaign=phase2-proof`
   - `source=lp`
   - `entry_events_30d=3`
   - `waitlist_joins_30d=1`
10. hosted discovery intake now has a current duplicate-path proof on the trusted hosted path:
   - a public `/api/discovery` candidate for an existing trainer was accepted as `pending`
   - hosted oversight later moved from `pending=1, duplicate=0` to `pending=0, duplicate=1`
   - the discovery heartbeat then recorded `duplicates=1`, `handled=1`, `last_run=2026-06-07T18:44:10.935161+00:00`
11. elapsed-window hosted loop proof now exists:
   - repeated hosted samples over time showed `ranking`, `pricing`, and `health` refreshing within expected cadence
   - the hosted discovery loop also advanced from the pre-proof run at `2026-06-07T18:34:09.921276+00:00` to the processed duplicate-path run at `2026-06-07T18:44:10.935161+00:00`

Still deferred at the project level:
1. final live provider exercise for external lifecycle paths, reserved for the actual-domain activation decision

Current readiness state:
1. website is owner/public review ready at the current baseline
2. non-provider Phase 2 hosted-path launch evidence is complete
3. website is not yet final-activation-ready because provider-coupled actual-domain proof remains deferred
4. final status remains `not launch-approved` until owner review and the deferred actual-domain activation checks are complete

Known remaining evidence gaps:
1. final live trainer submission E2E, deferred to the actual-domain activation decision
2. final live Stripe/Resend provider exercise, deferred to the actual-domain activation decision

## Current Runtime And Infrastructure Truth

Current code/runtime truths worth preserving:
1. oversight auth currently uses `ADMIN_PASS`
2. loop ownership is explicit and env-controlled
3. loop execution is lease-guarded so only one live owner executes loops at a time
4. startup seeds are now explicit opt-in and API-only through `ENABLE_STARTUP_SEEDS`
5. the optional local stack is being aligned to the same named DTD runtime path instead of a stale alternate DB name
6. active scope is region-gated
7. consent checkpoints are enforced on matching, contact release, and submission paths
8. intro idempotency remains enforced
9. conversion billing defaults remain `track_only`
10. intro billing collection path is Stripe invoice-based when configured
11. source-ingestion and outreach loops remain implemented in the runtime

Current infrastructure truths worth preserving:
1. the active Vercel project is `dtd`
2. the current safe hosted proof surface is `https://dtd-ten.vercel.app`
3. the public custom domains are intentionally withheld from final live use until launch trust is ready
4. a duplicate `dogtrainersdirectory` Vercel project remains account inventory only and should be treated as drift-risk

## Current Risks

1. the remaining launch gate is now the deferred actual-domain activation slice, not the trusted hosted path
2. stale local env values can mislead remote verification if they point to a retired backend URL
3. latent matching-capable code could be misread as the current product posture if authority order is ignored

## Restart Protocol

Any future session should restart from:
1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
4. `docs/governance/CURRENT_TRUTH_INDEX.md`
5. this file
6. the current repository state

Session-start rules:
1. inspect current worktree state first
2. preserve the locked chunk approvals unless explicitly replaced
3. preserve `/ops` semantics before aligning surrounding docs
4. do not reopen deferred high-power Ops controls during trust-first work

Launch authority:
1. final Go/No-Go authority remains the owner
2. launch approval must be explicit and evidence-backed

## Append-Only Execution Log

1. `2026-06-03`
- repo-anchored handoff established as safer than chat-memory continuation
- trust-first next-work order locked for post-Ops-foundation execution

2. `2026-06-06`
- documentation cleanup decomposed into locked chunks:
  - final file set
  - ownership rules
  - keep / merge / delete decisions
  - exact content allocation

3. `2026-06-07`
- code-informed refinement added to documentation cleanup
- `/ops` and `OPERATIONS_CONSOLE_SPEC.md` confirmed as preservation-sensitive
- bounded Layer 1 review-state writes confirmed as implemented truth
- documentation system cleanup completed:
  - workflow completion authority created
  - single execution-status authority created
  - parallel roadmap/handoff control docs retired
- startup seed control tightened in code:
  - seeds require explicit `ENABLE_STARTUP_SEEDS`
  - worker startup no longer participates in seeding
- optional local compose stack aligned toward DTD naming and worker topology

4. `2026-06-08`
- Phase 1 trust restoration completed
- local validation passed:
  - `python3 -m compileall backend`
  - `cd backend && ../.venv/bin/pytest -q tests/test_public_mode_unit.py tests/test_runtime_control_unit.py tests/test_lifecycle_endpoints_unit.py`
  - `cd frontend && CI=true npm test -- --watch=false --runInBand src/pages/Ops.test.jsx`
  - `cd frontend && npm run build`
- trusted state synced to `origin/main` at commit `12b049b8fb6ef06728a4dd6bd3f966f5e475ea4b`
- Vercel production deployment for commit `12b049b8fb6ef06728a4dd6bd3f966f5e475ea4b` reached `READY`
- live backend `/api/config` and `/api/oversight` now match the locked supply-first posture and current `/ops` contract
- current safe hosted verification routes returned `200`:
  - `/`
  - `/trainers`
  - `/ops`
- next active phase is launch-readiness proof, not further trust restoration

5. `2026-06-08`
- Phase 2 started
- `node scripts/check_prelaunch_release_gate.js` returned `PRELAUNCH_RELEASE_GATE=PASS`
- runtime-evidence review narrowed the active launch blockers to:
  - live trainer submission E2E proof
  - live Stripe/Resend provider exercise
  - campaign-attribution and discovery-pickup proof
  - long-window autonomous-loop proof
- stale closed-blocker rows in `RUNTIME_EVIDENCE_ALIGNMENT_MATRIX.md` were corrected so the matrix matches the current `/ops` contract and hosted runtime evidence

6. `2026-06-08`
- Phase 2 launch-readiness audit tightened the next human gate
- code audit confirmed the first live trainer-submission proof is provider-coupled, not inert:
  - `create_submission()` can trigger `notify_submitter_result()`
  - `create_intro()` can trigger `bill_intro()` and `notify_trainer_new_intro()`
- next live proof therefore requires deliberate owner approval before exercising real provider paths

7. `2026-06-08`
- owner decision recorded: defer provider-coupled live proof
- live trainer submission, notification, and billing-coupled exercise are no longer current Phase 2 blockers
- those proofs are reserved for the final actual-domain activation decision instead of the current safe hosted path

8. `2026-06-08`
- Phase 2 wording tightened to reflect the actual proof target
- nearest-to-live hosted verification already exists for the synced frontend alias, live backend contract, and `/ops` surface
- remaining current blockers are now described as hosted-path attribution/discovery proof and elapsed-window loop proof, not generic final-live proof

9. `2026-06-08`
- nearest-to-live hosted oversight snapshot re-checked against the current backend target
- hosted evidence now confirms:
  - discovery summary is present with promoted rows
  - loop statuses expose interval and age signals on the trusted hosted path
- remaining non-provider blocker language narrowed to:
  - campaign-attribution persistence and clean discovery-lineage proof
  - elapsed-window autonomous-loop proof

10. `2026-06-08`
- hosted Phase 2 non-provider proof completed on the trusted hosted path
- browser-driven landing and waitlist proof established a retained attribution cohort:
  - `campaign=phase2-proof`
  - `source=lp`
  - `entry_events_30d=3`
  - `waitlist_joins_30d=1`
- hosted duplicate-path discovery proof established current discovery intake and processing without creating a new public trainer row:
  - `POST /api/discovery` accepted a pending candidate for `https://www.dogforce1.com.au`
  - hosted oversight moved from `pending=1, duplicate=0` to `pending=0, duplicate=1`
  - hosted discovery heartbeat then recorded `duplicates=1`, `handled=1`, `last_run=2026-06-07T18:44:10.935161+00:00`
- elapsed-window hosted loop proof established that short-cadence loops continued refreshing over time:
  - `ranking`, `pricing`, and `health` stayed within expected cadence across repeated samples
  - `discovery` advanced from `last_run=2026-06-07T18:34:09.921276+00:00` to `last_run=2026-06-07T18:44:10.935161+00:00`
- current active Phase 2 blockers are therefore closed
- only deferred actual-domain activation proofs remain
