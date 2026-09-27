"""Unit test suite for Acquisition Architecture Audit & Match-Readiness Projection (DF-026).

Verifies the 7 mandatory acceptance criteria specified in:
docs/ANTIGRAVITY_ACQUISITION_MATCH_READINESS_HANDOFF.md
Governed by: AGENTS.md Rule 6A, CDR-021, and CDR-022.
"""

from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict
import pytest

from services.trainer_quality import (
    CANONICAL_SPECIALTIES,
    CANONICAL_SERVICE_FORMATS,
    CANONICAL_LIFE_STAGES,
    VALID_TRAINING_PHILOSOPHIES,
    VALID_CATCHMENT_TYPES,
    TRAINER_DECLARATION_TTL_DAYS,
    OFFICIAL_SOURCE_TTL_DAYS,
    AI_PROPOSED_TTL_DAYS,
    normalize_specialty,
    normalize_service_format,
    normalize_life_stage,
    normalize_training_philosophy,
    normalize_catchment_type,
    validate_capability_category,
    compute_capability_freshness,
    create_capability_fact,
    package_trainer_capabilities,
    invalidate_trainer_capabilities,
    build_match_ready_projection,
    assess_trainer_capability_health,
    now_iso,
)
from services import ai


# ==============================================================================
# Criterion 1: AI-proposed capability cannot independently become matchable
# ==============================================================================

def test_ai_proposed_capability_cannot_independently_become_matchable():
    """AI confidence or model extractions are display/prefill only and cannot enter projection."""
    now_ts = now_iso()
    # Fact created from AI extraction (basis="ai_proposed")
    fact = create_capability_fact(
        "specialties",
        ["puppy_training", "leash_reactivity"],
        basis="ai_proposed",
        evidence_reference="https://example-trainer.com.au",
        confirmed_at=now_ts,
    )
    # Must validate canonical terms but fail projection permission
    assert fact["validation_result"]["valid"] is True
    assert fact["basis"] == "ai_proposed"
    assert fact["permitted_in_projection"] is False, "AI-proposed capability MUST NOT be permitted in projection"

    # Profile with ONLY AI-proposed capabilities
    trainer_doc = {
        "id": "trainer_scraped_1",
        "name": "Scraped Dog Training",
        "suburb": "Richmond",
        "published": True,
        "contact_ready": True,
        "source_url": "https://example-trainer.com.au",
        "source_evidence_url": "https://example-trainer.com.au",
        "capabilities": {
            "specialties": fact,
            "service_formats": create_capability_fact(
                "service_formats",
                ["in_home"],
                basis="ai_proposed",
                evidence_reference="https://example-trainer.com.au",
                confirmed_at=now_ts,
            ),
        },
    }

    projection = build_match_ready_projection(trainer_doc)
    assert projection["match_eligible"] is False
    assert len(projection["specialties"]) == 0
    assert len(projection["service_formats"]) == 0
    assert "no_permitted_matchable_capabilities" in projection["eligibility_reasons"]


# ==============================================================================
# Criterion 2: Trainer-confirmed structured capability becomes matchable only after validation
# ==============================================================================

def test_trainer_confirmed_capability_becomes_matchable_only_after_validation():
    """Trainer-declared structured capability becomes matchable only if canonical validation passes."""
    now_ts = now_iso()

    # Case A: Valid declaration
    valid_caps = package_trainer_capabilities(
        specialties=["puppy training", "leash pulling", "excessive barking"],
        service_formats=["in-home private", "training centre"],
        life_stages=["puppy", "adolescent"],
        training_philosophy="Positive Reinforcement / Force-Free",
        serviced_suburbs=["Richmond", "South Yarra"],
        catchment_type="specific_suburbs",
        basis="trainer_declaration",
        evidence_reference="sub_12345",
        confirmed_at=now_ts,
    )

    trainer_valid = {
        "id": "trainer_declared_1",
        "name": "Pawsitive Steps",
        "suburb": "Richmond",
        "published": True,
        "contact_ready": True,
        "capabilities": valid_caps,
    }

    proj_valid = build_match_ready_projection(trainer_valid)
    assert proj_valid["match_eligible"] is True
    assert set(proj_valid["specialties"]) == {"puppy_training", "leash_reactivity", "barking"}
    assert set(proj_valid["service_formats"]) == {"in_home", "facility"}
    assert set(proj_valid["life_stages"]) == {"puppy", "adolescent"}
    assert proj_valid["training_philosophy"] == "positive_reinforcement_force_free"
    assert proj_valid["serviced_suburbs"] == ["Richmond", "South Yarra"]

    # Case B: Completely invalid / unrecognized capability
    invalid_fact = create_capability_fact(
        "specialties",
        ["underwater_circus", "telepathic_whispering"],
        basis="trainer_declaration",
        evidence_reference="sub_99999",
        confirmed_at=now_ts,
    )
    assert invalid_fact["validation_result"]["valid"] is False
    assert invalid_fact["permitted_in_projection"] is False
    assert "underwater_circus" in invalid_fact["validation_result"]["rejected_terms"]


