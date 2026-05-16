# Codex Platform Sync

Date: 2026-05-07  
Scope: Codex interaction workflow only (no product or feature behavior changes)

## Global source

1. Primary (portable): repo-local Codex policy + governance files:
   - `AGENTS.md`
   - `.codex/skill-policy.toml`
   - `docs/governance/CODEX_PLATFORM_SYNC.md`
2. Optional external feed (machine-specific, when available): owner-managed global Codex update file.

## Adopted global delta

1. `20260507-03` | Type: Automation Policy | Decision: Adopt | Risk: low

## Active protocols (platform-only)

1. Keep global sync entries concise and date-stamped.
2. Promote only interaction deltas that pass the Codex test pack before broader reuse.
3. Use the global session bootstrap block when a thread needs Codex-platform sync:
   - `Sync to latest available global Codex optimization source and apply only Codex-platform improvements relevant to this session. If the external global source is unavailable, use repo-local policy and governance files as authoritative.`

## Session log

1. `2026-05-07`:
   - Synced this project to the global Codex feed bootstrap entry.
   - Applied docs-level platform interaction governance only.
   - No project-specific optimization changes applied in this sync.

## Guardrail

1. This file governs Codex operating behavior for sessions in this repo.
2. Product, architecture, billing, or UI strategy changes must continue through existing governance files and roadmap flow.
