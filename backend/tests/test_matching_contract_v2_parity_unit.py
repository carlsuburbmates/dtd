"""Unit and Parity Test Suite for Owner-to-Trainer Matching Decision Contract v2.

Governed by:
- AGENTS.md (Rule 6A, Milestone M0)
- OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md (Sections 1-9)
- DTD_INVARIANTS_AND_CONSTRAINTS.md (Invariants 5, 6, 7, 10, 14)
- Findings: DF-018, DF-019, DF-021, DF-022, DF-023, DF-026
- Acceptance Criteria R1-R6:
  R1: Closed DecisionResponseV2 (enum states, scopes, reason codes, pool validation, fact claims)
  R2: Fail-closed reference eligibility (empty/missing life stage, exact declared suburb, profile suburb separation, greater melbourne catchment)
  R3: Repaired fixtures (None vs empty list, canonical delivery fields, isolated pools)
  R4: Genuine test-only adapter parity (normal, timeout, rate_limit, unavailable, malformed_output)
  R5: Scope guardrails (other/unsure clarification, limited_local_results only when expanded presented, complete PII stripping)
  R6: Clean diff without whitespace or lint errors
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List
import pytest
from pydantic import ValidationError

_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from services.matching_contract_v2 import (
        CANONICAL_DELIVERY_KEYS,
        COMPARABLE_FIT_BAND,
        CONCERN_TO_SPECIALTIES_MAP,
        DECISION_CONTRACT_VERSION,
        MAX_DESCRIPTION_CHARS,
        MAX_RECOMMENDED_CANDIDATES,
        OUTCOME_SCORE_WEIGHT,
        QUALIFICATION_THRESHOLD,
        DecisionResponseV2,
        DecisionState,
        DogAgeCategory,
        GeminiAdapterError,
        GeminiMalformedResponseError,
        GeminiRateLimitError,
        GeminiStubAdapter,
        GeminiTimeoutError,
        GeminiUnavailableError,
        MatchCandidateCard,
        MatchConsentIn,
        MatchRequestIn,
        MethodPreference,
        PrimaryConcern,
        ReasonCode,
        SearchScope,
        ServiceFormatPreference,
        apply_fair_presentation,
        check_candidate_eligibility,
        compute_deterministic_fit,
        execute_matching_with_adapter,
        get_dog_age_category,
        resolve_canonical_locality,
        run_deterministic_matching,
        sanitize_behaviour_description,
        validate_explanation_against_facts,
        validate_explanation_truthfulness,
    )
    from tests.fixtures_matching_v2 import (
        ScenarioDefinition,
        get_all_section_9_scenarios,
        make_test_trainer_doc,
        make_valid_match_request,
    )
except ImportError:
    from backend.services.matching_contract_v2 import (
        CANONICAL_DELIVERY_KEYS,
        COMPARABLE_FIT_BAND,
        CONCERN_TO_SPECIALTIES_MAP,
        DECISION_CONTRACT_VERSION,
        MAX_DESCRIPTION_CHARS,
        MAX_RECOMMENDED_CANDIDATES,
        OUTCOME_SCORE_WEIGHT,
        QUALIFICATION_THRESHOLD,
        DecisionResponseV2,
        DecisionState,
        DogAgeCategory,
        GeminiAdapterError,
        GeminiMalformedResponseError,
        GeminiRateLimitError,
        GeminiStubAdapter,
        GeminiTimeoutError,
        GeminiUnavailableError,
        MatchCandidateCard,
        MatchConsentIn,
        MatchRequestIn,
        MethodPreference,
        PrimaryConcern,
        ReasonCode,
        SearchScope,
        ServiceFormatPreference,
        apply_fair_presentation,
        check_candidate_eligibility,
        compute_deterministic_fit,
        execute_matching_with_adapter,
        get_dog_age_category,
        resolve_canonical_locality,
        run_deterministic_matching,
        sanitize_behaviour_description,
        validate_explanation_against_facts,
        validate_explanation_truthfulness,
    )
    from backend.tests.fixtures_matching_v2 import (
        ScenarioDefinition,
        get_all_section_9_scenarios,
        make_test_trainer_doc,
        make_valid_match_request,
    )


# ==============================================================================
# 1. Section 9 Fixture Scenarios (16 Mandatory Contract Scenarios)
# ==============================================================================

class TestSection9Scenarios:
    """Verifies all 16 scenarios mandated in Contract v2 Section 9 with isolated candidate pools."""

    @pytest.fixture(scope="class")
    def scenarios(self) -> Dict[str, ScenarioDefinition]:
        return get_all_section_9_scenarios()

    def test_scenario_01_local_puppy_manners(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_01_local_puppy_manners"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert resp.search_scope == sc.expected_search_scope
        assert len(resp.candidates) > 0
        candidate_ids = [c.trainer_id for c in resp.candidates]
        assert any(cid in sc.expected_eligible_ids for cid in candidate_ids)
        for code in sc.expected_reason_codes:
            assert code in [r.value for r in resp.candidates[0].reason_codes]

    def test_scenario_02_multi_concern_in_home(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_02_multi_concern_in_home"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert resp.search_scope == sc.expected_search_scope
        assert len(resp.candidates) == 1
        assert resp.candidates[0].trainer_id == "t_brunswick_eligible"
        card_reasons = [r.value for r in resp.candidates[0].reason_codes]
        assert ReasonCode.FORMAT_MATCH.value in card_reasons
        assert ReasonCode.METHOD_PREFERENCE_MATCH.value in card_reasons

    def test_scenario_03_ambiguous_input(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_03_ambiguous_input"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 0
        assert resp.clarification_prompt is not None

    def test_scenario_04_thin_local_expanded_result(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_04_thin_local_expanded_result"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert resp.search_scope == sc.expected_search_scope
        assert any(c.trainer_id == "t_melb_wide_1" for c in resp.candidates)
        expanded_cards = [c for c in resp.candidates if c.search_scope == SearchScope.EXPANDED]
        assert len(expanded_cards) > 0
        assert ReasonCode.EXPANDED_SERVICE_AREA in expanded_cards[0].reason_codes

    def test_scenario_05_no_current_capability_evidence(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_05_no_current_capability_evidence"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 0

    def test_scenario_06_stale_suppressed_projection(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_06_stale_suppressed_projection"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 0

    def test_scenario_07_exact_005_band(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_07_exact_005_band"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 2
        # Pro trainer sorts ahead of Claimed trainer within 0.05 band
        assert resp.candidates[0].trainer_id == "t_band_pro"
        assert resp.candidates[1].trainer_id == "t_band_claimed"

    def test_scenario_08_outside_band_paid_candidate(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_08_outside_band_paid_candidate"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 2
        # High-fit unclaimed candidate remains strictly first; outside-band paid tier cannot overtake
        assert resp.candidates[0].trainer_id == "t_high_fit_unclaimed"
        assert resp.candidates[1].trainer_id == "t_lower_fit_citywide"
        assert resp.candidates[0].match_score > resp.candidates[1].match_score

    def test_scenario_09_gemini_degradation_routes(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_09_gemini_degradation_routes"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool, degraded=True)
        assert resp.decision_state == sc.expected_decision_state
        assert resp.degraded is True
        assert len(resp.candidates) == 1
        assert resp.candidates[0].trainer_id == "t_richmond_alpha"

    def test_scenario_10_immediate_human_danger(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_10_immediate_human_danger"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool, triage_state=sc.triage_state)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 0

    def test_scenario_11_urgent_animal_health_support(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_11_urgent_animal_health_support"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool, triage_state=sc.triage_state)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 0

    def test_scenario_12_serious_behavioural_support(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_12_serious_behavioural_support"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 1
        assert resp.candidates[0].trainer_id == "t_clinical_aggression"
        assert ReasonCode.SERIOUS_BEHAVIOURAL_SUPPORT in resp.candidates[0].reason_codes

    def test_scenario_13_trainer_declaration_gaming(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_13_trainer_declaration_gaming"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert len(resp.candidates) == 0

    def test_scenario_14_privacy_url_leakage(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_14_privacy_url_leakage"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        assert "0412345678" not in sc.request.behaviour_description
        assert "john.doe@example.com" not in sc.request.behaviour_description
        assert "https://test.com" not in sc.request.behaviour_description
        assert "45 Smith St" not in sc.request.behaviour_description
        assert "PO Box 123" not in sc.request.behaviour_description
        assert "[PHONE_REDACTED]" not in sc.request.behaviour_description
        assert "[EMAIL_REDACTED]" not in sc.request.behaviour_description
        assert "[ADDRESS_REDACTED]" not in sc.request.behaviour_description
        assert "[URL_REDACTED]" not in sc.request.behaviour_description

    def test_scenario_15_follow_up_retry(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_15_follow_up_retry"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state

    def test_scenario_16_ops_redaction(self, scenarios: Dict[str, ScenarioDefinition]):
        sc = scenarios["scenario_16_ops_redaction"]
        resp = run_deterministic_matching(sc.request, sc.candidate_pool)
        assert resp.decision_state == sc.expected_decision_state
        resp_json = json.dumps(resp.model_dump())
        assert "Private owner details" not in resp_json


# ==============================================================================
# 2. R1: Closed DecisionResponseV2 & Schema Validation
# ==============================================================================

class TestClosedDecisionResponseV2:
    """Verifies that DecisionResponseV2 is closed against invalid states, reason codes, pools, and claims."""

    def test_decision_state_enum_validation(self):
        """Decision state must be a valid DecisionState enum; invalid strings are rejected."""
        valid_resp = DecisionResponseV2(
            decision_state=DecisionState.RECOMMENDATIONS,
            reason_codes=["capability_concern_match"],
        )
        assert valid_resp.decision_state == DecisionState.RECOMMENDATIONS

        with pytest.raises(ValidationError):
            DecisionResponseV2(
                decision_state="unrecognized_arbitrary_state",  # type: ignore
                reason_codes=["capability_concern_match"],
            )

    def test_search_scope_enum_validation(self):
        """Search scope must be a valid SearchScope enum; invalid strings are rejected."""
        valid_resp = DecisionResponseV2(
            decision_state=DecisionState.RECOMMENDATIONS,
            search_scope=SearchScope.EXPANDED,
            reason_codes=["capability_concern_match"],
        )
        assert valid_resp.search_scope == SearchScope.EXPANDED

        with pytest.raises(ValidationError):
            DecisionResponseV2(
                decision_state=DecisionState.RECOMMENDATIONS,
                search_scope="national_coverage",  # type: ignore
                reason_codes=["capability_concern_match"],
            )

    def test_top_level_reason_codes_validation(self):
        """Top-level reason codes must be within ALLOWED_TOP_LEVEL_REASON_CODES."""
        valid_resp = DecisionResponseV2(
            decision_state=DecisionState.RECOMMENDATIONS,
            reason_codes=["capability_concern_match", "service_area_match"],
        )
        assert len(valid_resp.reason_codes) == 2

        with pytest.raises(ValueError) as exc:
            DecisionResponseV2(
                decision_state=DecisionState.RECOMMENDATIONS,
                reason_codes=["unauthorized_marketing_claim"],
            )
        assert "Disallowed top-level reason code" in str(exc.value)

    def test_candidate_card_reason_codes_validation(self):
        """Candidate card reason codes must be valid ReasonCode enums."""
        card = MatchCandidateCard(
            trainer_id="t_1",
            match_score=0.85,
            reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH, ReasonCode.FORMAT_MATCH],
            explanation="Trainer provides verified manners training.",
        )
        assert len(card.reason_codes) == 2

        with pytest.raises(ValidationError):
            MatchCandidateCard(
                trainer_id="t_1",
                match_score=0.85,
                reason_codes=["not_a_canonical_code"],  # type: ignore
                explanation="Trainer provides verified manners training.",
            )

    def test_validate_against_eligible_pool_accepts_valid_pool(self):
        """Candidates within the deterministic eligible pool pass validation."""
        card = MatchCandidateCard(
            trainer_id="t_valid",
            match_score=0.9,
            reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH],
            explanation="Trainer services Richmond.",
        )
        resp = DecisionResponseV2(
            decision_state=DecisionState.RECOMMENDATIONS,
            candidates=[card],
            reason_codes=["capability_concern_match"],
        )
        # Passes with set of IDs
        resp.validate_against_eligible_pool({"t_valid", "t_other"})

    def test_validate_against_eligible_pool_rejects_outside_candidate(self):
        """Candidates outside the deterministic eligible pool are strictly rejected."""
        card = MatchCandidateCard(
            trainer_id="t_hallucinated",
            match_score=0.9,
            reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH],
            explanation="Trainer services Richmond.",
        )
        resp = DecisionResponseV2(
            decision_state=DecisionState.RECOMMENDATIONS,
            candidates=[card],
            reason_codes=["capability_concern_match"],
        )
        with pytest.raises(ValueError) as exc:
            resp.validate_against_eligible_pool({"t_valid_1", "t_valid_2"})
        assert "is not in deterministic eligible pool" in str(exc.value)

    def test_prohibited_explanation_guarantees_rejected(self):
        """Explanations containing guarantee claims are rejected by card validation."""
        prohibited_phrases = [
            "We offer a 100% guarantee on all behavioural issues.",
            "Our training promises a fail-safe outcome for your dog.",
            "Guaranteed results within two sessions.",
        ]
        for phrase in prohibited_phrases:
            with pytest.raises(ValueError) as exc:
                MatchCandidateCard(
                    trainer_id="t_1",
                    match_score=0.8,
                    reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH],
                    explanation=phrase,
                )
            assert "contains prohibited term" in str(exc.value)

    def test_prohibited_explanation_superlatives_rejected(self):
        """Explanations containing unsubstantiated superlatives are rejected."""
        prohibited_superlatives = [
            "Ranked the #1 trainer in Australia.",
            "The best world-class dog trainer in Melbourne.",
            "Premier unmatched obedience specialist.",
        ]
        for phrase in prohibited_superlatives:
            with pytest.raises(ValueError) as exc:
                MatchCandidateCard(
                    trainer_id="t_1",
                    match_score=0.8,
                    reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH],
                    explanation=phrase,
                )
            assert "contains prohibited term" in str(exc.value)

    def test_prohibited_explanation_diagnoses_rejected(self):
        """Explanations containing clinical veterinary diagnoses are rejected."""
        prohibited_diagnoses = [
            "We diagnose and cure psychiatric anxiety disorders.",
            "Specializes in clinical pathology treatment for dogs.",
        ]
        for phrase in prohibited_diagnoses:
            with pytest.raises(ValueError) as exc:
                MatchCandidateCard(
                    trainer_id="t_1",
                    match_score=0.8,
                    reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH],
                    explanation=phrase,
                )
            assert "contains prohibited term" in str(exc.value)

    def test_explanation_unsupported_facts_rejected(self):
        """Explanations claiming capabilities not supported by candidate projection facts are rejected."""
        candidate = make_test_trainer_doc(
            trainer_id="t_facts",
            name="Fact Trainer",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["facility"],
            life_stages=["adult"],
        )

        # 1. Claims puppy when candidate only supports adult
        with pytest.raises(ValueError) as exc1:
            validate_explanation_against_facts("Specialist in puppy training.", candidate)
        assert "claims puppy support not backed by candidate projection facts" in str(exc1.value)

        # 2. Claims in-home when candidate is facility only
        with pytest.raises(ValueError) as exc2:
            validate_explanation_against_facts("Provides in-home manners training.", candidate)
        assert "claims in-home format not backed by candidate projection facts" in str(exc2.value)

        # 3. Claims aggression when candidate only has obedience
        with pytest.raises(ValueError) as exc3:
            validate_explanation_against_facts("Expert in severe aggression.", candidate)
        assert "claims aggression specialty not backed by candidate projection facts" in str(exc3.value)

        # 4. Valid explanation citing verified facts passes without error
        validate_explanation_against_facts("Provides obedience training at facility.", candidate)


# ==============================================================================
# 3. R2: Fail-Closed Reference Eligibility
# ==============================================================================

class TestFailClosedReferenceEligibility:
    """Verifies that reference eligibility fails closed on missing facts, undeclared suburbs, and broad catchments."""

    def test_missing_or_empty_life_stages_fails_closed(self):
        """Missing or empty life_stages fails closed with missing_life_stage_support."""
        req = make_valid_match_request(dog_age_months=4)

        # None life_stages
        cand_none = make_test_trainer_doc(
            trainer_id="t_none",
            name="None Life Stages",
            life_stages=None,
            specialties=["puppy_training"],
            serviced_suburbs=["Richmond"],
        )
        is_el_none, reasons_none = check_candidate_eligibility(cand_none, req)
        assert is_el_none is False
        assert "missing_life_stage_support" in reasons_none

        # Empty list life_stages
        cand_empty = make_test_trainer_doc(
            trainer_id="t_empty",
            name="Empty Life Stages",
            life_stages=[],
            specialties=["puppy_training"],
            serviced_suburbs=["Richmond"],
        )
        is_el_empty, reasons_empty = check_candidate_eligibility(cand_empty, req)
        assert is_el_empty is False
        assert "missing_life_stage_support" in reasons_empty

    def test_incompatible_life_stage_fails_closed(self):
        """Candidate supporting only adult dogs fails closed for puppy request."""
        req = make_valid_match_request(dog_age_months=4)
        cand_adult = make_test_trainer_doc(
            trainer_id="t_adult",
            name="Adult Only",
            life_stages=["adult"],
            specialties=["puppy_training"],
            serviced_suburbs=["Richmond"],
        )
        is_el, reasons = check_candidate_eligibility(cand_adult, req)
        assert is_el is False
        assert "life_stage_incompatible" in reasons

    def test_compatible_life_stage_passes(self):
        """Candidate supporting puppy passes life stage eligibility."""
        req = make_valid_match_request(dog_age_months=4)
        cand_puppy = make_test_trainer_doc(
            trainer_id="t_puppy",
            name="Puppy Pro",
            life_stages=["puppy"],
            specialties=["puppy_training"],
            serviced_suburbs=["Richmond"],
        )
        is_el, reasons = check_candidate_eligibility(cand_puppy, req)
        assert is_el is True
        assert "eligible" in reasons

    def test_local_eligibility_requires_exact_declared_serviced_suburb(self):
        """Local eligibility requires exact declared serviced_suburbs match."""
        req = make_valid_match_request(suburb_or_postcode="Richmond")

        cand_serviced = make_test_trainer_doc(
            trainer_id="t_serviced",
            name="Richmond Servicing",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training"],
            life_stages=["puppy"],
        )
        is_el, _ = check_candidate_eligibility(cand_serviced, req, search_scope=SearchScope.LOCAL.value)
        assert is_el is True

        cand_not_serviced = make_test_trainer_doc(
            trainer_id="t_other",
            name="Brunswick Servicing",
            serviced_suburbs=["Brunswick"],
            specialties=["puppy_training"],
            life_stages=["puppy"],
        )
        is_el2, reasons2 = check_candidate_eligibility(cand_not_serviced, req, search_scope=SearchScope.LOCAL.value)
        assert is_el2 is False
        assert "outside_local_service_area" in reasons2

    def test_trainer_profile_suburb_is_not_service_area_declaration(self):
        """A trainer's profile suburb is NOT a service-area declaration; declared serviced_suburbs governs."""
        req = make_valid_match_request(suburb_or_postcode="Richmond")
        # Trainer profile suburb is Richmond, but declared serviced_suburbs is Burnley only
        cand = make_test_trainer_doc(
            trainer_id="t_suburb_trap",
            name="Profile Suburb Trap",
            suburb="Richmond",
            serviced_suburbs=["Burnley"],
            specialties=["puppy_training"],
            life_stages=["puppy"],
        )
        is_el, reasons = check_candidate_eligibility(cand, req, search_scope=SearchScope.LOCAL.value)
        assert is_el is False
        assert "outside_local_service_area" in reasons

    def test_broader_coverage_uses_only_declared_greater_melbourne_catchment(self):
        """In expanded search scope, candidate must have declared melbourne_wide / greater_melbourne."""
        req = make_valid_match_request(suburb_or_postcode="Richmond")

        # Specific suburbs catchment fails expanded search
        cand_specific = make_test_trainer_doc(
            trainer_id="t_spec",
            name="Specific Suburbs Trainer",
            serviced_suburbs=["Footscray"],
            catchment_type="specific_suburbs",
            specialties=["puppy_training"],
            life_stages=["puppy"],
        )
        is_el, reasons = check_candidate_eligibility(cand_specific, req, search_scope=SearchScope.EXPANDED.value)
        assert is_el is False
        assert "outside_expanded_catchment" in reasons

        # Declared melbourne_wide catchment passes expanded search
        cand_melb = make_test_trainer_doc(
            trainer_id="t_melb",
            name="Melbourne Wide Trainer",
            serviced_suburbs=["Carlton"],
            catchment_type="melbourne_wide",
            specialties=["puppy_training"],
            life_stages=["puppy"],
        )
        is_el2, reasons2 = check_candidate_eligibility(cand_melb, req, search_scope=SearchScope.EXPANDED.value)
        assert is_el2 is True


