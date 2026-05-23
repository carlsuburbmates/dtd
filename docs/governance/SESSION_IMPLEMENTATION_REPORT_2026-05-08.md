# Session Implementation Report

Historical artifact. Not current authority. Preserved for evidence/history only.
Current authority is `docs/governance/CURRENT_TRUTH_INDEX.md` and the Standards Set.

Date: 2026-05-08
Scope: architecture + workflow alignment, conflict resolution, and implementation planning for next session.

## Purpose

Provide a single, implementation-ready report that consolidates prior findings from this thread into:

1. confirmed problems/conflicts,
2. prioritized recommendations,
3. rationale per recommendation,
4. execution order and acceptance criteria for follow-on implementation.

## Source artifacts reviewed

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/audit/WORKFLOW_GAP_REVIEW_2026-05-08.md`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md`
3. `/Users/carlg/Documents/AI-Coding/dtd/docs/WORKFLOW_TRACE_SHEET.md`
4. `/Users/carlg/Documents/AI-Coding/dtd/docs/ARCHITECTURE.md`
5. `/Users/carlg/Documents/AI-Coding/dtd/docs/OPERATIONS.md`
6. `/Users/carlg/Documents/AI-Coding/dtd/docs/governance/ROADMAP.md`
7. `/Users/carlg/Documents/AI-Coding/dtd/backend/worker.py`
8. `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py`
9. `/Users/carlg/Documents/AI-Coding/dtd/backend/services/engine.py`
10. `/Users/carlg/Documents/AI-Coding/dtd/backend/services/stripe_billing.py`
11. `/Users/carlg/Documents/AI-Coding/dtd/docs/test_reports/iteration_3.json`

## Executive summary

The system is architecturally strong in autonomous matching and operational loops, but there are two classes of risk:

1. runtime architecture risk (loop ownership/scheduling conflicts),
2. operating-model/documentation risk (missing growth/onboarding/revenue lifecycle workflows and a few policy-language inconsistencies).

Highest-priority technical risk is loop ownership ambiguity that can allow duplicate loop scheduling depending on process startup and environment defaults.

## Confirmed findings

### A. Runtime architecture conflicts

1. `High` — Worker startup can still allow duplicate loop scheduling under inconsistent env defaults.
Evidence:
- `/Users/carlg/Documents/AI-Coding/dtd/backend/worker.py:35`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/worker.py:38`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:990`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:992`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/services/engine.py:638`

2. `High` — No cross-process lease/leader lock; loop execution is local and can duplicate across multiple runtime owners.
Evidence:
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:990`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/services/engine.py:638`

3. `Medium` — One test artifact still reports 6 loops while runtime schedules 8 loops, creating handoff confusion.
Evidence:
- `/Users/carlg/Documents/AI-Coding/dtd/backend/services/engine.py:643`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/services/engine.py:650`
- `/Users/carlg/Documents/AI-Coding/dtd/docs/test_reports/iteration_3.json:2`
- `/Users/carlg/Documents/AI-Coding/dtd/docs/test_reports/iteration_3.json:34`

### B. Workflow and policy-model conflicts

4. `Medium` — Workflow taxonomy labels demand-capture as acquisition and omits explicit demand-generation workflows.
Evidence:
- `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:15`
- `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:69`
- `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:166`

5. `Medium` — Trainer onboarding is incomplete as a lifecycle (submission exists; activation/recovery/reactivation missing as first-class workflows).
Evidence:
- `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:78`
- `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:92`
- `/Users/carlg/Documents/AI-Coding/dtd/docs/audit/WORKFLOW_GAP_REVIEW_2026-05-08.md:78`

6. `Medium` — Monetization is represented as plumbing and passive billing, not full lifecycle operations.
Evidence:
- `/Users/carlg/Documents/AI-Coding/dtd/docs/USER_WORKFLOWS.md:92`
- `/Users/carlg/Documents/AI-Coding/dtd/docs/WORKFLOW_TRACE_SHEET.md:22`
- `/Users/carlg/Documents/AI-Coding/dtd/docs/audit/WORKFLOW_GAP_REVIEW_2026-05-08.md:109`

7. `Low` — Submission endpoint docstring says auto-publish threshold `>= 0.85`, but behavior publishes at `>= 0.60` as unverified.
Evidence:
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:521`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:550`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:555`

