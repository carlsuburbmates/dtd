"""Lawful seed data loader for authentic Greater Melbourne dog-training businesses.

Replaces the unverified legacy baseline with candidates loaded from the
curated, primary-source candidate dataset at `backend/data/melbourne_trainers_seed.json`.

Zero invented trainer profiles, ABNs, services, locations, images, reviews, or
contact details. All candidates default to:
- tier: 'unclaimed'
- claim_status: 'unclaimed'
- abn_verified: False
- published: False
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

SEED_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "melbourne_trainers_seed.json"


def _load_candidates() -> List[Dict[str, Any]]:
    if not SEED_DATA_PATH.is_file():
        logger.warning("melbourne_trainers_seed.json not found at %s; seed supply is empty", SEED_DATA_PATH)
        return []
    try:
        with SEED_DATA_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        raw_candidates = data.get("candidates") or []
    except Exception as exc:
        logger.error("Failed to parse %s: %s", SEED_DATA_PATH, exc)
        return []

    processed: List[Dict[str, Any]] = []
    for cand in raw_candidates:
        # Build fail-closed candidate record
        entry = {
            "name": str(cand.get("name") or "").strip(),
            "suburb": str(cand.get("suburb") or "").strip(),
            "region": str(cand.get("region") or "Greater Melbourne").strip(),
            "website": str(cand.get("website") or "").strip(),
            "phone": str(cand.get("phone") or "").strip(),
            "email": str(cand.get("email") or "").strip(),
            "categories": list(cand.get("categories") or []),
            "services": list(cand.get("services") or []),
            "service_formats": list(cand.get("service_formats") or []),
            "training_philosophy": str(cand.get("training_philosophy") or "").strip(),
            "specialties": list(cand.get("specialties") or []),
            "bio": str(cand.get("bio") or "").strip(),
            "image_url": str(cand.get("image_url") or "").strip(),
            "source_evidence_url": str(cand.get("source_url") or "").strip(),
            "source_provenance": {
                "source_url": str(cand.get("source_url") or "").strip(),
                "source_type": str(cand.get("source_type") or "public_directory").strip(),
                "retrieved_at": str(cand.get("retrieved_at") or "").strip(),
                "raw_evidence": cand.get("raw_evidence") or {},
            },
            "tier": "unclaimed",
            "claim_status": "unclaimed",
            "abn": str(cand.get("abn") or "").strip(),
            "abn_status": "not_provided" if not cand.get("abn") else "pending_verification",
            "abn_verified": False,
            "abn_verified_at": "",
            "abn_verification_reason": "Candidate requires ABR lookup verification before public badge.",
        }
        processed.append(entry)
    return processed


MELBOURNE_TRAINERS: List[Dict[str, Any]] = _load_candidates()
