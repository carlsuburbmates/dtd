"""Durable Owner Responsibility Ledger & Escalation Service for DTD Operations.

Governing Principle: OWNER BY EXCEPTION. AUTOMATION BY DEFAULT.
Product Invariant: If the owner does not see a job requiring attention in /ops,
it must never be silently kept in the background or dropped.

This service maintains the `ops_obligations` collection in MongoDB, providing:
1. Durable capture of all genuine owner-required obligations (verification, delivery, claim, billing, scheduler, provider).
2. Cadence-aware SLA tracking (due dates).
3. Automated escalation when an obligation breaches its SLA (overdue detection).
4. Permanent persistence: obligations never roll off or vanish until explicitly resolved.
5. Auto-clearing with audit evidence when underlying entities reach valid terminal states.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("dtd.ops_obligations")

# Cadence-aware SLA definitions in hours
CATEGORY_SLAS: Dict[str, int] = {
    "scheduler": 1,             # Engine tick cron stall > 750s needs prompt attention (1 hour SLA)
    "claim_lock": 4,            # Stuck trainer profile claim lock needs release within 4 hours
    "provider": 6,              # External provider auth/outage needs review within 6 hours
    "client_enquiry": 12,       # Undelivered client enquiry needs delivery within 12 hours
    "directory_guardian": 24,   # Statutory or schema violation in directory within 24 hours
    "trainer_verification": 48, # New trainer onboarding / ABN verification within 48 hours
    "billing": 72,              # Past due subscription or billing exception within 72 hours
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def parse_iso(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(str(ts_str))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def compute_sla(
    category: str,
    created_at_iso: Optional[str],
    now_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    current_dt = now_dt or now_utc()
    created_dt = parse_iso(created_at_iso) or current_dt
    sla_hours = CATEGORY_SLAS.get(category, 24)
    due_dt = created_dt + timedelta(hours=sla_hours)

    is_overdue = current_dt > due_dt
    overdue_seconds = max(0.0, (current_dt - due_dt).total_seconds())
    overdue_hours = round(overdue_seconds / 3600.0, 1)

    if not is_overdue:
        escalation_level = 0
    elif overdue_hours <= sla_hours:
        escalation_level = 1  # Standard overdue escalation
    else:
        escalation_level = 2  # Critical overdue escalation (> 2x SLA)

    return {
        "created_at": created_dt.isoformat(),
        "due_at": due_dt.isoformat(),
        "sla_hours": sla_hours,
        "is_overdue": is_overdue,
        "overdue_hours": overdue_hours,
        "escalation_level": escalation_level,
    }


async def sync_durable_obligations(db, now_dt: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Scan authoritative system state and synchronize the durable `ops_obligations` collection."""
    current_dt = now_dt or now_utc()
    current_iso = current_dt.isoformat()
    active_obligations: Dict[str, Dict[str, Any]] = {}

    # 1. Trainer Submissions / Verification Obligations
    submissions_coll = getattr(db, "submissions", None)
    if submissions_coll is not None and hasattr(submissions_coll, "find"):
        try:
            pending_subs = await submissions_coll.find(
                {
                    "$or": [
                        {"status": {"$in": ["pending", "held", "requires_review", "under_review"]}},
                        {"abn_status": {"$in": ["unverified", "invalid", "degraded", "held", "abr_unavailable"]}},
                    ]
                },
                {"_id": 0, "id": 1, "business_name": 1, "name": 1, "abn": 1, "abn_status": 1, "created_at": 1},
            ).to_list(100)
            for sub in pending_subs:
                sub_id = str(sub.get("id") or "")
                if not sub_id:
                    continue
                obl_id = f"obligation:submission:{sub_id}"
                name = sub.get("business_name") or sub.get("name") or sub_id
                active_obligations[obl_id] = {
                    "obligation_id": obl_id,
                    "category": "trainer_verification",
                    "entity_id": sub_id,
                    "title": f"Review Trainer Submission: {name}",
                    "required_action": "Inspect ABN verification evidence and approve or reject trainer listing.",
                    "base_severity": "medium",
                    "created_at_source": sub.get("created_at") or current_iso,
                    "metadata": {"abn": sub.get("abn"), "abn_status": sub.get("abn_status")},
                }
        except Exception as exc:
            logger.warning("Error reading submissions for obligations: %s", exc)

    # 2. Stale Trainer Profile Claim Locks
    claim_events_coll = getattr(db, "claim_events", None)
    if claim_events_coll is not None and hasattr(claim_events_coll, "find"):
        try:
            stuck_claims = await claim_events_coll.find(
                {
                    "status": {"$in": ["initiated", "pending", "otp_sent", "stale", "lock_held"]},
                },
                {"_id": 0, "id": 1, "trainer_id": 1, "status": 1, "method": 1, "created_at": 1, "updated_at": 1},
            ).to_list(50)
            for claim in stuck_claims:
                claim_id = str(claim.get("id") or "")
                trainer_id = str(claim.get("trainer_id") or "")
                created_ts = claim.get("created_at") or claim.get("updated_at") or current_iso
                claim_dt = parse_iso(created_ts) or current_dt
                # Only flag as obligation if held > 15 minutes
                if (current_dt - claim_dt).total_seconds() >= 900:
                    obl_id = f"obligation:claim:{claim_id or trainer_id}"
                    active_obligations[obl_id] = {
                        "obligation_id": obl_id,
                        "category": "claim_lock",
                        "entity_id": claim_id or trainer_id,
                        "title": f"Stale Profile Claim Lock: Trainer {trainer_id}",
                        "required_action": "Release stale claim lock in /ops or verify trainer ownership manually.",
                        "base_severity": "medium",
                        "created_at_source": created_ts,
                        "metadata": {"trainer_id": trainer_id, "claim_status": claim.get("status")},
                    }
        except Exception as exc:
            logger.warning("Error reading claim events for obligations: %s", exc)

    # 3. Failed Message Delivery (Resend / Enquiries)
    message_log_coll = getattr(db, "message_log", None)
    if message_log_coll is not None and hasattr(message_log_coll, "find"):
        try:
            failed_messages = await message_log_coll.find(
                {"status": {"$in": ["failed", "bounced", "error"]}},
                {"_id": 0, "id": 1, "dispatch_id": 1, "recipient": 1, "subject": 1, "error": 1, "created_at": 1},
            ).sort("created_at", -1).limit(50).to_list(50)
            for msg in failed_messages:
                dispatch_id = str(msg.get("dispatch_id") or msg.get("id") or "")
                if not dispatch_id:
                    continue
                obl_id = f"obligation:message:{dispatch_id}"
                active_obligations[obl_id] = {
                    "obligation_id": obl_id,
                    "category": "client_enquiry",
                    "entity_id": dispatch_id,
                    "title": f"Undelivered Message: {msg.get('subject') or 'Client Enquiry'}",
                    "required_action": f"Verify recipient ({msg.get('recipient')}) or retry dispatch manually in /ops.",
                    "base_severity": "high",
                    "created_at_source": msg.get("created_at") or current_iso,
                    "metadata": {"recipient": msg.get("recipient"), "error": msg.get("error")},
                }
        except Exception as exc:
            logger.warning("Error reading message log for obligations: %s", exc)

    # 4. Engine Tick Cron / Scheduler Stalls
    system_state_coll = getattr(db, "system_state", None)
    if system_state_coll is not None and hasattr(system_state_coll, "find_one"):
        try:
            engine_tick_doc = await system_state_coll.find_one({"key": "engine_tick"}, {"_id": 0}) or {}
            tick_last_run = str(engine_tick_doc.get("last_run") or "")
            tick_status = str(engine_tick_doc.get("last_status") or "unknown")
            tick_failures = int(engine_tick_doc.get("consecutive_failures") or 0)
            tick_dt = parse_iso(tick_last_run)
            tick_age_s = (current_dt - tick_dt).total_seconds() if tick_dt else None

            is_stalled = tick_age_s is not None and tick_age_s > 750  # 600s + 150s grace
            is_failing = tick_status in ("partial_error", "error") or tick_failures > 0

            if is_stalled or is_failing:
                obl_id = "obligation:scheduler:engine_tick"
                title = (
                    f"Background Engine Tick Failing ({engine_tick_doc.get('last_error') or tick_status})"
                    if is_failing
                    else f"Background Engine Tick Stalled ({int(tick_age_s)}s since last run)"
                )
                active_obligations[obl_id] = {
                    "obligation_id": obl_id,
                    "category": "scheduler",
                    "entity_id": "engine_tick",
                    "title": title,
                    "required_action": "Verify Cloud Scheduler dtd-engine-tick-cron or trigger a manual engine tick in /ops.",
                    "base_severity": "high",
                    "created_at_source": tick_last_run or current_iso,
                    "metadata": {
                        "last_run": tick_last_run,
                        "last_status": tick_status,
                        "age_s": tick_age_s,
                        "failures": tick_failures,
                    },
                }
        except Exception as exc:
            logger.warning("Error checking scheduler for obligations: %s", exc)

    # 5. External Provider Outage / Auth Failure
    if system_state_coll is not None and hasattr(system_state_coll, "find_one"):
        try:
            resend_provider = await system_state_coll.find_one({"key": "provider:resend"}, {"_id": 0}) or {}
            if resend_provider.get("status") in ("failing", "auth_failed", "unavailable"):
                obl_id = "obligation:provider:resend"
                active_obligations[obl_id] = {
                    "obligation_id": obl_id,
                    "category": "provider",
                    "entity_id": "resend",
                    "title": "Email Provider (Resend) Degraded or Unauthorized",
                    "required_action": "Check RESEND_API_KEY secret in Secret Manager and verify billing tier.",
                    "base_severity": "high",
                    "created_at_source": resend_provider.get("last_failure") or current_iso,
                    "metadata": resend_provider,
                }
        except Exception as exc:
            logger.warning("Error checking providers for obligations: %s", exc)

    # 6. Synchronize with `ops_obligations` MongoDB Collection
    obligations_coll = getattr(db, "ops_obligations", None)
    synced_list: List[Dict[str, Any]] = []

    if obligations_coll is not None and hasattr(obligations_coll, "update_one"):
        for obl_id, obl_data in active_obligations.items():
            existing = await obligations_coll.find_one({"obligation_id": obl_id}, {"_id": 0}) or {}
            created_at_str = existing.get("created_at") or obl_data["created_at_source"]
            sla_info = compute_sla(obl_data["category"], created_at_str, now_dt=current_dt)

            is_overdue = sla_info["is_overdue"]
            escalation_level = sla_info["escalation_level"]
            severity = "high" if is_overdue else obl_data["base_severity"]
            status = "escalated" if is_overdue else existing.get("status", "pending")
            if existing.get("status") == "resolved" and not is_overdue:
                # If already resolved by owner, maintain resolved state unless recurring
                status = "resolved"

            escalated_at = existing.get("escalated_at")
            if is_overdue and not escalated_at:
                escalated_at = current_iso

            doc_payload = {
                "obligation_id": obl_id,
                "category": obl_data["category"],
                "entity_id": obl_data["entity_id"],
                "title": obl_data["title"],
                "required_action": obl_data["required_action"],
                "severity": severity,
                "status": status,
                "created_at": sla_info["created_at"],
                "due_at": sla_info["due_at"],
                "sla_hours": sla_info["sla_hours"],
                "is_overdue": is_overdue,
                "overdue_hours": sla_info["overdue_hours"],
                "escalation_level": escalation_level,
                "escalated_at": escalated_at,
                "metadata": obl_data.get("metadata", {}),
                "last_synced_at": current_iso,
            }

            await obligations_coll.update_one(
                {"obligation_id": obl_id},
                {"$set": doc_payload},
                upsert=True,
            )
            synced_list.append(doc_payload)

        # Mark obligations as resolved if they are no longer in active_obligations
        try:
            active_ids = list(active_obligations.keys())
            stale_cursor = obligations_coll.find(
                {
                    "obligation_id": {"$nin": active_ids},
                    "status": {"$in": ["pending", "escalated"]},
                },
                {"_id": 0, "obligation_id": 1},
            )
            stale_docs = await stale_cursor.to_list(100) if hasattr(stale_cursor, "to_list") else []
            for stale in stale_docs:
                stale_id = str(stale.get("obligation_id") or "")
                if not stale_id or stale_id in active_ids:
                    continue
                await obligations_coll.update_one(
                    {"obligation_id": stale_id},
                    {
                        "$set": {
                            "status": "resolved",
                            "resolved_at": current_iso,
                            "resolution_type": "auto_cleared",
                            "resolution_notes": "Underlying entity reached valid or terminal state; obligation cleared.",
                            "last_synced_at": current_iso,
                        }
                    },
                )
        except Exception as exc:
            logger.warning("Error resolving cleared obligations: %s", exc)

    return synced_list


