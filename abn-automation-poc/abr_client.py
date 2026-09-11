"""Australian Business Register (ABR) Web Services API Client.

Features:
- Official ABR JSON Web Service integration (abr.business.gov.au).
- Uses Python standard library (urllib.request) for zero-dependency portability.
- Handles JSONP/callback wrapper parsing returned by ABR.
- 30-day cache with TTL to prevent redundant network requests and respect government rate limits.
- Built-in mock mode with realistic test fixtures for offline/isolated testing.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.parse

try:
    from .abn_validator import normalize_abn, validate_abn_checksum, format_abn
except ImportError:
    from abn_validator import normalize_abn, validate_abn_checksum, format_abn

logger = logging.getLogger("dtd.abr_client")

ABR_JSON_ENDPOINT = "https://abr.business.gov.au/json/AbnDetails.aspx"
DEFAULT_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days

# Mock fixtures for offline testing without a live ABR GUID
MOCK_ABR_DATABASE: Dict[str, Dict[str, Any]] = {
    # 51824753556 - Real test ABN (RSPCA Victoria)
    "51824753556": {
        "abn": "51824753556",
        "abn_status": "Active",
        "abn_status_effective_from": "2000-05-01",
        "entity_name": "ROYAL SOCIETY FOR THE PREVENTION OF CRUELTY TO ANIMALS (VICTORIA)",
        "business_names": ["RSPCA VICTORIA", "RSPCA DOG TRAINING ACADEMY"],
        "entity_type_name": "Other Incorporated Entity",
        "address_state": "VIC",
        "address_postcode": "3131",
        "gst_status": "Active",
    },
    # 10000000032 - Mock Active Melbourne Dog Trainer (Sole Trader)
    "10000000032": {
        "abn": "10000000032",
        "abn_status": "Active",
        "abn_status_effective_from": "2018-03-15",
        "entity_name": "SMITH, JANE ELIZABETH",
        "business_names": ["MELBOURNE K9 BALANCE", "K9 REHABILITATION RICHMOND"],
        "entity_type_name": "Individual/Sole Trader",
        "address_state": "VIC",
        "address_postcode": "3121",
        "gst_status": "Active",
    },
    # 10000000064 - Mock Active Melbourne Dog Training Pty Ltd
    "10000000064": {
        "abn": "10000000064",
        "abn_status": "Active",
        "abn_status_effective_from": "2020-07-01",
        "entity_name": "POSITIVE K9 TRAINING PTY LTD",
        "business_names": ["POSITIVE K9 MELBOURNE", "EASTERN SUBURBS K9"],
        "entity_type_name": "Australian Private Company",
        "address_state": "VIC",
        "address_postcode": "3122",
        "gst_status": "Active",
    },
    # 10000000096 - Mock Cancelled ABN (Deregistered Business)
    "10000000096": {
        "abn": "10000000096",
        "abn_status": "Cancelled",
        "abn_status_effective_from": "2015-01-01",
        "entity_name": "DEREGISTERED PET TRAINING PTY LTD",
        "business_names": ["OLD DOG TRAINING CO"],
        "entity_type_name": "Australian Private Company",
        "address_state": "VIC",
        "address_postcode": "3000",
        "gst_status": "Cancelled",
    },
    # 48123123124 - Mock Interstate (NSW) Dog Trainer (Commonwealth Bank ABN test pattern)
    "48123123124": {
        "abn": "48123123124",
        "abn_status": "Active",
        "abn_status_effective_from": "2019-06-10",
        "entity_name": "SYDNEY CANINE COACHING",
        "business_names": ["SYDNEY DOGS"],
        "entity_type_name": "Individual/Sole Trader",
        "address_state": "NSW",
        "address_postcode": "2000",
        "gst_status": "Active",
    },
}


class AbrClient:
    """Standard-library based client for ABR Web Services."""

    def __init__(
        self,
        guid: Optional[str] = None,
        cache_file: Optional[Path] = None,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        use_mock_fallback: bool = True,
    ):
        self.guid = (guid or os.environ.get("ABR_GUID") or os.environ.get("ABR_GUID_KEY") or "").strip()
        self.cache_file = cache_file
        self.ttl_seconds = ttl_seconds
        self.use_mock_fallback = use_mock_fallback
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file and self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                self._memory_cache = data
            except Exception as e:
                logger.warning("Failed to load ABR cache from %s: %s", self.cache_file, e)

    def _save_cache(self) -> None:
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                self.cache_file.write_text(json.dumps(self._memory_cache, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning("Failed to save ABR cache to %s: %s", self.cache_file, e)

    def _parse_abr_response(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from ABR callback wrapper, e.g. callback({"Abn": "..."})."""
        text = raw_text.strip()
        # Strip callback(...) if present
        match = re.search(r"^[a-zA-Z0-9_]+\s*\((.*)\)\s*;?$", text, re.DOTALL)
        json_str = match.group(1) if match else text

        try:
            payload = json.loads(json_str)
        except Exception:
            return None

        # Check for ABR error messages
        message = payload.get("Message") or ""
        if "No record found" in message or "Search limit exceeded" in message:
            return {"error": message, "raw": payload}

        # Normalize ABR JSON schema into clean DTD schema
        abn_val = normalize_abn(payload.get("Abn"))
        if not abn_val:
            return {"error": "Missing ABN in response", "raw": payload}

        # Extract business names
        business_names: List[str] = []
        raw_bnames = payload.get("BusinessName") or []
        if isinstance(raw_bnames, list):
            business_names = [str(n).strip() for n in raw_bnames if str(n).strip()]
        elif isinstance(raw_bnames, str) and raw_bnames.strip():
            business_names = [raw_bnames.strip()]

        return {
            "abn": abn_val,
            "abn_formatted": format_abn(abn_val),
            "abn_status": str(payload.get("AbnStatus") or "").strip() or "Unknown",
            "abn_status_effective_from": str(payload.get("AbnStatusEffectiveFrom") or "").strip(),
            "entity_name": str(payload.get("EntityName") or "").strip(),
            "business_names": business_names,
            "entity_type_name": str(payload.get("EntityTypeName") or "").strip(),
            "address_state": str(payload.get("AddressState") or "").strip().upper(),
            "address_postcode": str(payload.get("AddressPostcode") or "").strip(),
            "gst_status": str(payload.get("Gst") or "").strip() or "Not registered",
            "source": "live_abr_api",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "is_active": (str(payload.get("AbnStatus") or "").strip().lower() == "active"),
            "is_victoria": (str(payload.get("AddressState") or "").strip().upper() == "VIC"),
        }

    def lookup_abn(self, raw_abn: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Lookup an ABN against cache, live ABR API, or mock fallback."""
        norm = normalize_abn(raw_abn)
        if not validate_abn_checksum(norm):
            return {
                "success": False,
                "error_code": "INVALID_CHECKSUM",
                "message": f"ABN '{raw_abn}' is not a mathematically valid Australian Business Number.",
                "abn": norm,
            }

        # Check Cache
        now_ts = time.time()
        if not force_refresh and norm in self._memory_cache:
            entry = self._memory_cache[norm]
            cached_at = entry.get("_cached_at_ts", 0)
            if now_ts - cached_at < self.ttl_seconds:
                res = dict(entry)
                res["cached"] = True
                res["source"] = "cache"
                return {"success": True, "data": res}

        # Live ABR API Call
        if self.guid:
            try:
                query_params = urllib.parse.urlencode({"abn": norm, "guid": self.guid})
                url = f"{ABR_JSON_ENDPOINT}?{query_params}"
                req = urllib.request.Request(url, headers={"User-Agent": "DTD-ABN-Validator/1.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw_text = response.read().decode("utf-8")
                    parsed = self._parse_abr_response(raw_text)
                    if parsed and "error" not in parsed:
                        parsed["_cached_at_ts"] = now_ts
                        parsed["cached"] = False
                        self._memory_cache[norm] = parsed
                        self._save_cache()
                        return {"success": True, "data": parsed}
                    elif parsed and "error" in parsed:
                        return {
                            "success": False,
                            "error_code": "ABR_RECORD_NOT_FOUND",
                            "message": parsed.get("error"),
                            "abn": norm,
                        }
            except Exception as exc:
                logger.error("ABR live API error for ABN %s: %s", norm, exc)
                if not self.use_mock_fallback:
                    return {
                        "success": False,
                        "error_code": "NETWORK_ERROR",
                        "message": f"Failed to connect to ABR Web Services: {exc}",
                        "abn": norm,
                    }

        # Mock Fallback for local development / testing without GUID
        if self.use_mock_fallback and norm in MOCK_ABR_DATABASE:
            mock_data = dict(MOCK_ABR_DATABASE[norm])
            mock_data["abn_formatted"] = format_abn(norm)
            mock_data["source"] = "mock_database"
            mock_data["cached"] = False
            mock_data["retrieved_at"] = datetime.now(timezone.utc).isoformat()
            mock_data["is_active"] = (mock_data.get("abn_status") == "Active")
            mock_data["is_victoria"] = (mock_data.get("address_state") == "VIC")
            mock_data["_cached_at_ts"] = now_ts
            self._memory_cache[norm] = mock_data
            self._save_cache()
            return {"success": True, "data": mock_data}

        return {
            "success": False,
            "error_code": "NO_RECORD_FOUND",
            "message": f"No active business entity record found on the ABR for ABN {norm}.",
            "abn": norm,
        }
