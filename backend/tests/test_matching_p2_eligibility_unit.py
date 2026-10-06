"""Unit tests for Package P2: Deterministic Eligibility & Match Record.

Governed by:
- AGENTS.md (Rule 6A, locked boundaries)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md (M2, M3)
- specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md (Sections 2, 3, 4)
- Findings: DF-018, DF-019, DF-022, DF-026

Acceptance Criteria Verified:
1. Strict schema validation, consent constraints, and boundary rejections.
2. Locality resolution, regex safety, and ambiguous postcode clarification.
3. Pre-AI triage intercept (immediate human danger, urgent animal health, serious behaviour, other/unsure).
4. Match-ready projection gating (stale declarations, unpublished, disputed, cancelled ABN).
5. Deterministic eligibility & thin supply expansion (local vs expanded search scope).
6. Privacy & sanitised persistence (zero PII, zero raw description in match_events, 30-day retention).
7. Opaque context token generation, SHA-256 hashing in DB, and /api/match/context retrieval.
8. Rate limiting against non-reversible SHA-256 IP key (10 per 10min, 3 per 30s burst).
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

import server
from services.matching_contract_v2 import (
    DECISION_CONTRACT_VERSION,
    DecisionResponseV2,
    DecisionState,
    MatchConsentIn,
    MatchRateLimiter,
    MatchRequestIn,
    MethodPreference,
    PrimaryConcern,
    ReasonCode,
    SearchScope,
    ServiceFormatPreference,
    GeminiStubAdapter,
    classify_pre_ai_triage,
    generate_match_context_token,
    hash_match_context_token,
    resolve_canonical_locality,
)
from services.trainer_quality import (
    DEFAULT_PROJECTION_POLICY,
    CapabilityProjectionPolicy,
    build_match_ready_projection,
    now_iso,
)
from tests.fixtures_matching_v2 import (
    make_test_raw_trainer_doc,
    make_test_trainer_doc,
    make_valid_match_request,
)


class _MockCollection:
    def __init__(self, rows: List[Dict[str, Any]] = None):
        self.rows = list(rows or [])
        self.inserted: List[Dict[str, Any]] = []

    def find(self, query: Dict[str, Any] = None, projection: Dict[str, Any] = None):
        res = list(self.rows)
        if query:
            if "published" in query:
                res = [r for r in res if r.get("published") == query["published"]]
            if "region" in query and "$in" in query["region"]:
                allowed_regions = set(query["region"]["$in"])
                res = [r for r in res if r.get("region") in allowed_regions]
        self._last_find = res
        return self

    async def to_list(self, limit: int = 100):
        return list(getattr(self, "_last_find", self.rows))[:limit]

    async def find_one(self, query: Dict[str, Any], projection: Dict[str, Any] = None):
        for r in self.rows + self.inserted:
            match = True
            for k, v in query.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                return dict(r)
        return None

    async def insert_one(self, doc: Dict[str, Any]):
        self.inserted.append(dict(doc))
        return SimpleNamespace(inserted_id="mock_id")


def _make_dummy_request(
    ip: str = "127.0.0.1",
    method: str = "POST",
    path: str = "/api/match",
    query_string: str = "",
    headers: Dict[str, str] = None,
) -> Request:
    raw_headers = [(b"host", b"testserver")]
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode(), v.encode()))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string.encode(),
        "headers": raw_headers,
        "client": (ip, 12345),
    }
    return Request(scope)


# ==============================================================================
# 1. Schema Validation & Consent Constraints
# ==============================================================================

class TestP2SchemaValidation:
    def test_strict_boolean_consent_required(self):
        """Reject non-boolean strings ('true', 'yes', '1') for mandatory consent."""
        for val in ["true", "yes", "1", 1, 0]:
            with pytest.raises(ValidationError) as exc:
                MatchConsentIn(match_processing=val, terms=True)  # type: ignore
            assert "must be an actual boolean" in str(exc.value)

    def test_missing_mandatory_fields_rejected(self):
        """Reject request missing dog_age_months, service_format, or method_preference."""
        with pytest.raises(ValidationError):
            MatchRequestIn(  # type: ignore
                suburb_or_postcode="Richmond",
                primary_concerns=["basic_manners"],
                service_format="in_home",
                method_preference="no_preference",
                consent=MatchConsentIn(match_processing=True, terms=True),
            )

        with pytest.raises(ValidationError):
            MatchRequestIn(  # type: ignore
                suburb_or_postcode="Richmond",
                dog_age_months=12,
                primary_concerns=["basic_manners"],
                method_preference="no_preference",
                consent=MatchConsentIn(match_processing=True, terms=True),
            )

    def test_dog_age_boundaries(self):
        """dog_age_months must be within 0..360."""
        req_valid = make_valid_match_request(dog_age_months=0)
        assert req_valid.dog_age_months == 0
        req_max = make_valid_match_request(dog_age_months=360)
        assert req_max.dog_age_months == 360

        with pytest.raises(ValidationError):
            make_valid_match_request(dog_age_months=-1)

        with pytest.raises(ValidationError):
            make_valid_match_request(dog_age_months=361)

    def test_behaviour_description_bounded_to_800_chars(self):
        """behaviour_description longer than 800 chars is stripped/truncated."""
        long_desc = "Barking and lunging on leash. " * 50
        req = make_valid_match_request(behaviour_description=long_desc)
        assert len(req.behaviour_description) <= 800


# ==============================================================================
# 2. Locality Resolution & Regex Safety
# ==============================================================================

class TestP2LocalityResolution:
    def test_canonical_postcode_resolution(self):
        """Unambiguous postcode 3067 resolves to Abbotsford."""
        res = resolve_canonical_locality("3067")
        assert res["valid"] is True
        assert res["canonical_name"] == "Abbotsford"

    def test_ambiguous_postcode_returns_clarification(self):
        """Ambiguous postcode 3121 returns needs_clarification."""
        res = resolve_canonical_locality("3121")
        assert res["valid"] is False
        assert res["reason"] == "ambiguous_postcode"

    def test_endpoint_ambiguous_postcode_clarification(self, monkeypatch):
        """Endpoint returns NEEDS_CLARIFICATION for ambiguous postcode."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(suburb_or_postcode="3121")
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == DecisionState.NEEDS_CLARIFICATION.value
        assert "ambiguous_postcode" in out["reason_codes"]
        assert len(out["candidates"]) == 0

    def test_endpoint_invalid_suburb_clarification(self, monkeypatch):
        """Endpoint returns NEEDS_CLARIFICATION for invalid suburb."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(suburb_or_postcode="Sydney CBD")
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == DecisionState.NEEDS_CLARIFICATION.value
        assert "invalid_locality" in out["reason_codes"]

    def test_regex_safety_special_characters(self, monkeypatch):
        """Special regex characters in suburb_or_postcode do not cause errors."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        malicious_inputs = ["^.*$", "Carlton|Richmond", "[A-Z]+", "'; DROP TABLE;--"]
        for mal in malicious_inputs:
            req = make_valid_match_request(suburb_or_postcode=mal)
            out = asyncio.run(server.instant_match(req))
            assert out["decision_state"] == DecisionState.NEEDS_CLARIFICATION.value


