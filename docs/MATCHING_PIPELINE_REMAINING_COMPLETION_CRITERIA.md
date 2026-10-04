# Owner-to-Trainer Matching: Remaining Completion Criteria

**Purpose:** the executable, evidence-led acceptance contract for the remaining owner-to-trainer matching roadmap. A future Antigravity handoff and Codex audit must assess every applicable criterion in this document before a work package can become `DONE`.

**Authority order:** `AGENTS.md` → invariants → CDR-018 through CDR-024 → [Decision Contract v2](specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md) → active matching specifications → [completion roadmap](DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md) → current-state findings. The Decision Contract controls the initial fit/presentation rules where an older planning document describes a later, outcome-enabled model.

**Current implementation candidate:** `8e03f6c29c43ad69d93edcb9a94414ec633fe128`, following cumulative local implementation `a167478592136bd4e0385f2c6dee3d0377c76222`; P1 reference baseline `5161a2bfc14514b3525f313ae361c4c580b8f847`. `8e03f6c` is not accepted for sandbox advancement: see the [latest independent audit](MATCHING_PIPELINE_8E03F6C_INDEPENDENT_AUDIT_2026-10-05.md), the [follow-up audit](MATCHING_PIPELINE_C7AFB07_INDEPENDENT_AUDIT_2026-10-05.md), and the original [P2-P6 audit](MATCHING_PIPELINE_P2_P6_INDEPENDENT_AUDIT_2026-10-04.md). This document does not change product policy or authorise deployment, provider activation, billing, authentication, data mutation, or production release.

## How a package becomes `DONE`

A package is `DONE` only when every applicable criterion below has a traceable evidence reference and Codex independently verifies the exact implementation commit. A passing unit test, a rendered screen, a database row, an endpoint `200`, or an Antigravity report is never sufficient by itself.

For every package, the evidence handoff must include:

1. exact branch, base SHA and commit SHA(s), plus a changed-file list;
2. local commands and complete outcomes, including any skipped tests and why;
3. schema/index/migration/data effects, including idempotent rerun evidence where relevant;
4. proof that no deployment, provider, billing, credential, authentication or production mutation occurred during implementation;
5. the affected owner, trainer, autonomous-system and operator workflow paths;
6. success, invalid, duplicate, stale/expired, suppressed, degraded and recovery branches relevant to the package;
7. sanitised fixture data and persisted-record samples; and
8. residual risks and the exact roadmap/finding IDs claimed closed.

Codex then reviews the actual diff and whole affected paths, re-runs proportionate checks and records every item as `DONE`, `PARTIAL`, `OPEN`, `REGRESSED`, `NOT_VERIFIED`, or `SUPERSEDED`. Any material `PARTIAL`, `OPEN`, `REGRESSED` or `NOT_VERIFIED` result returns the package to implementation; it cannot advance to sandbox.

## Cross-cutting non-negotiable controls

These controls apply to every remaining package. Evidence must demonstrate them once per affected path rather than merely restating them.

- [ ] **Three-layer separation:** deterministic eligibility, paid-neutral fit, and deterministic presentation remain separate. Commercial state is absent from eligibility and AI inputs, absent from raw/final fit, and may appear only in the locked `<= 0.05` presentation band.
- [ ] **Evidence authority:** matching uses only current, validated, permitted match-ready facts; marketing prose, reviews, pricing, sponsorship, AI confidence, raw acquisition pages and Maps/Places content cannot become matching facts.
- [ ] **Fail-closed freshness:** stale, invalidated, suppressed, disputed, uncontactable or statutory-revoked facts cannot reach an AI candidate pool or a public recommendation.
- [ ] **Privacy minimisation:** raw owner behavioural descriptions, contact details, IP addresses, opaque tokens, prompts and diagnostic scores are absent from URLs, public cards, analytics, routine logs and `/ops` read models.
- [ ] **Truthful copy:** public language distinguishes declared, official-source, reviewed and claimed facts; it does not say `verified`, `vetted`, available, qualified, safe, recommended, emergency or Melbourne-wide unless the exact evidence supports that claim.
- [ ] **No hidden manual matching:** no operator route can change a candidate, score, eligibility result or presentation order without an explicit policy-supported bounded action, authentication, confirmation, idempotency and audit record.
- [ ] **No unauthorised external state:** implementation itself does not deploy, send to real recipients, alter providers, enable billing/authentication, alter production data or make unsupported coverage claims.

