from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import server
from services import stripe_billing


class _Result:
    def __init__(self, matched_count=1):
        self.matched_count = matched_count


class _Trainers:
    def __init__(self, rows):
        self.rows = {row["id"]: dict(row) for row in rows}
        self.updated = []

    async def find_one(self, filt, _projection=None):
        if filt.get("id"):
            return self.rows.get(filt["id"])
        subscription_id = filt.get("stripe_subscription_id")
        return next((row for row in self.rows.values() if row.get("stripe_subscription_id") == subscription_id), None)

    async def update_one(self, filt, update, upsert=False):
        row = self.rows.get(filt.get("id"))
        if not row:
            return _Result(0)
        expected_subscription = filt.get("stripe_subscription_id")
        if expected_subscription and row.get("stripe_subscription_id") != expected_subscription:
            return _Result(0)
        row.update(update.get("$set") or {})
        self.updated.append((filt, update))
        return _Result(1)


class _StripeEvents:
    def __init__(self, duplicate=False):
        self.duplicate = duplicate
        self.inserted = []
        self.updated = []

    async def insert_one(self, row):
        if self.duplicate:
            raise server.DuplicateKeyError("duplicate")
        self.inserted.append(dict(row))

    async def update_one(self, filt, update):
        self.updated.append((filt, update))
        return _Result(1)


class _Request:
    headers = {"Stripe-Signature": "test-signature"}

    async def body(self):
        return b"{}"


def _trainer(**updates):
    base = {
        "id": "trainer_1",
        "name": "Northside Dogs",
        "email": "trainer@example.com",
        "claim_status": "claimed",
        "suburb": "Brunswick",
        "serviced_suburbs": ["Brunswick", "Coburg"],
        "abn": "51 824 753 556",
        "abn_verified": True,
    }
    base.update(updates)
    return base


def test_subscription_plan_matrix_is_fixed_and_validated():
    assert stripe_billing.subscription_plan(tier="pro")["amount_cents"] == 1900
    assert stripe_billing.subscription_plan(tier="suburb_sponsor", suburb="Brunswick")["amount_cents"] == 3900
    assert stripe_billing.subscription_plan(tier="citywide")["amount_cents"] == 19900
    assert stripe_billing.subscription_plan(tier="pro", interval="year")["amount_cents"] == 14900
    with pytest.raises(ValueError, match="suburb_required"):
        stripe_billing.subscription_plan(tier="suburb_sponsor")
    with pytest.raises(ValueError, match="suburb_not_allowed"):
        stripe_billing.subscription_plan(tier="pro", suburb="Brunswick")
    with pytest.raises(ValueError, match="annual"):
        stripe_billing.subscription_plan(tier="citywide", interval="year")


def test_invoice_subscription_metadata_supports_modern_stripe_nesting():
    invoice = {
        "id": "in_1",
        "payment_intent": "pi_1",
        "parent": {
            "subscription_details": {
                "subscription": "sub_1",
                "metadata": {"trainer_id": "trainer_1", "tier": "pro", "interval": "month"},
            }
        },
    }
    assert stripe_billing.subscription_id_for_event(invoice) == "sub_1"
    assert stripe_billing.subscription_trainer_id("invoice.payment_succeeded", invoice) == "trainer_1"
    updates = stripe_billing.subscription_update_for_event("invoice.payment_succeeded", invoice)
    assert updates["subscription_last_payment_intent_id"] == "pi_1"


def test_customer_portal_preserves_supplied_return_url(monkeypatch):
    calls = []

    class FakeStripe:
        class billing_portal:
            class Session:
                @staticmethod
                def create(**kwargs):
                    calls.append(kwargs)
                    return SimpleNamespace(url="https://billing.stripe.test/session")

    monkeypatch.setattr(stripe_billing, "checkout_enabled", lambda: True)
    monkeypatch.setattr(stripe_billing, "_client", lambda: FakeStripe)
    out = asyncio.run(
        stripe_billing.create_customer_portal_session(
            _trainer(stripe_customer_id="cus_1"),
            return_url="https://dtd.test/trainer/billing?trainerId=trainer_1&token=signed",
        )
    )
    assert out["ok"] is True
    assert calls[0]["return_url"].endswith("trainerId=trainer_1&token=signed")


def test_checkout_service_never_fabricates_url_when_stripe_is_unconfigured(monkeypatch):
    monkeypatch.setattr(stripe_billing, "checkout_enabled", lambda: False)
    out = asyncio.run(stripe_billing.create_checkout_session(SimpleNamespace(), _trainer(), tier="pro"))
    assert out["ok"] is False
    assert out["code"] == "billing_activation_required"
    assert "url" not in out


