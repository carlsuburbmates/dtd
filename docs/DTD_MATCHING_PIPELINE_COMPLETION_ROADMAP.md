# Owner-to-Trainer Matching Pipeline Completion Roadmap

**Purpose:** the execution checklist and post-completion verification basis for the owner-to-trainer matching pipeline.
**Status:** active roadmap; all work packages are `OPEN` unless independently evidenced otherwise.
**Scope:** matching only. This does not replace DTD-wide release work, commercial activation, credential/provider recovery, or production approval gates.
**Authority:** executes, but does not amend, `DTD_TARGETED_MATCHING_PIPELINE_STATE.md`, `specs/MATCHING_AND_RANKING.md`, `specs/ACQUISITION_AND_INGESTION.md`, `specs/OPS_AND_OBSERVABILITY.md`, the invariants, and CDR-018 through CDR-024.

## How to use this roadmap

Each work package is a complete workflow, not a coding task. Its status can be:

| Status | Meaning |
| --- | --- |
| `OPEN` | Not yet implemented or not yet evidenced. |
| `PARTIAL` | Some work exists, but a required branch, record, automation, safety control or evidence item is missing. |
| `NOT_VERIFIED` | A claimed result exists but has not passed the required independent audit or sandbox evidence gate. |
| `REGRESSED` | New evidence shows a previously accepted requirement no longer holds. |
| `DONE` | The package's exact completion rule and evidence bundle have passed independent Codex audit. |
| `SUPERSEDED` | An explicit owner decision replaces the package or requirement; cite the decision record. |

Do not mark a package `DONE` because a screen renders, an endpoint returns `200`, or a model responds. A package is `DONE` only after its owner, trainer, automation, AI/fallback, persistence, degraded-state and `/ops` obligations have been evidenced where applicable.

For every status change, append a short evidence entry beneath the package containing: date, commit SHA, changed files, tests and results, sandbox evidence, affected current-state findings, residual risk, and independent-audit classification. Keep credentials, owner descriptions and provider-private information out of this public repository.

## Completion register

| ID | Work package | Current status | Completion dependency | Related findings |
| --- | --- | --- | --- | --- |
| M0 | Decision contract and fixture baseline | `OPEN` | None | DF-018, DF-019, DF-021, DF-022, DF-023 |
| M1 | Trainer declaration and capability projection | `OPEN` | M0 | DF-014, DF-026 |
| M2 | Owner questionnaire, privacy and accessible states | `OPEN` | M0 | DF-015, DF-018, DF-021, DF-022 |
| M3 | Eligibility, geography and presentation | `OPEN` | M0, M1 | DF-014, DF-019, DF-023, DF-026 |
| M4 | AI fit and deterministic fallback | `OPEN` | M0, M1, M3 | DF-023 |
| M5 | Results, enquiry and follow-up | `OPEN` | M0, M2, M3, M4 | DF-015, DF-016, DF-017, DF-020 |
| M6 | Urgent-support directory and triage | `OPEN` | M0, M2 | DF-024 |
| M7 | Optional Maps/Places discovery | `OPEN` (conditional) | M6 | DF-025 |
| M8 | `/ops`, records and anti-gaming | `OPEN` | M1–M6 | DF-017, DF-022–DF-026 |
| M9 | Integrated sandbox and independent audit | `OPEN` | M0–M6, M8; M7 if enabled | DF-014–DF-026 where matching-relevant |
| M10 | Separate production promotion | `OPEN` | M9 and owner authority | Separate release gates |

## Locked boundaries

- AI assists fit only among deterministically eligible trainers. Decision Contract v2 selects the response to ambiguity, weak evidence, low supply and AI degradation; AI may not invent capabilities, override safety gates or issue treatment, legal or veterinary advice.
- Eligibility and raw fit are paid-neutral. Commercial ordering is permitted only in deterministic presentation, within `0.05` of the highest final fit.
- Acquisition/onboarding creates the match-ready capability projection. Matching consumes it and never treats marketing prose, paid state, AI confidence, unverified reviews or stale facts as matching evidence.
- Urgent support is a separate pre-match pathway. The provider directory is official-source based; Google Maps/Places is optional, user-initiated, session-only and never a DTD inventory, claim, AI input or ranking signal.
- Production deployment, provider activation, billing, data-retention decisions, credential changes and destructive data work retain their existing separate gates.