## M0 — Decision contract and fixture baseline

**Current status:** `DONE` locally. M0 is preserved as the reference baseline and must be reopened only if an explicit owner challenge or a new contract version changes matching policy.

To retain `DONE`:

- [ ] Contract version, canonical owner/trainer taxonomies, response states, score threshold, 0.05 presentation boundary, allowed reason codes and privacy/retention rules are versioned and have no unresolved contradiction with locked decisions.
- [ ] Every fixture uses synthetic owner data and records expected triage state, eligible IDs, fit-qualified IDs, reason-code categories, search scope, displayed order and parity expectation.
- [ ] The fixture harness proves candidate/presentation invariants without a live Gemini call.
- [ ] A contract change increments the policy/fixture version, identifies affected M1-M10 acceptance criteria and triggers a new independent audit before implementation proceeds.

## M1 — Trainer declaration and match-ready capability projection

**Current status:** `PARTIAL`. This package owns trainer capacity truth, not case-specific ranking.

### Functional completion criteria

- [ ] Trainer onboarding, verified claim and authenticated profile-update paths collect the structured fields required for matching: specialties, service formats, life-stage support, philosophy/method boundary, explicit serviced suburbs or approved catchment, and delivery constraints.
- [ ] The trainer sees prefilled official/acquisition facts distinctly from their declaration, can correct or omit each field, and must make an explicit confirmation before a declaration becomes matching capacity.
- [ ] Every matchable field stores normalised canonical value, basis, evidence reference, confirmation/retrieval timestamp, validation result, freshness state and invalidation metadata.
- [ ] AI-proposed or marketing/free-text values can be displayed only as non-matchable prefill/proposals; they cannot become `trainer_declaration` by claim verification alone.
- [ ] A projection is recomputed from authoritative trainer facts at match time, or a materialised projection has a proven current freshness/invalidation gate evaluated at match time. Presence of `projection_version` alone is never proof that the projection remains current.
- [ ] Publication, suppression, claim dispute, contact readiness and statutory status are evaluated from current authority records. A stale, unsupported, invalidated or revoked field fails closed only for the capacity it affects.
- [ ] Trainer correction, capability removal, failed refresh, suppression, delisting and statutory revocation invalidate affected matchability before the next match request.
- [ ] Paid tier, sponsor state, price, bio, reviews and acquisition-model confidence are absent from the projection and cannot affect capacity.
- [ ] The trainer-facing surface shows current match-ready status, non-matchable reasons and a correction path without exposing internal risk scoring or other trainers' data.

### Required negative and lifecycle tests

- [ ] Unconfirmed official/AI prefill, expired declaration, invalid term, missing required capacity, claim dispute, no contact readiness, unpublished/suppressed record and statutory revocation each exclude the trainer before AI invocation.
- [ ] A record with a previously materialised `projection_version` but newly stale or invalidated source fact is excluded; this specifically closes MP-001.
- [ ] A trainer declaration correction changes only supported match paths and does not unintentionally erase unrelated valid fields or historical audit evidence.
- [ ] Repeating confirmation/correction and migration/backfill operations is idempotent: no duplicate facts, no extended freshness without a real confirmation, and no promotion of AI-proposed facts.
- [ ] A paid-tier/marketing-field injection attempt cannot change the projection, eligibility result or anti-gaming evidence outcome.

### Data, operations and sandbox evidence

