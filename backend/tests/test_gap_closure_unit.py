from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

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
            target.update(update.get("$setOnInsert", {}))
            self.rows.append(target)
        if target is not None:
            target.update(update.get("$set", {}))
            for k, v in update.get("$inc", {}).items():
                target[k] = int(target.get(k) or 0) + int(v)

    async def update_many(self, filt, update):
        self.updated_many.append((filt, update))
        for row in self.rows:
            if all(row.get(k) == v for k, v in filt.items()):
                row.update(update.get("$set", {}))

    async def distinct(self, field, *_args, **_kwargs):
        return list({row.get(field) for row in self.rows if row.get(field) is not None})

    async def count_documents(self, filt=None):
        filt = filt or {}
        if not filt:
            return len(self.rows)
        total = 0
        for row in self.rows:
            matched = True
            for key, expected in filt.items():
                actual = row.get(key)
                if isinstance(expected, dict):
                    if "$gte" in expected and actual is not None and actual < expected["$gte"]:
                        matched = False
                        break
                elif actual != expected:
                    matched = False
                    break
            if matched:
                total += 1
        return total


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


def test_record_match_connect_click_rejects_trainer_not_in_result_set(monkeypatch):
    fake_db = SimpleNamespace(
        match_events=_Collection(find_one_result={"id": "m_1", "result_ids": ["t_1"], "campaign": "", "source": ""}),
        engagements=_Collection(),
        audit_log=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)
    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(
            server.record_match_connect_click(
                server.ConnectClickIn(match_id="m_1", trainer_id="t_2", rank=2)
            )
        )
    assert exc.value.status_code == 400


