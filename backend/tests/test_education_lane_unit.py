from __future__ import annotations

import asyncio
import importlib.metadata as importlib_metadata
import os
import sys
import types
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pydantic.networks as pydantic_networks

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017/test")
os.environ.setdefault("DB_NAME", "dtd_test")


if "motor.motor_asyncio" not in sys.modules:
    motor_mod = types.ModuleType("motor")
    motor_asyncio_mod = types.ModuleType("motor.motor_asyncio")

    class _FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def __getitem__(self, _name):
            return SimpleNamespace()

    motor_asyncio_mod.AsyncIOMotorClient = _FakeClient
    sys.modules["motor"] = motor_mod
    sys.modules["motor.motor_asyncio"] = motor_asyncio_mod

if "pymongo" not in sys.modules:
    pymongo_mod = types.ModuleType("pymongo")
    pymongo_errors_mod = types.ModuleType("pymongo.errors")

    class _ReturnDocument:
        AFTER = "after"
        BEFORE = "before"

    class _DuplicateKeyError(Exception):
        pass

    pymongo_mod.ReturnDocument = _ReturnDocument
    pymongo_errors_mod.DuplicateKeyError = _DuplicateKeyError
    sys.modules["pymongo"] = pymongo_mod
    sys.modules["pymongo.errors"] = pymongo_errors_mod

if "email_validator" not in sys.modules:
    email_validator_mod = types.ModuleType("email_validator")

    class _EmailNotValidError(ValueError):
        pass

    class _ValidatedEmail:
        def __init__(self, email: str):
            self.normalized = email
            self.local_part = email.split("@", 1)[0]

    def _validate_email(email, *_args, **_kwargs):
        if "@" not in str(email) or str(email).startswith("@") or str(email).endswith("@"):
            raise _EmailNotValidError("invalid email")
        return _ValidatedEmail(email)

    email_validator_mod.EmailNotValidError = _EmailNotValidError
    email_validator_mod.validate_email = _validate_email
    email_validator_mod.__version__ = "2.0.0"
    sys.modules["email_validator"] = email_validator_mod

_original_version = importlib_metadata.version


def _patched_version(distribution_name: str) -> str:
    if distribution_name == "email-validator":
        return "2.0.0"
    return _original_version(distribution_name)


importlib_metadata.version = _patched_version
pydantic_networks.version = _patched_version

import server


class _Collection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.inserted = []

    async def find_one(self, filt=None, *_args, **_kwargs):
        filt = filt or {}
        for row in self.rows:
            if all(row.get(key) == value for key, value in filt.items()):
                return row
        return None

    async def insert_one(self, doc):
        self.inserted.append(doc)
        self.rows.append(doc)

    async def update_one(self, filt, update, upsert=False):
        row = await self.find_one(filt)
        if row:
            row.update(update.get("$set", {}))
            return
        if upsert:
            doc = dict(filt)
            doc.update(update.get("$set", {}))
            self.rows.append(doc)

    async def create_index(self, *_args, **_kwargs):
        return None


def _fake_db():
    return SimpleNamespace(
        owner_education_magic_links=_Collection(),
        owner_education_owners=_Collection(),
        owner_education_sessions=_Collection(),
        owner_education_progress=_Collection(),
        owner_education_readiness=_Collection(),
        system_state=_Collection(),
    )


