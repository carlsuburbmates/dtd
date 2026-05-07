# Workflow Trace Sheet (W1-W14)

## Purpose
- This is the single technical trace table for workflow verification.
- It maps each workflow `W#` to entry surface, API routes, backend functions, DB reads/writes, and emitted signals.
- Use this file as the source of truth for "implemented vs partial vs broken" status.

## Status Legend
- `complete`: workflow path exists and is end-to-end functional in code.
- `partial`: path exists, but has operational gaps/caveats that can affect reliability, observability, or automation quality.
- `broken`: core expected path is missing or non-functional.

| W# | Actor | Entry Surface | API Route(s) | Backend Function(s) | Primary DB Reads | Primary DB Writes | Emitted Events/Signals | Status | Current Gap (if any) |
|---|---|---|---|---|---|---|---|---|---|
| W1 | Dog owner | `/` match form | `GET /api/config`, `POST /api/match` | `config()`, `instant_match()` | `trainers.distinct`, `trainers.find`, `pricing_state.find` | `match_events.insert_one` | `match_events` row (`result_ids`) | complete | None on core path. |
| W2 | Dog owner | `/t/:id` connect form | `GET /api/trainers/{id}`, `POST /api/intros` | `get_trainer()`, `create_intro()` | `trainers.find_one`, `intros.find_one` (idempotency), pricing lookup | `intros.insert_one`, `intros.update_one` (billing/notification), `audit_log.insert_one` | `audit_log:intro`, intro billing metadata, trainer-intro notification metadata | complete | None on core path. |
| W3 | Dog owner | Contact cards after connect | `POST /api/engagements` | `create_engagement()` | `intros.find_one`, `engagements.distinct`, `conversions.find_one` | `engagements.insert_one`, optional `conversions.insert_one`, `audit_log.insert_one` | `engagements`, optional `inferred_conversion` audit event | partial | Home-result `Connect` click itself is not recorded as a separate event before intro-level engagement. |
| W4 | Dog owner | "I hired them" button on trainer detail | `POST /api/conversions` | `create_conversion()` | `intros.find_one`, `conversions.find_one` | `conversions.update_many` (supersede pending inferred), `conversions.insert_one`, `audit_log.insert_one` | `conversions` explicit manual outcome | complete | None on core path. |
| W5 | System -> owner | Autonomous follow-up (T+7) | loop-driven (no direct UI route) | `engine.send_outreach()`, `automation.send_t7_outreach()` | `intros.find`, `outreach_events.find_one`, `conversions.find_one` | `outreach_events.insert_one`, `system_state.update_one(key=outreach)` | `outreach_events` (`sent`/`failed`) | partial | Follow-up sends and logs correctly, but owner return path is generic (no direct workflow-deep link token). |
| W6 | Trainer | `/trainers` education page | none (content/CTA only) | frontend-only (`Trainers.jsx`) | none | none | CTA signals only via navigation | complete | None on intended scope. |
| W7 | Trainer submitter | `/submit` form | `POST /api/submissions` | `create_submission()`, `stripe_billing.provision_trainer_billing_profile()`, `notifications.notify_submitter_result()` | AI score calls, trainer existence checks by downstream loops | `submissions.insert_one`, optional `submissions.update_one`, optional `trainers.insert_one/update_one`, `notification_events.insert_one`, `audit_log.insert_one` | submission status, billing profile status, submitter notification status | complete | None on core path. |
| W8 | System + trainer billing | Intro billing + webhook lifecycle | `POST /api/intros`, `POST /api/stripe/webhook` | `stripe_billing.bill_intro()`, `stripe_webhook()` | trainer billing profile fields, `stripe_events.find_one` | `intros.update_one/update_many`, `stripe_events.insert_one`, trainer profile updates | intro billing collection statuses (`invoice_sent`, `paid`, `failed`, etc.) | partial | Collection is fail-soft by design; full charging depends on Stripe/runtime config and trainer billing readiness. |
| W9 | Oversight operator | `/ops` login | `POST /api/oversight/login` | `oversight_login()` | none | none | auth decision only | complete | None on core path. |
| W10 | Oversight operator | `/ops` console polling | `GET /api/oversight` | `oversight()` | wide reads across `intros`, `conversions`, `engagements`, `system_state`, `pricing_state`, `trainers`, `audit_log`, etc. | none (read-only endpoint) | aggregated snapshot payload every poll | complete | None on core path. |
| W11 | External actor | discovery contribution | `POST /api/discovery` | `submit_discovery()` | minimal pre-validation only | `discovery_queue.insert_one` | new queue item (`status=pending`) | complete | None on core path. |
| W12 | Autonomous system | scheduled loops | internal loop scheduler | `recompute_ranking()`, `recompute_pricing()`, `schedule_all()` | `intros`, `conversions`, `engagements`, `trainers`, `pricing_state` | `trainers.update_one`, `pricing_state.update_one`, `system_state.update_one` | `system_state` loop heartbeat (`ranking`, `pricing`) | complete | None on core path. |
| W13 | Autonomous system | scheduled verification/discovery/source-ingestion | internal loop scheduler | `reverify_listings()`, `process_discovery_queue()`, `ingest_sources()` | `trainers`, `evidence`, `discovery_queue`, source URLs | `trainers.update_one/insert_one`, `discovery_queue.update_one/insert_one`, `system_state.update_one` | `system_state` loop heartbeat (`verification`, `discovery`, `source_ingestion`) | partial | Source ingestion quality depends on external URL health; failed sources are logged but not auto-remediated. |
| W14 | Autonomous system | scheduled inference/outreach/health | internal loop scheduler | `promote_inferred_conversions()`, `send_outreach()`, `update_health()` | `conversions`, `intros`, `submissions`, `trainers`, `config_snapshots` | `conversions.update_one`, `outreach_events.insert_one`, `system_state.update_one`, optional `config_snapshots.update_one` rollback flag | `system_state` loop heartbeat (`inference`, `outreach`, `health`), alerts, rollback markers | complete | None on core path. |

## Completion Snapshot
- `complete`: W1, W2, W4, W6, W7, W9, W10, W11, W12, W14 (10/14)
- `partial`: W3, W5, W8, W13 (4/14)
- `broken`: none found in current code paths

## Priority Fix Queue (to move partial -> complete)
1. W3: add explicit "result connect click" event logging before trainer-detail navigation.
2. W5: add owner follow-up deep-link to explicit outcome confirmation surface.
3. W13: add source-ingestion failure policy (backoff/suppress/alert thresholds).
4. W8: enforce production billing-readiness gates in launch config (`billing_profile_status` and Stripe secret/webhook readiness).
