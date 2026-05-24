# Codex Session Execution Standards

This file defines how future Codex sessions should execute work in this repository.

## Codex Capability Utilisation Rule (`LOCKED`)

All tasks must actively consider Codex-native capabilities where useful, including:

- skills
- subagents
- plugins
- browser/visual inspection tools
- repo analysis tools
- test/build tooling
- available MCP/app integrations
- project-specific reusable workflows

Codex must not default to manual text editing when a more suitable native capability is available.

## 1) Preflight Routing (required)

At the start of each new task:

1. Inspect repo root context and user goal.
2. Read these files before acting:
   - `AGENTS.md`
   - `.codex/skill-policy.toml` (if present)
   - `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
   - relevant workflow/process docs in `docs/` for the task domain
3. Treat the current session's available skills/plugins/tools as the source of truth.
4. Do not assume a globally installed skill is callable unless it is available in-session.
5. Before starting implementation, report:
   - relevant native capabilities/tools
   - what will be used
   - what will be skipped
   - why skipped items are not needed
   - key risks/dependencies for chosen tools
6. Route capability selection through `.codex/skill-policy.toml` and use fallback logic if a listed capability is unavailable in-session.

## 2) Skill Suggestions (required before optional skill use)

Before using optional skills, provide a concise `Skill Suggestions` list with:

- Skill
- Why matched
- Risk (`low`, `medium`, `high`)
- Dependencies
- Recommended action (`Use`, `Skip`, `Ask`)

Default behavior:

- Keep the active skill set small and task-relevant.
- Use broad coverage by default; avoid allowlisting unless explicitly required by policy.

## 3) Skill Policy Gate

If `.codex/skill-policy.toml` exists, it controls routing behavior.

- Enforce `blocked_skills` always.
- Enforce `allowed_skills` only when present.
- If `require_explicit_composio_invocation = true`, require explicit `$composio-...` user invocation before any Composio skill use.

## 4) Approval Gates

Default approval behavior is policy-driven:

- For `mode = "suggest_then_approve"`:
  - Do not use optional skills until user approval is granted.
  - Ask before any external mutation, irreversible action, or spend-impacting action.
- Read-only local repo analysis/editing without optional skills does not require separate approval.

## 5) Execution Workflow Expectations

1. Prefer non-destructive changes.
2. Implement minimal, high-value changes first.
3. Keep docs and policy files aligned in the same session when governance behavior changes.
4. Fix stale workspace/path references in authoritative docs when discovered.
5. Use subagents when work benefits from parallel specialist review (for example: frontend UX/copy review, repo audit + validation, accessibility + responsive checks, billing/auth/migration risk review).
6. Use skills/plugins when the task matches a repeatable workflow (for example: frontend audit, copy refinement, accessibility review, test/build verification, release readiness, docs cleanup, evidence audit).

## 6) Safety Boundary (locked)

Capability use never overrides project guardrails. Keep all existing prohibitions in force, including:

- no matching unlock
- no billing activation
- no auth replacement
- no backend changes unless approved
- no production deploy unless approved
- no unauthorized public market-coverage claims
- no guaranteed outcomes claims
- no unapproved scope expansion

## 7) Validation Before Completion

Before finishing a task:

1. Re-read changed files for internal consistency.
2. Run targeted checks relevant to the change scope when practical.
3. Report what was changed, what was validated, and any remaining risks/gaps.
4. If any skill/subagent/plugin/browser/integration was used, include:
   - what was used
   - what each produced
   - how output affected implementation decisions
   - supporting evidence
5. If available capabilities were not used, explain why.
6. Prefer response structure from `.codex/templates/FINAL_EVIDENCE_TEMPLATE.md`.

## 8) Turn Summary Requirement

Include `Active skills this turn:` in responses whenever any skill is active.
