from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import server
from services import automation
from services import engine


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    async def to_list(self, _n):
        return list(self.rows)


class _Collection:
    def __init__(self, rows=None, find_one_result=None):
        self.rows = list(rows or [])
        self.find_one_result = find_one_result
        self.inserted = []
        self.updated = []
        self.updated_many = []

    async def find_one(self, filt=None, *_args, **_kwargs):
        if self.find_one_result is not None:
            return self.find_one_result
        filt = filt or {}
        for row in self.rows:
            if all(row.get(k) == v for k, v in filt.items()):
                return row
        return None

    def find(self, *_args, **_kwargs):
        return _Cursor(self.rows)

    async def insert_one(self, doc):
        self.inserted.append(doc)
        self.rows.append(doc)

    async def update_one(self, filt, update, upsert=False):
        self.updated.append((filt, update, upsert))
        target = await self.find_one(filt)
        if target is None and upsert:
            target = dict(filt)
            self.rows.append(target)
        if target is not None:
            target.update(update.get("$set", {}))

    async def update_many(self, filt, update):
        self.updated_many.append((filt, update))
        for row in self.rows:
            if all(row.get(k) == v for k, v in filt.items()):
                row.update(update.get("$set", {}))

    async def distinct(self, field, *_args, **_kwargs):
        return list({row.get(field) for row in self.rows if row.get(field) is not None})


def test_record_match_connect_click_logs_event(monkeypatch):
    fake_db = SimpleNamespace(
        match_events=_Collection(find_one_result={"id": "m_1", "result_ids": ["t_1", "t_2"], "campaign": "seo", "source": "google"}),
        engagements=_Collection(),
        audit_log=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(
        server.record_match_connect_click(
            server.ConnectClickIn(match_id="m_1", trainer_id="t_2", rank=2)
        )
    )

    assert out["kind"] == "result_connect_click"
    assert out["trainer_id"] == "t_2"
    assert out["rank"] == 2
    assert fake_db.engagements.inserted[0]["campaign"] == "seo"
    assert fake_db.engagements.inserted[0]["source"] == "google"


def test_ingest_discovery_sources_applies_failure_suppression(monkeypatch):
    class _FailingResponse:
        status_code = 500

        def raise_for_status(self):
            raise RuntimeError("boom")

    def _fail_get(*_args, **_kwargs):
        return _FailingResponse()

    source_state = _Collection()
    fake_db = SimpleNamespace(
        source_ingestion_state=source_state,
        discovery_queue=_Collection(),
    )

    monkeypatch.setenv("DISCOVERY_SOURCE_URLS", "https://bad.example.com")
    monkeypatch.setenv("SOURCE_INGEST_FAILURE_SUPPRESS_AFTER", "2")
    monkeypatch.setenv("SOURCE_INGEST_SUPPRESS_HOURS", "24")
    monkeypatch.setattr(automation.requests, "get", _fail_get)

    first = asyncio.run(automation.ingest_discovery_sources(fake_db))
    second = asyncio.run(automation.ingest_discovery_sources(fake_db))

    assert first["failed_sources"] == 1
    assert second["failed_sources"] == 1
    row = source_state.rows[0]
    assert int(row.get("consecutive_failures") or 0) >= 2
    assert bool(row.get("suppressed_until"))


def test_growth_nurture_builds_remarketing_candidates():
    old_ts = datetime(2026, 5, 1, tzinfo=timezone.utc).isoformat()
    fake_db = SimpleNamespace(
        match_events=_Collection(rows=[{"id": "m_1", "campaign": "seo", "source": "google", "created_at": old_ts}]),
        intros=_Collection(rows=[]),
        conversions=_Collection(rows=[]),
        growth_attribution=_Collection(),
        system_state=_Collection(),
    )

    out = asyncio.run(engine.run_growth_nurture(fake_db))

    assert out["cohorts"] == 1
    assert out["matched"] == 1
    assert out["remarketing_candidates"] == 1
    assert fake_db.growth_attribution.updated