- [ ] A migration/backfill plan scopes exact collections/fields, is non-destructive, is executed only against a disposable sandbox dataset, and passes a second-run idempotency check.
- [ ] Required indexes/query plan are inspected for the match-readiness access path; the implementation does not hide a broad unbounded scan behind a small test fixture.
- [ ] `/ops` shows capability health, stale/invalidated counts and actionable reason codes without owner data or raw trainer evidence.
- [ ] Sandbox evidence traces a trainer from claim/declaration through a matchable projection, then correction/suppression through exclusion.

**M1 completion rule:** every trainer capacity assertion used in matching is current, structured, attributable and invalidated safely; no historical projection can bypass current evidence.

## M2 — Owner questionnaire, consent, privacy and accessible decision states

**Current status:** `PARTIAL`.

### Functional completion criteria

- [ ] The owner entry path has one clear, mobile-first route from public navigation/CTA to the structured questionnaire; stale waitlist/browse-only wording does not compete with a live matching path.
- [ ] The form collects and validates exactly the v2 request: canonical locality/postcode, age `0..360`, one or more concerns, service format, explicit method preference, bounded description and required matching/terms consent.
- [ ] `other` and `unsure` require a sufficient description; ambiguous postcode, invalid locality, missing/contradictory data and declined consent return the Decision Contract response before candidate lookup or AI invocation.
- [ ] Client checks improve usability but server validation is authoritative. Unknown fields, malformed types, oversized text, repeated submissions and limit breaches fail safely.
- [ ] The form has associated visible labels, instructions, keyboard operation, focus management, accessible errors, loading status and live announcements for every new decision state.
- [ ] The config-loading posture fails closed: unavailable or incomplete `/config` presents a truthful unavailable/waitlist state, not a live matching form. This closes the audited config-outage defect.
- [ ] A new match submission clears any previous match-context token before request dispatch. It stores only a new valid handoff token in `sessionStorage`; a non-handoff, error, expiry or invalid token leaves no prior context active.
- [ ] The raw behavioural description is PII-sanitised before model use and is not stored in match events, URLs, analytics, public result payloads, trainer profiles or `/ops`.
- [ ] Match records retain only versioned policy, normalised selections, consent/timestamp, route/state, reason codes, result IDs, retention expiry and token hash required by the contract.
- [ ] Token and detailed record retention/cleanup are automated and demonstrably remove or irreversibly aggregate expired data after 30 days.

### Required tests and evidence

- [ ] Frontend tests cover each input constraint, error, accessibility role/live state, mobile keyboard path, consent decline and config failure/partial config.
- [ ] API tests cover unknown/ambiguous locality, age bounds/type, concern/description rule, all consent combinations, description PII sanitisation, rate limit/burst, token expiry and expired-record cleanup.
- [ ] Privacy regression scans prove no behavioural text or token occurs in matching/profile URLs, referrers, public payloads, client telemetry or redacted `/ops` samples.
- [ ] Browser evidence on mobile and desktop captures normal, invalid, clarification, urgent, no-match and degraded states using synthetic data only.
- [ ] Sandbox record inspection proves token hashes—not token values—and no raw description appear in matching records.

**M2 completion rule:** an owner can complete or safely stop the questionnaire on mobile and desktop; every response state is accessible and privacy-bounded; a configuration or token failure cannot silently expose matching or stale context.

## M3 — Deterministic eligibility, geography and fair presentation

**Current status:** `PARTIAL`.

### Functional completion criteria

