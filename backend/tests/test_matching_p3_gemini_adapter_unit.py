"""Unit tests for Package P3: Real Gemini Matching Adapter & Sanitized Fallback.

Governed by:
- AGENTS.md (Rule 6A, locked boundaries)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md (M3, P3)
- specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md (Section 3, 4, 5)
- User Brief: P3 GeminiMatchingAdapter requirements

Acceptance Criteria:
1. Provider-prompt allow-list enforcement (strictly contract_version, owner signals, candidates allow-list).
2. Absolute exclusion of commercial tier, pricing, bios, reviews, URLs, contact fields, and candidate documents.
3. System instruction verbatim compliance.
4. Timeout enforcement (5-second timeout, GeminiTimeoutError, fallback engaged, degraded=True).
5. Rate limit handling (HTTP 429, GeminiRateLimitError, fallback engaged, degraded=True).
6. Malformed JSON & non-conforming schema rejection (ValueError, fallback engaged, degraded=True).
7. Closed-pool validation: model hallucinating candidate ID not in eligible candidate list is rejected.
8. Score range validation: semantic_fit strictly in [0.0, 1.0].
9. Server-side deterministic explanation rendering from permitted facts (model does not author explanations).
10. Unconfigured / unavailable client raises typed GeminiUnavailableError and engages fallback.
11. Unexpected programming errors propagate (do not falsely engage fallback).
12. Sanitized degradation metadata logging: provider, model, latency_ms, decision_state, policy_version,
    with zero prompt text, raw descriptions, tokens, IPs, emails, or phone numbers.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import ai
from services.matching_contract_v2 import (
    DecisionResponseV2,
    DecisionState,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    MatchConsentIn,
    MatchRequestIn,
    MethodPreference,
    PrimaryConcern,
    ReasonCode,
    SearchScope,
    ServiceFormatPreference,
    execute_matching_with_adapter,
    execute_matching_with_adapter_async,
)


@pytest.fixture(autouse=True)
def cleanup_ai_state(monkeypatch):
    """Ensure clean test environment without live credentials or residual degradation events."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ai.clear_degradation_events()
    ai.set_db(None)
    yield
    ai.clear_degradation_events()
    ai.set_db(None)


def _make_candidate(
    trainer_id: str,
    name: str = "Test Trainer",
    suburb: str = "Richmond",
    specialties: Optional[List[str]] = None,
    service_formats: Optional[List[str]] = None,
    life_stages: Optional[List[str]] = None,
    tier: str = "pro",
    pricing: str = "$150/hr",
    bio: str = "Extensive training experience with all breeds.",
    phone: str = "0400000000",
    email: str = "trainer@example.com",
    url: str = "https://example.com/trainer",
) -> Dict[str, Any]:
    return {
        "trainer_id": trainer_id,
        "id": trainer_id,
        "name": name,
        "suburb": suburb,
        "serviced_suburbs": [suburb, "Melbourne-Wide Mobile"],
        "specialties": specialties or ["obedience", "puppy_training"],
        "service_formats": service_formats or ["in_home", "online"],
        "life_stages": life_stages or ["puppy", "adolescent", "adult"],
        "training_philosophy": "Positive Reinforcement / Force-Free",
        "catchment_type": "specific_suburbs",
        "delivery_constraints": {"in_home_available": True, "travel_distance_km": 15.0},
        "match_eligible": True,
        # Commercial / forbidden fields
        "tier": tier,
        "pricing": pricing,
        "bio": bio,
        "phone": phone,
        "email": email,
        "website": url,
        "reviews": [{"rating": 5, "text": "Amazing trainer!"}],
        "acquisition_evidence": {"raw_doc": "some private document"},
    }


