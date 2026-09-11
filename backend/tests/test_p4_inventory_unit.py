from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from pymongo.errors import DuplicateKeyError

from services import engine, suburb_inventory


class _Result:
    def __init__(self, matched=1, modified=1):
        self.matched_count = matched
        self.modified_count = modified


def _matches(row, query):
    for key, expected in query.items():
        actual = row.get(key)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$lte" in expected and not (actual and actual <= expected["$lte"]):
                return False
            if "$gt" in expected and not (actual and actual > expected["$gt"]):
                return False
        elif actual != expected:
            return False
    return True


def _apply(row, update, *, inserted=False):
    if inserted:
        row.update(update.get("$setOnInsert") or {})
    row.update(update.get("$set") or {})
    for key, value in (update.get("$inc") or {}).items():
        row[key] = int(row.get(key) or 0) + int(value)
    for key in (update.get("$unset") or {}):
        row.pop(key, None)


class _Cursor:
    def __init__(self, rows):
        self.rows = [dict(row) for row in rows]

    def sort(self, key, direction):
        self.rows.sort(key=lambda row: row.get(key) or "", reverse=direction < 0)
        return self

    def limit(self, value):
        self.rows = self.rows[:value]
        return self

    async def to_list(self, value):
        return self.rows[:value]


class _Collection:
    def __init__(self):
        self.rows = {}
        self.lock = asyncio.Lock()

    async def insert_one(self, row):
        async with self.lock:
            key = row.get("id") or str(len(self.rows))
            if key in self.rows:
                raise DuplicateKeyError("duplicate")
            self.rows[key] = dict(row)
        return _Result()

    async def update_one(self, query, update, upsert=False):
        async with self.lock:
            row = next((item for item in self.rows.values() if _matches(item, query)), None)
            inserted = False
            if row is None and upsert:
                row = {key: value for key, value in query.items() if not key.startswith("$") and not isinstance(value, dict)}
                key = row.get("id") or str(len(self.rows))
                if key in self.rows:
                    raise DuplicateKeyError("duplicate")
                self.rows[key] = row
                inserted = True
            if row is None:
                return _Result(0, 0)
            next_occupancy = (update.get("$set") or {}).get("occupancy_key")
            if next_occupancy and any(
                other is not row and other.get("occupancy_key") == next_occupancy
                for other in self.rows.values()
            ):
                raise DuplicateKeyError("duplicate occupancy")
            _apply(row, update, inserted=inserted)
            return _Result(1, 1)

    async def find_one(self, query, _projection=None):
        async with self.lock:
            row = next((item for item in self.rows.values() if _matches(item, query)), None)
            return dict(row) if row else None

    async def find_one_and_update(self, query, update, upsert=False, return_document=None):
        async with self.lock:
            row = next((item for item in self.rows.values() if _matches(item, query)), None)
            inserted = False
            if row is None and upsert:
                row = {key: value for key, value in query.items() if not key.startswith("$") and not isinstance(value, dict)}
                key = row.get("id") or str(len(self.rows))
                if key in self.rows:
                    raise DuplicateKeyError("duplicate")
                self.rows[key] = row
                inserted = True
            if row is None:
                return None
            next_occupancy = (update.get("$set") or {}).get("occupancy_key")
            if next_occupancy and any(
                other is not row and other.get("occupancy_key") == next_occupancy
                for other in self.rows.values()
            ):
                raise DuplicateKeyError("duplicate occupancy")
            _apply(row, update, inserted=inserted)
            return dict(row)

    def find(self, query, _projection=None):
        return _Cursor([row for row in self.rows.values() if _matches(row, query)])

    async def count_documents(self, query):
        async with self.lock:
            return sum(1 for row in self.rows.values() if _matches(row, query))


def _db():
    return SimpleNamespace(
        sponsor_inventory=_Collection(),
        sponsor_inventory_events=_Collection(),
        sponsor_rotation_counters=_Collection(),
    )


def test_concurrent_suburb_reservations_never_exceed_two_slots():
    db = _db()

    async def run():
        return await asyncio.gather(
            *[
                suburb_inventory.reserve(db, trainer_id=f"trainer_{index}", tier="suburb_sponsor", suburb="Richmond")
                for index in range(3)
            ]
        )

    results = asyncio.run(run())
    assert sum(1 for result in results if result["ok"]) == 2
    assert sum(1 for result in results if result.get("code") == "inventory_sold_out") == 1
    assert sum(1 for row in db.sponsor_inventory.rows.values() if row.get("status") == "reserved") == 2


