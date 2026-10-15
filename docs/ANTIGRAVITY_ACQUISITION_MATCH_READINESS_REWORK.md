# DTD acquisition match-readiness: targeted rework and evidence response

## Status and intent

Keep the existing branch and commits `8d225b4` and `e60c830`. They contain valuable work: capability fact structures, normalisation, bounded AI candidate payloads, initial tests and backend health telemetry. **Do not revert, delete or redesign that foundation.**

Codex's independent audit does not accept the handoff as complete because several trust-critical paths are not connected. This is a narrow amendment package to make the existing work truthful, reachable and safe. Return one or more follow-up commits on top of `e60c830`.

Do not issue another downstream coordination brief. Implement and evidence the corrections below.

## Governing boundary

Acquisition owns reliable trainer facts. Matching later consumes a versioned, bounded projection. Acquisition must not select the owner-facing response for weak evidence, thin supply, ambiguity or AI degradation. Decision Contract v2 owns that choice.

The following remain locked:

- AI cannot invent or upgrade trainer capabilities.
- Paid tier, sponsorship, billing, reviews and marketing prose cannot enter eligibility or raw fit.
- Trainer declaration and authorised official-source facts are distinct, attributable evidence bases.
- Corrections, suppression, failed refresh and disputes must remove or limit matching capacity.
- A published profile is not automatically matchable.

## Findings to resolve

### R1 — Missing provenance is incorrectly promoted to a trainer declaration (P0)

**Observed:** `build_match_ready_projection()` treats a legacy profile with no `source_url` or `source_evidence_url` as trainer-declared. A direct reproduction showed that a published record with raw `specialties` and `service_formats`, but no capability record, provenance or declaration, returns `match_eligible: true`.

**Required correction:**

- Remove the implicit `(not source_url and not source_evidence_url)` declaration path.
- Legacy facts with no explicit source/declaration/confirmation evidence must remain unconfirmed and excluded from the projection.
- Tests may use an explicit test fixture basis; do not weaken production behaviour to support old tests.
- Preserve a clear reason code and `/ops` visibility for these records.

### R2 — OTP claim verification is incorrectly treated as capability confirmation (P0)

**Observed:** `/trainers/{id}/claim/verify` converts every existing capability fact, including `ai_proposed` facts, to `trainer_declaration` after email OTP verification. The current claim UI only proves control of the email; it neither displays nor obtains acceptance, correction or completion of each structured capability.

**Required correction:**

- Keep identity/ownership claim verification separate from capability confirmation.
- Add a trainer-facing structured capability confirmation/update step after successful claim or a protected equivalent flow. It must display prefilled values, support correction/removal and require an explicit confirmation of the structured declaration before the values gain `trainer_declaration` basis.
- The server must reject an attempt to promote facts solely because OTP claim verification succeeded.
- Record declaration basis, confirmation event/reference and timestamp per field.
- Cover cancellation, invalid values, partial confirmation and stale declaration paths.

### R3 — The real submission route cannot create the new capability declaration (P1)

**Observed:** `frontend/src/pages/Submit.jsx` sends free-text comma-separated `services` and `categories`; it does not collect the fields packaged by the new server code (`specialties`, `service_formats`, `life_stages`, `training_philosophy`, `serviced_suburbs`, `catchment_type`, delivery constraints).

**Required correction:**

- Add an accessible, mobile-usable structured capability declaration to the real trainer submission path.
- Use the canonical vocabulary and validation. Keep optional explanatory free text separate from the capability values.
- Explain, in plain language, that confirmed capability answers affect the owner requests for which DTD may consider the trainer.
- Do not make unrelated free text, marketing copy or tier data matchable.
- Add browser/component-level coverage for validation, successful submission and invalid/partial declarations.

### R4 — Capability invalidation is not connected to lifecycle events (P1)

**Observed:** `invalidate_trainer_capabilities()` exists but has no production call site. Correction, suppression, dispute and failed-refresh events do not currently update capability state.

**Required correction:**

- Trace the actual correction/removal, suppression/delisting, claim-dispute and refresh-failure paths.
- Wire field-level or whole-record invalidation into the applicable paths atomically with their lifecycle update.
- Preserve a reason, timestamp and audit record; never silently delete the evidence.
- A later valid correction or confirmation may create a new fact/version, but must not reactivate invalidated facts implicitly.
- Add integration tests through the real route/service boundaries, not only direct helper calls.

### R5 — Match-policy activation leaked into the acquisition package (P1)

**Observed:** `ai.match_trainers()` now filters candidates through the projection and returns an empty list when none remains. The current public `/match` path surfaces that result. This selects a weak-evidence owner outcome before Decision Contract v2 has selected and tested it.

