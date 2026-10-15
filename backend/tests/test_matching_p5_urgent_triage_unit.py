"""Unit tests for Package P5: Urgent Support, Deterministic Triage & Official Providers.

Governed by:
- AGENTS.md (Rule 6A, locked boundaries)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md (M6)
- specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md (Section 3)
- Finding DF-024

Acceptance Criteria Verified:
1. Four deterministic outcomes:
   - immediate_human_danger: stops matching; approved Triple Zero card (call 000). Zero token, zero candidates.
   - urgent_animal_health_support: stops matching; shows current urgent-care entries (The Lost Dogs' Home Vet Hospital).
   - serious_behavioural_support: proceeds only if stricter eligible specialist path succeeds (declared aggression/behaviour mod).
   - needs_clarification: stops matching until ambiguity is resolved.
2. Isolated urgent_providers record schema & official sources:
   - Triple Zero Victoria is approved immediate-danger source.
   - U-Vet Werribee is permanently closed and NOT seeded.
   - The Lost Dogs' Home is North Melbourne urgent-care only (hours stated, NOT 24/7).
   - Veterinary behaviourists: zero verified listings without direct provider evidence + VPRBV registration.
   - UI/API does not claim Melbourne-wide urgent coverage.
3. Urgent provider correction submission endpoint.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import server
from services import urgent_providers as urgent_providers_service
from services.matching_contract_v2 import (
    DecisionState,
    MatchConsentIn,
    MatchRequestIn,
    PrimaryConcern,
    classify_pre_ai_triage,
)
from tests.fixtures_matching_v2 import (
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
            if "category" in query:
                res = [r for r in res if r.get("category") == query["category"]]
            if "freshness_state" in query:
                res = [r for r in res if r.get("freshness_state") == query["freshness_state"]]
        self._last_find = res
        return self

    async def to_list(self, limit: int = 100):
        return list(getattr(self, "_last_find", self.rows))[:limit]

    async def count_documents(self, query: Dict[str, Any] = None):
        return len(self.rows) + len(self.inserted)

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


class TestP5UrgentSupportAndTriage:
    def test_triage_classification_four_states(self):
        """Pre-AI triage deterministically classifies into 4 controlled states."""
        # 1. Immediate human danger
        assert classify_pre_ai_triage(
            primary_concerns=["aggression"],
            behaviour_description="Dog attacked a child and bit severely",
        ) == DecisionState.IMMEDIATE_HUMAN_DANGER

        # 2. Urgent animal health support
        assert classify_pre_ai_triage(
            primary_concerns=["basic_manners"],
            behaviour_description="Dog ate snail poison and is having a seizure",
        ) == DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT

        # 3. Serious behavioural support
        assert classify_pre_ai_triage(
            primary_concerns=["aggression"],
            behaviour_description="Severe aggression towards strangers, multiple bites history",
        ) == DecisionState.SERIOUS_BEHAVIOURAL_SUPPORT

        # 4. Needs clarification
        assert classify_pre_ai_triage(
            primary_concerns=["other"],
            behaviour_description="Not sure what is going on",
        ) == DecisionState.NEEDS_CLARIFICATION

    def test_immediate_human_danger_stops_matching_and_returns_triple_zero(self, monkeypatch):
        """Immediate human danger halts matching, issues zero tokens, and returns Triple Zero notice."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            primary_concerns=["aggression"],
            behaviour_description="Active dog attack on neighbor, child bite emergency",
        )

        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == "immediate_human_danger"
        assert out["candidates"] == []
        assert out["matches"] == []
        assert out["context_token"] is None
        assert "emergency_notice" in out
        assert out["emergency_notice"]["source"] == "Triple Zero Victoria"
        assert "000" in out["emergency_notice"]["action"]
        assert len(fake_db.match_contexts.inserted) == 0

    def test_urgent_animal_health_stops_matching_and_returns_verified_provider(self, monkeypatch):
        """Urgent animal health halts matching, issues zero tokens, and returns verified urgent care providers."""
        fake_db = SimpleNamespace(
            trainers=_MockCollection([]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
            urgent_providers=_MockCollection(urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            primary_concerns=["basic_manners"],
            behaviour_description="Dog collapsed unconscious and bleeding profusely",
        )

        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == "urgent_animal_health_support"
        assert out["candidates"] == []
        assert out["matches"] == []
        assert out["context_token"] is None
        assert len(out["urgent_providers"]) > 0
        prov = out["urgent_providers"][0]
        assert prov["name"] == "The Lost Dogs' Home Veterinary Hospital"
        assert "(03) 8379 4498" in prov["contact_method"]
        assert "not a 24/7" in prov["stated_hours"].lower() or "not 24/7" in prov["stated_hours"].lower()
        # Coverage disclosure truthfulness: does NOT claim Melbourne-wide
        assert "does not claim Melbourne-wide" in out["coverage_disclosure"]
        assert "No verified veterinary behaviourist" in out["veterinary_behaviourist_status"]

    def test_serious_behavioural_support_enforces_stricter_specialist_eligibility(self, monkeypatch):
        """Serious behavioural support restricts matches to trainers with declared aggression capability."""
        # Trainer 1: Only basic manners (not qualified for serious behaviour)
        t_basic = make_test_trainer_doc(
            trainer_id="t_basic",
            name="Puppy Manners Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adult"],
        )
        # Trainer 2: Qualified with aggression specialty
        t_specialist = make_test_trainer_doc(
            trainer_id="t_spec",
            name="Richmond Aggression Specialists",
            serviced_suburbs=["Richmond"],
            specialties=["aggression", "behaviour_modification"],
            service_formats=["in_home"],
            life_stages=["puppy", "adult"],
        )

        fake_db = SimpleNamespace(
            trainers=_MockCollection([t_basic, t_specialist]),
            match_events=_MockCollection([]),
            match_contexts=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            primary_concerns=["aggression"],
            behaviour_description="Dog has severe aggression and bite history with other dogs",
        )

        out = asyncio.run(server.instant_match(req))
        # Candidates should ONLY include t_spec, NOT t_basic
        cand_ids = [c["trainer_id"] for c in out["candidates"]]
        assert "t_spec" in cand_ids
        assert "t_basic" not in cand_ids
        assert "support_context" in out
        assert "Specialist pathway active" in out["support_context"]

    def test_u_vet_werribee_strictly_forbidden_from_urgent_providers(self):
        """U-Vet Werribee permanently closed in 2022 and must never be present in urgent provider records."""
        for p in urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS:
            assert "u-vet" not in p["name"].lower()
            assert "u-vet" not in p["official_source_url"].lower()
            assert "u-vet" not in p["provider_id"].lower()

    def test_urgent_providers_api_and_disclosures(self, monkeypatch):
        """GET /api/urgent-providers returns verified records without claiming Melbourne-wide coverage."""
        fake_db = SimpleNamespace(
            urgent_providers=_MockCollection(urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS),
        )
        monkeypatch.setattr(server, "db", fake_db)

        res = asyncio.run(server.get_urgent_providers())
        assert len(res["urgent_providers"]) > 0
        assert "does not claim Melbourne-wide" in res["disclaimer"]
        assert res["veterinary_behaviourist_verified_count"] == 0
        assert "No verified veterinary behaviourist" in res["veterinary_behaviourist_status"]
        assert res["emergency_notice"]["source"] == "Triple Zero Victoria"

    def test_urgent_provider_correction_submission(self, monkeypatch):
        """POST /api/urgent-providers/correction stores public correction request for evidence review."""
        fake_db = SimpleNamespace(
            urgent_provider_corrections=_MockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = urgent_providers_service.UrgentProviderCorrectionIn(
            provider_id="urgent_care_lost_dogs_home_north_melbourne",
            provider_name="The Lost Dogs' Home",
            official_source_url="https://vet.dogshome.com/",
            reason="hours_changed",
            notes="Opening hours updated for public holidays",
        )

        res = asyncio.run(server.create_urgent_provider_correction(payload))
        assert res["status"] == "received"
        assert "request_id" in res
        assert len(fake_db.urgent_provider_corrections.inserted) == 1
        inserted = fake_db.urgent_provider_corrections.inserted[0]
        assert inserted["reason"] == "hours_changed"
        assert inserted["status"] == "pending_review"
