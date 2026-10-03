# Codex Independent Audit — Matching P1 Contract Fixtures and Parity Harness

**Audited commit:** `d42b5521138833ae0be3f9c043daf5d1a48e296a`  
**Base:** `ce14f4eeba6c675fce0997385800a8ec543d9ba9`  
**Classification:** `PARTIAL` — useful local-only foundation; not accepted for P2.

## What is accepted provisionally

- The commit adds a versioned contract module, a fixture builder and a 16-scenario suite without importing them from the current public API or frontend. It has not changed live matching behaviour.
- Fixtures invoke `build_match_ready_projection()`, and the constants cover the v2 policy values: 0.60 qualification, 0.05 comparable-fit band, zero outcome weight, 15-candidate bound, three returned cards, five-second provider limit, and 30-day record retention.
- Independent checks passed: 34 P1 tests, 318 backend unit tests and the frontend production build.

## Rework required before P1 acceptance

### R1 — make the contract response schema actually closed

`DecisionResponseV2` accepts arbitrary `decision_state` and top-level `reason_codes`; a valid candidate reason code also allows unsupported explanation text such as a guaranteed outcome. Use enum-typed state/scope and controlled reason-code vocabularies at every response level. Add a model-output validator that rejects candidate IDs outside the eligible pool and explanations not grounded in the supplied match-ready facts. A schema must not make a model claim true merely because it is syntactically valid.

### R2 — make the reference eligibility logic fail closed

Direct evaluation accepts a candidate with `life_stages=[]` and `serviced_suburbs=[]` if the profile's physical `suburb` equals the request locality. This violates Contract v2: required life-stage support and declared service-area coverage must be present; a listing suburb is not a declared service area. Require the relevant life-stage fact and exact `serviced_suburbs` coverage locally, with only declared `greater_melbourne` catchment available after the documented expansion condition. Add direct regressions for each missing fact.

### R3 — repair fixtures so they can expose, rather than mask, missing facts

The builder uses `value or default`, so an explicit empty life-stage or service-area list becomes a positive default. Preserve `None` as “use the ordinary fixture default” and preserve an explicit empty list. Use the P0 canonical delivery-constraint fields only: `in_home_available`, `facility_available`, `travel_distance_km` and `notes`; do not add ignored radius, fee-policy or alternate-notes fields. Test fixtures must exercise the actual projected shape.

### R4 — turn nominal parity checks into executable adapter parity

The current Gemini test handwrites one response then compares only its state and first candidate; timeout/429/malformed tests call the fallback directly. Add a small test-only model-adapter seam that is invoked for normal, timeout, quota/rate-limit, unavailable and malformed-output cases. Across the unambiguous Section 9 scenarios, assert the same triage outcome, eligible/qualified candidate set, state, scope and reason-code categories as the fallback. Keep real `ai.py`/Gemini integration for P3.

### R5 — keep premature workflow implementation non-runtime

The new module already contains full triage, scoring, presentation and public safety-copy logic, which are P2, P3 and P5 responsibilities. It may remain only as a test/reference oracle after R1–R4, clearly non-runtime and without public copy/provider claims. P2/P3/P5 must still independently integrate and verify their production paths; do not treat this commit as delivering those packages.

### R6 — clean the submitted diff

`git diff --check ce14f4e..d42b552` reports six trailing-whitespace lines and a blank line at EOF. Return a clean exact commit.

## Audit evidence and boundary

- Direct probe: `check_candidate_eligibility()` returned `eligible` for a projected candidate with empty life stages and empty declared service area solely because its profile suburb matched `Richmond`.
- Direct probe: arbitrary decision state and top-level reason codes, plus “Guaranteed best …” explanation copy, were accepted by `DecisionResponseV2` when the candidate reason code was otherwise valid.
- No provider, data, billing, authentication, deployment, sandbox, production or remote-Git mutation was performed. `ENABLE_MATCH_READY_PROJECTION_FILTER` remains disabled and P0 remains the accepted acquisition prerequisite.

## Return package

