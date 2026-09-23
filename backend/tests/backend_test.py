"""Dog Trainers Directory public API regression tests.

The service-backed suite is run through
``backend/scripts/run_isolated_integration_suite.py``.  That runner owns a
disposable local database containing one explicitly verified, published test
trainer.  Production's canonical intake seed is intentionally *not* reused:
it creates unclaimed, unpublished profiles until their evidence is reviewed.
"""
from __future__ import annotations

import os
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def _base_url() -> str:
    raw = (
        os.environ.get("REACT_APP_BACKEND_URL")
        or os.environ.get("REMOTE_BACKEND_URL")
        or "http://localhost:8001"
    )
    base = raw.strip().rstrip("/")
    if base.endswith("/api"):
        base = base[:-4]
    return base


BASE_URL = _base_url()
API = f"{BASE_URL}/api"
ADMIN_PASS = os.environ.get("ADMIN_PASS", "melbourne-bark-2026")
HDR = {"X-Admin-Pass": ADMIN_PASS}


def _public_matching_enabled(session) -> bool:
    r = session.get(f"{API}/config", timeout=60)
    if r.status_code != 200:
        return False
    return bool(r.json().get("public_matching_enabled"))


def _require_public_matching_or_skip(session) -> None:
    if not _public_matching_enabled(session):
        pytest.skip("Public matching is disabled in supply-first prelaunch mode.")


def assert_no_id(obj):
    if isinstance(obj, dict):
        assert "_id" not in obj, f"_id leaked: {list(obj.keys())[:8]}"
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


# --- Config / health -------------------------------------------------------

class TestConfig:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_config(self, session):
        r = session.get(f"{API}/config")
        assert r.status_code == 200
        d = r.json()
        # Owner matching and introductions are free.  Legacy per-introduction
        # configuration must not return as a public contract.
        assert "base_intro_fee_cents" not in d
        assert "fixed_intro_fee_cents" not in d
        assert "base_conversion_fee_cents" not in d
        assert d.get("pro_trial_days", 30) == 30
        assert d["public_matching_enabled"] is True
        assert isinstance(d["suburbs"], list)
        assert all(isinstance(x, str) for x in d["suburbs"])
        assert_no_id(d)


# --- Match (the product) --------------------------------------------------

