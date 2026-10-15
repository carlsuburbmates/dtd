from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from fastapi import HTTPException

import server
from services import ai as ai_service


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    async def to_list(self, _n=None):
        return list(self.rows)


class _MockCollection:
    def __init__(self, *, find_one_result=None, rows=None):
        self.find_one_result = find_one_result
        self.rows = list(rows) if rows else []
        self.updated = []
        self.inserted = []

    async def find_one(self, filt=None, *_args, **_kwargs):
        if filt and isinstance(filt, dict):
            for row in self.rows:
                match = True
                for k, v in filt.items():
                    if row.get(k) != v:
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


class _MockDB:
    def __init__(self, **collections):
        self._collections = collections

    def __getattr__(self, name: str):
        if name not in self._collections:
            self._collections[name] = _MockCollection()
        return self._collections[name]


def test_email_dispatch_noise_elimination():
    """Workstream A: Successful emails do not alert; failures alert; diagnostics retain all."""
    async def _test():
        now_str = datetime.now(timezone.utc).isoformat()
        sent_row = {
            "id": "msg_sent_1",
            "workflow": "match_intro",
            "recipient": "owner@example.com",
            "status": "sent",
            "http_status": 202,
            "created_at": now_str,
        }
        failed_row = {
            "id": "msg_failed_2",
            "workflow": "match_intro",
            "recipient": "trainer@example.com",
            "status": "failed",
            "http_status": 500,
            "error": "SMTP 500 Internal Error",
            "created_at": now_str,
        }
        error_row = {
            "id": "msg_error_3",
            "workflow": "claim_verification",
            "recipient": "claimant@example.com",
            "status": "error",
            "http_status": 400,
            "error": "Invalid address",
            "created_at": now_str,
        }

        message_log = [sent_row, failed_row, error_row]

        # Verify _ops_case_rows behavior
        cases = await server._ops_case_rows(
            discovery_summary={},
            waitlist_summary={},
            loop_statuses={},
            fraud_suppression_cases=[],
            claim_cases=[],
            abn_degradation_cases=[],
            billing_recovery_case_rows=[],
            subscription_billing_case_rows=[],
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=message_log,
            provider_cases=[],
            ai_degradation_cases=[],
            sponsor_inventory_cases=[],
        )

        case_ids = [c["case_id"] for c in cases]
        assert "message:msg_sent_1" not in case_ids, "Routine sent email must not generate an ops_case"
        assert "message:msg_failed_2" in case_ids, "Failed email must generate an ops_case"
        assert "message:msg_error_3" in case_ids, "Error email must generate an ops_case"

        failed_case = next(c for c in cases if c["case_id"] == "message:msg_failed_2")
        assert failed_case["severity"] == "high"
        assert failed_case["state"] == "detected"

        # Verify diagnostic log retention in _message_log_rows
        orig_db = server.db
        try:
            server.db = _MockDB(
                notification_events=_MockCollection(rows=[sent_row, failed_row]),
                outreach_events=_MockCollection(rows=[error_row]),
            )
            diagnostic_rows = await server._message_log_rows(limit=50)
            diagnostic_ids = [r.get("id") for r in diagnostic_rows]
            assert "msg_sent_1" in diagnostic_ids, "Diagnostic log must retain sent messages"
            assert "msg_failed_2" in diagnostic_ids, "Diagnostic log must retain failed messages"
            assert "msg_error_3" in diagnostic_ids, "Diagnostic log must retain error messages"
        finally:
            server.db = orig_db

    asyncio.run(_test())