Rework only P1 on `feature/matching-implementation`. Preserve the useful fixture foundation; do not delete it wholesale and do not start P2. Return one exact commit, changed files, `git diff --check`, focused/full test results, and a concise mapping of R1–R6 to tests. Codex will then perform a new independent audit before authorising P2.

## Resolution of Antigravity's stated assumptions

These are implementation directions, not new owner-decision requests.

1. **Heuristic weights:** do not treat the proposed `0.40/0.15/0.15/0.15/0.15` split as accepted policy. P1 may test a reference response, but must not establish a production scoring formula. P3 will define one versioned, evidence-backed deterministic fallback table and its boundary fixtures before runtime integration.
2. **Concern-to-specialty mapping:** do not use a broad default mapping for `other` or `unsure`, and do not let general `fear_anxiety` stand in for the explicit `separation_anxiety` specialty. Where a request cannot resolve to a documented canonical concern, return `needs_clarification`; it must not qualify a generic trainer through a speculative mapping. P3 owns the complete versioned table, with one-to-one and permitted alternative mappings explicitly tested.
3. **Safety keywords:** P1 must not introduce production triage keyword policy or public safety copy. Keep state-level fixtures only. P2/M6 will implement the conservative deterministic classifier, approved copy and urgent-directory evidence together; substring lists alone are not sufficient safety policy.
4. **Fixture supply:** use isolated, purpose-built candidate pools per scenario. Do not inflate a shared pool with duplicate-like trainers merely to suppress the documented thin-local-supply branch.
5. **`limited_local_results`:** use it only when fewer than three local eligible candidates caused expansion and at least one expanded candidate is presented. If one or two local candidates qualify and no expanded candidate does, use `recommendations` with the actual count; do not claim an expanded search result.
6. **PII sanitisation:** remove email addresses, phone numbers, URLs and address-like data before model use or storage; do not retain redaction-marker tokens in the matching payload. Normalize remaining whitespace. Tests should prove the sensitive value and marker are both absent.

## Re-audit of `b0b9d6bf1a13f330c9a5bd76ece3d4aea6dada0a`

**Classification:** `PARTIAL` — P1 remains unaccepted; do not begin P2.

### Accepted improvements

- The range from `ce14f4e` is one local commit and `git diff --check ce14f4e..b0b9d6b` is clean.
- The response state/scope and card reason-code enums are now closed. Explicit empty life-stage and declared-service-area facts are testable, and the reference local eligibility gate no longer treats a profile suburb as service coverage.
- The fixture builder now preserves explicit empty values, uses the P0 delivery-constraint keys, and the scenario pools are isolated.
- Independent verification passed: 50 P1 tests, 334 backend unit tests, 36 frontend tests and the frontend production build. The new module remains unimported by runtime paths.

### Remaining rework required

### R7 — enforce the input/privacy contract rather than relying on coercion

Direct probes show `MatchConsentIn(match_processing="yes", terms="true")` is accepted as both booleans, and a request omitting `service_format` and `method_preference` is silently assigned `any` and `no_preference`. Contract v2 requires explicit boolean consent and explicit format/method choices. Use strict input types and remove those defaults. The sanitizer also leaves `12 Smith Street, Richmond` intact despite the contract requiring address-like data to be stripped before model/storage use. Define and test a bounded address-redaction rule.

### R8 — finish concern/clarification policy

The mapping still permits `fear_anxiety` alone to qualify a `separation_anxiety` request, contrary to the prior direction. Make separation-anxiety support explicit. Also, an `other` request with a sufficiently long description currently becomes `no_confirmed_match`, not `needs_clarification`, because its mapping is empty. Until a request has an explicit canonical concern, it must remain in clarification; free text cannot choose a specialty mapping.

### R9 — make factual-explanation validation constructive and complete

The validator accepts unsupported statements such as “This trainer has twenty years experience and is available today.” It checks only selected words, so it cannot establish that an arbitrary model sentence contains only supplied facts. Replace the partial keyword screen with a structured allowed-fact/explanation-template mechanism: the candidate ID, reason codes and permitted projected facts select the rendered statement. Test unsupported availability, experience, accreditation, location, outcome and personality claims. Remove the reference engine's unsupported "verified expertise" wording.

