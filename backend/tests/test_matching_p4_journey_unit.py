"""Unit tests for Package P4: Owner Journey & Follow-Up Lifecycle.

Governed by:
- AGENTS.md (Rule 6A, locked boundaries)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md (M2, M5)
- specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md (Section 2, Section 5)
- Findings: DF-015, DF-016, DF-018, DF-022

Acceptance Criteria Verified:
1. Legacy InstantMatchIn rejection: Old two-field requests are rejected with HTTP 400 and cannot create a match, match event, or context token. Never fabricates owner age, concern, format, or method.
2. Follow-up endpoint (/api/match/follow-up) requires header-based X-Match-Context-Token; query parameters (?token=...) are strictly rejected with 400.
3. Follow-up endpoint creates idempotent intro linked to match context without leaking raw behavioural text.
4. Follow-up endpoint strictly requires consent_contact_release.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import server
from services.matching_contract_v2 import (
    DECISION_CONTRACT_VERSION,
    MatchConsentIn,
    MatchRequestIn,
    PrimaryConcern,
    ServiceFormatPreference,
    generate_match_context_token,
    hash_match_context_token,
)
from tests.fixtures_matching_v2 import (
    make_test_trainer_doc,
    make_valid_match_request,
)


class _MockCollection:
    def __init__(self, rows: List[Dict[str, Any]] = None):
        self.rows = list(rows or [])
        self.inserted: List[Dict[str, Any]] = []

    def find(self, query: Dict[str, Any] = None, projection: Dict[str, Any] = None):
        res = list(self.rows)
        if query:
            if "published" in query:
                res = [r for r in res if r.get("published") == query["published"]]
            if "region" in query and "$in" in query["region"]:
                allowed_regions = set(query["region"]["$in"])
                res = [r for r in res if r.get("region") in allowed_regions]
        self._last_find = res
        return self

    async def to_list(self, limit: int = 100):
        return list(getattr(self, "_last_find", self.rows))[:limit]

    async def find_one(self, query: Dict[str, Any], projection: Dict[str, Any] = None):
        for r in self.rows + self.inserted:
            if "$or" in query:
                or_matches = False
                for branch in query["$or"]:
                    branch_match = all(r.get(k) == v for k, v in branch.items())
                    if branch_match:
                        or_matches = True
                        break
                if or_matches:
                    return dict(r)
                continue
            match = True
            for k, v in query.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                return dict(r)
        return None

    async def insert_one(self, doc: Dict[str, Any]):
        self.inserted.append(dict(doc))
        return SimpleNamespace(inserted_id="mock_id")


def _make_dummy_request(
    ip: str = "127.0.0.1",
    method: str = "POST",
    path: str = "/api/match",
    query_string: str = "",
    headers: Dict[str, str] = None,
) -> Request:
    raw_headers = [(b"host", b"testserver")]
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode(), v.encode()))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string.encode(),
        "headers": raw_headers,
        "client": (ip, 12345),
    }
    return Request(scope)


class TestP4LegacyRejectionAndFollowUp:
    def test_legacy_payload_rejected_with_400_and_cannot_create_match(self, monkeypatch):
        """Legacy two-field payload is rejected with 400 and cannot create match, event, or token."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
        )
        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        legacy_payload = server.InstantMatchIn(
            description="8-month kelpie pulling on leash",
            suburb="Richmond",
            consent_match_processing=True,
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.instant_match(legacy_payload))

        assert exc.value.status_code == 400
        assert "Legacy two-field match requests are deprecated and rejected" in exc.value.detail
        # Invariants: Zero match events, zero context tokens persisted
        assert len(fake_db.match_events.inserted) == 0
        assert len(fake_db.match_contexts.inserted) == 0

    def test_follow_up_query_token_strictly_forbidden(self, monkeypatch):
        """Follow-up endpoint strictly forbids query-param tokens (?token=...)."""
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([]),
            trainers=_MockCollection([]),
            intros=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_richmond",
            user_name="Jane Doe",
            user_email="jane@example.com",
            consent_contact_release=True,
        )
        req = _make_dummy_request(
            method="POST",
            path="/api/match/follow-up",
            query_string="token=secret_query_token",
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.create_match_follow_up(payload=payload, request=req))

        assert exc.value.status_code == 400
        assert "Query parameter authentication is forbidden" in exc.value.detail

    def test_follow_up_missing_header_rejected_with_401(self, monkeypatch):
        """Follow-up endpoint requires X-Match-Context-Token header; 401 if missing."""
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([]),
            trainers=_MockCollection([]),
            intros=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_richmond",
            user_name="Jane Doe",
            user_email="jane@example.com",
            consent_contact_release=True,
        )
        req = _make_dummy_request(method="POST", path="/api/match/follow-up")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.create_match_follow_up(payload=payload, request=req))

        assert exc.value.status_code == 401
        assert "Missing X-Match-Context-Token header" in exc.value.detail

    def test_follow_up_missing_consent_rejected_with_400(self, monkeypatch):
        """Follow-up endpoint requires consent_contact_release=True."""
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([]),
            trainers=_MockCollection([]),
            intros=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_richmond",
            user_name="Jane Doe",
            user_email="jane@example.com",
            consent_contact_release=False,
        )
        req = _make_dummy_request(
            method="POST",
            path="/api/match/follow-up",
            headers={"X-Match-Context-Token": "some_token"},
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.create_match_follow_up(payload=payload, request=req))

        assert exc.value.status_code == 400
        assert "Consent required for contact release" in exc.value.detail

    def test_follow_up_creates_intro_linked_to_match_context(self, monkeypatch):
        """Follow-up creates intro linked to match context with zero raw behavioural description."""
        raw_token, token_hash = generate_match_context_token()
        ctx_doc = {
            "token_hash": token_hash,
            "match_id": "match_p4_test",
            "suburb_or_postcode": "Richmond",
            "dog_age_months": 18,
            "primary_concerns": ["basic_manners"],
            "service_format": "in_home",
        }
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
        )
        trainer["email"] = "trainer@example.com"
        trainer["phone"] = "0412345678"
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([ctx_doc]),
            trainers=_MockCollection([trainer]),
            intros=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_richmond",
            user_name="Jane Doe",
            user_email="jane@example.com",
            user_phone="0400000000",
            notes="Please call in the afternoon",
            consent_contact_release=True,
        )
        req = _make_dummy_request(
            method="POST",
            path="/api/match/follow-up",
            headers={"X-Match-Context-Token": raw_token},
        )
        out = asyncio.run(server.create_match_follow_up(payload=payload, request=req))

        # Strict response shape: intro_id, match_id, trainer_id, delivery_state, idempotent
        assert set(out.keys()) == {"intro_id", "match_id", "trainer_id", "delivery_state", "idempotent"}
        assert out["trainer_id"] == "t_richmond"
        assert out["match_id"] == "match_p4_test"
        assert out["delivery_state"] == "delivered"
        assert out["idempotent"] is False
        assert isinstance(out["intro_id"], str) and len(out["intro_id"]) > 0

        # No token, contact data, raw description, score, or tier in response
        assert "context_token" not in out
        assert "token" not in out
        assert "contact" not in out
        assert "user_email" not in out
        assert "description" not in out
        assert "match_score" not in out
        assert "tier" not in out

        # Check DB insertion: intro record has match_id, consent, and idempotency keys
        assert len(fake_db.intros.inserted) == 1
        inserted = fake_db.intros.inserted[0]
        assert inserted["match_id"] == "match_p4_test"
        assert inserted["trainer_id"] == "t_richmond"
        assert inserted["composite_idempotency_key"] is not None
        assert inserted["consent_contact_release"] is True

    def test_follow_up_idempotency_prevents_duplicate_intro(self, monkeypatch):
        """Repeated follow-up enquiry with same idempotency key returns existing intro with idempotent=True."""
        raw_token, token_hash = generate_match_context_token()
        ctx_doc = {
            "token_hash": token_hash,
            "match_id": "match_p4_test",
            "suburb_or_postcode": "Richmond",
            "dog_age_months": 18,
            "primary_concerns": ["basic_manners"],
            "service_format": "in_home",
        }
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
        )
        trainer["email"] = "trainer@example.com"
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([ctx_doc]),
            trainers=_MockCollection([trainer]),
            intros=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_richmond",
            user_name="Jane Doe",
            user_email="jane@example.com",
            consent_contact_release=True,
        )
        req = _make_dummy_request(
            method="POST",
            path="/api/match/follow-up",
            headers={
                "X-Match-Context-Token": raw_token,
                "Idempotency-Key": "client_idem_key_123",
            },
        )
        # First call
        out1 = asyncio.run(server.create_match_follow_up(payload=payload, request=req, idempotency_key="client_idem_key_123"))
        assert len(fake_db.intros.inserted) == 1
        assert out1["idempotent"] is False

        # Second call with same idempotency key
        out2 = asyncio.run(server.create_match_follow_up(payload=payload, request=req, idempotency_key="client_idem_key_123"))
        assert len(fake_db.intros.inserted) == 1
        assert out2["idempotent"] is True
        assert out1["intro_id"] == out2["intro_id"]

    def test_follow_up_rejects_candidate_not_in_match_results(self, monkeypatch):
        """Follow-up enquiry fails with 400 if trainer_id is not in match event result_ids."""
        raw_token, token_hash = generate_match_context_token()
        ctx_doc = {
            "token_hash": token_hash,
            "match_id": "match_p4_test",
            "suburb_or_postcode": "Richmond",
            "dog_age_months": 18,
            "primary_concerns": ["basic_manners"],
            "service_format": "in_home",
        }
        trainer = make_test_trainer_doc(
            trainer_id="t_other",
            name="Other Dog Trainer",
            serviced_suburbs=["Richmond"],
        )
        # Match event only has t_richmond in result_ids
        match_event_doc = {
            "id": "match_p4_test",
            "result_ids": ["t_richmond"],
        }
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([ctx_doc]),
            trainers=_MockCollection([trainer]),
            match_events=_MockCollection([match_event_doc]),
            intros=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_other",
            user_name="Jane Doe",
            user_email="jane@example.com",
            consent_contact_release=True,
        )
        req = _make_dummy_request(
            method="POST",
            path="/api/match/follow-up",
            headers={"X-Match-Context-Token": raw_token},
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.create_match_follow_up(payload=payload, request=req))

        assert exc.value.status_code == 400
        assert "Trainer is not in eligible match results" in exc.value.detail
