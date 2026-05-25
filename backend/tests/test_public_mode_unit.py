from __future__ import annotations

import asyncio
import importlib.metadata as importlib_metadata
import inspect
import os
import sys
import types
import typing
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
            }
        ]
    )
    intros = _Collection(
        rows=[
            {
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
        submissions=empty,
        discovery_queue=empty,
        pricing_state=empty,
        trainers=trainers,
        audit_log=empty,
        config_snapshots=empty,
        system_state=system_state,
        source_ingestion_state=empty,
        reactivation_candidates=empty,
    )


def test_config_exposes_public_matching_flag(monkeypatch):
    fake_db = SimpleNamespace(trainers=_Trainers())
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "PUBLIC_MATCHING_ENABLED", False)

    payload = asyncio.run(server.config())

    assert payload["public_matching_enabled"] is False
    assert payload["public_launch_phase"] == "supply_first"
    assert payload["public_emphasis"] == "waitlist_first"
    assert payload["trainer_onboarding_open"] is True
    assert payload["owner_waitlist_mode"] == "passive_only"
    assert "Carlton" in payload["suburbs"]


def test_config_public_matching_flag_true(monkeypatch):
    fake_db = SimpleNamespace(trainers=_Trainers())
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "PUBLIC_MATCHING_ENABLED", True)

    payload = asyncio.run(server.config())

    assert payload["public_matching_enabled"] is True


def test_config_exposes_claim_and_monetization_safe_defaults(monkeypatch):
    fake_db = SimpleNamespace(trainers=_Trainers())
    monkeypatch.setattr(server, "db", fake_db)

    payload = asyncio.run(server.config())

    assert payload["public_monetization_copy_mode"] == "legacy_intro_fee"
    assert payload["public_hide_legacy_intro_fee_copy"] is False
    assert payload["public_show_founding_profile_copy"] is False

    assert payload["claim_state_model_enabled"] is False
    assert payload["claim_state_current"] == "STATE_0"
    assert payload["claim_enforcement_mode"] == "report_only"
    assert payload["claim_block_melbourne_wide_below_state_2"] is True


def test_match_gate_off_denies(monkeypatch):
    monkeypatch.setattr(server, "PUBLIC_MATCHING_ENABLED", False)
    payload = server.InstantMatchIn(
        description="leash reactivity",
        suburb="Carlton",
        consent_match_processing=True,
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.instant_match(payload))
    assert exc.value.status_code == 403
    assert "education-first prelaunch" in str(exc.value.detail)


def test_intro_gate_off_denies(monkeypatch):
    monkeypatch.setattr(server, "PUBLIC_MATCHING_ENABLED", False)
    payload = server.IntroIn(
        trainer_id="t_1",
        description="help",
        user_email="owner@example.com",
        user_name="Owner",
        consent_contact_release=True,
        consent_outcome_tracking=True,
    )
    req = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.create_intro(payload, req))
    assert exc.value.status_code == 403
    assert "education-first prelaunch" in str(exc.value.detail)


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
    monkeypatch.setattr(server, "PUBLIC_MATCHING_ENABLED", True)

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
    monkeypatch.setattr(server, "PUBLIC_MATCHING_ENABLED", True)

    async def _noop_audit(*_args, **_kwargs):
        return None

    async def _fake_intro_fee(_db, _suburb):
        return 500

    async def _fake_fraud(_db, _ip, _trainer_id, _email):
        return {"billing_status": "billed", "reasons": []}

    async def _fake_bill_intro(_db, _trainer_doc, _intro):
        return {}

    async def _fake_notify(_db, _trainer_doc, _intro):
        return None

    monkeypatch.setattr(server, "_audit", _noop_audit)
    monkeypatch.setattr(server.autonomy, "get_intro_fee", _fake_intro_fee)
    monkeypatch.setattr(server.fraud_service, "evaluate_intro", _fake_fraud)
    monkeypatch.setattr(server.stripe_billing, "bill_intro", _fake_bill_intro)
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
    assert out["contact"]["email"] == "trainer@example.com"


