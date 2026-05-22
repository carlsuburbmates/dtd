# Project Launch Readiness And Operational Profile

Historical audit snapshot dated 2026-05-21.
Superseded for launch strategy by the committed supply-first Standards Set.

Date: 2026-05-21
Project: `DTD` / `Dog Trainers Directory`
Scope: docs-first launch-readiness, operational, governance, and implementation audit grounded in current repo truth, targeted code inspection, targeted test evidence, current CI configuration, current local env/config review, and limited live-access checks already performed in-session.
Status: audit artifact; not yet an authoritative replacement for `ROADMAP.md`, `LOCK_STATE.md`, or `NEXT_SESSION_HANDOFF.md`.

Known supersession points:
1. initial launch is now supply-first
2. live matching evidence is not the first launch gate
3. supply readiness is the first launch gate
4. phase records are required
5. `/ops` must show phase, readiness, and blockers

## Evidence Basis

Primary authority docs reviewed:
- `docs/governance/CURRENT_TRUTH_INDEX.md`
- `docs/governance/ROADMAP.md`
- `docs/governance/LOCK_STATE.md`
- `docs/governance/NEXT_SESSION_HANDOFF.md`
- `docs/governance/ADR-0001-runtime-canonical-mode.md`
- `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md`

Core implementation surfaces reviewed:
- `backend/server.py`
- `backend/services/engine.py`
- `backend/services/stripe_billing.py`
- `backend/services/automation.py`
- `backend/services/ai.py`
- `backend/worker.py`
- `frontend/src/App.js`
- `frontend/src/pages/*`
- `frontend/src/lib/api.js`
- `frontend/src/lib/publicPolicy.js`
- `backend/tests/*`
- `.github/workflows/verify.yml`
- `docker-compose.yml`
- `.env.example`, `backend/.env.example`, `frontend/.env.example`

Additional evidence gathered in-session:
- Production frontend reachability: VERIFIED (`200`)
- Production API reachability: VERIFIED (`200`)
- Vercel CLI authentication: VERIFIED
- Local ignored `.env` files exist and contain active-looking provider credentials and config drift; values are intentionally not reproduced here
- `.env`, `frontend/.env`, and `backend/.env` are git-ignored, untracked, and absent from git history

## Classification Legend

| Label | Meaning |
|---|---|
| `VERIFIED` | Supported directly by current code, tests, repo docs, or observed command evidence |
| `PARTIALLY VERIFIED` | Implemented or documented, but incomplete, environment-dependent, or lacking sustained/live proof |
| `UNVERIFIED` | Claimed or implied, but not established by current inspected evidence |
| `PLANNED` | Described for later work, not current launch truth |
| `MANUAL WORKAROUND` | Possible today only through manual operator or engineer action outside a first-class product flow |

## 1. Project Overview

| Item | Assessment |
|---|---|
| Project name | `DTD` / `Dog Trainers Directory` |
| Purpose | Melbourne-focused dog-training match engine with intro-first monetization, deterministic ranking, automated ingestion/verification, and read-only oversight |
| Intended users | Dog owners, trainer businesses, single founder/operator, autonomous background system |
| Core business workflows | Demand capture, owner waitlist or live matching, trainer submission and activation, intro billing, follow-up conversion capture, revenue recovery, trainer reactivation, oversight monitoring |
| Current project status | `PARTIALLY VERIFIED` prelaunch production deployment with local implementation closeout complete; final launch evidence and final owner go/no-go still pending |
| Claimed launch readiness level | Repo governance says `not launch-ready` until final live-verification window, matching-enabled release evidence, and explicit `Final Go/No-Go` are complete |
| Excluded / out of scope | No public trainer directory browse flow, no admin CRUD panel, no multi-operator RBAC console, no runtime external LLM dependency, no mature staging environment, no automated deploy rollback pipeline |
| Current environments | Local dev via Docker or bare metal; Vercel preview is implied for frontend only; production frontend and API are live; no clearly documented full staging stack |

### What problem the platform solves

`VERIFIED`: The platform is designed to convert a dog owner's short problem description into ranked trainer matches, reveal contact details through an intro event, and improve future ranking through engagement and conversion signals. In prelaunch mode, the same homepage is used to capture owner waitlist demand instead of exposing live public matching.

Evidence:
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/governance/ROADMAP.md`
- `frontend/src/pages/Home.jsx`
- `backend/server.py`

### Mission-critical workflows

`VERIFIED` mission-critical workflows are:
- W1 owner match request when matching is enabled
- W20 owner waitlist enrollment while matching is disabled
- W2 intro/contact release
- W7 trainer submission and activation start
- W8 intro billing and webhook reconciliation
- W10 `/ops` oversight visibility
- W13 supply verification/discovery ingestion
- W14 inference, outreach, and health protection
- W17 trainer activation readiness
- W18 revenue recovery
- W19 trainer reactivation

Evidence:
- `docs/USER_WORKFLOWS.md`
- `docs/WORKFLOW_TRACE_SHEET.md`

### Incomplete, unstable, manual, experimental, or founder-dependent areas

| Area | Classification | Reality |
|---|---|---|
| Final launch decision | `UNVERIFIED` | `Final Go/No-Go` has not been recorded |
| Matching-enabled public launch proof | `UNVERIFIED` | Unit coverage exists; release-level live evidence does not |
| Non-technical operations without founder | `PARTIALLY VERIFIED` | Routine monitoring is documented, but recovery still depends on technical-owner actions |
| Shared operator identity model | `PARTIALLY VERIFIED` | Passcode-only oversight auth, no per-operator identity or audit trail for `/ops` logins |
| CI/CD maturity | `PARTIALLY VERIFIED` | Verify workflow exists, but does not run frontend build/tests and ignores push to `main` |
| Rollback maturity | `PARTIALLY VERIFIED` | Manual redeploy is documented; no automated infra rollback pipeline |
| Shared operator note logging | `MANUAL WORKAROUND` | `/ops` notes are browser-local only |
| Secret/config hygiene | `PARTIALLY VERIFIED` | `.env` files are ignored locally, but secret sprawl and config drift exist across root/frontend/backend envs |
| Full production observability | `PARTIALLY VERIFIED` | `/ops` is rich, but external incident tooling is limited and API-side telemetry is thin |

### Active assumptions

| Assumption | Classification | Notes |
|---|---|---|
| Usage scale remains low enough for in-process loop scheduling and Mongo-backed queues | `PARTIALLY VERIFIED` | No dedicated broker or worker fleet architecture is documented |
| One founder can safely cover operator and technical-owner responsibilities | `PARTIALLY VERIFIED` | Explicit operating model; strong business continuity risk if founder unavailable |
| Production can remain safe with passcode-based oversight auth | `PARTIALLY VERIFIED` | Canonical launch decision today, but weak by standard security review expectations |
| Matching can stay disabled while prelaunch demand capture proceeds | `VERIFIED` | Current runtime truth and docs both support this |
| Vendor services remain available without redundancy | `PARTIALLY VERIFIED` | No documented failover plan for Vercel, Render, Atlas, Stripe, or Resend |

## 2. System Architecture Profile

### Stack Summary

| Layer | Current implementation | Classification |
|---|---|---|
| Frontend stack | React 19, React Router 7, CRACO, Tailwind, Radix UI, Axios | `VERIFIED` |
| Backend stack | FastAPI, Uvicorn, Motor, Pydantic v2 | `VERIFIED` |
| Database | MongoDB; Atlas recommended for production | `VERIFIED` |
| Hosting providers | Vercel frontend, Render backend/worker, Atlas database | `PARTIALLY VERIFIED` live topology from docs and session evidence |
| Infrastructure providers | Vercel, Render, MongoDB Atlas, domain/TLS provider chain | `PARTIALLY VERIFIED` |
| Queue/background systems | In-process async loops and Mongo-backed collections; no external queue broker | `VERIFIED` |
| Authentication systems | Shared passcode for oversight; trainer action tokens for lifecycle routes; no active end-user auth | `VERIFIED` |
| File storage systems | None identified as a first-class product dependency | `VERIFIED` |
| Email systems | Resend for app/outreach mail; Stripe-managed invoice mail for billing | `VERIFIED` |
| Payment systems | Stripe invoice workflow for intro billing | `VERIFIED` |
| AI/LLM integrations | No runtime LLM dependency; deterministic heuristics in local code | `VERIFIED` |
| External APIs/services | Stripe, Resend, Vercel, Render, MongoDB Atlas, Sentry, PostHog; Clerk present in env/docs as future or drifted auth path | `PARTIALLY VERIFIED` |
| Analytics/monitoring | `/ops`, persisted `system_state`, Sentry partial, PostHog documented, logs | `PARTIALLY VERIFIED` |
| CI/CD | GitHub Actions verify workflow plus manual CLI deploy/redeploy runbook | `PARTIALLY VERIFIED` |

Evidence:
- `frontend/package.json`
- `backend/requirements.txt`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `.github/workflows/verify.yml`

### High-Level Architecture Diagram

```text
Dog Owner / Trainer / Operator Browser
                |
                v
       Vercel-hosted React frontend
                |
                v
        FastAPI API on Render (or equivalent)
                |
                +------------------------------+
                |                              |
                v                              v
         MongoDB / Atlas                External providers
      trainers, intros, loops,          Stripe, Resend,
      waitlist, audits, growth          Vercel, Render,
      attribution, reactivation         Sentry, PostHog
                |
                v
     Autonomous loops (API-owned or worker-owned)
 ranking, pricing, verification, discovery,
 inference, outreach, billing recovery,
 nurture, reactivation, health
