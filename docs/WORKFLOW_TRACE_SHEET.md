# Workflow Trace Sheet (W1-W19)

## Purpose
- This is the single technical trace table for workflow verification.
- It maps each workflow `W#` to entry surface, API routes, backend functions, DB reads/writes, and emitted signals.
- Use this file as the source of truth for "implemented vs partial vs planned vs missing" status.

## Status Legend
- `complete`: workflow path exists and is end-to-end functional in code.
- `partial`: path exists, but has operational gaps/caveats that affect reliability, observability, or lifecycle coverage.
- `planned`: workflow is defined and scoped, but explicit implementation does not yet exist as a first-class flow.
- `missing`: workflow family has no current implementation path.
- `broken`: expected path exists in principle but is currently non-functional.

| W# | Actor | Entry Surface | API Route(s) | Backend Function(s) | Primary DB Reads | Primary DB Writes | Emitted Events/Signals | Status | Current Gap (if any) |
|---|---|---|---|---|---|---|---|---|---|
| W1 | Dog owner | `/` match form | `GET /api/config`, `POST /api/match` | `config()`, `instant_match()` | `trainers.distinct`, `trainers.find`, `pricing_state.find` | `match_events.insert_one` | `match_events` row (`result_ids`) | complete | None on core path. |
| W2 | Dog owner | `/t/:id` connect form | `GET /api/trainers/{id}`, `POST /api/intros` | `get_trainer()`, `create_intro()` | `trainers.find_one`, `intros.find_one` (idempotency), pricing lookup | `intros.insert_one`, `intros.update_one` (billing/notification), `audit_log.insert_one` | `audit_log:intro`, intro billing metadata, trainer-intro notification metadata | complete | None on core path. |
| W3 | Dog owner | Contact cards after connect | `POST /api/engagements` | `create_engagement()` | `intros.find_one`, `engagements.distinct`, `conversions.find_one` | `engagements.insert_one`, optional `conversions.insert_one`, `audit_log.insert_one` | `engagements`, optional `inferred_conversion` audit event | partial | Home-result `Connect` click itself is not recorded as a separate event before intro-level engagement. |
| W4 | Dog owner | "I hired them" button on trainer detail | `POST /api/conversions` | `create_conversion()` | `intros.find_one`, `conversions.find_one` | `conversions.update_many` (supersede pending inferred), `conversions.insert_one`, `audit_log.insert_one` | `conversions` explicit manual outcome | complete | None on core path. |
| W5 | System -> owner | Autonomous follow-up (T+7) | loop-driven (no direct UI route) | `engine.send_outreach()`, `automation.send_t7_outreach()` | `intros.find`, `outreach_events.find_one`, `conversions.find_one` | `outreach_events.insert_one`, `system_state.update_one(key=outreach)` | `outreach_events` (`sent`/`failed`) | partial | Follow-up sends and logs correctly, but owner return path is generic (no direct workflow-deep link token). |
| W6 | Trainer | `/trainers` education page | none (content/CTA only) | frontend-only (`Trainers.jsx`) | none | none | CTA signals only via navigation | complete | No explicit qualification/attribution event capture before submission. |
| W7 | Trainer submitter | `/submit` form | `POST /api/submissions` | `create_submission()`, `stripe_billing.provision_trainer_billing_profile()`, `notifications.notify_submitter_result()` | AI score calls, trainer existence checks by downstream loops | `submissions.insert_one`, optional `submissions.update_one`, optional `trainers.insert_one/update_one`, `notification_events.insert_one`, `audit_log.insert_one` | submission status, billing profile status, submitter notification status | complete | Core submission path works; downstream activation lifecycle is split into W17. |
| W8 | System + trainer billing | Intro billing + webhook lifecycle | `POST /api/intros`, `POST /api/stripe/webhook` | `stripe_billing.bill_intro()`, `stripe_webhook()` | trainer billing profile fields, `stripe_events.find_one` | `intros.update_one/update_many`, `stripe_events.insert_one`, trainer profile updates | intro billing collection statuses (`invoice_sent`, `paid`, `failed`, etc.) | partial | Revenue recovery/remediation policies are not yet explicit first-class workflow controls (W18). |
| W9 | Oversight operator | `/ops` login | `POST /api/oversight/login` | `oversight_login()` | none | none | auth decision only | complete | None on core path. |
| W10 | Oversight operator | `/ops` console polling | `GET /api/oversight` | `oversight()` | wide reads across `intros`, `conversions`, `engagements`, `system_state`, `pricing_state`, `trainers`, `audit_log`, etc. | none (read-only endpoint) | aggregated snapshot payload every poll | complete | None on core path. |
| W11 | External actor | discovery contribution | `POST /api/discovery` | `submit_discovery()` | minimal pre-validation only | `discovery_queue.insert_one` | new queue item (`status=pending`) | complete | None on core path. |
| W12 | Autonomous system | scheduled loops | internal loop scheduler | `recompute_ranking()`, `recompute_pricing()`, `schedule_all()` | `intros`, `conversions`, `engagements`, `trainers`, `pricing_state` | `trainers.update_one`, `pricing_state.update_one`, `system_state.update_one` | `system_state` loop heartbeat (`ranking`, `pricing`) | complete | None on core path. |
| W13 | Autonomous system | scheduled verification/discovery/source-ingestion | internal loop scheduler | `reverify_listings()`, `process_discovery_queue()`, `ingest_sources()` | `trainers`, `evidence`, `discovery_queue`, source URLs | `trainers.update_one/insert_one`, `discovery_queue.update_one/insert_one`, `system_state.update_one` | `system_state` loop heartbeat (`verification`, `discovery`, `source_ingestion`) | partial | Source ingestion quality depends on external URL health; failed sources are logged but not auto-remediated. |
| W14 | Autonomous system | scheduled inference/outreach/health | internal loop scheduler | `promote_inferred_conversions()`, `send_outreach()`, `update_health()` | `conversions`, `intros`, `submissions`, `trainers`, `config_snapshots` | `conversions.update_one`, `outreach_events.insert_one`, `system_state.update_one`, optional `config_snapshots.update_one` rollback flag | `system_state` loop heartbeat (`inference`, `outreach`, `health`), alerts, rollback markers | complete | None on core path. |
| W15 | Growth operations | public pages and landing entry | not first-class (currently indirect) | frontend navigation + analytics hooks | no canonical source-level attribution table | no canonical attribution write | demand source signal currently implicit | planned | Formal demand-source attribution loop is not yet implemented as a governed workflow. |
| W16 | Growth + platform | SEO routes and CTA handoff | `GET /api/seo/{slug}` + frontend route use | `get_seo()` | `seo_pages.find_one` | `seo_pages.insert_one` | generated SEO copy surface + CTA path | partial | SEO generation exists, but nurture/remarketing loop and conversion attribution are not first-class. |
| W17 | Trainer lifecycle ops | post-submission activation | partial via `POST /api/submissions` side-effects | `create_submission()`, `provision_trainer_billing_profile()` | `submissions`, `trainers`, billing profile fields | `submissions`/`trainers` state updates | billing-profile readiness states | planned | No dedicated onboarding-completion workflow orchestration or recovery states. |
| W18 | Revenue operations | failed/at-risk collection states | implicit via webhook/billing summaries | `stripe_webhook()`, billing status summarization in `oversight()` | `intros`, `stripe_events` | intro billing status updates | invoice lifecycle and dispute/refund counters | planned | Recovery policy (retry/remediate/reactivate) is not yet encoded as a first-class workflow. |
| W19 | Trainer lifecycle ops | low-activity / failed-billing cohorts | none | none | none | none | none | missing | No explicit trainer reactivation workflow yet. |

## Completion Snapshot
- `complete`: W1, W2, W4, W6, W7, W9, W10, W11, W12, W14 (10/19)
- `partial`: W3, W5, W8, W13, W16 (5/19)
- `planned`: W15, W17, W18 (3/19)
- `missing`: W19 (1/19)
- `broken`: none found in current code paths

## Priority Fix Queue (to move partial/planned/missing toward complete)
1. W3: add explicit "result connect click" event logging before trainer-detail navigation.
2. W5: add owner follow-up deep-link to explicit outcome confirmation surface.
3. W13: add source-ingestion failure policy (backoff/suppress/alert thresholds).
4. W15/W16: add demand-source attribution model and funnel evidence.
5. W17/W19: add trainer onboarding completion + reactivation orchestration states.
6. W8/W18: codify billing recovery policy and remediation lifecycle (not just invoice transport).
