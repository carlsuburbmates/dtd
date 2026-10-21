---
name: dtd-premium-look-audit
description: Audit and refine DTD public-facing website pages, current owner/trainer journeys, navigation, copy, CTAs, accessibility, metadata and mobile visual polish. Align with the current R-stage and verified deployment posture, not obsolete supply-first assumptions; do not expand into backend, billing, auth or major redesign without task authority.
---

# DTD Premium look audit

Use this skill to make restrained, high-impact improvements to DTD's public website.
Start from business hierarchy and launch posture, not from decoration or generic conversion patterns.

## Source of truth and route discovery

Read proportionately in this order:
1. `AGENTS.md` and `.codex/skill-policy.toml`.
2. `docs/README.md`, `docs/DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md` (R stage), `docs/DTD_CURRENT_STATE.md` and `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`.
3. `docs/DTD_FULL_PROJECT_COMPLETION_PLAN.md`, the relevant `docs/specs/` contract (website, matching, acquisition or commercial copy as applicable), and Decision Contract v2 for matching-visible states.
4. `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` only if a previous choice conflicts.
5. Locate **actual** route components by inspecting current frontend directories/router/source at HEAD; never hardcode an assumed `frontend/src/App.js` or historical design-spec path. Inspect deployed website/flags if making live-posture claims.

