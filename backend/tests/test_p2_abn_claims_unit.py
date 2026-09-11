from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests
from fastapi import HTTPException

import server
from services import claim_engine
from services.abn_validator import (
    format_abn,
    normalize_abn,
    validate_abn_checksum,
    validate_abn_detailed,
)
from services.abr_client import AbrClient


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, size):
        self.rows = self.rows[:size]
        return self

    async def to_list(self, _size):
        return list(self.rows)


class _Collection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.inserted = []

    @staticmethod
    def _matches(row, filt):
        for key, expected in (filt or {}).items():
            actual = row.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$nin" in expected and actual in expected["$nin"]:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, filt=None, *_args, **_kwargs):
        return next((row for row in self.rows if self._matches(row, filt)), None)

    def find(self, filt=None, *_args, **_kwargs):
        return _Cursor([row for row in self.rows if self._matches(row, filt)])

    async def insert_one(self, doc):
        self.inserted.append(doc)
        self.rows.append(doc)

    async def update_one(self, filt, update, upsert=False):
        row = await self.find_one(filt)
        if row is None and upsert:
            row = dict(filt)
            self.rows.append(row)
        if row is not None:
            row.update(update.get("$set", {}))
            for key, value in update.get("$inc", {}).items():
                row[key] = int(row.get(key) or 0) + value
        return SimpleNamespace(matched_count=1 if row else 0)

    async def update_many(self, filt, update):
        count = 0
        for row in self.rows:
            if self._matches(row, filt):
                row.update(update.get("$set", {}))
                count += 1
        return SimpleNamespace(matched_count=count)

    async def delete_one(self, filt):
        row = await self.find_one(filt)
        if row is not None:
            self.rows.remove(row)
            return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    async def count_documents(self, filt=None):
        return len([row for row in self.rows if self._matches(row, filt)])

    async def create_index(self, *args, **kwargs):
        return "mock_index"


def _fake_p2_db(trainer=None):
    trainers = [trainer] if trainer else []
    return SimpleNamespace(
        trainers=_Collection(trainers),
        claim_events=_Collection(),
        abn_cache=_Collection(),
        notification_events=_Collection(),
        audit_log=_Collection(),
        submissions=_Collection(),
        discovery_queue=_Collection(),
    )


# ---------------------------------------------------------------------------
# 1. ATO Modulus 89 Validation Tests
# ---------------------------------------------------------------------------


def test_ato_modulus_89_valid_vectors():
    # Valid Australian Business Numbers
    assert validate_abn_checksum("51 824 753 556") is True
    assert validate_abn_checksum("10 000 000 032") is True
    assert validate_abn_checksum("53 004 085 616") is True
    assert validate_abn_checksum("33 051 775 556") is True


def test_ato_modulus_89_invalid_checksums():
    # Last digit mutated
    assert validate_abn_checksum("51 824 753 557") is False
    assert validate_abn_checksum("10 000 000 033") is False
    assert validate_abn_checksum("00 000 000 000") is False


def test_ato_modulus_89_normalization_and_formatting():
    assert normalize_abn(" 51-824-753-556 ") == "51824753556"
    assert format_abn("51824753556") == "51 824 753 556"
    assert format_abn("123") == "123"


def test_validate_abn_detailed():
    assert validate_abn_detailed("")["code"] == "empty"
    assert validate_abn_detailed("abc")["code"] == "no_digits"
    assert validate_abn_detailed("12345")["code"] == "invalid_length"
    assert validate_abn_detailed("51 824 753 557")["code"] == "checksum_failed"
    valid = validate_abn_detailed("51 824 753 556")
    assert valid["valid"] is True
    assert valid["code"] == "valid"
    assert valid["formatted"] == "51 824 753 556"


# ---------------------------------------------------------------------------
# 2. ABR Client Lookup, Degraded States & 30-day Caching
# ---------------------------------------------------------------------------


def test_abr_lookup_invalid_checksum_rejected_locally():
    fake_db = _fake_p2_db()
    client = AbrClient(fake_db, guid="any-guid")
    result = asyncio.run(client.lookup("12345678901"))
    assert result["ok"] is False
    assert result["state"] == "invalid_checksum"
    assert result["reason_code"] == "invalid_checksum"
    assert result["abn_verified"] is False


