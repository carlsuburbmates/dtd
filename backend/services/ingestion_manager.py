"""Automated Trainer Acquisition & Ingestion Orchestrator (Engine 1).

Implements the serverless batch ingestion pipeline:
- Respects polite crawling (2.05s per-domain delay, robots.txt, 5s connect / 10s read timeouts).
- Uses Gemini on Vertex AI (with ADC or local API key) for structured fact extraction.
- Validates statutory identity via ATO Modulus 89 check and ABR Web Services.
- Enforces 4-tier deduplication (ABN -> domain -> phone -> name+suburb).
- Unconditionally protects claimed/paid profiles from being overwritten.
- Persists state to db.trainers and db.source_ingestion_state with /ops compatibility.
- Eliminates DF-014: statutory ABR status + reachability gate publication, never AI confidence.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import html
import json
import logging
import os
from pathlib import Path
import re
import socket
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from .abn_validator import format_abn, normalize_abn, validate_abn_detailed
from .abr_client import AbrClient
from . import ai
from . import deduplication
from . import source_approvals
from .trainer_quality import (
    check_dns_resolvable,
    check_source_reachability,
    extract_domain,
    find_existing_trainer,
    is_claimed_profile,
    now_iso,
    package_trainer_capabilities,
    publishing_quality,
    record_ingestion_failure,
    record_ingestion_success,
    validate_candidate_schema,
    validate_iso8601_utc,
)

logger = logging.getLogger(__name__)

USER_AGENT = "DTD-Bot/1.0 (+https://dogtrainersdirectory.com.au)"
DEFAULT_CONNECT_TIMEOUT_S = 5.0
DEFAULT_READ_TIMEOUT_S = 10.0
CRAWL_POLITE_DELAY_S = 2.05

_last_domain_crawl_time: Dict[str, float] = {}


def _normalise_html(text: str) -> str:
    """Strip tags and decode entities for structured text extraction."""
    without_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    decoded = html.unescape(without_tags)
    return " ".join(decoded.split())


async def polite_fetch_url(url: str, session: requests.Session) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]], str]:
    """Fetch an official business page respecting robots.txt and polite crawl delays.

    Returns:
        (ok, text_content, page_metadata, error_message)
    """
    domain = extract_domain(url)
    dns_ok, dns_msg = check_dns_resolvable(domain)
    if not dns_ok:
        return False, None, None, f"dns_unresolvable:{dns_msg}"

    # Polite per-domain rate limiting
    now = time.monotonic()
    last_time = _last_domain_crawl_time.get(domain, 0.0)
    elapsed = now - last_time
    if elapsed < CRAWL_POLITE_DELAY_S:
        await asyncio.sleep(CRAWL_POLITE_DELAY_S - elapsed)
    _last_domain_crawl_time[domain] = time.monotonic()

    # Parse robots.txt
    robots_url = f"https://{domain}/robots.txt"
    rp = RobotFileParser()
    try:
        r_resp = session.get(robots_url, timeout=(DEFAULT_CONNECT_TIMEOUT_S, DEFAULT_READ_TIMEOUT_S))
        if r_resp.ok:
            rp.parse(r_resp.text.splitlines())
        else:
            rp.parse([])
    except Exception:
        rp.parse([])

    if not rp.can_fetch(USER_AGENT, url):
        return False, None, None, f"robots_denied:{url}"

    # Fetch main page
    try:
        resp = session.get(url, timeout=(DEFAULT_CONNECT_TIMEOUT_S, DEFAULT_READ_TIMEOUT_S))
        if not resp.ok:
            return False, None, None, f"http_{resp.status_code}:{url}"

        text = _normalise_html(resp.text)
        metadata = {
            "url": str(resp.url),
            "http_status": resp.status_code,
            "sha256": hashlib.sha256(resp.content).hexdigest(),
        }
        return True, text, metadata, "ok"
    except requests.Timeout:
        return False, None, None, f"http_timeout:{url}"
    except Exception as exc:
        return False, None, None, f"fetch_error:{exc}"


async def resolve_candidate_source_urls(
    source_urls: Optional[List[str]],
    db: Any,
    batch_size: int = 10,
) -> List[Dict[str, Any]]:
    """Resolve candidate URLs to process.

    Order of resolution (Gap 1 Fix):
    1. Explicit source_urls parameter if supplied.
    2. Pending entries from db.discovery_queue.
    3. Fallback to un-crawled seed catalog URLs from data/melbourne_trainers_seed.json.
    """
    candidates: List[Dict[str, Any]] = []

    # 1. Explicit list provided
    if source_urls:
        for u in source_urls[:batch_size]:
            cleaned = str(u).strip()
            if cleaned:
                candidates.append({"url": cleaned, "source": "explicit_request", "queue_id": None})
        return candidates

    # 2. Check db.discovery_queue
    if db is not None:
        coll = getattr(db, "discovery_queue", None)
        if coll is not None:
            try:
                pending = await coll.find({"status": "pending"}, {"_id": 0}).limit(batch_size).to_list(batch_size)
                for entry in pending:
                    url = str(entry.get("url") or "").strip()
                    if url:
                        candidates.append({
                            "url": url,
                            "source": "discovery_queue",
                            "queue_id": entry.get("id"),
                            "hint_name": entry.get("hint_name", ""),
                            "hint_suburb": entry.get("hint_suburb", ""),
                            "hint_phone": entry.get("hint_phone", ""),
                            "hint_abn": entry.get("hint_abn", ""),
                        })
                if candidates:
                    return candidates
            except Exception as exc:
                logger.warning("Failed querying db.discovery_queue: %s", exc)

    # 3. Fallback to melbourne_trainers_seed.json
    seed_path = Path(__file__).resolve().parent.parent / "data" / "melbourne_trainers_seed.json"
    if seed_path.is_file():
        try:
            data = json.loads(seed_path.read_text(encoding="utf-8"))
            items = data.get("trainers") or data if isinstance(data, list) else []
            for item in items[:batch_size]:
                url = str(item.get("website") or item.get("source_url") or "").strip()
                if url:
                    candidates.append({
                        "url": url,
                        "source": "seed_catalog",
                        "queue_id": None,
                        "hint_name": item.get("name", ""),
                        "hint_suburb": item.get("suburb", ""),
                        "hint_phone": item.get("phone", ""),
                        "hint_abn": item.get("abn", ""),
                        "seed_item": item,
                    })
        except Exception as exc:
            logger.warning("Failed loading seed catalogue: %s", exc)

    return candidates


async def run_batch_ingestion_pipeline(
    source_urls: Optional[List[str]] = None,
    db: Any = None,
    *,
    dry_run: bool = False,
    batch_size: int = 10,
) -> Dict[str, Any]:
    """Execute the automated batch ingestion pipeline.

    Processes source URLs through polite fetch -> Gemini extraction -> ABR lookup ->
    4-tier deduplication -> quality scoring -> atomic persistence.
    """
    start_ts = now_iso()
    summary: Dict[str, Any] = {
        "ok": True,
        "started_at": start_ts,
        "completed_at": "",
        "total_resolved": 0,
        "total_processed": 0,
        "qualified": 0,
        "held": 0,
        "updated_unclaimed": 0,
        "skipped_claimed": 0,
        "errors": [],
    }

    # Verify source governance policy
    registry = source_approvals.load()
    if not source_approvals.approved(registry, "public_business_websites", "trainer_profile_source"):
        err = "Source policy check failed: public_business_websites is not approved for trainer_profile_source"
        summary["ok"] = False
        summary["errors"].append({"source_url": "system", "error": err})
        return summary

    # Resolve target candidate URLs
    candidates = await resolve_candidate_source_urls(source_urls, db, batch_size=batch_size)
    summary["total_resolved"] = len(candidates)
    if not candidates:
        summary["completed_at"] = now_iso()
        return summary

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    abr_client = AbrClient(db)

    for item in candidates:
        url = item["url"]
        summary["total_processed"] += 1

        try:
            # 1. Polite fetch & robots check
            fetch_ok, text_content, page_meta, fetch_err = await polite_fetch_url(url, session)
            if not fetch_ok or not text_content:
                await record_ingestion_failure(db, url, fetch_err, dry_run=dry_run)
                summary["held"] += 1
                summary["errors"].append({"source_url": url, "error": fetch_err})
                if item.get("queue_id") and db is not None and not dry_run:
                    await db.discovery_queue.update_one(
                        {"id": item["queue_id"]},
                        {"$set": {"status": "held", "reason": fetch_err, "processed_at": now_iso()}},
                    )
                continue

            # 2. Extract structured trainer facts using Gemini on Vertex AI
            extraction = await ai.extract_trainer_source(
                {"raw_text": text_content, "source_url": url, "hints": item},
                db=db,
            )

            # Heuristic / Hint field reconciliation
            name = str(item.get("hint_name") or "").strip()
            if not name:
                # Extract plausible business title from domain or first header line
                domain_parts = extract_domain(url).split(".")
                name = domain_parts[0].replace("-", " ").title() if domain_parts else "Independent Trainer"

            suburb = str(item.get("hint_suburb") or "").strip()
            if not suburb:
                serviced = extraction.get("serviced_suburbs") or []
                suburb = serviced[0] if serviced and serviced[0] != "Melbourne-Wide Mobile" else "Melbourne"

            phone = str(item.get("hint_phone") or "").strip()
            abn = normalize_abn(item.get("hint_abn"))

            # If ABN not in hint, search text for 11-digit ABN
            if not abn:
                abn_match = re.search(r"\b(\d{2}\s*\d{3}\s*\d{3}\s*\d{3}|\d{11})\b", text_content)
                if abn_match:
                    possible_abn = normalize_abn(abn_match.group(1))
                    if validate_abn_detailed(possible_abn)["valid"]:
                        abn = possible_abn

            # 3. Statutory ABR check (ATO Modulus 89 + ABR Web Services)
            abr_evidence: Dict[str, Any] = {}
            if abn:
                abr_res = await abr_client.lookup(abn)
                if abr_res.get("ok"):
                    abr_evidence = abr_res.get("data") or {}

            retrieved_at = now_iso()
            candidate_doc: Dict[str, Any] = {
                "name": name,
                "suburb": suburb,
                "website": url,
                "phone": phone,
                "email": "",
                "abn": abn,
                "source_url": url,
                "source_type": "business_website",
                "retrieved_at": retrieved_at,
                "services": extraction.get("specialties") or ["Puppy Training", "Obedience"],
                "specialties": extraction.get("specialties") or [],
                "service_formats": extraction.get("service_formats") or ["in_home"],
                "philosophy": extraction.get("training_philosophy") or "Positive Reinforcement / Force-Free",
                "raw_evidence": {
                    "source_url": url,
                    "matched_name": name,
                    "matched_suburb": suburb,
                    "matched_website": url,
                    "source_pages": [page_meta] if page_meta else [],
                    "ai_extraction": extraction,
                },
                "abr_evidence": abr_evidence,
            }

            # 4. Canonical Publishing Quality Assessment
            quality = publishing_quality(candidate_doc)
            is_active_abn = bool(abr_evidence.get("is_active")) and quality.get("active_abn_evidence")

            # DF-014 Remediation: Only statutory active ABR + reachability + quality eligibility can publish
            is_eligible_to_publish = bool(quality.get("eligible")) and is_active_abn

            # 5. 4-Tier Deduplication & Claimed Profile Protection
            existing = await find_existing_trainer(db, candidate_doc) if db is not None else None

            if existing:
                trainer_id = existing["id"]
                if is_claimed_profile(existing):
                    # Unconditional protection for claimed profiles
                    summary["skipped_claimed"] += 1
                    if db is not None and not dry_run:
                        # Only record source evidence; never overwrite profile fields
                        await db.trainers.update_one(
                            {"id": trainer_id},
                            {"$set": {"source_last_crawled_at": retrieved_at}},
                        )
                        await record_ingestion_success(db, candidate_doc, trainer_id, dry_run=dry_run)
                        if item.get("queue_id"):
                            await db.discovery_queue.update_one(
                                {"id": item["queue_id"]},
                                {"$set": {"status": "promoted", "trainer_id": trainer_id, "processed_at": retrieved_at}},
                            )
                    continue

                # Unclaimed existing profile update
                summary["updated_unclaimed"] += 1
                if db is not None and not dry_run:
                    update_fields: Dict[str, Any] = {
                        "source_last_crawled_at": retrieved_at,
                        "ingestion_quality_score": quality.get("score", 0.0),
                    }
                    if is_eligible_to_publish:
                        update_fields["published"] = True
                        update_fields["ingestion_quality_status"] = "qualified"
                        update_fields["abn_verified"] = True
                        update_fields["abn_verified_at"] = retrieved_at
                    await db.trainers.update_one({"id": trainer_id}, {"$set": update_fields})
                    await record_ingestion_success(db, candidate_doc, trainer_id, dry_run=dry_run)
                    if item.get("queue_id"):
                        await db.discovery_queue.update_one(
                            {"id": item["queue_id"]},
                            {"$set": {"status": "promoted", "trainer_id": trainer_id, "processed_at": retrieved_at}},
                        )
                continue

            # 6. New Profile Insertion
            trainer_id = f"trainer_{hashlib.sha1(url.encode('utf-8')).hexdigest()[:12]}"
            ai_capabilities = package_trainer_capabilities(
                specialties=candidate_doc.get("specialties"),
                service_formats=candidate_doc.get("service_formats"),
                training_philosophy=candidate_doc.get("philosophy"),
                serviced_suburbs=[suburb] if suburb else [],
                basis="ai_proposed",
                evidence_reference=url,
                confirmed_at=retrieved_at,
            )
            new_trainer: Dict[str, Any] = {
                "id": trainer_id,
                "name": name,
                "suburb": suburb,
                "region": "Greater Melbourne",
                "website": url,
                "phone": phone,
                "email": "",
                "services": candidate_doc["services"],
                "specialties": candidate_doc["specialties"],
                "service_formats": candidate_doc["service_formats"],
                "philosophy": candidate_doc["philosophy"],
                "capabilities": ai_capabilities,
                "bio": f"Professional dog training services based in {suburb}, Melbourne.",
                "image_url": "",
                "source_evidence_url": url,
                "abn": format_abn(abn) if abn else "",
                "abn_verified": is_active_abn,
                "abn_verified_at": retrieved_at if is_active_abn else "",
                "published": is_eligible_to_publish,
                "contact_ready": bool(phone or url),
                "ingestion_quality_status": "qualified" if is_eligible_to_publish else "held",
                "ingestion_hold_reason": "" if is_eligible_to_publish else "statutory_or_quality_evidence_required",
                "ingestion_quality_score": quality.get("score", 0.0),
                "created_at": retrieved_at,
                "claimed": False,
                "tier": "free",
            }

            if is_eligible_to_publish:
                summary["qualified"] += 1
            else:
                summary["held"] += 1

            if db is not None and not dry_run:
                await db.trainers.insert_one(new_trainer)
                await record_ingestion_success(db, candidate_doc, trainer_id, dry_run=dry_run)
                if item.get("queue_id"):
                    await db.discovery_queue.update_one(
                        {"id": item["queue_id"]},
                        {"$set": {
                            "status": "promoted" if is_eligible_to_publish else "held",
                            "trainer_id": trainer_id,
                            "processed_at": retrieved_at,
                        }},
                    )

        except Exception as exc:
            logger.exception("Error processing candidate source %s: %s", url, exc)
            summary["held"] += 1
            summary["errors"].append({"source_url": url, "error": str(exc)})
            await record_ingestion_failure(db, url, str(exc), dry_run=dry_run)

    summary["completed_at"] = now_iso()
    return summary
