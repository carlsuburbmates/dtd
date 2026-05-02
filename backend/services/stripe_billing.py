from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some environments
    stripe = None  # type: ignore


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _secret_key() -> str:
    return (os.environ.get("STRIPE_SECRET_KEY") or "").strip()


def _webhook_secret() -> str:
    return (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()


def _default_currency() -> str:
    return (os.environ.get("STRIPE_DEFAULT_CURRENCY") or "aud").strip().lower() or "aud"


def _require_consent_enabled() -> bool:
    return (os.environ.get("STRIPE_REQUIRE_BILLING_CONSENT") or "0").strip() == "1"


def _days_until_due() -> int:
    raw = (os.environ.get("STRIPE_INVOICE_DAYS_UNTIL_DUE") or "7").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 7
    return max(1, min(value, 60))


def billing_enabled() -> bool:
    return bool(stripe is not None and _secret_key())


def webhook_enabled() -> bool:
    return bool(billing_enabled() and _webhook_secret())


def _client():
    if stripe is None:
        raise RuntimeError("stripe_sdk_missing")
    secret = _secret_key()
    if not secret:
        raise RuntimeError("stripe_secret_missing")
    stripe.api_key = secret
    return stripe


def _pick_billing_email(trainer: Dict[str, Any]) -> str:
    return (trainer.get("billing_email") or trainer.get("email") or "").strip()


def _consent_ok(trainer: Dict[str, Any], consent_granted: bool) -> bool:
    if not _require_consent_enabled():
        return True
    if consent_granted:
        return True
    return bool(trainer.get("billing_terms_accepted_at"))


async def provision_trainer_billing_profile(
    db,
    trainer: Dict[str, Any],
    *,
    consent_granted: bool,
) -> Dict[str, Any]:
    """Ensure a trainer has a Stripe customer reference for intro invoicing.

    This function is fail-soft by design: it returns a status dictionary and
    does not raise for operational cases like missing email or missing config.
    """
    trainer_id = trainer.get("id")
    email = _pick_billing_email(trainer)
    status: Dict[str, Any] = {
        "billing_profile_updated_at": now_iso(),
        "billing_email": email,
    }

    if not _consent_ok(trainer, consent_granted):
        status.update({"billing_profile_status": "consent_required"})
        await db.trainers.update_one({"id": trainer_id}, {"$set": status})
        return status

    if consent_granted:
        status["billing_terms_accepted_at"] = now_iso()

    if not email:
        status.update({"billing_profile_status": "missing_email"})
        await db.trainers.update_one({"id": trainer_id}, {"$set": status})
        return status

    customer_id = (trainer.get("stripe_customer_id") or "").strip()
    if customer_id:
        status.update({"stripe_customer_id": customer_id, "billing_profile_status": "ready"})
        await db.trainers.update_one({"id": trainer_id}, {"$set": status})
        return status

    if not billing_enabled():
        status.update({"billing_profile_status": "stripe_unconfigured"})
        await db.trainers.update_one({"id": trainer_id}, {"$set": status})
        return status

    try:
        s = _client()
        customer = s.Customer.create(
            name=(trainer.get("name") or "").strip() or "Trainer",
            email=email,
            metadata={
                "trainer_id": str(trainer_id or ""),
                "region": str(trainer.get("region") or ""),
            },
        )
        status.update(
            {
                "stripe_customer_id": customer.id,
                "billing_profile_status": "ready",
            }
        )
    except Exception as exc:  # noqa: BLE001
        status.update(
            {
                "billing_profile_status": "stripe_error",
                "billing_profile_error": str(exc)[:240],
            }
        )

    await db.trainers.update_one({"id": trainer_id}, {"$set": status})
    return status


async def bill_intro(db, trainer: Dict[str, Any], intro: Dict[str, Any]) -> Dict[str, Any]:
    """Create and send a one-off Stripe invoice for a billed intro.

    Returns metadata that can be persisted on the intro row.
    """
    if intro.get("billing_status") != "billed":
        return {"billing_collection_status": "not_billable"}

    fee_cents = int(intro.get("intro_fee_cents") or 0)
    if fee_cents <= 0:
        return {"billing_collection_status": "not_billable"}

    if not billing_enabled():
        return {"billing_collection_status": "stripe_unconfigured"}

    if not _consent_ok(trainer, consent_granted=False):
        return {"billing_collection_status": "consent_required"}

    profile = await provision_trainer_billing_profile(db, trainer, consent_granted=False)
    customer_id = (profile.get("stripe_customer_id") or trainer.get("stripe_customer_id") or "").strip()
    if not customer_id:
        return {
            "billing_collection_status": "profile_incomplete",
            "billing_profile_status": profile.get("billing_profile_status"),
        }

    intro_id = str(intro.get("id") or "")
    metadata = {
        "intro_id": intro_id,
        "trainer_id": str(trainer.get("id") or ""),
        "match_id": str(intro.get("match_id") or ""),
    }

    description = f"Bark&Bond intro · {trainer.get('name') or 'Trainer'} · intro {intro_id[:8]}"

    try:
        s = _client()

        invoice = s.Invoice.create(
            customer=customer_id,
            collection_method="send_invoice",
            days_until_due=_days_until_due(),
            auto_advance=False,
            currency=_default_currency(),
            description=description,
            metadata=metadata,
        )

        s.InvoiceItem.create(
            customer=customer_id,
            invoice=invoice.id,
            amount=fee_cents,
            currency=_default_currency(),
            description=f"Lead intro fee ({intro_id[:8]})",
            metadata=metadata,
        )

        finalized = s.Invoice.finalize_invoice(invoice.id)
        sent = s.Invoice.send_invoice(invoice.id)

        return {
            "billing_collection_status": "invoice_sent",
            "stripe_customer_id": customer_id,
            "stripe_invoice_id": invoice.id,
            "stripe_invoice_status": sent.get("status") or finalized.get("status"),
            "stripe_hosted_invoice_url": sent.get("hosted_invoice_url") or finalized.get("hosted_invoice_url"),
            "stripe_invoice_sent_at": now_iso(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "billing_collection_status": "invoice_error",
            "stripe_customer_id": customer_id,
            "stripe_error": str(exc)[:240],
        }


def construct_webhook_event(payload: bytes, signature: str) -> Dict[str, Any]:
    if not webhook_enabled():
        raise RuntimeError("stripe_webhook_unconfigured")
    if not signature:
        raise RuntimeError("stripe_signature_missing")
    s = _client()
    event = s.Webhook.construct_event(payload=payload, sig_header=signature, secret=_webhook_secret())
    return event
