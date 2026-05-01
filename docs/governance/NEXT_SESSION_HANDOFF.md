# Next Session Handoff (Launch-Ready Website)

Date: 2026-05-01  
Repo: `/Users/carlg/Documents/AI-Coding/dtd`  
Baseline commit: `2666d5c`

## Primary objective

Complete a **ready-to-launch website** for Bark&Bond with production-grade deployment, legal/public copy, and verifiable operational readiness.

## Verified baseline (already done)

1. Public/trainer IA routes exist and are wired:
- `/`, `/how-it-works`, `/about`, `/pricing`, `/trust`, `/faq`, `/contact`, `/privacy`, `/terms`, `/trainers`, `/submit`, `/t/:id`, `/ops`
2. Backend launch policies are implemented:
- Region enforcement
- Consent checkpoints
- Intro idempotency
- Intro-first billing with conversion `track_only` default
3. Automation loops implemented:
- source ingestion (`DISCOVERY_SOURCE_URLS`)
- T+7 outreach (`RESEND_API_KEY`, `RESEND_FROM`)
4. Local verification already passing:
- `python3 -m compileall backend`
- `npm --prefix frontend run build`

## Human-first blockers (must be completed before more AI execution)

H-01 Domain and DNS finalization  
Owner: Human  
Required:
1. Confirm production domain(s) and canonical host.
2. Complete DNS records.
3. Confirm TLS issuance in Vercel.
Why human-first:
1. AI cannot complete registrar ownership actions without your account confirmation.

H-02 Platform secret readiness  
Owner: Human  
Required:
1. Ensure valid keys are present in secure storage and runtime env:
- `VERCEL_TOKEN` (if API automation used)
- `RESEND_API_KEY`
- `RESEND_FROM`
- `DISCOVERY_SOURCE_URLS`
- `SENTRY_DSN`
- `NEXT_PUBLIC_POSTHOG_KEY`
- `NEXT_PUBLIC_POSTHOG_HOST`
Why human-first:
1. Missing/invalid credentials block deployment and runtime evidence capture.

H-03 Legal copy sign-off  
Owner: Human  
Required:
1. Final approve legal/public wording for `/privacy`, `/terms`, `/trust`, `/pricing`.
Why human-first:
1. AI can draft text but cannot provide legal authority/approval.

H-04 Production billing/account state checks  
Owner: Human  
Required:
1. Confirm account plans/limits are active for Vercel/Render/Atlas/Resend/Sentry/PostHog.
Why human-first:
1. AI cannot resolve account billing/verification constraints without account actions.

## AI-executable tasks (after human blockers)

A-01 Documentation truth hardening  
Goal:
1. Remove stale references to external model runtime where deterministic heuristic is used.
2. Align README, ARCHITECTURE, and roadmap wording to exact implementation.
Verification:
1. `rg` scan shows no conflicting runtime claims.

A-02 Stage D evidence pack capture  
Goal:
1. Record exact commands/results for domain, TLS, and edge config.
Files:
1. `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md`
Verification:
1. Evidence entries include date, command, and observed result.

A-03 Stage E deploy/redeploy evidence pack  
Goal:
1. Execute repeatable deploy and rollback/redeploy path.
2. Record exact procedure and outcomes.
Verification:
1. Runbook contains a repeatable command sequence and pass/fail outcomes.

A-04 Runtime smoke and launch gate checks  
Goal:
1. Validate backend health and `/ops` loop state.
2. Validate frontend route accessibility and key CTAs.
Verification:
1. Build passes.
2. Oversight shows active loops with fresh `last_run`.
3. Route and CTA checklist passes.

A-05 Discovery + outreach operational proof  
Goal:
1. Validate source ingestion adds queue entries.
2. Validate outreach loop writes send/fail events.
Verification:
1. `system_state.source_ingestion` and `system_state.outreach` updated.
2. `discovery_queue` and `outreach_events` contain expected rows.

A-06 Final launch readiness report  
Goal:
1. Produce a final “Go/No-Go” summary with unresolved risks.
Verification:
1. Every roadmap gate is marked with objective evidence.

## Ordered execution plan for new session

1. Confirm H-01 to H-04 are complete.
2. Run A-01 documentation hardening.
3. Run A-02 Stage D evidence capture.
4. Run A-03 Stage E evidence capture.
5. Run A-04 runtime smoke checks.
6. Run A-05 automation proofs.
7. Run A-06 final launch report.

## Done definition (ready-to-launch website)

1. Public/trainer pages are complete and coherent.
2. Legal/policy pages are approved and final.
3. Domain + TLS are live and validated.
4. Deployment procedure is repeatable and documented.
5. Observability and outreach/discovery loops are operational.
6. Runbook contains evidence for Stages A-E.
7. Final Go/No-Go report exists with zero unresolved critical blockers.

## New session bootstrap prompt (copy/paste)

Use only `docs/governance/NEXT_SESSION_HANDOFF.md`, `docs/governance/ROADMAP.md`, and current repository state as authority.  
Primary goal: finish “ready-to-launch website” gates with zero scope drift.  
Do not re-open settled governance decisions unless an objective blocker appears.  
Execute tasks strictly in the listed order, recording command-level evidence for each gate.

