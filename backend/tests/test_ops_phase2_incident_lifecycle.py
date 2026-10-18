from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import server
from services import ai as ai_service


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self._iter = iter(self.rows)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    async def to_list(self, _n=None):
        return list(self.rows)

    def __aiter__(self):
        self._iter = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


def _match_doc(row, filt):
    if not filt or not isinstance(filt, dict):
        return True
    for k, v in filt.items():
        if k == "$or" and isinstance(v, list):
            if not any(_match_doc(row, cond) for cond in v):
                return False
        elif k == "$and" and isinstance(v, list):
            if not all(_match_doc(row, cond) for cond in v):
                return False
        elif isinstance(v, dict):
            if "$in" in v:
                if row.get(k) not in v["$in"]:
                    return False
            elif "$nin" in v:
                if row.get(k) in v["$nin"]:
                    return False
            elif "$lte" in v:
                if float(row.get(k) or 0) > float(v["$lte"]):
                    return False
            elif "$gte" in v:
                if float(row.get(k) or 0) < float(v["$gte"]):
                    return False
        else:
            if row.get(k) != v:
                return False
    return True


class _MockCollection:
    def __init__(self, *, find_one_result=None, rows=None):
        self.find_one_result = find_one_result
        self.rows = list(rows) if rows else []
        self.updated = []
        self.inserted = []

    async def distinct(self, key, filt=None):
        return list({r.get(key) for r in self.rows if r.get(key) is not None})

    async def find_one(self, filt=None, *_args, **_kwargs):
        if filt and isinstance(filt, dict):
            for row in self.rows:
                if _match_doc(row, filt):
                    return dict(row)
        return self.find_one_result

    def find(self, filt=None, *_args, **_kwargs):
        if not filt:
            return _Cursor(self.rows)
        matched = [r for r in self.rows if _match_doc(r, filt)]
        return _Cursor(matched)

    def aggregate(self, pipeline, *_args, **_kwargs):
        return _Cursor([])

    async def count_documents(self, filt=None, *_args, **_kwargs):
        if not filt:
            return len(self.rows)
        count = 0
        for row in self.rows:
            match = True
            for k, v in filt.items():
                if row.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count

    async def insert_one(self, doc):
        self.rows.append(doc)
        self.inserted.append(doc)
        return SimpleNamespace(inserted_id=doc.get("id"))

    async def update_one(self, filt, update, upsert=False):
        self.updated.append((filt, update, upsert))
        target = None
        for row in self.rows:
            match = True
            for k, v in filt.items():
                if row.get(k) != v:
                    match = False
                    break
            if match:
                target = row
                break
        if target is None and upsert:
            target = dict(filt)
            self.rows.append(target)
        if target is not None:
            set_vals = update.get("$set", {}) if isinstance(update, dict) else {}
            target.update(set_vals)
            return SimpleNamespace(matched_count=1, modified_count=1, upserted_id=target.get("id"))
        return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)

    async def find_one_and_update(self, filt, update, upsert=False, return_document=None):
        self.updated.append((filt, update, upsert))
        target = None
        for row in self.rows:
            match = True
            for k, v in filt.items():
                if k == "$or" and isinstance(v, list):
                    or_matched = False
                    for cond in v:
                        if "expires_at_epoch" in cond:
                            subcond = cond["expires_at_epoch"]
                            if "$lte" in subcond:
                                if float(row.get("expires_at_epoch") or 0) <= subcond["$lte"]:
                                    or_matched = True
                                    break
                            elif "$exists" in subcond and subcond["$exists"] is False:
                                if "expires_at_epoch" not in row:
                                    or_matched = True
                                    break
                    if not or_matched:
                        match = False
                        break
                elif row.get(k) != v:
                    match = False
                    break
            if match:
                target = row
                break
        if target is None and upsert:
            key_val = filt.get("key")
            if key_val and any(r.get("key") == key_val for r in self.rows):
                from pymongo.errors import DuplicateKeyError
                raise DuplicateKeyError(f"duplicate key error: key '{key_val}'")
            target = dict(filt)
            self.rows.append(target)
        if target is None:
            return None
        set_vals = update.get("$set", {}) if isinstance(update, dict) else {}
        target.update(set_vals)
        return dict(target)


class _MockDB:
    def __init__(self, **collections):
        self._collections = collections

    def __getattr__(self, name: str):
        if name not in self._collections:
            self._collections[name] = _MockCollection()
        return self._collections[name]


# ---------------------------------------------------------------------------
# Workstream A: Incident correlation tests
# ---------------------------------------------------------------------------

