# DTD Website Wireframe Spec

Date: 2026-06-09
Scope: canonical structural wireframe specification for the DTD website outside
the detailed `/ops` blueprint.

## Purpose

This document defines how the DTD website should be structurally composed so the
main routes, page groups, and key transitions read clearly and support the
intended workflows end to end.

It exists to answer:

> How should each canonical route be structurally laid out, in what order should
> its major modules appear, and what visual reading path should guide the user
> toward the correct next step?

It does not define:
1. workflow completion rules
2. route existence or route intent
3. detailed screen-state variants
4. component API or design-token contracts
5. the detailed `/ops` blueprint

## Authority And Role Boundaries

This file is part of the canonical implementation pack for website-wide
structural composition.

Role boundaries:
1. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` defines route purpose, required
   sections, and behavior.
2. `docs/governance/WORKFLOW_SURFACE_MATRIX.md` maps workflows to routes,
   surfaces, and `/ops` evidence.
3. this file defines structural page composition, module order, and cross-route
   reading paths for public and lifecycle routes.
4. `docs/governance/OPS_WIREFRAME_BLUEPRINT.md` defines the structural layout of
   `/ops`.
5. `docs/design/WIREFRAME_STATE_MAP.md` defines canonical state coverage.
6. `docs/design/FIGMA_COMPONENT_MAP.md` defines component naming and
   component-code mapping only.

If this file conflicts with workflow truth, page truth, or `/ops` truth, the
higher-authority document governs.

## Structural Principles

1. every page should make the next safe action obvious
2. every page should support a real workflow, not decorative browsing only
3. the first screen should explain posture before asking for commitment
4. the primary CTA should remain visually clear and truthful to the current
   launch phase
5. support, trust, and legal context should reduce friction without dominating
   the first read
6. lifecycle routes should feel guided and situational, not like generic
   marketing pages
7. `/ops` remains part of the website but uses its own dedicated blueprint

## Global Website Shell

All public and lifecycle routes should share these structural rules:
1. header with clear top-level navigation
2. readable page title or hero entry
3. one primary action consistent with route intent
4. secondary trust/support links where helpful
5. footer with legal and support continuity

The shell should always preserve:
1. clear trainer path continuity
2. clear owner path continuity
3. no implication of broad live matching while the current posture remains
   supply-first and waitlist-first
4. calm mobile readability

## Global Navigation Model

Primary top-level navigation should support:
1. home understanding
2. how it works
3. trust and product explanation
4. trainer onboarding
5. support/contact continuity

Primary route groups:
1. trust and education routes
2. trainer acquisition and lifecycle routes
3. owner lifecycle routes
4. attribution and localized entry routes
5. protected Ops route

## Route Group Blueprint

### 1. Trust And Education Routes

Routes:
1. `/`
2. `/how-it-works`
3. `/about`
4. `/pricing`
5. `/trust`
6. `/faq`
7. `/contact`
8. `/privacy`
9. `/terms`

These pages should structurally read from:
1. what this is
2. what the current posture is
3. why that posture exists
4. what the user should do next

They should not structurally read like:
1. a generic directory
2. a broad live marketplace
3. a dead-end brochure

### 2. Trainer Acquisition And Lifecycle Routes

Routes:
1. `/trainers`
2. `/submit`
3. `/submit/status/:submissionId`
4. `/trainer/billing`
5. `/trainer/reactivate`

These pages should structurally read from:
1. trainer understanding
2. trainer action
3. trainer state
4. trainer recovery

The owner should be able to inspect the same lifecycle from `/ops`, but the
route itself should still feel self-guiding to the trainer.

### 3. Owner Lifecycle Routes

Routes:
1. `/t/:id`
2. `/trainers/:id`
3. `/follow-up/:token`

These pages should structurally read from:
1. context
2. trust / consent
3. action
4. outcome / next step

### 4. Attribution And Localized Entry Routes

Routes:
1. `/lp/:campaign`
2. `/melbourne/:suburb`

These pages should structurally read like focused entry variants of the home
posture, not disconnected microsites.

### 5. Protected Ops Route

Route:
1. `/ops`

`/ops` belongs to the website system but its detailed wireframe is governed by
`docs/governance/OPS_WIREFRAME_BLUEPRINT.md`.

## Canonical Route Blueprint Table

| Route | Primary user / workflow support | First-read purpose | Structural module order | Primary action or outcome |
|---|---|---|---|---|
| `/` | Dog owner `W-DO-1`, trainer signpost `W-TR-1` | explain current posture and offer the right entry | hero and posture summary -> owner guidance -> waitlist form -> trainer CTA -> supporting trust/help blocks | join waitlist or continue to trainer path |
| `/how-it-works` | owner/trainer orientation | explain how DTD works now | hero explanation -> supply-first explanation -> owner path -> trainer path -> trust/support clarification | move into the right path with accurate expectations |
| `/about` | product framing | explain what DTD is and is not | product framing -> why quality/supply matters -> oversight/automation model -> trust continuity | improve trust and route into next relevant path |
| `/pricing` | trainer commercial understanding | explain the trainer-side model honestly | pricing framing -> intro-first model -> billing-readiness explanation -> non-guarantee clarification -> support path | continue to trainer submission path |
| `/trust` | trust/consent understanding | remove hesitation by clarifying boundaries | trust hero -> consent/contact-release explanation -> verification framing -> oversight/accountability framing | continue with a clearer trust model |
| `/faq` | pre-action clarification | answer common owner/trainer concerns | FAQ intro -> owner questions -> trainer questions -> lifecycle/billing questions -> support fallback | remove friction and direct into action |
| `/contact` | support workflow | provide one clear support path | purpose statement -> contact method -> expected use cases -> response expectation | contact support |
| `/privacy` | legal support | provide privacy baseline | legal content -> contact details | legal reading only |
| `/terms` | legal support | provide terms baseline | legal content -> contact details | legal reading only |
| `/trainers` | trainer acquisition `W-TR-1` | persuade the right trainers to continue | trainer value proposition -> how intros work -> who this is for -> next-step expectations -> submit CTA -> support path | proceed to `/submit` |
| `/submit` | trainer submission `W-TR-2` | collect trainer onboarding data safely | page context -> trainer details form -> consent/billing terms -> submission action -> result/next-step area | submit trainer details |
| `/submit/status/:submissionId` | trainer activation `W-TR-3`, `W-TR-4` | explain trainer state clearly | current status summary -> blockers or readiness explanation -> next-step guidance -> lifecycle CTA block -> support fallback | understand status and take the next recovery or wait step |
| `/trainer/billing` | billing remediation `W-TR-5` | guide safe billing recovery | issue summary -> billing profile/recovery context -> recovery action area -> support path | repair billing state |
| `/trainer/reactivate` | reactivation `W-TR-6` | guide return to active readiness | reactivation context -> recovery checklist -> next-step action -> support path | continue reactivation |
| `/t/:id` | owner detail and contact release `W-DO-3`, `W-DO-4` | help the owner judge and then connect | trainer summary -> trust/fit context -> consent/connect action -> contact outcome -> follow-up expectation | request or reveal contact under the current policy |
| `/trainers/:id` | alias to `/t/:id` | same as canonical trainer detail route | same as `/t/:id` | same as `/t/:id` |
| `/lp/:campaign` | campaign entry `W-DO-1` | preserve campaign context while keeping the same posture | focused hero -> campaign-relevant framing -> waitlist handoff -> trainer alternate path -> trust support | join waitlist from campaign entry |
| `/melbourne/:suburb` | localized owner entry `W-DO-1` | preserve suburb relevance while keeping the same posture | local relevance hero -> suburb guidance -> waitlist handoff -> trainer alternate path -> trust support | join waitlist from suburb entry |
| `/follow-up/:token` | owner follow-up `W-DO-5`, `W-DO-6` | capture an outcome quickly and clearly | context and why this matters -> outcome choice/action -> confirmation state -> support fallback | confirm outcome or lack of outcome |
| `/ops` | oversight workflows `W-OP-1`, `W-OP-2`, `W-OP-3` | owner review and decision surface | auth gate -> decision summary -> work queue -> supporting sections | read, review, decide, monitor |

## Shared Structural Rules By Page Type

### Marketing And Trust Pages

These pages should always have:
1. immediate posture clarity
2. one truthful main CTA
3. supporting educational blocks below the fold
4. trust and support continuity

### Form And Submission Pages

These pages should always have:
1. context before form fields
2. clear expectations before commitment
3. a contained form region
4. a visible result or next-step region
5. a support fallback

### Lifecycle Status And Recovery Pages

These pages should always have:
1. current state summary
2. explanation of what that state means
3. next-step guidance
4. recovery or wait-path continuity
5. support fallback

### Detail And Connect Pages

These pages should always have:
1. entity summary
2. trust and consent context
3. primary connect action
4. clear outcome or next-step explanation

## Cross-Route Transition Rules

The structural path between pages should remain clear:
1. home and campaign pages should feed the correct owner or trainer path
2. trainer acquisition should feed cleanly into trainer submission
3. submission should feed cleanly into status or recovery routes
4. trainer detail should feed cleanly into connect and follow-up lifecycle paths
5. support should remain reachable from all friction-heavy routes

No route should feel structurally isolated from the workflow it supports.

## Acceptance Rules

The website wireframe spec is structurally complete only when:
1. every canonical route has a clear first-read purpose
2. every canonical route has a truthful primary action or outcome
3. module order supports the workflow instead of fighting it
4. trust/support/legal surfaces reduce friction without diluting the main action
5. lifecycle routes feel guided rather than generic
6. `/ops` is treated as part of the website but still governed by its own
   dedicated blueprint
7. this document stays aligned with:
   - `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`
   - `docs/governance/WORKFLOW_SURFACE_MATRIX.md`
   - `docs/design/WIREFRAME_STATE_MAP.md`
   - `docs/governance/OPS_WIREFRAME_BLUEPRINT.md`
