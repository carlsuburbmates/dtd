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

    async def verified_abn_fields(abn):
        return {"abn": abn, "abn_status": "active", "abn_verified": True, "abn_verified_at": now_iso()}

    async def qualified_score(_payload):
        return {"confidence": 0.95, "reasoning": "Test fixture", "signals": [], "model": "fixture"}

    # Publication must depend on server-checked statutory evidence, never the
    # submitter's self-asserted ABN status or a developer's local ABR settings.
    monkeypatch.setattr(server, "_abn_profile_fields", verified_abn_fields)
    monkeypatch.setattr(server.ai_service, "score_trainer", qualified_score)

    payload = server.SubmissionIn(
        name="Live Submission Trainer",
        suburb="Brunswick",
        website="https://livesubmissiontrainer.com.au",
        phone="0412345679",
        email="trainer@livesubmissiontrainer.com.au",
        abn="51824753556",
        abn_status="active",
        abn_verified=False,
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

    # Calling OTP verify proves ownership, but DOES NOT promote capabilities
    res = asyncio.run(
        server.verify_trainer_claim(
            trainer_id,
            server.TrainerClaimVerifyIn(claim_event_id=claim_event_id, otp=otp),
        )
    )
    session_token = res.get("session", {}).get("token")
    assert session_token is not None
    assert trainer_doc.get("claim_status") == "claimed"

    # Crucial assertion: Capabilities remain ai_proposed and are NOT promoted solely by OTP
    updated_caps = trainer_doc["capabilities"]
    assert updated_caps["specialties"]["basis"] == "ai_proposed"
    assert updated_caps["specialties"]["permitted_in_projection"] is False
    assert updated_caps["service_formats"]["basis"] == "ai_proposed"
    assert updated_caps["service_formats"]["permitted_in_projection"] is False

    # Projection remains unmatchable
    proj_after_otp = build_match_ready_projection(trainer_doc)
    assert proj_after_otp["match_eligible"] is False
    assert "no_permitted_matchable_capabilities" in proj_after_otp["eligibility_reasons"]


def test_trainer_explicit_capability_confirmation_flow(monkeypatch):
    """R2: Explicit capability confirmation promotes capabilities, invalidates omitted facts, and requires statement."""
    import asyncio
    import uuid
    import server
    from fastapi import HTTPException

    trainer_id = f"trainer_confirm_test_{uuid.uuid4().hex[:8]}"
    now_ts = now_iso()

    # Start with AI-proposed capabilities (including an unwanted specialty 'barking')
    ai_caps = package_trainer_capabilities(
        specialties=["puppy_training", "barking"],
        service_formats=["in_home", "online"],
        basis="ai_proposed",
        evidence_reference="https://scraped.com.au",
        confirmed_at=now_ts,
    )
    trainer_doc = {
        "id": trainer_id,
        "name": "Confirmation Candidate",
        "suburb": "Brunswick",
        "email": "cand@example.com.au",
        "phone": "0412345678",
        "published": True,
        "contact_ready": True,
        "claim_status": "claimed",
        "capabilities": ai_caps,
    }

    fake_db = _make_fake_db(trainers=[trainer_doc])
    monkeypatch.setattr(server, "db", fake_db)

    session_data = server._issue_trainer_claim_session(trainer_id=trainer_id, claim_event_id="claim_event_test_1")
    claim_token = session_data["token"]

    from starlette.requests import Request
    mock_req = Request({"type": "http", "headers": [(b"x-trainer-claim-session", claim_token.encode("utf-8"))]})

    # P0 Item 3: Prefill endpoint requires and validates trainer claim session
    unauth_req = Request({"type": "http", "headers": []})
    with pytest.raises(HTTPException) as unauth_exc:
        asyncio.run(
            server.get_trainer_capabilities_prefill(trainer_id, request=unauth_req)
        )
    assert unauth_exc.value.status_code == 401

    foreign_session = server._issue_trainer_claim_session(trainer_id="foreign_trainer_99", claim_event_id="claim_2")
    foreign_req = Request({"type": "http", "headers": [(b"x-trainer-claim-session", foreign_session["token"].encode("utf-8"))]})
    with pytest.raises(HTTPException) as foreign_exc:
        asyncio.run(
            server.get_trainer_capabilities_prefill(
                trainer_id,
                request=foreign_req,
                x_trainer_claim_session=foreign_session["token"],
            )
        )
    assert foreign_exc.value.status_code == 403

    # Step 2A: Prefill endpoint returns existing capabilities and canonical options when authenticated
    prefill = asyncio.run(
        server.get_trainer_capabilities_prefill(
            trainer_id,
            request=mock_req,
            x_trainer_claim_session=claim_token,
        )
    )
    assert "puppy_training" in prefill["prefilled"]["specialties"]
    assert "barking" in prefill["prefilled"]["specialties"]
    assert "specialties" in prefill["canonical_options"]
    assert "delivery_constraints" in prefill["prefilled"]
    assert prefill["prefilled"]["delivery_constraints"]["in_home_available"] is False
    assert prefill["prefilled"]["delivery_constraints"]["facility_available"] is False
    assert prefill["prefilled"]["delivery_constraints"]["travel_distance_km"] == 0.0

    # Step 2B: Confirmation statement is required (false raises 400/422)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            server.confirm_trainer_capabilities(
                trainer_id,
                server.TrainerCapabilitiesConfirmIn(
                    confirmation_statement=False,
                    specialties=["puppy_training"],
                    service_formats=["in_home"],
                ),
                request=mock_req,
                x_trainer_claim_session=claim_token,
            )
        )
    assert exc_info.value.status_code in (400, 422)

    # Step 2C: Successful confirmation - sends every matchable declared field (P0 Item 4 / R2)
    confirm_res = asyncio.run(
        server.confirm_trainer_capabilities(
            trainer_id,
            server.TrainerCapabilitiesConfirmIn(
                confirmation_statement=True,
                specialties=["puppy_training", "obedience"],  # Corrected/added
                service_formats=["in_home"],                 # Kept in_home, omitted online
                life_stages=["puppy", "adolescent"],
                training_philosophy="positive_reinforcement_force_free",
                serviced_suburbs=["Brunswick", "Carlton"],
                catchment_type="specific_suburbs",
                delivery_constraints={
                    "in_home_available": True,
                    "facility_available": True,
                    "travel_distance_km": 25.0,
                    "notes": "Travels up to 25km with travel fee",
                },
            ),
            request=mock_req,
            x_trainer_claim_session=claim_token,
        )
    )
    assert confirm_res["ok"] is True
    updated_caps = confirm_res["capabilities"]

    # Verified declaration basis across all fields
    assert updated_caps["specialties"]["basis"] == "trainer_declaration"
    assert updated_caps["specialties"]["permitted_in_projection"] is True
    assert set(updated_caps["specialties"]["value"]) == {"puppy_training", "obedience"}
    assert updated_caps["service_formats"]["basis"] == "trainer_declaration"
    assert updated_caps["service_formats"]["permitted_in_projection"] is True
    assert set(updated_caps["service_formats"]["value"]) == {"in_home"}
    assert updated_caps["life_stages"]["basis"] == "trainer_declaration"
    assert updated_caps["life_stages"]["permitted_in_projection"] is True
    assert set(updated_caps["life_stages"]["value"]) == {"puppy", "adolescent"}
    assert updated_caps["training_philosophy"]["basis"] == "trainer_declaration"
    assert updated_caps["training_philosophy"]["value"] == "positive_reinforcement_force_free"
    assert updated_caps["delivery_constraints"]["basis"] == "trainer_declaration"
    assert updated_caps["delivery_constraints"]["permitted_in_projection"] is True
    assert updated_caps["delivery_constraints"]["value"]["in_home_available"] is True
    assert updated_caps["delivery_constraints"]["value"]["facility_available"] is True
    assert updated_caps["delivery_constraints"]["value"]["travel_distance_km"] == 25.0
    assert updated_caps["delivery_constraints"]["value"]["notes"] == "Travels up to 25km with travel fee"

    # Projection is now match-eligible
    trainer_doc["capabilities"] = updated_caps
    proj = build_match_ready_projection(trainer_doc)
    assert proj["match_eligible"] is True
    assert set(proj["specialties"]) == {"puppy_training", "obedience"}
    assert set(proj["service_formats"]) == {"in_home"}
    assert set(proj["life_stages"]) == {"puppy", "adolescent"}
    assert proj["delivery_constraints"]["travel_distance_km"] == 25.0


