"""Bounded Australian Business Register lookups with Mongo-backed caching."""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests

from .abn_validator import format_abn, normalize_abn, validate_abn_checksum


ABR_ENDPOINT = "https://abr.business.gov.au/json/AbnDetails.aspx"
ABR_NAME_ENDPOINT = "https://abr.business.gov.au/json/MatchingNames.aspx"
ABR_CACHE_TTL_S = 30 * 24 * 60 * 60


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _parse_payload(raw_text: str) -> Optional[Dict[str, Any]]:
    raw = (raw_text or "").strip()
    wrapped = re.match(r"^[A-Za-z0-9_]+\s*\((.*)\)\s*;?$", raw, flags=re.DOTALL)
    try:
        return json.loads(wrapped.group(1) if wrapped else raw)
    except (AttributeError, json.JSONDecodeError):
        return None


def _normalise_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    abn = normalize_abn(payload.get("Abn"))
    business_names = payload.get("BusinessName") or []
    if isinstance(business_names, str):
        business_names = [business_names]
    clean_business_names = [str(name).strip() for name in business_names if str(name).strip()]
    entity_name = str(payload.get("EntityName") or "").strip()
    trading_name = clean_business_names[0] if clean_business_names else entity_name
    entity_type_name = str(payload.get("EntityTypeName") or "").strip()
    return {
        "abn": abn,
        "abn_formatted": format_abn(abn),
        "abn_status": str(payload.get("AbnStatus") or "Unknown").strip(),
        "abn_status_effective_from": str(payload.get("AbnStatusEffectiveFrom") or "").strip(),
        "entity_name": entity_name,
        "trading_name": trading_name,
        "business_names": clean_business_names,
        "entity_type_name": entity_type_name,
        "business_type": entity_type_name,
        "address_state": str(payload.get("AddressState") or "").strip().upper(),
        "address_postcode": str(payload.get("AddressPostcode") or "").strip(),
        "gst_status": str(payload.get("Gst") or "").strip(),
        "is_active": str(payload.get("AbnStatus") or "").strip().lower() == "active",
        "retrieved_at": now_iso(),
    }


