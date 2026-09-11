"""Entity Deduplication, Canonicalization and Delisting Suppression Engine.

Matches multi-source public listings on:
1. Canonical ABN (100% confidence match)
2. Normalized Phone (Australian E.164 format)
3. Normalized Website Domain
4. Normalised Business Name + Suburb
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    from .abn_validator import normalize_abn
except ImportError:
    from abn_validator import normalize_abn


def normalize_phone_au(raw_phone: Optional[str]) -> str:
    """Normalize Australian phone numbers into E.164 (+61...) or standard 10-digit format."""
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", str(raw_phone).strip())
    if not digits:
        return ""

    # Convert 04xx xxx xxx to +614...
    if digits.startswith("0") and len(digits) == 10:
        return f"+61{digits[1:]}"
    # If already 614...
    if digits.startswith("61") and len(digits) == 11:
        return f"+{digits}"
    # Return stripped digits if international or local 8-digit
    return digits


def normalize_domain(raw_url: Optional[str]) -> str:
    """Extract clean lowercase domain without www, protocol, or path."""
    if not raw_url:
        return ""
    url = str(raw_url).strip().lower()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or ""
        netloc = re.sub(r"^www\.", "", netloc)
        return netloc.split(":")[0]  # strip port if any
    except Exception:
        return ""


def normalize_business_name(raw_name: Optional[str]) -> str:
    """Normalize business name by removing legal entity suffixes and punctuation."""
    if not raw_name:
        return ""
    name = str(raw_name).strip().lower()
    # Remove common legal suffixes
    name = re.sub(r"\b(pty|ltd|limited|proprietary|inc|incorporated|llc)\b", "", name)
    # Remove punctuation & extra whitespace
    name = re.sub(r"[^\w\s]", " ", name)
    return " ".join(name.split())


class DeduplicationEngine:
    """Matches and merges incoming candidate listings into canonical trainer records."""

    def __init__(self, delisted_entities: Optional[List[Dict[str, Any]]] = None):
        # In-memory suppression list for opted-out trainers
        self.delisted_entities: List[Dict[str, Any]] = delisted_entities or []

    def is_delisted(self, candidate: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if an entity is in the delisted suppression list."""
        cand_abn = normalize_abn(candidate.get("abn"))
        cand_phone = normalize_phone_au(candidate.get("phone"))
        cand_domain = normalize_domain(candidate.get("website"))

        for delist in self.delisted_entities:
            d_abn = normalize_abn(delist.get("abn"))
            d_phone = normalize_phone_au(delist.get("phone"))
            d_domain = normalize_domain(delist.get("website"))

            if cand_abn and d_abn and cand_abn == d_abn:
                return True, f"ABN {cand_abn} is on the delisted suppression list (opted out)."
            if cand_phone and d_phone and cand_phone == d_phone:
                return True, f"Phone {cand_phone} is on the delisted suppression list."
            if cand_domain and d_domain and cand_domain == d_domain:
                return True, f"Domain {cand_domain} is on the delisted suppression list."

        return False, ""

    def find_match(
        self, candidate: Dict[str, Any], existing_trainers: List[Dict[str, Any]]
    ) -> Optional[Tuple[Dict[str, Any], str]]:
        """Find an existing canonical record that matches the candidate listing."""
        cand_abn = normalize_abn(candidate.get("abn"))
        cand_phone = normalize_phone_au(candidate.get("phone"))
        cand_domain = normalize_domain(candidate.get("website"))
        cand_name = normalize_business_name(candidate.get("name"))
        cand_suburb = str(candidate.get("suburb") or "").strip().lower()

        # Match Strategy 1: Canonical ABN (100% confidence)
        if cand_abn:
            for t in existing_trainers:
                t_abn = normalize_abn(t.get("abn"))
                if t_abn and t_abn == cand_abn:
                    return t, "ABN_MATCH"

        # Match Strategy 2: Phone number match
        if cand_phone:
            for t in existing_trainers:
                t_phone = normalize_phone_au(t.get("phone"))
                if t_phone and t_phone == cand_phone:
                    return t, "PHONE_MATCH"

        # Match Strategy 3: Website domain match
        if cand_domain:
            for t in existing_trainers:
                t_domain = normalize_domain(t.get("website"))
                if t_domain and t_domain == cand_domain:
                    return t, "DOMAIN_MATCH"

        # Match Strategy 4: Exact normalized name + Suburb match
        if cand_name and cand_suburb:
            for t in existing_trainers:
                t_name = normalize_business_name(t.get("name"))
                t_suburb = str(t.get("suburb") or "").strip().lower()
                if t_name and t_name == cand_name and t_suburb == cand_suburb:
                    return t, "NAME_SUBURB_MATCH"

        return None

    def merge_records(
        self, canonical: Dict[str, Any], incoming: Dict[str, Any], match_reason: str
    ) -> Dict[str, Any]:
        """Merge new information from incoming source into existing canonical record."""
        merged = dict(canonical)

        # Merge ABN if not previously set
        if not merged.get("abn") and incoming.get("abn"):
            merged["abn"] = incoming["abn"]

        # Merge Phone
        if not merged.get("phone") and incoming.get("phone"):
            merged["phone"] = incoming["phone"]

        # Merge Website
        if not merged.get("website") and incoming.get("website"):
            merged["website"] = incoming["website"]

        # Merge Email
        if not merged.get("email") and incoming.get("email"):
            merged["email"] = incoming["email"]

        # Merge Suburb
        if not merged.get("suburb") and incoming.get("suburb"):
            merged["suburb"] = incoming["suburb"]

        # Merge Services list (deduplicated)
        merged_services = list(merged.get("services") or [])
        for s in incoming.get("services") or []:
            if s not in merged_services:
                merged_services.append(s)
        merged["services"] = merged_services

        # Merge Categories list (deduplicated)
        merged_categories = list(merged.get("categories") or [])
        for c in incoming.get("categories") or []:
            if c not in merged_categories:
                merged_categories.append(c)
        merged["categories"] = merged_categories

        # Merge Photo Gallery
        merged_gallery = list(merged.get("gallery_images") or [])
        for img in incoming.get("gallery_images") or []:
            if img not in merged_gallery:
                merged_gallery.append(img)
        merged["gallery_images"] = merged_gallery

        # Append source evidence history
        evidence_sources = list(merged.get("evidence_sources") or [])
        new_source = incoming.get("source_evidence_url") or incoming.get("website")
        if new_source and new_source not in evidence_sources:
            evidence_sources.append(new_source)
        merged["evidence_sources"] = evidence_sources

        # Record merge metadata
        merge_log = list(merged.get("merge_log") or [])
        merge_log.append({
            "matched_by": match_reason,
            "merged_source": incoming.get("source_name") or incoming.get("source_evidence_url") or "external_ingestion",
        })
        merged["merge_log"] = merge_log

        return merged
