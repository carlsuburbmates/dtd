# Autonomy Audit Tracker (15 Findings)

Historical artifact. Not current authority. Preserved for evidence/history only.
Current authority is `docs/governance/CURRENT_TRUTH_INDEX.md` and the Standards Set.

Date: 2026-05-20
Scope: backend, frontend, governance/docs, test alignment

| # | Finding | Affected project parts | Required fix | Implemented status |
|---|---|---|---|---|
| 1 | Public trainer billing/reactivation endpoints were effectively open | `backend/server.py`, `frontend/src/pages/SubmitStatus.jsx`, `TrainerBilling.jsx`, `TrainerReactivate.jsx` | Add trainer-scoped auth token and enforce on billing/reactivation endpoints | Done |
| 2 | Monetization model drift across active docs | `README.md`, `docs/DEPLOYMENT.md`, `docs/strategy/SOLO_FOUNDER_AUTONOMOUS_OPERATIONS_CONTROL_PACK.md`, `docs/governance/*` | Align to one canonical mode and record decision | Done |
| 3 | Startup split-brain window before lease ownership | `backend/server.py` startup + `backend/services/engine.py` lease loop | Require lease heartbeat ownership before initial loop writes | Done |
| 4 | Stripe webhook dedup non-atomic | `backend/server.py` `/api/stripe/webhook` | Claim event ID atomically before applying intro updates | Done |
| 5 | Intro idempotency race-to-insert could 500 | `backend/server.py` `/api/intros` | Catch duplicate-key and return canonical intro response | Done |
| 6 | Plaintext oversight pass persisted long-term in browser | `frontend/src/lib/api.js` | Replace `localStorage` with session-scoped TTL storage | Done |
| 7 | API/UI matching mode drift when toggle enabled | `frontend/src/pages/Home.jsx`, `frontend/src/App.js`, `backend/server.py` | Render working match form/results when enabled; keep prelaunch waitlist when disabled | Done |
| 8 | Tests assumed always-live matching and failed in prelaunch mode | `backend/tests/backend_test.py`, `backend/tests/test_iteration3.py` | Make tests mode-aware and skip live-flow tests when matching is disabled | Done |
| 9 | Audit logging could fail business operations | `backend/server.py` `_audit` | Make audit writes fail-soft with error logging | Done |
| 10 | Discovery dedup regex used unescaped user input | `backend/services/engine.py` | Escape regex input for domain/name dedup | Done |
| 11 | Oversight auth brute-force controls missing | `backend/server.py` auth paths | Add DB-backed attempt window + lockout for login/header failures | Done |
| 12 | Loop failures were log-only (no persisted failure state) | `backend/services/engine.py` | Persist per-loop status (`last_success`, `last_error`, `consecutive_failures`) | Done |
| 13 | Waitlist attribution gap from campaign landing | `frontend/src/pages/CampaignLanding.jsx`, `Home.jsx`, `backend/server.py` waitlist schema/events | Carry campaign/source/utm into waitlist writes and event records | Done |
| 14 | Frontend had no automated tests discovered by runner | `frontend/src/lib/api.test.js` | Add executable frontend tests so CI/test runner enforces regressions | Done |
| 15 | Governance drift: stale gate sequencing and authority ambiguity | `docs/governance/NEXT_SESSION_HANDOFF.md`, `ROADMAP.md`, `CURRENT_TRUTH_INDEX.md` | Add live gate table and explicit active-vs-historical truth index | Done |

## Per-item implementation notes
1. Trainer action token introduced with HMAC signature + expiry; required by billing/reactivation GET+POST endpoints.
2. Added ADR (`docs/governance/ADR-0001-runtime-canonical-mode.md`) and synchronized doc wording to canonical runtime.
3. Startup now probes lease ownership before initial ranking/pricing/health writes.
4. Webhook now inserts event claim first; duplicate insert returns `duplicate=true` without reapplying updates.
5. Intro create path handles unique-idempotency conflict by replaying existing intro response.
6. Ops passcode now stored in `sessionStorage` with 30-minute TTL.
7. Home page now supports both prelaunch waitlist mode and live matching mode from `/api/config`.
8. Integration tests now skip live-flow assertions when `public_matching_enabled=false`.
9. `_audit` now catches and logs failures instead of bubbling exceptions.
10. Discovery dedup now uses `re.escape` for regex query safety.
11. Added `auth_attempts` tracking and lockout checks for login + oversight header auth failures.
12. Loop runner persists success/failure counters in `system_state` keys `loop_status:*`.
13. Waitlist payload + events now include campaign/source/utm metadata.
14. Added frontend Jest tests (`src/lib/api.test.js`) to ensure suite discovery and session-secret behavior coverage.
15. Added governance current truth index and updated handoff gate table/order wording.

## Documentation sync closure (2026-05-20)
1. Replaced stale mixed-era handoff log with current-truth governance handoff format in `docs/governance/NEXT_SESSION_HANDOFF.md`.
2. Updated roadmap current-system truth and workflow coverage references (`W1-W21`) in `docs/governance/ROADMAP.md`.
3. Synced architecture/workflow/page specs to implemented mode-gated home behavior and active APIs:
- `POST /api/owner-waitlist`
- `GET /api/claims/validate`
- follow-up-driven conversion confirmation path.
4. Refreshed lock-state verification evidence with current local checks in `docs/governance/LOCK_STATE.md`.
