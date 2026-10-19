"""Durable Owner Responsibility Ledger & Escalation Service for DTD Operations.

Governing Principle: OWNER BY EXCEPTION. AUTOMATION BY DEFAULT.
Product Invariant: If the owner does not see a job requiring attention in /ops,
it must never be silently kept in the background or dropped.

This service maintains the `ops_obligations` collection in MongoDB, providing:
1. Durable capture of all genuine owner-required obligations (verification, delivery, claim, billing, scheduler, provider).
2. Cadence-aware SLA tracking (due dates).
3. Automated escalation when an obligation breaches its SLA (overdue detection).
4. Evidence-based terminal state verification: absence from a scan NEVER resolves an obligation.
5. Review state decoupling: Acknowledgment or dismissal does not falsely certify underlying business completion.
6. Safe recurrence detection: New failures reopen obligations without permanent suppression or flapping.
7. Non-technical owner escalation hierarchy: Clear practical impact, safe operating state, and sanitized technical handoff.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("dtd.ops_obligations")

# Cadence-aware SLA definitions in hours
CATEGORY_SLAS: Dict[str, int] = {
    "scheduler": 1,             # Engine tick cron stall > 750s needs prompt attention (1 hour SLA)
    "claim_lock": 4,            # Stuck trainer profile claim lock needs release within 4 hours
    "provider": 6,              # External provider auth/outage needs review within 6 hours
    "client_enquiry": 12,       # Undelivered client enquiry needs delivery within 12 hours
    "notification_delivery": 12,# Failed notification dispatch needs delivery within 12 hours
    "customer_complaint": 12,   # High-priority customer complaint or legal takedown
    "customer_support": 24,     # General customer support inquiry within 24 hours
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


async def verify_obligation_terminal_state(db, obl_doc: Dict[str, Any]) -> Tuple[bool, str]:
    """Inspect the specific underlying entity in its authoritative datastore.
    
    Returns (True, reason) ONLY when verified positive evidence demonstrates that the
    underlying entity has reached a valid terminal state.
    Returns (False, reason) if the entity is still active, missing without verification,
    or if the datastore query encounters an error.
    """
    category = obl_doc.get("category", "")
    entity_id = str(obl_doc.get("entity_id", ""))

    if not entity_id:
        return False, "Missing entity_id; cannot verify terminal state"

    try:
        if category == "trainer_verification":
            submissions_coll = getattr(db, "submissions", None)
            if submissions_coll is None:
                return False, "Submissions collection unavailable"

            sub = await submissions_coll.find_one({"id": entity_id}, {"_id": 0})
            if sub:
                status = str(sub.get("status") or "").lower()
                abn_status = str(sub.get("abn_status") or "").lower()
                if status in ("published", "approved") and abn_status not in ("unverified", "invalid", "degraded", "abr_unavailable"):
                    return True, f"Submission {entity_id} verified published and ABN validated ({abn_status})"
                if status in ("rejected", "declined", "withdrawn"):
                    return True, f"Submission {entity_id} reached terminal state '{status}'"
                return False, f"Submission {entity_id} remains pending (status: {status}, abn_status: {abn_status})"
            
            # If not in submissions, check if already converted to a published trainer
            trainers_coll = getattr(db, "trainers", None)
            if trainers_coll is not None:
                trainer = await trainers_coll.find_one({"$or": [{"id": entity_id}, {"submission_id": entity_id}]}, {"_id": 0})
                if trainer and trainer.get("status") in ("published", "active"):
                    return True, f"Trainer {trainer.get('id')} verified published in directory"

            return False, f"Submission {entity_id} record not found; preserving pending obligation"

        elif category == "claim_lock":
            claim_events_coll = getattr(db, "claim_events", None)
            trainers_coll = getattr(db, "trainers", None)

            claim_doc = None
            if claim_events_coll is not None:
                claim_doc = await claim_events_coll.find_one({"$or": [{"id": entity_id}, {"trainer_id": entity_id}]}, {"_id": 0})

            trainer_doc = None
            if trainers_coll is not None:
                t_id = (claim_doc.get("trainer_id") if claim_doc else entity_id)
                trainer_doc = await trainers_coll.find_one({"id": t_id}, {"_id": 0})

            if not claim_doc and not trainer_doc:
                return False, f"Neither claim event nor trainer record found for {entity_id}; cannot verify lock release"
            if not trainer_doc:
                return False, f"Trainer record {entity_id} not found; cannot verify lock release"

            lock_held = bool(trainer_doc.get("claim_in_progress"))
            if lock_held:
                return False, f"Claim lock still actively held on trainer {entity_id}"

            if claim_doc:
                claim_status = str(claim_doc.get("status") or "").lower()
                if claim_status in ("verified", "completed"):
                    return True, f"Profile claim verified and completed for trainer {entity_id}"
                if claim_status in ("expired", "cancelled", "released", "denied") and not lock_held:
                    return True, f"Claim lock released and confirmed inactive (claim status: {claim_status})"
                return False, f"Claim lock status is {claim_status}, lock_held: {lock_held}"

            return True, f"No active claim lock on trainer {entity_id} (lock_held: False)"

        elif category in ("client_enquiry", "notification_delivery"):
            notif_coll = getattr(db, "notification_events", None)
            message_log_coll = getattr(db, "message_log", None)

            # Check notification_events first (authoritative datastore)
            # Confirmed delivery requires terminal status 'delivered' or 'recovered', matched strictly on dispatch_id
            if notif_coll is not None and hasattr(notif_coll, "find_one"):
                delivered = await notif_coll.find_one(
                    {
                        "$or": [{"dispatch_id": entity_id}, {"id": entity_id}],
                        "status": {"$in": ["delivered", "recovered"]},
                    },
                    {"_id": 0, "status": 1, "created_at": 1},
                )
                if delivered:
                    return True, f"Notification dispatch {entity_id} verified delivered successfully"

            # Check message_log as secondary/legacy fallback
            if message_log_coll is not None and hasattr(message_log_coll, "find_one"):
                delivered = await message_log_coll.find_one(
                    {
                        "$or": [{"dispatch_id": entity_id}, {"id": entity_id}],
                        "status": {"$in": ["delivered", "recovered"]},
                    },
                    {"_id": 0, "status": 1, "created_at": 1},
                )
                if delivered:
                    return True, f"Message dispatch {entity_id} verified delivered successfully"

            return False, f"No confirmed delivery recorded for message dispatch {entity_id}"

        elif category in ("customer_support", "customer_complaint"):
            support_coll = getattr(db, "support_threads", None)
            if support_coll is None:
                return False, "Support threads collection unavailable"

            thread = await support_coll.find_one({"case_id": entity_id}, {"_id": 0, "status": 1})
            if not thread:
                return False, f"Support thread {entity_id} not found"

            th_status = str(thread.get("status") or "").lower()
            if th_status in ("resolved", "closed", "completed", "archived"):
                return True, f"Support thread {entity_id} verified {th_status}"

            return False, f"Support thread {entity_id} remains open (status: {th_status})"

        elif category == "scheduler":
            system_state_coll = getattr(db, "system_state", None)
            if system_state_coll is None:
                return False, "System state collection unavailable"

            engine_tick_doc = await system_state_coll.find_one({"key": "engine_tick"}, {"_id": 0}) or {}
            last_run = engine_tick_doc.get("last_run")
            last_status = str(engine_tick_doc.get("last_status") or "").lower()
            failures = int(engine_tick_doc.get("consecutive_failures") or 0)
            
            run_dt = parse_iso(last_run)
            age_s = (now_utc() - run_dt).total_seconds() if run_dt else None

            if last_status == "ok" and failures == 0 and age_s is not None and age_s <= 750:
                return True, f"Engine tick healthy (last run {int(age_s)}s ago, status: ok)"

            return False, f"Engine tick not healthy (status: {last_status}, age: {age_s}s, failures: {failures})"

        elif category == "provider":
            system_state_coll = getattr(db, "system_state", None)
            if system_state_coll is None:
                return False, "System state collection unavailable"

            prov_doc = await system_state_coll.find_one({"key": f"provider:{entity_id}"}, {"_id": 0}) or {}
            prov_status = str(prov_doc.get("status") or "").lower()

            if prov_status in ("healthy", "ok", "available"):
                return True, f"Provider {entity_id} operational state verified healthy"

            return False, f"Provider {entity_id} remains degraded or unknown (status: {prov_status})"

        return False, f"No terminal state verification rule defined for category '{category}'"

    except Exception as exc:
        logger.warning("Exception during terminal state verification for %s: %s", obl_doc.get("obligation_id"), exc)
        return False, f"Verification query error: {str(exc)}"


async def sync_durable_obligations(db, now_dt: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Scan authoritative system state and synchronize the durable `ops_obligations` collection.
    
    Enforces Evidence-Based Terminal-State Verification:
    Absence from a scan NEVER resolves an obligation.
    Existing obligations remain active until verified positive evidence shows terminal completion
    or explicit authorized operator review.
    """
    current_dt = now_dt or now_utc()
    current_iso = current_dt.isoformat()
    active_obligations: Dict[str, Dict[str, Any]] = {}
    source_status: Dict[str, Dict[str, Any]] = {}

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
            ).to_list(500)
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
                    "required_action": "Inspect ABN verification evidence and approve or reject trainer listing in /ops.",
                    "base_severity": "medium",
                    "created_at_source": sub.get("created_at") or current_iso,
                    "metadata": {"abn": sub.get("abn"), "abn_status": sub.get("abn_status")},
                    "resolution_type": "guided_in_ops",
                    "technical_assistance_required": False,
                    "safe_operating_state": "DTD public directory is operating normally. Listing is held pending owner review.",
                }
            source_status["trainer_verification"] = {"status": "ok", "checked_at": current_iso}
        except Exception as exc:
            logger.warning("Error reading submissions for obligations: %s", exc)
            source_status["trainer_verification"] = {"status": "error", "error": str(exc), "checked_at": current_iso}

    # 2. Stale Trainer Profile Claim Locks
    claim_events_coll = getattr(db, "claim_events", None)
    if claim_events_coll is not None and hasattr(claim_events_coll, "find"):
        try:
            stuck_claims = await claim_events_coll.find(
                {
                    "status": {"$in": ["initiated", "pending", "otp_sent", "stale", "lock_held"]},
                },
                {"_id": 0, "id": 1, "trainer_id": 1, "status": 1, "method": 1, "created_at": 1, "updated_at": 1},
            ).to_list(200)
            for claim in stuck_claims:
                claim_id = str(claim.get("id") or "")
                trainer_id = str(claim.get("trainer_id") or "")
                created_ts = claim.get("created_at") or claim.get("updated_at") or current_iso
                claim_dt = parse_iso(created_ts) or current_dt
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
                        "resolution_type": "guided_in_ops",
                        "technical_assistance_required": False,
                        "safe_operating_state": "Profile remains visible to pet owners; claiming is temporarily locked for edits.",
                    }
            source_status["claim_lock"] = {"status": "ok", "checked_at": current_iso}
        except Exception as exc:
            logger.warning("Error reading claim events for obligations: %s", exc)
            source_status["claim_lock"] = {"status": "error", "error": str(exc), "checked_at": current_iso}

    # 3. Failed Message Delivery (Resend / Enquiries)
    notif_coll = getattr(db, "notification_events", None)
    message_log_coll = getattr(db, "message_log", None)
    failed_messages: List[Dict[str, Any]] = []

    # Authoritative persistence: scan notification_events
    if notif_coll is not None and hasattr(notif_coll, "find"):
        try:
            raw_failed = await notif_coll.find(
                {"status": {"$in": ["failed", "bounced", "error"]}},
                {"_id": 0, "id": 1, "dispatch_id": 1, "to_email": 1, "kind": 1, "target_kind": 1, "target_id": 1, "error": 1, "created_at": 1},
            ).sort("created_at", -1).to_list(1000)
            for item in raw_failed:
                failed_messages.append({
                    "id": item.get("id"),
                    "dispatch_id": item.get("dispatch_id") or item.get("id"),
                    "recipient": item.get("to_email"),
                    "subject": item.get("kind") or "System Notification",
                    "error": item.get("error"),
                    "created_at": item.get("created_at"),
                    "target_kind": item.get("target_kind"),
                    "target_id": item.get("target_id"),
                })
        except Exception as exc:
            logger.warning("Error reading notification events for obligations: %s", exc)

    # Legacy/test fallback: scan message_log if notification_events was empty or unavailable
    if not failed_messages and message_log_coll is not None and hasattr(message_log_coll, "find"):
        try:
            raw_log = await message_log_coll.find(
                {"status": {"$in": ["failed", "bounced", "error"]}},
                {"_id": 0, "id": 1, "dispatch_id": 1, "recipient": 1, "subject": 1, "error": 1, "created_at": 1},
            ).sort("created_at", -1).to_list(1000)
            failed_messages.extend(raw_log)
        except Exception as exc:
            logger.warning("Error reading message log for obligations: %s", exc)

    try:
        for msg in failed_messages:
            dispatch_id = str(msg.get("dispatch_id") or msg.get("id") or "")
            if not dispatch_id:
                continue

            # Verify whether a subsequent retry or delivery event succeeded for this exact dispatch
            is_recovered = False
            if notif_coll is not None and hasattr(notif_coll, "find_one"):
                success_match = await notif_coll.find_one(
                    {
                        "$or": [
                            {"dispatch_id": dispatch_id, "status": {"$in": ["delivered", "recovered"]}},
                            {"retry_of_dispatch_id": dispatch_id, "status": {"$in": ["delivered", "recovered"]}},
                        ],
                    },
                    {"_id": 1},
                )
                if success_match:
                    is_recovered = True

            if is_recovered:
                continue

            target_kind = str(msg.get("target_kind") or "")
            cat = "client_enquiry" if target_kind == "intro" or "intro" in str(msg.get("subject") or "").lower() else "notification_delivery"
            obl_id = f"obligation:message:{dispatch_id}"
            active_obligations[obl_id] = {
                "obligation_id": obl_id,
                "category": cat,
                "entity_id": dispatch_id,
                "title": f"Undelivered Message: {msg.get('subject') or 'Client Enquiry'} ({msg.get('recipient')})",
                "required_action": f"Verify recipient ({msg.get('recipient')}) or retry dispatch manually in /ops.",
                "base_severity": "high",
                "status": "pending",
                "created_at_source": msg.get("created_at") or current_iso,
                "metadata": {"recipient": msg.get("recipient"), "error": msg.get("error"), "target_kind": target_kind, "target_id": msg.get("target_id")},
                "resolution_type": "guided_in_ops",
                "technical_assistance_required": False,
                "safe_operating_state": "Website is operating normally; this specific email notification needs retry.",
            }
        source_status["client_enquiry"] = {"status": "ok", "checked_at": current_iso}
    except Exception as exc:
        logger.warning("Error compiling message delivery obligations: %s", exc)
        source_status["client_enquiry"] = {"status": "error", "error": str(exc), "checked_at": current_iso}

    # 3b. Open Customer Support Threads & Inbound Complaints (including reply delivery failures and waiting states)
    support_coll = getattr(db, "support_threads", None)
    if support_coll is not None and hasattr(support_coll, "find"):
        try:
            open_threads = await support_coll.find(
                {"status": {"$in": ["open", "pending_owner", "escalated", "reply_delivery_failed", "awaiting_customer_reply", "awaiting_identity_proof"]}},
                {"_id": 0, "case_id": 1, "sender_email": 1, "category": 1, "severity": 1, "subject": 1, "status": 1, "created_at": 1},
            ).sort("created_at", -1).to_list(500)
            for thr in open_threads:
                case_id = str(thr.get("case_id") or "")
                if not case_id:
                    continue
                obl_id = f"obligation:support:{case_id}"
                thr_status = str(thr.get("status") or "").lower()

                if thr_status == "reply_delivery_failed":
                    cat = "customer_complaint" if thr.get("category") == "complaint" else "notification_delivery"
                    title = f"Failed Support Reply Delivery: {thr.get('subject') or thr.get('category')} ({thr.get('sender_email')})"
                    req_action = "Outbound support reply delivery failed. Retry reply dispatch or verify recipient email in /ops."
                    base_sev = "high"
                    obl_status = "pending"
                    safe_state = "Website is operating normally; this specific support reply delivery failed and requires retry."
                elif thr_status in ("awaiting_customer_reply", "awaiting_identity_proof"):
                    cat = "customer_support"
                    title = f"Awaiting External Response: {thr.get('subject') or thr.get('category')} ({thr.get('sender_email')})"
                    req_action = f"Awaiting response from customer ({thr_status.replace('_', ' ')}). Urgent alerts paused."
                    base_sev = "low"
                    obl_status = "waiting"
                    safe_state = f"Website is operating normally; thread is paused awaiting customer response ({thr_status.replace('_', ' ')})."
                else:
                    cat = "customer_complaint" if thr.get("category") == "complaint" or thr.get("severity") == "high" else "customer_support"
                    title = f"Customer Request: {thr.get('subject') or thr.get('category', 'Support')} ({thr.get('sender_email')})"
                    req_action = "Review inquiry, respond or escalate to specialized workflow in /ops."
                    base_sev = "high" if cat == "customer_complaint" else "medium"
                    obl_status = "pending"
                    safe_state = "Website is operating normally; this customer inquiry is awaiting operator response."

                active_obligations[obl_id] = {
                    "obligation_id": obl_id,
                    "category": cat,
                    "entity_id": case_id,
                    "title": title,
                    "required_action": req_action,
                    "base_severity": base_sev,
                    "status": obl_status,
                    "created_at_source": thr.get("created_at") or current_iso,
                    "metadata": {"sender_email": thr.get("sender_email"), "category": thr.get("category"), "severity": thr.get("severity"), "thread_status": thr_status},
                    "resolution_type": "guided_in_ops",
                    "technical_assistance_required": False,
                    "safe_operating_state": safe_state,
                }
            source_status["customer_support"] = {"status": "ok", "checked_at": current_iso}
        except Exception as exc:
            logger.warning("Error reading support threads for obligations: %s", exc)
            source_status["customer_support"] = {"status": "error", "error": str(exc), "checked_at": current_iso}

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
                    "required_action": "Technical assistance may be required: Cloud Scheduler task is delayed or failing. Public directory continues operating safely.",
                    "base_severity": "high",
                    "created_at_source": tick_last_run or current_iso,
                    "metadata": {
                        "last_run": tick_last_run,
                        "last_status": tick_status,
                        "age_s": tick_age_s,
                        "failures": tick_failures,
                    },
                    "resolution_type": "technical_specialist",
                    "technical_assistance_required": True,
                    "safe_operating_state": "DTD public directory remains operational; routine background ranking and nurture updates are paused.",
                    "technical_handoff": f"Engine tick cron has stalled or failed (status: {tick_status}, consecutive failures: {tick_failures}, age: {tick_age_s}s). Check Cloud Scheduler dtd-engine-tick-cron or Cloud Run /api/internal/jobs/engine-tick.",
                }
            source_status["scheduler"] = {"status": "ok", "checked_at": current_iso}
        except Exception as exc:
            logger.warning("Error checking scheduler for obligations: %s", exc)
            source_status["scheduler"] = {"status": "error", "error": str(exc), "checked_at": current_iso}

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
                    "required_action": "External provider action required: Check Resend account status and sending quota in Resend dashboard.",
                    "base_severity": "high",
                    "created_at_source": resend_provider.get("last_failure") or current_iso,
                    "metadata": resend_provider,
                    "resolution_type": "external_provider",
                    "technical_assistance_required": True,
                    "safe_operating_state": "Public directory browsing is active; outbound enquiry and verification emails are temporarily paused.",
                    "technical_handoff": f"Resend integration reports {resend_provider.get('status')}. Verify API key permissions or Resend account billing.",
                }
            source_status["provider"] = {"status": "ok", "checked_at": current_iso}
        except Exception as exc:
            logger.warning("Error checking providers for obligations: %s", exc)
            source_status["provider"] = {"status": "error", "error": str(exc), "checked_at": current_iso}

    # 6. Synchronize with `ops_obligations` MongoDB Collection
    obligations_coll = getattr(db, "ops_obligations", None)
    synced_list: List[Dict[str, Any]] = []

    if obligations_coll is not None and hasattr(obligations_coll, "update_one"):
        # A. Upsert Active Obligations Found in the Scan
        for obl_id, obl_data in active_obligations.items():
            existing = await obligations_coll.find_one({"obligation_id": obl_id}, {"_id": 0}) or {}
            created_at_str = existing.get("created_at") or obl_data["created_at_source"]
            sla_info = compute_sla(obl_data["category"], created_at_str, now_dt=current_dt)

            is_overdue = sla_info["is_overdue"]
            escalation_level = sla_info["escalation_level"]
            severity = "high" if is_overdue else obl_data["base_severity"]

            # Recurrence detection: if previously resolved, reopen with recurrence badge and increment count
            prev_status = existing.get("status")
            recurrence_count = int(existing.get("recurrence_count") or 0)
            is_recurrence = False
            is_waiting = (obl_data.get("status") == "waiting")

            if is_waiting:
                is_overdue = False
                escalation_level = 0
                severity = "low"
                status = "waiting"
                reopened_at = existing.get("reopened_at")
            elif prev_status == "resolved":
                is_recurrence = True
                recurrence_count += 1
                status = "escalated" if is_overdue else "pending"
                reopened_at = current_iso
            else:
                status = "escalated" if is_overdue else existing.get("status", "pending")
                reopened_at = existing.get("reopened_at")

            escalated_at = existing.get("escalated_at")
            if is_overdue and not escalated_at:
                escalated_at = current_iso

            # Preserve human review state without certifying false business completion
            review_obj = existing.get("review") or {}
            if is_recurrence:
                # Reset review state on recurrence so owner is re-notified
                review_obj = {
                    "review_state": "detected",
                    "reopened_reason": "Reopened due to recurrence of active failure",
                    "updated_at": current_iso,
                }

            history = existing.get("history") or []
            if is_recurrence:
                history.append({
                    "action": "reopened_recurrence",
                    "timestamp": current_iso,
                    "recurrence_count": recurrence_count,
                    "reason": "New active failure detected for previously resolved obligation",
                })

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
                "overdue_hours": 0.0 if is_waiting else sla_info["overdue_hours"],
                "escalation_level": escalation_level,
                "escalated_at": escalated_at,
                "recurrence_count": recurrence_count,
                "reopened_at": reopened_at,
                "metadata": obl_data.get("metadata", {}),
                "resolution_type": obl_data.get("resolution_type", "guided_in_ops"),
                "technical_assistance_required": obl_data.get("technical_assistance_required", False),
                "safe_operating_state": obl_data.get("safe_operating_state", "Operating normally."),
                "technical_handoff": obl_data.get("technical_handoff"),
                "review": review_obj,
                "history": history,
                "last_synced_at": current_iso,
                "last_verified_at": current_iso,
            }

            await obligations_coll.update_one(
                {"obligation_id": obl_id},
                {"$set": doc_payload},
                upsert=True,
            )
            synced_list.append(doc_payload)

        # B. Evidence-Based Terminal State Verification for Unseen Obligations
        # CRITICAL SAFETY INVARIANT: Absence from active scan NEVER automatically resolves an obligation!
        # We must inspect the specific entity in its authoritative collection.
        try:
            active_ids = set(active_obligations.keys())
            pending_cursor = obligations_coll.find(
                {"status": {"$in": ["pending", "escalated", "waiting"]}},
                {"_id": 0},
            )
            pending_docs = await pending_cursor.to_list(1000) if hasattr(pending_cursor, "to_list") else []

            for obl in pending_docs:
                obl_id = obl.get("obligation_id", "")
                if obl_id in active_ids:
                    continue  # Already refreshed in Step A

                cat = obl.get("category", "")
                # If the source query for this domain failed, PRESERVE the obligation without mutation
                cat_status = source_status.get(cat, {}).get("status")
                if cat_status == "error":
                    logger.info("Preserving obligation %s because source domain %s encountered a query error", obl_id, cat)
                    await obligations_coll.update_one(
                        {"obligation_id": obl_id},
                        {
                            "$set": {
                                "source_verification_gap": f"Source query failed for domain {cat}; preserved pending",
                                "last_checked_at": current_iso,
                            }
                        },
                    )
                    synced_list.append(obl)
                    continue

                # Query the specific underlying entity for verified positive terminal state
                is_terminal, reason = await verify_obligation_terminal_state(db, obl)
                if is_terminal:
                    history = obl.get("history") or []
                    history.append({
                        "action": "auto_resolved_terminal_state",
                        "timestamp": current_iso,
                        "notes": reason,
                    })
                    await obligations_coll.update_one(
                        {"obligation_id": obl_id},
                        {
                            "$set": {
                                "status": "resolved",
                                "resolved_at": current_iso,
                                "resolution_type": "verified_terminal_state",
                                "resolution_notes": reason,
                                "last_synced_at": current_iso,
                                "last_verified_at": current_iso,
                                "history": history,
                            }
                        },
                    )
                    logger.info("Obligation %s resolved via verified terminal state: %s", obl_id, reason)
                else:
                    # Positive evidence of resolution does NOT exist. Obligation remains ACTIVE!
                    is_waiting = (obl.get("status") == "waiting")
                    if is_waiting:
                        is_overdue = False
                        esc_level = 0
                        status = "waiting"
                        severity = "low"
                        overdue_h = 0.0
                    else:
                        sla_info = compute_sla(cat, obl.get("created_at"), now_dt=current_dt)
                        is_overdue = sla_info["is_overdue"]
                        esc_level = sla_info["escalation_level"]
                        status = "escalated" if is_overdue else obl.get("status", "pending")
                        severity = "high" if is_overdue else obl.get("severity", "medium")
                        overdue_h = sla_info["overdue_hours"]

                    update_payload = {
                        "is_overdue": is_overdue,
                        "overdue_hours": overdue_h,
                        "escalation_level": esc_level,
                        "status": status,
                        "severity": severity,
                        "verification_gap": reason,
                        "last_synced_at": current_iso,
                        "last_verified_at": current_iso,
                    }
                    await obligations_coll.update_one(
                        {"obligation_id": obl_id},
                        {"$set": update_payload},
                    )
                    obl.update(update_payload)
                    synced_list.append(obl)

        except Exception as exc:
            logger.warning("Error during evidence-based obligation resolution: %s", exc)

    return synced_list


