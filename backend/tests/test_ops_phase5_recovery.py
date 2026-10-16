"""Unit and integration test suite for DTD Operations Console Phase 5: Autonomous Recovery.

Verifies:
1. Default-disabled posture: master flag OPS_SELF_HEALING_ENABLED=0 rejects recovery.
2. Feature flag isolation: each routine requires its specific flag enabled.
3. Production hard block: gen-lang-client-0028123502 / production environment hard-blocks all recovery.
4. Routine eligibility rules:
   - routine:background_job_lease_recovery (expired lease only, never active future leases)
   - routine:stale_claim_lock_recovery (expired OTP claims only, zero trainer ownership mutation)
   - routine:transient_notification_retry (transient 429/503/timeout only, never permanent 401/404/400)
5. Atomic concurrency: MongoDB distributed claiming prevents duplicate worker execution.
6. Cooldown and max attempts: 300s cooldown and 2-attempt ceiling triggering owner escalation.
7. Daily limit ceiling: stops execution once daily limit is reached.
8. Downstream verification requirement: recovery is confirmed ONLY after verification succeeds.
9. AI boundary separation: Phase 4 Gemini AI Analyst has zero mutation authority.
10. Pure read-only case enrichment and Handled Automatically integration.
"""

import asyncio
from datetime import datetime, timezone, timedelta
import json
import pytest
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from services import ops_recovery
from services import ops_analyst
import server


class FakeMongoCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, length: int = 100) -> List[Dict[str, Any]]:
        return list(self._docs[:length])


class FakeMongoCollection:
    def __init__(self, initial_docs: Optional[List[Dict[str, Any]]] = None):
        self._docs: List[Dict[str, Any]] = list(initial_docs or [])

    async def find_one(self, query: Dict[str, Any], *args, **kwargs) -> Optional[Dict[str, Any]]:
        for d in self._docs:
            if self._match_doc(d, query):
                return dict(d)
        return None

    def find(self, query: Dict[str, Any] = None, *args, **kwargs):
        res = []
        for d in self._docs:
            if not query or self._match_doc(d, query):
                res.append(dict(d))
        return FakeMongoCursor(res)

    def _match_doc(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        if "$or" in query:
            return any(self._match_doc(doc, sub_q) for sub_q in query["$or"])
        for k, v in query.items():
            if k == "$or":
                continue
            if isinstance(v, dict):
                if "$in" in v and doc.get(k) not in v["$in"]:
                    return False
                if "$regex" in v:
                    prefix = v["$regex"].lstrip("^")
                    if not str(doc.get(k, "")).startswith(prefix):
                        return False
                if "$lte" in v and float(doc.get(k, 0)) > float(v["$lte"]):
                    return False
                if "$exists" in v:
                    exists = k in doc
                    if exists != v["$exists"]:
                        return False
            elif doc.get(k) != v:
                return False
        return True

    async def count_documents(self, query: Dict[str, Any]) -> int:
        count = 0
        for d in self._docs:
            if self._match_doc(d, query):
                count += 1
        return count

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        set_fields = update.get("$set", {})
        push_fields = update.get("$push", {})
        inc_fields = update.get("$inc", {})

        for i, d in enumerate(self._docs):
            if self._match_doc(d, query):
                self._docs[i].update(set_fields)
                for inc_k, inc_v in inc_fields.items():
                    self._docs[i][inc_k] = self._docs[i].get(inc_k, 0) + inc_v
                for push_k, push_v in push_fields.items():
                    lst = self._docs[i].setdefault(push_k, [])
                    lst.append(push_v)
                return MagicMock(matched_count=1, modified_count=1)
        if upsert:
            new_doc = {**query, **set_fields}
            self._docs.append(new_doc)
            return MagicMock(matched_count=0, upserted_id=1)
        return MagicMock(matched_count=0, modified_count=0)

    async def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any], return_document: bool = True, upsert: bool = False):
        set_fields = update.get("$set", {})
        inc_fields = update.get("$inc", {})

        for i, d in enumerate(self._docs):
            if self._match_doc(d, query):
                self._docs[i].update(set_fields)
                for inc_k, inc_v in inc_fields.items():
                    self._docs[i][inc_k] = self._docs[i].get(inc_k, 0) + inc_v
                return dict(self._docs[i])
        if upsert:
            new_doc = {**query, **set_fields}
            self._docs.append(new_doc)
            return dict(new_doc)
        return None

    async def insert_one(self, doc: Dict[str, Any]):
        new_d = dict(doc)
        if "_id" not in new_d:
            new_d["_id"] = len(self._docs) + 1
        self._docs.append(new_d)
        return MagicMock(inserted_id=new_d["_id"])


