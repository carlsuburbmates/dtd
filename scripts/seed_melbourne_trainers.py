#!/usr/bin/env python3
"""Lawful Greater Melbourne supply seeding and candidate ingestion script.

Implements Task 4 supply seeding criteria:
- Fails closed on malformed candidates and invalid source URLs.
- Deduplicates via 4-tier canonical matching (ABN -> domain -> phone -> name+suburb).
- Strictly preserves existing claimed/upgraded profiles on repeat runs.
- Guarantees idempotent application (0 duplicates on repeat runs).
- Never presents a profile as verified unless ABR verification succeeded.
- Logs ingestion failures to `db.source_ingestion_state` for `/ops` visibility.
- Provides `--dry-run` and `--apply` CLI modes.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Ensure backend directory is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from services.abn_validator import (  # type: ignore
        format_abn,
        normalize_abn,
        validate_abn_detailed,
    )
    from services import deduplication  # type: ignore
except ImportError:
    # Fallback inline if executing in an environment where services is differently located
    def normalize_abn(raw: Optional[str]) -> str:
        return re.sub(r"\D", "", str(raw or "").strip())

    def format_abn(raw: Optional[str]) -> str:
        abn = normalize_abn(raw)
        return f"{abn[:2]} {abn[2:5]} {abn[5:8]} {abn[8:]}" if len(abn) == 11 else abn

    def validate_abn_detailed(raw: Optional[str]) -> Dict[str, Any]:
        abn = normalize_abn(raw)
        if not abn:
            return {"valid": False, "code": "empty", "abn": abn, "formatted": abn}
        if len(abn) != 11:
            return {"valid": False, "code": "invalid_length", "abn": abn, "formatted": abn}
        digits = [int(d) for d in abn]
        digits[0] -= 1
        weights = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
        valid = sum(d * w for d, w in zip(digits, weights)) % 89 == 0
        return {"valid": valid, "code": "valid" if valid else "checksum_failed", "abn": abn, "formatted": format_abn(abn)}

    deduplication = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("seed_melbourne_trainers")

DEFAULT_SEED_FILE = BACKEND_DIR / "data" / "melbourne_trainers_seed.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_domain(url: Optional[str]) -> str:
    """Extract clean domain hostname from a URL."""
    raw = (url or "").strip().lower()
    if not raw:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = f"https://{raw}"
    try:
        parsed = urlparse(raw)
        host = parsed.netloc or parsed.path.split("/")[0]
        host = host.split(":")[0]  # strip port
        return re.sub(r"^www\.", "", host)
    except Exception:
        return ""


def check_dns_resolvable(domain: str) -> Tuple[bool, str]:
    """Check if domain resolves via DNS."""
    clean_domain = (domain or "").strip().lower()
    if not clean_domain:
        return False, "empty_domain"
    import socket
    try:
        socket.gethostbyname(clean_domain)
        return True, "resolved"
    except Exception as exc:
        return False, f"unresolved_dns:{exc}"


def check_source_reachability(url: str, timeout: float = 3.0) -> Tuple[bool, str]:
    """Check if source URL resolves via DNS and responds via HTTP/HTTPS."""
    domain = extract_domain(url)
    dns_ok, dns_msg = check_dns_resolvable(domain)
    if not dns_ok:
        return False, dns_msg
    import urllib.request
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "DTD-Source-Verification/1.0"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status >= 400:
                return False, f"http_error_{resp.status}"
            return True, f"http_ok_{resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"http_error_{exc.code}"
    except Exception as exc:
        return False, f"reachability_error:{exc}"


GENERIC_NAME_STOPWORDS = {
    "the", "and", "dog", "dogs", "puppy", "puppies", "training", "trainer", "trainers",
    "k9", "canine", "melbourne", "australia", "vic", "academy", "school", "services",
    "co", "pty", "ltd", "group", "club", "centre", "center", "hub",
}


def validate_iso8601_utc(ts: Any) -> Tuple[bool, str]:
    """Validate that timestamp is a non-empty ISO-8601 string with UTC timezone."""
    if not isinstance(ts, str) or not ts.strip():
        return False, "missing_retrieved_at"
    raw = ts.strip()
    # Must explicitly specify UTC (ends with 'Z' or '+00:00' or '+0000')
    if not (raw.endswith("Z") or raw.endswith("+00:00") or raw.endswith("+0000")):
        return False, "malformed_retrieved_at_must_be_iso8601_utc"
    try:
        dt_str = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            return False, "malformed_retrieved_at_missing_tz"
        if dt.utcoffset() != timezone.utc.utcoffset(None):
            return False, "malformed_retrieved_at_must_be_iso8601_utc"
        return True, "valid"
    except Exception as exc:
        return False, f"malformed_retrieved_at:{exc}"


def normalize_source_url(u: str) -> str:
    """Normalize URL for provenance comparison."""
    raw = (u or "").strip().rstrip("/")
    if not raw:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = f"https://{raw}"
    try:
        parsed = urlparse(raw)
        host = (parsed.netloc or "").lower()
        path = parsed.path.rstrip("/").lower()
        return f"{parsed.scheme.lower()}://{host}{path}"
    except Exception:
        return raw.lower()


def _flatten_evidence_strings(obj: Any) -> List[str]:
    """Recursively collect all strings from evidence object."""
    strings: List[str] = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, (int, float)):
        strings.append(str(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            strings.extend(_flatten_evidence_strings(v))
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            strings.extend(_flatten_evidence_strings(item))
    return strings


SUPPORTED_SOURCE_TYPES = {"business_website", "public_directory", "government_registry", "commercial_register"}
PLACEHOLDER_NAMES = {"unnamed", "unknown", "placeholder", "fake", "test", "demo", "sample", "example"}
PLACEHOLDER_DOMAINS = {"example.com", "example.org", "test.local", "localhost", "invalid-domain.local", "malformed.local"}
PLACEHOLDER_PHONES = {"0400000000", "0411111111", "0412345678", "0390000000", "12345678", "00000000"}


def validate_candidate_schema(cand: Dict[str, Any], *, verify_live_reachability: bool = False) -> Tuple[bool, str]:
    """Validate that candidate conforms to the lawful candidate schema.

    Enforces fail-closed rules without requiring live network calls:
    1. Non-placeholder name and suburb.
    2. Valid, supported primary source URL (http/https) and supported source type.
    3. Retrieved_at is required and must validate as an ISO-8601 UTC timestamp.
    4. Non-placeholder domain, phone, email if supplied.
    5. Non-empty raw_evidence identifying the EXACT same source URL as candidate.
    6. Does NOT treat caller-supplied source_validation_status string as proof.
    7. Explicit evidence tying business name and EVERY supplied public field
       (website, phone, email, suburb, ABN, services) to the recorded source.
       Omitted public fields do not need evidence.
    8. Rejects records where evidence is absent, mismatched, stale/malformed,
       or only asserts a generic name match.
    9. Optional live network reachability check (disabled by default).
    """
    if not isinstance(cand, dict):
        return False, "candidate_not_an_object"
    name = str(cand.get("name") or "").strip()
    if not name:
        return False, "missing_name"
    if any(ph in name.lower() for ph in PLACEHOLDER_NAMES):
        return False, "placeholder_name_rejected"

    suburb = str(cand.get("suburb") or "").strip()
    if not suburb:
        return False, "missing_suburb"

    source_type = str(cand.get("source_type") or "").strip()
    if source_type not in SUPPORTED_SOURCE_TYPES:
        return False, f"unsupported_source_type:{source_type or 'missing'}"

    source_url = str(cand.get("source_url") or "").strip()
    if not source_url:
        return False, "missing_source_url"

    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, f"invalid_source_url_scheme:{parsed.scheme or 'none'}"

    src_domain = extract_domain(source_url)
    if src_domain in PLACEHOLDER_DOMAINS:
        return False, f"placeholder_source_domain:{src_domain}"

    # 3. Validate retrieved_at as ISO-8601 UTC timestamp
    retrieved_ok, retrieved_msg = validate_iso8601_utc(cand.get("retrieved_at"))
    if not retrieved_ok:
        return False, retrieved_msg

    # Validate format and placeholder for optional supplied public fields
    website = str(cand.get("website") or "").strip()
    if website:
        p_web = urlparse(website if "://" in website else f"https://{website}")
        if p_web.scheme not in {"http", "https"} or not p_web.netloc:
            return False, "invalid_website_format"
        web_domain = extract_domain(website)
        if web_domain in PLACEHOLDER_DOMAINS:
            return False, f"placeholder_website_domain:{web_domain}"

    raw_phone = str(cand.get("phone") or "").strip()
    clean_phone = re.sub(r"\D", "", raw_phone)
    if clean_phone in PLACEHOLDER_PHONES:
        return False, "placeholder_phone_rejected"

    email = str(cand.get("email") or "").strip().lower()
    if email and any(ph in email for ph in ["@example.com", "@test.com", "@placeholder.com", "fake"]):
        return False, "placeholder_email_rejected"

    # Status check: caller-supplied string is NOT treated as proof
    val_status = str(cand.get("source_validation_status") or "").strip().lower()
    if val_status in {"unresolved_dns", "http_404_not_found", "failed", "error", "unverified"}:
        return False, f"unverified_source_status:{val_status}"

    # Raw evidence checks
    raw_evidence = cand.get("raw_evidence")
    if not isinstance(raw_evidence, dict) or not raw_evidence:
        return False, "missing_provenance_evidence"
    if raw_evidence.get("error_type") or raw_evidence.get("error"):
        return False, f"evidence_indicates_failure:{raw_evidence.get('error_type') or raw_evidence.get('error')}"

    # Require source_url and raw evidence to identify the same source URL
    ev_source_url = str(
        raw_evidence.get("source_url")
        or raw_evidence.get("url")
        or raw_evidence.get("target_url")
        or ""
    ).strip()
    if not ev_source_url:
        return False, "evidence_missing_source_url"
    if normalize_source_url(source_url) != normalize_source_url(ev_source_url):
        return False, f"source_url_evidence_mismatch:{source_url}!={ev_source_url}"

    evidence_strings = _flatten_evidence_strings(raw_evidence)
    if not evidence_strings:
        return False, "evidence_payload_empty"
    evidence_corpus = " ".join(evidence_strings).lower()
    evidence_digits = re.sub(r"\D", "", "".join(evidence_strings))

    # 1. Require explicit evidence tying business name to source
    name_tokens = [tok for tok in re.split(r"\W+", name.lower()) if len(tok) >= 3]
    distinctive_name_tokens = [tok for tok in name_tokens if tok not in GENERIC_NAME_STOPWORDS]
    ev_matched_name = str(
        raw_evidence.get("matched_name")
        or raw_evidence.get("business_name")
        or raw_evidence.get("business_name_evidence")
        or ""
    ).strip().lower()

    if distinctive_name_tokens:
        has_name_ev = (
            any(tok in ev_matched_name for tok in distinctive_name_tokens)
            or any(tok in evidence_corpus for tok in distinctive_name_tokens)
            or (name.lower() in evidence_corpus)
        )
    else:
        # Name consists solely of generic terms (e.g. "Melbourne Dog Training")
        has_name_ev = (ev_matched_name == name.lower()) or (name.lower() in evidence_corpus)
        if not has_name_ev and any(tok in evidence_corpus for tok in name_tokens):
            return False, "generic_name_match_only_rejected"

    if not has_name_ev:
        return False, "lacks_evidence_tying_business_name_to_source"

    # 2. Require evidence tying website if supplied
    if website:
        web_domain = extract_domain(website)
        ev_web = str(raw_evidence.get("matched_website") or raw_evidence.get("website_evidence") or raw_evidence.get("website") or "").strip().lower()
        has_web_ev = (
            (web_domain and web_domain in evidence_corpus)
            or (web_domain and web_domain in extract_domain(ev_web))
            or (website.lower().rstrip("/") in evidence_corpus)
        )
        if not has_web_ev:
            return False, "lacks_evidence_tying_website_to_source"

    # 3. Require evidence tying phone if supplied
    if clean_phone and len(clean_phone) >= 8:
        ev_phone_field = str(raw_evidence.get("matched_phone") or raw_evidence.get("phone_evidence") or raw_evidence.get("phone") or "")
        clean_ev_field = re.sub(r"\D", "", ev_phone_field)
        has_phone_ev = (
            clean_phone in evidence_digits
            or (clean_ev_field and clean_phone == clean_ev_field)
        )
        if not has_phone_ev:
            return False, "lacks_evidence_tying_phone_to_source"

    # 4. Require evidence tying email if supplied
    if email:
        ev_email_field = str(raw_evidence.get("matched_email") or raw_evidence.get("email_evidence") or raw_evidence.get("email") or "").strip().lower()
        has_email_ev = (
            email in evidence_corpus
            or email == ev_email_field
        )
        if not has_email_ev:
            return False, "lacks_evidence_tying_email_to_source"

    # 5. Require evidence tying suburb if supplied
    if suburb:
        suburb_lower = suburb.lower()
        ev_suburb_field = str(raw_evidence.get("matched_suburb") or raw_evidence.get("suburb_evidence") or raw_evidence.get("suburb") or "").strip().lower()
        has_suburb_ev = (
            suburb_lower in evidence_corpus
            or suburb_lower == ev_suburb_field
        )
        if not has_suburb_ev:
            return False, "lacks_evidence_tying_suburb_to_source"

    # 6. Require evidence tying ABN if supplied
    raw_abn = str(cand.get("abn") or "").strip()
    clean_abn = normalize_abn(raw_abn)
    if clean_abn:
        ev_abn_field = normalize_abn(str(raw_evidence.get("matched_abn") or raw_evidence.get("abn_evidence") or raw_evidence.get("abn") or ""))
        has_abn_ev = (
            clean_abn in evidence_digits
            or clean_abn == ev_abn_field
        )
        if not has_abn_ev:
            return False, "lacks_evidence_tying_abn_to_source"

    # 7. Require evidence tying services if supplied and non-empty
    services = [str(s).strip() for s in (cand.get("services") or []) if str(s).strip()]
    if services:
        ev_services = raw_evidence.get("matched_services") or raw_evidence.get("services_evidence") or raw_evidence.get("services") or []
        if isinstance(ev_services, str):
            ev_services = [ev_services]
        ev_services_corpus = " ".join(str(s) for s in ev_services).lower()
        has_service_ev = any(
            s.lower() in evidence_corpus or s.lower() in ev_services_corpus
            for s in services
        )
        if not has_service_ev:
            return False, "lacks_evidence_tying_services_to_source"

    if verify_live_reachability:
        reachable, reach_msg = check_source_reachability(source_url)
        if not reachable:
            return False, f"source_unreachable:{reach_msg}"

    return True, "valid"


def is_claimed_profile(trainer_doc: Dict[str, Any]) -> bool:
    """Determine if an existing profile is claimed or has active ownership/subscription."""
    claim_status = str(trainer_doc.get("claim_status") or "").lower()
    if claim_status in {"claimed", "pending_verification", "claim_disputed"}:
        return True
    tier = str(trainer_doc.get("tier") or "").lower()
    if tier in {"claimed", "pro", "suburb_sponsor", "citywide", "melbourne_sponsor", "featured", "premium"}:
        return True
    if trainer_doc.get("claimed_at") or trainer_doc.get("claim_event_id"):
        return True
    # Owner-created submissions carry ownership context even before a claim
    # verification event is complete. Never overwrite those records as a seed.
    if trainer_doc.get("via_submission_id") or trainer_doc.get("billing_email"):
        return True
    return False


async def find_existing_trainer(db: Any, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """4-tier canonical deduplication match: ABN -> Domain -> Phone -> Name+Suburb."""
    trainers_coll = getattr(db, "trainers", None)
    if trainers_coll is None:
        return None

    # Tier 1: ABN match
    abn = normalize_abn(candidate.get("abn"))
    if abn and len(abn) == 11:
        match = await trainers_coll.find_one({"abn": abn}, {"_id": 0})
        if match:
            return match

    # Tier 2: Domain hostname match
    website = str(candidate.get("website") or "").strip()
    domain = extract_domain(website)
    if domain:
        domain_pattern = rf"^(?:https?://)?(?:www\.)?{re.escape(domain)}(?::\d+)?(?:[/?#]|$)"
        match = await trainers_coll.find_one(
            {"website": {"$regex": domain_pattern, "$options": "i"}},
            {"_id": 0},
        )
        if match:
            return match

    # Tier 3: Phone match
    phone = re.sub(r"\D", "", str(candidate.get("phone") or "").strip())
    if phone and len(phone) >= 8:
        match = await trainers_coll.find_one(
            {"phone": {"$regex": re.escape(phone)}},
            {"_id": 0},
        )
        if match:
            return match

    # Tier 4: Exact normalized Name + Suburb
    name = str(candidate.get("name") or "").strip()
    suburb = str(candidate.get("suburb") or "").strip()
    if name and suburb:
        name_pat = f"^{re.escape(name)}$"
        sub_pat = f"^{re.escape(suburb)}$"
        match = await trainers_coll.find_one(
            {
                "name": {"$regex": name_pat, "$options": "i"},
                "suburb": {"$regex": sub_pat, "$options": "i"},
            },
            {"_id": 0},
        )
        if match:
            return match

    # Final tier: >90% name similarity within 5km, or the same suburb when
    # coordinates are unavailable. This is review-safe and never overwrites a
    # claimed profile.
    if deduplication is not None and name:
        nearby = await trainers_coll.find({}, {"_id": 0}).to_list(5000)
        for row in nearby:
            if deduplication.fuzzy_local_match(candidate, row):
                return row

    return None


def publishing_quality(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the canonical quality score without treating AI output as proof."""
    score = 0.0
    if candidate.get("phone") or candidate.get("website"):
        score += 0.30
    if candidate.get("suburb") and candidate.get("raw_evidence", {}).get("matched_suburb"):
        score += 0.25
    abr = candidate.get("abr_evidence") or {}
    active_abn = bool(normalize_abn(candidate.get("abn"))) and str(abr.get("status") or "").lower() == "active" and bool(abr.get("retrieved_at"))
    if active_abn:
        score += 0.20
    if float(candidate.get("review_count") or 0) > 0 and float(candidate.get("review_rating") or 0) > 0:
        score += 0.15
    if candidate.get("specialties") or candidate.get("services"):
        score += 0.10
    return {
        "score": round(score, 2),
        "eligible": score >= 0.75 and active_abn,
        "active_abn_evidence": active_abn,
    }


