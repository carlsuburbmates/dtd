from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import server
from services import claim_engine
from services.abn_validator import validate_abn_checksum, validate_abn_detailed
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


def _fake_db(trainer):
    return SimpleNamespace(
        trainers=_Collection([trainer]),
        claim_events=_Collection(),
        abn_cache=_Collection(),
        notification_events=_Collection(),
        audit_log=_Collection(),
        submissions=_Collection(),
    )


def _start_payload(email="trainer@example.com"):
    return server.TrainerClaimStartIn(email=email)


def test_ato_modulus_89_vectors():
    assert validate_abn_checksum("51 824 753 556") is True
    assert validate_abn_checksum("10 000 000 032") is True
    assert validate_abn_checksum("51 824 753 557") is False
    assert validate_abn_detailed("123") ["code"] == "invalid_length"


def test_abr_without_guid_is_explicitly_degraded(monkeypatch):
    fake_db = _fake_db({"id": "trainer_1"})
    monkeypatch.delenv("ABR_GUID", raising=False)
    result = asyncio.run(AbrClient(fake_db, guid="").lookup("51 824 753 556"))
    assert result["ok"] is False
    assert result["state"] == "abr_unavailable"
    assert result["reason_code"] == "abr_guid_missing"
    assert result["abn"] == "51824753556"
    assert result["abn_verified"] is False
    assert "ABR_GUID is not configured" in result["reason"]


def test_abr_uses_fresh_mongo_cache_before_network(monkeypatch):
    cached_at = datetime.now(timezone.utc).isoformat()
    fake_db = _fake_db({"id": "trainer_1"})
    fake_db.abn_cache.rows.append(
        {
            "abn": "51824753556",
            "cached_at": cached_at,
            "record": {"abn": "51824753556", "abn_status": "Active", "is_active": True},
        }
    )
    client = AbrClient(fake_db, guid="configured")
    monkeypatch.setattr("services.abr_client.requests.get", lambda *_args, **_kwargs: pytest.fail("network should not be called"))
    result = asyncio.run(client.lookup("51 824 753 556"))
    assert result["ok"] is True
    assert result["cached"] is True
    assert result["data"]["is_active"] is True


def test_submission_persists_profile_fields_without_self_claiming(monkeypatch):
    fake_db = _fake_db({"id": "existing"})
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.delenv("ABR_GUID", raising=False)

    async def _score(_payload):
        return {"confidence": 0.9, "reasoning": "test", "signals": [], "model": "test"}

    async def _billing(*_args, **_kwargs):
        return {"billing_profile_status": "ready"}

    async def _notification(*_args, **_kwargs):
        return {"submitter_notification_status": "sent", "submitter_notification_attempts": 1}

    monkeypatch.setattr(server.ai_service, "score_trainer", _score)
    monkeypatch.setattr(server.stripe_billing, "provision_trainer_billing_profile", _billing)
    monkeypatch.setattr(server.notifications_service, "notify_submitter_result", _notification)
    payload = server.SubmissionIn(
        name="Trainer One",
        suburb="Carlton",
        email="trainer@example.com",
        abn="51 824 753 556",
        training_philosophy="Evidence led",
        specialties=["Puppies"],
        service_formats=["In home"],
        serviced_suburbs=["Carlton"],
        catchment_type="Travel",
        booking_url="https://example.com/book",
        gallery_images=["https://example.com/image.jpg"],
        sponsored_suburbs=["Carlton"],
        review_summary="Independent reviews",
        tier="claimed",
        claim_status="claimed",
        consent_public_listing=True,
        consent_information_accuracy=True,
    )
    response = asyncio.run(server.create_submission(payload))
    trainer = next(row for row in fake_db.trainers.rows if row["id"] == response["trainer_id"])
    assert trainer["tier"] == "unclaimed"
    assert trainer["claim_status"] == "unclaimed"
    assert trainer["abn_status"] == "abr_unavailable"
    assert trainer["training_philosophy"] == "Evidence led"
    assert trainer["specialties"] == ["Puppies"]
    assert trainer["gallery_images"] == ["https://example.com/image.jpg"]


def test_claim_start_masks_destination_and_never_persists_raw_code(monkeypatch):
    trainer = {"id": "trainer_1", "name": "Trainer One", "email": "trainer@example.com", "claim_status": "unclaimed"}
    fake_db = _fake_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "otp-secret")
    monkeypatch.setattr(claim_engine, "generate_otp", lambda: "123456")

    async def _sent(*_args, **_kwargs):
        return {"claim_notification_status": "sent", "claim_notification_attempts": 1}

    monkeypatch.setattr(server.notifications_service, "notify_trainer_claim_otp", _sent)
    response = asyncio.run(server.start_trainer_claim("trainer_1", _start_payload()))
    event = fake_db.claim_events.rows[0]
    assert response["masked_destination"] == "t***@example.com"
    assert "123456" not in str(response)
    assert event["otp_digest"] != "123456"
    assert event["status"] == "pending_verification"
    assert datetime.fromisoformat(event["expires_at"]) > datetime.now(timezone.utc) + timedelta(minutes=14)


