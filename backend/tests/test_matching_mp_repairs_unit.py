"""Dedicated unit test suite covering the 5 repair blockers (MP-001 through MP-005).

Governed by:
- MATCHING_PIPELINE_P2_P6_INDEPENDENT_AUDIT_2026-10-04.md (Codex independent audit)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md
- AGENTS.md (Rule 6A, Evidence-first owner-assistance)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import server
from services import matching_contract_v2
from services import notifications as notifications_service
from services import trainer_quality
from services import urgent_providers as urgent_providers_service
from tests.fixtures_matching_v2 import (
    make_test_raw_trainer_doc,
    make_test_trainer_doc,
    make_valid_match_request,
)


class _MockCollection:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None):
        self.rows: List[Dict[str, Any]] = list(rows or [])
        self.inserted: List[Dict[str, Any]] = []

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        res = list(self.rows) + list(self.inserted)
        if query:
            if "published" in query:
                res = [r for r in res if r.get("published") == query["published"]]
            if "contact_ready" in query:
                res = [r for r in res if r.get("contact_ready") == query["contact_ready"]]
            if "region" in query:
                res = [r for r in res if r.get("region") == query["region"]]
            if "status" in query:
                res = [r for r in res if r.get("status") == query["status"]]
            if "token_hash" in query:
                res = [r for r in res if r.get("token_hash") == query["token_hash"]]
            if "id" in query:
                res = [r for r in res if r.get("id") == query["id"]]
            if "provider_id" in query:
                res = [r for r in res if r.get("provider_id") == query["provider_id"]]
        return _MockCursor(res)

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None):
        res = list(self.rows) + list(self.inserted)
        for r in res:
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

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        for r in self.rows + self.inserted:
            match = True
            for k, v in query.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                if "$set" in update:
                    r.update(update["$set"])
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)

    async def count_documents(self, query: Dict[str, Any]):
        c = 0
        for r in self.rows + self.inserted:
            match = True
            for k, v in query.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                c += 1
        return c


class _MockCursor:
    def __init__(self, items: List[Dict[str, Any]]):
        self.items = items

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n: int):
        self.items = self.items[:n]
        return self

    async def to_list(self, length: Optional[int] = None):
        return list(self.items)


def _make_dummy_request(client_host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/match",
        "headers": [(b"user-agent", b"Pytest-MP-Repairs")],
        "client": (client_host, 12345),
        "query_string": b"",
    }
    return Request(scope)


# ==============================================================================
# MP-001: Query-Time Stored Projection Freshness
# ==============================================================================

class TestMP001StoredProjectionFreshness:
    def test_stale_persisted_projection_is_excluded_at_query_time(self, monkeypatch):
        """A persisted document with projection_version: v1 and match_eligible: True

        must be dynamically recomputed at query time. If confirmation age > 180 days,
        it must be excluded from the candidate pool before matching evaluations.
        """
        raw_stale = make_test_raw_trainer_doc(
            trainer_id="t_stale_projection",
            name="Stale Recall Academy",
            suburb="Richmond",
            specialties=["basic_manners", "puppy_prep"],
            serviced_suburbs=["Richmond"],
            days_ago=200,
        )
        persisted_stale = dict(raw_stale)
        persisted_stale["projection_version"] = "v1"
        persisted_stale["match_eligible"] = True

        fake_db = SimpleNamespace(
            trainers=_MockCollection([persisted_stale]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
            urgent_providers=_MockCollection([]),
            ai_degradation_events=_MockCollection([]),
            intros=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(suburb_or_postcode="Richmond", primary_concerns=["basic_manners"])
        res = asyncio.run(server.instant_match(req, _make_dummy_request()))

        # Candidate pool must be empty because confirmation age is 200 days (>180)
        assert res["decision_state"] in ("no_confirmed_match", "degraded_no_confirmed_match")
        assert len(res["candidates"]) == 0

    def test_invalidated_abn_persisted_projection_fails_closed(self, monkeypatch):
        """If a stored document has cancelled ABN status, dynamic query-time re-projection

        must mark it ineligible and exclude it from the candidate pool.
        """
        raw_cancelled = make_test_raw_trainer_doc(
            trainer_id="t_cancelled_abn",
            name="Cancelled ABN Training",
            suburb="Richmond",
            specialties=["basic_manners"],
            serviced_suburbs=["Richmond"],
            days_ago=10,
            abn_verified=False,
            abn_status="cancelled",
        )
        persisted_doc = dict(raw_cancelled)
        persisted_doc["projection_version"] = "v1"
        persisted_doc["match_eligible"] = True

        fake_db = SimpleNamespace(
            trainers=_MockCollection([persisted_doc]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
            urgent_providers=_MockCollection([]),
            ai_degradation_events=_MockCollection([]),
            intros=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(suburb_or_postcode="Richmond", primary_concerns=["basic_manners"])
        res = asyncio.run(server.instant_match(req, _make_dummy_request()))

        assert len(res["candidates"]) == 0
        assert res["decision_state"] in ("no_confirmed_match", "degraded_no_confirmed_match")


# ==============================================================================
# MP-002: Real Follow-Up Notification Dispatch and Idempotent Retry
# ==============================================================================

class TestMP002FollowUpRealDeliveryAndRetry:
    def test_follow_up_success_delivery_and_notification(self, monkeypatch):
        """Match follow-up dispatches real notification and records delivered state."""
        raw_token, token_hash = matching_contract_v2.generate_match_context_token()
        ctx_doc = {
            "token_hash": token_hash,
            "match_id": "match_mp2_success",
            "suburb_or_postcode": "Richmond",
            "dog_age_months": 12,
            "primary_concerns": ["basic_manners"],
            "service_format": "in_home",
        }
        trainer = make_test_trainer_doc(
            trainer_id="t_mp2_success",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
        )
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([ctx_doc]),
            trainers=_MockCollection([trainer]),
            intros=_MockCollection([]),
            match_events=_MockCollection([{"id": "match_mp2_success", "campaign": "", "source": ""}]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_mp2_success",
            user_name="Jane Doe",
            user_email="jane@example.com",
            user_phone="0411222333",
            notes="Need help with leash pulling",
            consent_contact_release=True,
        )

        res = asyncio.run(
            server.create_match_follow_up(
                payload=payload,
                request=_make_dummy_request(),
                x_match_context_token=raw_token,
                idempotency_key="idem_mp2_success",
            )
        )

        assert res["delivery_state"] == "delivered"
        assert res["idempotent"] is False
        assert len(fake_db.intros.inserted) == 1
        inserted = fake_db.intros.inserted[0]
        assert inserted["delivery_state"] == "delivered"
        assert inserted["match_id"] == "match_mp2_success"

    def test_follow_up_transport_failure_records_retryable_state(self, monkeypatch):
        """When notification dispatch fails on transport, state is retryable_failure."""
        raw_token, token_hash = matching_contract_v2.generate_match_context_token()
        ctx_doc = {
            "token_hash": token_hash,
            "match_id": "match_mp2_fail",
            "suburb_or_postcode": "Richmond",
            "dog_age_months": 12,
            "primary_concerns": ["basic_manners"],
            "service_format": "in_home",
        }
        trainer = make_test_trainer_doc(
            trainer_id="t_mp2_fail",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
        )
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([ctx_doc]),
            trainers=_MockCollection([trainer]),
            intros=_MockCollection([]),
            match_events=_MockCollection([{"id": "match_mp2_fail", "campaign": "", "source": ""}]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # Force notifications service to report retryable transport failure
        async def _mock_notify_fail(*args, **kwargs):
            return {"attempted": True, "delivered": False, "reason": "transport_error"}

        monkeypatch.setattr(notifications_service, "notify_trainer_new_intro", _mock_notify_fail)

        payload = server.MatchFollowUpIn(
            trainer_id="t_mp2_fail",
            user_name="Jane Doe",
            user_email="jane@example.com",
            user_phone="0411222333",
            notes="Need help with leash pulling",
            consent_contact_release=True,
        )

        res = asyncio.run(
            server.create_match_follow_up(
                payload=payload,
                request=_make_dummy_request(),
                x_match_context_token=raw_token,
                idempotency_key="idem_mp2_fail",
            )
        )

        assert res["delivery_state"] == "retryable_failure"
        assert fake_db.intros.inserted[0]["delivery_state"] == "retryable_failure"

    def test_oversight_retry_performs_real_dispatch(self, monkeypatch):
        """Oversight retry performs real notification dispatch on retryable records."""
        intro_record = {
            "id": "intro_retry_test",
            "match_id": "match_retry_test",
            "trainer_id": "t_retry_trainer",
            "trainer_name": "Retry Trainer",
            "user_name": "Bob",
            "user_email": "bob@example.com",
            "suburb": "Richmond",
            "delivery_state": "retryable_failure",
            "status": "retryable_failure",
            "follow_up_type": "match_follow_up",
        }
        trainer_doc = {
            "id": "t_retry_trainer",
            "name": "Retry Trainer",
            "email": "trainer@example.com",
            "published": True,
            "region": "Greater Melbourne",
            "suburb": "Richmond",
        }
        fake_db = SimpleNamespace(
            intros=_MockCollection([intro_record]),
            trainers=_MockCollection([trainer_doc]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        retry_payload = server.OversightFollowUpRetryIn(confirmed=True, notes="Operator test retry")

        # First retry call: dispatches and marks delivered
        res = asyncio.run(
            server.oversight_matching_follow_up_retry(
                intro_id="intro_retry_test",
                payload=retry_payload,
            )
        )
        assert res["delivery_state"] == "delivered"
        assert res["idempotent"] is False
        assert intro_record["delivery_state"] == "delivered"

        # Second retry call: already delivered, returns idempotent: True
        res_replay = asyncio.run(
            server.oversight_matching_follow_up_retry(
                intro_id="intro_retry_test",
                payload=retry_payload,
            )
        )
        assert res_replay["delivery_state"] == "delivered"
        assert res_replay["idempotent"] is True

    def test_oversight_retry_blocks_terminal_and_suppressed(self, monkeypatch):
        """Oversight retry rejects retry on terminal_failure or suppressed follow-ups."""
        intro_suppressed = {
            "id": "intro_suppressed",
            "trainer_id": "t_retry_trainer",
            "delivery_state": "suppressed",
            "status": "suppressed",
        }
        fake_db = SimpleNamespace(
            intros=_MockCollection([intro_suppressed]),
            trainers=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        retry_payload = server.OversightFollowUpRetryIn(confirmed=True, notes="Attempt suppressed retry")

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                server.oversight_matching_follow_up_retry(
                    intro_id="intro_suppressed",
                    payload=retry_payload,
                )
            )
        assert exc.value.status_code == 409


# ==============================================================================
# MP-003: Urgent Provider Facts, Freshness Recheck and Review Gate
# ==============================================================================

class TestMP003UrgentProviderVerifiedFactsAndReviewGate:
    def test_official_lost_dogs_home_record_facts(self):
        """Lost Dogs' Home static record has verified official-source phone and hours."""
        ldh = next(
            (p for p in urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS if p["provider_id"] == "urgent_care_lost_dogs_home_north_melbourne"),
            None,
        )
        assert ldh is not None
        assert ldh["contact_method"] == "(03) 8379 4498"
        assert "8:10 am" in ldh["stated_hours"]
        assert "7:00 pm" in ldh["stated_hours"]
        assert "9:00 am – 4:00 pm" in ldh["stated_hours"]
        assert "not a 24/7 hospital" in ldh["stated_hours"]
        assert ldh["official_source_url"] == "https://vet.dogshome.com/"
        assert ldh["name"] == "The Lost Dogs' Home Veterinary Hospital"
        assert ldh["freshness_state"] == urgent_providers_service.FreshnessState.CURRENT.value
        assert "last_verified_at" in ldh

    def test_urgent_provider_freshness_recheck(self):
        """Records older than 90 days are marked stale; active provider filter excludes them."""
        fresh_record = {
            "provider_id": "fresh_1",
            "freshness_state": urgent_providers_service.FreshnessState.CURRENT.value,
            "last_verified_at": datetime.now(timezone.utc).isoformat(),
        }
        state, is_active = urgent_providers_service.compute_urgent_provider_freshness(fresh_record)
        assert state == urgent_providers_service.FreshnessState.CURRENT
        assert is_active is True

        stale_ts = (datetime.now(timezone.utc) - timedelta(days=95)).isoformat()
        stale_record = {
            "provider_id": "stale_1",
            "freshness_state": urgent_providers_service.FreshnessState.CURRENT.value,
            "last_verified_at": stale_ts,
        }
        state_stale, is_active_stale = urgent_providers_service.compute_urgent_provider_freshness(stale_record)
        assert state_stale == urgent_providers_service.FreshnessState.STALE
        assert is_active_stale is False

    def test_correction_review_requires_verified_official_source(self, monkeypatch):
        """Correction review cannot mark provider current without verified official-source URL."""
        corr = {
            "id": "corr_test_1",
            "provider_id": "urgent_test",
            "status": "pending",
            "field_name": "contact_method",
            "proposed_value": "0399998888",
        }
        prov = {
            "provider_id": "urgent_test",
            "name": "Test Vet",
            "contact_method": "0311112222",
            "freshness_state": "held",
        }
        fake_db = SimpleNamespace(
            urgent_provider_corrections=_MockCollection([corr]),
            urgent_providers=_MockCollection([prov]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # Unverified official source: fails
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                server.oversight_urgent_provider_correction_review(
                    correction_id="corr_test_1",
                    payload=server.OversightUrgentCorrectionReviewIn(
                        action="accept",
                        confirmed=True,
                        notes="Looks good",
                        verified_official_source=False,
                    ),
                )
            )
        assert exc.value.status_code == 400

        # Aggregator or social media source URL: fails
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                server.oversight_urgent_provider_correction_review(
                    correction_id="corr_test_1",
                    payload=server.OversightUrgentCorrectionReviewIn(
                        action="accept",
                        confirmed=True,
                        notes="Found on Facebook",
                        verified_official_source=True,
                        official_source_url="https://www.facebook.com/testvet",
                    ),
                )
            )
        assert exc.value.status_code == 400

        # Legitimate first-party verified source URL: succeeds
        res = asyncio.run(
            server.oversight_urgent_provider_correction_review(
                correction_id="corr_test_1",
                payload=server.OversightUrgentCorrectionReviewIn(
                    action="accept",
                    confirmed=True,
                    notes="Verified on clinic website contact page",
                    verified_official_source=True,
                    official_source_url="https://testvetclinic.com.au/contact",
                ),
            )
        )
        assert res["status"] == "accepted"
        assert prov["freshness_state"] == "current"


