from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import server


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _n):
        return list(self.rows)


class _Collection:
    def __init__(self, *, find_one_result=None, rows=None):
        self.find_one_result = find_one_result
        self.rows = rows or []
        self.updated = []

    async def find_one(self, *_args, **_kwargs):
        return self.find_one_result

    def find(self, *_args, **_kwargs):
        return _Cursor(self.rows)

    async def update_one(self, filt, update, upsert=False):
        self.updated.append((filt, update, upsert))
        target = self.find_one_result
        if target is None and self.rows:
            target = self.rows[0]
        if target is None and upsert:
            target = dict(filt)
            self.rows.append(target)
            if self.find_one_result is None:
                self.find_one_result = target
        if target is None:
            return
        target.update(update.get("$set", {}))

    async def delete_one(self, filt):
        key = next(iter(filt.items()), None)
        if self.find_one_result and key and self.find_one_result.get(key[0]) == key[1]:
            self.find_one_result = None
        self.rows = [row for row in self.rows if not all(row.get(k) == v for k, v in filt.items())]


def _signed_trainer_action_token(*, trainer_id: str, submission_id: str = "", exp_epoch: int) -> str:
    payload = {
        "trainer_id": trainer_id,
        "submission_id": submission_id,
        "exp": exp_epoch,
    }
    payload_blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(server._trainer_action_secret().encode("utf-8"), payload_blob, hashlib.sha256).digest()
    return f"{server._token_b64(payload_blob)}.{server._token_b64(sig)}"


def test_get_follow_up_invalid_token_404(monkeypatch):
    fake_db = SimpleNamespace(
        intros=_Collection(find_one_result=None),
        trainers=_Collection(find_one_result=None),
        conversions=_Collection(find_one_result=None),
    )
    monkeypatch.setattr(server, "db", fake_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.get_follow_up("invalid"))
    assert exc.value.status_code == 404


def test_get_submission_status_exposes_blockers(monkeypatch):
    fake_db = SimpleNamespace(
        submissions=_Collection(
            find_one_result={
                "id": "sub_1",
                "name": "Trainer One",
                "status": "held",
                "confidence_score": 0.42,
                "billing_profile_status": "missing_email",
            }
        ),
        trainers=_Collection(find_one_result=None),
    )
    monkeypatch.setattr(server, "db", fake_db)
    out = asyncio.run(server.get_submission_status("sub_1"))
    codes = {b["code"] for b in out["blockers"]}
    assert {"held", "billing_profile"} <= codes
    assert out["status"] == "held"
    assert out["activation_state"] == "held_for_review"


def test_get_submission_status_activation_state_intro_ready(monkeypatch):
    fake_db = SimpleNamespace(
        submissions=_Collection(
            find_one_result={
                "id": "sub_ready",
                "name": "Trainer Ready",
                "status": "published",
                "confidence_score": 0.91,
                "billing_profile_status": "ready",
            }
        ),
        trainers=_Collection(
            find_one_result={
                "id": "t_ready",
                "name": "Trainer Ready",
                "published": True,
                "billing_profile_status": "ready",
                "verification_status": "verified",
            }
        ),
    )
    monkeypatch.setattr(server, "db", fake_db)
    out = asyncio.run(server.get_submission_status("sub_ready"))
    assert out["activation_state"] == "intro_ready"
    assert out["blockers"] == []


def test_get_submission_status_activation_state_needs_billing_profile(monkeypatch):
    fake_db = SimpleNamespace(
        submissions=_Collection(
            find_one_result={
                "id": "sub_profile",
                "name": "Trainer Profile",
                "status": "published",
                "confidence_score": 0.75,
                "billing_profile_status": "missing_email",
            }
        ),
        trainers=_Collection(find_one_result=None),
    )
    monkeypatch.setattr(server, "db", fake_db)
    out = asyncio.run(server.get_submission_status("sub_profile"))
    assert out["activation_state"] == "needs_billing_profile"
    assert {b["code"] for b in out["blockers"]} == {"billing_profile"}


def test_get_submission_status_prefers_live_trainer_billing_state(monkeypatch):
    fake_db = SimpleNamespace(
        submissions=_Collection(
            find_one_result={
                "id": "sub_recovered",
                "name": "Trainer Recovered",
                "status": "published",
                "confidence_score": 0.88,
                "billing_profile_status": "missing_email",
                "trainer_id": "t_recovered",
            }
        ),
        trainers=_Collection(
            find_one_result={
                "id": "t_recovered",
                "name": "Trainer Recovered",
                "published": True,
                "billing_profile_status": "ready",
                "verification_status": "verified",
            }
        ),
    )
    monkeypatch.setattr(server, "db", fake_db)
    out = asyncio.run(server.get_submission_status("sub_recovered"))
    assert out["billing_profile_status"] == "ready"
    assert out["activation_state"] == "intro_ready"
    assert out["blockers"] == []


def test_get_trainer_billing_health_flags_issues(monkeypatch):
    fake_db = SimpleNamespace(
        trainers=_Collection(
            find_one_result={
                "id": "t_1",
                "name": "Trainer One",
                "billing_profile_status": "missing_email",
                "email": "trainer@example.com",
            }
        ),
        submissions=_Collection(find_one_result=None),
        intros=_Collection(
            rows=[
                {"intro_fee_cents": 500, "billing_collection_status": "payment_failed"},
                {"intro_fee_cents": 500, "billing_collection_status": "disputed"},
            ]
        ),
    )
    monkeypatch.setattr(server, "db", fake_db)
    token = server._issue_trainer_action_token(trainer_id="t_1")
    out = asyncio.run(
        server.get_trainer_billing_health(
            trainer_id="t_1",
            submission_id=None,
            trainer_action_token=token,
        )
    )
    assert out["issues"]["profile_incomplete"] is True
    assert out["issues"]["payment_failed_or_disputed"] is True
    assert out["status_counts"]["payment_failed"] == 1