### R10 — make parity a genuine adapter test and retain P1 scope

Normal-mode `GeminiStubAdapter` simply calls the deterministic reference engine, so its parity assertion is tautological. Its degradation modes likewise call fallback directly rather than exercising a provider-like failure through one adapter boundary. Produce a contract-shaped stub response independently, validate it against the deterministic eligible-pool/fact rules, and route raised timeout/rate-limit/unavailable/malformed exceptions through the one fallback wrapper.

The module also still embeds triage keyword policy and public emergency/urgent-care copy. P1 may retain state fixtures, but must not establish production triage policy or public safety copy; move that material out of the P1 reference until P2/M6. Finally, expansion must be triggered by fewer than three **local eligible** candidates, as Contract v2 specifies, rather than fewer than three locally scored candidates.

### Return package

Rework only R7–R10 on `feature/matching-implementation`. Preserve the accepted fixture and fail-closed-gate work. Return one amended/local commit, changed files, clean diff output, focused/full test results and direct test evidence for every case above. No P2, runtime integration, deployment, provider, data, billing, auth or remote-Git action is authorised.

## Re-audit of `3882bd2ecafc286bb1c5b3868e0108014d4792f5`

**Classification:** `PARTIAL` — substantial P1 progress, but P2 remains blocked.

### Accepted improvements

- Mandatory consent is now strict; format and method are required; `other`/`unsure` produce clarification; separation-anxiety matching requires the explicit specialty; and the sanitizer covers the supplied email/phone/URL/address/PO-box cases.
- P1 now uses explicit triage fixture states instead of static emergency keyword sets and public emergency copy. The thin-supply trigger is correctly based on local eligible count.
- The returned range is one clean local commit from `ce14f4e`, still unimported by public runtime paths. Independent checks passed: 59 P1 tests, 343 backend unit tests, 36 frontend tests and a production frontend build.

### Remaining rework required

### R11 — close every machine-readable boundary

`dog_age_months="4"` is coerced to `4` and `dog_age_months=True` becomes `1`; a card `match_score="0.9"` and response `degraded="false"` are also coerced. Use strict numeric/boolean types for all contract fields where the schema requires numbers or booleans, including the bounded dog age, score and degraded state. Make `policy_version` server-owned or constrain it to the exact active contract version so model output cannot select an arbitrary policy.

### R12 — make explanation truthfulness structural, not an expanding blacklist

The current checker still accepts unsupported claims such as “has a private two-acre training field” and “has won local awards for excellent results.” The deterministic generator is useful, but model-shaped output is not required to match it. Restrict accepted candidate explanations to deterministic rendering from candidate ID, permitted reason codes, search scope and supplied projected facts (or replace free-text model explanations with structured explanation facts and render them server-side). Add regressions for unsupported facilities, awards/reviews, prices, availability, credentials, outcomes, personality and location claims.

### R13 — repair adapter scope and failure semantics

For a valid `3067` (Abbotsford) request with a trainer declaring `Abbotsford`, deterministic reference returns local recommendations but normal adapter execution falls into degraded fallback. The adapter compares raw postcode text against suburb names when selecting card scope. Pass canonical locality/scopes from deterministic eligibility into the adapter and add postcode parity fixtures.

The fallback wrapper catches `Exception`, so an arbitrary programming error is silently represented as model degradation. Catch only defined provider, parsing and contract-validation errors; unexpected defects must propagate to the test/observability path. Add a regression using an injected unexpected exception.

### R14 — keep P1 state-only copy

Remove the remaining unsupported owner-facing “certified specialist” clarification prompt from the P1 reference module. P1 may assert states and structured reason codes; approved public copy belongs to its later owner-journey and urgent-support packages.

### Return package

Rework only R11–R14 on `feature/matching-implementation`; preserve the accepted P1 work. Return one amended/local commit, clean diff output, focused/full test results and direct regression proof for every point above. No P2, runtime integration, provider, data, deployment, billing, authentication or remote-Git action is authorised.
