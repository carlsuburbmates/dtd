# User Workflow Catalog

## Understanding Lock
- Goal: identify all project workflows and organize them by user type.
- Scope: current implemented product surfaces (`frontend/src/pages/*`) plus active API workflows (`backend/server.py`) and autonomous loops documented in architecture.
- Exclusions: deprecated legacy `/admin/*` and directory browse/list endpoints (explicitly removed).
- Mode lock note (2026-05-20): home entry behavior is enforced via `PUBLIC_MATCHING_ENABLED` (`/api/config` + `Home.jsx`) while owner/trainer lifecycle routes and APIs still exist in code.

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

#### W20. Owner waitlist enrollment (prelaunch demand capture)
- Scope: capture owner demand while public matching is gated.
- Entry: owner submits waitlist form on `/` (when `PUBLIC_MATCHING_ENABLED=false`) or campaign-driven entry (`/lp/:campaign`).
- Main path:
  1. Submit waitlist (`POST /api/owner-waitlist`) with email, suburb, consent, campaign/source metadata.
  2. System records normalized lifecycle events (`started`, `submitted`, `duplicate`, `rejected`).
- Exit outcomes:
  - Accepted waitlist enrollment.
  - Duplicate acknowledgement.
  - Rejected enrollment with explicit reason codes.
- Surfaces: `/`, `/lp/:campaign`.

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
- Entry: owner uses follow-up outcome action (`/follow-up/:token`) or explicit conversion API call.
- Main path:
  1. Submit follow-up outcome (`POST /api/follow-up/{token}/outcome`, action=`hired`) or direct conversion (`POST /api/conversions`).
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
- Current status: complete (webhook lifecycle outcomes, idempotency path, and oversight billing semantics are test-backed and documented).

### 6) Growth + lifecycle operations (cross-actor, implemented)

#### W15. Demand acquisition and attribution
- Scope: track how demand arrives before W1 demand capture.
- Entry: external traffic source lands on public pages (`/`, `/how-it-works`, `/pricing`, `/faq`).
- Main path:
  1. User enters through channel-driven landing surface or campaign page (`/lp/:campaign`, `/melbourne/:suburb`, query-attributed `/`).
  2. Frontend posts attribution entry (`POST /api/attribution/entry`) and forwards campaign/source metadata into waitlist or match flows.
  3. Attribution evidence is retained in `attribution_entries` / `growth_attribution` for channel performance analysis.
- Exit outcomes:
  - Attributed demand-source visibility for top-of-funnel traffic.
- Attribution schema:
  - `attribution_entries`: immutable entry events keyed by `kind`, `campaign`, `source`, `suburb`, `path`, `session_id`, `created_at`
  - `growth_attribution`: cohort rollup keyed by `campaign + source` with `entry_events_30d`, `waitlist_joins_30d`, `matched`, `connected`, `converted`, `remarketing_candidates`, `conversion_gap_candidates`
- Reporting surface:
  - `/ops` exposes `growth_attribution_summary` totals and top cohorts.
- Current status: complete (canonical entry writes, schema, and reporting surface are implemented and evidenced).

#### W16. Programmatic SEO and nurture loop
- Scope: generate and reuse SEO surfaces for ongoing demand generation.
- Entry: user lands on generated SEO pages (`/seo/{slug}` backend surface + routed frontend pages).
- Main path:
  1. SEO copy is generated/cached on demand (`GET /api/seo/{slug}`).
  2. SEO landing posts an attribution entry and forwards campaign/source metadata into the home CTA path.
  3. Growth nurture cohorts aggregate campaign/source performance for remarketing and conversion-gap review.
- Exit outcomes:
  - Search-sourced demand path is measurable and improvable.
- Measured path:
  1. `GET /api/seo/{slug}` generates or loads the SEO page.
  2. `/melbourne/:suburb` posts `seo_landing` attribution.
  3. SEO CTA forwards `campaign/source/utm_*` into `/`.
  4. Home propagates those fields into waitlist or match requests.
  5. Match, intro, conversion, and nurture reporting preserve the SEO cohort.
- Reporting surface:
  - `/ops` exposes SEO-attributed cohorts through `growth_attribution_summary`.
- Current status: complete (SEO entry, CTA propagation, attribution carry-through, and nurture reporting path are documented and test-backed).

