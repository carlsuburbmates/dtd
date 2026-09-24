from __future__ import annotations

import asyncio
import importlib.metadata as importlib_metadata
import inspect
import os
import sys
import types
import typing
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
import pydantic.networks as pydantic_networks
from pydantic import BaseModel, ValidationError

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017/test")
os.environ.setdefault("DB_NAME", "dtd_test")

if "motor.motor_asyncio" not in sys.modules:
    motor_mod = types.ModuleType("motor")
    motor_asyncio_mod = types.ModuleType("motor.motor_asyncio")

    class _FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def __getitem__(self, _name):
            return SimpleNamespace()

    motor_asyncio_mod.AsyncIOMotorClient = _FakeClient
    sys.modules["motor"] = motor_mod
    sys.modules["motor.motor_asyncio"] = motor_asyncio_mod

if "pymongo" not in sys.modules:
    pymongo_mod = types.ModuleType("pymongo")
    pymongo_errors_mod = types.ModuleType("pymongo.errors")

    class _ReturnDocument:
        AFTER = "after"
        BEFORE = "before"

    class _DuplicateKeyError(Exception):
        pass

    pymongo_mod.ReturnDocument = _ReturnDocument
    pymongo_errors_mod.DuplicateKeyError = _DuplicateKeyError
    sys.modules["pymongo"] = pymongo_mod
    sys.modules["pymongo.errors"] = pymongo_errors_mod

if "email_validator" not in sys.modules:
    email_validator_mod = types.ModuleType("email_validator")

    class _EmailNotValidError(ValueError):
        pass

    class _ValidatedEmail:
        def __init__(self, email: str):
            self.normalized = email
            self.local_part = email.split("@", 1)[0]

    def _validate_email(email, *_args, **_kwargs):
        if "@" not in str(email) or str(email).startswith("@") or str(email).endswith("@"):
            raise _EmailNotValidError("invalid email")
        return _ValidatedEmail(email)

    email_validator_mod.EmailNotValidError = _EmailNotValidError
    email_validator_mod.validate_email = _validate_email
    email_validator_mod.__version__ = "2.0.0"
    sys.modules["email_validator"] = email_validator_mod

_original_version = importlib_metadata.version


def _patched_version(distribution_name: str) -> str:
    if distribution_name == "email-validator":
        return "2.0.0"
    return _original_version(distribution_name)


importlib_metadata.version = _patched_version
pydantic_networks.version = _patched_version

import server


def test_first_leash_capture_is_not_a_main_api_route():
    paths = {route.path for route in server.app.routes}
    assert "/api/first-leash" not in paths
    assert "/api/owner-waitlist" in paths


def test_seo_generation_thresholds_fail_closed_when_not_explicitly_configured(monkeypatch):
    monkeypatch.delenv("SEO_MIN_PUBLISHED_TRAINERS", raising=False)
    monkeypatch.delenv("SEO_MIN_CONTENT_WORDS", raising=False)
    assert server._configured_positive_int("SEO_MIN_PUBLISHED_TRAINERS") is None
    assert server._configured_positive_int("SEO_MIN_CONTENT_WORDS") is None


def test_unknown_seo_slug_is_rejected_before_database_access():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(server.get_seo("not-a-canonical-melbourne-suburb"))
    assert exc_info.value.status_code == 404


class _Trainers:
    async def distinct(self, _field, _query):
        return ["Carlton", "Richmond"]


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    async def to_list(self, _n):
        return list(self.rows)


class _Collection:
    def __init__(self, rows=None, aggregate_rows=None):
        self.rows = list(rows or [])
        self.aggregate_rows = list(aggregate_rows or [])
        self.inserted = []
        self.updated = []

    def find(self, *_args, **_kwargs):
        return _Cursor(self.rows)

    async def find_one(self, filt=None, *_args, **_kwargs):
        filt = filt or {}
        for row in self.rows:
            if all(row.get(k) == v for k, v in filt.items()):
                return row
        return None

    async def insert_one(self, doc):
        self.inserted.append(doc)
        self.rows.append(doc)

    async def update_one(self, filt, update, upsert=False):
        self.updated.append((filt, update, upsert))
        row = await self.find_one(filt)
        if row:
            row.update(update.get("$set", {}))
        elif upsert:
            doc = dict(filt)
            doc.update(update.get("$set", {}))
            self.rows.append(doc)

    async def create_index(self, *_args, **_kwargs):
        return None

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
                    if "$in" in expected and actual not in expected["$in"]:
                        matched = False
                        break
                    if "$nin" in expected and actual in expected["$nin"]:
                        matched = False
                        break
                    if "$gte" in expected and actual is not None and actual < expected["$gte"]:
                        matched = False
                        break
                elif actual != expected:
                    matched = False
                    break
            if matched:
                total += 1
        return total

    def aggregate(self, *_args, **_kwargs):
        return _Cursor(self.aggregate_rows)

    async def distinct(self, field, filt=None):
        filt = filt or {}
        values = []
        for row in self.rows:
            matched = True
            for key, expected in filt.items():
                if row.get(key) != expected:
                    matched = False
                    break
            if matched and row.get(field) not in values:
                values.append(row.get(field))
        return values


def _fake_oversight_db():
    trainers = _Collection(
        rows=[
            {
                "id": "t_1",
                "name": "Trainer One",
                "suburb": "Carlton",
                "outcome_score": 0.8,
                "verification_status": "verified",
                "published": True,
                "confidence_score": 0.92,
                "billing_profile_status": "ready",
                "website": "https://trainer.example.com",
                "email": "trainer@example.com",
                "created_at": "2026-05-18T00:00:00+00:00",
                "updated_at": "2026-05-20T00:00:00+00:00",
                "intros_30d": 2,
                "conversions_30d": 1,
                "via_submission_id": "sub_1",
            }
        ]
    )
    intros = _Collection(
        rows=[
            {
                "id": "intro_1",
                "trainer_id": "t_1",
                "billing_status": "billed",
                "intro_fee_cents": 500,
                "billing_collection_status": "paid",
                "created_at": "2026-05-12T00:00:00+00:00",
            }
        ],
        aggregate_rows=[{"_id": "paid", "n": 1}],
    )
    conversions = _Collection(
        rows=[
            {
                "billing_status": "billed",
                "fee_cents": 0,
                "created_at": "2026-05-12T00:00:00+00:00",
            }
        ]
    )
    submissions = _Collection(
        rows=[
            {
                "id": "sub_1",
                "name": "Trainer One",
                "status": "held",
                "created_at": "2026-05-19T00:00:00+00:00",
                "submitter_notification_status": "sent",
            }
        ]
    )
    notification_events = _Collection(
        rows=[
            {
                "id": "note_1",
                "target_kind": "submission",
                "target_id": "sub_1",
                "kind": "submission_update",
                "status": "sent",
                "attempt": 1,
                "http_status": 202,
                "provider": "resend",
                "created_at": "2026-05-20T00:00:00+00:00",
            }
        ]
    )
    outreach_events = _Collection(
        rows=[
            {
                "id": "out_1",
                "intro_id": "intro_1",
                "kind": "t7_hire_check",
                "provider": "resend",
                "provider_id": "re_out_1",
                "status": "failed",
                "email": "owner@example.com",
                "created_at": "2026-05-19T12:00:00+00:00",
                "http_status": 500,
            }
        ]
    )
    owner_waitlist_events = _Collection(
        rows=[
            {
                "id": "wle_1",
                "event_type": "owner_waitlist_duplicate",
                "status": "duplicate",
                "email_norm": "owner@example.com",
                "suburb_norm": "carlton",
                "created_at": "2026-05-20T00:00:00+00:00",
            }
        ]
    )
    owner_waitlist = _Collection(
        rows=[
            {
                "id": "wl_1",
                "email_norm": "owner@example.com",
                "suburb_norm": "carlton",
                "suburb": "Carlton",
                "status": "active",
                "created_at": "2026-05-19T00:00:00+00:00",
            }
        ]
    )
    empty = _Collection(rows=[])
    system_state = _Collection(
        rows=[
            {"key": "health", "alerts": []},
            {"key": "ranking"},
            {"key": "pricing"},
            {"key": "verification"},
            {"key": "discovery"},
            {"key": "inference"},
            {"key": "source_ingestion"},
            {"key": "outreach"},
            {"key": "billing_recovery"},
            {"key": "nurture"},
            {"key": "reactivation_route"},
        ]
    )
    return SimpleNamespace(
        intros=intros,
        conversions=conversions,
        engagements=empty,
        submissions=submissions,
        discovery_queue=empty,
        pricing_state=empty,
        trainers=trainers,
        audit_log=empty,
        config_snapshots=empty,
        system_state=system_state,
        source_ingestion_state=empty,
        reactivation_candidates=empty,
        outreach_events=outreach_events,
        notification_events=notification_events,
        owner_waitlist=owner_waitlist,
        owner_waitlist_events=owner_waitlist_events,
        ops_case_states=_Collection(rows=[]),
    )