- [ ] Candidate retrieval begins from the current M1 projection and deterministic identity/contact gates; every ineligible trainer is excluded before the AI adapter is created or called.
- [ ] Eligibility checks each applicable gate independently: active region/publication, suppression/dispute/statutory/contact readiness, current capacity, exact local service-area declaration, requested format, life stage, required concern/specialty mapping and method compatibility.
- [ ] Missing support fails closed for the affected owner path. Radius/distance matching remains disabled until a separately approved canonical geo policy exists.
- [ ] Local eligibility runs first. Only when fewer than three local candidates pass may expanded eligibility consider declared `greater_melbourne`/`melbourne_wide` coverage; a trainer's profile suburb alone is never expanded coverage.
- [ ] The system records the actual local count, eligible IDs and local/expanded membership. Public results label every expanded candidate and disclose the expansion reason.
- [ ] Fit/presentation uses at most 15 eligible candidates for AI and at most three public results.
- [ ] Final fit is paid-neutral under Decision Contract v2: `final_fit = match_score - policy_penalty`, with outcome contribution exactly zero until a later accepted policy version enables it.
- [ ] `policy_penalty` is non-commercial, documented, reason-coded and tested; it cannot conceal a contact/readiness eligibility failure.
- [ ] The comparable-fit set is exactly `Smax - final_fit <= 0.05`. Commercial ordering applies only inside that set; outside it fit order is absolute; remaining ties use a stable non-commercial ID.
- [ ] Public responses omit score, tier, sponsor state, policy penalty and internal ordering metadata. Internal records keep raw fit and presentation order separately for audit.

### Required tests and evidence

- [ ] Gate-by-gate fixture tests prove each exclusion independently and prove excluded documents never occur in Gemini payloads.
- [ ] Geography tests cover exact canonical suburb, ambiguous postcode, less-than-three local pool, valid declared expansion, invalid profile-suburb expansion and all-empty pool.
- [ ] Presentation tests cover exactly `0.05`, just inside, just outside, equal scores and a higher-paid but lower-fit candidate outside the band.
- [ ] Tests prove paid/marketing/Google fields cannot affect raw fit, eligibility, AI payload or displayed factual explanation.
- [ ] API/UI evidence proves local, limited-local and no-confirmed-match states have truthful scope/count disclosure.
- [ ] Sandbox persisted records and `/ops` sample agree with the actual candidate pool and presentation order for selected fixtures.

**M3 completion rule:** only the exact set of currently eligible trainers can reach fit; geography and commercial ordering are transparently and mathematically faithful to the contract.

## M4 — AI-assisted fit, explanation and deterministic fallback

**Current status:** `PARTIAL`.

### Functional completion criteria

- [ ] The production default is a real configured `GeminiMatchingAdapter`, not a test stub. It obtains model/project/location/credentials only from existing managed runtime configuration; no secret or provider-management identity is embedded in code.
- [ ] Gemini receives a maximum of 15 already eligible projections and only the allow-listed fields: version, normalised owner signals, PII-sanitised description, ID, specialties, formats, life stages, method/philosophy, service-area/catchment and delivery constraints.
- [ ] Gemini input contains no candidate name/contact/URL, tier, sponsorship, pricing, bio, reviews, raw source content, Maps data, excluded trainer, owner PII or raw description.
- [ ] The model is constrained to approved decision states, eligible IDs, numerical range, allowed reason codes and factual non-clinical output. Unexpected IDs, duplicate IDs, malformed schema, out-of-range scores, unapproved codes or unsupported explanation claims fail validation.
- [ ] Server-side code renders or validates the public explanation against permitted facts; model prose cannot add credentials, availability, diagnosis, outcomes, superlatives or guarantees.
- [ ] Five-second timeout, rate limit, unavailable client/service and malformed/invalid response each use deterministic fallback and write a sanitised degradation event.
- [ ] Fallback operates on exactly the same eligible pool, compatibility gates, decision states and reason-code vocabulary. It is not allowed to broaden geography, revive excluded candidates or make a commercial decision.
- [ ] Owner-visible degraded state says standard matching rules were used without exposing provider internals.

### Required tests and evidence

- [ ] Offline tests assert prompt allow-list and forbidden-field absence, system constraints, ID closure, duplicate/unknown candidate rejection, schema/range/code validation and explanation truthfulness.
- [ ] Simulations cover timeout at five seconds, 429/rate limit, unavailable/unconfigured provider, transport error and malformed JSON/output.
- [ ] A versioned parity report covers every M0 ordinary fixture and records: triage state, eligible IDs, decision state, qualified candidate set, compatible reason-code categories, factual explanation review and allowable rank variation only within `0.05`.
- [ ] The report documents any disagreement as a failing fixture or an explicit policy issue; it never silently lowers the parity bar.
- [ ] Sandbox verifies managed runtime configuration without exposing credentials, performs one bounded safe provider call using synthetic data, and proves fallback/degradation telemetry in `/ops`.
- [ ] No real owner/trainer data is sent solely to create evaluation evidence.