# ==============================================================================
# Criterion 3: Correction, failed refresh, or suppression invalidates affected capability
# ==============================================================================

def test_correction_failed_refresh_or_suppression_invalidates_affected_capability():
    """Dispute, suppression, or trainer correction revokes match-ready permission."""
    now_ts = now_iso()
    caps = package_trainer_capabilities(
        specialties=["puppy_training", "obedience"],
        service_formats=["in_home"],
        basis="trainer_declaration",
        evidence_reference="claim_event_1",
        confirmed_at=now_ts,
    )
    trainer = {
        "id": "trainer_active_1",
        "name": "Reliable Canine",
        "suburb": "Hawthorn",
        "published": True,
        "contact_ready": True,
        "capabilities": caps,
    }

    # Before invalidation: match eligible
    proj_before = build_match_ready_projection(trainer)
    assert proj_before["match_eligible"] is True
    assert len(proj_before["specialties"]) == 2

    # Invalidate due to profile dispute / suppression
    invalidate_trainer_capabilities(trainer, reason="profile_claim_disputed")

    assert trainer["capabilities"]["specialties"]["permitted_in_projection"] is False
    assert trainer["capabilities"]["specialties"]["invalidation_reason"] == "profile_claim_disputed"
    assert trainer["capabilities"]["service_formats"]["permitted_in_projection"] is False

    proj_after = build_match_ready_projection(trainer)
    assert proj_after["match_eligible"] is False
    assert len(proj_after["specialties"]) == 0
    assert "no_permitted_matchable_capabilities" in proj_after["eligibility_reasons"]


# ==============================================================================
# Criterion 4: Paid status and marketing prose cannot enter the projection
# ==============================================================================

def test_paid_status_and_marketing_prose_cannot_enter_projection():
    """Commercial tier, pricing, reviews, and marketing prose are strictly excluded."""
    now_ts = now_iso()
    caps = package_trainer_capabilities(
        specialties=["puppy_training"],
        service_formats=["in_home"],
        training_philosophy="Positive Reinforcement",
        basis="trainer_declaration",
        evidence_reference="sub_abc",
        confirmed_at=now_ts,
    )

    trainer_with_commercial_data = {
        "id": "trainer_vip_1",
        "name": "Elite K9 Academy",
        "suburb": "Toorak",
        "published": True,
        "contact_ready": True,
        "tier": "melbourne_sponsor",
        "billing_status": "active",
        "subscription_tier": "featured_pro",
        "pricing": "$350 per private consultation",
        "review_count": 98,
        "review_rating": 4.95,
        "confidence_score": 0.99,
        "bio": "Melbourne's premier luxury dog training academy. Fast guaranteed results in 3 days!",
        "capabilities": caps,
    }

    projection = build_match_ready_projection(trainer_with_commercial_data)

    # Invariant checks: Keys that MUST NOT exist in projection
    forbidden_keys = {"bio", "tier", "billing_status", "subscription_tier", "pricing", "review_count", "review_rating", "confidence_score"}
    for key in forbidden_keys:
        assert key not in projection, f"Projection MUST NOT contain commercial or prose key '{key}'"

    # Content checks: Commercial words MUST NOT appear in serialized projection values
    serialized_proj = json.dumps(projection).lower()
    for forbidden_text in ["melbourne_sponsor", "luxury", "premier", "guaranteed", "350", "4.95"]:
        assert forbidden_text not in serialized_proj, f"Projection leaked marketing/commercial text: {forbidden_text}"


