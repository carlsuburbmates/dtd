# Matching and Ranking

**Implementation contract:** [Owner-to-Trainer Matching Decision Contract v2](OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md). Where an older statement conflicts with its field, state, privacy or fit rules, Decision Contract v2 governs the matching workstream.

## Objective

Return useful trainers based on owner needs and evidenced service suitability while keeping commercial influence bounded and explicit.

## AI-assisted matching operating model

DTD matching is AI-assisted. AI is a substantive fit-reasoning component, not a decorative copy layer: it may interpret an owner's ordinary-language description, identify structured behavioural, service and logistical signals, and select and explain candidates from the eligible pool. Decision Contract v2 must select and test the response to ambiguity, weak evidence, low supply and AI degradation; clarification and no-suitable-match are options, not preselected outcomes.

Deterministic rules remain authoritative for consent, data handling, candidate eligibility, suppression, publication, geography, safety policy, commercial fairness, delivery, persistence and operator evidence. AI cannot override those rules, access excluded candidates, use paid status as a fit signal, manufacture trainer facts or guarantee an outcome. The approved decision contract, rather than a blanket planning rule, determines the owner-visible response when matching evidence is insufficient.

Normal suitable matches should run without owner intervention. Human work is reserved for defined exceptions, provider degradation, trust/data disputes and systemic quality signals visible in `/ops`.

## Owner-to-trainer matching system workstream

**Status:** active verification and implementation workstream. This section defines the contract to prove; it does not claim that the current implementation meets it.

### Three separate decision layers

| Layer | Question | Authority | Commercial status |
| --- | --- | --- | --- |
| Eligibility | Can this trainer legitimately and safely be considered at all? | Deterministic policy and evidence gates | Never considered |
| Fit | How appropriate is this trainer for this owner and dog? | AI-assisted reasoning over eligible facts, bounded by deterministic policy | Never considered |
| Presentation | How are suitable trainers ordered and displayed? | Deterministic presentation policy | Only the documented 0.05 comparable-fit tiebreak |

No implementation may collapse these layers. In particular, a reviewed, verified, claimed or published state is evidence only for the eligibility rules expressly defined for it; it is not a generic fit signal or a substitute for demonstrated capability.

### Acquisition-to-matching dependency

Matching does not operate on the directory as undifferentiated profile text. The acquisition workflow is responsible for distinguishing identity/lifecycle facts, official-source or trainer-confirmed capability facts and non-matchable commercial or marketing data. Before an owner request reaches eligibility, matching receives a deterministic match-ready capability projection: only current, permitted facts with field-level provenance can become eligibility or fit inputs. A trainer's structured onboarding/claim declaration is a first-class matching-capacity input; it determines the owner needs for which that trainer can be considered. The acquisition quality gate remains responsible for source rights, deterministic validation, correction, suppression and refresh; the matching system remains responsible for applying those facts to a particular owner/dog without rewriting them.

A trainer can therefore be published in the directory yet be partially or wholly unavailable for a particular matching path if the capability evidence needed for that path is absent, stale, suppressed or unsupported. Conversely, paid visibility never makes a capability fact matchable.

### Required verification scope

