# Next Session Handoff (Launch-Ready Website)

Date: 2026-05-02  
Repo: `/Users/carlg/Documents/AI-Coding/dtd`  
Authority files:
1. `docs/governance/NEXT_SESSION_HANDOFF.md` (this file)
2. `docs/governance/ROADMAP.md`
3. `docs/governance/LOCK_STATE.md`
4. current repository state on `main`
Companion (Codex interaction governance):
- `docs/governance/CODEX_PLATFORM_SYNC.md`

## Primary objective

Finish a **ready-to-launch website** for Bark&Bond with:
1. production domain + TLS,
2. deploy/redeploy evidence,
3. final legal/public copy sign-off,
4. verified operational runtime checks.

## Session-start protocol (mandatory)

1. Capture current HEAD at session start:
- `git rev-parse --short HEAD`
2. Write it into this file under “Execution log”.
3. Do not rely on any prior chat history beyond the authority files above.
4. Do not re-open locked governance decisions unless an objective blocker appears.
5. If any status is changed in governance docs, include a command/file evidence reference in the same session log entry.

## Hard gate rule (mandatory)

Public-launch cutover and `GO` decision remain gated by H-01 to H-04 evidence completion.
`H-01` domain/TLS evidence is now satisfied and recorded; do not regress the live domain state.

## Execution log (append each session; mandatory)

Required entry format for this section:
1. UTC timestamp.
2. Session start HEAD (`git rev-parse --short HEAD`).
3. Status changes made (gate/task/status field and new value).
4. Evidence reference for each status change:
- command + observed result, and/or
- file path + line reference.

