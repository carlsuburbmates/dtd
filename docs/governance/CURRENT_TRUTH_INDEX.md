# Current Truth Index
Last updated: 2026-05-25

## Purpose

This file is the only entry point for future implementation work in this repo.

Rules:
1. Only the docs listed under `Canonical implementation pack` govern implementation.
2. Docs listed under `Runtime/code audit support` may be used during a no-edit code audit, but they do not define product truth by themselves.
3. Docs listed under `Runtime snapshot evidence` are evidence-only and must not override normative implementation truth.
4. Process and design docs are non-authoritative support material.
5. If a doc is not explicitly listed below, it must not drive implementation decisions.

## Core execution authorities

These govern Codex session behavior, not product definition:
- `AGENTS.md`
- `.codex/skill-policy.toml`
- `docs/governance/CURRENT_TRUTH_INDEX.md`

## Canonical implementation pack

These docs define the intended DTD website and operating model for implementation:
- `docs/standards/SSOT.md`
- `docs/standards/BUILD_CHECKLIST.md`
- `docs/standards/LAUNCH_GATE.md`
- `docs/standards/INTEGRITY_AUDIT.md`
- `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`
- `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md`
- `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md`
- `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`

## Runtime/code audit support

These docs support no-edit audit and sequencing work. They are not standalone product-definition sources:
- `docs/governance/ROADMAP.md`
- `docs/governance/RUNTIME_EVIDENCE_ALIGNMENT_MATRIX.md`

## Runtime snapshot evidence

These docs are runtime/evidence snapshots only. They do not override normative implementation truth, and they do not define product, page, or route truth:
- `docs/governance/LOCK_STATE.md`

## Canonical pack precedence

When canonical docs disagree, resolve within the pack in this order:
1. `docs/governance/CURRENT_TRUTH_INDEX.md` routes authority; it does not define product behavior by itself.
2. `docs/standards/SSOT.md` governs product model, launch model, route classes, and operating rules.
3. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` governs route-level and page-level behavior.
4. `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` and `docs/INITIAL_LAUNCH_EVIDENCE_MODEL_SUPPLY_FIRST.md` govern the current supply-first prelaunch goals and evidence model.
5. `docs/governance/OPS_COCKPIT_RESPONSIBILITY_MODEL.md` governs `/ops` responsibility boundaries and operator-mode separation.
6. `docs/standards/BUILD_CHECKLIST.md`, `docs/standards/LAUNCH_GATE.md`, and `docs/standards/INTEGRITY_AUDIT.md` govern build, launch-approval, and verification requirements.
7. `docs/governance/LOCK_STATE.md` is runtime/governance snapshot evidence only. It must not override `SSOT.md` or `COMPLETE_WEBSITE_PAGE_SPEC.md`, and it does not define product, page, or route truth.

## Process-only docs

These docs support repo workflows, Codex operation, deployment/runbook continuity, and session handoff. They must not define implementation scope:
- `README.md`
- `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
- `docs/process/WEBSITE_COMPLETION_CHECKLIST.md`
- `docs/process/NEXT_SESSION_HANDOFF.md`
- `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md`
- `docs/process/IMPLEMENTATION_EVIDENCE_MANIFEST.md`
- `docs/process/PRELAUNCH_CHECKS_RUNBOOK.md`
- `docs/process/CURATED_SYNC_PACKAGE_PLAN.md`
- `.codex/templates/CAPABILITY_BRIEF_TEMPLATE.md`
- `.codex/templates/FINAL_EVIDENCE_TEMPLATE.md`

## Design docs

These docs support design continuity only. They must not define implementation scope:
- `docs/design/README.md`
- `docs/design/FIGMA_SYNC_PLAYBOOK.md`
- `docs/design/FIGMA_COMPONENT_MAP.md`
- `docs/design/NO_PAYWALL_WORKFLOW.md`
- `docs/design/DESIGN_ALIGNMENT_REPORT_2026-05-07.md`
- `docs/design/design_guidelines.json`

## Resolution order

When conflicts exist, resolve in this order:
1. core execution authorities
2. canonical implementation pack
3. runtime/code audit support
4. runtime snapshot evidence
5. process-only docs
6. design docs