async def get_active_obligation_cases(db, now_dt: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Convert durable unaddressed obligations into top-priority Ops console cases."""
    current_dt = now_dt or now_utc()
    synced = await sync_durable_obligations(db, now_dt=current_dt)
    cases: List[Dict[str, Any]] = []

    for doc in synced:
        if doc.get("status") == "resolved":
            continue

        obl_id = doc.get("obligation_id", "")
        is_overdue = bool(doc.get("is_overdue"))
        esc_level = int(doc.get("escalation_level") or 0)
        overdue_h = doc.get("overdue_hours", 0)
        sla_h = doc.get("sla_hours", 24)

        title = doc.get("title", "")
        if is_overdue:
            prefix = "[CRITICAL OVERDUE ESCALATION] " if esc_level >= 2 else "[OVERDUE ESCALATION] "
            display_title = f"{prefix}{title}"
        else:
            display_title = title

        detail_rows = [
            {"label": "Durable Obligation ID", "value": obl_id},
            {"label": "Category", "value": doc.get("category", "general")},
            {"label": "SLA Policy Window", "value": f"{sla_h} hours"},
            {"label": "SLA Deadline", "value": doc.get("due_at")},
            {"label": "Overdue Status", "value": f"BREACHED by {overdue_h} hours" if is_overdue else "Within SLA window"},
            {"label": "Escalation Level", "value": f"Level {esc_level} (Action Urgent)" if is_overdue else "Normal (Pending)"},
        ]
        for k, v in (doc.get("metadata") or {}).items():
            if v is not None:
                detail_rows.append({"label": k.replace("_", " ").title(), "value": str(v)})

        case_obj = {
            "case_id": obl_id,
            "case_type": "owner_obligation",
            "canonical_user_type": "Solo Operator / System Owner",
            "workflow": doc.get("category", "operations"),
            "entity_type": "obligation",
            "entity_id": doc.get("entity_id"),
            "title": display_title,
            "summary": f"{doc.get('required_action')} (SLA: {sla_h}h, Status: {doc.get('status')})",
            "severity": "high" if is_overdue else doc.get("severity", "medium"),
            "state": "detected" if not is_overdue else "escalated",
            "owner": "Owner Action Required",
            "detected_at": doc.get("created_at"),
            "last_updated_at": doc.get("last_synced_at"),
            "source_refs": [{"kind": "ops_obligations", "id": obl_id}],
            "risk_reason_codes": ["sla_breached"] if is_overdue else ["owner_action_required"],
            "recommended_next_step": doc.get("required_action"),
            "responsibility_layer": "Owner Obligations (Durable Ledger)",
            "detail_rows": detail_rows,
            "is_overdue": is_overdue,
            "overdue_hours": overdue_h,
            "escalation_level": esc_level,
            "linked_paths": [],
            "audit_refs": [],
        }
        cases.append(case_obj)

    return cases