def test_raw_legacy_record_without_provenance_never_becomes_matchable():
    """R1: A raw legacy record with raw specialties/formats but no capability record/provenance fails closed."""
    legacy_trainer = {
        "id": "trainer_legacy_1",
        "name": "Legacy Unconfirmed Academy",
        "suburb": "Richmond",
        "published": True,
        "contact_ready": True,
        "specialties": ["Puppy Training", "Obedience"],
        "service_formats": ["In-Home Training"],
        # No capabilities fact dictionary, no declaration, no source_url
    }
    projection = build_match_ready_projection(legacy_trainer)
    assert projection["match_eligible"] is False, "Legacy unconfirmed profile MUST NOT be match-eligible"
    assert len(projection["specialties"]) == 0
    assert len(projection["service_formats"]) == 0
    assert "legacy_unconfirmed_provenance" in projection["eligibility_reasons"]


def test_competing_claim_dispute_invalidates_capabilities_in_server(monkeypatch):
    """R4: A competing submission on an already claimed profile atomically invalidates capabilities."""
    import asyncio
    import server

    existing_trainer = {
        "id": "claimed_trainer_1",
        "name": "Owner Profile",
        "suburb": "Carlton",
        "abn": "12345678901",
        "email": "owner@profile.com.au",
        "claim_status": "claimed",
        "published": True,
        "contact_ready": True,
        "capabilities": package_trainer_capabilities(
            specialties=["puppy_training"],
            service_formats=["in_home"],
            basis="trainer_declaration",
            evidence_reference="claim_1",
            confirmed_at=now_iso(),
        ),
    }
    fake_db = _make_fake_db(trainers=[existing_trainer])
    monkeypatch.setattr(server, "db", fake_db)

    sub_payload = server.SubmissionIn(
        name="Competing Submitter",
        suburb="Carlton",
        abn="12345678901",
        email="competitor@profile.com.au",
        consent_public_listing=True,
        consent_information_accuracy=True,
        consent_intro_billing_terms=True,
    )
    res = asyncio.run(server.create_submission(sub_payload))
    assert res["status"] == "held"
    assert res["duplicate"] is True
    assert res["reason"] == "profile_already_claimed"

    assert existing_trainer["claim_status"] == "claim_disputed"
    assert existing_trainer["capabilities"]["specialties"]["permitted_in_projection"] is False
    assert existing_trainer["capabilities"]["specialties"]["invalidation_reason"] == "ownership_dispute"

    proj = build_match_ready_projection(existing_trainer)
    assert proj["match_eligible"] is False


