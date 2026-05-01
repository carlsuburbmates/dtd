# Next Session Handoff (Launch-Ready Website)

Date: 2026-05-01  
Repo: `/Users/carlg/Documents/AI-Coding/dtd`  
Authority files:
1. `docs/governance/NEXT_SESSION_HANDOFF.md` (this file)
2. `docs/governance/ROADMAP.md`
3. `docs/governance/LOCK_STATE.md`
4. current repository state on `main`

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

## Hard gate rule (mandatory)

AI may continue development tasks while domains remain intentionally detached.  
Public-launch cutover and `GO` decision remain gated by H-01 to H-04 evidence completion.

## Execution log (fill in during next session)

1. Session start HEAD: `88e53c9` (`git rev-parse --short HEAD`)
2. Human gates completed: `H-03` completed (legal sign-off approved by owner), `H-04` completed (platform readiness verified across all configured integrations), `H-02` completed previously, and `H-01` remains intentionally held while UI/workflows are unfinished.
3. AI tasks completed: verified Vercel project/deployment state, DNS/TLS resolution, backend config endpoint, and frontend env wiring
4. Final Go/No-Go: pending

## Current verified state (2026-05-02)

1. Vercel project `dtd` is live and the latest production deployment is ready.
2. `https://dtd-api.onrender.com/api/config` returns `200` JSON with active-region and billing-mode config.
3. Vercel prod and preview envs both contain `REACT_APP_BACKEND_URL=https://dtd-api.onrender.com`.
4. `frontend/src/lib/api.js` builds the API base URL from `REACT_APP_BACKEND_URL`.
5. Vercel env inventory for `dtd` includes `REACT_APP_BACKEND_URL`, `REACT_APP_POSTHOG_KEY`, `REACT_APP_POSTHOG_HOST`, `NEXT_PUBLIC_POSTHOG_KEY`, and `NEXT_PUBLIC_POSTHOG_HOST`, and Render services `dtd-api`/`dtd-worker` include `RESEND_API_KEY`, `RESEND_FROM`, `DISCOVERY_SOURCE_URLS`, and `SENTRY_DSN`.
6. `dogtrainersdirectory.com.au` and `www.dogtrainersdirectory.com.au` still resolve to Vercel but return `404 DEPLOYMENT_NOT_FOUND` because the custom-domain aliases were intentionally removed/locked.

---

## Verified baseline (already complete)

1. Public/trainer routes implemented:
- `/`, `/how-it-works`, `/about`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`, `/trainers`, `/submit`, `/t/:id`, `/ops`
2. Launch policy implementation complete:
- region enforcement, consent checkpoints, intro idempotency, intro-first billing (`track_only`)
3. Automation loops implemented:
- source ingestion (`DISCOVERY_SOURCE_URLS`)
- T+7 outreach (`RESEND_API_KEY`, `RESEND_FROM`)
4. Local checks passing:
- `python3 -m compileall backend`
- `npm --prefix frontend run build`

---

## Human launch gates (required before public go-live)

### H-01 Domain + DNS + TLS finalization
Owner: Human

Status: Intentional hold during development (not a blocker for build-phase execution)

Required actions:
1. Confirm canonical production hostname (for example `dogtrainersdirectory.com.au` with `www` redirect policy).
2. Complete DNS records at registrar/DNS host.
3. Confirm TLS is issued and active.

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

Required actions:
1. Ensure launch-secret keys are set in runtime targets:
- `RESEND_API_KEY`
- `RESEND_FROM`
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
1. `rg -n "Claude|Sonnet|per-conversion fee|six loops|6 autonomous loops" README.md docs backend frontend -S`
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
2. Complete H-02 to H-04 during development and complete H-01 before public launch.
3. Run A-01.
4. Run A-02.
5. Run A-03.
6. Run A-04.
7. Run A-05.
8. Run A-06.

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
