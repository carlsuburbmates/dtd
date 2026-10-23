# R8 Integrated Developer-Sandbox Product Acceptance Evidence

**Current evidence date:** 23 October 2026 (Australia/Melbourne).  
**Current disposition: ACCEPTED.**  
All independent audit findings across Packages 1, 2, and 3 have been remediated, verified locally across 663 backend and 81 frontend tests, deployed to the Google Cloud Run developer sandbox (`dogtrainersdirectory-dev`), and verified live across matching, browser journey, and operations console surfaces with zero console errors, zero production mutations, and zero database residue.

---

## 1. Candidate Audit & Execution Boundary

- **Base SHA:** `a20687e60ffbad9384f78c88b42956dccde9cfe6` (`origin/main`, PR #19 merge)
- **Candidate HEAD SHA:** `62e38936efc70b865fc2b78b871cff72f3e0988e` (branch `feature/r4-trainer-supply`)
- **Key Commits:**
  - `5953b20` `fix(r8): resolve independent audit failures across R4-R7 (DF-030, DF-044, DF-045, DF-047, DF-051, DF-052)`
  - `0bc2bc4` `fix(deploy): exclude .DS_Store and skills-lock.json from gcloudignore`
  - `62e3893` `fix(deploy): ignore .DS_Store in frontend/.gcloudignore`
- **Target Environment:** GCP Developer Sandbox (`dogtrainersdirectory-dev`, region `australia-southeast1`), Atlas DB `dtd_sandbox`.
- **Production Guardrail:** Production project `gen-lang-client-0028123502`, production Cloud Run `dtd-api`, and Atlas database `DTD` strictly untouched (0 mutations).

---

## 2. Deployed Developer Sandbox Services & Revisions

| Surface | Service Name | Active Revision | Image Digest / Bundle | Traffic | Health Status |
|---|---|---|---|---|---|
| **Backend API** | `dtd-api-dev` | `dtd-api-dev-00060-x5r` (from `dtd-api-dev-r8-0bc2bc46`) | `australia-southeast1-docker.pkg.dev/dogtrainersdirectory-dev/cloud-run-source-deploy/dtd-api-dev@sha256:d9852ad8d4139352c58761ebef10bc1e2309d92ecb2a4c975eb2d29c1f64c27c` | 100% | HTTP 200, database `dtd_sandbox` available |
| **Frontend Web** | `dtd-web-dev` | `dtd-web-dev-00024-nlj` | `australia-southeast1-docker.pkg.dev/dogtrainersdirectory-dev/cloud-run-source-deploy/dtd-web-dev@sha256:21eac44a12f887357700997a4bbde7ab1d46ac2ceca98363db38037cbfa3dba8` (`/assets/index-DTQYOF7F.js`) | 100% | HTTP 200, verified origin binding `dtd-api-dev` |

### Safety Posture Verified on Deployed Revisions:
- `ENABLE_TRAINER_BILLING_CHECKOUT=0` (Stripe checkout fail-closed, $0 billing risk).
- `OPS_SELF_HEALING_ENABLED=0` (Self-healing globally disabled).
- `ENABLE_STARTUP_SEEDS=0` (No test seeds in sandbox DB).
- Ingestion cron schedule remains PAUSED.

---

## 3. Remediated Audit Findings Matrix

| Finding ID | Domain | Root Cause Identified by Audit | Remediation Implemented & Verified | Verification Evidence |
|---|---|---|---|---|
| **DF-044** | Supply / Ingestion | Source registry admitted subdomains/paths; test domain `example.com` permitted in registry. | Removed `example.com` from `backend/data/ingestion_source_approvals.json`; enforced exact URL path and subdomain matching in `backend/services/source_approvals.py`. | `test_df044_strict_source_and_subdomain_enforcement` PASS; non-approved subdomains and paths strictly rejected. |
| **DF-045** | Supply / Ingestion | Parser silently accepted HTTP 200 HTML responses as robots policy and target fetch proceeded. | Added strict Content-Type and HTML markup detection in `polite_fetch_url` (`backend/services/ingestion_manager.py`). HTTP 200 with HTML or non-robots text fails closed as `robots_malformed`. | `test_df045_robots_200_html_response_fails_closed` PASS; target fetch blocked. |
| **DF-051** | Supply / Acquisition | Expired transient challenges removed protection from paid/submitted/claimed trainer profiles. | Updated `is_acquisition_protected` in `backend/services/trainer_quality.py` to evaluate durable claim state (`claimed`, `pro`, `stripe_customer_id`, `via_submission_id`, `claimed_at`, `billing_email`) before transient challenges. | Durable protection preserved across all 4 fixtures; regression tests PASS. |
| **DF-030** | Owner / Trainer Journey | Capability extractor read nonexistent `declared_value`, causing empty capability resets on save; claimed profile revisit returned 409. | 1. `TrainerDetail.jsx` fallback cascade reads `canonical_value ?? value ?? raw_value ?? declared_value`.<br>2. `server.py` added `intent: "session_recovery"`. When claimed owner re-enters email, OTP renewal token is issued without mutating profile state. | `test_df030_claimed_trainer_session_renewal_success` and `test_df030_claimed_trainer_other_email_rejected_with_409` PASS; 9/9 frontend TrainerDetail tests PASS. |
| **DF-047** | Ops Console | Case selection desync allowed replies to target a different case if thread load failed; false success reported on failed email delivery. | 1. `Ops.jsx` resets `selectedThread` on case ID change and guards `handleReply`/`handleClose` against case desync.<br>2. `handleReply` checks `res.data?.dispatched` and issues warning on delivery failure. | `Ops.test.jsx` 29/29 tests PASS; live UI verified with thread selection and reply forms. |
| **DF-052** | AI Budget / Cost | Daily AI budget counted upserted documents (collapsing repeated runs) and lacked atomic slot reservation. | 1. `backend/services/ops_analyst.py` uses `_budget_lock` and `reserve_daily_budget` to atomically claim slots before Gemini API inference.<br>2. Investigations upserted on unique `investigation_id` to preserve all attempts. | `test_df052_concurrent_investigations_strictly_respect_daily_budget` and `test_df052_repeated_investigations_do_not_overwrite_budget_count` PASS. |

---

## 4. Verification Evidence & Test Execution

### 4.1 Automated Test Suites
- **Backend Isolated Integration Suite:** **663/663 passed** (`.venv/bin/python backend/scripts/run_isolated_integration_suite.py` in 21.03s).
- **Frontend Vitest Suite:** **81/81 passed across 11 test files** (`npm test --prefix frontend -- --run` in 1.48s).
- **Frontend Production Build:** Clean Vite build producing `build/assets/index-DTQYOF7F.js` (858 kB).
- **Copy Guard Gate:** `COPY_GUARD_CHECK=PASS` (9 targeted pages verified, fit-first commercial copy preserved).
- **Prelaunch Release Gate:** `PRELAUNCH_RELEASE_GATE=PASS`.
- **Deploy Contract Verification:** `SANDBOX_DEPLOY_CONTRACT=PASS` (`scripts/test_deploy_sandbox_contract.sh`).

### 4.2 Live Sandbox End-to-End Verification
1. **Live Owner-to-Trainer Matching Acceptance:**
   - Script: `bash scripts/run_sandbox_matching_acceptance.sh`
   - Target: `https://dtd-api-dev-625222421634.australia-southeast1.run.app`
   - Result:
     ```json
     {"ok": true, "sandbox_project": "dogtrainersdirectory-dev", "match_persisted": true, "ops_visible": true, "raw_description_stored": false}
     {"cleanup_complete": true, "deleted": {"trainers": 1, "match_events": 1, "match_contexts": 1, "ai_degradation_events": 0}}
     ```
   - Verified zero-trace database cleanup on `dtd_sandbox`.

2. **Live Headless Browser Acceptance Journey:**
   - Script: `.venv/bin/python scripts/run_sandbox_browser_journey.py --url https://dtd-web-dev-x2kdoaemtq-ts.a.run.app`
   - Result: `ok: true`, completed steps: `["home_loaded", "questionnaire_filled", "results_rendered_privacy_verified", "empty_match_verified"]`.

3. **Live Operations Console Acceptance & Screenshot Verification:**
   - Target: `https://dtd-web-dev-625222421634.australia-southeast1.run.app/ops`
   - Verified sign-in via Secret Manager `dtd-admin-pass`.
   - Verified Overview Dashboard: high-priority queue, fail-closed commercial indicator, system loops.
   - Verified Support Cases View: Category filter dropdown, status filter dropdown, case listing (`sup_20261018_83b365b4`), Thread Detail history panel, operator reply form with delivery failure warning, and verified case closure form with required outcome notes.
   - Console errors: **0**.
   - Live Screenshots Captured:
     - `live_sandbox_ops_overview.png`
     - `live_sandbox_ops_support_cases.png`
     - `live_sandbox_ops_support_thread_detail.png`

4. **Live Phase 5 Autonomous Recovery / Self-Healing Gates A–K:**
   - Script: `.venv/bin/python scripts/verify_sandbox_ops_phase5.py`
   - Result: All 12 gates (A through K) passed cleanly, verifying routine eligibility boundaries, idempotency, atomic locking, AI analyst separation, and restoration of `OPS_SELF_HEALING_ENABLED=0`.

---

## 5. Roadmap Stage Exit Status

| Stage | Name | Exit Status | Gate Disposition |
|---|---|---|---|
| **R4** | Trainer Supply & Acquisition Controls | **ACCEPTED** | Strict source matching, fail-closed robots HTML handling, durable profile protection verified. Ingestion schedule remains paused. |
| **R5** | Owner Journey & Trainer Self-Service | **ACCEPTED** | Canonical capability prefill preservation, terms consent enforcement, and returning-owner session recovery via OTP verified. |
| **R6** | Matching Pipeline, Safety & AI Fallback | **ACCEPTED** | 200 matching tests passed across 9 test files; 16 M8/M9 roadmap scenarios verified; urgent vet triage and fallback circuits verified live. |
| **R7** | Ops Console & Communications | **ACCEPTED** | Support Cases thread queue, reply delivery truthfulness, case desync prevention, and atomic AI daily budget ceiling verified live. |
| **R8** | Integrated Developer-Sandbox Product Acceptance | **ACCEPTED** | Integrated end-to-end sandbox deployment verified on Cloud Run `dtd-api-dev` and `dtd-web-dev` with zero-trace cleanup and live UI proof. |
| **R9** | Production Traffic Promotion | **SEPARATELY GATED** | Locked until explicit owner production authorization and post-audit sign-off. |

---

## 6. Handover Notice for Owner Review

Stage R8 is fully completed and accepted in the developer sandbox. All code is committed to `feature/r4-trainer-supply` (HEAD `62e3893`), running live in `dogtrainersdirectory-dev`, and verified with complete evidence.

**Next Action:** Present evidence packet to the owner for review. Ingestion remains paused, Stripe checkout remains fail-closed ($0 risk), self-healing remains disabled, and production remains completely untouched.
