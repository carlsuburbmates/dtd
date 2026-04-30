"""Autonomous engine — continuous loops the system runs without humans.

Loops (asyncio background tasks scheduled by ``schedule_all``):
  - ranking_loop      (60 s)  composite outcome_score over multiple signals.
  - pricing_loop      (90 s)  EWMA-smoothed, threshold-gated dynamic intro fee.
  - verification_loop (6 h)   age-weighted re-score; cross-source bonus.
  - discovery_loop    (10 min) processes the discovery_queue (ingestion).
  - inference_loop    (15 min) promotes inferred conversions to tracked/billed.
  - source_ingestion  (6 h)   scans configured source pages and queues candidates.
  - outreach_loop     (1 h)   sends T+7 follow-up emails via Resend.
  - health_loop       (45 s)  anomaly detection + auto-rollback last-good config.

The functions in this module are unit-testable and idempotent.  Each writes
to ``system_state`` so ``GET /api/oversight`` can show the last run.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from . import automation as automation_service

logger = logging.getLogger("dtd.engine")

# ---- Tunables -------------------------------------------------------------

BASE_INTRO_FEE = 500            # cents AUD (A$5)
BASE_CONVERSION_FEE = 6500      # cents AUD (A$65)
CONVERSION_BILLING_MODE = (os.environ.get("CONVERSION_BILLING_MODE") or "track_only").strip().lower()

RANKING_INTERVAL_S = 60
PRICING_INTERVAL_S = 90
VERIFICATION_INTERVAL_S = 60 * 60 * 6
DISCOVERY_INTERVAL_S = 60 * 10
INFERENCE_INTERVAL_S = 60 * 15
HEALTH_INTERVAL_S = 45
SOURCE_INGEST_INTERVAL_S = 60 * 60 * 6
OUTREACH_INTERVAL_S = 60 * 60

# Pricing only goes dynamic after a suburb has enough demand data.  Below
# this threshold, price is frozen at BASE_INTRO_FEE so we never sticker-shock
# trainers from noise on day one.
PRICING_MIN_INTROS_7D = 10
PRICING_EWMA_ALPHA = 0.30           # smoothing factor

# Outcome score is a weighted blend of multiple signals.
W_CONV = 0.50
W_ENGAGE = 0.25
W_RESPONSE = 0.15
W_RECENCY = 0.10

# Anti-gaming.
INTRO_RATE_LIMIT_PER_IP_HOUR = 6
CONVERSION_MIN_AGE_MINUTES = 5      # below this we treat as suspicious / not billed
ACTIVE_REGION = (os.environ.get("ACTIVE_REGION") or "Greater Melbourne").strip()


def confirmed_conversion_statuses() -> List[str]:
    # Intro-first launch default: conversions are tracked for quality, not billed.
    # Keep `billed` included so legacy rows still participate in scoring/health.
    if CONVERSION_BILLING_MODE == "bill":
        return ["billed"]
    return ["tracked", "billed"]


# ---- Time helpers ---------------------------------------------------------


def now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now().isoformat()


def _iso_ago(days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    return (now() - timedelta(days=days, hours=hours, minutes=minutes)).isoformat()


# ---------------------------------------------------------------------------
# Ranking loop — composite outcome score
# ---------------------------------------------------------------------------


async def _engagement_count(db, trainer_id: str, since_iso: str) -> int:
    return await db.engagements.count_documents(
        {"trainer_id": trainer_id, "created_at": {"$gte": since_iso}}
    )


async def _avg_response_latency_min(db, trainer_id: str) -> Optional[float]:
    """Avg minutes from intro → first engagement (proxy for trainer responsiveness)."""
    cutoff = _iso_ago(days=30)
    pipeline = [
        {"$match": {"trainer_id": trainer_id, "created_at": {"$gte": cutoff}}},
        {"$lookup": {
            "from": "engagements",
            "let": {"iid": "$id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$intro_id", "$$iid"]}}},
                {"$sort": {"created_at": 1}},
                {"$limit": 1},
            ],
            "as": "first_eng",
        }},
        {"$match": {"first_eng.0": {"$exists": True}}},
        {"$project": {
            "minutes": {
                "$divide": [
                    {"$subtract": [
                        {"$dateFromString": {"dateString": {"$arrayElemAt": ["$first_eng.created_at", 0]}}},
                        {"$dateFromString": {"dateString": "$created_at"}},
                    ]},
                    1000 * 60,
                ]
            }
        }},
        {"$group": {"_id": None, "avg": {"$avg": "$minutes"}}},
    ]
    out = await db.intros.aggregate(pipeline).to_list(1)
    if not out:
        return None
    return float(out[0]["avg"])


async def recompute_ranking(db) -> Dict[str, Any]:
    """Composite outcome score per trainer.

    score = 0.50 * conversion_rate
          + 0.25 * engagement_rate
          + 0.15 * response_score
          + 0.10 * recency_score

    Each component is clipped to [0,1].  Score itself is clipped to [0.05, 0.99]
    so cold-start trainers still receive some impressions (exploration).
    """
    cutoff = _iso_ago(days=30)
    trainers = await db.trainers.find({}, {"_id": 0, "id": 1, "created_at": 1}).to_list(2000)
    scored = 0
    conv_statuses = confirmed_conversion_statuses()
    for t in trainers:
        intros = await db.intros.count_documents(
            {"trainer_id": t["id"], "created_at": {"$gte": cutoff}, "billing_status": "billed"}
        )
        conversions = await db.conversions.count_documents(
            {"trainer_id": t["id"], "created_at": {"$gte": cutoff}, "billing_status": {"$in": conv_statuses}}
        )
        engagements = await _engagement_count(db, t["id"], cutoff)

        # Conversion rate (Beta posterior mean) — equivalent to (conv+1)/(intros+2).
        alpha = 1 + conversions
        beta = 1 + max(0, intros - conversions)
        conv_rate = alpha / (alpha + beta)

        # Engagement rate vs. intros — clipped 0..1.
        engage_rate = min(1.0, engagements / max(1, intros))

        # Response score: ≤30 min = 1.0, 24h = 0.5, ≥7d = 0.0; or 0.5 if no data.
        latency = await _avg_response_latency_min(db, t["id"])
        if latency is None:
            response_score = 0.5
        else:
            # Inverse-like decay.
            response_score = max(0.0, 1.0 - min(1.0, latency / (60 * 24 * 7)))

        # Recency: how recently the trainer received any signal.
        last_intro = await db.intros.find_one(
            {"trainer_id": t["id"]}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)]
        )
        if last_intro:
            days_ago = (now() - datetime.fromisoformat(last_intro["created_at"])).days
            recency_score = max(0.0, 1.0 - days_ago / 60)
        else:
            recency_score = 0.5  # neutral for cold-start; verified=true also goes here

        composite = (
            W_CONV * conv_rate
            + W_ENGAGE * engage_rate
            + W_RESPONSE * response_score
            + W_RECENCY * recency_score
        )
        composite = max(0.05, min(0.99, composite))

        await db.trainers.update_one(
            {"id": t["id"]},
            {
                "$set": {
                    "outcome_score": round(composite, 4),
                    "outcome_breakdown": {
                        "conversion_rate": round(conv_rate, 4),
                        "engagement_rate": round(engage_rate, 4),
                        "response_score": round(response_score, 4),
                        "recency_score": round(recency_score, 4),
                    },
                    "intros_30d": intros,
                    "conversions_30d": conversions,
                    "engagements_30d": engagements,
                    "outcome_updated_at": now_iso(),
                }
            },
        )
        scored += 1
    await db.system_state.update_one(
        {"key": "ranking"},
        {"$set": {"key": "ranking", "last_run": now_iso(), "trainers_scored": scored}},
        upsert=True,
    )
    return {"trainers_scored": scored}


# ---------------------------------------------------------------------------
# Pricing loop — threshold-gated, EWMA-smoothed
# ---------------------------------------------------------------------------


async def recompute_pricing(db) -> Dict[str, Any]:
    """Per-suburb intro fee.  Stays at base until enough demand is observed,
    then uses an EWMA over the demand multiplier so prices don't whiplash.
    """
    cutoff = _iso_ago(days=7)
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}, "billing_status": "billed"}},
        {"$group": {"_id": "$suburb", "n": {"$sum": 1}}},
    ]
    rows = await db.intros.aggregate(pipeline).to_list(500)
    counts = {r["_id"]: r["n"] for r in rows if r.get("_id")}

    qualifying = [n for n in counts.values() if n >= PRICING_MIN_INTROS_7D]
    median = max(1, (sum(qualifying) / len(qualifying)) if qualifying else 1)

    suburbs = await db.trainers.distinct("suburb", {"published": True})
    out: List[Dict[str, Any]] = []
    for suburb in suburbs:
        n = counts.get(suburb, 0)
        if n < PRICING_MIN_INTROS_7D:
            target_mult = 1.0  # frozen at base
        else:
            target_mult = max(0.7, min(2.5, 0.7 + 0.6 * (n / median)))

        existing = await db.pricing_state.find_one({"suburb": suburb}, {"_id": 0})
        prev_mult = float(existing["multiplier"]) if existing and existing.get("multiplier") else 1.0
        # EWMA smoothing.
        smoothed = (1 - PRICING_EWMA_ALPHA) * prev_mult + PRICING_EWMA_ALPHA * target_mult
        smoothed = round(smoothed, 3)
        fee = int(BASE_INTRO_FEE * smoothed)
        await db.pricing_state.update_one(
            {"suburb": suburb},
            {"$set": {
                "suburb": suburb,
                "multiplier": smoothed,
                "intro_fee_cents": fee,
                "intros_7d": n,
                "frozen": n < PRICING_MIN_INTROS_7D,
                "updated_at": now_iso(),
            }},
            upsert=True,
        )
        out.append({"suburb": suburb, "multiplier": smoothed, "intro_fee_cents": fee, "frozen": n < PRICING_MIN_INTROS_7D})

    await db.system_state.update_one(
        {"key": "pricing"},
        {"$set": {
            "key": "pricing",
            "last_run": now_iso(),
            "suburbs_priced": len(out),
            "frozen_count": sum(1 for r in out if r["frozen"]),
        }},
        upsert=True,
    )
    return {"suburbs_priced": len(out)}


async def get_intro_fee(db, suburb: Optional[str]) -> int:
    if suburb:
        ps = await db.pricing_state.find_one({"suburb": suburb}, {"_id": 0})
        if ps and ps.get("intro_fee_cents"):
            return int(ps["intro_fee_cents"])
    return BASE_INTRO_FEE


# ---------------------------------------------------------------------------
# Verification loop — age-weighted, cross-source aware
# ---------------------------------------------------------------------------


async def reverify_listings(db, ai_service, batch: int = 5) -> Dict[str, Any]:
    """Re-verify the N listings that look most stale.

    A trainer's "staleness" is days since last `verified_at` plus a penalty for
    listings near the 0.6 cliff (more sensitive to drift).
    """
    candidates = await db.trainers.find({}, {"_id": 0}).to_list(2000)

    def staleness(t):
        verified_at = t.get("verified_at")
        if not verified_at:
            return 9999
        age_h = (now() - datetime.fromisoformat(verified_at)).total_seconds() / 3600
        # closer to threshold → more often
        score = float(t.get("confidence_score") or 0.5)
        penalty = 24 if 0.55 < score < 0.75 else 0
        return age_h + penalty

    candidates.sort(key=staleness, reverse=True)
    selected = candidates[:batch]
    rescored = 0
    auto_pub = 0
    auto_hide = 0
    for t in selected:
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
        # Cross-source bonus: if multiple distinct sources reference this listing.
        sources = await db.evidence.count_documents({"trainer_id": t["id"]})
        if sources >= 2:
            conf = min(1.0, conf + 0.05)
        status = ai_service.status_for_score(conf)
        was_published = bool(t.get("published"))
        published = conf >= 0.6
        if published and not was_published:
            auto_pub += 1
        elif not published and was_published:
            auto_hide += 1
        history_entry = {"score": round(conf, 3), "ts": now_iso(), "model": score.get("model", "heuristic")}
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
                },
                "$push": {"verification_history": {"$each": [history_entry], "$slice": -20}},
            },
        )
        rescored += 1
    await db.system_state.update_one(
        {"key": "verification"},
        {"$set": {
            "key": "verification",
            "last_run": now_iso(),
            "rescored": rescored,
            "auto_published": auto_pub,
            "auto_hidden": auto_hide,
        }},
        upsert=True,
    )
    return {"rescored": rescored, "auto_published": auto_pub, "auto_hidden": auto_hide}


# ---------------------------------------------------------------------------
# Discovery loop — autonomous ingestion from a queue
# ---------------------------------------------------------------------------


async def process_discovery_queue(db, ai_service, batch: int = 3) -> Dict[str, Any]:
    """Process pending entries in ``discovery_queue``.

    Each entry has {url, hint_name, hint_suburb, source}.  We score it via AI
    and either auto-publish (≥0.85), auto-list-unverified (0.60-0.84), or
    auto-discard (<0.60).  Duplicate detection is by lowercased domain or name.
    """
    pending = await db.discovery_queue.find({"status": "pending"}, {"_id": 0}).to_list(batch)
    handled = 0
    promoted = 0
    discarded = 0
    duplicate = 0
    for entry in pending:
        url = (entry.get("url") or "").strip().lower()
        name = (entry.get("hint_name") or "").strip()
        # dedup on domain or name match
        existing = None
        if url:
            domain = url.split("/")[2] if "://" in url else url.split("/")[0]
            existing = await db.trainers.find_one(
                {"website": {"$regex": domain, "$options": "i"}}, {"_id": 0}
            )
        if not existing and name:
            existing = await db.trainers.find_one(
                {"name": {"$regex": f"^{name}$", "$options": "i"}}, {"_id": 0}
            )
        if existing:
            await db.discovery_queue.update_one(
                {"id": entry["id"]},
                {"$set": {"status": "duplicate", "trainer_id": existing["id"], "processed_at": now_iso()}},
            )
            duplicate += 1
            handled += 1
            continue
        # score the candidate
        candidate = {
            "name": name,
            "suburb": entry.get("hint_suburb", ""),
            "website": entry.get("url", ""),
            "phone": "",
            "email": "",
            "services": [],
            "categories": [],
            "bio": entry.get("hint_bio", ""),
            "source_evidence_url": entry.get("source", entry.get("url", "")),
        }
        score = await ai_service.score_trainer(candidate)
        conf = float(score["confidence"])
        if conf < 0.60:
            await db.discovery_queue.update_one(
                {"id": entry["id"]},
                {"$set": {"status": "discarded", "confidence": conf, "reason": score.get("reasoning"), "processed_at": now_iso()}},
            )
            discarded += 1
            handled += 1
            continue
        trainer_id = entry["id"] + ":t"  # deterministic id from queue id
        await db.trainers.insert_one(
            {
                "id": trainer_id,
                "name": name or "Unknown",
                "suburb": entry.get("hint_suburb", ""),
                "region": ACTIVE_REGION,
                "website": entry.get("url", ""),
                "phone": "",
                "email": "",
                "categories": [],
                "services": [],
                "bio": entry.get("hint_bio", ""),
                "image_url": "",
                "source_evidence_url": entry.get("source", entry.get("url", "")),
                "confidence_score": conf,
                "verification_status": ai_service.status_for_score(conf),
                "verification_reasoning": score.get("reasoning", ""),
                "verification_signals": score.get("signals", []),
                "verification_model": score.get("model", "heuristic"),
                "verified_at": now_iso(),
                "outcome_score": 0.05,
                "intros_30d": 0,
                "conversions_30d": 0,
                "engagements_30d": 0,
                "published": True,
                "created_at": now_iso(),
                "via_discovery": True,
            }
        )
        await db.discovery_queue.update_one(
            {"id": entry["id"]},
            {"$set": {"status": "promoted", "trainer_id": trainer_id, "confidence": conf, "processed_at": now_iso()}},
        )
        promoted += 1
        handled += 1
    await db.system_state.update_one(
        {"key": "discovery"},
        {"$set": {
            "key": "discovery",
            "last_run": now_iso(),
            "handled": handled,
            "promoted": promoted,
            "discarded": discarded,
            "duplicates": duplicate,
            "queue_pending": await db.discovery_queue.count_documents({"status": "pending"}),
        }},
        upsert=True,
    )
    return {"handled": handled, "promoted": promoted, "discarded": discarded, "duplicates": duplicate}


# ---------------------------------------------------------------------------
# Inference loop — promote high-confidence inferred conversions to billable
# ---------------------------------------------------------------------------


async def promote_inferred_conversions(db) -> Dict[str, Any]:
    """Inferred conversions live as `conversions` rows with `inferred=True` and
    a confidence in (0,1).  Once they age past 48h and confidence is ≥0.8, we
    flip ``billing_status`` to ``tracked`` in launch mode or ``billed`` in bill mode.
    """
    cutoff = _iso_ago(hours=48)
    cursor = db.conversions.find(
        {"inferred": True, "billing_status": "pending", "confidence": {"$gte": 0.8}, "created_at": {"$lt": cutoff}},
        {"_id": 0},
    )
    promoted = 0
    target_status = "billed" if CONVERSION_BILLING_MODE == "bill" else "tracked"
    async for conv in cursor:
        await db.conversions.update_one(
            {"id": conv["id"]},
            {"$set": {"billing_status": target_status, "billed_at": now_iso(), "fee_cents": BASE_CONVERSION_FEE if target_status == "billed" else 0}},
        )
        promoted += 1
    await db.system_state.update_one(
        {"key": "inference"},
        {"$set": {"key": "inference", "last_run": now_iso(), "promoted_inferred": promoted}},
        upsert=True,
    )
    return {"promoted_inferred": promoted}


# ---------------------------------------------------------------------------
# Health loop — anomaly detection + auto-rollback
# ---------------------------------------------------------------------------


async def update_health(db) -> Dict[str, Any]:
    conv_statuses = confirmed_conversion_statuses()
    intros_24 = await db.intros.count_documents(
        {"created_at": {"$gte": _iso_ago(hours=24)}, "billing_status": "billed"}
    )
    intros_prev = await db.intros.count_documents(
        {"created_at": {"$gte": _iso_ago(hours=48), "$lt": _iso_ago(hours=24)},
         "billing_status": "billed"}
    )
    conv_24 = await db.conversions.count_documents(
        {"created_at": {"$gte": _iso_ago(hours=24)}, "billing_status": {"$in": conv_statuses}}
    )
    conv_prev = await db.conversions.count_documents(
        {"created_at": {"$gte": _iso_ago(hours=48), "$lt": _iso_ago(hours=24)},
         "billing_status": {"$in": conv_statuses}}
    )

    intro_drop = (intros_prev - intros_24) / intros_prev if intros_prev > 4 else 0.0
    conv_drop = (conv_prev - conv_24) / conv_prev if conv_prev > 4 else 0.0

    suspicious = await db.trainers.count_documents(
        {"$or": [{"verification_status": "hold"}, {"confidence_score": {"$lt": 0.6}}]}
    )
    pending = await db.submissions.count_documents({"status": "pending"})
    suppressed_intros = await db.intros.count_documents({"billing_status": "suppressed"})

    alerts: List[Dict[str, Any]] = []
    rollback_event: Optional[Dict[str, Any]] = None

    if intro_drop >= 0.5:
        alerts.append({"severity": "high", "type": "intro_drop", "message": f"Intros dropped {int(intro_drop*100)}% in 24h."})
    if conv_drop >= 0.5:
        # Auto-rollback: if a config change in the last hour, revert it.
        latest_change = await db.config_snapshots.find_one(
            {"applied_at": {"$gte": _iso_ago(hours=1)}, "rolled_back": {"$ne": True}},
            {"_id": 0},
            sort=[("applied_at", -1)],
        )
        if latest_change:
            await db.config_snapshots.update_one(
                {"id": latest_change["id"]},
                {"$set": {"rolled_back": True, "rolled_back_at": now_iso(), "reason": "conv_drop_50"}},
            )
            rollback_event = {"snapshot_id": latest_change["id"], "kind": latest_change.get("kind"), "ts": now_iso()}
            alerts.append({"severity": "high", "type": "auto_rollback", "message": f"Auto-rolled back config '{latest_change.get('kind')}' due to conversion-rate cliff."})
        else:
            alerts.append({"severity": "high", "type": "conv_drop", "message": f"Conversions dropped {int(conv_drop*100)}% in 24h."})
    if suppressed_intros > 0:
        alerts.append({"severity": "medium", "type": "fraud_suppressed", "message": f"{suppressed_intros} intros suppressed for fraud signals."})
    if suspicious > 0:
        alerts.append({"severity": "low", "type": "low_confidence", "message": f"{suspicious} listings below verification threshold; verify-loop will hide them."})
    if pending > 0:
        alerts.append({"severity": "low", "type": "queue_lag", "message": f"{pending} submissions waiting on auto-score."})

    total_pub = await db.trainers.count_documents({"published": True})
    verified = await db.trainers.count_documents({"published": True, "verification_status": "verified"})
    integrity = round(verified / max(1, total_pub), 3)

    snapshot = {
        "key": "health",
        "intros_24h": intros_24,
        "intros_prev_24h": intros_prev,
        "intros_change_pct": round(-intro_drop, 3),
        "conversions_24h": conv_24,
        "conversions_prev_24h": conv_prev,
        "conversions_change_pct": round(-conv_drop, 3),
        "suspicious_listings": suspicious,
        "pending_submissions": pending,
        "suppressed_intros": suppressed_intros,
        "integrity_ratio": integrity,
        "alerts": alerts,
        "rollback_event": rollback_event,
        "last_run": now_iso(),
    }
    await db.system_state.update_one({"key": "health"}, {"$set": snapshot}, upsert=True)
    return snapshot


# ---------------------------------------------------------------------------
# Source ingestion + outreach loops
# ---------------------------------------------------------------------------


async def ingest_sources(db) -> Dict[str, Any]:
    result = await automation_service.ingest_discovery_sources(db)
    await db.system_state.update_one(
        {"key": "source_ingestion"},
        {"$set": {"key": "source_ingestion", "last_run": now_iso(), **result}},
        upsert=True,
    )
    return result


async def send_outreach(db) -> Dict[str, Any]:
    result = await automation_service.send_t7_outreach(db)
    await db.system_state.update_one(
        {"key": "outreach"},
        {"$set": {"key": "outreach", "last_run": now_iso(), **result}},
        upsert=True,
    )
    return result


# ---------------------------------------------------------------------------
# Loop runner
# ---------------------------------------------------------------------------


async def _run_loop(name: str, fn, interval: int) -> None:
    while True:
        try:
            await fn()
        except Exception:  # noqa: BLE001
            logger.exception("loop %s failed", name)
        await asyncio.sleep(interval)


def schedule_all(db, ai_service) -> List[asyncio.Task]:
    if os.environ.get("DISABLE_AUTONOMY") == "1":
        logger.warning("autonomy disabled via env")
        return []
    tasks = [
        asyncio.create_task(_run_loop("ranking", lambda: recompute_ranking(db), RANKING_INTERVAL_S)),
        asyncio.create_task(_run_loop("pricing", lambda: recompute_pricing(db), PRICING_INTERVAL_S)),
        asyncio.create_task(_run_loop("verification", lambda: reverify_listings(db, ai_service), VERIFICATION_INTERVAL_S)),
        asyncio.create_task(_run_loop("discovery", lambda: process_discovery_queue(db, ai_service), DISCOVERY_INTERVAL_S)),
        asyncio.create_task(_run_loop("inference", lambda: promote_inferred_conversions(db), INFERENCE_INTERVAL_S)),
        asyncio.create_task(_run_loop("health", lambda: update_health(db), HEALTH_INTERVAL_S)),
        asyncio.create_task(_run_loop("source_ingestion", lambda: ingest_sources(db), SOURCE_INGEST_INTERVAL_S)),
        asyncio.create_task(_run_loop("outreach", lambda: send_outreach(db), OUTREACH_INTERVAL_S)),
    ]
    return tasks
