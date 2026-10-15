# Owner-to-Trainer Matching Pipeline Completion Roadmap

**Purpose:** the execution checklist and post-completion verification basis for the owner-to-trainer matching pipeline.
**Status:** active roadmap; package status is set only by independent evidence and may be `DONE`, `PARTIAL`, `OPEN`, `NOT_VERIFIED`, `REGRESSED` or `SUPERSEDED`.
**Scope:** matching only. This does not replace DTD-wide release work, commercial activation, credential/provider recovery, or production approval gates.
**Authority:** executes, but does not amend, `DTD_TARGETED_MATCHING_PIPELINE_STATE.md`, `specs/MATCHING_AND_RANKING.md`, `specs/ACQUISITION_AND_INGESTION.md`, `specs/OPS_AND_OBSERVABILITY.md`, the invariants, and CDR-018 through CDR-024.

**Completion criteria:** [MATCHING_PIPELINE_REMAINING_COMPLETION_CRITERIA.md](MATCHING_PIPELINE_REMAINING_COMPLETION_CRITERIA.md) is the mandatory item-by-item acceptance companion. It converts every remaining package into auditable implementation, negative-case, data/automation, `/ops`, sandbox and independent-review checks. It does not change a locked product decision.

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
| M0 | Decision contract and fixture baseline | `DONE` — local contract/fixture baseline accepted; later package acceptance remains independent | None | DF-018, DF-019, DF-021, DF-022, DF-023 |
| M1 | Trainer declaration and capability projection | `PARTIAL` — declaration/projection exists; current-match freshness and sandbox migration evidence remain open | M0 | DF-014, DF-026 |
| M2 | Owner questionnaire, privacy and accessible states | `PARTIAL` — structured form and header-token handoff exist; token lifecycle and config-outage safety remain open | M0 | DF-015, DF-018, DF-021, DF-022 |
| M3 | Eligibility, geography and presentation | `PARTIAL` — deterministic path exists; stored-projection freshness bypass prevents acceptance | M0, M1 | DF-014, DF-019, DF-023, DF-026 |
| M4 | AI fit and deterministic fallback | `PARTIAL` — real adapter/mock failure tests exist; provider and sandbox parity are unverified | M0, M1, M3 | DF-023 |
| M5 | Results, enquiry and follow-up | `PARTIAL` — clean result/profile path exists; actual matched-enquiry delivery and direct-intro boundary remain open | M0, M2, M3, M4 | DF-015, DF-016, DF-017, DF-020 |
| M6 | Urgent-support directory and triage | `PARTIAL` — state machine exists; official-record accuracy and evidence-based reactivation remain open | M0, M2 | DF-024 |
| M7 | Optional Maps/Places discovery | `OPEN` (conditional) | M6 | DF-025 |
| M8 | `/ops`, records and anti-gaming | `PARTIAL` — protected redacted read model exists; false retry/delivery transition prevents acceptance | M1–M6 | DF-017, DF-022–DF-026 |
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
| H1 | What should an owner see when input is ambiguous, capability evidence is weak, supply is thin or AI is degraded? | **Resolved in Decision Contract v2.** Use clarification, disclosed limited-local results, no-confirmed-match, or the matching deterministic degraded equivalent as the applicable evidence state. | Implement M0 fixtures and M9 same-fixture AI/fallback evaluation. |
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

**Status:** `DONE` — local contract/fixture baseline accepted; downstream workflow and sandbox obligations remain separate.
**Depends on:** none
**Closes:** DF-021 in part; defines the repair scope for DF-018, DF-019, DF-022 and DF-023.

Decision Contract v2 is authored at `specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md`. It resolves the owner-visible response for ambiguity, thin supply, absent current capability evidence and AI degradation; it also fixes the v2 input, privacy, eligibility, fit, presentation and acceptance boundaries. The remaining M0 work is to implement its fixtures, data builders and Gemini/fallback parity harness before public workflow work.

Create a versioned fixture set with expected eligibility, fit and presentation outcomes. Each fixture must have permitted candidate facts, excluded facts, expected state, expected reason codes and expected displayed order; never use real owner descriptions. Define the initial anti-gaming event taxonomy around unsupported or out-of-vocabulary declarations, unsupported service-area expansion, stale-evidence attempts, repeated material declaration changes and any attempted paid-field input.

**Completion rule:** the contract and fixtures are reviewed against CDR-018 through CDR-024; every later package references their version; no unresolved ambiguity permits AI or a developer to make a product-policy choice at runtime.

