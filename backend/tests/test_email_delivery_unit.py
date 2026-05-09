from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services import automation
from services import notifications


class _EventsCollection:
    def __init__(self):
        self.rows = []

    async def insert_one(self, doc):
        self.rows.append(doc)

    async def find_one(self, *_args, **_kwargs):
        return None


class _IntrosCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def limit(self, _n):
        return self

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self._rows):
            raise StopAsyncIteration
        row = self._rows[self._idx]
        self._idx += 1
        return row


class _IntrosCollection:
    def __init__(self, rows):
        self._rows = rows

    def find(self, *_args, **_kwargs):
        return _IntrosCursor(self._rows)


def test_submitter_notification_payload_sets_reply_to_and_header(monkeypatch):
    sent_payload = {}

    def fake_post(_url, *, json, headers, timeout):
        sent_payload.update({"json": json, "headers": headers, "timeout": timeout})
        return SimpleNamespace(status_code=200, json=lambda: {"id": "re_123"})

    monkeypatch.setenv("RESEND_API_KEY", "rk_test")
    monkeypatch.setenv("RESEND_FROM", "no-reply@dogtrainersdirectory.com.au")
    monkeypatch.setenv("RESEND_REPLY_TO", "info@dogtrainersdirectory.com.au")
    monkeypatch.setattr(notifications.requests, "post", fake_post)

    fake_db = SimpleNamespace(notification_events=_EventsCollection())
    out = asyncio.run(
        notifications.notify_submitter_result(
            fake_db,
            {
                "id": "sub_1",
                "name": "Header Verify Trainer",
                "status": "published",
                "confidence_score": 0.95,
                "submitter_email": "info@dogtrainersdirectory.com.au",
            },
        )
    )

    assert out["submitter_notification_status"] == "sent"
    assert sent_payload["json"]["from"] == "no-reply@dogtrainersdirectory.com.au"
    assert sent_payload["json"]["reply_to"] == ["info@dogtrainersdirectory.com.au"]
    assert sent_payload["json"]["headers"]["Reply-To"] == "info@dogtrainersdirectory.com.au"


def test_outreach_payload_sets_reply_to_and_header(monkeypatch):
    sent_payload = {}

    def fake_post(_url, *, json, headers, timeout):
        sent_payload.update({"json": json, "headers": headers, "timeout": timeout})
        return SimpleNamespace(status_code=200, json=lambda: {"id": "re_out_1"})

    intro_created_at = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    fake_db = SimpleNamespace(
        intros=_IntrosCollection(
            [
                {
                    "id": "intro_1",
                    "trainer_name": "Header Verify Intro Trainer",
                    "user_email": "owner@example.com",
                    "created_at": intro_created_at,
                }
            ]
        ),
        outreach_events=_EventsCollection(),
        conversions=_EventsCollection(),
    )

    monkeypatch.setenv("RESEND_API_KEY", "rk_test")
    monkeypatch.setenv("RESEND_FROM", "no-reply@dogtrainersdirectory.com.au")
    monkeypatch.setenv("RESEND_REPLY_TO", "info@dogtrainersdirectory.com.au")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://dogtrainersdirectory.com.au")
    monkeypatch.setattr(automation.requests, "post", fake_post)

    out = asyncio.run(automation.send_t7_outreach(fake_db))
    assert out["sent"] == 1
    assert sent_payload["json"]["subject"] == "Quick follow-up on your dog trainer match"
    assert sent_payload["json"]["from"] == "no-reply@dogtrainersdirectory.com.au"
    assert sent_payload["json"]["reply_to"] == ["info@dogtrainersdirectory.com.au"]
    assert sent_payload["json"]["headers"]["Reply-To"] == "info@dogtrainersdirectory.com.au"
    assert "https://dogtrainersdirectory.com.au/follow-up/intro_1" in sent_payload["json"]["html"]
