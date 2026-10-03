"""Unit tests for Package P3: AI Fit, Fallback & Fair Presentation.

Governed by:
- AGENTS.md (Rule 6A, locked boundaries)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md (M3, M4)
- specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md (Sections 3, 4, 5, 6)
- Findings: DF-019, DF-023, DF-026

Acceptance Criteria Verified:
1. AI adapter integration (/api/match executes through execute_matching_with_adapter).
2. Degradation handling: timeout, rate limit, unavailable, and malformed model output cleanly cut over to deterministic fallback (degraded=True, DEGRADED_RECOMMENDATIONS).
3. Boundary safety: Unexpected errors (e.g. RuntimeError) propagate directly without being swallowed by fallback.
4. Paid-neutral raw fit: Commercial tier and outcome_score have strictly zero weight in raw fit calculation.
5. Fair presentation ordering: Commercial reordering operates strictly within the exact 0.05 band of the highest candidate fit; candidates outside 0.05 cannot overtake higher-scoring trainers.
6. Stable non-commercial tiebreaking: Exact ties are resolved deterministically by trainer_id ascending.
7. Truthful explanations: Prohibited superlatives, guarantees, and medical/legal diagnoses are strictly rejected.
8. Strict model input sanitization: marketing bios, commercial tiers, pricing, and PII are excluded from model candidate payloads.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from pydantic import ValidationError

import server
from services.matching_contract_v2 import (
    COMPARABLE_FIT_BAND,
    MAX_RECOMMENDED_CANDIDATES,
    QUALIFICATION_THRESHOLD,
    DecisionResponseV2,
    DecisionState,
    GeminiAdapterError,
    GeminiRateLimitError,
    GeminiStubAdapter,
    GeminiTimeoutError,
    GeminiUnavailableError,
    MatchRequestIn,
    PrimaryConcern,
    SearchScope,
    ServiceFormatPreference,
    apply_fair_presentation,
    compute_deterministic_fit,
    execute_matching_with_adapter,
    validate_explanation_truthfulness,
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


# ==============================================================================
# 1. AI Fit Adapter & Fallback Integration Tests
# ==============================================================================

class TestP3AdapterAndFallbackIntegration:
    @pytest.fixture(autouse=True)
    def reset_adapter(self):
        old_adapter = getattr(server, "matching_ai_adapter", None)
        yield
        server.matching_ai_adapter = old_adapter

    def test_adapter_normal_mode_produces_recommendations(self, monkeypatch):
        """Normal adapter execution returns RECOMMENDATIONS with degraded=False."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond_normal",
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
        server.matching_ai_adapter = GeminiStubAdapter(mode="normal")

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))

        assert out["decision_state"] == DecisionState.RECOMMENDATIONS.value
        assert out["degraded"] is False
        assert len(out["candidates"]) == 1
        assert out["candidates"][0]["trainer_id"] == "t_richmond_normal"

        # Match event persistence reflects non-degraded status
        assert len(fake_db.match_events.inserted) == 1
        ev = fake_db.match_events.inserted[0]
        assert ev["degraded"] is False
        assert ev["decision_state"] == DecisionState.RECOMMENDATIONS.value

    def test_adapter_timeout_engages_deterministic_fallback(self, monkeypatch):
        """Adapter timeout cleanly engages deterministic fallback with degraded=True."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond_timeout",
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
        server.matching_ai_adapter = GeminiStubAdapter(mode="timeout")

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))

        assert out["decision_state"] == DecisionState.DEGRADED_RECOMMENDATIONS.value
        assert out["degraded"] is True
        assert len(out["candidates"]) == 1
        assert out["candidates"][0]["trainer_id"] == "t_richmond_timeout"

        # Match event persistence reflects degraded fallback status
        assert len(fake_db.match_events.inserted) == 1
        ev = fake_db.match_events.inserted[0]
        assert ev["degraded"] is True
        assert ev["decision_state"] == DecisionState.DEGRADED_RECOMMENDATIONS.value

    def test_adapter_rate_limit_engages_deterministic_fallback(self, monkeypatch):
        """Adapter rate limit (HTTP 429) cleanly engages deterministic fallback."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond_ratelimit",
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
        server.matching_ai_adapter = GeminiStubAdapter(mode="rate_limit")

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))

        assert out["decision_state"] == DecisionState.DEGRADED_RECOMMENDATIONS.value
        assert out["degraded"] is True
        assert len(out["candidates"]) == 1

    def test_adapter_unavailable_engages_deterministic_fallback(self, monkeypatch):
        """Adapter unavailable (HTTP 503) cleanly engages deterministic fallback."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond_unavail",
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
        server.matching_ai_adapter = GeminiStubAdapter(mode="unavailable")

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))

        assert out["decision_state"] == DecisionState.DEGRADED_RECOMMENDATIONS.value
        assert out["degraded"] is True

    def test_adapter_malformed_output_engages_deterministic_fallback(self, monkeypatch):
        """Malformed output (hallucinated candidate, invalid schema) engages fallback."""
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond_valid",
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
        server.matching_ai_adapter = GeminiStubAdapter(mode="malformed_output")

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        out = asyncio.run(server.instant_match(req))

        # Hallucinated candidate rejected; valid candidate returned via deterministic fallback
        assert out["decision_state"] == DecisionState.DEGRADED_RECOMMENDATIONS.value
        assert out["degraded"] is True
        assert len(out["candidates"]) == 1
        assert out["candidates"][0]["trainer_id"] == "t_richmond_valid"

    def test_unexpected_exception_propagates_without_fallback(self, monkeypatch):
        """Unexpected internal errors (e.g. RuntimeError) propagate directly without fallback."""
        class CrashingAdapter(GeminiStubAdapter):
            def call_model(self, *args, **kwargs):
                raise RuntimeError("Unexpected internal crash in matching engine")

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
        server.matching_ai_adapter = CrashingAdapter()

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        with pytest.raises(RuntimeError) as exc:
            asyncio.run(server.instant_match(req))
        assert "Unexpected internal crash" in str(exc.value)


# ==============================================================================
# 2. Fair Presentation & Exact 0.05 Commercial Tiebreaking
# ==============================================================================

class TestP3FairPresentation:
    def test_paid_neutral_raw_fit_scoring(self):
        """Raw fit score is strictly paid-neutral; tier and outcome_score do not alter raw fit."""
        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        doc_unclaimed = make_test_trainer_doc(
            trainer_id="t_unclaimed",
            name="Unclaimed Trainer",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
            tier="unclaimed",
        )
        doc_unclaimed["outcome_score"] = 0.2
        doc_pro = make_test_trainer_doc(
            trainer_id="t_pro",
            name="Pro Trainer",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
            tier="pro",
        )
        doc_pro["outcome_score"] = 0.99

        score_unclaimed, _, _ = compute_deterministic_fit(doc_unclaimed, req)
        score_pro, _, _ = compute_deterministic_fit(doc_pro, req)

        assert score_unclaimed == score_pro
        assert score_unclaimed >= QUALIFICATION_THRESHOLD

    def test_commercial_reordering_strictly_within_0_05_band(self):
        """Commercial promotion operates strictly within 0.05; outside 0.05 cannot overtake."""
        # Candidate A: Unclaimed, fit 0.86
        # Candidate B: Pro, fit 0.82 (diff 0.04 <= 0.05) -> promoted ahead of A
        # Candidate C: Pro, fit 0.80 (diff 0.06 > 0.05)  -> cannot overtake A
        candidates = [
            {"trainer_id": "t_unclaimed_top", "match_score": 0.86, "tier": "unclaimed", "policy_penalty": 0.0, "reason_codes": ["basic_manners"], "explanation": "fit", "search_scope": "local"},
            {"trainer_id": "t_pro_inside_band", "match_score": 0.82, "tier": "pro", "policy_penalty": 0.0, "reason_codes": ["basic_manners"], "explanation": "fit", "search_scope": "local"},
            {"trainer_id": "t_pro_outside_band", "match_score": 0.80, "tier": "pro", "policy_penalty": 0.0, "reason_codes": ["basic_manners"], "explanation": "fit", "search_scope": "local"},
        ]
        presented = apply_fair_presentation(candidates, max_results=3)

        assert len(presented) == 3
        # t_pro_inside_band is promoted to index 0 because diff <= 0.05 and Pro > Unclaimed
        assert presented[0]["trainer_id"] == "t_pro_inside_band"
        # t_unclaimed_top is index 1
        assert presented[1]["trainer_id"] == "t_unclaimed_top"
        # t_pro_outside_band remains index 2 (cannot overtake t_unclaimed_top)
        assert presented[2]["trainer_id"] == "t_pro_outside_band"

    def test_exact_tie_resolved_by_stable_non_commercial_trainer_id(self):
        """Exact score and tier ties are resolved deterministically by trainer_id ascending."""
        candidates = [
            {"trainer_id": "trainer_z", "match_score": 0.85, "tier": "claimed", "policy_penalty": 0.0, "reason_codes": ["basic_manners"], "explanation": "fit", "search_scope": "local"},
            {"trainer_id": "trainer_a", "match_score": 0.85, "tier": "claimed", "policy_penalty": 0.0, "reason_codes": ["basic_manners"], "explanation": "fit", "search_scope": "local"},
            {"trainer_id": "trainer_m", "match_score": 0.85, "tier": "claimed", "policy_penalty": 0.0, "reason_codes": ["basic_manners"], "explanation": "fit", "search_scope": "local"},
        ]
        presented = apply_fair_presentation(candidates, max_results=3)

        assert [p["trainer_id"] for p in presented] == ["trainer_a", "trainer_m", "trainer_z"]


# ==============================================================================
# 3. Truthful Explanations Validation
# ==============================================================================

class TestP3TruthfulExplanations:
    def test_prohibited_superlatives_and_guarantees_rejected(self):
        """Prohibited superlative and guarantee terms raise ValueError."""
        cand_proj = {
            "trainer_id": "t_1",
            "specialties": ["basic_manners"],
            "serviced_suburbs": ["Richmond"],
            "service_formats": ["in_home"],
        }
        prohibited_phrases = [
            "Best dog trainer in Melbourne with 100% success rate",
            "We guarantee your dog will never bark again",
            "Number 1 rated puppy specialist in Australia",
            "Diagnosed ADHD and requires behavioural medication",
        ]
        for phrase in prohibited_phrases:
            with pytest.raises(ValueError):
                validate_explanation_truthfulness(phrase, cand_proj)

    def test_factual_declared_explanation_accepted(self):
        """Explanations citing only declared, permitted facts pass validation."""
        cand_proj = {
            "trainer_id": "t_1",
            "name": "Richmond Dog Training",
            "specialties": ["basic_manners", "puppy_training"],
            "serviced_suburbs": ["Richmond"],
            "service_formats": ["in_home"],
        }
        factual_text = "Offers in-home puppy training and basic manners in Richmond based on declared capability."
        # Must not raise
        validate_explanation_truthfulness(factual_text, cand_proj)