def test_abr_lookup_missing_guid_is_explicitly_degraded(monkeypatch):
    fake_db = _fake_p2_db()
    monkeypatch.delenv("ABR_GUID", raising=False)
    client = AbrClient(fake_db, guid="")
    result = asyncio.run(client.lookup("51 824 753 556"))
    assert result["ok"] is False
    assert result["state"] == "abr_unavailable"
    assert result["reason_code"] == "abr_guid_missing"
    assert result["abn_verified"] is False
    assert "ABR_GUID is not configured" in result["reason"]


def test_abr_lookup_network_error_returns_degraded(monkeypatch):
    fake_db = _fake_p2_db()

    def _fail_get(*_args, **_kwargs):
        raise requests.ConnectionError("Connection timeout")

    monkeypatch.setattr("services.abr_client.requests.get", _fail_get)
    client = AbrClient(fake_db, guid="test-guid")
    result = asyncio.run(client.lookup("51 824 753 556"))
    assert result["ok"] is False
    assert result["state"] == "abr_unavailable"
    assert result["reason_code"] == "abr_network_error"
    assert result["abn_verified"] is False


def test_abr_lookup_maintenance_returns_degraded(monkeypatch):
    fake_db = _fake_p2_db()
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    monkeypatch.setattr("services.abr_client.requests.get", lambda *_args, **_kwargs: mock_resp)
    client = AbrClient(fake_db, guid="test-guid")
    result = asyncio.run(client.lookup("51 824 753 556"))
    assert result["ok"] is False
    assert result["state"] == "abr_unavailable"
    assert result["reason_code"] == "abr_maintenance"
    assert result["abn_verified"] is False


def test_abr_lookup_success_writes_cache_with_ttl(monkeypatch):
    fake_db = _fake_p2_db()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = 'callback({"Abn": "51824753556", "AbnStatus": "Active", "EntityName": "AUSTRALIAN TAXATION OFFICE", "BusinessName": ["ATO DIRECT"], "EntityTypeName": "Commonwealth Government Entity", "AddressState": "ACT", "AddressPostcode": "2600", "Gst": "2000-07-01"});'
    monkeypatch.setattr("services.abr_client.requests.get", lambda *_args, **_kwargs: mock_resp)

    client = AbrClient(fake_db, guid="valid-guid", ttl_s=30 * 86400)
    result = asyncio.run(client.lookup("51 824 753 556"))
    assert result["ok"] is True
    assert result["state"] == "active"
    assert result["abn_verified"] is True
    assert result["data"]["entity_name"] == "AUSTRALIAN TAXATION OFFICE"
    assert result["data"]["trading_name"] == "ATO DIRECT"
    assert result["data"]["business_type"] == "Commonwealth Government Entity"

    # Check cache write
    cached_doc = fake_db.abn_cache.rows[0]
    assert cached_doc["abn"] == "51824753556"
    assert cached_doc["record"]["entity_name"] == "AUSTRALIAN TAXATION OFFICE"
    assert "expires_at" in cached_doc


def test_abr_cache_hit_avoids_network(monkeypatch):
    fake_db = _fake_p2_db()
    fake_db.abn_cache.rows.append(
        {
            "abn": "51824753556",
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "record": {
                "abn": "51824753556",
                "entity_name": "CACHED ENTITY",
                "trading_name": "CACHED TRADING",
                "abn_status": "Active",
                "is_active": True,
            },
        }
    )
    client = AbrClient(fake_db, guid="configured-guid")
    monkeypatch.setattr("services.abr_client.requests.get", lambda *_args, **_kwargs: pytest.fail("network must not be called"))
    result = asyncio.run(client.lookup("51 824 753 556"))
    assert result["ok"] is True
    assert result["cached"] is True
    assert result["data"]["entity_name"] == "CACHED ENTITY"
    assert result["abn_verified"] is True


# ---------------------------------------------------------------------------
# 3. Submissions & Newly Created Trainers Schema Expansion
# ---------------------------------------------------------------------------


