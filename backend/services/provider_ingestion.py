"""Legacy provider-readiness dry run; it never publishes trainers.

Google Places remains fail-closed and is not DTD's persistent acquisition
source. The planned licensed Sensis/Thryv adapter does not exist yet and must
not be inferred from this module. See the canonical acquisition pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .abr_client import AbrClient
from .places_client import PlacesClient
from . import source_approvals


async def prepare_candidates(
    db: Any,
    suburbs: Iterable[str],
    *,
    registry: Optional[Dict[str, Any]] = None,
    places: Optional[PlacesClient] = None,
    abr: Optional[AbrClient] = None,
    allow_network: bool = False,
) -> Dict[str, Any]:
    registry = registry if registry is not None else source_approvals.load()
    places = places or PlacesClient()
    abr = abr or AbrClient(db)
    places_approved = source_approvals.approved(registry, "google_places", "trainer_discovery")
    abr_approved = source_approvals.approved(registry, "abr_web_services", "abn_verification")
    candidates: List[Dict[str, Any]] = []
    provider_states: List[Dict[str, Any]] = []

    for suburb in dict.fromkeys(" ".join(str(value).split()) for value in suburbs if str(value).strip()):
        result = await places.search_trainers(suburb, approved=places_approved, allow_network=allow_network)
        provider_states.append({"provider": "google_places", "scope": suburb, "state": result.get("state"), "reason_code": result.get("reason_code")})
        candidates.extend(result.get("candidates") or [])

    for candidate in candidates:
        abn = str(candidate.get("abn") or "").strip()
        if not abn:
            candidate["abr_evidence"] = {"state": "not_attempted", "reason_code": "abn_not_discovered"}
            continue
        if not abr_approved:
            candidate["abr_evidence"] = {"state": "blocked", "reason_code": "source_terms_not_approved"}
            continue
        if not allow_network:
            candidate["abr_evidence"] = {"state": "blocked", "reason_code": "provider_network_not_authorised"}
            continue
        result = await abr.lookup(abn)
        candidate["abr_evidence"] = {
            "state": result.get("state"),
            "reason_code": result.get("reason_code") or "",
            "status": "active" if result.get("abn_verified") else "unverified",
            "retrieved_at": (result.get("data") or {}).get("retrieved_at") or "",
            "record": result.get("data") or {},
        }
        provider_states.append({"provider": "abr_web_services", "scope": abn, "state": result.get("state"), "reason_code": result.get("reason_code")})

    blocked = [row for row in provider_states if row.get("state") != "complete" and row.get("state") != "active" and row.get("state") != "cached"]
    return {
        "ok": not blocked,
        "mode": "provider_dry_run",
        "network_authorised": bool(allow_network),
        "candidates": candidates,
        "provider_states": provider_states,
        "blocked": blocked,
        "publication_allowed": False,
    }