def _fake_startup_db():
    coll = _Collection(rows=[])
    return SimpleNamespace(
        trainers=_Collection(rows=[]),
        intros=_Collection(rows=[]),
        conversions=_Collection(rows=[]),
        engagements=_Collection(rows=[]),
        submissions=coll,
        audit_log=coll,
        pricing_state=coll,
        system_state=coll,
        discovery_queue=_Collection(rows=[]),
        stripe_events=coll,
        config_snapshots=coll,
        outreach_events=coll,
        notification_events=coll,
        ops_case_states=coll,
        auth_attempts=coll,
        phase_readiness_snapshots=coll,
        phase_transition_decisions=coll,
        owner_waitlist=coll,
        owner_waitlist_events=coll,
    )


def test_config_exposes_public_matching_flag_enabled_by_default(monkeypatch):
    fake_db = SimpleNamespace(trainers=_Trainers())
    monkeypatch.setattr(server, "db", fake_db)

    payload = asyncio.run(server.config())

    assert payload["public_matching_enabled"] is True
    assert payload["public_launch_phase"] == "live_matching"
    assert payload["public_emphasis"] == "live_matching"
    assert payload["trainer_onboarding_open"] is True
    assert payload["owner_waitlist_mode"] == "passive_only"
    assert "Carlton" in payload["suburbs"]
    assert payload["suburb_count"] == 539
    assert payload["suburb_catalogue_version"] == "v1"
    assert payload["suburb_catalogue_source"] == "static_catalogue_fallback"


def test_config_public_matching_unaffected_by_legacy_disabled_env(monkeypatch):
    fake_db = SimpleNamespace(trainers=_Trainers())
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("PUBLIC_MATCHING_ENABLED", "0")
    monkeypatch.setenv("PUBLIC_MODE", "waitlist_only")

    payload = asyncio.run(server.config())

    assert payload["public_matching_enabled"] is True


def test_config_exposes_monetization_defaults_without_claim_state_dependency(monkeypatch):
    fake_db = SimpleNamespace(trainers=_Trainers())
    monkeypatch.setattr(server, "db", fake_db)

    payload = asyncio.run(server.config())

    assert payload["public_monetization_copy_mode"] == "flat_subscription"
    assert payload["public_hide_legacy_intro_fee_copy"] is True
    assert payload["public_show_founding_profile_copy"] is False

    # No dependency on claim_state or legacy STATE_0-STATE_4 marketing fields
    assert "claim_state_model_enabled" not in payload
    assert "claim_state_current" not in payload
    assert "claim_enforcement_mode" not in payload
    assert "claim_block_melbourne_wide_below_state_2" not in payload


def test_config_endpoint_is_strictly_read_only_and_does_not_mutate_db(monkeypatch):
    class FakeSystemState:
        def __init__(self):
            self.writes = []

        async def find_one(self, filt, projection=None):
            return {"key": "launch_phase_state", "current_phase": "supply_first"}

        async def insert_one(self, doc):
            self.writes.append(("insert", doc))

        async def update_one(self, filt, update, upsert=False):
            self.writes.append(("update", filt, update))

    system_state = FakeSystemState()
    fake_db = SimpleNamespace(trainers=_Trainers(), system_state=system_state)
    monkeypatch.setattr(server, "db", fake_db)

    payload = asyncio.run(server.config())

    assert len(system_state.writes) == 0
    assert payload["public_launch_phase"] == "live_matching"
    assert payload["public_matching_enabled"] is True
    assert payload["public_emphasis"] == "live_matching"
    assert payload["public_monetization_copy_mode"] == "flat_subscription"


def test_startup_skips_seeds_by_default(monkeypatch):
    fake_db = _fake_startup_db()
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.delenv("ENABLE_STARTUP_SEEDS", raising=False)

    calls = {"trainers": 0, "discovery": 0}

    async def _seed_trainers():
        calls["trainers"] += 1

    async def _seed_discovery():
        calls["discovery"] += 1

    monkeypatch.setattr(server, "_seed_if_empty", _seed_trainers)
    monkeypatch.setattr(server, "_seed_discovery_if_empty", _seed_discovery)
    monkeypatch.setattr(
        server.runtime_control,
        "resolve_loop_runtime",
        lambda process_role: server.runtime_control.LoopRuntimeConfig(
            process_role=process_role,
            loop_owner="none",
            source="test",
            should_schedule_loops=False,
            lease_enabled=False,
            lease_ttl_s=120,
            lease_renew_s=30,
            owner_id="test-owner",
        ),
    )

    asyncio.run(server.on_startup(process_role="api", allow_loop_schedule=False))

    assert calls == {"trainers": 0, "discovery": 0}


def test_startup_seeds_only_from_api_when_enabled(monkeypatch):
    fake_db = _fake_startup_db()
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("ENABLE_STARTUP_SEEDS", "1")

    calls = {"trainers": 0, "discovery": 0}

    async def _seed_trainers():
        calls["trainers"] += 1

    async def _seed_discovery():
        calls["discovery"] += 1

    monkeypatch.setattr(server, "_seed_if_empty", _seed_trainers)
    monkeypatch.setattr(server, "_seed_discovery_if_empty", _seed_discovery)
    monkeypatch.setattr(
        server.runtime_control,
        "resolve_loop_runtime",
        lambda process_role: server.runtime_control.LoopRuntimeConfig(
            process_role=process_role,
            loop_owner="none",
            source="test",
            should_schedule_loops=False,
            lease_enabled=False,
            lease_ttl_s=120,
            lease_renew_s=30,
            owner_id="test-owner",
        ),
    )

    asyncio.run(server.on_startup(process_role="worker", allow_loop_schedule=False))
    assert calls == {"trainers": 0, "discovery": 0}

    asyncio.run(server.on_startup(process_role="api", allow_loop_schedule=False))
    assert calls == {"trainers": 1, "discovery": 1}