def test_checkout_service_creates_monthly_inclusive_checkout_and_verified_abn_tax_id(monkeypatch):
    class FakeStripe:
        class Customer:
            @staticmethod
            def create(**_kwargs):
                return SimpleNamespace(id="cus_123")

            @staticmethod
            def create_tax_id(customer_id, **kwargs):
                assert customer_id == "cus_123"
                assert kwargs == {"type": "au_abn", "value": "51824753556"}
                return SimpleNamespace(id="txi_123")

        class checkout:
            class Session:
                @staticmethod
                def create(**kwargs):
                    assert kwargs["mode"] == "subscription"
                    assert kwargs["line_items"][0]["price_data"]["unit_amount"] == 3900
                    assert kwargs["line_items"][0]["price_data"]["recurring"] == {"interval": "month"}
                    assert kwargs["line_items"][0]["price_data"]["tax_behavior"] == "inclusive"
                    assert kwargs["subscription_data"]["metadata"]["tier"] == "suburb_sponsor"
                    return SimpleNamespace(id="cs_123", url="https://checkout.stripe.test/cs_123")

    trainers = _Trainers([_trainer()])
    monkeypatch.setattr(stripe_billing, "checkout_enabled", lambda: True)
    monkeypatch.setattr(stripe_billing, "billing_enabled", lambda: True)
    monkeypatch.setattr(stripe_billing, "_client", lambda: FakeStripe)
    out = asyncio.run(
        stripe_billing.create_checkout_session(
            SimpleNamespace(trainers=trainers), _trainer(), tier="suburb_sponsor", suburb="Brunswick", consent_granted=True, consent_version=stripe_billing.billing_terms_version(), idempotency_key="checkout-1"
        )
    )
    assert out["ok"] is True, out
    assert out["session_id"] == "cs_123"
    assert trainers.rows["trainer_1"]["stripe_customer_tax_id"] == "txi_123"
    assert trainers.rows["trainer_1"]["billing_terms_version"] == stripe_billing.billing_terms_version()


def test_checkout_endpoint_requires_claim_session_and_served_suburb(monkeypatch):
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "test-secret")
    trainers = _Trainers([_trainer()])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))

    checkout_calls = []

    async def _checkout(*_args, **kwargs):
        checkout_calls.append(kwargs)
        return {"ok": True, "url": "https://checkout.stripe.test/cs_1", "session_id": "cs_1", "customer_id": "cus_1"}

    monkeypatch.setattr(stripe_billing, "create_checkout_session", _checkout)
    monkeypatch.setattr(stripe_billing, "checkout_enabled", lambda: True)
    monkeypatch.setattr(
        server.suburb_inventory,
        "reserve",
        lambda *_args, **_kwargs: asyncio.sleep(0, result={"ok": True, "reservation": {"reservation_id": "res_1", "expires_at": "2099-01-01T00:00:00+00:00"}}),
    )
    token = server._issue_trainer_claim_session(trainer_id="trainer_1", claim_event_id="claim_1")["token"]
    out = asyncio.run(
        server.create_trainer_billing_checkout(
                server.TrainerCheckoutIn(trainer_id="trainer_1", tier="suburb_sponsor", suburb="Brunswick", consent_subscription_billing_terms=True, billing_terms_version=stripe_billing.billing_terms_version(), trainer_claim_session=token)
        )
    )
    assert out["session_id"] == "cs_1"
    assert events.inserted[0]["status"] == "created"
    return_url = checkout_calls[0]["billing_return_url"]
    assert "trainerId=trainer_1" in return_url
    assert "claimSession=" not in return_url
    assert "token=" not in return_url
    assert ":month:" in checkout_calls[0]["idempotency_key"]

    with pytest.raises(HTTPException) as consent:
        asyncio.run(
            server.create_trainer_billing_checkout(
                server.TrainerCheckoutIn(trainer_id="trainer_1", tier="pro", trainer_claim_session=token)
            )
        )
    assert consent.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            server.create_trainer_billing_checkout(
                server.TrainerCheckoutIn(trainer_id="trainer_1", tier="suburb_sponsor", suburb="Richmond", consent_subscription_billing_terms=True, billing_terms_version=stripe_billing.billing_terms_version(), trainer_claim_session=token)
            )
        )
    assert exc.value.status_code == 403


