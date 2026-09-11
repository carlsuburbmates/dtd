"""End-to-End Test Suite for ABN Validation, ABR Client, Deduplication and Verification.

Run with:
    pytest abn-automation-poc/test_pipeline_e2e.py -v
or:
    python abn-automation-poc/test_pipeline_e2e.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from abn_validator import (
    validate_abn_checksum,
    validate_abn_detailed,
    normalize_abn,
    format_abn,
)
from abr_client import AbrClient, MOCK_ABR_DATABASE
from deduplication import DeduplicationEngine, normalize_phone_au, normalize_domain
from verification_engine import VerificationEngine

CURRENT_DIR = Path(__file__).parent
TEST_DATA_FILE = CURRENT_DIR / "test_data.json"


def load_test_data() -> Dict[str, Any]:
    with open(TEST_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ==========================================
# 1. ABN Validator Tests (ATO Modulus 89)
# ==========================================


def test_valid_abn_checksums():
    """Verify mathematically valid Australian Business Numbers."""
    valid_abns = [
        "51 824 753 556",  # RSPCA Victoria
        "33 051 775 556",  # Telstra
        "16 009 661 901",  # Qantas
        "48 123 123 124",  # Commonwealth Bank
        "28 864 970 579",  # Australia Post
        "10 000 000 032",  # Melbourne Trainer Sole Trader
        "10 000 000 064",  # Melbourne Trainer Pty Ltd
    ]
    for abn in valid_abns:
        assert validate_abn_checksum(abn) is True, f"Expected {abn} to be mathematically valid."
        res = validate_abn_detailed(abn)
        assert res["valid"] is True
        assert res["error_code"] == "OK"


def test_invalid_abn_checksums():
    """Verify detection of invalid ABNs, typos, and bad lengths."""
    invalid_cases = [
        ("12 345 678 901", "CHECKSUM_FAILED"),
        ("12345", "INVALID_LENGTH"),
        ("1234567890123", "INVALID_LENGTH"),
        ("", "EMPTY_INPUT"),
        ("abcdefghijk", "NO_DIGITS"),
    ]
    for raw, expected_error in invalid_cases:
        assert validate_abn_checksum(raw) is False
        res = validate_abn_detailed(raw)
        assert res["valid"] is False
        assert res["error_code"] == expected_error


def test_abn_formatting():
    """Verify standard Australian 2-3-3-3 spacing display format."""
    assert format_abn("51824753556") == "51 824 753 556"
    assert format_abn("51 8247 53556") == "51 824 753 556"


# ==========================================
# 2. ABR Client & Cache Tests
# ==========================================


def test_abr_client_lookup():
    """Verify ABR client retrieval, JSON parsing, and active status checks."""
    client = AbrClient(use_mock_fallback=True)

    # Active Victorian Trainer
    res = client.lookup_abn("10000000032")
    assert res["success"] is True
    data = res["data"]
    assert data["abn"] == "10000000032"
    assert data["is_active"] is True
    assert data["is_victoria"] is True
    assert "MELBOURNE K9 BALANCE" in data["business_names"]

    # Cancelled ABN
    res_canc = client.lookup_abn("10000000096")
    assert res_canc["success"] is True
    assert res_canc["data"]["is_active"] is False
    assert res_canc["data"]["abn_status"] == "Cancelled"


def test_abr_client_caching():
    """Verify that second lookup hits the cache."""
    client = AbrClient(use_mock_fallback=True)
    first_res = client.lookup_abn("51824753556")
    assert first_res["success"] is True
    assert first_res["data"]["cached"] is False

    second_res = client.lookup_abn("51824753556")
    assert second_res["success"] is True
    assert second_res["data"]["cached"] is True


# ==========================================
# 3. Deduplication & Delisting Tests
# ==========================================


def test_delisting_suppression():
    """Verify that opted-out / delisted trainers are detected and blocked."""
    test_data = load_test_data()
    dedup = DeduplicationEngine(delisted_entities=test_data["delisted_suppression_list"])

    delisted_candidate = {
        "name": "Opted Out Trainer",
        "abn": "10 000 000 000",
        "phone": "0499 999 999",
        "website": "https://optouttrainer.com.au",
    }
    is_suppressed, reason = dedup.is_delisted(delisted_candidate)
    assert is_suppressed is True
    assert "delisted suppression list" in reason

    allowed_candidate = {
        "name": "Allowed Trainer",
        "abn": "51 824 753 556",
        "phone": "03 9224 2222",
    }
    is_suppressed2, _ = dedup.is_delisted(allowed_candidate)
    assert is_suppressed2 is False


def test_deduplication_entity_merging():
    """Verify matching across ABN, Phone, Domain and merging rich fields."""
    dedup = DeduplicationEngine()
    existing_trainers = [
        {
            "id": "tr_001",
            "name": "Positive K9 Training",
            "suburb": "Hawthorn",
            "abn": "10 000 000 064",
            "phone": "03 9819 0000",
            "website": "https://positivek9training.com.au",
            "services": ["In-home training"],
            "gallery_images": ["https://img1.jpg"],
        }
    ]

    # Incoming duplicate with same ABN but extra services and new photos
    incoming_duplicate = {
        "id": "cand_duplicate",
        "name": "Positive K9 Melbourne East",
        "abn": "10 000 000 064",
        "phone": "03 9819 0000",
        "website": "https://positivek9training.com.au/suburbs",
        "services": ["Puppy school", "Agility"],
        "gallery_images": ["https://img2.jpg"],
        "source_name": "google_places_harvest",
    }

    match_result = dedup.find_match(incoming_duplicate, existing_trainers)
    assert match_result is not None
    canonical, match_reason = match_result
    assert match_reason == "ABN_MATCH"
    assert canonical["id"] == "tr_001"

    merged = dedup.merge_records(canonical, incoming_duplicate, match_reason)
    # Check that services were merged without duplicates
    assert "In-home training" in merged["services"]
    assert "Puppy school" in merged["services"]
    assert "Agility" in merged["services"]
    # Check photos were merged
    assert "https://img1.jpg" in merged["gallery_images"]
    assert "https://img2.jpg" in merged["gallery_images"]


# ==========================================
# 4. Verification Engine & Badge Lifecycle
# ==========================================


def test_verification_badge_activation():
    """Verify that a valid active Melbourne ABN provisions the Verified Badge payload."""
    abr_client = AbrClient(use_mock_fallback=True)
    engine = VerificationEngine(abr_client)

    trainer_payload = {
        "name": "Melbourne K9 Balance",
        "suburb": "Richmond",
        "abn": "10 000 000 032",
        "phone": "0412 345 678",
    }

    result = engine.verify_trainer_abn(trainer_payload)
    assert result["abn_verified"] is True
    assert result["badge_status"] == "VERIFIED_ACTIVE"
    assert "ABN Verified" in result["badge_label"]
    assert result["trust_score_bonus"] > 0
    assert result["badge_payload"]["abn"] == "10000000032"
    assert result["badge_payload"]["status"] == "Active"
    assert result["badge_payload"]["state"] == "VIC"
    assert "https://abr.business.gov.au" in result["badge_payload"]["government_register_url"]


def test_verification_cancelled_abn_penalty():
    """Verify that a cancelled ABN is rejected and assigned a penalty."""
    abr_client = AbrClient(use_mock_fallback=True)
    engine = VerificationEngine(abr_client)

    cancelled_payload = {
        "name": "Old Dog Training Co",
        "suburb": "Melbourne",
        "abn": "10 000 000 096",
    }

    result = engine.verify_trainer_abn(cancelled_payload)
    assert result["abn_verified"] is False
    assert result["badge_status"] == "CANCELLED_ABN"
    assert result["trust_score_bonus"] < 0  # Penalty applied


def test_periodic_reverification_badge_revocation():
    """Verify that periodic re-verification detects cancellations and revokes badges."""
    abr_client = AbrClient(use_mock_fallback=True)
    engine = VerificationEngine(abr_client)

    # Previously verified trainer whose ABN is now cancelled
    trainer_profile = {
        "id": "tr_100",
        "name": "Old Dog Training Co",
        "abn": "10 000 000 096",
        "abn_verified": True,  # was verified
        "abn_badge_status": "VERIFIED_ACTIVE",
    }

    reverify_res = engine.periodic_reverify_trainer(trainer_profile)
    assert reverify_res["status"] == "BADGE_REVOKED"
    assert reverify_res["changed"] is True
    assert reverify_res["updated_fields"]["abn_verified"] is False
    assert reverify_res["updated_fields"]["abn_badge_status"] == "CANCELLED_ABN"


if __name__ == "__main__":
    print("Running standalone E2E pipeline tests...")
    test_valid_abn_checksums()
    test_invalid_abn_checksums()
    test_abn_formatting()
    test_abr_client_lookup()
    test_abr_client_caching()
    test_delisting_suppression()
    test_deduplication_entity_merging()
    test_verification_badge_activation()
    test_verification_cancelled_abn_penalty()
    test_periodic_reverification_badge_revocation()
    print("All 10 E2E pipeline tests passed successfully!")