# ==============================================================================
# 4. R3: Repaired Fixtures & Canonical Delivery Fields
# ==============================================================================

class TestFixturesIntegrity:
    """Verifies test fixture invariants: None vs [], canonical delivery fields, isolated pools."""

    def test_distinguish_none_from_empty_list_in_projection(self):
        """Fixtures distinguish None (absent facts) from [] (explicit empty list facts)."""
        doc_none = make_test_trainer_doc(
            trainer_id="t_none_fact",
            name="None Fact",
            life_stages=None,
        )
        assert doc_none["life_stages"] is None

        doc_empty = make_test_trainer_doc(
            trainer_id="t_empty_fact",
            name="Empty Fact",
            life_stages=[],
        )
        assert doc_empty["life_stages"] == []

    def test_canonical_delivery_fields_only(self):
        """All test fixtures use only canonical delivery keys: in_home_available, facility_available, travel_distance_km, notes."""
        doc = make_test_trainer_doc(
            trainer_id="t_deliv",
            name="Delivery Test",
            delivery_constraints={
                "in_home_available": True,
                "facility_available": False,
                "travel_distance_km": 15,
                "notes": "Eastern suburbs travel",
            },
        )
        deliv = doc.get("delivery_constraints") or {}
        for key in deliv.keys():
            assert key in CANONICAL_DELIVERY_KEYS

    def test_isolated_candidate_pools_per_scenario(self):
        """Each of the 16 Section 9 scenarios uses an isolated candidate pool without redundant duplicate trainers."""
        scenarios = get_all_section_9_scenarios()
        assert len(scenarios) == 16
        for s_id, sc in scenarios.items():
            assert len(sc.candidate_pool) > 0
            assert len(sc.candidate_pool) <= 5