def _make_request(
    suburb: str = "Richmond",
    concerns: Optional[List[str]] = None,
    age_months: int = 12,
    description: str = "Barks at other dogs on leash, contact me at test@example.com or 0411222333",
) -> MatchRequestIn:
    return MatchRequestIn(
        suburb_or_postcode=suburb,
        dog_age_months=age_months,
        primary_concerns=concerns or [PrimaryConcern.BASIC_MANNERS.value],
        service_format=ServiceFormatPreference.IN_HOME.value,
        method_preference=MethodPreference.NO_PREFERENCE.value,
        behaviour_description=description,
        consent=MatchConsentIn(
            match_processing=True,
            terms=True,
            referral_contact=False,
            follow_up=False,
        ),
    )


class TestGeminiInputAllowListAndSanitization:
    """Verify input allow-list and commercial data exclusion."""

    def test_prompt_allow_list_structure(self):
        req = _make_request()
        cands = [_make_candidate("t_01")]
        payload = ai.build_gemini_matching_input(req, cands)

        # 1. Top-level keys must ONLY be contract_version, owner, candidates
        assert set(payload.keys()) == {"contract_version", "owner", "candidates"}
        assert payload["contract_version"] == "v2"

        # 2. Owner keys must ONLY be allow-listed fields
        owner = payload["owner"]
        assert set(owner.keys()) == {
            "dog_age_category",
            "primary_concerns",
            "service_format",
            "method_preference",
            "behaviour_description",
        }
        assert owner["dog_age_category"] == "adolescent"

        # 3. Sanitized description must redact email and phone
        assert "test@example.com" not in owner["behaviour_description"]
        assert "0411222333" not in owner["behaviour_description"]

        # 4. Candidate keys must ONLY be allow-listed candidate fields
        cand = payload["candidates"][0]
        assert set(cand.keys()) == {
            "trainer_id",
            "specialties",
            "service_formats",
            "life_stages",
            "training_philosophy",
            "catchment_type",
            "serviced_suburbs",
            "delivery_constraints",
        }

    def test_strict_exclusion_of_commercial_and_private_fields(self):
        req = _make_request()
        cands = [
            _make_candidate(
                "t_cand_01",
                tier="pro",
                pricing="$200",
                bio="Secret bio",
                phone="0499888777",
                email="secret@trainer.com",
                url="https://secret.com",
            )
        ]
        payload = ai.build_gemini_matching_input(req, cands)
        json_str = json.dumps(payload)

        # Forbidden strings must NEVER appear in the payload
        forbidden_terms = [
            "\"tier\"",
            "\"pro\"",
            "\"pricing\"",
            "$200",
            "Secret bio",
            "0499888777",
            "secret@trainer.com",
            "https://secret.com",
            "\"reviews\"",
            "\"acquisition_evidence\"",
        ]
        for term in forbidden_terms:
            assert term not in json_str, f"Forbidden term '{term}' leaked into Gemini payload"

    def test_system_instruction_verbatim(self):
        expected_substrings = [
            "You are DTD’s constrained fit assessor.",
            "Assess fit only among the supplied, already eligible trainer candidates.",
            "You are not a safety triage service and must not give veterinary, medical, legal, behavioural-treatment, handling, or emergency advice.",
            "Use only the supplied structured fields and sanitised owner signals.",
            "Do not infer, invent, embellish, or use commercial status.",
            "Never claim availability, credentials, outcomes, personality traits, diagnoses, guarantees, rankings, reviews, or facts not present in the input.",
            "Return JSON only.",
            "Every trainer_id must be from the supplied candidate list.",
            "Return a semantic_fit from 0.00 to 1.00 and only approved factual reason codes.",
            "Do not write public-facing prose.",
            "The application renders explanations from validated reason codes and permitted facts.",
        ]
        for sub in expected_substrings:
            assert sub in ai.MATCHING_SYSTEM_INSTRUCTION, f"Missing system instruction element: '{sub}'"