@pytest.mark.anyio
async def test_ai_match_service_excludes_bio_and_tier_from_gemini_payload():
    """ai.match_trainers passes only clean projected capabilities to model, omitting bio and tier."""
    now_ts = now_iso()
    caps = package_trainer_capabilities(
        specialties=["puppy_training"],
        service_formats=["in_home"],
        basis="trainer_declaration",
        evidence_reference="sub_test",
        confirmed_at=now_ts,
    )

    trainer = {
        "id": "trainer_test_prompt",
        "name": "Prompt Test Trainer",
        "suburb": "Brunswick",
        "published": True,
        "contact_ready": True,
        "tier": "suburb_sponsor",
        "bio": "Marketing fluff that must be stripped completely.",
        "capabilities": caps,
    }

    class MockModel:
        def __init__(self):
            self.last_prompt = ""

        async def generate_content(self, model, contents, config):
            self.last_prompt = contents
            class MockResp:
                text = json.dumps([{"trainer_id": "trainer_test_prompt", "score": 0.85, "reasoning": "Good fit for puppy."}])
            return MockResp()

    class MockAio:
        def __init__(self):
            self.models = MockModel()

    class MockClient:
        def __init__(self):
            self.aio = MockAio()

    client = MockClient()
    matches = await ai.match_trainers("I need puppy help", [trainer], client=client)

    assert len(matches) == 1
    prompt = client.aio.models.last_prompt
    assert "suburb_sponsor" not in prompt, "Commercial tier MUST NOT be in prompt"
    assert '"tier"' not in prompt, "Tier key MUST NOT be in prompt"
    assert "Marketing fluff" not in prompt, "Marketing bio MUST NOT be in prompt"
    assert '"bio"' not in prompt, "Bio key MUST NOT be in prompt"


# ==============================================================================
# Criterion 5: AI confidence cannot grant public, contact, or matchable state
# ==============================================================================

def test_ai_confidence_cannot_grant_public_contact_or_matchable_state():
    """High AI confidence score never bypasses publication, contact readiness, or ABR revocation."""
    now_ts = now_iso()
    caps = package_trainer_capabilities(
        specialties=["puppy_training"],
        service_formats=["in_home"],
        basis="trainer_declaration",
        evidence_reference="sub_789",
        confirmed_at=now_ts,
    )

    # Case A: Unpublished listing with 1.0 confidence
    trainer_unpublished = {
        "id": "t_unpub",
        "name": "Unpublished Trainer",
        "suburb": "Carlton",
        "published": False,
        "contact_ready": True,
        "confidence_score": 1.0,
        "capabilities": caps,
    }
    proj_unpub = build_match_ready_projection(trainer_unpublished)
    assert proj_unpub["match_eligible"] is False
    assert "profile_not_published" in proj_unpub["eligibility_reasons"]

    # Case B: Deregistered statutory ABN with 0.95 confidence
    trainer_abn_revoked = {
        "id": "t_abn_bad",
        "name": "Cancelled ABN Trainer",
        "suburb": "Carlton",
        "published": True,
        "contact_ready": True,
        "abn_verified": False,
        "abn_status": "cancelled",
        "confidence_score": 0.95,
        "capabilities": caps,
    }
    proj_abn = build_match_ready_projection(trainer_abn_revoked)
    assert proj_abn["match_eligible"] is False
    assert "statutory_abn_revoked" in proj_abn["eligibility_reasons"]

    # Case C: Not contact ready
    trainer_no_contact = {
        "id": "t_no_contact",
        "name": "Silent Trainer",
        "suburb": "Carlton",
        "published": True,
        "contact_ready": False,
        "confidence_score": 0.99,
        "capabilities": caps,
    }
    proj_no_contact = build_match_ready_projection(trainer_no_contact)
    assert proj_no_contact["match_eligible"] is False
    assert "not_contact_ready" in proj_no_contact["eligibility_reasons"]


# ==============================================================================
# Criterion 6: Stale or unsupported fields are excluded or explicitly held
# ==============================================================================

def test_stale_or_unsupported_fields_are_excluded_or_explicitly_held():
    """Declarations older than TTL fail closed and are excluded from the projection."""
    now_dt = datetime.now(timezone.utc)
    old_dt = now_dt - timedelta(days=TRAINER_DECLARATION_TTL_DAYS + 10)  # 190 days old (stale)
    old_ts = old_dt.isoformat()

    freshness_state, is_fresh = compute_capability_freshness(old_ts, "trainer_declaration", as_of=now_dt)
    assert freshness_state == "stale"
    assert is_fresh is False

    stale_caps = package_trainer_capabilities(
        specialties=["puppy_training"],
        service_formats=["in_home"],
        basis="trainer_declaration",
        evidence_reference="old_sub_1",
        confirmed_at=old_ts,
    )

    trainer_stale = {
        "id": "t_stale",
        "name": "Stale Trainer",
        "suburb": "Fitzroy",
        "published": True,
        "contact_ready": True,
        "capabilities": stale_caps,
    }

    # As of today, the 190-day-old declaration must fail closed
    proj_stale = build_match_ready_projection(trainer_stale, as_of=now_dt)
    assert proj_stale["match_eligible"] is False
    assert len(proj_stale["specialties"]) == 0
    assert "no_permitted_matchable_capabilities" in proj_stale["eligibility_reasons"]

    # As of 30 days after confirmation, it was fresh and match eligible
    past_eval_dt = old_dt + timedelta(days=30)
    proj_fresh = build_match_ready_projection(trainer_stale, as_of=past_eval_dt)
    assert proj_fresh["match_eligible"] is True
    assert len(proj_fresh["specialties"]) == 1


