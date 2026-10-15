"""Sanitised provider-control status for the authenticated Operations Console.

This module deliberately never reads, returns, or validates credential values.
It distinguishes a runtime configuration check from runtime operational health
and evidence that a provider's management recovery path or independent alert route
has been tested.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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


def _configured(env_name: str, env: Optional[Dict[str, str]] = None) -> bool:
    # Only inspect presence. Never return, log, derive from, or validate the value.
    target = env if env is not None else os.environ
    return bool((target.get(env_name) or "").strip())


def snapshot(env: Optional[Dict[str, str]] = None, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return an authenticated, secret-free control-plane readiness snapshot.

    Differentiates:
    - configured: required environment variable present
    - operational_status: 'operational', 'degraded', 'unavailable', or 'unknown'
    - governance_status: 'compliant' or 'pending'
    """
    checked_at = _now_iso()
    t = telemetry or {}
    rows: List[Dict[str, Any]] = []

    for definition in _PROVIDERS:
        p_id = definition["id"]
        disabled = bool(definition.get("intentionally_disabled"))
        configured = _configured(str(definition["runtime_env"]), env=env)
        runtime_status = "intentionally_disabled" if disabled else ("configuration_detected" if configured else "configuration_missing")
        autonomous = "not_applicable" if disabled else "not_accepted"
        governance_status = "not_applicable" if disabled else ("pending" if autonomous == "not_accepted" else "compliant")

        # Evaluate operational status from telemetry
        operational_status = "unknown"
        operational_reason = ""

        if disabled:
            operational_status = "disabled"
            operational_reason = "Intentionally disabled by design."
        elif not configured:
            operational_status = "unavailable"
            operational_reason = f"Runtime configuration {definition['runtime_env']} is missing."
        else:
            # Configured: evaluate available runtime evidence
            if p_id == "atlas":
                if t.get("atlas_connected") is False:
                    operational_status = "unavailable"
                    operational_reason = "MongoDB connection ping failed or database unreachable."
                elif t.get("atlas_connected") is True:
                    operational_status = "operational"
                    operational_reason = "Database client connected and responsive."
                else:
                    operational_status = "unknown"
                    operational_reason = "Configuration present; no recent database operation signal recorded in observation window."
            elif p_id == "resend":
                r_status = str(t.get("resend_status") or "").lower()
                if r_status in {"auth_failure", "unauthorized", "invalid_key"}:
                    operational_status = "unavailable"
                    operational_reason = "Resend API authentication failed (HTTP 401/403)."
                elif r_status in {"service_error", "outage"}:
                    operational_status = "unavailable"
                    operational_reason = "Resend API returned persistent delivery errors (HTTP 5xx)."
                elif r_status in {"rate_limited", "throttled"}:
                    operational_status = "degraded"
                    operational_reason = "Resend API rate limit reached (HTTP 429)."
                elif r_status in {"ok", "operational"}:
                    operational_status = "operational"
                    operational_reason = "Recent email dispatches delivered successfully."
                else:
                    operational_status = "unknown"
                    operational_reason = "Configuration present; no recent delivery telemetry in observation window."
            elif p_id == "stripe_api":
                s_status = str(t.get("stripe_api_status") or "").lower()
                if s_status in {"auth_failure", "invalid_key"}:
                    operational_status = "unavailable"
                    operational_reason = "Stripe API authentication failed (invalid secret key)."
                elif s_status in {"connection_error", "unreachable"}:
                    operational_status = "unavailable"
                    operational_reason = "Stripe API network connection unreachable."
                elif s_status in {"degraded", "rate_limited"}:
                    operational_status = "degraded"
                    operational_reason = "Stripe API responding with intermittent rate limits or latency."
                elif s_status in {"ok", "operational"}:
                    operational_status = "operational"
                    operational_reason = "Recent Stripe API transactions succeeded."
                else:
                    operational_status = "unknown"
                    operational_reason = "Configuration present; no recent Stripe API calls in observation window."
            elif p_id == "stripe_webhook":
                w_status = str(t.get("stripe_webhook_status") or "").lower()
                if w_status in {"signature_verification_failed", "bad_signature"}:
                    operational_status = "degraded"
                    operational_reason = "Stripe webhook signature verification failed; events cannot be ingested."
                elif w_status in {"ok", "operational"}:
                    operational_status = "operational"
                    operational_reason = "Recent Stripe webhook signed and verified successfully."
                else:
                    operational_status = "unknown"
                    operational_reason = "Configuration present; no recent webhook deliveries recorded."
            elif p_id == "abr":
                abr_st = str(t.get("abr_status") or "").lower()
                if abr_st in {"service_unavailable", "network_error"}:
                    operational_status = "unavailable"
                    operational_reason = "ABR Web Services unavailable or network timeout."
                elif abr_st in {"maintenance", "degraded"}:
                    operational_status = "degraded"
                    operational_reason = "ABR Web Services reporting maintenance or degraded response."
                elif abr_st in {"ok", "operational"}:
                    operational_status = "operational"
                    operational_reason = "Recent ABR lookup verified successfully."
                else:
                    operational_status = "unknown"
                    operational_reason = "Configuration present; no recent ABN lookup telemetry."
            elif p_id == "sentry":
                sen_st = str(t.get("sentry_status") or "").lower()
                if sen_st in {"init_failed", "error"}:
                    operational_status = "unavailable"
                    operational_reason = "Sentry SDK failed initialization."
                elif sen_st in {"verified", "event_ingested"}:
                    operational_status = "operational"
                    operational_reason = "Sentry client initialized and event ingestion verified."
                else:
                    operational_status = "unknown"
                    operational_reason = "Configuration present; production canary event unverified."

        rows.append(
            {
                "id": p_id,
                "provider": definition["provider"],
                "purpose": definition["purpose"],
                "runtime_status": runtime_status,
                "operational_status": operational_status,
                "operational_reason": operational_reason,
                "governance_status": governance_status,
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
                "runtime_env": definition["runtime_env"],
            }
        )

    action_required = [
        row for row in rows
        if row["operational_status"] in {"unavailable", "degraded"} or row["autonomy_status"] == "not_accepted"
    ]
    return {
        "status": "action_required" if action_required else "ok",
        "checked_at": checked_at,
        "summary": {
            "providers_total": len(rows),
            "providers_operational": sum(row["operational_status"] == "operational" for row in rows),
            "providers_degraded": sum(row["operational_status"] == "degraded" for row in rows),
            "providers_unavailable": sum(row["operational_status"] == "unavailable" for row in rows),
            "providers_unknown": sum(row["operational_status"] == "unknown" for row in rows),
            "providers_governance_pending": sum(row["governance_status"] == "pending" for row in rows),
            "providers_missing_runtime_configuration": sum(row["runtime_status"] == "configuration_missing" for row in rows),
        },
        "providers": rows,
    }