class AbrClient:
    def __init__(self, db, *, guid: Optional[str] = None, ttl_s: int = ABR_CACHE_TTL_S) -> None:
        self.db = db
        self.guid = (guid if guid is not None else os.environ.get("ABR_GUID", "")).strip()
        self.ttl_s = ttl_s

    async def lookup(self, raw_abn: str) -> Dict[str, Any]:
        abn = normalize_abn(raw_abn)
        if not validate_abn_checksum(abn):
            return {
                "ok": False,
                "state": "invalid_checksum",
                "reason_code": "invalid_checksum",
                "abn": abn,
                "reason": "ABN checksum failed.",
                "abn_verified": False,
            }

        cached = await self.db.abn_cache.find_one({"abn": abn}, {"_id": 0}) if self.db is not None else None
        cached_at = _parse_iso((cached or {}).get("cached_at"))
        if cached and cached_at and cached_at + timedelta(seconds=self.ttl_s) > datetime.now(timezone.utc):
            record = cached.get("record") or {}
            return {
                "ok": True,
                "state": "cached",
                "data": record,
                "cached": True,
                "abn_verified": bool(record.get("is_active")),
            }

        if not self.guid:
            return {
                "ok": False,
                "state": "abr_unavailable",
                "reason_code": "abr_guid_missing",
                "abn": abn,
                "reason": "ABR_GUID is not configured.",
                "abn_verified": False,
            }

        try:
            response = await asyncio.to_thread(
                requests.get,
                ABR_ENDPOINT,
                params={"abn": abn, "guid": self.guid},
                timeout=10,
            )
            if not 200 <= response.status_code < 300:
                reason_code = "abr_maintenance" if response.status_code in {502, 503, 504} else "abr_unavailable"
                return {
                    "ok": False,
                    "state": "abr_unavailable",
                    "reason_code": reason_code,
                    "abn": abn,
                    "reason": f"ABR returned HTTP {response.status_code}.",
                    "abn_verified": False,
                }
            payload = _parse_payload(response.text)
        except requests.RequestException as exc:
            return {
                "ok": False,
                "state": "abr_unavailable",
                "reason_code": "abr_network_error",
                "abn": abn,
                "reason": f"ABR request failed: {type(exc).__name__}.",
                "abn_verified": False,
            }

        if not payload:
            return {
                "ok": False,
                "state": "abr_unavailable",
                "reason_code": "abr_unreadable",
                "abn": abn,
                "reason": "ABR returned an unreadable response.",
                "abn_verified": False,
            }
        message = str(payload.get("Message") or "")
        if "no record" in message.lower():
            return {
                "ok": False,
                "state": "abr_not_found",
                "reason_code": "abr_not_found",
                "abn": abn,
                "reason": message,
                "abn_verified": False,
            }
        record = _normalise_record(payload)
        if not record["abn"]:
            return {
                "ok": False,
                "state": "abr_unavailable",
                "reason_code": "abr_missing_abn",
                "abn": abn,
                "reason": message or "ABR record did not contain an ABN.",
                "abn_verified": False,
            }
        now_dt = datetime.now(timezone.utc)
        expires_at_dt = now_dt + timedelta(seconds=self.ttl_s)
        if self.db is not None:
            await self.db.abn_cache.update_one(
                {"abn": abn},
                {
                    "$set": {
                        "abn": abn,
                        "record": record,
                        "cached_at": now_dt.isoformat(),
                        "expires_at": expires_at_dt,
                    }
                },
                upsert=True,
            )
        return {
            "ok": True,
            "state": "active" if record["is_active"] else "inactive",
            "data": record,
            "cached": False,
            "abn_verified": bool(record["is_active"]),
        }

    async def search_names(self, name: str, *, max_results: int = 10) -> Dict[str, Any]:
        clean_name = " ".join(str(name or "").split())
        if not clean_name:
            return {"ok": False, "state": "invalid", "reason_code": "name_required", "matches": []}
        if not self.guid:
            return {"ok": False, "state": "abr_unavailable", "reason_code": "abr_guid_missing", "matches": []}

        try:
            response = await asyncio.to_thread(
                requests.get,
                ABR_NAME_ENDPOINT,
                params={"name": clean_name, "maxResults": max(1, min(int(max_results), 20)), "guid": self.guid},
                timeout=10,
            )
            if not 200 <= response.status_code < 300:
                return {"ok": False, "state": "abr_unavailable", "reason_code": f"abr_http_{response.status_code}", "matches": []}
            payload = _parse_payload(response.text)
        except (requests.RequestException, ValueError, TypeError):
            return {"ok": False, "state": "abr_unavailable", "reason_code": "abr_network_error", "matches": []}

        if not payload:
            return {"ok": False, "state": "abr_unavailable", "reason_code": "abr_unreadable", "matches": []}
        matches = []
        for row in payload.get("Names") or []:
            abn = normalize_abn(row.get("Abn"))
            if not abn:
                continue
            current_value = row.get("IsCurrent")
            is_current = current_value if isinstance(current_value, bool) else str(current_value or "").strip().upper() in {"Y", "YES", "TRUE", "1"}
            matches.append(
                {
                    "abn": abn,
                    "abn_formatted": format_abn(abn),
                    "name": str(row.get("Name") or "").strip(),
                    "name_type": str(row.get("NameType") or "").strip(),
                    "state": str(row.get("State") or "").strip().upper(),
                    "postcode": str(row.get("Postcode") or "").strip(),
                    "score": str(row.get("Score") or "").strip(),
                    "is_current": is_current,
                }
            )
        return {"ok": True, "state": "complete", "reason_code": "", "matches": matches}