Current session entries:
1. `2026-05-01T19:42:15Z` — Session start HEAD captured as `0e4382a` (`git rev-parse --short HEAD`).
2. Runtime verification commands executed:
- `curl -sS -o /tmp/dtd_api_config.json -w "HTTP=%{http_code}\n" https://dtd-api.onrender.com/api/config` → `HTTP=200`; response confirms `active_region_default=Greater Melbourne` and `conversion_billing_mode=track_only`.
- `curl -sSI https://dogtrainersdirectory.com.au` → `HTTP/2 404` with `x-vercel-error: DEPLOYMENT_NOT_FOUND`.
- `curl -sSI https://www.dogtrainersdirectory.com.au` → `HTTP/2 404` with `x-vercel-error: DEPLOYMENT_NOT_FOUND`.
3. Governance status sync applied in this session:
- `H-01`: unchanged (`final cutover step`, still open).
- `H-02`: unchanged (`completed`).
- `H-03`: unchanged (`completed`).
- `H-04`: unchanged (`completed`).
- Final Go/No-Go: unchanged (`pending`).
4. Stage E deploy/redeploy proof executed on `main`:
- `vercel --prod --yes` → `dpl_CBoYcSJxiJprePuwDjUaQaLp9k5H` (`https://dtd-9frc4tnxs-carlitos-projects-a62ff78f.vercel.app`) ready.
- `vercel --prod --yes` (second run) → `dpl_AD5Kghob4aQNHcAFVQyWwNoq373K` (`https://dtd-hdpnfurhw-carlitos-projects-a62ff78f.vercel.app`) ready and aliased to production.
5. Runtime/API/Ops verification executed after deploys:
- `curl https://dtd-api.onrender.com/api/` → `HTTP=200`.
- `curl https://dtd-api.onrender.com/api/config` → `HTTP=200` (`active_region_default=Greater Melbourne`, `conversion_billing_mode=track_only`).
- `curl -H "X-Admin-Pass: $ADMIN_PASS" https://dtd-api.onrender.com/api/oversight` → `HTTP=200`; loop keys present: `ranking`, `pricing`, `verification`, `discovery`, `inference`, `health`, `source_ingestion`, `outreach`; all `last_run` values within 2x interval.
6. Protected deployment route-smoke verification executed with authenticated Vercel access:
- `vercel curl <route> --deployment dpl_AD5Kghob4aQNHcAFVQyWwNoq373K` across required routes (`/`, `/how-it-works`, `/about`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`, `/trainers`, `/submit`, `/t/test-id`, `/ops`) -> all `HTTP=200`.
7. Outreach operational proof executed:
- Created intro `70c9efee-1cc3-41f8-b1bb-eae0365979f0`, backdated to T+8d eligibility in runtime DB, ran `send_t7_outreach` once.
- Result: `outreach_events_total=1`; latest row status `sent`, `http_status=200`.
8. `2026-05-02T07:07:55Z` — Session start HEAD captured as `527c0b2` (`git rev-parse --short HEAD`) for frontend audit/remediation session.
- Status changes in this entry: none yet (initial session bootstrap entry only).
- Evidence: command output `git rev-parse --short HEAD` -> `527c0b2`.
9. `2026-05-02T07:19:58Z` — Session baseline revalidated as clean/synced on `main` with HEAD `68e6a7e` before frontend audit execution.
- Status changes in this entry: none (baseline verification only).
- Evidence: `git branch --show-current` -> `main`; `git rev-parse --short HEAD` -> `68e6a7e`; `git status --short` -> clean; `git rev-list --left-right --count origin/main...HEAD` -> `0 0`.
10. Frontend audit/remediation milestone completed on `main` (HEAD baseline `68e6a7e`).
- Status changes in this entry:
  - Frontend accessibility/semantics baseline moved from partial compliance to verified pass on audited surfaces.
  - Frontend route/CTA/workflow smoke revalidated after grouped fixes.
  - Audit wording corrected: home suburb select control id is `match-suburb` (not `suburb`).
  - Launch gates: unchanged (`H-01` open; `H-02/H-03/H-04` completed; final Go/No-Go pending).
- Evidence (commands + observed results):
  - `npm --prefix frontend run build` -> `Compiled successfully`.
  - Local route smoke: `curl http://localhost:3000<route>` for `/`, `/how-it-works`, `/about`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`, `/trainers`, `/submit`, `/t/f1c3885f-53a7-4764-969f-278ba5b774b9`, `/ops`, `/melbourne/richmond` -> all `HTTP=200`.
  - Accessibility re-checks (Lighthouse):
    - `npx lighthouse http://localhost:3000/ ...` -> accessibility score `1`.
    - `npx lighthouse http://localhost:3000/submit ...` -> accessibility score `1`.
    - `npx lighthouse http://localhost:3000/trainers ...` -> accessibility score `1`.
    - `npx lighthouse http://localhost:3000/t/f1c3885f-53a7-4764-969f-278ba5b774b9 ...` -> accessibility score `1`.
    - `npx lighthouse http://localhost:3000/ops ...` -> accessibility score `1`.
    - Additional route checks `/about`, `/how-it-works`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`, `/melbourne/richmond` -> accessibility score `1` each.
- Evidence (file paths updated in this milestone):
  - `frontend/src/index.css`
  - `frontend/src/lib/api.js`
  - `frontend/src/components/PublicChrome.jsx`
  - `frontend/src/pages/Home.jsx`
  - `frontend/src/pages/Trainers.jsx`
  - `frontend/src/pages/Submit.jsx`
  - `frontend/src/pages/TrainerDetail.jsx`
  - `frontend/src/pages/Ops.jsx`
  - `frontend/src/pages/SuburbSEO.jsx`
11. Stripe intro-billing integration milestone completed (build-phase, no domain-cutover impact).
- Status changes in this entry:
  - Added fail-soft Stripe billing service for intro invoicing and trainer billing profile provisioning.
  - Added webhook reconciliation endpoint `POST /api/stripe/webhook` and intro-level collection status tracking.
  - Added trainer submit consent checkpoint for intro billing terms in UI.
- Evidence (commands + observed results):
  - `python3 -m compileall backend` -> pass.
  - `npm --prefix frontend run build` -> pass.
- Evidence (file paths updated in this milestone):
  - `backend/services/stripe_billing.py`
  - `backend/server.py`
  - `frontend/src/pages/Submit.jsx`
  - `README.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DEPLOYMENT.md`
  - `docs/governance/ROADMAP.md`
  - `docs/governance/LOCK_STATE.md`
12. `2026-05-07T14:13:11Z` — Session start HEAD captured as `b670472` (`git rev-parse --short HEAD`) and launch-track verification rerun.
- Status changes in this entry:
  - Backend regression harness hardened to avoid env-coupled collection failures.
  - Full backend test suite now runs and passes in local environment.
  - Runtime drift discovered for operational loops despite platform env-key presence checks.
- Evidence (commands + observed results):
  - `python -m pytest -q backend/tests` -> `45 passed`.
  - `python3` runtime checks against `https://dtd-api.onrender.com/api`:
    - `/api/` -> `HTTP 200`
    - `/api/config` -> `HTTP 200` (`active_region_default=Greater Melbourne`, `conversion_billing_mode=track_only`)
    - `/api/oversight` -> `HTTP 200` with required loop keys present.
  - Oversight loop snapshot:
    - `source_ingestion` -> `reason=no_sources_configured`, `sources=1`, `failed_sources=1`
    - `outreach` -> `reason=no_resend_api_key`, `checked=4`, `sent=0`
  - Render API diagnostics:
    - `GET /v1/services?limit=100` -> `HTTP 200`; `dtd-api` and `dtd-worker` found/live.
    - `GET /v1/services/{id}/env-vars` -> required keys present for both services (`RESEND_API_KEY`, `RESEND_FROM`, `RESEND_REPLY_TO`, `DISCOVERY_SOURCE_URLS`, `SENTRY_DSN`).
  - Stage-A remote runtime verification:
    - `STAGE_A_MODE=remote bash scripts/verify_stage_a_runtime.sh` -> `RESULT=PASS`.
- Evidence (file paths updated in this milestone):
  - `backend/tests/backend_test.py`
  - `backend/tests/test_iteration3.py`
  - `backend/tests/test_w8_billing_unit.py`
13. `2026-05-07T14:47:14Z` — Session start HEAD captured as `b33f30a` (`git rev-parse --short HEAD`) for domain-state reconciliation.
- Status changes in this entry:
  - `H-01` transitioned from open to completed.
  - Stage D evidence pack transitioned from open to complete.
  - Governance docs were updated to match the live public-domain state.
- Evidence:
  - `vercel alias ls` -> `dogtrainersdirectory.com.au` and `www.dogtrainersdirectory.com.au` both aliased to `dtd-mv0os58gf-carlitos-projects-a62ff78f.vercel.app`.
  - `vercel domains ls` -> `dogtrainersdirectory.com.au` present in the Vercel domain inventory.
  - `curl -sSI https://dogtrainersdirectory.com.au` -> `HTTP/2 307` redirecting to `https://www.dogtrainersdirectory.com.au/`.
  - `curl -sSI https://www.dogtrainersdirectory.com.au` -> `HTTP/2 200`.
  - `curl -sSI https://www.dogtrainersdirectory.com.au/trainers` -> `HTTP/2 200`.

## Current verified state (2026-05-07)

1. Vercel project `dtd` is live and the latest production deployment is ready.
2. `https://dtd-api.onrender.com/api/config` returns `200` JSON with active-region and billing-mode config.
3. Vercel prod and preview envs both contain `REACT_APP_BACKEND_URL=https://dtd-api.onrender.com`.
4. `frontend/src/lib/api.js` builds the API base URL from `REACT_APP_BACKEND_URL`.
5. Vercel env inventory for `dtd` includes `REACT_APP_BACKEND_URL`, `REACT_APP_POSTHOG_KEY`, `REACT_APP_POSTHOG_HOST`, `NEXT_PUBLIC_POSTHOG_KEY`, and `NEXT_PUBLIC_POSTHOG_HOST`, and Render services `dtd-api`/`dtd-worker` include `RESEND_API_KEY`, `RESEND_FROM`, `RESEND_REPLY_TO`, `DISCOVERY_SOURCE_URLS`, and `SENTRY_DSN`.
6. `dogtrainersdirectory.com.au` and `www.dogtrainersdirectory.com.au` now resolve to Vercel and return live responses (`307` apex redirect to `www`, `200` on `www` and `/trainers`).
7. Required frontend routes are renderable on the protected production deployment when accessed via authenticated Vercel route smoke.
8. Historical `outreach_events` evidence exists; live oversight loop reasons are now cleared after the Render env verification/redeploys, and `source_ingestion.failed_sources=1` remains only as a historical count until the next successful ingestion cycle.

Evidence references:
1. H-01 live-domain proof: execution log entry 13 + `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("Stage D/E (complete)").
2. H-02 snapshot and env inventory: `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("H-02 readiness snapshot", items 1-4).
3. H-04 readiness proof: `docs/governance/H04_VERIFICATION_REPORT.json`.
4. API base URL wiring: `frontend/src/lib/api.js`.
5. Live runtime checks from this session log (section above): API, oversight, protected route-smoke, and outreach loop-output evidence.

---

## Verified baseline (already complete)

1. Public/trainer routes implemented:
- `/`, `/how-it-works`, `/about`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`, `/trainers`, `/submit`, `/t/:id`, `/ops`
2. Launch policy implementation complete:
- region enforcement, consent checkpoints, intro idempotency, intro-first billing (`track_only`)
3. Automation loops implemented:
- source ingestion (`DISCOVERY_SOURCE_URLS`)
- T+7 outreach (`RESEND_API_KEY`, `RESEND_FROM`, `RESEND_REPLY_TO`)
4. Local checks passing:
- `python3 -m compileall backend`
- `npm --prefix frontend run build`

---

## Human launch gates (required before public go-live)

### H-01 Domain + DNS + TLS finalization
Owner: Human

Status: Completed on 2026-05-07
Evidence status reference: current-session execution log (`vercel alias ls` + `curl -I` checks) + `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("Stage D/E (complete)").

Required actions:
1. None; canonical production hostname, redirect policy, DNS, and TLS are live and verified.

Required evidence (must be recorded in runbook):
1. Screenshot or export showing DNS records.
2. Screenshot showing domain status in Vercel (or target edge platform).
3. Command proof:
- `dig +short <domain>`
- `dig +short www.<domain>`
- `curl -I https://<domain>`

Pass criteria:
1. DNS resolves correctly.
2. HTTPS returns valid response with no certificate warning.

### H-02 Platform secret readiness
Owner: AI (autonomous verification + patching)

Status: Completed on 2026-05-02
Evidence status reference: `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("H-02 readiness snapshot", items 1-4).

Required actions:
1. Ensure launch-secret keys are set in runtime targets:
- `RESEND_API_KEY`
- `RESEND_FROM`
- `RESEND_REPLY_TO`
- `DISCOVERY_SOURCE_URLS`
- `SENTRY_DSN`
- `NEXT_PUBLIC_POSTHOG_KEY`
- `NEXT_PUBLIC_POSTHOG_HOST`
2. Ensure frontend runtime vars are set for current CRA build path:
- `REACT_APP_BACKEND_URL`
- `REACT_APP_POSTHOG_KEY`
- `REACT_APP_POSTHOG_HOST`
3. `VERCEL_TOKEN` remains optional and only required if standalone Vercel REST automation is used outside authenticated CLI context.

Required evidence:
1. Render API verification completed for both service IDs:
- `srv-d7plat9kh4rs73e92qcg` (`dtd-api`)
- `srv-d7platpf9bms73alk5u0` (`dtd-worker`)
2. Vercel project env verification completed for:
- `prj_TviWWkrOzNENkY4cazM3XsRHyIR1` (`dtd`)
3. Production redeploy completed after env upsert:
- `dpl_H8gcahxzuwLfEmf66VL3v9MnoWno`

Pass criteria:
1. No missing required key for launch workflow.

### H-03 Legal copy sign-off
Owner: Human

Status: Completed on 2026-05-02 (owner approval recorded)
Evidence status reference: `docs/governance/LOCK_STATE.md` ("Legal copy sign-off (H-03)").

Required actions:
1. Approve final public/legal copy for:
- `/privacy`
- `/terms`
- `/trust`
- `/pricing`

Required evidence:
1. Sign-off note in `docs/governance/LOCK_STATE.md` containing:
- approver name/role
- date
- scope approved

Pass criteria:
1. Approved copy is recorded and versioned in git.

### H-04 Account/billing readiness
Owner: Human

Status: Completed on 2026-05-02 (AI verification run)
Evidence status reference: `docs/governance/H04_VERIFICATION_REPORT.json` + `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` ("H-04 platform readiness snapshot").

Required actions:
1. Confirm active account state/limits for:
- Vercel
- Render
- MongoDB Atlas
- Resend
- Sentry
- PostHog

Required evidence:
1. Verification report committed at:
- `docs/governance/H04_VERIFICATION_REPORT.json`
2. Runbook checklist updated with per-platform API/runtime proof:
- Vercel, Render, MongoDB Atlas, Resend, Sentry, PostHog

Pass criteria:
1. No platform blocks deployment or runtime event capture.

---

## AI-executable tasks (development can proceed while H-01 is intentionally held)

### A-01 Documentation truth hardening
Goal:
1. Remove stale references that conflict with runtime truth.
2. Ensure docs consistently describe deterministic heuristic runtime and launch billing mode.

Files:
1. `README.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DEPLOYMENT.md`
4. `docs/OPERATIONS.md`
5. `docs/governance/ROADMAP.md`
6. `docs/governance/LOCK_STATE.md`

Verification commands:
1. `rg -n "Claude|Sonnet|per-conversion fee|six loops|6 autonomous loops|RUN_AUTONOMY_IN_API=1 = API owns loops" README.md docs backend frontend -S`
2. Confirm all hits are either intentional historical notes or corrected.

Pass criteria:
1. No conflicting product/runtime claims remain.

### A-02 Stage D evidence pack capture (domain/TLS/edge)
Goal:
1. Record command-level domain and edge evidence in runbook.

Primary commands:
1. `dig +short <domain>`
2. `dig +short www.<domain>`
3. `curl -I https://<domain>`
4. If Vercel CLI available:
- `vercel domains ls`
- `vercel inspect <deployment-url>`

Fallback if CLI unavailable:
1. Capture dashboard screenshots and record URLs/timestamps in runbook.

Pass criteria:
1. Runbook includes date, exact command (or dashboard path), and observed result.

### A-03 Stage E deploy/redeploy evidence pack
Goal:
1. Prove repeatable deploy and rollback/redeploy process.

Minimum evidence sequence:
1. Record initial deployed commit.
2. Trigger deployment of current main.
3. Verify app health on deployed URL.
4. Trigger second deploy (or rollback + redeploy path).
5. Re-verify health and key routes.

Verification commands:
1. `git rev-parse --short HEAD`
2. frontend/backend build/runtime checks as appropriate
3. deployment platform command/log references

Pass criteria:
1. A repeatable runbook sequence exists and was executed successfully at least once end-to-end.

### A-04 Runtime smoke and launch gate checks
Goal:
1. Validate route accessibility and operational oversight freshness.

Checks:
1. Frontend routes return renderable pages for all required public/trainer paths.
2. Backend `/api/` and `/api/config` return success.
3. `/ops` loads and displays loop cards.

Pass thresholds:
1. Frontend build passes.
2. `ranking`, `pricing`, `verification`, `discovery`, `inference`, `health`, `source_ingestion`, `outreach` appear in oversight.
3. Loop `last_run` values are not stale beyond 2x their interval.

### A-05 Discovery + outreach operational proof
Goal:
1. Demonstrate loop output, not just code presence.

Checks:
1. `system_state.source_ingestion` updated with recent run.
2. `system_state.outreach` updated with recent run.
3. `discovery_queue` contains candidate rows from configured sources.
4. `outreach_events` contains sent/failed rows for eligible intros.

Pass criteria:
1. All four checks have recorded evidence in runbook.

### A-06 Final launch readiness report
Goal:
1. Produce final Go/No-Go report with explicit blockers (if any).

Required sections:
1. Completed gates
2. Remaining blockers (critical/high/medium)
3. Recommendation (`GO` or `NO-GO`)
4. Required next action list if `NO-GO`

Pass criteria:
1. Every roadmap gate has objective evidence reference.

---

## Ordered execution plan (do not reorder)

1. Session-start protocol.
2. Maintain H-02/H-03/H-04 as complete (re-verify only if configuration changes).
3. Run A-01.
4. Run A-02.
5. Run A-03.
6. Run A-04.
7. Run A-05.
8. Run A-06.
9. Complete H-01 as the final public-launch cutover step.

---

## Done definition (ready-to-launch website)

A launch-ready website is true only when:
1. Public/trainer routes are complete, accessible, and consistent.
2. Legal copy is approved and committed.
3. Domain and TLS are validated with command evidence.
4. Deploy/redeploy procedure is documented and proven.
5. Operational loops are visible and fresh in oversight.
6. Discovery and outreach loops show real runtime outputs.
7. Runbook contains evidence for stages A through E.
8. Final report returns `GO` with zero unresolved critical blockers.

---

## New session bootstrap prompt (copy/paste)

Use only `docs/governance/NEXT_SESSION_HANDOFF.md`, `docs/governance/ROADMAP.md`, `docs/governance/LOCK_STATE.md`, and current repo state.  
Primary goal: complete launch-readiness gates for a ready-to-launch website with zero scope drift.  
Do not execute public launch cutover or final `GO` declaration until H-01..H-04 are explicitly marked complete with evidence in-file.  
Record command-level evidence for every gate outcome.
