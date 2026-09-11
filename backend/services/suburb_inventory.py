from __future__ import annotations

import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


ACTIVE_STATES = {"reserved", "active"}
REUSABLE_STATES = ["available", "released", "expired", "cancelled", "refunded"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_key(value: Any) -> str:
    return "-".join(str(value or "").strip().lower().split())


def reservation_ttl_minutes() -> int:
    try:
        value = int((os.environ.get("SPONSOR_RESERVATION_TTL_MINUTES") or "30").strip())
    except ValueError:
        value = 30
    return max(5, min(value, 120))


def suburb_slot_cap() -> int:
    return 2


def citywide_slot_cap() -> int:
    return 5


def trainer_suburb_cap() -> int:
    try:
        value = int((os.environ.get("SPONSOR_MAX_SUBURBS_PER_TRAINER") or "5").strip())
    except ValueError:
        value = 5
    return max(3, min(value, 5))


def inventory_scope(tier: str, suburb: Optional[str] = None) -> Dict[str, Any]:
    normalized_tier = str(tier or "").strip().lower()
    if normalized_tier == "suburb_sponsor":
        key = normalize_key(suburb)
        if not key:
            raise ValueError("suburb_required_for_sponsor_inventory")
        return {"scope": "suburb", "key": key, "label": " ".join(str(suburb).strip().split()), "cap": suburb_slot_cap()}
    if normalized_tier == "citywide":
        return {"scope": "citywide", "key": "greater-melbourne", "label": "Greater Melbourne", "cap": citywide_slot_cap()}
    raise ValueError("tier_has_no_sponsor_inventory")


async def _record_event(db, event_type: str, **fields: Any) -> None:
    coll = getattr(db, "sponsor_inventory_events", None)
    if coll is None:
        return
    await coll.insert_one(
        {
            "id": f"inventory:{uuid.uuid4()}",
            "event_type": event_type,
            "status": fields.pop("status", "recorded"),
            "created_at": now_iso(),
            **fields,
        }
    )


async def release_expired(db, *, now: Optional[datetime] = None) -> int:
    coll = getattr(db, "sponsor_inventory", None)
    if coll is None:
        return 0
    current = now or datetime.now(timezone.utc)
    current_iso = current.isoformat()
    rows = await coll.find(
        {"status": "reserved", "expires_at": {"$lte": current_iso}},
        {"_id": 0},
    ).to_list(500)
    released = 0
    for row in rows:
        result = await coll.update_one(
            {"id": row.get("id"), "status": "reserved", "reservation_id": row.get("reservation_id")},
            {
                "$set": {"status": "expired", "release_reason": "reservation_expired", "updated_at": current_iso},
                "$unset": {"trainer_id": "", "occupancy_key": "", "stripe_subscription_id": "", "activated_at": ""},
            },
        )
        if getattr(result, "modified_count", 0):
            released += 1
            await _record_event(
                db,
                "reservation_expired",
                reservation_id=row.get("reservation_id"),
                trainer_id=row.get("trainer_id"),
                scope=row.get("scope"),
                key=row.get("key"),
                suburb=row.get("suburb"),
            )
    return released


async def reserve(
    db,
    *,
    trainer_id: str,
    tier: str,
    suburb: Optional[str] = None,
    idempotency_key: str = "",
) -> Dict[str, Any]:
    coll = getattr(db, "sponsor_inventory", None)
    if coll is None:
        return {"ok": False, "code": "inventory_store_unavailable"}
    trainer_id = str(trainer_id or "").strip()
    if not trainer_id:
        raise ValueError("trainer_id_required")
    scope = inventory_scope(tier, suburb)
    await release_expired(db)

    existing = await coll.find_one(
        {
            "scope": scope["scope"],
            "key": scope["key"],
            "trainer_id": trainer_id,
            "status": {"$in": list(ACTIVE_STATES)},
        },
        {"_id": 0},
    )
    if existing:
        return {"ok": True, "reservation": existing, "idempotent": True}

    now = datetime.now(timezone.utc)
    reservation_id = f"res_{uuid.uuid4().hex}"
    expires_at = (now + timedelta(minutes=reservation_ttl_minutes())).isoformat()
    occupancy_key = f"{scope['scope']}:{scope['key']}:{trainer_id}"
    acquired: Optional[Dict[str, Any]] = None

    for slot in range(1, int(scope["cap"]) + 1):
        slot_id = f"{scope['scope']}:{scope['key']}:{slot}"
        try:
            await coll.update_one(
                {"id": slot_id},
                {
                    "$setOnInsert": {
                        "id": slot_id,
                        "scope": scope["scope"],
                        "key": scope["key"],
                        "suburb": scope["label"] if scope["scope"] == "suburb" else "",
                        "slot": slot,
                        "status": "available",
                        "created_at": now.isoformat(),
                    }
                },
                upsert=True,
            )
            acquired = await coll.find_one_and_update(
                {"id": slot_id, "status": {"$in": REUSABLE_STATES}},
                {
                    "$set": {
                        "status": "reserved",
                        "trainer_id": trainer_id,
                        "tier": str(tier),
                        "occupancy_key": occupancy_key,
                        "reservation_id": reservation_id,
                        "idempotency_key": str(idempotency_key or ""),
                        "reserved_at": now.isoformat(),
                        "expires_at": expires_at,
                        "updated_at": now.isoformat(),
                        "release_reason": "",
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            acquired = None
        if acquired:
            break

    if not acquired:
        return {"ok": False, "code": "inventory_sold_out", "scope": scope}

    active_for_key = await coll.count_documents(
        {
            "scope": scope["scope"],
            "key": scope["key"],
            "trainer_id": trainer_id,
            "status": {"$in": list(ACTIVE_STATES)},
        }
    )
    active_suburbs = await coll.count_documents(
        {"scope": "suburb", "trainer_id": trainer_id, "status": {"$in": list(ACTIVE_STATES)}}
    )
    if active_for_key > 1 or (scope["scope"] == "suburb" and active_suburbs > trainer_suburb_cap()):
        code = "duplicate_sponsor_for_suburb" if active_for_key > 1 else "trainer_suburb_cap_reached"
        await release_reservation(db, reservation_id=reservation_id, reason=code)
        return {"ok": False, "code": code, "scope": scope}

    await _record_event(
        db,
        "inventory_reserved",
        reservation_id=reservation_id,
        trainer_id=trainer_id,
        scope=scope["scope"],
        key=scope["key"],
        suburb=scope["label"] if scope["scope"] == "suburb" else "",
        expires_at=expires_at,
    )
    return {"ok": True, "reservation": acquired, "idempotent": False}


async def activate_reservation(db, *, reservation_id: str, subscription_id: str) -> Dict[str, Any]:
    coll = getattr(db, "sponsor_inventory", None)
    if coll is None:
        return {"ok": False, "code": "inventory_store_unavailable"}
    await release_expired(db)
    now = now_iso()
    row = await coll.find_one_and_update(
        {"reservation_id": reservation_id, "status": "reserved", "expires_at": {"$gt": now}},
        {
            "$set": {
                "status": "active",
                "stripe_subscription_id": str(subscription_id or ""),
                "activated_at": now,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not row:
        existing = await coll.find_one(
            {"reservation_id": reservation_id, "status": "active", "stripe_subscription_id": str(subscription_id or "")},
            {"_id": 0},
        )
        if existing:
            return {"ok": True, "reservation": existing, "idempotent": True}
        return {"ok": False, "code": "reservation_missing_or_expired"}
    await _record_event(
        db,
        "inventory_activated",
        reservation_id=reservation_id,
        trainer_id=row.get("trainer_id"),
        scope=row.get("scope"),
        key=row.get("key"),
        suburb=row.get("suburb"),
        stripe_subscription_id=str(subscription_id or ""),
    )
    return {"ok": True, "reservation": row, "idempotent": False}


async def release_reservation(
    db,
    *,
    reservation_id: str = "",
    subscription_id: str = "",
    reason: str = "released",
) -> Dict[str, Any]:
    coll = getattr(db, "sponsor_inventory", None)
    if coll is None:
        return {"ok": False, "code": "inventory_store_unavailable", "released": 0}
    query: Dict[str, Any] = {"status": {"$in": list(ACTIVE_STATES)}}
    if reservation_id:
        query["reservation_id"] = reservation_id
    elif subscription_id:
        query["stripe_subscription_id"] = subscription_id
    else:
        raise ValueError("reservation_or_subscription_required")
    rows = await coll.find(query, {"_id": 0}).to_list(20)
    released = 0
    status = reason if reason in {"expired", "cancelled", "refunded"} else "released"
    for row in rows:
        result = await coll.update_one(
            {"id": row.get("id"), "status": {"$in": list(ACTIVE_STATES)}},
            {
                "$set": {"status": status, "release_reason": reason, "updated_at": now_iso()},
                "$unset": {"trainer_id": "", "occupancy_key": "", "stripe_subscription_id": "", "activated_at": "", "expires_at": ""},
            },
        )
        if getattr(result, "modified_count", 0):
            released += 1
            await _record_event(
                db,
                f"inventory_{status}",
                reservation_id=row.get("reservation_id"),
                trainer_id=row.get("trainer_id"),
                scope=row.get("scope"),
                key=row.get("key"),
                suburb=row.get("suburb"),
                stripe_subscription_id=row.get("stripe_subscription_id"),
                reason=reason,
            )
    return {"ok": True, "released": released, "idempotent": released == 0}


async def availability(db, suburbs: Iterable[str] = ()) -> Dict[str, Any]:
    coll = getattr(db, "sponsor_inventory", None)
    await release_expired(db)
    result: Dict[str, Any] = {
        "citywide": {"capacity": citywide_slot_cap(), "occupied": 0, "available": citywide_slot_cap(), "status": "available"},
        "suburbs": [],
    }
    if coll is None:
        result["store_available"] = False
        return result
    citywide_occupied = await coll.count_documents({"scope": "citywide", "key": "greater-melbourne", "status": {"$in": list(ACTIVE_STATES)}})
    result["citywide"] = _availability_row("Greater Melbourne", citywide_slot_cap(), citywide_occupied)
    for suburb in dict.fromkeys(" ".join(str(value).strip().split()) for value in suburbs if str(value).strip()):
        occupied = await coll.count_documents({"scope": "suburb", "key": normalize_key(suburb), "status": {"$in": list(ACTIVE_STATES)}})
        result["suburbs"].append(_availability_row(suburb, suburb_slot_cap(), occupied))
    result["store_available"] = True
    return result


def _availability_row(label: str, capacity: int, occupied: int) -> Dict[str, Any]:
    available = max(0, int(capacity) - int(occupied))
    status = "sold_out" if available == 0 else ("one_left" if available == 1 else "available")
    return {"suburb": label, "capacity": int(capacity), "occupied": int(occupied), "available": available, "status": status}


async def rotate_public_trainers(db, trainers: List[Dict[str, Any]], *, suburb: Optional[str]) -> List[Dict[str, Any]]:
    coll = getattr(db, "sponsor_inventory", None)
    counters = getattr(db, "sponsor_rotation_counters", None)
    if coll is None or not trainers:
        return trainers
    await release_expired(db)
    rows = await coll.find({"status": "active"}, {"_id": 0, "trainer_id": 1, "scope": 1, "key": 1}).to_list(1000)
    citywide_ids = [str(row.get("trainer_id")) for row in rows if row.get("scope") == "citywide"]
    suburb_key = normalize_key(suburb)
    suburb_ids = [str(row.get("trainer_id")) for row in rows if row.get("scope") == "suburb" and row.get("key") == suburb_key]

    async def rotated(ids: List[str], counter_key: str) -> List[str]:
        unique = list(dict.fromkeys(ids))
        if len(unique) < 2 or counters is None:
            return unique
        counter = await counters.find_one_and_update(
            {"id": counter_key},
            {"$inc": {"sequence": 1}, "$set": {"updated_at": now_iso()}, "$setOnInsert": {"created_at": now_iso()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        offset = (int((counter or {}).get("sequence") or 1) - 1) % len(unique)
        return unique[offset:] + unique[:offset]

    citywide_ids = await rotated(citywide_ids, "citywide:greater-melbourne")
    suburb_ids = await rotated(suburb_ids, f"suburb:{suburb_key}") if suburb_key else []
    by_id = {str(row.get("id")): dict(row) for row in trainers}
    used: set[str] = set()
    ordered: List[Dict[str, Any]] = []

    def add(ids: Iterable[str], placement: str) -> None:
        for trainer_id in ids:
            row = by_id.get(str(trainer_id))
            if row and str(trainer_id) not in used:
                row["placement"] = placement
                ordered.append(row)
                used.add(str(trainer_id))

    if suburb_key:
        add(suburb_ids, "suburb_sponsor")
        add(citywide_ids, "citywide_sponsor")
        organic = [row for row in trainers if str(row.get("id")) not in used]
        local = [row for row in organic if normalize_key(row.get("suburb")) == suburb_key]
        if local:
            community = max(local, key=lambda row: float(row.get("review_rating") or 0) * math.log(float(row.get("review_count") or 0) + 1))
            add([str(community.get("id"))], "community_choice")
    else:
        add(citywide_ids, "citywide_sponsor")
    add([str(row.get("id")) for row in trainers], "organic")
    return ordered


async def ops_snapshot(db) -> Dict[str, Any]:
    coll = getattr(db, "sponsor_inventory", None)
    events = getattr(db, "sponsor_inventory_events", None)
    expired_released = await release_expired(db)
    if coll is None:
        return {"available": False, "rows": [], "summary": {}, "exceptions": [], "expired_released": expired_released}
    rows = await coll.find({}, {"_id": 0}).to_list(1000)
    active = sum(1 for row in rows if row.get("status") == "active")
    reserved = sum(1 for row in rows if row.get("status") == "reserved")
    exception_rows: List[Dict[str, Any]] = []
    if events is not None:
        exception_rows = await events.find(
            {"status": {"$in": ["needs_review", "failed"]}},
            {"_id": 0},
        ).sort("created_at", -1).limit(50).to_list(50)
    return {
        "available": True,
        "rows": rows,
        "summary": {
            "active": active,
            "reserved": reserved,
            "reusable": len(rows) - active - reserved,
            "suburb_capacity": suburb_slot_cap(),
            "citywide_capacity": citywide_slot_cap(),
            "trainer_suburb_cap": trainer_suburb_cap(),
        },
        "exceptions": exception_rows,
        "expired_released": expired_released,
    }
