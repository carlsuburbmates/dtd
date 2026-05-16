# Codex Capability Routing Matrix (Non-Locking)

Date: 2026-05-17  
Scope: execution-quality routing guidance for future Codex sessions in this repo.

## Purpose

This matrix standardizes capability selection while keeping skill access broad.

Rules:
1. Guidance only: this file does not lock or allowlist skills.
2. Use only capabilities available in the current session.
3. Keep guardrails from `AGENTS.md`, `ROADMAP.md`, and `LOCK_STATE.md` in force.

## Routing Principles

1. Prefer the smallest capable toolchain that achieves the outcome.
2. Use browser/visual inspection by default when frontend behavior or presentation changes.
3. Use subagents only when parallel specialist work materially reduces risk or cycle time.
4. Use repeatable skill/plugin workflows for audits, verification, and evidence-heavy tasks.
5. Always report capabilities used, skipped, risks, dependencies, and evidence.

## Task-to-Capability Matrix

| Task Type | Primary Capability Set | Secondary/Optional | When To Skip | Minimum Evidence |
|---|---|---|---|---|
| Repo governance/docs policy update | Repo search + targeted file edits + consistency re-read | `analyze-project` skill | Skip skills/subagents for small scoped doc edits | changed files + consistency check summary |
| Frontend UI/layout/theme change | Repo edits + Browser visual inspection (desktop/mobile) + frontend build | accessibility audit skill; copy/refinement skill | Skip browser only if no UI-affecting change | build result + screenshots or route visual checks |
| Frontend copy/claim safety update | Repo edits + copy guard scripts + Browser spot check | copy refinement skill | Skip browser for tiny text-only internal docs changes | script output + affected file references |
| Backend endpoint/logic change | Repo edits + targeted backend tests + architecture/governance cross-check | backend/architecture skill | Skip subagents for isolated low-risk fix | test output + route/function impact summary |
| Billing/auth/migration risk review | Parallel review (subagents) + governance docs + targeted tests | security/billing skills | Skip subagents only for clearly trivial no-risk change | findings list + validation outputs + guardrail confirmation |
| Workflow gap / traceability audit | Repo-wide analysis + workflow sheet reconciliation | `analyze-project` or architecture skill | Skip plugins when local docs/code already sufficient | mapped workflow deltas + status updates |
| Release readiness / prelaunch check | Existing project scripts + CI parity checks + selective browser smoke | GitHub plugin (if CI/PR context needed) | Skip browser only if no frontend artifact changed | gate script outputs + test/build results |
| Cross-domain session (frontend+backend+governance) | split work by area + optional subagents + integrated verification bundle | multiple skills/plugins as needed | Skip subagents if change is too small to parallelize | integrated evidence package across all touched areas |

## Capability Selection by Risk

1. Low risk:
- single-surface changes, narrow diff
- minimal toolchain and fast validation bundle
2. Medium risk:
- cross-file behavior changes or policy updates
- add architecture/workflow consistency checks
3. High risk:
- billing/auth/runtime ownership/production-state interactions
- prefer parallel specialist review and stronger evidence before completion

## Session Availability Rule

At task start, route against currently available capabilities only:
1. core local tools (repo analysis/editing/tests)
2. available skills
3. available plugins/browser tools
4. available integrations/apps

If a capability is unavailable, choose the nearest safe fallback and state why.