**Required correction:**

- Do not choose or implement the owner-visible weak-evidence response in this package.
- Keep the capability projection available to matching, but isolate final request-specific eligibility and owner-response activation behind the future Decision Contract v2 boundary.
- If a temporary integration is essential, it must be disabled by default outside the developer sandbox and return explicit machine-readable diagnostic evidence without altering public owner behaviour. Do not invent a no-match, clarification or shortlist policy.
- Document the exact interface that Codex/Decision Contract v2 must consume: projection version, fact basis, freshness, validation, invalidation and reason codes.

### R6 — Evidence-basis and freshness rules have been prematurely locked (P1)

**Observed:** the implementation hard-codes 180/90/30-day TTLs, permits only `trainer_declaration`, and requires specialties or service formats. This excludes fresh, structured `official_source` facts, although approved target authority permits source-backed or trainer-confirmed facts. Per-concern minimum evidence remains Decision Contract v2 work.

**Required correction:**

- Preserve provenance and freshness computation, but move policy-sensitive allowed-basis, TTL and per-request minimum-evidence decisions into a clearly versioned, documented configuration/contract boundary.
- Do not make an unapproved operational default appear locked. If a safe temporary default remains necessary for local tests, label it provisional and keep it out of public activation.
- Return an evidence table distinguishing immutable data integrity rules from Decision Contract v2 policy inputs.

### R7 — `/ops` evidence is backend-only and its summary is inaccurate (P1)

**Observed:** the API returns `capability_health_summary`, but `Ops.jsx` does not render it. The aggregate query also counts stored `permitted_in_projection` flags rather than recalculating freshness/invalidation consistently, and checks `claimed` although the claim path uses `claim_status: "claimed"`.

**Required correction:**

- Render a concise owner-readable capability-health panel in protected `/ops`.
- Its counts must reflect the same effective projection logic used by the bounded interface; do not present stale or invalidated facts as eligible.
- Provide actionable, non-PII reason categories: missing declaration, AI-proposed/unconfirmed, stale, invalid, disputed, suppressed and contact/publication gate.
- Add API and frontend tests proving protected visibility and truthful counts.

### R8 — Evidence and documentation hygiene (P2)

**Required correction:**

- Re-run `git diff --check`; the current commit range has whitespace failures.
- Separate the acquisition implementation delta from unrelated matching-planning documents where practical. Do not rewrite established authority content merely to make the commit appear smaller.
- Reconcile DF-014 against current code. `reverify_listings()` currently preserves publication state and only suppresses known statutory revocation; if that satisfies the original finding, update the finding with precise evidence. If another path still grants state from AI confidence, identify it with code and a regression test.

## Required tests

Add and run tests that prove all of the following through real workflow boundaries:

1. A raw legacy record without provenance/confirmation never becomes matchable.
2. Email OTP claim alone never promotes any capability.
3. A trainer views, edits and explicitly confirms structured capability facts; only then do valid fields receive declaration basis.
4. Submission UI creates the declared fields and invalid/partial input is explicit.
5. A correction, dispute, suppression/delisting and failed refresh invalidate affected capability facts and their effective projection.
6. New confirmation creates a new valid fact rather than silently reviving old invalidated facts.
7. Marketing prose, reviews, paid tier, billing data and AI confidence never enter the bounded projection.
8. `/ops` shows effective, non-PII health/reason states consistent with projection logic.
9. The package does not alter the public owner match response for weak evidence before Decision Contract v2.
10. Existing relevant unit and frontend/component tests still pass.

## Constraints

- No remote push, PR, deployment, provider/configuration mutation, billing/auth change, production-data query or migration.
- No new external acquisition sources, Google Places/Maps, Search Grounding or generic scraping.
- No owner questionnaire, scoring, ranking, commercial ordering, Gemini fit design or urgent-support implementation.
- Keep existing commits. Amend with minimal follow-up commits only.

## Return format

Return an evidence handoff with:

1. Follow-up commit SHA(s) and exact changed files.
2. Finding-by-finding response to R1–R8: `DONE`, `PARTIAL` or `OPEN`, with direct code/test evidence.
3. Workflow trace for submission, claim confirmation, correction/suppression/refresh and `/ops`.
4. All test commands and unabridged pass/fail results.
5. Any remaining Decision Contract v2 inputs clearly labelled as open hypotheses, not implementation rules.
6. Explicit confirmation that no prohibited external or production action occurred.

Do not claim completion until all R1–R7 are `DONE`; R8 may remain separately recorded only if no behaviour or authority drift remains.
