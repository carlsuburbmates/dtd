"""Official-source urgent provider directory and deterministic triage support.

Governed by:
- AGENTS.md (Rule 6A, locked boundaries)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md (M6)
- specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md (Section 3)
- Finding DF-024

Invariants:
1. No Maps/Places, aggregator, social, search-grounding or runtime provider import.
2. Local static records allowed ONLY where the provider's own official page supplies every displayed fact.
3. Triple Zero Victoria is the approved immediate-danger source (call 000).
4. U-Vet Werribee permanently closed in 2022 and is strictly forbidden from seeding.
5. The Lost Dogs' Home Vet Hospital is North Melbourne urgent-care only, with published phone and stated hours (NOT 24/7).
6. Veterinary-behaviourist records require direct official-provider evidence plus VPRBV registration/endorsement;
   otherwise show no current verified listing.
7. UI must not claim Melbourne-wide urgent coverage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UrgentProviderCategory(str, Enum):
    URGENT_VETERINARY_CARE = "urgent_veterinary_care"
    VETERINARY_BEHAVIOURIST = "veterinary_behaviourist"


class FreshnessState(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    SUPPRESSED = "suppressed"


class SourceBasis(str, Enum):
    OFFICIAL_PROVIDER = "official_provider"
    OFFICIAL_REGULATOR = "official_regulator"


class UrgentProviderDoc(BaseModel):
    provider_id: str
    category: UrgentProviderCategory
    name: str
    official_source_url: str
    contact_method: str
    service_area: List[str]
    stated_hours: str
    retrieved_at: str
    freshness_state: FreshnessState = FreshnessState.CURRENT
    correction_path: str = "/urgent-providers/correction"
    source_basis: SourceBasis


class UrgentProviderCorrectionIn(BaseModel):
    provider_id: Optional[str] = None
    provider_name: str
    official_source_url: str
    reason: str = Field(..., description="e.g. hours_changed, closed, contact_changed, removal_request")
    notes: Optional[str] = None
    contact_email: Optional[str] = None


# Official-source seeded records verified against provider's official web page
# U-Vet Werribee is excluded (permanently closed on 24 December 2022).
# No veterinary behaviourists are currently verified against VPRBV register with official direct evidence.
OFFICIAL_STATIC_URGENT_PROVIDERS: List[Dict[str, Any]] = [
    {
        "provider_id": "urgent_care_lost_dogs_home_north_melbourne",
        "category": UrgentProviderCategory.URGENT_VETERINARY_CARE.value,
        "name": "The Lost Dogs' Home Veterinary Hospital",
        "official_source_url": "https://vet.dogshome.com/",
        "contact_method": "(03) 8379 4498",
        "service_area": [
            "North Melbourne",
            "Flemington",
            "Kensington",
            "Melbourne",
            "Parkville",
            "Carlton",
            "West Melbourne",
        ],
        "stated_hours": "Monday to Friday: 8:10 am – 7:00 pm; Saturday: 9:00 am – 4:00 pm (Closed Sundays and Public Holidays; not a 24/7 hospital)",
        "retrieved_at": "2026-10-04T12:00:00Z",
        "last_verified_at": "2026-10-04T12:00:00Z",
        "freshness_state": FreshnessState.CURRENT.value,
        "correction_path": "/urgent-providers/correction",
        "source_basis": SourceBasis.OFFICIAL_PROVIDER.value,
    }
]

# Emergency card for immediate human danger
TRIPLE_ZERO_VICTORIA_NOTICE = {
    "source": "Triple Zero Victoria",
    "official_source_url": "https://www.triplezero.vic.gov.au/making-triple-zero-000-call",
    "action": "Call 000 immediately if there is an active threat of serious harm, dog attack, or a child bite requiring medical attention.",
    "phone": "000",
}


def compute_urgent_provider_freshness(
    provider: Dict[str, Any],
    *,
    as_of: Optional[datetime] = None,
    max_age_days: int = 90,
) -> tuple[FreshnessState, bool]:
    """Compute deterministic freshness state of an urgent provider record.

    Governance Invariants (AGENTS.md Rule 6A, M6, MP-003):
    - Suppressed providers fail closed immediately.
    - Records without retrieved_at or last_verified_at fail closed as STALE.
    - Records older than max_age_days (90 days) fail closed as STALE.
    - Only independently checked official-source records within max_age_days are CURRENT.
    """
    if str(provider.get("freshness_state") or "").lower() == FreshnessState.SUPPRESSED.value:
        return FreshnessState.SUPPRESSED, False

    ref_ts_str = str(provider.get("last_verified_at") or provider.get("retrieved_at") or "")
    if not ref_ts_str:
        return FreshnessState.STALE, False

    try:
        ref_dt = datetime.fromisoformat(ref_ts_str.replace("Z", "+00:00"))
        now_dt = as_of or datetime.now(timezone.utc)
        age_days = (now_dt - ref_dt).total_seconds() / 86400.0
        if age_days > max_age_days:
            return FreshnessState.STALE, False
        return FreshnessState.CURRENT, True
    except Exception:
        return FreshnessState.STALE, False


def get_static_urgent_providers(
    category: Optional[str] = None,
    freshness: Optional[str] = FreshnessState.CURRENT.value,
) -> List[Dict[str, Any]]:
    """Return filtered static urgent provider records."""
    results = []
    for p in OFFICIAL_STATIC_URGENT_PROVIDERS:
        if category and p.get("category") != category:
            continue
        state, is_fresh = compute_urgent_provider_freshness(p)
        effective_state = state.value if isinstance(state, FreshnessState) else str(state)
        if freshness and effective_state != freshness:
            continue
        out_doc = dict(p)
        out_doc["freshness_state"] = effective_state
        results.append(out_doc)
    return results


async def get_active_urgent_providers(
    db: Any,
    category: Optional[str] = None,
    suburb: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve active urgent providers from DB or static fallback with freshness verification."""
    cat_str = category.strip() if isinstance(category, str) and category.strip() else None
    sub_str = suburb.strip() if isinstance(suburb, str) and suburb.strip() else None

    if hasattr(db, "urgent_providers"):
        query: Dict[str, Any] = {"freshness_state": FreshnessState.CURRENT.value}
        if cat_str:
            query["category"] = cat_str
        if sub_str:
            query["$or"] = [
                {"service_area": sub_str},
                {"service_area": {"$regex": f"^{sub_str}$", "$options": "i"}},
            ]
        cursor = db.urgent_providers.find(query, {"_id": 0})
        docs = await cursor.to_list(100)
        if docs:
            fresh_docs = []
            for d in docs:
                state, is_fresh = compute_urgent_provider_freshness(d)
                if is_fresh and state == FreshnessState.CURRENT:
                    fresh_docs.append(dict(d))
            return fresh_docs

    # Fallback to static records if DB empty or unseeded
    static_docs = get_static_urgent_providers(category=cat_str, freshness=FreshnessState.CURRENT.value)
    if sub_str:
        norm_suburb = sub_str.lower()
        matched = [
            p for p in static_docs
            if any(s.strip().lower() == norm_suburb for s in p.get("service_area", []))
            or "north melbourne" in norm_suburb  # broad local inner north match
        ]
        if matched:
            return matched
    return static_docs