def test_create_engagement_records_event_and_infers_conversion(monkeypatch):
    intro = {
        "id": "intro_1",
        "trainer_id": "t_1",
        "match_id": "m_1",
        "campaign": "seo_richmond",
        "source": "seo",
    }
    fake_db = SimpleNamespace(
        intros=_Collection(find_one_result=intro),
        engagements=_Collection(rows=[{"intro_id": "intro_1", "kind": "website_click"}]),
        conversions=_Collection(),
        audit_log=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(
        server.create_engagement(
            server.EngagementIn(intro_id="intro_1", kind="phone_click")
        )
    )

    assert out["kind"] == "phone_click"
    assert fake_db.engagements.inserted[-1]["trainer_id"] == "t_1"
    assert len(fake_db.conversions.inserted) == 1
    inferred = fake_db.conversions.inserted[0]
    assert inferred["match_id"] == "m_1"
    assert inferred["campaign"] == "seo_richmond"
    assert inferred["attribution_source"] == "seo"
    assert inferred["billing_status"] == "pending"


def test_create_engagement_unknown_intro_raises_404(monkeypatch):
    fake_db = SimpleNamespace(
        intros=_Collection(find_one_result=None),
        engagements=_Collection(),
        conversions=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server.create_engagement(server.EngagementIn(intro_id="missing", kind="website_click")))
    assert exc.value.status_code == 404


def test_record_attribution_entry_upserts_growth_attribution(monkeypatch):
    fake_db = SimpleNamespace(
        attribution_entries=_Collection(),
        growth_attribution=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(
        server.record_attribution_entry(
            server.AttributionEntryIn(
                kind="seo_landing",
                campaign="seo_richmond",
                source="seo",
                suburb="Richmond",
                path="/melbourne/richmond",
            )
        )
    )
    assert out["ok"] is True
    assert len(fake_db.attribution_entries.inserted) == 1
    assert len(fake_db.growth_attribution.rows) == 1
    row = fake_db.growth_attribution.rows[0]
    assert row["campaign"] == "seo_richmond"
    assert row["source"] == "seo"
    assert int(row.get("entry_events_30d") or 0) == 1


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


def test_growth_attribution_summary_includes_totals(monkeypatch):
    now_ts = datetime(2026, 5, 20, tzinfo=timezone.utc).isoformat()
    fake_db = SimpleNamespace(
        growth_attribution=_Collection(
            rows=[
                {
                    "campaign": "seo_richmond",
                    "source": "seo",
                    "matched": 3,
                    "connected": 2,
                    "converted": 1,
                    "remarketing_candidates": 1,
                    "conversion_gap_candidates": 0,
                    "entry_events_30d": 4,
                    "waitlist_joins_30d": 2,
                    "updated_at": now_ts,
                }
            ]
        ),
        attribution_entries=_Collection(rows=[{"created_at": now_ts}, {"created_at": now_ts}]),
    )
    monkeypatch.setattr(server, "db", fake_db)
    out = asyncio.run(server._growth_attribution_summary())
    assert out["status"] == "ok"
    assert out["totals"]["cohort_count"] == 1
    assert out["totals"]["entry_events_30d"] == 2
    assert out["cohorts"][0]["campaign"] == "seo_richmond"


def test_growth_attribution_summary_includes_waitlist_join_cohort(monkeypatch):
    now_ts = datetime(2026, 5, 20, tzinfo=timezone.utc).isoformat()
    fake_db = SimpleNamespace(
        growth_attribution=_Collection(
            rows=[
                {
                    "campaign": "spring_launch",
                    "source": "lp",
                    "matched": 0,
                    "connected": 0,
                    "converted": 0,
                    "remarketing_candidates": 0,
                    "conversion_gap_candidates": 0,
                    "entry_events_30d": 1,
                    "waitlist_joins_30d": 3,
                    "updated_at": now_ts,
                }
            ]
        ),
        attribution_entries=_Collection(rows=[{"created_at": now_ts}]),
    )
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(server._growth_attribution_summary())

    assert out["totals"]["waitlist_joins_30d"] == 3
    assert out["cohorts"][0]["campaign"] == "spring_launch"
    assert out["cohorts"][0]["source"] == "lp"


def test_growth_nurture_rolls_up_seo_match_intro_conversion_path():
    old_ts = datetime(2026, 5, 1, tzinfo=timezone.utc).isoformat()
    growth = _Collection()
    fake_db = SimpleNamespace(
        match_events=_Collection(rows=[{"id": "m_seo", "campaign": "seo_richmond", "source": "seo", "created_at": old_ts}]),
        intros=_Collection(rows=[{"id": "intro_1", "match_id": "m_seo", "created_at": old_ts, "campaign": "seo_richmond", "source": "seo"}]),
        conversions=_Collection(rows=[{"intro_id": "intro_1", "billing_status": "tracked"}]),
        growth_attribution=growth,
        system_state=_Collection(),
    )

    out = asyncio.run(engine.run_growth_nurture(fake_db))

    assert out["cohorts"] == 1
    assert out["matched"] == 1
    assert out["connected"] == 1
    assert out["converted"] == 1
    row = growth.rows[0]
    assert row["campaign"] == "seo_richmond"
    assert row["source"] == "seo"
    assert row["converted"] == 1


def test_run_billing_recovery_marks_retry_exhausted():
    intro = {
        "id": "intro_exhausted",
        "trainer_id": "t_1",
        "billing_status": "billed",
        "billing_collection_status": "payment_failed",
        "billing_retry_attempts": 3,
    }
    intros = _Collection(rows=[intro])
    fake_db = SimpleNamespace(
        intros=intros,
        trainers=_Collection(rows=[{"id": "t_1", "name": "Trainer One"}]),
        system_state=_Collection(),
    )

    out = asyncio.run(engine.run_billing_recovery(fake_db))

    assert out["retry_exhausted"] == 1
    assert intro["billing_retry_state"] == "retry_exhausted"


def test_run_billing_recovery_respects_backoff_without_retry(monkeypatch):
    now_ts = datetime.now(timezone.utc).isoformat()
    intro = {
        "id": "intro_waiting",
        "trainer_id": "t_1",
        "billing_status": "billed",
        "billing_collection_status": "payment_failed",
        "billing_retry_attempts": 0,
        "billing_last_retry_at": now_ts,
    }
    intros = _Collection(rows=[intro])
    fake_db = SimpleNamespace(
        intros=intros,
        trainers=_Collection(rows=[{"id": "t_1", "name": "Trainer One"}]),
        system_state=_Collection(),
    )

    async def _unexpected_retry(*_args, **_kwargs):
        raise AssertionError("bill_intro should not be called while backoff is active")

    monkeypatch.setattr(engine.stripe_billing, "bill_intro", _unexpected_retry)

    out = asyncio.run(engine.run_billing_recovery(fake_db))

    assert out["waiting_backoff"] == 1
    assert intro.get("billing_retry_state") != "retry_sent"


def test_process_discovery_queue_writes_discovery_heartbeat():
    pending = {
        "id": "dq_1",
        "url": "https://example.com/no-signal",
        "hint_name": "Candidate",
        "hint_suburb": "Carlton",
        "status": "pending",
    }

    class _Ai:
        async def score_trainer(self, _payload):
            return {"confidence": 0.3, "reasoning": "insufficient signal", "signals": [], "model": "heuristic"}

        @staticmethod
        def status_for_score(_score):
            return "hold"

    fake_db = SimpleNamespace(
        discovery_queue=_Collection(rows=[pending]),
        trainers=_Collection(rows=[]),
        system_state=_Collection(rows=[]),
    )

    out = asyncio.run(engine.process_discovery_queue(fake_db, _Ai(), batch=1))

    assert out["handled"] == 1
    assert out["discarded"] == 1
    assert fake_db.discovery_queue.rows[0]["status"] == "discarded"
    heartbeat = next(row for row in fake_db.system_state.rows if row.get("key") == "discovery")
    assert heartbeat["handled"] == 1
    assert heartbeat["discarded"] == 1
    assert heartbeat["promoted"] == 0
    assert heartbeat["duplicates"] == 0
    assert heartbeat.get("last_run")


def test_ingest_sources_writes_source_ingestion_heartbeat(monkeypatch):
    async def _fake_ingest(_db):
        return {"ok": True, "sources": 1, "failed_sources": 0, "queued": 2, "reason_codes": ["source_ok"]}

    fake_db = SimpleNamespace(system_state=_Collection(rows=[]))
    monkeypatch.setattr(engine.automation_service, "ingest_discovery_sources", _fake_ingest)

    out = asyncio.run(engine.ingest_sources(fake_db))

    assert out["ok"] is True
    heartbeat = next(row for row in fake_db.system_state.rows if row.get("key") == "source_ingestion")
    assert heartbeat["sources"] == 1
    assert heartbeat["failed_sources"] == 0
    assert heartbeat["queued"] == 2
    assert heartbeat["reason_codes"] == ["source_ok"]
    assert heartbeat.get("last_run")


def test_ingest_discovery_sources_recovers_after_failure(monkeypatch):
    class _FailingResponse:
        status_code = 500
        text = ""

        def raise_for_status(self):
            raise RuntimeError("boom")

    class _OkResponse:
        status_code = 200
        text = '<a href="https://trainer.example.com/dog-training">Profile</a>'

        def raise_for_status(self):
            return None

    state = {"phase": "fail"}

    def _flip_get(*_args, **_kwargs):
        if state["phase"] == "fail":
            return _FailingResponse()
        return _OkResponse()

    fake_db = SimpleNamespace(
        source_ingestion_state=_Collection(),
        discovery_queue=_Collection(),
    )

    monkeypatch.setenv("DISCOVERY_SOURCE_URLS", "https://source.example.com")
    monkeypatch.setenv("SOURCE_INGEST_FAILURE_SUPPRESS_AFTER", "3")
    monkeypatch.setenv("SOURCE_INGEST_SUPPRESS_HOURS", "24")
    monkeypatch.setattr(automation.requests, "get", _flip_get)

    first = asyncio.run(automation.ingest_discovery_sources(fake_db))
    state["phase"] = "ok"
    second = asyncio.run(automation.ingest_discovery_sources(fake_db))

    assert first["failed_sources"] == 1
    assert second["failed_sources"] == 0
    source_row = fake_db.source_ingestion_state.rows[0]
    assert int(source_row.get("consecutive_failures") or 0) == 0
    assert source_row.get("last_error") == ""
    assert source_row.get("suppressed_until") == ""
    assert source_row.get("last_ok_at")
    assert second["queued"] == 1
    assert fake_db.discovery_queue.rows[0]["status"] == "pending"