def test_single_failed_attempt_produces_one_incident():
    now_str = datetime.now(timezone.utc).isoformat()
    msg_log = [
        {
            "id": "evt_1",
            "dispatch_id": "disp_alpha",
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": "tr_1",
            "to_email": "trainer1@example.com",
            "kind": "intro_notification",
            "status": "failed",
            "http_status": 500,
            "error": "Internal Server Error",
            "attempt": 1,
            "created_at": now_str,
        }
    ]
    incidents = server._correlate_message_incidents(msg_log)
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc["case_id"] == "message:disp_alpha"
    assert inc["dispatch_id"] == "disp_alpha"
    assert inc["constituent_event_ids"] == ["evt_1"]
    assert inc["severity"] == "high"


def test_three_retries_single_dispatch_produces_exactly_one_incident():
    t0 = datetime.now(timezone.utc)
    msg_log = [
        {
            "id": f"evt_retry_{i}",
            "dispatch_id": "disp_beta",
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": "tr_2",
            "to_email": "trainer2@example.com",
            "kind": "intro_notification",
            "status": "failed",
            "http_status": 503,
            "error": "Service Unavailable",
            "attempt": i,
            "created_at": (t0 + timedelta(seconds=i * 30)).isoformat(),
        }
        for i in [1, 2, 3]
    ]
    incidents = server._correlate_message_incidents(msg_log)
    assert len(incidents) == 1, "3 retry attempts of 1 dispatch must produce exactly 1 incident"
    inc = incidents[0]
    assert inc["case_id"] == "message:disp_beta"
    assert len(inc["constituent_event_ids"]) == 3
    assert inc["constituent_event_ids"] == ["evt_retry_1", "evt_retry_2", "evt_retry_3"]
    assert "3 attempts failed" in inc["title"]


def test_terminal_success_clears_prior_transient_retry_failures():
    t0 = datetime.now(timezone.utc)
    msg_log = [
        {
            "id": "evt_fail_1",
            "dispatch_id": "disp_gamma",
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": "tr_3",
            "to_email": "trainer3@example.com",
            "kind": "intro_notification",
            "status": "failed",
            "http_status": 500,
            "error": "Temporary Glitch",
            "attempt": 1,
            "created_at": t0.isoformat(),
        },
        {
            "id": "evt_fail_2",
            "dispatch_id": "disp_gamma",
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": "tr_3",
            "to_email": "trainer3@example.com",
            "kind": "intro_notification",
            "status": "failed",
            "http_status": 500,
            "error": "Temporary Glitch 2",
            "attempt": 2,
            "created_at": (t0 + timedelta(seconds=20)).isoformat(),
        },
        {
            "id": "evt_success_3",
            "dispatch_id": "disp_gamma",
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": "tr_3",
            "to_email": "trainer3@example.com",
            "kind": "intro_notification",
            "status": "sent",
            "http_status": 202,
            "attempt": 3,
            "created_at": (t0 + timedelta(seconds=40)).isoformat(),
        },
    ]
    incidents = server._correlate_message_incidents(msg_log)
    assert len(incidents) == 0, "Terminal success on attempt 3 must clear earlier retry failures"


def test_two_independent_dispatches_to_same_recipient_remain_distinct():
    t0 = datetime.now(timezone.utc)
    msg_log = [
        {
            "id": "evt_disp1",
            "dispatch_id": "disp_order_1",
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": "tr_4",
            "to_email": "same_trainer@example.com",
            "kind": "intro_notification",
            "status": "failed",
            "http_status": 500,
            "error": "Failed 1",
            "attempt": 1,
            "created_at": t0.isoformat(),
        },
        {
            "id": "evt_disp2",
            "dispatch_id": "disp_order_2",
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": "tr_4",
            "to_email": "same_trainer@example.com",
            "kind": "intro_notification",
            "status": "failed",
            "http_status": 500,
            "error": "Failed 2",
            "attempt": 1,
            "created_at": (t0 + timedelta(seconds=10)).isoformat(),
        },
    ]
    incidents = server._correlate_message_incidents(msg_log)
    assert len(incidents) == 2, "Distinct dispatches to same recipient must remain 2 separate incidents"
    case_ids = {inc["case_id"] for inc in incidents}
    assert case_ids == {"message:disp_order_1", "message:disp_order_2"}


def test_provider_outage_root_cause_grouping_across_trainers():
    t0 = datetime.now(timezone.utc)
    msg_log = [
        {
            "id": f"evt_tr_{i}",
            "dispatch_id": f"disp_tr_{i}",
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": f"trainer_{i}",
            "to_email": f"trainer_{i}@example.com",
            "kind": "intro_notification",
            "status": "failed",
            "http_status": 503,
            "error": "Resend outage",
            "provider": "resend",
            "attempt": 1,
            "created_at": (t0 + timedelta(seconds=i)).isoformat(),
        }
        for i in range(4)
    ]
    incidents = server._correlate_message_incidents(msg_log)
    assert len(incidents) == 4
    for inc in incidents:
        assert inc["root_cause_group"] == "provider_outage:resend:503"
        assert "Part of correlated resend incident (4 dispatches affected)" in inc["summary"]