# ==============================================================================
# Criterion 7: /ops exposes actionable state without personal owner data
# ==============================================================================

def test_ops_exposes_actionable_state_without_personal_owner_data():
    """assess_trainer_capability_health exposes operational telemetry with zero owner PII."""
    now_ts = now_iso()
    caps = package_trainer_capabilities(
        specialties=["puppy_training", "unknown_bogus_specialty"],
        service_formats=["in_home"],
        basis="trainer_declaration",
        evidence_reference="sub_ops",
        confirmed_at=now_ts,
    )

    trainer = {
        "id": "trainer_ops_audit",
        "name": "Audit Sample Trainer",
        "suburb": "Preston",
        "published": True,
        "contact_ready": True,
        "capabilities": caps,
    }

    health = assess_trainer_capability_health(trainer)

    # Check structural operational telemetry
    assert health["trainer_id"] == "trainer_ops_audit"
    assert health["has_structured_capabilities"] is True
    assert health["total_facts"] == 2
    assert health["permitted_facts"] == 2
    assert health["stale_facts"] == 0
    assert "unknown_bogus_specialty" in health["rejected_terms"]
    assert health["match_eligible"] is True

    # PII verification: Absolutely zero owner fields
    serialized_health = json.dumps(health).lower()
    owner_pii_markers = ["owner", "dog_name", "enquiry", "user_email", "phone_number", "questionnaire"]
    for marker in owner_pii_markers:
        assert marker not in serialized_health, f"/ops capability health leaked owner marker: {marker}"


# ==============================================================================
# Ingestion & Submission Integration Tests
# ==============================================================================

# ==============================================================================
# Ingestion, Claim, and Oversight Unit Tests
# ==============================================================================

class _FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, size):
        self.rows = self.rows[:size]
        return self

    async def to_list(self, _size=None):
        return list(self.rows)


class _FakeCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.inserted = []

    @staticmethod
    def _get_val(row, path):
        parts = path.split(".")
        curr = row
        for part in parts:
            if not isinstance(curr, dict):
                return None
            curr = curr.get(part)
        return curr

    @classmethod
    def _matches_cond(cls, val, expected):
        if isinstance(expected, dict):
            for op, op_val in expected.items():
                if op == "$ne" and val == op_val:
                    return False
                if op == "$exists":
                    exists = val is not None
                    if exists != op_val:
                        return False
                if op == "$in" and val not in op_val:
                    return False
                if op == "$nin" and val in op_val:
                    return False
            return True
        return val == expected

    @classmethod
    def _matches(cls, row, filt):
        if not filt:
            return True
        for key, expected in filt.items():
            if key == "$or":
                if not any(cls._matches(row, sub_filt) for sub_filt in expected):
                    return False
                continue
            val = cls._get_val(row, key)
            if not cls._matches_cond(val, expected):
                return False
        return True

    async def find_one(self, filt=None, *_args, **_kwargs):
        return next((row for row in self.rows if self._matches(row, filt)), None)

    def find(self, filt=None, *_args, **_kwargs):
        return _FakeCursor([row for row in self.rows if self._matches(row, filt)])

    async def insert_one(self, doc):
        self.inserted.append(doc)
        self.rows.append(doc)

    async def update_one(self, filt, update, upsert=False):
        from types import SimpleNamespace
        row = await self.find_one(filt)
        if row is None and upsert:
            row = dict(filt)
            self.rows.append(row)
        if row is not None:
            set_vals = update.get("$set", {})
            for k, v in set_vals.items():
                parts = k.split(".")
                curr = row
                for part in parts[:-1]:
                    if part not in curr or not isinstance(curr[part], dict):
                        curr[part] = {}
                    curr = curr[part]
                curr[parts[-1]] = v
            for k, v in update.get("$inc", {}).items():
                row[k] = int(row.get(k) or 0) + v
        return SimpleNamespace(matched_count=1 if row else 0)

    async def update_many(self, filt, update):
        from types import SimpleNamespace
        count = 0
        for row in self.rows:
            if self._matches(row, filt):
                for k, v in update.get("$set", {}).items():
                    row[k] = v
                count += 1
        return SimpleNamespace(matched_count=count)

    async def count_documents(self, filt=None):
        return sum(1 for row in self.rows if self._matches(row, filt))