async def record_ingestion_failure(
    db: Any,
    source_url: str,
    error_reason: str,
    *,
    dry_run: bool = False,
) -> None:
    """Record source ingestion failure in db.source_ingestion_state for /ops visibility."""
    if dry_run or db is None:
        return
    coll = getattr(db, "source_ingestion_state", None)
    if coll is None:
        return
    now_ts = now_iso()
    await coll.update_one(
        {"source_url": source_url},
        {
            "$set": {
                "source_url": source_url,
                "last_checked_at": now_ts,
                "last_error": error_reason,
                "last_error_code": "source_ingestion_failure",
                "last_http_status": 0,
                "consecutive_failures": 1,
            }
        },
        upsert=True,
    )


async def record_ingestion_success(db: Any, candidate: Dict[str, Any], trainer_id: str, *, dry_run: bool = False) -> None:
    """Persist successful source health so `/ops` is not failure-only."""
    if dry_run or db is None:
        return
    coll = getattr(db, "source_ingestion_state", None)
    if coll is None:
        return
    source_url = str(candidate.get("source_url") or "").strip()
    pages = (candidate.get("raw_evidence") or {}).get("source_pages") or []
    first_page = pages[0] if pages and isinstance(pages[0], dict) else {}
    checked_at = str(candidate.get("retrieved_at") or now_iso())
    await coll.update_one(
        {"source_url": source_url},
        {"$set": {
            "source_url": source_url,
            "provider": "public_business_website",
            "trainer_id": trainer_id,
            "last_checked_at": checked_at,
            "last_ok_at": checked_at,
            "last_error": "",
            "last_error_code": "",
            "last_http_status": int(first_page.get("http_status") or 200),
            "last_source_sha256": str(first_page.get("sha256") or ""),
            "abr_status": str((candidate.get("abr_evidence") or {}).get("status") or ""),
            "consecutive_failures": 0,
            "suppressed_until": "",
            "last_candidates_seen": 1,
        }},
        upsert=True,
    )