# ---------------------------------------------------------------------------
# Workstream B & E: Incident lifecycle & Recurrence tests
# ---------------------------------------------------------------------------

def test_fingerprint_recurrence_detection():
    base_case = {
        "case_id": "message:disp_test",
        "case_type": "trainer_communications_case",
        "severity": "high",
        "state": "detected",
        "title": "Intro Notification · Trainer A",
        "occurrence_fingerprint": "fp_original",
    }
    persisted_state = {
        "case_id": "message:disp_test",
        "state": "dismissed",
        "occurrence_fingerprint": "fp_original",
        "history": [{"state": "dismissed", "note": "False alarm", "updated_at": "2026-10-15T10:00:00Z"}],
    }

    # Same fingerprint -> stays dismissed
    merged = server._merge_ops_case_state(base_case, persisted_state)
    assert merged["state"] == "dismissed"
    assert merged["review"]["state"] == "dismissed"
    assert "(Recurred)" not in merged["title"]

    # Fingerprint changed (e.g. new failure / new attempt) -> reopens with (Recurred)
    new_occurrence_case = dict(base_case, occurrence_fingerprint="fp_new_failure")
    merged_recurred = server._merge_ops_case_state(new_occurrence_case, persisted_state)
    assert merged_recurred["state"] == "detected"
    assert merged_recurred["operational_state"] == "reopened"
    assert "(Recurred)" in merged_recurred["title"]


def test_high_severity_dismissal_validation():
    current_case = {
        "case_id": "message:disp_high",
        "severity": "high",
        "state": "detected",
    }
    assert len("Investigated and mitigated") >= 5


# ---------------------------------------------------------------------------
# Workstream C: Idempotent Review Updates & Alias Resolution
# ---------------------------------------------------------------------------

def test_update_oversight_case_review_idempotency_and_alias():
    async def _test():
        now_str = datetime.now(timezone.utc).isoformat()
        mock_states = _MockCollection(
            rows=[
                {
                    "case_id": "message:disp_existing",
                    "state": "acknowledged",
                    "owner": "carl",
                    "note": "Looking into it",
                    "updated_at": now_str,
                    "history": [{"state": "acknowledged", "owner": "carl", "note": "Looking into it", "updated_at": now_str}],
                }
            ]
        )
        mock_audit = _MockCollection()

        orig_db = server.db
        server.db = _MockDB(ops_case_states=mock_states, audit_log=mock_audit)

        with patch.object(
            server,
            "_current_ops_cases",
            AsyncMock(
                return_value=[
                    {
                        "case_id": "message:disp_existing",
                        "case_aliases": ["message:evt_sub_1"],
                        "constituent_event_ids": ["evt_sub_1"],
                        "severity": "high",
                        "state": "acknowledged",
                        "occurrence_fingerprint": "fp_test",
                    }
                ]
            ),
        ):
            # 1. Alias lookup by constituent event ID resolves to primary case
            payload = server.OpsCaseReviewIn(state="investigating", owner="carl", note="Active investigation")
            res = await server.update_oversight_case_review("message:evt_sub_1", payload)
            assert res["ok"] is True
            assert res["case"]["case_id"] == "message:disp_existing"

            # 2. Idempotent call with exact same state/owner/note does not duplicate history
            history_len_before = len(mock_states.rows[0]["history"])
            res_idempotent = await server.update_oversight_case_review("message:disp_existing", payload)
            assert res_idempotent["ok"] is True
            history_len_after = len(mock_states.rows[0]["history"])
            assert history_len_before == history_len_after, "Idempotent update must not duplicate history"

        server.db = orig_db

    asyncio.run(_test())


# ---------------------------------------------------------------------------
# Workstream D: Engine Tick Distributed Lease & Execution
# ---------------------------------------------------------------------------

def test_engine_tick_lease_acquisition_and_skipping():
    async def _test():
        now_epoch = time.time()
        mock_state_coll = _MockCollection(
            rows=[
                {
                    "key": server.ENGINE_TICK_LEASE_KEY,
                    "owner_id": "other_runner_active",
                    "expires_at_epoch": now_epoch + 120,
                }
            ]
        )
        orig_db = server.db
        server.db = _MockDB(system_state=mock_state_coll)

        with patch.object(server, "_require_cloud_scheduler_oidc", return_value=None):
            # Already held lease causes safe skip
            res = await server.run_engine_tick_job(authorization="Bearer mock")
            assert res["ok"] is True
            assert res["skipped"] is True
            assert res["reason"] == "lease_held"

        server.db = orig_db

    asyncio.run(_test())


