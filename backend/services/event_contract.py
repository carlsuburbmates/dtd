from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

# Explicit owner waitlist event allowlist for prelaunch funnel tracking.
OWNER_WAITLIST_EVENT_NAMES: Tuple[str, ...] = (
    "owner_waitlist_started",
    "owner_waitlist_submitted",
    "owner_waitlist_duplicate",
    "owner_waitlist_rejected",
)

# Required fields by event type. Missing values are normalized to deterministic defaults.
OWNER_WAITLIST_REQUIRED_FIELDS: Dict[str, Tuple[str, ...]] = {
    "owner_waitlist_started": ("email_norm", "suburb_norm", "status"),
    "owner_waitlist_submitted": ("email_norm", "suburb_norm", "status", "waitlist_id"),
    "owner_waitlist_duplicate": ("email_norm", "suburb_norm", "status", "waitlist_id", "reason_codes"),
    "owner_waitlist_rejected": ("email_norm", "suburb_norm", "status", "reason_codes"),
}

ALLOWED_EVENT_NAMES = set(OWNER_WAITLIST_EVENT_NAMES)


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_reason_codes(value: Any) -> Iterable[str]:
    if isinstance(value, list):
        out = []
        for item in value:
            token = _as_text(item)
            if token:
                out.append(token)
        return out
    return []


def normalize_prelaunch_event(
    event_type: str,
    payload: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Normalize internal prelaunch event records in a deterministic way.

    Invalid event names are flagged in `contract_status`/`contract_reason_codes` but
    still emitted as records so existing paths remain non-blocking.
    """

    raw_event_type = _as_text(event_type).lower()
    normalized_payload = dict(payload or {})

    contract_status = "ok"
    contract_reason_codes = []

    if raw_event_type not in ALLOWED_EVENT_NAMES:
        contract_status = "warn"
        contract_reason_codes.append("invalid_event_name")

    # Deterministic key normalization for current waitlist event payloads.
    normalized_payload["email_norm"] = _as_text(normalized_payload.get("email_norm"))
    normalized_payload["suburb_norm"] = _as_text(normalized_payload.get("suburb_norm"))
    normalized_payload["status"] = _as_text(normalized_payload.get("status")) or "unknown"
    normalized_payload["waitlist_id"] = _as_text(normalized_payload.get("waitlist_id")) or None
    normalized_payload["reason_codes"] = list(_normalize_reason_codes(normalized_payload.get("reason_codes")))

    required_fields = OWNER_WAITLIST_REQUIRED_FIELDS.get(raw_event_type, ())
    for field_name in required_fields:
        value = normalized_payload.get(field_name)
        if field_name == "reason_codes":
            if not isinstance(value, list):
                normalized_payload[field_name] = []
                contract_status = "warn"
                contract_reason_codes.append("missing_required_field:reason_codes")
            continue
        if field_name == "waitlist_id":
            if not _as_text(value):
                contract_status = "warn"
                contract_reason_codes.append("missing_required_field:waitlist_id")
            continue
        if not _as_text(value):
            contract_status = "warn"
            contract_reason_codes.append(f"missing_required_field:{field_name}")

    if not raw_event_type:
        raw_event_type = "unknown_event"
        contract_status = "warn"
        contract_reason_codes.append("empty_event_name")

    return {
        "event_type": raw_event_type,
        "payload": normalized_payload,
        "contract_status": contract_status,
        "contract_reason_codes": sorted(set(contract_reason_codes)),
    }