class TestMatch:
    def test_match_returns_up_to_three(self, session):
        _require_public_matching_or_skip(session)
        r = session.post(
            f"{API}/match",
            json={"description": "Reactive 6-month border collie pup that pulls hard on lead in Fitzroy.", "consent_match_processing": True},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "match_id" in body
        assert "matches" in body
        ms = body["matches"]
        assert isinstance(ms, list)
        assert 1 <= len(ms) <= 3
        for m in ms:
            assert "id" in m
            assert "match_reasoning" in m
            assert isinstance(m["match_reasoning"], str) and m["match_reasoning"]
            assert m["published"] is True
            assert "intro_fee_cents" not in m
            assert "demand_multiplier" not in m
        assert_no_id(body)
        pytest.last_match_id = body["match_id"]
        pytest.last_trainer_id = ms[0]["id"]

    def test_match_short_description_validation(self, session):
        r = session.post(f"{API}/match", json={"description": "x"})
        assert r.status_code == 422


# --- Trainer detail -------------------------------------------------------

class TestTrainerDetail:
    def test_get_published(self, session):
        # use trainer from prior match; otherwise pick from oversight top trainers
        tid = getattr(pytest, "last_trainer_id", None)
        if not tid:
            ov = session.get(f"{API}/oversight", headers=HDR).json()
            tid = ov["top_trainers"][0]["id"]
        r = session.get(f"{API}/trainers/{tid}")
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == tid
        assert d["published"] is True
        assert d["verification_status"] == "verified"
        assert "intro_fee_cents" not in d
        assert "demand_multiplier" not in d
        assert_no_id(d)

    def test_404_for_unknown(self, session):
        r = session.get(f"{API}/trainers/{uuid.uuid4()}")
        assert r.status_code == 404


# --- Intros + conversions -------------------------------------------------

class TestIntrosConversions:
    def test_intro_then_conversion_idempotent(self, session):
        _require_public_matching_or_skip(session)
        tid = getattr(pytest, "last_trainer_id", None)
        match_id = getattr(pytest, "last_match_id", None)
        assert tid, "match must have produced a trainer id"
        intro_payload = {
            "trainer_id": tid,
            "description": "TEST_ Need force-free help with reactive collie pup",
            "user_email": "TEST_user@example.com",
            "user_name": "TEST_User",
            "user_phone": "0411222333",
            "match_id": match_id,
            "consent_contact_release": True,
            "consent_outcome_tracking": True,
        }
        r = session.post(f"{API}/intros", json=intro_payload)
        assert r.status_code == 200, r.text
        intro = r.json()
        assert intro["trainer_id"] == tid
        assert intro["delivery_status"] in ("delivered", "suppressed")
        assert intro["fraud_status"] in ("clear", "suppressed")
        assert "intro_fee_cents" not in intro
        contact = intro.get("contact", {})
        assert contact.get("name")  # contact info revealed
        assert_no_id(intro)
        intro_id = intro["id"]

        # Conversion 1 — track-only by default, bill-mode optional
        r1 = session.post(f"{API}/conversions", json={"intro_id": intro_id, "confirmed": True})
        assert r1.status_code == 200, r1.text
        c = r1.json()
        assert c.get("billing_status") in ("tracked", "suspicious")
        assert c.get("billed") is False
        assert c.get("fee_cents") == 0
        assert_no_id(c)

        # Conversion 2 — same intro_id, must NOT double-bill
        r2 = session.post(f"{API}/conversions", json={"intro_id": intro_id, "confirmed": True})
        assert r2.status_code == 200
        c2 = r2.json()
        assert c2.get("existing") is True
        assert c2.get("billed") is False

    def test_intro_for_unknown_trainer_404(self, session):
        _require_public_matching_or_skip(session)
        r = session.post(
            f"{API}/intros",
            json={
                "trainer_id": str(uuid.uuid4()),
                "description": "Valid test request for an unknown trainer",
                "user_email": "unknown-trainer@example.com",
                "user_name": "Unknown Trainer Test",
                "consent_contact_release": True,
                "consent_outcome_tracking": True,
            },
        )
        assert r.status_code == 404

    def test_conversion_for_unknown_intro_404(self, session):
        r = session.post(f"{API}/conversions", json={"intro_id": str(uuid.uuid4())})
        assert r.status_code == 404


# --- Submissions: auto-publish vs auto-hold -------------------------------

class TestSubmissions:
    def test_evidence_without_statutory_verification_is_held(self, session):
        # AI confidence and a website are not statutory verification.  This
        # intentionally uses test-only data: real businesses must enter via an
        # authorised acquisition source or a first-party submission/claim.
        payload = {
            "name": f"TEST_UnverifiedEvidence {uuid.uuid4().hex[:6]}",
            "suburb": "Eastern Suburbs",
            "region": "Greater Melbourne",
            "website": "https://example.test/unverified-evidence",
            "phone": "0411 234 567",
            "email": "info@positivek9training.com.au",
            "categories": ["obedience", "puppy", "behaviour"],
            "services": ["In-home training", "Group classes", "One-on-one"],
            "bio": "Test-only force-free trainer profile supplied to confirm that unsupported evidence remains held for review.",
            "source_evidence_url": "https://example.test/unverified-evidence",
            "consent_public_listing": True,
            "consent_information_accuracy": True,
        }
        r = session.post(f"{API}/submissions", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        sub = r.json()
        assert sub["status"] == "held", sub
        assert sub.get("trainer_id"), "held submissions persist a reviewable trainer record"
        assert isinstance(sub["confidence_score"], (int, float))
        assert_no_id(sub)

    def test_weak_evidence_auto_holds(self, session):
        payload = {
            "name": f"TEST_WeakSub {uuid.uuid4().hex[:6]}",
            "suburb": "Carlton",
            "consent_public_listing": True,
            "consent_information_accuracy": True,
        }
        r = session.post(f"{API}/submissions", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        sub = r.json()
        # heuristic for name+suburb only is ~0.35 → held
        assert sub["status"] == "held", f"expected held, got {sub}"
        assert sub.get("trainer_id"), "held submissions persist a reviewable trainer record"
        assert_no_id(sub)


# --- SEO generation is canonical, eligible and bounded -------------------

class TestSEO:
    def test_eligible_canonical_slug_is_cached(self, session):
        slug = "fitzroy"
        r = session.get(f"{API}/seo/{slug}", timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d["slug"] == slug
        assert "copy" in d
        assert d["publication_status"] == "published"
        assert d["meta_robots"] == "index,follow"
        assert_no_id(d)
        # cache hit on 2nd call
        r2 = session.get(f"{API}/seo/{slug}", timeout=30)
        assert r2.status_code == 200
        assert r2.json()["id"] == d["id"]

    def test_unknown_slug_is_not_a_generation_path(self, session):
        r = session.get(f"{API}/seo/not-a-canonical-melbourne-suburb", timeout=30)
        assert r.status_code == 404


# --- Oversight (read-only) ------------------------------------------------

class TestOversight:
    def test_login_invalid(self, session):
        r = session.post(f"{API}/oversight/login", json={"passcode": "wrong"})
        assert r.status_code == 401

    def test_login_valid(self, session):
        r = session.post(f"{API}/oversight/login", json={"passcode": ADMIN_PASS})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_oversight_requires_header(self, session):
        r = session.get(f"{API}/oversight")
        assert r.status_code == 401

    def test_oversight_with_header(self, session):
        r = session.get(f"{API}/oversight", headers=HDR)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in (
            "throughput",
            "loops",
            "alerts",
            "top_trainers",
            "audit_recent",
            "submissions_summary",
            "integrity",
        ):
            assert k in d, f"missing {k}"
        # loops
        for loop_key in ("ranking", "verification", "discovery", "inference", "health", "pro_trial_warnings"):
            assert loop_key in d["loops"]
        assert "revenue" not in d
        assert "pricing_state" not in d
        # The isolated fixture proves a published profile is visible in the
        # operational surface without making canonical startup seeding public.
        assert len(d["top_trainers"]) >= 1
        assert d["top_trainers"][0]["id"]
        assert_no_id(d)


# --- Removed legacy admin mutation endpoints ------------------------------

class TestLegacyRemoved:
    @pytest.mark.parametrize("path,method", [
        ("/admin/login", "POST"),
        ("/admin/trainers", "GET"),
        ("/admin/leads", "GET"),
        ("/admin/submissions", "GET"),
        ("/admin/analytics", "GET"),
        ("/admin/health", "GET"),
        ("/admin/audit-log", "GET"),
        ("/admin/seed", "POST"),
        ("/admin/ab-tests", "GET"),
        ("/admin/seo", "GET"),
        ("/featured", "GET"),
        ("/leads", "POST"),
        ("/suburbs", "GET"),
        ("/categories", "GET"),
        ("/stats/public", "GET"),
    ])
    def test_endpoint_gone(self, session, path, method):
        url = f"{API}{path}"
        r = session.request(method, url, json={} if method == "POST" else None,
                            headers=HDR if "/admin" in path else None)
        # Acceptable: 404 (route absent) or 405 (path collision but no method)
        assert r.status_code in (404, 405), f"{method} {path} → {r.status_code}: should be removed"


class TestDirectoryBrowse:
    def test_published_trainers_are_browsable(self, session):
        r = session.get(f"{API}/trainers")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] >= 1
        assert body["trainers"]
        assert all(row["published"] is True for row in body["trainers"])
        assert_no_id(body)
