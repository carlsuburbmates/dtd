"""Trainer Quality, Validation & Governance Service.

Canonical implementation of candidate validation, publishing quality scoring,
deduplication matching, and source ingestion status logging.
Shared between CLI intake tools (scripts/) and automated backend jobs (services/).
"""

from __future__ import annotations

from dataclasses import dataclass
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
    now_ts = now_iso()
    if coll is not None:
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

    # R4 & P0: If existing trainer profile is linked to this failing source URL (via source_url, source_evidence_url, or website), invalidate capabilities upon refresh failure
    trainers_coll = getattr(db, "trainers", None)
    if trainers_coll is not None:
        matched_trainers = []
        for field in ("source_url", "source_evidence_url", "website"):
            found = await trainers_coll.find_one({field: source_url}, {"_id": 0})
            if found and found.get("id") and not any(t["id"] == found["id"] for t in matched_trainers):
                matched_trainers.append(found)

        for existing_trainer in matched_trainers:
            if existing_trainer and existing_trainer.get("capabilities"):
                inv_caps = invalidate_trainer_capabilities(existing_trainer, reason=f"source_refresh_failed:{error_reason}")
                await trainers_coll.update_one(
                    {"id": existing_trainer["id"]},
                    {"$set": {"capabilities": inv_caps, "source_last_error": error_reason, "updated_at": now_ts}},
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


# ===========================================================================
# DF-026 & CDR-021/CDR-022: Match-Ready Capability Projection Architecture
# ===========================================================================

CANONICAL_SPECIALTIES: Dict[str, Dict[str, Any]] = {
    "puppy_training": {
        "label": "Puppy Training & Socialisation",
        "aliases": {
            "puppy", "puppies", "puppy_training", "puppy training",
            "puppy socialisation", "puppy socialization", "puppy basics",
            "puppy manners", "early puppy", "toilet training",
            "puppy preschool", "puppy school", "puppy classes", "puppy approach",
        },
    },
    "obedience": {
        "label": "Basic & Advanced Obedience",
        "aliases": {
            "obedience", "basic obedience", "manners", "general obedience",
            "basic manners", "foundation training", "good manners",
            "advanced obedience", "pet manners", "dog training",
            "general dog training", "puppy & dog training", "dog & puppy training",
        },
    },
    "behaviour_modification": {
        "label": "Behaviour Modification & Challenges",
        "aliases": {
            "behaviour_modification", "behavior_modification", "behaviour modification",
            "behavior modification", "behavioural challenges", "behavioral challenges",
            "behaviour consultations", "behaviour consultation", "behaviour support",
            "behavior support", "behaviour & training", "behaviour problems",
            "problem behaviours", "behaviour consults", "behavioural consultations",
            "behavioural support", "challenging behaviours",
        },
    },
    "leash_reactivity": {
        "label": "Leash Reactivity & Pulling",
        "aliases": {
            "leash_reactivity", "leash reactivity", "reactivity",
            "leash pulling", "pulling on leash", "leash manners",
            "loose leash", "loose leash walking", "barking on leash",
        },
    },
    "separation_anxiety": {
        "label": "Separation Anxiety",
        "aliases": {
            "separation_anxiety", "separation anxiety", "home alone",
            "alone time", "isolation distress", "separation distress",
        },
    },
    "barking": {
        "label": "Excessive Barking",
        "aliases": {
            "barking", "excessive barking", "nuisance barking",
            "alert barking", "vocalisation", "barking at fence",
        },
    },
    "aggression": {
        "label": "Aggression & Complex Behaviour",
        "aliases": {
            "aggression", "dog aggression", "human aggression",
            "dog-to-dog aggression", "bite history", "fear aggression",
            "reactive aggression", "aggressive behaviour",
        },
    },
    "fear_anxiety": {
        "label": "Fear, Phobias & Generalised Anxiety",
        "aliases": {
            "fear_anxiety", "fearful", "fear", "anxiety",
            "nervous dogs", "sound phobia", "thunderstorm phobia",
            "generalised anxiety", "rescue trauma", "nervous",
        },
    },
    "recall": {
        "label": "Reliable Recall (Come When Called)",
        "aliases": {
            "recall", "reliable recall", "off leash", "off-leash recall",
            "come when called", "distance recall",
        },
    },
    "resource_guarding": {
        "label": "Resource Guarding",
        "aliases": {
            "resource_guarding", "resource guarding", "food guarding",
            "possession guarding", "toy guarding", "space guarding",
        },
    },
    "rescue_rehoming": {
        "label": "Rescue & Rehoming Integration",
        "aliases": {
            "rescue_rehoming", "rescue", "rescue dogs", "shelter dogs",
            "rehoming", "adoption transition", "post-adoption",
        },
    },
    "scent_work": {
        "label": "Scent Work & Mental Stimulation",
        "aliases": {
            "scent_work", "scent work", "nosework", "tracking", "scent detection",
        },
    },
    "therapy_assistance": {
        "label": "Therapy & Assistance Dog Preparation",
        "aliases": {
            "therapy_assistance", "therapy dog", "assistance dog",
            "service dog", "therapy preparation",
        },
    },
}

CANONICAL_SERVICE_FORMATS: Dict[str, Dict[str, Any]] = {
    "in_home": {
        "label": "In-Home Private Training",
        "aliases": {
            "in_home", "in home", "in-home", "private in-home",
            "home visits", "mobile", "at home", "private consultation",
            "in_home_private", "in-home private", "in-house training",
            "in house training", "private dog training", "private training",
            "private consults", "consultations", "in-home training",
            "in home training",
        },
    },
    "facility": {
        "label": "Training Centre / Facility",
        "aliases": {
            "facility", "training center", "training centre",
            "in-facility", "facility-based", "in studio", "classroom",
        },
    },
    "outdoor_park": {
        "label": "Outdoor & Park Sessions",
        "aliases": {
            "outdoor_park", "park", "outdoor", "public park",
            "outdoor sessions", "park training",
        },
    },
    "board_and_train": {
        "label": "Board & Train (Residential)",
        "aliases": {
            "board_and_train", "board and train", "residential",
            "boot camp", "residential training",
        },
    },
    "online": {
        "label": "Online / Virtual Coaching",
        "aliases": {
            "online", "virtual", "zoom", "remote consultation",
            "online coaching", "telehealth",
        },
    },
    "group_classes": {
        "label": "Group Classes",
        "aliases": {
            "group_classes", "group class", "group sessions",
            "classes", "puppy school", "puppy class", "group training",
            "puppy preschool", "puppy classes",
        },
    },
}

CANONICAL_LIFE_STAGES: Dict[str, Dict[str, Any]] = {
    "puppy": {
        "label": "Puppy (< 6 months)",
        "aliases": {"puppy", "puppies", "young puppy", "< 6 months", "0-6 months"},
    },
    "adolescent": {
        "label": "Adolescent (6 - 18 months)",
        "aliases": {"adolescent", "teenager", "juvenile", "6-18 months", "young dog"},
    },
    "adult": {
        "label": "Adult (1.5 - 7 years)",
        "aliases": {"adult", "mature", "1.5-7 years", "adult dog"},
    },
    "senior": {
        "label": "Senior (7+ years)",
        "aliases": {"senior", "geriatric", "older dogs", "7+ years", "older dog"},
    },
    "all_life_stages": {
        "label": "All Life Stages",
        "aliases": {"all", "all stages", "all ages", "any age", "all_life_stages"},
    },
}

VALID_TRAINING_PHILOSOPHIES: Dict[str, Dict[str, Any]] = {
    "positive_reinforcement_force_free": {
        "label": "Positive Reinforcement / Force-Free",
        "aliases": {
            "positive reinforcement / force-free", "positive reinforcement",
            "force-free", "force free", "positive_reinforcement", "force_free",
            "r+", "lima", "reward-based", "force-free / positive",
        },
    },
    "balanced": {
        "label": "Balanced Training",
        "aliases": {"balanced", "balanced training", "traditional and modern"},
    },
}

VALID_CATCHMENT_TYPES: Dict[str, Dict[str, Any]] = {
    "specific_suburbs": {
        "label": "Specific Nominated Suburbs",
        "aliases": {"specific_suburbs", "suburbs", "selected suburbs"},
    },
    "radius": {
        "label": "Distance Radius from Suburb",
        "aliases": {"radius", "distance radius", "km radius"},
    },
    "melbourne_wide": {
        "label": "Melbourne-Wide Coverage",
        "aliases": {"melbourne_wide", "melbourne wide", "greater melbourne", "all melbourne", "citywide"},
    },
}

# Freshness TTL Constants (in days)
TRAINER_DECLARATION_TTL_DAYS = 180  # 6 months for trainer declarations
OFFICIAL_SOURCE_TTL_DAYS = 90       # 3 months for official source captures
AI_PROPOSED_TTL_DAYS = 30           # 30 days for AI extractions (display/prefill only)

VALID_CAPABILITY_BASES: Set[str] = {"trainer_declaration", "official_source", "ai_proposed"}


@dataclass(frozen=True)
class CapabilityProjectionPolicy:
    """Configurable projection policy boundary separating immutable data integrity from Decision Contract v2 policy.

    Immutable Data Integrity Rules:
    - Canonical taxonomy validation against CANONICAL_SPECIALTIES, CANONICAL_SERVICE_FORMATS, etc.
    - Field-level provenance tracking (basis, confirmed_at, evidence_reference).
    - Lifecycle invalidation enforcement (invalidated facts cannot be projected).
    - Hard status/gate requirements (publication, ownership dispute, statutory ABN revocation, contact readiness).
    - Strict exclusion of commercial bias (paid tier, pricing, marketing bio, reviews, AI confidence).

    Decision Contract v2 Policy Inputs (Configurable):
    - permitted_bases: The evidence bases eligible for matching consideration.
    - declaration_ttl_days: Validity window for direct trainer declarations.
    - official_source_ttl_days: Validity window for structured official source captures.
    - ai_proposed_ttl_days: Validity window for AI extractions (display/prefill only).
    - require_specialties_or_formats: Minimum capability gate before match eligibility is granted.
    """
    version: str = "v1"
    permitted_bases: Tuple[str, ...] = ("trainer_declaration",)
    declaration_ttl_days: int = 180
    official_source_ttl_days: int = 90
    ai_proposed_ttl_days: int = 30
    require_specialties_or_formats: bool = True


DEFAULT_PROJECTION_POLICY = CapabilityProjectionPolicy()


def normalize_specialty(val: str) -> Optional[str]:
    """Normalize specialty alias to canonical ID."""
    clean = re.sub(r"[\s\-_]+", " ", str(val or "").strip().lower())
    if not clean:
        return None
    for canon_id, meta in CANONICAL_SPECIALTIES.items():
        if clean == canon_id.replace("_", " ") or clean == canon_id:
            return canon_id
        if any(re.sub(r"[\s\-_]+", " ", a.lower()) == clean for a in meta["aliases"]):
            return canon_id
    return None


def normalize_service_format(val: str) -> Optional[str]:
    """Normalize service format alias to canonical ID."""
    clean = re.sub(r"[\s\-_]+", " ", str(val or "").strip().lower())
    if not clean:
        return None
    for canon_id, meta in CANONICAL_SERVICE_FORMATS.items():
        if clean == canon_id.replace("_", " ") or clean == canon_id:
            return canon_id
        if any(re.sub(r"[\s\-_]+", " ", a.lower()) == clean for a in meta["aliases"]):
            return canon_id
    return None


def normalize_life_stage(val: str) -> Optional[str]:
    """Normalize dog life stage alias to canonical ID."""
    clean = re.sub(r"[\s\-_]+", " ", str(val or "").strip().lower())
    if not clean:
        return None
    for canon_id, meta in CANONICAL_LIFE_STAGES.items():
        if clean == canon_id.replace("_", " ") or clean == canon_id:
            return canon_id
        if any(re.sub(r"[\s\-_]+", " ", a.lower()) == clean for a in meta["aliases"]):
            return canon_id
    return None


def normalize_training_philosophy(val: str) -> Optional[str]:
    """Normalize training philosophy alias to canonical ID."""
    clean = re.sub(r"[\s\-_/]+", " ", str(val or "").strip().lower())
    if not clean:
        return None
    for canon_id, meta in VALID_TRAINING_PHILOSOPHIES.items():
        if clean == canon_id.replace("_", " ") or clean == canon_id:
            return canon_id
        if any(re.sub(r"[\s\-_/]+", " ", a.lower()) == clean for a in meta["aliases"]):
            return canon_id
    return None


def normalize_catchment_type(val: str) -> Optional[str]:
    """Normalize catchment type alias to canonical ID."""
    clean = re.sub(r"[\s\-_]+", " ", str(val or "").strip().lower())
    if not clean:
        return None
    for canon_id, meta in VALID_CATCHMENT_TYPES.items():
        if clean == canon_id.replace("_", " ") or clean == canon_id:
            return canon_id
        if any(re.sub(r"[\s\-_]+", " ", a.lower()) == clean for a in meta["aliases"]):
            return canon_id
    return None


def validate_capability_category(category: str, raw_value: Any) -> Dict[str, Any]:
    """Deterministically validate capability values against canonical vocabularies."""
    result: Dict[str, Any] = {
        "valid": False,
        "canonical_terms": [] if category not in {"training_philosophy", "catchment_type"} else "",
        "rejected_terms": [],
        "reason": "",
    }

    if category == "specialties":
        items = raw_value if isinstance(raw_value, (list, tuple, set)) else [raw_value]
        canonical_terms: List[str] = []
        rejected: List[str] = []
        for it in items:
            it_str = str(it or "").strip()
            if not it_str:
                continue
            norm = normalize_specialty(it_str)
            if norm:
                if norm not in canonical_terms:
                    canonical_terms.append(norm)
            else:
                rejected.append(it_str)
        result["canonical_terms"] = canonical_terms
        result["rejected_terms"] = rejected
        result["valid"] = len(canonical_terms) > 0
        if not result["valid"]:
            result["reason"] = f"no_valid_canonical_specialties (rejected: {rejected})"
        elif rejected:
            result["reason"] = f"partial_valid_with_rejected_terms: {rejected}"
        else:
            result["reason"] = "valid"
        return result

    if category == "service_formats":
        items = raw_value if isinstance(raw_value, (list, tuple, set)) else [raw_value]
        canonical_terms = []
        rejected = []
        for it in items:
            it_str = str(it or "").strip()
            if not it_str:
                continue
            norm = normalize_service_format(it_str)
            if norm:
                if norm not in canonical_terms:
                    canonical_terms.append(norm)
            else:
                rejected.append(it_str)
        result["canonical_terms"] = canonical_terms
        result["rejected_terms"] = rejected
        result["valid"] = len(canonical_terms) > 0
        if not result["valid"]:
            result["reason"] = f"no_valid_canonical_service_formats (rejected: {rejected})"
        elif rejected:
            result["reason"] = f"partial_valid_with_rejected_terms: {rejected}"
        else:
            result["reason"] = "valid"
        return result

    if category == "life_stages":
        items = raw_value if isinstance(raw_value, (list, tuple, set)) else [raw_value]
        canonical_terms = []
        rejected = []
        for it in items:
            it_str = str(it or "").strip()
            if not it_str:
                continue
            norm = normalize_life_stage(it_str)
            if norm:
                if norm not in canonical_terms:
                    canonical_terms.append(norm)
            else:
                rejected.append(it_str)
        result["canonical_terms"] = canonical_terms
        result["rejected_terms"] = rejected
        result["valid"] = len(canonical_terms) > 0
        if not result["valid"]:
            result["reason"] = f"no_valid_canonical_life_stages (rejected: {rejected})"
        elif rejected:
            result["reason"] = f"partial_valid_with_rejected_terms: {rejected}"
        else:
            result["reason"] = "valid"
        return result

    if category == "training_philosophy":
        it_str = str(raw_value or "").strip()
        norm = normalize_training_philosophy(it_str)
        if norm:
            result["canonical_terms"] = norm
            result["valid"] = True
            result["reason"] = "valid"
        else:
            result["rejected_terms"] = [it_str] if it_str else []
            result["valid"] = False
            result["reason"] = f"unsupported_training_philosophy:{it_str}"
        return result

    if category == "catchment_type":
        it_str = str(raw_value or "").strip()
        norm = normalize_catchment_type(it_str)
        if norm:
            result["canonical_terms"] = norm
            result["valid"] = True
            result["reason"] = "valid"
        else:
            result["rejected_terms"] = [it_str] if it_str else []
            result["valid"] = False
            result["reason"] = f"unsupported_catchment_type:{it_str}"
        return result

    if category == "serviced_suburbs":
        items = raw_value if isinstance(raw_value, (list, tuple, set)) else [raw_value]
        cleaned_suburbs: List[str] = []
        rejected = []
        for it in items:
            s_name = str(it or "").strip().title()
            if not s_name:
                continue
            if len(s_name) < 2 or any(ph in s_name.lower() for ph in PLACEHOLDER_NAMES):
                rejected.append(s_name)
            else:
                if s_name not in cleaned_suburbs:
                    cleaned_suburbs.append(s_name)
        result["canonical_terms"] = cleaned_suburbs
        result["rejected_terms"] = rejected
        result["valid"] = len(cleaned_suburbs) > 0
        result["reason"] = "valid" if not rejected else f"partial_valid_with_rejected_suburbs: {rejected}"
        return result

    if category == "delivery_constraints":
        if not isinstance(raw_value, dict):
            result["valid"] = False
            result["reason"] = "invalid_delivery_constraints_format"
            return result

        # Fail closed on unknown or invalid types
        raw_in_home = raw_value.get("in_home_available")
        if raw_in_home is not None:
            if not isinstance(raw_in_home, bool):
                result["valid"] = False
                result["reason"] = "invalid_in_home_available_must_be_boolean"
                return result
            in_home = raw_in_home
        else:
            in_home = False

        raw_facility = raw_value.get("facility_available")
        if raw_facility is not None:
            if not isinstance(raw_facility, bool):
                result["valid"] = False
                result["reason"] = "invalid_facility_available_must_be_boolean"
                return result
            facility = raw_facility
        else:
            facility = False

        raw_dist = raw_value.get("travel_distance_km")
        if raw_dist is not None:
            if isinstance(raw_dist, bool) or not isinstance(raw_dist, (int, float)):
                result["valid"] = False
                result["reason"] = "invalid_travel_distance_km_type"
                return result
            dist = float(raw_dist)
            if math.isnan(dist) or math.isinf(dist):
                result["valid"] = False
                result["reason"] = "invalid_travel_distance_km_non_finite"
                return result
            if dist < 0.0 or dist > 200.0:
                result["valid"] = False
                result["reason"] = "invalid_travel_distance_km_range"
                return result
        else:
            dist = 0.0

        raw_notes = raw_value.get("notes")
        if raw_notes is not None:
            if not isinstance(raw_notes, str):
                result["valid"] = False
                result["reason"] = "invalid_notes_must_be_string"
                return result
            trimmed_notes = raw_notes.strip()
            if len(trimmed_notes) > 200:
                result["valid"] = False
                result["reason"] = "notes_exceeds_max_length_200"
                return result
        else:
            trimmed_notes = ""

        result["canonical_terms"] = {
            "in_home_available": in_home,
            "facility_available": facility,
            "travel_distance_km": float(dist),
            "notes": trimmed_notes,
        }
        result["valid"] = True
        result["reason"] = "valid"
        return result

    result["valid"] = False
    result["reason"] = f"unrecognized_capability_category:{category}"
    return result


def compute_capability_freshness(
    confirmed_at_str: str,
    basis: str,
    *,
    as_of: Optional[datetime] = None,
    policy: Optional[CapabilityProjectionPolicy] = None,
) -> Tuple[str, bool]:
    """Compute deterministic freshness state based on basis TTL."""
    if not confirmed_at_str or not isinstance(confirmed_at_str, str):
        return "missing_confirmation_timestamp", False

    active_policy = policy or DEFAULT_PROJECTION_POLICY

    # Validate ISO-8601 UTC
    valid_ts, _ = validate_iso8601_utc(confirmed_at_str)
    if not valid_ts:
        return "malformed_confirmation_timestamp", False

    ref_time = as_of or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    try:
        confirmed_dt = datetime.fromisoformat(confirmed_at_str.replace("Z", "+00:00"))
        age_days = (ref_time - confirmed_dt).total_seconds() / 86400.0
    except Exception as exc:
        return f"timestamp_parse_error:{exc}", False

    if age_days < 0:
        return "future_timestamp_rejected", False

    ttl_days = (
        active_policy.declaration_ttl_days if basis == "trainer_declaration"
        else active_policy.official_source_ttl_days if basis == "official_source"
        else active_policy.ai_proposed_ttl_days
    )

    if age_days > ttl_days:
        return "stale", False

    return "fresh", True


def create_capability_fact(
    category: str,
    raw_value: Any,
    *,
    basis: str,
    evidence_reference: str,
    confirmed_at: Optional[str] = None,
    as_of: Optional[datetime] = None,
    policy: Optional[CapabilityProjectionPolicy] = None,
) -> Dict[str, Any]:
    """Create a structured capability fact with field-level provenance and validation.

    Governance Rules (CDR-021 & CDR-022):
    - Basis 'trainer_declaration' is the primary source of matching capacity.
    - Basis 'ai_proposed' is display/prefill ONLY and NEVER permitted in the match-ready projection.
    - Stale or invalid facts fail closed (permitted_in_projection = False).
    """
    if basis not in VALID_CAPABILITY_BASES:
        raise ValueError(f"Invalid capability basis: {basis}. Must be one of {VALID_CAPABILITY_BASES}")

    active_policy = policy or DEFAULT_PROJECTION_POLICY
    confirmation_ts = confirmed_at or now_iso()
    validation = validate_capability_category(category, raw_value)
    freshness_state, is_fresh = compute_capability_freshness(confirmation_ts, basis, as_of=as_of, policy=active_policy)

    # Core match-readiness rule:
    # 1. Must be valid
    # 2. Must be fresh
    # 3. Must be permitted under active policy
    permitted = bool(validation["valid"]) and is_fresh and (basis in active_policy.permitted_bases)

    return {
        "category": category,
        "canonical_value": validation["canonical_terms"],
        "value": validation["canonical_terms"],
        "raw_value": raw_value,
        "basis": basis,
        "evidence_reference": evidence_reference,
        "confirmed_at": confirmation_ts,
        "freshness_state": freshness_state,
        "validation_result": validation,
        "permitted_in_projection": permitted,
        "invalidated_at": "",
        "invalidation_reason": "",
    }


def package_trainer_capabilities(
    *,
    specialties: Optional[List[str]] = None,
    service_formats: Optional[List[str]] = None,
    life_stages: Optional[List[str]] = None,
    training_philosophy: Optional[str] = None,
    serviced_suburbs: Optional[List[str]] = None,
    catchment_type: Optional[str] = None,
    delivery_constraints: Optional[Dict[str, Any]] = None,
    basis: str = "trainer_declaration",
    evidence_reference: str = "",
    confirmed_at: Optional[str] = None,
    as_of: Optional[datetime] = None,
    policy: Optional[CapabilityProjectionPolicy] = None,
) -> Dict[str, Dict[str, Any]]:
    """Helper to bundle all capability categories into a structured capabilities dictionary."""
    capabilities: Dict[str, Dict[str, Any]] = {}
    ts = confirmed_at or now_iso()

    if specialties is not None:
        capabilities["specialties"] = create_capability_fact(
            "specialties", specialties, basis=basis, evidence_reference=evidence_reference, confirmed_at=ts, as_of=as_of, policy=policy,
        )
    if service_formats is not None:
        capabilities["service_formats"] = create_capability_fact(
            "service_formats", service_formats, basis=basis, evidence_reference=evidence_reference, confirmed_at=ts, as_of=as_of, policy=policy,
        )
    if life_stages is not None:
        capabilities["life_stages"] = create_capability_fact(
            "life_stages", life_stages, basis=basis, evidence_reference=evidence_reference, confirmed_at=ts, as_of=as_of, policy=policy,
        )
    if training_philosophy is not None:
        capabilities["training_philosophy"] = create_capability_fact(
            "training_philosophy", training_philosophy, basis=basis, evidence_reference=evidence_reference, confirmed_at=ts, as_of=as_of, policy=policy,
        )
    if serviced_suburbs is not None:
        capabilities["serviced_suburbs"] = create_capability_fact(
            "serviced_suburbs", serviced_suburbs, basis=basis, evidence_reference=evidence_reference, confirmed_at=ts, as_of=as_of, policy=policy,
        )
    if catchment_type is not None:
        capabilities["catchment_type"] = create_capability_fact(
            "catchment_type", catchment_type, basis=basis, evidence_reference=evidence_reference, confirmed_at=ts, as_of=as_of, policy=policy,
        )
    if delivery_constraints is not None:
        capabilities["delivery_constraints"] = create_capability_fact(
            "delivery_constraints", delivery_constraints, basis=basis, evidence_reference=evidence_reference, confirmed_at=ts, as_of=as_of, policy=policy,
        )

    return capabilities


def invalidate_trainer_capabilities(
    trainer_doc: Dict[str, Any],
    reason: str,
    *,
    field_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Invalidate trainer capabilities upon correction, dispute, suppression, or failed refresh."""
    capabilities = trainer_doc.get("capabilities") or {}
    now_ts = now_iso()
    targets = set(field_names) if field_names else set(capabilities.keys())

    for k, fact in capabilities.items():
        if (not field_names or k in targets) and isinstance(fact, dict):
            fact["permitted_in_projection"] = False
            fact["invalidated_at"] = now_ts
            fact["invalidation_reason"] = reason

    if "capabilities" in trainer_doc:
        trainer_doc["capabilities"] = capabilities

    return capabilities


def build_match_ready_projection(
    trainer_doc: Dict[str, Any],
    *,
    as_of: Optional[datetime] = None,
    policy: Optional[CapabilityProjectionPolicy] = None,
) -> Dict[str, Any]:
    """Construct a bounded, deterministic match-ready capability projection for matching.

    Governance Invariants (AGENTS.md Rule 6A, CDR-021, CDR-022, DF-026):
    - Consumes ONLY validated, fresh, permitted capability facts.
    - AI-proposed facts CANNOT enter the projection without trainer confirmation.
    - Paid tier, pricing, marketing bio, reviews, and AI confidence are STRICTLY EXCLUDED.
    - Profiles that are unpublished, disputed, contact-unready, or statutory revoked fail closed.
    - R1: Legacy records without explicit provenance/confirmation fail closed with legacy_unconfirmed_provenance.
    """
    active_policy = policy or DEFAULT_PROJECTION_POLICY
    as_of_iso = (as_of or datetime.now(timezone.utc)).isoformat()
    reasons: List[str] = []
    is_eligible = True

    # 1. Gate: Publication state
    # Database records always contain 'published'. Ingested sources must be published.
    if "published" in trainer_doc and not trainer_doc.get("published"):
        is_eligible = False
        reasons.append("profile_not_published")
    elif "published" not in trainer_doc and (trainer_doc.get("source_url") or trainer_doc.get("source_evidence_url")):
        is_eligible = False
        reasons.append("profile_not_published")

    # 2. Gate: Ownership disputes
    claim_status = str(trainer_doc.get("claim_status") or "").lower()
    if claim_status == "claim_disputed":
        is_eligible = False
        reasons.append("ownership_disputed")

    # 3. Gate: Statutory ABN status
    abn_status = str(trainer_doc.get("abn_status") or "").lower()
    if trainer_doc.get("abn_verified") is False and abn_status in {"cancelled", "inactive", "deregistered"}:
        is_eligible = False
        reasons.append("statutory_abn_revoked")

    # 4. Gate: Contact readiness
    if "contact_ready" in trainer_doc:
        if not trainer_doc["contact_ready"]:
            is_eligible = False
            reasons.append("not_contact_ready")
    elif trainer_doc.get("source_url") or trainer_doc.get("source_evidence_url"):
        has_contact = bool(
            trainer_doc.get("phone")
            or trainer_doc.get("email")
            or trainer_doc.get("website")
        )
        if not has_contact:
            is_eligible = False
            reasons.append("not_contact_ready")

    # 5. Extract capabilities with provenance
    capabilities = trainer_doc.get("capabilities") or {}
    projected_specialties: List[str] = []
    projected_service_formats: List[str] = []
    projected_life_stages: List[str] = []
    projected_philosophy = ""
    projected_serviced_suburbs: List[str] = []
    projected_catchment_type = ""
    projected_delivery_constraints: Dict[str, Any] = {}

    if capabilities:
        # Evaluate structured facts
        for cat, fact in capabilities.items():
            if not isinstance(fact, dict):
                continue
            # Re-evaluate freshness using active policy
            freshness_state, is_fresh = compute_capability_freshness(
                str(fact.get("confirmed_at") or ""),
                str(fact.get("basis") or "ai_proposed"),
                as_of=as_of,
                policy=active_policy,
            )
            basis = str(fact.get("basis") or "ai_proposed")
            is_valid = bool((fact.get("validation_result") or {}).get("valid", True))
            is_permitted = (
                (basis in active_policy.permitted_bases)
                and is_valid
                and is_fresh
                and not fact.get("invalidation_reason")
                and not fact.get("invalidated_at")
            )
            if not is_permitted:
                continue

            val = fact.get("canonical_value")
            if cat == "specialties" and isinstance(val, list):
                projected_specialties = val
            elif cat == "service_formats" and isinstance(val, list):
                projected_service_formats = val
            elif cat == "life_stages" and isinstance(val, list):
                projected_life_stages = val
            elif cat == "training_philosophy" and isinstance(val, str):
                projected_philosophy = val
            elif cat == "serviced_suburbs" and isinstance(val, list):
                projected_serviced_suburbs = val
            elif cat == "catchment_type" and isinstance(val, str):
                projected_catchment_type = val
            elif cat == "delivery_constraints" and isinstance(val, dict):
                projected_delivery_constraints = val
    else:
        # R1: Missing provenance is NOT promoted to a trainer declaration.
        # Legacy records without structured capabilities fail closed unless explicit test fixture basis is provided.
        test_fixture_basis = str(trainer_doc.get("_test_fixture_basis") or "")
        if test_fixture_basis in active_policy.permitted_bases:
            confirmed_ts = str(trainer_doc.get("created_at") or trainer_doc.get("updated_at") or now_iso())
            f_state, is_fresh = compute_capability_freshness(confirmed_ts, test_fixture_basis, as_of=as_of, policy=active_policy)
            if is_fresh:
                raw_specs = trainer_doc.get("specialties") or trainer_doc.get("services") or []
                v_spec = validate_capability_category("specialties", raw_specs)
                if v_spec["valid"]:
                    projected_specialties = v_spec["canonical_terms"]

                raw_fmts = trainer_doc.get("service_formats") or []
                v_fmt = validate_capability_category("service_formats", raw_fmts)
                if v_fmt["valid"]:
                    projected_service_formats = v_fmt["canonical_terms"]

                raw_phil = trainer_doc.get("training_philosophy") or trainer_doc.get("philosophy") or ""
                v_phil = validate_capability_category("training_philosophy", raw_phil)
                if v_phil["valid"]:
                    projected_philosophy = v_phil["canonical_terms"]

                raw_suburbs = trainer_doc.get("serviced_suburbs") or []
                v_sub = validate_capability_category("serviced_suburbs", raw_suburbs)
                if v_sub["valid"]:
                    projected_serviced_suburbs = v_sub["canonical_terms"]

                raw_catch = trainer_doc.get("catchment_type") or ""
                v_catch = validate_capability_category("catchment_type", raw_catch)
                if v_catch["valid"]:
                    projected_catchment_type = v_catch["canonical_terms"]
            else:
                reasons.append("legacy_trainer_declaration_stale")
        else:
            is_eligible = False
            reasons.append("legacy_unconfirmed_provenance")

    # Minimum capability requirement for matching
    if active_policy.require_specialties_or_formats:
        if not projected_specialties and not projected_service_formats:
            is_eligible = False
            reasons.append("no_permitted_matchable_capabilities")

    return {
        "trainer_id": str(trainer_doc.get("id") or ""),
        "name": str(trainer_doc.get("name") or ""),
        "suburb": str(trainer_doc.get("suburb") or ""),
        "region": str(trainer_doc.get("region") or "Greater Melbourne"),
        "serviced_suburbs": projected_serviced_suburbs,
        "catchment_type": projected_catchment_type,
        "service_formats": projected_service_formats,
        "specialties": projected_specialties,
        "life_stages": projected_life_stages,
        "training_philosophy": projected_philosophy,
        "delivery_constraints": projected_delivery_constraints,
        "projection_version": active_policy.version,
        "as_of": as_of_iso,
        "match_eligible": is_eligible,
        "eligibility_reasons": reasons,
    }


def assess_trainer_capability_health(
    trainer_doc: Dict[str, Any],
    *,
    as_of: Optional[datetime] = None,
    policy: Optional[CapabilityProjectionPolicy] = None,
) -> Dict[str, Any]:
    """Assess capability health and provenance for `/ops` visibility (zero owner PII)."""
    active_policy = policy or DEFAULT_PROJECTION_POLICY
    capabilities = trainer_doc.get("capabilities") or {}
    total_facts = len(capabilities)
    permitted_facts = 0
    stale_facts = 0
    ai_proposed_count = 0
    invalidated_count = 0
    rejected_terms: List[str] = []

    for fact in capabilities.values():
        if not isinstance(fact, dict):
            continue
        basis = str(fact.get("basis") or "")
        if basis == "ai_proposed":
            ai_proposed_count += 1
        freshness, is_fresh = compute_capability_freshness(
            str(fact.get("confirmed_at") or ""),
            basis,
            as_of=as_of,
            policy=active_policy,
        )
        if not is_fresh and freshness == "stale":
            stale_facts += 1
        if fact.get("invalidated_at") or fact.get("invalidation_reason"):
            invalidated_count += 1
        if fact.get("permitted_in_projection") and is_fresh and not fact.get("invalidation_reason") and not fact.get("invalidated_at") and (basis in active_policy.permitted_bases):
            permitted_facts += 1
        val_res = fact.get("validation_result") or {}
        rej = val_res.get("rejected_terms") or []
        rejected_terms.extend(rej)

    projection = build_match_ready_projection(trainer_doc, as_of=as_of, policy=active_policy)

    return {
        "trainer_id": str(trainer_doc.get("id") or ""),
        "name": str(trainer_doc.get("name") or ""),
        "has_structured_capabilities": total_facts > 0,
        "total_facts": total_facts,
        "permitted_facts": permitted_facts,
        "stale_facts": stale_facts,
        "invalidated_facts": invalidated_count,
        "ai_proposed_unconfirmed": ai_proposed_count,
        "rejected_terms": rejected_terms,
        "match_eligible": projection["match_eligible"],
        "eligibility_reasons": projection["eligibility_reasons"],
    }


async def compute_capability_health_summary(
    trainers_coll: Any,
    *,
    as_of: Optional[datetime] = None,
    policy: Optional[CapabilityProjectionPolicy] = None,
) -> Dict[str, int]:
    """Compute aggregate capability health metrics across all trainers for /ops visibility.

    Evaluates effective projection logic across all trainers. Zero owner PII.
    Provides actionable, non-PII reason categories.
    """
    active_policy = policy or DEFAULT_PROJECTION_POLICY
    cursor = trainers_coll.find({}, {
        "_id": 0,
        "id": 1,
        "name": 1,
        "suburb": 1,
        "published": 1,
        "claim_status": 1,
        "contact_ready": 1,
        "abn_status": 1,
        "abn_verified": 1,
        "phone": 1,
        "email": 1,
        "website": 1,
        "capabilities": 1,
        "source_url": 1,
        "source_evidence_url": 1,
    })

    if hasattr(cursor, "to_list"):
        trainers = await cursor.to_list(10000)
    else:
        trainers = list(cursor)

    total_trainers = len(trainers)
    match_eligible_count = 0
    missing_declaration_count = 0
    ai_proposed_unconfirmed_count = 0
    stale_count = 0
    invalidated_count = 0
    ownership_disputed_count = 0
    suppressed_or_unpublished_count = 0
    contact_gate_count = 0

    for t in trainers:
        proj = build_match_ready_projection(t, as_of=as_of, policy=active_policy)
        reasons = proj.get("eligibility_reasons") or []
        caps = t.get("capabilities") or {}

        if proj.get("match_eligible"):
            match_eligible_count += 1
            continue

        # Classify reasons
        if "ownership_disputed" in reasons or str(t.get("claim_status") or "").lower() == "claim_disputed":
            ownership_disputed_count += 1
        elif "profile_not_published" in reasons or "statutory_abn_revoked" in reasons:
            suppressed_or_unpublished_count += 1
        elif "not_contact_ready" in reasons:
            contact_gate_count += 1
        elif any(isinstance(f, dict) and (f.get("invalidated_at") or f.get("invalidation_reason")) for f in caps.values()):
            invalidated_count += 1
        elif any(isinstance(f, dict) and compute_capability_freshness(str(f.get("confirmed_at") or ""), str(f.get("basis") or ""), as_of=as_of, policy=active_policy)[0] == "stale" for f in caps.values()):
            stale_count += 1
        elif any(isinstance(f, dict) and f.get("basis") == "ai_proposed" for f in caps.values()):
            ai_proposed_unconfirmed_count += 1
        else:
            missing_declaration_count += 1

    return {
        "policy_version": active_policy.version,
        "permitted_bases": list(active_policy.permitted_bases),
        "total_trainers": total_trainers,
        "match_eligible_trainers": match_eligible_count,
        "missing_declaration": missing_declaration_count,
        "ai_proposed_unconfirmed": ai_proposed_unconfirmed_count,
        "stale_capabilities": stale_count,
        "invalidated_capabilities": invalidated_count,
        "ownership_disputed": ownership_disputed_count,
        "suppressed_or_unpublished": suppressed_or_unpublished_count,
        "not_contact_ready": contact_gate_count,
    }
