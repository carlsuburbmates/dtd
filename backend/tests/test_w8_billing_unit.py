from __future__ import annotations

import asyncio
from types import SimpleNamespace

import server
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


class _Req:
    def __init__(self, payload: bytes, signature: str = "sig"):
        self._payload = payload
        self.headers = {"Stripe-Signature": signature}

    async def body(self):
        return self._payload


class _StripeEventsCollection:
    def __init__(self, duplicate=False):
        self.duplicate = duplicate
        self.inserted = []
        self.updated = []

    async def insert_one(self, doc):
        if self.duplicate:
            raise server.DuplicateKeyError("dup")
        self.inserted.append(doc)

    async def update_one(self, filt, update):
        self.updated.append((filt, update))


class _IntrosCollection:
    def __init__(self):
        self.updated_many = []

    async def update_many(self, filt, update):
        self.updated_many.append((filt, update))


def test_billing_updates_cover_failure_and_uncollectible_states():
    assert stripe_billing.billing_updates_for_event("invoice.sent", {}).get("billing_collection_status") == "invoice_sent"
    assert stripe_billing.billing_updates_for_event("invoice.payment_failed", {}).get("billing_collection_status") == "payment_failed"
    assert stripe_billing.billing_updates_for_event("invoice.marked_uncollectible", {}).get("billing_collection_status") == "uncollectible"


def test_server_stripe_webhook_handles_full_lifecycle_events(monkeypatch):
    event_cases = [
        ("invoice.sent", "invoice_sent", "in_sent"),
        ("invoice.payment_failed", "payment_failed", "in_failed"),
        ("invoice.marked_uncollectible", "uncollectible", "in_uncollectible"),
        ("charge.dispute.created", "disputed", "in_disputed"),
        ("charge.dispute.closed", "dispute_resolved", "in_resolved"),
    ]

    for event_type, expected_status, invoice_id in event_cases:
        stripe_events = _StripeEventsCollection(duplicate=False)
        intros = _IntrosCollection()
        monkeypatch.setattr(server, "db", SimpleNamespace(stripe_events=stripe_events, intros=intros))
        monkeypatch.setattr(
            stripe_billing,
            "construct_webhook_event",
            lambda payload, signature, event_type=event_type, invoice_id=invoice_id: {
                "id": f"evt_{invoice_id}",
                "type": event_type,
                "data": {"object": {"id": invoice_id, "invoice": invoice_id, "charge": f"ch_{invoice_id}", "metadata": {"intro_id": "intro_1"}}},
            },
        )
        monkeypatch.setattr(stripe_billing, "extract_invoice_id", lambda _etype, obj, invoice_id=invoice_id: obj.get("id") or invoice_id)
        monkeypatch.setattr(stripe_billing, "invoice_id_from_charge", lambda _charge_id, invoice_id=invoice_id: invoice_id)

        out = asyncio.run(server.stripe_webhook(_Req(b"{}")))

        assert out["ok"] is True
        assert len(intros.updated_many) == 1
        assert intros.updated_many[0][0] == {"stripe_invoice_id": invoice_id}
        assert intros.updated_many[0][1]["$set"]["billing_collection_status"] == expected_status
        assert len(stripe_events.updated) == 1


def test_server_stripe_webhook_updates_intro_and_marks_processed(monkeypatch):
    stripe_events = _StripeEventsCollection(duplicate=False)
    intros = _IntrosCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(stripe_events=stripe_events, intros=intros))
    monkeypatch.setattr(
        stripe_billing,
        "construct_webhook_event",
        lambda payload, signature: {
            "id": "evt_1",
            "type": "invoice.paid",
            "data": {"object": {"id": "in_1", "metadata": {"intro_id": "intro_1"}}},
        },
    )
    monkeypatch.setattr(stripe_billing, "extract_invoice_id", lambda _etype, _obj: "in_1")
    monkeypatch.setattr(stripe_billing, "billing_updates_for_event", lambda _etype, _obj: {"billing_collection_status": "paid"})

    out = asyncio.run(server.stripe_webhook(_Req(b"{}")))
    assert out["ok"] is True
    assert len(stripe_events.inserted) == 1
    assert len(intros.updated_many) == 1
    assert intros.updated_many[0][0] == {"stripe_invoice_id": "in_1"}
    assert len(stripe_events.updated) == 1


def test_server_stripe_webhook_duplicate_event_returns_duplicate(monkeypatch):
    stripe_events = _StripeEventsCollection(duplicate=True)
    intros = _IntrosCollection()
    monkeypatch.setattr(server, "db", SimpleNamespace(stripe_events=stripe_events, intros=intros))
    monkeypatch.setattr(
        stripe_billing,
        "construct_webhook_event",
        lambda payload, signature: {
            "id": "evt_1",
            "type": "invoice.paid",
            "data": {"object": {"id": "in_1", "metadata": {"intro_id": "intro_1"}}},
        },
    )
    monkeypatch.setattr(stripe_billing, "extract_invoice_id", lambda _etype, _obj: "in_1")
    monkeypatch.setattr(stripe_billing, "billing_updates_for_event", lambda _etype, _obj: {"billing_collection_status": "paid"})

    out = asyncio.run(server.stripe_webhook(_Req(b"{}")))
    assert out["ok"] is True
    assert out["duplicate"] is True
    assert intros.updated_many == []