def test_claim_validate_default_report_only_contract(monkeypatch):
    monkeypatch.setattr(server, "CLAIM_STATE_MODEL_ENABLED", True)
    monkeypatch.setattr(server, "CLAIM_ENFORCEMENT_MODE", "report_only")
    monkeypatch.setattr(server, "CLAIM_STATE_CURRENT", "STATE_0")
    monkeypatch.setattr(server, "CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2", True)

    out = asyncio.run(server.validate_claim(claim="We service Melbourne-wide", state=None))

    assert out["allowed"] is True
    assert out["would_block"] is False
    assert out["enforced"] is False
    assert out["reason_codes"]
    assert "CLAIM_POLICY_REPORT_ONLY" in out["reason_codes"]

    for key in ("allowed", "would_block", "enforced", "reason_codes", "claim_policy", "ts"):
        assert key in out
    assert isinstance(out["claim_policy"], dict)
    assert isinstance(out["reason_codes"], list)
    assert isinstance(out["ts"], str)
    assert "T" in out["ts"]


@pytest.mark.parametrize("state", ["STATE_0", "STATE_1"])
def test_claim_validate_block_invalid_blocks_melbourne_wide_below_state_2(monkeypatch, state):
    monkeypatch.setattr(server, "CLAIM_STATE_MODEL_ENABLED", True)
    monkeypatch.setattr(server, "CLAIM_ENFORCEMENT_MODE", "block_invalid")
    monkeypatch.setattr(server, "CLAIM_STATE_CURRENT", "STATE_0")
    monkeypatch.setattr(server, "CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2", True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.validate_claim(claim="Available across Melbourne", state=state))

    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert detail["code"] == "claim_blocked"
    assert detail["state"] == state
    assert "MELBOURNE_WIDE_BELOW_STATE_2" in detail["reason_codes"]


@pytest.mark.parametrize("state", ["STATE_2", "STATE_3", "STATE_4"])
def test_claim_validate_block_invalid_allows_melbourne_wide_at_state_2_plus(monkeypatch, state):
    monkeypatch.setattr(server, "CLAIM_STATE_MODEL_ENABLED", True)
    monkeypatch.setattr(server, "CLAIM_ENFORCEMENT_MODE", "block_invalid")
    monkeypatch.setattr(server, "CLAIM_STATE_CURRENT", "STATE_0")
    monkeypatch.setattr(server, "CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2", True)

    out = asyncio.run(server.validate_claim(claim="all Melbourne", state=state))

    assert out["state"] == state
    assert out["allowed"] is True
    assert out["would_block"] is False
    assert out["enforced"] is True
    assert out["claim_policy"]["enforcement_mode"] == "block_invalid"


def test_claim_validate_unknown_state_normalizes_to_current(monkeypatch):
    monkeypatch.setattr(server, "CLAIM_STATE_MODEL_ENABLED", True)
    monkeypatch.setattr(server, "CLAIM_ENFORCEMENT_MODE", "report_only")
    monkeypatch.setattr(server, "CLAIM_STATE_CURRENT", "STATE_3")
    monkeypatch.setattr(server, "CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2", True)

    out = asyncio.run(server.validate_claim(claim="melbourne-wide", state="STATE_X"))

    assert out["state"] == "STATE_3"
    assert out["claim_policy"]["state"] == "STATE_3"
    assert out["claim_policy"]["state_current"] == "STATE_3"


@pytest.mark.parametrize("claim_text", ["melbourne-wide", "available across melbourne", "all melbourne"])
def test_claim_validate_report_only_vs_block_invalid_deterministic(monkeypatch, claim_text):
    monkeypatch.setattr(server, "CLAIM_STATE_MODEL_ENABLED", True)
    monkeypatch.setattr(server, "CLAIM_STATE_CURRENT", "STATE_0")
    monkeypatch.setattr(server, "CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2", True)

    monkeypatch.setattr(server, "CLAIM_ENFORCEMENT_MODE", "report_only")
    report_out = asyncio.run(server.validate_claim(claim=claim_text, state="STATE_0"))
    assert report_out["enforced"] is False
    assert report_out["state"] == "STATE_0"
    assert isinstance(report_out["reason_codes"], list)

    monkeypatch.setattr(server, "CLAIM_ENFORCEMENT_MODE", "block_invalid")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.validate_claim(claim=claim_text, state="STATE_0"))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "claim_blocked"
    assert exc.value.detail["state"] == "STATE_0"