**Required evidence:** contract document; fixture files; schema validation tests; decision-table review; independent audit.

**Evidence entry — 27 September 2026:** contract authority committed as `b4ce0c0` (`docs/specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md`) and the staged Antigravity implementation handoff committed as `b4ce0c0` (`docs/ANTIGRAVITY_MATCHING_PIPELINE_IMPLEMENTATION_HANDOFF.md`). Documentation cross-references were reviewed; `f8792f6` remediates one Markdown whitespace finding. No fixture, executable parity harness, code, provider or deployment evidence exists yet; M0 remains `PARTIAL`.

**Evidence entry — 4 October 2026:** P1 baseline was independently accepted at `5161a2bfc14514b3525f313ae361c4c580b8f847`. The cumulative P2-P6 implementation at `a167478592136bd4e0385f2c6dee3d0377c76222` contains versioned fixtures, the adapter boundary and focused parity tests. Codex reran 145 matching tests successfully and reviewed the complete changed path. M0 is `DONE` as a local baseline only; it does not establish sandbox or provider readiness. See `MATCHING_PIPELINE_P2_P6_INDEPENDENT_AUDIT_2026-10-04.md`.

### M1 — Trainer capability declaration and match-ready projection

**Status:** `PARTIAL`
**Depends on:** M0
**Closes:** DF-026; establishes the matching prerequisite for DF-014.

Implement the structured declaration across trainer onboarding, claim and profile-update paths. It must collect and confirm service areas, formats, concerns/specialties, relevant life stages, philosophy/method boundaries, in-home/facility constraints and material availability limits. Official-source data may prefill fields; trainers can correct or complete them.

Materialise or deterministically derive a match-ready projection with field-level normalised value, basis, source/evidence reference, last confirmation/retrieval, freshness, validation outcome and invalidation state. Changes, corrections, failed refresh, suppression and delisting must remove or limit capacity before later matches. Free text may explain a structured declaration but cannot create matchable claims on its own. The trainer claim/profile surface shows its current structured capability status and correction path; outbound notifications are not an assumed requirement for this slice.

**Completion rule:** a trainer's declared or authorised facts affect only the exact matching capacity they support; an unsupported or stale fact fails closed; paid tier cannot change capacity; trainer-facing status makes the correction path visible. Publication or contact readiness cannot become matchability authority from AI confidence alone.

**Required evidence:** migration/backfill plan and idempotent sandbox run; trainer-flow tests; acquisition/refresh/correction/suppression invalidation tests; projection query/index evidence; sanitised `/ops` evidence.

**Evidence entry — 4 October 2026:** `a167478` includes structured declaration and match-ready projection integration. Audit found `/match` trusts a stored record when it already has `projection_version`, bypassing the projection function's fresh capability/invalidation evaluation. M1 remains `PARTIAL` until the runtime re-evaluates current eligibility and the required sandbox migration/record evidence exists.

### M2 — Owner questionnaire, consent, privacy and accessible decision states

**Status:** `PARTIAL`
**Depends on:** M0
**Closes:** DF-015, DF-018, DF-021 and DF-022 in part; supports DF-020.

Replace the free-text-only match entry with the contract's mobile-first structured questionnaire. Validate canonical suburb/postcode, dog age/life stage, one or more concerns, service format, relevant method preference, bounded optional description and distinct consents before AI invocation. Add accessible labels, errors and live announcements for validation, loading and new decision states.

Persist only minimised, sanitised match data plus consent version/time and retention metadata. Keep behavioural descriptions and match context out of URL parameters, public analytics, trainer-profile fields and operator views. Use server-side match context for profile handoff and separate contact-release consent for an enquiry.

**Completion rule:** a user can understand and complete the questionnaire on mobile and desktop; invalid, declined-consent, urgent and Decision Contract-selected response states are explicit; records evidence the applicable consent without retaining unnecessary free text.

**Required evidence:** frontend interaction/accessibility tests; API validation and abuse-control tests; persistence and cleanup/expiry tests; URL/log/privacy regression checks; sandbox owner journey evidence.

**Evidence entry — 4 October 2026:** `a167478` implements the contract questionnaire, bounded description, consent, clean `/t/:id` links and header-only context retrieval. Audit found that a new non-handoff match does not clear a previous session token, and `/config` failure still defaults to live matching. M2 remains `PARTIAL`.