## Open hypotheses and provisional planning defaults

These entries make planning uncertainty visible. They are not locked product decisions; M0 or the named package must either resolve them with fixture/evaluation evidence or retain them as an explicit later decision gate.

| ID | Question | Current planning position | Resolution evidence |
| --- | --- | --- | --- |
| H1 | What should an owner see when input is ambiguous, capability evidence is weak, supply is thin or AI is degraded? | **Open.** CDR-024 requires Decision Contract v2 to compare and choose bounded responses; no outcome is preselected. | M0 decision table and same-fixture AI/fallback evaluation in M9. |
| H2 | How are urgent-provider corrections handled without creating a high-maintenance provider portal? | **Provisional default:** a public correction/removal request enters an evidence-backed `/ops` review; only authorised official-source facts can change a public provider record. No provider self-service publishing is assumed for the first slice. | M6 workflow, correction fixtures, source/provenance checks and operator-load review. |
| H3 | How does a trainer learn that a capability field is stale, unsupported or no longer matchable? | **Provisional default:** the claim/profile surface shows the current structured capability status and correction path. Outbound notifications are not assumed until the communications path is evidenced and the need is demonstrated. | M1 trainer journey and M8 operator/trainer visibility tests. |
| H4 | How is declaration gaming detected without speculative scoring or arbitrary thresholds? | **Provisional default:** enforce structured vocabularies, field provenance, freshness, evidence-state invalidation and paid-field exclusion first; record explicit invalid/unsupported/boundary-crossing declarations for review. | M0 taxonomy, M1 validation tests, M8 exception evidence and M9 adversarial fixtures. |

## Completion dependency map

```text
M0 Decision Contract and fixture baseline
├─ M1 Trainer capability declaration and projection
├─ M2 Owner questionnaire, privacy and accessible states
├─ M3 Deterministic eligibility, geography and presentation
│  └─ M4 AI-assisted fit and deterministic fallback
├─ M5 Results, protected enquiry and follow-up
└─ M6 Urgent-support directory and triage
   └─ M7 Optional Maps/Places discovery surface, if enabled

M1–M6 + M8 Operations and observability
└─ M9 Integrated sandbox acceptance
   └─ M10 Separate production promotion gate
```

## Work packages

### M0 — Versioned decision contract and fixture baseline

**Status:** `OPEN`
**Depends on:** none
**Closes:** DF-021 in part; defines the repair scope for DF-018, DF-019, DF-022 and DF-023.

Create `Owner-to-Trainer Matching Decision Contract v2` as the implementation contract. It must define the normalised owner-input fields, validation, consent records, retention metadata, triage and decision-state vocabulary, API request/response schemas, reason codes, evidence grades, policy penalties, thin-supply trigger, explanation rules and exact screen states. It must select the owner-visible response for ambiguous input, weak evidence, low supply, absent required capability evidence and AI degradation. It must define material AI/fallback agreement for the same fixture: decision state, candidate eligibility, reason-code compatibility, explanation-fact truthfulness and permitted ordering variance. It must state how outcome data is excluded from fit until attribution, sample, freshness, anti-gaming and appeal rules have been accepted and validated.

Create a versioned fixture set with expected eligibility, fit and presentation outcomes. Each fixture must have permitted candidate facts, excluded facts, expected state, expected reason codes and expected displayed order; never use real owner descriptions. Define the initial anti-gaming event taxonomy around unsupported or out-of-vocabulary declarations, unsupported service-area expansion, stale-evidence attempts, repeated material declaration changes and any attempted paid-field input.

**Completion rule:** the contract and fixtures are reviewed against CDR-018 through CDR-024; every later package references their version; no unresolved ambiguity permits AI or a developer to make a product-policy choice at runtime.

**Required evidence:** contract document; fixture files; schema validation tests; decision-table review; independent audit.

### M1 — Trainer capability declaration and match-ready projection

**Status:** `OPEN`
**Depends on:** M0
**Closes:** DF-026; establishes the matching prerequisite for DF-014.

Implement the structured declaration across trainer onboarding, claim and profile-update paths. It must collect and confirm service areas, formats, concerns/specialties, relevant life stages, philosophy/method boundaries, in-home/facility constraints and material availability limits. Official-source data may prefill fields; trainers can correct or complete them.