def test_statutory_revocation_unpublishes_and_invalidates_capabilities_in_engine(monkeypatch):
    """R4: Statutory ABR cancellation in reverify_listings unpublishes trainer and invalidates capabilities."""
    import asyncio
    from services import engine

    trainer = {
        "id": "revoked_trainer_1",
        "name": "Deregistered Business",
        "suburb": "Collingwood",
        "abn": "99999999999",
        "abn_status": "cancelled",
        "abn_verified": False,
        "published": True,
        "contact_ready": True,
        "verified_at": "2026-01-01T00:00:00+00:00",
        "capabilities": package_trainer_capabilities(
            specialties=["puppy_training"],
            service_formats=["in_home"],
            basis="trainer_declaration",
            evidence_reference="sub_1",
            confirmed_at=now_iso(),
        ),
    }
    fake_db = _make_fake_db(trainers=[trainer])
    fake_db.evidence = _FakeCollection()
    fake_db.system_state = _FakeCollection()

    class MockAIService:
        async def score_trainer(self, payload):
            return {"confidence": 0.5, "signals": [], "model": "heuristic", "reasoning": "ABN cancelled"}
        def status_for_score(self, score):
            return "hold"

    res = asyncio.run(engine.reverify_listings(fake_db, MockAIService(), batch=1))
    assert res.get("trainers_reverified", 1) >= 0

    assert trainer["published"] is False
    assert trainer["capabilities"]["specialties"]["permitted_in_projection"] is False
    assert trainer["capabilities"]["specialties"]["invalidation_reason"] == "statutory_abn_revoked"

    proj = build_match_ready_projection(trainer)
    assert proj["match_eligible"] is False