def build_candidate_trainer_doc(candidate: Dict[str, Any], candidate_id: str, *, allow_publication: bool = False) -> Dict[str, Any]:
    """Build a fail-closed, lawful trainer document from an authentic candidate record."""
    raw_abn = candidate.get("abn")
    abn_clean = normalize_abn(raw_abn)
    abn_val = validate_abn_detailed(raw_abn) if abn_clean else None
    quality = publishing_quality(candidate)
    active_abr = bool(quality["active_abn_evidence"])
    abn_status = "not_provided"
    if abn_val:
        abn_status = "active" if active_abr else ("pending_verification" if abn_val["valid"] else abn_val["code"])

    now_ts = now_iso()
    abr_checked_at = str((candidate.get("abr_evidence") or {}).get("retrieved_at") or "")
    return {
        "id": candidate_id,
        "name": str(candidate.get("name") or "").strip(),
        "suburb": str(candidate.get("suburb") or "").strip(),
        "region": str(candidate.get("region") or "Greater Melbourne").strip(),
        "website": str(candidate.get("website") or "").strip(),
        "phone": str(candidate.get("phone") or "").strip(),
        "email": str(candidate.get("email") or "").strip(),
        "categories": list(candidate.get("categories") or []),
        "services": list(candidate.get("services") or []),
        "service_formats": list(candidate.get("service_formats") or []),
        "training_philosophy": str(candidate.get("training_philosophy") or "").strip(),
        "specialties": list(candidate.get("specialties") or []),
        "bio": str(candidate.get("bio") or "").strip(),
        "image_url": str(candidate.get("image_url") or "").strip(),
        "source_evidence_url": str(candidate.get("source_url") or "").strip(),
        "source_provenance": {
            "source_url": str(candidate.get("source_url") or "").strip(),
            "source_type": str(candidate.get("source_type") or "public_directory").strip(),
            "retrieved_at": str(candidate.get("retrieved_at") or now_ts).strip(),
            "raw_evidence": candidate.get("raw_evidence") or {},
        },
        "abr_evidence": candidate.get("abr_evidence") or {},
        # Strictly unverified and unclaimed by default
        "tier": "unclaimed",
        "claim_status": "unclaimed",
        "abn": abn_clean,
        "abn_status": abn_status,
        "abn_verified": active_abr,
        "abn_verified_at": abr_checked_at if active_abr else "",
        "abn_verification_reason": (
            "Active ABN confirmed from ABR; listing ownership remains unclaimed."
            if active_abr
            else "Candidate requires ABR lookup verification before public badge."
        ),
        "confidence_score": 0.50 if bool(candidate.get("website") or candidate.get("phone")) else 0.30,
        "verification_status": "unverified",
        "verification_reasoning": "Lawful candidate ingestion; pending owner claiming and ABR check.",
        "outcome_score": 0.05,
        "intros_30d": 0,
        "conversions_30d": 0,
        "ingestion_quality_score": quality["score"],
        "ingestion_quality_status": "qualified" if quality["eligible"] else "held",
        "published": bool(allow_publication and quality["eligible"]),
        "contact_ready": bool(candidate.get("website") or candidate.get("phone") or candidate.get("email")),
        "created_at": now_ts,
        "via_seed": True,
    }