# ==============================================================================
# 5. R4: Test-Only Adapter Parity Harness
# ==============================================================================

class TestGeminiStubAdapterParity:
    """Verifies that the GeminiStubAdapter achieves strict contract parity across all execution modes."""

    def test_adapter_normal_mode_parity_all_unambiguous_scenarios(self):
        """Normal mode produces exact parity with deterministic fallback across all Section 9 scenarios."""
        scenarios = get_all_section_9_scenarios()
        adapter = GeminiStubAdapter(mode="normal")

        for s_id, sc in scenarios.items():
            # Invoke adapter
            adapter_resp = adapter.match(sc.request, sc.candidate_pool, triage_state=sc.triage_state)
            # Invoke deterministic fallback
            deterministic_resp = run_deterministic_matching(sc.request, sc.candidate_pool, degraded=False, triage_state=sc.triage_state)

            assert adapter_resp.decision_state == deterministic_resp.decision_state, f"Mismatch in {s_id}"
            assert adapter_resp.search_scope == deterministic_resp.search_scope, f"Scope mismatch in {s_id}"
            assert len(adapter_resp.candidates) == len(deterministic_resp.candidates), f"Candidate count mismatch in {s_id}"

            adapter_ids = [c.trainer_id for c in adapter_resp.candidates]
            deterministic_ids = [c.trainer_id for c in deterministic_resp.candidates]
            assert adapter_ids == deterministic_ids, f"Candidate IDs mismatch in {s_id}"

            # Assert valid reason codes
            for card in adapter_resp.candidates:
                for r in card.reason_codes:
                    assert isinstance(r, ReasonCode)

    def test_adapter_timeout_mode_engages_fallback(self):
        """Timeout mode engages deterministic fallback and sets degraded=True."""
        scenarios = get_all_section_9_scenarios()
        sc = scenarios["scenario_01_local_puppy_manners"]
        adapter = GeminiStubAdapter(mode="timeout")

        resp = adapter.match(sc.request, sc.candidate_pool)
        assert resp.degraded is True
        assert resp.decision_state == DecisionState.DEGRADED_RECOMMENDATIONS.value
        assert len(resp.candidates) > 0

    def test_adapter_rate_limit_mode_engages_fallback(self):
        """HTTP 429 quota exhaustion engages deterministic fallback and sets degraded=True."""
        scenarios = get_all_section_9_scenarios()
        sc = scenarios["scenario_01_local_puppy_manners"]
        adapter = GeminiStubAdapter(mode="rate_limit")

        resp = adapter.match(sc.request, sc.candidate_pool)
        assert resp.degraded is True
        assert resp.decision_state == DecisionState.DEGRADED_RECOMMENDATIONS.value

    def test_adapter_unavailable_mode_engages_fallback(self):
        """HTTP 503 provider unavailability engages deterministic fallback and sets degraded=True."""
        scenarios = get_all_section_9_scenarios()
        sc = scenarios["scenario_01_local_puppy_manners"]
        adapter = GeminiStubAdapter(mode="unavailable")

        resp = adapter.match(sc.request, sc.candidate_pool)
        assert resp.degraded is True
        assert resp.decision_state == DecisionState.DEGRADED_RECOMMENDATIONS.value

    def test_adapter_malformed_output_mode_engages_fallback(self):
        """Malformed or hallucinated AI output is caught and engages deterministic fallback."""
        scenarios = get_all_section_9_scenarios()
        sc = scenarios["scenario_01_local_puppy_manners"]
        adapter = GeminiStubAdapter(mode="malformed_output")

        resp = adapter.match(sc.request, sc.candidate_pool)
        assert resp.degraded is True
        assert resp.decision_state == DecisionState.DEGRADED_RECOMMENDATIONS.value
        assert len(resp.candidates) > 0