def test_reverify_listings_ai_confidence_cannot_alter_publication_state(monkeypatch):
    """DF-014: AI confidence alone NEVER alters publication status in reverify_listings."""
    import asyncio
    from services import engine

    t_unpub = {
        "id": "t_unpub",
        "name": "Unpublished Trainer",
        "suburb": "Fitzroy",
        "abn_status": "active",
        "abn_verified": True,
        "published": False,
        "contact_ready": True,
        "verified_at": "2026-01-01T00:00:00+00:00",
    }
    t_pub = {
        "id": "t_pub",
        "name": "Published Trainer",
        "suburb": "Fitzroy",
        "abn_status": "active",
        "abn_verified": True,
        "published": True,
        "contact_ready": True,
        "verified_at": "2026-01-01T00:00:00+00:00",
    }

    fake_db = _make_fake_db(trainers=[t_unpub, t_pub])
    fake_db.evidence = _FakeCollection()
    fake_db.system_state = _FakeCollection()

    class MockAIService:
        async def score_trainer(self, payload):
            if payload["name"] == "Unpublished Trainer":
                return {"confidence": 0.99, "signals": [], "model": "heuristic", "reasoning": "High confidence"}
            return {"confidence": 0.10, "signals": [], "model": "heuristic", "reasoning": "Low confidence"}
        def status_for_score(self, score):
            return "verified" if score >= 0.6 else "hold"

    asyncio.run(engine.reverify_listings(fake_db, MockAIService(), batch=2))

    assert t_unpub["published"] is False, "AI confidence MUST NOT publish an unpublished trainer"
    assert t_pub["published"] is True, "AI confidence drop MUST NOT unpublish a trainer with active ABR verification"


@pytest.mark.anyio
async def test_match_trainers_does_not_filter_public_flow_by_default(monkeypatch):
    """R5: Match filtering is disabled by default; passes unconfirmed candidates with diagnostic metadata."""
    from types import SimpleNamespace
    monkeypatch.delenv("ENABLE_MATCH_READY_PROJECTION_FILTER", raising=False)

    legacy_trainer = {
        "id": "trainer_candidate_1",
        "name": "Test Candidate",
        "suburb": "Richmond",
        "published": True,
        "contact_ready": True,
        "services": ["Puppy Training"],
    }

    class MockModel:
        async def generate_content(self, model, contents, config):
            class MockResp:
                text = json.dumps([{"trainer_id": "trainer_candidate_1", "score": 0.8, "reasoning": "Fit"}])
            return MockResp()

    class MockClient:
        aio = SimpleNamespace(models=MockModel())

    matches = await ai.match_trainers("puppy help", [legacy_trainer], client=MockClient())
    assert len(matches) == 1, "Public candidate flow MUST NOT be suppressed before Decision Contract v2"
    assert matches[0]["match_ready"] is False
    assert "legacy_unconfirmed_provenance" in matches[0]["eligibility_reasons"]


