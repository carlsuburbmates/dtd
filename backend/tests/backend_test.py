"""Backend regression tests for the Dog Trainers Directory autonomous OS.

Covers:
- Public endpoints (trainers, featured, suburbs, categories, stats, leads,
  submissions, AI match, SEO autogen)
- Admin auth gate (passcode + X-Admin-Pass header)
- Admin CRUD: trainers patch/delete/verify, submissions approve/reject,
  leads patch, analytics, A/B tests, health, audit log, SEO, seed
- _id scrubbing assertion across all responses
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_PASS = "melbourne-bark-2026"
HDR = {"X-Admin-Pass": ADMIN_PASS}


def assert_no_id(obj):
    if isinstance(obj, dict):
        assert "_id" not in obj, f"_id leaked: {list(obj.keys())[:6]}"
        for v in obj.values():
            assert_no_id(v)
    elif isinstance(obj, list):
        for v in obj:
            assert_no_id(v)


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Public ----------------------------------------------------------------

class TestPublic:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_list_trainers(self, session):
        r = session.get(f"{API}/trainers")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        first = data[0]
        for key in ("id", "name", "suburb", "verification_status", "placement", "tier"):
            assert key in first, f"missing {key}"
        assert first["placement"] in ("paid", "organic")
        assert_no_id(data)

    def test_trainer_detail(self, session):
        listing = session.get(f"{API}/trainers").json()
        tid = listing[0]["id"]
        r = session.get(f"{API}/trainers/{tid}")
        assert r.status_code == 200
        assert r.json()["id"] == tid
        assert_no_id(r.json())

    def test_trainer_detail_404(self, session):
        r = session.get(f"{API}/trainers/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_featured(self, session):
        r = session.get(f"{API}/featured")
        assert r.status_code == 200
        for t in r.json():
            assert t["tier"] in ("featured", "premium")
        assert_no_id(r.json())

    def test_suburbs(self, session):
        r = session.get(f"{API}/suburbs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert all(isinstance(x, str) for x in r.json())

    def test_categories(self, session):
        r = session.get(f"{API}/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_stats(self, session):
        r = session.get(f"{API}/stats/public")
        assert r.status_code == 200
        d = r.json()
        for k in ("trainers", "verified", "suburbs"):
            assert k in d
            assert isinstance(d[k], int)

    def test_filter_only_verified(self, session):
        r = session.get(f"{API}/trainers", params={"only_verified": "true"})
        assert r.status_code == 200
        for t in r.json():
            assert t["verification_status"] == "verified"


# --- Leads -----------------------------------------------------------------

class TestLeads:
    def test_create_lead_and_persist(self, session):
        trainers = session.get(f"{API}/trainers").json()
        tid = trainers[0]["id"]
        payload = {
            "trainer_id": tid,
            "user_name": "TEST_Lead User",
            "user_email": "TEST_lead@example.com",
            "user_phone": "0411222333",
            "dog_description": "TEST_ Two-year-old kelpie cross with mild reactivity on lead in busy suburbs.",
            "goals": "Loose-lead walking and calm greetings",
        }
        r = session.post(f"{API}/leads", json=payload)
        assert r.status_code == 200, r.text
        lead = r.json()
        assert lead["trainer_id"] == tid
        assert lead["user_email"] == payload["user_email"]
        assert lead["status"] == "new"
        assert 0.0 <= lead["quality_score"] <= 1.0
        assert lead["quality_score"] >= 0.8  # phone + long desc + goals
        assert "id" in lead
        assert_no_id(lead)
        # ensure persisted via admin endpoint
        adm = session.get(f"{API}/admin/leads", headers=HDR).json()
        assert any(x["id"] == lead["id"] for x in adm)
        pytest.lead_id = lead["id"]

    def test_create_lead_invalid_trainer(self, session):
        r = session.post(f"{API}/leads", json={
            "trainer_id": str(uuid.uuid4()),
            "user_name": "x",
            "user_email": "x@example.com",
            "dog_description": "d",
        })
        assert r.status_code == 404

    def test_create_lead_invalid_email(self, session):
        trainers = session.get(f"{API}/trainers").json()
        r = session.post(f"{API}/leads", json={
            "trainer_id": trainers[0]["id"],
            "user_name": "x",
            "user_email": "not-an-email",
            "dog_description": "d",
        })
        assert r.status_code == 422


# --- Submissions ----------------------------------------------------------

class TestSubmissions:
    def test_create_submission(self, session):
        payload = {
            "name": f"TEST_Submission {uuid.uuid4().hex[:6]}",
            "suburb": "Fitzroy",
            "website": "https://example.com",
            "phone": "0411223344",
            "email": "TEST_sub@example.com",
            "categories": ["puppy"],
            "services": ["group classes"],
            "bio": "TEST_ Force-free puppy school in Fitzroy with weekly cohorts.",
            "source_evidence_url": "https://example.com/about",
        }
        r = session.post(f"{API}/submissions", json=payload)
        assert r.status_code == 200, r.text
        sub = r.json()
        assert sub["status"] == "pending"
        assert "confidence_score" in sub
        assert isinstance(sub["confidence_score"], (int, float))
        assert "verification_signals" in sub
        assert_no_id(sub)
        pytest.submission_id = sub["id"]


# --- AI Match -------------------------------------------------------------

class TestMatch:
    def test_match_returns_results(self, session):
        r = session.post(f"{API}/match", json={
            "description": "I have a 6 month old reactive border collie pup in Fitzroy that pulls on the lead.",
        }, timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "matches" in body
        assert isinstance(body["matches"], list)
        assert 1 <= len(body["matches"]) <= 5
        for m in body["matches"]:
            assert "id" in m and "match_score" in m and "match_reasoning" in m
        assert_no_id(body)


# --- SEO ------------------------------------------------------------------

class TestSEO:
    def test_seo_autogen(self, session):
        slug = f"fitzroy/puppy-school"
        r = session.get(f"{API}/seo/{slug}", timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d["slug"] == slug
        assert "copy" in d
        assert_no_id(d)
        # second call must hit cache (same id)
        r2 = session.get(f"{API}/seo/{slug}", timeout=30)
        assert r2.json()["id"] == d["id"]


# --- Admin auth -----------------------------------------------------------

class TestAdminAuth:
    def test_login_invalid(self, session):
        r = session.post(f"{API}/admin/login", json={"passcode": "wrong"})
        assert r.status_code == 401

    def test_login_valid(self, session):
        r = session.post(f"{API}/admin/login", json={"passcode": ADMIN_PASS})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_protected_requires_header(self, session):
        for path in ["/admin/trainers", "/admin/leads", "/admin/submissions",
                     "/admin/analytics", "/admin/health", "/admin/audit-log",
                     "/admin/ab-tests", "/admin/seo"]:
            r = session.get(f"{API}{path}")
            assert r.status_code == 401, path

    def test_protected_with_header(self, session):
        for path in ["/admin/trainers", "/admin/leads", "/admin/submissions",
                     "/admin/analytics", "/admin/health", "/admin/audit-log",
                     "/admin/ab-tests", "/admin/seo"]:
            r = session.get(f"{API}{path}", headers=HDR)
            assert r.status_code == 200, f"{path}: {r.text[:200]}"


# --- Admin operations -----------------------------------------------------

class TestAdminOps:
    def test_patch_trainer_tier_and_publish(self, session):
        trainers = session.get(f"{API}/admin/trainers", headers=HDR).json()
        tid = trainers[0]["id"]
        r = session.patch(f"{API}/admin/trainers/{tid}", headers=HDR,
                          json={"tier": "featured", "published": True})
        assert r.status_code == 200
        assert r.json()["tier"] == "featured"
        assert r.json()["published"] is True

    def test_verify_trainer(self, session):
        trainers = session.get(f"{API}/admin/trainers", headers=HDR).json()
        tid = trainers[0]["id"]
        r = session.post(f"{API}/admin/verify/{tid}", headers=HDR, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["verification_status"] in ("verified", "unverified", "hold")
        assert "confidence_score" in d

    def test_lead_patch(self, session):
        lead_id = getattr(pytest, "lead_id", None)
        if not lead_id:
            pytest.skip("no lead created")
        r = session.patch(f"{API}/admin/leads/{lead_id}", headers=HDR,
                          json={"status": "contacted"})
        assert r.status_code == 200
        assert r.json()["status"] == "contacted"

    def test_submission_approve(self, session):
        sid = getattr(pytest, "submission_id", None)
        if not sid:
            pytest.skip("no submission created")
        r = session.post(f"{API}/admin/submissions/{sid}/approve", headers=HDR)
        assert r.status_code == 200
        new_trainer = r.json()
        assert new_trainer["published"] is True
        # cleanup
        session.delete(f"{API}/admin/trainers/{new_trainer['id']}", headers=HDR)

    def test_submission_reject(self, session):
        # create another submission
        payload = {
            "name": f"TEST_Reject {uuid.uuid4().hex[:6]}",
            "suburb": "Carlton",
            "categories": ["obedience"],
            "bio": "TEST_ to be rejected",
        }
        sub = session.post(f"{API}/submissions", json=payload).json()
        r = session.post(f"{API}/admin/submissions/{sub['id']}/reject", headers=HDR)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_analytics(self, session):
        r = session.get(f"{API}/admin/analytics", headers=HDR)
        assert r.status_code == 200
        d = r.json()
        for key in ("total_trainers", "by_tier", "mrr", "arr",
                    "lead_funnel", "verification_mix", "leads_timeseries"):
            assert key in d
        assert d["arr"] == d["mrr"] * 12

    def test_health(self, session):
        r = session.get(f"{API}/admin/health", headers=HDR)
        assert r.status_code == 200
        d = r.json()
        assert "alerts" in d and isinstance(d["alerts"], list)
        assert "audit_recent" in d

    def test_audit_log(self, session):
        r = session.get(f"{API}/admin/audit-log", headers=HDR)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ab_test_create(self, session):
        r = session.post(f"{API}/admin/ab-tests", headers=HDR, json={
            "name": "TEST_AB experiment",
            "metric": "lead_conversions",
            "variants": ["control", "variant"],
            "allocation": [0.5, 0.5],
            "status": "running",
        })
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_AB experiment"

    def test_seo_generate(self, session):
        r = session.post(f"{API}/admin/seo/generate", headers=HDR,
                         json={"suburb": "Carlton", "category": "obedience"}, timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d["slug"] == "carlton/obedience"
        assert "copy" in d

    def test_seed_idempotent(self, session):
        r = session.post(f"{API}/admin/seed", headers=HDR, timeout=120)
        assert r.status_code == 200
        d = r.json()
        # should be 0 inserts after auto-seed at startup (idempotent by name)
        assert d["inserted"] == 0
        assert d["total"] >= 1

    def test_delete_trainer(self, session):
        # Use approved test submission flow - create then delete
        payload = {
            "name": f"TEST_Delete {uuid.uuid4().hex[:6]}",
            "suburb": "Carlton",
            "categories": ["obedience"],
            "bio": "TEST_",
        }
        sub = session.post(f"{API}/submissions", json=payload).json()
        approved = session.post(f"{API}/admin/submissions/{sub['id']}/approve", headers=HDR).json()
        tid = approved["id"]
        r = session.delete(f"{API}/admin/trainers/{tid}", headers=HDR)
        assert r.status_code == 200
        # verify gone
        r2 = session.get(f"{API}/trainers/{tid}")
        assert r2.status_code == 404
