# Codex Execution Playbook

Date: 2026-05-17  
Scope: repeatable execution workflow for future Codex sessions.

## 1) Mandatory Pre-Execution Brief

Before implementation, publish a concise capability brief:
1. relevant capabilities (tools/skills/plugins/subagents/browser/integrations)
2. what will be used
3. what will be skipped
4. why skipped capabilities are not needed
5. key risks and dependencies

Use template: `.codex/templates/CAPABILITY_BRIEF_TEMPLATE.md`.

For integrated tech and tool work:
1. actively prefer the available relevant native capability when it materially improves implementation quality or evidence quality
2. do not default to manual-only implementation or inspection when a relevant available plugin, browser workflow, subagent, or integration-aware skill is a better fit
3. if a relevant capability is skipped, state why it was not needed for the active scope
4. if a blocker is discovered during execution, call it out immediately and fix it in the same execution path unless a locked guardrail, destructive migration, missing approval, or external-runtime impossibility prevents that fix

## 2) Skill Suggestions Standard

Before optional skill use, provide:
- Skill
- Why matched
- Risk (`low`, `medium`, `high`)
- Dependencies
- Recommended action (`Use`, `Skip`, `Ask`)

Policy behavior comes from `.codex/skill-policy.toml`.

## 3) Subagent Playbooks (When to Parallelize)

Use subagents only when parallel specialist review has clear value.

Playbook A: Frontend UX + Accessibility + Copy
1. Agent 1: visual/UX review
2. Agent 2: accessibility/semantic review
3. Agent 3: copy/claims guardrail review
Use when: major page redesign, new funnel page, broad CTA changes.

Playbook B: Backend Change + Validation
1. Agent 1: logic/risk review
2. Agent 2: tests and failure-mode verification
Use when: billing/auth/loop/runtime control changes.

Playbook C: Documentation + Evidence Audit
1. Agent 1: workflow/governance consistency
2. Agent 2: evidence/runbook completeness
Use when: status/gate claims are updated.

Do not parallelize when:
1. change is tiny and single-file
2. review overhead exceeds implementation cost
3. no independent write/read scopes exist

## 4) Verification Bundles

Choose the smallest bundle that matches change scope.

Bundle D (Docs-only)
1. Re-read changed docs for contradictions.
2. Verify referenced paths/files exist.
3. If governance/policy changed, ensure `AGENTS.md` and policy docs still align.

Bundle F (Frontend-impacting)
1. Run frontend production build.
2. Run copy/claim guard scripts when applicable.
3. Browser visual check for changed routes (desktop + mobile).
4. Confirm key CTA/interaction path still works.

Bundle B (Backend-impacting)
1. Run targeted backend tests for changed area.
2. Run compile/import sanity for touched backend modules.
3. Verify API/workflow docs stay consistent with route/function changes.

Bundle X (Cross-surface)
1. Run Bundle B + F + D.
2. Provide one integrated risk summary across all touched areas.

## 5) Browser/Visual Default Rule

For frontend changes, visual verification is default:
1. inspect at least one desktop viewport and one mobile viewport
2. check changed route(s) and one adjacent high-traffic route
3. include resulting evidence in final report

Skip only with explicit reason (for example: no UI/runtime change).

## 6) Final Evidence Schema

Use template: `.codex/templates/FINAL_EVIDENCE_TEMPLATE.md`.

Required sections:
1. capabilities used
2. capabilities skipped and why
3. outputs produced by each used capability
4. how outputs affected implementation decisions
5. validation results
6. residual risks or open gaps

When implementation required a bounded execution-time decision:
1. record the decision separately from the normal change summary
2. state the affected area
3. state the evidence basis used, preferring:
   - canonical standards and product docs
   - codebase/runtime evidence
   - official docs for active integrations/tools
   - market-appropriate best option within locked scope
4. state why that decision was the best bounded choice
5. include supporting evidence in the final report

## 7) Safety and Guardrails

Capability use never overrides locked guardrails:
1. no matching unlock without approval
2. no billing activation without approval
3. no auth replacement without approval
4. no backend changes unless approved when required by project gate
5. no production deploy without approval
6. no unauthorized market-coverage or guaranteed-outcome claims
7. no scope expansion without explicit instruction
8. execution blockers should be fixed immediately when they can be fixed safely inside these guardrails