# ==============================================================================
# MP-004: Context Token Clearance and Direct /intros Boundary
# ==============================================================================

class TestMP004ContextTokenAndDirectIntrosBoundary:
    def test_direct_intros_rejects_client_supplied_match_id(self, monkeypatch):
        """Direct /intros endpoint must reject client-supplied match_id with HTTP 400."""
        trainer = {
            "id": "t_direct_test",
            "name": "Direct Trainer",
            "published": True,
            "region": "Greater Melbourne",
            "suburb": "Richmond",
        }
        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer]),
            intros=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        intro_payload = server.IntroIn(
            trainer_id="t_direct_test",
            description="Need help with puppy socialization",
            user_email="direct_user@example.com",
            user_name="Direct User",
            user_phone="0411222333",
            match_id="arbitrary_client_match_id_123",
            consent_contact_release=True,
            consent_outcome_tracking=True,
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                server.create_intro(
                    payload=intro_payload,
                    request=_make_dummy_request(),
                )
            )
        assert exc.value.status_code == 400
        assert "Direct enquiries cannot attach match_id" in exc.value.detail

    def test_direct_intros_without_match_id_succeeds_with_match_id_none(self, monkeypatch):
        """Direct /intros without match_id succeeds and sets match_id to None."""
        trainer = {
            "id": "t_direct_valid",
            "name": "Direct Valid Trainer",
            "published": True,
            "region": "Greater Melbourne",
            "suburb": "Richmond",
        }
        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer]),
            intros=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        intro_payload = server.IntroIn(
            trainer_id="t_direct_valid",
            description="Need help with puppy socialization",
            user_email="direct_user@example.com",
            user_name="Direct User",
            user_phone="0411222333",
            match_id=None,
            consent_contact_release=True,
            consent_outcome_tracking=True,
        )

        res = asyncio.run(
            server.create_intro(
                payload=intro_payload,
                request=_make_dummy_request(),
            )
        )
        assert res["trainer_id"] == "t_direct_valid"
        assert fake_db.intros.inserted[0]["match_id"] is None

    def test_follow_up_requires_valid_token_and_persists_match_id(self, monkeypatch):
        """Match follow-up endpoint requires valid X-Match-Context-Token and binds match_id."""
        raw_token, token_hash = matching_contract_v2.generate_match_context_token()
        ctx_doc = {
            "token_hash": token_hash,
            "match_id": "match_mp4_token_verified",
            "suburb_or_postcode": "Richmond",
            "dog_age_months": 12,
            "primary_concerns": ["basic_manners"],
            "service_format": "in_home",
        }
        trainer = make_test_trainer_doc(
            trainer_id="t_mp4_token",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
        )
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([ctx_doc]),
            trainers=_MockCollection([trainer]),
            intros=_MockCollection([]),
            match_events=_MockCollection([{"id": "match_mp4_token_verified", "campaign": "", "source": ""}]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_mp4_token",
            user_name="Jane Doe",
            user_email="jane@example.com",
            user_phone="0411222333",
            notes="Need help with leash pulling",
            consent_contact_release=True,
        )

        # Without token: raises 401
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                server.create_match_follow_up(
                    payload=payload,
                    request=_make_dummy_request(),
                    x_match_context_token=None,
                )
            )
        assert exc.value.status_code == 401

        # With valid token: persists match_id from context doc
        res = asyncio.run(
            server.create_match_follow_up(
                payload=payload,
                request=_make_dummy_request(),
                x_match_context_token=raw_token,
            )
        )
        assert res["match_id"] == "match_mp4_token_verified"
        assert fake_db.intros.inserted[0]["match_id"] == "match_mp4_token_verified"


# ==============================================================================
# MP-005: Config Fallback Contract
# ==============================================================================

class TestMP005ConfigFallbackContract:
    def test_get_config_contract(self, monkeypatch):
        """GET /api/config returns matching and launch configuration."""
        fake_db = SimpleNamespace(
            config=_MockCollection([]),
            suburbs=_MockCollection([{"name": "Richmond", "postcode": "3121"}]),
            trainers=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        cfg = asyncio.run(server.config())
        assert "public_matching_enabled" in cfg
        assert "public_launch_phase" in cfg
        assert "trainer_onboarding_open" in cfg
        assert "suburbs" in cfg
