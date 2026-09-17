from __future__ import annotations

from typing import Any, Callable, Dict

from services import notifications, stripe_billing


async def process_expiry_warnings(
    db,
    *,
    billing_url_factory: Callable[[Dict[str, Any]], str],
) -> Dict[str, Any]:
    """Process due Pro-trial warnings once, retaining failed sends for retry."""
    trainers = await db.trainers.find(
        {"subscription_tier": "pro", "subscription_status": "trialing"},
        {"_id": 0},
    ).to_list(1000)
    summary = {"key": "pro_trial_warnings", "candidates": 0, "sent": 0, "skipped": 0, "failed": 0}

    for trainer in trainers:
        status = stripe_billing.trial_status(trainer)
        if not status.get("expiry_warning"):
            continue
        summary["candidates"] += 1
        trainer_id = str(trainer.get("id") or "")
        already_sent = bool(trainer.get("pro_trial_warning_sent_at"))
        if not already_sent:
            existing = await db.notification_events.find_one(
                {
                    "kind": "pro_trial_expiry_warning",
                    "target_kind": "trainer",
                    "target_id": trainer_id,
                    "status": "sent",
                },
                {"_id": 0, "created_at": 1},
            )
            already_sent = bool(existing)
        if already_sent:
            summary["skipped"] += 1
            continue

        outcome = await notifications.notify_pro_trial_expiry_warning(
            db,
            trainer,
            billing_url=billing_url_factory(trainer),
            ends_at=str(status.get("ends_at") or ""),
            days_remaining=int(status.get("days_remaining") or 0),
        )
        if outcome.get("status") == "sent":
            summary["sent"] += 1
            await db.trainers.update_one(
                {"id": trainer_id, "pro_trial_warning_sent_at": {"$exists": False}},
                {"$set": {"pro_trial_warning_sent_at": notifications.now_iso()}},
            )
        elif outcome.get("status") == "skipped":
            summary["skipped"] += 1
        else:
            summary["failed"] += 1

    summary["last_run"] = notifications.now_iso()
    summary["status"] = "ok" if summary["failed"] == 0 else "degraded"
    await db.system_state.update_one(
        {"key": "pro_trial_warnings"},
        {"$set": summary},
        upsert=True,
    )
    return summary
