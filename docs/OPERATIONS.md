# Operations & troubleshooting

The system is autonomous; this document explains how to read it and how to recover when a loop misbehaves.

## 1. Reading `/ops` (read-only oversight)

Sign in with `ADMIN_PASS`. The page polls every 15 s.

| Tile | Means |
|---|---|
| **Revenue · booked** | Status-based commercial value (`booked_revenue_cents`) from billed intros + conversion fee rows. In launch `track_only` mode, conversion booking is expected to stay at 0. |
| **Revenue · collected** | Cash-collected intro value (`collected_revenue_cents`) from settled invoice outcomes (`paid`/`dispute_resolved`). |
| **Revenue · at risk** | Booked intro value currently exposed to collection risk (`at_risk_revenue_cents`) for failed/uncollectible/disputed/remediation statuses. |
| **Trial free** | Intro rows in trainer 30-day free window (`billing_collection_status=trial_free`), excluded from collected revenue. |
| **Intros 24 h / 7 d** | Billed intros only. |
| **Conversions 24 h** | Confirmed outcomes (`tracked` + `billed`). |
| **Engagement events** | website/phone/email/return-visit clicks since launch. |
| **Connect-click signals** | included in engagement totals as `result_connect_click` pre-intro signals. |
| **Suppressed intros** | Anti-gaming filter rejected billing for these. Ranking unaffected by them. |
| **Suspicious conversions** | Manual confirms inside 5 min of intro. Stored, not billed. |
| **Inferred pending** | Multi-signal conversions awaiting the 48 h + ≥0.8 confidence promotion to `tracked` (or `billed` in bill-mode). |
| **Loop cards** | Last-run timestamp + key counter per loop (including billing recovery, nurture, and reactivation routing). |
| **Pricing state** | Per suburb fixed intro fee snapshot. Launch mode is `pricing_mode=fixed` and fee defaults to A$5 after trainer trial window. |
| **Top trainers** | Sorted by `outcome_score`. Breakdown is on the trainer doc. |
| **Recent system actions** | Audit log. `actor=system` rows are loop activity. |

## 2. Healthy state checklist

- All active loops show `last_run` ≤ 2 × their interval (e.g. ranking ≤ 120 s, health ≤ 90 s).
- `integrity_ratio` ≥ 0.5.
- No `severity:high` alerts older than the last loop run.
- `discovery.pending` trends down over time (queue is being processed).
- `billing_recovery.retry_exhausted` does not grow continuously (or remediation path is actively being worked).
- `source_ingestion.suppressed_sources` remains low and non-sticky after source health recovers.

## 3. Common failure scenarios

### A. A loop has stopped (last_run is far in the past)

Likely cause: backend crash or a long-running coroutine. Action:
1. `tail -n 200 /var/log/supervisor/backend.err.log` — look for tracebacks.
2. `sudo supervisorctl restart backend` — loops re-schedule on startup.
3. Check `/api/oversight` after 60 s — `last_run` should refresh.

### B. `intro_drop` alert (≥50 % drop in 24 h)

If the drop is real (not a side effect of yesterday's burst):
1. Check `audit_recent` for any high-impact changes (deletions, manual config writes).
2. Inspect `pricing_state` — confirm `pricing_mode=fixed` and `intro_fee_cents` equals your launch policy.
3. If a recent change is the cause, write its inverse as a fresh `config_snapshots` row; the next health loop will treat the previous change as outdated.

### C. `auto_rollback` alert

Means the health loop reverted a `config_snapshots` row because conversions cliffed. Expected next steps:
1. Read the rolled-back snapshot's `kind` and `payload`.
2. Either re-apply with adjusted parameters, or leave reverted (the system kept itself stable in the meantime).

### D. `fraud_suppressed` alert spikes

Often a single bad actor. Inspect:
```bash
mongo $MONGO_URL/$DB_NAME --eval 'db.intros.aggregate([
  {$match:{billing_status:"suppressed"}},
  {$group:{_id:"$ip", n:{$sum:1}}},
  {$sort:{n:-1}}, {$limit:5}
])'
```
No action is required — these intros never billed and never affected ranking. If you want to permanently block, add the IP to a future `blocklist` collection (already supported by `evaluate_intro` if you extend it).

### E. Discovery queue not draining

Loop runs every 10 min. Check `system_state.discovery.last_run`. If stale, see (A). If fresh but pending count is high, the queue may be backlogged; heuristic verification still resolves items conservatively (many go to `discarded`).

### F. Pricing mismatch

If intro fee differs from expected launch policy, verify runtime env and restart runtime:
- `FIXED_INTRO_FEE_CENTS` should match your intended amount (default `500`).
- `TRAINER_FREE_INTRO_DAYS` should match your intended trial window (default `30`).

## 4. Manual interventions (when essential)

The system is designed so that none of the routine workflows need a human. Direct DB intervention is reserved for:
- Legal takedown of a real listing → `db.trainers.updateOne({id:"…"}, {$set:{published:false, verification_status:"hold"}})`.
- Refunding a billed intro/conversion → flip `billing_status` to `refunded` (any non-`billed` value is excluded from revenue & ranking automatically).
- Wiping a poisoned discovery batch → `db.discovery_queue.deleteMany({source:"…"})`.

Every direct write should be paired with an `audit_log` insert noting the human actor and reason; this preserves the integrity of the snapshot timeline.

## 5. Reading logs

```bash
# Backend supervisor logs (stderr is where uvicorn writes)
tail -f /var/log/supervisor/backend.err.log

# Loop heartbeat
grep -E "loop (ranking|pricing|verification|discovery|inference|health)" /var/log/supervisor/backend.err.log
```

## 6. Test credentials & sanity probes

`/app/memory/test_credentials.md` contains the dev passcode.
Quick health probe:
```bash
curl -s "$BACKEND/api/" && curl -s "$BACKEND/api/config"
curl -s "$BACKEND/api/oversight" -H "X-Admin-Pass: $ADMIN_PASS" | jq '.loops | keys'
```
