# Architecture

Current mode-lock context (2026-05-10): education-first prelaunch. Public matching from home is gated by `PUBLIC_MATCHING_ENABLED` (`/api/config` consumed by `Home.jsx`), while owner/trainer lifecycle routes and APIs remain implemented.

## 1. Final product model

| Layer | What it is | Where |
|---|---|---|
| Product surface | Technical path: one input → 3 ranked trainers → Connect → contact reveal → hire. Current public entry may be deferred by mode-lock flag. | `frontend/src/pages/Home.jsx`, `TrainerDetail.jsx` |
| Lifecycle surfaces | Follow-up confirmation, trainer onboarding status, billing remediation, reactivation, campaign entry | `frontend/src/pages/FollowUp.jsx`, `SubmitStatus.jsx`, `TrainerBilling.jsx`, `TrainerReactivate.jsx`, `CampaignLanding.jsx` |
| Match decision | Deterministic heuristic relevance × outcome posterior | `backend/services/ai.py` + `engine.recompute_ranking` |
| Monetisation | Intro-first; `/api/intros` meters lead fee. Submission-registered trainers receive `trial_free` intros for first 30 days, then Stripe invoice collection begins. Launch defaults to `track_only` conversion tracking. | `POST /api/intros`, `POST /api/stripe/webhook`, `POST /api/conversions` |
| Trust | Bayesian outcome score; multi-signal conversion inference | `engine.py` |
| Anti-gaming | IP/email duplicate suppression, conversion velocity check | `services/fraud.py` |
| Ingestion | Public `POST /api/discovery` → autonomous discovery loop | `engine.process_discovery_queue` |
| Oversight | Read-only snapshot at `/api/oversight` | `frontend/src/pages/Ops.jsx` |

## 2. How the business runs as a continuous system

```
                     ┌──────────────────────────────────────────────┐
                     │                  USER                       │
   problem ─────────▶│           POST /api/match                   │
                     └──────────────────────┬──────────────────────┘
                                            │
                                            ▼
                          ┌────────────────────────────────────┐
                          │  deterministic relevance            │
                          │  +  outcome_score (engine.ranking) │
                          └────────────────┬───────────────────┘
                                           ▼
                          ┌────────────────────────────────────┐
                          │  3 trainers + fixed intro fee      │
                          └────────────────┬───────────────────┘
                                           ▼ Connect
                          ┌────────────────────────────────────┐
                          │  POST /api/intros (fraud filter)   │
                          │  → trial-free (30d) or bills A$5   │
                          │  → creates/sends Stripe invoice    │
                          │  → reveals contact                 │
                          └────────────────┬───────────────────┘
                                           ▼
                       engagement events  ─────────────────────┐
                       POST /api/engagements  ─────────────────┤
                                           │                   ▼
                                           │      conversions_inferred (≥2 signals)
                                           ▼                   │
                          ┌────────────────────────────────────┐
                          │  POST /api/conversions (manual)    │
                          │  → tracked by default (or billed in bill-mode) │
                          └────────────────┬───────────────────┘
                                           ▼
                                 ranking_loop incorporates
                                 outcome → next user benefits
```

## 3. Core loops

| Loop | Cadence | Source signals | Output |
|---|---|---|---|
| `recompute_ranking` | 60 s | intros + conversions + engagements + response latency + recency | `trainers.outcome_score` (0.05 – 0.99), `outcome_breakdown` |
| `recompute_pricing` | 90 s | published trainer suburbs + billed intros over 7 d | fixed `pricing_state` snapshot (`intro_fee_cents`, `pricing_mode`) |
| `reverify_listings` | 6 h | AI re-score on staleness-prioritised batch + cross-source bonus | `trainers.confidence_score`, `published`, `verification_history[]` |
| `process_discovery_queue` | 10 min | `discovery_queue` items | new trainer documents (auto-published / discarded / duplicates) |
| `promote_inferred_conversions` | 15 min | `conversions` with `inferred=true, confidence ≥0.8`, age ≥48 h | flips to `billing_status="tracked"` (`"billed"` in bill-mode) |
| `ingest_sources` | 6 h | `DISCOVERY_SOURCE_URLS` pages + per-source health state | queues new candidate URLs, suppresses repeatedly failing sources, emits alerts |
| `send_outreach` | 1 h | intros older than 7d with no conversion + Resend | sends T+7 conversion prompt and records `outreach_events` |
| `run_billing_recovery` | 30 min | intro rows in failed/uncollectible/error states | bounded retry/backoff collection orchestration + retry state updates |
| `run_growth_nurture` | 1 h | campaign/source attribution from match->intro->conversion | remarketing cohorts + conversion-gap cohorts in `growth_attribution` |
| `run_reactivation_routing` | 6 h | trainer inactivity + billing blockers + confidence/publication drift | auto-routed reactivation candidates + trainer notification workflow |
| `update_health` | 45 s | rolling intro/conv counts + suppressed counts | `system_state.health` + alerts + auto-rollback of last config snapshot if conversion rate drops ≥50 % |

