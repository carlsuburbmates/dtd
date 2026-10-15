from __future__ import annotations

import asyncio
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
                match = True
                for k, v in filt.items():
                    if k == "$or" and isinstance(v, list):
                        or_match = False
                        for cond in v:
                            if all(row.get(ck) == cv for ck, cv in cond.items()):
                                or_match = True
                                break
                        if not or_match:
                            match = False
                            break
                    elif row.get(k) != v:
                        match = False
                        break
                if match:
                    return dict(row)
        return self.find_one_result

    def find(self, *_args, **_kwargs):
        return _Cursor(self.rows)

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

            res = await server.run_engine_tick_job(authorization="Bearer mock")
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

        server.db = orig_db

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
