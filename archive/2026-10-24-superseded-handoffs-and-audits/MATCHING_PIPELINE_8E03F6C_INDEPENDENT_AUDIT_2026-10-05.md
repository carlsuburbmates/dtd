# Independent audit — matching repair `8e03f6c` (5 October 2026)

**Candidate:** `8e03f6c29c43ad69d93edcb9a94414ec633fe128` on `feature/matching-implementation` (parent `c7afb07`).

**Decision:** `PARTIAL` — do not advance this commit to the developer sandbox yet. The delivery and urgent-routing repairs are accepted locally, but the public-trust-copy finding is not fully closed.

## Evidence independently checked

- `git diff --check c7afb07..8e03f6c` passed; the candidate working tree was clean.
- `backend/tests/test_matching_mp_repairs_unit.py -v`: 32 passed.
- `backend/tests/test_matching_p6_integrated_acceptance_unit.py -v`: 16 passed.
- `backend/tests/test_*_unit.py -q`: 461 passed.
- `npm test --prefix frontend -- --watchAll=false`: 10 suites / 43 tests passed.
- `npm run build --prefix frontend`: passed.
- The urgent-provider visual fixture completed with the corrected Lost Dogs' Home information and an explicit mocked-evidence notice.

## Accepted local repairs

| Finding | Result | Evidence reviewed |
| --- | --- | --- |
| MP-002R | `DONE` locally | Notification outcomes now distinguish delivered, retryable failure and terminal failure; a missing provider key is no longer recorded as delivered. |
| MP-002S | `DONE` locally | Composite idempotency and a leased compare-and-set retry path prevent duplicate matched-intro dispatch under normal concurrent requests. |
| MP-003R | `DONE` locally | Urgent-provider lookup returns no local providers when the requested locality is not covered; the response declares `no_local_coverage` rather than falling back to a North Melbourne listing. |
| MP-003S | `DONE` locally | Urgent-provider corrections require retained official-source evidence before approval. |
| MP-003T | `DONE` locally | `/ops` derives urgent-provider freshness at read time rather than presenting stale records as current. |
| Urgent visual fixture | `DONE` locally | The fixture no longer uses the incorrect emergency listing and visibly marks its data as mocked. |

## Remaining blocker — MP-005R

The new neutrality regression test scans only a fixed subset of page files. It therefore passes while publicly rendered copy still overstates DTD's evidence model:

- `frontend/src/components/PublicChrome.jsx`: “Reviewed trainers for Melbourne”.
- `frontend/src/pages/Trainers.jsx`: “Browse reviewed trainer profiles …”.
- `frontend/src/pages/About.jsx`: “it is reviewed before a profile appears”.
- `frontend/src/pages/Submit.jsx`: “Profiles are reviewed and selected based on experience, public proof, and alignment …”.

These statements are visible to visitors and imply universal review/selection that the present listing facts do not establish. This leaves DF-016 and MP-005R `PARTIAL`. The regression must cover public shared components and all public routes, not merely a hand-maintained subset of pages.

## Narrow required rework

1. Replace the four public claims above with factual, evidence-bounded language. Do not introduce a new universal review, verification, qualification, availability or safety claim.
2. Expand the neutrality regression so it exercises every publicly rendered route and shared public chrome/component, and assert that prohibited universal trust claims cannot reappear.
3. Preserve the accepted delivery, urgent-routing, telemetry and visual-fixture work. Make no provider, data, billing, authentication, deployment or production change.
4. Return one local commit, changed-file list, focused test output and a statement of external actions (expected: none) for a narrow re-audit.

## Still outside this local acceptance

M1--M10 remain subject to their completion criteria. In particular, disposable developer-sandbox owner journey, persistence/redaction, notification-provider and operational evidence (M2/M5/M9) have not been run. Local tests and a local visual fixture are not sandbox acceptance.