**M4 completion rule:** Gemini materially improves semantic fit inside a closed factual pool, and every provider failure returns a truthful, observable deterministic result with tested parity.

## M5 — Results, protected enquiry and follow-up lifecycle

**Current status:** `PARTIAL`.

### Functional completion criteria

- [ ] Results lead with the actual decision state and useful next action. Recommendation cards contain only trainer identity, factual local/service-format information, approved reason/explanation and explicit expansion/degraded disclosure where applicable.
- [ ] Results/profiles do not use unsupported `verified`, `vetted`, credential, insurance, availability, outcome or emergency claims. Any label maps to an evidenced taxonomy.
- [ ] The profile route is clean `/t/:trainerId`; no match ID, opaque token or description appears in its query string, browser history/referrer or link preview.
- [ ] Profile match context is retrieved only with the opaque header token, returns the minimum safe normalised context, and is inaccessible with a query token, missing token, invalid token, expired token or an unrelated trainer.
- [ ] Direct directory enquiries and matched enquiries are distinct: the protected matched route derives match attribution from context; direct `/intros` rejects or ignores client `match_id` and never persists arbitrary matching attribution. This closes MP-004.
- [ ] Separate contact/referral consent is required at enquiry time; no contact/description is released to a trainer without it.
- [ ] Matched enquiry uses the same real dispatch contract as direct enquiry. It starts as `pending` and resolves only from an actual notification result to `delivered`, `retryable_failure`, `terminal_failure` or `suppressed`.
- [ ] `delivered` means a provider accepted the notification or an explicitly defined equivalent delivery confirmation—not merely an intro row insert or an operator click. This closes MP-002.
- [ ] Idempotency protects client retries and concurrent submissions. A success cannot send twice; a retryable failure can safely retry with bounded attempts/backoff; terminal failure and suppression cannot be falsely retried.
- [ ] Trainer communication includes only separately authorised enquiry data and no raw behavioural description beyond the owner-released notes.
- [ ] Optional outcome/follow-up remains separate from match scoring and uses distinct consent, lifecycle state, expiry and unsubscribe/suppression behaviour.

### Required tests and evidence

- [ ] Full browser journeys cover normal match → result → profile → matched enquiry, direct directory enquiry, no-confirmed-match, expanded result, degraded result, invalid/expired/foreign context and mobile keyboard flow.
- [ ] Tests prove clean URLs/referrers, token removal on new match/expiry, token non-disclosure in API errors/logs and no client-controlled match attribution.
- [ ] Notification tests use a sandbox/test sink and cover successful send, provider timeout, retryable failure then one successful retry, terminal failure, fraud/duplicate suppression and idempotent replay after success.
- [ ] Persisted intro/notification/audit samples show state transitions, attempt identifiers/timestamps and no contradictory `delivered` state.
- [ ] `/ops` displays aggregated lifecycle states and bounded recovery action, without owner contact details or free text.

**M5 completion rule:** the owner can follow a truthful, privacy-safe path from result to contact, and every claimed delivery/retry state corresponds to a real idempotent notification attempt and operator-visible evidence.

## M6 — Urgent-support directory and deterministic triage

**Current status:** `PARTIAL`.

### Functional completion criteria