def test_match_gate_default_and_legacy_env_allows(monkeypatch):
    trainers = _Collection(
        rows=[
            {
                "id": "t_1",
                "name": "Trainer One",
                "suburb": "Carlton",
                "region": "Greater Melbourne",
                "published": True,
                "outcome_score": 0.6,
                "billing_profile_status": "ready",
            }
        ]
    )
    fake_db = SimpleNamespace(
        trainers=trainers,
        match_events=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("PUBLIC_MATCHING_ENABLED", "0")
    monkeypatch.setenv("PUBLIC_MODE", "0")

    async def _fake_match(_description, _pool):
        return [{"trainer_id": "t_1", "score": 0.9, "reasoning": "best fit"}]

    async def _fake_decorate(rows):
        return rows

    monkeypatch.setattr(server.ai_service, "match_trainers", _fake_match)
    monkeypatch.setattr(server, "_decorate_with_pricing", _fake_decorate)

    payload = server.InstantMatchIn(
        description="leash reactivity",
        suburb="Carlton",
        consent_match_processing=True,
    )
    out = asyncio.run(server.instant_match(payload))
    assert out["matches"][0]["id"] == "t_1"


def test_diagnostic_paid_tier_breaks_only_comparable_fit_band():
    rows = [
        {"id": "free_top", "name": "Free Top", "tier": "claimed", "match_score": 0.90, "outcome_score": 0.50},
        {"id": "pro_close", "name": "Pro Close", "tier": "pro", "match_score": 0.86, "outcome_score": 0.50},
        {"id": "citywide_far", "name": "Citywide Far", "tier": "citywide", "match_score": 0.80, "outcome_score": 0.50},
    ]

    ranked = server._sort_diagnostic_matches(rows)

    assert [row["id"] for row in ranked] == ["pro_close", "free_top", "citywide_far"]


def test_diagnostic_paid_tier_has_no_influence_outside_tie_band():
    rows = [
        {"id": "free_best", "name": "Free Best", "tier": "claimed", "match_score": 0.92, "outcome_score": 0.50},
        {"id": "citywide_lower", "name": "Citywide Lower", "tier": "citywide", "match_score": 0.80, "outcome_score": 0.50},
    ]

    ranked = server._sort_diagnostic_matches(rows)

    assert [row["id"] for row in ranked] == ["free_best", "citywide_lower"]


def test_intro_gate_default_and_legacy_env_allows(monkeypatch):
    trainer = {
        "id": "t_1",
        "name": "Trainer One",
        "suburb": "Carlton",
        "region": "Greater Melbourne",
        "published": True,
        "website": "https://trainer.example.com",
        "phone": "0400000000",
        "email": "trainer@example.com",
    }
    fake_db = SimpleNamespace(
        trainers=_Collection(rows=[trainer]),
        intros=_Collection(rows=[]),
        match_events=_Collection(rows=[]),
    )
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("PUBLIC_MATCHING_ENABLED", "0")
    monkeypatch.setenv("PUBLIC_MODE", "0")

    async def _noop_audit(*_args, **_kwargs):
        return None

    async def _fake_fraud(_db, _ip, _trainer_id, _email):
        return {"delivery_status": "delivered", "fraud_status": "clear", "reasons": []}

    async def _unexpected_bill_intro(*_args, **_kwargs):
        raise AssertionError("intros must not create Stripe invoices")

    async def _fake_notify(_db, _trainer_doc, _intro):
        return None

    monkeypatch.setattr(server, "_audit", _noop_audit)
    monkeypatch.setattr(server.fraud_service, "evaluate_intro", _fake_fraud)
    monkeypatch.setattr(server.stripe_billing, "bill_intro", _unexpected_bill_intro)
    monkeypatch.setattr(server.notifications_service, "notify_trainer_new_intro", _fake_notify)

    payload = server.IntroIn(
        trainer_id="t_1",
        description="help",
        user_email="owner@example.com",
        user_name="Owner",
        consent_contact_release=True,
        consent_outcome_tracking=True,
    )
    req = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})
    out = asyncio.run(server.create_intro(payload, req, idempotency_key=""))
    assert out["trainer_id"] == "t_1"
    assert out["delivery_status"] == "delivered"
    assert "intro_fee_cents" not in out
    assert out["contact"]["email"] == "trainer@example.com"


def test_match_gate_on_allows_existing_behavior(monkeypatch):
    trainers = _Collection(
        rows=[
            {
                "id": "t_1",
                "name": "Trainer One",
                "suburb": "Carlton",
                "region": "Greater Melbourne",
                "published": True,
                "outcome_score": 0.6,
                "billing_profile_status": "ready",
            }
        ]
    )
    fake_db = SimpleNamespace(
        trainers=trainers,
        match_events=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("PUBLIC_MATCHING_ENABLED", "1")

    async def _fake_match(_description, _pool):
        return [{"trainer_id": "t_1", "score": 0.9, "reasoning": "best fit"}]

    async def _fake_decorate(rows):
        return rows

    monkeypatch.setattr(server.ai_service, "match_trainers", _fake_match)
    monkeypatch.setattr(server, "_decorate_with_pricing", _fake_decorate)

    payload = server.InstantMatchIn(
        description="leash reactivity",
        suburb="Carlton",
        consent_match_processing=True,
    )
    out = asyncio.run(server.instant_match(payload))
    assert out["matches"][0]["id"] == "t_1"
    assert len(fake_db.match_events.inserted) == 1


def test_intro_gate_on_allows_existing_success_behavior(monkeypatch):
    trainer = {
        "id": "t_1",
        "name": "Trainer One",
        "suburb": "Carlton",
        "region": "Greater Melbourne",
        "published": True,
        "website": "https://trainer.example.com",
        "phone": "0400000000",
        "email": "trainer@example.com",
    }
    fake_db = SimpleNamespace(
        trainers=_Collection(rows=[trainer]),
        intros=_Collection(rows=[]),
        match_events=_Collection(rows=[]),
    )
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setenv("PUBLIC_MATCHING_ENABLED", "1")

    async def _noop_audit(*_args, **_kwargs):
        return None

    async def _fake_fraud(_db, _ip, _trainer_id, _email):
        return {"delivery_status": "delivered", "fraud_status": "clear", "reasons": []}

    async def _unexpected_bill_intro(*_args, **_kwargs):
        raise AssertionError("intros must not create Stripe invoices")

    async def _fake_notify(_db, _trainer_doc, _intro):
        return None

    monkeypatch.setattr(server, "_audit", _noop_audit)
    monkeypatch.setattr(server.fraud_service, "evaluate_intro", _fake_fraud)
    monkeypatch.setattr(server.stripe_billing, "bill_intro", _unexpected_bill_intro)
    monkeypatch.setattr(server.notifications_service, "notify_trainer_new_intro", _fake_notify)

    payload = server.IntroIn(
        trainer_id="t_1",
        description="help",
        user_email="owner@example.com",
        user_name="Owner",
        consent_contact_release=True,
        consent_outcome_tracking=True,
    )
    req = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})
    out = asyncio.run(server.create_intro(payload, req, idempotency_key=""))
    assert out["trainer_id"] == "t_1"
    assert out["delivery_status"] == "delivered"
    assert "intro_fee_cents" not in out
    assert out["contact"]["email"] == "trainer@example.com"