class FakeDatabase:
    def __init__(self):
        self.ops_recovery_executions = FakeMongoCollection()
        self.ops_case_states = FakeMongoCollection()
        self.system_state = FakeMongoCollection()
        self.trainer_claims = FakeMongoCollection()
        self.trainers = FakeMongoCollection()
        self.notification_events = FakeMongoCollection()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_default_disabled_posture_rejects_recovery():
    """Verify that with default configuration (all flags off), recovery is ineligible."""
    async def _test():
        db = FakeDatabase()
        case = {
            "case_id": "test_lease_case_DF-029",
            "case_type": "autonomy_serverless_unowned",
            "summary": "Scheduler lease stall detected",
            "risk_reason_codes": ["autonomy_serverless_unowned"],
        }

        with patch.dict("os.environ", {}, clear=True):
            assert not ops_recovery.is_self_healing_globally_enabled()
            eval_res = await ops_recovery.evaluate_incident_recovery(db, case)
            assert eval_res["eligible"] is False
            assert "disabled" in eval_res["reason"].lower()

            exec_res = await ops_recovery.attempt_recovery(db, case)
            assert exec_res["ok"] is False
            assert exec_res["status"] == "ineligible"
    asyncio.run(_test())


def test_production_hard_block_strictly_prevents_recovery():
    """Verify that production environments enforce a fail-closed hard block."""
    async def _test():
        db = FakeDatabase()
        case = {
            "case_id": "test_lease_case_DF-029",
            "case_type": "autonomy_serverless_unowned",
            "summary": "Scheduler lease stall detected",
            "risk_reason_codes": ["autonomy_serverless_unowned"],
        }

        prod_scenarios = [
            {"PROJECT_ID": "gen-lang-client-0028123502", "OPS_SELF_HEALING_ENABLED": "1"},
            {"VERTEXAI_PROJECT": "gen-lang-client-0028123502", "OPS_SELF_HEALING_ENABLED": "1"},
            {"SENTRY_ENVIRONMENT": "production", "OPS_SELF_HEALING_ENABLED": "1"},
            {"PRODUCTION": "1", "OPS_SELF_HEALING_ENABLED": "1"},
        ]

        for env in prod_scenarios:
            with patch.dict("os.environ", env, clear=True):
                assert ops_recovery.is_production_environment() is True
                assert ops_recovery.is_self_healing_globally_enabled() is False

                eval_res = await ops_recovery.evaluate_incident_recovery(db, case)
                assert eval_res["eligible"] is False
                assert eval_res["environment_blocked"] is True
                assert "production hard block" in eval_res["reason"].lower()

                exec_res = await ops_recovery.attempt_recovery(db, case)
                assert exec_res["ok"] is False
                assert exec_res["status"] == "ineligible"
    asyncio.run(_test())


