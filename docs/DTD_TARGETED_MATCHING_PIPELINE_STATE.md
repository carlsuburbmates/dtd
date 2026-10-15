# DTD Targeted Matching Pipeline State

**Purpose:** the concrete target state for DTD's owner-to-trainer matching pipeline.
**Status:** owner-directed target; implementation, scenario evaluation and sandbox acceptance remain open.
**Authority:** consolidates CDR-018 through CDR-024. It does not claim that the current public matching path already meets this state.

## Target outcome

DTD gives a Greater Melbourne dog owner a safe, understandable and useful path to an appropriate trainer without manual operator matching. The result is a reasoned introduction, not a diagnosis, guarantee, clinical assessment or paid lead placement.

The system is AI-assisted where ordinary language and contextual fit matter, and deterministic wherever legitimacy, safety, privacy, fairness, commercial boundaries, delivery and auditability matter. Decision Contract v2 will select and test the owner-visible response when evidence is weak, input is ambiguous, supply is thin or AI is degraded. A solo owner operates exceptions and systemic quality signals through `/ops`, rather than manually deciding routine matches.

## What this target is not

- It is not a general trainer search ranking, a medical/veterinary advice service, or a guarantee that a trainer will accept an owner or achieve an outcome.
- It does not allow paid tier, sponsorship, marketing prose, unverified reviews or AI confidence to influence eligibility or raw fit.
- It does not turn Google Maps/Places, Search Grounding or generic search results into DTD trainer/provider inventory, claims or AI evidence.
- It does not authorise a production deployment, provider activation, new billing, credential or data-retention decision by itself.

## Canonical end-to-end workflow

```text
Trainer official-source capture and/or structured trainer declaration
→ field-level provenance, validation, refresh and suppression
→ deterministic match-ready capability projection

Owner questionnaire
→ deterministic validation and urgent-support triage
→ deterministic eligibility pool
→ AI-assisted fit and a Decision Contract-defined response
→ deterministic presentation and explanation
→ trainer profile and protected enquiry
→ consented outcome follow-up
→ privacy-bounded records and /ops evidence
```

Every arrow is a product contract. A page rendering, model response or database row alone does not satisfy the target.

## 1. Trainer capability supply: acquisition and onboarding

Acquisition and matching remain separate workflows connected by one match-ready capability projection.

1. Authorised official sources may prefill trainer facts.
2. Trainer onboarding, claim and profile-update flows collect a structured capability declaration. It is a primary source of matching capacity.
3. The trainer confirms or corrects service areas, service formats, specialties/concerns, life-stage suitability where relevant, training philosophy/method boundaries, in-home or facility constraints and material availability constraints.
4. Each matchable field has a normalised value, basis (`official_source` or `trainer_declaration`), source/evidence reference, last confirmation/retrieval time, freshness state and deterministic validation outcome.
5. A change, correction, expiry, failed refresh, suppression or delisting updates the projection before later owner matches. A published directory profile may therefore be unavailable for a particular match path.
6. Free text may explain a structured declaration or propose a value for trainer confirmation. It cannot independently create an unbounded specialty, service area or method claim.

The acquisition system owns source rights, provenance, correction, suppression and freshness. The matching system may only consume the resulting permitted fields; it cannot infer or repair trainer capacity during an owner request.

## 2. Owner questionnaire and privacy boundary

The mobile-first questionnaire gathers only what is necessary for an informed match:

- Greater Melbourne suburb or postcode;
- dog age in months, from which life stage is derived;
- one or more primary concerns, including `other` and `unsure`;
- desired service format and any in-home/facility constraint, where `any` means no preference;
- method preference when relevant;
- an optional, bounded behavioural description; and
- distinct consents for match processing, referral/contact release, terms and optional follow-up.

The form validates required data before an AI request. It gives clear, accessible error, loading and Decision Contract-defined response states on mobile and desktop. Behavioural descriptions are minimised, sanitised, never placed in URLs and retained only under the versioned matching-consent and retention contract.