- [ ] Triage executes before ordinary matching and deterministically distinguishes `immediate_human_danger`, `urgent_animal_health_support`, `serious_behavioural_support` and `needs_clarification`.
- [ ] Immediate human danger stops ordinary matching, issues no candidate/token and shows only approved Victorian Triple Zero information and a current official link. It gives no handling, clinical, legal or behavioural-treatment advice.
- [ ] Urgent animal-health support stops ordinary matching, issues no candidate/token and displays only current official/provider-authored records. If no current local record exists, the UI says so and avoids a coverage implication.
- [ ] Serious behavioural support continues only through ordinary eligibility with the stricter required capability evidence; unclear inputs request clarification without scoring.
- [ ] Triage continues to work safely if Gemini is unavailable because its safety state machine and approved copy are deterministic.
- [ ] Each urgent-provider record contains category, provider identity, official source URL, exact displayed contact/hours/service area, checked timestamp, freshness state, evidence reference and correction/removal path.
- [ ] Every displayed provider fact is rechecked from its official source before sandbox release. The record must match the source exactly enough to avoid wrong phone, hours, availability or location claims. This includes correcting the audited Lost Dogs' Home facts and preserving the correct U-Vet Werribee exclusion.
- [ ] `current` can be set or restored only after an operator has recorded independently checked official-source evidence. A public correction request alone can create only `pending_review`; it cannot reactivate or rewrite a provider. This closes MP-003.
- [ ] Freshness expiry/change detection moves unsupported records to held/stale/suppressed before public display. There is a defined evidence-based recheck path, not a false automatic reactivation.
- [ ] Directory/public copy says only what its evidence supports. It never claims Melbourne-wide emergency coverage, 24/7 availability, clinical endorsement or a veterinary-behaviourist listing without both direct provider and regulator evidence.
- [ ] The dedicated support page, questionnaire and results use the same record/copy source to avoid contradictory emergency information.

### Required tests and evidence

- [ ] Synthetic fixtures cover all four triage states, mixed/ambiguous language, Gemini unavailable and no-provider/stale-provider route.
- [ ] Provider tests cover exact official source fields, freshness expiry, missing evidence hold, public correction submission, unsupported correction rejection, verified correction acceptance, suppression and non-reactivation without new evidence.
- [ ] UI mobile/desktop captures show each safety card, no-match/token state, source link, coverage limitation and no freeform advice.
- [ ] `/ops` shows current/stale/held/suppressed counts, coverage gaps, correction state, last check/evidence reference and bounded next action without exposing contributor contact details.
- [ ] Sandbox source review stores only sanitised provenance metadata; it does not use Maps/Places or search-grounding to populate DTD provider facts.

**M6 completion rule:** urgent routes are deterministic, safety-bounded and factually current; provider information is independently evidenced, can age safely, and never overstates coverage or medical authority.

## M7 — Optional Google Maps/Places urgent-support discovery

**Current status:** `OPEN`, conditional. It is not a core matching blocker while disabled.

### If the feature remains disabled

- [ ] The roadmap records it as intentionally disabled for the current release, and public/API surfaces make no claim that live Google discovery is available.
- [ ] No Maps/Places content, Place ID, Google grounding result or Google-derived field enters persistent trainer/provider records, Gemini, eligibility, ranking, analytics or test fixtures.

### If the feature is enabled

- [ ] Before code work, document the exact Maps product, current terms, permitted fields, attribution rules, caching/session limits, Place-ID allowance, privacy notice, cost/quota controls, abuse controls and outage behaviour using primary sources.
- [ ] Entry is available only after the approved urgent route and is explicitly user-initiated. It is navigation/discovery assistance, not a DTD recommendation or provider-directory record.
- [ ] Content has required Google attribution, is visually and semantically separated from official-source DTD records, and is retained only for the allowed session duration.
- [ ] The feature cannot create/refresh trainers or urgent providers, substantiate DTD claims, influence AI/eligibility/fit/presentation, or become model evaluation/training input.
- [ ] Outage, quota, bad response and no-results states are clear, safe and do not block approved static emergency/support information.
- [ ] Sandbox tests inspect network/storage boundaries, attribution, session expiry, no-persistence/no-ranking proof, cost/error controls and `/ops` aggregate degradation visibility.

**M7 completion rule:** either explicitly disabled with no hidden dependency, or enabled only as a terms-compliant, attributed, session-scoped navigation aid that is technically isolated from DTD matching truth.