### M3 — Deterministic eligibility, geographic search and fair presentation

**Status:** `PARTIAL`
**Depends on:** M0 and M1
**Closes:** DF-019; depends on the DF-014 acquisition authority repair and supports DF-023 and DF-026.

Implement the deterministic candidate pipeline before any AI fit call. Apply publication, suppression, policy, source-freshness, contact-readiness, declared service area, service-format and required-capability gates. Publication and contact gates must come from the acquisition-authority path, not model confidence. Build the local pool first. Expand only when fewer than three trainers pass local eligibility, disclose the expanded scope, and never present expanded candidates as local.

Apply deterministic presentation after fit. Where Decision Contract v2 selects a recommendation response, show up to three suitable candidates and follow its defined response when fewer than three candidates qualify or none has required capability evidence. Protect the paid-neutral raw score and apply the locked commercial ordering only within the exact `0.05` band. Resolve equality using a stable non-commercial field.

**Completion rule:** excluded trainers cannot reach AI or presentation; paid status cannot alter eligibility or raw fit; location and candidate-count disclosures match the actual applied search.

**Required evidence:** gate-by-gate unit tests; geography and thin-supply fixtures; `0.05` boundary tests; candidate-pool inspection proving paid/marketing/Google data exclusion; API/UI expanded-scope and Decision-Contract-selected weak-evidence response tests.

**Evidence entry — 4 October 2026:** `a167478` implements deterministic gating, local-first expansion and `0.05` presentation tests. The stored-projection bypass recorded under M1 can admit stale or invalidated capability facts, so M3 remains `PARTIAL`.

### M4 — AI-assisted fit, explanation and deterministic fallback

**Status:** `PARTIAL`
**Depends on:** M0, M1 and M3
**Closes:** DF-023.

Implement Gemini only over the bounded eligible projection and sanitised owner signals. The model returns the strict schema and response states selected by Decision Contract v2, with factual reason codes/explanations where candidates are presented. It receives neither commercial fields nor excluded candidates, raw provider/Google content, unsupported profile prose or unbounded owner data.

Build a deterministic fallback using exactly the same input projection, decision states and reason-code vocabulary. Timeout, rate limit, malformed JSON and unavailable-model events must result in the selected, truthful and observable Decision Contract response; the roadmap does not preselect that response.

**Completion rule:** Gemini and fallback are materially consistent against the fixture suite, and explanations cite only actual permitted facts.

**Required evidence:** prompt/input allow-list; output-schema validation; provider-failure simulation; parity report over fixtures; reason/explanation truthfulness review; latency and degraded-event `/ops` evidence.

**Evidence entry — 4 October 2026:** `a167478` replaces the default stub with `GeminiMatchingAdapter`, with constrained input, JSON validation, 5-second timeout and mocked fallback/degradation tests. No configured provider or same-fixture sandbox Gemini/fallback parity evidence was performed. M4 remains `PARTIAL`.

### M5 — Results, protected enquiry and outcome/follow-up lifecycle

**Status:** `PARTIAL`
**Depends on:** M0, M2, M3 and M4
**Closes:** DF-015, DF-016, DF-017 and DF-020 in part.

Deliver one coherent owner path from a clear entry point to decision state, result cards, trainer profile and protected enquiry. Results must lead with the selected decision state and explain why a candidate fits using factual plain language where candidates are presented. They must disclose service area, format and expansion. Every Decision Contract-selected response and degraded route must be a useful destination, not a dead end. Replace unsupported “vetted”, “verified” or similar trust language with labels that match the actual evidence taxonomy.

Protect the match context server-side. Release only minimum relevant information to a trainer after distinct consent. Make outcome follow-up optional and implement distinct pending, retryable failure, delivered, terminal failure and suppression states. A previous failed send must not permanently prevent a safe retry; a successful send must not duplicate.

**Completion rule:** the full owner-to-trainer journey works on mobile and desktop without URL leakage; trainer communications contain only authorised context; follow-up is retry-safe and operator-visible.

**Required evidence:** browser journeys; profile/enquiry API and persistence tests; notification failure/retry/idempotency tests; trainer payload minimisation review; `/ops` lifecycle evidence.

**Evidence entry — 4 October 2026:** `a167478` removes the prior URL description/match query flow and uses header-based protected context for the profile path. Audit found matched follow-ups are stored and returned as `delivered` without notification dispatch, while `/intros` still accepts client `match_id`. M5 remains `PARTIAL`.