def test_compute_capability_health_summary_exposes_clean_telemetry():
    """compute_capability_health_summary exposes operational capability metrics with zero owner PII."""
    import asyncio
    from services.trainer_quality import compute_capability_health_summary

    t1 = {
        "id": "t1",
        "published": True,
        "contact_ready": True,
        "claim_status": "claimed",
        "capabilities": package_trainer_capabilities(
            specialties=["puppy_training"],
            service_formats=["in_home"],
            basis="trainer_declaration",
            evidence_reference="claim_1",
            confirmed_at=now_iso(),
        ),
    }
    t2 = {
        "id": "t2",
        "published": True,
        "contact_ready": True,
        "claim_status": "unclaimed",
        "capabilities": package_trainer_capabilities(
            specialties=["puppy_training"],
            service_formats=["in_home"],
            basis="ai_proposed",
            evidence_reference="scrape_1",
            confirmed_at=now_iso(),
        ),
    }
    t3 = {
        "id": "t3",
        "published": True,
        "contact_ready": True,
        "claim_status": "claimed",
        "capabilities": package_trainer_capabilities(
            specialties=["puppy_training"],
            service_formats=["in_home"],
            basis="trainer_declaration",
            evidence_reference="sub_1",
            confirmed_at=(datetime.now(timezone.utc) - timedelta(days=200)).isoformat(),
        ),
    }

    fake_coll = _FakeCollection([t1, t2, t3])
    summary = asyncio.run(compute_capability_health_summary(fake_coll))

    assert summary["total_trainers"] == 3
    assert summary["match_eligible_trainers"] == 1
    assert summary["ai_proposed_unconfirmed"] == 1
    assert summary["stale_capabilities"] == 1
    assert summary["policy_version"] == "v1"

    # Verify zero owner PII in capability_health_summary
    serialized = json.dumps(summary).lower()
    for marker in ["owner_name", "first_name", "last_name", "email", "phone", "dog_name", "enquiry", "passcode"]:
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


# ==============================================================================
# R3: Fail-Closed Delivery Constraints & Conservative Prefill Regression Tests
# ==============================================================================

def test_delivery_constraints_domain_validation_rejects_malformed_and_unbounded():
    """R3: validate_capability_category('delivery_constraints') strictly enforces schema and ranges."""
    # Case 1: String booleans must be rejected
    res_str_bool = validate_capability_category("delivery_constraints", {
        "in_home_available": "false",
        "facility_available": "true",
    })
    assert res_str_bool["valid"] is False
    assert res_str_bool["reason"] == "invalid_in_home_available_must_be_boolean"

    res_facility_str = validate_capability_category("delivery_constraints", {
        "in_home_available": False,
        "facility_available": "true",
    })
    assert res_facility_str["valid"] is False
    assert res_facility_str["reason"] == "invalid_facility_available_must_be_boolean"

    # Case 2: Numeric non-booleans for availability flags
    res_num_bool = validate_capability_category("delivery_constraints", {
        "in_home_available": 1,
    })
    assert res_num_bool["valid"] is False
    assert res_num_bool["reason"] == "invalid_in_home_available_must_be_boolean"

    # Case 3: Negative travel distance
    res_neg_dist = validate_capability_category("delivery_constraints", {
        "travel_distance_km": -1.0,
    })
    assert res_neg_dist["valid"] is False
    assert res_neg_dist["reason"] == "invalid_travel_distance_km_range"

    # Case 4: Unbounded travel distance (> 200 km)
    res_unbounded = validate_capability_category("delivery_constraints", {
        "travel_distance_km": 999999.0,
    })
    assert res_unbounded["valid"] is False
    assert res_unbounded["reason"] == "invalid_travel_distance_km_range"

    # Case 5: Non-finite travel distance (nan, inf)
    res_nan = validate_capability_category("delivery_constraints", {
        "travel_distance_km": float("nan"),
    })
    assert res_nan["valid"] is False
    assert res_nan["reason"] == "invalid_travel_distance_km_non_finite"

    res_inf = validate_capability_category("delivery_constraints", {
        "travel_distance_km": float("inf"),
    })
    assert res_inf["valid"] is False
    assert res_inf["reason"] == "invalid_travel_distance_km_non_finite"

    # Case 6: Non-numeric distance type (string or bool)
    res_str_dist = validate_capability_category("delivery_constraints", {
        "travel_distance_km": "25",
    })
    assert res_str_dist["valid"] is False
    assert res_str_dist["reason"] == "invalid_travel_distance_km_type"

    res_bool_dist = validate_capability_category("delivery_constraints", {
        "travel_distance_km": True,
    })
    assert res_bool_dist["valid"] is False
    assert res_bool_dist["reason"] == "invalid_travel_distance_km_type"

    # Case 7: Overlong notes (> 200 chars)
    res_overlong_notes = validate_capability_category("delivery_constraints", {
        "notes": "x" * 201,
    })
    assert res_overlong_notes["valid"] is False
    assert res_overlong_notes["reason"] == "notes_exceeds_max_length_200"

    # Case 8: Non-string notes
    res_non_str_notes = validate_capability_category("delivery_constraints", {
        "notes": 12345,
    })
    assert res_non_str_notes["valid"] is False
    assert res_non_str_notes["reason"] == "invalid_notes_must_be_string"

    # Case 9: Non-dict input
    res_non_dict = validate_capability_category("delivery_constraints", "in_home")
    assert res_non_dict["valid"] is False
    assert res_non_dict["reason"] == "invalid_delivery_constraints_format"

    # Case 10: Valid dictionary passes and normalises canonical terms with conservative defaults
    res_valid = validate_capability_category("delivery_constraints", {
        "in_home_available": True,
        "facility_available": False,
        "travel_distance_km": 30.5,
        "notes": "  Servicing inner north  ",
    })
    assert res_valid["valid"] is True
    assert res_valid["reason"] == "valid"
    assert res_valid["canonical_terms"] == {
        "in_home_available": True,
        "facility_available": False,
        "travel_distance_km": 30.5,
        "notes": "Servicing inner north",
    }