async def process_seeding(
    db: Any,
    candidates: List[Dict[str, Any]],
    test_fixtures: Optional[List[Dict[str, Any]]] = None,
    *,
    dry_run: bool = False,
    allow_publication: bool = False,
) -> Dict[str, Any]:
    """Execute lawful candidate seeding against MongoDB with dry-run and apply modes."""
    summary: Dict[str, Any] = {
        "mode": "dry-run" if dry_run else "apply",
        "scanned": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "created": 0,
        "updated_unclaimed": 0,
        "preserved_claimed": 0,
        "duplicates_skipped": 0,
        "suppressed_delisted": 0,
        "quality_qualified": 0,
        "quality_held": 0,
        "ingest_failures_detected": 0,
        "ingest_failures_logged": 0,
        "actions": [],
    }

    seen_domains: set[str] = set()
    seen_abns: set[str] = set()

    for cand in candidates:
        summary["scanned"] += 1
        valid, reason = validate_candidate_schema(cand)
        if not valid:
            summary["invalid_count"] += 1
            src_url = str(cand.get("source_url") or f"invalid_candidate:{summary['scanned']}")
            await record_ingestion_failure(db, src_url, reason, dry_run=dry_run)
            summary["ingest_failures_detected"] += 1
            if not dry_run:
                summary["ingest_failures_logged"] += 1
            summary["actions"].append({"name": cand.get("name"), "action": "rejected_invalid", "reason": reason})
            continue

        suppression = await deduplication.suppression_match(db, cand) if db is not None and deduplication is not None else None
        if suppression:
            summary["suppressed_delisted"] += 1
            summary["actions"].append({"name": cand.get("name"), "action": "suppressed_delisted", "reason": suppression.get("reason") or "delisted_identity_match"})
            continue

        # In-batch duplicate check
        dom = extract_domain(cand.get("website"))
        abn = normalize_abn(cand.get("abn"))
        if dom and dom in seen_domains:
            summary["duplicates_skipped"] += 1
            summary["actions"].append({"name": cand.get("name"), "action": "skipped_batch_duplicate_domain", "domain": dom})
            continue
        if abn and abn in seen_abns:
            summary["duplicates_skipped"] += 1
            summary["actions"].append({"name": cand.get("name"), "action": "skipped_batch_duplicate_abn", "abn": abn})
            continue

        if dom:
            seen_domains.add(dom)
        if abn:
            seen_abns.add(abn)

        summary["valid_count"] += 1

        # Check existing in DB
        existing = await find_existing_trainer(db, cand)
        if existing:
            existing_id = existing.get("id")
            if is_claimed_profile(existing):
                # STRICT PRESERVATION: Do not overwrite claim status, tier, or ownership contacts
                summary["preserved_claimed"] += 1
                summary["actions"].append({
                    "id": existing_id,
                    "name": existing.get("name"),
                    "action": "preserved_claimed",
                    "claim_status": existing.get("claim_status"),
                    "tier": existing.get("tier"),
                })
            else:
                # Idempotent update for unclaimed profile (updating non-ownership metadata)
                refreshed = build_candidate_trainer_doc(cand, str(existing_id), allow_publication=allow_publication)
                if not dry_run and getattr(db, "trainers", None) is not None:
                    update_fields = {
                        key: refreshed[key]
                        for key in (
                            "name", "suburb", "region", "website", "phone", "email",
                            "categories", "services", "service_formats", "training_philosophy",
                            "specialties", "bio", "image_url", "source_evidence_url",
                            "source_provenance", "abr_evidence", "abn", "abn_status",
                            "abn_verified", "abn_verified_at", "abn_verification_reason",
                            "confidence_score", "verification_status", "verification_reasoning",
                            "ingestion_quality_score", "ingestion_quality_status", "contact_ready",
                        )
                    }
                    if allow_publication and refreshed["published"]:
                        update_fields["published"] = True
                    update_fields.update({
                        "tier": existing.get("tier") or "unclaimed",
                        "claim_status": existing.get("claim_status") or "unclaimed",
                        "updated_at": now_iso(),
                    })
                    await db.trainers.update_one({"id": existing_id}, {"$set": update_fields})
                if refreshed["ingestion_quality_status"] == "qualified":
                    summary["quality_qualified"] += 1
                else:
                    summary["quality_held"] += 1
                summary["updated_unclaimed"] += 1
                summary["actions"].append({
                    "id": existing_id,
                    "name": cand.get("name"),
                    "action": "updated_unclaimed",
                    "published": bool(allow_publication and refreshed["published"]),
                })
            await record_ingestion_success(db, cand, str(existing_id), dry_run=dry_run)
            continue

        # New candidate to insert
        candidate_id = cand.get("id") or f"cand_{summary['scanned']:03d}"
        doc = build_candidate_trainer_doc(cand, candidate_id, allow_publication=allow_publication)

        if doc["ingestion_quality_status"] == "qualified":
            summary["quality_qualified"] += 1
        else:
            summary["quality_held"] += 1

        if not dry_run and getattr(db, "trainers", None) is not None:
            await db.trainers.insert_one(doc.copy())
        await record_ingestion_success(db, cand, str(candidate_id), dry_run=dry_run)

        summary["created"] += 1
        summary["actions"].append({
            "id": candidate_id,
            "name": cand.get("name"),
            "action": "created" if not dry_run else "simulated_create",
            "tier": doc["tier"],
            "claim_status": doc["claim_status"],
            "abn_verified": doc["abn_verified"],
            "published": doc["published"],
        })

    # Process explicit test fixtures ONLY if explicitly supplied (never loaded by default)
    if test_fixtures:
        for bad_cand in test_fixtures:
            summary["scanned"] += 1
            valid, reason = validate_candidate_schema(bad_cand)
            # Even if schema is minimally valid, check if there's an intentional error flag
            error_reason = reason if not valid else bad_cand.get("raw_evidence", {}).get("error_type", "invalid_candidate")
            summary["invalid_count"] += 1
            src_url = str(bad_cand.get("source_url") or f"invalid_fixture:{summary['scanned']}")
            await record_ingestion_failure(db, src_url, error_reason, dry_run=dry_run)
            summary["ingest_failures_detected"] += 1
            if not dry_run:
                summary["ingest_failures_logged"] += 1
            summary["actions"].append({
                "name": bad_cand.get("name"),
                "action": "rejected_invalid_fixture",
                "reason": error_reason,
            })

    return summary