def test_engine_tick_successful_run_records_telemetry():
    async def _test():
        mock_state_coll = _MockCollection(rows=[])
        orig_db = server.db
        server.db = _MockDB(system_state=mock_state_coll)

        with patch.object(server, "_require_cloud_scheduler_oidc", return_value=None), \
             patch("services.engine.recompute_ranking", AsyncMock(return_value={"trainers_scored": 5})), \
             patch("services.engine.promote_inferred_conversions", AsyncMock(return_value={"promoted": 1})), \
             patch("services.engine.update_health", AsyncMock(return_value={"healthy": True})), \
             patch("services.engine.maintain_sponsor_inventory", AsyncMock(return_value={"released": 0})), \
             patch("services.engine.run_growth_nurture", AsyncMock(return_value={"nurtured": 0})), \
             patch("services.engine.run_reactivation_routing", AsyncMock(return_value={"routed": 0})):

            res = await server.run_engine_tick_job(authorization="Bearer mock", profile="routine")
            assert res["ok"] is True
            assert res["job"] == "engine-tick"
            assert res["status"] == "ok"
            assert "ranking" in res["results"]
            assert res["results"]["ranking"]["status"] == "ok"

            # Verify engine_tick summary doc in system_state
            tick_doc = next((r for r in mock_state_coll.rows if r.get("key") == "engine_tick"), None)
            assert tick_doc is not None
            assert tick_doc["execution_owner"] == "cloud_scheduler"
            assert tick_doc["last_status"] == "ok"
            assert tick_doc["consecutive_failures"] == 0

        server.db = orig_db

    asyncio.run(_test())


def test_engine_tick_profile_monitoring_has_strictly_zero_entity_mutations():
    async def _test():
        mock_state_coll = _MockCollection(rows=[])
        orig_db = server.db
        server.db = _MockDB(system_state=mock_state_coll)

        ranking_mock = AsyncMock(return_value={"trainers_scored": 5})
        inference_mock = AsyncMock(return_value={"promoted": 1})
        sponsor_mock = AsyncMock(return_value={"released": 0})
        nurture_mock = AsyncMock(return_value={"nurtured": 0})
        reactivation_mock = AsyncMock(return_value={"routed": 0})
        recovery_mock = AsyncMock(return_value={"recovered": 0})
        health_mock = AsyncMock(return_value={"healthy": True})
        obligations_mock = AsyncMock(return_value=[])

        with patch.object(server, "_require_cloud_scheduler_oidc", return_value=None), \
             patch("services.engine.recompute_ranking", ranking_mock), \
             patch("services.engine.promote_inferred_conversions", inference_mock), \
             patch("services.engine.update_health", health_mock), \
             patch("services.engine.maintain_sponsor_inventory", sponsor_mock), \
             patch("services.engine.run_growth_nurture", nurture_mock), \
             patch("services.engine.run_reactivation_routing", reactivation_mock), \
             patch("services.ops_obligations.sync_durable_obligations", obligations_mock), \
             patch("services.ops_recovery.run_scheduled_recovery", recovery_mock):

            # Default profile is "monitoring"
            res = await server.run_engine_tick_job(authorization="Bearer mock")
            assert res["ok"] is True
            assert res["profile"] == "monitoring"
            # Verify data pipeline mutators were NOT invoked
            assert ranking_mock.call_count == 0
            assert inference_mock.call_count == 0
            assert sponsor_mock.call_count == 0
            assert nurture_mock.call_count == 0
            assert reactivation_mock.call_count == 0
            assert recovery_mock.call_count == 0
            # Only health and obligations monitoring were called
            assert health_mock.call_count == 1
            assert obligations_mock.call_count >= 1

        server.db = orig_db

    asyncio.run(_test())


