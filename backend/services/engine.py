"""Autonomous engine — continuous loops the system runs without humans.

Loops (asyncio background tasks scheduled by ``schedule_all``):
  - ranking_loop      (60 s)  composite outcome_score over multiple signals.
  - pricing_loop      (90 s)  refreshes fixed intro fee state per suburb.
  - verification_loop (6 h)   age-weighted re-score; cross-source bonus.
  - discovery_loop    (10 min) processes the discovery_queue (ingestion).
  - inference_loop    (15 min) promotes inferred conversions to tracked/billed.
  - source_ingestion  (6 h)   scans configured source pages and queues candidates.
  - outreach_loop     (1 h)   sends T+7 follow-up emails via Resend.
  - billing_recovery  (30 min) retries failed intro collection with backoff.
  - nurture_loop      (1 h)   updates campaign/source remarketing cohorts.
  - reactivation_loop (6 h)   routes inactive trainers to reactivation lifecycle.
  - health_loop       (45 s)  anomaly detection + auto-rollback last-good config.

The functions in this module are unit-testable and idempotent.  Each writes
to ``system_state`` so ``GET /api/oversight`` can show the last run.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from . import automation as automation_service
from . import notifications as notifications_service
from . import stripe_billing

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
BILLING_RECOVERY_INTERVAL_S = 60 * 30
NURTURE_INTERVAL_S = 60 * 60
REACTIVATION_ROUTE_INTERVAL_S = 60 * 60 * 6
AUTONOMY_LEASE_KEY = "autonomy_loop_lease"

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


def _parse_iso(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _int_env(name: str, default: int, *, minimum: int = 1, maximum: int = 10_000) -> int:
    raw = (os.environ.get(name) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


FIXED_INTRO_FEE_CENTS = _int_env("FIXED_INTRO_FEE_CENTS", BASE_INTRO_FEE, minimum=100, maximum=50_000)


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
# Pricing loop — fixed intro fee state
# ---------------------------------------------------------------------------


async def recompute_pricing(db) -> Dict[str, Any]:
    """Per-suburb intro fee snapshot.

    Launch policy uses a fixed intro fee after trial, so this loop keeps
    `pricing_state` synchronized for oversight visibility.
    """
    cutoff = _iso_ago(days=7)
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}, "billing_status": "billed"}},
        {"$group": {"_id": "$suburb", "n": {"$sum": 1}}},
    ]
    rows = await db.intros.aggregate(pipeline).to_list(500)
    counts = {r["_id"]: r["n"] for r in rows if r.get("_id")}

    suburbs = await db.trainers.distinct("suburb", {"published": True})
    out: List[Dict[str, Any]] = []
    for suburb in suburbs:
        n = counts.get(suburb, 0)
        fee = int(FIXED_INTRO_FEE_CENTS)
        await db.pricing_state.update_one(
            {"suburb": suburb},
            {"$set": {
                "suburb": suburb,
                "multiplier": 1.0,
                "intro_fee_cents": fee,
                "intros_7d": n,
                "frozen": True,
                "pricing_mode": "fixed",
                "updated_at": now_iso(),
            }},
            upsert=True,
        )
        out.append({"suburb": suburb, "multiplier": 1.0, "intro_fee_cents": fee, "frozen": True, "pricing_mode": "fixed"})

    await db.system_state.update_one(
        {"key": "pricing"},
        {"$set": {
            "key": "pricing",
            "last_run": now_iso(),
            "suburbs_priced": len(out),
            "fixed_count": len(out),
        }},
        upsert=True,
    )
    return {"suburbs_priced": len(out)}


async def get_intro_fee(db, suburb: Optional[str]) -> int:
    fixed = int(FIXED_INTRO_FEE_CENTS)
    if suburb:
        ps = await db.pricing_state.find_one({"suburb": suburb}, {"_id": 0})
        if ps and ps.get("intro_fee_cents"):
            return int(ps["intro_fee_cents"])
    return fixed


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
                    "contact_ready": bool(t.get("website") or t.get("phone") or t.get("email")),
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
            domain_pattern = re.escape(domain)
            existing = await db.trainers.find_one(
                {"website": {"$regex": domain_pattern, "$options": "i"}}, {"_id": 0}
            )
        if not existing and name:
            name_pattern = re.escape(name)
            existing = await db.trainers.find_one(
                {"name": {"$regex": f"^{name_pattern}$", "$options": "i"}}, {"_id": 0}
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
                "contact_ready": bool(entry.get("url", "") or candidate.get("phone") or candidate.get("email")),
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
# Revenue recovery + growth nurture + reactivation routing
# ---------------------------------------------------------------------------


async def run_billing_recovery(db) -> Dict[str, Any]:
    """Retry intro collection with bounded attempts and exponential backoff."""
    max_attempts = _int_env("BILLING_RETRY_MAX_ATTEMPTS", 3, minimum=1, maximum=10)
    base_delay_h = _int_env("BILLING_RETRY_BASE_DELAY_HOURS", 24, minimum=1, maximum=168)
    retryable_statuses = {"payment_failed", "uncollectible", "invoice_error"}
    remediation_statuses = {"profile_incomplete", "consent_required", "stripe_unconfigured"}

    candidates = await db.intros.find(
        {"billing_status": "billed", "billing_collection_status": {"$in": list(retryable_statuses | remediation_statuses)}},
        {"_id": 0},
    ).to_list(3000)

    now_dt = now()
    scanned = len(candidates)
    retried = 0
    retry_sent = 0
    retry_failed = 0
    retry_exhausted = 0
    needs_remediation = 0
    waiting_backoff = 0

    for intro in candidates:
        status = str(intro.get("billing_collection_status") or "")
        if status in remediation_statuses:
            needs_remediation += 1
            if str(intro.get("billing_retry_state") or "") != "needs_remediation":
                await db.intros.update_one({"id": intro["id"]}, {"$set": {"billing_retry_state": "needs_remediation"}})
            continue

        attempts = int(intro.get("billing_retry_attempts") or 0)
        if attempts >= max_attempts:
            retry_exhausted += 1
            if str(intro.get("billing_retry_state") or "") != "retry_exhausted":
                await db.intros.update_one({"id": intro["id"]}, {"$set": {"billing_retry_state": "retry_exhausted"}})
            continue

        backoff_h = min(base_delay_h * (2 ** attempts), 168)
        last_ts = (
            intro.get("billing_last_retry_at")
            or intro.get("stripe_last_event_at")
            or intro.get("stripe_invoice_sent_at")
            or intro.get("created_at")
            or ""
        )
        last_dt = _parse_iso(str(last_ts))
        if last_dt and (now_dt - last_dt).total_seconds() < backoff_h * 3600:
            waiting_backoff += 1
            continue

        trainer = await db.trainers.find_one({"id": intro.get("trainer_id")}, {"_id": 0})
        if not trainer:
            needs_remediation += 1
            await db.intros.update_one(
                {"id": intro["id"]},
                {"$set": {
                    "billing_retry_state": "trainer_missing",
                    "billing_retry_attempts": attempts + 1,
                    "billing_last_retry_at": now_iso(),
                }},
            )
            continue

        billing_meta = await stripe_billing.bill_intro(db, trainer, intro)
        retried += 1
        new_status = str(billing_meta.get("billing_collection_status") or "")
        update_fields: Dict[str, Any] = {
            **billing_meta,
            "billing_retry_attempts": attempts + 1,
            "billing_last_retry_at": now_iso(),
            "billing_retry_max_attempts": max_attempts,
        }
        if new_status in {"invoice_sent", "invoice_finalized", "paid"}:
            update_fields["billing_retry_state"] = "retry_sent"
            retry_sent += 1
        elif new_status in remediation_statuses:
            update_fields["billing_retry_state"] = "needs_remediation"
            needs_remediation += 1
        else:
            update_fields["billing_retry_state"] = "retry_failed"
            retry_failed += 1
        await db.intros.update_one({"id": intro["id"]}, {"$set": update_fields})

    summary = {
        "scanned": scanned,
        "retried": retried,
        "retry_sent": retry_sent,
        "retry_failed": retry_failed,
        "retry_exhausted": retry_exhausted,
        "needs_remediation": needs_remediation,
        "waiting_backoff": waiting_backoff,
        "max_attempts": max_attempts,
        "base_delay_hours": base_delay_h,
    }
    await db.system_state.update_one(
        {"key": "billing_recovery"},
        {"$set": {"key": "billing_recovery", "last_run": now_iso(), **summary}},
        upsert=True,
    )
    return summary


async def run_growth_nurture(db) -> Dict[str, Any]:
    """Build remarketing cohorts from campaign/source attribution."""
    window_start = _iso_ago(days=30)
    matches = await db.match_events.find(
        {"created_at": {"$gte": window_start}},
        {"_id": 0, "id": 1, "campaign": 1, "source": 1, "created_at": 1},
    ).to_list(5000)

    if not matches:
        empty = {"cohorts": 0, "matched": 0, "connected": 0, "converted": 0, "remarketing_candidates": 0}
        await db.system_state.update_one(
            {"key": "nurture"},
            {"$set": {"key": "nurture", "last_run": now_iso(), **empty}},
            upsert=True,
        )
        return empty

    match_ids = [m["id"] for m in matches if m.get("id")]
    intros = await db.intros.find(
        {"match_id": {"$in": match_ids}},
        {"_id": 0, "id": 1, "match_id": 1, "created_at": 1, "campaign": 1, "source": 1},
    ).to_list(6000)
    intros_by_match: Dict[str, List[Dict[str, Any]]] = {}
    for intro in intros:
        intros_by_match.setdefault(str(intro.get("match_id") or ""), []).append(intro)

    intro_ids = [i["id"] for i in intros if i.get("id")]
    converted_intro_ids = set(
        await db.conversions.distinct(
            "intro_id",
            {"intro_id": {"$in": intro_ids}, "billing_status": {"$in": ["tracked", "billed", "suspicious"]}},
        )
    ) if intro_ids else set()

    now_dt = now()
    cohorts: Dict[str, Dict[str, Any]] = {}
    for match in matches:
        campaign = (match.get("campaign") or "unknown").strip().lower() or "unknown"
        source = (match.get("source") or "unknown").strip().lower() or "unknown"
        key = f"{campaign}|{source}"
        bucket = cohorts.setdefault(
            key,
            {
                "campaign": campaign,
                "source": source,
                "matched": 0,
                "connected": 0,
                "converted": 0,
                "remarketing_candidates": 0,
                "conversion_gap_candidates": 0,
            },
        )
        bucket["matched"] += 1
        linked_intros = intros_by_match.get(str(match.get("id") or ""), [])
        if linked_intros:
            bucket["connected"] += 1
            has_conversion = any(str(i.get("id") or "") in converted_intro_ids for i in linked_intros)
            if has_conversion:
                bucket["converted"] += 1
            else:
                oldest_intro = min((_parse_iso(str(i.get("created_at") or "")) for i in linked_intros if i.get("created_at")), default=None)
                if oldest_intro and (now_dt - oldest_intro).total_seconds() >= 7 * 24 * 3600:
                    bucket["conversion_gap_candidates"] += 1
        else:
            created_at = _parse_iso(str(match.get("created_at") or ""))
            if created_at and (now_dt - created_at).total_seconds() >= 24 * 3600:
                bucket["remarketing_candidates"] += 1

    upserts = 0
    remarketing_total = 0
    for value in cohorts.values():
        remarketing_total += int(value["remarketing_candidates"])
        await db.growth_attribution.update_one(
            {"campaign": value["campaign"], "source": value["source"]},
            {"$set": {
                **value,
                "updated_at": now_iso(),
            }},
            upsert=True,
        )
        upserts += 1

    summary = {
        "cohorts": upserts,
        "matched": sum(int(v["matched"]) for v in cohorts.values()),
        "connected": sum(int(v["connected"]) for v in cohorts.values()),
        "converted": sum(int(v["converted"]) for v in cohorts.values()),
        "remarketing_candidates": remarketing_total,
    }
    await db.system_state.update_one(
        {"key": "nurture"},
        {"$set": {"key": "nurture", "last_run": now_iso(), **summary}},
        upsert=True,
    )
    return summary


async def run_reactivation_routing(db) -> Dict[str, Any]:
    """Detect and route inactive/billing-blocked trainers into reactivation flow."""
    trainers = await db.trainers.find({}, {"_id": 0}).to_list(3000)
    now_dt = now()
    notify_cooldown_h = _int_env("REACTIVATION_NOTIFY_COOLDOWN_HOURS", 168, minimum=12, maximum=24 * 60)

    candidates: Dict[str, Dict[str, Any]] = {}
    for trainer in trainers:
        trainer_id = str(trainer.get("id") or "")
        if not trainer_id:
            continue
        reasons: List[str] = []
        created = _parse_iso(str(trainer.get("created_at") or ""))
        age_days = (now_dt - created).days if created else 999
        billing_state = str(trainer.get("billing_profile_status") or "")
        if age_days >= 14 and int(trainer.get("intros_30d") or 0) == 0:
            reasons.append("No intro activity in the past 30 days.")
        if not bool(trainer.get("published")) or float(trainer.get("confidence_score") or 0) < 0.60:
            reasons.append("Listing is currently unpublished or below confidence threshold.")
        if billing_state in {"missing_email", "profile_incomplete", "consent_required", "stripe_unconfigured", "stripe_error"}:
            reasons.append("Billing profile has unresolved blockers.")
        if not reasons:
            continue
        candidates[trainer_id] = {
            "trainer_id": trainer_id,
            "trainer_name": trainer.get("name", ""),
            "email": trainer.get("billing_email") or trainer.get("email") or "",
            "reasons": reasons,
            "status": "open",
            "updated_at": now_iso(),
        }

    existing_open = await db.reactivation_candidates.find({"status": "open"}, {"_id": 0, "trainer_id": 1}).to_list(4000)
    existing_open_ids = {str(row.get("trainer_id") or "") for row in existing_open}

    routed = 0
    notified = 0
    skipped_notify = 0
    for trainer_id, payload in candidates.items():
        prior = await db.reactivation_candidates.find_one({"trainer_id": trainer_id, "status": "open"}, {"_id": 0})
        await db.reactivation_candidates.update_one(
            {"trainer_id": trainer_id},
            {"$set": payload, "$setOnInsert": {"created_at": now_iso()}},
            upsert=True,
        )
        routed += 1

        last_notified_at = _parse_iso(str((prior or {}).get("last_notified_at") or ""))
        should_notify = prior is None
        if last_notified_at and (now_dt - last_notified_at).total_seconds() < notify_cooldown_h * 3600:
            should_notify = False
        if not should_notify:
            skipped_notify += 1
            continue
        outcome = await notifications_service.notify_trainer_reactivation_candidate(
            db,
            {
                "id": trainer_id,
                "name": payload["trainer_name"],
                "billing_email": payload["email"],
                "email": payload["email"],
            },
            reasons=payload["reasons"],
        )
        if outcome.get("status") == "sent":
            notified += 1
            await db.reactivation_candidates.update_one(
                {"trainer_id": trainer_id},
                {"$set": {"last_notified_at": now_iso(), "last_notification_status": "sent"}},
            )
        elif outcome.get("status") == "failed":
            await db.reactivation_candidates.update_one(
                {"trainer_id": trainer_id},
                {"$set": {"last_notified_at": now_iso(), "last_notification_status": "failed"}},
            )
        else:
            skipped_notify += 1

    resolved_ids = [x for x in existing_open_ids if x not in candidates]
    if resolved_ids:
        await db.reactivation_candidates.update_many(
            {"trainer_id": {"$in": resolved_ids}, "status": "open"},
            {"$set": {"status": "resolved", "resolved_at": now_iso(), "updated_at": now_iso()}},
        )

    summary = {
        "routed": routed,
        "notified": notified,
        "skipped_notify": skipped_notify,
        "resolved": len(resolved_ids),
        "open_candidates": routed,
    }
    await db.system_state.update_one(
        {"key": "reactivation_route"},
        {"$set": {"key": "reactivation_route", "last_run": now_iso(), **summary}},
        upsert=True,
    )
    return summary


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


class LoopLease:
    def __init__(self, db, *, owner_id: str, ttl_s: int, renew_s: int):
        self.db = db
        self.owner_id = owner_id
        self.ttl_s = ttl_s
        self.renew_s = renew_s
        self.is_holder = False
        self.last_seen_owner: Optional[str] = None

    async def heartbeat(self) -> bool:
        now_epoch = time.time()
        expires_epoch = now_epoch + self.ttl_s
        now_ts = now_iso()
        try:
            doc = await self.db.system_state.find_one_and_update(
                {
                    "key": AUTONOMY_LEASE_KEY,
                    "$or": [
                        {"owner_id": self.owner_id},
                        {"expires_at_epoch": {"$lte": now_epoch}},
                        {"expires_at_epoch": {"$exists": False}},
                    ],
                },
                {
                    "$set": {
                        "key": AUTONOMY_LEASE_KEY,
                        "owner_id": self.owner_id,
                        "expires_at_epoch": expires_epoch,
                        "ttl_s": self.ttl_s,
                        "last_heartbeat": now_ts,
                    },
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            doc = await self.db.system_state.find_one({"key": AUTONOMY_LEASE_KEY}, {"_id": 0})

        self.last_seen_owner = (doc or {}).get("owner_id")
        self.is_holder = bool(
            doc
            and doc.get("owner_id") == self.owner_id
            and float(doc.get("expires_at_epoch") or 0) > now_epoch
        )
        return self.is_holder


async def _mark_loop_success(db, name: str) -> None:
    await db.system_state.update_one(
        {"key": f"loop_status:{name}"},
        {
            "$set": {
                "key": f"loop_status:{name}",
                "name": name,
                "last_success": now_iso(),
                "last_error": "",
            },
            "$setOnInsert": {
                "consecutive_failures": 0,
            },
        },
        upsert=True,
    )
    await db.system_state.update_one(
        {"key": f"loop_status:{name}"},
        {"$set": {"consecutive_failures": 0}},
    )


async def _mark_loop_failure(db, name: str, error: str) -> None:
    row = await db.system_state.find_one({"key": f"loop_status:{name}"}, {"_id": 0}) or {}
    failures = int(row.get("consecutive_failures") or 0) + 1
    await db.system_state.update_one(
        {"key": f"loop_status:{name}"},
        {
            "$set": {
                "key": f"loop_status:{name}",
                "name": name,
                "last_failure": now_iso(),
                "last_error": error[:400],
                "consecutive_failures": failures,
            }
        },
        upsert=True,
    )


async def _run_loop_with_lease(name: str, fn, interval: int, lease: Optional[LoopLease], db) -> None:
    while True:
        try:
            if lease is None or lease.is_holder:
                await fn()
                await _mark_loop_success(db, name)
        except Exception:  # noqa: BLE001
            logger.exception("loop %s failed", name)
            await _mark_loop_failure(db, name, f"loop {name} failed")
        await asyncio.sleep(interval)


async def _lease_heartbeat_task(lease: LoopLease) -> None:
    was_holder = False
    while True:
        try:
            is_holder = await lease.heartbeat()
            if is_holder and not was_holder:
                logger.info("autonomy lease acquired owner_id=%s ttl=%ss", lease.owner_id, lease.ttl_s)
            if (not is_holder) and was_holder:
                logger.warning("autonomy lease lost owner_id=%s current_owner=%s", lease.owner_id, lease.last_seen_owner)
            was_holder = is_holder
        except Exception:  # noqa: BLE001
            logger.exception("autonomy lease heartbeat failed owner_id=%s", lease.owner_id)
            was_holder = False
        await asyncio.sleep(lease.renew_s)


def schedule_all(
    db,
    ai_service,
    *,
    owner_id: str = "",
    lease_enabled: bool = True,
    lease_ttl_s: int = 120,
    lease_renew_s: int = 30,
) -> List[asyncio.Task]:
    if os.environ.get("DISABLE_AUTONOMY") == "1":
        logger.warning("autonomy disabled via env")
        return []
    lease = LoopLease(
        db,
        owner_id=owner_id or f"autonomy@{os.getpid()}",
        ttl_s=lease_ttl_s,
        renew_s=lease_renew_s,
    ) if lease_enabled else None
    tasks = [
        asyncio.create_task(_run_loop_with_lease("ranking", lambda: recompute_ranking(db), RANKING_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("pricing", lambda: recompute_pricing(db), PRICING_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("verification", lambda: reverify_listings(db, ai_service), VERIFICATION_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("discovery", lambda: process_discovery_queue(db, ai_service), DISCOVERY_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("inference", lambda: promote_inferred_conversions(db), INFERENCE_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("health", lambda: update_health(db), HEALTH_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("source_ingestion", lambda: ingest_sources(db), SOURCE_INGEST_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("outreach", lambda: send_outreach(db), OUTREACH_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("billing_recovery", lambda: run_billing_recovery(db), BILLING_RECOVERY_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("nurture", lambda: run_growth_nurture(db), NURTURE_INTERVAL_S, lease, db)),
        asyncio.create_task(_run_loop_with_lease("reactivation_route", lambda: run_reactivation_routing(db), REACTIVATION_ROUTE_INTERVAL_S, lease, db)),
    ]
    if lease is not None:
        tasks.append(asyncio.create_task(_lease_heartbeat_task(lease)))
    return tasks