def _make_fake_db(trainers=None, claim_events=None, submissions=None):
    from types import SimpleNamespace
    return SimpleNamespace(
        trainers=_FakeCollection(trainers),
        claim_events=_FakeCollection(claim_events),
        submissions=_FakeCollection(submissions),
        audit_log=_FakeCollection(),
        abn_cache=_FakeCollection(),
        notification_events=_FakeCollection(),
        auth_attempts=_FakeCollection(),
        intros=_FakeCollection(),
        config_snapshots=_FakeCollection(),
    )


def test_trainer_submission_creates_validated_capabilities(monkeypatch):
    """POST /api/submissions persists trainer capabilities with basis='trainer_declaration'."""
    import asyncio
    import server

    fake_db = _make_fake_db()
    monkeypatch.setattr(server, "db", fake_db)

    payload = server.SubmissionIn(
        name="Live Submission Trainer",
        suburb="Brunswick",
        website="https://livesubmissiontrainer.com.au",
        phone="0412345679",
        email="trainer@livesubmissiontrainer.com.au",
        abn="51824753556",
        abn_status="active",
        abn_verified=True,
        specialties=["puppy_training", "obedience"],
        service_formats=["in_home"],
        training_philosophy="Positive Reinforcement / Force-Free",
        serviced_suburbs=["Brunswick", "Coburg"],
        catchment_type="specific_suburbs",
        consent_public_listing=True,
        consent_information_accuracy=True,
    )

    res = asyncio.run(server.create_submission(payload))
    trainer_id = res.get("trainer_id")
    assert trainer_id, "Submission must return trainer_id"

    trainer = next((t for t in fake_db.trainers.rows if t.get("id") == trainer_id), None)
    assert trainer is not None
    assert "capabilities" in trainer
    caps = trainer["capabilities"]
    assert caps["specialties"]["basis"] == "trainer_declaration"
    assert caps["specialties"]["permitted_in_projection"] is True
    assert set(caps["specialties"]["canonical_value"]) == {"puppy_training", "obedience"}
    assert caps["service_formats"]["permitted_in_projection"] is True

    # And verify the resulting projection is match-ready
    projection = build_match_ready_projection(trainer)
    assert projection["match_eligible"] is True
    assert "puppy_training" in projection["specialties"]


