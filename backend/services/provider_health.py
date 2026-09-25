"""Sanitised provider-control status for the authenticated Operations Console.

This module deliberately never reads, returns, or validates credential values.
It distinguishes a runtime configuration check from evidence that a provider,
its management recovery path, or its independent alert route has been tested.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List


_PROVIDERS = (
    {
        "id": "atlas",
        "provider": "MongoDB Atlas",
        "purpose": "Directory database",
        "runtime_env": "MONGO_URL",
        "degraded_behavior": "The API cannot safely serve database-backed work.",
        "known_gap": "Static egress and a least-privilege database user are not yet evidenced.",
        "severity": "high",
    },
    {
        "id": "resend",
        "provider": "Resend",
        "purpose": "Transactional email",
        "runtime_env": "RESEND_API_KEY",
        "degraded_behavior": "Outbound notifications are recorded as failed; no delivery is claimed.",
        "known_gap": "A separate provider-management recovery identity and controlled sending-key rotation are not yet evidenced.",
        "severity": "medium",
    },
    {
        "id": "stripe_api",
        "provider": "Stripe API",
        "purpose": "Trainer billing and subscription lifecycle",
        "runtime_env": "STRIPE_SECRET_KEY",
        "degraded_behavior": "Commercial mutations fail closed when Stripe is unavailable or gated.",
        "known_gap": "Least-privilege runtime-key rotation and management recovery are not yet evidenced.",
        "severity": "medium",
    },
    {
        "id": "stripe_webhook",
        "provider": "Stripe webhook",
        "purpose": "Signed billing-event intake",
        "runtime_env": "STRIPE_WEBHOOK_SECRET",
        "degraded_behavior": "Billing-event processing is held for review rather than treated as complete.",
        "known_gap": "A provider-signed delivery to the current Cloud Run endpoint is not yet evidenced.",
        "severity": "high",
    },
    {
        "id": "abr",
        "provider": "Australian Business Register",
        "purpose": "ABN verification",
        "runtime_env": "ABR_GUID",
        "degraded_behavior": "Identity verification is marked degraded or held; publication is not silently validated.",
        "known_gap": "Government-issued GUID ownership/recovery and a safe runtime-value verification path are not yet evidenced.",
        "severity": "medium",
    },
    {
        "id": "sentry",
        "provider": "Sentry",
        "purpose": "Application error intake",
        "runtime_env": "SENTRY_DSN",
        "degraded_behavior": "Sentry events are unavailable when the DSN is missing or initialization fails; no alerting is claimed.",
        "known_gap": "A production canary event and independent alert-route verification are still required before accepting Sentry as autonomous.",
        "severity": "low",
    },
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _configured(env_name: str) -> bool:
    # Only inspect presence. Never return, log, derive from, or validate the value.
    return bool((os.environ.get(env_name) or "").strip())


def snapshot() -> Dict[str, Any]:
    """Return an authenticated, secret-free control-plane readiness snapshot."""
    checked_at = _now_iso()
    rows: List[Dict[str, Any]] = []
    for definition in _PROVIDERS:
        disabled = bool(definition.get("intentionally_disabled"))
        configured = _configured(str(definition["runtime_env"]))
        runtime_status = "intentionally_disabled" if disabled else ("configuration_detected" if configured else "configuration_missing")
        autonomous = "not_applicable" if disabled else "not_accepted"
        rows.append(
            {
                "id": definition["id"],
                "provider": definition["provider"],
                "purpose": definition["purpose"],
                "runtime_status": runtime_status,
                "management_recovery_status": "not_applicable" if disabled else "not_evidenced",
                "safe_verification_status": "not_applicable" if disabled else "not_evidenced",
                "independent_alert_status": "not_applicable" if disabled else "not_evidenced",
                "autonomy_status": autonomous,
                "last_verified_at": None,
                "configuration_checked_at": checked_at,
                "next_review": definition["known_gap"],
                "degraded_behavior": definition["degraded_behavior"],
                "recovery_owner": "Owner",
                "severity": definition["severity"],
            }
        )
    action_required = [row for row in rows if row["autonomy_status"] == "not_accepted"]
    return {
        "status": "action_required" if action_required else "ok",
        "checked_at": checked_at,
        "summary": {
            "providers_total": len(rows),
            "providers_not_accepted": len(action_required),
            "providers_missing_runtime_configuration": sum(row["runtime_status"] == "configuration_missing" for row in rows),
        },
        "providers": rows,
    }


def cases(provider_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build bounded review cases; these remain review-state-only in /ops."""
    now = provider_snapshot.get("checked_at") or _now_iso()
    output: List[Dict[str, Any]] = []
    for row in provider_snapshot.get("providers") or []:
        if row.get("autonomy_status") != "not_accepted":
            continue
        output.append(
            {
                "case_id": f"provider:{row['id']}",
                "case_type": "provider_resilience_case",
                "canonical_user_type": "Autonomous system actor",
                "workflow": "provider resilience",
                "entity_type": "provider",
                "entity_id": row["id"],
                "title": f"{row['provider']} control path needs evidence",
                "summary": row["next_review"],
                "severity": row["severity"],
                "state": "detected",
                "owner": "",
                "detected_at": now,
                "last_updated_at": now,
                "source_refs": [{"kind": "provider_registry", "id": row["id"]}],
                "risk_reason_codes": ["provider_not_autonomous", row["runtime_status"]],
                "recommended_next_step": row["next_review"],
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Runtime", "value": row["runtime_status"]},
                    {"label": "Management recovery", "value": row["management_recovery_status"]},
                    {"label": "Safe verification", "value": row["safe_verification_status"]},
                    {"label": "Independent alert", "value": row["independent_alert_status"]},
                    {"label": "Recovery owner", "value": row["recovery_owner"]},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )
    return output
