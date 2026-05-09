from __future__ import annotations

import asyncio
from types import SimpleNamespace

from services import stripe_billing


def test_extract_invoice_id_by_event_type():
    assert stripe_billing.extract_invoice_id("invoice.paid", {"id": "in_123"}) == "in_123"
    assert stripe_billing.extract_invoice_id("charge.refunded", {"invoice": "in_456"}) == "in_456"
    assert stripe_billing.extract_invoice_id("unknown.event", {"id": "x"}) == ""


def test_billing_updates_for_extended_lifecycle_states():
    assert stripe_billing.billing_updates_for_event("invoice.voided", {}).get("billing_collection_status") == "waived"
    assert stripe_billing.billing_updates_for_event("charge.refunded", {}).get("billing_collection_status") == "refunded"
    assert stripe_billing.billing_updates_for_event("charge.dispute.created", {}).get("billing_collection_status") == "disputed"
    assert stripe_billing.billing_updates_for_event("charge.dispute.closed", {}).get("billing_collection_status") == "dispute_resolved"


def test_bill_intro_invoice_sent_with_mocked_stripe(monkeypatch):
    class FakeStripe:
        class Invoice:
            @staticmethod
            def create(**kwargs):
                assert kwargs["customer"] == "cus_123"
                return SimpleNamespace(id="in_123")

            @staticmethod
            def finalize_invoice(_invoice_id):
                return {"status": "open", "hosted_invoice_url": "https://example.com/inv"}

            @staticmethod
            def send_invoice(_invoice_id):
                return {"status": "open", "hosted_invoice_url": "https://example.com/inv"}

        class InvoiceItem:
            @staticmethod
            def create(**kwargs):
                assert kwargs["invoice"] == "in_123"
                return {"id": "ii_123"}

    async def fake_profile(_db, _trainer, *, consent_granted):
        assert consent_granted is False
        return {"stripe_customer_id": "cus_123", "billing_profile_status": "ready"}

    monkeypatch.setattr(stripe_billing, "billing_enabled", lambda: True)
    monkeypatch.setattr(stripe_billing, "_client", lambda: FakeStripe)
    monkeypatch.setattr(stripe_billing, "provision_trainer_billing_profile", fake_profile)
    monkeypatch.setattr(stripe_billing, "_consent_ok", lambda _trainer, consent_granted: True)

    trainer = {"id": "t_1", "name": "Trainer", "stripe_customer_id": "", "billing_profile_status": "ready"}
    intro = {"id": "i_1", "billing_status": "billed", "intro_fee_cents": 500, "match_id": "m_1"}
    out = asyncio.run(stripe_billing.bill_intro(object(), trainer, intro))
    assert out["billing_collection_status"] == "invoice_sent"
    assert out["stripe_invoice_id"] == "in_123"


def test_bill_intro_profile_incomplete_when_customer_unavailable(monkeypatch):
    async def fake_profile(_db, _trainer, *, consent_granted):
        assert consent_granted is False
        return {"billing_profile_status": "missing_email"}

    monkeypatch.setattr(stripe_billing, "billing_enabled", lambda: True)
    monkeypatch.setattr(stripe_billing, "provision_trainer_billing_profile", fake_profile)
    monkeypatch.setattr(stripe_billing, "_consent_ok", lambda _trainer, consent_granted: True)

    trainer = {"id": "t_1", "name": "Trainer", "stripe_customer_id": ""}
    intro = {"id": "i_1", "billing_status": "billed", "intro_fee_cents": 500}
    out = asyncio.run(stripe_billing.bill_intro(object(), trainer, intro))
    assert out["billing_collection_status"] == "profile_incomplete"
    assert out["billing_profile_status"] == "missing_email"


def test_bill_intro_trial_free_skips_invoice(monkeypatch):
    monkeypatch.setenv("TRAINER_FREE_INTRO_DAYS", "30")
    monkeypatch.setattr(stripe_billing, "billing_enabled", lambda: True)
    monkeypatch.setattr(stripe_billing, "_consent_ok", lambda _trainer, consent_granted: True)

    trainer = {
        "id": "t_1",
        "name": "Trainer",
        "via_submission_id": "sub_1",
        "created_at": stripe_billing.now_iso(),
    }
    intro = {"id": "i_1", "billing_status": "billed", "intro_fee_cents": 500}
    out = asyncio.run(stripe_billing.bill_intro(object(), trainer, intro))
    assert out["billing_collection_status"] == "trial_free"
    assert out["intro_fee_cents"] == 0
    assert out["intro_fee_list_cents"] == 500
