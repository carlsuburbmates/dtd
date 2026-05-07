# User Workflow Catalog

## Understanding Lock
- Goal: identify all project workflows and organize them by user type.
- Scope: current implemented product surfaces (`frontend/src/pages/*`) plus active API workflows (`backend/server.py`) and autonomous loops documented in architecture.
- Exclusions: deprecated legacy `/admin/*` and directory browse/list endpoints (explicitly removed).

## Workflow Inventory By User Type

### 1) Dog owner (primary end user)

#### W1. Match request (core acquisition flow)
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

#### W6. Trainer education and intent capture
- Scope: communicate model and route to submission.
- Entry: trainer visits `/trainers` or trainer CTAs from public pages.
- Main path:
  1. Read pay-on-outcome model.
  2. Click through to `/submit` or support email.
- Exit outcomes:
  - Proceeds to submission or support.

#### W7. Listing submission and auto-decision
- Scope: create/verify listing with no manual review.
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

#### W8. Passive trainer monetization lifecycle
- Scope: trainer-side billing events after intros.
- Entry: owner creates billed intro for trainer.
- Main path:
  1. Intro fee metered on `POST /api/intros`.
  2. Stripe invoice creation/sending attempted fail-soft.
  3. Stripe webhook reconciles invoice state (`POST /api/stripe/webhook`).
- Exit outcomes:
  - Intro billing status updated (`invoice_sent`, `paid`, `failed`, etc.).

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
- `Acquisition`: W1, W6.
- `Activation`: W2, W7, W9.
- `Engagement`: W3, W10.
- `Outcome/Revenue`: W4, W8.
- `Retention/Reactivation`: W5.
- `Supply growth`: W11, W13.
- `Autonomous optimization`: W12, W14.

## Decision Log
- Chosen actor model includes human and non-human actors because the product is explicitly autonomous.
- Legacy admin CRUD workflows are excluded by design; endpoints are removed and routes redirect to `/ops`.
- Trainer lifecycle split into explicit submitter flow (W7) and passive billing lifecycle (W8) to avoid mixing UI and backend revenue mechanics.

## Execution Readiness
- Design artifact completeness: complete (Understanding Lock + workflow map + decision log).
- Risk level for this deliverable: low (read-only documentation task).
- Next step: proceed to implementation planning if you want this converted into wireframes, journey maps, or test cases.
