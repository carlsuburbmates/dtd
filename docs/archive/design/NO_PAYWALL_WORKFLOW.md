# DTD No-Paywall Design Workflow

Updated: 2026-05-07

## Goal

Allow continuous design and UI development before launch without depending on paid Figma/MCP quotas.

## Operating model

1. Source of truth is code and repo docs.
2. Figma is a visual review surface, not the primary system record.
3. MCP automation is optional and deferred when quota-limited.

## Primary artifacts (must stay current)

1. Tokens:
- `/Users/carlg/Documents/AI-Coding/dtd/frontend/design-tokens/dtd.figma.tokens.json`

2. Component mapping:
- `/Users/carlg/Documents/AI-Coding/dtd/docs/design/FIGMA_COMPONENT_MAP.md`

3. Sync runbook:
- `/Users/carlg/Documents/AI-Coding/dtd/docs/design/FIGMA_SYNC_PLAYBOOK.md`

4. Live implementation:
- `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Home.jsx`
- `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/components/PublicChrome.jsx`
- `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/index.css`

## Session workflow (default)

1. Update UI in React code first.
2. Update token JSON if colors/spacing/radius semantics changed.
3. Update component map if props/variants changed.
4. Run frontend production build.
5. Capture screenshots manually for stakeholders.
6. Mirror into Figma only as needed for presentations/reviews.

## MCP-minimized workflow (when quota exists)

Use MCP only for high-value tasks:

1. `whoami` to confirm seat/plan context.
2. `add_code_connect_map` for targeted mappings.
3. `use_figma` only for delta updates with high payoff.

Avoid low-value exploratory MCP calls on Starter plans.

## Exit criteria for upgrading

Upgrade Figma seat/plan only when one of these is true:

1. Weekly UI iteration speed is blocked by manual Figma updates.
2. Multiple collaborators need reliable design-to-code automation.
3. Launch operations require sustained Code Connect + MCP workflows.

## Risks and mitigations

1. Risk: design drift between code and Figma.
- Mitigation: code-first updates + artifact triad update every session (tokens/map/playbook).

2. Risk: loss of context across sessions.
- Mitigation: always append decisions and constraints to docs in this folder.

3. Risk: launch rush migration overhead.
- Mitigation: keep stable naming and variant contracts now so future bulk sync is mechanical.
