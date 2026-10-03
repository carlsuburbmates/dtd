"""Contract v2 Fixtures and Standardized Test Scenarios.

Governed by:
- OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md (Section 9)
- AGENTS.md (Rule 6A, M0 acceptance criteria)
- Findings: DF-018, DF-019, DF-021, DF-022, DF-023

Contains:
1. Data builders producing valid build_match_ready_projection() trainer fixtures.
   - Distinguishes None (absent facts) from explicit empty lists [].
   - Uses canonical delivery fields: in_home_available, facility_available, travel_distance_km, notes.
2. Isolated candidate pools per scenario (no duplicate-like trainers).
3. The complete 16-scenario test matrix for Contract v2 Section 9.
"""

from __future__ import annotations

import sys
from pathlib import Path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from services.matching_contract_v2 import (
        DECISION_CONTRACT_VERSION,
        DecisionResponseV2,
        DecisionState,
        DogAgeCategory,
        MatchConsentIn,
        MatchRequestIn,
        MethodPreference,
        PrimaryConcern,
        ReasonCode,
        SearchScope,
        ServiceFormatPreference,
        run_deterministic_matching,
    )
    from services.trainer_quality import (
        build_match_ready_projection,
        create_capability_fact,
        now_iso,
        package_trainer_capabilities,
    )
except ImportError:
    from backend.services.matching_contract_v2 import (
        DECISION_CONTRACT_VERSION,
        DecisionResponseV2,
        DecisionState,
        DogAgeCategory,
        MatchConsentIn,
        MatchRequestIn,
        MethodPreference,
        PrimaryConcern,
        ReasonCode,
        SearchScope,
        ServiceFormatPreference,
        run_deterministic_matching,
    )
    from backend.services.trainer_quality import (
        build_match_ready_projection,
        create_capability_fact,
        now_iso,
        package_trainer_capabilities,
    )


# ==============================================================================
# 1. Standard Test Data Builders
# ==============================================================================

def make_test_trainer_doc(
    *,
    trainer_id: str,
    name: str,
    suburb: str = "Richmond",
    region: str = "Greater Melbourne",
    specialties: Optional[List[str]] = None,
    service_formats: Optional[List[str]] = None,
    life_stages: Optional[List[str]] = None,
    training_philosophy: Optional[str] = None,
    serviced_suburbs: Optional[List[str]] = None,
    catchment_type: Optional[str] = "specific_suburbs",
    delivery_constraints: Optional[Dict[str, Any]] = None,
    published: bool = True,
    contact_ready: bool = True,
    claim_status: str = "claimed",
    tier: str = "claimed",
    days_ago: int = 5,
    empty_capabilities: bool = False,
) -> Dict[str, Any]:
    """Build a raw trainer document with full provenance and run build_match_ready_projection.

    Distinguishes None (absent facts) from explicit empty lists [] for rigorous fail-closed testing.
    Uses only canonical delivery fields: in_home_available, facility_available, travel_distance_km, notes.
    """
    confirmed_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    confirmed_ts = confirmed_dt.isoformat()

    if empty_capabilities:
        caps = {}
    else:
        # Canonical delivery constraint defaults if not explicitly provided
        deliv = delivery_constraints
        if deliv is None:
            deliv = {
                "in_home_available": True,
                "facility_available": False,
                "travel_distance_km": 20,
                "notes": "Standard travel radius",
            }

        caps = package_trainer_capabilities(
            specialties=specialties,
            service_formats=service_formats,
            life_stages=life_stages,
            training_philosophy=training_philosophy,
            serviced_suburbs=serviced_suburbs,
            catchment_type=catchment_type,
            delivery_constraints=deliv,
            basis="trainer_declaration",
            confirmed_at=confirmed_ts,
        )

    doc = {
        "id": trainer_id,
        "name": name,
        "suburb": suburb,
        "region": region,
        "published": published,
        "contact_ready": contact_ready,
        "claim_status": claim_status,
        "tier": tier,
        "capabilities": caps,
        "source_url": f"https://example.com/trainers/{trainer_id}",
        "source_evidence_url": f"https://example.com/trainers/{trainer_id}",
    }

    projection = build_match_ready_projection(doc)
    projection["tier"] = tier
    if life_stages is None:
        projection["life_stages"] = None
    if specialties is None and "specialties" not in caps:
        projection["specialties"] = None
    if service_formats is None and "service_formats" not in caps:
        projection["service_formats"] = None
    if serviced_suburbs is None and "serviced_suburbs" not in caps:
        projection["serviced_suburbs"] = None
    return projection


