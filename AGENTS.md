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
   - `docs/README.md` for the active documentation map
   - `docs/DTD_CURRENT_STATE.md`, `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md` and the relevant active `docs/specs/` file for the task domain
   - `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` when an old statement resurfaces
   - Never read `archive/` during routine work. It is historical, not an instruction source; inspect only on an explicit archival-research request.
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
7. Apply passive prompt optimization by default before execution:
   - internally rewrite ambiguous or verbose user prompts into concise, constraint-aware execution intent
   - preserve user objective exactly; do not expand scope
   - add explicit output shape and acceptance criteria when missing
   - only skip this rewrite when the user explicitly requests verbatim handling

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

## Deferred finding record

When an authorised task uncovers a material code, configuration, security, data, or workflow gap that is not fixed in that task, record it before closing the turn. Use `docs/DTD_CURRENT_STATE.md` for verified open findings; use `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` only for actual owner decisions. Each entry needs an ID, observation date, evidence and uncertainty, impact, why it was deferred, and the next action or decision gate. Close an entry only with verification evidence, then remove it from the live open-findings section; git history preserves the audit trail without a growing resolved backlog. This is incremental discovery, not a claim that the codebase has been fully reconciled or audited.

This repository is public. Never put a credential, personal data, private artifact URL, or exploit instructions in the record. Keep the entry actionable but sanitised; report sensitive particulars to the owner separately. Escalate an urgent exposure instead of treating documentation as remediation.

## 8) Turn Summary Requirement

Include `Active skills this turn:` in responses whenever any skill is active.

## 9) Unacceptable Underimplementation & Strict Verification Mandate (Locked)

Underimplementation and lack of verification are UNACCEPTABLE and SHALL NOT happen again.

When executing any task, migration, or refactoring:
1. **Zero Tolerance for Partial Work:** Do not stop execution simply because the compiler passes or the script runs without errors. You are responsible for the entire end-to-end functionality, including visual state, aesthetics, and edge cases.
2. **Explicit Verification Mandate:** You MUST rigorously verify the final outcome of your changes. For frontend tasks, this means ensuring all styling dependencies (fonts, plugins, external CSS) are active and the UI maintains its premium feel. For backend tasks, this means verifying the entire request lifecycle.
3. **Escalate Instead of Assuming:** If you cannot definitively verify the outcome due to environmental constraints, you must escalate and ask the user to manually verify before moving on or marking the task as complete.