def test_public_trainer_payload_hides_contact_until_consented_intro():
    public = server._public_trainer_payload({
        "id": "t_1",
        "name": "Trainer One",
        "tier": "claimed",
        "email": "trainer@example.com",
        "phone": "0400000000",
        "website": "https://trainer.example.com",
        "booking_url": "https://booking.example.com",
        "claim_status": "claimed",
    })

    assert public["id"] == "t_1"
    assert public["claim_status"] == "claimed"
    assert "email" not in public
    assert "phone" not in public
    assert "website" not in public
    assert "booking_url" not in public


def test_public_trainer_payload_rejects_unsafe_historical_urls():
    public = server._public_trainer_payload({
        "id": "t_1",
        "name": "Trainer One",
        "tier": "pro",
        "website": "javascript:alert(document.domain)",
        "booking_url": "data:text/html,unsafe",
        "image_url": "javascript:alert(document.domain)",
        "gallery_images": ["https://images.example.com/one.jpg", "javascript:alert(1)"],
    })

    assert "website" not in public
    assert "booking_url" not in public
    assert "image_url" not in public
    assert public["gallery_images"] == ["https://images.example.com/one.jpg"]


def test_released_contact_payload_rejects_unsafe_historical_website():
    contact = server._released_contact_payload({
        "name": "Trainer One",
        "website": "javascript:alert(document.domain)",
        "phone": "0400000000",
        "email": "trainer@example.com",
    })

    assert contact["website"] is None
    assert contact["phone"] == "0400000000"
    assert contact["email"] == "trainer@example.com"


@pytest.mark.parametrize("field", ["website", "booking_url", "image_url", "source_evidence_url"])
def test_submission_rejects_unsafe_public_urls(field):
    payload = {
        "name": "Trainer One",
        "suburb": "Carlton",
        "consent_public_listing": True,
        "consent_information_accuracy": True,
        field: "javascript:alert(document.domain)",
    }

    with pytest.raises(ValidationError):
        server.SubmissionIn(**payload)


def test_directory_returns_public_safe_ranked_profiles(monkeypatch):
    trainers = _Collection(rows=[
        {"id": "basic", "name": "Basic", "region": "Greater Melbourne", "published": True, "tier": "basic", "email": "private@example.com"},
        {"id": "pro", "name": "Pro", "region": "Greater Melbourne", "published": True, "tier": "pro", "verification_status": "verified", "website": "https://pro.example.com", "booking_url": "https://book.example.com"},
    ])
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers))

    out = asyncio.run(server.list_trainers(suburb=None, category=None, limit=60))

    assert [row["id"] for row in out["trainers"]] == ["pro", "basic"]
    assert out["trainers"][0]["website"] == "https://pro.example.com"
    assert out["trainers"][0]["booking_url"] == "https://book.example.com"
    assert "email" not in out["trainers"][1]


def test_intro_requires_owner_identity_and_valid_contact():
    with pytest.raises(ValidationError):
        server.IntroIn(
            trainer_id="t_1",
            description="help with reactivity",
            consent_contact_release=True,
            consent_outcome_tracking=True,
        )


def test_intro_idempotency_key_cannot_release_different_trainer_contact(monkeypatch):
    trainers = _Collection(rows=[
        {"id": "t_2", "name": "Trainer Two", "region": "Greater Melbourne", "published": True, "email": "two@example.com"},
    ])
    intros = _Collection(rows=[{"id": "intro_1", "trainer_id": "t_1", "user_email": "owner@example.com", "idempotency_key": "same-key"}])
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, intros=intros))
    payload = server.IntroIn(
        trainer_id="t_2",
        description="help with reactivity",
        user_email="owner@example.com",
        user_name="Owner",
        consent_contact_release=True,
        consent_outcome_tracking=True,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.create_intro(payload, SimpleNamespace(client=None, headers={}), idempotency_key="same-key"))
    assert exc.value.status_code == 409


def test_claim_validate_non_blocking_compatibility_neutral_response():
    out = asyncio.run(server.validate_claim(claim="We service Melbourne-wide"))

    assert out["ok"] is True
    assert out["allowed"] is True
    assert out["valid"] is True
    assert out["status"] == "valid"
    assert out["normalized_claim"] == "We service Melbourne-wide"
    assert "ts" in out
    # Removed legacy gating fields
    assert "would_block" not in out
    assert "enforced" not in out
    assert "claim_policy" not in out


@pytest.mark.parametrize("state", ["STATE_0", "STATE_1", "STATE_2", "STATE_3", "STATE_4"])
@pytest.mark.parametrize("claim_text", ["melbourne-wide", "available across melbourne", "all melbourne"])
def test_claim_validate_never_blocks_under_any_state_or_claim(state, claim_text):
    out = asyncio.run(server.validate_claim(claim=claim_text, state=state))
    assert out["ok"] is True
    assert out["allowed"] is True
    assert out["valid"] is True


def test_claim_validate_has_no_claim_state_dependency(monkeypatch):
    out = asyncio.run(server.validate_claim(claim="Positive reinforcement trainer"))
    assert out["ok"] is True
    assert out["allowed"] is True


def test_guardrail_invariant_match_and_intro_routes_do_not_require_public_matching():
    src_match = inspect.getsource(server.instant_match)
    src_intro = inspect.getsource(server.create_intro)
    assert "_require_public_matching" not in src_match
    assert "_require_public_matching" not in src_intro


def test_guardrail_invariant_intro_flow_never_calls_bill_intro():
    src = inspect.getsource(server.create_intro)
    assert "stripe_billing.bill_intro" not in src


def test_guardrail_invariant_oversight_route_requires_auth_dependency():
    route = None
    for candidate in server.app.routes:
        if str(getattr(candidate, "path", "")) == "/api/oversight" and "GET" in set(getattr(candidate, "methods", set()) or set()):
            route = candidate
            break
    assert route is not None, "Expected GET /api/oversight route"

    dependant = getattr(route, "dependant", None)
    assert dependant is not None, "Expected FastAPI dependant metadata on oversight route"
    dep_calls = {getattr(dep, "call", None) for dep in (dependant.dependencies or [])}
    assert server.require_oversight in dep_calls


def test_guardrail_invariant_server_has_no_public_matching_enabled_symbol_or_dependency():
    """Verify PUBLIC_MATCHING_ENABLED is removed as a runtime symbol and has no dependency in server.py."""
    assert not hasattr(server, "PUBLIC_MATCHING_ENABLED")
    src = inspect.getsource(server)
    assert "PUBLIC_MATCHING_ENABLED" not in src