def test_catalog_exposes_locked_curriculum_shape():
    catalog = server.education_catalog.get_catalog()
    assert len(catalog["modules"]) == 7
    assert catalog["modules"][0]["title"] == "The Blueprint"
    assert catalog["modules"][-1]["title"] == "The Freedom Framework"
    assert catalog["modules"][0]["dashboard_path"] == "/education/modules/the-blueprint/guide"
    assert catalog["roadmap"][0]["title"] == "Foundations"
    lesson = server.education_catalog.get_lesson("the-blueprint", "home-base-first")
    assert lesson is not None
    assert lesson["lesson"]["scenario"]
    assert lesson["lesson"]["common_mistake"]
    assert lesson["lesson"]["decision_rule"]
    assert [tool["slug"] for tool in lesson["tool_refs"]] == [
        "safe-home-checklist",
        "first-vet-visit-checklist",
    ]
    preview = server.education_catalog.get_public_lesson_preview("the-blueprint", "home-base-first")
    assert preview is not None
    assert preview["lesson"]["title"] == "Home Base First"
    assert preview["tool_refs"][0]["slug"] == "safe-home-checklist"
    transition_module = server.education_catalog.get_module("the-transition-phase")
    assert transition_module is not None
    assert transition_module["intro"].startswith("The first days and weeks with a new puppy or dog often feel messy")
    transition_preview = server.education_catalog.get_public_lesson_preview(
        "the-transition-phase", "accidents-need-routine-not-anger"
    )
    assert transition_preview is not None
    assert transition_preview["lesson"]["decision_rule"] == (
        "Reward the correct moment. Tighten the routine, use the same toilet area, and reinforce toileting in the right place within one or two seconds."
    )
    empathy_module = server.education_catalog.get_module("the-empathy-engine")
    assert empathy_module is not None
    assert len(empathy_module["lessons"]) == 4
    assert empathy_module["intro"].startswith("Many early behaviour problems are really communication problems.")
    empathy_preview = server.education_catalog.get_public_lesson_preview(
        "the-empathy-engine", "freeze-growl-snap-warning"
    )
    assert empathy_preview is not None
    assert empathy_preview["lesson"]["decision_rule"] == (
        "Thank the warning by making the situation safer. Ask what the dog was trying to stop or avoid, then change the setup."
    )
    social_filter_module = server.education_catalog.get_module("the-social-filter")
    assert social_filter_module is not None
    assert len(social_filter_module["lessons"]) == 4
    assert social_filter_module["intro"].startswith("Socialisation is not about exposing the dog to everything as fast as possible.")
    social_filter_preview = server.education_catalog.get_public_lesson_preview(
        "the-social-filter", "traffic-light-rule-for-fear"
    )
    assert social_filter_preview is not None
    assert social_filter_preview["lesson"]["decision_rule"] == (
        "Stay in green. Respect yellow. Exit red. If the experience is no longer easy enough for the dog, step back."
    )
    sync_module = server.education_catalog.get_module("the-sync-mechanics")
    assert sync_module is not None
    assert len(sync_module["lessons"]) == 4
    assert sync_module["intro"].startswith("Dogs learn from what works.")
    sync_preview = server.education_catalog.get_public_lesson_preview(
        "the-sync-mechanics", "stop-paying-for-the-wrong-behaviour"
    )
    assert sync_preview is not None
    assert sync_preview["lesson"]["decision_rule"] == (
        "Reward the replacement, not the chaos. Ask what the dog should do instead, then reward that instead of the old behaviour."
    )
    urban_module = server.education_catalog.get_module("the-urban-flow-and-the-shield")
    assert urban_module is not None
    assert len(urban_module["lessons"]) == 4
    assert urban_module["intro"].startswith("Modern homes and streets are noisy, busy, and full of triggers.")
    urban_preview = server.education_catalog.get_public_lesson_preview(
        "the-urban-flow-and-the-shield", "alone-time-starts-below-threshold"
    )
    assert urban_preview is not None
    assert urban_preview["lesson"]["decision_rule"] == (
        "Practise absence below panic level. If the dog cannot stay calm for this amount of alone time, make the step smaller and safer."
    )
    freedom_module = server.education_catalog.get_module("the-freedom-framework")
    assert freedom_module is not None
    assert len(freedom_module["lessons"]) == 4
    assert freedom_module["intro"].startswith("Freedom should expand only when the dog is ready for it.")
    freedom_preview = server.education_catalog.get_public_lesson_preview(
        "the-freedom-framework", "signals-and-the-optional-toilet-bell"
    )
    assert freedom_preview is not None
    assert freedom_preview["lesson"]["decision_rule"] == (
        "A signal should support the routine, not replace it. The bell is optional, and the routine matters more than the tool."
    )
    guide = server.education_catalog.get_module_guide("the-blueprint", completed_lesson_keys=["the-blueprint:home-base-first"])
    assert guide is not None
    assert guide["continue_path"] == "/education/modules/the-blueprint/lessons/hazards-before-habits"
    assert guide["checkpoint"]["items"]


