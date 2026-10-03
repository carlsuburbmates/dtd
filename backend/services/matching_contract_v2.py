"""Owner-to-Trainer Matching Decision Contract v2 Implementation.

Governed by:
- AGENTS.md (Rule 6A, locked invariants)
- OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md
- DTD_INVARIANTS_AND_CONSTRAINTS.md (Invariants 5, 6, 7, 10, 14)
- Findings: DF-018, DF-019, DF-021, DF-022, DF-023

Scope Note (P1):
This module defines the reference contract models, deterministic eligibility gates,
and test-only parity adapters. Scoring weights here serve as the test reference engine;
production scoring formula and real ai.py integration are scheduled for P3.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

try:
    from services.suburb_catalogue import canonical_suburb_names, load_catalogue
except ImportError:
    from backend.services.suburb_catalogue import canonical_suburb_names, load_catalogue


# ==============================================================================
# 1. Versioned Policy Configuration & Constants
# ==============================================================================

DECISION_CONTRACT_VERSION: str = "v2"

# Fit scoring thresholds
QUALIFICATION_THRESHOLD: float = 0.60  # Initial qualification threshold (replaces legacy 0.40)
COMPARABLE_FIT_BAND: float = 0.05     # Exact 0.05 commercial tiebreak band
OUTCOME_SCORE_WEIGHT: float = 0.0     # Strictly 0.0 until accepted attribution policy exists

# Candidate pool bounds
MAX_ELIGIBLE_CANDIDATES: int = 15     # Maximum eligible candidates sent to AI model
MAX_RECOMMENDED_CANDIDATES: int = 3   # Maximum candidate cards returned to owner

# Operational & Protection bounds
GEMINI_TIMEOUT_S: float = 5.0         # Hard timeout for AI provider calls
MATCH_ATTEMPT_RATE_LIMIT: int = 10     # Max requests per window
MATCH_RATE_LIMIT_WINDOW_S: int = 600   # 10 minutes (600s)
MATCH_RATE_LIMIT_BURST_INTERVAL_S: int = 30  # 30s burst interval
RETENTION_PERIOD_DAYS: int = 30       # Data retention TTL for detailed records
MAX_DESCRIPTION_CHARS: int = 800      # Bounded owner behaviour description limit


# ==============================================================================
# 2. Canonical Enums & Controlled Vocabularies
# ==============================================================================

class DecisionState(str, Enum):
    """Authoritative decision states defined in Contract v2 Section 3."""
    IMMEDIATE_HUMAN_DANGER = "immediate_human_danger"
    URGENT_ANIMAL_HEALTH_SUPPORT = "urgent_animal_health_support"
    SERIOUS_BEHAVIOURAL_SUPPORT = "serious_behavioural_support"
    NEEDS_CLARIFICATION = "needs_clarification"
    RECOMMENDATIONS = "recommendations"
    LIMITED_LOCAL_RESULTS = "limited_local_results"
    NO_CONFIRMED_MATCH = "no_confirmed_match"
    DEGRADED_RECOMMENDATIONS = "degraded_recommendations"
    DEGRADED_NO_CONFIRMED_MATCH = "degraded_no_confirmed_match"


class SearchScope(str, Enum):
    """Declared catchment search scope."""
    LOCAL = "local"
    EXPANDED = "expanded"


class ReasonCode(str, Enum):
    """Permitted candidate card reason codes (Contract v2 Section 5)."""
    CAPABILITY_CONCERN_MATCH = "capability_concern_match"
    LIFE_STAGE_MATCH = "life_stage_match"
    FORMAT_MATCH = "format_match"
    METHOD_PREFERENCE_MATCH = "method_preference_match"
    SERVICE_AREA_MATCH = "service_area_match"
    EXPANDED_SERVICE_AREA = "expanded_service_area"
    SERIOUS_BEHAVIOURAL_SUPPORT = "serious_behavioural_support"


# Allowed top-level response reason codes
ALLOWED_TOP_LEVEL_REASON_CODES: Set[str] = {
    ReasonCode.CAPABILITY_CONCERN_MATCH.value,
    ReasonCode.LIFE_STAGE_MATCH.value,
    ReasonCode.FORMAT_MATCH.value,
    ReasonCode.METHOD_PREFERENCE_MATCH.value,
    ReasonCode.SERVICE_AREA_MATCH.value,
    ReasonCode.EXPANDED_SERVICE_AREA.value,
    ReasonCode.SERIOUS_BEHAVIOURAL_SUPPORT.value,
    "immediate_human_danger",
    "urgent_animal_health_support",
    "needs_clarification",
    "no_qualified_candidates",
    "thin_local_supply",
    "ambiguous_postcode",
    "invalid_locality",
    "unknown_locality",
}


class PrimaryConcern(str, Enum):
    """Canonical owner concerns (Contract v2 Section 2)."""
    BASIC_MANNERS = "basic_manners"
    PULLING_LEASH = "pulling_leash"
    REACTIVITY = "reactivity"
    AGGRESSION = "aggression"
    SEPARATION_ANXIETY = "separation_anxiety"
    BARKING = "barking"
    RECALL = "recall"
    SOCIALISATION = "socialisation"
    PUPPY_PREP = "puppy_prep"
    OTHER = "other"
    UNSURE = "unsure"


class ServiceFormatPreference(str, Enum):
    """Service format preferences (Contract v2 Section 2)."""
    IN_HOME = "in_home"
    FACILITY_OR_FIELD = "facility_or_field"
    GROUP_CLASS = "group_class"
    ONLINE_COACHING = "online_coaching"
    ANY = "any"


class MethodPreference(str, Enum):
    """Method compatibility choices (Contract v2 Section 2)."""
    POSITIVE_REINFORCEMENT_ONLY = "positive_reinforcement_only"
    BALANCED = "balanced"
    NO_PREFERENCE = "no_preference"


class DogAgeCategory(str, Enum):
    """Derived dog age categories (Contract v2 Section 2)."""
    PUPPY = "puppy"            # < 6 months (0..5)
    ADOLESCENT = "adolescent"  # 6..18 months
    ADULT = "adult"            # 19..83 months
    SENIOR = "senior"          # 84+ months


# Mapping from primary owner concerns to canonical trainer specialty IDs in trainer_quality.py.
# Note:
# - separation_anxiety strictly requires separation_anxiety (fear_anxiety alone does not qualify).
# - other and unsure map to empty sets; they require clarification until canonical concern is selected.
CONCERN_TO_SPECIALTIES_MAP: Dict[str, Set[str]] = {
    PrimaryConcern.BASIC_MANNERS.value: {"obedience"},
    PrimaryConcern.PULLING_LEASH.value: {"leash_reactivity", "obedience"},
    PrimaryConcern.REACTIVITY.value: {"leash_reactivity", "behaviour_modification"},
    PrimaryConcern.AGGRESSION.value: {"aggression", "behaviour_modification"},
    PrimaryConcern.SEPARATION_ANXIETY.value: {"separation_anxiety"},
    PrimaryConcern.BARKING.value: {"barking", "behaviour_modification"},
    PrimaryConcern.RECALL.value: {"recall", "obedience"},
    PrimaryConcern.SOCIALISATION.value: {"puppy_training", "obedience"},
    PrimaryConcern.PUPPY_PREP.value: {"puppy_training"},
    PrimaryConcern.OTHER.value: set(),
    PrimaryConcern.UNSURE.value: set(),
}

# Commercial tier priority weights for the comparable-fit band (Contract v2 Section 6)
COMMERCIAL_TIER_PRIORITY: Dict[str, int] = {
    "citywide": 4,
    "suburb_sponsor": 3,
    "pro": 2,
    "claimed": 1,
    "unclaimed": 0,
}

# Delivery constraint keys (canonical per P0 R2)
CANONICAL_DELIVERY_KEYS: Set[str] = {
    "in_home_available",
    "facility_available",
    "travel_distance_km",
    "notes",
}


# ==============================================================================
# 3. Privacy, Address Stripping & Sanitization Helpers
# ==============================================================================

_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_REGEX = re.compile(r"(\+?61|0)[2-478](?:[ -]?[0-9]){8}")
_URL_REGEX = re.compile(r"https?://\S+|www\.\S+")

_STREET_TYPE_PATTERN = (
    r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Court|Ct|Place|Pl|"
    r"Boulevard|Blvd|Way|Parade|Pde|Terrace|Tce|Crescent|Cres|Highway|Hwy|Close|Cl|Grove|Grv)"
)
_ADDRESS_REGEX = re.compile(
    rf"\b(?:(?:Unit|Suite|Apt|Apartment|Flat|Level|Lot|PO Box|P\.O\. Box)\s+[\w/-]+,?\s*)?"
    rf"\b\d+[\w/-]*\s+[A-Za-z0-9\s\'-]+?\s+{_STREET_TYPE_PATTERN}\b\.?",
    re.IGNORECASE,
)
_PO_BOX_REGEX = re.compile(r"\b(?:PO Box|P\.O\. Box|GPO Box)\s+\d+\b", re.IGNORECASE)

# Prohibited explanation patterns (superlatives, guarantees, clinical diagnoses, experience, availability, accreditation, personality)
PROHIBITED_EXPLANATION_PATTERNS = [
    # Guarantees & outcomes
    re.compile(r"(?:\b(guarantee|guaranteed|guarantees|promise|promised|promises|fail-safe|perfect outcome|cure|cured|cures|fix|fixed|transform|transforms|transformative)\b|100%)", re.IGNORECASE),
    # Superlatives
    re.compile(r"(?:\b(best|number one|greatest|unmatched|premier|world-class|unrivaled|top-rated)\b|#1)", re.IGNORECASE),
    # Diagnoses
    re.compile(r"\b(diagnose|diagnosed|diagnosis|pathology|psychiatric|disorder)\b", re.IGNORECASE),
    # Experience claims
    re.compile(r"\b(years of experience|decades of experience|experienced|veteran|seasoned|decades)\b", re.IGNORECASE),
    # Availability claims
    re.compile(r"\b(available|availability|openings|schedule|same-day|booking now|open slots|immediate booking)\b", re.IGNORECASE),
    # Accreditation / Credentials claims
    re.compile(r"\b(certified|accredited|licensed|degree|diploma|board-certified|credentialed|master trainer)\b", re.IGNORECASE),
    # Personality claims
    re.compile(r"\b(friendly|compassionate|patient|caring|gentle|passionate|loving|kind-hearted)\b", re.IGNORECASE),
    # Prohibited phrasing
    re.compile(r"\bverified expertise\b", re.IGNORECASE),
]


def sanitize_behaviour_description(text: Optional[str]) -> str:
    """Sanitize behaviour description before model or storage use (DF-015, DF-022).

    Removes email addresses, phone numbers, URLs, and address-like text entirely (no marker tokens).
    Truncates to MAX_DESCRIPTION_CHARS.
    """
    if not text:
        return ""
    clean = str(text)
    clean = _URL_REGEX.sub("", clean)
    clean = _EMAIL_REGEX.sub("", clean)
    clean = _PHONE_REGEX.sub("", clean)
    clean = _ADDRESS_REGEX.sub("", clean)
    clean = _PO_BOX_REGEX.sub("", clean)
    clean = re.sub(r"\s+([,.;])", r"\1", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:MAX_DESCRIPTION_CHARS]


def get_dog_age_category(months: int) -> DogAgeCategory:
    """Derive dog age category strictly according to Contract v2 Section 2."""
    if months < 6:
        return DogAgeCategory.PUPPY
    if months <= 18:
        return DogAgeCategory.ADOLESCENT
    if months <= 83:
        return DogAgeCategory.ADULT
    return DogAgeCategory.SENIOR


# ==============================================================================
# 4. Request & Response Validation Schemas (Pydantic Models)
# ==============================================================================

class MatchConsentIn(BaseModel):
    """Consent inputs for match processing (Contract v2 Section 2)."""
    match_processing: bool = Field(..., description="Mandatory consent for matching calculation")
    terms: bool = Field(..., description="Mandatory consent for terms")
    referral_contact: Optional[bool] = Field(default=False, description="Collected only before enquiry")
    follow_up: Optional[bool] = Field(default=False, description="Separately optional follow-up consent")

    @field_validator("match_processing", "terms", mode="before")
    @classmethod
    def validate_strict_mandatory_consent(cls, v: Any, info: Any) -> bool:
        if not isinstance(v, bool):
            raise ValueError(f"{info.field_name} must be an actual boolean, got {type(v).__name__}")
        if not v:
            raise ValueError(f"{info.field_name} must be explicitly accepted")
        return v

    @field_validator("referral_contact", "follow_up", mode="before")
    @classmethod
    def validate_strict_optional_consent(cls, v: Any, info: Any) -> Optional[bool]:
        if v is not None and not isinstance(v, bool):
            raise ValueError(f"{info.field_name} must be an actual boolean, got {type(v).__name__}")
        return v


class MatchRequestIn(BaseModel):
    """Strict, bounded matching request schema (Contract v2 Section 2)."""
    suburb_or_postcode: str = Field(..., min_length=2, max_length=60)
    dog_age_months: int = Field(..., ge=0, le=360)
    primary_concerns: List[str] = Field(..., min_length=1)
    service_format: str = Field(..., description="Explicit service format preference")
    method_preference: str = Field(..., description="Explicit method preference")
    behaviour_description: Optional[str] = Field(default="")
    consent: MatchConsentIn
    policy_version: str = Field(default=DECISION_CONTRACT_VERSION)

    @field_validator("behaviour_description", mode="before")
    @classmethod
    def sanitize_description_field(cls, v: Any) -> str:
        return sanitize_behaviour_description(v)

    @field_validator("primary_concerns")
    @classmethod
    def validate_concerns(cls, concerns: List[str]) -> List[str]:
        valid_concerns = {c.value for c in PrimaryConcern}
        for c in concerns:
            if c not in valid_concerns:
                raise ValueError(f"Unknown primary concern: {c}")
        return concerns

    @field_validator("service_format")
    @classmethod
    def validate_service_format(cls, v: str) -> str:
        valid_formats = {f.value for f in ServiceFormatPreference}
        if v not in valid_formats:
            raise ValueError(f"Unknown service format: {v}")
        return v

    @field_validator("method_preference")
    @classmethod
    def validate_method_preference(cls, v: str) -> str:
        valid_methods = {m.value for m in MethodPreference}
        if v not in valid_methods:
            raise ValueError(f"Unknown method preference: {v}")
        return v


class MatchCandidateCard(BaseModel):
    """Candidate presentation card schema (Contract v2 Section 5 & 6)."""
    trainer_id: str
    match_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reason_codes: List[ReasonCode] = Field(..., min_length=1)
    explanation: str
    search_scope: SearchScope = SearchScope.LOCAL

    @field_validator("explanation")
    @classmethod
    def validate_explanation_content(cls, text: str) -> str:
        clean = text.strip()
        if not clean:
            raise ValueError("Explanation must not be empty")
        for pat in PROHIBITED_EXPLANATION_PATTERNS:
            if pat.search(clean):
                raise ValueError(f"Explanation contains prohibited term: {clean}")
        return clean


class DecisionResponseV2(BaseModel):
    """Deterministic output schema conforming to Contract v2 Section 3 & 5."""
    decision_state: DecisionState
    candidates: List[MatchCandidateCard] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    degraded: bool = False
    search_scope: SearchScope = SearchScope.LOCAL
    policy_version: str = DECISION_CONTRACT_VERSION
    disclaimer: Optional[str] = None
    clarification_prompt: Optional[str] = None

    @field_validator("reason_codes")
    @classmethod
    def validate_top_level_reason_codes(cls, codes: List[str]) -> List[str]:
        for code in codes:
            if code not in ALLOWED_TOP_LEVEL_REASON_CODES:
                raise ValueError(f"Disallowed top-level reason code: {code}")
        return codes

    def validate_against_eligible_pool(
        self,
        eligible_pool: Any,
    ) -> None:
        """Reject candidate IDs outside the deterministic pool and validate explanation truthfulness."""
        if isinstance(eligible_pool, set):
            eligible_ids = eligible_pool
            cand_map: Dict[str, Dict[str, Any]] = {}
        elif isinstance(eligible_pool, dict):
            eligible_ids = set(eligible_pool.keys())
            cand_map = eligible_pool
        elif isinstance(eligible_pool, list):
            eligible_ids = {c.get("trainer_id") or c.get("id") for c in eligible_pool}
            cand_map = {c.get("trainer_id") or c.get("id"): c for c in eligible_pool}
        else:
            eligible_ids = set(eligible_pool)
            cand_map = {}

        for card in self.candidates:
            if card.trainer_id not in eligible_ids:
                raise ValueError(
                    f"Candidate {card.trainer_id} is not in deterministic eligible pool: {eligible_ids}"
                )
            if cand_map and card.trainer_id in cand_map:
                cand = cand_map[card.trainer_id]
                validate_explanation_truthfulness(card.explanation, cand)


def validate_explanation_truthfulness(
    explanation: str,
    candidate_projection: Dict[str, Any],
) -> None:
    """Validate that candidate card explanation contains only claims supported by verified facts.

    Rejects:
    - Prohibited terms (superlatives, guarantees, clinical diagnoses, experience, availability, accreditation, personality, 'verified expertise').
    - Factual claims contradicted or unsupported by the candidate's match-ready projection.
    """
    clean = str(explanation or "").strip()
    if not clean:
        raise ValueError("Explanation must not be empty")

    for pat in PROHIBITED_EXPLANATION_PATTERNS:
        if pat.search(clean):
            raise ValueError(f"Explanation contains prohibited term: {clean}")

    cand_specs = set(candidate_projection.get("specialties") or [])
    cand_formats = set(candidate_projection.get("service_formats") or [])
    cand_stages = set(candidate_projection.get("life_stages") or [])
    cand_catchment = str(candidate_projection.get("catchment_type") or "").lower()

    lower = clean.lower()

    if "puppy" in lower:
        has_puppy = "puppy_training" in cand_specs or "puppy" in cand_stages or "all_life_stages" in cand_stages
        if not has_puppy:
            raise ValueError(f"Explanation claims puppy support not backed by candidate projection facts: '{clean}'")

    if "in-home" in lower or "in home" in lower:
        if "in_home" not in cand_formats:
            raise ValueError(f"Explanation claims in-home format not backed by candidate projection facts: '{clean}'")

    if "facility" in lower:
        if "facility" not in cand_formats and "outdoor_park" not in cand_formats:
            raise ValueError(f"Explanation claims facility format not backed by candidate projection facts: '{clean}'")

    if "group" in lower:
        if "group_classes" not in cand_formats:
            raise ValueError(f"Explanation claims group class format not backed by candidate projection facts: '{clean}'")

    if "online" in lower:
        if "online" not in cand_formats:
            raise ValueError(f"Explanation claims online format not backed by candidate projection facts: '{clean}'")

    if "aggression" in lower:
        if "aggression" not in cand_specs:
            raise ValueError(f"Explanation claims aggression specialty not backed by candidate projection facts: '{clean}'")

    if "separation anxiety" in lower:
        if "separation_anxiety" not in cand_specs:
            raise ValueError(f"Explanation claims separation anxiety specialty not backed by candidate projection facts: '{clean}'")

    if "reactivity" in lower or "reactive" in lower:
        if "leash_reactivity" not in cand_specs and "behaviour_modification" not in cand_specs:
            raise ValueError(f"Explanation claims reactivity specialty not backed by candidate projection facts: '{clean}'")

    if "greater melbourne" in lower:
        if cand_catchment not in {"melbourne_wide", "greater_melbourne"}:
            raise ValueError(f"Explanation claims Greater Melbourne coverage not backed by candidate projection facts: '{clean}'")


validate_explanation_against_facts = validate_explanation_truthfulness


# ==============================================================================
# 5. Locality Resolution Helpers
# ==============================================================================

def resolve_canonical_locality(suburb_or_postcode: str) -> Dict[str, Any]:
    """Resolve suburb or postcode against the canonical catalogue (DF-018)."""
    clean = str(suburb_or_postcode or "").strip()
    if not clean:
        return {"valid": False, "reason": "empty_locality"}

    catalogue = load_catalogue()
    suburbs = catalogue["suburbs"]

    for row in suburbs:
        if row["suburb_name"].lower() == clean.lower() or row["slug"].lower() == clean.lower():
            return {
                "valid": True,
                "canonical_name": row["suburb_name"],
                "slug": row["slug"],
                "region_cluster": row.get("region_cluster"),
                "postcodes": row.get("postcodes", []),
            }

    if clean.isdigit() and len(clean) == 4:
        matching = [row for row in suburbs if clean in row.get("postcodes", [])]
        if len(matching) == 1:
            row = matching[0]
            return {
                "valid": True,
                "canonical_name": row["suburb_name"],
                "slug": row["slug"],
                "region_cluster": row.get("region_cluster"),
                "postcodes": row.get("postcodes", []),
            }
        elif len(matching) > 1:
            return {
                "valid": False,
                "reason": "ambiguous_postcode",
                "candidate_suburbs": sorted(row["suburb_name"] for row in matching),
            }

    return {"valid": False, "reason": "unknown_locality"}


# ==============================================================================
# 6. Deterministic Candidate Eligibility Evaluation (Fail-Closed)
# ==============================================================================

def check_candidate_eligibility(
    candidate: Dict[str, Any],
    request: MatchRequestIn,
    *,
    search_scope: str = SearchScope.LOCAL.value,
    triage_state: Optional[DecisionState] = None,
) -> Tuple[bool, List[str]]:
    """Evaluate deterministic eligibility over build_match_ready_projection facts.

    Governance (Contract v2 Section 4, DF-026):
    - Must be match_eligible == True.
    - Format compatibility.
    - Method compatibility.
    - Life stage compatibility (empty or missing fails closed).
    - Local eligibility requires exact declared serviced_suburbs match (profile suburb is not a declaration).
    - Broader coverage may use only declared greater_melbourne/melbourne_wide catchment.
    - Concern / specialty mapping (separation_anxiety requires separation_anxiety).
    - Serious behaviourist requirement if serious_behavioural_support triage triggered.
    """
    if not candidate.get("match_eligible"):
        return False, ["projection_ineligible"] + list(candidate.get("eligibility_reasons", []))

    # 1. Service format compatibility
    req_format = request.service_format
    if req_format != ServiceFormatPreference.ANY.value:
        formats = candidate.get("service_formats") or []
        if req_format == ServiceFormatPreference.IN_HOME.value:
            if "in_home" not in formats:
                return False, ["format_incompatible_in_home"]
        elif req_format == ServiceFormatPreference.FACILITY_OR_FIELD.value:
            if not ("facility" in formats or "outdoor_park" in formats):
                return False, ["format_incompatible_facility"]
        elif req_format == ServiceFormatPreference.GROUP_CLASS.value:
            if "group_classes" not in formats:
                return False, ["format_incompatible_group"]
        elif req_format == ServiceFormatPreference.ONLINE_COACHING.value:
            if "online" not in formats:
                return False, ["format_incompatible_online"]

    # 2. Method preference compatibility
    req_method = request.method_preference
    cand_philosophy = str(candidate.get("training_philosophy") or "")
    if req_method == MethodPreference.POSITIVE_REINFORCEMENT_ONLY.value:
        if cand_philosophy != "positive_reinforcement_force_free":
            return False, ["method_incompatible_positive_only"]
    elif req_method == MethodPreference.BALANCED.value:
        if cand_philosophy != "balanced":
            return False, ["method_incompatible_balanced"]

    # 3. Dog life stage compatibility (empty or missing fails closed)
    cand_stages = candidate.get("life_stages")
    if not cand_stages:
        return False, ["missing_life_stage_support"]

    dog_stage = get_dog_age_category(request.dog_age_months).value
    if not (dog_stage in cand_stages or "all_life_stages" in cand_stages):
        return False, ["life_stage_incompatible"]

    # 4. Locality and catchment compatibility
    loc_res = resolve_canonical_locality(request.suburb_or_postcode)
    req_suburb = loc_res.get("canonical_name", request.suburb_or_postcode)

    serviced = set(candidate.get("serviced_suburbs") or [])
    catchment = str(candidate.get("catchment_type") or "").lower()

    if search_scope == SearchScope.LOCAL.value:
        # Exact serviced_suburbs match required; trainer profile suburb is NOT a service area declaration
        if req_suburb not in serviced:
            return False, ["outside_local_service_area"]
    else:  # expanded search scope
        # Broader coverage may use ONLY declared greater_melbourne / melbourne_wide catchment
        is_melb_wide = catchment in {"melbourne_wide", "greater_melbourne"}
        if not is_melb_wide:
            return False, ["outside_expanded_catchment"]

    # 5. Concern / specialty mapping overlap
    cand_specs = set(candidate.get("specialties") or [])
    required_specs: Set[str] = set()
    for concern in request.primary_concerns:
        mapped = CONCERN_TO_SPECIALTIES_MAP.get(concern, set())
        required_specs.update(mapped)

    if not required_specs or not cand_specs.intersection(required_specs):
        return False, ["no_matching_specialty"]

    # 6. Serious behavioural support triage restriction
    is_serious = (
        triage_state == DecisionState.SERIOUS_BEHAVIOURAL_SUPPORT
        or PrimaryConcern.AGGRESSION.value in request.primary_concerns
    )
    if is_serious:
        serious_specs = {"aggression", "behaviour_modification"}
        if not cand_specs.intersection(serious_specs):
            return False, ["not_qualified_for_serious_behaviour"]

    return True, ["eligible"]


# ==============================================================================
# 7. Deterministic Fit Scoring & Truthful Explanation Templates
# ==============================================================================

def compute_deterministic_fit(
    candidate: Dict[str, Any],
    request: MatchRequestIn,
    *,
    search_scope: str = SearchScope.LOCAL.value,
    triage_state: Optional[DecisionState] = None,
) -> Tuple[float, List[ReasonCode], str]:
    """Compute paid-neutral deterministic fit score for test reference fixture validation.

    Governance (DF-023, Invariant 5):
    - NO outcome_score contribution (weight is strictly 0.0).
    - NO unconditional 0.40 baseline. Unqualified candidates receive 0.0.
    - Qualification threshold = 0.60.
    - Must match at least one concern; otherwise returns 0.0.
    - Permitted card reason codes only.
    - Deterministic factual explanation template without 'verified expertise' or unsupported claims.
    """
    cand_specs = set(candidate.get("specialties") or [])
    cand_formats = set(candidate.get("service_formats") or [])
    cand_stages = set(candidate.get("life_stages") or [])
    cand_phil = str(candidate.get("training_philosophy") or "")

    reason_codes: List[ReasonCode] = []

    # 1. Concern coverage score (weight: 0.40)
    matched_concerns = 0
    total_concerns = len(request.primary_concerns)
    required_specs: Set[str] = set()
    for c in request.primary_concerns:
        mapped = CONCERN_TO_SPECIALTIES_MAP.get(c, set())
        required_specs.update(mapped)
        if cand_specs.intersection(mapped):
            matched_concerns += 1

    if matched_concerns == 0:
        return 0.0, [], ""

    reason_codes.append(ReasonCode.CAPABILITY_CONCERN_MATCH)
    concern_score = (matched_concerns / total_concerns) * 0.40

    # 2. Life stage compatibility (weight: 0.15)
    dog_stage = get_dog_age_category(request.dog_age_months).value
    life_stage_score = 0.0
    if dog_stage in cand_stages or "all_life_stages" in cand_stages:
        life_stage_score = 0.15
        reason_codes.append(ReasonCode.LIFE_STAGE_MATCH)

    # 3. Service format compatibility (weight: 0.15)
    req_format = request.service_format
    format_score = 0.0
    if req_format == ServiceFormatPreference.ANY.value:
        format_score = 0.15
        reason_codes.append(ReasonCode.FORMAT_MATCH)
    elif req_format == ServiceFormatPreference.IN_HOME.value and "in_home" in cand_formats:
        format_score = 0.15
        reason_codes.append(ReasonCode.FORMAT_MATCH)
    elif req_format == ServiceFormatPreference.FACILITY_OR_FIELD.value and ("facility" in cand_formats or "outdoor_park" in cand_formats):
        format_score = 0.15
        reason_codes.append(ReasonCode.FORMAT_MATCH)
    elif req_format == ServiceFormatPreference.GROUP_CLASS.value and "group_classes" in cand_formats:
        format_score = 0.15
        reason_codes.append(ReasonCode.FORMAT_MATCH)
    elif req_format == ServiceFormatPreference.ONLINE_COACHING.value and "online" in cand_formats:
        format_score = 0.15
        reason_codes.append(ReasonCode.FORMAT_MATCH)

    # 4. Method preference compatibility (weight: 0.15)
    req_method = request.method_preference
    method_score = 0.0
    if req_method == MethodPreference.NO_PREFERENCE.value:
        method_score = 0.15
        if cand_phil:
            reason_codes.append(ReasonCode.METHOD_PREFERENCE_MATCH)
    elif req_method == MethodPreference.POSITIVE_REINFORCEMENT_ONLY.value and cand_phil == "positive_reinforcement_force_free":
        method_score = 0.15
        reason_codes.append(ReasonCode.METHOD_PREFERENCE_MATCH)
    elif req_method == MethodPreference.BALANCED.value and cand_phil == "balanced":
        method_score = 0.15
        reason_codes.append(ReasonCode.METHOD_PREFERENCE_MATCH)

    # 5. Locality score (weight: 0.15 for local, 0.05 for expanded)
    locality_score = 0.0
    if search_scope == SearchScope.LOCAL.value:
        locality_score = 0.15
        reason_codes.append(ReasonCode.SERVICE_AREA_MATCH)
    else:
        locality_score = 0.05
        reason_codes.append(ReasonCode.EXPANDED_SERVICE_AREA)

    is_serious = (
        triage_state == DecisionState.SERIOUS_BEHAVIOURAL_SUPPORT
        or PrimaryConcern.AGGRESSION.value in request.primary_concerns
    )
    if is_serious:
        reason_codes.append(ReasonCode.SERIOUS_BEHAVIOURAL_SUPPORT)

    total_raw_fit = round(concern_score + life_stage_score + format_score + method_score + locality_score, 4)

    if total_raw_fit < QUALIFICATION_THRESHOLD:
        return 0.0, [], ""

    # Deterministic factual explanation template
    if req_format == ServiceFormatPreference.ANY.value:
        fmt_str = "training sessions"
    elif req_format == ServiceFormatPreference.IN_HOME.value:
        fmt_str = "in-home training sessions"
    elif req_format == ServiceFormatPreference.FACILITY_OR_FIELD.value:
        fmt_str = "facility training sessions"
    elif req_format == ServiceFormatPreference.GROUP_CLASS.value:
        fmt_str = "group training classes"
    elif req_format == ServiceFormatPreference.ONLINE_COACHING.value:
        fmt_str = "online coaching sessions"
    else:
        fmt_str = "training sessions"

    matched_specs = sorted(cand_specs.intersection(required_specs))
    specs_str = ", ".join(s.replace("_", " ") for s in matched_specs[:2]) if matched_specs else "dog training"

    loc_res = resolve_canonical_locality(request.suburb_or_postcode)
    req_suburb = loc_res.get("canonical_name", request.suburb_or_postcode)

    if search_scope == SearchScope.LOCAL.value:
        loc_str = f"in {req_suburb}"
    else:
        loc_str = "across Greater Melbourne"

    explanation = f"{candidate.get('name', 'Trainer')} provides {fmt_str} for {specs_str} {loc_str}."

    return total_raw_fit, reason_codes, explanation


# ==============================================================================
# 8. Fair Presentation & Exact 0.05 Tiebreaking
# ==============================================================================

def apply_fair_presentation(
    candidates: List[Dict[str, Any]],
    *,
    max_results: int = MAX_RECOMMENDED_CANDIDATES,
) -> List[Dict[str, Any]]:
    """Apply exact 0.05 comparable-fit commercial tiebreaking (Contract v2 Section 6, Invariant 6)."""
    if not candidates:
        return []

    decorated: List[Dict[str, Any]] = []
    for c in candidates:
        raw_fit = float(c.get("match_score", 0.0))
        policy_penalty = float(c.get("policy_penalty", 0.0))
        final_fit = round(raw_fit - policy_penalty, 4)
        tier = str(c.get("tier") or "unclaimed").lower()
        tier_weight = COMMERCIAL_TIER_PRIORITY.get(tier, 0)
        trainer_id = str(c.get("trainer_id") or "")

        item = dict(c)
        item["final_fit"] = final_fit
        item["tier_weight"] = tier_weight
        item["trainer_id"] = trainer_id
        decorated.append(item)

    s_max = max(item["final_fit"] for item in decorated)

    inside_band: List[Dict[str, Any]] = []
    outside_band: List[Dict[str, Any]] = []

    for item in decorated:
        diff = round(s_max - item["final_fit"], 4)
        if diff <= COMPARABLE_FIT_BAND:
            inside_band.append(item)
        else:
            outside_band.append(item)

    # Inside band: sort by tier_weight descending, final_fit descending, trainer_id ascending
    inside_band.sort(key=lambda x: (-x["tier_weight"], -x["final_fit"], x["trainer_id"]))

    # Outside band: sort strictly by final_fit descending, trainer_id ascending
    outside_band.sort(key=lambda x: (-x["final_fit"], x["trainer_id"]))

    combined = inside_band + outside_band
    return combined[:max_results]


# ==============================================================================
# 9. Full Deterministic Matching Engine
# ==============================================================================

def run_deterministic_matching(
    request: MatchRequestIn,
    candidate_pool: List[Dict[str, Any]],
    *,
    degraded: bool = False,
    triage_state: Optional[DecisionState] = None,
) -> DecisionResponseV2:
    """Run full deterministic decision contract workflow (Contract v2 Sections 3, 4, 5, 6)."""
    # 1. State-level triage handling (P2/M6 fixtures)
    if triage_state in {DecisionState.IMMEDIATE_HUMAN_DANGER, DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT}:
        return DecisionResponseV2(
            decision_state=triage_state,
            candidates=[],
            reason_codes=[triage_state.value],
            degraded=degraded,
            search_scope=SearchScope.LOCAL,
        )

    # 2. Other / Unsure concerns require clarification until owner chooses a canonical concern.
    # Free text cannot create a specialty mapping.
    has_other_or_unsure = any(
        c in {PrimaryConcern.OTHER.value, PrimaryConcern.UNSURE.value}
        for c in request.primary_concerns
    )
    if has_other_or_unsure:
        return DecisionResponseV2(
            decision_state=DecisionState.NEEDS_CLARIFICATION,
            candidates=[],
            reason_codes=["needs_clarification"],
            degraded=degraded,
            search_scope=SearchScope.LOCAL,
            clarification_prompt="Please select a canonical dog training concern (e.g. basic manners, puppy prep, reactivity) so we can match an appropriate certified specialist.",
        )

    # 3. Local eligibility
    local_eligible: List[Dict[str, Any]] = []
    for cand in candidate_pool:
        is_el, _ = check_candidate_eligibility(
            cand, request, search_scope=SearchScope.LOCAL.value, triage_state=triage_state
        )
        if is_el:
            local_eligible.append(cand)

    # 4. Score local candidates
    scored_candidates: List[Dict[str, Any]] = []
    for cand in local_eligible[:MAX_ELIGIBLE_CANDIDATES]:
        score, codes, explanation = compute_deterministic_fit(
            cand, request, search_scope=SearchScope.LOCAL.value, triage_state=triage_state
        )
        if score >= QUALIFICATION_THRESHOLD:
            scored_candidates.append({
                "trainer_id": cand.get("trainer_id") or cand.get("id"),
                "name": cand.get("name"),
                "match_score": score,
                "reason_codes": codes,
                "explanation": explanation,
                "tier": cand.get("tier", "unclaimed"),
                "policy_penalty": cand.get("policy_penalty", 0.0),
                "search_scope": SearchScope.LOCAL,
            })

    # 5. Thin-local-supply condition:
    # Expansion triggers ONLY when fewer than 3 LOCAL ELIGIBLE candidates exist!
    if len(local_eligible) < MAX_RECOMMENDED_CANDIDATES:
        expanded_eligible: List[Dict[str, Any]] = []
        for cand in candidate_pool:
            if cand in local_eligible:
                continue
            is_el, _ = check_candidate_eligibility(
                cand, request, search_scope=SearchScope.EXPANDED.value, triage_state=triage_state
            )
            if is_el:
                expanded_eligible.append(cand)

        remaining_slots = MAX_ELIGIBLE_CANDIDATES - len(scored_candidates)
        for cand in expanded_eligible[:remaining_slots]:
            score, codes, explanation = compute_deterministic_fit(
                cand, request, search_scope=SearchScope.EXPANDED.value, triage_state=triage_state
            )
            if score >= QUALIFICATION_THRESHOLD:
                scored_candidates.append({
                    "trainer_id": cand.get("trainer_id") or cand.get("id"),
                    "name": cand.get("name"),
                    "match_score": score,
                    "reason_codes": codes,
                    "explanation": explanation,
                    "tier": cand.get("tier", "unclaimed"),
                    "policy_penalty": cand.get("policy_penalty", 0.0),
                    "search_scope": SearchScope.EXPANDED,
                })

    # 6. Fair Presentation (0.05 band tiebreak)
    presented = apply_fair_presentation(scored_candidates, max_results=MAX_RECOMMENDED_CANDIDATES)

    # 7. Map to closed decision response
    if not presented:
        state = (
            DecisionState.DEGRADED_NO_CONFIRMED_MATCH
            if degraded
            else DecisionState.NO_CONFIRMED_MATCH
        )
        return DecisionResponseV2(
            decision_state=state,
            candidates=[],
            reason_codes=["no_qualified_candidates"],
            degraded=degraded,
            search_scope=SearchScope.LOCAL,
        )

    any_expanded = any(p.get("search_scope") == SearchScope.EXPANDED for p in presented)
    overall_scope = SearchScope.EXPANDED if any_expanded else SearchScope.LOCAL

    if degraded:
        state = DecisionState.DEGRADED_RECOMMENDATIONS
    elif any_expanded:
        state = DecisionState.LIMITED_LOCAL_RESULTS
    else:
        state = DecisionState.RECOMMENDATIONS

    card_models = [
        MatchCandidateCard(
            trainer_id=str(p["trainer_id"]),
            match_score=float(p["match_score"]),
            reason_codes=list(p["reason_codes"]),
            explanation=str(p["explanation"]),
            search_scope=p["search_scope"],
        )
        for p in presented
    ]

    top_reasons = [r.value for r in card_models[0].reason_codes] if card_models else []

    return DecisionResponseV2(
        decision_state=state,
        candidates=card_models,
        reason_codes=top_reasons,
        degraded=degraded,
        search_scope=overall_scope,
    )


# ==============================================================================
# 10. Test-Only Gemini Stub Adapter & Fallback Wrapper
# ==============================================================================

class GeminiAdapterError(Exception):
    """Base exception for Gemini adapter errors."""
    pass


class GeminiTimeoutError(GeminiAdapterError):
    """Raised when simulated Gemini API call times out."""
    pass


class GeminiRateLimitError(GeminiAdapterError):
    """Raised when simulated Gemini API quota is exceeded (HTTP 429)."""
    pass


class GeminiUnavailableError(GeminiAdapterError):
    """Raised when simulated Gemini service is unavailable (HTTP 503)."""
    pass


class GeminiMalformedResponseError(GeminiAdapterError):
    """Raised when simulated Gemini returns malformed response."""
    pass


class GeminiStubAdapter:
    """Test-only adapter simulating Gemini model responses conforming to Contract v2.

    Supports simulated execution modes:
    - 'normal': Constructs an independent contract-shaped model response.
    - 'timeout': Raises GeminiTimeoutError through adapter boundary.
    - 'rate_limit': Raises GeminiRateLimitError through adapter boundary.
    - 'unavailable': Raises GeminiUnavailableError through adapter boundary.
    - 'malformed_output': Returns malformed data violating schema/pool/truthfulness constraints.
    """

    def __init__(self, mode: str = "normal"):
        self.mode = mode

    def call_model(
        self,
        request: MatchRequestIn,
        eligible_candidates: List[Dict[str, Any]],
        search_scope: SearchScope = SearchScope.LOCAL,
        triage_state: Optional[DecisionState] = None,
        *,
        candidate_scopes: Optional[Dict[str, str]] = None,
        canonical_locality: Optional[str] = None,
        db: Optional[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Simulate calling the Gemini AI model. Raises through adapter boundary on degradation."""
        if self.mode == "timeout":
            raise GeminiTimeoutError("Gemini call timed out after 5.0s")
        elif self.mode == "rate_limit":
            raise GeminiRateLimitError("Gemini API quota exceeded (HTTP 429)")
        elif self.mode == "unavailable":
            raise GeminiUnavailableError("Gemini service unavailable (HTTP 503)")
        elif self.mode == "malformed_output":
            return {
                "decision_state": "recommendations",
                "candidates": [
                    {
                        "trainer_id": "unauthorized_hallucinated_candidate_999",
                        "match_score": 0.99,
                        "reason_codes": ["capability_concern_match"],
                        "explanation": "Guaranteed best trainer in Australia with 20 years experience.",
                        "search_scope": search_scope.value,
                    }
                ],
                "reason_codes": ["capability_concern_match"],
                "search_scope": search_scope.value,
            }

        # NORMAL MODE:
        # Construct an independent contract-shaped model response from eligible candidates
        if triage_state in {DecisionState.IMMEDIATE_HUMAN_DANGER, DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT}:
            return {
                "decision_state": triage_state.value,
                "candidates": [],
                "reason_codes": [triage_state.value],
                "search_scope": SearchScope.LOCAL.value,
            }

        if not eligible_candidates:
            return {
                "decision_state": DecisionState.NO_CONFIRMED_MATCH.value,
                "candidates": [],
                "reason_codes": ["no_qualified_candidates"],
                "search_scope": search_scope.value,
            }

        loc_res = resolve_canonical_locality(request.suburb_or_postcode)
        req_suburb = (canonical_locality or loc_res.get("canonical_name") or request.suburb_or_postcode).strip().lower()

        # Independently select and rank candidates up to MAX_RECOMMENDED_CANDIDATES
        # without calling run_deterministic_matching
        cards_data: List[Dict[str, Any]] = []
        for cand in eligible_candidates:
            cid = cand.get("trainer_id") or cand.get("id")
            if candidate_scopes and cid in candidate_scopes:
                cand_scope = candidate_scopes[cid]
            else:
                cand_serviced = {str(s).strip().lower() for s in (cand.get("serviced_suburbs") or [])}
                if req_suburb in cand_serviced:
                    cand_scope = SearchScope.LOCAL.value
                else:
                    cand_scope = SearchScope.EXPANDED.value

            score, codes, explanation = compute_deterministic_fit(
                cand, request, search_scope=cand_scope, triage_state=triage_state
            )
            if score >= QUALIFICATION_THRESHOLD:
                cards_data.append({
                    "trainer_id": cid,
                    "match_score": score,
                    "reason_codes": [c.value for c in codes],
                    "explanation": explanation,
                    "search_scope": cand_scope,
                    "tier": cand.get("tier", "unclaimed"),
                    "policy_penalty": cand.get("policy_penalty", 0.0),
                })

        presented = apply_fair_presentation(cards_data, max_results=MAX_RECOMMENDED_CANDIDATES)

        if not presented:
            return {
                "decision_state": DecisionState.NO_CONFIRMED_MATCH.value,
                "candidates": [],
                "reason_codes": ["no_qualified_candidates"],
                "search_scope": search_scope.value,
            }

        any_expanded = any(p.get("search_scope") == SearchScope.EXPANDED.value for p in presented)
        decision_state = (
            DecisionState.LIMITED_LOCAL_RESULTS.value
            if any_expanded
            else DecisionState.RECOMMENDATIONS.value
        )

        final_cards = [
            {
                "trainer_id": p["trainer_id"],
                "match_score": p["match_score"],
                "reason_codes": p["reason_codes"],
                "explanation": p["explanation"],
                "search_scope": p["search_scope"],
            }
            for p in presented
        ]

        top_reasons = final_cards[0]["reason_codes"] if final_cards else []

        return {
            "decision_state": decision_state,
            "candidates": final_cards,
            "reason_codes": top_reasons,
            "search_scope": search_scope.value,
        }

    def match(
        self,
        request: MatchRequestIn,
        candidate_pool: List[Dict[str, Any]],
        *,
        triage_state: Optional[DecisionState] = None,
    ) -> DecisionResponseV2:
        """Convenience entry point executing through the deterministic fallback wrapper."""
        return execute_matching_with_adapter(request, candidate_pool, self, triage_state=triage_state)


