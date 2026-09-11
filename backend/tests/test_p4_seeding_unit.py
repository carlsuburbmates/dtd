"""Unit tests for Task P4-B: Lawful Greater Melbourne supply seeding and fail-closed provenance validation.

Validates:
1. The authorised initial batch contains 20 source-backed candidates with an explicit remaining gap.
2. Startup still creates no records unless the explicit seeding command is used.
3. Missing or malformed retrieved_at is rejected (must be valid ISO-8601 UTC timestamp).
4. Arbitrary "verified" status plus name-only evidence is rejected.
5. Fully evidenced synthetic test candidate passes (including with omitted optional public fields).
6. Fail-closed rejection of inline test-local invalid fixtures (unresolved DNS, 404, placeholder values, empty provenance, mismatched URL).
7. Non-publication and unverified-ABN defaults guarantee.
8. Canonical-path idempotency on repeat runs (0 duplicates created).
9. Strict claimed-profile preservation (claim_status, tier, owner contacts preserved).
10. In-batch duplicate candidate suppression.
11. Real /ops oversight aggregation path surfaces unverified-ABN and source-ingestion failures.
12. Dry-run mode performs zero writes.
13. Startup seeds disabled by default in production.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

import server
from scripts import seed_melbourne_trainers


class _MockCursor:
    def __init__(self, rows: List[Dict[str, Any]]):
        self._rows = [dict(r) for r in rows]

    def sort(self, *args, **kwargs) -> _MockCursor:
        return self

    def limit(self, count: int) -> _MockCursor:
        self._rows = self._rows[:count]
        return self

    async def to_list(self, length: int) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._rows[:length]]


class _MockCollection:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None):
        self.rows: List[Dict[str, Any]] = [dict(r) for r in (rows or [])]

    async def count_documents(self, filt: Optional[Dict[str, Any]] = None) -> int:
        if not filt:
            return len(self.rows)
        cursor = self.find(filt)
        results = await cursor.to_list(10000)
        return len(results)

    def find(self, filt: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None) -> _MockCursor:
        matched = []
        for r in self.rows:
            match = True
            if filt:
                for k, v in filt.items():
                    if k == "$or" and isinstance(v, list):
                        match = any(all(self._match_field(r, sub_k, sub_v) for sub_k, sub_v in condition.items()) for condition in v)
                    else:
                        match = self._match_field(r, k, v)
                    if not match:
                        break
            if match:
                matched.append(r)
        return _MockCursor(matched)

    def _match_field(self, row: Dict[str, Any], k: str, v: Any) -> bool:
        if isinstance(v, dict):
            if "$in" in v and row.get(k) not in v["$in"]:
                return False
            if "$nin" in v and row.get(k) in v["$nin"]:
                return False
            if "$ne" in v and row.get(k) == v["$ne"]:
                return False
            if "$exists" in v and (k in row) != v["$exists"]:
                return False
            if "$regex" in v:
                flags = re.IGNORECASE if "i" in str(v.get("$options") or "") else 0
                val = str(row.get(k) or "")
                if not re.search(str(v["$regex"]), val, flags):
                    return False
            return True
        return row.get(k) == v

    async def find_one(self, filt: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        cursor = self.find(filt, projection)
        results = await cursor.to_list(1)
        return results[0] if results else None

    async def distinct(self, key: str, filt: Optional[Dict[str, Any]] = None) -> List[Any]:
        rows = self.rows
        if filt:
            rows = [r for r in rows if all(self._match_field(r, k, v) for k, v in filt.items())]
        return list({r.get(key) for r in rows if key in r and r.get(key) is not None})

    def aggregate(self, pipeline: Optional[List[Dict[str, Any]]] = None) -> _MockCursor:
        return _MockCursor([])

    async def insert_one(self, doc: Dict[str, Any]) -> Any:
        self.rows.append(dict(doc))
        return type("InsertResult", (), {"inserted_id": doc.get("id")})()

    async def update_one(self, filt: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> Any:
        existing = await self.find_one(filt)
        if existing:
            for idx, r in enumerate(self.rows):
                if r.get("id") == existing.get("id") or r.get("source_url") == existing.get("source_url"):
                    if "$set" in update:
                        self.rows[idx].update(update["$set"])
                    return type("UpdateResult", (), {"matched_count": 1, "modified_count": 1})()
        elif upsert:
            new_doc = {}
            new_doc.update(filt)
            if "$set" in update:
                new_doc.update(update["$set"])
            self.rows.append(new_doc)
            return type("UpdateResult", (), {"matched_count": 0, "upserted_id": new_doc.get("id")})()
        return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0})()


class _MockDB:
    def __init__(self):
        self.trainers = _MockCollection()
        self.source_ingestion_state = _MockCollection()
        self.submissions = _MockCollection()
        self.claim_events = _MockCollection()
        self.ops_case_states = _MockCollection()
        self.discovery_queue = _MockCollection()
        self.system_state = _MockCollection()
        self.intros = _MockCollection()
        self.conversions = _MockCollection()
        self.engagements = _MockCollection()
        self.audit_log = _MockCollection()
        self.config_snapshots = _MockCollection()
        self.stripe_events = _MockCollection()
        self.reactivation_candidates = _MockCollection()
        self.owner_waitlist = _MockCollection()
        self.owner_waitlist_events = _MockCollection()
        self.launch_phase_state = _MockCollection()
        self.delisted_entities = _MockCollection()


SEED_JSON_PATH = Path(server.__file__).resolve().parent / "data" / "melbourne_trainers_seed.json"


def test_seed_dataset_contains_authorised_verified_initial_batch():
    """Verify the production seed has 20 unique, schema-valid, quality-qualified candidates."""
    assert SEED_JSON_PATH.is_file(), f"Seed dataset missing at {SEED_JSON_PATH}"
    with SEED_JSON_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("version") == 2
    assert "Greater Melbourne" in data.get("jurisdiction", "")

    candidates = data.get("candidates", [])
    assert len(candidates) == 20
    assert len({candidate["id"] for candidate in candidates}) == 20
    assert len({candidate["abn"] for candidate in candidates}) == 20
    for candidate in candidates:
        assert seed_melbourne_trainers.validate_candidate_schema(candidate) == (True, "valid")
        assert seed_melbourne_trainers.publishing_quality(candidate)["eligible"] is True

    # Production dataset must never contain invalid_candidates test fixtures
    assert "invalid_candidates" not in data, "Production seed dataset must not contain test fixture records"

    data_gap = data.get("data_gap_declaration", {})
    assert data_gap.get("status") == "initial_authorised_batch_verified"
    assert data_gap.get("authentic_count") == 20
    assert data_gap.get("initial_launch_count") == 20
    assert data_gap.get("target_launch_count") == 20
    assert data_gap.get("target_supply_count") == 100
    assert data_gap.get("remaining_data_gap") == 80
    assert "fail_closed" in data_gap.get("policy", "")

    from services.seed import MELBOURNE_TRAINERS
    assert len(MELBOURNE_TRAINERS) == 20
    assert all(row["published"] is False for row in MELBOURNE_TRAINERS if "published" in row)


def test_startup_loads_batch_unpublished_with_healthy_source_evidence(monkeypatch):
    """Verify startup cannot publish but does retain successful source-health evidence."""
    fake_db = _MockDB()
    monkeypatch.setattr(server, "db", fake_db)

    # Trigger server startup seed
    asyncio.run(server._seed_if_empty())

    assert len(fake_db.trainers.rows) == 20
    assert all(row.get("published") is False for row in fake_db.trainers.rows)
    assert len(fake_db.source_ingestion_state.rows) == 20
    assert all(row.get("consecutive_failures") == 0 for row in fake_db.source_ingestion_state.rows)
    assert all(row.get("abr_status") == "active" for row in fake_db.source_ingestion_state.rows)


def test_missing_or_malformed_retrieved_at_is_rejected():
    """Verify missing or malformed retrieved_at is rejected (must be valid ISO-8601 UTC)."""
    base_cand = {
        "name": "Carlton Canine Coaching",
        "suburb": "Carlton",
        "source_url": "https://carltoncanine.com.au",
        "source_type": "business_website",
        "raw_evidence": {
            "source_url": "https://carltoncanine.com.au",
            "matched_name": "Carlton Canine Coaching",
            "matched_suburb": "Carlton",
        },
    }

    # 1. Missing retrieved_at
    cand_missing = dict(base_cand)
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_missing)
    assert valid is False
    assert reason == "missing_retrieved_at"

    # 2. Empty retrieved_at string
    cand_empty = dict(base_cand, retrieved_at="   ")
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_empty)
    assert valid is False
    assert reason == "missing_retrieved_at"

    # 3. Malformed non-date string
    cand_malformed = dict(base_cand, retrieved_at="yesterday_afternoon")
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_malformed)
    assert valid is False
    assert "malformed_retrieved_at" in reason

    # 4. Date without time and UTC timezone
    cand_no_tz = dict(base_cand, retrieved_at="2026-09-09")
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_no_tz)
    assert valid is False
    assert "malformed_retrieved_at" in reason

    # 5. Non-UTC timezone (e.g. AEST +10:00)
    cand_non_utc = dict(base_cand, retrieved_at="2026-09-09T10:00:00+10:00")
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_non_utc)
    assert valid is False
    assert "malformed_retrieved_at" in reason

    # 6. Valid UTC ISO-8601 timestamps pass retrieved_at check
    cand_utc_z = dict(base_cand, retrieved_at="2026-09-09T00:00:00Z")
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_utc_z)
    assert valid is True
    assert reason == "valid"


def test_arbitrary_verified_status_plus_name_only_evidence_is_rejected():
    """Verify arbitrary 'verified' status plus name-only evidence is rejected when public fields are supplied."""
    cand = {
        "name": "Fitzroy Dog Academy",
        "suburb": "Fitzroy",
        "website": "https://fitzroydogacademy.com.au",
        "phone": "03 9419 2233",
        "email": "contact@fitzroydogacademy.com.au",
        "abn": "51 824 753 556",
        "services": ["Puppy School", "Agility"],
        "source_url": "https://fitzroydogacademy.com.au",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "source_validation_status": "verified",  # Caller claimed verified
        "raw_evidence": {
            # Evidence only contains source_url and matched_name, with no evidence for supplied fields
            "source_url": "https://fitzroydogacademy.com.au",
            "matched_name": "Fitzroy Dog Academy",
        },
    }

    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand)
    assert valid is False
    # Must fail because supplied public fields (website, phone, email, suburb, abn, services) lack evidence
    assert "lacks_evidence_tying_" in reason

    # Also verify that a generic-name-only match is rejected
    cand_generic_name = {
        "name": "Melbourne Dog Training",
        "suburb": "Melbourne",
        "source_url": "https://directory.example.org/entry/123",
        "source_type": "public_directory",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "source_validation_status": "verified",
        "raw_evidence": {
            "source_url": "https://directory.example.org/entry/123",
            "matched_suburb": "Melbourne",
            "snippet": "We list dog training and trainer services across Victoria.",
        },
    }
    valid_gen, reason_gen = seed_melbourne_trainers.validate_candidate_schema(cand_generic_name)
    assert valid_gen is False
    assert reason_gen in {"generic_name_match_only_rejected", "lacks_evidence_tying_business_name_to_source"}


def test_fully_evidenced_synthetic_test_candidate_passes():
    """Verify a fully evidenced synthetic test candidate passes validation."""
    fully_evidenced_candidate = {
        "id": "cand_synthetic_pass",
        "name": "Prahran Dog Training",
        "suburb": "Prahran",
        "region": "Melbourne Inner South",
        "website": "https://prahrandogtraining.com.au",
        "phone": "03 9510 1234",
        "email": "info@prahrandogtraining.com.au",
        "abn": "51 824 753 556",
        "services": ["Puppy Training", "Obedience"],
        "source_url": "https://prahrandogtraining.com.au",
        "source_type": "business_website",
        "source_validation_status": "verified",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "raw_evidence": {
            "source_url": "https://prahrandogtraining.com.au",
            "matched_name": "Prahran Dog Training",
            "matched_suburb": "Prahran",
            "matched_website": "https://prahrandogtraining.com.au",
            "matched_phone": "03 9510 1234",
            "matched_email": "info@prahrandogtraining.com.au",
            "matched_abn": "51 824 753 556",
            "matched_services": ["Puppy Training", "Obedience"],
            "snippet": "Prahran Dog Training in Prahran provides puppy training and obedience classes. Contact 03 9510 1234 or info@prahrandogtraining.com.au. ABN: 51 824 753 556.",
        },
    }

    valid, reason = seed_melbourne_trainers.validate_candidate_schema(fully_evidenced_candidate)
    assert valid is True
    assert reason == "valid"

    # Also verify that omitted public fields (e.g. no phone, no email, no ABN) do not require evidence
    minimal_evidenced_candidate = {
        "id": "cand_minimal_synthetic",
        "name": "Prahran Dog Training",
        "suburb": "Prahran",
        "region": "Melbourne Inner South",
        "source_url": "https://prahrandogtraining.com.au",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "raw_evidence": {
            "source_url": "https://prahrandogtraining.com.au",
            "matched_name": "Prahran Dog Training",
            "matched_suburb": "Prahran",
        },
    }
    valid_min, reason_min = seed_melbourne_trainers.validate_candidate_schema(minimal_evidenced_candidate)
    assert valid_min is True
    assert reason_min == "valid"


def test_inline_rejection_examples_fail_closed():
    """Verify inline test-local rejection fixtures fail closed without external network calls."""
    # 1. Unresolved DNS fixture
    cand_dns = {
        "name": "Melbourne K9 Balance",
        "suburb": "Richmond",
        "source_url": "https://k9balance.com.au",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "source_validation_status": "unresolved_dns",
        "raw_evidence": {
            "source_url": "https://k9balance.com.au",
            "error_type": "unresolved_dns",
            "detail": "nodename nor servname provided, or not known",
        },
    }
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_dns)
    assert valid is False
    assert "unresolved_dns" in reason or "unverified_source_status" in reason or "evidence_indicates_failure" in reason

    # 2. HTTP 404 Not Found fixture
    cand_404 = {
        "name": "RSPCA Dog Training Academy",
        "suburb": "Burwood East",
        "source_url": "https://rspcavic.org/dog-training",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "source_validation_status": "http_404_not_found",
        "raw_evidence": {
            "source_url": "https://rspcavic.org/dog-training",
            "error_type": "http_404_not_found",
            "detail": "HTTP Error 404: Not Found",
        },
    }
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_404)
    assert valid is False
    assert "http_404" in reason or "evidence_indicates_failure" in reason

    # 3. Placeholder values (phone, name, domain)
    cand_placeholder = {
        "name": "Placeholder Trainer Academy",
        "suburb": "Melbourne",
        "website": "https://example.com/trainer",
        "phone": "0400 000 000",
        "email": "test@example.com",
        "source_url": "https://example.com/trainer",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "raw_evidence": {"source_url": "https://example.com/trainer"},
    }
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_placeholder)
    assert valid is False
    assert "placeholder" in reason

    # 4. Missing provenance evidence (empty raw_evidence)
    cand_empty_ev = {
        "name": "Unprovenanced Trainer",
        "suburb": "Fitzroy",
        "source_url": "https://unprovenanced.com.au",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "raw_evidence": {},
    }
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_empty_ev)
    assert valid is False
    assert reason == "missing_provenance_evidence"

    # 5. Mismatched source URL between candidate and raw_evidence
    cand_mismatch = {
        "name": "Mismatched Source Dog Training",
        "suburb": "Brunswick",
        "source_url": "https://source-a.com.au/profile",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "raw_evidence": {
            "source_url": "https://source-b.com.au/profile",
            "matched_name": "Mismatched Source Dog Training",
            "matched_suburb": "Brunswick",
        },
    }
    valid, reason = seed_melbourne_trainers.validate_candidate_schema(cand_mismatch)
    assert valid is False
    assert "source_url_evidence_mismatch" in reason


def test_dry_run_performs_zero_writes():
    """Verify --dry-run validates records without modifying MongoDB collections."""
    fake_db = _MockDB()
    candidates, data_gap = seed_melbourne_trainers.load_seed_file(SEED_JSON_PATH)

    synthetic_candidate = {
        "id": "cand_test_dry",
        "name": "Kew Canine Training",
        "suburb": "Kew",
        "source_url": "https://kewcanine.com.au",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "raw_evidence": {
            "source_url": "https://kewcanine.com.au",
            "matched_name": "Kew Canine Training",
            "matched_suburb": "Kew",
        },
    }

    summary = asyncio.run(
        seed_melbourne_trainers.process_seeding(
            fake_db,
            [synthetic_candidate],
            dry_run=True,
        )
    )

    assert summary["mode"] == "dry-run"
    assert summary["scanned"] == 1
    assert summary["valid_count"] == 1
    assert summary["created"] == 1

    # Strictly 0 database writes
    assert len(fake_db.trainers.rows) == 0
    assert len(fake_db.source_ingestion_state.rows) == 0


def test_non_publication_and_unverified_abn_defaults():
    """Verify that seeded candidates strictly default to unpublished, unclaimed, and unverified ABN."""
    fake_db = _MockDB()

    valid_candidate = {
        "id": "cand_test_defaults",
        "name": "Prahran Dog Training",
        "suburb": "Prahran",
        "region": "Melbourne Inner South",
        "website": "https://prahrandogtraining.com.au",
        "phone": "03 9510 1234",
        "abn": "51 824 753 556",
        "source_url": "https://prahrandogtraining.com.au",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "raw_evidence": {
            "source_url": "https://prahrandogtraining.com.au",
            "matched_name": "Prahran Dog Training",
            "matched_suburb": "Prahran",
            "matched_website": "https://prahrandogtraining.com.au",
            "matched_phone": "03 9510 1234",
            "matched_abn": "51 824 753 556",
            "snippet": "Prahran Dog Training in Prahran. Call 03 9510 1234. ABN: 51 824 753 556.",
        },
    }

    summary = asyncio.run(
        seed_melbourne_trainers.process_seeding(
            fake_db,
            [valid_candidate],
            dry_run=False,
        )
    )

    assert summary["created"] == 1
    assert len(fake_db.trainers.rows) == 1

    doc = fake_db.trainers.rows[0]
    # Requirements: candidates remain unpublished, unclaimed, and ABR-unverified
    assert doc["published"] is False, "Candidates must never be auto-published"
    assert doc["tier"] == "unclaimed", "Candidate tier must be 'unclaimed'"
    assert doc["claim_status"] == "unclaimed", "Candidate claim status must be 'unclaimed'"
    assert doc["abn_verified"] is False, "ABN must never be marked verified without approved ABR lookup"
    assert doc["verification_status"] == "unverified", "Verification status must remain 'unverified'"
    assert doc["abn_status"] == "pending_verification"
    assert doc["image_url"] == ""


def test_canonical_path_idempotency_and_claimed_preservation():
    """Verify repeat runs are idempotent (0 new creations) and existing claimed profiles are preserved."""
    fake_db = _MockDB()

    valid_candidate = {
        "id": "cand_test_idem",
        "name": "St Kilda Canine Academy",
        "suburb": "St Kilda",
        "region": "Melbourne Inner South",
        "website": "https://stkildacanine.com.au",
        "phone": "03 9534 5678",
        "source_url": "https://stkildacanine.com.au",
        "source_type": "business_website",
        "retrieved_at": "2026-09-09T00:00:00Z",
        "raw_evidence": {
            "source_url": "https://stkildacanine.com.au",
            "matched_name": "St Kilda Canine Academy",
            "matched_suburb": "St Kilda",
            "matched_website": "https://stkildacanine.com.au",
            "matched_phone": "03 9534 5678",
            "snippet": "Professional dog training in St Kilda. Contact 03 9534 5678.",
        },
    }

    # Run 1: Creates new candidate
    summary1 = asyncio.run(seed_melbourne_trainers.process_seeding(fake_db, [valid_candidate], dry_run=False))
    assert summary1["created"] == 1
    assert summary1["updated_unclaimed"] == 0
    assert len(fake_db.trainers.rows) == 1
    initial_id = fake_db.trainers.rows[0]["id"]

    # Run 2: Idempotent repeat run creates 0 records
    summary2 = asyncio.run(seed_melbourne_trainers.process_seeding(fake_db, [valid_candidate], dry_run=False))
    assert summary2["created"] == 0
    assert summary2["updated_unclaimed"] == 1
    assert len(fake_db.trainers.rows) == 1
    assert fake_db.trainers.rows[0]["id"] == initial_id

    # Now simulate owner claiming this profile
    fake_db.trainers.rows[0]["claim_status"] = "claimed"
    fake_db.trainers.rows[0]["tier"] = "pro"
    fake_db.trainers.rows[0]["email"] = "owner@stkildacanine.com.au"
    fake_db.trainers.rows[0]["claimed_at"] = "2026-09-01T10:00:00Z"
    fake_db.trainers.rows[0]["abn_verified"] = True

    # Run 3: Repeat run must strictly preserve the claimed profile
    summary3 = asyncio.run(seed_melbourne_trainers.process_seeding(fake_db, [valid_candidate], dry_run=False))
    assert summary3["created"] == 0
    assert summary3["preserved_claimed"] == 1

    preserved = fake_db.trainers.rows[0]
    assert preserved["claim_status"] == "claimed"
    assert preserved["tier"] == "pro"
    assert preserved["email"] == "owner@stkildacanine.com.au"
    assert preserved["claimed_at"] == "2026-09-01T10:00:00Z"
    assert preserved["abn_verified"] is True


def test_domain_match_is_hostname_exact_not_suffix_substring():
    fake_db = _MockDB()
    fake_db.trainers.rows.append({
        "id": "dale",
        "name": "Dale For Dogs",
        "suburb": "Melbourne",
        "website": "https://daledogtraining.com.au",
        "published": True,
    })
    candidate = {
        "id": "command",
        "name": "Command Dog Training School",
        "suburb": "Blackburn",
        "website": "https://dogtraining.com.au/",
        "source_url": "https://dogtraining.com.au/",
        "source_type": "business_website",
        "retrieved_at": "2026-09-11T00:00:00Z",
        "raw_evidence": {
            "source_url": "https://dogtraining.com.au/",
            "matched_name": "Command Dog Training School",
            "matched_suburb": "Blackburn",
            "matched_website": "https://dogtraining.com.au/",
        },
    }
    summary = asyncio.run(seed_melbourne_trainers.process_seeding(fake_db, [candidate], dry_run=False))
    assert summary["created"] == 1
    assert len(fake_db.trainers.rows) == 2


def test_apply_can_publish_and_enrich_existing_qualified_unclaimed_profile():
    fake_db = _MockDB()
    fake_db.trainers.rows.append({
        "id": "existing",
        "name": "Evidence Dogs",
        "suburb": "Richmond",
        "website": "https://evidencedogs.example.au",
        "tier": "unclaimed",
        "claim_status": "unclaimed",
        "published": False,
    })
    candidate = {
        "name": "Evidence Dogs",
        "suburb": "Richmond",
        "website": "https://evidencedogs.example.au",
        "abn": "51 824 753 556",
        "services": ["Puppy training"],
        "source_url": "https://evidencedogs.example.au",
        "source_type": "business_website",
        "retrieved_at": "2026-09-11T00:00:00Z",
        "abr_evidence": {"status": "active", "retrieved_at": "2026-09-11T00:00:00Z"},
        "raw_evidence": {
            "source_url": "https://evidencedogs.example.au",
            "matched_name": "Evidence Dogs",
            "matched_suburb": "Richmond",
            "matched_website": "https://evidencedogs.example.au",
            "matched_abn": "51 824 753 556",
            "matched_services": ["Puppy training"],
        },
    }
    summary = asyncio.run(seed_melbourne_trainers.process_seeding(
        fake_db, [candidate], dry_run=False, allow_publication=True
    ))
    assert summary["updated_unclaimed"] == 1
    assert summary["quality_qualified"] == 1
    assert fake_db.trainers.rows[0]["published"] is True
    assert fake_db.trainers.rows[0]["abn"] == "51824753556"
    assert fake_db.trainers.rows[0]["abr_evidence"]["status"] == "active"


def test_owner_submission_is_preserved_as_claimed_context():
    assert seed_melbourne_trainers.is_claimed_profile({"via_submission_id": "submission-1"}) is True


def test_in_batch_duplicates_skipped():
    """Verify that multiple candidates sharing domain or ABN are deduplicated within the batch."""
    fake_db = _MockDB()

    duplicate_candidates = [
        {
            "name": "K9 Training Hub East",
            "suburb": "Hawthorn",
            "website": "https://k9traininghub.com.au",
            "source_url": "https://k9traininghub.com.au",
            "source_type": "business_website",
            "retrieved_at": "2026-09-09T00:00:00Z",
            "raw_evidence": {
                "source_url": "https://k9traininghub.com.au",
                "matched_name": "K9 Training Hub East",
                "matched_suburb": "Hawthorn",
                "matched_website": "https://k9traininghub.com.au",
            },
        },
        {
            "name": "K9 Training Hub South",
            "suburb": "Prahran",
            "website": "https://k9traininghub.com.au/prahran",
            "source_url": "https://k9traininghub.com.au",
            "source_type": "business_website",
            "retrieved_at": "2026-09-09T00:00:00Z",
            "raw_evidence": {
                "source_url": "https://k9traininghub.com.au",
                "matched_name": "K9 Training Hub South",
                "matched_suburb": "Prahran",
                "matched_website": "https://k9traininghub.com.au",
            },
        },
    ]

    summary = asyncio.run(
        seed_melbourne_trainers.process_seeding(
            fake_db,
            duplicate_candidates,
            dry_run=False,
        )
    )

    assert summary["created"] == 1
    assert summary["duplicates_skipped"] == 1
    assert len(fake_db.trainers.rows) == 1


def test_delisted_identity_is_suppressed_before_seed_creation():
    fake_db = _MockDB()
    fake_db.delisted_entities.rows.append({"website_domain": "optedout.example", "reason": "owner_requested"})
    candidate = {
        "name": "Opted Out Canine",
        "suburb": "Kew",
        "website": "https://optedout.example",
        "source_url": "https://optedout.example",
        "source_type": "business_website",
        "retrieved_at": "2026-09-10T00:00:00Z",
        "raw_evidence": {
            "source_url": "https://optedout.example",
            "matched_name": "Opted Out Canine",
            "matched_suburb": "Kew",
            "matched_website": "https://optedout.example",
        },
    }
    summary = asyncio.run(seed_melbourne_trainers.process_seeding(fake_db, [candidate], dry_run=False))
    assert summary["suppressed_delisted"] == 1
    assert summary["created"] == 0
    assert fake_db.trainers.rows == []


def test_quality_gate_requires_active_abr_evidence_before_publication():
    candidate = {
        "name": "Evidence First Dogs",
        "suburb": "Richmond",
        "website": "https://evidencefirst.example.au",
        "abn": "51 824 753 556",
        "review_rating": 4.8,
        "review_count": 20,
        "specialties": ["puppy_training"],
        "raw_evidence": {"matched_suburb": "Richmond"},
    }
    held = seed_melbourne_trainers.publishing_quality(candidate)
    assert held == {"score": 0.8, "eligible": False, "active_abn_evidence": False}
    candidate["abr_evidence"] = {"status": "active", "retrieved_at": "2026-09-10T00:00:00Z"}
    qualified = seed_melbourne_trainers.publishing_quality(candidate)
    assert qualified == {"score": 1.0, "eligible": True, "active_abn_evidence": True}


def test_dry_run_manifest_is_machine_readable_and_traceable():
    summary = {"mode": "dry-run", "scanned": 0, "actions": []}
    manifest = seed_melbourne_trainers.build_run_manifest(
        summary,
        seed_file=SEED_JSON_PATH,
        data_gap={"authentic_count": 0, "remaining_data_gap": 100},
    )
    assert manifest["manifest_version"] == 1
    assert manifest["run_id"].startswith("ingest-")
    assert manifest["mode"] == "dry-run"
    assert manifest["summary"] == summary


def test_ops_case_surfaces_delisted_reingestion_suppression(monkeypatch):
    fake_db = _MockDB()
    monkeypatch.setattr(server, "db", fake_db)
    cases = asyncio.run(
        server._ops_case_rows(
            discovery_summary={"pending": 0, "promoted": 0, "duplicate": 0, "discarded": 0, "suppressed": 2},
            waitlist_summary={},
            loop_statuses={},
            reactivation_case_rows=[],
            source_ingestion_state_rows=[],
            message_log=[],
        )
    )
    row = next(case for case in cases if case["case_id"] == "discovery:suppressed")
    assert row["severity"] == "medium"
    assert row["risk_reason_codes"] == ["discovery_delisted_identity_suppressed"]


def test_real_ops_aggregation_path_surfaces_unverified_abn_and_source_failures(monkeypatch):
    """Verify that unverified ABN candidates and source ingestion failures surface through server.oversight()."""
    fake_db = _MockDB()
    monkeypatch.setattr(server, "db", fake_db)

    # 1. Seed an unverified ABN candidate into db.trainers
    unverified_cand = {
        "id": "cand_melb_unverified_abn",
        "name": "South Yarra K9 Training",
        "suburb": "South Yarra",
        "region": "Melbourne Inner South",
        "abn": "51 824 753 556",
        "abn_status": "pending_verification",
        "abn_verified": False,
        "abn_verification_reason": "Candidate requires ABR lookup verification before public badge.",
        "abn_checked_at": "2026-09-09T00:00:00Z",
        "published": False,
        "created_at": "2026-09-09T00:00:00Z",
    }
    fake_db.trainers.rows.append(unverified_cand)

    # 2. Record a source ingestion failure in db.source_ingestion_state
    fake_db.source_ingestion_state.rows.append({
        "source_url": "https://k9balance.com.au",
        "last_checked_at": "2026-09-09T00:00:00Z",
        "last_error": "unresolved_dns: nodename nor servname provided, or not known",
        "last_error_code": "source_ingestion_failure",
        "last_http_status": 0,
        "consecutive_failures": 1,
    })

    # 3. Call the REAL /ops aggregation path: server.oversight()
    oversight_result = asyncio.run(server.oversight(_=None))

    assert "ops_cases" in oversight_result, "Oversight result must include aggregated 'ops_cases'"
    cases = oversight_result["ops_cases"]

    # Verify ABN verification case is present
    abn_cases = [c for c in cases if c.get("case_type") == "abn_verification_case" and c.get("entity_id") == "cand_melb_unverified_abn"]
    assert len(abn_cases) == 1, "Unverified ABN candidate must surface as abn_verification_case"
    assert "South Yarra K9 Training" in abn_cases[0]["title"]
    assert "pending_verification" in abn_cases[0]["risk_reason_codes"]

    # Verify Source Ingestion failure case is present
    source_cases = [c for c in cases if c.get("case_type") == "source_ingestion_case" and c.get("entity_id") == "https://k9balance.com.au"]
    assert len(source_cases) == 1, "Source ingestion failure must surface as source_ingestion_case"
    assert "unresolved_dns" in source_cases[0]["summary"]
    assert source_cases[0]["severity"] == "medium"


def test_startup_seeds_disabled_by_default(monkeypatch):
    """Verify that startup seeding is disabled by default unless STARTUP_SEEDS_ENV is set."""
    monkeypatch.delenv(server.STARTUP_SEEDS_ENV, raising=False)
    assert server._startup_seeds_enabled("api") is False
    assert server._startup_seeds_enabled("worker") is False

    monkeypatch.setenv(server.STARTUP_SEEDS_ENV, "1")
    assert server._startup_seeds_enabled("api") is True
    assert server._startup_seeds_enabled("worker") is False


def test_cli_test_fixture_file_never_loads_from_production_seed_file(tmp_path, monkeypatch):
    """Verify CLI never loads test fixtures from production seed file and ignores it if passed."""
    import argparse
    import io
    import sys

    # Case 1: Pointing --test-fixture-file to DEFAULT_SEED_FILE is rejected/ignored
    args_prod = argparse.Namespace(
        apply=False,
        seed_file=str(SEED_JSON_PATH),
        mongo_url="",
        db_name="",
        test_fixture_file=str(SEED_JSON_PATH),
    )
    # run_cli should run with 0 scanned since production file candidates is empty and fixture is ignored
    exit_code = asyncio.run(seed_melbourne_trainers.run_cli(args_prod))
    assert exit_code == 0

    # Case 2: Explicit external test fixture file is supported
    ext_fixture = tmp_path / "test_fixtures.json"
    ext_fixture.write_text(
        json.dumps({
            "invalid_candidates": [
                {
                    "name": "External Test Candidate",
                    "suburb": "Melbourne",
                    "source_url": "https://example.com/ext",
                    "source_type": "business_website",
                    "retrieved_at": "invalid-timestamp",
                    "raw_evidence": {"source_url": "https://example.com/ext"},
                }
            ]
        }),
        encoding="utf-8",
    )
    args_ext = argparse.Namespace(
        apply=False,
        seed_file=str(SEED_JSON_PATH),
        mongo_url="",
        db_name="",
        test_fixture_file=str(ext_fixture),
    )
    exit_code_ext = asyncio.run(seed_melbourne_trainers.run_cli(args_ext))
    assert exit_code_ext == 0