Materialise or deterministically derive a match-ready projection with field-level normalised value, basis, source/evidence reference, last confirmation/retrieval, freshness, validation outcome and invalidation state. Changes, corrections, failed refresh, suppression and delisting must remove or limit capacity before later matches. Free text may explain a structured declaration but cannot create matchable claims on its own. The trainer claim/profile surface shows its current structured capability status and correction path; outbound notifications are not an assumed requirement for this slice.

**Completion rule:** a trainer's declared or authorised facts affect only the exact matching capacity they support; an unsupported or stale fact fails closed; paid tier cannot change capacity; trainer-facing status makes the correction path visible. Publication or contact readiness cannot become matchability authority from AI confidence alone.

**Required evidence:** migration/backfill plan and idempotent sandbox run; trainer-flow tests; acquisition/refresh/correction/suppression invalidation tests; projection query/index evidence; sanitised `/ops` evidence.

### M2 — Owner questionnaire, consent, privacy and accessible decision states

**Status:** `OPEN`
**Depends on:** M0
**Closes:** DF-015, DF-018, DF-021 and DF-022 in part; supports DF-020.

Replace the free-text-only match entry with the contract's mobile-first structured questionnaire. Validate canonical suburb/postcode, dog age/life stage, one or more concerns, service format, relevant method preference, bounded optional description and distinct consents before AI invocation. Add accessible labels, errors and live announcements for validation, loading and new decision states.

Persist only minimised, sanitised match data plus consent version/time and retention metadata. Keep behavioural descriptions and match context out of URL parameters, public analytics, trainer-profile fields and operator views. Use server-side match context for profile handoff and separate contact-release consent for an enquiry.

**Completion rule:** a user can understand and complete the questionnaire on mobile and desktop; invalid, declined-consent, urgent and Decision Contract-selected response states are explicit; records evidence the applicable consent without retaining unnecessary free text.

**Required evidence:** frontend interaction/accessibility tests; API validation and abuse-control tests; persistence and cleanup/expiry tests; URL/log/privacy regression checks; sandbox owner journey evidence.

### M3 — Deterministic eligibility, geographic search and fair presentation

**Status:** `OPEN`
**Depends on:** M0 and M1
**Closes:** DF-019; depends on the DF-014 acquisition authority repair and supports DF-023 and DF-026.

Implement the deterministic candidate pipeline before any AI fit call. Apply publication, suppression, policy, source-freshness, contact-readiness, declared service area, service-format and required-capability gates. Publication and contact gates must come from the acquisition-authority path, not model confidence. Build the local pool first. Expand only when fewer than three trainers pass local eligibility, disclose the expanded scope, and never present expanded candidates as local.

Apply deterministic presentation after fit. Where Decision Contract v2 selects a recommendation response, show up to three suitable candidates and follow its defined response when fewer than three candidates qualify or none has required capability evidence. Protect the paid-neutral raw score and apply the locked commercial ordering only within the exact `0.05` band. Resolve equality using a stable non-commercial field.

**Completion rule:** excluded trainers cannot reach AI or presentation; paid status cannot alter eligibility or raw fit; location and candidate-count disclosures match the actual applied search.

**Required evidence:** gate-by-gate unit tests; geography and thin-supply fixtures; `0.05` boundary tests; candidate-pool inspection proving paid/marketing/Google data exclusion; API/UI expanded-scope and Decision-Contract-selected weak-evidence response tests.

### M4 — AI-assisted fit, explanation and deterministic fallback

**Status:** `OPEN`
**Depends on:** M0, M1 and M3
**Closes:** DF-023.

Implement Gemini only over the bounded eligible projection and sanitised owner signals. The model returns the strict schema and response states selected by Decision Contract v2, with factual reason codes/explanations where candidates are presented. It receives neither commercial fields nor excluded candidates, raw provider/Google content, unsupported profile prose or unbounded owner data.

Build a deterministic fallback using exactly the same input projection, decision states and reason-code vocabulary. Timeout, rate limit, malformed JSON and unavailable-model events must result in the selected, truthful and observable Decision Contract response; the roadmap does not preselect that response.

**Completion rule:** Gemini and fallback are materially consistent against the fixture suite, and explanations cite only actual permitted facts.