def test_billing_portal_return_url_excludes_trainer_bearer_tokens(monkeypatch):
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "test-secret")
    trainers = _Trainers([_trainer()])
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=_StripeEvents()))
    portal_calls = []

    async def _portal(*_args, **kwargs):
        portal_calls.append(kwargs)
        return {"ok": True, "url": "https://billing.stripe.test/session"}

    monkeypatch.setattr(stripe_billing, "create_customer_portal_session", _portal)
    token = server._issue_trainer_claim_session(trainer_id="trainer_1", claim_event_id="claim_1")["token"]

    out = asyncio.run(
        server.create_trainer_billing_portal(
            server.TrainerPortalIn(trainer_id="trainer_1", trainer_claim_session=token)
        )
    )

    assert out["ok"] is True
    assert portal_calls[0]["return_url"].endswith("/trainer/billing?trainerId=trainer_1")
    assert "claimSession=" not in portal_calls[0]["return_url"]
    assert "token=" not in portal_calls[0]["return_url"]


def test_checkout_provider_failure_is_recorded_for_ops(monkeypatch):
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "test-secret")
    trainers = _Trainers([_trainer()])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))

    async def _unconfigured(*_args, **_kwargs):
        return {"ok": False, "code": "stripe_unconfigured"}

    monkeypatch.setattr(stripe_billing, "create_checkout_session", _unconfigured)
    monkeypatch.setattr(stripe_billing, "checkout_enabled", lambda: True)
    token = server._issue_trainer_claim_session(trainer_id="trainer_1", claim_event_id="claim_1")["token"]
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.create_trainer_billing_checkout(server.TrainerCheckoutIn(trainer_id="trainer_1", tier="pro", consent_subscription_billing_terms=True, billing_terms_version=stripe_billing.billing_terms_version(), trainer_claim_session=token)))
    assert exc.value.status_code == 503
    assert events.inserted[0]["status"] == "provider_unavailable"
    assert events.inserted[0]["reason"] == "stripe_unconfigured"


def test_subscription_webhooks_update_entitlement_and_preserve_replay_protection(monkeypatch):
    trainers = _Trainers([_trainer()])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))
    monkeypatch.setattr(
        stripe_billing,
        "construct_webhook_event",
        lambda *_args, **_kwargs: {
            "id": "evt_sub_created",
            "type": "customer.subscription.created",
            "data": {"object": {"id": "sub_1", "customer": "cus_1", "status": "active", "metadata": {"trainer_id": "trainer_1", "tier": "pro", "suburb": "", "interval": "month"}}},
        },
    )
    out = asyncio.run(server.stripe_webhook(_Request()))
    assert out == {"ok": True, "needs_review": False}
    assert trainers.rows["trainer_1"]["tier"] == "pro"
    assert trainers.rows["trainer_1"]["stripe_subscription_id"] == "sub_1"
    assert events.updated[-1][1]["$set"]["status"] == "processed"

    events.duplicate = True
    duplicate = asyncio.run(server.stripe_webhook(_Request()))
    assert duplicate == {"ok": True, "duplicate": True}


def test_subscription_update_invoice_and_deletion_webhooks_preserve_entitlement_lifecycle(monkeypatch):
    trainers = _Trainers([_trainer(tier="pro", stripe_subscription_id="sub_1")])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))

    event = {
        "id": "evt_sub_updated",
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_1", "customer": "cus_1", "status": "past_due", "metadata": {"trainer_id": "trainer_1", "tier": "pro"}}},
    }
    monkeypatch.setattr(stripe_billing, "construct_webhook_event", lambda *_args, **_kwargs: event)
    assert asyncio.run(server.stripe_webhook(_Request())) == {"ok": True, "needs_review": False}
    assert trainers.rows["trainer_1"]["tier"] == "pro"
    assert trainers.rows["trainer_1"]["subscription_status"] == "past_due"

    event.update(
        {
            "id": "evt_invoice_paid",
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_sub_1", "subscription": "sub_1", "status": "paid", "metadata": {}}},
        }
    )
    assert asyncio.run(server.stripe_webhook(_Request())) == {"ok": True, "needs_review": False}
    assert trainers.rows["trainer_1"]["subscription_billing_status"] == "paid"

    event.update(
        {
            "id": "evt_sub_deleted",
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_1", "customer": "cus_1", "status": "canceled", "metadata": {"trainer_id": "trainer_1", "tier": "pro"}}},
        }
    )
    assert asyncio.run(server.stripe_webhook(_Request())) == {"ok": True, "needs_review": False}
    assert trainers.rows["trainer_1"]["tier"] == "claimed"
    assert trainers.rows["trainer_1"]["subscription_status"] == "canceled"