def execute_matching_with_adapter(
    request: MatchRequestIn,
    candidate_pool: List[Dict[str, Any]],
    adapter: Any,
    *,
    triage_state: Optional[DecisionState] = None,
    db: Optional[Any] = None,
) -> DecisionResponseV2:
    """Execute matching through adapter boundary with deterministic fallback wrapper."""
    # State-level triage check
    if triage_state in {DecisionState.IMMEDIATE_HUMAN_DANGER, DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT}:
        return run_deterministic_matching(request, candidate_pool, triage_state=triage_state)

    # Other / Unsure concerns require clarification
    has_other_or_unsure = any(
        c in {PrimaryConcern.OTHER.value, PrimaryConcern.UNSURE.value}
        for c in request.primary_concerns
    )
    if has_other_or_unsure:
        return run_deterministic_matching(request, candidate_pool, triage_state=triage_state)

    # Resolve canonical locality
    loc_res = resolve_canonical_locality(request.suburb_or_postcode)
    canonical_suburb = loc_res.get("canonical_name", request.suburb_or_postcode)

    # Compute local eligible candidates
    local_eligible = [
        c for c in candidate_pool
        if check_candidate_eligibility(c, request, search_scope=SearchScope.LOCAL.value, triage_state=triage_state)[0]
    ]

    # Thin supply condition: fewer than 3 LOCAL ELIGIBLE candidates
    search_scope = SearchScope.LOCAL
    eligible_pool = list(local_eligible)
    candidate_scopes: Dict[str, str] = {
        (c.get("trainer_id") or c.get("id")): SearchScope.LOCAL.value
        for c in local_eligible
    }
    if len(local_eligible) < MAX_RECOMMENDED_CANDIDATES:
        expanded_eligible = [
            c for c in candidate_pool
            if c not in local_eligible and check_candidate_eligibility(c, request, search_scope=SearchScope.EXPANDED.value, triage_state=triage_state)[0]
        ]
        if expanded_eligible:
            search_scope = SearchScope.EXPANDED
            eligible_pool.extend(expanded_eligible)
            for c in expanded_eligible:
                candidate_scopes[c.get("trainer_id") or c.get("id")] = SearchScope.EXPANDED.value

    try:
        try:
            raw_output = adapter.call_model(
                request,
                eligible_pool,
                search_scope,
                triage_state=triage_state,
                candidate_scopes=candidate_scopes,
                canonical_locality=canonical_suburb,
                db=db,
            )
        except TypeError:
            raw_output = adapter.call_model(
                request,
                eligible_pool,
                search_scope,
                triage_state=triage_state,
                candidate_scopes=candidate_scopes,
                canonical_locality=canonical_suburb,
            )
        # Parse into closed DecisionResponseV2
        model_resp = DecisionResponseV2(**raw_output)
        # Closed pool and explanation truthfulness validation
        cand_map = {c.get("trainer_id") or c.get("id"): c for c in eligible_pool}
        model_resp.validate_against_eligible_pool(cand_map)
        return model_resp
    except (GeminiAdapterError, ValidationError, ValueError):
        # Fallback wrapper catches declared adapter errors and model schema/contract validation errors
        return run_deterministic_matching(request, candidate_pool, degraded=True, triage_state=triage_state)


