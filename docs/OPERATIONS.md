# Operations & troubleshooting

The system is autonomous; this document explains how to read it and how to recover when a loop misbehaves.

## 1. Reading `/ops` (read-only oversight)

Sign in with `ADMIN_PASS`. The page polls every 15 s.

| Tile | Means |
|---|---|
| **Revenue · billed** | All-time billed intro + conversion cents. In launch `track_only` mode, conversion revenue is expected to stay at 0. |
| **Intros 24 h / 7 d** | Billed intros only. |
| **Conversions 24 h** | Confirmed outcomes (`tracked` + `billed`). |
| **Engagement events** | website/phone/email/return-visit clicks since launch. |
| **Suppressed intros** | Anti-gaming filter rejected billing for these. Ranking unaffected by them. |
| **Suspicious conversions** | Manual confirms inside 5 min of intro. Stored, not billed. |
| **Inferred pending** | Multi-signal conversions awaiting the 48 h + ≥0.8 confidence promotion to `tracked` (or `billed` in bill-mode). |
| **Loop cards** | Last-run timestamp + key counter per loop. |
| **Pricing state** | Per suburb. `frozen=true` means below the 10 intros / 7 d threshold; price is locked at A$5. |
| **Top trainers** | Sorted by `outcome_score`. Breakdown is on the trainer doc. |
| **Recent system actions** | Audit log. `actor=system` rows are loop activity. |

## 2. Healthy state checklist

- All active loops show `last_run` ≤ 2 × their interval (e.g. ranking ≤ 120 s, health ≤ 90 s).
- `integrity_ratio` ≥ 0.5.
- No `severity:high` alerts older than the last loop run.
- `discovery.pending` trends down over time (queue is being processed).

## 3. Common failure scenarios

### A. A loop has stopped (last_run is far in the past)

Likely cause: backend crash or a long-running coroutine. Action:
1. `tail -n 200 /var/log/supervisor/backend.err.log` — look for tracebacks.
2. `sudo supervisorctl restart backend` — loops re-schedule on startup.
3. Check `/api/oversight` after 60 s — `last_run` should refresh.

### B. `intro_drop` alert (≥50 % drop in 24 h)

If the drop is real (not a side effect of yesterday's burst):
1. Check `audit_recent` for any high-impact changes (deletions, manual config writes).
2. Inspect `pricing_state` — sometimes a sudden multiplier hike chokes demand. The pricing loop will smooth this back over the next two passes due to EWMA.
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

### F. Pricing whiplash

If a suburb's multiplier swings by more than 0.5 between passes, lower `PRICING_EWMA_ALPHA` in `engine.py`. Defaults to 0.30; 0.15 produces glassier curves at the cost of slower demand response.

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