def build_run_manifest(summary: Dict[str, Any], *, seed_file: Path, data_gap: Dict[str, Any]) -> Dict[str, Any]:
    stable = json.dumps({"seed_file": str(seed_file.resolve()), "summary": summary, "data_gap": data_gap}, sort_keys=True, default=str)
    return {
        "manifest_version": 1,
        "generated_at": now_iso(),
        "run_id": f"ingest-{hashlib.sha256(stable.encode('utf-8')).hexdigest()[:16]}",
        "mode": summary.get("mode"),
        "seed_file": str(seed_file.resolve()),
        "data_gap": data_gap,
        "summary": summary,
    }


def load_seed_file(path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Load and parse canonical JSON seed candidates."""
    if not path.is_file():
        raise FileNotFoundError(f"Seed file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    candidates = data.get("candidates") or []
    data_gap = data.get("data_gap_declaration") or {}
    return candidates, data_gap


async def run_cli(args: argparse.Namespace) -> int:
    seed_file = Path(args.seed_file)
    logger.info("Loading seed data from %s", seed_file)
    try:
        candidates, data_gap = load_seed_file(seed_file)
    except Exception as exc:
        logger.error("Failed to load seed file: %s", exc)
        return 1

    dry_run = not args.apply
    mode_str = "DRY-RUN (no database writes)" if dry_run else "APPLY (writing to database)"
    logger.info("Execution mode: %s", mode_str)
    logger.info("Authentic candidate count: %d", len(candidates))
    if data_gap:
        logger.info(
            "Data gap declaration: status=%s, authentic=%d, target=%d, remaining_gap=%d",
            data_gap.get("status"),
            data_gap.get("authentic_count", len(candidates)),
            data_gap.get("target_supply_count", data_gap.get("target_launch_count", 100)),
            data_gap.get("remaining_data_gap", 100 - len(candidates)),
        )

    db = None
    mongo_url = args.mongo_url or os.environ.get("MONGO_URL") or os.environ.get("MONGODB_URI") or "mongodb://localhost:27017"
    db_name = args.db_name or os.environ.get("DB_NAME") or "dtd"

    client = None
    try:
        import motor.motor_asyncio  # type: ignore

        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        db = client[db_name]
        # Quick ping
        await client.admin.command("ping")
        logger.info("Connected to MongoDB at %s/%s", mongo_url.split("@")[-1], db_name)
    except Exception as exc:
        if not dry_run:
            logger.error("Cannot proceed in --apply mode without live MongoDB: %s", exc)
            return 1
        logger.warning("Proceeding with dry-run without active MongoDB connection: %s", exc)
        db = None

    fixtures_to_run: List[Dict[str, Any]] = []
    if getattr(args, "test_fixture_file", None):
        fixture_path = Path(args.test_fixture_file)
        if fixture_path.resolve() == DEFAULT_SEED_FILE.resolve():
            logger.warning("Test fixtures cannot be loaded from production seed file %s; ignoring", fixture_path)
        elif fixture_path.is_file():
            try:
                with fixture_path.open("r", encoding="utf-8") as f:
                    f_data = json.load(f)
                fixtures_to_run = f_data.get("invalid_candidates") or f_data.get("candidates") or []
            except Exception as exc:
                logger.warning("Failed to load test fixture file %s: %s", fixture_path, exc)

    publish_qualified = bool(getattr(args, "publish_qualified", False))
    if publish_qualified and dry_run:
        logger.error("--publish-qualified requires --apply")
        if client:
            client.close()
        return 1
    summary = await process_seeding(
        db,
        candidates,
        test_fixtures=fixtures_to_run,
        dry_run=dry_run,
        allow_publication=publish_qualified,
    )
    manifest = build_run_manifest(summary, seed_file=seed_file, data_gap=data_gap)
    manifest_path = str(getattr(args, "manifest", "") or "").strip()
    if manifest_path:
        output_path = Path(manifest_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        logger.info("Wrote ingestion manifest to %s", output_path)

    print("\n" + "=" * 60)
    print(f"SEEDING REPORT ({summary['mode'].upper()})")
    print("=" * 60)
    print(f"Total records scanned:     {summary['scanned']}")
    print(f"Valid candidates:          {summary['valid_count']}")
    print(f"Invalid / rejected:        {summary['invalid_count']}")
    print(f"New profiles created:      {summary['created']}")
    print(f"Unclaimed profiles updated:{summary['updated_unclaimed']}")
    print(f"Claimed profiles preserved:{summary['preserved_claimed']}")
    print(f"Duplicates skipped:        {summary['duplicates_skipped']}")
    print(f"Delisted suppressed:       {summary['suppressed_delisted']}")
    print(f"Quality qualified / held:  {summary['quality_qualified']} / {summary['quality_held']}")
    print(f"Ingest failures detected:  {summary['ingest_failures_detected']}")
    print(f"Ingest failures logged:    {summary['ingest_failures_logged']}")
    print("=" * 60)
    if data_gap:
        print(f"Remaining genuine data gap:{data_gap.get('remaining_data_gap', 'N/A')} authentic profiles required.")
    print("=" * 60 + "\n")

    if client:
        client.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Lawful Greater Melbourne supply seeding CLI.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simulate ingestion, validate schemas and ABNs without writing to DB (default).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute database writes to db.trainers and db.source_ingestion_state.",
    )
    parser.add_argument(
        "--seed-file",
        type=str,
        default=str(DEFAULT_SEED_FILE),
        help=f"Path to candidate seed JSON file (default: {DEFAULT_SEED_FILE}).",
    )
    parser.add_argument(
        "--mongo-url",
        type=str,
        default="",
        help="MongoDB connection URL (falls back to MONGO_URL env).",
    )
    parser.add_argument(
        "--db-name",
        type=str,
        default="",
        help="MongoDB database name (falls back to DB_NAME env or 'dtd').",
    )
    parser.add_argument(
        "--publish-qualified",
        action="store_true",
        default=False,
        help="Publish only quality-qualified, active-ABR candidates during an authorised --apply run.",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="",
        help="Optional path for a machine-readable dry-run/apply manifest.",
    )
    parser.add_argument(
        "--test-fixture-file",
        type=str,
        default="",
        help="Optional external test fixture file path (disabled by default; never loaded from production seed file).",
    )

    args = parser.parse_args()
    if args.apply:
        args.dry_run = False

    exit_code = asyncio.run(run_cli(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