8. `Low` — Oversight “revenue” is derived from billed-intro/conversion status, while collection outcomes are tracked separately; this can be misread as cash-collected.
Evidence:
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:668`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:691`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/server.py:720`
- `/Users/carlg/Documents/AI-Coding/dtd/backend/services/stripe_billing.py:147`

## Recommendations with rationale

### R1. Enforce a single loop-owner contract in code and startup paths (`P0`)

Change:
1. Centralize loop-owner resolution into one shared function/config contract.
2. Prevent `server.on_startup()` from scheduling loops when called from worker bootstrap path.
3. Add a startup assertion/log block that states resolved owner and scheduled loop count.

Rationale:
1. Eliminates the highest-risk conflict (duplicate autonomous actions).
2. Makes runtime behavior deterministic and auditable across environments.
3. Reduces hidden coupling between API startup defaults and worker defaults.

Tradeoff:
1. Slightly more startup wiring complexity.
2. Requires careful migration to avoid downtime during rollout.

Acceptance:
1. API-only mode schedules loops once.
2. Worker-owned mode schedules loops once.
3. Mixed-mode misconfiguration exits with explicit error.
4. Oversight loop timestamps no longer show duplicate rapid updates from multiple owners.

### R2. Add a lightweight distributed loop lease (`P0`)

Change:
1. Use a DB-backed lease (for example `system_state` key with owner id + ttl) before loop scheduling.
2. Only the lease holder runs loops; others retry/idle.

Rationale:
1. Prevents duplicate loops when horizontal scaling or accidental dual process ownership occurs.
2. Aligns architecture with autonomous control-plane expectations.

Tradeoff:
1. Adds coordination logic and failure-mode handling.
2. Requires TTL and heartbeat tuning.

Acceptance:
1. In two-process simulation, only one process performs loop writes at any time.
2. On owner termination, standby process acquires lease within bounded failover window.

### R3. Reconcile workflow taxonomy and extend missing workflow families (`P1`)

Change:
1. Update workflow map to separate demand-generation from demand-capture.
2. Add missing workflows proposed earlier (`W15-W19`) for marketing, onboarding completion, revenue recovery, and trainer reactivation.
3. Keep existing `W1-W14` but reclassify and relabel where necessary.

Rationale:
1. Current catalog overstates completeness and hides missing operating loops.
2. A correct taxonomy is required before implementation sequencing and KPI ownership can be trusted.

Tradeoff:
1. More workflow IDs and documentation maintenance.
2. Temporary “planned/missing” rows until implementation catches up.

Acceptance:
1. `USER_WORKFLOWS.md` reflects full lifecycle coverage (demand, supply, revenue, trust).
2. `WORKFLOW_TRACE_SHEET.md` includes explicit statuses for added workflows.

### R4. Remove policy-language drift between code and docs (`P1`)

Change:
1. Align submission threshold language everywhere with implemented behavior (`>=0.60` publish, `>=0.85` verified).
2. Update stale loop-count references in old test artifacts and handoff notes.

Rationale:
1. Reduces operator and reviewer confusion.
2. Prevents future implementation from coding against incorrect documentation.

Tradeoff:
1. Requires touching multiple docs with no direct feature output.

Acceptance:
1. No doc claims conflict with current threshold behavior.
2. Loop count in docs/reports consistently states 8 current loops.

### R5. Split commercial KPIs into “booked” vs “collected” (`P2`)

Change:
1. In oversight payload/UI, expose separate revenue measures:
- `booked_revenue_cents` (status-based),
- `collected_revenue_cents` (paid/settled collection events),
- `at_risk_revenue_cents` (failed/disputed/uncollectible).
2. Add definitions in operations docs.

Rationale:
1. Current naming can mislead strategic decisions.
2. Improves monetization governance without changing existing billing flow.

Tradeoff:
1. More metrics and UI complexity.
2. Backfill logic may be needed for old rows.

Acceptance:
1. Oversight clearly distinguishes cash collection from booked demand.
2. Operations docs define each metric unambiguously.

### R6. Clarify roadmap scope boundaries (`P2`)

Change:
1. In roadmap, keep “website completion” as IA/routes/UX only.
2. Add explicit “business workflow completeness” stage with evidence gates.

Rationale:
1. Prevents governance ambiguity where route-complete is mistaken for operating-model complete.
2. Keeps stage claims evidence-driven and falsifiable.

Tradeoff:
1. Adds one more governance section to maintain.

Acceptance:
1. Roadmap status cannot be interpreted as full workflow completion without dedicated evidence.

## Implementation sequence (next session)

### Phase 0: Safety-first runtime hardening

1. Implement `R1`.
2. Implement `R2` (minimum viable lease).
3. Validate with local dual-process simulation and oversight timestamp checks.

### Phase 1: Workflow model correction

1. Implement `R3` doc updates.
2. Implement `R4` policy-language cleanup.
3. Mark new workflows as `planned/missing/partial/complete` in trace sheet.

### Phase 2: Commercial observability tightening

1. Implement `R5` metric separation in backend oversight payload.
2. Update ops UI and operations docs to reflect revised KPI semantics.
3. Implement `R6` roadmap scope clarifications.

## Discussion agenda for next session

1. Decide whether loop lease is mandatory now or staged behind an env flag.
2. Confirm canonical workflow ID expansion (`W15-W19`) and naming conventions.
3. Approve KPI semantics (`booked` vs `collected`) as product language.
4. Confirm acceptance thresholds for marking each recommendation complete.

## Ready-to-create implementation tasks

1. `TASK-A1` Loop ownership unification and single-scheduler guarantee.
2. `TASK-A2` DB lease-based autonomous loop leader election.
3. `TASK-D1` Workflow taxonomy update (`USER_WORKFLOWS.md` + `WORKFLOW_TRACE_SHEET.md`).
4. `TASK-D2` Documentation consistency pass (thresholds + loop count + roadmap scope).
5. `TASK-O1` Oversight revenue metric separation and operations doc update.

## Success criteria for the follow-on implementation session

1. No duplicate loop scheduling in any supported runtime mode.
2. Workflow model explicitly covers demand generation, onboarding completion, and revenue recovery.
3. Governance/docs contain no known contradictions with implemented behavior.
4. Oversight metrics distinguish economic booking from cash collection.
