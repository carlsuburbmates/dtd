"""Canonical Melbourne suburb catalogue loading and API fallback support."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple


CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "data" / "dtd_melbourne_suburbs.v1.json"
CATALOGUE_VERSION = "v1"
EXPECTED_SUBURB_COUNT = 539
REQUIRED_FIELDS = {
    "slug",
    "suburb_name",
    "postcodes",
    "lat",
    "lng",
    "region_cluster",
    "lga",
}


@lru_cache(maxsize=1)
def load_catalogue() -> Dict[str, Any]:
    """Load and fail closed on structural drift in the approved v1 asset."""

    payload = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    suburbs = payload.get("suburbs")
    meta = payload.get("meta")
    if not isinstance(meta, dict) or not isinstance(suburbs, list):
        raise ValueError("canonical suburb catalogue must contain meta and suburbs")
    if len(suburbs) != EXPECTED_SUBURB_COUNT or meta.get("total_suburbs") != EXPECTED_SUBURB_COUNT:
        raise ValueError(
            f"canonical suburb catalogue must contain exactly {EXPECTED_SUBURB_COUNT} suburbs"
        )

    slugs = set()
    for row in suburbs:
        if not isinstance(row, dict) or not REQUIRED_FIELDS.issubset(row):
            raise ValueError("canonical suburb catalogue contains an invalid row")
        slug = str(row.get("slug") or "").strip()
        if not slug or slug in slugs:
            raise ValueError(f"canonical suburb catalogue contains duplicate or empty slug: {slug!r}")
        slugs.add(slug)
    return payload


def canonical_suburbs() -> List[Dict[str, Any]]:
    return [dict(row) for row in load_catalogue()["suburbs"]]


def canonical_suburb_names() -> List[str]:
    return sorted(str(row["suburb_name"]) for row in load_catalogue()["suburbs"])


async def config_suburb_names(db: Any) -> Tuple[List[str], str]:
    """Read the seeded collection, falling back to the versioned asset.

    The API must never regress to deriving the canonical geography from the
    currently published trainer sample. A missing, unavailable, or partially
    seeded collection therefore fails soft to the approved static catalogue.
    """

    collection = getattr(db, "suburbs", None)
    if collection is not None and hasattr(collection, "find"):
        try:
            canonical_names = canonical_suburb_names()
            rows = await collection.find(
                {
                    "active": {"$ne": False},
                    "catalogue_version": CATALOGUE_VERSION,
                },
                {"_id": 0, "suburb_name": 1},
            ).sort("suburb_name", 1).to_list(EXPECTED_SUBURB_COUNT + 1)
            names = sorted(
                {
                    str(row.get("suburb_name") or "").strip()
                    for row in rows
                    if str(row.get("suburb_name") or "").strip()
                }
            )
            if names == canonical_names:
                return names, "database"
        except Exception:
            pass
    return canonical_suburb_names(), "static_catalogue_fallback"