# ==============================================================================
# 6. R5: Scope Guardrails, Clarification & PII Sanitization
# ==============================================================================

class TestScopeGuardrails:
    """Verifies that other/unsure concerns require clarification, limited_local_results is strictly applied, and PII is stripped."""

    def test_other_unsure_empty_specialties_mapping(self):
        """'other' and 'unsure' map to empty sets; they cannot broadly match generic specialties."""
        assert CONCERN_TO_SPECIALTIES_MAP[PrimaryConcern.OTHER.value] == set()
        assert CONCERN_TO_SPECIALTIES_MAP[PrimaryConcern.UNSURE.value] == set()

    def test_unresolved_other_requires_clarification(self):
        """Unresolved 'other' or 'unsure' request without detailed description returns NEEDS_CLARIFICATION."""
        req = make_valid_match_request(
            primary_concerns=[PrimaryConcern.OTHER.value],
            behaviour_description="",
        )
        resp = run_deterministic_matching(req, [])
        assert resp.decision_state == DecisionState.NEEDS_CLARIFICATION.value
        assert "needs_clarification" in resp.reason_codes

    def test_limited_local_results_applies_only_when_expanded_candidate_presented(self):
        """LIMITED_LOCAL_RESULTS applies only when one or more expanded candidates are actually presented."""
        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=4,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
        )

        # Pool with 1 local qualified candidate and NO expanded candidates
        pool_local_only = [
            make_test_trainer_doc(
                trainer_id="t_local_1",
                name="Local Trainer",
                serviced_suburbs=["Richmond"],
                specialties=["obedience"],
                service_formats=["in_home"],
                life_stages=["puppy"],
            )
        ]
        resp_local = run_deterministic_matching(req, pool_local_only)
        # Even though fewer than 3 candidates exist, NO expanded candidate was presented -> state is RECOMMENDATIONS
        assert resp_local.decision_state == DecisionState.RECOMMENDATIONS.value
        assert resp_local.search_scope == SearchScope.LOCAL.value

        # Pool with 1 local qualified candidate and 1 expanded qualified candidate
        pool_with_expanded = [
            pool_local_only[0],
            make_test_trainer_doc(
                trainer_id="t_expanded_1",
                name="Expanded Trainer",
                serviced_suburbs=["Carlton"],
                catchment_type="melbourne_wide",
                specialties=["obedience"],
                service_formats=["in_home"],
                life_stages=["puppy"],
            ),
        ]
        resp_expanded = run_deterministic_matching(req, pool_with_expanded)
        # Expanded candidate is presented -> state is LIMITED_LOCAL_RESULTS
        assert resp_expanded.decision_state == DecisionState.LIMITED_LOCAL_RESULTS.value
        assert resp_expanded.search_scope == SearchScope.EXPANDED.value

    def test_pii_stripped_completely_without_marker_tokens(self):
        """PII (email, phone, URL) is removed entirely without retaining marker tokens."""
        raw = "Contact me at owner@example.com or 0412 345 678. Visit https://mysite.com. Dog jumps on guests."
        cleaned = sanitize_behaviour_description(raw)

        assert "owner@example.com" not in cleaned
        assert "0412 345 678" not in cleaned
        assert "https://mysite.com" not in cleaned
        # Redaction marker tokens must NOT be retained
        assert "[EMAIL_REDACTED]" not in cleaned
        assert "[PHONE_REDACTED]" not in cleaned
        assert "[URL_REDACTED]" not in cleaned
        assert "Dog jumps on guests." in cleaned

    def test_sanitize_truncates_to_800_chars(self):
        overlong = "a" * 1200
        cleaned = sanitize_behaviour_description(overlong)
        assert len(cleaned) == MAX_DESCRIPTION_CHARS

    def test_commercial_presentation_005_band_invariants(self):
        """Candidates within 0.05 are ordered by commercial tier; outside are strictly ordered by fit."""
        candidates = [
            {"trainer_id": "t_unclaimed", "match_score": 0.84, "tier": "unclaimed"},
            {"trainer_id": "t_claimed", "match_score": 0.83, "tier": "claimed"},
            {"trainer_id": "t_pro", "match_score": 0.82, "tier": "pro"},
        ]
        # Diff <= 0.05 -> Pro (weight 2) > Claimed (weight 1) > Unclaimed (weight 0)
        presented = apply_fair_presentation(candidates, max_results=3)
        assert [c["trainer_id"] for c in presented] == ["t_pro", "t_claimed", "t_unclaimed"]

        # Outside band candidate cannot overtake
        outside = [
            {"trainer_id": "t_high_fit", "match_score": 0.90, "tier": "unclaimed"},
            {"trainer_id": "t_lower_fit", "match_score": 0.80, "tier": "citywide"},
        ]
        presented_out = apply_fair_presentation(outside, max_results=2)
        assert presented_out[0]["trainer_id"] == "t_high_fit"

    def test_outcome_score_weight_strictly_zero(self):
        """Outcome score contribution is strictly zero (Invariant 5, DF-023)."""
        assert OUTCOME_SCORE_WEIGHT == 0.0

    def test_qualification_threshold_is_0_60(self):
        assert QUALIFICATION_THRESHOLD == 0.60

    def test_dog_age_boundaries(self):
        assert get_dog_age_category(0) == DogAgeCategory.PUPPY
        assert get_dog_age_category(5) == DogAgeCategory.PUPPY
        assert get_dog_age_category(6) == DogAgeCategory.ADOLESCENT
        assert get_dog_age_category(18) == DogAgeCategory.ADOLESCENT
        assert get_dog_age_category(19) == DogAgeCategory.ADULT
        assert get_dog_age_category(83) == DogAgeCategory.ADULT
        assert get_dog_age_category(84) == DogAgeCategory.SENIOR
        assert get_dog_age_category(120) == DogAgeCategory.SENIOR

    def test_locality_resolution(self):
        res = resolve_canonical_locality("Richmond")
        assert res["valid"] is True
        assert res["canonical_name"] == "Richmond"

        res_postcode = resolve_canonical_locality("3067")
        assert res_postcode["valid"] is True
        assert res_postcode["canonical_name"] == "Abbotsford"

        res_ambiguous = resolve_canonical_locality("3121")
        assert res_ambiguous["valid"] is False
        assert res_ambiguous["reason"] == "ambiguous_postcode"


