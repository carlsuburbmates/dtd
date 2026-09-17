from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services import stripe_billing

ANCHOR = "2026-09-01T00:00:00+00:00"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in (
        "STRIPE_SECRET_KEY",
        "STRIPE_LIVE_ANCHOR_AT",
        "PRO_TRIAL_DAYS",
        "PRO_TRIAL_EXPIRY_WARNING_DAY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_cohort_inactive_in_stripe_test_mode(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", ANCHOR)

    assert stripe_billing.stripe_live_mode() is False
    assert stripe_billing.trial_cohort_active() is False

    status = stripe_billing.trial_status({"registered_at": "2026-09-10T00:00:00+00:00"})
    assert status["active"] is False
    assert status["in_cohort"] is False


def test_cohort_inactive_without_live_anchor(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")

    assert stripe_billing.stripe_live_mode() is True
    assert stripe_billing.trial_cohort_active() is False

    status = stripe_billing.trial_status({"registered_at": "2026-09-10T00:00:00+00:00"})
    assert status["in_cohort"] is False


def test_trainer_registered_before_anchor_is_not_in_cohort(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", ANCHOR)

    status = stripe_billing.trial_status({"registered_at": "2026-08-15T00:00:00+00:00"})
    assert status["cohort_active"] is True
    assert status["in_cohort"] is False
    assert status["active"] is False


def test_trainer_after_anchor_is_in_cohort_and_active(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    now = datetime.now(timezone.utc)
    anchor = now - timedelta(days=40)
    registered = now - timedelta(days=5)
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", _iso(anchor))

    status = stripe_billing.trial_status({"registered_at": _iso(registered)})
    assert status["in_cohort"] is True
    assert status["active"] is True
    assert status["days"] == 30
    ends = datetime.fromisoformat(status["ends_at"])
    assert abs((ends - (registered + timedelta(days=30))).total_seconds()) < 2


def test_expiry_warning_fires_from_day_23(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    now = datetime.now(timezone.utc)
    anchor = now - timedelta(days=60)
    registered = now - timedelta(days=25)
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", _iso(anchor))

    status = stripe_billing.trial_status({"registered_at": _iso(registered)})
    assert status["active"] is True
    assert status["expiry_warning"] is True
    assert status["days_remaining"] <= 7


def test_no_warning_early_in_trial(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    now = datetime.now(timezone.utc)
    anchor = now - timedelta(days=60)
    registered = now - timedelta(days=3)
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", _iso(anchor))

    status = stripe_billing.trial_status({"registered_at": _iso(registered)})
    assert status["active"] is True
    assert status["expiry_warning"] is False


def test_expired_trial_is_in_cohort_but_not_active(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    now = datetime.now(timezone.utc)
    anchor = now - timedelta(days=120)
    registered = now - timedelta(days=45)
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", _iso(anchor))

    status = stripe_billing.trial_status({"registered_at": _iso(registered)})
    assert status["in_cohort"] is True
    assert status["active"] is False