def test_feature_flag_isolation_requires_both_master_and_routine_flag():
    """Verify that enabling master flag is not enough; the specific routine flag must also be enabled."""
    async def _test():
        db = FakeDatabase()
        case = {
            "case_id": "test_lease_case_DF-029",
            "case_type": "autonomy_serverless_unowned",
            "summary": "Scheduler lease stall detected",
            "risk_reason_codes": ["autonomy_serverless_unowned"],
        }

        # Master on, but lease routine flag off
        with patch.dict("os.environ", {
            "OPS_SELF_HEALING_ENABLED": "1",
            "OPS_RECOVERY_LEASE_ENABLED": "0",
        }, clear=True):
            eval_res = await ops_recovery.evaluate_incident_recovery(db, case)
            assert eval_res["eligible"] is False
            assert "no registered recovery routine eligible or enabled" in eval_res["reason"].lower()

        # Master on, and lease routine flag on
        with patch.dict("os.environ", {
            "OPS_SELF_HEALING_ENABLED": "1",
            "OPS_RECOVERY_LEASE_ENABLED": "1",
        }, clear=True):
            eval_res = await ops_recovery.evaluate_incident_recovery(db, case)
            assert eval_res["eligible"] is True
            assert eval_res["routine_id"] == "routine:background_job_lease_recovery"
    asyncio.run(_test())


def test_lease_recovery_eligibility_and_verification():
    """Verify background job lease recovery: eligible when expired, ineligible when active."""
    async def _test():
        db = FakeDatabase()
        now_epoch = time.time()

        # 1. Active lease in future -> Ineligible
        db.system_state._docs = [{
            "key": ops_recovery.ENGINE_TICK_LEASE_KEY,
            "expires_at_epoch": now_epoch + 120,
        }]
        case = {
            "case_id": "engine_tick_lease_stall",
            "case_type": "autonomy_serverless_unowned",
            "summary": "Scheduler lease stall",
            "risk_reason_codes": ["autonomy_serverless_unowned"],
        }

        with patch.dict("os.environ", {"OPS_SELF_HEALING_ENABLED": "1", "OPS_RECOVERY_LEASE_ENABLED": "1"}):
            eval_res = await ops_recovery.evaluate_incident_recovery(db, case)
            assert eval_res["eligible"] is False

            # 2. Expired lease in past -> Eligible
            db.system_state._docs[0]["expires_at_epoch"] = now_epoch - 30
            eval_res2 = await ops_recovery.evaluate_incident_recovery(db, case)
            assert eval_res2["eligible"] is True

            # Execute recovery
            res = await ops_recovery.attempt_recovery(db, case)
            assert res["ok"] is True
            assert res["status"] == "verified_recovery"

            # Verify system_state lease cleared
            lease_doc = await db.system_state.find_one({"key": ops_recovery.ENGINE_TICK_LEASE_KEY})
            assert lease_doc["expires_at_epoch"] == 0
            assert "recovered_by" in lease_doc

            # Verify case state updated to resolved
            case_state = await db.ops_case_states.find_one({"case_id": case["case_id"]})
            assert case_state["state"] == "resolved"
            assert case_state["auto_resolved"] is True
    asyncio.run(_test())


def test_stale_claim_lock_recovery_eligibility_and_zero_ownership_mutation():
    """Verify stale claim lock recovery releases lock without transferring ownership."""
    async def _test():
        db = FakeDatabase()
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

        db.trainer_claims._docs = [{
            "_id": 1,
            "id": "claim_test_123",
            "trainer_id": "trainer_alpha",
            "status": "pending_verification",
            "created_at": past_iso,
            "expires_at": past_iso,
        }]
        db.trainers._docs = [{
            "_id": 10,
            "id": "trainer_alpha",
            "name": "Alpha Dog Training",
            "claim_in_progress": True,
            "verified": False,
            "owner_user_id": None,
        }]

        case = {
            "case_id": "claim:claim_test_123",
            "case_type": "trainer_claim_case",
            "entity_id": "claim_test_123",
            "summary": "Trainer claim lock pending",
        }

        with patch.dict("os.environ", {"OPS_SELF_HEALING_ENABLED": "1", "OPS_RECOVERY_CLAIM_LOCK_ENABLED": "1"}):
            eval_res = await ops_recovery.evaluate_incident_recovery(db, case)
            assert eval_res["eligible"] is True
            assert eval_res["routine_id"] == "routine:stale_claim_lock_recovery"

            exec_res = await ops_recovery.attempt_recovery(db, case)
            assert exec_res["ok"] is True
            assert exec_res["status"] == "verified_recovery"

            # Claim marked expired
            claim = await db.trainer_claims.find_one({"id": "claim_test_123"})
            assert claim["status"] == "expired"

            # Trainer lock cleared, but ZERO ownership mutation
            trainer = await db.trainers.find_one({"id": "trainer_alpha"})
            assert trainer["claim_in_progress"] is False
            assert trainer["owner_user_id"] is None
            assert trainer["verified"] is False
    asyncio.run(_test())