def test_magic_link_request_verify_and_progress_flow(monkeypatch):
    fake_db = _fake_db()
    monkeypatch.setattr(server, "db", fake_db)

    async def _fake_notify(*_args, **_kwargs):
        return {"education_link_status": "skipped", "education_link_attempts": 0}

    monkeypatch.setattr(server.notifications_service, "notify_owner_education_magic_link", _fake_notify)

    async def _run():
        request_out = await server.request_education_magic_link(
            server.EducationRequestLinkIn(email="owner@example.com", redirect_path="/education/dashboard")
        )
        assert request_out["accepted"] is True
        assert request_out["debug_magic_link"].startswith("http://localhost:3000/education/auth/callback?token=")

        parsed = urlparse(request_out["debug_magic_link"])
        token = parse_qs(parsed.query)["token"][0]
        verify_out = await server.verify_education_magic_link_post(server.EducationVerifyIn(token=token))
        assert verify_out["accepted"] is True
        assert verify_out["owner"]["email"] == "owner@example.com"
        assert verify_out["session"]["token"]

        owner_session = {"owner": {"id": verify_out["owner"]["id"], "email": verify_out["owner"]["email"]}}
        dashboard = await server.get_education_dashboard(owner_session=owner_session)
        assert dashboard["modules"][0]["status"] == "in_progress"
        assert dashboard["next_step"]["module_slug"] == "the-blueprint"
        assert dashboard["capability_tracker"][0]["key"] == "safe_home_setup"
        assert dashboard["trainer_readiness_prompt"]
        assert dashboard["launch_posture"]["phase"] == "supply_first"
        assert dashboard["course_overview"]["total_lessons"] == 26
        assert dashboard["roadmap"][0]["modules"][0]["dashboard_path"] == "/education/modules/the-blueprint/guide"

        guide = await server.get_education_module_guide("the-blueprint", owner_session=owner_session)
        assert guide["module"]["title"] == "The Blueprint"
        assert guide["lesson_rows"][0]["status"] == "current"

        progress_out = await server.update_education_progress(
            server.EducationProgressIn(
                module_slug="the-blueprint",
                lesson_slug="home-base-first",
                completed=True,
            ),
            owner_session=owner_session,
        )
        assert "the-blueprint:home-base-first" in progress_out["completed_lessons"]

        readiness_out = await server.upsert_trainer_readiness(
            server.EducationTrainerReadinessIn(
                main_concern="Dog shuts down on walks",
                trigger_pattern="Loud trucks and fast scooters",
                frequency="3 times a week",
                owner_attempts="Tried shorter walks and more distance",
                safety_concern="Owner feels unsure near roads",
                desired_outcome="Calmer public walks",
                has_video_reference=True,
            ),
            owner_session=owner_session,
        )
        assert readiness_out["main_concern"] == "Dog shuts down on walks"

        tool_out = await server.get_education_tool("trainer-summary-builder", owner_session=owner_session)
        assert tool_out["saved_output"]["desired_outcome"] == "Calmer public walks"

        public_preview = await server.get_education_public_lesson_preview("the-blueprint", "home-base-first")
        assert public_preview["lesson"]["decision_rule"] == "Start small, calm, and safe. Create one protected base area and rest zone before expanding the dog's world."

    asyncio.run(_run())


def test_dashboard_launch_posture_uses_phase_specific_copy(monkeypatch):
    fake_db = _fake_db()
    fake_db.system_state.rows.append(
        {
            "key": "launch_phase_state",
            "current_phase": "growth",
            "public_matching_enabled": False,
            "public_emphasis": "growth_prep",
            "owner_waitlist_mode": "passive_only",
        }
    )
    fake_db.owner_education_progress.rows.append(
        server._default_education_progress(owner_id="owner_1")
    )
    fake_db.owner_education_owners.rows.append(
        {"id": "owner_1", "email": "owner@example.com", "email_norm": "owner@example.com"}
    )
    monkeypatch.setattr(server, "db", fake_db)

    async def _run():
        dashboard = await server.get_education_dashboard(owner_session={"owner": {"id": "owner_1", "email": "owner@example.com"}})
        assert dashboard["launch_phase"] == "growth"
        assert dashboard["launch_posture"]["phase"] == "growth"
        assert dashboard["trainer_bridge"]["enabled"] is False
        assert "opening carefully" in dashboard["launch_posture"]["title"].lower()

    asyncio.run(_run())