### M6 — Urgent-support directory and deterministic triage

**Status:** `PARTIAL`
**Depends on:** M0 and M2
**Closes:** DF-024.

Create the approved urgent-route state machine and versioned owner-facing safety cards. Immediate human danger must bypass ordinary matching. Possible urgent animal-health needs must show only current, provider-authored contact information from the official-source urgent-provider directory. Serious behavioural and unclear states follow the contract and never generate freeform treatment, veterinary or legal advice.

Create the separate urgent-provider record type and its official-source provenance, category, stated location/service area, contact method, stated hours/availability, last-checked date, freshness handling and correction/removal path. The first correction/removal workflow is public request → evidence/provenance check → bounded `/ops` review → publish, hold or suppress; it does not assume provider self-service publishing. Start with evidence-backed regional coverage; where none exists, state that DTD has no current verified listing rather than implying Melbourne-wide availability.

**Completion rule:** every urgent path is reachable before ordinary matching, safe when AI is unavailable, truthful about coverage and provider availability, and independently observable without presenting DTD as a clinical or emergency service.

**Required evidence:** triage fixtures for all approved states; directory sourcing/provenance tests; stale/provider-correction tests; public-page mobile/desktop journeys; fallback routing tests; `/ops` coverage and freshness evidence.

**Evidence entry — 4 October 2026:** `a167478` implements four deterministic triage states and isolated urgent-provider records. Current official-source review found the static Lost Dogs' Home telephone and hours are inaccurate, and correction acceptance can restore `current` status without verified official evidence. M6 remains `PARTIAL`.

### M7 — Optional Google Maps/Places urgent-support discovery surface

**Status:** `OPEN` (conditional; required only if the surface is enabled)
**Depends on:** M6
**Closes:** DF-025 when enabled and verified.

Before implementation, verify the precise selected Maps product's current terms, allowed data fields, attribution/display rules, session/caching limits, permitted Place-ID handling, privacy disclosure, cost controls and outage behaviour. Build an isolated, user-initiated navigation/discovery surface only after this review.

Google content must be visibly attributed and distinct from DTD directory facts. It must not populate or refresh trainer/provider records, substantiate DTD claims, enter Gemini inputs/outputs/evaluation/training, change ranking, or be retained beyond permitted session handling.

**Completion rule:** if enabled, the feature passes product-specific legal/terms review and sandbox tests proving attribution, data minimisation, no persistent DTD fact creation, no AI/ranking path and a truthful outage route. If it remains disabled, record it as intentionally unenabled rather than treating it as a core-matching failure.

**Required evidence:** selected-product assessment; implementation review; session/storage inspection; privacy-copy review; sandbox outage and boundary tests; `/ops` degradation evidence.

### M8 — Matching operations, audit records and anti-gaming controls

**Status:** `PARTIAL`
**Depends on:** M1 through M6
**Closes:** the `/ops` and record-evidence portions of DF-017 and DF-022 through DF-026.

Create sanitised records for policy version, consent/retention metadata, applied search scope, triage outcome, eligible-candidate count, AI/fallback path, reason codes, result IDs and degraded events. `/ops` must surface decision-state distribution, selected weak-evidence-response and thin-supply patterns, model health, provider-directory freshness/coverage/corrections, capability invalidation, anti-gaming exception events and follow-up lifecycle failures.

Provide only bounded recovery actions with authentication, confirmation, idempotency and audit records. Do not create routine manual matching or untracked override controls. Monitor declarations and provider changes for anti-gaming signals without exposing private owner data.

**Completion rule:** scripted operator scenarios prove that, without raw owner descriptions, an authorised operator can identify the affected record, policy/evidence reason, current state and bounded next action for: a stale trainer capability, model degradation, urgent-provider correction and failed follow-up. The same scenarios prove that `/ops` cannot silently override matching policy.

**Required evidence:** record schema and redaction tests; `/ops` role/auth checks; the four scripted operator scenarios; anti-gaming exception fixtures; operator workflows for degraded model, stale capability, provider correction and follow-up retry; audit-event inspection; privacy review.

**Evidence entry — 4 October 2026:** `a167478` supplies protected redacted read models and authenticated confirmation-gated recovery endpoints. The follow-up recovery endpoint changes state to `delivered` without dispatching a notification, and urgent-provider correction acceptance can reactivate a record without source verification. M8 remains `PARTIAL`.

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