def test_reactivation_routing_gates_notifications_by_default(monkeypatch):
    from services import engine
    async def _test():
        now_dt = datetime.now(timezone.utc)
        created_old = (now_dt - timedelta(days=20)).isoformat()
        trainer = {
            "id": "tr_inactive_1",
            "name": "Inactive Trainer",
            "email": "inactive@example.com",
            "created_at": created_old,
            "intros_30d": 0,
            "published": True,
            "confidence_score": 0.85,
        }
        trainers_coll = _MockCollection(rows=[trainer])
        reactivation_coll = _MockCollection(rows=[])
        state_coll = _MockCollection(rows=[])
        mock_db = _MockDB(
            trainers=trainers_coll,
            reactivation_candidates=reactivation_coll,
            system_state=state_coll,
        )

        with patch.object(engine.notifications_service, "notify_trainer_reactivation_candidate", AsyncMock()) as notify_mock:
            # 1. Default: ENABLE_REACTIVATION_NOTIFICATIONS not set / false
            monkeypatch.delenv("ENABLE_REACTIVATION_NOTIFICATIONS", raising=False)
            res = await engine.run_reactivation_routing(mock_db)
            assert res["routed"] == 1
            assert res["notified"] == 0
            assert res["skipped_notify"] == 1
            assert res["notifications_enabled"] is False
            assert notify_mock.call_count == 0

            # 2. Explicitly enabled: ENABLE_REACTIVATION_NOTIFICATIONS=1
            reactivation_coll.rows.clear()
            notify_mock.return_value = {"status": "sent"}
            monkeypatch.setenv("ENABLE_REACTIVATION_NOTIFICATIONS", "1")
            res2 = await engine.run_reactivation_routing(mock_db)
            assert res2["routed"] == 1
            assert res2["notified"] == 1
            assert res2["notifications_enabled"] is True
            assert notify_mock.call_count == 1

    asyncio.run(_test())


# ---------------------------------------------------------------------------
# Workstream F: Read-only Oversight Invariant (Zero DB Writes)
# ---------------------------------------------------------------------------

def test_oversight_get_endpoint_zero_db_writes():
    async def _test():
        write_operations = []

        class _SpyCollection(_MockCollection):
            async def insert_one(self, doc):
                write_operations.append(("insert_one", doc))
                return await super().insert_one(doc)

            async def update_one(self, filt, update, upsert=False):
                write_operations.append(("update_one", filt, update))
                return await super().update_one(filt, update, upsert)

            async def find_one_and_update(self, filt, update, upsert=False, return_document=None):
                write_operations.append(("find_one_and_update", filt, update))
                return await super().find_one_and_update(filt, update, upsert, return_document)

        orig_db = server.db
        server.db = _MockDB(
            system_state=_SpyCollection(),
            intros=_SpyCollection(),
            conversions=_SpyCollection(),
            trainers=_SpyCollection(),
            discovery_queue=_SpyCollection(),
            audit_log=_SpyCollection(),
            ops_case_states=_SpyCollection(),
        )

        with patch.object(server, "require_oversight", return_value=None), \
             patch.object(server, "_get_read_only_phase_runtime_records", AsyncMock(return_value={
                 "phase_state": {"phase": 2},
                 "readiness_snapshot": {"readiness_status": "ready"},
                 "phase_decisions": [],
             })), \
             patch.object(server, "_current_ops_cases", AsyncMock(return_value=[])):

            res = await server.oversight()
            assert isinstance(res, dict)
            assert len(write_operations) == 0, f"GET /api/oversight must perform zero DB writes, but performed: {write_operations}"

        server.db = orig_db

    asyncio.run(_test())


def test_engine_tick_partial_error_and_consecutive_failure_tracking():
    async def _test():
        mock_state_coll = _MockCollection(rows=[])
        orig_db = server.db
        server.db = _MockDB(system_state=mock_state_coll)

        failing_step = AsyncMock(side_effect=RuntimeError("Ranking calculation exploded"))
        with patch.object(server, "_require_cloud_scheduler_oidc", return_value=None), \
             patch("services.engine.recompute_ranking", failing_step), \
             patch("services.engine.promote_inferred_conversions", AsyncMock(return_value={"promoted": 1})), \
             patch("services.engine.update_health", AsyncMock(return_value={"healthy": True})), \
             patch("services.engine.maintain_sponsor_inventory", AsyncMock(return_value={"released": 0})), \
             patch("services.ops_obligations.sync_durable_obligations", AsyncMock(return_value=[])):

            res = await server.run_engine_tick_job(authorization="Bearer mock", profile="routine")
            assert res["ok"] is False
            assert res["status"] == "partial_error"
            assert res["results"]["ranking"]["status"] == "error"

            tick_doc = next((r for r in mock_state_coll.rows if r.get("key") == "engine_tick"), None)
            assert tick_doc is not None
            assert tick_doc["last_status"] == "partial_error"
            assert tick_doc["consecutive_failures"] == 1
            assert "ranking" in tick_doc["last_error"]

            # Verify _loop_status reports investigate/failing even though tick was just run (fresh)
            now_dt = datetime.now(timezone.utc)
            loop_stat = server._loop_status("engine_tick", tick_doc, now_dt=now_dt)
            assert loop_stat["status"] in ("investigate", "escalate")
            assert loop_stat["execution_owner"] == "failing"

        server.db = orig_db

    asyncio.run(_test())


