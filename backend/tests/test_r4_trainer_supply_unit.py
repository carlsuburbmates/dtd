"""Unit tests for Stage R4 (Trainer Supply & Acquisition Controls).

Covers:
- DF-044: Fail-closed source and candidate URL/domain registry authorization.
- DF-045: Robots.txt fail-closed/defer on unavailable, error, or malformed policy.
  Target page fetch is never executed when robots retrieval fails or disallows.
- DF-051: Acquisition deduplication regression: expired claim challenge leaves
  profile eligible for acquisition updates without stale pending block.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest
import requests

from services import automation, ingestion_manager, source_approvals
from services.trainer_quality import is_claimed_profile


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
                if r.get(k) != v:
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
        self.trainers = _MockCollection()
        self.discovery_queue = _MockCollection()
        self.source_ingestion_state = _MockCollection()
        self.system_state = _MockCollection()
        self.ingestion_runs = _MockCollection()


# ==============================================================================
# DF-044: Source & Candidate URL/Domain Authorization
# ==============================================================================

def test_df044_candidate_url_approvals_synthetic():
    registry = {
        "version": 1,
        "sources": [
            {
                "provider": "public_business_websites",
                "approved": True,
                "approved_by": "DTD owner",
                "terms_reviewed_at": "2026-09-11",
                "approved_uses": ["trainer_profile_source"],
                "approved_domains": ["*"],
                "disallowed_domains": [
                    "google.com",
                    "maps.google.com",
                    "yellowpages.com.au",
                    "facebook.com",
                ],
            }
        ],
    }

    # Allowed general trainer domain
    ok, reason = source_approvals.is_candidate_url_approved(registry, "https://kintalaclub.com.au/puppy")
    assert ok is True
    assert reason == "approved"

    # Disallowed domains
    ok, reason = source_approvals.is_candidate_url_approved(registry, "https://www.yellowpages.com.au/vic/richmond/dog-trainer")
    assert ok is False
    assert "disallowed_domain" in reason

    ok, reason = source_approvals.is_candidate_url_approved(registry, "https://google.com/maps/place/DogTrainer")
    assert ok is False
    assert "disallowed_domain" in reason

    ok, reason = source_approvals.is_candidate_url_approved(registry, "https://facebook.com/dogtrainersmelb")
    assert ok is False
    assert "disallowed_domain" in reason

    # Invalid / malformed scheme
    ok, reason = source_approvals.is_candidate_url_approved(registry, "ftp://malicious.example.com")
    assert ok is False
    assert reason == "unsupported_url_scheme"


def test_df044_discovery_source_approvals_synthetic():
    registry = {
        "version": 1,
        "sources": [
            {
                "provider": "configured_discovery_sources",
                "approved": True,
                "approved_by": "DTD owner",
                "terms_reviewed_at": "2026-10-20",
                "approved_uses": ["discovery_scan"],
                "approved_source_urls": [
                    "https://www.petprofessionalguild.com/find-a-member",
                ],
                "approved_domains": [
                    "petprofessionalguild.com",
                ],
            }
        ],
    }

    # Approved source
    ok, reason = source_approvals.is_discovery_source_approved(registry, "https://www.petprofessionalguild.com/find-a-member")
    assert ok is True
    assert reason == "approved"

    # Unapproved source URL on different domain
    ok, reason = source_approvals.is_discovery_source_approved(registry, "https://unapproved-aggregator.com/trainers")
    assert ok is False
    assert "unapproved_discovery_source" in reason


def test_df044_ingest_discovery_sources_filters_unapproved_and_disallowed(monkeypatch):
    db = _MockDB()

    # Synthetic registry
    test_reg = {
        "version": 1,
        "sources": [
            {
                "provider": "configured_discovery_sources",
                "approved": True,
                "approved_by": "DTD owner",
                "terms_reviewed_at": "2026-10-20",
                "approved_uses": ["discovery_scan"],
                "approved_domains": ["approved-directory.com.au"],
            },
            {
                "provider": "public_business_websites",
                "approved": True,
                "approved_by": "DTD owner",
                "terms_reviewed_at": "2026-09-11",
                "approved_uses": ["trainer_profile_source"],
                "approved_domains": ["*"],
                "disallowed_domains": ["yellowpages.com.au"],
            },
        ],
    }

    # 1 approved source and 1 unapproved source configured
    monkeypatch.setenv(
        "DISCOVERY_SOURCE_URLS",
        "https://unapproved-scraper.com/list,https://approved-directory.com.au/trainers",
    )

    class _Response:
        status_code = 200
        headers = {"content-type": "text/html; charset=utf-8"}
        content = b"html content"
        text = """
        <html>
            <a href="https://goodtrainer.com.au/dog-training">Valid Trainer</a>
            <a href="https://yellowpages.com.au/dog-training">Disallowed Aggregator</a>
        </html>
        """
        def raise_for_status(self):
            return None

    monkeypatch.setattr(automation.requests, "get", lambda *a, **k: _Response())

    summary = asyncio.run(automation.ingest_discovery_sources(db, registry=test_reg))

    # Unapproved source must fail closed and record alert without fetching
    assert summary["failed_sources"] == 1
    assert any("unapproved_source" in r for r in summary["reason_codes"])
    assert any(a["type"] == "unapproved_discovery_source" for a in summary["alerts"])

    # Approved source yielded only the approved candidate URL
    assert summary["queued"] == 1
    assert len(db.discovery_queue.rows) == 1
    assert db.discovery_queue.rows[0]["url"] == "https://goodtrainer.com.au/dog-training"


# ==============================================================================
# DF-045: Robots Fail-Closed / Defer on Unavailable or Error Policy
# ==============================================================================

def test_df045_robots_200_disallowed_blocks_target_fetch():
    target_fetch_called = False
    session = requests.Session()

    class _RobotsResponse:
        status_code = 200
        text = "User-agent: *\nDisallow: /"

    def _mock_session_get(url, *args, **kwargs):
        nonlocal target_fetch_called
        if "robots.txt" in url:
            return _RobotsResponse()
        target_fetch_called = True
        resp = requests.Response()
        resp.status_code = 200
        return resp

    with patch("services.ingestion_manager.check_dns_resolvable", return_value=(True, "ok")), \
         patch.object(session, "get", side_effect=_mock_session_get):
        ok, content, meta, reason = asyncio.run(ingestion_manager.polite_fetch_url("https://trainer.example.com/services", session))

    assert ok is False
    assert "robots_denied" in reason
    assert target_fetch_called is False, "Target page MUST NOT be fetched if robots.txt disallows"


def test_df045_robots_200_allowed_proceeds_to_fetch():
    target_fetch_called = False
    session = requests.Session()

    class _RobotsResponse:
        status_code = 200
        text = "User-agent: *\nAllow: /"

    class _TargetResponse:
        status_code = 200
        ok = True
        url = "https://trainer.example.com/services"
        content = b"<html><body><h1>Trainer Services</h1></body></html>"
        text = "<html><body><h1>Trainer Services</h1></body></html>"
        headers = {"content-type": "text/html"}

    def _mock_session_get(url, *args, **kwargs):
        nonlocal target_fetch_called
        if "robots.txt" in url:
            return _RobotsResponse()
        target_fetch_called = True
        return _TargetResponse()

    with patch("services.ingestion_manager.check_dns_resolvable", return_value=(True, "ok")), \
         patch.object(session, "get", side_effect=_mock_session_get):
        ok, content, meta, reason = asyncio.run(ingestion_manager.polite_fetch_url("https://trainer.example.com/services", session))

    assert ok is True
    assert reason == "ok"
    assert target_fetch_called is True
    assert "Trainer Services" in content


def test_df045_robots_404_allowed_rfc9309():
    target_fetch_called = False
    session = requests.Session()

    class _Robots404Response:
        status_code = 404
        text = "Not Found"

    class _TargetResponse:
        status_code = 200
        ok = True
        url = "https://trainer.example.com/services"
        content = b"<html><body><h1>Trainer 404 Robots</h1></body></html>"
        text = "<html><body><h1>Trainer 404 Robots</h1></body></html>"
        headers = {"content-type": "text/html"}

    def _mock_session_get(url, *args, **kwargs):
        nonlocal target_fetch_called
        if "robots.txt" in url:
            return _Robots404Response()
        target_fetch_called = True
        return _TargetResponse()

    with patch("services.ingestion_manager.check_dns_resolvable", return_value=(True, "ok")), \
         patch.object(session, "get", side_effect=_mock_session_get):
        ok, content, meta, reason = asyncio.run(ingestion_manager.polite_fetch_url("https://trainer.example.com/services", session))

    assert ok is True
    assert reason == "ok"
    assert target_fetch_called is True


@pytest.mark.parametrize("status_code", [500, 503, 403, 429])
def test_df045_robots_http_error_fails_closed_no_fetch(status_code):
    target_fetch_called = False
    session = requests.Session()

    class _RobotsErrorResponse:
        def __init__(self, code):
            self.status_code = code
            self.text = "Error"

    def _mock_session_get(url, *args, **kwargs):
        nonlocal target_fetch_called
        if "robots.txt" in url:
            return _RobotsErrorResponse(status_code)
        target_fetch_called = True
        resp = requests.Response()
        resp.status_code = 200
        return resp

    with patch("services.ingestion_manager.check_dns_resolvable", return_value=(True, "ok")), \
         patch.object(session, "get", side_effect=_mock_session_get):
        ok, content, meta, reason = asyncio.run(ingestion_manager.polite_fetch_url("https://trainer.example.com/services", session))

    assert ok is False
    assert "robots_unavailable" in reason
    assert target_fetch_called is False, f"Target page MUST NOT be fetched on robots status {status_code}"


def test_df045_robots_network_timeout_fails_closed_no_fetch():
    target_fetch_called = False
    session = requests.Session()

    def _mock_session_get(url, *args, **kwargs):
        nonlocal target_fetch_called
        if "robots.txt" in url:
            raise requests.Timeout("robots request timed out")
        target_fetch_called = True
        resp = requests.Response()
        resp.status_code = 200
        return resp

    with patch("services.ingestion_manager.check_dns_resolvable", return_value=(True, "ok")), \
         patch.object(session, "get", side_effect=_mock_session_get):
        ok, content, meta, reason = asyncio.run(ingestion_manager.polite_fetch_url("https://trainer.example.com/services", session))

    assert ok is False
    assert "robots_unavailable:network_error" in reason
    assert target_fetch_called is False, "Target page MUST NOT be fetched if robots request times out"


# ==============================================================================
# DF-051: Acquisition Deduplication with Expired Claim Challenge
# ==============================================================================

def test_df051_expired_claim_challenge_does_not_block_acquisition_dedup():
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(minutes=30)).isoformat()
    future_time = (now + timedelta(minutes=15)).isoformat()

    # 1. Claim status pending_verification with expired OTP
    expired_trainer = {
        "id": "tr_expired_1",
        "name": "Expired OTP Trainer",
        "claim_status": "pending_verification",
        "is_claimed": False,
        "claim_expires_at": expired_time,
    }
    assert is_claimed_profile(expired_trainer) is False, (
        "Expired pending claim challenge MUST NOT be treated as claimed in acquisition dedup"
    )

    # 2. Claim status pending_verification with active OTP
    active_pending_trainer = {
        "id": "tr_active_pending",
        "name": "Active OTP Trainer",
        "claim_status": "pending_verification",
        "is_claimed": False,
        "claim_expires_at": future_time,
    }
    assert is_claimed_profile(active_pending_trainer) is True, (
        "Active pending claim challenge MUST be protected from overwrite"
    )

    # 3. Fully verified claimed profile
    verified_trainer = {
        "id": "tr_claimed",
        "name": "Verified Trainer",
        "claim_status": "claimed",
        "is_claimed": True,
    }
    assert is_claimed_profile(verified_trainer) is True
