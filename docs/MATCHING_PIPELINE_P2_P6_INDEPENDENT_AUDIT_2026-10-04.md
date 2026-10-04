# Matching pipeline P2-P6 independent audit — 4 October 2026

## Scope and boundary

This is Codex's independent local audit of Antigravity's cumulative matching implementation at commit `a167478592136bd4e0385f2c6dee3d0377c76222`, compared with the accepted P1 baseline `5161a2bfc14514b3525f313ae361c4c580b8f847`.

No code, deployment, provider configuration, billing, authentication configuration, production data or external provider record was changed by this audit.

## Evidence performed

- Reviewed the changed API, matching contract, Gemini adapter, urgent-provider service, owner and trainer UI, `/ops` controls, and matching tests.
- Ran `./.venv/bin/pytest backend/tests/test_matching* -q`: **145 passed**.
- Ran frontend tests: **10 suites / 40 tests passed**; production build passed.
- Ran the supplied local Playwright visual script. It passed its mocked desktop/mobile flows and produced screenshots. It does not exercise the profile-to-enquiry handoff or a real API.
- Ran `git diff --check 5161a2b..HEAD`: **failed** on four trailing-whitespace lines in `scripts/verify_matching_visuals.py`.
- Rechecked the urgent-provider facts against current first-party pages. The Lost Dogs' Home page currently gives `(03) 8379 4498`, Monday-Friday `8:10 am-7 pm`, Saturday `9 am-4 pm`, Sunday/public holidays closed, and says to call for a pet emergency. It does not support the stored phone or hours. The U-Vet Werribee exclusion is correct: the University says it permanently closed on 24 December 2022.

Passing local tests are evidence for their covered assertions only. They do not override the source-path defects below or establish sandbox/provider readiness.

## Package classification

| Package | Classification | Evidence-backed position |
| --- | --- | --- |
| P2 / M3 eligibility | `PARTIAL` | Structured request, fail-closed projection and deterministic geography/presentation exist. However `/match` trusts any stored document with `projection_version` instead of recomputing the projection, so a stale/invalidation-changed stored projection can remain matchable. |
| P3 / M4 Gemini fit | `PARTIAL` | A real `GeminiMatchingAdapter`, allow-list, 5-second timeout, typed degradation and deterministic fallback now exist and pass mocked tests. A real configured provider and same-fixture Gemini/fallback sandbox parity are not verified. |
| P4 / M2/M5 owner path | `PARTIAL` | The structured form, clean `/t/:id` link, header token transport and no public score/tier are implemented. A new resultless/triage match does not clear an older session token, and the legacy direct `/intros` endpoint still accepts client-supplied `match_id`. |
| P5 / M5/M6 safety and urgent support | `PARTIAL` | Four deterministic states and separate provider records exist. The only static provider has incorrect official facts; correction acceptance can mark a provider `current` without independently verified official evidence; no freshness/recheck job is evidenced. |
| P6 / M8 operations | `PARTIAL` | Protected, redacted matching read model and bounded endpoints exist. The follow-up retry endpoint writes `delivered` without delivering anything; it is not a retry. |
| M9 sandbox acceptance | `OPEN` | Local mocked tests and mocked visual screens are not the isolated developer-sandbox acceptance required by the roadmap. |

## Blocking repair findings

### MP-001 — Stored match projections can bypass current freshness and invalidation evaluation

`backend/server.py` uses a stored trainer document directly whenever it has `projection_version`. The fresh projection function re-evaluates capability basis, confirmation age and invalidation; the reused document does not. This can let a previously materialised but now stale or invalidated capability reach eligibility, AI and presentation.

**Required repair:** rebuild the match-ready projection from the trainer source record for every match, or introduce a separately versioned projection with an explicit, verified freshness/invalidation gate that is evaluated at query time. Add an integration fixture proving a stale persisted projection is excluded before Gemini receives candidates.

### MP-002 — Matched enquiry delivery is recorded without a delivery attempt

`POST /match/follow-up` inserts an introduction with `delivery_state: delivered` but does not call `notifications_service.notify_trainer_new_intro`. The P6 retry endpoint similarly changes any retryable/pending record to `delivered` without notification dispatch. This creates false operational records and leaves the owner believing an enquiry was sent.

**Required repair:** use the same notification/service contract as direct enquiries, persist the actual attempt result as `pending`, `delivered`, `retryable_failure`, `terminal_failure` or `suppressed`, and make the operator retry call the real idempotent dispatch. Add successful, failed-then-retry, suppressed and no-duplicate tests.

### MP-003 — Urgent-provider record is not currently factual

The static Lost Dogs' Home record publishes the wrong phone and hours. Its current official page should be the sole source for the exact public facts. The correction-review endpoint also permits an operator to restore a record to `current` based on a public request without recording an independently checked official source.

**Required repair:** correct the static record to the official page; preserve source URL and retrieval/check timestamp; require documented official-source verification before any `current`/unsuppress action; keep unsupported providers held or suppressed. Add a freshness/recheck test and a correction-acceptance test that proves unverified submission alone cannot reactivate a listing.

### MP-004 — Context and attribution boundaries remain incomplete

The browser retains a prior opaque context token after a later new match returns no handoff token. The direct `/intros` schema still accepts `match_id`, allowing a client to attach an ordinary enquiry to an arbitrary event outside the protected match-context flow.

**Required repair:** clear the session token at the start of every new matching submission, then store only the newly returned valid token; reject `match_id` on direct `/intros` (or ignore it server-side and ensure it is never persisted); add regression tests for both paths.

### MP-005 — Public trust claims and config-outage fallback are not reconciled

The matching page still describes a “vetted network” and urgent card calls the provider listing “Verified”; current evidence supports only specific declared, reviewed or official-source facts. Also, Home defaults a failed/incomplete `/config` request to live matching. That can expose matching when runtime state is not confirmed.

**Required repair:** apply the evidence taxonomy across matching copy and fail closed or present a truthful unavailable/waitlist state when configuration cannot be obtained. Add focused copy and config-failure tests.

## Non-blocking audit hygiene finding

`scripts/verify_matching_visuals.py` contains trailing whitespace and hard-codes an external Antigravity artifact directory. Its pass is useful as a mocked UI smoke test, but it is not a portable, real-end-to-end verification artifact. Clean the whitespace, write temporary artifacts to a controlled ignored location and add a profile/enquiry visual/API journey.

## Remaining evidence gates after repair

1. Re-run the P2-P6 focused tests with new negative fixtures for MP-001 through MP-005.
2. Run the 16 mandatory scenarios against a disposable developer-sandbox dataset, including a configured-but-safe Gemini parity case and a simulated provider failure/retry.
3. Inspect persisted match, context, intro, provider-correction and `/ops` records for redaction and truthful state transitions.
4. Independently verify the protected operator actions and owner mobile/desktop profile-to-enquiry journey.
5. Only then mark M1-M6/M8/M9 `DONE`; production remains M10 and requires separate owner authority.