def test_submission_and_trainer_creation_persists_expanded_profile_fields(monkeypatch):
    fake_db = _fake_p2_db()
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("ABR_GUID", "test-guid")

    # Mock AbrClient to return active entity
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = 'callback({"Abn": "51824753556", "AbnStatus": "Active", "EntityName": "CANINE MASTERS PTY LTD", "BusinessName": ["MELBOURNE K9"], "EntityTypeName": "Australian Private Company", "AddressState": "VIC", "AddressPostcode": "3000"});'
    monkeypatch.setattr("services.abr_client.requests.get", lambda *_args, **_kwargs: mock_resp)

    async def _mock_score(_payload):
        return {"confidence": 0.95, "reasoning": "verified", "signals": [], "model": "test"}

    async def _mock_billing(*_args, **_kwargs):
        return {"billing_profile_status": "ready"}

    async def _mock_notif(*_args, **_kwargs):
        return {"submitter_notification_status": "sent", "submitter_notification_attempts": 1}

    monkeypatch.setattr(server.ai_service, "score_trainer", _mock_score)
    monkeypatch.setattr(server.stripe_billing, "provision_trainer_billing_profile", _mock_billing)
    monkeypatch.setattr(server.notifications_service, "notify_submitter_result", _mock_notif)

    payload = server.SubmissionIn(
        name="Canine Masters",
        suburb="Richmond",
        region="Greater Melbourne",
        email="contact@caninemasters.com.au",
        phone="0400000000",
        website="https://caninemasters.com.au",
        abn="51 824 753 556",
        training_philosophy="Positive reinforcement with evidence-led boundaries",
        specialties=["Puppy Training", "Behaviour Modification"],
        service_formats=["1-on-1 Private", "Group Classes"],
        serviced_suburbs=["Richmond", "Cremorne", "Burnley"],
        catchment_type="Travel within 15km",
        booking_url="https://caninemasters.com.au/book",
        gallery_images=["https://images.example.com/k9-1.jpg", "https://images.example.com/k9-2.jpg"],
        sponsored_suburbs=["Richmond"],
        review_summary="5.0 stars across 45 verified reviews",
        consent_public_listing=True,
        consent_information_accuracy=True,
        tier="claimed",  # Submitter tries to self-assert claimed
        claim_status="claimed",  # Submitter tries to self-assert claimed
    )

    result = asyncio.run(server.create_submission(payload))
    trainer_id = result["trainer_id"]
    trainer = next(row for row in fake_db.trainers.rows if row["id"] == trainer_id)

    # Must NOT allow self-asserted claim or tier
    assert trainer["tier"] == "unclaimed"
    assert trainer["claim_status"] == "unclaimed"

    # Expanded profile fields must be populated
    assert trainer["abn"] == "51824753556"
    assert trainer["entity_name"] == "CANINE MASTERS PTY LTD"
    assert trainer["trading_name"] == "MELBOURNE K9"
    assert trainer["business_type"] == "Australian Private Company"
    assert trainer["abn_status"] == "active"
    assert trainer["abn_verified"] is True
    assert trainer["training_philosophy"] == "Positive reinforcement with evidence-led boundaries"
    assert trainer["specialties"] == ["Puppy Training", "Behaviour Modification"]
    assert trainer["service_formats"] == ["1-on-1 Private", "Group Classes"]
    assert trainer["serviced_suburbs"] == ["Richmond", "Cremorne", "Burnley"]
    assert trainer["catchment_type"] == "Travel within 15km"
    assert trainer["booking_url"] == "https://caninemasters.com.au/book"
    assert trainer["gallery_images"] == ["https://images.example.com/k9-1.jpg", "https://images.example.com/k9-2.jpg"]
    assert trainer["sponsored_suburbs"] == ["Richmond"]
    assert trainer["review_summary"] == "5.0 stars across 45 verified reviews"
    assert trainer["abn_badge_payload"]["status"] == "Active"


# ---------------------------------------------------------------------------
# 4. POST /api/trainers/{id}/claim Endpoint
# ---------------------------------------------------------------------------


def test_claim_endpoint_with_email_success(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "unclaimed",
        "tier": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")
    monkeypatch.setattr(claim_engine, "generate_otp", lambda: "654321")

    async def _mock_send(_db, _trainer, *, to_email, otp):
        return {"claim_notification_status": "sent", "claim_notification_attempts": 1}

    monkeypatch.setattr(server.notifications_service, "notify_trainer_claim_otp", _mock_send)

    payload = server.TrainerClaimStartIn(email="trainer@melbournedog.com.au", method="email")
    response = asyncio.run(server.start_trainer_claim("tr_1", payload))

    assert response["status"] == "pending_verification"
    assert response["masked_destination"] == "t***@melbournedog.com.au"
    assert "654321" not in str(response)

    # Check db.claim_events: raw OTP is never stored, only keyed HMAC digest
    event = fake_db.claim_events.rows[0]
    assert event["status"] == "pending_verification"
    assert event["otp_digest"] == claim_engine.otp_digest("654321", secret="secret-key")
    assert "654321" not in event.values()
    assert event["max_attempts"] == 5

    # Check trainer claim_status updated
    assert trainer["claim_status"] == "pending_verification"


def test_claim_endpoint_with_sms_returns_503_degraded(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)

    payload = server.TrainerClaimStartIn(email="trainer@melbournedog.com.au", method="sms")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("tr_1", payload))

    assert exc.value.status_code == 503
    assert "SMS/phone claim verification is not available yet" in exc.value.detail
    event = fake_db.claim_events.rows[0]
    assert event["status"] == "provider_unavailable"