@pytest.mark.parametrize("state", ["STATE_0", "STATE_1"])
@pytest.mark.parametrize("claim_text", ["melbourne-wide", "available across melbourne", "all melbourne"])
def test_claim_validate_block_invalid_never_silent_pass_below_state_2(monkeypatch, state, claim_text):
    monkeypatch.setattr(server, "CLAIM_STATE_MODEL_ENABLED", True)
    monkeypatch.setattr(server, "CLAIM_ENFORCEMENT_MODE", "block_invalid")
    monkeypatch.setattr(server, "CLAIM_STATE_CURRENT", "STATE_0")
    monkeypatch.setattr(server, "CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2", True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.validate_claim(claim=claim_text, state=state))
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert detail["code"] == "claim_blocked"
    assert detail["state"] == state
    assert "MELBOURNE_WIDE_BELOW_STATE_2" in detail["reason_codes"]


def test_guardrail_invariant_matching_gate_env_controlled(monkeypatch):
    monkeypatch.setattr(server, "PUBLIC_MATCHING_ENABLED", False)
    with pytest.raises(HTTPException) as exc:
        server._require_public_matching("Public matching")
    assert exc.value.status_code == 403

    monkeypatch.setattr(server, "PUBLIC_MATCHING_ENABLED", True)
    server._require_public_matching("Public matching")


def test_guardrail_invariant_intro_flow_uses_bill_intro_symbol():
    src = inspect.getsource(server.create_intro)
    assert "stripe_billing.bill_intro" in src


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
    assert phase_state["current_phase"] == "supply_first"
    assert phase_state["public_matching_enabled"] is False
    assert phase_state["public_emphasis"] == "waitlist_first"
    assert phase_state["trainer_onboarding_open"] is True

    assert isinstance(readiness, dict)
    assert readiness["phase"] == "supply_first"
    assert readiness["matching_exposure_enabled"] is False
    assert readiness["public_emphasis"] == "waitlist_first"
    assert readiness["readiness_status"] in {"collecting_evidence", "attention_needed"}
    assert isinstance(readiness.get("recommendation"), str)
    assert isinstance(readiness.get("intro_ready_trainer_count"), int)
    assert isinstance(readiness.get("blocked_trainer_count"), int)
    assert isinstance(readiness.get("blockers_to_next_phase"), list)
    assert isinstance(readiness.get("blocker_buckets"), dict)

    assert out["launch_phase"] == "supply_first"
    assert out["public_emphasis"] == "waitlist_first"
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
    assert isinstance(ops.get("billing_recovery_cases"), list)
    assert isinstance(ops.get("reactivation_cases"), list)
    assert isinstance(ops.get("source_ingestion_sources"), list)
    assert isinstance(ops.get("discovery_alerts"), list)
    assert ops["billing_recovery_cases"][0]["billing_retry_state"] == "retry_exhausted"
    assert ops["reactivation_cases"][0]["trainer_name"] == "Trainer One"
    assert ops["source_ingestion_sources"][0]["source_url"] == "https://source.example.com"
    assert ops["loop_statuses"]["ranking"]["status"] in {"ok", "investigate", "escalate", "warn"}


def test_oversight_billing_summary_semantics_include_at_risk_and_collected(monkeypatch):
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

    billing = out["billing_summary"]
    revenue = out["revenue"]
    assert billing["paid"] == 1
    assert billing["payment_failed"] == 1
    assert billing["disputed"] == 1
    assert billing["trial_free"] == 1
    assert revenue["collected_revenue_cents"] == 500
    assert revenue["at_risk_revenue_cents"] == 1000


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