def test_claim_verification_promotes_capabilities_to_trainer_declaration(monkeypatch):
    """POST /trainers/{id}/verify promotes unconfirmed or AI-proposed capabilities to trainer_declaration."""
    import asyncio
    import uuid
    import server
    from services import claim_engine

    trainer_id = f"trainer_claim_test_{uuid.uuid4().hex[:8]}"
    now_ts = now_iso()

    # Ingested profile with AI-proposed capabilities
    ai_caps = package_trainer_capabilities(
        specialties=["puppy_training", "obedience"],
        service_formats=["in_home"],
        training_philosophy="Positive Reinforcement / Force-Free",
        serviced_suburbs=["Richmond"],
        catchment_type="specific_suburbs",
        basis="ai_proposed",
        evidence_reference="https://scraped-trainer.com.au",
        confirmed_at=now_ts,
    )

    trainer_doc = {
        "id": trainer_id,
        "name": "Claim Verification Candidate",
        "suburb": "Richmond",
        "email": "candidate@example.com.au",
        "published": True,
        "contact_ready": True,
        "claim_status": "unclaimed",
        "capabilities": ai_caps,
    }

    # Initial state: unconfirmed AI proposed capabilities are not permitted in projection
    proj_initial = build_match_ready_projection(trainer_doc)
    assert proj_initial["match_eligible"] is False
    assert "no_permitted_matchable_capabilities" in proj_initial["eligibility_reasons"]

    monkeypatch.setenv("TRAINER_CLAIM_OTP_SECRET", "otp-secret")
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "action-secret")

    # Create a valid claim event with OTP
    claim_event_id = f"evt_{uuid.uuid4().hex[:8]}"
    otp = "123456"
    claim_event = {
        "id": claim_event_id,
        "trainer_id": trainer_id,
        "claimant_email": "candidate@example.com.au",
        "masked_destination": "c***@example.com.au",
        "method": "email",
        "otp_digest": claim_engine.otp_digest(otp),
        "attempts": 0,
        "max_attempts": 3,
        "status": "pending_verification",
        "delivery_status": "sent",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        "created_at": now_ts,
        "updated_at": now_ts,
    }

    fake_db = _make_fake_db(trainers=[trainer_doc], claim_events=[claim_event])
    monkeypatch.setattr(server, "db", fake_db)


    res = asyncio.run(
        server.verify_trainer_claim(
            trainer_id,
            server.TrainerClaimVerifyIn(claim_event_id=claim_event_id, otp=otp),
        )
    )
    assert res.get("session", {}).get("token") is not None
    assert trainer_doc.get("claim_status") == "claimed"

    updated_caps = trainer_doc["capabilities"]
    assert updated_caps["specialties"]["basis"] == "trainer_declaration"
    assert updated_caps["specialties"]["permitted_in_projection"] is True
    assert updated_caps["specialties"]["evidence_reference"] == f"claim_event:{claim_event_id}"
    assert updated_caps["service_formats"]["basis"] == "trainer_declaration"
    assert updated_caps["service_formats"]["permitted_in_projection"] is True

    # Projection is now match-ready
    proj_verified = build_match_ready_projection(trainer_doc)
    assert proj_verified["match_eligible"] is True
    assert set(proj_verified["specialties"]) == {"puppy_training", "obedience"}
    assert set(proj_verified["service_formats"]) == {"in_home"}



def test_compute_capability_health_summary_exposes_clean_telemetry():
    """compute_capability_health_summary exposes operational capability metrics with zero owner PII."""
    import asyncio
    from services.trainer_quality import compute_capability_health_summary

    t1 = {
        "id": "t1",
        "published": True,
        "claim_status": "claimed",
        "capabilities": {
            "specialties": {"basis": "trainer_declaration", "permitted_in_projection": True},
        },
    }
    t2 = {
        "id": "t2",
        "published": True,
        "claim_status": "unclaimed",
        "capabilities": {
            "specialties": {"basis": "ai_proposed", "permitted_in_projection": False},
        },
    }
    t3 = {
        "id": "t3",
        "published": True,
        "claim_status": "claimed",
        "capabilities": {
            "specialties": {"basis": "trainer_declaration", "permitted_in_projection": False, "freshness_state": "stale"},
        },
    }

    fake_coll = _FakeCollection([t1, t2, t3])
    summary = asyncio.run(compute_capability_health_summary(fake_coll))

    assert summary["match_eligible_trainers"] == 1
    assert summary["trainers_with_declared_capabilities"] == 2
    assert summary["trainers_with_only_ai_proposed"] == 1
    assert summary["stale_capability_trainers"] == 1

    # Verify zero owner PII in capability_health_summary
    serialized = json.dumps(summary).lower()
    for marker in ["owner", "email", "phone", "dog_name", "enquiry", "passcode"]:
        assert marker not in serialized, f"capability_health_summary leaked marker: {marker}"


def test_real_melbourne_seed_trainers_map_cleanly_to_taxonomies():
    """Verify that all 20 real Melbourne seed trainers map cleanly to canonical taxonomies."""
    from pathlib import Path
    seed_path = Path(__file__).resolve().parent.parent / "data" / "melbourne_trainers_seed.json"
    assert seed_path.exists(), "melbourne_trainers_seed.json must exist"

    with open(seed_path) as f:
        seed = json.load(f)

    candidates = seed.get("candidates") or []
    assert len(candidates) >= 20, "Expected at least 20 real Melbourne seed trainers"

    for candidate in candidates:
        name = candidate["name"]
        raw_services = candidate.get("services") or []
        assert raw_services, f"Candidate {name} should have raw services listed"

        v_spec = validate_capability_category("specialties", raw_services)
        v_fmt = validate_capability_category("service_formats", raw_services)

        # Every candidate must map to at least one specialty or service format
        total_matched = len(v_spec["canonical_terms"]) + len(v_fmt["canonical_terms"])
        assert total_matched > 0, f"Real Melbourne trainer {name} with services {raw_services} failed to map to any canonical taxonomy"


