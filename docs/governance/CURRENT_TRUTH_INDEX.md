# Current Truth Index

Last updated: 2026-07-02

## Purpose

This file is the only entry point for implementation and documentation-truth
routing in this repo.

Rules:
1. only the docs listed under `Canonical implementation pack` govern implementation truth
2. docs listed under `Execution control` govern current work sequencing and current state only
3. docs listed under `Verification and evidence` support proof and runtime review only
4. process docs and any design docs not explicitly listed in the canonical implementation pack are non-authoritative support material
5. if a doc is not explicitly listed below, it must not drive implementation or truth decisions

## Core Execution Authorities

These govern Codex session behavior and execution method, not product truth:
1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
4. `docs/governance/CURRENT_TRUTH_INDEX.md`

## Canonical Implementation Pack

These docs define the intended DTD website and operating model:
1. `docs/standards/SSOT.md`
2. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`
3. `docs/governance/WORKFLOW_COMPLETION_SPEC.md`
4. `docs/governance/WORKFLOW_SURFACE_MATRIX.md`
5. `docs/design/WEBSITE_WIREFRAME_SPEC.md`
6. `docs/governance/OPERATIONS_CONSOLE_SPEC.md`
7. `docs/governance/OPS_WIREFRAME_BLUEPRINT.md`
8. `docs/governance/OPS_DAILY_OPERATING_MANUAL.md`
9. `docs/design/WIREFRAME_STATE_MAP.md`
10. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`
11. `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`
12. `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`
13. `docs/standards/BUILD_CHECKLIST.md`
14. `docs/standards/LAUNCH_GATE.md`
15. `docs/standards/INTEGRITY_AUDIT.md`

## Execution Control

These docs govern active work and current-state control. They must not redefine
product or workflow truth:
1. `docs/governance/EXECUTION_STATUS.md`
2. `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`

## Verification And Evidence

These docs support verification, runtime review, and proof continuity. They do
not override normative truth:
1. `docs/governance/LOCK_STATE.md`
2. `docs/governance/RUNTIME_EVIDENCE_ALIGNMENT_MATRIX.md`
3. `docs/governance/CANONICAL_INTEGRATIONS.md`
4. `docs/process/PRELAUNCH_CHECKS_RUNBOOK.md`
5. `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md`
6. `docs/process/CURATED_SYNC_PACKAGE_PLAN.md`
7. `docs/process/IMPLEMENTATION_EVIDENCE_MANIFEST.md`

## Canonical Pack Precedence

When canonical docs disagree, resolve in this order:
1. `docs/governance/CURRENT_TRUTH_INDEX.md` routes authority only
2. `docs/standards/SSOT.md` governs product model, actor types, launch model, and operating rules
3. `docs/governance/WORKFLOW_COMPLETION_SPEC.md` governs end-to-end workflow completion and E2E completion criteria
4. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` governs page-level and route-level behavior
5. `docs/governance/WORKFLOW_SURFACE_MATRIX.md` governs the canonical workflow-to-route-to-ops mapping
6. `docs/design/WEBSITE_WIREFRAME_SPEC.md` governs website-wide structural layout, module order, and visual reading hierarchy outside the detailed `/ops` blueprint
7. `docs/governance/OPERATIONS_CONSOLE_SPEC.md` governs the current `/ops` product surface and operator-facing semantics
8. `docs/governance/OPS_WIREFRAME_BLUEPRINT.md` governs the structural layout, grouping, and reading hierarchy of `/ops`
9. `docs/governance/OPS_DAILY_OPERATING_MANUAL.md` governs day-to-day `/ops` reading order, operating priorities, and visual/data prioritisation for the owner
10. `docs/design/WIREFRAME_STATE_MAP.md` governs canonical screen-state coverage under workflow and page truth
11. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md` governs `/ops` responsibility boundaries and escalation layers
12. `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` and `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` govern the current supply-first phase goals and evidence model
13. `docs/standards/BUILD_CHECKLIST.md`, `docs/standards/LAUNCH_GATE.md`, and `docs/standards/INTEGRITY_AUDIT.md` govern build, launch approval, and verification requirements

## Execution Control Rules

1. `docs/governance/EXECUTION_STATUS.md` is the only current-state controller
2. `docs/process/WEBSITE_COMPLETION_CHECKLIST.md` is the execution checklist only
3. execution docs may not redefine product truth, workflow truth, page truth, or `/ops` behavior

## Verification And Evidence Rules

1. evidence docs may support or challenge a claim
2. evidence docs may not redefine product, workflow, page, or `/ops` truth
3. runtime snapshots must not be mistaken for normative implementation requirements

## Process-Only Docs

These docs support repo workflow and orientation only. They must not define
implementation truth:
1. `README.md`
2. `.codex/templates/CAPABILITY_BRIEF_TEMPLATE.md`
3. `.codex/templates/FINAL_EVIDENCE_TEMPLATE.md`

## Design Docs

These docs support design continuity only. They must not define implementation
scope:
1. `docs/design/README.md`
2. `docs/design/FIGMA_SYNC_PLAYBOOK.md`
3. `docs/design/FIGMA_COMPONENT_MAP.md`
4. `docs/design/NO_PAYWALL_WORKFLOW.md`
5. `docs/design/DESIGN_ALIGNMENT_REPORT_2026-05-07.md`
6. `docs/design/design_guidelines.json`

## Resolution Order

When conflicts exist, resolve in this order:
1. core execution authorities
2. canonical implementation pack
3. execution control
4. verification and evidence
5. process-only docs
6. design docs
