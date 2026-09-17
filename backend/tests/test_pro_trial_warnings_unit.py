from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services import notifications, pro_trials, stripe_billing


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _limit):
        return [dict(row) for row in self.rows]


class _Trainers:
    def __init__(self, rows):
        self.rows = rows
        self.updates = []

    def find(self, *_args, **_kwargs):
        return _Cursor(self.rows)

    async def update_one(self, filt, update):
        self.updates.append((filt, update))
        return SimpleNamespace(matched_count=1)


class _Events:
    def __init__(self, existing=None):
        self.existing = existing

    async def find_one(self, *_args, **_kwargs):
        return self.existing


class _State:
    def __init__(self):
        self.updates = []

    async def update_one(self, filt, update, upsert=False):
        self.updates.append((filt, update, upsert))


def _due_trainer(now):
    start = now - timedelta(days=23)
    return {
        "id": "trainer_1",
        "name": "Northside Dogs",
        "email": "trainer@example.com",
        "claimed_at": (now - timedelta(days=30)).isoformat(),
        "subscription_tier": "pro",
        "subscription_status": "trialing",
        "pro_trial_started_at": start.isoformat(),
        "pro_trial_ends_at": (start + timedelta(days=30)).isoformat(),
        "pro_trial_consumed_at": start.isoformat(),
    }


def test_day_23_warning_sends_once_and_records_job_state(monkeypatch):
    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", (now - timedelta(days=60)).isoformat())
    monkeypatch.setattr(stripe_billing, "_now", lambda: now)
    sent = []

    async def _send(*_args, **kwargs):
        sent.append(kwargs)
        return {"status": "sent", "attempts": 1}

    monkeypatch.setattr(notifications, "notify_pro_trial_expiry_warning", _send)
    db = SimpleNamespace(trainers=_Trainers([_due_trainer(now)]), notification_events=_Events(), system_state=_State())
    result = asyncio.run(pro_trials.process_expiry_warnings(db, billing_url_factory=lambda _trainer: "https://dtd.test/billing?signed=1"))
    assert result["candidates"] == 1
    assert result["sent"] == 1
    assert sent[0]["days_remaining"] == 7
    assert db.trainers.updates[0][1]["$set"]["pro_trial_warning_sent_at"]
    assert db.system_state.updates[0][0] == {"key": "pro_trial_warnings"}


def test_existing_sent_event_prevents_duplicate(monkeypatch):
    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", (now - timedelta(days=60)).isoformat())
    monkeypatch.setattr(stripe_billing, "_now", lambda: now)
    db = SimpleNamespace(
        trainers=_Trainers([_due_trainer(now)]),
        notification_events=_Events({"created_at": now.isoformat()}),
        system_state=_State(),
    )
    result = asyncio.run(pro_trials.process_expiry_warnings(db, billing_url_factory=lambda _trainer: "unused"))
    assert result["sent"] == 0
    assert result["skipped"] == 1
    assert not db.trainers.updates
