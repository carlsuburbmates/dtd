"""Lightweight fraud / anti-gaming primitives.

These functions are pure async helpers used by the API layer; they don't
schedule their own work — the engine.health_loop surfaces aggregate signals.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_ago(hours: int = 0, minutes: int = 0) -> str:
    return (_now() - timedelta(hours=hours, minutes=minutes)).isoformat()


async def evaluate_intro(db, ip: str, trainer_id: str, user_email: str) -> Dict[str, Any]:
    """Return {accept: bool, delivery_status: str, status: str, fraud_status: str, reasons: [str]}.

    Soft-suppresses obvious abuse so the data doesn't poison ranking, but never
    hard-blocks the user (we want them to find a trainer; we just suppress the delivery/fraud signal).
    """
    reasons: list[str] = []
    accept = True
    delivery_status = "delivered"
    fraud_status = "clear"

    if ip:
        # rate-limit per IP / hour
        recent = await db.intros.count_documents(
            {"ip": ip, "created_at": {"$gte": _iso_ago(hours=1)}}
        )
        if recent >= 6:
            reasons.append("ip_rate_limited")
            delivery_status = "suppressed"
            fraud_status = "suppressed"
        # same-trainer same-IP within 24h → probably duplicate / clicker
        dup = await db.intros.count_documents(
            {"ip": ip, "trainer_id": trainer_id, "created_at": {"$gte": _iso_ago(hours=24)}}
        )
        if dup >= 1:
            reasons.append("ip_trainer_dup_24h")
            delivery_status = "suppressed"
            fraud_status = "suppressed"

    if user_email:
        # repeat from same email to same trainer within 7d → suppressed (still record)
        em = await db.intros.count_documents(
            {"user_email": user_email, "trainer_id": trainer_id,
             "created_at": {"$gte": _iso_ago(hours=24 * 7)}}
        )
        if em >= 1:
            reasons.append("email_trainer_dup_7d")
            delivery_status = "suppressed"
            fraud_status = "suppressed"

    return {
        "accept": accept,
        "delivery_status": delivery_status,
        "status": delivery_status,
        "fraud_status": fraud_status,
        "reasons": reasons,
    }


async def evaluate_conversion(db, intro: Dict[str, Any]) -> Dict[str, Any]:
    """Decide whether a manual conversion is suspicious or tracked.

    Conversions confirmed within ``CONVERSION_MIN_AGE_MINUTES`` of the intro
    are flagged as suspicious and stored as ``inferred=False, billing_status='suspicious', status='suspicious'``.
    The inference loop never auto-promotes 'suspicious' rows.
    """
    created = intro.get("created_at")
    age_min = 999
    if created:
        try:
            age_min = (_now() - datetime.fromisoformat(created)).total_seconds() / 60
        except ValueError:
            pass
    if age_min < 5:
        return {"quality_status": "suspicious", "status": "suspicious", "reason": "too_fast"}
    return {"quality_status": "tracked", "status": "tracked", "reason": ""}