def test_unresolved_subscription_webhook_is_visible_for_review(monkeypatch):
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(stripe_events=events, trainers=_Trainers([])))
    monkeypatch.setattr(
        stripe_billing,
        "construct_webhook_event",
        lambda *_args, **_kwargs: {
            "id": "evt_unresolved",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_unknown", "status": "active", "metadata": {"tier": "pro"}}},
        },
    )
    out = asyncio.run(server.stripe_webhook(_Request()))
    assert out == {"ok": True, "needs_review": True}
    assert events.updated[-1][1]["$set"]["status"] == "needs_review"
    assert events.updated[-1][1]["$set"]["reason"] == "subscription_trainer_unresolved"


def test_sponsor_checkout_reserves_inventory_and_releases_it_when_provider_fails(monkeypatch):
    monkeypatch.setenv("TRAINER_ACTION_TOKEN_SECRET", "test-secret")
    trainers = _Trainers([_trainer()])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))
    calls = []

    async def _reserve(*_args, **_kwargs):
        return {"ok": True, "reservation": {"reservation_id": "res_1", "expires_at": "2099-01-01T00:00:00+00:00"}}

    async def _release(*_args, **kwargs):
        calls.append(kwargs)
        return {"ok": True, "released": 1}

    async def _checkout(*_args, **kwargs):
        assert kwargs["reservation_id"] == "res_1"
        return {"ok": False, "code": "stripe_error"}

    monkeypatch.setattr(server.suburb_inventory, "reserve", _reserve)
    monkeypatch.setattr(server.suburb_inventory, "release_reservation", _release)
    monkeypatch.setattr(stripe_billing, "create_checkout_session", _checkout)
    monkeypatch.setattr(stripe_billing, "checkout_enabled", lambda: True)
    token = server._issue_trainer_claim_session(trainer_id="trainer_1", claim_event_id="claim_1")["token"]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            server.create_trainer_billing_checkout(
                server.TrainerCheckoutIn(
                    trainer_id="trainer_1",
                    tier="suburb_sponsor",
                    suburb="Brunswick",
                    consent_subscription_billing_terms=True,
                    billing_terms_version=stripe_billing.billing_terms_version(),
                    trainer_claim_session=token,
                )
            )
        )

    assert exc.value.status_code == 503
    assert calls == [{"reservation_id": "res_1", "reason": "checkout_failed"}]
    assert events.inserted[0]["status"] == "needs_review"


def test_active_sponsor_webhook_requires_inventory_activation_before_entitlement(monkeypatch):
    trainers = _Trainers([_trainer()])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))
    calls = []
    monkeypatch.setattr(
        stripe_billing,
        "construct_webhook_event",
        lambda *_args, **_kwargs: {
            "id": "evt_sponsor_created",
            "type": "customer.subscription.created",
            "data": {"object": {"id": "sub_1", "customer": "cus_1", "status": "active", "metadata": {"trainer_id": "trainer_1", "tier": "suburb_sponsor", "suburb": "Brunswick", "interval": "month", "reservation_id": "res_1"}}},
        },
    )

    async def _activate(*_args, **kwargs):
        calls.append(kwargs)
        return {"ok": True, "reservation": {"reservation_id": "res_1"}}

    monkeypatch.setattr(server.suburb_inventory, "activate_reservation", _activate)
    out = asyncio.run(server.stripe_webhook(_Request()))

    assert out == {"ok": True, "needs_review": False}
    assert calls == [{"reservation_id": "res_1", "subscription_id": "sub_1"}]
    assert trainers.rows["trainer_1"]["tier"] == "suburb_sponsor"
    assert trainers.rows["trainer_1"]["sponsor_reservation_id"] == "res_1"


def test_sponsor_webhook_does_not_grant_entitlement_when_reservation_expired(monkeypatch):
    trainers = _Trainers([_trainer()])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))
    monkeypatch.setattr(
        stripe_billing,
        "construct_webhook_event",
        lambda *_args, **_kwargs: {
            "id": "evt_sponsor_expired",
            "type": "customer.subscription.created",
            "data": {"object": {"id": "sub_1", "status": "active", "metadata": {"trainer_id": "trainer_1", "tier": "suburb_sponsor", "suburb": "Brunswick", "reservation_id": "res_expired"}}},
        },
    )

    async def _expired(*_args, **_kwargs):
        return {"ok": False, "code": "reservation_missing_or_expired"}

    monkeypatch.setattr(server.suburb_inventory, "activate_reservation", _expired)
    out = asyncio.run(server.stripe_webhook(_Request()))

    assert out == {"ok": True, "needs_review": True}
    assert trainers.rows["trainer_1"].get("tier") != "suburb_sponsor"
    assert events.updated[-1][1]["$set"]["reason"] == "reservation_missing_or_expired"