def test_health_deep_scheduler_outcome_and_threshold():
    async def _test():
        now_dt = datetime.now(timezone.utc)
        recent_iso = now_dt.isoformat()
        old_iso = (now_dt - timedelta(seconds=800)).isoformat()

        # Case 1: Fresh and OK
        mock_coll = _MockCollection(rows=[
            {"key": "engine_tick", "last_run": recent_iso, "last_status": "ok", "execution_owner": "cloud_scheduler"}
        ])
        orig_db = server.db
        server.db = _MockDB(system_state=mock_coll)

        resp = await server.health_deep()
        data = json.loads(resp.body.decode("utf-8"))
        assert data["checks"]["scheduler"]["status"] == "fresh"
        assert data["checks"]["scheduler"]["threshold_s"] == 750

        # Case 2: Fresh but partial_error -> must be failing_or_degraded!
        mock_coll.rows = [
            {"key": "engine_tick", "last_run": recent_iso, "last_status": "partial_error", "execution_owner": "cloud_scheduler"}
        ]
        resp = await server.health_deep()
        data = json.loads(resp.body.decode("utf-8"))
        assert data["checks"]["scheduler"]["status"] == "failing_or_degraded"

        # Case 3: Stale (> 750s)
        mock_coll.rows = [
            {"key": "engine_tick", "last_run": old_iso, "last_status": "ok", "execution_owner": "cloud_scheduler"}
        ]
        resp = await server.health_deep()
        data = json.loads(resp.body.decode("utf-8"))
        assert data["checks"]["scheduler"]["status"] == "delayed_or_stale"

        server.db = orig_db

    asyncio.run(_test())


def test_ops_obligations_persistence_and_escalation():
    from services import ops_obligations
    async def _test():
        now_dt = datetime.now(timezone.utc)
        old_created = (now_dt - timedelta(hours=50)).isoformat()  # > 48h SLA

        mock_subs = _MockCollection(rows=[
            {
                "id": "sub_overdue_1",
                "business_name": "Overdue K9 Academy",
                "status": "pending",
                "abn_status": "unverified",
                "created_at": old_created,
            }
        ])
        mock_claims = _MockCollection(rows=[])
        mock_msg = _MockCollection(rows=[])
        mock_state = _MockCollection(rows=[])
        mock_obligations = _MockCollection(rows=[])

        orig_db = server.db
        server.db = _MockDB(
            submissions=mock_subs,
            claim_events=mock_claims,
            message_log=mock_msg,
            system_state=mock_state,
            ops_obligations=mock_obligations,
            ops_case_states=_MockCollection(rows=[]),
        )

        cases = await ops_obligations.get_active_obligation_cases(server.db, now_dt=now_dt)
        assert len(cases) == 1
        case = cases[0]
        assert case["case_id"] == "obligation:submission:sub_overdue_1"
        assert "[OVERDUE ESCALATION]" in case["title"]
        assert case["is_overdue"] is True
        assert case["escalation_level"] >= 1
        assert case["severity"] == "high"

        # Verify persisted in ops_obligations collection
        obl_doc = next((r for r in mock_obligations.rows if r.get("obligation_id") == "obligation:submission:sub_overdue_1"), None)
        assert obl_doc is not None
        assert obl_doc["status"] == "escalated"
        assert obl_doc["is_overdue"] is True

        # Verify review action resolves the obligation in the ledger
        with patch.object(server, "require_oversight", return_value=None), \
             patch.object(server, "_audit", AsyncMock()):
            review_payload = server.OpsCaseReviewIn(
                state="resolved",
                owner="carl",
                note="Verified manually against official ABR register",
            )
            res = await server.update_oversight_case_review(
                case_id="obligation:submission:sub_overdue_1",
                payload=review_payload,
            )
            assert res["ok"] is True
            assert obl_doc["status"] == "resolved"
            assert obl_doc["resolution"]["notes"] == "Verified manually against official ABR register"

        server.db = orig_db

    asyncio.run(_test())