def test_persisted_legacy_false_launch_phase_state_is_migrated_and_does_not_block_matching(monkeypatch):
    legacy_row = {
        "key": "launch_phase_state",
        "current_phase": "supply_first",
        "matching_exposure_enabled": False,
        "public_matching_enabled": False,
        "public_emphasis": "waitlist_first",
        "trainer_onboarding_open": True,
        "owner_waitlist_mode": "active",
        "evidence_window_mode": "30_day_prelaunch_evidence_window",
        "requires_owner_review_for_phase_change": True,
        "active_regions": ["Greater Melbourne"],
    }
    system_state_coll = _Collection(rows=[legacy_row.copy()])
    trainers_coll = _Collection(
        rows=[
            {
                "id": "t_1",
                "name": "Trainer One",
                "suburb": "Carlton",
                "region": "Greater Melbourne",
                "published": True,
                "outcome_score": 0.9,
                "billing_profile_status": "ready",
                "website": "https://example.com",
                "phone": "0400000000",
                "email": "trainer@example.com",
            }
        ]
    )
    fake_db = SimpleNamespace(
        system_state=system_state_coll,
        trainers=trainers_coll,
        match_events=_Collection(),
        intros=_Collection(),
        conversions=_Collection(),
        engagements=_Collection(),
        phase_readiness_snapshots=_Collection(),
        phase_transition_decisions=_Collection(),
        audit_log=_Collection(),
    )
    monkeypatch.setattr(server, "db", fake_db)

    # 1. State migration on retrieval
    phase_state = asyncio.run(server._get_or_create_launch_phase_state())
    assert phase_state["matching_exposure_enabled"] is True
    assert phase_state["public_matching_enabled"] is True
    assert phase_state["public_emphasis"] == "live_matching"

    # Persisted row in system_state must be migrated
    persisted = asyncio.run(system_state_coll.find_one({"key": "launch_phase_state"}))
    assert persisted["matching_exposure_enabled"] is True
    assert persisted["public_matching_enabled"] is True
    assert persisted["public_emphasis"] == "live_matching"

    # 2. Readiness snapshot derives open matching from target state, never env/constant
    readiness = asyncio.run(server._build_phase_readiness_snapshot(phase_state))
    assert readiness["matching_exposure_enabled"] is True
    assert readiness["public_emphasis"] == "live_matching"

    # 3. Transition baseline derives open matching from target state
    decisions = asyncio.run(server._ensure_phase_transition_baseline(phase_state, readiness))
    assert len(decisions) >= 1
    assert decisions[0]["public_matching_enabled"] is True

    # 4. Matching is not blocked by legacy row
    async def _fake_match(_description, _pool):
        return [{"trainer_id": "t_1", "score": 0.9, "reasoning": "best fit"}]

    async def _fake_decorate(rows):
        return rows

    monkeypatch.setattr(server.ai_service, "match_trainers", _fake_match)
    monkeypatch.setattr(server, "_decorate_with_pricing", _fake_decorate)

    payload = server.InstantMatchIn(
        description="leash reactivity",
        suburb="Carlton",
        consent_match_processing=True,
    )
    match_out = asyncio.run(server.instant_match(payload))
    assert match_out["matches"][0]["id"] == "t_1"

    # 5. Contact release / intro creation is not blocked by legacy row
    async def _noop_audit(*_args, **_kwargs):
        return None

    async def _fake_fraud(_db, _ip, _trainer_id, _email):
        return {"delivery_status": "delivered", "fraud_status": "clear", "reasons": []}

    async def _unexpected_bill_intro(*_args, **_kwargs):
        raise AssertionError("intros must not create Stripe invoices")

    async def _fake_notify(_db, _trainer_doc, _intro):
        return None

    monkeypatch.setattr(server, "_audit", _noop_audit)
    monkeypatch.setattr(server.fraud_service, "evaluate_intro", _fake_fraud)
    monkeypatch.setattr(server.stripe_billing, "bill_intro", _unexpected_bill_intro)
    monkeypatch.setattr(server.notifications_service, "notify_trainer_new_intro", _fake_notify)

    intro_payload = server.IntroIn(
        trainer_id="t_1",
        description="help with my dog",
        user_email="owner@example.com",
        user_name="Owner",
        consent_contact_release=True,
        consent_outcome_tracking=True,
    )
    req = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})
    intro_out = asyncio.run(server.create_intro(intro_payload, req, idempotency_key=""))
    assert intro_out["trainer_id"] == "t_1"
    assert intro_out["delivery_status"] == "delivered"
    assert "intro_fee_cents" not in intro_out
    assert intro_out["contact"]["email"] == "trainer@example.com"


def test_oversight_exposes_read_only_integrity_identity_contract(monkeypatch):
    monkeypatch.setattr(server, "db", _fake_oversight_db())

    out = asyncio.run(server.oversight(None))

    assert "claim_policy" in out
    assert "integrity" in out

    assert "dataset_identity" in out
    assert "integrity_status" in out
    assert "integrity_reason_codes" in out

    dataset = out["dataset_identity"]
    assert isinstance(dataset, dict)
    assert "list_id" in dataset
    assert "suburb_count" in dataset
    assert any(k in dataset for k in ("hash", "suburb_hash_sha256_code_name"))

    assert out["integrity_status"] in {"ok", "warn"}
    assert isinstance(out["integrity_reason_codes"], list)


def test_oversight_exposes_kpi_prelaunch_contract_fields_and_types(monkeypatch):
    monkeypatch.setattr(server, "db", _fake_oversight_db())

    out = asyncio.run(server.oversight(None))
    kpi = out.get("kpi_prelaunch")
    assert isinstance(kpi, dict), "Expected kpi_prelaunch object in oversight payload"

    assert isinstance(kpi.get("owner_waitlist_total_active"), int)
    assert isinstance(kpi.get("owner_waitlist_joins_24h"), int)
    assert isinstance(kpi.get("waitlist_suburb_coverage_count"), int)
    assert isinstance(kpi.get("published_trainer_count"), int)
    assert isinstance(kpi.get("verified_trainer_count"), int)
    assert isinstance(kpi.get("trainer_suburb_coverage_count"), int)
    assert isinstance(kpi.get("status"), str)
    assert kpi["status"] in {"ok", "warn", "unavailable"}
    assert isinstance(kpi.get("reason_codes"), list)


def test_oversight_exposes_launch_phase_and_readiness_contract(monkeypatch):
    monkeypatch.setattr(server, "db", _fake_oversight_db())

    out = asyncio.run(server.oversight(None))

    phase_state = out.get("launch_phase_state")
    readiness = out.get("phase_readiness_snapshot")
    decisions = out.get("phase_transition_decisions")

    assert isinstance(phase_state, dict)
    assert phase_state["current_phase"] == "live_matching"
    assert phase_state["public_matching_enabled"] is True
    assert phase_state["public_emphasis"] == "live_matching"
    assert phase_state["trainer_onboarding_open"] is True

    assert isinstance(readiness, dict)
    assert readiness["phase"] == "live_matching"
    assert readiness["matching_exposure_enabled"] is True
    assert readiness["public_emphasis"] == "live_matching"
    assert readiness["readiness_status"] in {"collecting_evidence", "attention_needed"}
    assert isinstance(readiness.get("recommendation"), str)
    assert isinstance(readiness.get("intro_ready_trainer_count"), int)
    assert isinstance(readiness.get("blocked_trainer_count"), int)
    assert isinstance(readiness.get("blockers_to_next_phase"), list)
    assert isinstance(readiness.get("blocker_buckets"), dict)

    assert out["launch_phase"] == "live_matching"
    assert out["public_emphasis"] == "live_matching"
    assert out["readiness_status"] == readiness["readiness_status"]
    assert out["readiness_recommendation"] == readiness["recommendation"]
    assert out["intro_ready_trainer_count"] == readiness["intro_ready_trainer_count"]
    assert out["blocked_trainer_count"] == readiness["blocked_trainer_count"]

    assert isinstance(decisions, list)