def test_correct_claim_code_marks_profile_claimed_and_returns_scoped_session(monkeypatch):
    trainer = {"id": "trainer_1", "name": "Trainer One", "email": "trainer@example.com", "claim_status": "pending_verification"}
    fake_db = _fake_db(trainer)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "otp-secret")
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "action-secret")
    fake_db.claim_events.rows.append(
        {
            "id": "claim_1",
            "trainer_id": "trainer_1",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("123456"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )
    monkeypatch.setattr(server, "db", fake_db)
    response = asyncio.run(server.verify_trainer_claim("trainer_1", server.TrainerClaimVerifyIn(claim_event_id="claim_1", otp="123456")))
    assert trainer["claim_status"] == "claimed"
    assert trainer["tier"] == "claimed"
    assert fake_db.claim_events.rows[0]["status"] == "verified"
    assert response["session"]["token"]


def test_invalid_claim_code_keeps_profile_unchanged(monkeypatch):
    trainer = {"id": "trainer_1", "email": "trainer@example.com", "claim_status": "pending_verification"}
    fake_db = _fake_db(trainer)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "otp-secret")
    fake_db.claim_events.rows.append(
        {
            "id": "claim_1",
            "trainer_id": "trainer_1",
            "status": "pending_verification",
            "otp_digest": claim_engine.otp_digest("123456"),
            "attempts": 0,
            "max_attempts": 5,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
    )
    monkeypatch.setattr(server, "db", fake_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("trainer_1", server.TrainerClaimVerifyIn(claim_event_id="claim_1", otp="000000")))
    assert exc.value.status_code == 400
    assert trainer["claim_status"] == "pending_verification"
    assert fake_db.claim_events.rows[0]["attempts"] == 1


def test_duplicate_claim_on_claimed_profile_returns_409_without_altering_trainer(monkeypatch):
    trainer = {"id": "trainer_1", "email": "trainer@example.com", "claim_status": "claimed", "tier": "claimed", "claimed_at": "2026-09-01T00:00:00Z"}
    fake_db = _fake_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("trainer_1", _start_payload()))
    assert exc.value.status_code == 409
    assert "already" in exc.value.detail.lower()
    assert trainer["claim_status"] == "claimed"
    assert trainer["tier"] == "claimed"
    assert trainer["claimed_at"] == "2026-09-01T00:00:00Z"
    assert len(fake_db.claim_events.rows) == 0


def test_repeated_claim_attempt_on_already_disputed_profile(monkeypatch):
    trainer = {"id": "trainer_1", "email": "trainer@example.com", "claim_status": "claim_disputed", "tier": "claimed", "claimed_at": "2026-09-01T00:00:00Z"}
    fake_db = _fake_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim("trainer_1", _start_payload()))
    assert exc.value.status_code == 409
    assert "already" in exc.value.detail.lower()
    assert trainer["claim_status"] == "claim_disputed"
    assert trainer["tier"] == "claimed"
    assert trainer["claimed_at"] == "2026-09-01T00:00:00Z"
    assert len(fake_db.claim_events.rows) == 0


def test_delivery_failure_and_ops_case_are_visible(monkeypatch):
    trainer = {"id": "trainer_1", "email": "trainer@example.com", "claim_status": "unclaimed"}
    fake_db = _fake_db(trainer)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "otp-secret")

    async def _failed(*_args, **_kwargs):
        return {"claim_notification_status": "failed", "claim_notification_error": "provider_timeout"}

    monkeypatch.setattr(server.notifications_service, "notify_trainer_claim_otp", _failed)
    response = asyncio.run(server.start_trainer_claim("trainer_1", _start_payload()))
    assert response["status"] == "delivery_failed"
    cases = asyncio.run(
        server._ops_case_rows(
            discovery_summary={},
            waitlist_summary={},
            loop_statuses={},
            claim_cases=fake_db.claim_events.rows,
            abn_degradation_cases=[
                {
                    "id": "trainer_2",
                    "name": "Trainer Two",
                    "abn": "51824753556",
                    "abn_status": "abr_unavailable",
                    "abn_verification_reason": "ABR_GUID is not configured.",
                }
            ],
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=[],
        )
    )
    assert any(case["case_type"] == "trainer_claim_case" and case["entity_id"] == "trainer_1" for case in cases)
    assert any(case["case_type"] == "abn_verification_case" and case["entity_id"] == "trainer_2" for case in cases)
