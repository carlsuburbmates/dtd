# Current Truth Index

Last updated: 2026-09-11

## Purpose

This file is the single entry point for implementation and documentation-truth
routing in this repo.

Rules:
1. `docs/standards/DTD_PROJECT_CONTEXT.md` is the required high-signal project-context entry point
2. only the docs listed under `Canonical implementation pack` govern implementation truth
3. docs listed under `Execution control` govern current work sequencing and current state only
4. docs listed under `Verification and evidence` support proof and runtime review only
5. process docs and any design docs not explicitly listed in the canonical implementation pack are non-authoritative support material
6. if a doc is not explicitly listed below, it must not drive implementation or truth decisions

## Core Execution Authorities

These govern session behavior and execution method, not product truth:
1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
4. `docs/governance/CURRENT_TRUTH_INDEX.md`

## Canonical Implementation Pack

These docs define the intended DTD website, flywheel, architecture, monetization, and operating model:
1. `docs/standards/DTD_PROJECT_CONTEXT.md` (Required project orientation; routes agents to detailed authority without duplicating it)
2. `docs/strategy/DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md` (Governs product vision, flywheel, monetization tiers, ranking algorithms, and fairness controls)
3. `docs/strategy/DTD_AUTOMATION_AND_INTEGRATION_SPEC.md` (Governs background engines, platform integrations, communication triggers, and data contracts)
4. `docs/strategy/DTD_ACQUISITION_AND_INGESTION_PIPELINE.md` (Governs source selection, data-use boundaries, ingestion stages, acquisition activation gates, and post-launch supply maintenance; it supersedes conflicting acquisition text elsewhere)
5. `docs/strategy/DTD_GOOGLE_ECOSYSTEM_MIGRATION_AND_ARCHITECTURE_SPEC.md` (Governs Google ecosystem migration architecture, cutover design, and task sequencing; it cannot redefine the product, automation, or acquisition blueprints)
6. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`
7. `docs/governance/WORKFLOW_COMPLETION_SPEC.md`
8. `docs/governance/STAKEHOLDER_COMMUNICATION_CONTRACT.md`
9. `docs/governance/WORKFLOW_SURFACE_MATRIX.md`
10. `docs/design/WEBSITE_WIREFRAME_SPEC.md`
11. `docs/governance/OPERATIONS_CONSOLE_SPEC.md`
12. `docs/governance/OPS_WIREFRAME_BLUEPRINT.md`
13. `docs/governance/OPS_DAILY_OPERATING_MANUAL.md`
14. `docs/design/WIREFRAME_STATE_MAP.md`
15. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`
16. `docs/standards/BUILD_CHECKLIST.md`
17. `docs/standards/LAUNCH_GATE.md`
18. `docs/standards/INTEGRITY_AUDIT.md`

## Execution Control

These docs govern active work and current-state control. They must not redefine
product or workflow truth:
1. `docs/governance/EXECUTION_STATUS.md`
2. `docs/process/DTD_DELIVERY_ORCHESTRATION.md` (Codex-Antigravity delivery coordination only)
3. `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`

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
2. `docs/standards/DTD_PROJECT_CONTEXT.md` governs project orientation and supersedes older contextual summaries, but defers detailed rules to the blueprints below
3. `docs/strategy/DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md` governs product vision, 4-step flywheel, tier definitions, pricing, search ranking algorithms, and anti-monopoly fairness rules
4. `docs/strategy/DTD_AUTOMATION_AND_INTEGRATION_SPEC.md` governs autonomous background engines, 3rd-party integrations, communication triggers, state machines, and evidence schemas
5. `docs/strategy/DTD_ACQUISITION_AND_INGESTION_PIPELINE.md` governs source approval, acquisition, enrichment boundaries, publication gates, and post-launch supply maintenance
6. `docs/strategy/DTD_GOOGLE_ECOSYSTEM_MIGRATION_AND_ARCHITECTURE_SPEC.md` governs Google ecosystem migration architecture, cutover design, and task sequencing
7. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` governs page-level and route-level behavior when consistent with the product blueprint
8. `docs/governance/WORKFLOW_COMPLETION_SPEC.md` governs end-to-end workflow completion and E2E completion criteria
9. `docs/governance/STAKEHOLDER_COMMUNICATION_CONTRACT.md` governs lifecycle communication recipients, delivery states, reply routing, and communication exception evidence
10. `docs/governance/WORKFLOW_SURFACE_MATRIX.md` governs the canonical workflow-to-route-to-ops mapping
11. `docs/design/WEBSITE_WIREFRAME_SPEC.md` governs website-wide structural layout, module order, and visual reading hierarchy outside the detailed `/ops` blueprint
12. `docs/governance/OPERATIONS_CONSOLE_SPEC.md` governs the current `/ops` product surface and operator-facing semantics
13. `docs/governance/OPS_WIREFRAME_BLUEPRINT.md` governs the structural layout, grouping, and reading hierarchy of `/ops`
14. `docs/governance/OPS_DAILY_OPERATING_MANUAL.md` governs day-to-day `/ops` reading order, operating priorities, and visual/data prioritisation for the owner
15. `docs/design/WIREFRAME_STATE_MAP.md` governs canonical screen-state coverage under workflow and page truth
16. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md` governs `/ops` responsibility boundaries and escalation layers
17. `docs/standards/BUILD_CHECKLIST.md`, `docs/standards/LAUNCH_GATE.md`, and `docs/standards/INTEGRITY_AUDIT.md` govern build, launch approval, and verification requirements

## Execution Control Rules

1. `docs/governance/EXECUTION_STATUS.md` is the only current-state controller
2. `docs/process/DTD_DELIVERY_ORCHESTRATION.md` governs task handoff, dependency, integration, and recovery protocol only
3. `docs/process/WEBSITE_COMPLETION_CHECKLIST.md` is the execution checklist only
4. execution docs may not redefine product truth, workflow truth, page truth, or `/ops` behavior

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