async def execute_matching_with_adapter_async(
    request: MatchRequestIn,
    candidate_pool: List[Dict[str, Any]],
    adapter: Any,
    *,
    triage_state: Optional[DecisionState] = None,
    db: Optional[Any] = None,
) -> DecisionResponseV2:
    """Async execution of matching through adapter boundary with deterministic fallback wrapper."""
    if triage_state in {DecisionState.IMMEDIATE_HUMAN_DANGER, DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT}:
        return run_deterministic_matching(request, candidate_pool, triage_state=triage_state)

    has_other_or_unsure = any(
        c in {PrimaryConcern.OTHER.value, PrimaryConcern.UNSURE.value}
        for c in request.primary_concerns
    )
    if has_other_or_unsure:
        return run_deterministic_matching(request, candidate_pool, triage_state=triage_state)

    loc_res = resolve_canonical_locality(request.suburb_or_postcode)
    canonical_suburb = loc_res.get("canonical_name", request.suburb_or_postcode)

    local_eligible = [
        c for c in candidate_pool
        if check_candidate_eligibility(c, request, search_scope=SearchScope.LOCAL.value, triage_state=triage_state)[0]
    ]

    search_scope = SearchScope.LOCAL
    eligible_pool = list(local_eligible)
    candidate_scopes: Dict[str, str] = {
        (c.get("trainer_id") or c.get("id")): SearchScope.LOCAL.value
        for c in local_eligible
    }
    if len(local_eligible) < MAX_RECOMMENDED_CANDIDATES:
        expanded_eligible = [
            c for c in candidate_pool
            if c not in local_eligible and check_candidate_eligibility(c, request, search_scope=SearchScope.EXPANDED.value, triage_state=triage_state)[0]
        ]
        if expanded_eligible:
            search_scope = SearchScope.EXPANDED
            eligible_pool.extend(expanded_eligible)
            for c in expanded_eligible:
                candidate_scopes[c.get("trainer_id") or c.get("id")] = SearchScope.EXPANDED.value

    try:
        if hasattr(adapter, "call_model_async") and callable(adapter.call_model_async):
            raw_output = await adapter.call_model_async(
                request,
                eligible_pool,
                search_scope,
                triage_state=triage_state,
                candidate_scopes=candidate_scopes,
                canonical_locality=canonical_suburb,
                db=db,
            )
        else:
            raw_output = adapter.call_model(
                request,
                eligible_pool,
                search_scope,
                triage_state=triage_state,
                candidate_scopes=candidate_scopes,
                canonical_locality=canonical_suburb,
                db=db,
            )
        model_resp = DecisionResponseV2(**raw_output)
        cand_map = {c.get("trainer_id") or c.get("id"): c for c in eligible_pool}
        model_resp.validate_against_eligible_pool(cand_map)
        return model_resp
    except (GeminiAdapterError, ValidationError, ValueError):
        return run_deterministic_matching(request, candidate_pool, degraded=True, triage_state=triage_state)


