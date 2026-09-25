from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from services import stripe_billing

ANCHOR = "2026-09-01T00:00:00+00:00"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in ("STRIPE_SECRET_KEY", "STRIPE_LIVE_ANCHOR_AT", "PRO_TRIAL_DAYS", "PRO_TRIAL_EXPIRY_WARNING_DAY"):
        monkeypatch.delenv(key, raising=False)


def _activate_cohort(monkeypatch, now: datetime) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", _iso(now - timedelta(days=40)))
    monkeypatch.setattr(stripe_billing, "_now", lambda: now)


def test_cohort_requires_live_key_and_anchor(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", ANCHOR)
    assert stripe_billing.trial_status({"registered_at": "2026-09-10T00:00:00+00:00"})["in_cohort"] is False

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    monkeypatch.delenv("STRIPE_LIVE_ANCHOR_AT")
    assert stripe_billing.trial_status({"registered_at": "2026-09-10T00:00:00+00:00"})["in_cohort"] is False


def test_pre_anchor_trainer_is_not_eligible(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
    monkeypatch.setenv("STRIPE_LIVE_ANCHOR_AT", ANCHOR)
    status = stripe_billing.trial_status({"claimed_at": "2026-08-15T00:00:00+00:00"})
    assert status["cohort_active"] is True
    assert status["in_cohort"] is False
    assert status["eligible"] is False


def test_post_anchor_claim_is_eligible_until_consumed(monkeypatch):
    now = datetime(2026, 9, 18, tzinfo=timezone.utc)
    _activate_cohort(monkeypatch, now)
    status = stripe_billing.trial_status({"claimed_at": _iso(now - timedelta(days=2))})
    assert status["in_cohort"] is True
    assert status["eligible"] is True
    assert status["active"] is False

    consumed = stripe_billing.trial_status({"claimed_at": _iso(now - timedelta(days=2)), "pro_trial_consumed_at": _iso(now)})
    assert consumed["eligible"] is False
    assert consumed["consumed"] is True


def test_provider_backed_trial_and_day_23_warning(monkeypatch):
    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    _activate_cohort(monkeypatch, now)
    start = now - timedelta(days=23)
    trainer = {
        "claimed_at": _iso(now - timedelta(days=30)),
        "subscription_status": "trialing",
        "pro_trial_started_at": _iso(start),
        "pro_trial_ends_at": _iso(start + timedelta(days=30)),
        "pro_trial_consumed_at": _iso(start),
    }
    status = stripe_billing.trial_status(trainer)
    assert status["active"] is True
    assert status["eligible"] is False
    assert status["expiry_warning"] is True
    assert status["days_remaining"] == 7


def test_only_eligible_pro_checkout_receives_full_stripe_trial(monkeypatch):
    now = datetime(2026, 9, 18, tzinfo=timezone.utc)
    _activate_cohort(monkeypatch, now)
    calls = []

    class FakeStripe:
        class checkout:
            class Session:
                @staticmethod
                def create(**kwargs):
                    calls.append(kwargs)
                    return SimpleNamespace(id="cs_trial", url="https://checkout.stripe.test/cs_trial")

    monkeypatch.setattr(stripe_billing, "_client", lambda: FakeStripe)
    monkeypatch.setattr(stripe_billing, "checkout_enabled", lambda: True)
    monkeypatch.setattr(
        stripe_billing,
        "provision_trainer_billing_profile",
        lambda *_args, **_kwargs: asyncio.sleep(0, result={"billing_profile_status": "ready", "stripe_customer_id": "cus_1"}),
    )
    trainer = {"id": "trainer_1", "claimed_at": _iso(now - timedelta(days=1))}
    out = asyncio.run(
        stripe_billing.create_checkout_session(
            SimpleNamespace(),
            trainer,
            tier="pro",
            consent_granted=True,
            consent_version=stripe_billing.billing_terms_version(),
        )
    )
    assert out["pro_trial_offered"] is True
    assert calls[0]["subscription_data"]["trial_period_days"] == 30
    assert calls[0]["subscription_data"]["metadata"]["pro_trial_cohort_anchor_at"]


def test_webhook_persists_provider_trial_period_and_consumption():
    start = datetime(2026, 9, 18, tzinfo=timezone.utc)
    updates = stripe_billing.subscription_update_for_event(
        "customer.subscription.created",
        {
            "id": "sub_1",
            "customer": "cus_1",
            "status": "trialing",
            "trial_start": int(start.timestamp()),
            "trial_end": int((start + timedelta(days=30)).timestamp()),
            "metadata": {"trainer_id": "trainer_1", "tier": "pro", "interval": "month"},
        },
    )
    assert updates["pro_trial_started_at"] == _iso(start)
    assert updates["pro_trial_ends_at"] == _iso(start + timedelta(days=30))
    assert updates["pro_trial_consumed_at"]
