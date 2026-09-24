from __future__ import annotations

import math
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some environments
    stripe = None  # type: ignore


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _secret_key() -> str:
    return (os.environ.get("STRIPE_SECRET_KEY") or "").strip()


def _webhook_secret() -> str:
    return (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()


def _default_currency() -> str:
    return (os.environ.get("STRIPE_DEFAULT_CURRENCY") or "aud").strip().lower() or "aud"


SUBSCRIPTION_PLANS: Dict[str, Dict[str, Any]] = {
    "pro": {"amount_cents": 1900, "annual_amount_cents": 14900, "name": "DTD Pro", "requires_suburb": False},
    "suburb_sponsor": {"amount_cents": 3900, "name": "DTD Suburb Sponsorship", "requires_suburb": True},
    "citywide": {"amount_cents": 19900, "name": "DTD Melbourne-Wide", "requires_suburb": False},
}

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}
TERMINAL_NONPAYMENT_SUBSCRIPTION_STATUSES = {"unpaid", "incomplete_expired"}
BILLING_TERMS_VERSION = "2026-09-24"


def billing_terms_version() -> str:
    return BILLING_TERMS_VERSION


def checkout_enabled() -> bool:
    """Whether DTD is deliberately accepting new paid subscriptions.

    A configured Stripe key may be present for webhook verification or
    pre-launch work. It is not, by itself, permission to collect a payment.
    """
    return bool(billing_enabled() and (os.environ.get("ENABLE_TRAINER_BILLING_CHECKOUT") or "0").strip() == "1")


def _days_until_due() -> int:
    raw = (os.environ.get("STRIPE_INVOICE_DAYS_UNTIL_DUE") or "7").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 7
    return max(1, min(value, 60))


def pro_trial_days() -> int:
    raw = (os.environ.get("PRO_TRIAL_DAYS") or "30").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 30
    return max(0, min(value, 365))


def pro_trial_expiry_warning_day() -> int:
    raw = (os.environ.get("PRO_TRIAL_EXPIRY_WARNING_DAY") or "23").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 23
    return max(0, min(value, 365))


def stripe_live_mode() -> bool:
    """Stripe live mode is detected from the secret key prefix (sk_live_ vs sk_test_)."""
    return _secret_key().startswith("sk_live_")


def stripe_live_anchor_at() -> Optional[datetime]:
    """The cohort anchor: the moment Stripe went live.

    Pro-trial cohort membership begins at this timestamp. This replaces the retired
    always-on free-intro window; a trainer is only in the cohort when Stripe is live,
    the anchor is set, and the trainer registered at or after the anchor.
    """
    raw = (os.environ.get("STRIPE_LIVE_ANCHOR_AT") or "").strip()
    if not raw:
        return None
    return _parse_iso(raw)


def trial_cohort_active() -> bool:
    return bool(stripe_live_mode() and stripe_live_anchor_at() is not None)


def _registration_started_at(trainer: Dict[str, Any]) -> Optional[datetime]:
    for field in ("claimed_at", "registered_at"):
        value = (trainer.get(field) or "").strip() if isinstance(trainer.get(field), str) else ""
        if value:
            dt = _parse_iso(value)
            if dt:
                return dt
    created = (trainer.get("created_at") or "").strip() if isinstance(trainer.get("created_at"), str) else ""
    if (trainer.get("via_submission_id") or "").strip():
        return _parse_iso(created) if created else None
    return None


def trial_status(trainer: Dict[str, Any]) -> Dict[str, Any]:
    """Pro trial status, anchored to the Stripe-live cohort.

    Cohort eligibility starts when Stripe live mode is explicitly anchored. The
    actual 30-day period starts when Stripe creates the Pro subscription; the
    expiry warning becomes due on day 23 of that provider-backed period.
    """
    days = pro_trial_days()
    warning_day = pro_trial_expiry_warning_day()
    anchor = stripe_live_anchor_at()
    cohort_active = bool(stripe_live_mode() and anchor is not None)
    cohort_start = _registration_started_at(trainer)
    trial_start = _parse_iso(str(trainer.get("pro_trial_started_at") or ""))
    trial_end = _parse_iso(str(trainer.get("pro_trial_ends_at") or ""))
    consumed = bool(trainer.get("pro_trial_consumed_at"))
    subscription_status = str(trainer.get("subscription_status") or "").strip().lower()

    base = {
        "active": False,
        "eligible": False,
        "consumed": consumed,
        "days": days,
        "warning_day": warning_day,
        "cohort_active": cohort_active,
        "cohort_anchor_at": anchor.isoformat() if anchor else "",
        "in_cohort": False,
        "days_remaining": 0,
        "expiry_warning": False,
        "started_at": "",
        "ends_at": "",
    }

    if not cohort_active or days <= 0 or cohort_start is None:
        return base
    if anchor is not None and cohort_start < anchor:
        return base

    now = _now()
    active = bool(subscription_status == "trialing" and trial_start and trial_end and now < trial_end)
    days_remaining = max(0, math.ceil((trial_end - now).total_seconds() / 86400)) if active and trial_end else 0
    warning_due_at = trial_start + timedelta(days=warning_day) if trial_start else None
    return {
        **base,
        "active": active,
        "in_cohort": True,
        "eligible": not consumed and not active,
        "days_remaining": days_remaining,
        "expiry_warning": bool(active and warning_due_at and now >= warning_due_at),
        "started_at": trial_start.isoformat() if trial_start else "",
        "ends_at": trial_end.isoformat() if trial_end else "",
    }