def test_sponsor_cancellation_webhook_releases_position(monkeypatch):
    trainers = _Trainers([_trainer(tier="suburb_sponsor", stripe_subscription_id="sub_1", sponsor_reservation_id="res_1")])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))
    monkeypatch.setattr(
        stripe_billing,
        "construct_webhook_event",
        lambda *_args, **_kwargs: {
            "id": "evt_sponsor_deleted",
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_1", "status": "canceled", "metadata": {"trainer_id": "trainer_1", "tier": "suburb_sponsor", "suburb": "Brunswick", "reservation_id": "res_1"}}},
        },
    )
    released = []
    monkeypatch.setattr(
        server.suburb_inventory,
        "release_reservation",
        lambda *_args, **kwargs: asyncio.sleep(0, result=released.append(kwargs) or {"ok": True, "released": 1}),
    )

    out = asyncio.run(server.stripe_webhook(_Request()))

    assert out == {"ok": True, "needs_review": False}
    assert trainers.rows["trainer_1"]["tier"] == "claimed"
    assert released[0]["reservation_id"] == "res_1"
    assert released[0]["reason"] == "cancelled"


def test_terminal_sponsor_nonpayment_releases_position_and_entitlement(monkeypatch):
    trainers = _Trainers([_trainer(tier="suburb_sponsor", stripe_subscription_id="sub_1", sponsor_reservation_id="res_1")])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))
    monkeypatch.setattr(
        stripe_billing,
        "construct_webhook_event",
        lambda *_args, **_kwargs: {
            "id": "evt_sponsor_unpaid",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_1", "status": "unpaid", "metadata": {"trainer_id": "trainer_1", "tier": "suburb_sponsor", "suburb": "Brunswick", "reservation_id": "res_1"}}},
        },
    )
    released = []
    monkeypatch.setattr(
        server.suburb_inventory,
        "release_reservation",
        lambda *_args, **kwargs: asyncio.sleep(0, result=released.append(kwargs) or {"ok": True, "released": 1}),
    )

    out = asyncio.run(server.stripe_webhook(_Request()))

    assert out == {"ok": True, "needs_review": False}
    assert trainers.rows["trainer_1"]["tier"] == "claimed"
    assert trainers.rows["trainer_1"]["subscription_status"] == "unpaid"
    assert released == [{"reservation_id": "res_1", "subscription_id": "", "reason": "payment_failed"}]


def test_ops_refund_is_gated_and_success_releases_inventory(monkeypatch):
    trainer = _trainer(
        tier="suburb_sponsor",
        subscription_tier="suburb_sponsor",
        subscription_status="active",
        subscription_interval="month",
        subscription_active_at=datetime.now(timezone.utc).isoformat(),
        stripe_subscription_id="sub_1",
        sponsor_reservation_id="res_1",
    )
    trainers = _Trainers([trainer])
    events = _StripeEvents()
    monkeypatch.setattr(server, "db", SimpleNamespace(trainers=trainers, stripe_events=events))
    payload = server.OpsSubscriptionRefundIn(
        trainer_id="trainer_1",
        stripe_subscription_id="sub_1",
        payment_intent_id="pi_1",
        reason="Requested within guarantee",
    )

    monkeypatch.delenv("ENABLE_OPS_STRIPE_REFUNDS", raising=False)
    with pytest.raises(HTTPException) as gated:
        asyncio.run(server.refund_trainer_subscription(payload))
    assert gated.value.status_code == 503

    monkeypatch.setenv("ENABLE_OPS_STRIPE_REFUNDS", "1")
    monkeypatch.setattr(
        stripe_billing,
        "refund_subscription_payment",
        lambda **_kwargs: asyncio.sleep(0, result={"ok": True, "refund_id": "re_1", "status": "succeeded"}),
    )
    released = []
    monkeypatch.setattr(
        server.suburb_inventory,
        "release_reservation",
        lambda *_args, **kwargs: asyncio.sleep(0, result=released.append(kwargs) or {"ok": True, "released": 1}),
    )
    out = asyncio.run(server.refund_trainer_subscription(payload))

    assert out == {"ok": True, "refund_id": "re_1", "status": "succeeded"}
    assert trainers.rows["trainer_1"]["tier"] == "claimed"
    assert released[0]["reason"] == "refunded"
    assert events.updated[-1][1]["$set"]["status"] == "processed"
