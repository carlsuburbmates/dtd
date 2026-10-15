# DTD acquisition architecture audit and match-readiness correction

## Why this work is being assigned

DTD is building an AI-assisted Owner-to-Trainer Matching Pipeline. Matching may assess an owner’s dog and needs only against trainers whose capability facts are deterministic, current, structured and supported by evidence.

This does **not** make acquisition part of matching. Acquisition remains its own workflow and authority. It maintains trainer identity, lifecycle and capability facts. Matching later consumes a constrained, versioned match-ready projection; it must never infer, repair or invent trainer capabilities during an owner request.

Codex’s matching work has established these owner-approved directions:

- Deterministic eligibility, AI-assisted paid-neutral fit and deterministic presentation are separate layers.
- Commercial tier cannot influence eligibility or raw fit; it may only act inside the locked `0.05` presentation tiebreak.
- A trainer’s structured onboarding, claim or profile-update declaration is a primary source of matching capacity.
- Authorised official sources may prefill capability fields, but trainers must be able to confirm, correct or complete them.
- Free-text marketing/profile copy cannot independently create a matchable specialty, service area, method claim or service format.
- AI confidence is not authority to publish, verify, mark contact-ready, or make a trainer matchable.
- Matching policy choices for weak evidence, low supply, ambiguity and degraded AI remain open for Decision Contract v2. Do not decide them here.

The purpose of this work is to make acquisition/onboarding capable of supplying reliable facts to the future matching pipeline, without implementing matching itself.

## Read first

Read, in this order:

1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/README.md`
4. `docs/DTD_CURRENT_STATE.md`
5. `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`
6. `docs/specs/ACQUISITION_AND_INGESTION.md`
7. `docs/specs/MATCHING_AND_RANKING.md`
8. `docs/DTD_TARGETED_MATCHING_PIPELINE_STATE.md`
9. `docs/DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md`
10. `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md`, especially CDR-018 through CDR-024

Do not read `archive/` unless explicitly instructed.

## Current evidence to verify, not blindly trust

The repository has trainer fields including `specialties`, `service_formats`, `serviced_suburbs`, `catchment_type`, and `training_philosophy`. Current evidence indicates these may lack a field-level source/declaration basis, confirmation time, freshness state, deterministic validation outcome, and matchability projection. The current matching path may also receive broad profile data after coarse filtering instead of a bounded capability projection.

`DF-014` records a possible re-verification/publication-authority defect. Re-check the current implementation and tests before treating the finding as technically current. If code and current-state documentation disagree, establish the actual truth and correct documentation or implementation accordingly.

`DF-026` records the broader match-readiness gap. Treat it as the core architecture finding.

## Objective

Audit and, where safe and evidence-backed, correct the acquisition/onboarding architecture so it can produce a deterministic match-ready capability projection.

Required capability categories:

- service areas/catchment;
- supported service formats;
- specialties and concern categories;
- relevant dog life-stage suitability;
- training philosophy and method boundaries;
- in-home, facility or other delivery constraints; and
- material availability constraints, if explicitly modelled.

For every matchable field, establish the ability to retain:

- normalised value;
- basis: `official_source` or `trainer_declaration`;
- evidence/source reference;
- retrieval or trainer-confirmation time;
- freshness state;
- deterministic validation result; and
- whether it is permitted in the match-ready projection.

A published profile is not automatically matchable for every owner request.

## Scope

1. Audit the full lifecycle:

   ```text
   authorised acquisition
   → extraction/normalisation
   → trainer submission, claim or profile update
   → provenance and validation
   → publication/hold/suppression/refresh
   → match-ready capability projection
   → operator evidence in /ops
   ```

2. Trace actual UI, API, model/schema, acquisition services, persistence, refresh/reverification, correction/removal, suppression, tests and `/ops` surfaces.

3. Identify which current values are structured and match-ready; display-only; marketing/free text; unsupported/stale; AI-proposed but unconfirmed; missing provenance/freshness; or incorrectly able to affect publication, contact readiness or future matching.

4. Implement the smallest safe architecture corrections where the intended rule is already approved. This may include structured capability declaration/confirmation, deterministic vocabularies and validation, field-level provenance/freshness, correction/suppression invalidation, an internal match-ready projection, `/ops` visibility, and regression tests.

5. Preserve compatibility where practical. Do not silently treat legacy free text or unknown historic data as verified matching capability.

## Explicit non-goals

Do not:

- implement or redesign the owner questionnaire, match API, ranking, scoring, Gemini fit prompt, fallback outcome or commercial ordering;
- choose the weak-evidence, low-supply, ambiguous-input or degraded-AI owner response;
- deploy, push, open a PR, alter production, change providers, activate billing, create credentials, mutate live data or run a production migration;
- enable Google Places/Maps, Search Grounding, generic scraping or any unapproved acquisition source;
- convert Google/Maps content into persistent trainer facts;
- make AI confidence authority for publication, verification, contact readiness or matching capacity;
- alter matching-policy authority documents except for a factual acquisition-interface correction; or
- make unsupported public verification, credential, insurance or professional-quality claims. Report these separately; public matching/profile remediation stays with the matching roadmap.

## Decision boundaries

Proceed autonomously with evidence-backed local changes. Stop and report only if resolution requires a new external data source/source-rights change, production/provider mutation, data retention/privacy policy, irreversible historic-record migration, new commercial/ranking/matching rule, or a capability-taxonomy choice that cannot be resolved from current authority.

When uncertain, preserve or fail closed for matching capacity rather than inventing or promoting a capability.

## Required acceptance evidence

Return an evidence handoff containing:

1. Commit SHA(s) and changed files.
2. Current-state audit: verified, corrected, open, or contradicted earlier documentation.
3. Field-by-field matrix: current source, schema location, declaration/confirmation path, validation, provenance/freshness, correction/suppression invalidation, projection eligibility and `/ops` evidence.
4. Full actor-path coverage: acquisition automation; trainer submission/claim/update; trainer correction; stale/unsupported capability; suppression/removal; oversight operator.
5. Test commands/results covering:
   - AI-proposed capability cannot independently become matchable;
   - trainer-confirmed structured capability becomes matchable only after validation;
   - correction, failed refresh or suppression invalidates the affected capability;
   - paid status and marketing prose cannot enter the projection;
   - AI confidence cannot grant public/contact/matchable state;
   - stale/unsupported fields are excluded or explicitly held; and
   - `/ops` exposes actionable state without personal owner data.
6. Findings that must return to Codex/the owner, with evidence and the smallest decision required.
7. Confirmation that no deployment, provider, billing, production-data or remote mutation occurred.

## Completion standard

This work is complete only when acquisition can evidence the origin, confirmation, freshness, validation and invalidation of every trainer capability it supplies to matching, and matching can later consume that bounded projection without relying on marketing prose, AI confidence or unsupported facts.