def test_oversight_exposes_growth_and_reactivation_summary_contract(monkeypatch):
    monkeypatch.setattr(server, "db", _fake_oversight_db())

    out = asyncio.run(server.oversight(None))
    growth = out.get("growth_attribution_summary")
    react = out.get("reactivation_summary")

    assert isinstance(growth, dict)
    assert isinstance(react, dict)
    assert "status" in growth
    assert "reason_codes" in growth
    assert "status" in react
    assert "reason_codes" in react


def test_oversight_exposes_operations_console_read_models(monkeypatch):
    monkeypatch.setattr(server, "db", _fake_oversight_db())

    out = asyncio.run(server.oversight(None))

    trainer_inventory = out.get("trainer_inventory")
    message_log = out.get("message_log")
    ops_cases = out.get("ops_cases")

    assert isinstance(trainer_inventory, list)
    assert trainer_inventory
    assert trainer_inventory[0]["name"] == "Trainer One"
    assert trainer_inventory[0]["source_kind"] == "submission"
    assert isinstance(trainer_inventory[0]["blocker_codes"], list)
    assert "created_at" in trainer_inventory[0]

    assert isinstance(message_log, list)
    assert message_log
    assert message_log[0]["workflow"] == "trainer submission"
    assert message_log[0]["status"] == "sent"
    assert any(row["workflow"] == "t+7 follow-up" for row in message_log)
    follow_up_row = next(row for row in message_log if row["workflow"] == "t+7 follow-up")
    assert follow_up_row["entity_label"] == "Trainer One"
    assert follow_up_row["canonical_user_type"] == "Dog owner"
    assert follow_up_row["source_kind"] == "outreach_event"
    assert follow_up_row["status"] == "failed"

    assert isinstance(ops_cases, list)
    assert ops_cases
    assert any(case["case_type"] == "trainer_submission_case" for case in ops_cases)
    assert any(case["case_type"] == "trainer_communications_case" for case in ops_cases)
    assert any(case["case_type"] == "owner_follow_up_case" for case in ops_cases)