def test_transient_notification_retry_bounds_and_excludes_permanent_errors():
    """Verify transient delivery retry allows 429/503 but strictly rejects permanent errors (401, 404)."""
    async def _test():
        db = FakeDatabase()

        # 1. Permanent error HTTP 401 (invalid API key) -> Ineligible
        perm_case = {
            "case_id": "message:dispatch_perm",
            "case_type": "trainer_communications_case",
            "summary": "Dispatch rejected HTTP 401",
            "detail_rows": [{"label": "HTTP status", "value": "401"}, {"label": "Attempts", "value": "1"}],
        }
        with patch.dict("os.environ", {"OPS_SELF_HEALING_ENABLED": "1", "OPS_RECOVERY_NOTIFICATION_ENABLED": "1"}):
            eval_res = await ops_recovery.evaluate_incident_recovery(db, perm_case)
            assert eval_res["eligible"] is False
            assert "permanent error" in eval_res["reason"].lower()

        # 2. Transient error HTTP 429 (rate limit) -> Eligible
        db.notification_events._docs = [{
            "_id": 100,
            "id": "evt_orig_429",
            "dispatch_id": "dispatch_transient",
            "status": "failed",
            "http_status": 429,
            "attempt": 1,
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        }]
        transient_case = {
            "case_id": "message:dispatch_transient",
            "dispatch_id": "dispatch_transient",
            "case_type": "trainer_communications_case",
            "summary": "Dispatch failed HTTP 429 rate limit",
            "detail_rows": [{"label": "HTTP status", "value": "429"}, {"label": "Attempts", "value": "1"}],
        }

        with patch.dict("os.environ", {"OPS_SELF_HEALING_ENABLED": "1", "OPS_RECOVERY_NOTIFICATION_ENABLED": "1"}):
            eval_res2 = await ops_recovery.evaluate_incident_recovery(db, transient_case)
            assert eval_res2["eligible"] is True
            assert eval_res2["routine_id"] == "routine:transient_notification_retry"

            exec_res = await ops_recovery.attempt_recovery(db, transient_case)
            assert exec_res["ok"] is True
            assert exec_res["status"] == "verified_recovery"

            # Verify retry document exists with attempt 2 and status delivered
            new_event = await db.notification_events.find_one({"dispatch_id": "dispatch_transient", "attempt": 2})
            assert new_event is not None
            assert new_event["status"] == "delivered"
            assert new_event["http_status"] == 200
    asyncio.run(_test())


def test_atomic_concurrency_lock_prevents_duplicate_worker_execution():
    """Verify that when one worker is executing, another concurrent worker cannot claim the same recovery."""
    async def _test():
        db = FakeDatabase()
        now_epoch = time.time()

        # Worker 1 currently holds the execution lease
        db.ops_recovery_executions._docs = [{
            "execution_id": "rec_worker_1",
            "case_id": "test_concurrency_case",
            "occurrence_fingerprint": "test_concurrency_case",
            "routine_id": "routine:background_job_lease_recovery",
            "status": "executing",
            "lease_expires_at": now_epoch + 50,  # actively held
            "created_at": datetime.now(timezone.utc).isoformat(),
        }]

        case = {
            "case_id": "test_concurrency_case",
            "case_type": "autonomy_serverless_unowned",
            "summary": "Scheduler lease stall",
            "risk_reason_codes": ["autonomy_serverless_unowned"],
        }

        with patch.dict("os.environ", {"OPS_SELF_HEALING_ENABLED": "1", "OPS_RECOVERY_LEASE_ENABLED": "1"}):
            res = await ops_recovery.attempt_recovery(db, case)
            assert res["ok"] is False
            assert res["status"] == "concurrency_lock"
            assert "another worker is currently executing" in res["reason"].lower()
    asyncio.run(_test())


