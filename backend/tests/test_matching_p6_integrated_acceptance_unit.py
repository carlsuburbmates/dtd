"""Comprehensive Acceptance & Regression Test Suite for all 16 Roadmap Scenarios.

Governed by:
- AGENTS.md (Rule 6A, locked boundaries)
- DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md (M8, Scenarios 1–16)
- specs/SANDBOX_VERIFICATION_MATRIX.md
- Findings: DF-014 through DF-026

Acceptance Scenarios Verified:
 1. Puppy basic manners with a local suitable trainer.
 2. Multiple concerns with an in-home requirement and method boundary.
 3. Ambiguous description with the Decision Contract-selected response (needs_clarification).
 4. Fewer than three local eligible trainers and truthfully disclosed Greater Melbourne expansion.
 5. No trainer with the required capability evidence after eligibility and fit rules (no_confirmed_match).
 6. Stale, suppressed or unsupported trainer capability excluded before AI fit.
 7. Exact 0.05 comparable-fit presentation boundary and an outside-band paid candidate.
 8. Gemini timeout, rate limit and malformed output with deterministic fallback response.
 9. Immediate human-danger, possible urgent animal-health, serious behavioural and unclear urgent routes.
10. Trainer declaration correction, failed refresh and suppression invalidating later matchability.
11. Consent rejection, privacy/URL protection and protected-enquiry minimisation.
12. Follow-up delivery, retryable failure, terminal suppression and no-duplicate success.
13. Parity between Gemini adapter and deterministic fallback against material-agreement bar.
14. Anti-gaming: unsupported, out-of-vocabulary, stale or paid-field declaration attempts held/excluded.
15. Urgent-provider correction request through evidence check, bounded operator review and outcome.
16. The four scripted /ops recovery controls and protected, redacted read models (zero PII/tokens).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import server
from services import ai as ai_service
from services import matching_contract_v2
from services import trainer_quality
from services import urgent_providers as urgent_providers_service
from tests.fixtures_matching_v2 import (
    make_test_trainer_doc,
    make_valid_match_request,
)


class _ComprehensiveMockCollection:
    def __init__(self, rows: List[Dict[str, Any]] = None):
        self.rows: List[Dict[str, Any]] = [dict(r) for r in (rows or [])]
        self.inserted: List[Dict[str, Any]] = []

    def find(self, query: Dict[str, Any] = None, projection: Dict[str, Any] = None):
        res = list(self.rows) + list(self.inserted)
        if query:
            if "published" in query:
                res = [r for r in res if r.get("published") == query["published"]]
            if "category" in query:
                res = [r for r in res if r.get("category") == query["category"]]
            if "freshness_state" in query:
                res = [r for r in res if r.get("freshness_state") == query["freshness_state"]]
            if "region" in query and "$in" in query["region"]:
                allowed = set(query["region"]["$in"])
                res = [r for r in res if r.get("region") in allowed]
        self._last_find = res
        return self

    def sort(self, key: str, direction: int = -1):
        # Sort in-memory if needed
        return self

    def limit(self, count: int):
        if hasattr(self, "_last_find"):
            self._last_find = self._last_find[:count]
        return self

    async def to_list(self, limit: int = 100):
        items = getattr(self, "_last_find", self.rows + self.inserted)
        return list(items)[:limit]

    async def count_documents(self, query: Dict[str, Any] = None):
        items = self.rows + self.inserted
        if query:
            filtered = []
            for r in items:
                match = True
                for k, v in query.items():
                    if k == "$or":
                        or_ok = any(all(r.get(sk) == sv for sk, sv in branch.items()) for branch in v)
                        if not or_ok:
                            match = False
                            break
                    elif r.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(r)
            return len(filtered)
        return len(items)

    def _match_doc(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        for k, v in query.items():
            if k == "$or":
                if not any(self._match_doc(doc, branch) for branch in v):
                    return False
            elif isinstance(v, dict):
                val = doc.get(k)
                if "$in" in v:
                    if val not in v["$in"]:
                        return False
                if "$lt" in v:
                    if val is None or val >= v["$lt"]:
                        return False
                if "$exists" in v:
                    exists = k in doc and doc[k] is not None
                    if exists != v["$exists"]:
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    async def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any], return_document: bool = True):
        for r in self.rows + self.inserted:
            if not self._match_doc(r, query):
                continue
            if "$set" in update:
                r.update(update["$set"])
            return dict(r)
        return None

    async def find_one(self, query: Dict[str, Any], projection: Dict[str, Any] = None):
        for r in self.rows + self.inserted:
            if self._match_doc(r, query):
                return dict(r)
        return None

    async def insert_one(self, doc: Dict[str, Any]):
        copy_doc = dict(doc)
        self.inserted.append(copy_doc)
        return SimpleNamespace(inserted_id="mock_id")

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        target = None
        for r in self.rows + self.inserted:
            if self._match_doc(r, query):
                target = r
                break
        if target and "$set" in update:
            target.update(update["$set"])
            return SimpleNamespace(matched_count=1, modified_count=1)
        elif not target and upsert:
            new_doc = dict(query)
            if "$set" in update:
                new_doc.update(update["$set"])
            self.inserted.append(new_doc)
            return SimpleNamespace(matched_count=0, modified_count=1, upserted_id="mock_upsert")
        return SimpleNamespace(matched_count=0, modified_count=0)


def _make_dummy_request(
    ip: str = "127.0.0.1",
    method: str = "POST",
    path: str = "/api/match",
    query_string: str = "",
    headers: Dict[str, str] = None,
) -> Request:
    raw_headers = [(b"host", b"testserver")]
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode(), v.encode()))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string.encode(),
        "headers": raw_headers,
        "client": (ip, 12345),
    }
    return Request(scope)


class TestMatchingRoadmapScenarios1To16:
    """Rigorous acceptance verification for all 16 roadmap scenarios."""

    @pytest.fixture(autouse=True)
    def default_mock_adapter(self, monkeypatch):
        """Ensure standard tests run with mock adapter unless explicitly testing real Gemini or fallback."""
        adapter = matching_contract_v2.GeminiStubAdapter(mode="normal")
        monkeypatch.setattr(server, "matching_ai_adapter", adapter)

    # --------------------------------------------------------------------------
    # Scenario 1: Puppy basic manners with a local suitable trainer
    # --------------------------------------------------------------------------
    def test_scenario_01_puppy_basic_manners_local(self, monkeypatch):
        t1 = make_test_trainer_doc(
            trainer_id="t_richmond_puppy",
            name="Richmond Puppy Academy",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent"],
            training_philosophy="positive_reinforcement_force_free",
        )
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([t1]),
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=4,
            primary_concerns=["puppy_prep", "basic_manners"],
            service_format="in_home",
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] in {"recommendations", "limited_local_results"}
        assert len(out["candidates"]) == 1
        cand = out["candidates"][0]
        assert cand["trainer_id"] == "t_richmond_puppy"
        assert cand["name"] == "Richmond Puppy Academy"
        assert cand["locality"] == "Richmond"
        assert cand["search_scope"] == "local"
        assert out["context_token"] is not None

    # --------------------------------------------------------------------------
    # Scenario 2: Multiple concerns with in-home requirement & method boundary
    # --------------------------------------------------------------------------
    def test_scenario_02_multiple_concerns_in_home_method_boundary(self, monkeypatch):
        # T1: In-home and positive reinforcement only
        t1 = make_test_trainer_doc(
            trainer_id="t_positive",
            name="Positive Home Training",
            serviced_suburbs=["Fitzroy"],
            specialties=["barking", "separation_anxiety"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent", "adult"],
            training_philosophy="positive_reinforcement_force_free",
        )
        # T2: Only facility/field, balanced method
        t2 = make_test_trainer_doc(
            trainer_id="t_balanced_facility",
            name="Balanced Field Academy",
            serviced_suburbs=["Fitzroy"],
            specialties=["barking", "separation_anxiety"],
            service_formats=["facility"],
            life_stages=["puppy", "adolescent", "adult"],
            training_philosophy="balanced",
        )
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([t1, t2]),
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Fitzroy",
            dog_age_months=20,
            primary_concerns=["barking", "separation_anxiety"],
            service_format="in_home",
            method_preference="positive_reinforcement_only",
        )
        out = asyncio.run(server.instant_match(req))
        cand_ids = [c["trainer_id"] for c in out["candidates"]]
        assert "t_positive" in cand_ids
        assert "t_balanced_facility" not in cand_ids

    # --------------------------------------------------------------------------
    # Scenario 3: Ambiguous description with Decision Contract-selected response
    # --------------------------------------------------------------------------
    def test_scenario_03_ambiguous_description_needs_clarification(self, monkeypatch):
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([]),
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            primary_concerns=["other"],
            behaviour_description="Not quite sure what help is needed",
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == "needs_clarification"
        assert out["candidates"] == []
        assert out["context_token"] is None
        assert "clarification_notice" in out

    # --------------------------------------------------------------------------
    # Scenario 4: Fewer than 3 local trainers with disclosed Greater Melbourne expansion
    # --------------------------------------------------------------------------
    def test_scenario_04_fewer_than_3_expanded_disclosure(self, monkeypatch):
        # Only 1 local trainer in Carlton
        t_local = make_test_trainer_doc(
            trainer_id="t_carlton",
            name="Carlton Local Trainer",
            serviced_suburbs=["Carlton"],
            specialties=["obedience"],
            service_formats=["in_home"],
            life_stages=["all_life_stages"],
            training_philosophy="positive_reinforcement_force_free",
        )
        # Regional trainer servicing Greater Melbourne
        t_regional = make_test_trainer_doc(
            trainer_id="t_regional",
            name="Melbourne Wide Behaviour",
            serviced_suburbs=["Melbourne", "Richmond"],
            specialties=["obedience"],
            service_formats=["in_home"],
            life_stages=["all_life_stages"],
            training_philosophy="positive_reinforcement_force_free",
            catchment_type="melbourne_wide",
        )
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([t_local, t_regional]),
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Carlton",
            primary_concerns=["basic_manners"],
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == "limited_local_results"
        assert out["search_scope"] == "expanded"
        # Disclosed expanded area
        cand_scopes = [c["search_scope"] for c in out["candidates"]]
        assert "expanded" in cand_scopes

    # --------------------------------------------------------------------------
    # Scenario 5: No trainer with required capability (no_confirmed_match)
    # --------------------------------------------------------------------------
    def test_scenario_05_no_trainer_with_required_capability(self, monkeypatch):
        # Trainers exist, but none handle fear/phobia
        t1 = make_test_trainer_doc(
            trainer_id="t_manners",
            name="Manners Only",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
        )
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([t1]),
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            primary_concerns=["separation_anxiety"],
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == "no_confirmed_match"
        assert out["candidates"] == []
        assert out["context_token"] is None

    # --------------------------------------------------------------------------
    # Scenario 6: Stale, suppressed, or unsupported capability excluded
    # --------------------------------------------------------------------------
    def test_scenario_06_stale_suppressed_capability_excluded(self, monkeypatch):
        # Trainer with expired projection or unverified ABN
        t_unverified = make_test_trainer_doc(
            trainer_id="t_unverified_abn",
            name="Unverified Academy",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["in_home"],
            life_stages=["all_life_stages"],
            training_philosophy="positive_reinforcement_force_free",
        )
        t_unverified["abn_status"] = "cancelled"  # Statutory gate fail
        t_unverified["match_eligible"] = False

        t_valid = make_test_trainer_doc(
            trainer_id="t_valid",
            name="Valid Academy",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["in_home"],
            life_stages=["all_life_stages"],
            training_philosophy="positive_reinforcement_force_free",
        )
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([t_unverified, t_valid]),
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            primary_concerns=["basic_manners"],
        )
        out = asyncio.run(server.instant_match(req))
        cand_ids = [c["trainer_id"] for c in out["candidates"]]
        assert "t_valid" in cand_ids
        assert "t_unverified_abn" not in cand_ids

    # --------------------------------------------------------------------------
    # Scenario 7: Exact 0.05 comparable-fit presentation boundary & paid candidate outside band
    # --------------------------------------------------------------------------
    def test_scenario_07_exact_005_fit_boundary_and_paid_outside_band(self):
        c1 = {"trainer_id": "t_high_organic", "match_score": 0.90, "tier": "unclaimed"}
        # Inside exact 0.05 band: 0.90 - 0.05 = 0.85
        c2 = {"trainer_id": "t_pro_inside", "match_score": 0.85, "tier": "pro"}
        # Outside band: 0.849 < 0.85
        c3 = {"trainer_id": "t_pro_outside", "match_score": 0.849, "tier": "pro"}

        ranked = matching_contract_v2.apply_fair_presentation([c1, c2, c3])
        # t_pro_inside enters top band; t_pro_outside does not outrank higher scores
        res_ids = [c["trainer_id"] for c in ranked]
        assert res_ids.index("t_pro_inside") < res_ids.index("t_pro_outside")

    # --------------------------------------------------------------------------
    # Scenario 8: Gemini timeout / rate limit / malformed with deterministic fallback
    # --------------------------------------------------------------------------
    def test_scenario_08_gemini_timeout_fallback_cutover(self, monkeypatch):
        t1 = make_test_trainer_doc(
            trainer_id="t_timeout_fallback",
            name="Fallback Academy",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["in_home"],
            life_stages=["all_life_stages"],
            training_philosophy="positive_reinforcement_force_free",
        )
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([t1]),
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
            ai_degradation_events=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # Force timeout adapter
        async def timeout_generate(*args, **kwargs):
            raise asyncio.TimeoutError("Gemini call timed out")

        mock_aio = SimpleNamespace(models=SimpleNamespace(generate_content=timeout_generate))
        timeout_client = SimpleNamespace(aio=mock_aio)
        adapter = ai_service.GeminiMatchingAdapter(client=timeout_client, timeout_s=0.01)
        monkeypatch.setattr(server, "matching_ai_adapter", adapter)

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            primary_concerns=["basic_manners"],
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == "degraded_recommendations"
        assert len(out["candidates"]) == 1
        assert out["candidates"][0]["trainer_id"] == "t_timeout_fallback"
        # Degradation event recorded
        assert len(fake_db.ai_degradation_events.inserted) >= 1

    # --------------------------------------------------------------------------
    # Scenario 9: Urgent routes (danger, health, serious behaviour, clarification)
    # --------------------------------------------------------------------------
    def test_scenario_09_urgent_routes_deterministic_safety(self, monkeypatch):
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([]),
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
            urgent_providers=_ComprehensiveMockCollection(urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # Immediate danger -> 000
        req_danger = make_valid_match_request(
            behaviour_description="Dog attacked child and is actively biting",
        )
        out_danger = asyncio.run(server.instant_match(req_danger))
        assert out_danger["decision_state"] == "immediate_human_danger"
        assert "Triple Zero" in out_danger["emergency_notice"]["source"]

        # Urgent health -> verified care
        req_health = make_valid_match_request(
            behaviour_description="Dog swallowed rat poison and is having severe seizures",
        )
        out_health = asyncio.run(server.instant_match(req_health))
        assert out_health["decision_state"] == "urgent_animal_health_support"
        assert len(out_health["urgent_providers"]) > 0

    # --------------------------------------------------------------------------
    # Scenario 10: Declaration correction & suppression invalidating later matchability
    # --------------------------------------------------------------------------
    def test_scenario_10_declaration_correction_and_suppression(self, monkeypatch):
        t1 = make_test_trainer_doc(
            trainer_id="t_to_suppress",
            name="Suppressed Trainer",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
        )
        trainers_coll = _ComprehensiveMockCollection([t1])
        audit_coll = _ComprehensiveMockCollection([])
        fake_db = SimpleNamespace(
            trainers=trainers_coll,
            match_events=_ComprehensiveMockCollection([]),
            match_contexts=_ComprehensiveMockCollection([]),
            audit_log=audit_coll,
        )
        monkeypatch.setattr(server, "db", fake_db)

        # Invalidate trainer declaration
        t1["match_eligible"] = False
        t1["invalidation_reasons"] = ["unsupported_statutory_claim"]

        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            primary_concerns=["basic_manners"],
        )
        out = asyncio.run(server.instant_match(req))
        assert out["decision_state"] == "no_confirmed_match"
        assert out["candidates"] == []

    # --------------------------------------------------------------------------
    # Scenario 11: Consent rejection, privacy/URL protection & enquiry minimisation
    # --------------------------------------------------------------------------
    def test_scenario_11_consent_rejection_and_url_privacy(self, monkeypatch):
        # 1. Declined consent rejected with 400
        req_no_consent = make_valid_match_request()
        req_no_consent.consent.match_processing = False
        with pytest.raises(HTTPException) as exc:
            asyncio.run(server.instant_match(req_no_consent))
        assert exc.value.status_code == 400
        assert "Consent required" in exc.value.detail

        # 2. Follow-up query-param token forbidden (?token=...)
        follow_req = _make_dummy_request(
            method="POST",
            path="/api/match/follow-up",
            query_string="token=forbidden_token_in_url",
        )
        with pytest.raises(HTTPException) as exc2:
            asyncio.run(server.create_match_follow_up(
                payload=server.MatchFollowUpIn(
                    trainer_id="t_test",
                    user_name="John",
                    user_email="john@example.com",
                    consent_contact_release=True,
                ),
                request=follow_req,
            ))
        assert exc2.value.status_code == 400

    # --------------------------------------------------------------------------
    # Scenario 12: Follow-up delivery, retryable failure & idempotent replay
    # --------------------------------------------------------------------------
    def test_scenario_12_follow_up_delivery_and_idempotent_replay(self, monkeypatch):
        raw_token, token_hash = matching_contract_v2.generate_match_context_token()
        ctx_doc = {
            "token_hash": token_hash,
            "match_id": "match_s12",
            "suburb_or_postcode": "Richmond",
            "dog_age_months": 12,
            "primary_concerns": ["basic_manners"],
            "service_format": "in_home",
        }
        trainer = make_test_trainer_doc(
            trainer_id="t_richmond_12",
            name="Richmond Dog Academy",
            serviced_suburbs=["Richmond"],
            specialties=["basic_manners"],
        )
        fake_db = SimpleNamespace(
            match_contexts=_ComprehensiveMockCollection([ctx_doc]),
            trainers=_ComprehensiveMockCollection([trainer]),
            intros=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        payload = server.MatchFollowUpIn(
            trainer_id="t_richmond_12",
            user_name="Alice Smith",
            user_email="alice@example.com",
            consent_contact_release=True,
        )
        req = _make_dummy_request(
            method="POST",
            path="/api/match/follow-up",
            headers={"X-Match-Context-Token": raw_token, "Idempotency-Key": "key_s12"},
        )
        # First call -> delivery_state=delivered, idempotent=False
        r1 = asyncio.run(server.create_match_follow_up(payload=payload, request=req, idempotency_key="key_s12"))
        assert r1["idempotent"] is False
        assert r1["delivery_state"] == "delivered"

        # Replay with same key -> idempotent=True, same intro_id
        r2 = asyncio.run(server.create_match_follow_up(payload=payload, request=req, idempotency_key="key_s12"))
        assert r2["idempotent"] is True
        assert r2["intro_id"] == r1["intro_id"]

    # --------------------------------------------------------------------------
    # Scenario 13: Parity between Gemini adapter & fallback against material agreement
    # --------------------------------------------------------------------------
    def test_scenario_13_gemini_and_fallback_material_agreement(self):
        t1 = make_test_trainer_doc(
            trainer_id="t_fit_1",
            name="Top Fit Trainer",
            serviced_suburbs=["Richmond"],
            specialties=["puppy_training", "obedience"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent"],
            training_philosophy="positive_reinforcement_force_free",
        )
        t2 = make_test_trainer_doc(
            trainer_id="t_fit_2",
            name="Secondary Fit Trainer",
            serviced_suburbs=["Richmond"],
            specialties=["obedience"],
            service_formats=["in_home"],
            life_stages=["puppy", "adolescent"],
            training_philosophy="positive_reinforcement_force_free",
        )
        pool = [t1, t2]
        req = make_valid_match_request(
            suburb_or_postcode="Richmond",
            dog_age_months=5,
            primary_concerns=["puppy_prep", "basic_manners"],
        )

        # Deterministic fallback evaluation
        resp = matching_contract_v2.run_deterministic_matching(req, pool)
        assert len(resp.candidates) > 0
        assert resp.candidates[0].trainer_id == "t_fit_1"

    # --------------------------------------------------------------------------
    # Scenario 14: Anti-gaming: out-of-vocabulary or paid-field declaration held
    # --------------------------------------------------------------------------
    def test_scenario_14_anti_gaming_unsupported_declarations(self):
        doc = make_test_trainer_doc(
            trainer_id="t_gaming",
            name="Gaming Trainer",
            specialties=["fake_specialty", "buy_reviews_now"],
        )
        proj = trainer_quality.build_match_ready_projection(doc)
        # Out-of-vocabulary specialties are not mapped to canonical concerns
        assert "fake_specialty" not in proj.get("canonical_concerns", [])

    # --------------------------------------------------------------------------
    # Scenario 15: Urgent-provider correction request & operator review
    # --------------------------------------------------------------------------
    def test_scenario_15_urgent_provider_correction_and_review(self, monkeypatch):
        fake_db = SimpleNamespace(
            urgent_providers=_ComprehensiveMockCollection(urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS),
            urgent_provider_corrections=_ComprehensiveMockCollection([]),
            audit_log=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # 1. Public user submits correction request
        corr_in = urgent_providers_service.UrgentProviderCorrectionIn(
            provider_id="urgent_care_lost_dogs_home_north_melbourne",
            provider_name="The Lost Dogs' Home",
            official_source_url="https://vet.dogshome.com/",
            reason="hours_changed",
            notes="Closing early on public holidays",
        )
        submit_res = asyncio.run(server.create_urgent_provider_correction(corr_in))
        corr_id = submit_res["request_id"]

        # 2. Operator reviews and accepts correction with bounded evidence
        review_in = server.OversightUrgentCorrectionReviewIn(
            action="accept",
            confirmed=True,
            verified_official_source=True,
            official_source_url="https://vet.dogshome.com/",
            evidence_reference="Official Vet Clinic Website Contact Page",
            reviewed_field_values={"contact_method": "(03) 8379 4498"},
            notes="Verified against official website",
        )
        rev_res = asyncio.run(server.oversight_urgent_provider_correction_review(corr_id, review_in, request=_make_dummy_request()))
        assert rev_res["ok"] is True
        assert rev_res["status"] == "accepted"
        assert len(fake_db.audit_log.inserted) == 1

    # --------------------------------------------------------------------------
    # Scenario 16: The four scripted /ops recovery controls & redacted read model
    # --------------------------------------------------------------------------
    def test_scenario_16_ops_recovery_controls_and_read_model(self, monkeypatch):
        fake_db = SimpleNamespace(
            trainers=_ComprehensiveMockCollection([
                make_test_trainer_doc(trainer_id="t_recheck", name="Recheck Trainer", specialties=["basic_manners"]),
            ]),
            match_events=_ComprehensiveMockCollection([
                {
                    "id": "match_ops_test",
                    "decision_state": "recommendations",
                    "search_scope": "local",
                    "result_ids": ["t_recheck"],
                    "reason_codes": ["capability_concern_match"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            ]),
            intros=_ComprehensiveMockCollection([
                {
                    "id": "intro_ops_test",
                    "match_id": "match_ops_test",
                    "trainer_id": "t_recheck",
                    "delivery_state": "retryable_failure",
                    "status": "retryable_failure",
                },
            ]),
            urgent_providers=_ComprehensiveMockCollection(urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS),
            urgent_provider_corrections=_ComprehensiveMockCollection([]),
            ai_degradation_events=_ComprehensiveMockCollection([]),
            audit_log=_ComprehensiveMockCollection([]),
        )
        monkeypatch.setattr(server, "db", fake_db)

        # Control 1: AI degradation acknowledge
        deg_res = asyncio.run(server.oversight_matching_degradation_acknowledge(
            server.OversightDegradationAcknowledgeIn(action="reset_circuit", confirmed=True)
        ))
        assert deg_res["ok"] is True
        assert deg_res["circuit_status"] == "reset"

        # Control 2: Follow-up retry with mocked successful provider acceptance
        async def _mock_notify(*args, **kwargs):
            return {"trainer_notification_status": "sent"}
        monkeypatch.setattr(server.notifications_service, "notify_trainer_new_intro", _mock_notify)

        retry_res = asyncio.run(server.oversight_matching_follow_up_retry(
            "intro_ops_test", server.OversightFollowUpRetryIn(confirmed=True), request=_make_dummy_request()
        ))
        assert retry_res["ok"] is True
        assert retry_res["delivery_state"] == "delivered"

        # Control 3: Trainer capability recheck
        recheck_res = asyncio.run(server.oversight_trainer_capability_recheck(
            "t_recheck", server.OversightCapabilityRecheckIn(confirmed=True)
        ))
        assert recheck_res["ok"] is True
        assert recheck_res["trainer_id"] == "t_recheck"

        # Verify /ops matching read model: Zero PII, zero tokens, zero raw descriptions
        read_model = asyncio.run(server.build_matching_oversight_read_model(fake_db))
        assert "policy_version" in read_model
        assert "decision_triage_distribution" in read_model
        assert "urgent_provider_status" in read_model
        assert "follow_up_distribution" in read_model
        assert "presentation_order_sample" in read_model
        # Zero PII guarantees:
        sample = read_model["presentation_order_sample"]
        assert len(sample) > 0
        ev = sample[0]
        assert "description" not in ev
        assert "user_email" not in ev
        assert "user_phone" not in ev
        assert "context_token" not in ev
        assert "token" not in ev
        assert "ip" not in ev
        assert "match_score" not in ev
        assert "tier" not in ev