def test_oversight_exposes_sanitised_provider_control_gaps(monkeypatch):
    monkeypatch.setattr(server, "db", _fake_oversight_db())
    monkeypatch.setenv("MONGO_URL", "configured-for-test")
    monkeypatch.setenv("RESEND_API_KEY", "configured-for-test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "configured-for-test")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "configured-for-test")
    monkeypatch.setenv("ABR_GUID", "configured-for-test")

    out = asyncio.run(server.oversight(None))

    provider_health = out["provider_health"]
    assert provider_health["status"] == "action_required"
    assert provider_health["summary"]["providers_total"] == 6
    assert all("configured-for-test" not in str(row) for row in provider_health["providers"])
    atlas = next(row for row in provider_health["providers"] if row["id"] == "atlas")
    assert atlas["runtime_status"] == "configuration_detected"
    assert atlas["management_recovery_status"] == "not_evidenced"
    assert atlas["last_verified_at"] is None
    assert any(case["case_id"] == "provider:atlas" for case in out["ops_cases"])


def test_oversight_exposes_supply_decision_support_contract(monkeypatch):
    monkeypatch.setattr(server, "db", _fake_oversight_db())

    out = asyncio.run(server.oversight(None))

    geography = out.get("ops_supply_geography")
    trends = out.get("ops_supply_trends")

    assert isinstance(geography, dict)
    assert isinstance(trends, dict)
    assert isinstance(geography.get("trainer_suburbs_top"), list)
    assert isinstance(geography.get("waitlist_suburbs_top"), list)
    assert isinstance(geography.get("demand_gaps"), list)
    assert isinstance(geography.get("trainer_suburb_coverage_count"), int)
    assert isinstance(geography.get("waitlist_suburb_coverage_count"), int)
    assert isinstance(trends.get("submissions_7d"), int)
    assert isinstance(trends.get("submitted_total"), int)
    assert isinstance(trends.get("published_trainers_7d"), int)
    assert isinstance(trends.get("published_trainers_30d"), int)
    assert isinstance(trends.get("intro_ready_now"), int)
    assert isinstance(trends.get("blocked_now"), int)
    assert isinstance(trends.get("waitlist_joins_30d"), int)
    assert trends.get("submission_pace") in {"rising", "steady", "slowing", "quiet"}
    assert trends.get("published_pace") in {"rising", "steady", "slowing", "quiet"}


def test_oversight_merges_persisted_case_review_state(monkeypatch):
    fake_db = _fake_oversight_db()
    fake_db.ops_case_states = _Collection(
        rows=[
            {
                "case_id": "submission:sub_1",
                "state": "investigating",
                "owner": "Carl",
                "note": "Checked trainer evidence.",
                "updated_at": "2026-05-21T00:00:00+00:00",
                "history": [
                    {
                        "state": "acknowledged",
                        "owner": "Carl",
                        "note": "Opened the case.",
                        "updated_at": "2026-05-20T12:00:00+00:00",
                        "actor": "ops:Carl",
                    }
                ],
            }
        ]
    )
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(server.oversight(None))
    case = next(row for row in out["ops_cases"] if row["case_id"] == "submission:sub_1")

    assert case["state"] == "investigating"
    assert case["owner"] == "Carl"
    assert case["review"]["state"] == "investigating"
    assert case["review"]["note"] == "Checked trainer evidence."
    assert case["review"]["history"][0]["state"] == "acknowledged"


def test_update_oversight_case_review_persists_state_and_history(monkeypatch):
    fake_db = _fake_oversight_db()
    monkeypatch.setattr(server, "db", fake_db)
    audit_calls = []

    async def _noop_audit(action, entity_id, before=None, after=None, actor="system"):
        audit_calls.append(
            {
                "action": action,
                "entity_id": entity_id,
                "before": before,
                "after": after,
                "actor": actor,
            }
        )

    monkeypatch.setattr(server, "_audit", _noop_audit)

    payload = server.OpsCaseReviewIn(
        state="investigating",
        owner="Carl",
        note="Reviewed the submission and kept it open.",
    )

    out = asyncio.run(server.update_oversight_case_review("submission:sub_1", payload, None))

    assert out["ok"] is True
    assert out["case"]["state"] == "investigating"
    assert out["case"]["review"]["owner"] == "Carl"
    assert out["case"]["review"]["state"] == "investigating"
    assert fake_db.ops_case_states.rows[0]["case_id"] == "submission:sub_1"
    assert fake_db.ops_case_states.rows[0]["history"][0]["note"] == "Reviewed the submission and kept it open."
    assert audit_calls[0]["action"] == "ops_case_review_updated"


def test_oversight_exposes_ops_investigation_contract(monkeypatch):
    fake_db = _fake_oversight_db()
    fake_db.intros = _Collection(
        rows=[
            {
                "id": "intro_ops_1",
                "trainer_id": "t_1",
                "billing_status": "billed",
                "billing_collection_status": "payment_failed",
                "billing_retry_state": "retry_exhausted",
                "billing_retry_attempts": 3,
                "billing_last_retry_at": "2026-05-20T00:00:00+00:00",
                "intro_fee_cents": 500,
                "created_at": "2026-05-19T00:00:00+00:00",
            }
        ],
        aggregate_rows=[{"_id": "payment_failed", "n": 1}],
    )
    fake_db.system_state = _Collection(
        rows=[
            {"key": "health", "alerts": [{"severity": "high", "type": "intro_drop", "message": "drop detected"}], "last_run": "2026-05-20T00:00:00+00:00"},
            {"key": "ranking", "last_run": "2026-05-20T00:00:30+00:00"},
            {"key": "pricing", "last_run": "2026-05-20T00:00:30+00:00"},
            {"key": "verification", "last_run": "2026-05-20T00:00:30+00:00"},
            {"key": "discovery", "last_run": "2026-05-20T00:00:30+00:00"},
            {"key": "inference", "last_run": "2026-05-20T00:00:30+00:00"},
            {"key": "source_ingestion", "last_run": "2026-05-20T00:00:30+00:00", "alerts": [{"severity": "medium", "type": "source_ingestion_failures"}]},
            {"key": "outreach", "last_run": "2026-05-20T00:00:30+00:00"},
            {"key": "billing_recovery", "last_run": "2026-05-20T00:00:30+00:00"},
            {"key": "nurture", "last_run": "2026-05-20T00:00:30+00:00"},
            {"key": "reactivation_route", "last_run": "2026-05-20T00:00:30+00:00"},
        ]
    )
    fake_db.source_ingestion_state = _Collection(
        rows=[
            {
                "source_url": "https://source.example.com",
                "consecutive_failures": 2,
                "suppressed_until": "2026-05-21T00:00:00+00:00",
                "last_error_code": "source_request_failed",
                "last_ok_at": "2026-05-19T00:00:00+00:00",
            }
        ]
    )
    fake_db.reactivation_candidates = _Collection(
        rows=[
            {
                "trainer_id": "t_1",
                "trainer_name": "Trainer One",
                "status": "open",
                "reasons": ["Billing profile has unresolved blockers."],
                "last_notified_at": "2026-05-20T00:00:00+00:00",
                "last_notification_status": "sent",
            }
        ]
    )
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(server.oversight(None))
    ops = out.get("ops_investigation")

    assert isinstance(ops, dict)
    assert isinstance(ops.get("loop_statuses"), dict)
    assert isinstance(ops.get("intro_delivery_cases"), list)
    assert isinstance(ops.get("conversion_quality_cases"), list)
    assert isinstance(ops.get("reactivation_cases"), list)
    assert isinstance(ops.get("source_ingestion_sources"), list)
    assert isinstance(ops.get("discovery_alerts"), list)
    assert ops["intro_delivery_cases"][0]["delivery_status"] == "delivered"
    assert ops["reactivation_cases"][0]["trainer_name"] == "Trainer One"
    assert ops["source_ingestion_sources"][0]["source_url"] == "https://source.example.com"
    assert ops["loop_statuses"]["ranking"]["status"] in {"ok", "investigate", "escalate", "warn"}


def test_oversight_scrubs_nested_objectids_from_live_like_payload(monkeypatch):
    bson = pytest.importorskip("bson")
    object_id = bson.ObjectId()
    fake_db = _fake_oversight_db()
    fake_db.system_state = _Collection(
        rows=[
            {"key": "health", "alerts": [{"source_id": object_id}]},
            {"key": "ranking"},
            {"key": "pricing"},
            {"key": "verification"},
            {"key": "discovery"},
            {"key": "inference"},
            {"key": "source_ingestion", "alerts": [{"job_id": object_id}]},
            {"key": "outreach"},
            {"key": "billing_recovery"},
            {"key": "nurture"},
            {"key": "reactivation_route"},
        ]
    )
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(server.oversight(None))

    assert out["alerts"][0]["source_id"] == str(object_id)
    assert out["loops"]["health"]["alerts"][0]["source_id"] == str(object_id)
    assert out["ops_investigation"]["discovery_alerts"][0]["job_id"] == str(object_id)
    json.dumps(out)


def test_oversight_excludes_legacy_intro_billing_summary(monkeypatch):
    fake_db = _fake_oversight_db()
    fake_db.intros = _Collection(
        rows=[
            {"billing_status": "billed", "intro_fee_cents": 500, "billing_collection_status": "paid", "created_at": "2026-05-12T00:00:00+00:00"},
            {"billing_status": "billed", "intro_fee_cents": 500, "billing_collection_status": "payment_failed", "created_at": "2026-05-12T00:00:00+00:00"},
            {"billing_status": "billed", "intro_fee_cents": 500, "billing_collection_status": "disputed", "created_at": "2026-05-12T00:00:00+00:00"},
            {"billing_status": "billed", "intro_fee_cents": 0, "billing_collection_status": "trial_free", "created_at": "2026-05-12T00:00:00+00:00"},
        ],
        aggregate_rows=[
            {"_id": "paid", "n": 1},
            {"_id": "payment_failed", "n": 1},
            {"_id": "disputed", "n": 1},
            {"_id": "trial_free", "n": 1},
        ],
    )
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(server.oversight(None))

    assert "billing_summary" not in out
    assert "revenue" not in out
    assert "pricing_state" not in out


def _waitlist_post_path() -> str:
    for route in server.app.routes:
        path = str(getattr(route, "path", ""))
        methods = set(getattr(route, "methods", set()) or set())
        if path.startswith("/api/") and "waitlist" in path.lower() and "POST" in methods:
            return path
    pytest.fail("No POST waitlist route found under /api/*waitlist*")


def _waitlist_post_route():
    path = _waitlist_post_path()
    for route in server.app.routes:
        if str(getattr(route, "path", "")) == path and "POST" in set(getattr(route, "methods", set()) or set()):
            return route
    pytest.fail("Unable to resolve waitlist POST route object")


def _invoke_waitlist_route(payload):
    route = _waitlist_post_route()
    endpoint = route.endpoint
    sig = inspect.signature(endpoint)
    hints = typing.get_type_hints(endpoint)
    kwargs = {}

    for name, param in sig.parameters.items():
        ann = hints.get(name, param.annotation)
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            try:
                kwargs[name] = ann(**payload)
            except ValidationError:
                return 422, None
            continue
        if name == "request":
            kwargs[name] = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})
            continue
        if param.default is inspect._empty:
            pytest.fail(f"Unsupported required waitlist route parameter: {name}")

    try:
        out = endpoint(**kwargs)
        if asyncio.iscoroutine(out):
            out = asyncio.run(out)
    except HTTPException as exc:
        return exc.status_code, exc.detail
    return 200, out