def make_valid_match_request(
    *,
    suburb_or_postcode: str = "Richmond",
    dog_age_months: int = 4,
    primary_concerns: Optional[List[str]] = None,
    service_format: str = ServiceFormatPreference.ANY.value,
    method_preference: str = MethodPreference.NO_PREFERENCE.value,
    behaviour_description: str = "Puppy needs basic manners and recall",
    consent_processing: bool = True,
    consent_terms: bool = True,
) -> MatchRequestIn:
    """Helper to instantiate a valid MatchRequestIn."""
    return MatchRequestIn(
        suburb_or_postcode=suburb_or_postcode,
        dog_age_months=dog_age_months,
        primary_concerns=primary_concerns or [PrimaryConcern.BASIC_MANNERS.value, PrimaryConcern.PUPPY_PREP.value],
        service_format=service_format,
        method_preference=method_preference,
        behaviour_description=behaviour_description,
        consent=MatchConsentIn(
            match_processing=consent_processing,
            terms=consent_terms,
        ),
    )


# ==============================================================================
# 2. Section 9 Scenarios with Isolated Candidate Pools
# ==============================================================================

class ScenarioDefinition:
    """Structured representation of an acceptance scenario."""
    def __init__(
        self,
        scenario_id: str,
        title: str,
        request: MatchRequestIn,
        candidate_pool: List[Dict[str, Any]],
        expected_decision_state: str,
        expected_search_scope: str,
        expected_eligible_ids: List[str],
        expected_reason_codes: List[str],
        parity_assertion: str,
        triage_state: Optional[DecisionState] = None,
    ):
        self.scenario_id = scenario_id
        self.title = title
        self.request = request
        self.candidate_pool = candidate_pool
        self.expected_decision_state = expected_decision_state
        self.expected_search_scope = expected_search_scope
        self.expected_eligible_ids = expected_eligible_ids
        self.expected_reason_codes = expected_reason_codes
        self.parity_assertion = parity_assertion
        self.triage_state = triage_state