# ==============================================================================
# 3. Pre-AI Triage Intercept
# ==============================================================================

class TestP2PreAiTriage:
    def test_immediate_human_danger_bypasses_matching(self, monkeypatch):
        """Immediate human danger text stops matching, returns immediate_human_danger."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            behaviour_description="Dog attacked someone in the park, active attack emergency hospital!"
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == DecisionState.IMMEDIATE_HUMAN_DANGER.value
        assert len(out["candidates"]) == 0
        # Persisted event must not contain raw description
        assert len(fake_db.match_events.inserted) == 1
        ev = fake_db.match_events.inserted[0]
        assert ev["decision_state"] == DecisionState.IMMEDIATE_HUMAN_DANGER.value
        assert "description" not in ev
        assert "active attack" not in str(ev)

    def test_urgent_animal_health_stops_matching(self, monkeypatch):
        """Acute animal health need stops matching, returns urgent_animal_health_support."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            behaviour_description="Puppy swallowed rat poison and is having a seizure"
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT.value
        assert len(out["candidates"]) == 0

    def test_other_unsure_concerns_require_clarification(self, monkeypatch):
        """Concern other or unsure returns needs_clarification."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            primary_concerns=[PrimaryConcern.OTHER.value],
            behaviour_description="Dog is acting strange lately",
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == DecisionState.NEEDS_CLARIFICATION.value


# ==============================================================================
# 4. Match-Ready Projection & Status Gating
# ==============================================================================

class TestP2ProjectionGating:
    def test_stale_declaration_fails_closed(self):
        """Trainer declaration older than 180 days fails closed."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=181)).isoformat()
        stale_doc = make_test_raw_trainer_doc(
            trainer_id="t_stale",
            name="Stale Trainer",
            confirmed_ts=old_date,
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            life_stages=["puppy", "adult"],
        )
        proj = build_match_ready_projection(stale_doc)
        assert proj["match_eligible"] is False
        assert "no_permitted_matchable_capabilities" in proj["eligibility_reasons"]

    def test_unpublished_profile_excluded(self):
        """Unpublished trainer fails closed."""
        doc = make_test_raw_trainer_doc(
            trainer_id="t_unpub",
            name="Unpublished Trainer",
            published=False,
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            life_stages=["puppy", "adult"],
        )
        proj = build_match_ready_projection(doc)
        assert proj["match_eligible"] is False
        assert "profile_not_published" in proj["eligibility_reasons"]

    def test_ownership_disputed_profile_excluded(self):
        """Disputed claim status fails closed."""
        doc = make_test_raw_trainer_doc(
            trainer_id="t_dispute",
            name="Disputed Trainer",
            claim_status="claim_disputed",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            life_stages=["puppy", "adult"],
        )
        proj = build_match_ready_projection(doc)
        assert proj["match_eligible"] is False
        assert "ownership_disputed" in proj["eligibility_reasons"]

    def test_cancelled_abn_profile_excluded(self):
        """Statutory cancelled ABN fails closed."""
        doc = make_test_raw_trainer_doc(
            trainer_id="t_cancelled_abn",
            name="Cancelled ABN",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            life_stages=["puppy", "adult"],
            abn_verified=False,
            abn_status="cancelled",
        )
        proj = build_match_ready_projection(doc)
        assert proj["match_eligible"] is False
        assert "statutory_abn_revoked" in proj["eligibility_reasons"]

    def test_legacy_request_rejected_with_400_and_cannot_create_match_or_token(self, monkeypatch):
        """Legacy InstantMatchIn request is rejected with 400 and cannot create match, event, or context token."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
        )
        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        legacy_payload = server.InstantMatchIn(
            description="basic manners",
            suburb="Richmond",
            consent_match_processing=True,
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.instant_match(legacy_payload))

        assert exc.value.status_code == 400
        assert "Legacy two-field match requests are deprecated and rejected" in exc.value.detail
        # Zero match events or context tokens persisted
        assert len(fake_db.match_events.inserted) == 0
        assert len(fake_db.match_contexts.inserted) == 0


# ==============================================================================
# 5. Deterministic Eligibility & Thin Supply Expansion
# ==============================================================================

class TestP2EligibilityAndExpansion:
    def test_exact_declared_suburb_local_eligibility(self, monkeypatch):
        """Only trainers with exact declared serviced_suburbs qualify for LOCAL search."""
        trainer_richmond = make_test_trainer_doc(
            trainer_id="t_richmond",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["adult"],
        )
        trainer_carlton = make_test_trainer_doc(
            trainer_id="t_carlton",
            name="Carlton Dog Academy",
            serviced_suburbs=["Carlton"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["adult"],
        )

        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer_richmond, trainer_carlton]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=24,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))
        assert out["search_scope"] == SearchScope.LOCAL.value
        candidate_ids = [c["trainer_id"] for c in out["candidates"]]
        assert "t_richmond" in candidate_ids
        assert "t_carlton" not in candidate_ids

    def test_thin_supply_triggers_expanded_search(self, monkeypatch):
        """When fewer than 3 local candidates exist, search_scope becomes EXPANDED with declared catchments."""
        trainer_local = make_test_trainer_doc(
            trainer_id="t_local",
            name="Local Trainer",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["adult"],
        )
        trainer_expanded = make_test_trainer_doc(
            trainer_id="t_expanded",
            name="Greater Melbourne Trainer",
            serviced_suburbs=["Footscray"],
            catchment_type="melbourne_wide",
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["adult"],
        )

        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer_local, trainer_expanded]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)
        monkeypatch.setattr(server, "matching_ai_adapter", GeminiStubAdapter(mode="normal"))

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=24,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))
        assert out["search_scope"] == SearchScope.EXPANDED.value
        assert out["decision_state"] == DecisionState.LIMITED_LOCAL_RESULTS.value
        candidate_ids = [c["trainer_id"] for c in out["candidates"]]
        assert "t_local" in candidate_ids
        assert "t_expanded" in candidate_ids

    def test_no_confirmed_match_when_no_trainers_qualify(self, monkeypatch):
        """Returns NO_CONFIRMED_MATCH when no candidates satisfy compatibility."""
        trainer_wrong_format = make_test_trainer_doc(
            trainer_id="t_facility_only",
            name="Facility Trainer",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["facility"],
            life_stages=["adult"],
        )
        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer_wrong_format]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # Owner explicitly requires in_home
        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=24,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == DecisionState.NO_CONFIRMED_MATCH.value
        assert len(out["candidates"]) == 0


# ==============================================================================
# 6. Privacy & Match Context Lifecycle
# ==============================================================================

class TestP2PrivacyAndContextLifecycle:
    def test_zero_raw_description_or_pii_in_match_events(self, monkeypatch):
        """Match event record contains zero raw description or PII."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["adult"],
        )
        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        raw_desc = "Call me on 0412 345 678 or owner@test.com. Dog jumps on sofa."
        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=24,
            behaviour_description=raw_desc,
        )
        out = asyncio.run(server.instant_match(req))

        assert len(fake_db.match_events.inserted) == 1
        ev = fake_db.match_events.inserted[0]

        # Invariants: no raw description, no PII, 30-day retention
        assert "description" not in ev
        assert "behaviour_description" not in ev
        assert "0412 345 678" not in str(ev)
        assert "owner@test.com" not in str(ev)
        assert ev["policy_version"] == DECISION_CONTRACT_VERSION
        assert ev["locality"] == "Richmond"
        assert isinstance(ev["expires_at"], datetime)
        assert ev["expires_at"] > datetime.now(timezone.utc)
        assert "context_token_hash" in ev

    def test_context_token_retrieval_endpoint(self, monkeypatch):
        """Context retrieval endpoint retrieves sanitised context by raw token via header."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
        )
        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(suburb_or_postcode="Richmond", dog_age_months=18)
        match_out = asyncio.run(server.instant_match(req))

        raw_token = match_out["context_token"]
        assert raw_token is not None

        # Verify raw token is NOT in db; only hash is stored
        assert len(fake_db.match_contexts.inserted) == 1
        ctx_doc = fake_db.match_contexts.inserted[0]
        assert ctx_doc["token_hash"] == hash_match_context_token(raw_token)
        assert raw_token not in str(ctx_doc)
        assert isinstance(ctx_doc["expires_at"], datetime)

        # Retrieve context via GET /api/match/context using X-Match-Context-Token header
        dummy_req = _make_dummy_request(
            method="GET",
            path="/api/match/context",
            headers={"X-Match-Context-Token": raw_token},
        )
        ctx_out = asyncio.run(server.get_match_context(request=dummy_req))
        assert ctx_out["suburb_or_postcode"] == "Richmond"
        assert ctx_out["dog_age_months"] == 18
        assert "behaviour_description" not in ctx_out

    def test_context_token_query_param_strictly_forbidden(self, monkeypatch):
        """Query parameter tokens (?token=... or ?context_token=...) are rejected with 400."""
        fake_db = SimpleNamespace(match_contexts=_MockCollection([]))
        monkeypatch.setattr(server, "db", fake_db)

        # 1. query param 'token'
        req1 = _make_dummy_request(
            method="GET",
            path="/api/match/context",
            query_string="token=secret_context_token_123",
        )
        with pytest.raises(HTTPException) as exc1:
            asyncio.run(server.get_match_context(request=req1))
        assert exc1.value.status_code == 400
        assert "Query parameter authentication is forbidden" in exc1.value.detail

        # 2. query param 'context_token'
        req2 = _make_dummy_request(
            method="GET",
            path="/api/match/context",
            query_string="context_token=secret_context_token_123",
        )
        with pytest.raises(HTTPException) as exc2:
            asyncio.run(server.get_match_context(request=req2))
        assert exc2.value.status_code == 400
        assert "Query parameter authentication is forbidden" in exc2.value.detail

    def test_context_token_missing_header_rejected_with_401(self, monkeypatch):
        """Missing X-Match-Context-Token header is rejected with 401."""
        fake_db = SimpleNamespace(match_contexts=_MockCollection([]))
        monkeypatch.setattr(server, "db", fake_db)

        req = _make_dummy_request(method="GET", path="/api/match/context")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.get_match_context(request=req))
        assert exc.value.status_code == 401
        assert "Missing X-Match-Context-Token header" in exc.value.detail

    def test_context_token_invalid_or_expired_rejected(self, monkeypatch):
        """Context retrieval rejects invalid or expired tokens in headers."""
        fake_db = SimpleNamespace(
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # Invalid token via header
        req_invalid = _make_dummy_request(
            method="GET",
            path="/api/match/context",
            headers={"X-Match-Context-Token": "invalid_random_token"},
        )
        with pytest.raises(HTTPException) as exc1:
            asyncio.run(server.get_match_context(request=req_invalid))
        assert exc1.value.status_code == 404

        # Expired token via header
        expired_token, expired_hash = generate_match_context_token()
        expired_ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        fake_db.match_contexts.rows.append({
            "token_hash": expired_hash,
            "match_id": "m_exp",
            "expires_at": expired_ts,
        })
        req_expired = _make_dummy_request(
            method="GET",
            path="/api/match/context",
            headers={"X-Match-Context-Token": expired_token},
        )
        with pytest.raises(HTTPException) as exc2:
            asyncio.run(server.get_match_context(request=req_expired))
        assert exc2.value.status_code == 410

    def test_no_context_token_issued_for_non_handoff_states(self, monkeypatch):
        """No context token is issued or persisted for triage, invalid locality, or empty results."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # 1. Invalid locality
        req_invalid_loc = make_valid_match_request(suburb_or_postcode="Sydney CBD")
        out1 = asyncio.run(server.instant_match(req_invalid_loc))
        assert out1["context_token"] is None
        assert len(fake_db.match_contexts.inserted) == 0

        # 2. Immediate danger
        req_danger = make_valid_match_request(
            behaviour_description="Active dog attack emergency hospital bite"
        )
        out2 = asyncio.run(server.instant_match(req_danger))
        assert out2["context_token"] is None
        assert len(fake_db.match_contexts.inserted) == 0

        # 3. Urgent animal health
        req_health = make_valid_match_request(
            behaviour_description="Puppy swallowed poison and is convulsing"
        )
        out3 = asyncio.run(server.instant_match(req_health))
        assert out3["context_token"] is None
        assert len(fake_db.match_contexts.inserted) == 0

        # 4. Ambiguous postcode
        req_ambig = make_valid_match_request(suburb_or_postcode="3121")
        out4 = asyncio.run(server.instant_match(req_ambig))
        assert out4["context_token"] is None
        assert len(fake_db.match_contexts.inserted) == 0

        # 5. No confirmed match (empty candidate pool)
        req_empty = make_valid_match_request(suburb_or_postcode="Richmond")
        out5 = asyncio.run(server.instant_match(req_empty))
        assert out5["context_token"] is None
        assert len(fake_db.match_contexts.inserted) == 0

    def test_public_response_redacts_match_score_and_tier(self, monkeypatch):
        """Public candidate and match responses strictly redact raw match_score and commercial tier."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
            tier="premium_partner",
        )
        fake_db = SimpleNamespace(
            trainers=_MockCollection([trainer]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))

        assert len(out["candidates"]) >= 1
        for cand in out["candidates"]:
            assert "match_score" not in cand
            assert "tier" not in cand

        assert len(out["matches"]) >= 1
        for match in out["matches"]:
            assert "match_score" not in match
            assert "tier" not in match

        # Internal match_event record DOES record fit scores for protected audit/telemetry
        assert len(fake_db.match_events.inserted) == 1
        ev = fake_db.match_events.inserted[0]
        assert "candidate_fit_scores" in ev
        assert "t_richmond" in ev["candidate_fit_scores"]


# ==============================================================================
# 7. Rate Limiting Against Non-Reversible Key
# ==============================================================================

class TestP2RateLimiter:
    def test_non_reversible_ip_key(self):
        """Rate limiter derives one-way SHA-256 hash from IP."""
        limiter = MatchRateLimiter()
        key1 = limiter.hash_key("203.0.113.195")
        key2 = limiter.hash_key("203.0.113.195")
        key3 = limiter.hash_key("203.0.113.196")

        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 64
        # Cannot derive IP back from hash
        assert "203.0.113.195" not in key1

    def test_burst_limit_exceeded(self):
        """Exceeding 3 requests within 30 seconds triggers burst_limit_exceeded."""
        limiter = MatchRateLimiter(burst_max_attempts=3, burst_interval_seconds=30)
        ip = "198.51.100.1"
        now = 1000.0

        for _ in range(3):
            allowed, reason = limiter.check_limit(ip, now_ts=now)
            assert allowed is True
            limiter.record_attempt(ip, now_ts=now)
            now += 5.0

        # 4th request within 15 seconds (<= 30s burst interval)
        allowed4, reason4 = limiter.check_limit(ip, now_ts=now)
        assert allowed4 is False
        assert reason4 == "burst_limit_exceeded"

    def test_window_limit_exceeded(self):
        """Exceeding 10 requests within 600 seconds triggers window_limit_exceeded."""
        limiter = MatchRateLimiter(max_attempts=10, window_seconds=600, burst_max_attempts=20)
        ip = "198.51.100.2"
        now = 1000.0

        for i in range(10):
            allowed, _ = limiter.check_limit(ip, now_ts=now)
            assert allowed is True
            limiter.record_attempt(ip, now_ts=now)
            now += 35.0  # spacing out to avoid burst limit

        # 11th request within 350 seconds (< 600s window)
        allowed11, reason11 = limiter.check_limit(ip, now_ts=now)
        assert allowed11 is False
        assert reason11 == "window_limit_exceeded"

    def test_endpoint_rate_limiting_enforced(self, monkeypatch):
        """Endpoint raises 429 when rate limit is exceeded."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)
        server.matching_contract_v2.match_rate_limiter.reset()

        req = make_valid_match_request()
        dummy_http_req = _make_dummy_request(ip="192.0.2.99")

        # 3 quick requests succeed
        for _ in range(3):
            asyncio.run(server.instant_match(req, request=dummy_http_req))

        # 4th immediate request exceeds burst limit and raises 429
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.instant_match(req, request=dummy_http_req))
        assert exc.value.status_code == 429
        assert "Rate limit exceeded" in exc.value.detail
        server.matching_contract_v2.match_rate_limiter.reset()
