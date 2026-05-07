# Design Alignment Report (2026-05-07)

## Purpose

Ensure all design-related docs in the repo are aligned for uninterrupted multi-session development.

## Documents reviewed

1. `/Users/carlg/Documents/AI-Coding/dtd/docs/design_guidelines.json`
2. `/Users/carlg/Documents/AI-Coding/dtd/docs/audit/FRONTEND_AUDIT_ERRATA_2026-05-02.md`
3. `/Users/carlg/Documents/AI-Coding/dtd/docs/governance/NEXT_SESSION_HANDOFF.md`
4. `/Users/carlg/Documents/AI-Coding/dtd/docs/design/FIGMA_SYNC_PLAYBOOK.md`
5. `/Users/carlg/Documents/AI-Coding/dtd/docs/design/FIGMA_COMPONENT_MAP.md`
6. `/Users/carlg/Documents/AI-Coding/dtd/docs/design/NO_PAYWALL_WORKFLOW.md`
7. `/Users/carlg/Documents/AI-Coding/dtd/frontend/design-tokens/dtd.figma.tokens.json`
8. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Home.jsx`
9. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/components/PublicChrome.jsx`
10. `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/index.css`

## Alignment results

1. Visual direction is aligned:
- Organic/light public surface + dark/dense ops surface are consistent between `design_guidelines.json` and current code.

2. Typography direction is aligned:
- `Cormorant Garamond`, `Outfit`, and `JetBrains Mono` are present and used in runtime styles.

3. Token strategy is aligned:
- Runtime CSS variables and Figma token export are semantically aligned for public/admin modes.

4. Workflow alignment is now explicit:
- No-paywall, code-first workflow is documented and linked from the design index.

5. Figma constraints are documented:
- Starter page cap and MCP quota constraints are captured in the sync playbook.

## Resolved ambiguity

1. Canonical source order is now explicit in:
- `/Users/carlg/Documents/AI-Coding/dtd/docs/design/README.md`

2. `design_guidelines.json` is treated as creative direction reference, not runtime source-of-truth.

## Required maintenance rule

For any future design change, update in the same session:

1. Runtime implementation (code)
2. `dtd.figma.tokens.json` (if token semantics changed)
3. `FIGMA_COMPONENT_MAP.md` (if component API changed)
4. `FIGMA_SYNC_PLAYBOOK.md` (if process/constraints changed)
