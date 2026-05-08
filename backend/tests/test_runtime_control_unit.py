from __future__ import annotations

import asyncio
import time

import pytest
from pymongo.errors import DuplicateKeyError

from services.engine import LoopLease
from services.runtime_control import resolve_loop_runtime


class FakeSystemState:
    def __init__(self):
        self.doc = None

    async def find_one_and_update(self, filt, update, upsert=False, return_document=None):
        _ = return_document
        now_epoch = time.time()
        allowed = False
        if self.doc is None:
            allowed = bool(upsert)
        else:
            if self.doc.get("owner_id") == filt["$or"][0].get("owner_id"):
                allowed = True
            elif float(self.doc.get("expires_at_epoch") or 0) <= now_epoch:
                allowed = True
            elif "expires_at_epoch" not in self.doc:
                allowed = True
        if not allowed:
            raise DuplicateKeyError("simulated unique key conflict")
        self.doc = dict(update.get("$set", {}))
        return dict(self.doc)

    async def find_one(self, filt, projection=None):
        _ = projection
        if self.doc is None:
            return None
        if filt.get("key") and self.doc.get("key") != filt.get("key"):
            return None
        return dict(self.doc)


class FakeDB:
    def __init__(self):
        self.system_state = FakeSystemState()


def test_runtime_control_defaults_to_api_owner():
    cfg = resolve_loop_runtime("api", env={})
    assert cfg.loop_owner == "api"
    assert cfg.should_schedule_loops is True
    assert cfg.source == "default"


def test_runtime_control_detects_owner_conflict():
    with pytest.raises(RuntimeError):
        resolve_loop_runtime(
            "api",
            env={
                "AUTONOMY_LOOP_OWNER": "worker",
                "RUN_AUTONOMY_IN_API": "1",
            },
        )


def test_runtime_control_disable_autonomy_stops_scheduling():
    cfg = resolve_loop_runtime(
        "worker",
        env={
            "AUTONOMY_LOOP_OWNER": "worker",
            "DISABLE_AUTONOMY": "1",
        },
    )
    assert cfg.should_schedule_loops is False


def test_runtime_control_rejects_invalid_lease_window():
    with pytest.raises(RuntimeError):
        resolve_loop_runtime(
            "api",
            env={
                "AUTONOMY_LOOP_LEASE_TTL_S": "30",
                "AUTONOMY_LOOP_LEASE_RENEW_S": "30",
            },
        )


def test_loop_lease_single_holder_and_failover():
    async def _run():
        db = FakeDB()
        lease_a = LoopLease(db, owner_id="owner-a", ttl_s=60, renew_s=10)
        lease_b = LoopLease(db, owner_id="owner-b", ttl_s=60, renew_s=10)

        acquired_a = await lease_a.heartbeat()
        acquired_b = await lease_b.heartbeat()
        assert acquired_a is True
        assert acquired_b is False

        db.system_state.doc["expires_at_epoch"] = time.time() - 1
        acquired_b_after_expiry = await lease_b.heartbeat()
        assert acquired_b_after_expiry is True

    asyncio.run(_run())
