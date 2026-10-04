# Matching pipeline `c7afb07` independent audit — 5 October 2026

## Scope and decision

This is Codex's independent local re-audit of Antigravity candidate commit `c7afb0752267332c0f4be30b1bd092ab89c63fb7`, against the prior cumulative implementation `a167478592136bd4e0385f2c6dee3d0377c76222` and the active [completion criteria](MATCHING_PIPELINE_REMAINING_COMPLETION_CRITERIA.md).

**Decision: `PARTIAL` — do not advance to M9 developer-sandbox acceptance.** The commit contains valid, retained repairs. It must receive a narrow follow-up rework for the material items below; it does not need a redesign or rollback.

No code, deployment, provider configuration, billing, authentication configuration, production data or external provider record was changed by this audit.

## Accepted local repairs

| Prior finding | Classification | Independent evidence |
| --- | --- | --- |
| MP-001 stale stored projection | `DONE` locally | `/match` now rebuilds `build_match_ready_projection(doc)` for every candidate. The new stale-confirmation and cancelled-ABN tests pass. |
| MP-004 stale browser context/direct attribution | `DONE` locally | Home removes `d_match_context_token` before a dispatched request; direct `/intros` rejects client `match_id`; matching follow-up derives attribution from the verified context token. |
| MP-005 config fail-closed/home-card wording | `PARTIAL` | Home starts disabled and handles `/config` failure as unavailable. The matching card no longer says "vetted network" and the urgent-card label is now evidence-specific. Broader public trust copy remains unsupported. |
| MP-003 stored Lost Dogs' Home facts | `DONE` locally | The static record now uses `(03) 8379 4498`, stated weekday/Saturday hours and official provider URL; the record is freshness-calculated. |

## Blocking rework findings

### MP-002R — A provider-not-configured notification is falsely recorded as delivered

`notifications._send_with_retry()` returns `status: "skipped", reason: "no_resend_api_key"` when no provider key exists. Both `POST /match/follow-up` and the protected retry endpoint then map that result to `delivery_state: "delivered"`.

This is not delivery evidence. It violates M5/M8's meaning of `delivered`, makes the owner/operator record false, and its new unit test currently treats the no-key test shortcut as success. The direct-enquiry path also retains its older misleading delivery-state handling and should be brought under the same truthful state mapping in this repair.

**Required repair:** map no configured provider to a truthful non-delivered state (normally `retryable_failure`, or a separately documented non-delivery state if policy requires it); preserve the concrete reason and attempt count; make owner and `/ops` messaging truthful; and use one shared mapping for direct and matched enquiries. Add negative tests for missing key, provider rejection/transport failure, suppression, missing recipient and successful provider acceptance.

### MP-002S — Follow-up and retry idempotency is only sequential, not concurrency-safe

The matched flow checks for an existing intro and then inserts. The only unique index is `idempotency_key`; there is no uniqueness/duplicate-key recovery for `composite_idempotency_key`. Two concurrent requests with different client keys can therefore create two matched intros and send twice. The retry endpoint similarly reads state, dispatches, then updates without atomically claiming the retry; concurrent operator requests can dispatch twice.

**Required repair:** enforce a unique match composite key, handle duplicate-key recovery deterministically, and use an atomic claimed/in-progress state or equivalent compare-and-set mechanism before retry dispatch. Add parallel/concurrency fixtures proving one outbound attempt for each logical enquiry/retry.

### MP-003R — Urgent directory returns an unrelated provider when local coverage is absent

`get_active_urgent_providers(..., suburb="Werribee")` returns the North Melbourne Lost Dogs' Home record when no Werribee coverage matches. Codex reproduced this directly in the local candidate. That contradicts the contract: until a region has a current entry, DTD must say it has no current local listing rather than imply coverage.

**Required repair:** return only exact/evidence-backed service-area matches for a locality, otherwise return an empty result plus the approved no-local-coverage state/copy. Add exact-match, unmatched-suburb, stale-record and DB/static-fallback tests.

### MP-003S — Official-source correction verification is operator assertion, not captured evidence

The correction-review endpoint accepts any non-aggregator HTTP(S) URL plus a caller-supplied boolean, then restores the provider to `current`. It does not establish that the URL is first-party or record a verifiable evidence outcome beyond the operator assertion.

