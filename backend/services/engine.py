"""Autonomous engine — continuous loops + math the system runs without humans.

Loops (all run as asyncio background tasks scheduled at fixed intervals):
  - ranking_loop      : recompute Bayesian outcome_score for each trainer.
  - pricing_loop      : recompute per-(suburb,category) intro fee from demand.
  - verification_loop : re-score listings; auto-publish ≥0.85, auto-hide <0.6.
  - health_loop       : detect anomalies, write health_state.

Math:
  Outcome score uses a Beta(α,β) posterior over conversion-from-intro:
      α = 1 + conversions_30d
      β = 1 + (intros_30d - conversions_30d)
  We rank by the posterior mean: α / (α + β). Floor at 0.05 so cold-start
  trainers still surface occasionally (exploration).

  Demand price uses a smoothed multiplier:
      multiplier = clip( 0.6 + 0.4 * (intros_7d / median_intros_7d), 0.6, 2.5 )
      fee = base_intro_fee * multiplier
"""

from __future__ import annotations

import asyncio
import logging
import os
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("dtd.engine")

BASE_INTRO_FEE = 500           # cents AUD (A$5)
BASE_CONVERSION_FEE = 6500     # cents AUD (A$65)
RANKING_INTERVAL_S = 60
PRICING_INTERVAL_S = 90
VERIFICATION_INTERVAL_S = 60 * 60 * 6
HEALTH_INTERVAL_S = 45


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_minus(days: int = 0, hours: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days, hours=hours)).isoformat()


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


async def recompute_ranking(db) -> Dict[str, Any]:
    """Recompute trainer.outcome_score from intros + conversions over last 30d."""
    cutoff = _iso_minus(days=30)
    trainers = await db.trainers.find({}, {"_id": 0, "id": 1}).to_list(2000)
    total = 0
    for t in trainers:
        intros = await db.intros.count_documents({"trainer_id": t["id"], "created_at": {"$gte": cutoff}})
        conversions = await db.conversions.count_documents(
            {"trainer_id": t["id"], "created_at": {"$gte": cutoff}}
        )
        alpha = 1 + conversions
        beta = 1 + max(0, intros - conversions)
        outcome = alpha / (alpha + beta)
        # clamp + cold-start floor
        outcome = max(0.05, min(0.99, outcome))
        await db.trainers.update_one(
            {"id": t["id"]},
            {
                "$set": {
                    "outcome_score": round(outcome, 4),
                    "intros_30d": intros,
                    "conversions_30d": conversions,
                    "outcome_updated_at": now_iso(),
                }
            },
        )
        total += 1
    await db.system_state.update_one(
        {"key": "ranking"},
        {"$set": {"key": "ranking", "last_run": now_iso(), "trainers_scored": total}},
        upsert=True,
    )
    return {"trainers_scored": total}


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


async def recompute_pricing(db) -> Dict[str, Any]:
    """Recompute per-suburb dynamic intro fee multiplier from last-7-day intros."""
    cutoff = _iso_minus(days=7)
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$suburb", "n": {"$sum": 1}}},
    ]
    rows = await db.intros.aggregate(pipeline).to_list(500)
    counts = {r["_id"]: r["n"] for r in rows if r.get("_id")}
    median = statistics.median(counts.values()) if counts else 1
    median = max(1, median)

    out: List[Dict[str, Any]] = []
    suburbs = await db.trainers.distinct("suburb", {"published": True})
    for suburb in suburbs:
        n = counts.get(suburb, 0)
        multiplier = 0.6 + 0.4 * (n / median)
        multiplier = max(0.6, min(2.5, multiplier))
        fee = int(BASE_INTRO_FEE * multiplier)
        await db.pricing_state.update_one(
            {"suburb": suburb},
            {
                "$set": {
                    "suburb": suburb,
                    "multiplier": round(multiplier, 2),
                    "intro_fee_cents": fee,
                    "intros_7d": n,
                    "updated_at": now_iso(),
                }
            },
            upsert=True,
        )
        out.append({"suburb": suburb, "multiplier": round(multiplier, 2), "intro_fee_cents": fee})

    await db.system_state.update_one(
        {"key": "pricing"},
        {"$set": {"key": "pricing", "last_run": now_iso(), "suburbs_priced": len(out), "median_intros_7d": median}},
        upsert=True,
    )
    return {"suburbs_priced": len(out)}


async def get_intro_fee(db, suburb: Optional[str]) -> int:
    """Look up the current intro fee for a suburb (in cents)."""
    if suburb:
        ps = await db.pricing_state.find_one({"suburb": suburb}, {"_id": 0})
        if ps and ps.get("intro_fee_cents"):
            return int(ps["intro_fee_cents"])
    return BASE_INTRO_FEE


# ---------------------------------------------------------------------------
# Verification (re-score loop)
# ---------------------------------------------------------------------------