def test_cooldown_and_max_attempts_exhaustion():
    """Verify that failed recovery triggers cooldown and max attempts ceiling enforces escalation."""
    async def _test():
        db = FakeDatabase()
        now_epoch = time.time()

        case = {
            "case_id": "test_exhaustion_case",
            "case_type": "autonomy_serverless_unowned",
            "summary": "Scheduler lease stall",
            "risk_reason_codes": ["autonomy_serverless_unowned"],
        }

        # 1. Cooldown active
        db.ops_recovery_executions._docs = [{
            "execution_id": "rec_fail_1",
            "case_id": "test_exhaustion_case",
            "occurrence_fingerprint": "test_exhaustion_case",
            "routine_id": "routine:background_job_lease_recovery",
            "status": "failed",
            "attempts": 1,
            "next_retry_epoch": now_epoch + 180,  # 180s left in cooldown
        }]

        with patch.dict("os.environ", {"OPS_SELF_HEALING_ENABLED": "1", "OPS_RECOVERY_LEASE_ENABLED": "1"}):
            res_cooldown = await ops_recovery.attempt_recovery(db, case)
            assert res_cooldown["ok"] is False
            assert res_cooldown["status"] == "cooldown_active"
            assert "wait" in res_cooldown["reason"].lower()

            # 2. Max attempts reached (attempts=2, ceiling=2)
            db.ops_recovery_executions._docs[0]["attempts"] = 2
            db.ops_recovery_executions._docs[0]["next_retry_epoch"] = 0  # cooldown expired

            res_exhausted = await ops_recovery.attempt_recovery(db, case)
            assert res_exhausted["ok"] is False
            assert res_exhausted["status"] == "exhausted"
            assert "owner escalation required" in res_exhausted["reason"].lower()
    asyncio.run(_test())


def test_daily_limit_ceiling_blocks_runaway_recovery():
    """Verify that daily limit ceiling prevents runaway recovery loops."""
    async def _test():
        db = FakeDatabase()
        today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Seed 20 verified recoveries for today
        for i in range(20):
            db.ops_recovery_executions._docs.append({
                "execution_id": f"rec_today_{i}",
                "case_id": f"case_{i}",
                "status": "verified",
                "created_at": f"{today_prefix}T10:{i:02d}:00Z",
            })

        case = {
            "case_id": "test_daily_limit_case",
            "case_type": "autonomy_serverless_unowned",
            "summary": "Scheduler lease stall",
            "risk_reason_codes": ["autonomy_serverless_unowned"],
        }

        with patch.dict("os.environ", {
            "OPS_SELF_HEALING_ENABLED": "1",
            "OPS_RECOVERY_LEASE_ENABLED": "1",
            "OPS_RECOVERY_DAILY_LIMIT": "20",
        }):
            res = await ops_recovery.attempt_recovery(db, case)
            assert res["ok"] is False
            assert res["status"] == "daily_limit_exhausted"
            assert "ceiling reached" in res["reason"].lower()
    asyncio.run(_test())