def test_claim_endpoint_mismatched_email_returns_403(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "listed@melbournedog.com.au",
        "claim_status": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)

    payload = server.TrainerClaimStartIn(email="other@melbournedog.com.au", method="email")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("tr_1", payload))

    assert exc.value.status_code == 403
    assert "Use the email address currently recorded" in exc.value.detail


def test_claim_endpoint_repeat_claimant_on_claimed_profile_returns_409_and_leaves_claimed(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "claimed",
        "tier": "claimed",
        "claimed_at": "2026-09-01T00:00:00Z",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)

    payload = server.TrainerClaimStartIn(email="trainer@melbournedog.com.au", method="email")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("tr_1", payload))

    assert exc.value.status_code == 409
    assert "already" in exc.value.detail.lower()
    assert trainer["claim_status"] == "claimed"
    assert trainer["tier"] == "claimed"
    assert trainer["claimed_at"] == "2026-09-01T00:00:00Z"
    assert len(fake_db.claim_events.rows) == 0


def test_arbitrary_email_against_claimed_profile_returns_409_and_leaves_profile_claimed(monkeypatch):
    trainer = {
        "id": "tr_claimed_arbitrary",
        "name": "Melbourne Dog Training",
        "email": "owner@melbournedog.com.au",
        "claim_status": "claimed",
        "tier": "claimed",
        "claimed_at": "2026-09-01T12:00:00Z",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)

    payload = server.TrainerClaimStartIn(email="attacker@randomdomain.com", method="email")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("tr_claimed_arbitrary", payload))

    assert exc.value.status_code == 409
    assert "already" in exc.value.detail.lower()
    assert trainer["claim_status"] == "claimed"
    assert trainer["tier"] == "claimed"
    assert trainer["claimed_at"] == "2026-09-01T12:00:00Z"
    assert len(fake_db.claim_events.rows) == 0


def test_arbitrary_email_against_disputed_profile_leaves_it_disputed(monkeypatch):
    trainer = {
        "id": "tr_disputed_arbitrary",
        "name": "Melbourne Dog Training",
        "email": "owner@melbournedog.com.au",
        "claim_status": "claim_disputed",
        "tier": "claimed",
        "claimed_at": "2026-09-01T12:00:00Z",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)

    payload = server.TrainerClaimStartIn(email="attacker@randomdomain.com", method="email")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("tr_disputed_arbitrary", payload))

    assert exc.value.status_code == 409
    assert trainer["claim_status"] == "claim_disputed"
    assert trainer["tier"] == "claimed"
    assert trainer["claimed_at"] == "2026-09-01T12:00:00Z"
    assert len(fake_db.claim_events.rows) == 0


