---
name: dtd-premium-look-audit
description: Audit and refine DTD public-facing website pages, route groups, navigation, public copy, CTA hierarchy, metadata, and light visual/mobile polish while preserving the current business priority and locked launch posture. Use when Codex is asked to review or improve the homepage, landing pages, trainer-facing pages, owner waitlist surfaces, navigation, footer, public copy, visual hierarchy, mobile presentation, or premium brand quality across the public website without expanding into backend, billing, auth, database, or major product redesign work.
---

# DTD Premium look audit

Use this skill to make restrained, high-impact improvements to DTD's public website.
Start from business hierarchy and launch posture, not from decoration or generic conversion patterns.

## Source Of Truth

Read these in order before editing public pages:
1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
4. `docs/governance/CURRENT_TRUTH_INDEX.md`
5. `docs/standards/SSOT.md`
6. `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`
7. `docs/design/WEBSITE_WIREFRAME_SPEC.md`
8. `docs/INITIAL_LAUNCH_GOALS_SUPPLY_FIRST.md`
9. `frontend/src/App.js`

Use lower-authority design/process docs only as support material after the canonical pack is clear.

## When To Use

Use this skill when the task is about:
1. homepage audit or refinement
2. landing page refinement
3. trainer-facing page improvement
4. owner waitlist page improvement
5. navigation or footer cleanup
6. CTA hierarchy cleanup
7. public copy tightening
8. mobile UI polish
9. visual hierarchy review
10. removing cheap, scattered, repetitive, or internal-sounding public wording
11. locking or updating the public-page operating rules inside the canonical website spec before a broad public-site overhaul

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

If the task crosses into these areas, stop and ask for explicit approval or route to a more appropriate skill or workflow.

## Locked Business Context

Assume these truths unless the current task explicitly states a different approved posture:
1. DTD is a guided dog-trainer match-and-intro platform, not a generic directory.
2. The current launch posture is `supply_first`.
3. `PUBLIC_MATCHING_ENABLED=false`.
4. Trainer acquisition is the primary public priority in the current locked posture.
5. Owner demand capture remains passive through education and waitlist flows.
6. Public pages must not imply broad live matching is currently open.
7. `/ops` is a protected oversight surface, not a public marketing route.

Do not hardcode one permanent CTA order across all future tasks.
Identify the current business priority from the user's prompt first, then preserve that hierarchy consistently across copy, CTA weight, section order, and visual emphasis.

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
10. launch-posture changes that would imply live matching is open

## Required Workflow

1. Read the task prompt and identify the current business priority.
2. Read `docs/COMPLETE_WEBSITE_PAGE_SPEC.md` and treat its global public-page operating rules as the mandatory contract for page purpose, CTA hierarchy, public-language discipline, visual weight, and explanation limits.
3. Identify the relevant public routes from the prompt, `docs/COMPLETE_WEBSITE_PAGE_SPEC.md`, and `frontend/src/App.js`.
4. Inspect the current implementation files for those routes before suggesting or making changes.
5. Use browser or Playwright inspection if available when UI changes or visual judgments matter.
6. Review both desktop and mobile presentation.
7. Identify hierarchy, CTA, copy, visual, and public-language issues before editing.
8. If the task reveals the operating rules are missing, contradictory, or too weak for the requested overhaul, stop and update the canonical website spec first before editing implementation.
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
4. the page does not imply live capabilities that are currently gated
5. visual quality improves through restraint, not clutter
6. mobile presentation remains readable and intentional
7. no backend, billing, auth, database, or major route scope was changed without explicit approval
8. validation appropriate to the change scope was completed or the gap was reported clearly
9. broad public-site work did not proceed without first checking the canonical public-page operating rules in the website spec
