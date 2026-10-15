# Independent audit — MP-005R copy rework `1cdd88d` (5 October 2026)

**Candidate:** `1cdd88d38d9098c87085d81ef087e14f6f4080bd` on `feature/matching-implementation` (parent `8e03f6c`).

**Decision:** `PARTIAL` — do not advance this commit to the developer sandbox. The rework correctly removes the four previously identified public claims and improves regression coverage, but one public `verified` claim remains outside its prohibited-phrase list.

## Independently checked

- The exact candidate commit exists, is clean and passes `git diff --check 8e03f6c..1cdd88d`.
- `./.venv/bin/pytest backend/tests/test_matching_mp_repairs_unit.py -v`: 32 passed.
- `npm test --prefix frontend -- --watchAll=false`: 10 suites / 44 tests passed.
- `npm run build --prefix frontend`: passed.
- The diff neutralises the identified `PublicChrome`, `Trainers`, `About` and `Submit` review/selection wording.
- The new regression dynamically scans direct public page and shared-component source files rather than the former six-file list.

## Remaining MP-005R blocker

`frontend/src/components/PublicArt.jsx` retains `eyebrow: "Verified rollout"` in the `network` variant. `About.jsx` imports that variant, so visitors to `/about` still see an unsupported broad verification claim.

The source scan includes `PublicArt.jsx`, but its prohibited-phrase list does not include `verified rollout`; therefore the test passes while the public claim remains. This is a regression-test blind spot, not evidence that the wording is acceptable.

## Required local-only follow-up

1. Replace `Verified rollout` with a neutral, factual label such as `Initial rollout` or `Melbourne rollout`.
2. Add the exact prohibited phrase (and, preferably, a narrowly scoped `verified` wording rule for marketing/shared-art content) to the regression test.
3. Re-run the focused backend copy test, frontend tests and build; return one local commit and the usual no-external-actions handoff.

No matching, delivery, urgent-provider, provider, data, billing, authentication, deployment or production work is requested. Once this is independently accepted, the next stage is developer-sandbox acceptance; local tests alone do not close M2/M5/M6/M9.
