# DTD Figma Sync Playbook

Updated: 2026-05-07

## Scope

This document is the continuity guide for Figma design-system synchronization for this repo:

- Repo: `/Users/carlg/Documents/AI-Coding/dtd`
- Target Figma file: https://www.figma.com/design/Is3zJpOaGhUo2nrTFzHww6
- File key: `Is3zJpOaGhUo2nrTFzHww6`

## Current status

Completed in Figma:

1. Page structure (Starter-compatible):
- `Cover`
- `Foundations`
- `Components`

2. Variable collections:
- `DTD/Primitives` (22 variables)
- `DTD/Color` (22 variables; modes: `Public Light`, `Admin Dark`)
- `DTD/Spacing` (9 variables)
- `DTD/Radius` (6 variables)

Not completed yet in Figma:

1. Text styles
2. Effect styles
3. Component sets and variants
4. Code Connect mappings

## Source-of-truth in codebase

Use these files as canonical inputs for future sync sessions:

1. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/index.css`
2. `/Users/carlg/Documents/AI-Coding/dtd/frontend/tailwind.config.js`
3. `/Users/carlg/Documents/AI-Coding/dtd/frontend/design-tokens/dtd.figma.tokens.json`
4. `/Users/carlg/Documents/AI-Coding/dtd/docs/design/FIGMA_COMPONENT_MAP.md`
5. `/Users/carlg/Documents/AI-Coding/dtd/docs/design/NO_PAYWALL_WORKFLOW.md`

Direction references (non-canonical, but relevant):

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/design_guidelines.json`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/audit/FRONTEND_AUDIT_ERRATA_2026-05-02.md`
3. `/Users/carlg/Documents/AI-Coding/dtd/docs/design/DESIGN_ALIGNMENT_REPORT_2026-05-07.md`

## External constraints

As of 2026-05-07:

1. Starter plan file structure limit:
- 3 pages max per file.

2. Figma MCP call quotas:
- Starter or View/Collab seats: up to 6 MCP tool calls per month.
- Some tools are exempt from standard MCP limits (`whoami`, `add_code_connect_map`, `generate_figma_design`).

Reference:
- https://developers.figma.com/docs/figma-mcp-server/plans-access-and-permissions/

## Session resume checklist

At the start of each new session:

1. Confirm current branch and working tree state.
2. Open the Figma file URL above and verify pages still exist (`Cover`, `Foundations`, `Components`).
3. Confirm MCP access with `whoami`.
4. If MCP is limited, switch to the no-paywall workflow immediately.
5. Keep updates additive and idempotent (do not recreate existing token collections).

## Next MCP sync pass (when quota allows)

1. Create text styles:
- `Typography/Public/H1`, `H2`, `H3`, `Body`, `Label`
- `Typography/Admin/H1`, `Metric`, `TableHeader`, `TableCell`

2. Create effect styles:
- `Effect/Public/CardShadow`

3. Build component sets on `Components` page:
- `Button`, `Card`, `Badge`, `Input`
- `PublicHeader`, `PublicFooter`

4. Add React Code Connect mappings according to:
- `/Users/carlg/Documents/AI-Coding/dtd/docs/design/FIGMA_COMPONENT_MAP.md`

## Non-MCP fallback

If MCP is blocked or quota-limited:

1. Continue evolving tokens/components in code first.
2. Update token JSON and component map in this repo.
3. Apply changes manually in Figma UI only for screens needed for review.
4. Defer full MCP sync to a quota-reset session.