## 3. Urgent-support triage

Urgent support is resolved before ordinary trainer matching and is available from the questionnaire, results and a dedicated public support page.

| Route | Target response |
| --- | --- |
| Immediate danger to a person | Show approved emergency-services information; do not delay with trainer matching. |
| Possible urgent animal-health need | Show current, provider-authored urgent-care information and the verified regional directory. |
| Serious but not clearly emergency behavioural concern | Offer urgent-support information alongside ordinary matching only if normal eligibility and fit rules permit it. |
| Unclear | Show conservative approved support information and request clarification. |

AI may classify only these approved route states and render versioned approved copy. It must not generate medical, veterinary, legal or behavioural-treatment advice, create providers or claim current availability.

The urgent-provider directory is a separate record type with official-source provenance, stated location/service area, contact details, stated hours/availability, category, last-checked date and correction/removal path. Until regional coverage is evidenced, DTD says it has no current verified listing rather than implying Melbourne-wide coverage.

A future Google Maps/Places module is optional and user-initiated. It is a clearly attributed, session-only discovery/navigation aid; it cannot populate the directory, substantiate DTD claims, enter AI reasoning or alter DTD ordering.

## 4. Matching decision model

### Eligibility — deterministic

Eligibility answers whether a trainer can be considered at all. It applies publication, suppression, policy, source-freshness, contact-readiness, geography, declared service-format and required-capability gates before any fit assessment. Missing, stale or unsupported capability data fails closed for the affected match path. Commercial state never enters this layer.

### Fit — AI-assisted and paid-neutral

Gemini receives only the sanitised owner signals, approved decision-policy version and a bounded eligible candidate pool containing permitted projected fields. It may interpret ordinary language, compare needs with declared capability boundaries and return factual reason codes/explanations only in the strict decision schema selected by Decision Contract v2. That contract selects the response for ambiguity, weak evidence, low supply and no suitable capability evidence.

Gemini cannot access excluded candidates, paid state, raw provider/Google content, unsupported profile text or private owner data beyond the minimised request. It cannot add capabilities, override eligibility or guarantee suitability. Its explanation must cite only actual matching facts.

The deterministic fallback uses the same input projection, decision states, result schema and reason-code vocabulary. Gemini timeout, rate limit, malformed output and unavailability are explicit, observable degraded states whose owner-visible response is selected and tested in Decision Contract v2; the roadmap does not preselect that response.

### Presentation — deterministic and commercially bounded

Only eligible, suitable candidates proceed to presentation. Raw diagnostic fit remains paid-neutral:

```text
fit = (match_score × 0.70) + (outcome_score × 0.30) - policy_penalty
```

Outcome evidence may influence fit only after its collection, attribution, sample sufficiency, freshness, anti-gaming and appeal rules are specified and validated. Before then, it cannot create a hidden advantage.

Select up to three candidates when the Decision Contract selects a recommendation response. The same contract defines the response when fewer than three eligible/suitable candidates exist or none has the required capability evidence. Start with the declared local service area. Expand only under the documented thin-supply condition, disclose the expanded scope and never represent broader results as local.

Within `0.05` of the highest final fit, deterministic presentation may use the locked commercial order: Melbourne-Wide, Suburb Sponsor, Pro, Claimed, then Unclaimed. Outside that band, fit order is absolute. A stable non-commercial field resolves equality.

## 5. Owner results, enquiry and follow-up

The owner sees the Decision Contract-defined state first, alongside any required urgent-support route and a clearly disclosed degraded state. Where the selected response includes recommendations, each states why it fits in factual plain language, its actual service area/format and any expanded-search disclosure.

The profile handoff preserves match context server-side rather than in a URL. Protected enquiry releases contact information only with its own consent. Trainer-facing communication contains only the minimum relevant owner context. Outcome follow-up is optional, retry-safe, bounded and observable; failure, retry, suppression and terminal states are distinct.