The former `docs/process/CODEX_EXECUTION_PLAYBOOK.md`, `docs/governance/CURRENT_TRUTH_INDEX.md`, `docs/standards/SSOT.md`, `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, `docs/design/WEBSITE_WIREFRAME_SPEC.md`, `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md` and `frontend/src/App.js` were absent at the inspected release SHA. Do not create or follow substitute copies as if they were active authority. Archive/history are evidence only when explicitly requested.

## When To Use

Use this skill when the task is about:
1. homepage audit or refinement
2. landing page refinement
3. trainer-facing page improvement
4. owner questionnaire/results/profile/protected-enquiry and any **actually active** waitlist page refinement
5. navigation or footer cleanup
6. CTA hierarchy cleanup
7. public copy tightening
8. mobile UI polish
9. visual hierarchy review
10. removing cheap, scattered, repetitive, or internal-sounding public wording
11. checking applicable current public-page contracts before a broad public-site overhaul; updating an existing active specification only when the authorised task requires it

## When Not To Use

Do not use this skill when the task mainly requires:
1. database schema changes
2. auth changes
3. payment changes
4. matching logic changes
5. backend API changes
6. major route restructuring
7. full redesign work
8. new feature development
9. long-form education or curriculum rewrites
10. `/ops` product work unless the ask is limited to public-facing navigation or copy continuity

If the task crosses into these areas, route to the suitable skill and existing owner authority; ask only if the needed consequential action has not been authorised. An authorised cross-surface feature task need not stop merely because this visual skill is narrow.

## Approved current business context

1. DTD serves dog owners and legitimate trainers through trustworthy Greater Melbourne discovery and AI-assisted, evidence-bounded matching, with protected enquiry; it is not merely a generic directory and does not promise training outcomes.
2. **Do not hardcode** `supply_first`, `PUBLIC_MATCHING_ENABLED=false`, waitlist-first or assumed live matching. Determine present route/feature availability from active source, environment and deployed evidence. The previous documented public phase is `live_matching`, but current deployed status must be verified before copy claims.
3. Respect both owner and trainer journeys. Select CTA hierarchy using **the actual R stage, live posture, evidence and requested page purpose**, not an obsolete supply priority. Never show a gated CTA as operational.
4. Free owner use, no per-lead or introduction fees; commercial priority cannot falsify eligibility or fit. Public copy must distinguish actual claims, trainer declarations, official-source facts and review outcomes.
5. `/ops` is protected owner oversight, not a public marketing route. First Leash remains a separate education deployment with privacy-safe linking.
6. Visual polishing cannot authorise new matching states, payments, production settings, provider sources or product-policy changes.


## Premium Standard

Aim for pages that feel:
1. premium
2. intentional
3. visually calm
4. local where relevant
5. category-leading without inflated claims

Premium does not mean more decoration.
Prefer restraint, spacing, hierarchy, typography rhythm, clear CTAs, and removal of clutter.

## Audit Rubric

### 1. Business Hierarchy

Check whether the page supports the current business priority.
Ask:
1. Which audience is primary in this task: trainers, owners, or trust/support?
2. Does the first screen make that priority obvious?
3. Do secondary CTAs support the main goal instead of competing with it?
4. Does the section order reinforce the intended priority?
5. Does any copy accidentally flatten all user paths into equal importance?

### 2. CTA Hierarchy

Check whether calls to action are truthful, visible, and ranked correctly.
Ask:
1. Is there one dominant CTA?
2. Are secondary actions clearly secondary?
3. Do labels use customer-facing language instead of internal language?
4. Does any CTA promise a capability the current posture does not expose?
5. Are there dead-end, duplicate, or low-value CTAs that should be removed?

### 3. Copy Quality

Use fewer words with more weight.
Avoid:
1. long explanatory taglines
2. generic startup language
3. cute filler
4. inflated claims
5. repetitive sections
6. internal labels
7. instructional wording on marketing surfaces

Prefer copy that is:
1. concise
2. specific
3. deliberate
4. trustworthy
5. aligned to the current launch posture

### 4. Visual Quality

Check:
1. hierarchy before decoration
2. clean spacing rhythm
3. readable grouping
4. strong contrast and scannability
5. reduced clutter
6. consistent component emphasis
7. whether a section can be removed instead of embellished

### 5. Mobile Presentation

Check:
1. first-screen clarity on narrow screens
2. stacked CTA order
3. heading wrap quality
4. card density
5. form usability
6. nav/footer scan quality
7. whether spacing collapses into noise or excessive length

### 6. Public-Language Guardrail

Public pages should not expose internal implementation terms unless intentionally branded.
Look for internal terms that may appear in code, docs, analytics, workflow labels, or config and translate them into customer-facing language on public surfaces.

## Allowed Changes

Make these changes without separate approval when they are restrained and clearly improve the public surface:
1. public copy changes
2. headings and subheadings
3. CTA labels
4. simple section order changes
5. nav or footer label cleanup
6. metadata title or description cleanup
7. minor spacing or styling improvements
8. card hierarchy improvements
9. mobile layout refinements
10. removing repeated or low-value sections

## Changes That Need Explicit Request

Do not make these changes unless the user explicitly asks:
1. database schema changes
2. auth changes
3. payment changes
4. matching logic changes
5. backend API changes
6. major route restructuring
7. full redesign
8. new feature development
9. broad education-content rewrites
10. changed feature availability, public-policy or launch posture beyond evidence for the current environment

## Required Workflow

1. Read the task prompt; identify the R stage, current business priority and previously accepted visual/browser evidence.
2. Consult the active roadmap, documentation map, invariants and applicable real route/product specifications; do not stop to resurrect missing historical website specs.
3. Discover relevant public routes from the actual current frontend tree and router and, when applicable, the authenticated developer-sandbox website.
4. Inspect the implementation and current feature/rollout state before proposing or making changes.
5. Use browser or Playwright inspection if available when UI changes or visual judgments matter.
6. Review both desktop and mobile presentation.
7. Identify hierarchy, CTA, copy, visual, and public-language issues before editing.
8. If active specifications genuinely conflict, resolve the narrow conflict using the existing authority order; record a proposed decision only where owner authority is actually needed. Do not recreate obsolete SSOT files or block minor authorised edits on a missing historical design document.
9. If the user asked for a review only, stop after findings and do not edit.
10. If the user asked for improvements, make restrained, high-impact edits only within the allowed scope.
11. Preserve the current business hierarchy through copy weight, section order, and CTA emphasis.
12. Run the smallest useful validation for the changed surface, then expand only if needed.

## Final Report Format

Report in this order:
1. business priority used for the pass
2. routes inspected
3. key issues found
4. changes made
5. copy and CTA changes
6. visual and mobile notes
7. validation performed and results
8. remaining issues or risks

If no files were changed, say so explicitly.
If a requested improvement would require prohibited scope, call that out explicitly instead of quietly crossing the boundary.

## Acceptance Criteria

Treat the pass as successful only if:
1. the page clearly supports the current business priority
2. the main CTA hierarchy is obvious and truthful
3. public copy feels customer-facing, concise, and deliberate
4. the page accurately describes verified live capabilities and does not expose a gated or nonfunctional CTA
5. visual quality improves through restraint, not clutter
6. mobile presentation remains readable and intentional
7. no backend, billing, auth, database, or major route scope was changed without explicit approval
8. validation appropriate to the change scope was completed or the gap was reported clearly
9. broad public-site work was grounded in the active roadmap, real routes, approved specs and current environment state, rather than stale supply-first assumptions