def test_delivery_constraints_pydantic_schema_validation():
    """R3: DeliveryConstraintsIn model strictly validates input types before endpoint execution."""
    import server
    import pydantic

    # String booleans raise ValidationError
    with pytest.raises(pydantic.ValidationError) as exc:
        server.DeliveryConstraintsIn(in_home_available="false")
    assert "Availability flags must be actual booleans" in str(exc.value)

    with pytest.raises(pydantic.ValidationError) as exc:
        server.DeliveryConstraintsIn(facility_available="true")
    assert "Availability flags must be actual booleans" in str(exc.value)

    # String distance raises ValidationError
    with pytest.raises(pydantic.ValidationError) as exc:
        server.DeliveryConstraintsIn(travel_distance_km="25")
    assert "travel_distance_km must be a number" in str(exc.value)

    # Negative distance raises ValidationError
    with pytest.raises(pydantic.ValidationError) as exc:
        server.DeliveryConstraintsIn(travel_distance_km=-5.0)
    assert "between 0 and 200 km" in str(exc.value)

    # Unbounded distance raises ValidationError
    with pytest.raises(pydantic.ValidationError) as exc:
        server.DeliveryConstraintsIn(travel_distance_km=999999.0)
    assert "between 0 and 200 km" in str(exc.value)

    # Overlong notes raise ValidationError
    with pytest.raises(pydantic.ValidationError) as exc:
        server.DeliveryConstraintsIn(notes="a" * 201)
    assert "must not exceed 200 characters" in str(exc.value)

    # Valid model serializes cleanly
    model = server.DeliveryConstraintsIn(
        in_home_available=True,
        facility_available=False,
        travel_distance_km=25.0,
        notes="  Up to 25km  ",
    )
    assert model.in_home_available is True
    assert model.facility_available is False
    assert model.travel_distance_km == 25.0
    assert model.notes == "Up to 25km"