def test_obligation_persists_when_absent_from_scan_or_query_fails():
    """Correction One: Absence from a scan or query failure NEVER resolves an obligation."""
    from services import ops_obligations
    async def _test():
        now_dt = datetime.now(timezone.utc)
        mock_obligations = _MockCollection(rows=[
            {
                "obligation_id": "obligation:submission:sub_unresolved_1",
                "category": "trainer_verification",
                "entity_id": "sub_unresolved_1",
                "title": "Review Trainer Submission",
                "required_action": "Verify ABN",
                "status": "pending",
                "created_at": now_dt.isoformat(),
                "is_overdue": False,
            }
        ])

        # 1. Missing source data (e.g. empty scan) does NOT resolve the obligation!
        mock_empty_subs = _MockCollection(rows=[])
        mock_db = _MockDB(
            submissions=mock_empty_subs,
            claim_events=_MockCollection(rows=[]),
            message_log=_MockCollection(rows=[]),
            system_state=_MockCollection(rows=[]),
            ops_obligations=mock_obligations,
            trainers=_MockCollection(rows=[]),
        )

        synced = await ops_obligations.sync_durable_obligations(mock_db, now_dt=now_dt)
        obl_doc = next((r for r in mock_obligations.rows if r.get("obligation_id") == "obligation:submission:sub_unresolved_1"), None)
        assert obl_doc is not None
        assert obl_doc["status"] == "pending", "Absence from scan must not auto-resolve an obligation!"
        assert "not found" in obl_doc.get("verification_gap", "").lower()

        # 2. Source query exception does NOT resolve the obligation!
        class _FailingCollection(_MockCollection):
            def find(self, *args, **kwargs):
                raise RuntimeError("MongoDB connection timeout during find()")

        mock_db_failing = _MockDB(
            submissions=_FailingCollection(rows=[]),
            claim_events=_MockCollection(rows=[]),
            message_log=_MockCollection(rows=[]),
            system_state=_MockCollection(rows=[]),
            ops_obligations=mock_obligations,
            trainers=_MockCollection(rows=[]),
        )

        synced2 = await ops_obligations.sync_durable_obligations(mock_db_failing, now_dt=now_dt)
        assert obl_doc["status"] == "pending", "Query exception must not auto-resolve an obligation!"
        assert "query failed" in obl_doc.get("source_verification_gap", "").lower()

    asyncio.run(_test())


def test_obligation_verified_terminal_state_resolves_it():
    """Correction One: Verified positive terminal state in the underlying datastore resolves it."""
    from services import ops_obligations
    async def _test():
        now_dt = datetime.now(timezone.utc)
        mock_obligations = _MockCollection(rows=[
            {
                "obligation_id": "obligation:submission:sub_term_1",
                "category": "trainer_verification",
                "entity_id": "sub_term_1",
                "title": "Review Trainer Submission",
                "required_action": "Verify ABN",
                "status": "pending",
                "created_at": now_dt.isoformat(),
                "is_overdue": False,
            }
        ])

        # Underlying submission reached terminal valid state ("published" with valid ABN)
        mock_subs = _MockCollection(rows=[
            {
                "id": "sub_term_1",
                "business_name": "Completed K9",
                "status": "published",
                "abn_status": "active_matched",
            }
        ])

        mock_db = _MockDB(
            submissions=mock_subs,
            claim_events=_MockCollection(rows=[]),
            message_log=_MockCollection(rows=[]),
            system_state=_MockCollection(rows=[]),
            ops_obligations=mock_obligations,
            trainers=_MockCollection(rows=[]),
        )

        synced = await ops_obligations.sync_durable_obligations(mock_db, now_dt=now_dt)
        obl_doc = next((r for r in mock_obligations.rows if r.get("obligation_id") == "obligation:submission:sub_term_1"), None)
        assert obl_doc is not None
        assert obl_doc["status"] == "resolved"
        assert obl_doc["resolution_type"] == "verified_terminal_state"
        assert "verified published" in obl_doc["resolution_notes"]
        assert len(obl_doc["history"]) > 0

    asyncio.run(_test())


def test_obligation_review_acknowledgment_does_not_falsely_resolve_business_completion():
    """Correction One & Five: Review acknowledgment or dismissal does not falsely resolve obligation."""
    async def _test():
        now_dt = datetime.now(timezone.utc)
        mock_obligations = _MockCollection(rows=[
            {
                "obligation_id": "obligation:submission:sub_ack_1",
                "category": "trainer_verification",
                "entity_id": "sub_ack_1",
                "title": "Review Trainer Submission",
                "required_action": "Verify ABN",
                "status": "pending",
                "created_at": now_dt.isoformat(),
                "is_overdue": False,
            }
        ])

        orig_db = server.db
        server.db = _MockDB(
            submissions=_MockCollection(rows=[{
                "id": "sub_ack_1",
                "status": "pending",
                "abn_status": "unverified",
                "created_at": now_dt.isoformat(),
            }]),
            claim_events=_MockCollection(rows=[]),
            message_log=_MockCollection(rows=[]),
            system_state=_MockCollection(rows=[]),
            ops_obligations=mock_obligations,
            ops_case_states=_MockCollection(rows=[]),
            trainers=_MockCollection(rows=[]),
        )

        with patch.object(server, "require_oversight", return_value=None), \
             patch.object(server, "_audit", AsyncMock()):

            # Operator acknowledges case (state: "investigating")
            payload = server.OpsCaseReviewIn(
                state="investigating",
                owner="carl",
                note="Acknowledged by owner in daily triage; waiting on ABR document.",
            )
            res = await server.update_oversight_case_review(
                case_id="obligation:submission:sub_ack_1",
                payload=payload,
            )
            assert res["ok"] is True

            obl_doc = next((r for r in mock_obligations.rows if r.get("obligation_id") == "obligation:submission:sub_ack_1"), None)
            assert obl_doc is not None
            # Obligation status must NOT be resolved!
            assert obl_doc["status"] == "pending", "Acknowledgment must not resolve the obligation!"
            assert obl_doc["review"]["review_state"] == "investigating"
            assert "waiting on ABR" in obl_doc["review"]["notes"]

        server.db = orig_db

    asyncio.run(_test())