def _stripe_timestamp_iso(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat() if value is not None else ""
    except (TypeError, ValueError, OSError):
        return ""


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


def _stripe_value(value: Any, key: str, default: Any = "") -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _normalized_abn(value: Any) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def subscription_plan(*, tier: str, suburb: Optional[str] = None, interval: str = "month") -> Dict[str, Any]:
    """Return a validated, fixed-price DTD subscription plan."""
    normalized_tier = (tier or "").strip().lower()
    normalized_suburb = " ".join((suburb or "").strip().split())
    normalized_interval = (interval or "").strip().lower()
    plan = SUBSCRIPTION_PLANS.get(normalized_tier)
    if plan is None:
        raise ValueError("unsupported_subscription_tier")
    if normalized_interval not in {"month", "year"}:
        raise ValueError("unsupported_subscription_interval")
    if normalized_interval == "year" and normalized_tier != "pro":
        raise ValueError("unsupported_annual_subscription_tier")
    if bool(plan["requires_suburb"]) and not normalized_suburb:
        raise ValueError("suburb_required_for_subscription_tier")
    if not bool(plan["requires_suburb"]) and normalized_suburb:
        raise ValueError("suburb_not_allowed_for_subscription_tier")
    return {
        "tier": normalized_tier,
        "suburb": normalized_suburb,
        "interval": normalized_interval,
        "amount_cents": int(plan.get("annual_amount_cents") if normalized_interval == "year" else plan["amount_cents"]),
        "name": str(plan["name"]),
        "currency": _default_currency(),
    }


def _consent_ok(trainer: Dict[str, Any], consent_granted: bool, consent_version: str) -> bool:
    if consent_granted:
        return str(consent_version or "") == billing_terms_version()
    return bool(trainer.get("billing_terms_accepted_at")) and str(trainer.get("billing_terms_version") or "") == billing_terms_version()


async def provision_trainer_billing_profile(
    db,
    trainer: Dict[str, Any],
    *,
    consent_granted: bool,
    consent_version: str = "",
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

    if not checkout_enabled():
        status.update({"billing_profile_status": "billing_activation_required"})
        await db.trainers.update_one({"id": trainer_id}, {"$set": status})
        return status

    if not _consent_ok(trainer, consent_granted, consent_version):
        status.update({"billing_profile_status": "consent_required"})
        await db.trainers.update_one({"id": trainer_id}, {"$set": status})
        return status

    if consent_granted:
        status.update(
            {
                "billing_terms_accepted_at": now_iso(),
                "billing_terms_version": billing_terms_version(),
            }
        )

    if not email:
        status.update({"billing_profile_status": "missing_email"})
        await db.trainers.update_one({"id": trainer_id}, {"$set": status})
        return status

    customer_id = (trainer.get("stripe_customer_id") or "").strip()
    if not billing_enabled():
        status.update({"billing_profile_status": "stripe_unconfigured"})
        await db.trainers.update_one({"id": trainer_id}, {"$set": status})
        return status

    try:
        s = _client()
        if not customer_id:
            customer = s.Customer.create(
                name=(trainer.get("name") or "").strip() or "Trainer",
                email=email,
                metadata={
                    "trainer_id": str(trainer_id or ""),
                    "region": str(trainer.get("region") or ""),
                },
            )
            customer_id = str(_stripe_value(customer, "id") or "")
        if not customer_id:
            raise RuntimeError("stripe_customer_missing_id")

        status.update({"stripe_customer_id": customer_id, "billing_profile_status": "ready"})
        abn = _normalized_abn(trainer.get("abn"))
        if bool(trainer.get("abn_verified")) and len(abn) == 11 and not trainer.get("stripe_customer_tax_id"):
            tax_id = s.Customer.create_tax_id(customer_id, type="au_abn", value=abn)
            status["stripe_customer_tax_id"] = str(_stripe_value(tax_id, "id") or "")
    except Exception as exc:  # noqa: BLE001
        status.update(
            {
                "billing_profile_status": "stripe_error",
                "billing_profile_error": str(exc)[:240],
            }
        )

    await db.trainers.update_one({"id": trainer_id}, {"$set": status})
    return status


def _subscription_metadata(*, trainer_id: str, plan: Dict[str, Any], reservation_id: str = "") -> Dict[str, str]:
    return {
        "trainer_id": str(trainer_id),
        "tier": str(plan["tier"]),
        "suburb": str(plan["suburb"]),
        "interval": str(plan["interval"]),
        "reservation_id": str(reservation_id or ""),
    }


async def create_checkout_session(
    db,
    trainer: Dict[str, Any],
    *,
    tier: str,
    suburb: Optional[str] = None,
    interval: str = "month",
    consent_granted: bool = False,
    consent_version: str = "",
    idempotency_key: Optional[str] = None,
    reservation_id: str = "",
    billing_return_url: str = "",
) -> Dict[str, Any]:
    """Create a hosted Stripe Checkout session for one validated DTD plan.

    The caller is responsible for trainer authorisation. This function never
    fabricates a checkout URL when Stripe is not configured.
    """
    plan = subscription_plan(tier=tier, suburb=suburb, interval=interval)
    trainer_id = str(trainer.get("id") or "")
    if not trainer_id:
        raise ValueError("trainer_id_required")
    if not checkout_enabled():
        return {"ok": False, "code": "billing_activation_required", "plan": plan}

    profile = await provision_trainer_billing_profile(
        db,
        trainer,
        consent_granted=consent_granted,
        consent_version=consent_version,
    )
    if profile.get("billing_profile_status") != "ready":
        return {"ok": False, "code": str(profile.get("billing_profile_status") or "billing_profile_unavailable"), "plan": plan}

    metadata = _subscription_metadata(trainer_id=trainer_id, plan=plan, reservation_id=reservation_id)
    metadata["billing_terms_version"] = billing_terms_version()
    trial = trial_status(trainer)
    subscription_data: Dict[str, Any] = {"metadata": metadata}
    if plan["tier"] == "pro" and bool(trial.get("eligible")):
        subscription_data["trial_period_days"] = pro_trial_days()
        metadata["pro_trial_cohort_anchor_at"] = str(trial.get("cohort_anchor_at") or "")
    base_url = (os.environ.get("FRONTEND_BASE_URL") or "http://127.0.0.1:3001").strip().rstrip("/")
    return_url = str(billing_return_url or "").strip() or f"{base_url}/trainer/billing"
    return_separator = "&" if "?" in return_url else "?"
    try:
        session = _client().checkout.Session.create(
            mode="subscription",
            customer=str(profile["stripe_customer_id"]),
            client_reference_id=trainer_id,
            line_items=[
                {
                    "price_data": {
                        "currency": plan["currency"],
                        "unit_amount": plan["amount_cents"],
                        "tax_behavior": "inclusive",
                        "recurring": {"interval": plan["interval"]},
                        "product_data": {"name": plan["name"], "metadata": metadata},
                    },
                    "quantity": 1,
                }
            ],
            metadata=metadata,
            subscription_data=subscription_data,
            success_url=f"{return_url}{return_separator}checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{return_url}{return_separator}checkout=cancelled",
            idempotency_key=idempotency_key or f"dtd-checkout:{trainer_id}:{plan['tier']}:{plan['suburb'] or 'all'}",
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": "stripe_error", "detail": str(exc)[:240], "plan": plan}

    session_id = str(_stripe_value(session, "id") or "")
    session_url = str(_stripe_value(session, "url") or "")
    if not session_id or not session_url:
        return {"ok": False, "code": "stripe_checkout_response_invalid", "plan": plan}
    return {
        "ok": True,
        "session_id": session_id,
        "url": session_url,
        "plan": plan,
        "customer_id": str(profile["stripe_customer_id"]),
        "pro_trial_offered": "trial_period_days" in subscription_data,
    }


async def create_customer_portal_session(trainer: Dict[str, Any], *, return_url: str = "") -> Dict[str, Any]:
    customer_id = str(trainer.get("stripe_customer_id") or "").strip()
    if not customer_id:
        return {"ok": False, "code": "stripe_customer_missing"}
    if not checkout_enabled():
        return {"ok": False, "code": "billing_activation_required"}
    base_url = (os.environ.get("FRONTEND_BASE_URL") or "http://127.0.0.1:3001").strip().rstrip("/")
    resolved_return_url = str(return_url or "").strip() or f"{base_url}/trainer/billing"
    try:
        session = _client().billing_portal.Session.create(customer=customer_id, return_url=resolved_return_url)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": "stripe_error", "detail": str(exc)[:240]}
    url = str(_stripe_value(session, "url") or "")
    return {"ok": bool(url), "url": url, "code": "" if url else "stripe_portal_response_invalid"}


async def refund_subscription_payment(*, payment_intent_id: str, idempotency_key: str) -> Dict[str, Any]:
    payment_intent_id = str(payment_intent_id or "").strip()
    if not payment_intent_id:
        return {"ok": False, "code": "payment_intent_required"}
    if not billing_enabled():
        return {"ok": False, "code": "stripe_unconfigured"}
    try:
        refund = _client().Refund.create(payment_intent=payment_intent_id, idempotency_key=idempotency_key)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": "stripe_error", "detail": str(exc)[:240]}
    refund_id = str(_stripe_value(refund, "id") or "")
    status = str(_stripe_value(refund, "status") or "")
    return {"ok": bool(refund_id), "refund_id": refund_id, "status": status, "code": "" if refund_id else "stripe_refund_response_invalid"}


def subscription_update_for_event(event_type: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    """Map subscription lifecycle webhooks to DTD trainer entitlement fields."""
    metadata = subscription_metadata(obj)
    tier = str(metadata.get("tier") or "").strip().lower()
    subscription_id = str(obj.get("id") or subscription_id_for_event(obj) or "")
    customer_id = str(obj.get("customer") or "")
    status = str(obj.get("status") or "").strip().lower()
    now = now_iso()

    if event_type == "checkout.session.completed":
        return {
            "stripe_checkout_session_id": str(obj.get("id") or ""),
            "stripe_subscription_id": str(obj.get("subscription") or ""),
            "stripe_customer_id": customer_id,
            "subscription_checkout_status": str(obj.get("status") or "completed"),
            "subscription_checkout_completed_at": now,
        }
    if event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.resumed"}:
        if tier not in SUBSCRIPTION_PLANS:
            return {"subscription_status": status or "unknown", "subscription_last_event_at": now, "subscription_metadata_error": "unsupported_or_missing_tier"}
        updates: Dict[str, Any] = {
            "stripe_subscription_id": subscription_id,
            "stripe_customer_id": customer_id,
            "subscription_status": status,
            "subscription_tier": tier,
            "subscription_suburb": str(metadata.get("suburb") or ""),
            "subscription_interval": str(metadata.get("interval") or "month"),
            "subscription_last_event_at": now,
            "sponsor_reservation_id": str(metadata.get("reservation_id") or ""),
        }
        if status in ACTIVE_SUBSCRIPTION_STATUSES:
            updates["tier"] = tier
            updates["subscription_active_at"] = now
            if tier == "pro" and status == "trialing":
                trial_start = _stripe_timestamp_iso(obj.get("trial_start"))
                trial_end = _stripe_timestamp_iso(obj.get("trial_end"))
                if trial_start and trial_end:
                    updates.update(
                        {
                            "pro_trial_started_at": trial_start,
                            "pro_trial_ends_at": trial_end,
                            "pro_trial_consumed_at": now,
                        }
                    )
        elif status in TERMINAL_NONPAYMENT_SUBSCRIPTION_STATUSES:
            updates["tier"] = "claimed"
            updates["subscription_ended_at"] = now
        return updates
    if event_type in {"customer.subscription.deleted", "customer.subscription.paused"}:
        return {
            "stripe_subscription_id": subscription_id,
            "stripe_customer_id": customer_id,
            "subscription_status": "canceled" if event_type.endswith("deleted") else "paused",
            "subscription_tier": tier,
            "tier": "claimed",
            "sponsor_reservation_id": str(metadata.get("reservation_id") or ""),
            "subscription_ended_at": now,
        }
    if event_type in {"invoice.paid", "invoice.payment_succeeded"}:
        return {
            "subscription_billing_status": "paid",
            "subscription_paid_at": now,
            "subscription_last_invoice_id": str(obj.get("id") or ""),
            "subscription_last_payment_intent_id": str(obj.get("payment_intent") or ""),
        }
    if event_type == "invoice.payment_failed":
        return {"subscription_billing_status": "payment_failed", "subscription_payment_failed_at": now, "subscription_last_invoice_id": str(obj.get("id") or "")}
    if event_type == "charge.refunded":
        return {
            "subscription_status": "refunded",
            "subscription_billing_status": "refunded",
            "subscription_tier": tier,
            "stripe_subscription_id": str(obj.get("subscription") or metadata.get("subscription_id") or ""),
            "sponsor_reservation_id": str(metadata.get("reservation_id") or ""),
            "tier": "claimed",
            "subscription_ended_at": now,
        }
    return {}


def subscription_trainer_id(event_type: str, obj: Dict[str, Any]) -> str:
    metadata = subscription_metadata(obj)
    trainer_id = str(metadata.get("trainer_id") or "")
    if trainer_id:
        return trainer_id
    if event_type == "checkout.session.completed":
        return str(obj.get("client_reference_id") or "")
    return ""


def subscription_metadata(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Read DTD metadata from direct or modern Stripe invoice nesting."""
    direct = obj.get("metadata") or {}
    if direct:
        return direct
    subscription_details = obj.get("subscription_details") or {}
    nested = subscription_details.get("metadata") or {}
    if nested:
        return nested
    parent = obj.get("parent") or {}
    parent_details = parent.get("subscription_details") or {}
    return parent_details.get("metadata") or {}


def subscription_id_for_event(obj: Dict[str, Any]) -> str:
    direct = str(obj.get("subscription") or "")
    if direct:
        return direct
    parent = obj.get("parent") or {}
    details = parent.get("subscription_details") or obj.get("subscription_details") or {}
    return str(details.get("subscription") or "")


async def bill_intro(db, trainer: Dict[str, Any], intro: Dict[str, Any]) -> Dict[str, Any]:
    """Decommissioned in P1-B. Introductions are not billed."""
    return {"billed": False, "billing_collection_status": "decommissioned", "fee_cents": 0}


def construct_webhook_event(payload: bytes, signature: str) -> Dict[str, Any]:
    if not webhook_enabled():
        raise RuntimeError("stripe_webhook_unconfigured")
    if not signature:
        raise RuntimeError("stripe_signature_missing")
    s = _client()
    event = s.Webhook.construct_event(payload=payload, sig_header=signature, secret=_webhook_secret())
    return event


def extract_invoice_id(event_type: str, obj: Dict[str, Any]) -> str:
    if event_type.startswith("invoice."):
        return str(obj.get("id") or "")
    if event_type.startswith("charge."):
        return str(obj.get("invoice") or "")
    if event_type.startswith("credit_note."):
        return str(obj.get("invoice") or "")
    return ""


def invoice_id_from_charge(charge_id: str) -> str:
    charge_id = (charge_id or "").strip()
    if not charge_id or not billing_enabled():
        return ""
    try:
        s = _client()
        charge = s.Charge.retrieve(charge_id)
        return str((charge or {}).get("invoice") or "")
    except Exception:  # noqa: BLE001
        return ""


def billing_updates_for_event(event_type: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    if event_type in {"invoice.paid", "invoice.payment_succeeded"}:
        return {
            "billing_collection_status": "paid",
            "stripe_invoice_status": "paid",
            "stripe_invoice_paid_at": now_iso(),
        }
    if event_type == "invoice.payment_failed":
        return {
            "billing_collection_status": "payment_failed",
            "stripe_invoice_status": str(obj.get("status") or "open"),
        }
    if event_type == "invoice.sent":
        return {
            "billing_collection_status": "invoice_sent",
            "stripe_invoice_status": str(obj.get("status") or "open"),
        }
    if event_type == "invoice.finalized":
        return {
            "billing_collection_status": "invoice_finalized",
            "stripe_invoice_status": str(obj.get("status") or "open"),
        }
    if event_type == "invoice.marked_uncollectible":
        return {
            "billing_collection_status": "uncollectible",
            "stripe_invoice_status": str(obj.get("status") or "uncollectible"),
        }
    if event_type == "invoice.voided":
        return {
            "billing_collection_status": "waived",
            "stripe_invoice_status": str(obj.get("status") or "void"),
        }
    if event_type == "charge.refunded":
        return {
            "billing_collection_status": "refunded",
            "stripe_invoice_status": "refunded",
        }
    if event_type in {"charge.dispute.created", "charge.dispute.funds_withdrawn"}:
        return {
            "billing_collection_status": "disputed",
            "stripe_invoice_status": "disputed",
        }
    if event_type in {"charge.dispute.closed", "charge.dispute.funds_reinstated"}:
        return {
            "billing_collection_status": "dispute_resolved",
            "stripe_invoice_status": "dispute_resolved",
        }
    return {}