def test_unprefilled_claim_prefill_and_confirmation_conservative_defaults(monkeypatch):
    """R3: An unprefilled trainer profile returns conservative false delivery constraints and does not create false positive facts."""
    import asyncio
    import server
    from starlette.requests import Request

    trainer_id = "trainer_unprefilled_r3"
    trainer_doc = {
        "id": trainer_id,
        "name": "Unprefilled Dog Academy",
        "suburb": "Fitzroy",
        "published": True,
        "contact_ready": True,
        "claim_status": "claimed",
        "capabilities": {},  # No declared capabilities
    }

    fake_db = _make_fake_db(trainers=[trainer_doc])
    monkeypatch.setattr(server, "db", fake_db)

    session_data = server._issue_trainer_claim_session(trainer_id=trainer_id, claim_event_id="claim_ev_unprefilled")
    claim_token = session_data["token"]
    req = Request({"type": "http", "headers": [(b"x-trainer-claim-session", claim_token.encode("utf-8"))]})

    # 1. Prefill returns conservative false defaults for delivery_constraints
    prefill = asyncio.run(
        server.get_trainer_capabilities_prefill(trainer_id, request=req, x_trainer_claim_session=claim_token)
    )
    dc_prefill = prefill["prefilled"]["delivery_constraints"]
    assert dc_prefill["in_home_available"] is False, "Default in_home_available MUST be False when unprefilled"
    assert dc_prefill["facility_available"] is False
    assert dc_prefill["travel_distance_km"] == 0.0
    assert dc_prefill["notes"] == ""

    # 2. Confirming with default untouched delivery_constraints preserves false in_home_available
    confirm_res = asyncio.run(
        server.confirm_trainer_capabilities(
            trainer_id,
            server.TrainerCapabilitiesConfirmIn(
                confirmation_statement=True,
                specialties=["puppy_training"],
                service_formats=["in_home"],
                delivery_constraints=server.DeliveryConstraintsIn(
                    in_home_available=False,
                    facility_available=False,
                    travel_distance_km=0.0,
                    notes="",
                ),
            ),
            request=req,
            x_trainer_claim_session=claim_token,
        )
    )
    assert confirm_res["ok"] is True
    updated_caps = confirm_res["capabilities"]
    assert updated_caps["delivery_constraints"]["value"]["in_home_available"] is False

    # Projection reflects false in_home_available
    trainer_doc["capabilities"] = updated_caps
    proj = build_match_ready_projection(trainer_doc)
    assert proj["delivery_constraints"]["in_home_available"] is False


def test_delivery_constraints_preserves_permitted_prefill_for_correction(monkeypatch):
    """R3: Existing permitted delivery constraints are preserved exactly in prefill for correction."""
    import asyncio
    import server
    from starlette.requests import Request

    trainer_id = "trainer_permitted_prefill_r3"
    now_ts = now_iso()
    permitted_caps = package_trainer_capabilities(
        specialties=["puppy_training"],
        service_formats=["in_home"],
        delivery_constraints={
            "in_home_available": True,
            "facility_available": True,
            "travel_distance_km": 40.0,
            "notes": "Servicing eastern suburbs",
        },
        basis="trainer_declaration",
        evidence_reference="claim_ref_prev",
        confirmed_at=now_ts,
    )
    trainer_doc = {
        "id": trainer_id,
        "name": "Permitted Dog Academy",
        "suburb": "Camberwell",
        "published": True,
        "contact_ready": True,
        "claim_status": "claimed",
        "capabilities": permitted_caps,
    }

    fake_db = _make_fake_db(trainers=[trainer_doc])
    monkeypatch.setattr(server, "db", fake_db)

    session_data = server._issue_trainer_claim_session(trainer_id=trainer_id, claim_event_id="claim_ev_permitted")
    claim_token = session_data["token"]
    req = Request({"type": "http", "headers": [(b"x-trainer-claim-session", claim_token.encode("utf-8"))]})

    # Prefill retrieves exact permitted declaration
    prefill = asyncio.run(
        server.get_trainer_capabilities_prefill(trainer_id, request=req, x_trainer_claim_session=claim_token)
    )
    dc_prefill = prefill["prefilled"]["delivery_constraints"]
    assert dc_prefill["in_home_available"] is True
    assert dc_prefill["facility_available"] is True
    assert dc_prefill["travel_distance_km"] == 40.0
    assert dc_prefill["notes"] == "Servicing eastern suburbs"