**Required repair:** require the evidence record defined by M6 (source URL, reviewed timestamp, reviewed field values/evidence reference and responsible operator), validate first-party authority under a bounded rule, and keep a record held when that evidence is absent. This need not introduce scraping or external provider calls.

### MP-003T — `/ops` can report stale urgent records as current

The public retrieval path recomputes freshness, but the `/ops` fallback and DB summary count stored `freshness_state` values. A record can exceed its 90-day check date while `/ops` still reports it as current. The static fallback likewise does not present an explicit no-local-coverage condition.

**Required repair:** calculate the read model from the same freshness function used for public display, expose actionable stale/coverage-gap counts without provider-owner data, and add expiry tests.

### MP-005R — Unsupported global trust claims remain public

The matching card was improved, but `About`, `HowItWorks`, `Trust` and `Terms` still promise universal "verified" or manual checks of credentials, insurance and affiliations. The current evidence taxonomy does not support those universal claims.

**Required repair:** replace these with the scoped declared, claimed, ABR-evidenced, reviewed or official-source labels that the applicable record can prove. Add a focused public-copy regression check. This is a matching trust dependency, not a request to alter trainer fit rules.

## Audit-hygiene gap

`scripts/verify_matching_visuals.py` is now portable and clean, but it still stubs the old Lost Dogs' Home phone, hours, name and source URL. Its screenshot therefore renders obsolete emergency information while reporting success. Update the fixture from the canonical provider record or run the test against a local API fixture generated from that record; keep it labelled as mocked visual evidence, not end-to-end proof.

## Validation performed

- `git diff --check a167478..c7afb07`: passed.
- `./.venv/bin/pytest backend/tests/test_matching_mp_repairs_unit.py -v`: 13 passed.
- `./.venv/bin/pytest backend/tests/test_matching*.py -q`: 158 passed.
- `./.venv/bin/pytest backend/tests/test_*_unit.py -q`: 442 passed.
- `npm test --prefix frontend -- --watchAll=false`: 10 suites / 42 tests passed.
- `npm run build --prefix frontend`: passed.
- `./.venv/bin/python scripts/verify_matching_visuals.py`: passed as a mocked UI smoke test only; rendered urgent data was stale because its mock was stale.
- Direct local probe: the urgent-provider lookup for `Werribee` returned `urgent_care_lost_dogs_home_north_melbourne`, confirming MP-003R.

Passing tests demonstrate covered behavior only. Several currently encode the no-provider-key state as `delivered`, so they cannot close MP-002R.

## Package status after this audit

| Package / milestone | Classification | Reason |
| --- | --- | --- |
| M1 capability truth | `PARTIAL` | Query-time projection repair is accepted locally; full onboarding, lifecycle and sandbox criteria remain. |
| M2 owner input/privacy path | `PARTIAL` | Config fail-closed and context correction are accepted locally; sandbox and whole-site trust-copy evidence remain. |
| M3 deterministic eligibility/presentation | `PARTIAL` | Existing implementation/tests remain local-only; geographic trainer flow needs sandbox evidence. |
| M4 Gemini/fallback | `PARTIAL` | Local adapter/fallback evidence exists; configured safe-Gemini parity is unverified. |
| M5 enquiry/follow-up | `PARTIAL` | Protected attribution and real dispatch invocation exist, but truthful no-provider state and concurrency safety are unresolved. |
| M6 urgent support | `PARTIAL` | State machine, separate records and corrected stored facts exist, but locality, verification-evidence and `/ops` freshness requirements remain. |
| M7 Maps/Places | `OPEN` | Optional surface is not implemented and has not yet been recorded intentionally disabled. |
| M8 operations | `PARTIAL` | Bounded controls exist, but delivery and urgent-freshness telemetry are not truthful in all degraded paths. |
| M9 sandbox acceptance | `OPEN` | No approved developer-sandbox deployment, fixture run, safe provider dispatch, real Gemini parity or persisted-record inspection. |
| M10 production | `OPEN` | Separate owner-authorised gate; no action taken. |

## Next gate

Return a focused local rework commit closing MP-002R/S, MP-003R/S/T, MP-005R and the stale visual fixture, with the exact negative/concurrency tests listed above. Codex will then re-audit the diff before any sandbox action. Provider configuration, actual email dispatch, deployment, billing, authentication and production changes remain out of scope.
