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
Phase 2 launch-readiness proof is complete under the current governance scope.
Phase 3 owner review and bounded Go/No-Go is complete.

The first operator-facing `/ops` optimisation pass is now complete.

The current objective is now to complete the `/ops` layout reframe so the live
screen packaging matches the cleaned decision-first operating model before the
deferred actual-domain activation slice begins.

The current project execution priority is:
1. preserve the completed hosted-path evidence set
2. preserve the completed `/ops` decision-first implementation and trust boundary
3. reframe `/ops` into a calmer section shell with stable left-side navigation
4. keep one dominant work surface per section and move support panels below or beside the main work
5. keep monitoring and system health visible, but structurally secondary to decision work
6. only after 1 to 5 are complete, run the deferred provider-coupled actual-domain activation proof slice
7. reach final explicit owner Go/No-Go immediately after that slice
8. confirm launch readiness before any deferred Ops power is reconsidered

## Current Blocker

No active Phase 1 blocker remains.
No active Phase 2 blocker remains.
No active Phase 3 blocker remains.

Current remaining launch gates are still final-activation gates:
1. live trainer submission E2E remains reserved for the final actual-domain activation decision
2. live provider exercise for notification and billing-coupled paths remains reserved for the final actual-domain activation decision
3. final owner launch approval remains intentionally withheld until the actual-domain activation slice is complete

Current execution blocker:
1. the current `/ops` screen shell is still noisier than the intended owner-reading model
2. the remaining launch gates are still reserved for the actual-domain activation slice

## Current Priority Order

1. preserve the completed hosted-path launch evidence against `LAUNCH_GATE.md`
2. preserve the completed `/ops` decision-surface improvements
3. complete the `/ops` layout reframe using the LeaseMate prototype only as layout reference
4. verify the reframe preserves DTD workflow evidence and Normal Ops boundaries
5. complete the deferred provider-coupled actual-domain activation slice
6. complete final owner Go/No-Go
7. only after 1 to 6 are complete may bounded owner controls be reconsidered
8. only after 7 is proven safe may technical-owner controls be reconsidered

## Current Accepted Scope

In scope now:
1. preservation of the trusted hosted-path evidence set
2. completed `/ops` decision-surface implementation as the baseline to preserve
3. `/ops` shell and section-layout reframe
4. documentation alignment for the reframe
5. deferred provider-coupled proof for the actual-domain activation decision
6. final owner Go/No-Go
7. `/ops` review of launch-critical workflow evidence during final activation work

Out of scope now:
1. Owner Override controls
2. Technical-Owner controls
3. public live matching enablement
4. broad admin CRUD
5. unrelated code refactors
6. public custom-domain activation
7. provider-coupled live trainer submission, notification, and billing exercise before the final actual-domain decision
8. importing LeaseMate business logic, request/cart flows, or non-DTD workflow language into DTD

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
12. the local end-to-end `/ops` optimisation pass now verifies against the updated local oversight contract:
   - overview now leads with a decision summary, next safest step, and plain-language attention counts
   - work queue now exposes a decision column, explicit case intent, and safer review-state guidance
   - trainer supply now exposes geography coverage, demand gaps, pace, blocked supply, and intro-ready trajectory signals
   - system activity remains visible as a supporting surface after the main decision surfaces

Still deferred at the project level:
1. final live provider exercise for external lifecycle paths, reserved for the actual-domain activation decision

Current readiness state:
1. website is owner/public review ready at the current baseline
2. Phase 2 is complete under the current governance scope
3. Phase 3 owner review is complete with a bounded outcome:
   - complete `/ops` optimisation before final activation work
   - keep No-Go on final public launch approval until the full final verification group passes
4. the first `/ops` optimisation pass is complete
5. the `/ops` layout reframe is still open before final activation work
6. final status remains `not launch-approved` until the deferred actual-domain activation checks are complete

Known remaining evidence gaps:
1. final live trainer submission E2E, deferred to the actual-domain activation decision
2. final live Stripe/Resend provider exercise, deferred to the actual-domain activation decision
3. final explicit owner approval after the actual-domain activation slice

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

1. the current `/ops` shell is still noisier than the intended owner-reading model
2. copying LeaseMate too literally would risk importing the wrong product model into DTD
3. the remaining launch gate is now the deferred actual-domain activation slice, not the trusted hosted path
4. stale local env values can mislead remote verification if they point to a retired backend URL
5. latent matching-capable code could be misread as the current product posture if authority order is ignored

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
5. preserve the completed decision-first `/ops` implementation during the layout reframe and final activation verification work

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

10. `2026-06-09`
- remaining DTD work reprioritised around how the owner actually uses `/ops`
- the new active order is:
  - decision surfaces first
  - supply/readiness decision support second
  - lifecycle/support wording cleanup third
  - monitoring/system-health separation fourth
  - final verification group later
- final public launch approval remains withheld until the later verification group is complete
- remaining non-provider blocker language narrowed to:
  - campaign-attribution persistence and clean discovery-lineage proof
  - elapsed-window autonomous-loop proof

11. `2026-06-08`
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
- Phase 2 is complete under the current governance scope
- next active phase is owner review and launch decision preparation
- only deferred actual-domain activation proofs remain

12. `2026-06-08`
- Phase 3 owner review and bounded Go/No-Go completed
- Browser review verified the key trusted hosted surfaces used for owner review:
  - `/`
  - `/trainers`
  - `/ops`
- launch-gate assessment confirmed the hosted-path non-provider evidence set is sufficient to move forward
- bounded decision recorded:
  - Go to the deferred actual-domain activation slice after remaining `/ops` completion work
  - No-Go on final public launch approval until the provider-coupled actual-domain checks pass

13. `2026-06-09`
- remaining `/ops` optimisation work completed
- local oversight contract extended with:
  - `ops_supply_geography`
  - `ops_supply_trends`
- overview now leads with decision-summary reading and plain-language next-step guidance
- work queue now exposes explicit decision guidance in both the table and the detail panel
- trainer supply now exposes geography coverage, demand gaps, pace, blocked supply, and intro-ready trajectory signals
- monitoring/system health remains visible as a supporting section instead of the primary operator reading surface
- local browser verification confirmed the decision-first `/ops` flow on desktop and mobile against the updated local backend contract