def test_ai_fallback_noise_elimination_isolated_vs_sustained():
    """Workstream B: Isolated recovered fallback is monitoring/low; sustained is detected; unrecovered is high."""
    async def _test():
        now = datetime.now(timezone.utc)

        # 1. Isolated recovered fallback (< 3 events in 1h)
        isolated_events = [
            {
                "id": "ai_deg_1",
                "created_at": now.isoformat(),
                "fallback_used": True,
                "recovered": True,
                "error": "Gemini 503 Service Unavailable",
                "model": "gemini-1.5-flash",
                "error_type": "timeout",
            }
        ]
        mock_db_isolated = _MockDB(ai_degradation_events=_MockCollection(rows=isolated_events))
        isolated_cases = await ai_service.get_ops_degradation_cases(db=mock_db_isolated)
        assert len(isolated_cases) == 1
        assert isolated_cases[0]["severity"] == "low"
        assert isolated_cases[0]["state"] == "monitoring"
        assert "AI fallback engaged" in isolated_cases[0]["title"]
        assert any(d["label"] == "Fallback used" and d["value"] == "true" for d in isolated_cases[0]["detail_rows"])
        assert "isolated fallback recovered request deterministically" in isolated_cases[0]["recommended_next_step"]

        # 2. Sustained degradation (>= 3 events in 1h window)
        sustained_events = [
            {
                "id": f"ai_deg_{i}",
                "created_at": (now - timedelta(minutes=i * 5)).isoformat(),
                "fallback_used": True,
                "recovered": True,
                "error": "Gemini timeout",
                "model": "gemini-1.5-flash",
                "error_type": "timeout",
            }
            for i in range(4)
        ]
        mock_db_sustained = _MockDB(ai_degradation_events=_MockCollection(rows=sustained_events))
        sustained_cases = await ai_service.get_ops_degradation_cases(db=mock_db_sustained)
        assert len(sustained_cases) == 1
        assert sustained_cases[0]["case_id"] == "ai_degradation:sustained"
        assert sustained_cases[0]["state"] == "detected"
        assert sustained_cases[0]["severity"] in {"medium", "high"}
        assert "Sustained AI provider degradation" in sustained_cases[0]["title"]

        # 3. Unrecovered failure
        unrecovered_events = [
            {
                "id": "ai_deg_fail",
                "created_at": now.isoformat(),
                "fallback_used": False,
                "recovered": False,
                "error": "Unhandled exception during synthesis",
            }
        ]
        mock_db_unrecovered = _MockDB(ai_degradation_events=_MockCollection(rows=unrecovered_events))
        unrecovered_cases = await ai_service.get_ops_degradation_cases(db=mock_db_unrecovered)
        assert len(unrecovered_cases) == 1
        assert unrecovered_cases[0]["state"] == "detected"
        assert unrecovered_cases[0]["severity"] == "high"

        # 4. Stale recovered event (> 24h) ignored
        stale_events = [
            {
                "id": "ai_deg_stale",
                "timestamp": (now - timedelta(hours=25)).isoformat(),
                "fallback_used": True,
                "recovered": True,
                "error": "Old timeout",
            }
        ]
        mock_db_stale = _MockDB(ai_degradation_events=_MockCollection(rows=stale_events))
        stale_cases = await ai_service.get_ops_degradation_cases(db=mock_db_stale)
        assert len(stale_cases) == 0, "Stale recovered events older than 24h should not generate cases"

    asyncio.run(_test())


def test_provider_resilience_governance_vs_operational_separation():
    """Workstream C: Configured providers with incomplete autonomy/rotation are governance/monitoring; unconfigured are operational/detected."""
    from services import provider_health

    mock_snapshot = {
        "checked_at": "2026-10-15T10:00:00Z",
        "providers": [
            {
                "id": "resend",
                "provider": "Resend",
                "purpose": "Transactional email",
                "runtime_status": "configuration_detected",
                "autonomy_status": "not_accepted",
                "severity": "medium",
                "degraded_behavior": "Outbound notifications fail",
                "next_review": "Key rotation not evidenced",
                "management_recovery_status": "not_evidenced",
                "safe_verification_status": "not_evidenced",
                "independent_alert_status": "not_evidenced",
                "recovery_owner": "Owner",
            },
            {
                "id": "abr",
                "provider": "Australian Business Register",
                "purpose": "ABN verification",
                "runtime_status": "configuration_missing",
                "autonomy_status": "not_accepted",
                "severity": "high",
                "degraded_behavior": "Identity verification degraded",
                "next_review": "Configure ABR_GUID",
                "management_recovery_status": "not_evidenced",
                "safe_verification_status": "not_evidenced",
                "independent_alert_status": "not_evidenced",
                "recovery_owner": "Owner",
                "runtime_env": "ABR_GUID",
            },
        ],
    }

    cases = provider_health.cases(mock_snapshot)
    resend_case = next((c for c in cases if c["entity_id"] == "resend"), None)
    abr_case = next((c for c in cases if c["entity_id"] == "abr"), None)

    assert resend_case is not None
    assert resend_case["case_type"] == "provider_governance_case"
    assert resend_case["severity"] == "low"
    assert resend_case["state"] == "monitoring"
    assert "control path needs evidence" in resend_case["title"]

    assert abr_case is not None
    assert abr_case["case_type"] == "provider_operational_case"
    assert abr_case["severity"] == "high"
    assert abr_case["state"] == "detected"
    assert "runtime configuration missing" in abr_case["title"]