class TestGeminiMatchingAdapterExecution:
    """Verify GeminiMatchingAdapter runtime behaviors with mocked GenAI client."""

    def test_unconfigured_client_raises_unavailable_and_records_degradation(self):
        adapter = ai.GeminiMatchingAdapter(client=None)
        req = _make_request()
        cands = [_make_candidate("t_01")]

        with pytest.raises(GeminiUnavailableError):
            asyncio.run(adapter.call_model_async(req, cands))

        # Check recorded degradation event
        events = asyncio.run(ai.get_degradation_events(limit=10))
        assert len(events) > 0
        latest = events[0]
        assert latest["error_type"] == "unavailable_service"
        assert latest["error_code"] == "UNAVAILABLE_UNCONFIGURED"
        assert latest["fallback_used"] is True
        assert latest["policy_version"] == "v2"
        # Verify no PII
        assert "test@example.com" not in str(latest)
        assert "0411222333" not in str(latest)

    def test_gemini_timeout_raises_timeout_error_and_records_degradation(self):
        # Mock client whose generate_content hangs
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10.0)

        mock_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=slow_generate)
        )
        mock_client = SimpleNamespace(aio=mock_aio)

        adapter = ai.GeminiMatchingAdapter(client=mock_client, timeout_s=0.05)
        req = _make_request()
        cands = [_make_candidate("t_01")]

        with pytest.raises(GeminiTimeoutError) as exc_info:
            asyncio.run(adapter.call_model_async(req, cands))

        assert "timed out" in str(exc_info.value)
        events = asyncio.run(ai.get_degradation_events(limit=5))
        latest = events[0]
        assert latest["error_type"] == "timeout"
        assert latest["fallback_used"] is True

    def test_gemini_rate_limit_raises_rate_limit_error(self):
        async def rate_limited_generate(*args, **kwargs):
            raise RuntimeError("Resource has been exhausted (e.g. check quota) 429")

        mock_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=rate_limited_generate)
        )
        mock_client = SimpleNamespace(aio=mock_aio)

        adapter = ai.GeminiMatchingAdapter(client=mock_client)
        req = _make_request()
        cands = [_make_candidate("t_01")]

        with pytest.raises(GeminiRateLimitError):
            asyncio.run(adapter.call_model_async(req, cands))

        events = asyncio.run(ai.get_degradation_events(limit=5))
        latest = events[0]
        assert latest["error_type"] == "rate_limit"
        assert latest["error_code"] == "RATE_LIMIT_429"

    def test_gemini_malformed_json_raises_value_error(self):
        async def bad_json_generate(*args, **kwargs):
            return SimpleNamespace(text="NOT JSON AT ALL! <xml></xml>")

        mock_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=bad_json_generate)
        )
        mock_client = SimpleNamespace(aio=mock_aio)

        adapter = ai.GeminiMatchingAdapter(client=mock_client)
        req = _make_request()
        cands = [_make_candidate("t_01")]

        with pytest.raises(ValueError) as exc:
            asyncio.run(adapter.call_model_async(req, cands))
        assert "malformed" in str(exc.value).lower()
        latest = asyncio.run(ai.get_degradation_events(limit=1))[0]
        assert latest["error_type"] == "malformed_output"
        assert latest["error_code"] == "MALFORMED_OUTPUT"

    def test_matching_request_disables_automatic_function_calling_and_bounds_output(self):
        captured = {}

        async def valid_generate(*args, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text=json.dumps({
                "candidates": [{
                    "trainer_id": "t_01",
                    "semantic_fit": 0.88,
                    "reason_codes": ["capability_concern_match"],
                }],
            }))

        mock_client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=valid_generate)))
        adapter = ai.GeminiMatchingAdapter(client=mock_client)
        asyncio.run(adapter.call_model_async(_make_request(), [_make_candidate("t_01")]))

        config = captured["config"]
        dumped = config.model_dump(by_alias=False) if hasattr(config, "model_dump") else config
        automatic = dumped["automatic_function_calling"]
        thinking = dumped["thinking_config"]
        assert automatic["disable"] is True
        assert thinking["thinking_budget"] == 0
        assert dumped["max_output_tokens"] == 512
        assert dumped["response_schema"] == ai.MATCHING_RESPONSE_SCHEMA

    def test_closed_pool_validation_rejects_hallucinated_candidate(self):
        async def hallucinated_cand_generate(*args, **kwargs):
            payload = {
                "candidates": [
                    {
                        "trainer_id": "hallucinated_rogue_trainer_99",
                        "semantic_fit": 0.95,
                        "reason_codes": ["capability_concern_match"],
                    }
                ]
            }
            return SimpleNamespace(text=json.dumps(payload))

        mock_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=hallucinated_cand_generate)
        )
        mock_client = SimpleNamespace(aio=mock_aio)

        adapter = ai.GeminiMatchingAdapter(client=mock_client)
        req = _make_request()
        cands = [_make_candidate("t_01")]

        with pytest.raises(ValueError) as exc:
            asyncio.run(adapter.call_model_async(req, cands))
        assert "not in eligible pool" in str(exc.value)

    def test_out_of_bounds_semantic_fit_rejected(self):
        async def invalid_fit_generate(*args, **kwargs):
            payload = {
                "candidates": [
                    {
                        "trainer_id": "t_01",
                        "semantic_fit": 1.50,  # Invalid: > 1.00
                        "reason_codes": ["capability_concern_match"],
                    }
                ]
            }
            return SimpleNamespace(text=json.dumps(payload))

        mock_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=invalid_fit_generate)
        )
        mock_client = SimpleNamespace(aio=mock_aio)

        adapter = ai.GeminiMatchingAdapter(client=mock_client)
        req = _make_request()
        cands = [_make_candidate("t_01")]

        with pytest.raises(ValueError) as exc:
            asyncio.run(adapter.call_model_async(req, cands))
        assert "out of bounds" in str(exc.value)

    def test_valid_model_output_renders_deterministic_explanations(self):
        async def valid_generate(*args, **kwargs):
            payload = {
                "candidates": [
                    {
                        "trainer_id": "t_01",
                        "semantic_fit": 0.88,
                        "reason_codes": ["capability_concern_match", "service_area_match"],
                    }
                ]
            }
            return SimpleNamespace(text=json.dumps(payload))

        mock_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=valid_generate)
        )
        mock_client = SimpleNamespace(aio=mock_aio)

        adapter = ai.GeminiMatchingAdapter(client=mock_client)
        req = _make_request()
        cands = [_make_candidate("t_01", name="Factual Trainer", suburb="Richmond")]

        out = asyncio.run(adapter.call_model_async(req, cands))
        assert out["decision_state"] == "recommendations"
        assert len(out["candidates"]) == 1
        cand = out["candidates"][0]
        assert cand["trainer_id"] == "t_01"
        assert cand["match_score"] == 0.88
        # Explanation must be deterministically rendered by server from factual attributes
        assert isinstance(cand["explanation"], str)
        assert len(cand["explanation"]) > 0
        assert "Richmond" in cand["explanation"]

    def test_adapter_fallback_integration_on_failure(self):
        """When Gemini adapter fails, execute_matching_with_adapter_async engages deterministic fallback."""
        async def failing_generate(*args, **kwargs):
            raise RuntimeError("API quota exceeded 429")

        mock_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=failing_generate)
        )
        mock_client = SimpleNamespace(aio=mock_aio)

        adapter = ai.GeminiMatchingAdapter(client=mock_client)
        req = _make_request(concerns=[PrimaryConcern.BASIC_MANNERS.value])
        pool = [_make_candidate("t_01", suburb="Richmond")]

        resp = asyncio.run(execute_matching_with_adapter_async(req, pool, adapter))
        assert isinstance(resp, DecisionResponseV2)
        assert resp.degraded is True
        assert resp.decision_state == DecisionState.DEGRADED_RECOMMENDATIONS
        assert len(resp.candidates) == 1
        assert resp.candidates[0].trainer_id == "t_01"

    def test_unexpected_programming_error_propagates(self):
        """Unexpected programming errors (e.g. KeyError in wrapper) must NOT be masked as degraded fallback."""
        class CrashingAdapter:
            async def call_model_async(self, *args, **kwargs):
                raise KeyError("Unexpected unhandled dictionary key missing")

        req = _make_request()
        pool = [_make_candidate("t_01")]

        with pytest.raises(KeyError):
            asyncio.run(execute_matching_with_adapter_async(req, pool, CrashingAdapter()))