## 6. Fairness, privacy and anti-gaming

- The same eligibility and fit policy applies regardless of commercial tier.
- Trainer declarations affect matching capacity only through structured, validated fields; marketing language cannot game matchability.
- Changes to declared capacity are versioned, attributable and auditable. Material corrections or suppression invalidate affected matchability immediately or fail closed until resolved.
- Owner descriptions, urgent signals and consent evidence are privacy-bounded. They are not URL data, marketing audiences, trainer profile data or model-training material.
- Provider/trainer data is used only within its approved source rights and correction/removal obligations.

## 7. Records and `/ops`

Every match records the decision-policy version, consent evidence, sanitised request/retention metadata, applied search scope, triage outcome, eligible-candidate count, AI or fallback path, reason codes, presented result IDs and degraded state where applicable. It does not need to retain more free text than the versioned privacy contract permits.

`/ops` provides owner-readable evidence for:

- match volume and decision-state distribution;
- AI/fallback health, latency and invalid-output/degraded events;
- Decision Contract-defined response-state and thin-supply patterns;
- urgent-support directory freshness, coverage gaps and provider corrections;
- trainer declaration changes, stale capability fields, suppression and matching-capacity invalidation; and
- outcome/follow-up delivery, retry and terminal-failure states.

`/ops` supports bounded review and recovery, not routine manual matching or untracked overrides.

## 8. Acceptance state

This target is achieved only when all of the following are evidenced in the developer sandbox before any production promotion:

1. Trainer onboarding/claim, authorised acquisition, correction, refresh and suppression produce and invalidate the match-ready capability projection correctly.
2. The owner journey works from entry point through questionnaire, every triage/decision state, result/profile handoff, protected enquiry and follow-up on mobile and desktop.
3. Gemini and deterministic fallback produce materially consistent decisions and compatible evidence for the same realistic fixtures.
4. Fixtures cover puppy and adult needs, multiple concerns, in-home requirements, method preference, thin local supply, incomplete input, unsafe/urgent signals, unsuitable or absent required capability evidence, stale trainer facts, declared-capability changes, AI failure and attempted commercial gaming, with the chosen response specified for each.
5. Privacy, consent, retention, explanation truthfulness, 0.05 commercial boundary and expanded-geography disclosure are verified end to end.
6. `/ops` exposes success, the selected Decision Contract response states, suppression, failed refresh, provider degradation, urgent-directory and follow-up failure/retry states without exposing private owner data.

## Delivery sequence

1. Finalise the versioned Owner-to-Trainer Matching Decision Contract v2, including field taxonomy, consent/retention, evidence grades, policy penalties, outcome rules and exact API/screen states.
2. Build the trainer declaration and match-ready capability projection across acquisition, onboarding/claim and correction/suppression flows.
3. Create scenario fixtures and a Gemini-versus-fallback evaluation harness; resolve policy drift before public workflow work.
4. Deliver one complete ordinary-matching vertical slice in sandbox.
5. Deliver the urgent-support directory, triage and optional Maps/Places surface as a separate sandbox-verified slice.
6. Promote only after the target acceptance state and separate production gates are met.

## Completion-roadmap readiness

This target is ready to become a gated completion roadmap. The product boundary, decision layers, acquisition/onboarding dependency, data boundaries, acceptance evidence and delivery order are now defined well enough to plan accountable work packages without inventing owner choices.

The roadmap must begin with Decision Contract v2 and scenario fixtures rather than a frontend, model or cloud build. `DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md` is the execution checklist and independent-verification basis for this target. The known implementation gaps are recorded in `DTD_CURRENT_STATE.md` as DF-017 through DF-026, with the matching-specific architecture gaps concentrated in DF-018, DF-019 and DF-021 through DF-026. Those findings establish the work; they do not make the pipeline complete or safe to release. Production, provider activation, retention-policy, billing and other separate approval gates remain unchanged.