1. **Owner input and triage.** Define the exact minimum and optional data for an informed match: dog life stage/age, behavioural concern or concerns, suburb, desired service format (including in-home need), method preference where relevant, and any other necessary contextual details. Define consent, validation, privacy/retention, missing-data and urgent-safety states, plus the Decision Contract-selected response to ambiguity or weak evidence.
2. **Trainer capability facts.** Verify which structured, evidence-backed profile facts can support matching: service areas, formats, specialties, methods/philosophy, availability-relevant constraints and publication/review/claim state. Do not infer capability from paid tier, unverified prose or AI-generated facts.
3. **Fit decision contract.** Specify how owner signals and trainer facts contribute to fit, the AI's allowed outputs, confidence thresholds, unsuitable-exclusion, explainable reason states and the selected response options for ambiguity, weak evidence, low supply and absent required capability evidence. The AI receives only the eligible candidate set and relevant permitted facts.
4. **Fallback and parity.** Define Gemini-unavailable, timeout, malformed-output and rate-limit behaviour. The deterministic fallback must produce the same decision states and compatible evidence fields as the AI path, including the contract-selected response for weak or missing evidence.
5. **Geography and top-three selection.** Define exact local-service-area matching, disclosed Greater Melbourne expansion when local supply is weak, the selected response when the pool is depleted, all fit inputs, top-three selection and deterministic stable ordering.
6. **Fairness and presentation.** Prove paid-neutral raw fit; apply commercial ordering only after fit, only within the exact 0.05 band, and never above a materially stronger fit. Cover anti-gaming, explanation truthfulness and any outcome-score influence on future fit.
7. **Owner-to-trainer journey.** Verify mobile and desktop flow from questionnaire through results, trainer profile and protected enquiry; keep behavioural descriptions out of URLs and disclose expanded geography. Verify consented delivery, trainer-facing relevance, outcome follow-up, retry/failure and `/ops` evidence.
8. **Scenario evaluation.** Build realistic dog-owner test cases covering puppy/life-stage needs, reactivity and other behavioural concerns, in-home requirements, method preference, thin local supply, incomplete input, unsuitable candidates, no suitable trainer, AI degradation and attempted commercial gaming. Evaluate AI and fallback recommendations for material consistency against the same fixtures.

### Strategic execution order

1. **Decision contract first.** Resolve the owner inputs, trainer facts, eligibility gates, AI decision states, weak-evidence response options, fit signals, presentation policy, data handling and expected scenario outcomes as one versioned contract. This is the first refinement task.
2. **Evaluation second.** Turn the contract into reusable realistic scenarios with expected eligibility, fit and presentation outcomes. Use them to prove Gemini and deterministic fallback behaviour before a public workflow rewrite.
3. **Architecture third.** Bind the proved contract to the smallest maintainable implementation. The current Google-native hosting and AI path is a starting point, not a requirement to migrate every operational dependency. Any Google-only data/platform migration requires a separate evidence-backed architecture decision.
4. **Vertical delivery fourth.** Implement and verify one complete questionnaire → decision → results → trainer → enquiry → follow-up → `/ops` slice in the sandbox. Do not add RAG, vector search, agent orchestration or new data platforms unless scenario evidence shows that the defined contract requires them.

### Urgent-support pathway

Urgent support is a pre-match safety pathway, not a trainer-specialty filter and not a medical or legal advice service. It must be available from the owner questionnaire, matching results and a dedicated public support page.

1. **Human immediate-danger route.** Where the owner indicates a person is in immediate danger, show the approved Victorian emergency-services card. DTD does not diagnose, assess legal liability or delay that route with ordinary matching.
2. **Pet urgent-care route.** Where the owner indicates a possible animal health emergency or needs urgent veterinary support, show a region-filtered urgent-support directory and provider-authored contact instructions. This is a referral-information surface, not a clinical assessment or treatment recommendation. A separate, optional Google Maps/Places module may provide live discovery/navigation in the owner session under CDR-020; its Google-sourced content is visually identified and is never a DTD provider claim, ranking signal or AI input.
3. **Safety-sensitive behavioural route.** Where a behavioural concern is serious but does not clearly require emergency services, offer the urgent-support page alongside normal matching only when the ordinary eligibility and fit rules are met.
4. **Unclear route.** When AI confidence is insufficient to distinguish urgent-route states, it must show the conservative approved support card. Decision Contract v2 determines any clarification or ordinary-matching response; AI must not manufacture a diagnosis.

AI may classify only among the approved pathway states and render approved, versioned support copy. It may not provide freeform medical, veterinary, legal or behavioural-treatment advice; a disclaimer does not make unsupported generated advice safe. It cannot create, alter or claim the availability of providers.