## M8 — Matching operations, audit records and anti-gaming controls

**Current status:** `PARTIAL`.

### Functional completion criteria

- [ ] Protected `/ops` read models expose the aggregate evidence required by the contract: policy version, decision/triage distribution, scope, eligible counts, result/presentation IDs, AI/fallback/degradation state, reason-code patterns, capability health, provider freshness/corrections and enquiry/follow-up lifecycle.
- [ ] Read models explicitly exclude raw behavioural text, owner/trainer contact details, IPs, tokens, prompts, raw scores, commercial tiers and confidential provider evidence.
- [ ] Each mutable recovery action requires oversight authentication, explicit confirmation, bounded allowed action, idempotency/concurrency protection and a sanitised audit event naming actor/time/before/after reason.
- [ ] Degradation acknowledgement may only acknowledge/reset the documented bounded health state; it cannot hide events or change matching outcomes.
- [ ] Capability recheck recomputes facts under the same live projection rules as matching. It cannot manually mark a trainer eligible or bypass source freshness.
- [ ] Provider-correction review cannot make an unsupported record current. It requires a captured official-source verification outcome; suppress/hold paths are safe and auditable.
- [ ] Follow-up recovery calls the real dispatch pathway and updates state from its actual result. It never writes `delivered` without delivery evidence. This closes MP-002 at the operator layer.
- [ ] Anti-gaming events cover unsupported/out-of-vocabulary fields, stale capability attempts, material declaration changes, invalid catchment expansion and paid/commercial field injection. They are actionable without speculative hidden scoring.
- [ ] No `/ops` control enables routine manual matching, score overrides, candidate substitution or untracked policy change.

### Required tests and evidence

- [ ] Auth tests prove absent/invalid credentials are rejected and rate-limited; valid operator access is required for each mutating endpoint.
- [ ] Recovery tests cover duplicate click/idempotent replay, invalid state, stale record, terminal failure, source-evidence rejection and successful bounded action.
- [ ] Redaction tests enumerate and assert forbidden fields against every matching `/ops` payload and audit sample.
- [ ] The four scripted operator scenarios run in sandbox: stale trainer fact, Gemini degradation, urgent-provider correction and failed follow-up retry. Each proves identification, evidence reason, bounded action, resulting state and audit event.
- [ ] `/ops` labels a no-provider/no-data condition as such; it does not manufacture a healthy or delivered state from missing telemetry.

**M8 completion rule:** a solo operator can understand and safely resolve defined exceptions from evidence, while `/ops` cannot leak owner data or override matching policy.

## M9 — Integrated sandbox and independent-audit acceptance

**Current status:** `OPEN`. M9 validates the joined workflow after M1-M6/M8 repairs; it is not a wrapper around local unit tests.

### Sandbox preconditions

- [ ] The exact accepted local commit is deployed only to `dogtrainersdirectory-dev` / disposable `dtd-sandbox` data; no connection, secret, provider action or email can touch production.
- [ ] Fixture trainer/owner/provider data is synthetic, scoped and disposable. Notifications use a contained test sink; Gemini evidence uses synthetic payloads only.
- [ ] Required match/context/intro/notification/provider/audit collections are identifiable and cleaned or irreversibly isolated after verification.
- [ ] Codex confirms sandbox health, database availability, correct isolated configuration and no public matching/billing/provider change outside the sandbox before scenario execution.

### Mandatory scenario acceptance

Every scenario must prove UI/API, relevant stored record(s), automation/fallback and `/ops` result as applicable.