```

### Data Flow Explanation

1. Public homepage loads `/api/config`.
2. If `PUBLIC_MATCHING_ENABLED=false`, the owner can only join the waitlist.
3. If `PUBLIC_MATCHING_ENABLED=true`, owner submits `/api/match`, sees ranked results, and can proceed to trainer detail.
4. Owner contact release writes an intro row via `/api/intros`, runs fraud suppression, and attempts billing fail-soft.
5. Engagements and follow-up conversions feed ranking and quality signals.
6. Trainer submissions can auto-publish and attempt Stripe billing-profile provisioning.
7. Background loops update ranking, pricing, verification, health, discovery ingestion, outreach, billing recovery, nurture, and reactivation state.
8. `/api/oversight` aggregates these states for `/ops`.

Evidence:
- `docs/ARCHITECTURE.md`
- `backend/server.py`
- `backend/services/engine.py`

### Environment Structure

| Environment | Current reality | Classification |
|---|---|---|
| Local development | Docker Compose and bare-metal flows documented and runnable | `VERIFIED` |
| Frontend preview | Vercel preview/project env is documented | `PARTIALLY VERIFIED` |
| Backend staging | No complete staging environment or promotion workflow documented | `UNVERIFIED` |
| Production | Production frontend/API are reachable and governance docs describe live deployment state | `PARTIALLY VERIFIED` |

### External Dependency Map

| Dependency | Role | Criticality | Outage effect | Classification |
|---|---|---|---|---|
| MongoDB Atlas / MongoDB | Primary system of record | `CRITICAL` | Core app and loops stop or degrade immediately | `VERIFIED` |
| Render API / worker runtime | Backend execution | `CRITICAL` | API or loop outage | `PARTIALLY VERIFIED` |
| Vercel | Frontend delivery and domain routing | `CRITICAL` | Public site unavailable or misrouted | `PARTIALLY VERIFIED` |
| Domain/TLS provider chain | Public reachability | `CRITICAL` | Public launch inaccessible or insecure | `PARTIALLY VERIFIED` |
| Stripe | Intro billing and webhook reconciliation | `HIGH` | Revenue collection degrades; contact release still continues fail-soft | `VERIFIED` |
| Resend | T+7 outreach and notification delivery | `HIGH` | Follow-up/outreach visibility and some notifications degrade | `VERIFIED` |
| Sentry | Error tracking | `MEDIUM` | Diagnosis worsens; app still runs | `PARTIALLY VERIFIED` |
| PostHog | Analytics | `MEDIUM` | Analytics blind spots; app still runs | `PARTIALLY VERIFIED` |
| GitHub Actions | CI verification | `MEDIUM` | Reduced automated quality gate | `VERIFIED` |
| Clerk | Not canonical launch auth | `LOW` | Current launch behavior should not depend on it | `PLANNED` |

### Which systems are business-critical

`VERIFIED` business-critical systems:
- MongoDB / Atlas
- Render runtime
- Vercel frontend/domain routing
- Stripe for intended intro collection reliability
- Resend for follow-up and some lifecycle notifications
- `/api/oversight` + `/ops` as primary operational truth surface

### Highest operational risk services

`PARTIALLY VERIFIED` highest operational risks:
- MongoDB / Atlas: single data store, no repo-documented restore runbook
- Render runtime: loop ownership and API availability depend on it
- Stripe: collection path and retry semantics rely on external invoicing/webhook health
- Vercel/domain/TLS chain: public access dependency
- Resend: follow-up, trainer, and submitter notification reliability

### Single points of failure

`VERIFIED` single points of failure:
- Founder/operator/technical owner (`carlg`)
- Single support mailbox (`info@dogtrainersdirectory.com.au`)
- Single primary data store
- Single active loop owner topology by design
- Vendor concentration with no documented failover or hot standby plan

## 3. Feature Verification Matrix

The matrix below uses the implemented workflow inventory as the most complete feature/module list in the repo.

| Feature | Description | Status Classification | How to Test | Expected Result | Dependencies | Known Limitations | Evidence |
|---|---|---|---|---|---|---|---|
| W1 Match request | Owner submits problem and gets ranked matches when matching is enabled | `VERIFIED` | `POST /api/match` with consent and valid payload | Up to 3 ranked results with `match_id` | Backend config, heuristics, trainer data | Publicly gated off when `PUBLIC_MATCHING_ENABLED=false` | `docs/USER_WORKFLOWS.md`, `docs/WORKFLOW_TRACE_SHEET.md`, `backend/server.py` |
| W20 Owner waitlist | Owner demand capture while public matching is gated | `VERIFIED` | Submit waitlist form on `/` or `/lp/:campaign` | Accepted, duplicate, or rejected with reason codes | Home UI, `/api/owner-waitlist`, waitlist collections | No shared operator tooling beyond `/ops` visibility | `backend/server.py`, `frontend/src/pages/Home.jsx`, `docs/USER_WORKFLOWS.md` |
| W2 Contact release / intro | Owner reveals trainer contact and creates intro row | `VERIFIED` | Open trainer detail and submit connect form | Contact card returned; intro persisted | Trainer detail UI, `/api/intros`, fraud logic, optional Stripe | In prelaunch current runtime, direct connect is visually gated from home flow | `backend/server.py`, `frontend/src/pages/TrainerDetail.jsx` |
| W3 Engagement tracking | Website/phone/email/connect-click signals after result/contact | `VERIFIED` | Trigger engagement endpoints from UI | Engagement rows written; conversion inference may follow | Engagement endpoints, intros, matches | Visibility is aggregate, not per-operator workflow-managed | `backend/server.py`, `docs/WORKFLOW_TRACE_SHEET.md` |
| W4 Outcome confirmation | Explicit hired outcome | `VERIFIED` | Submit follow-up or direct conversion | Conversion recorded idempotently | Follow-up token or intro id, conversions table | Fraud/suspicious logic can suppress billing outcome | `backend/server.py`, `docs/USER_WORKFLOWS.md` |
| W5 T+7 follow-up | Automated outreach to owners with no conversion signal | `VERIFIED` | Run outreach loop on eligible intro set | Outreach events recorded; owner can respond | Resend, outreach loop, intro data | External email delivery dependency | `backend/services/automation.py`, `backend/services/engine.py`, `docs/OPERATIONS.md` |
| W6 Trainer acquisition page | Public trainer value proposition and CTA to submit | `VERIFIED` | Open `/trainers` | Informational page with CTA to `/submit` | Frontend only | No strong in-product qualification flow before submission | `frontend/src/pages/Trainers.jsx`, `docs/WORKFLOW_TRACE_SHEET.md` |
| W7 Trainer submission | Create submission and auto-publish/hold | `VERIFIED` | Submit `/submit` with required consents | Held or published with status payload | `/api/submissions`, heuristics, MongoDB | Publish path is non-transactional across trainer + submission writes | `backend/server.py`, `frontend/src/pages/Submit.jsx` |
| W8 Intro billing lifecycle | Stripe invoice and webhook reconciliation | `VERIFIED` | Create billed intro and send matching Stripe webhook events | Billing collection status transitions update correctly | Stripe, webhook secret, intro rows | Contact release fails open even if Stripe is down | `backend/services/stripe_billing.py`, `backend/tests/test_w8_billing_unit.py` |
| W9 Oversight login | Passcode login to `/ops` | `VERIFIED` | `POST /api/oversight/login` with passcode | Auth success or 401/429 | `ADMIN_PASS`, auth_attempts collection | Shared secret only; no user identity | `backend/server.py`, `docs/WORKFLOW_TRACE_SHEET.md` |
| W10 Oversight monitoring | Read-only operations console | `VERIFIED` | Load `/ops` after login | Polling snapshot of health, revenue, loops, alerts, etc. | `/api/oversight`, frontend ops page | Local-only notes, no in-app case management | `frontend/src/pages/Ops.jsx`, `backend/server.py` |
| W11 Discovery contribution | Public candidate URL submission | `VERIFIED` | `POST /api/discovery` | Queue item created | Discovery queue, later processing loop | Public unauthenticated write surface; abuse risk | `backend/server.py`, `docs/WORKFLOW_TRACE_SHEET.md` |
| W12 Ranking and pricing loops | Continuous ranking/pricing updates | `VERIFIED` | Run scheduled loops | `trainers.outcome_score` and `pricing_state` update | Loop scheduler, MongoDB | In-process scheduler, no external queue system | `backend/services/engine.py`, `docs/ARCHITECTURE.md` |
| W13 Verification and discovery | Reverify listings, process queue, ingest sources | `VERIFIED` | Run verification/discovery/source loops | Listings verified or suppressed; queue progresses | Heuristic verifier, discovery queue, source URLs | Source ingestion failures are operationally recoverable but vendor/content dependent | `backend/services/engine.py`, `backend/services/automation.py` |
| W14 Inference / outreach / health | Promote inferred conversions, outreach, health alerts | `VERIFIED` | Run loops on prepared data | Inference, outreach, alerts, rollback markers | Loop scheduler, intros, conversions, config snapshots | Auto-rollback marks snapshots only; it does not revert infra | `backend/services/engine.py` |
| W15 Attribution entry | Demand acquisition attribution and cohorting | `VERIFIED` | Hit landing surfaces and attribution endpoint | Attribution entry and cohort rollups persist | Frontend landing pages, attribution endpoint | Not a substitute for full analytics warehouse | `backend/server.py`, `frontend/src/pages/CampaignLanding.jsx` |
| W16 Programmatic SEO | Generated SEO page plus attributed CTA handoff | `VERIFIED` | `GET /api/seo/{slug}` or open `/melbourne/:suburb` | SEO page generated or returned; attribution preserved | SEO generator, MongoDB, frontend suburb route | GET request mutates state by generating/storing page | `backend/server.py`, `frontend/src/pages/SuburbSEO.jsx` |
| W17 Submission status / activation | Trainer activation-state and blocker visibility | `VERIFIED` | Open `/submit/status/:submissionId` | Activation state, blockers, optional token returned | Submission records, trainer state | Knowing `submission_id` can mint trainer token for linked trainer | `backend/server.py`, `frontend/src/pages/SubmitStatus.jsx` |
| W18 Billing recovery | Retry and remediation handling for at-risk collection | `VERIFIED` | Observe `/ops` and run billing recovery loop | Retry states progress or remediation state is surfaced | Stripe, intros, retry loop | Some resolutions still require human support handling | `backend/services/engine.py`, `docs/OPERATIONS.md` |
| W19 Trainer reactivation | Diagnose and reactivate low-activity or blocked trainers | `VERIFIED` | Open `/trainer/reactivate` with valid token and submit | Trainer re-scored and publication may be restored | Trainer token, reactivation loop, scoring | Billing or verification blockers may still require technical-owner follow-up | `backend/server.py`, `frontend/src/pages/TrainerReactivate.jsx` |
| W21 Claim validation | Read-only public claim policy validation | `VERIFIED` | `GET /api/claims/validate` | Deterministic allow/block response | Backend policy evaluator | Internal/control feature, not public operator UI | `backend/server.py`, `docs/USER_WORKFLOWS.md` |

### Placeholder, hidden, manual, unsupported, or engineer-dependent functionality

| Area | Classification | Reality |
|---|---|---|
| Multi-user admin operations | `UNVERIFIED` | No admin CRUD console exists |
| Shared ops notes / case management | `MANUAL WORKAROUND` | `/ops` notes are local browser storage only |
| Structured support ticketing | `UNVERIFIED` | Support falls back to mailbox/manual handling |
| Deployment rollback | `MANUAL WORKAROUND` | Manual redeploy/recovery is documented; no automated rollback pipeline |
| Full public matching launch | `UNVERIFIED` | Matching-enabled release evidence remains open |
| Runtime auth migration to Clerk | `PLANNED` | Env/docs mention it, governance says current launch auth is passcode-only |

## 4. User Roles And Permissions

### Roles

| Role | Purpose | Current protection |
|---|---|---|
| Dog owner | Match, waitlist, connect, follow-up, engagement | Public routes plus consent checks |
| Trainer / submitter | Submit listing, check status, billing remediation, reactivate | Public submission; trainer token for billing/reactivation |
| Oversight operator / technical-owner mode | Same owner handles read-only operations visibility by default and boundary-crossing runtime, infra, deployment, DB, or policy actions when needed | Shared `ADMIN_PASS` for oversight plus out-of-band platform access for technical-owner actions |
| Autonomous system | Loops and internal mutations | Process ownership plus DB lease |
| External contributor / ecosystem actor | Feed discovery queue | Public `POST /api/discovery` |

### Permissions Matrix

| Role | Allowed actions | Restricted actions | Sensitive/destructive actions |
|---|---|---|---|
| Dog owner | Waitlist, match, connect, follow-up, engagement | No admin or config access | Conversion confirmation can affect revenue signals |
| Trainer / submitter | Submit listing, read submission status, billing reconnect, reactivate | No `/ops`, no runtime config | Billing profile changes and reactivation mutate trainer state |
| Oversight operator / technical-owner mode | Read `/ops`, sign in/out, use linked remediation routes, and when required restart services, rotate secrets, change env, deploy, or perform direct DB writes | No direct runtime mutation in `/ops`; boundary-crossing actions require switching into `technical-owner mode` | Shared passcode disclosure would expose oversight data; technical-owner actions can alter runtime policy, data integrity, domains, billing, or launch mode |
| Autonomous system | Update operational collections and derived state | No independent external governance approval | Automated loops can mutate ranking, pricing, health flags, and reactivation state |

### Actions that can cause irreversible or high-impact damage

| Action | Classification | Current safeguard |
|---|---|---|
| Direct DB edits for legal takedown/refund/discovery wipe | `VERIFIED` high-risk | Documented runbook only; requires the same owner in `technical-owner mode` |
| Runtime flag changes (`PUBLIC_MATCHING_ENABLED`, loop owner, billing mode) | `VERIFIED` high-risk | Governance policy and manual discipline; no product guardrail |
| Secret rotation / provider account changes | `VERIFIED` high-risk | Out-of-band platform access |
| Domain/TLS/hosting changes | `VERIFIED` high-risk | Out-of-band provider access |
| Trainer token misuse | `PARTIALLY VERIFIED` high-risk | HMAC token and context checks, but token issuance surface is broad |

### Safeguards against operator mistakes

| Safeguard | Classification | Notes |
|---|---|---|
| `/ops` is read-only | `VERIFIED` | Reduces accidental runtime mutation |
| Oversight lockout after failed pass attempts | `VERIFIED` | IP-based lockout exists |
| Hard operator boundary rule in docs | `VERIFIED` | Policy safeguard, not technical enforcement |
| Trainer action tokens for sensitive trainer lifecycle actions | `VERIFIED` | Better than public mutation, but still not equivalent to user auth |
| Shared per-operator identity, approval, or confirmation flow | `UNVERIFIED` | Not implemented |

### Workflows that still require engineering access

`VERIFIED`:
- service restart/redeploy
- env var changes
- billing mode or public matching mode changes
- DB repairs and manual writes
- domain/DNS/TLS changes
- vendor credential management
- debugging runtime crashes outside `/ops`

### Actions that are insufficiently protected

| Action | Classification | Why |
|---|---|---|
| Oversight access | `PARTIALLY VERIFIED` | Shared passcode only; no per-user identity |
| `GET /submissions/{submission_id}/status` token minting | `VERIFIED` risk | Knowledge of submission ID can produce trainer action token |
| Follow-up token handling | `VERIFIED` risk | Follow-up token is intro ID lookup rather than independent signed expiring token |
| Public write endpoints (`/discovery`, `/owner-waitlist`, `/attribution/entry`) | `VERIFIED` risk | No auth, limited abuse controls |

## 5. Operator Readiness And Non-Technical Workflows

### Overall assessment

`PARTIALLY VERIFIED`: Non-technical daily monitoring is well documented and meaningfully surfaced in `/ops`. Recovery and exception handling are not yet fully non-technical; many critical scenarios still require the same owner to switch into `technical-owner mode`.

### Operator Workflow Matrix

| Scenario | Trigger | Operator Action | Expected Outcome | Escalation Path | Requires Engineer? |
|---|---|---|---|---|---|
| Daily health review | Start/mid/end of day | Open `/ops`, review priority cards, log note | Current state understood and triaged | Escalate if alerts/loops/revenue trend trigger thresholds | `No` for routine monitoring |
| High-severity alert | `/ops` shows persistent `severity:high` | Refresh, confirm persistence, log context | Distinguish transient vs persistent issue | Immediate switch into `technical-owner mode` | `Yes` if alert persists |
| Stale loop | Loop older than 2x interval | Confirm in `/ops`, consult runbook | Determine if runtime is stale vs data delay | Same owner restarts runtime in `technical-owner mode` | `Yes` |
| At-risk revenue rising | `Revenue · at risk` rises across checks | Inspect billing queue and retry/remediation states | Identify collectible vs blocked cases | Trainer remediation plus `technical-owner mode` if persistent | `Sometimes` |
| Trainer billing blocker | `needs_remediation` or billing issue surfaced | Send trainer through `/trainer/billing` or support mailbox | Billing profile improved or case queued | Escalate if Stripe/config issue remains | `Sometimes` |
| Trainer reactivation weak | Reactivation return-to-active rate falls below threshold | Review reasons in `/ops`, direct trainer to reactivation or support path | Trainer either reactivated or escalated | `technical-owner mode` if issue is systemic or persistent | `Sometimes` |
| Discovery backlog rising | Discovery pending rises without recovery | Inspect source-ingestion detail and queue trend | Determine if source issue or runtime issue | `technical-owner mode` if suppression repeats or queue stalls | `Yes` if persistent |
| Owner/trainer support request | User reports broken path | Reproduce via public route and review `/ops` context | Basic user support or escalation | `technical-owner mode` if flow is broken | `Sometimes` |
| Notification delivery issue | Submission or intro notifications fail repeatedly | Review notification summary in `/ops`, use support mailbox | Determine whether delivery issue is localized | `technical-owner mode` for provider/config failures | `Yes` if systemic |
| Deployment anomaly | Public pages or API unavailable | Use runbook health probes | Determine if outage is domain/front/API | Same owner handles deploy/restart/recovery in `technical-owner mode` | `Yes` |

### What still requires engineering involvement

`VERIFIED`:
- restart backend/worker
- inspect supervisor or service logs
- recover from deploy/runtime misconfiguration
- investigate provider auth failures
- perform direct DB remediation
- rotate secrets
- reconcile infra/domain failures
- resolve broken CI/CD or deployment pipelines

### Risky or irreversible operator actions

`PARTIALLY VERIFIED`:
- trainer billing reconnect and reactivation are bounded but still mutate state
- support guidance is safe, but wrong advice can delay revenue recovery
- true irreversible/high-risk actions are correctly kept outside `/ops`, but then depend on technical owner

### Operational bottlenecks

| Bottleneck | Classification | Notes |
|---|---|---|
| Single founder handles ops and engineering | `VERIFIED` | Major continuity constraint |
| Support relies on one mailbox | `VERIFIED` | No case queue or multi-agent routing |
| Recovery depends on technical runbook execution | `VERIFIED` | Non-technical ops stop at escalation boundary |
| Shared ops notes are local-only | `VERIFIED` | No persistent team history |
| Incident detection outside `/ops` is limited | `PARTIALLY VERIFIED` | No mature external alert routing shown in repo |

### Undocumented or weakly documented knowledge

`PARTIALLY VERIFIED` gaps:
- formal restore procedure for production database
- provider account recovery procedure beyond password-manager assumption
- complete staging/promote/release workflow
- API-side telemetry/diagnostics beyond logs and `/ops`
- operational implications of local env drift vs canonical governance docs

### Can operations continue safely without the original developer?

`PARTIALLY VERIFIED`: Routine monitoring can continue from the docs and `/ops`. Incident recovery, environment changes, provider failures, deployment recovery, and many billing/auth/infrastructure issues remain founder-dependent.

## 6. Failure And Recovery Matrix

Estimated RTO/RPO values below are operational estimates, not contract-backed SLOs.

| Failure Scenario | Detection Method | User Impact | Recovery Procedure | Estimated Recovery Time | Requires Engineer? |
|---|---|---|---|---|---|
| API failure | Public route probe, `/api/` health probe, user reports | Full user-facing outage | Restart/redeploy backend, inspect logs | `PARTIALLY VERIFIED` 15-60 min if noticed | `Yes` |
| Loop owner failure / stale loops | `/ops` loop cards, `/api/oversight` freshness | Ranking, health, outreach, discovery, billing recovery degrade silently over time | Restore owner process, confirm lease/freshness | `PARTIALLY VERIFIED` 15-60 min if noticed | `Yes` |
| Frontend deployment failure | Public site check, Vercel route smoke | Public UI unavailable | Redeploy/repoint on Vercel | `PARTIALLY VERIFIED` 15-60 min | `Yes` |
| MongoDB / Atlas outage | API failures, widespread query errors | Core app outage, no reads/writes | Restore DB service, provider recovery, reconnect app | `UNVERIFIED` hours | `Yes` |
| Payment failure (`payment_failed`, `uncollectible`) | `/ops` billing summary and at-risk revenue | Revenue collection at risk, contact release already occurred | Billing recovery loop, trainer remediation, support escalation | `PARTIALLY VERIFIED` hours to days | `Sometimes` |
| Stripe webhook failure | Billing states stall, retry states do not progress | Collection visibility drifts from Stripe reality | Fix webhook config/auth, replay where possible | `PARTIALLY VERIFIED` hours | `Yes` |
| Resend / email delivery failure | Notification summary, outreach failure rows, support reports | Follow-up and notifications fail | Fix provider config/identity, rerun outreach later | `PARTIALLY VERIFIED` hours | `Yes` |
| Source ingestion failure | `/ops` source-ingestion detail, suppressed source counters | Supply growth stalls | Wait suppression expiry or fix source/provider issue | `PARTIALLY VERIFIED` hours to days | `Sometimes` |
| Discovery backlog / queue lag | Rising pending counts in `/ops` | New trainer intake slows | Restore discovery loop or investigate queue quality | `PARTIALLY VERIFIED` hours | `Yes` if persistent |
| Auth/passcode failure | Login 401/429, operator report | `/ops` inaccessible | Correct passcode or auth config, clear cause of lockout by time window | `PARTIALLY VERIFIED` minutes to hours | `Sometimes` |
| Trainer token misuse or broken token flow | Trainer route 401/404, support reports | Billing/remediation/reactivation blocked | Reissue via submission status or investigate token logic | `PARTIALLY VERIFIED` minutes to hours | `Sometimes` |
| CI/CD verification gap | Failing or absent automated checks | Bad changes can reach main with weak automation | Run local checks manually, fix workflow | `VERIFIED` ongoing risk | `Yes` |
| Domain/TLS issue | Public host checks, user reports | Site unavailable or certificate issues | Provider/domain recovery | `UNVERIFIED` hours | `Yes` |
| Heuristic scoring defect | Weird ranking or verification drift, operator observation | Match quality declines | Code/test fix plus redeploy | `UNVERIFIED` hours to days | `Yes` |

### Estimated RTO / RPO Summary

| Area | Estimated RTO | Estimated RPO | Classification |
|---|---|---|---|
| Frontend-only outage | 15-60 min | near-zero for persisted data | `PARTIALLY VERIFIED` |
| API/runtime outage | 15-60 min if noticed promptly | in-flight request loss only; persisted Mongo state survives | `PARTIALLY VERIFIED` |
| Billing/provider issue | hours to days | billing state drift until reconciliation | `PARTIALLY VERIFIED` |
| Database outage/corruption | hours to unbounded | `UNVERIFIED`; backup/restore not documented in repo | `UNVERIFIED` |

### Failures not automatically detectable or likely to go silent

`PARTIALLY VERIFIED` / `VERIFIED`:
- API-side exceptions outside worker Sentry coverage
- provider auth drift if not surfaced directly in `/ops`
- weak or stale secrets unless a feature actively fails
- local-only operator notes disappearing with browser reset
- data quality issues from public discovery or SEO generation spam
- degraded ranking quality from heuristic drift

### Failures with no complete documented recovery process

`UNVERIFIED`:
- full Atlas restore after corruption or destructive write
- credential compromise response plan for all providers
- formal incident commander / postmortem procedure
- automated replay strategy for missed webhook/event windows

### Failures most likely under real production load

`PARTIALLY VERIFIED`:
- public write surface abuse (`/discovery`, attribution, waitlist)
- provider/auth drift for billing/email/observability
- loop lag or stale owner if runtime restarts are incomplete
- noisy or duplicate data from heuristic discovery and non-transactional writes

## 7. Data And Database Profile

### Schema Overview

MongoDB is used as a schemaless primary store with app-level validation and selected unique indexes.

### Core Entities

| Entity / Collection | Purpose | Classification |
|---|---|---|
| `trainers` | Published trainer records and performance state | `VERIFIED` |
| `submissions` | Trainer intake and activation state | `VERIFIED` |
| `intros` | Contact-release and intro billing events | `VERIFIED` |
| `conversions` | Explicit and inferred outcomes | `VERIFIED` |
| `engagements` | Post-result and post-connect interaction signals | `VERIFIED` |
| `match_events` | Match request/result records | `VERIFIED` |
| `discovery_queue` | Candidate trainer URL queue | `VERIFIED` |
| `outreach_events` | T+7 follow-up send/response records | `VERIFIED` |
| `pricing_state` | Current intro pricing snapshots | `VERIFIED` |
| `system_state` | Loop heartbeats, health, summaries, lease, loop status | `VERIFIED` |
| `stripe_events` | Webhook idempotency and receipt records | `VERIFIED` |
| `audit_log` | Selected mutating action audit trail | `PARTIALLY VERIFIED` |
| `owner_waitlist` / `owner_waitlist_events` | Prelaunch owner demand capture | `VERIFIED` |
| `growth_attribution` / `attribution_entries` | Growth and cohort attribution | `VERIFIED` |
| `reactivation_candidates` | Trainer reactivation routing state | `VERIFIED` |
| `seo_pages` | Generated SEO content cache | `VERIFIED` |
| `source_ingestion_state` | Per-source suppression and failure state | `VERIFIED` |
| `auth_attempts` | Oversight login lockout state | `VERIFIED` |
| `config_snapshots` | Config change snapshots for health rollback markers | `PARTIALLY VERIFIED` |

### Critical Relationships

| Relationship | Notes | Classification |
|---|---|---|
| `submissions` -> `trainers` | Submission can auto-create trainer on publish | `VERIFIED` |
| `match_events` -> `intros` | Intro may reference `match_id` | `VERIFIED` |
| `intros` -> `conversions` | Conversions are keyed by `intro_id` | `VERIFIED` |
| `intros` -> `outreach_events` | Outreach and follow-up tied to intro | `VERIFIED` |
| `trainers` -> `reactivation_candidates` | Reactivation state derives from trainer condition | `VERIFIED` |
| `campaign/source` -> `growth_attribution` | Attribution rollups aggregate funnel progression | `VERIFIED` |

### Data Retention, Backup, Restore, Audit, Migration

| Topic | Assessment |
|---|---|
| Data retention policies | `UNVERIFIED`; no explicit retention schedule found |
| Backup strategy | `UNVERIFIED` in repo; Atlas implies provider backup options, but no restore SOP is documented |
| Restore strategy | `UNVERIFIED` |
| Audit logging approach | `PARTIALLY VERIFIED`; `audit_log` exists, but docs overstate coverage |
| Data validation | `VERIFIED` request-level Pydantic models and application logic |
| Migration process | `PARTIALLY VERIFIED`; Mongo schema evolves in code with no formal migration framework |

### Known data inconsistencies or integrity risks

| Risk | Classification | Notes |
|---|---|---|
| Non-transactional cross-collection writes | `VERIFIED` | Example: trainer publish and submission insert are best-effort, not atomic |
| Discovery duplicate creation | `VERIFIED` | Dedup is heuristic only |
| Read-side SEO generation writes data | `VERIFIED` | `GET /api/seo/{slug}` generates and stores a page |
| Seed-on-empty startup behavior | `VERIFIED` | Empty DB can auto-seed trainer/discovery data |
| Audit coverage gaps | `VERIFIED` | Not all state mutations write to `audit_log` |

### Manual database interventions currently documented

`VERIFIED` manual DB operations in runbooks:
- legal takedown of a listing
- refund state change
- wiping poisoned discovery batches

Evidence:
- `docs/OPERATIONS.md`

### Recovery risks if data corruption occurs

`UNVERIFIED` / `PARTIALLY VERIFIED`:
- no repo-documented restore runbook
- schemaless data model complicates repair
- no documented replay procedure for every derived collection
- startup seeding behavior creates risk if corruption is misinterpreted as empty dataset

## 8. Security And Access Control

### Current Authentication And Authorization Architecture

| Area | Current reality | Classification |
|---|---|---|
| Oversight auth | Shared `ADMIN_PASS` with IP-based lockout | `VERIFIED` |
| Trainer lifecycle auth | HMAC trainer action token with context and expiry | `VERIFIED` |
| Public user auth | None; consent and validation only | `VERIFIED` |
| Role model | Mostly policy-based in docs, not identity-backed in product | `PARTIALLY VERIFIED` |
| Clerk auth | Present in local env/docs as drift or future migration, not canonical launch auth | `PLANNED` |

### Secret Management And Environment Management

| Topic | Assessment |
|---|---|
| Intended secret policy | Password manager + local `.env` + provider env vars; do not commit secrets | `VERIFIED` |
| Git protection for `.env` files | `.env` files are ignored, untracked, and absent from git history | `VERIFIED` |
| Secret sprawl | Secrets/config are spread across root, frontend, and backend local `.env` files | `VERIFIED` |
| Frontend local env contains server-side secrets | `VERIFIED` local hygiene risk |
| Local auth-mode drift | Root and backend local `.env` files currently contain Clerk-oriented oversight settings even though governance and code truth for launch are passcode-based | `VERIFIED` |
| Local env drift vs governance/auth docs | `VERIFIED` |

### Admin Route Protections, Audit Trails, Data Protection

| Topic | Assessment |
|---|---|
| `/api/oversight` protection | `VERIFIED` passcode and lockout |
| `/ops` mutability | `VERIFIED` read-only server-side |
| Audit trail completeness | `PARTIALLY VERIFIED`; selected actions only |
| PII protection | `PARTIALLY VERIFIED`; data lives in Mongo and is exposed through functional endpoints as needed; no formal data-protection policy beyond route logic |

### Known security limitations

| Limitation | Classification | Why it matters |
|---|---|---|
| Shared passcode auth | `VERIFIED` | Weak operator accountability and broad compromise impact |
| `TRAINER_ACTION_TOKEN_SECRET` can fall back to `ADMIN_PASS` | `VERIFIED` | Couples unrelated trust domains |
| Submission-status route can mint trainer token | `VERIFIED` | Makes `submission_id` a sensitive bearer identifier |
| Follow-up token equals intro identifier | `VERIFIED` | Simpler than a dedicated signed outcome token |
| Public write endpoints are unauthenticated | `VERIFIED` | Abuse, spam, and data-pollution risk |
| Default/well-known example passcodes appear in docs/examples | `VERIFIED` | Raises misconfiguration and accidental weak-secret risk |
| CORS default is permissive in examples | `VERIFIED` | Fine for dev, weak as production default |

### Security hardening still pending

`PARTIALLY VERIFIED` / `PLANNED`:
- stronger operator auth than shared passcode
- per-operator identity and auditability
- removal of local env drift and secret sprawl
- stricter protections for submission status and follow-up token flows
- public write-surface abuse hardening
- consolidated secret rotation runbook

### What would likely fail a professional security audit today

`PARTIALLY VERIFIED` / `VERIFIED` likely findings:
- shared passcode instead of user-based operator auth
- local secret sprawl across multiple `.env` files
- public unauthenticated mutation endpoints without robust abuse controls
- weak linkage between some bearer identifiers and protected actions
- incomplete audit-log coverage
- lack of documented restore/incident/credential-compromise procedures

## 9. Observability And Monitoring

### Monitoring Stack

| System | Reality | Classification |
|---|---|---|
| `/ops` dashboard | Primary operational console | `VERIFIED` |
| `/api/oversight` | Aggregated truth endpoint for revenue, loops, alerts, queues, attribution, reactivation | `VERIFIED` |
| `system_state` | Loop/health persistence | `VERIFIED` |
| `audit_log` | Partial mutation trail | `PARTIALLY VERIFIED` |
| Logs | Standard Python logs and runtime/service logs | `PARTIALLY VERIFIED` |
| Sentry | Worker-side init exists; full API/frontend telemetry not proven in code reviewed | `PARTIALLY VERIFIED` |
| PostHog | Documented integration and frontend envs; runtime coverage not fully established here | `PARTIALLY VERIFIED` |
| Uptime monitoring | No dedicated uptime service found in repo | `UNVERIFIED` |
| Incident tracking | No structured incident system found in repo | `UNVERIFIED` |

### How operators are informed of failures

`VERIFIED`:
- `/ops` loop cards
- `/ops` alerts
- billing recovery summaries
- reactivation summary
- source-ingestion detail
- notification summaries
- public route/API manual smoke checks in runbook

### What events currently lack monitoring or are hard to diagnose

| Gap | Classification | Notes |
|---|---|---|
| Full API exception capture | `PARTIALLY VERIFIED` | Worker-side Sentry exists; API-side coverage is unclear |
| External provider auth drift | `PARTIALLY VERIFIED` | Not all provider failures are surfaced early in `/ops` |
| Credential compromise | `UNVERIFIED` | No dedicated alerting or rotation detection |
| Shared operator-note continuity | `VERIFIED` gap | Notes are local only |
| Deployment regression in frontend | `PARTIALLY VERIFIED` | Repo CI does not run frontend tests/build |
| Silent heuristic quality degradation | `PARTIALLY VERIFIED` | Some effects show in KPIs, but root cause diagnosis is manual |

### Failures that can occur silently

`PARTIALLY VERIFIED`:
- subtle ranking quality regressions
- partial notification degradation
- provider token drift until the relevant flow is exercised
- weak audit coverage for some automated mutations

### Monitoring gaps that create operational risk

`VERIFIED` / `PARTIALLY VERIFIED`:
- no durable/shared operator note system
- no dedicated uptime monitor documented
- thin CI confidence for frontend release quality
- no formal incident ticketing or on-call system
- no exported metrics system beyond `/ops` and logs

### Screenshots / examples

Screenshots were not attached in this artifact.

Available in-repo operational examples instead:
- `/ops` implementation: `frontend/src/pages/Ops.jsx`
- oversight payload contract tests: `backend/tests/test_public_mode_unit.py`
- live route smoke commands: `docs/governance/NEXT_SESSION_HANDOFF.md`

## 10. Infrastructure And Deployment Operations

### Deployment And Rollback Profile

| Topic | Assessment |
|---|---|
| Deployment process | `PARTIALLY VERIFIED`; manual CLI-driven deploy/redeploy evidence exists |
| Rollback process | `MANUAL WORKAROUND`; redeploy/rollback is operationally manual |
| CI/CD overview | `PARTIALLY VERIFIED`; GitHub Actions verify job exists but is limited |
| Environment management | `PARTIALLY VERIFIED`; runbooks and env examples exist, but real env drift is present locally |
| Domain/DNS ownership | `PARTIALLY VERIFIED`; documented as complete/live in runbook/governance |
| SSL/TLS management | `PARTIALLY VERIFIED`; documented as complete/live |
| Hosting configuration | `PARTIALLY VERIFIED`; production topology is documented but not fully codified as IaC |
| Scaling limitations | `PARTIALLY VERIFIED`; single loop owner, no queue broker, no documented scale testing |
| Infrastructure cost visibility | `UNVERIFIED`; no cost model or budget runbook found |

### Deployment questions answered explicitly

| Question | Answer |
|---|---|
| Can deployments be safely rolled back? | `PARTIALLY VERIFIED`: application/config rollbacks are manual; `config_snapshots` rollback only marks records, not infra rollback |
| What deployment steps are manual? | Vercel deploy/redeploy, provider/env updates, Render recovery, domain/TLS changes, many runbook verifications |
| Highest infrastructure failure risks | Render runtime loss, Atlas outage/corruption, domain/TLS drift, Vercel misrouting, provider auth drift |
| Scaling bottlenecks | In-process loops, Mongo-backed pseudo-queues, single loop owner, no documented horizontal scale test |
| Insufficiently documented processes | full staging model, rollback automation, restore operations, cost controls, provider access recovery detail |

### CI/CD Reality

`VERIFIED` from `.github/workflows/verify.yml`:
- Workflow runs on pull requests and pushes except `main`
- Backend job compiles Python and runs only selected backend tests
- Frontend job only prints package metadata; it does not build or test the frontend

Operational implication:
- Local evidence is stronger than CI evidence
- `main` can diverge from verified frontend release assumptions

## 11. Known Limitations / Technical Debt

| Item | Classification | Notes |
|---|---|---|
| Public matching still gated off in live prelaunch mode | `VERIFIED` | Matching-enabled release evidence remains open |
| Shared passcode oversight auth | `VERIFIED` | Weak operational security model |
| Trainer token issuance via submission status | `VERIFIED` | Sensitive bearer surface |
| Follow-up token design | `VERIFIED` | Intro ID is used directly |
| In-process loop scheduler instead of dedicated worker infrastructure | `PARTIALLY VERIFIED` | Fine for low scale; weak for serious scale |
| No dedicated queue broker | `VERIFIED` | Mongo collections used as queue surfaces |
| Manual deployment and rollback | `VERIFIED` | Runbook-heavy |
| Thin frontend CI/test coverage | `VERIFIED` | Frontend helper tests exist; route/page coverage is thin |
| Docs/UI/runtime drift in several places | `VERIFIED` | Especially auth, monetization copy, operator note semantics |
| Local secret sprawl across ignored `.env` files | `VERIFIED` | Not synced to git, but still a local operational risk |
| Seed-on-empty startup behavior | `VERIFIED` | Dangerous if production DB starts empty/mispointed |
| Partial audit-log coverage | `VERIFIED` | Docs overstate mutation auditing |
| No formal restore/backup runbook in repo | `UNVERIFIED` | Critical business continuity gap |
| No mature incident-management process | `UNVERIFIED` | No ticketing/on-call/postmortem system found |

### What would most likely fail under scale

`PARTIALLY VERIFIED` likely first failures under real scale:
- in-process loop scheduling and lease model under higher concurrency
- Mongo-backed queue patterns and unbounded public write surfaces
- heuristic duplicate detection and content ingestion quality
- manual support/recovery processes
- weak CI/CD for frontend regressions

### Areas least production-ready

`VERIFIED` / `PARTIALLY VERIFIED`:
- security/access control model
- business continuity without founder
- restore/recovery maturity
- deploy rollback automation
- shared operational case management

## 12. Operational Dependency And Ownership Profile

| System/Service | Owner | Access Recovery Method | Criticality | Failure Impact |
|---|---|---|---|---|
| Domain/DNS/TLS | Founder / provider account owner | Provider account recovery + password manager | `CRITICAL` | Public site unavailable or misconfigured |
| Vercel frontend | Founder | Vercel account/CLI access recovery | `CRITICAL` | Public site unavailable |
| Render backend/worker | Founder | Render account/API key recovery | `CRITICAL` | API or loops unavailable |
| MongoDB Atlas | Founder | Atlas account/API/DB credential recovery | `CRITICAL` | Data plane outage or integrity loss |
| Stripe | Founder | Stripe dashboard/API access recovery | `HIGH` | Billing collection degraded |
| Resend | Founder | Resend account/API access recovery | `HIGH` | Outreach and notification failures |
| Sentry | Founder | Sentry org/token recovery | `MEDIUM` | Diagnosis worsens |
| PostHog | Founder | PostHog project/token recovery | `MEDIUM` | Analytics blind spots |
| GitHub / CI | Founder | GitHub account recovery | `MEDIUM` | Reduced delivery confidence |
| Support mailbox | Founder / mailbox owner | Mail provider account recovery | `HIGH` | Support and remediation path breaks |
| Clerk | Founder | Clerk account recovery | `LOW` for current launch | Current canonical launch auth should not depend on it |

### Explicit ownership-risk answers

| Question | Answer |
|---|---|
| What systems are single points of failure? | Founder access, Vercel, Render, Atlas, support mailbox, single active loop owner model |
| What access risks exist? | Secret sprawl, local env drift, passcode-centric ops auth, undocumented recovery playbooks, vendor concentration |
| What knowledge remains founder-dependent? | Deploy/recover steps, provider troubleshooting, DB intervention judgment, launch-go decision, credential governance |
| What happens if access is lost? | Recovery is slow or blocked because no redundant operator or documented delegation chain exists |
| What lacks redundancy? | Human ownership, support inbox, vendor topology, loop-owner runtime, DB layer |

## 13. Launch Readiness Declaration

### Readiness Matrix

| Category | Status | Evidence | Remaining Risks |
|---|---|---|---|
| Feature completeness | `PARTIALLY VERIFIED` | W1-W21 marked complete; code/test evidence strong | Matching-enabled release evidence still open; some UX/doc drift remains |
| Operational readiness | `PARTIALLY VERIFIED` | `/ops`, runbooks, billing recovery, reactivation workflows exist | Recovery still requires technical-owner intervention |
| Monitoring readiness | `PARTIALLY VERIFIED` | `/ops`, `system_state`, health alerts, limited Sentry/PostHog docs | No mature external alerting/uptime/incident system |
| Security readiness | `PARTIALLY VERIFIED` leaning weak | Passcode lockout and trainer tokens exist | Shared passcode, broad public write surfaces, token issuance risks, env sprawl |
| Operator readiness | `PARTIALLY VERIFIED` | Non-technical routine is documented and reflected in `/ops` | Non-routine recovery is not non-technical |
| Deployment readiness | `PARTIALLY VERIFIED` | Manual deploy/redeploy evidence exists | Rollback and CI/CD maturity are limited |
| Support readiness | `PARTIALLY VERIFIED` | Single support mailbox, remediation pages exist | No ticketing/case workflow, founder-dependent |
| Scalability readiness | `UNVERIFIED` | No serious scale evidence found | In-process loops and Mongo queue patterns likely bottleneck first |
| Billing/payment readiness | `PARTIALLY VERIFIED` | Stripe path, webhook reconciliation, retry loop, tests | Contact release is fail-open; provider config must remain correct |
| Recovery readiness | `PARTIALLY VERIFIED` leaning weak | Some recovery SOPs exist | No restore runbook, no formal incident management, manual-heavy remediation |

### Explicit recommendation

| Decision question | Answer |
|---|---|
| Is full production launch currently recommended? | `No` for full public launch under the repo's own launch definition |
| Is prelaunch production operation defensible? | `Yes, with caveats`: current waitlist-mode production deployment is already supportable as a controlled prelaunch surface |

### Remaining blockers

`VERIFIED` blockers from current governance:
- explicit `Final Go/No-Go` not yet recorded
- required sustained launch evidence window not yet completed
- matching-enabled public-path release evidence still open while live runtime remains gated

### Remaining unresolved operational risks

`VERIFIED` / `PARTIALLY VERIFIED`:
- founder as operational and technical SPOF
- weak operator auth model
- no robust restore/backup procedure in repo
- manual deploy/recovery path
- thin CI/CD for frontend release confidence
- local env/config drift and secret sprawl

### Assumptions still requiring validation

`PARTIALLY VERIFIED`:
- low enough scale for current loop and queue model
- operator can manage incidents through docs and `/ops` without engineering burnout
- provider credentials/config remain correct across all live systems
- matching-enabled public launch behaves as expected in production, not just tests

## 14. Required Supporting Materials

The following supporting materials exist in the repo or are partially available:

| Material | Location | Availability |
|---|---|---|
| Architecture diagram / system model | `docs/ARCHITECTURE.md` | `VERIFIED` |
| SOPs / runbooks | `docs/OPERATIONS.md`, `docs/DEPLOYMENT.md`, `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` | `VERIFIED` |
| Infrastructure / deployment documentation | `docs/DEPLOYMENT.md`, `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` | `VERIFIED` |
| API documentation | Route definitions in `backend/server.py`; no separate OpenAPI artifact maintained in docs | `PARTIALLY VERIFIED` |
| Feature inventory | `docs/USER_WORKFLOWS.md`, `docs/WORKFLOW_TRACE_SHEET.md` | `VERIFIED` |
| Admin/operator guide | `docs/OPERATIONS.md` and `/ops` implementation | `VERIFIED` |
| Escalation procedures | `docs/OPERATIONS.md` | `VERIFIED` |
| Monitoring screenshots | Not attached in repo | `UNVERIFIED` |
| Error-tracking screenshots | Not attached in repo | `UNVERIFIED` |
| Queue/dashboard screenshots | Not attached in repo | `UNVERIFIED` |
| Environment inventory | `.env.example`, `backend/.env.example`, `frontend/.env.example`, `docs/governance/INTEGRATION_CREDENTIALS_RUNBOOK.md` | `PARTIALLY VERIFIED` |
| Launch checklist | `docs/governance/ROADMAP.md`, `docs/governance/LOCK_STATE.md`, `docs/governance/NEXT_SESSION_HANDOFF.md` | `VERIFIED` |

## 15. Final Declaration

### What parts are genuinely production-ready today

`VERIFIED` / `PARTIALLY VERIFIED`:
- public frontend delivery in current prelaunch mode
- production API reachability
- deterministic matching/waitlist/trainer lifecycle code paths
- intro billing code path and webhook reconciliation logic
- background automation loops and oversight aggregation
- read-only operator visibility through `/ops`
- domain/TLS and manual deploy/redeploy evidence

### What still depends on engineering intervention

`VERIFIED`:
- service restarts and runtime recovery
- deployment rollback/redeploy
- environment and secret changes
- DB repair or manual data correction
- provider auth/config issues
- incident diagnosis beyond what `/ops` shows
- any launch-mode or policy change

### What operational risks remain unresolved

`VERIFIED` / `PARTIALLY VERIFIED`:
- final launch evidence window is incomplete
- public matching-enabled release evidence is still missing
- passcode-only operator auth is weak
- local auth configuration is drifted enough to create operator confusion or misdeployment if `.env` values are treated as truth over governance docs
- founder/vendor concentration is high
- backup/restore maturity is under-documented
- frontend CI coverage is too thin for high confidence launch governance
- local secret/config sprawl increases human error and exposure risk

### What assumptions currently exist about user behavior, scale, reliability, and operator competency

`PARTIALLY VERIFIED` assumptions:
- user volume remains modest enough for current loop and queue approach
- operators can identify serious issues from `/ops` without formal incident tooling
- providers remain healthy and correctly configured
- public matching can be enabled later without uncovering major release-only regressions
- operator competency is sufficient to triage but not necessarily to recover independently

### What would most likely fail first under real-world usage

`PARTIALLY VERIFIED` likely first failure points:
- operational recovery process rather than core code path
- public write-surface abuse or noisy discovery data
- weak CI/CD letting a frontend regression through
- provider auth/config drift in Stripe, Resend, or telemetry
- founder response bandwidth under simultaneous support and technical incidents

### What areas represent the greatest business continuity risk

`VERIFIED`:
- founder as the single human owner of operations, engineering, and approvals
- lack of documented restore and delegated access procedures
- shared passcode operational model
- single support mailbox and vendor concentration

### What areas currently lack sufficient operational maturity

`VERIFIED` / `PARTIALLY VERIFIED`:
- security hardening and access control
- formal recovery/restore operations
- CI/CD and rollback automation
- multi-operator support workflows and case tracking
- scaling evidence
- sustained live launch evidence for the matching-enabled public path

## Executive Bottom Line

The application is technically substantial, unusually well documented for a solo project, and locally well validated. It is not yet fully launch-ready by its own governance standard.

The repo supports a credible controlled prelaunch operation in waitlist mode.

It does not yet support an unqualified declaration of full public production readiness because the remaining gap is no longer mostly feature implementation. The remaining gap is operational maturity, final live evidence, stronger access-control confidence, and lower founder dependence.