def test_verify_endpoint_rejects_verification_on_disputed_profile(monkeypatch):
    trainer = {
        "id": "tr_disputed_verify",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "claim_disputed",
        "tier": "claimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    event_id = "evt_pending_on_disputed"
    fake_db.claim_events.rows.append(
        {
            "id": event_id,
            "trainer_id": "tr_disputed_verify",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("123456"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("tr_disputed_verify", server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="123456")))

    assert exc.value.status_code == 409
    assert "ownership dispute" in exc.value.detail.lower()
    assert trainer["claim_status"] == "claim_disputed"
    assert fake_db.claim_events.rows[0]["status"] == "stale"


def test_stale_verification_after_another_claim_succeeds_cannot_issue_session_or_alter_profile(monkeypatch):
    trainer = {
        "id": "tr_already_claimed",
        "name": "Melbourne Dog Training",
        "email": "legit_owner@melbournedog.com.au",
        "claim_status": "claimed",
        "tier": "claimed",
        "claimed_at": "2026-09-01T12:00:00Z",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")

    event_id = "evt_stale_challenge"
    fake_db.claim_events.rows.append(
        {
            "id": event_id,
            "trainer_id": "tr_already_claimed",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("654321", secret="secret-key"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )

    payload = server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="654321")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("tr_already_claimed", payload))

    assert exc.value.status_code == 409
    assert "already been claimed" in exc.value.detail.lower()
    assert trainer["claim_status"] == "claimed"
    assert trainer["tier"] == "claimed"
    assert trainer["claimed_at"] == "2026-09-01T12:00:00Z"
    stale_event = next(e for e in fake_db.claim_events.rows if e["id"] == event_id)
    assert stale_event["status"] == "stale"


def test_no_arbitrary_claim_request_creates_high_severity_ops_dispute_case(monkeypatch):
    trainer = {
        "id": "tr_safe_ops",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "claimed",
        "tier": "claimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)

    payload = server.TrainerClaimStartIn(email="unauthorized@attacker.org", method="email")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("tr_safe_ops", payload))

    assert exc.value.status_code == 409

    ops_cases = asyncio.run(
        server._ops_case_rows(
            discovery_summary={},
            waitlist_summary={},
            loop_statuses={},
            claim_cases=fake_db.claim_events.rows,
            abn_degradation_cases=[],
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=[],
        )
    )
    high_dispute_cases = [
        c for c in ops_cases
        if c.get("case_type") == "trainer_claim_case" and c.get("severity") == "high" and "claim_disputed" in c.get("risk_reason_codes", [])
    ]
    assert len(high_dispute_cases) == 0


# ---------------------------------------------------------------------------
# 5. POST /api/trainers/{id}/verify (and /claim/verify) Endpoint
# ---------------------------------------------------------------------------


def test_verify_endpoint_success_sets_claimed_and_issues_session(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "pending_verification",
        "tier": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "action-secret")

    event_id = "evt_claim_123"
    fake_db.claim_events.rows.append(
        {
            "id": event_id,
            "trainer_id": "tr_1",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("987654", secret="secret-key"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )

    payload = server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="987654")
    # Verify using the /verify endpoint
    response = asyncio.run(server.verify_trainer_claim("tr_1", payload))

    assert response["ok"] is True
    assert response["claim_status"] == "claimed"
    assert response["tier"] == "claimed"
    assert trainer["claim_status"] == "claimed"
    assert trainer["tier"] == "claimed"
    assert fake_db.claim_events.rows[0]["status"] == "verified"
    assert "session" in response
    assert response["session"]["token"]


def test_verify_endpoint_rejects_a_claim_race_without_issuing_a_session(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "pending_verification",
        "tier": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")
    event_id = "evt_claim_race"
    fake_db.claim_events.rows.append(
        {
            "id": event_id,
            "trainer_id": "tr_1",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("987654", secret="secret-key"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )

    original_update_one = fake_db.trainers.update_one

    async def _lost_claim_race(filt, update, upsert=False):
        if update.get("$set", {}).get("claim_status") == "claimed":
            return SimpleNamespace(matched_count=0)
        return await original_update_one(filt, update, upsert=upsert)

    monkeypatch.setattr(fake_db.trainers, "update_one", _lost_claim_race)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("tr_1", server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="987654")))

    assert exc.value.status_code == 409
    assert trainer["claim_status"] == "pending_verification"
    assert fake_db.claim_events.rows[0]["status"] == "stale"



def test_verify_endpoint_invalid_code_does_not_alter_trainer(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "pending_verification",
        "tier": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")

    event_id = "evt_claim_123"
    fake_db.claim_events.rows.append(
        {
            "id": event_id,
            "trainer_id": "tr_1",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("987654", secret="secret-key"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )

    payload = server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="000000")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("tr_1", payload))

    assert exc.value.status_code == 400
    assert trainer["claim_status"] == "pending_verification"
    assert trainer["tier"] == "unclaimed"
    assert fake_db.claim_events.rows[0]["attempts"] == 1
    assert fake_db.claim_events.rows[0]["status"] == "pending_verification"


def test_verify_endpoint_locks_after_five_failed_attempts(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "pending_verification",
        "tier": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")

    event_id = "evt_claim_123"
    fake_db.claim_events.rows.append(
        {
            "id": event_id,
            "trainer_id": "tr_1",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("987654", secret="secret-key"),
            "attempts": 4,  # 4 previous failed attempts
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )

    payload = server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="000000")
    # 5th failed attempt triggers lock and returns 429
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("tr_1", payload))

    assert exc.value.status_code == 429
    assert "locked" in exc.value.detail.lower()
    assert fake_db.claim_events.rows[0]["status"] == "locked"
    assert fake_db.claim_events.rows[0]["attempts"] == 5
    assert trainer["claim_status"] == "pending_verification"


def test_verify_endpoint_expired_code_returns_410(monkeypatch):
    trainer = {
        "id": "tr_1",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "pending_verification",
        "tier": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")

    event_id = "evt_claim_123"
    fake_db.claim_events.rows.append(
        {
            "id": event_id,
            "trainer_id": "tr_1",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("987654", secret="secret-key"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(),
        }
    )

    payload = server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="987654")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("tr_1", payload))

    assert exc.value.status_code == 410
    assert "expired" in exc.value.detail.lower()
    assert fake_db.claim_events.rows[0]["status"] == "expired"
    assert trainer["claim_status"] == "pending_verification"


# ---------------------------------------------------------------------------
# 6. Ops Cases for Claim Lifecycle & ABR Degradation
# ---------------------------------------------------------------------------


def test_ops_cases_surface_all_claim_and_abr_states():
    claim_cases = [
        {"id": "c1", "trainer_id": "tr1", "status": "pending_verification", "created_at": "2026-09-09T00:00:00Z"},
        {"id": "c2", "trainer_id": "tr2", "status": "delivery_failed", "delivery_error": "resend_error", "created_at": "2026-09-09T00:00:00Z"},
        {"id": "c3", "trainer_id": "tr3", "status": "expired", "created_at": "2026-09-09T00:00:00Z"},
        {"id": "c4", "trainer_id": "tr4", "status": "locked", "created_at": "2026-09-09T00:00:00Z"},
        {"id": "c5", "trainer_id": "tr5", "status": "claim_disputed", "reason": "profile_already_claimed", "created_at": "2026-09-09T00:00:00Z"},
    ]
    abn_degradation_cases = [
        {"id": "abr1", "name": "ABR Web Services", "abn_status": "abr_guid_missing", "abn_verification_reason": "ABR_GUID missing", "created_at": "2026-09-09T00:00:00Z"},
    ]

    cases = asyncio.run(
        server._ops_case_rows(
            discovery_summary={},
            waitlist_summary={},
            loop_statuses={},
            claim_cases=claim_cases,
            abn_degradation_cases=abn_degradation_cases,
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=[],
        )
    )

    case_ids = {c["case_id"] for c in cases}
    assert "trainer_claim:c1" in case_ids
    assert "trainer_claim:c2" in case_ids
    assert "trainer_claim:c3" in case_ids
    assert "trainer_claim:c4" in case_ids
    assert "trainer_claim:c5" in case_ids
    assert "abn_verification:abr1" in case_ids

    c5_case = next(c for c in cases if c["case_id"] == "trainer_claim:c5")
    assert c5_case["severity"] == "high"
    labels = {r["label"]: r["value"] for r in c5_case["detail_rows"]}
    assert labels["Claim status"] == "claim_disputed"
    assert labels["Profile ownership state"] == "claim_disputed"



# ---------------------------------------------------------------------------
# 7. Replay, Resend Rate Limit, Delivery Rollback & Deduplication
# ---------------------------------------------------------------------------


def test_verify_endpoint_rejects_replay(monkeypatch):
    trainer = {
        "id": "tr_replay",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "pending_verification",
        "tier": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "action-secret")

    event_id = "evt_claim_replay"
    fake_db.claim_events.rows.append(
        {
            "id": event_id,
            "trainer_id": "tr_replay",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("987654", secret="secret-key"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )

    payload = server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="987654")
    # First verification succeeds
    res1 = asyncio.run(server.verify_trainer_claim("tr_replay", payload))
    assert res1["ok"] is True
    assert trainer["claim_status"] == "claimed"
    assert fake_db.claim_events.rows[0]["status"] == "verified"

    # Second verification with exact same payload must be rejected as replay
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("tr_replay", payload))
    assert exc.value.status_code == 409
    assert "not available for verification" in exc.value.detail.lower()


def test_claim_resend_rate_limit_cooldown(monkeypatch):
    trainer = {
        "id": "tr_cooldown",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")
    monkeypatch.setattr(server, "TRAINER_CLAIM_RESEND_COOLDOWN_S", 60)

    async def _mock_send(_db, _trainer, *, to_email, otp):
        return {"claim_notification_status": "sent", "claim_notification_attempts": 1}

    monkeypatch.setattr(server.notifications_service, "notify_trainer_claim_otp", _mock_send)

    payload = server.TrainerClaimStartIn(email="trainer@melbournedog.com.au", method="email")
    # First dispatch succeeds
    res1 = asyncio.run(server.start_trainer_claim("tr_cooldown", payload))
    assert res1["status"] == "pending_verification"

    # Immediate second dispatch within 60s cooldown must return 429
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("tr_cooldown", payload))
    assert exc.value.status_code == 429
    assert "please wait" in exc.value.detail.lower()

    # Rate-limited event must be recorded and visible in /ops
    rate_events = [r for r in fake_db.claim_events.rows if r["status"] == "rate_limited"]
    assert len(rate_events) == 1
    assert rate_events[0]["reason"] == "resend_cooldown_active"

    cases = asyncio.run(
        server._ops_case_rows(
            discovery_summary={},
            waitlist_summary={},
            loop_statuses={},
            claim_cases=fake_db.claim_events.rows,
            abn_degradation_cases=[],
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=[],
        )
    )
    assert any(c["case_type"] == "trainer_claim_case" and "rate limited" in c["title"].lower() for c in cases)


def test_claim_resend_after_cooldown_supersedes_prior_challenge(monkeypatch):
    trainer = {
        "id": "tr_supersede",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "pending_verification",
    }
    fake_db = _fake_p2_db(trainer)
    # Prior challenge created 120 seconds ago
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    fake_db.claim_events.rows.append(
        {
            "id": "old_challenge",
            "trainer_id": "tr_supersede",
            "status": "pending_verification",
            "created_at": old_time,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=13)).isoformat(),
        }
    )
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")
    monkeypatch.setattr(server, "TRAINER_CLAIM_RESEND_COOLDOWN_S", 60)

    async def _mock_send(_db, _trainer, *, to_email, otp):
        return {"claim_notification_status": "sent", "claim_notification_attempts": 1}

    monkeypatch.setattr(server.notifications_service, "notify_trainer_claim_otp", _mock_send)

    payload = server.TrainerClaimStartIn(email="trainer@melbournedog.com.au", method="email")
    res = asyncio.run(server.start_trainer_claim("tr_supersede", payload))
    assert res["status"] == "pending_verification"

    # Old challenge must now be superseded
    old_evt = next(r for r in fake_db.claim_events.rows if r["id"] == "old_challenge")
    assert old_evt["status"] == "superseded"


def test_claim_delivery_failure_reverts_trainer_to_unclaimed(monkeypatch):
    trainer = {
        "id": "tr_delivery_fail",
        "name": "Melbourne Dog Training",
        "email": "trainer@melbournedog.com.au",
        "claim_status": "unclaimed",
    }
    fake_db = _fake_p2_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "secret-key")
    monkeypatch.setattr(server, "TRAINER_CLAIM_RESEND_COOLDOWN_S", 0)

    async def _mock_failed_send(_db, _trainer, *, to_email, otp):
        return {"claim_notification_status": "failed", "claim_notification_error": "resend_api_down"}

    monkeypatch.setattr(server.notifications_service, "notify_trainer_claim_otp", _mock_send_fail if "_mock_send_fail" in dir() else _mock_failed_send)

    payload = server.TrainerClaimStartIn(email="trainer@melbournedog.com.au", method="email")
    res = asyncio.run(server.start_trainer_claim("tr_delivery_fail", payload))
    assert res["status"] == "delivery_failed"
    assert res["delivery_status"] == "failed"
    # Trainer must revert to unclaimed so profile is not stuck in pending
    assert trainer["claim_status"] == "unclaimed"
    # Claim event is recorded as delivery_failed
    assert fake_db.claim_events.rows[0]["status"] == "delivery_failed"


def test_submission_with_already_claimed_abn_creates_held_dispute(monkeypatch):
    existing_claimed_trainer = {
        "id": "tr_existing_claimed",
        "name": "Original K9 Academy",
        "email": "owner@originalk9.com.au",
        "abn": "51824753556",
        "claim_status": "claimed",
        "tier": "claimed",
        "published": True,
    }
    fake_db = _fake_p2_db(existing_claimed_trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("ABR_GUID", "test-guid")

    # Mock AbrClient to return active entity
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = 'callback({"Abn": "51824753556", "AbnStatus": "Active", "EntityName": "CANINE MASTERS PTY LTD", "BusinessName": ["MELBOURNE K9"], "EntityTypeName": "Australian Private Company", "AddressState": "VIC", "AddressPostcode": "3000"});'
    monkeypatch.setattr("services.abr_client.requests.get", lambda *_args, **_kwargs: mock_resp)

    async def _mock_score(_payload):
        return {"confidence": 0.95, "reasoning": "valid", "signals": [], "model": "test"}

    monkeypatch.setattr(server.ai_service, "score_trainer", _mock_score)

    payload = server.SubmissionIn(
        name="Competing Canine School",
        suburb="Richmond",
        email="competitor@k9school.com.au",
        abn="51 824 753 556",
        consent_public_listing=True,
        consent_information_accuracy=True,
    )

    result = asyncio.run(server.create_submission(payload))
    assert result["status"] == "held"
    assert result["duplicate"] is True
    assert result["reason"] == "profile_already_claimed"
    assert result["trainer_id"] == "tr_existing_claimed"

    # Existing trainer must not be modified
    assert existing_claimed_trainer["name"] == "Original K9 Academy"
    assert existing_claimed_trainer["claim_status"] == "claimed"
    assert len(fake_db.trainers.rows) == 1

    # Submission must be held in db.submissions with high severity
    sub_doc = fake_db.submissions.rows[0]
    assert sub_doc["status"] == "held"
    assert sub_doc["duplicate"] is True
    assert sub_doc["reason"] == "profile_already_claimed"

    cases = asyncio.run(
        server._ops_case_rows(
            discovery_summary={},
            waitlist_summary={},
            loop_statuses={},
            claim_cases=[],
            abn_degradation_cases=[],
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=[],
        )
    )
    # The held submission appears in /ops work queue
    held_cases = [c for c in cases if c.get("case_type") == "trainer_submission_case"]
    assert len(held_cases) == 1
    assert held_cases[0]["severity"] == "high"
    assert any(d.get("label") == "Duplicate" and d.get("value") == "true" for d in held_cases[0]["detail_rows"])


def test_submission_with_existing_unclaimed_trainer_enriches_without_duplicate(monkeypatch):
    existing_unclaimed = {
        "id": "tr_unclaimed_base",
        "name": "Base K9",
        "suburb": "Carlton",
        "email": "base@k9.com.au",
        "abn": "51824753556",
        "claim_status": "unclaimed",
        "tier": "unclaimed",
        "training_philosophy": "",
        "published": False,
    }
    fake_db = _fake_p2_db(existing_unclaimed)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("ABR_GUID", "test-guid")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = 'callback({"Abn": "51824753556", "AbnStatus": "Active", "EntityName": "CANINE MASTERS PTY LTD", "BusinessName": ["MELBOURNE K9"], "EntityTypeName": "Australian Private Company", "AddressState": "VIC", "AddressPostcode": "3000"});'
    monkeypatch.setattr("services.abr_client.requests.get", lambda *_args, **_kwargs: mock_resp)

    async def _mock_score(_payload):
        return {"confidence": 0.95, "reasoning": "valid", "signals": [], "model": "test"}

    async def _mock_billing(*_args, **_kwargs):
        return {"billing_profile_status": "ready"}

    async def _mock_notif(*_args, **_kwargs):
        return {"submitter_notification_status": "sent"}

    monkeypatch.setattr(server.ai_service, "score_trainer", _mock_score)
    monkeypatch.setattr(server.stripe_billing, "provision_trainer_billing_profile", _mock_billing)
    monkeypatch.setattr(server.notifications_service, "notify_submitter_result", _mock_notif)

    payload = server.SubmissionIn(
        name="Enriched K9 Carlton",
        suburb="Carlton",
        email="base@k9.com.au",
        abn="51 824 753 556",
        training_philosophy="Positive reinforcement with evidence-led boundaries",
        consent_public_listing=True,
        consent_information_accuracy=True,
    )

    result = asyncio.run(server.create_submission(payload))
    assert result["trainer_id"] == "tr_unclaimed_base"
    # Must NOT create a second trainer
    assert len(fake_db.trainers.rows) == 1
    # Must enrich existing trainer
    updated = fake_db.trainers.rows[0]
    assert updated["name"] == "Enriched K9 Carlton"
    assert updated["training_philosophy"] == "Positive reinforcement with evidence-led boundaries"
    assert updated["abn_verified"] is True

