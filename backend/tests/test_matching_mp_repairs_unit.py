"""Dedicated unit test suite covering the 5 repair blockers (MP-001 through MP-005).

Governed by:
- MATCHING_PIPELINE_P2_P6_INDEPENDENT_AUDIT_2026-10-04.md (Codex independent audit)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md
- AGENTS.md (Rule 6A, Evidence-first owner-assistance)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
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


import pymongo.errors


class _MockCollection:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, unique_fields: Optional[List[str]] = None):
        self.rows: List[Dict[str, Any]] = list(rows or [])
        self.inserted: List[Dict[str, Any]] = []
        self.unique_fields = unique_fields if unique_fields is not None else ["composite_idempotency_key", "idempotency_key"]

    def _match_doc(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        for k, v in query.items():
            if k == "$or":
                if not any(self._match_doc(doc, branch) for branch in v):
                    return False
            elif isinstance(v, dict):
                val = doc.get(k)
                if "$in" in v:
                    if val not in v["$in"]:
                        return False
                if "$lt" in v:
                    if val is None or val >= v["$lt"]:
                        return False
                if "$exists" in v:
                    exists = k in doc and doc[k] is not None
                    if exists != v["$exists"]:
                        return False
                if "$regex" in v:
                    import re
                    pattern = v["$regex"]
                    flags = re.IGNORECASE if v.get("$options") == "i" else 0
                    if not re.search(pattern, str(val or ""), flags):
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        res = list(self.rows) + list(self.inserted)
        if query:
            res = [r for r in res if self._match_doc(r, query)]
        return _MockCursor(res)

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None):
        for r in self.rows + self.inserted:
            if self._match_doc(r, query):
                return dict(r)
        return None

    async def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any], return_document: bool = True):
        for r in self.rows + self.inserted:
            if not self._match_doc(r, query):
                continue
            if "$set" in update:
                r.update(update["$set"])
            return dict(r)
        return None

    async def insert_one(self, doc: Dict[str, Any]):
        for ufield in self.unique_fields:
            if ufield in doc and doc[ufield] is not None:
                val = doc[ufield]
                for existing in self.rows + self.inserted:
                    if existing.get(ufield) == val:
                        raise pymongo.errors.DuplicateKeyError(f"Duplicate key on {ufield}: {val}")
        copy_doc = dict(doc)
        self.inserted.append(copy_doc)
        return SimpleNamespace(inserted_id="mock_id")

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        for r in self.rows + self.inserted:
            if self._match_doc(r, query):
                if "$set" in update:
                    r.update(update["$set"])
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)

    async def count_documents(self, query: Dict[str, Any]):
        items = self.rows + self.inserted
        if query:
            return len([r for r in items if self._match_doc(r, query)])
        return len(items)


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

        async def _mock_notify_ok(*args, **kwargs):
            return {"trainer_notification_status": "sent"}

        monkeypatch.setattr(notifications_service, "notify_trainer_new_intro", _mock_notify_ok)

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

        async def _mock_notify_ok(*args, **kwargs):
            return {"trainer_notification_status": "sent"}

        monkeypatch.setattr(notifications_service, "notify_trainer_new_intro", _mock_notify_ok)

        retry_payload = server.OversightFollowUpRetryIn(confirmed=True, notes="Operator test retry")

        # First retry call: dispatches and marks delivered
        res = asyncio.run(
            server.oversight_matching_follow_up_retry(
                intro_id="intro_retry_test",
                payload=retry_payload,
                request=_make_dummy_request(),
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
                request=_make_dummy_request(),
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
                    request=_make_dummy_request(),
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
            "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
            "provider_name": "The Lost Dogs' Home",
            "status": "pending",
            "field_name": "contact_method",
            "proposed_value": "0399998888",
        }
        prov = {
            "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
            "name": "The Lost Dogs' Home Veterinary Hospital",
            "official_source_url": "https://vet.dogshome.com/",
            "contact_method": "(03) 8379 4498",
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
                    request=_make_dummy_request("10.0.0.1"),
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
                        evidence_reference="Facebook Page",
                        reviewed_field_values={"contact_method": "0399998888"},
                    ),
                    request=_make_dummy_request("10.0.0.1"),
                )
            )
        assert exc.value.status_code == 400

        # Legitimate first-party verified source URL: succeeds
        corr["provider_id"] = "urgent_care_lost_dogs_home_north_melbourne"
        prov["provider_id"] = "urgent_care_lost_dogs_home_north_melbourne"
        prov["official_source_url"] = "https://vet.dogshome.com/"

        res = asyncio.run(
            server.oversight_urgent_provider_correction_review(
                correction_id="corr_test_1",
                payload=server.OversightUrgentCorrectionReviewIn(
                    action="accept",
                    confirmed=True,
                    notes="Verified on clinic website contact page",
                    verified_official_source=True,
                    official_source_url="https://vet.dogshome.com/",
                    evidence_reference="Official Vet Clinic Website Contact Page",
                    reviewed_field_values={"contact_method": "(03) 8379 4498"},
                ),
                request=_make_dummy_request("10.0.0.1"),
            )
        )
        assert res["status"] == "accepted"
        assert prov["freshness_state"] == "current"
        assert prov["verified_by"] == "ops:10.0.0.1"


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


# ==============================================================================
# MP-002R: Truthful Shared Delivery State Mapping
# ==============================================================================

class TestMP002R_SharedDeliveryStateMapper:
    """Refinement 5: Shared delivery-state mapper for direct and matched enquiries."""

    def test_missing_resend_api_key_maps_to_retryable_failure(self):
        state, fields = server.map_notification_delivery_state("pending", {
            "trainer_notification_status": "skipped",
            "trainer_notification_reason": "no_resend_api_key",
        })
        assert state == "retryable_failure"
        assert fields["delivery_state"] == "retryable_failure"
        assert fields["delivery_reason"] == "no_resend_api_key"

    def test_missing_recipient_email_maps_to_terminal_failure(self):
        state, fields = server.map_notification_delivery_state("pending", {
            "trainer_notification_status": "skipped",
            "trainer_notification_reason": "missing_email",
        })
        assert state == "terminal_failure"
        assert fields["delivery_state"] == "terminal_failure"
        assert fields["delivery_reason"] == "missing_email"

    def test_provider_acceptance_maps_to_delivered(self):
        state, fields = server.map_notification_delivery_state("pending", {
            "trainer_notification_status": "sent",
            "trainer_notification_id": "resend_123",
        })
        assert state == "delivered"
        assert fields["delivery_state"] == "delivered"
        assert fields["delivery_reason"] == "provider_accepted"

    def test_suppressed_initial_state_maps_to_suppressed(self):
        state, fields = server.map_notification_delivery_state("suppressed", None)
        assert state == "suppressed"
        assert fields["delivery_state"] == "suppressed"

    def test_direct_intro_maps_to_retryable_failure_when_resend_key_absent(self, monkeypatch):
        """Direct /intros endpoint produces retryable_failure when email provider is unconfigured."""
        trainer = {
            "id": "t_direct_nokey",
            "name": "Direct Trainer",
            "email": "trainer@example.com",
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
        monkeypatch.setenv("RESEND_API_KEY", "")

        intro_payload = server.IntroIn(
            trainer_id="t_direct_nokey",
            description="Need help with puppy socialization",
            user_email="direct_user@example.com",
            user_name="Direct User",
            user_phone="0411222333",
            match_id=None,
            consent_contact_release=True,
            consent_outcome_tracking=True,
        )

        res = asyncio.run(server.create_intro(intro_payload, request=_make_dummy_request()))
        assert res["delivery_status"] == "retryable_failure"
        assert fake_db.intros.inserted[0]["delivery_state"] == "retryable_failure"
        assert fake_db.intros.inserted[0]["delivery_reason"] == "no_resend_api_key"


# ==============================================================================
# MP-002S: Concurrency and Atomic Lease Recovery
# ==============================================================================

class TestMP002S_ConcurrencyAndLeaseRecovery:
    """Refinement 3: Concurrency protection, composite idempotency, and atomic lease recovery."""

    def test_duplicate_concurrent_submission_dispatches_once(self, monkeypatch):
        """Concurrent submissions for same match/trainer/user: exactly 1 outbound dispatch, 2nd gets idempotent True."""
        raw_token, token_hash = matching_contract_v2.generate_match_context_token()
        ctx_doc = {
            "token_hash": token_hash,
            "match_id": "match_concurrent_sub",
            "suburb_or_postcode": "Richmond",
            "dog_age_months": 12,
            "primary_concerns": ["basic_manners"],
            "service_format": "in_home",
        }
        trainer = make_test_trainer_doc(
            trainer_id="t_concurrent",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
        )
        trainer["email"] = "trainer@example.com"
        intros_coll = _MockCollection([])
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([ctx_doc]),
            trainers=_MockCollection([trainer]),
            intros=intros_coll,
            match_events=_MockCollection([{"id": "match_concurrent_sub", "campaign": "", "source": ""}]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        dispatch_count = 0
        async def _mock_notify(*args, **kwargs):
            nonlocal dispatch_count
            dispatch_count += 1
            return {"trainer_notification_status": "sent"}

        monkeypatch.setattr(notifications_service, "notify_trainer_new_intro", _mock_notify)

        payload = server.MatchFollowUpIn(
            trainer_id="t_concurrent",
            user_name="Jane Doe",
            user_email="jane@example.com",
            user_phone="0411222333",
            notes="Need help with leash pulling",
            consent_contact_release=True,
        )

        async def _run_concurrent():
            t1 = server.create_match_follow_up(
                payload=payload,
                request=_make_dummy_request(),
                x_match_context_token=raw_token,
            )
            t2 = server.create_match_follow_up(
                payload=payload,
                request=_make_dummy_request(),
                x_match_context_token=raw_token,
            )
            return await asyncio.gather(t1, t2)

        res1, res2 = asyncio.run(_run_concurrent())
        # Exactly one outbound dispatch
        assert dispatch_count == 1
        # Exactly one document persisted in intros
        assert len(intros_coll.inserted) == 1
        # One response was the initial insert, the other was idempotent replay
        idempotent_flags = [res1.get("idempotent"), res2.get("idempotent")]
        assert False in idempotent_flags
        assert True in idempotent_flags

    def test_concurrent_retry_only_one_claims_lease(self, monkeypatch):
        """Concurrent retry calls: exactly one claims the lease; the other gets HTTP 409."""
        intro_record = {
            "id": "intro_lease_concurrent",
            "match_id": "match_lease_concurrent",
            "trainer_id": "t_concurrent_retry",
            "trainer_name": "Concurrent Trainer",
            "user_name": "Alice",
            "user_email": "alice@example.com",
            "delivery_state": "retryable_failure",
            "status": "retryable_failure",
        }
        trainer_doc = {
            "id": "t_concurrent_retry",
            "name": "Concurrent Trainer",
            "email": "trainer@example.com",
            "published": True,
            "region": "Greater Melbourne",
            "suburb": "Richmond",
        }
        intros_coll = _MockCollection([intro_record])
        fake_db = SimpleNamespace(
            intros=intros_coll,
            trainers=_MockCollection([trainer_doc]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        retry_count = 0
        async def _mock_notify(*args, **kwargs):
            nonlocal retry_count
            retry_count += 1
            await asyncio.sleep(0.01)
            return {"trainer_notification_status": "sent"}

        monkeypatch.setattr(notifications_service, "notify_trainer_new_intro", _mock_notify)

        payload = server.OversightFollowUpRetryIn(confirmed=True, notes="Concurrent retry test")

        async def _run_concurrent():
            t1 = server.oversight_matching_follow_up_retry("intro_lease_concurrent", payload, request=_make_dummy_request("10.0.0.1"))
            t2 = server.oversight_matching_follow_up_retry("intro_lease_concurrent", payload, request=_make_dummy_request("10.0.0.2"))
            return await asyncio.gather(t1, t2, return_exceptions=True)

        results = asyncio.run(_run_concurrent())
        successes = [r for r in results if isinstance(r, dict) and r.get("ok")]
        conflicts = [r for r in results if isinstance(r, HTTPException) and r.status_code == 409]

        assert len(successes) == 1
        assert len(conflicts) == 1
        assert retry_count == 1

    def test_retry_lease_expiry_crash_recovery(self, monkeypatch):
        """Worker crash leaving in_progress with expired lease (>300s): re-claimed and retried successfully."""
        now_dt = datetime.now(timezone.utc)
        expired_claimed_at = (now_dt - timedelta(seconds=server.RETRY_LEASE_SECONDS + 60)).isoformat()
        intro_record = {
            "id": "intro_crash_recovery",
            "trainer_id": "t_recovery",
            "delivery_state": "in_progress",
            "status": "in_progress",
            "retry_claimed_at": expired_claimed_at,
            "retry_claimed_by": "ops:old_dead_worker",
        }
        trainer_doc = {
            "id": "t_recovery",
            "name": "Recovery Trainer",
            "email": "trainer@example.com",
            "published": True,
            "region": "Greater Melbourne",
            "suburb": "Richmond",
        }
        intros_coll = _MockCollection([intro_record])
        fake_db = SimpleNamespace(
            intros=intros_coll,
            trainers=_MockCollection([trainer_doc]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        async def _mock_notify(*args, **kwargs):
            return {"trainer_notification_status": "sent"}
        monkeypatch.setattr(notifications_service, "notify_trainer_new_intro", _mock_notify)

        payload = server.OversightFollowUpRetryIn(confirmed=True, notes="Crash recovery retry")
        res = asyncio.run(server.oversight_matching_follow_up_retry("intro_crash_recovery", payload, request=_make_dummy_request("10.0.0.5")))

        assert res["ok"] is True
        assert res["delivery_state"] == "delivered"
        assert intro_record["delivery_state"] == "delivered"
        assert intro_record["retry_claimed_at"] is None

    def test_retry_active_lease_rejected(self, monkeypatch):
        """Active lease (<300s) rejects concurrent retry attempt with HTTP 409."""
        now_dt = datetime.now(timezone.utc)
        active_claimed_at = (now_dt - timedelta(seconds=30)).isoformat()
        intro_record = {
            "id": "intro_active_lease",
            "trainer_id": "t_active",
            "delivery_state": "in_progress",
            "status": "in_progress",
            "retry_claimed_at": active_claimed_at,
            "retry_claimed_by": "ops:live_worker",
        }
        intros_coll = _MockCollection([intro_record])
        fake_db = SimpleNamespace(
            intros=intros_coll,
            trainers=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.OversightFollowUpRetryIn(confirmed=True, notes="Active lease test")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.oversight_matching_follow_up_retry("intro_active_lease", payload, request=_make_dummy_request("10.0.0.9")))

        assert exc.value.status_code == 409
        assert "Retry already in progress" in exc.value.detail


# ==============================================================================
# MP-003R: Urgent Locality Fallback
# ==============================================================================

class TestMP003R_UrgentLocalityAbsence:
    """Refinement 4: Explicit no_local_coverage state and notice when local coverage is absent."""

    def test_werribee_returns_no_local_coverage(self):
        """Locality without local coverage (Werribee) returns empty list and never falls back to North Melbourne."""
        fake_db = SimpleNamespace(
            urgent_providers=_MockCollection([]),
        )
        providers = asyncio.run(urgent_providers_service.get_active_urgent_providers(fake_db, suburb="Werribee"))
        assert providers == []

    def test_urgent_providers_api_no_local_coverage(self, monkeypatch):
        """GET /api/urgent-providers?suburb=Werribee returns explicit no_local_coverage and notice."""
        fake_db = SimpleNamespace(
            urgent_providers=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        res = asyncio.run(server.get_urgent_providers(suburb="Werribee"))
        assert res["coverage_state"] == "no_local_coverage"
        assert res["coverage_notice"] == "DTD has no current local listing for this area."
        assert res["urgent_providers"] == []

    def test_urgent_providers_api_local_coverage(self, monkeypatch):
        """GET /api/urgent-providers?suburb=Carlton returns local_coverage with matching provider."""
        fake_db = SimpleNamespace(
            urgent_providers=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        res = asyncio.run(server.get_urgent_providers(suburb="Carlton"))
        assert res["coverage_state"] == "local_coverage"
        assert res["coverage_notice"] is None
        assert len(res["urgent_providers"]) == 1
        assert res["urgent_providers"][0]["name"] == "The Lost Dogs' Home Veterinary Hospital"

    def test_match_triage_health_support_unserved_locality(self, monkeypatch):
        """POST /api/match triage for health emergency in unserved locality returns no_local_coverage and notice."""
        fake_db = SimpleNamespace(
            urgent_providers=_MockCollection([]),
            match_events=_MockCollection([]),
            trainers=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Werribee",
            behaviour_description="My dog ingested rat poison and is vomiting blood urgently.",
            primary_concerns=["basic_manners"],
        )
        res = asyncio.run(server.instant_match(req, request=_make_dummy_request()))
        assert res["decision_state"] == "urgent_animal_health_support"
        assert res["coverage_state"] == "no_local_coverage"
        assert res["coverage_notice"] == "DTD has no current local listing for this area."
        assert res["urgent_providers"] == []


# ==============================================================================
# MP-003S: Urgent Provider Reactivation Bounded Evidence Model
# ==============================================================================

class TestMP003S_UrgentProviderReactivationEvidenceModel:
    """Refinement 2: Bounded recorded evidence model with server-side operator identity."""

    def test_operator_identity_derived_from_request_ip(self, monkeypatch):
        """Operator identity is derived server-side from request, not accepted from body."""
        corr = {
            "id": "corr_ev_1",
            "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
            "status": "pending",
            "official_source_url": "https://vet.dogshome.com/",
        }
        prov = {
            "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
            "name": "The Lost Dogs' Home Veterinary Hospital",
            "official_source_url": "https://vet.dogshome.com/",
            "freshness_state": "held",
        }
        corrections_coll = _MockCollection([corr])
        providers_coll = _MockCollection([prov])
        audit_coll = _MockCollection([])
        fake_db = SimpleNamespace(
            urgent_provider_corrections=corrections_coll,
            urgent_providers=providers_coll,
            audit_log=audit_coll,
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.OversightUrgentCorrectionReviewIn(
            action="accept",
            confirmed=True,
            verified_official_source=True,
            official_source_url="https://vet.dogshome.com/",
            evidence_reference="Official Provider Contact Page and Hours Section",
            reviewed_field_values={"contact_method": "(03) 8379 4498"},
            notes="Verified against official website",
        )
        dummy_req = _make_dummy_request(client_host="192.168.1.50")
        res = asyncio.run(server.oversight_urgent_provider_correction_review("corr_ev_1", payload, request=dummy_req))

        assert res["ok"] is True
        assert res["status"] == "accepted"
        assert prov["verified_by"] == "ops:192.168.1.50"
        assert prov["evidence_reference"] == "Official Provider Contact Page and Hours Section"
        assert prov["freshness_state"] == "current"
        assert len(audit_coll.inserted) == 1
        assert audit_coll.inserted[0]["after"]["operator"] == "ops:192.168.1.50"

    def test_rejection_of_aggregators_and_social_media(self, monkeypatch):
        """Social media, maps links, and aggregators are rejected as official sources."""
        corr = {
            "id": "corr_ev_bad",
            "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
            "status": "pending",
        }
        fake_db = SimpleNamespace(
            urgent_provider_corrections=_MockCollection([corr]),
            urgent_providers=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        for bad_url in ["https://facebook.com/dogshome", "https://google.com/maps/place/dogshome", "https://www.truelocal.com.au/vet"]:
            payload = server.OversightUrgentCorrectionReviewIn(
                action="accept",
                confirmed=True,
                verified_official_source=True,
                official_source_url=bad_url,
                evidence_reference="Page 1",
                reviewed_field_values={"contact_method": "0383794498"},
            )
            with pytest.raises(HTTPException) as exc:
                asyncio.run(server.oversight_urgent_provider_correction_review("corr_ev_bad", payload, request=_make_dummy_request()))
            assert exc.value.status_code == 400
            assert "not permitted official sources" in exc.value.detail

    def test_rejection_of_unapproved_domain(self, monkeypatch):
        """Domain without approved provider relationship is rejected."""
        corr = {
            "id": "corr_ev_domain",
            "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
            "provider_name": "The Lost Dogs' Home",
            "status": "pending",
        }
        fake_db = SimpleNamespace(
            urgent_provider_corrections=_MockCollection([corr]),
            urgent_providers=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.OversightUrgentCorrectionReviewIn(
            action="accept",
            confirmed=True,
            verified_official_source=True,
            official_source_url="https://random-vet-blog.com/hours",
            evidence_reference="Blog Article Section 3",
            reviewed_field_values={"contact_method": "0383794498"},
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.oversight_urgent_provider_correction_review("corr_ev_domain", payload, request=_make_dummy_request()))
        assert exc.value.status_code == 400
        assert "does not have an approved first-party provider relationship" in exc.value.detail

    def test_rejection_of_missing_evidence_reference(self, monkeypatch):
        """Missing or short evidence_reference is rejected."""
        corr = {
            "id": "corr_ev_no_ref",
            "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
            "status": "pending",
        }
        fake_db = SimpleNamespace(
            urgent_provider_corrections=_MockCollection([corr]),
            urgent_providers=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.OversightUrgentCorrectionReviewIn(
            action="accept",
            confirmed=True,
            verified_official_source=True,
            official_source_url="https://vet.dogshome.com/",
            evidence_reference="",
            reviewed_field_values={"contact_method": "0383794498"},
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.oversight_urgent_provider_correction_review("corr_ev_no_ref", payload, request=_make_dummy_request()))
        assert exc.value.status_code == 400
        assert "evidence reference is required" in exc.value.detail


# ==============================================================================
# MP-003T: Ops Read-Model Freshness Recheck
# ==============================================================================

class TestMP003T_OpsReadModelFreshnessRecheck:
    """Refinement / MP-003T: Dynamic freshness recheck in /ops matching read model."""

    def test_ops_read_model_rechecks_provider_freshness(self, monkeypatch):
        stale_ts = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        db_provider = {
            "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
            "name": "The Lost Dogs' Home Veterinary Hospital",
            "category": "urgent_veterinary_care",
            "freshness_state": "current",
            "last_verified_at": stale_ts,
            "service_area": ["North Melbourne", "Flemington"],
            "official_source_url": "https://vet.dogshome.com/",
        }
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            intros=_MockCollection([]),
            urgent_providers=_MockCollection([db_provider]),
            urgent_provider_corrections=_MockCollection([]),
            ai_degradation_events=_MockCollection([]),
            audit_log=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        read_model = asyncio.run(server.build_matching_oversight_read_model(fake_db))
        prov_status = read_model["urgent_provider_status"]
        assert prov_status["stale_records"] >= 1
        assert prov_status["current_records"] == 0
        assert prov_status["has_local_coverage"] is False


# ==============================================================================
# MP-005R: Public Copy Neutrality
# ==============================================================================

class TestMP005R_PublicCopyNeutrality:
    """Refinement 1: Public trust copy neutrality - no universal unsupported verified/reviewed claims."""

    def test_frontend_public_pages_do_not_contain_universal_verified_or_reviewed_claims(self):
        frontend_src = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages"
        pages_to_check = ["Home.jsx", "About.jsx", "HowItWorks.jsx", "Trust.jsx", "Terms.jsx", "FAQ.jsx"]

        disallowed_phrases = [
            "verified trainers",
            "every trainer is reviewed",
            "reviewed local directory",
            "reviewed trainers",
            "verified local profiles",
            "verified profiles only",
            "verified, independent dog trainers",
            "verified dog trainers",
            "every trainer is manually verified",
        ]

        for page in pages_to_check:
            page_path = frontend_src / page
            if not page_path.exists():
                continue
            content = page_path.read_text(encoding="utf-8").lower()
            for phrase in disallowed_phrases:
                assert phrase not in content, f"Disallowed phrase '{phrase}' found in {page}"