def _extract_waitlist_status(payload):
    if not isinstance(payload, dict):
        return None
    status = str(payload.get("status") or "").strip().lower()
    if status:
        return status
    if payload.get("duplicate") is True:
        return "duplicate"
    if payload.get("accepted") is True:
        return "accepted"
    return None


def _base_waitlist_payload(**overrides):
    payload = {
        "email": "owner@example.com",
        "suburb": "Carlton",
        # Provide multiple consent aliases to stay compatible with model naming.
        "consent_owner_waitlist": True,
        "consent_waitlist": True,
        "consent": True,
    }
    payload.update(overrides)
    return payload


def _make_waitlist_test_client_db():
    # Reuse existing generic collection behavior for deterministic in-memory tests.
    coll = _Collection(rows=[])
    empty = _Collection(rows=[])
    system_state = _Collection(
        rows=[
            {"key": "health", "alerts": []},
            {"key": "ranking"},
            {"key": "pricing"},
            {"key": "verification"},
            {"key": "discovery"},
            {"key": "inference"},
            {"key": "source_ingestion"},
            {"key": "outreach"},
            {"key": "billing_recovery"},
            {"key": "nurture"},
            {"key": "reactivation_route"},
        ]
    )
    db = SimpleNamespace(
        owner_waitlist=coll,
        waitlist=coll,
        owner_waitlist_events=_Collection(rows=[]),
        waitlist_events=_Collection(rows=[]),
        growth_attribution=_Collection(rows=[]),
        attribution_entries=_Collection(rows=[]),
        intros=empty,
        conversions=empty,
        engagements=empty,
        submissions=empty,
        discovery_queue=empty,
        pricing_state=empty,
        trainers=empty,
        audit_log=empty,
        config_snapshots=empty,
        system_state=system_state,
    )
    return db


def test_waitlist_valid_submission_accepted(monkeypatch):
    fake_db = _make_waitlist_test_client_db()
    monkeypatch.setattr(server, "db", fake_db)
    code, out = _invoke_waitlist_route(_base_waitlist_payload())

    assert code in {200, 201}
    status = _extract_waitlist_status(out)
    assert status in {"accepted", "created", "ok"}


def test_waitlist_missing_consent_rejected(monkeypatch):
    fake_db = _make_waitlist_test_client_db()
    monkeypatch.setattr(server, "db", fake_db)
    payload = _base_waitlist_payload(consent_owner_waitlist=False, consent_waitlist=False, consent=False)
    code, _out = _invoke_waitlist_route(payload)

    assert code == 400


def test_waitlist_invalid_email_rejected(monkeypatch):
    fake_db = _make_waitlist_test_client_db()
    monkeypatch.setattr(server, "db", fake_db)
    code, _out = _invoke_waitlist_route(_base_waitlist_payload(email="not-an-email"))

    # Pydantic validation returns 422; explicit handler may return 400.
    assert code in {400, 422}


def test_waitlist_duplicate_dedupes(monkeypatch):
    fake_db = _make_waitlist_test_client_db()
    monkeypatch.setattr(server, "db", fake_db)
    first_code, first_out = _invoke_waitlist_route(_base_waitlist_payload(email="Dup@Example.com", suburb="  Richmond "))
    second_code, second_out = _invoke_waitlist_route(_base_waitlist_payload(email="dup@example.com", suburb="richmond"))

    assert first_code in {200, 201}
    assert second_code in {200, 201}
    assert _extract_waitlist_status(second_out) in {"duplicate", "exists", "ok"}


def test_owner_waitlist_event_valid_event_accepted_with_contract_shape(monkeypatch):
    fake_db = _make_waitlist_test_client_db()
    monkeypatch.setattr(server, "db", fake_db)

    asyncio.run(
        server._record_owner_waitlist_event(
            "owner_waitlist_submitted",
            email_norm="owner@example.com",
            suburb_norm="carlton",
            status="accepted",
            reason_codes=["owner_waitlist_submitted"],
            waitlist_id="wl_123",
        )
    )

    assert len(fake_db.owner_waitlist_events.rows) == 1
    event = fake_db.owner_waitlist_events.rows[0]
    assert event["event_type"] == "owner_waitlist_submitted"
    assert event["status"] == "accepted"
    assert event["email_norm"] == "owner@example.com"
    assert event["suburb_norm"] == "carlton"
    assert event["reason_codes"] == ["owner_waitlist_submitted"]
    assert event["waitlist_id"] == "wl_123"
    assert event.get("contract_status") == "ok"
    assert event.get("contract_reason_codes") == []
    for key in ("id", "created_at"):
        assert isinstance(event.get(key), str)
        assert event[key]


def test_owner_waitlist_event_invalid_name_handled_deterministically(monkeypatch):
    fake_db = _make_waitlist_test_client_db()
    monkeypatch.setattr(server, "db", fake_db)

    asyncio.run(
        server._record_owner_waitlist_event(
            "owner_waitlist_not_in_contract",
            email_norm="owner@example.com",
            suburb_norm="fitzroy",
            status="rejected",
            reason_codes=["invalid_event_name"],
        )
    )

    assert len(fake_db.owner_waitlist_events.rows) == 1
    event = fake_db.owner_waitlist_events.rows[0]
    # Deterministic handling: event is recorded with explicit invalid-name reason, not silently dropped.
    assert event["event_type"] == "owner_waitlist_not_in_contract"
    assert event["reason_codes"] == ["invalid_event_name"]
    assert event["status"] == "rejected"
    assert event.get("contract_status") == "warn"
    contract_reason_codes = event.get("contract_reason_codes") or []
    assert "invalid_event_name" in contract_reason_codes


def test_owner_waitlist_event_required_field_defaults(monkeypatch):
    fake_db = _make_waitlist_test_client_db()
    monkeypatch.setattr(server, "db", fake_db)

    asyncio.run(
        server._record_owner_waitlist_event(
            "owner_waitlist_started",
            status="started",
        )
    )

    assert len(fake_db.owner_waitlist_events.rows) == 1
    event = fake_db.owner_waitlist_events.rows[0]
    assert event["event_type"] == "owner_waitlist_started"
    assert event["status"] == "started"
    assert event["email_norm"] == ""
    assert event["suburb_norm"] == ""
    assert event["reason_codes"] == []
    assert event["waitlist_id"] is None
    assert event.get("contract_status") == "warn"
    contract_reason_codes = set(event.get("contract_reason_codes") or [])
    assert "missing_required_field:email_norm" in contract_reason_codes
    assert "missing_required_field:suburb_norm" in contract_reason_codes


def test_oversight_waitlist_summary_fields_present(monkeypatch):
    fake_db = _make_waitlist_test_client_db()
    monkeypatch.setattr(server, "db", fake_db)

    out = asyncio.run(server.oversight(None))
    summary = out.get("owner_waitlist_summary") or out.get("waitlist_summary")
    assert isinstance(summary, dict), "Expected owner_waitlist_summary/waitlist_summary in oversight payload"

    keys = set(summary.keys())
    assert any(k in keys for k in {"total", "total_count", "waitlist_total", "total_active"})
    assert any(k in keys for k in {"recent_7d", "recent_joins_7d", "recent_joins", "joins_24h"})
    assert any(k in keys for k in {"top_suburbs", "top_suburbs_7d"})
    assert "duplicate_24h" in keys
    assert "rejected_24h" in keys
