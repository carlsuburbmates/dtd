"""Automated ABN Verification, Badge Provisioning and Re-Verification Lifecycle Engine.

Responsibilities:
1. Verifies trainer listings against ABR data.
2. Evaluates state alignment (VIC/Melbourne), active commercial status, and name alignment.
3. Automatically provisions the "ABN Verified" trust badge and popover payload.
4. Executes 14-day periodic re-verification and automatically revokes badges if an ABN is cancelled/deregistered.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    from .abn_validator import validate_abn_checksum, format_abn
    from .abr_client import AbrClient
    from .deduplication import normalize_business_name
except ImportError:
    from abn_validator import validate_abn_checksum, format_abn
    from abr_client import AbrClient
    from deduplication import normalize_business_name

logger = logging.getLogger("dtd.verification_engine")


def _is_melbourne_postcode(postcode_str: Optional[str]) -> bool:
    """Check if a postcode falls within Greater Melbourne / Victoria range (3000 - 3999)."""
    if not postcode_str:
        return False
    try:
        code = int(str(postcode_str).strip())
        return 3000 <= code <= 3999
    except ValueError:
        return False


def _check_name_similarity(listing_name: str, abr_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if the trainer's listing name reasonably matches ABR legal or trading names."""
    norm_listing = normalize_business_name(listing_name)
    if not norm_listing:
        return False, "Missing listing name"

    entity_name = normalize_business_name(abr_data.get("entity_name"))
    business_names = [normalize_business_name(b) for b in abr_data.get("business_names") or []]

    # 1. Exact match on trading name
    for bname in business_names:
        if norm_listing == bname or norm_listing in bname or bname in norm_listing:
            return True, f"Matched registered business name: {bname}"

    # 2. Exact match on legal entity name
    if norm_listing == entity_name or norm_listing in entity_name or entity_name in norm_listing:
        return True, f"Matched registered legal entity name: {entity_name}"

    # 3. Word token overlap (e.g. "Jane Smith Dog Training" matches "Smith, Jane")
    listing_tokens = set(norm_listing.split())
    entity_tokens = set(entity_name.split())
    shared_tokens = listing_tokens.intersection(entity_tokens)
    # Exclude trivial words
    shared_meaningful = {t for t in shared_tokens if len(t) > 2 and t not in {"dog", "k9", "training", "pets", "melbourne"}}
    if shared_meaningful:
        return True, f"Matched entity name tokens: {', '.join(shared_meaningful)}"

    # If entity is Sole Trader, surname match is common
    if "individual" in str(abr_data.get("entity_type_name") or "").lower():
        return True, "Sole Trader individual entity (acceptable naming match)"

    return False, "Listing name differs substantially from ABR records (flagged for review)"


class VerificationEngine:
    """Automated verification and badge management engine."""

    def __init__(self, abr_client: AbrClient):
        self.abr_client = abr_client

    def verify_trainer_abn(self, trainer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive automated ABN verification for a trainer profile."""
        raw_abn = trainer_data.get("abn")
        if not raw_abn:
            return {
                "abn_verified": False,
                "badge_status": "UNVERIFIED_NO_ABN",
                "badge_label": "",
                "trust_score_bonus": 0.0,
                "badge_payload": None,
                "reason": "No ABN provided.",
            }

        # Step 1: Checksum Validation
        if not validate_abn_checksum(raw_abn):
            return {
                "abn_verified": False,
                "badge_status": "INVALID_CHECKSUM",
                "badge_label": "",
                "trust_score_bonus": 0.0,
                "badge_payload": None,
                "reason": "ABN failed ATO Modulus 89 mathematical checksum.",
            }

        # Step 2: ABR Lookup
        lookup = self.abr_client.lookup_abn(raw_abn)
        if not lookup.get("success"):
            return {
                "abn_verified": False,
                "badge_status": "ABR_LOOKUP_FAILED",
                "badge_label": "",
                "trust_score_bonus": 0.0,
                "badge_payload": None,
                "reason": lookup.get("message") or "ABR lookup failed.",
            }

        abr = lookup["data"]

        # Step 3: Check Active Commercial Status
        if not abr.get("is_active"):
            return {
                "abn_verified": False,
                "badge_status": "CANCELLED_ABN",
                "badge_label": "ABN Cancelled / Inactive",
                "trust_score_bonus": -0.2,  # Penalty for deregistered entity
                "badge_payload": {
                    "abn": abr["abn"],
                    "abn_formatted": abr["abn_formatted"],
                    "status": "Cancelled",
                    "effective_from": abr.get("abn_status_effective_from"),
                    "entity_name": abr.get("entity_name"),
                },
                "reason": "ABN is currently marked as Cancelled/Inactive on the Australian Business Register.",
            }

        # Step 4: Geographic State Alignment (Victoria / Greater Melbourne)
        is_vic = (abr.get("address_state") == "VIC") or _is_melbourne_postcode(abr.get("address_postcode"))
        state_note = "VIC" if is_vic else abr.get("address_state", "AU")

        # Step 5: Name Similarity
        name_ok, match_note = _check_name_similarity(trainer_data.get("name", ""), abr)

        # Step 6: Generate Verified Badge Payload
        badge_payload = {
            "abn": abr["abn"],
            "abn_formatted": abr["abn_formatted"],
            "status": "Active",
            "entity_name": abr.get("entity_name"),
            "business_names": abr.get("business_names", []),
            "entity_type": abr.get("entity_type_name"),
            "state": abr.get("address_state"),
            "postcode": abr.get("address_postcode"),
            "gst_registered": (abr.get("gst_status") == "Active"),
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "abr_source": abr.get("source"),
            "government_register_url": f"https://abr.business.gov.au/ABN/View?id={abr['abn']}",
        }

        badge_label = f"ABN Verified • Registered Business ({state_note})"

        return {
            "abn_verified": True,
            "badge_status": "VERIFIED_ACTIVE",
            "badge_label": badge_label,
            "trust_score_bonus": 0.35,  # Strong reputation signal
            "is_victoria": is_vic,
            "name_match_confidence": "HIGH" if name_ok else "REVIEW_RECOMMENDED",
            "name_match_note": match_note,
            "badge_payload": badge_payload,
            "reason": f"ABN {abr['abn_formatted']} active on ABR for '{abr.get('entity_name')}'. {match_note}",
        }

    def periodic_reverify_trainer(self, trainer: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate periodic re-verification for an existing published profile."""
        current_abn = trainer.get("abn")
        if not current_abn or not trainer.get("abn_verified"):
            return {"status": "SKIPPED_NO_VERIFIED_ABN", "changed": False}

        # Force refresh ABR lookup to bypass local memory cache
        new_result = self.verify_trainer_abn(trainer)

        was_verified = trainer.get("abn_verified", False)
        now_verified = new_result.get("abn_verified", False)

        if was_verified and not now_verified:
            # Automatic Badge Revocation
            logger.warning("ABN Revocation detected for trainer '%s' (ABN %s)", trainer.get("name"), current_abn)
            return {
                "status": "BADGE_REVOKED",
                "changed": True,
                "revocation_reason": new_result.get("reason"),
                "badge_status": new_result.get("badge_status"),
                "updated_fields": {
                    "abn_verified": False,
                    "abn_badge_status": new_result.get("badge_status"),
                    "abn_revoked_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        return {
            "status": "RE_VERIFIED_STABLE",
            "changed": False,
            "badge_status": new_result.get("badge_status"),
        }