def get_default_ai_adapter() -> Any:
    """Return default production AI adapter for matching (GeminiMatchingAdapter)."""
    try:
        from services.ai import GeminiMatchingAdapter
    except ImportError:
        from backend.services.ai import GeminiMatchingAdapter
    return GeminiMatchingAdapter()


# ==============================================================================
# 7. Operational Primitives (Rate Limiting, Context Token, Pre-AI Triage)
# ==============================================================================

class MatchRateLimiter:
    """Application-level request limiter for matching requests.

    Governance (Contract v2 Section 2):
    - 10 match attempts per IP-derived, non-reversible key in 10 minutes (600s).
    - 30-second burst interval (at most 3 attempts within 30s).
    - Non-reversible SHA-256 hashed keys. Raw IP is never stored.
    - Exposes rate-limit events to /ops without personal data.
    """

    def __init__(
        self,
        max_attempts: int = MATCH_ATTEMPT_RATE_LIMIT,
        window_seconds: int = MATCH_RATE_LIMIT_WINDOW_S,
        burst_interval_seconds: int = MATCH_RATE_LIMIT_BURST_INTERVAL_S,
        burst_max_attempts: int = 3,
        salt: str = "dtd_match_rate_limit_salt_v2",
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.burst_interval_seconds = burst_interval_seconds
        self.burst_max_attempts = burst_max_attempts
        self.salt = salt
        self._history: Dict[str, List[float]] = defaultdict(list)

    def hash_key(self, raw_ip: str) -> str:
        """Derive a one-way non-reversible key from the client IP address."""
        clean_ip = (raw_ip or "unknown").strip().lower()
        return hashlib.sha256(f"{self.salt}:{clean_ip}".encode("utf-8")).hexdigest()

    def check_limit(self, raw_ip: str, now_ts: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        """Check whether the given IP is within rate limits.

        Returns:
            (allowed: bool, reason: Optional[str])
            Reasons: "window_limit_exceeded", "burst_limit_exceeded", or None
        """
        now = now_ts or time.time()
        key = self.hash_key(raw_ip)
        timestamps = self._history[key]

        # Prune timestamps older than window
        cutoff = now - self.window_seconds
        valid_ts = [t for t in timestamps if t >= cutoff]
        self._history[key] = valid_ts

        # 1. Check window limit (max 10 in 600s)
        if len(valid_ts) >= self.max_attempts:
            return False, "window_limit_exceeded"

        # 2. Check burst limit (max 3 in 30s)
        burst_cutoff = now - self.burst_interval_seconds
        burst_count = sum(1 for t in valid_ts if t >= burst_cutoff)
        if burst_count >= self.burst_max_attempts:
            return False, "burst_limit_exceeded"

        return True, None

    def record_attempt(self, raw_ip: str, now_ts: Optional[float] = None) -> None:
        """Record a successful match attempt timestamp."""
        now = now_ts or time.time()
        key = self.hash_key(raw_ip)
        self._history[key].append(now)

    def reset(self) -> None:
        """Clear all rate limit history (useful for testing)."""
        self._history.clear()


match_rate_limiter = MatchRateLimiter()


def generate_match_context_token() -> Tuple[str, str]:
    """Generate an opaque random context token and its SHA-256 hash.

    Returns:
        (raw_token, token_hash)
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_match_context_token(raw_token)
    return raw_token, token_hash


def hash_match_context_token(raw_token: str) -> str:
    """Compute deterministic SHA-256 hash of opaque token."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def classify_pre_ai_triage(
    primary_concerns: List[str],
    behaviour_description: Optional[str] = None,
) -> Optional[DecisionState]:
    """Evaluate pre-AI triage triggers before candidate eligibility.

    Governance (Contract v2 Section 3, DF-024):
    - Immediate human danger: active attack, child bite emergency -> IMMEDIATE_HUMAN_DANGER.
    - Urgent animal health: poison, seizure, profuse bleeding -> URGENT_ANIMAL_HEALTH_SUPPORT.
    - Serious behavioural support: bite history, severe aggression -> SERIOUS_BEHAVIOURAL_SUPPORT.
    - Unresolved other/unsure concerns -> NEEDS_CLARIFICATION.
    """
    clean_desc = sanitize_behaviour_description(behaviour_description or "")
    lower_desc = clean_desc.lower()

    # Immediate human danger triggers (child bite, active attack, police emergency)
    danger_triggers = [
        "child bite", "bitten a child", "bit a child", "attacked a child", "attacked child",
        "child attack", "active attack", "attacking someone", "emergency hospital",
        "police emergency", "vicious attack", "severe bite to a child",
    ]
    if any(t in lower_desc for t in danger_triggers):
        return DecisionState.IMMEDIATE_HUMAN_DANGER

    # Urgent animal health triggers (poison, seizure, unconscious, profuse bleeding)
    health_triggers = [
        "poison", "poisoned", "seizure", "unconscious",
        "profuse bleeding", "bleeding heavily", "hit by car",
    ]
    if any(t in lower_desc for t in health_triggers):
        return DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT

    # Serious behavioural support triggers
    serious_triggers = [
        "severe aggression", "history of bites", "multiple bites",
        "bites people", "bite history", "directed aggression",
    ]
    if any(t in lower_desc for t in serious_triggers) or PrimaryConcern.AGGRESSION.value in primary_concerns:
        return DecisionState.SERIOUS_BEHAVIOURAL_SUPPORT

    # Other / unsure concerns require clarification
    has_other_or_unsure = any(
        c in {PrimaryConcern.OTHER.value, PrimaryConcern.UNSURE.value}
        for c in primary_concerns
    )
    if has_other_or_unsure:
        return DecisionState.NEEDS_CLARIFICATION

    return None