#### W17. Trainer onboarding completion and activation
- Scope: advance newly submitted trainers from publish decision to intro-ready state.
- Entry: W7 publish result + billing readiness outcomes.
- Main path:
  1. Submission publishes as verified/unverified or holds.
  2. Billing profile state (`ready`, `profile_incomplete`, etc.) is exposed through `/submit/status/:submissionId` with deterministic `activation_state` and blocker codes.
  3. Trainer can enter billing remediation via `/trainer/billing`, and live trainer billing state feeds back into submission status.
- Activation states:
  - `held_for_review`
  - `pending_autonomous_review`
  - `needs_billing_profile`
  - `needs_billing_consent`
  - `billing_system_blocked`
  - `intro_ready`
- Exit outcomes:
  - Trainer reaches intro-eligible state or enters remediation path.
- Current status: complete (submission-status transitions and billing recovery path are deterministic and test-backed).

#### W18. Revenue recovery and billing remediation
- Scope: recover revenue when collection path degrades.
- Entry: failed/uncollectible/disputed/profile-incomplete invoice outcomes.
- Main path:
  1. Billing states are observed via webhook and oversight.
  2. Recovery loop applies bounded retry/backoff policy and marks rows as `retry_sent`, `retry_failed`, `retry_exhausted`, or `needs_remediation`.
  3. Operator uses `/trainer/billing` and `/ops` to distinguish collectible recovery from at-risk/remediation states.
- Exit outcomes:
  - Revenue risk and recovery are explicit and measurable.
- Current status: complete (bounded retry policy, operator actions, and retry-state tests are in place).

#### W19. Trainer reactivation and retention
- Scope: re-activate low-activity or billing-blocked trainers.
- Entry: low activity, repeated suppression, or billing failure patterns.
- Main path:
  1. Detect reactivation candidates from oversight and loop outputs.
  2. Trigger remediation sequence (listing refresh, billing repair, outreach).
  3. Track resolved candidates and `active_after_resolution_7d` return-to-active outcomes in oversight.
- Exit outcomes:
  - Recoverable trainers re-enter live demand flow.
- Success criteria:
  - Monitor: fewer than 5 resolved cases in 7 days, or return-to-active rate is at least 50%.
  - Investigate: 5 or more resolved cases in 7 days and return-to-active rate falls below 50%.
  - Escalate: return-to-active rate falls below 25% across two consecutive daily checks, or open candidates rise while resolved stays flat.
- Current status: complete (`/trainer/reactivate` APIs/UI, return-to-active measurement, and operator success thresholds are now aligned).

#### W21. Public claim validation control
- Scope: deterministic validation for public claim wording under claim-state policy.
- Entry: internal or external caller hits read-only claim validation endpoint.
- Main path:
  1. Validate claim against current state (`GET /api/claims/validate`).
  2. Evaluate allow/block using configured enforcement mode.
- Exit outcomes:
  - Allowed claim with policy reason codes.
  - Blocked claim (`403`) when enforcement mode is `block_invalid`.
- Current status: complete (read-only policy endpoint implemented).

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
- Current status: complete (failure reason codes, suppression/remediation path, loop-heartbeat writes, and failure-to-recovery behavior are test-backed).

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
- `Demand generation`: W15, W16, W20.
- `Demand capture`: W1.
- `Supply capture`: W6, W11.
- `Activation`: W2, W7, W9.
- `Engagement`: W3, W10.
- `Outcome/Revenue`: W4, W8, W18.
- `Retention/Reactivation`: W5, W19.
- `Supply growth`: W13, W17.
- `Autonomous optimization`: W12, W14.
- `Policy controls`: W21.

## Decision Log
- Chosen actor model includes human and non-human actors because the product is explicitly autonomous.
- Legacy admin CRUD workflows are excluded by design; endpoints are removed and routes redirect to `/ops`.
- Trainer lifecycle is split across supply capture (W6/W7), onboarding completion (W17), monetization lifecycle (W8/W18), and reactivation (W19).

## Execution Readiness
- Design artifact completeness: complete (Understanding Lock + workflow map + decision log).
- Technical traceability: complete via `docs/WORKFLOW_TRACE_SHEET.md`.
- Current implementation status: complete for W1-W21 (no `partial`, `planned`, `missing`, or `broken` rows in the workflow trace sheet).
- Next step: maintain completeness with regression checks and governance evidence updates whenever workflow-affecting changes are introduced.
