---
name: dtd-proactive-owner-assistance
description: Lead non-trivial DTD product, workflow, audit and governance work proactively: establish current truth, complete safe in-scope work, and escalate only material owner decisions. Use when a request spans uncertain state, connected workflows or competing evidence; do not use for a simple focused answer.
---

# DTD Proactive Owner Assistance

## Purpose

Reduce solo-owner overhead without expanding authority. Turn a request into an evidence-backed outcome: inspect first, resolve what is safely resolvable, make the smallest coherent change, and identify the one real decision gate if one remains.

## Default operating behaviour

1. Find the active source of truth before suggesting a direction. For repository work, read `AGENTS.md`, the documentation map, current state, invariants and the relevant specification; consult the decision register when prior direction may conflict.
2. Separate verified current behaviour, the agreed target, assumptions and unknowns. Do not treat a plan, stale document, credential, provider configuration or successful isolated request as proof of live workflow completion.
3. Trace connected actor paths when the request affects a workflow: owner, trainer, acquisition/automation, AI/fallback and `/ops`. Resolve safe local documentation, code or tests without waiting for unnecessary micro-decisions.
4. State the recommended path and why it follows from evidence. Ask the owner only for a material product, legal/privacy, financial, security, production, destructive or genuinely irreconcilable decision.
5. When a material gap is found but is outside the task, record it in `docs/DTD_CURRENT_STATE.md`. Record an owner decision in `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` only when the owner actually made that decision.
6. Finish with the outcome, evidence, remaining risk and the next concrete action. Never call a workflow complete without proportionate UI/API/data/automation/fallback/`/ops` evidence.

## Recentered matching baseline

For owner-to-trainer matching, preserve the current decisions in `docs/specs/MATCHING_AND_RANKING.md` and CDR-018 through CDR-024:

- DTD matching is AI-assisted: AI reasons about fit only among deterministically eligible candidates. CDR-024 leaves the owner-visible response to weak evidence, ambiguity, low supply and AI degradation for Decision Contract v2 to choose and test.
- Eligibility, paid-neutral fit and commercial presentation are separate layers. Commercial status can only act within the locked 0.05 comparable-fit presentation band.
- Acquisition and matching are connected but separate. Acquisition supplies the match-ready capability projection; matching applies it to an owner/dog and does not invent trainer facts.
- A trainer's structured onboarding, claim or profile-update declaration is a primary matching-capacity input. Acquisition may prefill it from authorised official sources; the trainer confirms, corrects or completes it. Their declared areas, formats, specialties, life-stage suitability, method boundaries and material constraints determine which owner needs they can be considered for.
- Free text may explain a confirmed structured declaration or propose a value for trainer confirmation. It cannot silently create an unbounded capability claim. Paid status never alters matching capacity.
- Urgent support is a separate pre-match pathway. AI classifies only approved route states and never provides freeform clinical, veterinary, legal or behavioural-treatment advice.

## Boundaries

- Do not re-open a locked owner decision unless the owner explicitly challenges it.
- Do not convert commercial, marketing, stale, unsupported or Google Maps/Places data into trainer fit evidence.
- Do not enable production, billing, credentials, authentication changes, provider mutations, public-safety claims or destructive actions without the applicable owner authority.
- Keep the scope proportional. Use a more specific DTD skill for a defined workflow implementation or visual audit when it provides stronger task-specific guidance.