def test_get_trainer_reactivation_health_lists_reasons(monkeypatch):
    fake_db = SimpleNamespace(
        trainers=_Collection(
            find_one_result={
                "id": "t_2",
                "name": "Trainer Two",
                "published": False,
                "confidence_score": 0.33,
                "billing_profile_status": "consent_required",
                "intros_30d": 0,
                "conversions_30d": 0,
                "outcome_score": 0.05,
            }
        ),
        submissions=_Collection(find_one_result=None),
    )
    monkeypatch.setattr(server, "db", fake_db)
    token = server._issue_trainer_action_token(trainer_id="t_2")
    out = asyncio.run(
        server.get_trainer_reactivation_health(
            trainer_id="t_2",
            submission_id=None,
            trainer_action_token=token,
        )
    )
    codes = {r["code"] for r in out["reasons"]}
    assert {"low_activity", "verification_drift", "billing_blocker"} <= codes


def test_oversight_login_returns_429_after_lockout_threshold(monkeypatch):
    auth_attempts = _Collection(find_one_result=None, rows=[])
    fake_db = SimpleNamespace(auth_attempts=auth_attempts)
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("ADMIN_PASS", "correct-pass")
    monkeypatch.setattr(server, "OVERSIGHT_AUTH_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(server, "OVERSIGHT_AUTH_WINDOW_S", 600)
    monkeypatch.setattr(server, "OVERSIGHT_AUTH_LOCK_S", 900)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})

    with pytest.raises(HTTPException) as first_exc:
        asyncio.run(server.oversight_login(server.OversightLogin(passcode="wrong"), request))
    assert first_exc.value.status_code == 401

    with pytest.raises(HTTPException) as second_exc:
        asyncio.run(server.oversight_login(server.OversightLogin(passcode="wrong"), request))
    assert second_exc.value.status_code == 401

    assert auth_attempts.rows[0]["locked_until_epoch"] > 0

    with pytest.raises(HTTPException) as locked_exc:
        asyncio.run(server.oversight_login(server.OversightLogin(passcode="correct-pass"), request))
    assert locked_exc.value.status_code == 429


def test_verify_trainer_action_token_rejects_invalid_format():
    with pytest.raises(HTTPException) as exc:
        server._verify_trainer_action_token("not-a-token", trainer_id="t_1")
    assert exc.value.status_code == 401


def test_verify_trainer_action_token_rejects_tampered_signature():
    token = server._issue_trainer_action_token(trainer_id="t_1")
    payload_part, _sig_part = token.split(".", 1)
    tampered_sig = server._token_b64(b"not-the-real-signature")

    with pytest.raises(HTTPException) as exc:
        server._verify_trainer_action_token(f"{payload_part}.{tampered_sig}", trainer_id="t_1")
    assert exc.value.status_code == 401


def test_verify_trainer_action_token_rejects_expired_token(monkeypatch):
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    expired = _signed_trainer_action_token(trainer_id="t_1", exp_epoch=now_epoch - 60)

    with pytest.raises(HTTPException) as exc:
        server._verify_trainer_action_token(expired, trainer_id="t_1")
    assert exc.value.status_code == 401


def test_verify_trainer_action_token_rejects_wrong_trainer_context():
    token = server._issue_trainer_action_token(trainer_id="t_1")

    with pytest.raises(HTTPException) as exc:
        server._verify_trainer_action_token(token, trainer_id="t_2")
    assert exc.value.status_code == 403


def test_verify_trainer_action_token_rejects_wrong_submission_context():
    token = server._issue_trainer_action_token(trainer_id="t_1", submission_id="sub_a")

    with pytest.raises(HTTPException) as exc:
        server._verify_trainer_action_token(token, trainer_id="t_1", submission_id="sub_b")
    assert exc.value.status_code == 403


def test_reconnect_trainer_billing_returns_updated_profile_status(monkeypatch):
    trainer_doc = {
        "id": "t_bill",
        "name": "Trainer Billing",
        "billing_profile_status": "missing_email",
        "email": "trainer@example.com",
    }
    trainers = _Collection(find_one_result=trainer_doc)
    fake_db = SimpleNamespace(
        trainers=trainers,
        submissions=_Collection(find_one_result=None),
    )
    monkeypatch.setattr(server, "db", fake_db)

    async def _fake_profile(_db, trainer, *, consent_granted):
        assert trainer["billing_email"] == "billing@example.com"
        assert consent_granted is False
        trainer["billing_profile_status"] = "ready"
        return {"billing_profile_status": "ready"}

    async def _noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(server.stripe_billing, "provision_trainer_billing_profile", _fake_profile)
    monkeypatch.setattr(server, "_audit", _noop_audit)

    token = server._issue_trainer_action_token(trainer_id="t_bill", submission_id="sub_bill")
    out = asyncio.run(
        server.reconnect_trainer_billing(
            server.TrainerBillingActionIn(
                trainer_id="t_bill",
                submission_id="sub_bill",
                billing_email="billing@example.com",
                trainer_action_token=token,
            )
        )
    )

    assert out["ok"] is True
    assert out["billing_profile_status"] == "ready"
    assert trainers.find_one_result["billing_email"] == "billing@example.com"


def test_submit_follow_up_outcome_rejects_unknown_action(monkeypatch):
    fake_db = SimpleNamespace(
        intros=_Collection(find_one_result={"id": "intro_1", "trainer_id": "t_1"}),
        outreach_events=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.submit_follow_up_outcome("intro_1", server.FollowUpOutcomeIn(action="oops")))
    assert exc.value.status_code == 400