async def get_active_obligation_cases(db, now_dt: Optional[datetime] = None, read_only: bool = False) -> List[Dict[str, Any]]:
    """Convert durable unaddressed obligations into top-priority Ops console cases."""
    current_dt = now_dt or now_utc()
    if read_only:
        obls_coll = getattr(db, "ops_obligations", None)
        if obls_coll is None or not hasattr(obls_coll, "find"):
            return []
        docs = await obls_coll.find({"status": {"$ne": "resolved"}}).sort("created_at", -1).to_list(1000)
    else:
        synced = await sync_durable_obligations(db, now_dt=current_dt)
        docs = [d for d in synced if d.get("status") != "resolved"]

    cases: List[Dict[str, Any]] = []

    for doc in docs:
        obl_id = doc.get("obligation_id", "")
        sla_info = compute_sla(doc.get("category", ""), doc.get("created_at_source") or doc.get("created_at"), now_dt=current_dt)
        is_waiting = (doc.get("status") == "waiting")
        if is_waiting:
            is_overdue = False
            esc_level = 0
            overdue_h = 0.0
        else:
            is_overdue = sla_info["is_overdue"]
            esc_level = sla_info["escalation_level"]
            overdue_h = sla_info["overdue_hours"]
        sla_h = sla_info["sla_hours"]
        recurrence_count = int(doc.get("recurrence_count") or 0)

        title = doc.get("title", "")
        prefix_parts = []
        if recurrence_count > 0:
            prefix_parts.append(f"(Recurred x{recurrence_count})")
        if is_overdue:
            prefix_parts.append("[CRITICAL OVERDUE ESCALATION]" if esc_level >= 2 else "[OVERDUE ESCALATION]")

        if prefix_parts:
            display_title = f"{' '.join(prefix_parts)} {title}"
        else:
            display_title = title

        # Non-Technical Owner Escalation Hierarchy Details
        tech_req = bool(doc.get("technical_assistance_required", False))
        safe_state = doc.get("safe_operating_state", "Operating normally.")
        res_type = doc.get("resolution_type", "guided_in_ops")
        handoff = doc.get("technical_handoff")

        detail_rows = [
            {"label": "Durable Obligation ID", "value": obl_id},
            {"label": "Category", "value": doc.get("category", "general")},
            {"label": "SLA Policy Window", "value": f"{sla_h} hours"},
            {"label": "SLA Deadline", "value": doc.get("due_at")},
            {"label": "Overdue Status", "value": f"BREACHED by {overdue_h} hours" if is_overdue else "Within SLA window"},
            {"label": "Escalation Level", "value": f"Level {esc_level} (Action Urgent)" if is_overdue else "Normal (Pending)"},
            {"label": "Safe Operating Status", "value": safe_state},
            {"label": "Resolution Channel", "value": res_type.replace("_", " ").title()},
        ]

        if tech_req:
            detail_rows.append({"label": "Support Requirement", "value": "Technical assistance may be required."})
        if handoff:
            detail_rows.append({"label": "Technical Diagnostic Handoff", "value": handoff})

        for k, v in (doc.get("metadata") or {}).items():
            if v is not None:
                detail_rows.append({"label": k.replace("_", " ").title(), "value": str(v)})

        # Review tracking decoupling
        review_obj = doc.get("review") or {}
        review_state = review_obj.get("review_state")
        if review_state == "acknowledged":
            display_title = f"[ACKNOWLEDGED - IN PROGRESS] {display_title}"
            detail_rows.append({"label": "Operator Review Note", "value": review_obj.get("notes") or "Acknowledged in ops triage"})

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
            "technical_assistance_required": tech_req,
            "safe_operating_state": safe_state,
            "technical_handoff": handoff,
            "resolution_type": res_type,
            "linked_paths": [],
            "audit_refs": [],
        }
        cases.append(case_obj)

    return cases
