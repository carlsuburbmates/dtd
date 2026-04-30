# Architecture

## 1. Final product model

| Layer | What it is | Where |
|---|---|---|
| Product surface | One input → 3 ranked trainers → Connect → contact reveal → hire | `frontend/src/pages/Home.jsx`, `TrainerDetail.jsx` |
| Match decision | Claude Sonnet 4.5 relevance × outcome posterior | `backend/services/ai.py` + `engine.recompute_ranking` |
| Monetisation | Intro-first (dynamic per-intro fee), conversion tracking by default | `POST /api/intros`, `POST /api/conversions` |
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
                          │  Claude Sonnet 4.5 relevance       │
                          │  +  outcome_score (engine.ranking) │
                          └────────────────┬───────────────────┘
                                           ▼
                          ┌────────────────────────────────────┐
                          │  3 trainers + dynamic intro fee    │
                          └────────────────┬───────────────────┘
                                           ▼ Connect
                          ┌────────────────────────────────────┐
                          │  POST /api/intros (fraud filter)   │
                          │  → bills suburb-priced fee         │
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
| `recompute_pricing` | 90 s | billed intros over 7 d per suburb | `pricing_state.intro_fee_cents`, `frozen` flag if below min-data threshold |
| `reverify_listings` | 6 h | AI re-score on staleness-prioritised batch + cross-source bonus | `trainers.confidence_score`, `published`, `verification_history[]` |
| `process_discovery_queue` | 10 min | `discovery_queue` items | new trainer documents (auto-published / discarded / duplicates) |
| `promote_inferred_conversions` | 15 min | `conversions` with `inferred=true, confidence ≥0.8`, age ≥48 h | flips to `billing_status="tracked"` (`"billed"` in bill-mode) |
| `update_health` | 45 s | rolling intro/conv counts + suppressed counts | `system_state.health` + alerts + auto-rollback of last config snapshot if conversion rate drops ≥50 % |

Loop ownership is explicit via env:
- `RUN_AUTONOMY_IN_API=1` → API process schedules loops.
- `RUN_AUTONOMY_IN_API=0` → worker process owns loops.
Set `DISABLE_AUTONOMY=1` to suppress all loops (useful in tests).

## 4. Data model (collections)

| Collection | Purpose |
|---|---|
| `trainers` | published listings + verification + outcome state |
| `submissions` | public submissions (auto-published / auto-held by score) |
| `intros` | every Connect click; `billing_status ∈ {billed, suppressed}` |
| `engagements` | website / phone / email / return-visit signals on an intro |
| `conversions` | manual ("I hired them") and inferred (multi-signal, T+48 h), primarily tracked for outcome quality at launch |
| `match_events` | each `/api/match` invocation (description + result IDs) |
| `discovery_queue` | candidate URLs awaiting autonomous processing |
| `pricing_state` | per-suburb dynamic intro fee + EWMA multiplier + `frozen` |
| `system_state` | last-run summary per loop (`key` ∈ {ranking, pricing, …}) |
| `audit_log` | every state-mutating action with before/after |
| `evidence` | (reserved) cross-source confidence bonus inputs |
| `config_snapshots` | (reserved for prod) snapshots used by health auto-rollback |
| `seo_pages` | auto-generated suburb landing pages |

## 5. Signal model

The system *reacts* to signals, it doesn't sit in static rules:

- **New listing in queue** → discovery loop scores it → either publishes or discards.
- **User clicks Connect** → fraud module evaluates → bills or suppresses → ranking loop re-scores trainer in the next pass.
- **User clicks website / phone / email** → engagement recorded → if 2+ distinct kinds within an intro: inferred conversion logged.
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