def cases(provider_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build bounded review cases; these remain review-state-only in /ops.

    Distinguishes:
    1. Active operational failures (operational_status == 'unavailable'):
       Severity high/medium, state 'detected' -> Needs Review.
    2. Active operational degradations (operational_status == 'degraded'):
       Severity medium, state 'detected' -> Needs Review.
    3. Architecture governance requirements (operational_status in {'operational', 'unknown'} and governance_status == 'pending'):
       Severity low, state 'monitoring' -> Monitoring.
    """
    now = provider_snapshot.get("checked_at") or _now_iso()
    output: List[Dict[str, Any]] = []

    for row in provider_snapshot.get("providers") or []:
        op_status = row.get("operational_status")
        gov_status = row.get("governance_status")

        # Fallback/normalization for raw or legacy snapshots lacking explicit operational fields
        if op_status is None:
            if row.get("runtime_status") == "configuration_missing":
                op_status = "unavailable"
            elif row.get("runtime_status") == "runtime_disabled":
                op_status = "disabled"
            else:
                op_status = "operational"

        if gov_status is None:
            if row.get("autonomy_status") != "accepted":
                gov_status = "pending"
            else:
                gov_status = "compliant"

        if op_status == "disabled":
            continue

        if op_status == "unavailable":
            # Active operational outage / failure: missing configuration OR runtime failure
            reason_msg = row.get("operational_reason") or f"Required runtime secret/env {row.get('runtime_env', '')} is missing."
            if row.get("runtime_status") == "configuration_missing":
                title = f"{row['provider']} runtime configuration missing"
            else:
                title = f"{row['provider']} unavailable · {reason_msg}"
            summary = f"{reason_msg} {row['degraded_behavior']}"
            severity = row["severity"]
            state = "detected"
            risk_codes = ["provider_unavailable", row.get("runtime_status", "unknown")]
            next_step = f"Investigate {row['provider']} failure: {reason_msg}"
            case_type = "provider_operational_case"
        elif op_status == "degraded":
            # Active operational degradation
            reason_msg = row.get("operational_reason") or "Reduced functionality detected at runtime."
            title = f"{row['provider']} degraded · {reason_msg}"
            summary = f"{reason_msg} {row['degraded_behavior']}"
            severity = "medium"
            state = "detected"
            risk_codes = ["provider_degraded", row.get("runtime_status", "unknown")]
            next_step = f"Inspect telemetry and recovery options for {row['provider']}."
            case_type = "provider_operational_case"
        elif gov_status == "pending":
            # Static architectural governance requirement (runtime is active or unknown, not actively failing)
            case_type = "provider_governance_case"
            title = f"{row['provider']} control path needs evidence"
            summary = row["next_review"]
            severity = "low"
            state = "monitoring"
            risk_codes = ["provider_governance_incomplete", row.get("runtime_status", "unknown")]
            next_step = row["next_review"]
        else:
            # Operational and compliant -> no case needed
            continue

        output.append(
            {
                "case_id": f"provider:{row['id']}",
                "case_type": case_type,
                "canonical_user_type": "Autonomous system actor",
                "workflow": "provider resilience",
                "entity_type": "provider",
                "entity_id": row["id"],
                "title": title,
                "summary": summary,
                "severity": severity,
                "state": state,
                "owner": "",
                "detected_at": now,
                "last_updated_at": now,
                "source_refs": [{"kind": "provider_registry", "id": row["id"]}],
                "risk_reason_codes": risk_codes,
                "recommended_next_step": next_step,
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Runtime configuration", "value": row.get("runtime_status", "unknown")},
                    {"label": "Operational status", "value": row.get("operational_status", op_status)},
                    {"label": "Operational diagnostic", "value": row.get("operational_reason") or "None"},
                    {"label": "Governance status", "value": row.get("governance_status", gov_status)},
                    {"label": "Management recovery", "value": row.get("management_recovery_status", "not_evidenced")},
                    {"label": "Safe verification", "value": row.get("safe_verification_status", "not_evidenced")},
                    {"label": "Independent alert", "value": row.get("independent_alert_status", "not_evidenced")},
                    {"label": "Recovery owner", "value": row.get("recovery_owner", "Owner")},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    return output
