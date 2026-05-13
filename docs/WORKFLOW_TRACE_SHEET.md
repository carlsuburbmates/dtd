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
| W3 | Dog owner | Contact cards after connect | `POST /api/engagements`, `POST /api/match/connect-click` | `create_engagement()`, `record_match_connect_click()` | `intros.find_one`, `engagements.distinct`, `conversions.find_one`, `match_events.find_one` | `engagements.insert_one`, optional `conversions.insert_one`, `audit_log.insert_one` | `engagements`, optional `inferred_conversion` audit event, `result_connect_click` | partial | Connect-click signal is wired when matching is enabled; in education-first mode the flow is intentionally traffic-gated. |
| W4 | Dog owner | "I hired them" button on trainer detail | `POST /api/conversions` | `create_conversion()` | `intros.find_one`, `conversions.find_one` | `conversions.update_many` (supersede pending inferred), `conversions.insert_one`, `audit_log.insert_one` | `conversions` explicit manual outcome | complete | None on core path. |
| W5 | System -> owner | Autonomous follow-up (T+7) | `GET /api/follow-up/{token}`, `POST /api/follow-up/{token}/outcome` + loop-driven send | `engine.send_outreach()`, `automation.send_t7_outreach()`, `get_follow_up()`, `submit_follow_up_outcome()` | `intros.find`, `outreach_events.find_one`, `conversions.find_one` | `outreach_events.insert_one/update_one`, `conversions.insert_one/update_many`, `audit_log.insert_one`, `system_state.update_one(key=outreach)` | `outreach_events` (`sent`/`failed`/response kinds), optional conversion record | complete | None on core path. |
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
| W17 | Trainer lifecycle ops | post-submission activation | `POST /api/submissions`, `GET /api/submissions/{submission_id}/status` | `create_submission()`, `get_submission_status()`, `provision_trainer_billing_profile()` | `submissions`, `trainers`, billing profile fields | `submissions`/`trainers` state updates | billing-profile readiness states + blocker payload | partial | Lifecycle path exists, but no full state-machine/orchestrated recovery workflow. |
| W18 | Revenue operations | failed/at-risk collection states | `POST /api/stripe/webhook`, `GET /api/oversight` + scheduled recovery loop | `stripe_webhook()`, `run_billing_recovery()`, billing status summarization in `oversight()` | `intros`, `stripe_events`, `system_state` | intro billing status + retry-state updates, loop heartbeat writes | invoice lifecycle, retry states, dispute/refund counters | partial | Recovery loop exists; policy tuning and operator runbook hardening are still required. |
| W19 | Trainer lifecycle ops | low-activity / failed-billing cohorts | `GET/POST /api/trainer/reactivate` + scheduled routing loop | `get_trainer_reactivation_health()`, `reactivate_trainer_listing()`, `run_reactivation_routing()` | `trainers`, `submissions`, `system_state` | trainer verification/publication updates, reactivation candidate writes, loop heartbeat writes | reactivation reasons + candidate routing state | partial | Reactivation surfaces exist, but cohort effectiveness criteria and closed-loop measurement remain limited. |

## Completion Snapshot
- `complete`: W1, W2, W4, W5, W6, W7, W9, W10, W11, W12, W14 (11/19)
- `partial`: W3, W8, W13, W16, W17, W18, W19 (7/19)
- `planned`: W15 (1/19)
- `missing`: none
- `broken`: none found in current code paths

## Priority Fix Queue (to move partial/planned/missing toward complete)
1. W3: monitor connect-click telemetry quality once matching gate is enabled publicly.
2. W13: add source-ingestion observability and remediation SOP tied to failure alerts.
3. W15/W16: add demand-source attribution model and funnel evidence.
4. W17/W19: formalize lifecycle success criteria and closed-loop reactivation measurement.
5. W8/W18: harden billing recovery policy and remediation runbook against edge-case failures.