def test_oversight_case_review_fraud_claim_abn_endpoints():
    """Workstream D: Reviewing fraud, claim, and abn cases succeeds via POST /api/oversight/cases/{case_id} without 404."""
    async def _test():
        original_db = server.db
        try:
            mock_intros = _MockCollection(
                rows=[
                    {
                        "id": "intro_fraud_abc",
                        "trainer_id": "trainer_1",
                        "delivery_status": "suppressed",
                        "fraud_status": "flagged_risk",
                        "fraud_reasons": ["suspicious_ip"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            )
            mock_claims = _MockCollection(
                rows=[
                    {
                        "id": "claim_evt_def",
                        "trainer_id": "trainer_2",
                        "status": "pending_verification",
                        "reason": "manual_review_needed",
                        "delivery_status": "failed",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            )
            mock_trainers = _MockCollection(
                rows=[
                    {
                        "id": "trainer_abn_ghi",
                        "name": "K9 Academy",
                        "abn": "12345678901",
                        "abn_status": "abr_unavailable",
                        "abn_verification_reason": "ABR Web Service timeout",
                        "abn_verified": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            )
            mock_case_states = _MockCollection(rows=[])
            mock_audit_log = _MockCollection(rows=[])

            server.db = _MockDB(
                intros=mock_intros,
                claim_events=mock_claims,
                trainers=mock_trainers,
                ops_case_states=mock_case_states,
                audit_log=mock_audit_log,
                discovery_queue=_MockCollection(rows=[]),
                discovery_batches=_MockCollection(rows=[]),
                suburb_waitlists=_MockCollection(rows=[]),
                daemon_heartbeats=_MockCollection(rows=[]),
                billing_recovery_events=_MockCollection(rows=[]),
                trainer_subscriptions=_MockCollection(rows=[]),
                reactivation_events=_MockCollection(rows=[]),
                source_ingestion_state=_MockCollection(rows=[]),
                message_log=_MockCollection(rows=[]),
                notification_events=_MockCollection(rows=[]),
                outreach_events=_MockCollection(rows=[]),
                email_delivery_events=_MockCollection(rows=[]),
                ai_degradation_events=_MockCollection(rows=[]),
            )

            # 1. Verify case discovery in _current_ops_cases()
            cases = await server._current_ops_cases()
            case_ids = {c["case_id"] for c in cases}
            assert "fraud:intro_fraud_abc" in case_ids, "Fraud suppression case must be discovered in _current_ops_cases"
            assert "trainer_claim:claim_evt_def" in case_ids, "Claim event case must be discovered in _current_ops_cases"
            assert "abn_verification:trainer_abn_ghi" in case_ids, "ABN degradation case must be discovered in _current_ops_cases"

            # 2. Review fraud case via update_oversight_case_review
            payload = server.OpsCaseReviewIn(
                state="acknowledged",
                owner="Carl",
                note="Customer identity verified by phone",
            )
            res = await server.update_oversight_case_review("fraud:intro_fraud_abc", payload, _=None)
            assert res["ok"] is True
            assert res["case"]["case_id"] == "fraud:intro_fraud_abc"
            assert res["case"]["state"] == "acknowledged"

            # Verify ops_case_states updated
            saved_state = await server.db.ops_case_states.find_one({"case_id": "fraud:intro_fraud_abc"})
            assert saved_state is not None
            assert saved_state["state"] == "acknowledged"
            assert saved_state["owner"] == "Carl"

            # Verify audit_log entry recorded
            assert len(server.db.audit_log.rows) == 1
            assert server.db.audit_log.rows[0]["action"] == "ops_case_review_updated"
            assert server.db.audit_log.rows[0]["target"] == "fraud:intro_fraud_abc"

            # Verify underlying intros record was NEVER mutated
            intro_doc = await server.db.intros.find_one({"id": "intro_fraud_abc"})
            assert intro_doc["delivery_status"] == "suppressed"
            assert intro_doc["fraud_status"] == "flagged_risk"

            # 3. Review claim case via update_oversight_case_review
            res_claim = await server.update_oversight_case_review(
                "trainer_claim:claim_evt_def",
                server.OpsCaseReviewIn(state="monitoring", owner="Carl", note="Monitoring SMS retry"),
                _=None,
            )
            assert res_claim["ok"] is True
            assert res_claim["case"]["state"] == "monitoring"

            # 4. Attempting to review an unknown non-existent case raises HTTP 404
            with pytest.raises(HTTPException) as exc_info:
                await server.update_oversight_case_review(
                    "nonexistent:case_999",
                    server.OpsCaseReviewIn(state="resolved", owner="Carl"),
                    _=None,
                )
            assert exc_info.value.status_code == 404

        finally:
            server.db = original_db

    asyncio.run(_test())


def test_related_classification_noise_elimination():
    """Workstream E: Discovery backlog threshold, delisted suppression, serverless loop disabling, ingestion failures."""
    async def _test():
        # 1. Discovery backlog
        cases_low = await server._ops_case_rows(
            discovery_summary={"pending": 15, "suppressed": 5},
            waitlist_summary={},
            loop_statuses={},
            fraud_suppression_cases=[],
            claim_cases=[],
            abn_degradation_cases=[],
            billing_recovery_case_rows=[],
            subscription_billing_case_rows=[],
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=[],
            provider_cases=[],
            ai_degradation_cases=[],
            sponsor_inventory_cases=[],
        )
        pending_case_low = next(c for c in cases_low if c["case_id"] == "discovery:pending")
        assert pending_case_low["state"] == "monitoring", "Backlog under 50 items should be in monitoring"

        suppressed_case = next(c for c in cases_low if c["case_id"] == "discovery:suppressed")
        assert suppressed_case["state"] == "monitoring"
        assert suppressed_case["severity"] == "low"

        cases_high = await server._ops_case_rows(
            discovery_summary={"pending": 75, "suppressed": 5},
            waitlist_summary={},
            loop_statuses={},
            fraud_suppression_cases=[],
            claim_cases=[],
            abn_degradation_cases=[],
            billing_recovery_case_rows=[],
            subscription_billing_case_rows=[],
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=[],
            provider_cases=[],
            ai_degradation_cases=[],
            sponsor_inventory_cases=[],
        )
        pending_case_high = next(c for c in cases_high if c["case_id"] == "discovery:pending")
        assert pending_case_high["state"] == "detected", "Backlog of 50+ items should be detected"

        # 2. Serverless loop handling
        prev_disable = os.environ.get("DISABLE_AUTONOMY")
        try:
            os.environ["DISABLE_AUTONOMY"] = "1"
            # When fresh external execution exists -> ok
            now_str = datetime.now(timezone.utc).isoformat()
            status_fresh = server._loop_status("ranking", {"last_run": now_str}, now_dt=datetime.now(timezone.utc))
            assert status_fresh["status"] == "ok"
            assert status_fresh["execution_owner"] == "scheduler"

            # When no last_run exists in serverless mode -> missing_owner (DF-029)
            status_unowned = server._loop_status("ranking", {}, now_dt=datetime.now(timezone.utc))
            assert status_unowned["status"] == "missing_owner"
            assert status_unowned["execution_owner"] == "none"

            cases_loops = await server._ops_case_rows(
                discovery_summary={},
                waitlist_summary={},
                loop_statuses={"ranking": status_unowned, "verification": status_fresh},
                fraud_suppression_cases=[],
                claim_cases=[],
                abn_degradation_cases=[],
                billing_recovery_case_rows=[],
                subscription_billing_case_rows=[],
                reactivation_case_rows=[],
                source_ingestion_state_rows=[],
                message_log=[],
                provider_cases=[],
                ai_degradation_cases=[],
                sponsor_inventory_cases=[],
            )
            # Unowned serverless loops are aggregated into a single architectural governance case (DF-029) in monitoring
            assert len(cases_loops) == 1
            assert cases_loops[0]["case_id"] == "autonomy:missing_scheduled_owner"
            assert cases_loops[0]["state"] == "monitoring"
            assert cases_loops[0]["severity"] == "low"
            assert "DF-029" in cases_loops[0]["risk_reason_codes"]
        finally:
            if prev_disable is None:
                os.environ.pop("DISABLE_AUTONOMY", None)
            else:
                os.environ["DISABLE_AUTONOMY"] = prev_disable

        # 3. Source ingestion noise
        cases_ingestion = await server._ops_case_rows(
            discovery_summary={},
            waitlist_summary={},
            loop_statuses={},
            fraud_suppression_cases=[],
            claim_cases=[],
            abn_degradation_cases=[],
            billing_recovery_case_rows=[],
            subscription_billing_case_rows=[],
            reactivation_case_rows=[],
            source_ingestion_state_rows=[
                {
                    "id": "source_1",
                    "source_url": "https://example.com/source",
                    "consecutive_failures": 0,
                    "last_error": "Temporary network drop that recovered",
                }
            ],
            message_log=[],
            provider_cases=[],
            ai_degradation_cases=[],
            sponsor_inventory_cases=[],
        )
        assert len(cases_ingestion) == 0, "Ingestion sources with 0 consecutive failures must not alert"

    asyncio.run(_test())


def test_loop_status_ownership_and_safety_matrix():
    """Workstream A: Distinguish failing loops, external scheduler ok, external scheduler stale, and missing owner."""
    now_dt = datetime.now(timezone.utc)
    fresh_ts = (now_dt - timedelta(seconds=45)).isoformat()
    stale_ts = (now_dt - timedelta(hours=48)).isoformat()

    # 1. Real failure must NEVER be suppressed, even when DISABLE_AUTONOMY=1
    prev = os.environ.get("DISABLE_AUTONOMY")
    try:
        os.environ["DISABLE_AUTONOMY"] = "1"
        res_fail = server._loop_status("ranking", {"consecutive_failures": 3, "last_error": "Crash on fetch"}, now_dt=now_dt)
        assert res_fail["status"] == "escalate"
        assert res_fail["execution_mode"] == "failing"

        res_investigate = server._loop_status("ranking", {"consecutive_failures": 1, "last_error": "Timeout"}, now_dt=now_dt)
        assert res_investigate["status"] == "investigate"
        assert res_investigate["execution_mode"] == "failing"

        # 2. Serverless external scheduler with cadence-aware freshness
        res_ok = server._loop_status("ranking", {"last_run": fresh_ts}, now_dt=now_dt)
        assert res_ok["status"] == "ok"
        assert res_ok["execution_owner"] == "scheduler"
        assert res_ok["execution_mode"] == "external_scheduler"

        res_stale = server._loop_status("ranking", {"last_run": stale_ts}, now_dt=now_dt)
        assert res_stale["status"] == "escalate"
        assert res_stale["execution_mode"] == "external_scheduler_stale"

        # 3. Missing execution owner (DF-029)
        res_unowned = server._loop_status("ranking", {}, now_dt=now_dt)
        assert res_unowned["status"] == "missing_owner"
        assert res_unowned["execution_owner"] == "none"
        assert res_unowned["execution_mode"] == "unowned_serverless"
    finally:
        if prev is None:
            os.environ.pop("DISABLE_AUTONOMY", None)
        else:
            os.environ["DISABLE_AUTONOMY"] = prev


def test_threshold_boundaries_discovery_and_ai():
    """Workstream C: Strict boundary tests for discovery backlog and AI fallback thresholds."""
    async def _test():
        now_dt = datetime.now(timezone.utc)
        recent_ts = (now_dt - timedelta(minutes=10)).isoformat()
        yesterday_ts = (now_dt - timedelta(hours=12)).isoformat()

        # 1. Discovery backlog boundaries (49 vs 50 vs 51)
        cases_49 = await server._ops_case_rows(
            discovery_summary={"pending": 49}, waitlist_summary={}, loop_statuses={},
            fraud_suppression_cases=[], claim_cases=[], abn_degradation_cases=[],
            billing_recovery_case_rows=[], subscription_billing_case_rows=[],
            reactivation_case_rows=[], source_ingestion_state_rows=[], message_log=[],
        )
        case_49 = next(c for c in cases_49 if c["case_id"] == "discovery:pending")
        assert case_49["state"] == "monitoring"
        assert case_49["severity"] == "low"

        cases_50 = await server._ops_case_rows(
            discovery_summary={"pending": 50}, waitlist_summary={}, loop_statuses={},
            fraud_suppression_cases=[], claim_cases=[], abn_degradation_cases=[],
            billing_recovery_case_rows=[], subscription_billing_case_rows=[],
            reactivation_case_rows=[], source_ingestion_state_rows=[], message_log=[],
        )
        case_50 = next(c for c in cases_50 if c["case_id"] == "discovery:pending")
        assert case_50["state"] == "detected"
        assert case_50["severity"] == "medium"

        # 2. AI unrecovered failure (even single event triggers high severity detected)
        single_unrecovered = [
            {"id": "ev_unrec_1", "timestamp": recent_ts, "recovered": False, "fallback_used": False, "error_type": "all_failed"}
        ]
        ai_service._degradation_events.clear()
        ai_service._degradation_events.extend(single_unrecovered)
        cases_ai_unrec = await ai_service.get_ops_degradation_cases()
        assert len(cases_ai_unrec) == 1
        assert cases_ai_unrec[0]["severity"] == "high"
        assert cases_ai_unrec[0]["state"] == "detected"

        # 3. AI burst fallback boundaries (2 vs 3 in 1 hour)
        two_recovered_1h = [
            {"id": f"ev_rec_{i}", "timestamp": recent_ts, "recovered": True, "fallback_used": True, "error_type": "rate_limit"}
            for i in range(2)
        ]
        ai_service._degradation_events.clear()
        ai_service._degradation_events.extend(two_recovered_1h)
        cases_ai_2 = await ai_service.get_ops_degradation_cases()
        assert len(cases_ai_2) == 2
        assert all(c["state"] == "monitoring" and c["severity"] == "low" for c in cases_ai_2)

        three_recovered_1h = [
            {"id": f"ev_rec_{i}", "timestamp": recent_ts, "recovered": True, "fallback_used": True, "error_type": "rate_limit"}
            for i in range(3)
        ]
        ai_service._degradation_events.clear()
        ai_service._degradation_events.extend(three_recovered_1h)
        cases_ai_3 = await ai_service.get_ops_degradation_cases()
        assert len(cases_ai_3) == 1
        assert cases_ai_3[0]["case_id"] == "ai_degradation:sustained"
        assert cases_ai_3[0]["state"] == "detected"

        # 4. AI persistent low-volume boundaries (4 vs 5 across 24h, all > 1h ago)
        four_recovered_24h = [
            {"id": f"ev_rec_24h_{i}", "timestamp": yesterday_ts, "recovered": True, "fallback_used": True, "error_type": "timeout"}
            for i in range(4)
        ]
        ai_service._degradation_events.clear()
        ai_service._degradation_events.extend(four_recovered_24h)
        cases_ai_4 = await ai_service.get_ops_degradation_cases()
        assert len(cases_ai_4) == 4
        assert all(c["state"] == "monitoring" and c["severity"] == "low" for c in cases_ai_4)

        five_recovered_24h = [
            {"id": f"ev_rec_24h_{i}", "timestamp": yesterday_ts, "recovered": True, "fallback_used": True, "error_type": "timeout"}
            for i in range(5)
        ]
        ai_service._degradation_events.clear()
        ai_service._degradation_events.extend(five_recovered_24h)
        cases_ai_5 = await ai_service.get_ops_degradation_cases()
        assert len(cases_ai_5) == 1
        assert cases_ai_5[0]["case_id"] == "ai_degradation:persistent_low_volume"
        assert cases_ai_5[0]["state"] == "detected"
        assert cases_ai_5[0]["severity"] == "medium"

    asyncio.run(_test())


def test_high_severity_dismissal_requires_explanatory_note():
    """Workstream D: Dismissing high-severity cases requires note >= 5 characters."""
    async def _test():
        original_db = server.db
        try:
            mock_submissions = _MockCollection(
                rows=[
                    {
                        "id": "sub_held_1",
                        "name": "Suspicious Trainer",
                        "status": "held",
                        "reason": "abn_mismatch",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            )
            mock_case_states = _MockCollection(rows=[])
            mock_audit_log = _MockCollection(rows=[])
            server.db = _MockDB(
                submissions=mock_submissions,
                intros=_MockCollection(rows=[]),
                claim_events=_MockCollection(rows=[]),
                trainers=_MockCollection(rows=[]),
                ops_case_states=mock_case_states,
                audit_log=mock_audit_log,
                discovery_queue=_MockCollection(rows=[]),
                discovery_batches=_MockCollection(rows=[]),
                suburb_waitlists=_MockCollection(rows=[]),
                daemon_heartbeats=_MockCollection(rows=[]),
                billing_recovery_events=_MockCollection(rows=[]),
                trainer_subscriptions=_MockCollection(rows=[]),
                reactivation_events=_MockCollection(rows=[]),
                source_ingestion_state=_MockCollection(rows=[]),
                message_log=_MockCollection(rows=[]),
                notification_events=_MockCollection(rows=[]),
                outreach_events=_MockCollection(rows=[]),
                email_delivery_events=_MockCollection(rows=[]),
                ai_degradation_events=_MockCollection(rows=[]),
            )

            # Verify it's recognized as a high-severity case
            cases = await server._current_ops_cases()
            target = next(c for c in cases if c["case_id"] == "submission:sub_held_1")
            assert target["severity"] == "high"

            # 1. Dismissing high-severity case with short note (< 5 chars) raises HTTP 400
            with pytest.raises(HTTPException) as exc_info:
                await server.update_oversight_case_review(
                    "submission:sub_held_1",
                    server.OpsCaseReviewIn(state="dismissed", owner="Carl", note="nope"),
                    _=None,
                )
            assert exc_info.value.status_code == 400
            assert "explanatory review note" in exc_info.value.detail

            # 2. Dismissing high-severity case with note >= 5 chars succeeds
            res = await server.update_oversight_case_review(
                "submission:sub_held_1",
                server.OpsCaseReviewIn(state="dismissed", owner="Carl", note="Verified legitimate test fixture during QA."),
                _=None,
            )
            assert res["ok"] is True
            assert res["case"]["state"] == "dismissed"

        finally:
            server.db = original_db

    asyncio.run(_test())


def test_recurrence_detection_and_reopening():
    """Workstream D / Correction C: Safe recurrence detection based on authoritative occurrence fingerprints."""
    # 1. Authoritative occurrence fingerprint differs -> incident recurred, reopens into detected
    recurred_case = {
        "case_id": "test:incident_1",
        "title": "Stripe Webhook Failure",
        "severity": "high",
        "state": "detected",
        "occurrence_fingerprint": "evt_stripe_fail_v2",
        "last_updated_at": "2026-10-15T12:00:00Z",
    }
    prior_dismissal_override = {
        "state": "dismissed",
        "owner": "Carl",
        "note": "Resolved temporary webhook glitch",
        "updated_at": "2026-10-15T10:00:00Z",
        "occurrence_fingerprint": "evt_stripe_fail_v1",
        "history": [],
    }

    merged = server._merge_ops_case_state(recurred_case, prior_dismissal_override)
    assert merged["state"] == "detected", "Recurred incident must reopen into detected state"
    assert merged["recurred"] is True
    assert "(Recurred)" in merged["title"]
    assert "incident_recurred" in merged["risk_reason_codes"]
    assert merged["review"]["recurrence_tracking"] == "fingerprint_verified"

    # 2. Same occurrence fingerprint revisited (snapshot rewrite / re-read) -> remains dismissed, no false recurrence
    static_case = {
        "case_id": "test:incident_1",
        "title": "Stripe Webhook Failure",
        "severity": "high",
        "state": "detected",
        "occurrence_fingerprint": "evt_stripe_fail_v1",
        "last_updated_at": "2026-10-15T12:30:00Z",
    }
    merged_static = server._merge_ops_case_state(static_case, prior_dismissal_override)
    assert merged_static["state"] == "dismissed"
    assert merged_static["recurred"] is False
    assert "(Recurred)" not in merged_static["title"]

    # 3. Case lacking occurrence identity -> recurrence conservatively deferred to Phase 2, no fabricated recurrence
    untracked_case = {
        "case_id": "test:generic_warning",
        "title": "Generic Uncorrelated Warning",
        "severity": "high",
        "state": "detected",
        "last_updated_at": "2026-10-15T13:00:00Z",
    }
    untracked_override = {
        "state": "dismissed",
        "owner": "Carl",
        "note": "Acknowledged generic warning",
        "updated_at": "2026-10-15T10:00:00Z",
        "history": [],
    }
    merged_untracked = server._merge_ops_case_state(untracked_case, untracked_override)
    assert merged_untracked["state"] == "dismissed"
    assert merged_untracked["recurred"] is False
    assert merged_untracked["review"]["recurrence_tracking"] == "deferred_to_phase2"


def test_correction_a_bounded_grace_and_cadence_matrix():
    """Correction A: Bounded grace periods and loop cadence matrix verification."""
    # Test bounded_grace_seconds calculations across all standard tiers
    assert server.bounded_grace_seconds(0) == 0
    assert server.bounded_grace_seconds(45) == 30    # 45s health: 30s grace -> stale at 75s
    assert server.bounded_grace_seconds(60) == 30    # 60s ranking: 30s grace -> stale at 90s
    assert server.bounded_grace_seconds(600) == 150  # 10m discovery: 150s grace -> stale at 750s (12.5m)
    assert server.bounded_grace_seconds(3600) == 900 # 1h outreach: 900s grace -> stale at 75m
    assert server.bounded_grace_seconds(21600) == 2160 # 6h verification: 2160s (36m) grace -> stale at 6h 36m
    assert server.bounded_grace_seconds(86400) == 3600 # 24h pro trial: 3600s (1h) grace -> stale at 25h

    now_dt = datetime.now(timezone.utc)

    # Health loop (45s cadence):
    # Age 30s -> fresh (ok)
    h_ok = server._loop_status("health", {"last_run": (now_dt - timedelta(seconds=30)).isoformat()}, now_dt=now_dt)
    assert h_ok["status"] == "ok"
    assert h_ok["interval_s"] == 45
    assert h_ok["stale_after_s"] == 75

    # Age 80s -> delayed (investigate)
    h_delayed = server._loop_status("health", {"last_run": (now_dt - timedelta(seconds=80)).isoformat()}, now_dt=now_dt)
    assert h_delayed["status"] == "investigate"
    assert h_delayed["execution_mode"] in {"daemon_delayed", "external_scheduler_delayed"}

    # Age 130s -> stalled/stale (escalate)
    h_stale = server._loop_status("health", {"last_run": (now_dt - timedelta(seconds=130)).isoformat()}, now_dt=now_dt)
    assert h_stale["status"] == "escalate"
    assert h_stale["execution_mode"] in {"daemon_stalled", "external_scheduler_stale"}

    # Discovery loop (10m / 600s cadence):
    # Age 5m (300s) -> fresh (ok)
    d_ok = server._loop_status("discovery", {"last_run": (now_dt - timedelta(minutes=5)).isoformat()}, now_dt=now_dt)
    assert d_ok["status"] == "ok"
    assert d_ok["interval_s"] == 600
    assert d_ok["stale_after_s"] == 750

    # Verification loop (6h / 21600s cadence):
    # Age 4h -> fresh (ok)
    v_ok = server._loop_status("verification", {"last_run": (now_dt - timedelta(hours=4)).isoformat()}, now_dt=now_dt)
    assert v_ok["status"] == "ok"
    assert v_ok["stale_after_s"] == 23760

    # Clock skew: future timestamp (> 30s in future)
    future_run = (now_dt + timedelta(seconds=90)).isoformat()
    skew_res = server._loop_status("ranking", {"last_run": future_run}, now_dt=now_dt)
    assert skew_res["status"] == "investigate"
    assert skew_res["execution_mode"] == "clock_skew"
    assert "future" in skew_res["reason"].lower()

    # Unknown cadence: unconfigured loop key
    unk_res = server._loop_status("nonexistent_loop", {"last_run": (now_dt - timedelta(seconds=10)).isoformat()}, now_dt=now_dt)
    assert unk_res["status"] == "unknown_cadence"
    assert unk_res["execution_mode"] == "unconfigured_cadence"

    # Maintenance mode boundary
    prev_maint = os.environ.get("MAINTENANCE_MODE")
    try:
        os.environ["MAINTENANCE_MODE"] = "1"
        maint_res = server._loop_status("ranking", {"last_run": (now_dt - timedelta(minutes=5)).isoformat()}, now_dt=now_dt)
        assert maint_res["status"] == "maintenance_paused"
        assert maint_res["execution_mode"] == "maintenance_paused"
    finally:
        if prev_maint is None:
            os.environ.pop("MAINTENANCE_MODE", None)
        else:
            os.environ["MAINTENANCE_MODE"] = prev_maint


def test_correction_b_provider_health_evidence_first():
    """Correction B: Provider operational status requires authoritative recent operation evidence."""
    from services import provider_health

    # 1. Atlas: No recent operation signal -> operational_status must be 'unknown', NOT 'operational'
    snap_no_signal = provider_health.snapshot(
        env={"MONGO_URL": "mongodb+srv://mock.mongodb.net", "DB_NAME": "dtd_prod"},
        telemetry={"atlas_connected": None},
    )
    atlas_row = next(r for r in snap_no_signal["providers"] if r["id"] == "atlas")
    assert atlas_row["runtime_status"] == "configuration_detected"
    assert atlas_row["operational_status"] == "unknown"
    assert "no recent database operation signal" in atlas_row["operational_reason"].lower()

    # 2. Atlas: Recent operation verified -> operational
    snap_verified = provider_health.snapshot(
        env={"MONGO_URL": "mongodb+srv://mock.mongodb.net", "DB_NAME": "dtd_prod"},
        telemetry={"atlas_connected": True},
    )
    atlas_verified = next(r for r in snap_verified["providers"] if r["id"] == "atlas")
    assert atlas_verified["operational_status"] == "operational"

    # 3. Atlas: Connection failure -> unavailable
    snap_failed = provider_health.snapshot(
        env={"MONGO_URL": "mongodb+srv://mock.mongodb.net", "DB_NAME": "dtd_prod"},
        telemetry={"atlas_connected": False},
    )
    atlas_failed = next(r for r in snap_failed["providers"] if r["id"] == "atlas")
    assert atlas_failed["operational_status"] == "unavailable"

    # 4. Sentry: Configured DSN without verified canary -> operational_status must be 'unknown'
    snap_sentry_unverified = provider_health.snapshot(
        env={"SENTRY_DSN": "https://pubkey@o123456.ingest.sentry.io/78910"},
        telemetry={"sentry_status": "unverified"},
    )
    sentry_row = next(r for r in snap_sentry_unverified["providers"] if r["id"] == "sentry")
    assert sentry_row["runtime_status"] == "configuration_detected"
    assert sentry_row["operational_status"] == "unknown"
    assert "canary event unverified" in sentry_row["operational_reason"].lower()

    # 5. Sentry: Verified event ingestion -> operational
    snap_sentry_verified = provider_health.snapshot(
        env={"SENTRY_DSN": "https://pubkey@o123456.ingest.sentry.io/78910"},
        telemetry={"sentry_status": "verified"},
    )
    sentry_ok = next(r for r in snap_sentry_verified["providers"] if r["id"] == "sentry")
    assert sentry_ok["operational_status"] == "operational"

    # 6. Resend: No delivery activity in window -> unknown
    snap_resend_no_activity = provider_health.snapshot(
        env={"RESEND_API_KEY": "re_live_mockkey123"},
        telemetry={"resend_status": "unknown"},
    )
    resend_row = next(r for r in snap_resend_no_activity["providers"] if r["id"] == "resend")
    assert resend_row["runtime_status"] == "configuration_detected"
    assert resend_row["operational_status"] == "unknown"


def test_correction_d_ai_telemetry_temporal_validation():
    """Correction D: AI degradation events with invalid/missing timestamps never enter rolling burst windows."""
    async def _test():
        now_dt = datetime.now(timezone.utc)

        # 1. Multiple recovered events with MISSING or UNPARSEABLE timestamps
        # Must NOT trigger ai_degradation:sustained burst alert!
        malformed_events = [
            {"id": "ev_bad_1", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": None},
            {"id": "ev_bad_2", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": ""},
            {"id": "ev_bad_3", "error_type": "rate_limit", "recovered": True, "fallback_used": True, "timestamp": "not_a_real_iso_date"},
            {"id": "ev_bad_4", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": "invalid_tz_string"},
        ]
        mock_db_bad = _MockDB(ai_degradation_events=_MockCollection(rows=malformed_events))
        cases_bad = await ai_service.get_ops_degradation_cases(db=mock_db_bad, burst_threshold=3)
        # Sustained burst case MUST NOT be generated from malformed timestamps!
        assert not any(c["case_id"] == "ai_degradation:sustained" for c in cases_bad)
        assert not any(c["case_id"] == "ai_degradation:persistent_low_volume" for c in cases_bad)

        # 2. Unrecovered failure with missing timestamp -> generates high severity case with age='unknown'
        unrecovered_bad_ts = [
            {
                "id": "ev_unrecov_1",
                "error_type": "model_error",
                "error_code": "GEMINI_QUOTA_EXHAUSTED",
                "recovered": False,
                "fallback_used": False,
                "timestamp": None,
                "message": "Both Gemini and fallback failed",
            }
        ]
        mock_db_unrecov = _MockDB(ai_degradation_events=_MockCollection(rows=unrecovered_bad_ts))
        cases_unrecov = await ai_service.get_ops_degradation_cases(db=mock_db_unrecov)
        unrecov_case = next(c for c in cases_unrecov if c["case_id"] == "ai_degradation:ev_unrecov_1")
        assert unrecov_case["severity"] == "high"
        assert unrecov_case["state"] == "detected"
        assert unrecov_case["detected_at"] == "unknown"
        ts_detail = next(d for d in unrecov_case["detail_rows"] if d["label"] == "Timestamp status")
        assert ts_detail["value"] == "missing_or_malformed"
        age_detail = next(d for d in unrecov_case["detail_rows"] if d["label"] == "Age")
        assert age_detail["value"] == "unknown"

        # 3. Future timestamp (clock skew > 60s) -> excluded from rolling burst window
        future_event = [
            {"id": "ev_future_1", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": (now_dt + timedelta(minutes=10)).isoformat()},
            {"id": "ev_future_2", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": (now_dt + timedelta(minutes=10)).isoformat()},
            {"id": "ev_future_3", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": (now_dt + timedelta(minutes=10)).isoformat()},
        ]
        mock_db_future = _MockDB(ai_degradation_events=_MockCollection(rows=future_event))
        cases_future = await ai_service.get_ops_degradation_cases(db=mock_db_future, burst_threshold=3)
        assert not any(c["case_id"] == "ai_degradation:sustained" for c in cases_future)

        # 4. Valid recent timestamps -> properly aggregated into burst alert
        valid_events = [
            {"id": "ev_ok_1", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": (now_dt - timedelta(minutes=2)).isoformat()},
            {"id": "ev_ok_2", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": (now_dt - timedelta(minutes=3)).isoformat()},
            {"id": "ev_ok_3", "error_type": "timeout", "recovered": True, "fallback_used": True, "timestamp": (now_dt - timedelta(minutes=4)).isoformat()},
        ]
        mock_db_valid = _MockDB(ai_degradation_events=_MockCollection(rows=valid_events))
        cases_valid = await ai_service.get_ops_degradation_cases(db=mock_db_valid, burst_threshold=3)
        assert any(c["case_id"] == "ai_degradation:sustained" for c in cases_valid)

    asyncio.run(_test())