**Required evidence:** prompt/input allow-list; output-schema validation; provider-failure simulation; parity report over fixtures; reason/explanation truthfulness review; latency and degraded-event `/ops` evidence.

### M5 — Results, protected enquiry and outcome/follow-up lifecycle

**Status:** `OPEN`
**Depends on:** M0, M2, M3 and M4
**Closes:** DF-015, DF-016, DF-017 and DF-020 in part.

Deliver one coherent owner path from a clear entry point to decision state, result cards, trainer profile and protected enquiry. Results must lead with the selected decision state and explain why a candidate fits using factual plain language where candidates are presented. They must disclose service area, format and expansion. Every Decision Contract-selected response and degraded route must be a useful destination, not a dead end. Replace unsupported “vetted”, “verified” or similar trust language with labels that match the actual evidence taxonomy.

Protect the match context server-side. Release only minimum relevant information to a trainer after distinct consent. Make outcome follow-up optional and implement distinct pending, retryable failure, delivered, terminal failure and suppression states. A previous failed send must not permanently prevent a safe retry; a successful send must not duplicate.

**Completion rule:** the full owner-to-trainer journey works on mobile and desktop without URL leakage; trainer communications contain only authorised context; follow-up is retry-safe and operator-visible.

**Required evidence:** browser journeys; profile/enquiry API and persistence tests; notification failure/retry/idempotency tests; trainer payload minimisation review; `/ops` lifecycle evidence.

### M6 — Urgent-support directory and deterministic triage

**Status:** `OPEN`
**Depends on:** M0 and M2
**Closes:** DF-024.

Create the approved urgent-route state machine and versioned owner-facing safety cards. Immediate human danger must bypass ordinary matching. Possible urgent animal-health needs must show only current, provider-authored contact information from the official-source urgent-provider directory. Serious behavioural and unclear states follow the contract and never generate freeform treatment, veterinary or legal advice.

Create the separate urgent-provider record type and its official-source provenance, category, stated location/service area, contact method, stated hours/availability, last-checked date, freshness handling and correction/removal path. The first correction/removal workflow is public request → evidence/provenance check → bounded `/ops` review → publish, hold or suppress; it does not assume provider self-service publishing. Start with evidence-backed regional coverage; where none exists, state that DTD has no current verified listing rather than implying Melbourne-wide availability.

**Completion rule:** every urgent path is reachable before ordinary matching, safe when AI is unavailable, truthful about coverage and provider availability, and independently observable without presenting DTD as a clinical or emergency service.

**Required evidence:** triage fixtures for all approved states; directory sourcing/provenance tests; stale/provider-correction tests; public-page mobile/desktop journeys; fallback routing tests; `/ops` coverage and freshness evidence.

### M7 — Optional Google Maps/Places urgent-support discovery surface

**Status:** `OPEN` (conditional; required only if the surface is enabled)
**Depends on:** M6
**Closes:** DF-025 when enabled and verified.

Before implementation, verify the precise selected Maps product's current terms, allowed data fields, attribution/display rules, session/caching limits, permitted Place-ID handling, privacy disclosure, cost controls and outage behaviour. Build an isolated, user-initiated navigation/discovery surface only after this review.

Google content must be visibly attributed and distinct from DTD directory facts. It must not populate or refresh trainer/provider records, substantiate DTD claims, enter Gemini inputs/outputs/evaluation/training, change ranking, or be retained beyond permitted session handling.

**Completion rule:** if enabled, the feature passes product-specific legal/terms review and sandbox tests proving attribution, data minimisation, no persistent DTD fact creation, no AI/ranking path and a truthful outage route. If it remains disabled, record it as intentionally unenabled rather than treating it as a core-matching failure.

**Required evidence:** selected-product assessment; implementation review; session/storage inspection; privacy-copy review; sandbox outage and boundary tests; `/ops` degradation evidence.

### M8 — Matching operations, audit records and anti-gaming controls

**Status:** `OPEN`
**Depends on:** M1 through M6
**Closes:** the `/ops` and record-evidence portions of DF-017 and DF-022 through DF-026.

Create sanitised records for policy version, consent/retention metadata, applied search scope, triage outcome, eligible-candidate count, AI/fallback path, reason codes, result IDs and degraded events. `/ops` must surface decision-state distribution, selected weak-evidence-response and thin-supply patterns, model health, provider-directory freshness/coverage/corrections, capability invalidation, anti-gaming exception events and follow-up lifecycle failures.

