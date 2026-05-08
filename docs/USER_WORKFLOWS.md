# User Workflow Catalog

## Understanding Lock
- Goal: identify all project workflows and organize them by user type.
- Scope: current implemented product surfaces (`frontend/src/pages/*`) plus active API workflows (`backend/server.py`) and autonomous loops documented in architecture.
- Exclusions: deprecated legacy `/admin/*` and directory browse/list endpoints (explicitly removed).

## Workflow Inventory By User Type

Technical skeleton companion:
- See `docs/WORKFLOW_TRACE_SHEET.md` for per-workflow route -> function -> DB -> event traceability and implementation status.

### 1) Dog owner (primary end user)

#### W1. Match request (core demand-capture flow)
- Scope: discover trainers from one problem statement.
- Entry: owner opens `/` and submits issue text with consent.
- Main path:
  1. Load config (`GET /api/config`) for suburbs/active region.
  2. Submit request (`POST /api/match`) with description + optional suburb + consent.
  3. Receive up to 3 ranked trainer matches.
- Exit outcomes:
  - Success: ranked results rendered, `match_id` created.
  - Failure: validation/processing error toast; user retries.
- Surfaces: `/`, `/how-it-works`, `/faq`, `/trust`.

#### W2. Connect to trainer (conversion gateway)
- Scope: release contact details and create intro record.
- Entry: owner clicks Connect from match result (`/t/:id`).
- Main path:
  1. Load trainer (`GET /api/trainers/{id}`).
  2. Submit contact form + 2 consents (`POST /api/intros`).
  3. Intro is fraud-evaluated, billed/suppressed, and contact details returned.
- Exit outcomes:
  - Success: contact card shown (website/phone/email).
  - Failure: trainer not found, consent missing, or request error.
- Surfaces: `/t/:id`, `/trainers/:id`.

#### W3. Post-connect engagement signals
- Scope: quality signals after contact reveal.
- Entry: owner clicks trainer contact actions.
- Main path:
  1. Website/phone/email click tracked (`POST /api/engagements`).
  2. If 2+ distinct engagement kinds, inferred conversion may be created.
- Exit outcomes:
  - Signals logged for ranking/inference.

#### W4. Outcome confirmation
- Scope: explicit hire confirmation.
- Entry: owner clicks “I hired them”.
- Main path:
  1. Submit conversion (`POST /api/conversions`).
  2. System marks tracked/billed/suspicious (mode + fraud dependent).
- Exit outcomes:
  - First confirmation recorded.
  - Repeat confirmations idempotently ignored.

#### W5. T+7 follow-up response loop (owner re-engagement)
- Scope: re-contact owners with no conversion signal after 7 days.
- Entry: intro older than 7 days, no conversion, user_email present.
- Main path:
  1. Automated outreach email sent by loop (`services/automation.py`).
  2. Owner can return and complete W4.
- Exit outcomes:
  - Follow-up sent (or failed) and logged in `outreach_events`.

### 2) Trainer / business submitter

#### W6. Trainer acquisition and qualification entry
- Scope: attract trainer interest and route qualified supply to submission.
- Entry: trainer visits `/trainers` or trainer CTAs from public pages.
- Main path:
  1. Read pay-on-outcome model.
  2. Click through to `/submit` or support email.
- Exit outcomes:
  - Proceeds to submission or support.

#### W7. Listing submission, decision, and activation start
- Scope: create/verify listing with no manual review and begin onboarding activation.
- Entry: submitter posts form on `/submit` with required consents.
- Main path:
  1. Submit profile (`POST /api/submissions`).
  2. AI confidence score determines outcome:
     - `>= 0.85`: auto-published as verified.
     - `0.60 - 0.849`: auto-published as unverified.
     - `< 0.60`: held.
  3. If published, billing profile provisioning is attempted.
- Exit outcomes:
  - Published with `trainer_id` and public detail page.
  - Held with reasoning.

#### W8. Trainer monetization lifecycle
- Scope: trainer-side billing and collection lifecycle after intros.
- Entry: owner creates billed intro for trainer.
- Main path:
  1. Intro fee metered on `POST /api/intros`.
  2. Stripe invoice creation/sending attempted fail-soft.
  3. Stripe webhook reconciles invoice state (`POST /api/stripe/webhook`).
- Exit outcomes:
  - Intro billing status updated (`invoice_sent`, `paid`, `failed`, etc.).

### 6) Growth + lifecycle operations (cross-actor, partially implemented)

#### W15. Demand acquisition and attribution
- Scope: track how demand arrives before W1 demand capture.
- Entry: external traffic source lands on public pages (`/`, `/how-it-works`, `/pricing`, `/faq`).
- Main path:
  1. User enters through channel-driven landing surface.
  2. User proceeds to W1 match request.
  3. Attribution evidence is retained for channel performance analysis.
- Exit outcomes:
  - Attributed demand-source visibility for top-of-funnel traffic.

#### W16. Programmatic SEO and nurture loop
- Scope: generate and reuse SEO surfaces for ongoing demand generation.
- Entry: user lands on generated SEO pages (`/seo/{slug}` backend surface + routed frontend pages).
- Main path:
  1. SEO copy is generated/cached on demand (`GET /api/seo/{slug}`).
  2. Visitor follows CTA path into W1/W2 flows.
  3. Follow-up or nurture pathways are measured for optimization.