def test_downstream_verification_failure_keeps_incident_unresolved():
    """Verify that if verification fails, recovery status becomes failed and incident remains unresolved."""
    async def _test():
        db = FakeDatabase()
        case = {
            "case_id": "test_verify_fail_case",
            "case_type": "autonomy_serverless_unowned",
            "summary": "Scheduler lease stall",
            "risk_reason_codes": ["autonomy_serverless_unowned"],
        }

        # Mock execute to succeed, but verify to fail
        with patch.dict("os.environ", {"OPS_SELF_HEALING_ENABLED": "1", "OPS_RECOVERY_LEASE_ENABLED": "1"}):
            with patch.dict(ops_recovery.RECOVERY_REGISTRY["routine:background_job_lease_recovery"], {
                "fn_execute": AsyncMock(return_value={"executed": True}),
                "fn_verify": AsyncMock(return_value=(False, "Post-recovery check failed: lease still held", {})),
            }):
                res = await ops_recovery.attempt_recovery(db, case)
                assert res["ok"] is False
                assert res["status"] == "verification_failed"
                assert "Post-recovery check failed" in res["reason"]

                # Verify that execution record is marked failed
                rec = await db.ops_recovery_executions.find_one({"case_id": "test_verify_fail_case"})
                assert rec["status"] == "failed"
                assert "Post-recovery check failed" in rec["verification_error"]

                # Verify that case was NOT marked resolved
                case_state = await db.ops_case_states.find_one({"case_id": "test_verify_fail_case"})
                assert case_state is None
    asyncio.run(_test())


def test_ai_separation_analyst_has_zero_recovery_mutation_authority():
    """Verify that Phase 4 Gemini Analyst output cannot invoke or mutate recovery routines."""
    async def _test():
        db = FakeDatabase()
        case = {
            "case_id": "test_ai_separation_case",
            "case_type": "trainer_submission_case",
            "severity": "high",
            "summary": "Submission held for ABN verification",
        }

        # Verify that the analyst module has NO reference to recovery execution routines
        assert not hasattr(ops_analyst, "attempt_recovery")
        assert not hasattr(ops_analyst, "RECOVERY_REGISTRY")

        # Ingesting the analysis into case does NOT trigger recovery
        enriched_cases = await ops_analyst.enrich_cases_with_investigations(db, [case])
        assert enriched_cases[0]["case_id"] == "test_ai_separation_case"

        # Zero records in ops_recovery_executions
        count = await db.ops_recovery_executions.count_documents({})
        assert count == 0
    asyncio.run(_test())


def test_enrich_cases_with_recovery_status_is_pure_read_only():
    """Verify enrich_cases_with_recovery_status adds recovery metadata without database mutation."""
    async def _test():
        db = FakeDatabase()
        db.ops_recovery_executions._docs = [{
            "case_id": "case_alpha",
            "routine_id": "routine:stale_claim_lock_recovery",
            "status": "verified",
            "attempts": 1,
            "verified_at": "2026-10-16T12:00:00Z",
            "created_at": "2026-10-16T11:55:00Z",
        }]

        cases = [
            {"case_id": "case_alpha", "title": "Alpha Case"},
            {"case_id": "case_beta", "title": "Beta Case"},
        ]

        res = await ops_recovery.enrich_cases_with_recovery_status(db, cases)
        assert len(res) == 2

        # Case Alpha has recovery record
        assert res[0]["auto_recovery_status"] == "verified"
        assert res[0]["auto_recovery_routine"] == "routine:stale_claim_lock_recovery"
        assert res[0]["auto_recovery_attempts"] == 1

        # Case Beta has none
        assert res[1]["auto_recovery_status"] == "none"
        assert res[1]["auto_recovery_routine"] is None
    asyncio.run(_test())


def test_handled_automatically_surfaces_verified_recoveries():
    """Verify that _build_handled_automatically_summary includes verified auto-recoveries at top."""
    recent_recoveries = [{
        "execution_id": "rec_test_999",
        "case_id": "case_lease_123",
        "routine_id": "routine:background_job_lease_recovery",
        "routine_title": "Background Job Lease Recovery",
        "verified_at": "2026-10-16T12:30:00Z",
    }]

    items = server._build_handled_automatically_summary(
        pipeline_guardian={},
        fraud_cases=[],
        submissions_summary={},
        discovery_summary={},
        audit_recent=[],
        ops_cases=[],
        recent_recoveries=recent_recoveries,
    )

    assert len(items) >= 1
    recovery_item = items[0]
    assert recovery_item["category"] == "auto_recovery"
    assert "Self-Healed: Background Job Lease Recovery" in recovery_item["title"]
    assert "case_lease_123" in recovery_item["summary"]
    assert recovery_item["status"] == "completed"