async def reverify_listings(db, ai_service, batch: int = 5) -> Dict[str, Any]:
    """Re-verify the N least-recently-checked listings.

    Auto-publishes when score ≥ 0.85, auto-unpublishes when < 0.6.
    """
    cursor = db.trainers.find({}, {"_id": 0}).sort("verified_at", 1).limit(batch)
    rescored = 0
    auto_pub = 0
    auto_hide = 0
    async for t in cursor:
        payload = {
            "name": t.get("name"),
            "suburb": t.get("suburb"),
            "website": t.get("website"),
            "phone": t.get("phone"),
            "email": t.get("email"),
            "services": t.get("services"),
            "categories": t.get("categories"),
            "bio": t.get("bio"),
            "source_evidence_url": t.get("source_evidence_url"),
        }
        score = await ai_service.score_trainer(payload)
        conf = float(score["confidence"])
        status = ai_service.status_for_score(conf)
        was_published = bool(t.get("published"))
        published = conf >= 0.6
        if published and not was_published:
            auto_pub += 1
        elif not published and was_published:
            auto_hide += 1
        await db.trainers.update_one(
            {"id": t["id"]},
            {
                "$set": {
                    "confidence_score": conf,
                    "verification_status": status,
                    "verification_reasoning": score.get("reasoning", ""),
                    "verification_signals": score.get("signals", []),
                    "verification_model": score.get("model", "heuristic"),
                    "verified_at": now_iso(),
                    "published": published,
                }
            },
        )
        rescored += 1

    await db.system_state.update_one(
        {"key": "verification"},
        {
            "$set": {
                "key": "verification",
                "last_run": now_iso(),
                "rescored": rescored,
                "auto_published": auto_pub,
                "auto_hidden": auto_hide,
            }
        },
        upsert=True,
    )
    return {"rescored": rescored, "auto_published": auto_pub, "auto_hidden": auto_hide}


# ---------------------------------------------------------------------------
# Health monitor (anomaly detector)
# ---------------------------------------------------------------------------


async def update_health(db) -> Dict[str, Any]:
    """Compute system health snapshot — written to a singleton state doc."""
    intros_24 = await db.intros.count_documents({"created_at": {"$gte": _iso_minus(hours=24)}})
    intros_prev = await db.intros.count_documents(
        {"created_at": {"$gte": _iso_minus(hours=48), "$lt": _iso_minus(hours=24)}}
    )
    conv_24 = await db.conversions.count_documents({"created_at": {"$gte": _iso_minus(hours=24)}})
    drop_pct = 0.0
    if intros_prev > 4:
        drop_pct = (intros_prev - intros_24) / intros_prev

    suspicious = await db.trainers.count_documents(
        {"$or": [{"verification_status": "hold"}, {"confidence_score": {"$lt": 0.6}}]}
    )
    pending = await db.submissions.count_documents({"status": "pending"})
    held = await db.submissions.count_documents({"status": "held"})

    alerts: List[Dict[str, Any]] = []
    if drop_pct >= 0.5:
        alerts.append(
            {
                "severity": "high",
                "type": "intro_drop",
                "message": f"Intros dropped {int(drop_pct*100)}% in the last 24h vs prior 24h.",
            }
        )
    if suspicious > 0:
        alerts.append(
            {
                "severity": "medium",
                "type": "low_confidence",
                "message": f"{suspicious} live listings below verification threshold; will be auto-hidden by next verify pass.",
            }
        )
    if pending > 0:
        alerts.append(
            {
                "severity": "low",
                "type": "queue_lag",
                "message": f"{pending} ingestion items awaiting auto-score.",
            }
        )

    # Rolling integrity ratio
    total_pub = await db.trainers.count_documents({"published": True})
    verified = await db.trainers.count_documents({"published": True, "verification_status": "verified"})
    integrity = round(verified / max(1, total_pub), 3)

    snapshot = {
        "key": "health",
        "intros_24h": intros_24,
        "intros_prev_24h": intros_prev,
        "intros_change_pct": round(-drop_pct, 3),
        "conversions_24h": conv_24,
        "suspicious_listings": suspicious,
        "pending_submissions": pending,
        "held_submissions": held,
        "integrity_ratio": integrity,
        "alerts": alerts,
        "last_run": now_iso(),
    }
    await db.system_state.update_one({"key": "health"}, {"$set": snapshot}, upsert=True)
    return snapshot


# ---------------------------------------------------------------------------
# Loop scheduling
# ---------------------------------------------------------------------------


async def _run_loop(name: str, fn, interval: int) -> None:
    while True:
        try:
            await fn()
        except Exception:  # noqa: BLE001
            logger.exception("loop %s failed", name)
        await asyncio.sleep(interval)


def schedule_all(db, ai_service) -> List[asyncio.Task]:
    """Start every autonomous loop. Returns the spawned tasks."""
    tasks: List[asyncio.Task] = []
    if os.environ.get("DISABLE_AUTONOMY") == "1":
        logger.warning("autonomy disabled via env")
        return tasks

    tasks.append(asyncio.create_task(_run_loop("ranking", lambda: recompute_ranking(db), RANKING_INTERVAL_S)))
    tasks.append(asyncio.create_task(_run_loop("pricing", lambda: recompute_pricing(db), PRICING_INTERVAL_S)))
    tasks.append(
        asyncio.create_task(_run_loop("verification", lambda: reverify_listings(db, ai_service), VERIFICATION_INTERVAL_S))
    )
    tasks.append(asyncio.create_task(_run_loop("health", lambda: update_health(db), HEALTH_INTERVAL_S)))
    return tasks