1. [ ] Puppy/basic-manners owner receives a local, truthful eligible recommendation.
2. [ ] Multiple concerns plus in-home and method preference exclude incompatible trainer(s).
3. [ ] Ambiguous/`other`/`unsure` request produces clarification and no AI/candidate/token.
4. [ ] Fewer than three local candidates expands only to declared coverage and labels every expanded result.
5. [ ] Missing required capability evidence produces `no_confirmed_match`, not a manufactured card.
6. [ ] Stale, suppressed, disputed, revoked or unsupported projection is excluded before Gemini payload creation, including a stale stored-projection regression.
7. [ ] Exact `0.05` comparable-fit boundary permits the commercial tiebreak; an outside-band higher tier cannot move ahead.
8. [ ] Gemini timeout, rate limit, unavailable client and malformed output each produce the contract-selected deterministic degraded response and degradation record.
9. [ ] Immediate danger, urgent animal health, serious behavioural support and clarification routes follow their exact stop/continue/token/provider rules.
10. [ ] Trainer declaration correction, failed refresh and suppression invalidate later matchability while preserving unrelated valid capacity/audit history.
11. [ ] Consent rejection and privacy tests prove clean URLs, header-only context, no raw description/PII in records/read models and no stale context after a new match.
12. [ ] Matched enquiry proves actual test-sink delivery, retryable failure, bounded safe retry, terminal/suppressed state and no duplicate success.
13. [ ] The same ordinary fixture through configured Gemini and fallback meets the M4 material-agreement bar.
14. [ ] Unsupported/stale/out-of-vocabulary/paid-field declaration attempts are held/excluded and visible as an anti-gaming exception.
15. [ ] Urgent-provider correction/removal proceeds through evidence check, bounded review and truthful public status; unsupported request cannot reactivate a provider.
16. [ ] The four `/ops` recovery scenarios prove redaction, authentication, confirmation, idempotency and audit trace.

### M9 evidence and acceptance

- [ ] A scenario report maps every scenario to request/fixture IDs, expected/actual UI state, API response, persisted-record assertion, notification/fallback result, `/ops` assertion and sanitised capture.
- [ ] Codex independently reruns a proportionate subset that includes all prior blockers MP-001 through MP-005, all safety routes, one real Gemini parity case and the full enquiry lifecycle.
- [ ] All M1-M6/M8 criteria are `DONE`; M7 is `DONE` if enabled or recorded intentionally disabled; related findings are closed with evidence or validly superseded.

**M9 completion rule:** the matching pipeline works as one isolated, evidence-backed sandbox workflow, with no unresolved material requirement or unsupported completion claim.

## M10 — Separate production promotion gate

**Current status:** `OPEN`. M10 is outside developer-sandbox completion and requires explicit owner authority.

- [ ] M9 is `DONE` on one exact reviewed commit and remote CI is green for that commit.
- [ ] Owner explicitly authorises production promotion after receiving the complete sandbox/audit evidence bundle and exact release scope.
- [ ] Production runtime configuration, managed secret references, provider health/recovery path, feature posture and database migration plan are independently inspected without exposing secret values.
- [ ] A zero-traffic production canary is deployed; health/config/read-only matching safety smoke checks pass with no production owner data created and no real provider message sent unless separately authorised.
- [ ] Traffic promotion, if approved, is monitored through health/error and `/ops` evidence; rollback target and trigger are documented before promotion.
- [ ] Post-promotion verification proves public UI, API, persisted data, privacy boundary, deterministic fallback and `/ops` read model against production-safe synthetic or no-op checks.
- [ ] Any production provider activation, new credential, Maps enablement, billing/refund activation, retention change, email delivery to real recipients or destructive data operation has its own explicit authority and is not implied by M10.

**M10 completion rule:** production promotion is separately owner-authorised, reversible, observed and evidenced. It does not retroactively weaken sandbox acceptance or activate unrelated gated systems.

## Audit close-out checklist

Codex may declare the matching pipeline complete in the developer sandbox only when:

- [ ] M0-M6 and M8 are `DONE` under this document.
- [ ] M7 is `DONE` if enabled, otherwise recorded intentionally disabled.
- [ ] M9 is `DONE` with every mandatory scenario evidenced.
- [ ] Every matching-relevant current-state finding is closed with evidence or explicitly superseded by an owner decision.
- [ ] Documentation, tests, code, sandbox configuration, persisted data and `/ops` evidence agree on the same exact behaviour.

M10 remains a distinct production decision.