Provide only bounded recovery actions with authentication, confirmation, idempotency and audit records. Do not create routine manual matching or untracked override controls. Monitor declarations and provider changes for anti-gaming signals without exposing private owner data.

**Completion rule:** scripted operator scenarios prove that, without raw owner descriptions, an authorised operator can identify the affected record, policy/evidence reason, current state and bounded next action for: a stale trainer capability, model degradation, urgent-provider correction and failed follow-up. The same scenarios prove that `/ops` cannot silently override matching policy.

**Required evidence:** record schema and redaction tests; `/ops` role/auth checks; the four scripted operator scenarios; anti-gaming exception fixtures; operator workflows for degraded model, stale capability, provider correction and follow-up retry; audit-event inspection; privacy review.

### M9 — Integrated fixture, sandbox and independent-audit acceptance

**Status:** `OPEN`
**Depends on:** M0 through M6 and M8; M7 only if enabled.

Run the matching-specific sandbox gate in `specs/SANDBOX_VERIFICATION_MATRIX.md` against an isolated, disposable dataset. The suite must cover at least these realistic scenarios:

1. Puppy basic manners with a local suitable trainer.
2. Multiple concerns with an in-home requirement and method boundary.
3. Ambiguous description with the Decision Contract-selected response.
4. Fewer than three local eligible trainers and truthfully disclosed Greater Melbourne expansion.
5. No trainer with the required capability evidence after eligibility and fit rules, with the Decision Contract-selected response.
6. Stale, suppressed or unsupported trainer capability excluded before AI fit.
7. Exact `0.05` comparable-fit presentation boundary and an outside-band paid candidate.
8. Gemini timeout, rate limit and malformed output with the Decision Contract-selected deterministic fallback response.
9. Immediate human-danger, possible urgent animal-health, serious behavioural and unclear urgent routes.
10. Trainer declaration correction, failed refresh and suppression invalidating later matchability.
11. Consent rejection, privacy/URL protection and protected-enquiry minimisation.
12. Follow-up delivery, retryable failure, terminal suppression and no-duplicate success.
13. The same ordinary-case fixture through Gemini and deterministic fallback, assessed against M0's defined material-agreement bar.
14. Unsupported, out-of-vocabulary, stale or paid-field declaration attempts held or excluded with a visible anti-gaming exception.
15. Urgent-provider correction/removal request through evidence check, bounded operator review and a truthful public outcome.
16. The four scripted `/ops` recovery scenarios without exposure of owner free text.

Each implementation package is delegated, if at all, under the Antigravity local-only handoff rules. Codex independently audits the exact diff and reruns proportionate UI, API, persistence, automation/fallback, `/ops`, privacy and sandbox checks.

**Completion rule:** every mandatory scenario passes in sandbox; all M0–M6 and M8 packages are `DONE`; M7 is either `DONE` or recorded as intentionally disabled; DF-014 through DF-026 are closed only where they are matching-relevant and the evidence actually satisfies their next actions. No `PARTIAL`, `NOT_VERIFIED` or `REGRESSED` matching requirement remains.

**Required evidence:** exact commits; local and sandbox test output; sanitised fixture data; UI captures for mobile and desktop; persisted-record checks; `/ops` checks; independent audit report with a status for every package and finding.

### M10 — Separate production promotion gate

**Status:** `OPEN`
**Depends on:** M9.

Production promotion is outside sandbox completion. It requires the applicable owner authority and the existing review, remote CI, zero-traffic canary, live-safe smoke test and production acceptance sequence. No roadmap item authorises billing activation, provider/credential mutation, data-retention change or public coverage claim by implication.

**Completion rule:** only after M9 is `DONE` and the separate applicable production gates are expressly approved and evidenced.

## Final matching-pipeline completion definition

The matching pipeline is complete in the developer sandbox only when M0–M6, M8 and M9 are `DONE`, M7 is `DONE` if enabled or explicitly recorded as disabled, and every related current-state finding is either closed with evidence or legitimately `SUPERSEDED` by a later owner decision. M10 is a distinct production-release decision, not a shortcut to claim live completion.

At final audit, reconcile this roadmap line by line against the current target, code, test results, sandbox records and `/ops` evidence. Any unsupported claim is `NOT_VERIFIED`, not complete.
