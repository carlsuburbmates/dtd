"""Canonical identity and delisting checks for lawful trainer ingestion."""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def normalize_abn(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def normalize_phone(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("61") and len(digits) >= 10:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+61{digits[1:]}"
    return f"+{digits}" if digits else ""


def normalize_domain(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    return re.sub(r"^www\.", "", (parsed.hostname or "").lower())


def normalize_name(value: Any) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())


def identity(candidate: Dict[str, Any]) -> Dict[str, str]:
    return {
        "abn": normalize_abn(candidate.get("abn")),
        "normalized_phone": normalize_phone(candidate.get("phone")),
        "website_domain": normalize_domain(candidate.get("website") or candidate.get("source_url")),
        "normalized_name": normalize_name(candidate.get("name")),
    }


async def suppression_match(db: Any, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    coll = getattr(db, "delisted_entities", None)
    if coll is None:
        return None
    keys = identity(candidate)
    clauses = [{key: value} for key, value in keys.items() if value and key != "normalized_name"]
    if not clauses:
        return None
    return await coll.find_one({"$or": clauses}, {"_id": 0})


def _distance_km(a: Dict[str, Any], b: Dict[str, Any]) -> Optional[float]:
    try:
        lat1, lon1 = float(a.get("latitude")), float(a.get("longitude"))
        lat2, lon2 = float(b.get("latitude")), float(b.get("longitude"))
    except (TypeError, ValueError):
        return None
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def fuzzy_local_match(candidate: Dict[str, Any], existing: Dict[str, Any]) -> bool:
    left, right = normalize_name(candidate.get("name")), normalize_name(existing.get("name"))
    if not left or not right or SequenceMatcher(None, left, right).ratio() <= 0.90:
        return False
    distance = _distance_km(candidate, existing)
    if distance is not None:
        return distance <= 5
    return normalize_name(candidate.get("suburb")) == normalize_name(existing.get("suburb"))