def test_reservation_is_idempotent_and_duplicate_business_cannot_take_both_slots():
    db = _db()
    first = asyncio.run(suburb_inventory.reserve(db, trainer_id="trainer_1", tier="suburb_sponsor", suburb="Richmond"))
    second = asyncio.run(suburb_inventory.reserve(db, trainer_id="trainer_1", tier="suburb_sponsor", suburb="Richmond"))

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["idempotent"] is True
    assert first["reservation"]["reservation_id"] == second["reservation"]["reservation_id"]


def test_expired_hold_is_released_and_slot_can_be_reserved_again():
    db = _db()
    first = asyncio.run(suburb_inventory.reserve(db, trainer_id="trainer_1", tier="suburb_sponsor", suburb="Richmond"))
    future = datetime.now(timezone.utc) + timedelta(hours=3)
    assert asyncio.run(suburb_inventory.release_expired(db, now=future)) == 1

    second = asyncio.run(suburb_inventory.reserve(db, trainer_id="trainer_2", tier="suburb_sponsor", suburb="Richmond"))
    assert second["ok"] is True
    assert second["reservation"]["slot"] == first["reservation"]["slot"]


def test_activation_and_cancellation_release_are_idempotent():
    db = _db()
    reserved = asyncio.run(suburb_inventory.reserve(db, trainer_id="trainer_1", tier="citywide"))
    reservation_id = reserved["reservation"]["reservation_id"]

    active = asyncio.run(suburb_inventory.activate_reservation(db, reservation_id=reservation_id, subscription_id="sub_1"))
    duplicate = asyncio.run(suburb_inventory.activate_reservation(db, reservation_id=reservation_id, subscription_id="sub_1"))
    released = asyncio.run(suburb_inventory.release_reservation(db, subscription_id="sub_1", reason="cancelled"))
    released_again = asyncio.run(suburb_inventory.release_reservation(db, subscription_id="sub_1", reason="cancelled"))

    assert active["ok"] is True
    assert duplicate["idempotent"] is True
    assert released["released"] == 1
    assert released_again["idempotent"] is True


def test_dual_suburb_sponsors_rotate_first_position_fairly():
    db = _db()
    for trainer_id in ("trainer_1", "trainer_2"):
        reserved = asyncio.run(suburb_inventory.reserve(db, trainer_id=trainer_id, tier="suburb_sponsor", suburb="Richmond"))
        asyncio.run(
            suburb_inventory.activate_reservation(
                db,
                reservation_id=reserved["reservation"]["reservation_id"],
                subscription_id=f"sub_{trainer_id}",
            )
        )
    trainers = [
        {"id": "trainer_1", "suburb": "Richmond", "review_rating": 4.8, "review_count": 20},
        {"id": "trainer_2", "suburb": "Richmond", "review_rating": 4.7, "review_count": 15},
        {"id": "organic", "suburb": "Richmond", "review_rating": 5.0, "review_count": 30},
    ]

    first = asyncio.run(suburb_inventory.rotate_public_trainers(db, trainers, suburb="Richmond"))
    second = asyncio.run(suburb_inventory.rotate_public_trainers(db, trainers, suburb="Richmond"))

    assert [first[0]["id"], second[0]["id"]] == ["trainer_1", "trainer_2"]
    assert first[2]["id"] == "organic"
    assert first[2]["placement"] == "community_choice"


def test_availability_exposes_capacity_without_trainer_identity():
    db = _db()
    asyncio.run(suburb_inventory.reserve(db, trainer_id="trainer_1", tier="suburb_sponsor", suburb="Richmond"))
    snapshot = asyncio.run(suburb_inventory.availability(db, ["Richmond"]))

    assert snapshot["suburbs"][0] == {
        "suburb": "Richmond",
        "capacity": 2,
        "occupied": 1,
        "available": 1,
        "status": "one_left",
    }


def test_inventory_maintenance_loop_releases_expired_holds(monkeypatch):
    monkeypatch.setattr(
        suburb_inventory,
        "release_expired",
        lambda _db: asyncio.sleep(0, result=3),
    )
    assert asyncio.run(engine.maintain_sponsor_inventory(SimpleNamespace())) == {"released": 3}