def get_all_section_9_scenarios() -> Dict[str, ScenarioDefinition]:
    """Build and return all 16 Section 9 test scenarios with isolated candidate pools."""
    scenarios: Dict[str, ScenarioDefinition] = {}

    # --------------------------------------------------------------------------
    # Scenario 1: Local Puppy Manners (Isolated pool: 3 Richmond puppy trainers)
    # --------------------------------------------------------------------------
    pool_01 = [
        make_test_trainer_doc(
            trainer_id="t_richmond_alpha",
            name="Richmond Puppy Academy",
            suburb="Richmond",
            serviced_suburbs=["Richmond", "Burnley"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home", "group_classes"],
            life_stages=["puppy", "adolescent"],
            training_philosophy="positive_reinforcement_force_free",
            tier="pro",
        ),
        make_test_trainer_doc(
            trainer_id="t_richmond_beta",
            name="Yarra Valley Canine School",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy"],
            training_philosophy="positive_reinforcement_force_free",
            tier="claimed",
        ),
        make_test_trainer_doc(
            trainer_id="t_richmond_gamma",
            name="Melbourne City Manners",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent"],
            training_philosophy="positive_reinforcement_force_free",
            tier="unclaimed",
        ),
    ]

    scenarios["scenario_01_local_puppy_manners"] = ScenarioDefinition(
        scenario_id="scenario_01_local_puppy_manners",
        title="1. Local Puppy Manners",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=4,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value, PrimaryConcern.PUPPY_PREP.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
            method_preference=MethodPreference.POSITIVE_REINFORCEMENT_ONLY.value,
        ),
        candidate_pool=pool_01,
        expected_decision_state=DecisionState.RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_richmond_alpha", "t_richmond_beta", "t_richmond_gamma"],
        expected_reason_codes=[
            ReasonCode.CAPABILITY_CONCERN_MATCH.value,
            ReasonCode.LIFE_STAGE_MATCH.value,
            ReasonCode.FORMAT_MATCH.value,
            ReasonCode.METHOD_PREFERENCE_MATCH.value,
            ReasonCode.SERVICE_AREA_MATCH.value,
        ],
        parity_assertion="Local puppy request produces recommendations state with exact local candidates",
    )

    # --------------------------------------------------------------------------
    # Scenario 2: Multi-concern In-Home & Method Boundary (Isolated pool: 3 Brunswick trainers)
    # --------------------------------------------------------------------------
    pool_02 = [
        # Candidate A: In-home positive specialist -> ELIGIBLE
        make_test_trainer_doc(
            trainer_id="t_brunswick_eligible",
            name="Brunswick Dog Behaviour",
            suburb="Brunswick",
            serviced_suburbs=["Brunswick", "Coburg"],
            specialties=["leash_reactivity", "behaviour_modification"],
            service_formats=["in_home"],
            life_stages=["adolescent", "adult"],
            training_philosophy="positive_reinforcement_force_free",
            tier="pro",
        ),
        # Candidate B: Facility only -> EXCLUDED by format
        make_test_trainer_doc(
            trainer_id="t_brunswick_facility_only",
            name="Brunswick Facility School",
            suburb="Brunswick",
            serviced_suburbs=["Brunswick"],
            specialties=["leash_reactivity"],
            service_formats=["facility"],
            life_stages=["adolescent", "adult"],
            training_philosophy="positive_reinforcement_force_free",
            tier="claimed",
        ),
        # Candidate C: Balanced -> EXCLUDED by method preference
        make_test_trainer_doc(
            trainer_id="t_brunswick_balanced",
            name="Brunswick Balanced K9",
            suburb="Brunswick",
            serviced_suburbs=["Brunswick"],
            specialties=["leash_reactivity"],
            service_formats=["in_home"],
            life_stages=["adolescent", "adult"],
            training_philosophy="balanced",
            tier="unclaimed",
        ),
    ]

    scenarios["scenario_02_multi_concern_in_home"] = ScenarioDefinition(
        scenario_id="scenario_02_multi_concern_in_home",
        title="2. Multi-concern In-Home & Method Boundary",
        request=make_valid_match_request(
            suburb_or_postcode="Brunswick",
            dog_age_months=14,
            primary_concerns=[PrimaryConcern.PULLING_LEASH.value, PrimaryConcern.REACTIVITY.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
            method_preference=MethodPreference.POSITIVE_REINFORCEMENT_ONLY.value,
        ),
        candidate_pool=pool_02,
        expected_decision_state=DecisionState.RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_brunswick_eligible"],
        expected_reason_codes=[
            ReasonCode.CAPABILITY_CONCERN_MATCH.value,
            ReasonCode.LIFE_STAGE_MATCH.value,
            ReasonCode.FORMAT_MATCH.value,
            ReasonCode.METHOD_PREFERENCE_MATCH.value,
            ReasonCode.SERVICE_AREA_MATCH.value,
        ],
        parity_assertion="In-home and positive boundaries filter out non-compliant trainers",
    )

    # --------------------------------------------------------------------------
    # Scenario 3: Ambiguous Input (Isolated pool)
    # --------------------------------------------------------------------------
    scenarios["scenario_03_ambiguous_input"] = ScenarioDefinition(
        scenario_id="scenario_03_ambiguous_input",
        title="3. Ambiguous Input",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=12,
            primary_concerns=[PrimaryConcern.OTHER.value],
            behaviour_description="",  # Missing required description for 'other'
        ),
        candidate_pool=[pool_01[0]],
        expected_decision_state=DecisionState.NEEDS_CLARIFICATION.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=[],
        expected_reason_codes=["needs_clarification"],
        parity_assertion="Returns needs_clarification state without attempting candidate scoring",
    )

    # --------------------------------------------------------------------------
    # Scenario 4: Thin Local Supply / Disclosed Expanded Result (Isolated pool: 1 local, 2 expanded)
    # --------------------------------------------------------------------------
    pool_04 = [
        # 1 local Footscray trainer
        make_test_trainer_doc(
            trainer_id="t_footscray_local",
            name="Footscray Puppy Coaching",
            suburb="Footscray",
            serviced_suburbs=["Footscray"],
            specialties=["puppy_training"],
            service_formats=["in_home"],
            life_stages=["puppy"],
            training_philosophy="positive_reinforcement_force_free",
            tier="claimed",
        ),
        # 2 Melbourne-wide expanded trainers
        make_test_trainer_doc(
            trainer_id="t_melb_wide_1",
            name="Greater Melbourne Puppy Coaches",
            suburb="Carlton",
            serviced_suburbs=["Carlton"],
            catchment_type="melbourne_wide",
            specialties=["puppy_training"],
            service_formats=["in_home"],
            life_stages=["puppy"],
            training_philosophy="positive_reinforcement_force_free",
            tier="pro",
        ),
        make_test_trainer_doc(
            trainer_id="t_melb_wide_2",
            name="Victoria Canine Education",
            suburb="Hawthorn",
            serviced_suburbs=["Hawthorn"],
            catchment_type="melbourne_wide",
            specialties=["puppy_training"],
            service_formats=["in_home"],
            life_stages=["puppy"],
            training_philosophy="positive_reinforcement_force_free",
            tier="unclaimed",
        ),
    ]

    scenarios["scenario_04_thin_local_expanded_result"] = ScenarioDefinition(
        scenario_id="scenario_04_thin_local_expanded_result",
        title="4. Thin Local Supply / Expanded Result",
        request=make_valid_match_request(
            suburb_or_postcode="Footscray",
            dog_age_months=5,
            primary_concerns=[PrimaryConcern.PUPPY_PREP.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        ),
        candidate_pool=pool_04,
        expected_decision_state=DecisionState.LIMITED_LOCAL_RESULTS.value,
        expected_search_scope=SearchScope.EXPANDED.value,
        expected_eligible_ids=["t_melb_wide_1", "t_footscray_local", "t_melb_wide_2"],
        expected_reason_codes=[
            ReasonCode.CAPABILITY_CONCERN_MATCH.value,
            ReasonCode.EXPANDED_SERVICE_AREA.value,
        ],
        parity_assertion="Discloses expanded search scope and returns limited_local_results state",
    )

    # --------------------------------------------------------------------------
    # Scenario 5: No Current Capability Evidence (Isolated pool)
    # --------------------------------------------------------------------------
    pool_05 = [
        make_test_trainer_doc(
            trainer_id="t_obedience_only",
            name="Strict Obedience Academy",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["facility"],
            life_stages=["adult"],
        )
    ]

    scenarios["scenario_05_no_current_capability_evidence"] = ScenarioDefinition(
        scenario_id="scenario_05_no_current_capability_evidence",
        title="5. No Current Capability Evidence",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=48,
            primary_concerns=[PrimaryConcern.SEPARATION_ANXIETY.value],
            service_format=ServiceFormatPreference.ONLINE_COACHING.value,
        ),
        candidate_pool=pool_05,
        expected_decision_state=DecisionState.NO_CONFIRMED_MATCH.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=[],
        expected_reason_codes=["no_qualified_candidates"],
        parity_assertion="Fails closed and returns no_confirmed_match rather than manufacturing false match",
    )

    # --------------------------------------------------------------------------
    # Scenario 6: Stale / Suppressed Projection (Isolated pool)
    # --------------------------------------------------------------------------
    pool_06 = [
        make_test_trainer_doc(
            trainer_id="t_unpublished",
            name="Unpublished Trainer",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            published=False,
            specialties=["puppy_training"],
        ),
        make_test_trainer_doc(
            trainer_id="t_stale",
            name="Stale Capabilities Trainer",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            days_ago=400,
            specialties=["puppy_training"],
        ),
    ]

    scenarios["scenario_06_stale_suppressed_projection"] = ScenarioDefinition(
        scenario_id="scenario_06_stale_suppressed_projection",
        title="6. Stale / Suppressed Projection",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=4,
            primary_concerns=[PrimaryConcern.PUPPY_PREP.value],
        ),
        candidate_pool=pool_06,
        expected_decision_state=DecisionState.NO_CONFIRMED_MATCH.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=[],
        expected_reason_codes=["no_qualified_candidates"],
        parity_assertion="Unpublished and stale projection records fail closed before scoring",
    )

    # --------------------------------------------------------------------------
    # Scenario 7: Exact 0.05 Band Commercial Tiebreak (Isolated pool: Claimed vs Pro)
    # --------------------------------------------------------------------------
    pool_07 = [
        make_test_trainer_doc(
            trainer_id="t_band_claimed",
            name="Richmond Dog Manners",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["in_home", "facility"],
            life_stages=["puppy", "adolescent"],
            tier="claimed",
        ),
        make_test_trainer_doc(
            trainer_id="t_band_pro",
            name="Richmond Canine Pro",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["in_home", "facility"],
            life_stages=["puppy", "adolescent"],
            tier="pro",
        ),
    ]

    scenarios["scenario_07_exact_005_band"] = ScenarioDefinition(
        scenario_id="scenario_07_exact_005_band",
        title="7. Exact 0.05 Band Commercial Tiebreak",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=4,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
        ),
        candidate_pool=pool_07,
        expected_decision_state=DecisionState.RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_band_pro", "t_band_claimed"],
        expected_reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH.value],
        parity_assertion="Within 0.05 band, Pro tier (weight 2) sorts ahead of Claimed tier (weight 1)",
    )

    # --------------------------------------------------------------------------
    # Scenario 8: Outside-Band Paid Candidate (Isolated pool: High fit Unclaimed vs Low fit Citywide)
    # --------------------------------------------------------------------------
    pool_08 = [
        # Candidate A: Unclaimed, high fit (puppy_training + obedience -> 1.0 fit)
        make_test_trainer_doc(
            trainer_id="t_high_fit_unclaimed",
            name="High Fit Unclaimed Trainer",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy"],
            tier="unclaimed",
        ),
        # Candidate C: Citywide sponsor, lower fit (obedience only -> 0.80 fit, diff = 0.20 > 0.05)
        make_test_trainer_doc(
            trainer_id="t_lower_fit_citywide",
            name="Lower Fit Citywide Trainer",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["in_home"],
            life_stages=["puppy"],
            tier="citywide",
        ),
    ]

    scenarios["scenario_08_outside_band_paid_candidate"] = ScenarioDefinition(
        scenario_id="scenario_08_outside_band_paid_candidate",
        title="8. Outside-Band Paid Candidate",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=4,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value, PrimaryConcern.PUPPY_PREP.value],
            service_format=ServiceFormatPreference.IN_HOME.value,
        ),
        candidate_pool=pool_08,
        expected_decision_state=DecisionState.RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_high_fit_unclaimed", "t_lower_fit_citywide"],
        expected_reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH.value],
        parity_assertion="Higher fit candidate ranks strictly first; Citywide sponsor outside 0.05 cannot overtake",
    )

    # --------------------------------------------------------------------------
    # Scenario 9: Gemini Degradation Routes
    # --------------------------------------------------------------------------
    scenarios["scenario_09_gemini_degradation_routes"] = ScenarioDefinition(
        scenario_id="scenario_09_gemini_degradation_routes",
        title="9. Gemini Degradation Routes",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=4,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
        ),
        candidate_pool=[pool_01[0]],
        expected_decision_state=DecisionState.DEGRADED_RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_richmond_alpha"],
        expected_reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH.value],
        parity_assertion="Fallback invokes seamlessly on model degradation and outputs degraded_recommendations",
    )

    # --------------------------------------------------------------------------
    # Scenario 10: Immediate Human Danger
    # --------------------------------------------------------------------------
    scenarios["scenario_10_immediate_human_danger"] = ScenarioDefinition(
        scenario_id="scenario_10_immediate_human_danger",
        title="10. Immediate Human Danger",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=24,
            primary_concerns=[PrimaryConcern.AGGRESSION.value],
            behaviour_description="Dog is attacking neighbor right now, bit child, blood everywhere, need police ambulance",
        ),
        candidate_pool=pool_01,
        expected_decision_state=DecisionState.IMMEDIATE_HUMAN_DANGER.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=[],
        expected_reason_codes=["immediate_human_danger"],
        parity_assertion="Matching halts immediately; returns 0 candidate cards and Triple Zero guidance",
        triage_state=DecisionState.IMMEDIATE_HUMAN_DANGER,
    )

    # --------------------------------------------------------------------------
    # Scenario 11: Urgent Animal Health Support
    # --------------------------------------------------------------------------
    scenarios["scenario_11_urgent_animal_health_support"] = ScenarioDefinition(
        scenario_id="scenario_11_urgent_animal_health_support",
        title="11. Urgent Animal Health Support",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=18,
            primary_concerns=[PrimaryConcern.OTHER.value],
            behaviour_description="Dog ate rat poison 30 minutes ago, collapsed and having seizures",
        ),
        candidate_pool=pool_01,
        expected_decision_state=DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=[],
        expected_reason_codes=["urgent_animal_health_support"],
        parity_assertion="Matching halts immediately; displays urgent veterinary guidance",
        triage_state=DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT,
    )

    # --------------------------------------------------------------------------
    # Scenario 12: Serious Behavioural Support (Isolated pool: 1 general, 1 clinical aggression)
    # --------------------------------------------------------------------------
    pool_12 = [
        make_test_trainer_doc(
            trainer_id="t_general_obedience",
            name="General Obedience Trainer",
            suburb="Hawthorn",
            serviced_suburbs=["Hawthorn"],
            specialties=["obedience"],
            service_formats=["in_home"],
            life_stages=["adult"],
        ),
        make_test_trainer_doc(
            trainer_id="t_clinical_aggression",
            name="Clinical Canine Behaviourists",
            suburb="Hawthorn",
            serviced_suburbs=["Hawthorn"],
            specialties=["aggression", "behaviour_modification"],
            service_formats=["in_home"],
            life_stages=["adult"],
            tier="citywide",
        ),
    ]

    scenarios["scenario_12_serious_behavioural_support"] = ScenarioDefinition(
        scenario_id="scenario_12_serious_behavioural_support",
        title="12. Serious Behavioural Support",
        request=make_valid_match_request(
            suburb_or_postcode="Hawthorn",
            dog_age_months=36,
            primary_concerns=[PrimaryConcern.AGGRESSION.value],
            behaviour_description="Severe aggression towards strangers, bite history, growling at family",
        ),
        candidate_pool=pool_12,
        expected_decision_state=DecisionState.RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_clinical_aggression"],
        expected_reason_codes=[
            ReasonCode.CAPABILITY_CONCERN_MATCH.value,
            ReasonCode.SERIOUS_BEHAVIOURAL_SUPPORT.value,
        ],
        parity_assertion="Candidate pool restricted exclusively to clinical aggression specialists",
    )

    # --------------------------------------------------------------------------
    # Scenario 13: Trainer Declaration Gaming (Isolated pool)
    # --------------------------------------------------------------------------
    pool_13 = [
        make_test_trainer_doc(
            trainer_id="t_gaming_candidate",
            name="Gamer Dog Training",
            suburb="Richmond",
            serviced_suburbs=["Richmond"],
            specialties=["unverified_claim_100%_guaranteed"],
            empty_capabilities=True,
        )
    ]

    scenarios["scenario_13_trainer_declaration_gaming"] = ScenarioDefinition(
        scenario_id="scenario_13_trainer_declaration_gaming",
        title="13. Trainer Declaration Gaming",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=6,
            primary_concerns=[PrimaryConcern.PUPPY_PREP.value],
        ),
        candidate_pool=pool_13,
        expected_decision_state=DecisionState.NO_CONFIRMED_MATCH.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=[],
        expected_reason_codes=["no_qualified_candidates"],
        parity_assertion="Out-of-vocabulary and unvalidated declarations fail closed and do not match",
    )

    # --------------------------------------------------------------------------
    # Scenario 14: Privacy & URL Leakage Protection (Isolated pool)
    # --------------------------------------------------------------------------
    scenarios["scenario_14_privacy_url_leakage"] = ScenarioDefinition(
        scenario_id="scenario_14_privacy_url_leakage",
        title="14. Privacy & URL Leakage Protection",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=8,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            behaviour_description="Call me at 0412345678 or john.doe@example.com, my site is https://test.com, come to 45 Smith St, Richmond VIC 3121 or PO Box 123",
        ),
        candidate_pool=[pool_01[0]],
        expected_decision_state=DecisionState.RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_richmond_alpha"],
        expected_reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH.value],
        parity_assertion="Sanitizer strips email, phone, and URLs from description without retaining marker tokens",
    )

    # --------------------------------------------------------------------------
    # Scenario 15: Follow-Up Retry Lifecycle (Isolated pool)
    # --------------------------------------------------------------------------
    scenarios["scenario_15_follow_up_retry"] = ScenarioDefinition(
        scenario_id="scenario_15_follow_up_retry",
        title="15. Follow-Up Retry Lifecycle",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=6,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
        ),
        candidate_pool=[pool_01[0]],
        expected_decision_state=DecisionState.RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_richmond_alpha"],
        expected_reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH.value],
        parity_assertion="Follow-up states define explicit pending, retryable_failure, delivered, and suppressed states",
    )

    # --------------------------------------------------------------------------
    # Scenario 16: Ops Redaction & Aggregation (Isolated pool)
    # --------------------------------------------------------------------------
    scenarios["scenario_16_ops_redaction"] = ScenarioDefinition(
        scenario_id="scenario_16_ops_redaction",
        title="16. Ops Redaction & Aggregation",
        request=make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=6,
            primary_concerns=[PrimaryConcern.BASIC_MANNERS.value],
            behaviour_description="Private owner details for matching",
        ),
        candidate_pool=[pool_01[0]],
        expected_decision_state=DecisionState.RECOMMENDATIONS.value,
        expected_search_scope=SearchScope.LOCAL.value,
        expected_eligible_ids=["t_richmond_alpha"],
        expected_reason_codes=[ReasonCode.CAPABILITY_CONCERN_MATCH.value],
        parity_assertion="Operational telemetry logs aggregate reason codes and token hashes with zero raw owner text",
    )

    return scenarios