- Exit outcomes:
  - Search-sourced demand path is measurable and improvable.

#### W17. Trainer onboarding completion and activation
- Scope: advance newly submitted trainers from publish decision to intro-ready state.
- Entry: W7 publish result + billing readiness outcomes.
- Main path:
  1. Submission publishes as verified/unverified or holds.
  2. Billing profile state (`ready`, `profile_incomplete`, etc.) is set.
  3. Trainer progresses toward first-intro readiness and activation.
- Exit outcomes:
  - Trainer reaches intro-eligible state or enters remediation path.

#### W18. Revenue recovery and billing remediation
- Scope: recover revenue when collection path degrades.
- Entry: failed/uncollectible/disputed/profile-incomplete invoice outcomes.
- Main path:
  1. Billing states are observed via webhook and oversight.
  2. Recovery actions are triggered (notify, fix profile, retry policy, or suppress).
  3. Recovered rows return to collectible path or move to at-risk reporting.
- Exit outcomes:
  - Revenue risk and recovery are explicit and measurable.

#### W19. Trainer reactivation and retention
- Scope: re-activate low-activity or billing-blocked trainers.
- Entry: low activity, repeated suppression, or billing failure patterns.
- Main path:
  1. Detect reactivation candidates from oversight and loop outputs.
  2. Trigger remediation sequence (listing refresh, billing repair, outreach).
  3. Return trainer to intro-ready/active state.
- Exit outcomes:
  - Recoverable trainers re-enter live demand flow.

### 3) Oversight operator (internal observer)

#### W9. Oversight authentication
- Scope: access read-only system console.
- Entry: operator opens `/ops` and enters passcode.
- Main path:
  1. Login check (`POST /api/oversight/login`).
  2. Passcode stored client-side for session header.
- Exit outcomes:
  - Authenticated oversight session or rejection.

#### W10. Continuous oversight monitoring
- Scope: monitor autonomous engine health and business KPIs.
- Entry: authenticated `/ops` session.
- Main path:
  1. Poll snapshot every 15s (`GET /api/oversight` with `X-Admin-Pass`).
  2. Review revenue, throughput, trust signals, loops, pricing state, top trainers, audit feed.
  3. Optional manual refresh; sign out clears session.
- Exit outcomes:
  - Operational visibility only (no mutation controls).

### 4) External contributor / ecosystem actor

#### W11. Discovery queue contribution
- Scope: feed candidate trainer URLs.
- Entry: external actor calls public discovery endpoint.
- Main path:
  1. Submit URL + hints (`POST /api/discovery`).
  2. Item enters `discovery_queue` as pending.
- Exit outcomes:
  - Queue item accepted for autonomous processing.

### 5) Autonomous system actor (non-human user type)

#### W12. Ranking and pricing adaptation
- Scope: keep matching and fee signals current.
- Entry: scheduled loops.
- Main path:
  1. Recompute ranking every 60s.
  2. Recompute suburb intro pricing every 90s.
- Exit outcomes:
  - Updated `trainers.outcome_score` and `pricing_state`.

#### W13. Verification and discovery ingestion
- Scope: maintain listing quality and supply.
- Entry: scheduled loops + pending queue.
- Main path:
  1. Reverify listings on cadence.
  2. Process `discovery_queue` to promote/discard/duplicate.
  3. Optionally ingest configured source URLs into queue.
- Exit outcomes:
  - Listing status maintained; new candidates promoted where valid.

#### W14. Conversion inference, outreach, and health protection
- Scope: infer outcomes, collect lagging signals, protect system integrity.
- Entry: scheduled loops and health thresholds.
- Main path:
  1. Promote high-confidence inferred conversions after 48h.
  2. Send T+7 outreach for missing outcomes.
  3. Run health checks and emit alerts/auto-rollback markers.
- Exit outcomes:
  - More complete outcome signal set and stabilized ops state.

## Workflow Scope Map (quick grouping)
- `Demand generation`: W15, W16.
- `Demand capture`: W1.
- `Supply capture`: W6, W11.
- `Activation`: W2, W7, W9.
- `Engagement`: W3, W10.
- `Outcome/Revenue`: W4, W8, W18.
- `Retention/Reactivation`: W5, W19.
- `Supply growth`: W13, W17.
- `Autonomous optimization`: W12, W14.

## Decision Log
- Chosen actor model includes human and non-human actors because the product is explicitly autonomous.
- Legacy admin CRUD workflows are excluded by design; endpoints are removed and routes redirect to `/ops`.
- Trainer lifecycle is split across supply capture (W6/W7), onboarding completion (W17), monetization lifecycle (W8/W18), and reactivation (W19).

## Execution Readiness
- Design artifact completeness: complete (Understanding Lock + workflow map + decision log).
- Technical traceability: complete via `docs/WORKFLOW_TRACE_SHEET.md`.
- Current implementation status: mixed (`complete` + `partial` + `planned` + `missing`), no fully broken core workflow paths identified in existing implemented routes.
- Next step: execute the priority fix queue from `docs/WORKFLOW_TRACE_SHEET.md` to move all partial workflows to complete.
