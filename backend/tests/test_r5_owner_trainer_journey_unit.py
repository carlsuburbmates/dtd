"""Unit tests for Stage R5 (Owner Journey, Website, and Trainer Self-Service).

Covers:
- DF-030: Storefront owner claim session validation, token restoration, and protected capability/billing authorization.
- DF-041: Submission endpoint consent enforcement, statutory verification gating, and safe audit recording.
- DF-051: Trainer claim lifecycle: OTP verification, session generation, capability declaration, and expiry/lockout handling.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import server
from services import claim_engine


def _matches_val(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if "$in" in expected:
            return actual in expected["$in"]
        if "$ne" in expected:
            return actual != expected["$ne"]
    return actual == expected


def _matches(row: Dict[str, Any], query: Dict[str, Any]) -> bool:
    for k, v in query.items():
        if k == "$or":
            if not any(
                all(_matches_val(row.get(ck), cv) for ck, cv in clause.items())
                for clause in v
            ):
                return False
        elif not _matches_val(row.get(k), v):
            return False
    return True


class _MockCollection:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None):
        self.rows: List[Dict[str, Any]] = [dict(r) for r in (rows or [])]

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        query = query or {}
        matched = [r.copy() for r in self.rows if _matches(r, query)]

        class _Cursor:
            def __init__(self, items):
                self.items = items
            def sort(self, key, direction):
                return _Cursor(sorted(self.items, key=lambda row: row.get(key, ""), reverse=direction < 0))
            def skip(self, n):
                return _Cursor(self.items[n:])
            def limit(self, n):
                return _Cursor(self.items[:n])
            async def to_list(self, n=None):
                return self.items[:n] if n is not None else self.items
        return _Cursor(matched)

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        for r in self.rows:
            if _matches(r, query):
                return r.copy()
        return None

    async def insert_one(self, doc: Dict[str, Any]) -> None:
        self.rows.append(doc.copy())

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        target = None
        for r in self.rows:
            if _matches(r, query):
                target = r
                break
        if target is not None:
            if "$set" in update:
                target.update(update["$set"])
            return SimpleNamespace(matched_count=1, modified_count=1)
        elif upsert:
            new_doc = query.copy()
            if "$set" in update:
                new_doc.update(update["$set"])
            self.rows.append(new_doc)
            return SimpleNamespace(matched_count=0, modified_count=1, upserted_id="mock_id")
        return SimpleNamespace(matched_count=0, modified_count=0)

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]):
        count = 0
        for r in self.rows:
            if _matches(r, query):
                if "$set" in update:
                    r.update(update["$set"])
                count += 1
        return SimpleNamespace(matched_count=count, modified_count=count)


class _MockDB:
    def __init__(self):
        self.trainers = _MockCollection()
        self.submissions = _MockCollection()
        self.claim_events = _MockCollection()
        self.notification_events = _MockCollection()
        self.audit_log = _MockCollection()
        self.billing_profiles = _MockCollection()
        self.system_state = _MockCollection()
        self.support_threads = _MockCollection()


# ==============================================================================
# DF-030: Claim Session Token Verification & Lifecycle
# ==============================================================================

def test_df030_verify_trainer_claim_session_valid():
    session_data = server._issue_trainer_claim_session(trainer_id="trainer_123", claim_event_id="evt_123")
    token = session_data["token"]

    session = server._verify_trainer_claim_session(token, trainer_id="trainer_123")
    assert session["kind"] == "trainer_claim_session"
    assert session["trainer_id"] == "trainer_123"


def test_df030_verify_trainer_claim_session_mismatched_trainer_id_rejected():
    session_data = server._issue_trainer_claim_session(trainer_id="trainer_123", claim_event_id="evt_123")
    token = session_data["token"]

    with pytest.raises(HTTPException) as exc:
        server._verify_trainer_claim_session(token, trainer_id="trainer_999")
    assert exc.value.status_code == 403
    assert "does not match trainer context" in exc.value.detail.lower()


def test_df030_verify_trainer_claim_session_missing_or_invalid_rejected():
    with pytest.raises(HTTPException) as exc:
        server._verify_trainer_claim_session("", trainer_id="trainer_123")
    assert exc.value.status_code == 401


# ==============================================================================
# DF-041: Submission Consent Enforcement & Statutory Identity Gating
# ==============================================================================

def test_df041_submission_requires_all_consents():
    base_payload = server.SubmissionIn(
        name="Melbourne K9 Training",
        suburb="Richmond",
        website="https://melbournek9.com.au",
        abn="53780168767",
        consent_public_listing=True,
        consent_information_accuracy=True,
        consent_intro_billing_terms=True,
    )

    # 1. Missing billing terms consent -> 400
    p1 = base_payload.model_copy(update={"consent_intro_billing_terms": False})
    with pytest.raises(HTTPException) as exc1:
        asyncio.run(server.create_submission(p1))
    assert exc1.value.status_code == 400
    assert "terms" in exc1.value.detail.lower()

    # 2. Missing public listing consent -> 400
    p2 = base_payload.model_copy(update={"consent_public_listing": False})
    with pytest.raises(HTTPException) as exc2:
        asyncio.run(server.create_submission(p2))
    assert exc2.value.status_code == 400
    assert "consent" in exc2.value.detail.lower()

    # 3. Missing accuracy confirmation -> 400
    p3 = base_payload.model_copy(update={"consent_information_accuracy": False})
    with pytest.raises(HTTPException) as exc3:
        asyncio.run(server.create_submission(p3))
    assert exc3.value.status_code == 400
    assert "consent" in exc3.value.detail.lower()


# ==============================================================================
# DF-051: Trainer Claim Full Lifecycle & Expiration
# ==============================================================================

def test_df051_claim_lifecycle_success(monkeypatch):
    db = _MockDB()
    trainer_doc = {
        "id": "tr_lifecycle_1",
        "name": "Prahran Dog Training",
        "email": "owner@prahrandog.com.au",
        "claim_status": "unclaimed",
        "tier": "unclaimed",
        "is_claimed": False,
    }
    db.trainers.rows.append(dict(trainer_doc))
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "test-otp-secret")
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "test-session-secret")
    monkeypatch.setattr(claim_engine, "generate_otp", lambda: "012345")

    # Mock OTP notification
    with patch("server.notifications_service.notify_trainer_claim_otp", new=AsyncMock(return_value={"claim_notification_status": "sent", "claim_notification_attempts": 1})):
        start_res = asyncio.run(server.start_trainer_claim(
            "tr_lifecycle_1",
            server.TrainerClaimStartIn(email="owner@prahrandog.com.au", method="email"),
        ))

    assert start_res["status"] == "pending_verification"
    assert start_res["delivery_status"] == "sent"
    claim_event_id = start_res["claim_event_id"]
    assert claim_event_id

    # Trainer document now has claim_expires_at recorded
    persisted_trainer = next(r for r in db.trainers.rows if r["id"] == "tr_lifecycle_1")
    assert persisted_trainer["claim_status"] == "pending_verification"
    assert persisted_trainer.get("claim_expires_at")

    # Find OTP from event digest
    event = next(r for r in db.claim_events.rows if r["id"] == claim_event_id)
    otp = "012345"
    assert claim_engine.otp_matches(otp, event["otp_digest"])

    # Verify claim with correct OTP
    verify_res = asyncio.run(server.verify_trainer_claim(
        "tr_lifecycle_1",
        server.TrainerClaimVerifyIn(claim_event_id=claim_event_id, otp=otp),
    ))

    assert verify_res["ok"] is True
    session_token = verify_res["session"]["token"]
    assert session_token

    # Verify trainer is now claimed
    assert persisted_trainer["claim_status"] == "claimed"
    assert persisted_trainer["tier"] == "claimed"

    # Confirm capabilities using the claim session token
    confirm_payload = server.TrainerCapabilitiesConfirmIn(
        confirmation_statement=True,
        specialties=["puppy_training"],
        service_formats=["in_home"],
        life_stages=["puppy"],
        training_philosophy="Positive reinforcement",
        serviced_suburbs=["Prahran", "South Yarra"],
        catchment_type="specific_suburbs",
        delivery_constraints={"in_home_available": True, "facility_available": False, "travel_distance_km": 15, "notes": "Local only"},
    )
    confirm_res = asyncio.run(server.confirm_trainer_capabilities(
        "tr_lifecycle_1",
        confirm_payload,
        request=SimpleNamespace(headers={}),
        x_trainer_claim_session=session_token,
    ))

    assert confirm_res["ok"] is True
    caps = confirm_res["capabilities"]
    assert caps["specialties"]["basis"] == "trainer_declaration"
    assert caps["specialties"]["permitted_in_projection"] is True


def test_df030_claimed_trainer_session_renewal_success(monkeypatch):
    """Ensure a verified/claimed owner can request and verify an OTP to renew their session without 409."""
    db = _MockDB()
    trainer_doc = {
        "id": "tr_claimed_renew",
        "name": "Bayside K9",
        "email": "owner@baysidek9.com.au",
        "billing_email": "owner@baysidek9.com.au",
        "claim_status": "claimed",
        "tier": "claimed",
        "is_claimed": True,
        "claimed_at": "2026-10-01T12:00:00Z",
    }
    db.trainers.rows.append(dict(trainer_doc))
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "test-otp-secret")
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "test-session-secret")
    monkeypatch.setattr(claim_engine, "generate_otp", lambda: "012345")

    with patch("server.notifications_service.notify_trainer_claim_otp", new=AsyncMock(return_value={"claim_notification_status": "sent", "claim_notification_attempts": 1})):
        start_res = asyncio.run(server.start_trainer_claim(
            "tr_claimed_renew",
            server.TrainerClaimStartIn(email="owner@baysidek9.com.au", method="email", intent="session_recovery"),
        ))

    assert start_res["status"] == "pending_verification"
    assert start_res["is_renewal"] is True
    claim_event_id = start_res["claim_event_id"]

    # Verify trainer claim_status remained 'claimed' rather than being wiped
    persisted = next(r for r in db.trainers.rows if r["id"] == "tr_claimed_renew")
    assert persisted["claim_status"] == "claimed"

    event = next(r for r in db.claim_events.rows if r["id"] == claim_event_id)
    otp = "012345"
    assert claim_engine.otp_matches(otp, event["otp_digest"])

    verify_res = asyncio.run(server.verify_trainer_claim(
        "tr_claimed_renew",
        server.TrainerClaimVerifyIn(claim_event_id=claim_event_id, otp=otp),
    ))

    assert verify_res["ok"] is True
    assert verify_res["session_renewed"] is True
    assert verify_res["session"]["token"]
    assert persisted["claim_status"] == "claimed"


def test_df030_claimed_trainer_other_email_rejected_with_409(monkeypatch):
    """Ensure a third party cannot start a claim or renew for an already-claimed trainer."""
    db = _MockDB()
    trainer_doc = {
        "id": "tr_claimed_other",
        "name": "Bayside K9",
        "email": "owner@baysidek9.com.au",
        "claim_status": "claimed",
        "tier": "claimed",
        "is_claimed": True,
    }
    db.trainers.rows.append(dict(trainer_doc))
    monkeypatch.setattr(server, "db", db)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.start_trainer_claim(
            "tr_claimed_other",
            server.TrainerClaimStartIn(email="stranger@otherdomain.com", method="email"),
        ))
    assert exc.value.status_code == 409
    assert "already been claimed" in exc.value.detail.lower()



def _start_session_recovery(monkeypatch):
    db = _MockDB()
    db.trainers.rows.append({
        "id": "recovery-fixture", "name": "Synthetic Trainer", "email": "owner@example.com",
        "billing_email": "owner@example.com", "claim_status": "claimed", "tier": "pro",
        "claim_event_id": "original-owner", "claimed_at": "2026-10-01T12:00:00Z",
    })
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "test-otp-secret")
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "test-session-secret")
    monkeypatch.setattr(claim_engine, "generate_otp", lambda: "012345")
    notifier = AsyncMock(return_value={"claim_notification_status": "sent"})
    monkeypatch.setattr(server.notifications_service, "notify_trainer_claim_otp", notifier)
    response = asyncio.run(server.start_trainer_claim(
        "recovery-fixture", server.TrainerClaimStartIn(email="owner@example.com", intent="session_recovery"),
    ))
    assert notifier.await_args.kwargs["otp"] == "012345"
    return db, response["claim_event_id"]


@pytest.mark.parametrize("changes", [
    {"email": "new@example.com", "billing_email": "new@example.com"},
    {"claim_status": "unclaimed"},
    {"claim_status": "claim_disputed"},
    {"claim_event_id": "different-owner"},
])
def test_df030_session_recovery_rejects_changed_ownership(monkeypatch, changes):
    db, event_id = _start_session_recovery(monkeypatch)
    db.trainers.rows[0].update(changes)
    with patch.object(server, "_issue_trainer_claim_session") as issue_session:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.verify_trainer_claim("recovery-fixture", server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="012345")))
        assert exc.value.status_code == 409
        issue_session.assert_not_called()
    assert db.claim_events.rows[0]["status"] == "stale"


def test_df030_session_recovery_replay_rejected(monkeypatch):
    db, event_id = _start_session_recovery(monkeypatch)
    payload = server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="012345")
    assert asyncio.run(server.verify_trainer_claim("recovery-fixture", payload))["session_renewed"] is True
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("recovery-fixture", payload))
    assert exc.value.status_code == 409
    assert db.trainers.rows[0]["tier"] == "pro"


def test_df030_session_recovery_concurrent_consumption_has_one_winner(monkeypatch):
    db, event_id = _start_session_recovery(monkeypatch)
    original_find = db.claim_events.find_one
    async def run():
        barrier = asyncio.Event()
        snapshots = 0
        async def simultaneous_find(query, projection=None):
            nonlocal snapshots
            result = await original_find(query, projection)
            if query.get("id") == event_id:
                snapshots += 1
                if snapshots == 2:
                    barrier.set()
                await barrier.wait()
            return result
        monkeypatch.setattr(db.claim_events, "find_one", simultaneous_find)
        return await asyncio.gather(*[
            server.verify_trainer_claim("recovery-fixture", server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="012345"))
            for _ in range(2)
        ], return_exceptions=True)
    results = asyncio.run(run())
    assert sum(isinstance(result, dict) and result.get("ok") is True for result in results) == 1
    assert sum(isinstance(result, HTTPException) and result.status_code == 409 for result in results) == 1
    assert db.claim_events.rows[0]["status"] == "verified"


@pytest.mark.parametrize("state,expected_status", [("expired", 410), ("wrong_otp", 400), ("locked", 429)])
def test_df030_session_recovery_failure_paths_do_not_issue_session(monkeypatch, state, expected_status):
    db, event_id = _start_session_recovery(monkeypatch)
    if state == "expired":
        db.claim_events.rows[0]["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    if state == "locked":
        db.claim_events.rows[0]["attempts"] = db.claim_events.rows[0]["max_attempts"]
    with patch.object(server, "_issue_trainer_claim_session") as issue_session:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.verify_trainer_claim("recovery-fixture", server.TrainerClaimVerifyIn(claim_event_id=event_id, otp="000000" if state == "wrong_otp" else "012345")))
        assert exc.value.status_code == expected_status
        issue_session.assert_not_called()
    assert db.trainers.rows[0]["claim_status"] == "claimed"


@pytest.mark.parametrize("changes,confirmed,trainer_id,expected_status", [
    ({"category": "privacy_request"}, True, "trainer-link", 422),
    ({"status": "resolved"}, True, "trainer-link", 409),
    ({"status": "rejected"}, True, "trainer-link", 409),
    ({}, False, "trainer-link", 400),
    ({}, True, "missing-trainer", 404),
    ({"trainer_id": "other-trainer"}, True, "trainer-link", 409),
])
def test_support_listing_link_rejects_invalid_context(monkeypatch, changes, confirmed, trainer_id, expected_status):
    db = _MockDB()
    db.support_threads.rows.append({"case_id": "support-link", "category": "delisting_request", "status": "open", **changes})
    db.trainers.rows.append({"id": "trainer-link", "name": "Synthetic Trainer"})
    monkeypatch.setattr(server, "db", db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.link_support_thread_trainer("support-link", server.SupportTrainerLinkIn(trainer_id=trainer_id, confirmed=confirmed)))
    assert exc.value.status_code == expected_status


def test_support_listing_link_records_listing_without_identity_assertion(monkeypatch):
    db = _MockDB()
    db.support_threads.rows.append({"case_id": "support-link", "category": "delisting_request", "status": "open"})
    db.trainers.rows.append({"id": "trainer-link", "name": "Synthetic Trainer"})
    monkeypatch.setattr(server, "db", db)
    result = asyncio.run(server.link_support_thread_trainer("support-link", server.SupportTrainerLinkIn(trainer_id="trainer-link", confirmed=True)))
    assert result["thread"]["trainer_id"] == "trainer-link"
    assert result["thread"]["status"] == "open"
    assert "identity_verified" not in result["thread"]
    assert db.audit_log.rows[-1]["action"] == "support_thread_trainer_linked"


def test_df030_delivery_completion_cannot_reopen_consumed_recovery(monkeypatch):
    db = _MockDB()
    db.trainers.rows.append({"id": "delivery-race", "email": "owner@example.com", "claim_status": "claimed", "tier": "claimed"})
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "test-otp-secret")
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "test-session-secret")
    monkeypatch.setattr(claim_engine, "generate_otp", lambda: "012345")
    async def delivered_before_completion(*args, **kwargs):
        event_id = db.claim_events.rows[-1]["id"]
        await server.verify_trainer_claim("delivery-race", server.TrainerClaimVerifyIn(claim_event_id=event_id, otp=kwargs["otp"]))
        return {"claim_notification_status": "sent"}
    monkeypatch.setattr(server.notifications_service, "notify_trainer_claim_otp", delivered_before_completion)
    result = asyncio.run(server.start_trainer_claim("delivery-race", server.TrainerClaimStartIn(email="owner@example.com", intent="session_recovery")))
    assert db.claim_events.rows[0]["status"] == "verified"
    assert db.claim_events.rows[0]["delivery_status"] == "sent"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.verify_trainer_claim("delivery-race", server.TrainerClaimVerifyIn(claim_event_id=result["claim_event_id"], otp="012345")))
    assert exc.value.status_code == 409


def test_support_thread_pagination_exposes_remaining_cases(monkeypatch):
    db = _MockDB()
    db.support_threads.rows = [{"case_id": f"sup_{i}", "created_at": str(i), "status": "open"} for i in range(3)]
    monkeypatch.setattr(server, "db", db)
    first = asyncio.run(server.list_support_threads(limit=2, offset=0))
    second = asyncio.run(server.list_support_threads(limit=2, offset=2))
    assert first["has_more"] is True
    assert second["has_more"] is False
    assert {row["case_id"] for row in first["threads"] + second["threads"]} == {"sup_0", "sup_1", "sup_2"}
