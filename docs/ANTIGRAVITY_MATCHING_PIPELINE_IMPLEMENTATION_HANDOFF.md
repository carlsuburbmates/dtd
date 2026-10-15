# Antigravity Handoff — Owner-to-Trainer Matching Pipeline

**Prepared by:** Codex matching-pipeline session
**Scope:** local implementation only, in staged packages. This is the execution handoff and acceptance contract for `DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md`.

## Why this work is needed

The current public route is an earlier diagnostic matcher: it takes unbounded free text and optional suburb; directly queries the trainer collection; falls back to all Greater Melbourne trainers without disclosure; sends a raw description to Gemini; gives fallback candidates a `0.40` baseline without a capability match; applies a default outcome uplift; and puts the description in a trainer-profile URL. Its current capabilities do not satisfy the targeted matching pipeline.

The target is AI-assisted fit only after deterministic eligibility, with paid-neutral raw fit and deterministic presentation. Trainer matching capacity comes from the acquisition/onboarding match-ready projection, not profile prose.

## Non-negotiable boundaries

- Work locally on isolated branches. Do not push, deploy, change Cloud Run/Scheduler, mutate providers, enable billing/authentication, create credentials, or modify production/sandbox data.
- Preserve `0.05` commercial tiebreak behaviour exactly. Commercial fields never enter eligibility, fit, prompts or fallback scores.
- Do not expose owner descriptions or opaque tokens in URLs, analytics, trainer profiles or `/ops`.
- Do not create a manual-match or untracked override tool.
- Do not make veterinary, clinical, legal or behaviour-treatment claims. Do not build the optional Maps/Places surface.
- Return one package at a time with commit SHA, changed files, tests/results, migrations/data effects, residual risks and exact roadmap/finding IDs claimed addressed. Await Codex audit before the next package or any environment advancement.

## First: repair the inherited acquisition dependency (P0)

The branch head `b3aa7fd` contains useful match-readiness work but is not accepted as-is. Make this a narrow acquisition remediation package before matching cutover:

1. Remove or quarantine `POST /api/oversight/jobs/trainer-ingest` and its `/ops` trigger. `/ops` remains evidence-led/read-only; live acquisition scheduling is not established by repository tests.
2. Revert unsupported live-scheduler/manual-run assertions in `docs/DTD_CURRENT_STATE.md` and `docs/specs/ACQUISITION_AND_INGESTION.md` to evidence-based wording. Do not call a Cloud Scheduler or production runtime verified without independently authenticated control-plane evidence.
3. Require and validate the trainer claim session for `GET /api/trainers/{id}/capabilities/prefill`; do not accept an unused header as authorisation.
4. Make the trainer confirmation UI send every matchable declared field: specialties, formats, life stages, philosophy, serviced suburbs, catchment and delivery constraints.
5. Ensure source-refresh invalidation recognises `source_evidence_url` as well as legacy source fields.
6. Keep match-ready projection cutover disabled until the matching packages below pass. Documentation must say that the foundation exists but active matching is not yet strict.

Acceptance: focused claim/auth, projection, invalidation and Ops tests; no mutation route remains; no unsupported live assertion remains. This package addresses acquisition dependency defects, not the matching roadmap itself.

## P1 — Contract fixtures and test harness (M0; DF-018, DF-019, DF-021, DF-022, DF-023)

Implement `docs/specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md` without changing its decision boundaries. Create a fixture/data-builder module and test matrix that names expected triage state, eligible IDs, decision state, reason codes and search scope for every section-9 fixture. Add a Gemini-stub versus deterministic-fallback parity harness.

Do not yet change public responses except contract/schema compatibility scaffolding. Make policy values versioned constants/configuration, not scattered literals. Existing tests may be updated only where they encode superseded diagnostic-matcher behaviour.

Acceptance: fixture suite fails if an eligible candidate, reason-code category, decision state, expansion disclosure, privacy boundary, or parity rule drifts.

