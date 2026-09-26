"""Trainer Quality, Validation & Governance Service.

Canonical implementation of candidate validation, publishing quality scoring,
deduplication matching, and source ingestion status logging.
Shared between CLI intake tools (scripts/) and automated backend jobs (services/).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import logging
import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

try:
    from services.abn_validator import (  # type: ignore
        format_abn,
        normalize_abn,
        validate_abn_detailed,
    )
    from services import deduplication  # type: ignore
except ImportError:
    from backend.services.abn_validator import (  # type: ignore
        format_abn,
        normalize_abn,
        validate_abn_detailed,
    )
    from backend.services import deduplication  # type: ignore

logger = logging.getLogger(__name__)

SUPPORTED_SOURCE_TYPES: Set[str] = {
    "business_website",
    "public_directory",
    "government_registry",
    "commercial_register",
}

PLACEHOLDER_NAMES: Set[str] = {
    "unnamed", "unknown", "placeholder", "fake", "test", "demo", "sample", "example",
}

PLACEHOLDER_DOMAINS: Set[str] = {
    "example.com", "example.org", "test.local", "localhost", "invalid-domain.local", "malformed.local",
}

PLACEHOLDER_PHONES: Set[str] = {
    "0400000000", "0411111111", "0412345678", "0390000000", "12345678", "00000000",
}

GENERIC_NAME_STOPWORDS: Set[str] = {
    "the", "and", "dog", "dogs", "puppy", "puppies", "training", "trainer", "trainers",
    "k9", "canine", "melbourne", "australia", "vic", "academy", "school", "services",
    "co", "pty", "ltd", "group", "club", "centre", "center", "hub",
}


def now_iso() -> str:
    """Return ISO-8601 UTC timestamp."""
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

    retrieved_ok, retrieved_msg = validate_iso8601_utc(cand.get("retrieved_at"))
    if not retrieved_ok:
        return False, retrieved_msg

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

    val_status = str(cand.get("source_validation_status") or "").strip().lower()
    if val_status in {"unresolved_dns", "http_404_not_found", "failed", "error", "unverified"}:
        return False, f"unverified_source_status:{val_status}"

    raw_evidence = cand.get("raw_evidence")
    if not isinstance(raw_evidence, dict) or not raw_evidence:
        return False, "missing_provenance_evidence"
    if raw_evidence.get("error_type") or raw_evidence.get("error"):
        return False, f"evidence_indicates_failure:{raw_evidence.get('error_type') or raw_evidence.get('error')}"

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
        has_name_ev = (ev_matched_name == name.lower()) or (name.lower() in evidence_corpus)
        if not has_name_ev and any(tok in evidence_corpus for tok in name_tokens):
            return False, "generic_name_match_only_rejected"

    if not has_name_ev:
        return False, "lacks_evidence_tying_business_name_to_source"

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

    if clean_phone and len(clean_phone) >= 8:
        ev_phone_field = str(raw_evidence.get("matched_phone") or raw_evidence.get("phone_evidence") or raw_evidence.get("phone") or "")
        clean_ev_field = re.sub(r"\D", "", ev_phone_field)
        has_phone_ev = (
            clean_phone in evidence_digits
            or (clean_ev_field and clean_phone == clean_ev_field)
        )
        if not has_phone_ev:
            return False, "lacks_evidence_tying_phone_to_source"

    if email:
        ev_email_field = str(raw_evidence.get("matched_email") or raw_evidence.get("email_evidence") or raw_evidence.get("email") or "").strip().lower()
        has_email_ev = (
            email in evidence_corpus
            or email == ev_email_field
        )
        if not has_email_ev:
            return False, "lacks_evidence_tying_email_to_source"

    if suburb:
        suburb_lower = suburb.lower()
        ev_suburb_field = str(raw_evidence.get("matched_suburb") or raw_evidence.get("suburb_evidence") or raw_evidence.get("suburb") or "").strip().lower()
        has_suburb_ev = (
            suburb_lower in evidence_corpus
            or suburb_lower == ev_suburb_field
        )
        if not has_suburb_ev:
            return False, "lacks_evidence_tying_suburb_to_source"

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
        match = await trainers_coll.find_one(
            {
                "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"},
                "suburb": {"$regex": f"^{re.escape(suburb)}$", "$options": "i"},
            },
            {"_id": 0},
        )
        if match:
            return match

    # Tier 4b: Fuzzy local match
    if name:
        nearby = await trainers_coll.find({"suburb": suburb}, {"_id": 0}).to_list(10)
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


async def record_ingestion_success(
    db: Any,
    candidate: Dict[str, Any],
    trainer_id: str,
    *,
    dry_run: bool = False,
) -> None:
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
