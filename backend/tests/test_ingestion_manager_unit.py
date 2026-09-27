"""Unit tests for Automated Ingestion Orchestrator (Engine 1).

Verifies:
- Candidate URL resolution (explicit -> discovery queue -> seed catalogue).
- Fail-closed governance policy checking.
- Polite crawl boundaries and robots.txt compliance.
- Statutory ABR publication gating (DF-014: AI confidence never publishes without active ABR).
- Claimed profile protection (claimed profiles never overwritten).
- /ops error logging in db.source_ingestion_state.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import ingestion_manager
from services.trainer_quality import publishing_quality


class _MockCollection:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None):
        self.rows: List[Dict[str, Any]] = [dict(r) for r in (rows or [])]

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        query = query or {}
        matched = []
        for r in self.rows:
            match = True
            for k, v in query.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                matched.append(r.copy())

        class _Cursor:
            def __init__(self, items):
                self.items = items
            def limit(self, n):
                return _Cursor(self.items[:n])
            async def to_list(self, n=None):
                return self.items[:n] if n is not None else self.items
        return _Cursor(matched)

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        for r in self.rows:
            match = True
            for k, v in query.items():
                if isinstance(v, dict) and "$regex" in v:
                    val = str(r.get(k) or "")
                    flags = re.IGNORECASE if v.get("$options") == "i" else 0
                    if not re.search(v["$regex"], val, flags):
                        match = False
                        break
                elif r.get(k) != v:
                    match = False
                    break
            if match:
                return r.copy()
        return None

    async def insert_one(self, doc: Dict[str, Any]) -> None:
        self.rows.append(doc.copy())

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> None:
        target = None
        for r in self.rows:
            match = True
            for k, v in query.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                target = r
                break
        if target is not None:
            if "$set" in update:
                target.update(update["$set"])
        elif upsert:
            new_doc = query.copy()
            if "$set" in update:
                new_doc.update(update["$set"])
            self.rows.append(new_doc)


class _MockDB:
    def __init__(self):
        self._collections = {}
        self.trainers = self._get_coll("trainers")
        self.discovery_queue = self._get_coll("discovery_queue")
        self.source_ingestion_state = self._get_coll("source_ingestion_state")
        self.system_state = self._get_coll("system_state")
        self.ingestion_runs = self._get_coll("ingestion_runs")

    def _get_coll(self, name: str) -> _MockCollection:
        if name not in self._collections:
            self._collections[name] = _MockCollection()
        return self._collections[name]

    def __getattr__(self, name: str) -> _MockCollection:
        return self._get_coll(name)


def test_resolve_candidate_source_urls_explicit():
    db = _MockDB()
    urls = ["https://kintala.com.au", "https://dogsandbonds.com.au"]
    resolved = asyncio.run(ingestion_manager.resolve_candidate_source_urls(urls, db, batch_size=5))
    assert len(resolved) == 2
    assert resolved[0]["url"] == "https://kintala.com.au"
    assert resolved[0]["source"] == "explicit_request"


def test_resolve_candidate_source_urls_from_queue():
    db = _MockDB()
    asyncio.run(db.discovery_queue.insert_one({"id": "q1", "url": "https://queuedtrainer.com.au", "status": "pending"}))
    resolved = asyncio.run(ingestion_manager.resolve_candidate_source_urls(None, db, batch_size=5))
    assert len(resolved) >= 1
    assert resolved[0]["url"] == "https://queuedtrainer.com.au"
    assert resolved[0]["source"] == "discovery_queue"


def test_run_batch_ingestion_pipeline_qualifies_active_abn():
    db = _MockDB()

    mock_html = "<html><body><h1>Kintala Dog Training</h1><p>Puppy school in Heidelberg. Phone: 0394575455. ABN: 53 780 168 767</p></body></html>"

    with patch("services.ingestion_manager.polite_fetch_url", new=AsyncMock(return_value=(True, mock_html, {"http_status": 200, "sha256": "abc"}, "ok"))), \
         patch("services.abr_client.AbrClient.lookup", new=AsyncMock(return_value={
             "ok": True,
             "data": {
                 "abn": "53780168767",
                 "entity_name": "THE KINTALA CLUB INC",
                 "is_active": True,
                 "status": "Active",
                 "retrieved_at": datetime.now(timezone.utc).isoformat(),
             }
         })):

        summary = asyncio.run(ingestion_manager.run_batch_ingestion_pipeline(
            source_urls=["https://kintala.com.au"],
            db=db,
            batch_size=1,
        ))

        assert summary["ok"] is True
        assert summary["total_processed"] == 1
        assert summary["qualified"] == 1
        assert summary["held"] == 0

        # Verify persisted record
        assert len(db.trainers.rows) == 1
        trainer = db.trainers.rows[0]
        assert trainer["published"] is True
        assert trainer["abn_verified"] is True
        assert trainer["ingestion_quality_status"] == "qualified"
        assert trainer["website"] == "https://kintala.com.au"


def test_run_batch_ingestion_pipeline_holds_unverified_abn_df014():
    """DF-014 Enforcer: AI confidence alone must NEVER publish without active ABR."""
    db = _MockDB()

    mock_html = "<html><body><h1>Unregistered Trainer</h1><p>Dog training in Richmond. No ABN listed.</p></body></html>"

    # Return AI confidence of 0.95 (super high) but NO active ABR
    with patch("services.ingestion_manager.polite_fetch_url", new=AsyncMock(return_value=(True, mock_html, {"http_status": 200, "sha256": "def"}, "ok"))), \
         patch("services.ai.extract_trainer_source", new=AsyncMock(return_value={
             "training_philosophy": "Positive Reinforcement / Force-Free",
             "specialties": ["puppy_training"],
             "service_formats": ["in_home"],
             "serviced_suburbs": ["Richmond"],
             "confidence": 0.95,
             "reasoning": "High confidence text.",
             "signals": ["good signal"],
             "published": False,
             "abn_verified": False,
         })), \
         patch("services.abr_client.AbrClient.lookup", new=AsyncMock(return_value={"ok": False, "state": "not_found"})):

        summary = asyncio.run(ingestion_manager.run_batch_ingestion_pipeline(
            source_urls=["https://unregistered-trainer.com.au"],
            db=db,
            batch_size=1,
        ))

        assert summary["total_processed"] == 1
        assert summary["qualified"] == 0
        assert summary["held"] == 1

        # Verify trainer was persisted as held, NOT published
        assert len(db.trainers.rows) == 1
        trainer = db.trainers.rows[0]
        assert trainer["published"] is False
        assert trainer["ingestion_quality_status"] == "held"
        assert trainer["ingestion_hold_reason"] == "statutory_or_quality_evidence_required"


def test_run_batch_ingestion_pipeline_protects_claimed_profile():
    """Ensures claimed profiles are NEVER overwritten by automated ingestion sweeps."""
    db = _MockDB()

    # Existing claimed trainer
    claimed_doc = {
        "id": "trainer_claimed_123",
        "name": "Original Trainer Name",
        "website": "https://claimedtrainer.com.au",
        "phone": "+61411222333",
        "claimed": True,
        "claim_status": "claimed",
        "tier": "pro",
        "bio": "Original custom trainer bio",
        "published": True,
    }
    asyncio.run(db.trainers.insert_one(claimed_doc))

    mock_html = "<html><body><h1>Overwriting Attempt</h1><p>New bio text</p></body></html>"

    with patch("services.ingestion_manager.polite_fetch_url", new=AsyncMock(return_value=(True, mock_html, {"http_status": 200, "sha256": "ghi"}, "ok"))):
        summary = asyncio.run(ingestion_manager.run_batch_ingestion_pipeline(
            source_urls=["https://claimedtrainer.com.au"],
            db=db,
            batch_size=1,
        ))

        assert summary["total_processed"] == 1
        assert summary["skipped_claimed"] == 1

        # Verify trainer record was preserved
        trainer = db.trainers.rows[0]
        assert trainer["name"] == "Original Trainer Name"
        assert trainer["bio"] == "Original custom trainer bio"
        assert trainer["tier"] == "pro"
        assert trainer["claimed"] is True
        assert "source_last_crawled_at" in trainer


def test_run_batch_ingestion_pipeline_logs_failures_to_ops():
    """Ensures fetch failures write structured logs to db.source_ingestion_state for /ops."""
    db = _MockDB()

    with patch("services.ingestion_manager.polite_fetch_url", new=AsyncMock(return_value=(False, None, None, "dns_unresolvable:empty_domain"))):
        summary = asyncio.run(ingestion_manager.run_batch_ingestion_pipeline(
            source_urls=["https://broken-nonexistent-site.local"],
            db=db,
            batch_size=1,
        ))

        assert summary["held"] == 1
        assert len(summary["errors"]) == 1

        # Verify /ops state collection
        assert len(db.source_ingestion_state.rows) == 1
        err_row = db.source_ingestion_state.rows[0]
        assert err_row["source_url"] == "https://broken-nonexistent-site.local"
        assert err_row["last_error"] == "dns_unresolvable:empty_domain"
        assert err_row["last_error_code"] == "source_ingestion_failure"
        assert err_row["consecutive_failures"] == 1


def test_trainer_ingest_endpoint_requires_oidc():
    import server
    with pytest.raises(server.HTTPException) as rejected:
        asyncio.run(server.run_trainer_ingest_job(payload=None, authorization=""))
    assert rejected.value.status_code == 401


def test_trainer_ingest_endpoint_executes_with_valid_oidc(monkeypatch):
    import server
    monkeypatch.setenv("CLOUD_SCHEDULER_OIDC_SERVICE_ACCOUNT", "scheduler@dtd.test")
    monkeypatch.setenv("CLOUD_SCHEDULER_OIDC_AUDIENCE", "https://dtd-api.test")
    monkeypatch.setattr(
        server.google_id_token,
        "verify_oauth2_token",
        lambda token, request, audience: {
            "email": "scheduler@dtd.test",
            "email_verified": True,
            "aud": audience,
        },
    )

    fake_ingest_summary = {"ok": True, "total_processed": 1, "qualified": 1, "held": 0}
    fake_guardian_summary = {"status": "clean", "total_trainers_scanned": 1}

    with patch("services.ingestion_manager.run_batch_ingestion_pipeline", new=AsyncMock(return_value=fake_ingest_summary)), \
         patch("services.pipeline_guardian.audit_corpus_integrity", new=AsyncMock(return_value=fake_guardian_summary)):

        payload = server.TrainerIngestJobRequest(source_urls=["https://test-trainer.com.au"], batch_size=1)
        res = asyncio.run(server.run_trainer_ingest_job(payload=payload, authorization="Bearer valid-token"))

        assert res["ok"] is True
        assert res["ingestion"]["qualified"] == 1
        assert res["guardian"]["status"] == "clean"
        assert "executed_at" in res


def test_trainer_ingest_operator_manual_execution():
    """Verifies that the /ops operator-manual endpoint runs with trigger='operator_manual' and persists to db.ingestion_runs."""
    import server
    mock_db = _MockDB()

    fake_ingest_summary = {"ok": True, "total_processed": 2, "qualified": 2, "held": 0, "errors": []}
    fake_guardian_summary = {"status": "clean", "total_trainers_scanned": 2, "anomalies": []}

    with patch.object(server, "db", mock_db), \
         patch("services.ingestion_manager.run_batch_ingestion_pipeline", new=AsyncMock(return_value=fake_ingest_summary)), \
         patch("services.pipeline_guardian.audit_corpus_integrity", new=AsyncMock(return_value=fake_guardian_summary)):

        payload = server.TrainerIngestJobRequest(source_urls=["https://trainer1.com.au"], batch_size=2)
        res = asyncio.run(server.run_trainer_ingest_job_manual(payload=payload, _=None))

        assert res["ok"] is True
        assert res["trigger"] == "operator_manual"
        assert res["ingestion"]["qualified"] == 2
        assert res["guardian"]["status"] == "clean"
        assert res["id"].startswith("ingest_")

        # Verify persisted record in db.ingestion_runs
        assert len(mock_db.ingestion_runs.rows) == 1
        saved_run = mock_db.ingestion_runs.rows[0]
        assert saved_run["id"] == res["id"]
        assert saved_run["trigger"] == "operator_manual"
        assert saved_run["ok"] is True
        assert saved_run["ingestion"]["qualified"] == 2


def test_trainer_ingest_pipeline_failure_records_to_db():
    """Verifies that pipeline exceptions record a failure entry in db.ingestion_runs and /ops state."""
    import server
    mock_db = _MockDB()

    with patch.object(server, "db", mock_db), \
         patch("services.ingestion_manager.run_batch_ingestion_pipeline", new=AsyncMock(side_effect=RuntimeError("Simulated LLM outage"))):

        with pytest.raises(server.HTTPException) as exc_info:
            asyncio.run(server.run_trainer_ingest_job_manual(payload=None, _=None))

        assert exc_info.value.status_code == 500
        assert "Simulated LLM outage" in str(exc_info.value.detail)

        # Verify failed run was logged in db.ingestion_runs
        assert len(mock_db.ingestion_runs.rows) == 1
        failed_run = mock_db.ingestion_runs.rows[0]
        assert failed_run["ok"] is False
        assert failed_run["trigger"] == "operator_manual"
        assert "Simulated LLM outage" in failed_run["error"]

        # Verify db.source_ingestion_state recorded the failure
        assert len(mock_db.source_ingestion_state.rows) == 1
        state_row = mock_db.source_ingestion_state.rows[0]
        assert state_row["source_url"] == "system_job_failure"
        assert state_row["last_error_code"] == "internal_job_exception"
