"""Fail-closed legacy Google Places probe; not a listing-acquisition adapter."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


PLACES_TEXT_SEARCH_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
PLACES_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.rating",
        "places.userRatingCount",
        "places.businessStatus",
        "places.primaryType",
    ]
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlacesClient:
    def __init__(self, *, api_key: Optional[str] = None, transport=requests) -> None:
        self.api_key = (api_key if api_key is not None else os.environ.get("GOOGLE_PLACES_API_KEY", "")).strip()
        self.transport = transport

    async def search_trainers(self, suburb: str, *, approved: bool, allow_network: bool) -> Dict[str, Any]:
        suburb = " ".join(str(suburb or "").split())
        if not approved:
            return {"ok": False, "state": "blocked", "reason_code": "source_terms_not_approved", "candidates": []}
        if not self.api_key:
            return {"ok": False, "state": "blocked", "reason_code": "google_places_key_missing", "candidates": []}
        if not allow_network:
            return {"ok": False, "state": "blocked", "reason_code": "provider_network_not_authorised", "candidates": []}
        if not suburb:
            return {"ok": False, "state": "invalid", "reason_code": "suburb_required", "candidates": []}

        def request() -> Any:
            return self.transport.post(
                PLACES_TEXT_SEARCH_ENDPOINT,
                json={"textQuery": f"dog trainer in {suburb}, VIC, Australia", "pageSize": 20, "includePureServiceAreaBusinesses": True},
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": PLACES_FIELD_MASK,
                },
                timeout=15,
            )

        try:
            response = await asyncio.to_thread(request)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            return {"ok": False, "state": "degraded", "reason_code": f"google_places_{type(exc).__name__.lower()}", "candidates": []}

        candidates: List[Dict[str, Any]] = []
        retrieved_at = now_iso()
        for place in payload.get("places") or []:
            place_id = str(place.get("id") or "").strip()
            name = str((place.get("displayName") or {}).get("text") or "").strip()
            if not place_id or not name:
                continue
            location = place.get("location") or {}
            candidates.append(
                {
                    "provider": "google_places",
                    "provider_record_id": place_id,
                    "name": name,
                    "suburb": suburb,
                    "address": str(place.get("formattedAddress") or ""),
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "phone": str(place.get("nationalPhoneNumber") or ""),
                    "website": str(place.get("websiteUri") or ""),
                    "review_rating": place.get("rating"),
                    "review_count": place.get("userRatingCount"),
                    "business_status": str(place.get("businessStatus") or ""),
                    "source_type": "commercial_register",
                    "source_url": f"https://places.google.com/?q=place_id:{place_id}",
                    "retrieved_at": retrieved_at,
                    "raw_evidence": {
                        "source_url": f"https://places.google.com/?q=place_id:{place_id}",
                        "provider_record_id": place_id,
                        "matched_name": name,
                        "matched_suburb": suburb,
                        "matched_phone": str(place.get("nationalPhoneNumber") or ""),
                        "matched_website": str(place.get("websiteUri") or ""),
                        "formatted_address": str(place.get("formattedAddress") or ""),
                    },
                }
            )
        return {"ok": True, "state": "complete", "reason_code": "", "candidates": candidates, "next_page_token": str(payload.get("nextPageToken") or "")}
