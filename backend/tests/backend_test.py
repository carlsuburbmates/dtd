"""Bark&Bond — intro-first match engine regression tests.

Covers (per redesign iteration 2):
  * /api/config + root health
  * Instant /match (single input → up to 3 results) and per-trainer detail
  * /intros (records intro, returns contact, intro billing may be suppressed by fraud rules)
  * /conversions (idempotent, tracked outcome by default)
  * /submissions auto-publish (≥0.60; ≥0.85 = verified) and auto-hold (<0.6)
  * /seo/{slug:path} including nested slugs
  * /oversight login + read-only oversight surface (X-Admin-Pass)
  * Mongo `_id` scrub everywhere
  * Legacy admin mutation endpoints removed (404)
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
        pytest.skip("Public matching is disabled in education-first prelaunch mode.")


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
        assert d["base_intro_fee_cents"] == 500
        assert d.get("fixed_intro_fee_cents", d["base_intro_fee_cents"]) == d["base_intro_fee_cents"]
        assert d.get("trainer_free_intro_days", 30) == 30
        assert d["base_conversion_fee_cents"] == 6500
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
            assert "match_score" in m
            assert "match_reasoning" in m
            assert "intro_fee_cents" in m
            assert isinstance(m["intro_fee_cents"], int) and m["intro_fee_cents"] >= 300
            assert "outcome_score" in m
            assert "demand_multiplier" in m
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
        assert "intro_fee_cents" in d
        assert "demand_multiplier" in d
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
        assert intro["intro_fee_cents"] >= 0
        assert intro["billing_status"] in ("billed", "suppressed")
        contact = intro.get("contact", {})
        assert contact.get("name")  # contact info revealed
        assert_no_id(intro)
        intro_id = intro["id"]

        # Conversion 1 — track-only by default, bill-mode optional
        r1 = session.post(f"{API}/conversions", json={"intro_id": intro_id, "confirmed": True})
        assert r1.status_code == 200, r1.text
        c = r1.json()
        assert c.get("billing_status") in ("tracked", "billed", "suspicious")
        if c.get("billing_status") == "tracked":
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
                "description": "x",
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
    def test_strong_evidence_auto_publishes(self, session):
        # Use a real Melbourne dog-training business so AI verification clears 0.6.
        # Source: publicly listed business with operating website.
        payload = {
            "name": "Positive K9 Training Melbourne",
            "suburb": "Eastern Suburbs",
            "region": "Greater Melbourne",
            "website": "https://positivek9training.com.au",
            "phone": "0411 234 567",
            "email": "info@positivek9training.com.au",
            "categories": ["obedience", "puppy", "behaviour"],
            "services": ["In-home training", "Group classes", "One-on-one"],
            "bio": "Certified force-free trainers offering in-home and group sessions across Melbourne's Eastern Suburbs, the Dandenongs and Mornington Peninsula. Top-rated on Google and Facebook with 8+ years experience.",
            "source_evidence_url": "https://positivek9training.com.au",
            "consent_public_listing": True,
            "consent_information_accuracy": True,
        }
        r = session.post(f"{API}/submissions", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        sub = r.json()
        assert sub["status"] in ("published", "held"), sub
        # Strong evidence should publish (≥0.6) — not held
        assert sub["status"] == "published", f"expected published, got {sub}"
        assert sub.get("trainer_id"), "trainer_id required when published"
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
        assert sub.get("trainer_id") in (None, "")
        assert_no_id(sub)


# --- SEO autogen with nested slug ----------------------------------------

class TestSEO:
    def test_nested_slug(self, session):
        slug = "fitzroy/puppy-school"
        r = session.get(f"{API}/seo/{slug}", timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d["slug"] == slug
        assert "copy" in d
        assert_no_id(d)
        # cache hit on 2nd call
        r2 = session.get(f"{API}/seo/{slug}", timeout=30)
        assert r2.status_code == 200
        assert r2.json()["id"] == d["id"]


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
            "revenue",
            "throughput",
            "loops",
            "alerts",
            "pricing_state",
            "top_trainers",
            "audit_recent",
            "submissions_summary",
            "integrity",
        ):
            assert k in d, f"missing {k}"
        # loops
        for loop_key in ("ranking", "pricing", "verification", "health"):
            assert loop_key in d["loops"]
        # ranking ran at startup
        assert d["loops"]["ranking"].get("trainers_scored", 0) >= 1
        # at least one suburb priced after startup pass
        assert isinstance(d["pricing_state"], list)
        assert len(d["pricing_state"]) >= 1
        ps = d["pricing_state"][0]
        assert "intro_fee_cents" in ps and "multiplier" in ps
        # top trainers populated with outcome_score
        assert len(d["top_trainers"]) >= 1
        assert "outcome_score" in d["top_trainers"][0]
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
        ("/trainers", "GET"),  # list endpoint intentionally removed
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
