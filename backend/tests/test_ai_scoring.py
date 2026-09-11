"""Unit tests for M1-AI Gemini Foundation service.

Validates:
  1. No-key fallback (deterministic extraction, matching, scoring without live network calls)
  2. Valid structured response (Gemini extraction, explainable diagnostic matching, scoring)
  3. Malformed model response rejection (non-JSON, missing schema fields, invalid types)
  4. Timeout / provider failure handling (safe fallback, degradation event)
  5. Rate-limit failure handling (429/quota exhaustion, safe fallback, degradation event)
  6. Safety boundary (AI output alone NEVER publishes, verifies ABN, or creates trust claims)
  7. /ops degradation visibility (cases generated, sanitized without prompts/secrets/source text)
  8. Paid tier neutrality (commercial tier is never passed to model and never influences fit)
"""

import asyncio
import json
import pytest
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from services import ai as ai_service
import server


@pytest.fixture
def anyio_backend():
    """The backend service is asyncio-based; do not require an undeclared Trio runtime."""
    return "asyncio"


@pytest.fixture(autouse=True)
def cleanup_ai_state(monkeypatch):
    """Ensure clean test environment without live credentials."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ai_service.clear_degradation_events()
    ai_service.set_db(None)
    yield
    ai_service.clear_degradation_events()
    ai_service.set_db(None)


# ---------- Mock Helpers ----------

class MockModelResponse:
    def __init__(self, text: str):
        self.text = text


def make_mock_client(response_text: Optional[str] = None, side_effect: Optional[Exception] = None):
    """Create a mock Google GenAI client whose aio.models.generate_content can be controlled."""
    mock_client = MagicMock()
    mock_models = MagicMock()
    mock_aio = MagicMock()

    if side_effect:
        mock_models.generate_content = AsyncMock(side_effect=side_effect)
    else:
        mock_models.generate_content = AsyncMock(return_value=MockModelResponse(response_text or "{}"))

    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    return mock_client


# ---------- 1. No-Key Fallback ----------

def test_is_gemini_configured_without_key():
    assert not ai_service.is_gemini_configured()
    assert ai_service.get_gemini_client() is None


@pytest.mark.anyio
async def test_no_key_fallback_extraction():
    raw_source = (
        "Positive Paws Melbourne. Force-free and positive reinforcement puppy training and leash reactivity. "
        "In-home consultations in Richmond and South Yarra."
    )
    result = await ai_service.extract_trainer_source(raw_source)

    assert result["fallback_used"] is True
    assert result["model"] == "heuristic-fallback"
    assert result["training_philosophy"] == "Positive Reinforcement / Force-Free"
    assert "puppy_training" in result["specialties"]
    assert "leash_reactivity" in result["specialties"]
    assert "in_home" in result["service_formats"]
    assert result["confidence"] > 0.0
    assert result["published"] is False
    assert result["abn_verified"] is False
    # Local development without a key must NOT generate degradation events
    events = await ai_service.get_degradation_events()
    assert len(events) == 0


@pytest.mark.anyio
async def test_no_key_fallback_matching():
    trainers = [
        {
            "id": "t1",
            "name": "Bark Busters Richmond",
            "suburb": "Richmond",
            "services": ["puppy", "manners"],
            "bio": "Specialising in puppy training in Richmond",
        },
        {
            "id": "t2",
            "name": "Melbourne Dog Training",
            "suburb": "Brunswick",
            "services": ["agility"],
            "bio": "Agility and sport dogs only",
        },
    ]
    matches = await ai_service.match_trainers("I need puppy manners help in Richmond", trainers)

    assert len(matches) > 0
    assert matches[0]["trainer_id"] == "t1"
    assert matches[0]["score"] >= 0.4
    assert "reasoning" in matches[0]


@pytest.mark.anyio
async def test_no_key_fallback_scoring():
    payload = {
        "website": "https://k9training.com.au",
        "suburb": "Richmond",
        "phone": "0400 123 456",
        "services": ["puppy"],
        "bio": "Certified dog trainer with 10 years experience serving inner Melbourne.",
    }
    score = await ai_service.score_trainer(payload)

    assert score["model"] == "heuristic"
    assert score["confidence"] >= 0.70
    assert score["published"] is False
    assert score["abn_verified"] is False
    assert len(score["signals"]) > 0


# ---------- 2. Valid Structured Response ----------

@pytest.mark.anyio
async def test_valid_structured_extraction():
    valid_payload = {
        "training_philosophy": "Positive Reinforcement / Force-Free",
        "specialties": ["puppy_training", "leash_reactivity", "separation_anxiety"],
        "service_formats": ["in_home", "facility"],
        "serviced_suburbs": ["Richmond", "Fitzroy", "Abbotsford"],
        "confidence": 0.94,
        "reasoning": "Clear and consistent force-free evidence with defined suburban service radius.",
        "signals": ["Delta Institute certified", "Zero-force guarantee listed on website"],
    }
    mock_client = make_mock_client(response_text=json.dumps(valid_payload))

    result = await ai_service.extract_trainer_source("Raw trainer bio...", client=mock_client)

    assert result["fallback_used"] is False
    assert result["model"] == ai_service.GEMINI_MODEL
    assert result["training_philosophy"] == "Positive Reinforcement / Force-Free"
    assert result["specialties"] == ["puppy_training", "leash_reactivity", "separation_anxiety"]
    assert result["service_formats"] == ["in_home", "facility"]
    assert result["serviced_suburbs"] == ["Richmond", "Fitzroy", "Abbotsford"]
    assert result["confidence"] == 0.94
    assert result["published"] is False
    assert result["abn_verified"] is False


@pytest.mark.anyio
async def test_valid_diagnostic_matching():
    mock_matches = [
        {
            "trainer_id": "t1",
            "score": 0.95,
            "reasoning": "Extensive experience with leash aggression in urban environments.",
        },
        {
            "trainer_id": "t2",
            "score": 0.70,
            "reasoning": "Offers general behavior consultations in nearby suburb.",
        },
    ]
    mock_client = make_mock_client(response_text=json.dumps(mock_matches))

    candidates = [
        {
            "id": "t1",
            "name": "Reactivity Specialist",
            "suburb": "Richmond",
            "tier": "citywide",
            "services": ["reactivity"],
        },
        {
            "id": "t2",
            "name": "General K9",
            "suburb": "Cremorne",
            "tier": "core",
            "services": ["obedience"],
        },
    ]
    matches = await ai_service.match_trainers("Dog lunges at other dogs on leash", candidates, client=mock_client)

    assert len(matches) == 2
    assert matches[0]["trainer_id"] == "t1"
    assert matches[0]["score"] == 0.95
    assert "Extensive experience" in matches[0]["reasoning"]

    # Verify candidate input sent to model did NOT include tier
    call_args = mock_client.aio.models.generate_content.call_args
    prompt_sent = call_args.kwargs.get("contents") or call_args.args[0]
    assert "citywide" not in prompt_sent
    assert '"tier"' not in prompt_sent


@pytest.mark.anyio
async def test_valid_structured_scoring():
    valid_score = {
        "confidence": 0.88,
        "reasoning": (
            "Strong evidence of an active Melbourne business with verified domain and local physical address."
        ),
        "signals": ["Has Australian business phone number", "Provides physical training address in Moorabbin"],
    }
    mock_client = make_mock_client(response_text=json.dumps(valid_score))

    score = await ai_service.score_trainer({"website": "https://example.com.au"}, client=mock_client)

    assert score["confidence"] == 0.88
    assert score["model"] == ai_service.GEMINI_MODEL
    assert score["fallback_used"] is False
    assert "Moorabbin" in score["signals"][1]
    assert score["published"] is False
    assert score["abn_verified"] is False


# ---------- 3. Malformed Response Rejection ----------

@pytest.mark.anyio
async def test_malformed_json_extraction_triggers_fallback():
    mock_client = make_mock_client(response_text="Not valid JSON at all! {unclosed bracket")

    result = await ai_service.extract_trainer_source("Positive puppy training in Richmond", client=mock_client)

    assert result["fallback_used"] is True
    assert result["model"] == "heuristic-fallback"
    assert "puppy_training" in result["specialties"]

    # Bounded degradation event must be recorded
    events = await ai_service.get_degradation_events()
    assert len(events) == 1
    assert events[0]["error_type"] == "malformed_output"
    assert events[0]["error_code"] == "SCHEMA_VALIDATION_FAILED"
    assert events[0]["fallback_used"] is True


@pytest.mark.anyio
async def test_missing_schema_fields_extraction_triggers_fallback():
    # Missing required 'specialties' and 'confidence'
    incomplete = {
        "training_philosophy": "Positive Reinforcement / Force-Free",
        "service_formats": ["in_home"],
    }
    mock_client = make_mock_client(response_text=json.dumps(incomplete))

    result = await ai_service.extract_trainer_source("Some text", client=mock_client)

    assert result["fallback_used"] is True
    events = await ai_service.get_degradation_events()
    assert len(events) == 1
    assert events[0]["error_type"] == "malformed_output"


@pytest.mark.anyio
async def test_invalid_types_extraction_triggers_fallback():
    # Confidence is string not float, specialties is not a list
    invalid_data = {
        "training_philosophy": "Positive Reinforcement / Force-Free",
        "specialties": "not_a_list",
        "service_formats": ["in_home"],
        "serviced_suburbs": ["Richmond"],
        "confidence": "super_high",
        "reasoning": "Looks good",
    }
    mock_client = make_mock_client(response_text=json.dumps(invalid_data))

    result = await ai_service.extract_trainer_source("Some text", client=mock_client)

    assert result["fallback_used"] is True
    events = await ai_service.get_degradation_events()
    assert len(events) == 1
    assert events[0]["error_type"] == "malformed_output"


@pytest.mark.anyio
async def test_matching_unknown_trainer_id_triggers_fallback():
    mock_matches = [
        {"trainer_id": "ghost_id_not_in_pool", "score": 0.99, "reasoning": "Hallucinated match."}
    ]
    mock_client = make_mock_client(response_text=json.dumps(mock_matches))

    candidates = [
        {"id": "valid_trainer_1", "name": "Real Trainer", "suburb": "Richmond", "services": ["puppy"]}
    ]
    matches = await ai_service.match_trainers("Puppy help", candidates, client=mock_client)

    assert len(matches) == 1
    assert matches[0]["trainer_id"] == "valid_trainer_1"  # Fallback used valid ID
    events = await ai_service.get_degradation_events()
    assert len(events) == 1
    assert events[0]["error_type"] == "malformed_output"


# ---------- 4. Timeout / Provider Failure ----------

@pytest.mark.anyio
async def test_timeout_triggers_fallback_and_degradation():
    mock_client = make_mock_client(side_effect=asyncio.TimeoutError())

    result = await ai_service.extract_trainer_source("Trainer bio", client=mock_client)

    assert result["fallback_used"] is True
    events = await ai_service.get_degradation_events()
    assert len(events) == 1
    assert events[0]["error_type"] == "timeout"
    assert events[0]["error_code"] == "TIMEOUT"
    assert "timed out" in events[0]["message"]


@pytest.mark.anyio
async def test_service_unavailable_triggers_fallback_and_degradation():
    mock_client = make_mock_client(side_effect=Exception("503 Service Unavailable: High load"))

    result = await ai_service.score_trainer({"website": "https://example.com"}, client=mock_client)

    assert result["model"] == "heuristic"
    events = await ai_service.get_degradation_events()
    assert len(events) == 1
    assert events[0]["error_type"] == "unavailable_service"
    assert events[0]["error_code"] == "SERVICE_UNAVAILABLE"


# ---------- 5. Rate-Limit Failure ----------

@pytest.mark.anyio
async def test_rate_limit_triggers_fallback_and_degradation():
    mock_client = make_mock_client(side_effect=Exception("429 ResourceExhausted: Quota exceeded for quota metric"))

    candidates = [{"id": "t1", "name": "Trainer", "suburb": "Richmond", "services": ["puppy"]}]
    matches = await ai_service.match_trainers("Puppy training", candidates, client=mock_client)

    assert len(matches) == 1
    assert matches[0]["trainer_id"] == "t1"
    events = await ai_service.get_degradation_events()
    assert len(events) == 1
    assert events[0]["error_type"] == "rate_limit"
    assert events[0]["error_code"] == "RATE_LIMIT_429"


# ---------- 6. Safety Boundary: No Unsupported Publication or Verification ----------

@pytest.mark.anyio
async def test_ai_output_cannot_publish_or_verify_abn():
    """Even if model claims a listing is published or ABN verified, the schema layer zeroes it."""
    malicious_injection = {
        "training_philosophy": "Positive Reinforcement / Force-Free",
        "specialties": ["puppy_training"],
        "service_formats": ["in_home"],
        "serviced_suburbs": ["Richmond"],
        "confidence": 0.99,
        "reasoning": "Claiming official verification",
        "signals": ["Fabricated verified seal"],
        "published": True,
        "abn_verified": True,
        "trust_badge": "government_verified",
    }
    mock_client = make_mock_client(response_text=json.dumps(malicious_injection))

    extracted = await ai_service.extract_trainer_source("Text", client=mock_client)
    assert extracted["published"] is False
    assert extracted["abn_verified"] is False
    assert extracted["trust_badge"] is None

    score_injection = {
        "confidence": 0.99,
        "reasoning": "Looks real",
        "signals": ["Verified"],
        "published": True,
        "abn_verified": True,
    }
    mock_client_score = make_mock_client(response_text=json.dumps(score_injection))
    scored = await ai_service.score_trainer({}, client=mock_client_score)
    assert scored["published"] is False
    assert scored["abn_verified"] is False


# ---------- 7. /ops Degradation Visibility & Sanitization ----------

@pytest.mark.anyio
async def test_degradation_event_sanitization_no_prompts_no_secrets():
    secret_key = "AIzaSy_SECRET_API_KEY_12345"
    private_source_text = "Private client notes about a sensitive dog aggression case."

    # Trigger a rate-limit error
    mock_client = make_mock_client(side_effect=Exception(f"429 quota error while using {secret_key}"))
    await ai_service.extract_trainer_source(private_source_text, client=mock_client)

    events = await ai_service.get_degradation_events()
    assert len(events) == 1
    ev = events[0]

    # Verify no prompt, source, or secret leakage
    serialized = json.dumps(ev)
    assert secret_key not in serialized
    assert private_source_text not in serialized
    assert "Private client notes" not in serialized
    assert ev["error_type"] == "rate_limit"
    assert ev["operation"] == "trainer_source_extraction"


@pytest.mark.anyio
async def test_ops_degradation_case_formatting():
    # Record a synthetic degradation event
    await ai_service.record_degradation_event(
        event_type="timeout",
        error_code="TIMEOUT",
        message="Gemini diagnostic_matching timed out after 5.0s; deterministic fallback engaged.",
        operation="diagnostic_matching",
    )

    cases = await ai_service.get_ops_degradation_cases()
    assert len(cases) == 1
    c = cases[0]
    assert c["case_type"] == "ai_degradation_case"
    assert c["canonical_user_type"] == "System / AI Integration"
    assert c["workflow"] == "AI scoring and matching"
    assert c["entity_type"] == "ai_service"
    assert "TIMEOUT" in c["risk_reason_codes"]
    assert c["responsibility_layer"] == "Layer 1 — Normal Ops"
    assert any(row["label"] == "Fallback used" and row["value"] == "true" for row in c["detail_rows"])


@pytest.mark.anyio
async def test_ops_case_rows_includes_ai_degradation(monkeypatch):
    class _EmptyCursor:
        def sort(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        async def to_list(self, *a, **kw):
            return []

    class _MockColl:
        def find(self, *a, **kw):
            return _EmptyCursor()

    class _MockDb:
        def __getattr__(self, name):
            return _MockColl()

    monkeypatch.setattr(server, "db", _MockDb())

    ai_case = {
        "case_id": "ai_degradation:test1",
        "case_type": "ai_degradation_case",
        "title": "AI provider degradation · Timeout",
        "summary": "Gemini timed out",
    }
    ops_rows = await server._ops_case_rows(
        discovery_summary={},
        waitlist_summary={},
        loop_statuses={},
        reactivation_case_rows=[],
        source_ingestion_state_rows=[],
        message_log=[],
        ai_degradation_cases=[ai_case],
    )
    case_ids = {r["case_id"] for r in ops_rows}
    assert "ai_degradation:test1" in case_ids


# ---------- 8. Paid Tier Neutrality ----------

@pytest.mark.anyio
async def test_paid_tier_does_not_bias_matching():
    trainers = [
        {
            "id": "trainer_citywide_sponsor",
            "name": "Big Brand Trainer",
            "suburb": "Geelong",
            "tier": "citywide",
            "services": ["agility"],
            "bio": "Agility obstacle training only",
        },
        {
            "id": "trainer_free_unclaimed",
            "name": "Local Puppy Expert",
            "suburb": "Brunswick",
            "tier": "unclaimed",
            "services": ["puppy_training", "toilet_training"],
            "bio": "Brunswick specialist in puppy toilet training and early socialization",
        },
    ]

    # In heuristic fallback: free local puppy trainer matches query, citywide agility trainer does not
    matches = await ai_service.match_trainers("I need puppy toilet training in Brunswick", trainers)
    assert len(matches) > 0
    assert matches[0]["trainer_id"] == "trainer_free_unclaimed"
    # Even though trainer_citywide_sponsor has citywide tier, it must NOT rank higher
    if len(matches) > 1:
        assert matches[0]["score"] > matches[1]["score"]


# ---------- 9. M1-AI Hard Safety Boundary Regressions ----------

class _MockCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, size):
        self._rows = self._rows[:size]
        return self

    async def to_list(self, _size=None):
        return list(self._rows)


class _MockCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.inserted = []

    @staticmethod
    def _matches(row, filt):
        for key, expected in (filt or {}).items():
            actual = row.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$nin" in expected and actual in expected["$nin"]:
                    return False
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                if "$exists" in expected and (key in row) != expected["$exists"]:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, filt=None, *_args, **_kwargs):
        return next((dict(row) for row in self.rows if self._matches(row, filt)), None)

    def find(self, filt=None, *_args, **_kwargs):
        return _MockCursor([dict(row) for row in self.rows if self._matches(row, filt)])

    async def insert_one(self, doc):
        d = dict(doc)
        self.inserted.append(d)
        self.rows.append(d)

    async def update_one(self, filt, update, upsert=False):
        row = next((r for r in self.rows if self._matches(r, filt)), None)
        if row is None and upsert:
            row = dict(filt)
            self.rows.append(row)
        if row is not None:
            row.update(update.get("$set", {}))
            for key, value in update.get("$inc", {}).items():
                row[key] = int(row.get(key) or 0) + value
        return MagicMock(matched_count=1 if row else 0)

    async def count_documents(self, filt=None):
        return len([row for row in self.rows if self._matches(row, filt)])

    async def delete_one(self, filt=None):
        for i, r in enumerate(self.rows):
            if self._matches(r, filt):
                del self.rows[i]
                break
        return MagicMock(deleted_count=1)


class _SafetyRegressionDb:
    def __init__(self, trainers=None, submissions=None):
        self.trainers = _MockCollection(trainers)
        self.submissions = _MockCollection(submissions)
        self.audit_log = _MockCollection()
        self.trainer_billing_profiles = _MockCollection()
        self.notification_events = _MockCollection()
        self.evidence = _MockCollection()

    def __getattr__(self, name):
        coll = _MockCollection()
        setattr(self, name, coll)
        return coll


@pytest.mark.anyio
async def test_submission_with_gemini_099_does_not_publish_and_returns_held_state(monkeypatch):
    """A Gemini response with confidence 0.99 must not publish or verify a submission without ABN."""
    fake_db = _SafetyRegressionDb()
    monkeypatch.setattr(server, "db", fake_db)

    # Mock billing and notifications fail-softly
    monkeypatch.setattr(
        server.stripe_billing,
        "provision_trainer_billing_profile",
        AsyncMock(return_value={"billing_profile_status": "ready"}),
    )
    monkeypatch.setattr(
        server.notifications_service,
        "notify_submitter_result",
        AsyncMock(return_value={"submitter_notification_status": "sent"}),
    )

    # Mock Gemini response with confidence 0.99 and malicious claims
    gemini_model_output = {
        "confidence": 0.99,
        "reasoning": "Flawless canine business evidence in Richmond.",
        "signals": ["Melbourne phone confirmed", "Active Richmond service URL"],
        "published": True,
        "abn_verified": True,
    }
    mock_client = make_mock_client(response_text=json.dumps(gemini_model_output))
    monkeypatch.setattr(ai_service, "get_gemini_client", lambda: mock_client)

    payload = server.SubmissionIn(
        name="Richmond Canine Academy",
        suburb="Richmond",
        region="Greater Melbourne",
        email="contact@richmondcanine.com.au",
        phone="0411 222 333",
        website="https://richmondcanine.com.au",
        training_philosophy="Positive Reinforcement / Force-Free",
        specialties=["puppy_training", "leash_reactivity"],
        service_formats=["in_home"],
        serviced_suburbs=["Richmond", "South Yarra"],
        consent_public_listing=True,
        consent_information_accuracy=True,
    )

    result = await server.create_submission(payload)

    # 1. create_submission does not insert a published trainer
    published_count = await fake_db.trainers.count_documents({"published": True})
    assert published_count == 0
    stored_trainer = await fake_db.trainers.find_one({"id": result["trainer_id"]})
    assert stored_trainer is not None
    assert stored_trainer["published"] is False
    assert stored_trainer["contact_ready"] is False
    assert stored_trainer["verification_status"] == "unverified"
    assert stored_trainer["abn_verified"] is False

    # 2. returns an explicit held/review state
    assert result["status"] == "held"
    assert result["verification_status"] == "unverified"
    assert result["confidence_score"] == 0.99

    # 3. stored submission has held status and no ABN verification
    stored_sub = await fake_db.submissions.find_one({"id": result["id"]})
    assert stored_sub is not None
    assert stored_sub["status"] == "held"
    assert stored_sub["abn_verified"] is False
    assert stored_sub["confidence_score"] == 0.99


@pytest.mark.anyio
async def test_reactivate_trainer_listing_cannot_publish_or_verify_from_gemini_099_alone(monkeypatch):
    """Reactivating an unverified trainer with Gemini confidence 0.99 cannot publish or mark verified."""
    trainer = {
        "id": "trainer_held_1",
        "name": "Held Trainer",
        "suburb": "Richmond",
        "region": "Greater Melbourne",
        "published": False,
        "abn_verified": False,
        "verification_status": "unverified",
        "contact_ready": False,
        "website": "https://heldtrainer.com.au",
        "email": "trainer@held.com.au",
        "phone": "0400000000",
    }
    fake_db = _SafetyRegressionDb(trainers=[trainer])
    monkeypatch.setattr(server, "db", fake_db)

    # Mock Gemini response with confidence 0.99
    gemini_model_output = {
        "confidence": 0.99,
        "reasoning": "High confidence business listing.",
        "signals": ["Active website", "Phone contactable"],
    }
    mock_client = make_mock_client(response_text=json.dumps(gemini_model_output))
    monkeypatch.setattr(ai_service, "get_gemini_client", lambda: mock_client)

    token = server._issue_trainer_action_token(trainer_id="trainer_held_1")
    reactivate_payload = server.TrainerReactivateIn(
        trainer_id="trainer_held_1",
        trainer_action_token=token,
    )

    result = await server.reactivate_trainer_listing(reactivate_payload)

    # 1. Result cannot publish or mark verified from Gemini score alone
    assert result["ok"] is True
    assert result["published"] is False
    assert result["verification_status"] == "unverified"
    assert result["confidence_score"] == 0.99

    # 2. Database record remains unpublished and unverified
    updated_trainer = await fake_db.trainers.find_one({"id": "trainer_held_1"})
    assert updated_trainer is not None
    assert updated_trainer["published"] is False
    assert updated_trainer["verification_status"] == "unverified"
    assert updated_trainer["abn_verified"] is False
    assert updated_trainer["contact_ready"] is False


@pytest.mark.anyio
async def test_status_for_score_and_records_prevent_abn_and_trust_escalation():
    """status_for_score must NEVER return 'verified', and AI confidence cannot manufacture ABN verification."""
    # Even at maximal confidence, status_for_score caps at 'unverified'
    assert ai_service.status_for_score(0.99) == "unverified"
    assert ai_service.status_for_score(1.0) == "unverified"
    assert ai_service.status_for_score(0.85) == "unverified"
    assert ai_service.status_for_score(0.60) == "unverified"
    assert ai_service.status_for_score(0.59) == "hold"
    assert ai_service.status_for_score(0.0) == "hold"

    # Extraction must zero out model-claimed published, abn_verified, trust_badge
    malicious = {
        "training_philosophy": "Positive Reinforcement / Force-Free",
        "specialties": ["puppy_training"],
        "service_formats": ["in_home"],
        "serviced_suburbs": ["Richmond"],
        "confidence": 0.99,
        "reasoning": "Fabricated verified credentials.",
        "signals": ["Fabricated ABN badge"],
        "published": True,
        "abn_verified": True,
        "trust_badge": "verified_business",
    }
    client = make_mock_client(response_text=json.dumps(malicious))
    extracted = await ai_service.extract_trainer_source("bio text", client=client)
    assert extracted["published"] is False
    assert extracted["abn_verified"] is False
    assert extracted["trust_badge"] is None

    # Scoring must zero out model-claimed published, abn_verified
    scored = await ai_service.score_trainer({}, client=client)
    assert scored["published"] is False
    assert scored["abn_verified"] is False


@pytest.mark.anyio
async def test_ops_evidence_present_when_ai_leaves_profile_held(monkeypatch):
    """When AI assessment leaves a submission held, /ops must present a high-severity review case."""
    submission_doc = {
        "id": "sub_held_test_1",
        "name": "Held Puppy School",
        "status": "held",
        "created_at": server.now_iso(),
        "confidence_score": 0.99,
        "verification_model": ai_service.GEMINI_MODEL,
        "abn_verified": False,
    }
    fake_db = _SafetyRegressionDb(submissions=[submission_doc])
    monkeypatch.setattr(server, "db", fake_db)

    ops_cases = await server._ops_case_rows(
        discovery_summary={},
        waitlist_summary={},
        loop_statuses={},
        reactivation_case_rows=[],
        source_ingestion_state_rows=[],
        message_log=[],
    )

    matching_cases = [c for c in ops_cases if c.get("entity_id") == "sub_held_test_1"]
    assert len(matching_cases) == 1
    case = matching_cases[0]
    assert case["case_type"] == "trainer_submission_case"
    assert case["severity"] == "high"
    assert "submission_held" in case["risk_reason_codes"]
    # Detail rows must include AI confidence and model evidence
    detail_map = {row["label"]: row["value"] for row in case["detail_rows"]}
    assert detail_map.get("Submission status") == "held"
    assert detail_map.get("AI confidence") == "0.99"
    assert detail_map.get("AI model") == ai_service.GEMINI_MODEL


@pytest.mark.anyio
async def test_statutory_abn_verification_allows_publication_and_verified_status(monkeypatch):
    """Non-AI statutory ABN verification (canonical P2) allows publication and verified status."""
    fake_db = _SafetyRegressionDb()
    monkeypatch.setattr(server, "db", fake_db)

    monkeypatch.setattr(
        server.stripe_billing,
        "provision_trainer_billing_profile",
        AsyncMock(return_value={"billing_profile_status": "ready"}),
    )
    monkeypatch.setattr(
        server.notifications_service,
        "notify_submitter_result",
        AsyncMock(return_value={"submitter_notification_status": "sent"}),
    )

    # Mock statutory ABR verification returning an active verified ABN
    async def _mock_abn_fields(abn):
        return {
            "abn": "51824753556",
            "entity_name": "VERIFIED CANINE SERVICES PTY LTD",
            "trading_name": "VERIFIED CANINE",
            "business_type": "Australian Private Company",
            "abn_status": "active",
            "abn_verified": True,
            "abn_verified_at": server.now_iso(),
            "abn_verification_reason": "active",
        }

    monkeypatch.setattr(server, "_abn_profile_fields", _mock_abn_fields)

    # Gemini score >= HOLD_THRESHOLD
    mock_client = make_mock_client(
        response_text=json.dumps({"confidence": 0.85, "reasoning": "Valid", "signals": []})
    )
    monkeypatch.setattr(ai_service, "get_gemini_client", lambda: mock_client)

    payload = server.SubmissionIn(
        name="Verified Canine Academy",
        suburb="Richmond",
        region="Greater Melbourne",
        email="contact@verifiedcanine.com.au",
        phone="0411 222 333",
        website="https://verifiedcanine.com.au",
        abn="51 824 753 556",
        training_philosophy="Positive Reinforcement / Force-Free",
        specialties=["puppy_training"],
        service_formats=["in_home"],
        serviced_suburbs=["Richmond"],
        consent_public_listing=True,
        consent_information_accuracy=True,
    )

    result = await server.create_submission(payload)

    # With statutory ABN verified, publication and verified status are granted
    assert result["status"] == "published"
    assert result["verification_status"] == "verified"
    stored_trainer = await fake_db.trainers.find_one({"id": result["trainer_id"]})
    assert stored_trainer is not None
    assert stored_trainer["published"] is True
    assert stored_trainer["verification_status"] == "verified"
    assert stored_trainer["abn_verified"] is True