The urgent-support directory is a separate provider record type, never a `trainers` substitute. A public provider entry requires an owner-authorised official source URL, stated location/service area, contact method, stated hours or availability, category, source-retrieval time, a visible last-checked date and a correction/removal path. Public labels must say what the provider states, not that DTD has clinically vetted it. Paid status never affects inclusion or order. Until the coverage register evidences a region, the page must say that DTD has no current verified listing there rather than imply Melbourne-wide availability. A live Google Maps/Places module supplements this directory only: it cannot populate it, substantiate a DTD claim, enter AI reasoning or alter DTD ordering.

### Urgent-support execution plan

1. Define the approved pathway states, owner-facing safety cards, AI confidence/clarification rules and `/ops` events using current Victorian emergency-service wording and veterinary-provider instructions.
2. Build the separate official-source provider register, starting with a coverage matrix for inner/north, east, south-east, west and outer-growth areas. Treat provider hours and instructions as volatile facts requiring refresh and stale-record suppression.
3. Define provider publication, correction, removal, recheck cadence and source-rights rules before any public directory page or automated refresh.
4. Before enabling any Google Maps/Places module, confirm the exact product's terms, attribution/display requirements, data fields, caching/retention rules, privacy disclosure, cost controls and degraded state. Use only permitted session data (and a Place ID only if the applicable terms permit it); do not reuse the trainer-acquisition adapter or send Maps content to Gemini.
5. Add AI and deterministic test fixtures for human-danger, possible pet urgent-care, safety-sensitive behaviour, unclear input, unavailable local support and ordinary trainer matching. The same state must be reachable when Gemini is unavailable.
6. Implement the dedicated public page and the questionnaire/results entry points as one sandbox-verified vertical slice, including privacy minimisation, mobile use, no-match, provider-change and `/ops` degradation states.

### Workstream completion rule

This workstream is complete only when the full decision contract is documented and implemented; every scenario has repeatable expected eligibility, fit and presentation outcomes; AI and fallback parity is evidenced; the owner journey is verified on mobile and desktop; persisted consent and match evidence are privacy-bounded; follow-up/outcome loops are safe and observable; and sandbox evidence proves UI → API → persisted state → notification/fallback → `/ops` for success, no-match and degraded branches.

## Diagnostic fit

Current deterministic fit is:

```text
fit = (match_score × 0.70) + (outcome_score × 0.30) - policy_penalty
```

Paid tier, subscription state and billing fields do not enter this score. The AI matching prompt must likewise omit those fields.

## Comparable-fit tiebreak

1. Calculate all eligible trainers' fit scores.
2. Find the highest fit score.
3. A trainer is in the comparable-fit band only when the difference from the top is at most `0.05`.
4. Within that band, tier order is Melbourne-Wide (4), Suburb Sponsor (3), Pro (2), Claimed (1), base/unclaimed (0).
5. Outside the band, fit order is preserved; payment cannot lift a materially weaker match above a stronger one.
6. Deterministic stable fields resolve any remaining equality.

This replaces the former 15% “Pro Verification” fit weight.

## Directory browse ranking

General directory browsing is a visibility surface rather than a diagnostic recommendation. It may use suburb sponsorship, tier, verification, reviews and outcome evidence in the documented deterministic order. UI must not represent paid visibility as independent clinical suitability.

## Eligibility and safety

- Suppressed, delisted, unpublished, policy-ineligible or geographically ineligible trainers do not enter ranking.
- Missing evidence defaults conservatively; AI output does not override deterministic gates.
- Fallback radius/catchment expansion must remain visible to the user and must not invent local presence.

## Acceptance tests

- Changing paid tier alone never changes fit score.
- Tier can reorder two trainers inside the 0.05 band.
- Tier cannot promote a trainer outside the band above the best fit.
- Policy penalties and publication/suppression gates apply before commercial ordering.
- AI and deterministic fallback return compatible, explainable evidence fields.