Loop ownership is explicit via env:
- `AUTONOMY_LOOP_OWNER=api` → API process is owner.
- `AUTONOMY_LOOP_OWNER=worker` → worker process is owner.
- `AUTONOMY_LOOP_OWNER=none` → no process owns/schedules loops.
- Legacy compatibility: `RUN_AUTONOMY_IN_API=1|0` still maps to `api|worker`, but conflicting values with `AUTONOMY_LOOP_OWNER` hard-fail startup.
- DB lease guard (`system_state.key=autonomy_loop_lease`) ensures only one live owner executes loops across multiple processes.
Set `DISABLE_AUTONOMY=1` to suppress all loops (useful in tests).

## 4. Data model (collections)

| Collection | Purpose |
|---|---|
| `trainers` | published listings + verification + outcome state |
| `submissions` | public submissions (auto-published / auto-held by score) |
| `intros` | every Connect click; `billing_status ∈ {billed, suppressed}` |
| `engagements` | pre-intro result connect-click + website / phone / email / return-visit intro signals |
| `conversions` | owner-confirmed (follow-up action) and inferred (multi-signal, T+48 h), primarily tracked for outcome quality at launch |
| `match_events` | each `/api/match` invocation (description + result IDs) |
| `discovery_queue` | candidate URLs awaiting autonomous processing |
| `outreach_events` | T+7 email sends/failures for intro follow-up |
| `pricing_state` | per-suburb fixed intro fee snapshot + `pricing_mode` |
| `system_state` | last-run summary per loop (`key` ∈ {ranking, pricing, …}) |
| `stripe_events` | webhook idempotency + latest Stripe event receipts |
| `audit_log` | every state-mutating action with before/after |
| `evidence` | (reserved) cross-source confidence bonus inputs |
| `config_snapshots` | (reserved for prod) snapshots used by health auto-rollback |
| `seo_pages` | auto-generated suburb landing pages |
| `source_ingestion_state` | per-source failure counters, suppression windows, and last-check telemetry |
| `growth_attribution` | campaign/source attribution cohorts and nurture/remarketing counters |
| `reactivation_candidates` | auto-detected trainer reactivation cohort and notification status |

## 5. Signal model

The system *reacts* to signals, it doesn't sit in static rules:

- **New listing in queue** → discovery loop scores it → either publishes or discards.
- **User clicks Connect** → fraud module evaluates → bills or suppresses → ranking loop re-scores trainer in the next pass.
- **Stripe webhook arrives** (`invoice.sent`, `invoice.paid`, `invoice.payment_failed`) → intro row `billing_collection_status` is reconciled.
- **User clicks Connect from result list** → explicit pre-intro engagement logged (`result_connect_click`).
- **User clicks website / phone / email** → engagement recorded → if 2+ distinct kinds within an intro: inferred conversion logged.
- **T+7 follow-up email click** → `/follow-up/:token` → explicit hired/still-deciding/rematch outcome path.
- **Collection fails** (`payment_failed` / `uncollectible` / `invoice_error`) → billing recovery loop retries with bounded exponential backoff.
- **Campaign/source cohorts underperform** → nurture loop updates remarketing candidate totals for growth ops.
- **Trainer drifts inactive or blocked** → reactivation routing loop creates/updates candidate and can notify trainer.
- **24-h conversion drop ≥50 %** → health loop rolls back the most recent `config_snapshots` row (if any) and emits an `auto_rollback` alert.

## 6. Anti-gaming

- Per-IP intro rate limit (6 / hour); flagged intros are inserted but `billing_status="suppressed"` and don't influence ranking.
- Same-IP-same-trainer dedup (24 h) and same-email-same-trainer dedup (7 d).
- Manual conversions confirmed within 5 min of intro are tagged `suspicious`; they are stored, but the conversion fee is not charged and they don't earn ranking.
- Inferred conversions never auto-promote inside 48 h of the intro, regardless of confidence.

## 7. Verification evolution

- Every listing re-scored on a cadence weighted by `(staleness_hours + threshold_proximity_penalty)`.
- The 0.6 cliff is rechecked more often than well-clear listings.
- Listings referenced in ≥2 distinct evidence rows get a +0.05 confidence bonus.
- Confidence < 0.6 → `published=false` (auto-hidden); ≥ 0.85 → `verified`; in between → `unverified`.
- A 20-row rolling `verification_history` lets us see drift; that history is what an external compliance agent would consume.

## 8. Failure & recovery

- All state changes write to `audit_log` with `actor`.
- Health loop emits structured alerts to the oversight surface.
- Auto-rollback of the most recent `config_snapshots` row when conversion rate cliff is detected. Snapshots are append-only; the loop only flips a `rolled_back=true` flag, so nothing is destroyed.
- The frontend is stateless beyond `localStorage` (oversight passcode), so a backend rollback is sufficient.

## 9. Componentinteraction

- **Frontend → backend**: REST only, all under `/api`.
- **Backend → MongoDB**: Motor (async).
- **Backend → inference**: deterministic heuristics in `services/ai.py` (no external model dependency at runtime).
- **Backend ↔ frontend**: cookies are not used. The oversight passcode travels as `X-Admin-Pass` only on `/api/oversight*` routes.
