from __future__ import annotations

import asyncio
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

    async def find_one(self, *_args, **_kwargs):
        return self.find_one_result

    def find(self, *_args, **_kwargs):
        return _Cursor(self.rows)


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
    out = asyncio.run(server.get_trainer_billing_health(trainer_id="t_1", submission_id=None))
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
    out = asyncio.run(server.get_trainer_reactivation_health(trainer_id="t_2", submission_id=None))
    codes = {r["code"] for r in out["reasons"]}
    assert {"low_activity", "verification_drift", "billing_blocker"} <= codes


def test_submit_follow_up_outcome_rejects_unknown_action(monkeypatch):
    fake_db = SimpleNamespace(
        intros=_Collection(find_one_result={"id": "intro_1", "trainer_id": "t_1"}),
        outreach_events=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.submit_follow_up_outcome("intro_1", server.FollowUpOutcomeIn(action="oops")))
    assert exc.value.status_code == 400