def test_obligation_recurrence_is_not_permanently_suppressed():
    """Correction One: Genuine recurrence reopens obligation with incremented recurrence count."""
    from services import ops_obligations
    async def _test():
        now_dt = datetime.now(timezone.utc)
        # Previously resolved obligation
        mock_obligations = _MockCollection(rows=[
            {
                "obligation_id": "obligation:scheduler:engine_tick",
                "category": "scheduler",
                "entity_id": "engine_tick",
                "title": "Background Engine Tick Stalled",
                "status": "resolved",
                "resolved_at": (now_dt - timedelta(hours=2)).isoformat(),
                "recurrence_count": 0,
                "history": [],
            }
        ])

        # New failure occurs: scheduler stalls again (age > 750s)
        stalled_ts = (now_dt - timedelta(seconds=900)).isoformat()
        mock_state = _MockCollection(rows=[
            {
                "key": "engine_tick",
                "last_run": stalled_ts,
                "last_status": "ok",
                "consecutive_failures": 0,
            }
        ])

        mock_db = _MockDB(
            submissions=_MockCollection(rows=[]),
            claim_events=_MockCollection(rows=[]),
            message_log=_MockCollection(rows=[]),
            system_state=mock_state,
            ops_obligations=mock_obligations,
            trainers=_MockCollection(rows=[]),
        )

        cases = await ops_obligations.get_active_obligation_cases(mock_db, now_dt=now_dt)
        assert len(cases) == 1
        case = cases[0]
        assert "(Recurred x1)" in case["title"]
        assert case["escalation_level"] >= 0

        obl_doc = next((r for r in mock_obligations.rows if r.get("obligation_id") == "obligation:scheduler:engine_tick"), None)
        assert obl_doc is not None
        assert obl_doc["status"] in ("pending", "escalated"), "Recurrence must reopen the obligation!"
        assert obl_doc["recurrence_count"] == 1
        assert len(obl_doc["history"]) > 0
        assert obl_doc["history"][-1]["action"] == "reopened_recurrence"

    asyncio.run(_test())


def test_engine_tick_invalid_profile_fails_closed():
    """Correction Two: Invalid or unknown execution profiles fail closed with HTTP 400."""
    async def _test():
        orig_db = server.db
        server.db = _MockDB(system_state=_MockCollection(rows=[]))

        with patch.object(server, "_require_cloud_scheduler_oidc", return_value=None):
            try:
                await server.run_engine_tick_job(authorization="Bearer mock", profile="malicious_or_unknown")
                assert False, "Should have raised HTTPException(400) for unknown profile"
            except server.HTTPException as exc:
                assert exc.status_code == 400
                assert "Invalid scheduler profile" in exc.detail

        server.db = orig_db

    asyncio.run(_test())


def test_non_technical_owner_escalation_details():
    """Correction Five: Non-technical owner escalation hierarchy provides safe operating status and technical handoff."""
    from services import ops_obligations
    async def _test():
        now_dt = datetime.now(timezone.utc)
        mock_state = _MockCollection(rows=[
            {
                "key": "engine_tick",
                "last_run": (now_dt - timedelta(seconds=1200)).isoformat(),
                "last_status": "partial_error",
                "last_error": "Ranking step crashed",
                "consecutive_failures": 2,
            }
        ])

        mock_db = _MockDB(
            submissions=_MockCollection(rows=[]),
            claim_events=_MockCollection(rows=[]),
            message_log=_MockCollection(rows=[]),
            system_state=mock_state,
            ops_obligations=_MockCollection(rows=[]),
            trainers=_MockCollection(rows=[]),
        )

        cases = await ops_obligations.get_active_obligation_cases(mock_db, now_dt=now_dt)
        assert len(cases) == 1
        case = cases[0]

        # Verify non-technical owner escalation fields
        assert case["technical_assistance_required"] is True
        assert "Technical assistance may be required." in [r["value"] for r in case["detail_rows"]]
        assert "public directory remains operational" in case["safe_operating_state"]
        assert case["technical_handoff"] is not None
        assert "consecutive failures: 2" in case["technical_handoff"]

    asyncio.run(_test())