## P2 — Deterministic eligibility and match record (M2/M3; DF-018, DF-019, DF-022, DF-026)

Replace the `InstantMatchIn` free-text contract and `/api/match` pool selection with the v2 request. Reuse canonical suburb services and `build_match_ready_projection()`; do not read raw capability fields as a fallback. Add deterministic pre-AI triage and eligibility. Implement local-then-expanded declared-service-area search, labelled `search_scope`; do not infer radius/distance.

Persist only the v2 sanitised match record and consent/retention metadata. Issue an opaque, expiring context token stored hashed server-side. Add request throttling against a non-reversible key. No raw behaviour description goes in a URL, match event, audit event or analytics record.

Acceptance: validation, regex-safety, locality, consent persistence, retention metadata, rate-limit, projection freshness/suppression, local/expanded/no-confirmed-match tests. A non-projected or stale record never reaches Gemini.

## P3 — Fit, fallback and presentation (M3/M4; DF-019, DF-023, DF-026)

Refactor `backend/services/ai.py` and the current `/match` orchestration to consume the eligible projection only. Replace list-only model output with the v2 decision schema and restricted reason-code vocabulary. Implement the deterministic score/qualification algorithm from v2; remove the unconditional `0.40` fallback and all outcome-score contribution. Enforce five-second provider timeout and sanitised degradation records.

Apply the existing exact `0.05` commercial rule only after raw final fit; record raw fit and display order separately. Stable non-commercial ID resolves equality. Never decorate recommendations with pricing before fit/presentation is complete.

Acceptance: paid-field non-influence, exact boundary and outside-band tests; same eligible pool in Gemini/fallback; timeout/rate-limit/malformed/provider-unavailable tests; no unsupported explanation fact; all v2 fixture parity tests.

## P4 — Owner journey, profile handoff and follow-up (M2/M5; DF-015, DF-016, DF-017, DF-020)

Replace Home's two-field match form with the mobile-first v2 questionnaire and all distinct decision/triage/degraded states. Preserve only non-sensitive in-progress values in session. Render factual cards with actual service format/area and expanded-search disclosure. Make the trainer profile retrieve match context through the opaque session token/header, not `?q=` or a raw description query parameter.

Require separate contact-release consent before enquiry. Repair the follow-up lifecycle so delivery, retryable failure, backoff, terminal failure and suppression are explicit and idempotent. Add protected, redacted `/ops` evidence rather than routine manual controls.

Acceptance: mobile and desktop browser journeys, keyboard/accessibility states, no URL/raw-description inspection, profile/enquiry consent tests, failed-then-retry follow-up test, and `/ops` redaction/state tests.

## P5 — Urgent support directory and triage (M6; DF-024)

Implement only after P1-P4 acceptance. Add a separate urgent-provider data model, official-source provenance, freshness, correction/removal and protected Ops evidence. Use only approved route state/copy from the v2 contract. Do not make coverage or availability claims without current provider-authored evidence. Keep user-initiated Google Maps/Places work out of scope.

Acceptance: triage bypass, stale/absent provider coverage, correction/suppression, source provenance, redacted Ops and public mobile/desktop tests. Provide the proposed initial source list for Codex review before any data import.

## P6 — integrated acceptance (M8/M9; DF-017, DF-022 through DF-026)

Complete matching-specific Ops summaries and run the full isolated-data sandbox matrix. Do not call a local test result or branch build a deployment. Prepare a concise evidence handoff for Codex independent audit covering UI/API/records/automation/fallback/Ops/privacy and all fixture IDs.

## Explicitly deferred

- M7 Google Maps/Places urgent discovery: disabled; requires fresh terms/attribution/data-retention review and separate owner-approved implementation package.
- Outcome score use in fit: disabled until a later accepted evidence and fairness policy.
- Any provider discovery/import, live runtime configuration, provider contact, production/sandbox deployment or billing/authentication change.