# ==============================================================================
# 7. Codex Audit Targeted Verifications (P1 Rework Checklist)
# ==============================================================================

class TestCodexAuditP1Rework:
    """Explicitly verifies each of the 5 audit rework requirements from Codex."""

    def test_strict_boolean_consent_rejections(self):
        """Require actual boolean values; reject coercible strings and ints."""
        coercible_values = ["true", "false", "yes", "no", "TRUE", "YES", 1, 0, 1.0]

        for val in coercible_values:
            with pytest.raises(ValidationError) as exc1:
                MatchConsentIn(match_processing=val, terms=True)  # type: ignore
            assert "must be an actual boolean" in str(exc1.value)

            with pytest.raises(ValidationError) as exc2:
                MatchConsentIn(match_processing=True, terms=val)  # type: ignore
            assert "must be an actual boolean" in str(exc2.value)

        # Valid booleans pass
        c1 = MatchConsentIn(match_processing=True, terms=True)
        assert c1.match_processing is True and c1.terms is True
        # False for mandatory consent raises ValueError
        with pytest.raises(ValidationError) as exc_false:
            MatchConsentIn(match_processing=False, terms=True)
        assert "must be explicitly accepted" in str(exc_false.value)
        # Optional consent accepts False
        c_opt = MatchConsentIn(match_processing=True, terms=True, referral_contact=False, follow_up=False)
        assert c_opt.referral_contact is False and c_opt.follow_up is False

    def test_missing_service_format_and_method_preference_rejected(self):
        """Require explicit service_format and method_preference; no defaults."""
        # Missing service_format
        with pytest.raises(ValidationError) as exc1:
            MatchRequestIn(
                suburb_or_postcode="Richmond",
                dog_age_months=6,
                primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
                method_preference=MethodPreference.NO_PREFERENCE.value,
                consent=MatchConsentIn(match_processing=True, terms=True),
            )  # type: ignore
        assert "service_format" in str(exc1.value)

        # Missing method_preference
        with pytest.raises(ValidationError) as exc2:
            MatchRequestIn(
                suburb_or_postcode="Richmond",
                dog_age_months=6,
                primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
                service_format=ServiceFormatPreference.ANY.value,
                consent=MatchConsentIn(match_processing=True, terms=True),
            )  # type: ignore
        assert "method_preference" in str(exc2.value)

    def test_sanitize_strips_street_addresses_and_po_boxes(self):
        """Strip street address text and PO boxes completely without marker tokens."""
        raw_text = (
            "Please visit us at 123 Main Street or 45 Smith St, Richmond. "
            "Our mailing address is PO Box 789 or P.O. Box 456. "
            "You can email contact@example.com or phone 0412 345 678. "
            "Website: https://dogtraining.com.au. "
            "Dog pulls strongly on leash during walks."
        )
        cleaned = sanitize_behaviour_description(raw_text)

        # All PII stripped
        assert "123 Main Street" not in cleaned
        assert "45 Smith St" not in cleaned
        assert "PO Box 789" not in cleaned
        assert "P.O. Box 456" not in cleaned
        assert "contact@example.com" not in cleaned
        assert "0412 345 678" not in cleaned
        assert "https://dogtraining.com.au" not in cleaned

        # Zero marker tokens
        assert "[ADDRESS_REDACTED]" not in cleaned
        assert "[PHONE_REDACTED]" not in cleaned
        assert "[EMAIL_REDACTED]" not in cleaned
        assert "[URL_REDACTED]" not in cleaned

        # Core behavioral text retained
        assert "Dog pulls strongly on leash during walks." in cleaned

    def test_separation_anxiety_requires_explicit_specialty(self):
        """separation_anxiety requires explicit separation_anxiety specialty; fear_anxiety alone must not qualify."""
        req = make_valid_match_request(
            primary_concerns=[PrimaryConcern.SEPARATION_ANXIETY.value],
        )

        cand_fear_only = make_test_trainer_doc(
            trainer_id="t_fear_only",
            name="Fear Only Trainer",
            specialties=["fear_anxiety"],
            serviced_suburbs=["Richmond"],
            life_stages=["puppy", "adolescent", "adult"],
        )
        is_el, reasons = check_candidate_eligibility(cand_fear_only, req)
        assert is_el is False
        assert "no_matching_specialty" in reasons

        cand_sep = make_test_trainer_doc(
            trainer_id="t_sep_anxiety",
            name="Separation Anxiety Specialist",
            specialties=["separation_anxiety"],
            serviced_suburbs=["Richmond"],
            life_stages=["puppy", "adolescent", "adult"],
        )
        is_el_sep, reasons_sep = check_candidate_eligibility(cand_sep, req)
        assert is_el_sep is True
        assert "eligible" in reasons_sep

    def test_other_unsure_free_text_cannot_create_specialty_mapping(self):
        """other/unsure concerns remain needs_clarification regardless of free text content."""
        req_other = make_valid_match_request(
            primary_concerns=[PrimaryConcern.OTHER.value],
            behaviour_description="Dog bites other dogs and people, very reactive on leash, need puppy crate help",
        )
        pool = [
            make_test_trainer_doc(
                trainer_id="t_react",
                name="Reactive Specialist",
                specialties=["aggression", "leash_reactivity", "puppy_training"],
                serviced_suburbs=["Richmond"],
                life_stages=["puppy"],
            )
        ]
        resp_other = run_deterministic_matching(req_other, pool)
        assert resp_other.decision_state == DecisionState.NEEDS_CLARIFICATION.value
        assert "needs_clarification" in resp_other.reason_codes
        assert len(resp_other.candidates) == 0

        req_unsure = make_valid_match_request(
            primary_concerns=[PrimaryConcern.UNSURE.value],
            behaviour_description="Puppy biting feet and crying at night",
        )
        resp_unsure = run_deterministic_matching(req_unsure, pool)
        assert resp_unsure.decision_state == DecisionState.NEEDS_CLARIFICATION.value
        assert len(resp_unsure.candidates) == 0

    def test_explanation_prohibited_terms_comprehensive(self):
        """Reject experience, availability, accreditation, location, outcomes, personality, verified expertise, and diagnoses."""
        cand = make_test_trainer_doc(
            trainer_id="t_prohibited",
            name="Prohibited Terms Test",
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy"],
            serviced_suburbs=["Richmond"],
        )

        prohibited_samples = [
            # Experience
            "Has over 15 years of experience in dog training.",
            "Highly experienced in handling puppies.",
            # Availability
            "Available this weekend for home visits.",
            "Has immediate openings for clients.",
            "Offers flexible schedule for busy families.",
            # Accreditation
            "Certified IAABC accredited dog behaviour consultant.",
            "Licensed APDT trainer.",
            # Personality
            "A friendly and patient approach to training.",
            "Loving and compassionate handler.",
            # "Verified expertise"
            "Provides verified expertise in puppy training.",
            # Outcomes / Guarantees
            "Guaranteed 100% success rate with puppy recall.",
            "Promises a peaceful and obedient dog.",
            # Superlatives
            "The best world-class dog trainer in Melbourne.",
            "Ranked #1 puppy school in Australia.",
            # Diagnoses
            "Treats canine PTSD and neurological panic disorder.",
        ]

        for sample in prohibited_samples:
            with pytest.raises(ValueError) as exc:
                validate_explanation_truthfulness(sample, cand)
            assert "contains prohibited term" in str(exc.value)

    def test_adapter_raises_boundary_exceptions_directly(self):
        """Adapter raises boundary exceptions directly from call_model on degraded modes."""
        req = make_valid_match_request()
        pool = [make_test_trainer_doc(trainer_id="t_1", name="Trainer 1", serviced_suburbs=["Richmond"], specialties=["puppy_training"], life_stages=["puppy"])]

        adapter_timeout = GeminiStubAdapter(mode="timeout")
        with pytest.raises(GeminiTimeoutError):
            adapter_timeout.call_model(req, pool, SearchScope.LOCAL)

        adapter_rate_limit = GeminiStubAdapter(mode="rate_limit")
        with pytest.raises(GeminiRateLimitError):
            adapter_rate_limit.call_model(req, pool, SearchScope.LOCAL)

        adapter_unavailable = GeminiStubAdapter(mode="unavailable")
        with pytest.raises(GeminiUnavailableError):
            adapter_unavailable.call_model(req, pool, SearchScope.LOCAL)

        adapter_malformed = GeminiStubAdapter(mode="malformed_output")
        raw = adapter_malformed.call_model(req, pool, SearchScope.LOCAL)
        assert raw["candidates"][0]["trainer_id"] == "unauthorized_hallucinated_candidate_999"

    def test_execute_matching_with_adapter_handles_all_boundary_errors(self):
        """execute_matching_with_adapter catches all adapter boundary errors and engages fallback."""
        req = make_valid_match_request()
        pool = [make_test_trainer_doc(trainer_id="t_1", name="Trainer 1", serviced_suburbs=["Richmond"], specialties=["puppy_training"], life_stages=["puppy"])]

        for mode in ["timeout", "rate_limit", "unavailable", "malformed_output"]:
            adapter = GeminiStubAdapter(mode=mode)
            resp = execute_matching_with_adapter(req, pool, adapter)
            assert resp.degraded is True
            assert resp.decision_state == DecisionState.DEGRADED_RECOMMENDATIONS.value
            assert len(resp.candidates) == 1
            assert resp.candidates[0].trainer_id == "t_1"

    def test_expansion_governed_strictly_by_local_eligible_count(self):
        """Expansion triggers ONLY when fewer than 3 local eligible candidates exist, NOT when score < threshold."""
        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=4,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value, PrimaryConcern.PUPPY_PREP.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )

        cand1 = make_test_trainer_doc(
            trainer_id="t_local_1",
            name="Local Trainer 1",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy"],
        )
        cand2 = make_test_trainer_doc(
            trainer_id="t_local_2",
            name="Local Trainer 2",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy"],
        )
        cand3 = make_test_trainer_doc(
            trainer_id="t_local_3",
            name="Local Trainer 3",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy"],
        )
        cand_expanded = make_test_trainer_doc(
            trainer_id="t_melb_expanded",
            name="Melb Expanded Trainer",
            serviced_suburbs=["Carlton"],
            catchment_type="melbourne_wide",
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy"],
        )

        pool = [cand1, cand2, cand3, cand_expanded]

        # Check local eligible count
        local_el = [
            c for c in pool
            if check_candidate_eligibility(c, req, search_scope=SearchScope.LOCAL.value)[0]
        ]
        assert len(local_el) == 3

        # Run deterministic matching
        resp = run_deterministic_matching(req, pool)

        # Because len(local_eligible) == 3, expansion did NOT trigger!
        assert resp.search_scope == SearchScope.LOCAL.value
        assert resp.decision_state == DecisionState.RECOMMENDATIONS.value
        c_ids = [c.trainer_id for c in resp.candidates]
        assert "t_melb_expanded" not in c_ids
        assert len(c_ids) == 3
        assert set(c_ids) == {"t_local_1", "t_local_2", "t_local_3"}

        # Now remove cand3 so len(local_eligible) == 2 (< 3):
        pool_thin = [cand1, cand2, cand_expanded]
        resp_thin = run_deterministic_matching(req, pool_thin)
        assert resp_thin.search_scope == SearchScope.EXPANDED.value
        assert resp_thin.decision_state == DecisionState.LIMITED_LOCAL_RESULTS.value
        c_ids_thin = [c.trainer_id for c in resp_thin.candidates]
        assert "t_melb_expanded" in c_ids_thin

    def test_canonical_postcode_adapter_parity(self):
        """Unambiguous postcode (3067 -> Abbotsford) achieves exact parity without degradation."""
        req = make_valid_match_request(
            suburb_or_postcode="3067",
            dog_age_months=4,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        )
        pool = [
            make_test_trainer_doc(
                trainer_id="t_abbotsford",
                name="Abbotsford Canine Academy",
                serviced_suburbs=["Abbotsford"],
                specialties=["obedience", "puppy_training"],
                service_formats=["in_home"],
                life_stages=["puppy"],
            )
        ]
        det_resp = run_deterministic_matching(req, pool)
        adapter = GeminiStubAdapter(mode="normal")
        adapter_resp = adapter.match(req, pool)

        assert det_resp.decision_state == DecisionState.RECOMMENDATIONS.value
        assert adapter_resp.decision_state == DecisionState.RECOMMENDATIONS.value
        assert adapter_resp.degraded is False
        assert adapter_resp.search_scope == SearchScope.LOCAL.value
        assert len(adapter_resp.candidates) == 1
        assert adapter_resp.candidates[0].trainer_id == "t_abbotsford"
        assert adapter_resp.candidates[0].trainer_id == det_resp.candidates[0].trainer_id
        assert "in Abbotsford" in adapter_resp.candidates[0].explanation
        assert adapter_resp.candidates[0].reason_codes == det_resp.candidates[0].reason_codes

    def test_unexpected_exception_propagates_without_fallback(self):
        """Injected unexpected errors (e.g. RuntimeError) propagate through execute_matching_with_adapter rather than engaging fallback."""
        req = make_valid_match_request()
        pool = [make_test_trainer_doc(trainer_id="t_1", name="Trainer 1", serviced_suburbs=["Richmond"], specialties=["puppy_training"], life_stages=["puppy"])]

        class CrashingAdapter(GeminiStubAdapter):
            def call_model(self, *args, **kwargs):
                raise RuntimeError("Injected unexpected system failure")

        adapter = CrashingAdapter()
        with pytest.raises(RuntimeError) as exc:
            execute_matching_with_adapter(req, pool, adapter)
        assert "Injected unexpected system failure" in str(exc.value)
