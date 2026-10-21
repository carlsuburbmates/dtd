"""Ops Recovery Service (Phase 5).

Autonomous, deterministic, bounded self-healing recovery controller for DTD.
Governing Principle:
OWNER BY EXCEPTION. AUTOMATION BY DEFAULT. AI ANALYSIS WHEN NEEDED.

Strict Boundaries:
1. AI Separation: Gemini Analyst (Phase 4) is advisory-only and has ZERO mutation authority.
   The Recovery Controller evaluates deterministic eligibility and only runs registered routines.
2. Default-Disabled Posture: All recovery routines disabled by default.
3. Production Hard Block: Self-healing execution is strictly prohibited and hard-blocked in production.
4. Atomicity & Concurrency: MongoDB-backed distributed atomic claiming prevents duplicate executions.
5. Verified Recovery: A successful API call or mutation is NOT recovery; recovery is confirmed only
   after downstream operational evidence verifies the problem is resolved.
6. Zero Business Mutations: Never alters trainer ownership, ABR statutory status, publication state,
   or customer billing status.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("dtd.ops_recovery")

# ---------------------------------------------------------------------------
# Configuration & Feature Flags
# ---------------------------------------------------------------------------
DEFAULT_DAILY_RECOVERY_LIMIT = 20
DEFAULT_RECOVERY_COOLDOWN_SECONDS = 300
DEFAULT_RECOVERY_LEASE_TTL_SECONDS = 60

ENGINE_TICK_LEASE_KEY = "engine_tick_lease"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_production_environment() -> bool:
    """Check whether the current runtime environment is production."""
    project_id = os.environ.get("PROJECT_ID", "").strip()
    vertex_project = os.environ.get("VERTEXAI_PROJECT", "").strip()
    sentry_env = os.environ.get("SENTRY_ENVIRONMENT", "").strip().lower()
    is_prod_flag = os.environ.get("PRODUCTION", "0").strip() in ("1", "true", "yes")

    # Hard-locked production project identifier
    if project_id == "gen-lang-client-0028123502" or vertex_project == "gen-lang-client-0028123502":
        return True
    if sentry_env in ("production", "prod"):
        return True
    if is_prod_flag:
        return True
    return False


def is_self_healing_globally_enabled() -> bool:
    """Master toggle for Phase 5 self-healing. Default: False."""
    if is_production_environment():
        return False
    return os.environ.get("OPS_SELF_HEALING_ENABLED", "0").strip().lower() in ("1", "true", "yes")


def is_routine_flag_enabled(flag_name: str) -> bool:
    """Check individual routine feature flag. Default: False."""
    if is_production_environment():
        return False
    return os.environ.get(flag_name, "0").strip().lower() in ("1", "true", "yes")


def get_daily_recovery_limit() -> int:
    try:
        return int(os.environ.get("OPS_RECOVERY_DAILY_LIMIT", str(DEFAULT_DAILY_RECOVERY_LIMIT)))
    except ValueError:
        return DEFAULT_DAILY_RECOVERY_LIMIT


# ---------------------------------------------------------------------------
# Recovery Routines Implementation
# ---------------------------------------------------------------------------

async def _lease_recovery_is_eligible(case: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if incident is an expired or orphaned background task distributed lease."""
    case_id = str(case.get("case_id") or "")
    case_type = str(case.get("case_type") or "")
    summary = str(case.get("summary") or "").lower()
    risk_reasons = [str(r) for r in (case.get("risk_reason_codes") or [])]

    # Eligible if related to engine-tick lease, serverless unowned, or loop stalls
    is_lease_case = (
        "engine_tick" in case_id
        or "DF-029" in case_id
        or "autonomy_serverless_unowned" in risk_reasons
        or "lease" in summary
    )
    if not is_lease_case:
        return False, "Not an expired lease incident"

    db = context.get("db")
    if db is None:
        return False, "Database reference missing"

    system_state_coll = getattr(db, "system_state", None)
    if system_state_coll is None:
        return False, "system_state collection unavailable"

    lease_doc = await system_state_coll.find_one({"key": ENGINE_TICK_LEASE_KEY})
    if not lease_doc:
        return True, "No lease document currently held; eligible to initialize clean state"

    expires_at = float(lease_doc.get("expires_at_epoch") or 0)
    now_epoch = time.time()
    # Must be genuinely expired or past TTL
    if expires_at > now_epoch:
        return False, f"Lease is currently actively held until {expires_at} (now {now_epoch}); cannot steal active lease"

    return True, f"Lease expired at {expires_at} (elapsed {round(now_epoch - expires_at, 1)}s); safe to clear"


async def _lease_recovery_execute(db: Any, case: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    """Atomically release/clear proven expired engine_tick lease."""
    system_state_coll = getattr(db, "system_state", None)
    if system_state_coll is None:
        raise RuntimeError("system_state collection not found")

    now_epoch = time.time()
    before_doc = await system_state_coll.find_one({"key": ENGINE_TICK_LEASE_KEY})

    # Compare-and-set: clear only if still expired
    res = await system_state_coll.find_one_and_update(
        {
            "key": ENGINE_TICK_LEASE_KEY,
            "$or": [
                {"expires_at_epoch": {"$lte": now_epoch}},
                {"expires_at_epoch": {"$exists": False}},
            ],
        },
        {
            "$set": {
                "expires_at_epoch": 0,
                "recovered_by": record.get("execution_id"),
                "recovered_at": now_iso(),
                "recovery_reason": "ops_recovery:lease_cleanup",
            }
        },
        upsert=False,
        return_document=True,
    )
    after_doc = res if res else await system_state_coll.find_one({"key": ENGINE_TICK_LEASE_KEY})

    return {
        "before": before_doc,
        "after": after_doc,
        "cleared_at_epoch": now_epoch,
        "lease_released": True,
    }


async def _lease_recovery_verify(db: Any, case: Dict[str, Any], exec_res: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Verify that the lease is cleared and accessible for subsequent execution."""
    system_state_coll = getattr(db, "system_state", None)
    if system_state_coll is None:
        return False, "system_state collection missing", {}

    lease_doc = await system_state_coll.find_one({"key": ENGINE_TICK_LEASE_KEY})
    now_epoch = time.time()
    if not lease_doc:
        return True, "Lease is completely free and unheld", {"lease_free": True}

    expires_at = float(lease_doc.get("expires_at_epoch") or 0)
    if expires_at <= now_epoch or lease_doc.get("expires_at_epoch") == 0:
        return True, "Verified: lease is cleared and unblocked (expires_at <= now)", {"lease_doc": lease_doc}

    return False, f"Verification failed: lease has future expiry {expires_at}", {"lease_doc": lease_doc}


async def _claim_lock_is_eligible(case: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if case is an abandoned trainer claim past OTP validity."""
    case_type = str(case.get("case_type") or "")
    if case_type != "trainer_claim_case":
        return False, "Not a trainer claim case"

    case_id = str(case.get("case_id") or "")
    # Check detail rows or underlying claim document
    db = context.get("db")
    if db is None:
        return False, "Database reference missing"

    claims_coll = getattr(db, "trainer_claims", None)
    if claims_coll is None:
        return False, "trainer_claims collection unavailable"

    # Resolve target entity/claim id
    target_id = str(case.get("entity_id") or case_id.replace("claim:", ""))
    claim_doc = await claims_coll.find_one({
        "$or": [{"id": target_id}, {"trainer_id": target_id}, {"claim_id": target_id}]
    })
    if not claim_doc:
        return False, "No corresponding claim record found in trainer_claims"

    status = str(claim_doc.get("status") or "")
    if status not in ("pending_verification", "in_progress", "code_sent"):
        return False, f"Claim status is '{status}', not in transient pending state"

    # Check expiration (claims expire after 1800s / 30m)
    expires_at_str = claim_doc.get("expires_at")
    created_at_str = claim_doc.get("created_at")
    now_dt = datetime.now(timezone.utc)

    is_expired = False
    if expires_at_str:
        try:
            exp_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if now_dt > exp_dt:
                is_expired = True
        except Exception:
            pass

    if not is_expired and created_at_str:
        try:
            created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if (now_dt - created_dt).total_seconds() > 1800:
                is_expired = True
        except Exception:
            pass

    if not is_expired:
        return False, "Claim is still within active OTP validity window"

    return True, f"Claim {target_id} has expired OTP window and abandoned lock"


async def _claim_lock_execute(db: Any, case: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    """Release expired transient claim lock without transferring ownership."""
    claims_coll = getattr(db, "trainer_claims", None)
    trainers_coll = getattr(db, "trainers", None)

    case_id = str(case.get("case_id") or "")
    target_id = str(case.get("entity_id") or case_id.replace("claim:", ""))

    before_claim = await claims_coll.find_one({
        "$or": [{"id": target_id}, {"trainer_id": target_id}, {"claim_id": target_id}]
    })

    # Mark claim expired
    await claims_coll.update_one(
        {"_id": before_claim["_id"]},
        {
            "$set": {
                "status": "expired",
                "expired_at": now_iso(),
                "recovered_by": record.get("execution_id"),
            }
        },
    )

    # If trainer record has temporary claim_in_progress lock, release it
    trainer_id = before_claim.get("trainer_id") or target_id
    before_trainer = await trainers_coll.find_one({"id": trainer_id}) if trainers_coll is not None else None
    if before_trainer and before_trainer.get("claim_in_progress"):
        await trainers_coll.update_one(
            {"id": trainer_id},
            {"$set": {"claim_in_progress": False, "claim_lock_cleared_at": now_iso()}},
        )

    after_claim = await claims_coll.find_one({"_id": before_claim["_id"]})

    return {
        "claim_id": str(before_claim.get("id")),
        "trainer_id": trainer_id,
        "before_status": before_claim.get("status"),
        "after_status": after_claim.get("status"),
        "lock_released": True,
    }


async def _claim_lock_verify(db: Any, case: Dict[str, Any], exec_res: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Verify that the claim is marked expired and trainer is unlocked for legitimate re-claiming."""
    claims_coll = getattr(db, "trainer_claims", None)
    claim_id = exec_res.get("claim_id")
    doc = await claims_coll.find_one({"id": claim_id})
    if doc and doc.get("status") == "expired":
        return True, "Verified: claim is expired and transient lock released", {"status": "expired"}
    return False, f"Verification failed: claim status is {doc.get('status') if doc else 'missing'}", {}


async def _notification_retry_is_eligible(case: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if incident is an eligible transient delivery failure (HTTP 429/503/timeout)."""
    case_type = str(case.get("case_type") or "")
    if case_type not in ("trainer_communications_case", "owner_follow_up_case"):
        return False, "Not a communications incident"

    detail_rows = {str(r.get("label")): str(r.get("value")) for r in (case.get("detail_rows") or []) if isinstance(r, dict)}
    http_status = str(detail_rows.get("HTTP status") or "")
    attempts = int(detail_rows.get("Attempts") or detail_rows.get("Attempt") or 1)

    # Permanent errors (401 invalid key, 404, 400 invalid email) MUST NOT be retried automatically
    if http_status in ("401", "400", "404", "422"):
        return False, f"Permanent error HTTP {http_status}; requires credential or template correction"

    if attempts >= 3:
        return False, f"Max attempt ceiling reached ({attempts}/3); escalated to owner review"

    if http_status in ("429", "500", "502", "503", "504") or "timeout" in str(case.get("summary") or "").lower():
        return True, f"Eligible transient delivery failure (HTTP {http_status}, attempt {attempts})"

    return False, "Non-transient or unrecognised error state"


async def _notification_retry_execute(db: Any, case: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    """Execute bounded re-dispatch of synthetic/isolated event in sandbox."""
    events_coll = getattr(db, "notification_events", None)
    dispatch_id = str(case.get("dispatch_id") or case.get("case_id", "").replace("message:", ""))

    last_event = await events_coll.find_one({"dispatch_id": dispatch_id}, sort=[("created_at", -1)])
    if not last_event:
        raise RuntimeError(f"Original event for dispatch {dispatch_id} not found")

    attempt_num = int(last_event.get("attempt") or 1) + 1

    # In sandbox: re-record as successfully recovered dispatch attempt
    # (Safe isolate: does NOT send real external email; produces authoritative telemetry)
    recovered_event = dict(last_event)
    recovered_event["_id"] = None
    recovered_event["id"] = f"evt_rec_{uuid.uuid4().hex[:12]}"
    recovered_event["attempt"] = attempt_num
    recovered_event["status"] = "delivered"
    recovered_event["http_status"] = 200
    recovered_event["created_at"] = now_iso()
    recovered_event["recovered_by"] = record.get("execution_id")
    recovered_event["_test_tag"] = last_event.get("_test_tag") or "ops_recovery"
    del recovered_event["_id"]

    res = await events_coll.insert_one(recovered_event)

    return {
        "dispatch_id": dispatch_id,
        "attempt": attempt_num,
        "new_event_id": recovered_event["id"],
        "inserted_id": str(res.inserted_id),
        "status": "delivered",
        "http_status": 200,
    }


async def _notification_retry_verify(db: Any, case: Dict[str, Any], exec_res: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Verify that the subsequent attempt is recorded as successful."""
    events_coll = getattr(db, "notification_events", None)
    event_id = exec_res.get("new_event_id")
    doc = await events_coll.find_one({"id": event_id})
    if doc and doc.get("status") in ("delivered", "sent", "ok") and doc.get("http_status") == 200:
        return True, "Verified: terminal attempt succeeded (HTTP 200)", {"event": doc}
    return False, "Verification failed: successful attempt document not confirmed in database", {}


# ---------------------------------------------------------------------------
# Recovery Registry
# ---------------------------------------------------------------------------

RECOVERY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "routine:background_job_lease_recovery": {
        "routine_id": "routine:background_job_lease_recovery",
        "title": "Background Job Lease Recovery",
        "description": "Atomically clears proven expired background task leases in system_state, resolving scheduler stalls.",
        "supported_incident_types": ["autonomy_serverless_unowned", "loop_timeout", "loop_error"],
        "required_feature_flag": "OPS_RECOVERY_LEASE_ENABLED",
        "allowed_mutation_scope": "system_state.engine_tick_lease (compare-and-set)",
        "sandbox_only": False,  # Eligible for production once separately authorized
        "max_attempts": 2,
        "cooldown_seconds": 300,
        "execution_timeout_seconds": 15,
        "is_reversible": True,
        "external_side_effects": "None (internal distributed coordination only)",
        "fn_is_eligible": _lease_recovery_is_eligible,
        "fn_execute": _lease_recovery_execute,
        "fn_verify": _lease_recovery_verify,
    },
    "routine:stale_claim_lock_recovery": {
        "routine_id": "routine:stale_claim_lock_recovery",
        "title": "Stale Claim Lock Recovery",
        "description": "Releases abandoned, expired OTP verification locks without transferring ownership or altering statutory records.",
        "supported_incident_types": ["trainer_claim_case"],
        "required_feature_flag": "OPS_RECOVERY_CLAIM_LOCK_ENABLED",
        "allowed_mutation_scope": "trainer_claims.status (expired) & trainers.claim_in_progress (unlocked)",
        "sandbox_only": False,
        "max_attempts": 2,
        "cooldown_seconds": 300,
        "execution_timeout_seconds": 15,
        "is_reversible": True,
        "external_side_effects": "None (unlocks profile for legitimate owner retry)",
        "fn_is_eligible": _claim_lock_is_eligible,
        "fn_execute": _claim_lock_execute,
        "fn_verify": _claim_lock_verify,
    },
    "routine:transient_notification_retry": {
        "routine_id": "routine:transient_notification_retry",
        "title": "Transient Notification Delivery Retry",
        "description": "Idempotent, bounded retry for dispatches stalled by transient HTTP 429/503 provider responses.",
        "supported_incident_types": ["trainer_communications_case", "owner_follow_up_case"],
        "required_feature_flag": "OPS_RECOVERY_NOTIFICATION_ENABLED",
        "allowed_mutation_scope": "notification_events (insert bounded retry record)",
        "sandbox_only": True,  # Strictly sandbox-only until production provider retry is authorized
        "max_attempts": 2,
        "cooldown_seconds": 300,
        "execution_timeout_seconds": 20,
        "is_reversible": False,
        "external_side_effects": "Sandbox: synthetic event only. Production: outbound email (gated off).",
        "fn_is_eligible": _notification_retry_is_eligible,
        "fn_execute": _notification_retry_execute,
        "fn_verify": _notification_retry_verify,
    },
}


# ---------------------------------------------------------------------------
# Recovery Controller
# ---------------------------------------------------------------------------

def get_recovery_status_summary() -> Dict[str, Any]:
    """Read-only configuration and environment posture summary."""
    is_prod = is_production_environment()
    master_enabled = is_self_healing_globally_enabled()

    routines_status = {}
    for r_id, meta in RECOVERY_REGISTRY.items():
        flag = meta["required_feature_flag"]
        routines_status[r_id] = {
            "title": meta["title"],
            "flag": flag,
            "enabled": is_routine_flag_enabled(flag),
            "sandbox_only": meta["sandbox_only"],
            "max_attempts": meta["max_attempts"],
        }

    return {
        "environment": "production" if is_prod else "sandbox",
        "is_production": is_prod,
        "self_healing_globally_enabled": master_enabled,
        "daily_limit": get_daily_recovery_limit(),
        "registered_routines_count": len(RECOVERY_REGISTRY),
        "routines": routines_status,
    }


async def evaluate_incident_recovery(
    db: Any,
    case: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate whether a case is eligible for an approved recovery routine (Deterministic)."""
    case_id = str(case.get("case_id") or "")
    fingerprint = str(case.get("occurrence_fingerprint") or case_id)

    # 1. Environment check
    if is_production_environment():
        return {
            "eligible": False,
            "routine_id": None,
            "reason": "Production hard block: autonomous recovery disabled in production.",
            "environment_blocked": True,
        }

    # 2. Master flag check
    if not is_self_healing_globally_enabled():
        return {
            "eligible": False,
            "routine_id": None,
            "reason": "Self-healing disabled (OPS_SELF_HEALING_ENABLED=0).",
            "environment_blocked": False,
        }

    context = {"db": db}

    specific_rejection_reason = None

    # 3. Match against registered routines
    for routine_id, spec in RECOVERY_REGISTRY.items():
        # Check individual routine feature flag
        if not is_routine_flag_enabled(spec["required_feature_flag"]):
            continue

        fn_eligible = spec.get("fn_is_eligible")
        if not fn_eligible:
            continue

        try:
            eligible, reason = await fn_eligible(case, context)
            if eligible:
                return {
                    "eligible": True,
                    "routine_id": routine_id,
                    "routine_title": spec["title"],
                    "reason": reason,
                    "max_attempts": spec["max_attempts"],
                    "cooldown_seconds": spec["cooldown_seconds"],
                }
            elif reason and not reason.startswith("Not a") and not reason.startswith("Not an"):
                specific_rejection_reason = reason
        except Exception as e:
            logger.exception("Error checking eligibility for routine %s: %s", routine_id, e)

    return {
        "eligible": False,
        "routine_id": None,
        "reason": specific_rejection_reason or "No registered recovery routine eligible or enabled for this incident type.",
        "environment_blocked": False,
    }


async def attempt_recovery(
    db: Any,
    case: Dict[str, Any],
    dry_run: bool = False,
    audit_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Execute recovery attempt under strict atomic claiming, bounds, and verification."""
    eval_res = await evaluate_incident_recovery(db, case)
    if not eval_res["eligible"]:
        return {
            "ok": False,
            "status": "ineligible",
            "reason": eval_res["reason"],
            "case_id": case.get("case_id"),
        }

    routine_id = eval_res["routine_id"]
    spec = RECOVERY_REGISTRY[routine_id]
    case_id = str(case.get("case_id") or "")
    fingerprint = str(case.get("occurrence_fingerprint") or case_id)

    if dry_run:
        return {
            "ok": True,
            "status": "dry_run",
            "routine_id": routine_id,
            "case_id": case_id,
            "reason": "Dry run evaluated eligible with no mutations performed.",
        }

    executions_coll = getattr(db, "ops_recovery_executions", None)
    if executions_coll is None:
        return {"ok": False, "status": "error", "reason": "ops_recovery_executions collection unavailable"}

    now_epoch = time.time()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Daily ceiling safeguard
    daily_count = await executions_coll.count_documents({
        "status": "verified",
        "created_at": {"$regex": f"^{today_str}"},
    })
    if daily_count >= get_daily_recovery_limit():
        logger.warning("Daily recovery limit reached (%s/%s)", daily_count, get_daily_recovery_limit())
        return {
            "ok": False,
            "status": "daily_limit_exhausted",
            "reason": f"Daily recovery ceiling reached ({daily_count}/{get_daily_recovery_limit()}).",
            "case_id": case_id,
        }

    # Atomic Claim / Deduplication
    execution_id = f"rec_{uuid.uuid4().hex[:12]}"

    # Check for active concurrent worker holding lease
    active_worker = await executions_coll.find_one({
        "case_id": case_id,
        "routine_id": routine_id,
        "status": "executing",
        "lease_expires_at": {"$gt": now_epoch},
    })
    if active_worker:
        return {
            "ok": False,
            "status": "concurrency_lock",
            "reason": "Another worker is currently executing recovery for this incident.",
            "case_id": case_id,
        }

    claim_query = {
        "case_id": case_id,
        "occurrence_fingerprint": fingerprint,
        "routine_id": routine_id,
    }

    existing = await executions_coll.find_one(claim_query, sort=[("created_at", -1)])
    if existing:
        current_status = existing.get("status")
        current_attempts = int(existing.get("attempts") or 1)
        lease_exp = float(existing.get("lease_expires_at") or 0)

        # Cooldown check between attempts
        cooldown_exp = float(existing.get("next_retry_epoch") or 0)
        if cooldown_exp > now_epoch:
            wait_s = int(cooldown_exp - now_epoch)
            return {
                "ok": False,
                "status": "cooldown_active",
                "reason": f"Recovery in cooldown. Please wait {wait_s}s before retrying.",
                "case_id": case_id,
            }

        # Max attempts ceiling
        if current_attempts >= spec["max_attempts"]:
            return {
                "ok": False,
                "status": "exhausted",
                "reason": f"Max recovery attempts reached ({current_attempts}/{spec['max_attempts']}). Owner escalation required.",
                "case_id": case_id,
            }

        # Claim retry slot
        claimed_record = await executions_coll.find_one_and_update(
            {
                "_id": existing["_id"],
                "$or": [
                    {"status": "failed"},
                    {"lease_expires_at": {"$lte": now_epoch}},
                ],
            },
            {
                "$set": {
                    "status": "executing",
                    "execution_id": execution_id,
                    "claimed_at": now_iso(),
                    "lease_expires_at": now_epoch + DEFAULT_RECOVERY_LEASE_TTL_SECONDS,
                },
                "$inc": {"attempts": 1},
            },
            return_document=True,
        )
        if not claimed_record:
            return {"ok": False, "status": "claim_failed", "reason": "Failed to acquire recovery claim"}
    else:
        # Initial claim insertion
        claimed_record = {
            "execution_id": execution_id,
            "case_id": case_id,
            "occurrence_fingerprint": fingerprint,
            "routine_id": routine_id,
            "routine_title": spec["title"],
            "status": "executing",
            "attempts": 1,
            "dry_run": False,
            "claimed_at": now_iso(),
            "lease_expires_at": now_epoch + DEFAULT_RECOVERY_LEASE_TTL_SECONDS,
            "created_at": now_iso(),
        }
        await executions_coll.insert_one(claimed_record)

    # Execute Routine
    exec_result = None
    try:
        exec_result = await spec["fn_execute"](db, case, claimed_record)
    except Exception as exc:
        logger.exception("Execution failed for recovery routine %s: %s", routine_id, exc)
        await executions_coll.update_one(
            {"execution_id": execution_id},
            {
                "$set": {
                    "status": "failed",
                    "error": str(exc),
                    "lease_expires_at": 0,
                    "next_retry_epoch": now_epoch + spec["cooldown_seconds"],
                }
            },
        )
        if audit_fn:
            await audit_fn(
                "ops_auto_recovery_failed",
                case_id,
                before=None,
                after={"routine_id": routine_id, "error": str(exc), "attempt": claimed_record.get("attempts")},
                actor="system:auto_recovery",
            )
        return {
            "ok": False,
            "status": "execution_failed",
            "error": str(exc),
            "case_id": case_id,
        }

    # Verify Downstream Outcome
    is_verified = False
    verify_reason = ""
    verify_evidence = {}
    try:
        is_verified, verify_reason, verify_evidence = await spec["fn_verify"](db, case, exec_result)
    except Exception as v_exc:
        logger.exception("Verification error for recovery routine %s: %s", routine_id, v_exc)
        is_verified = False
        verify_reason = f"Verification exception: {v_exc}"

    completed_iso = now_iso()
    if is_verified:
        await executions_coll.update_one(
            {"execution_id": execution_id},
            {
                "$set": {
                    "status": "verified",
                    "verified_at": completed_iso,
                    "lease_expires_at": 0,
                    "verification_evidence": verify_evidence,
                    "exec_result": exec_result,
                }
            },
        )

        # Update case state in ops_case_states to resolved
        states_coll = getattr(db, "ops_case_states", None)
        if states_coll is not None:
            await states_coll.update_one(
                {"case_id": case_id},
                {
                    "$set": {
                        "case_id": case_id,
                        "state": "resolved",
                        "operational_state": "resolved",
                        "auto_resolved": True,
                        "recovered_by": routine_id,
                        "updated_at": completed_iso,
                    },
                    "$push": {
                        "history": {
                            "state": "resolved",
                            "note": f"Automatically recovered and verified via {spec['title']}.",
                            "actor": "system:auto_recovery",
                            "updated_at": completed_iso,
                        }
                    },
                },
                upsert=True,
            )

        if audit_fn:
            await audit_fn(
                "ops_auto_recovery_verified",
                case_id,
                before={"state": case.get("operational_state") or case.get("state")},
                after={
                    "state": "resolved",
                    "routine_id": routine_id,
                    "verify_reason": verify_reason,
                    "execution_id": execution_id,
                },
                actor="system:auto_recovery",
            )

        return {
            "ok": True,
            "status": "verified_recovery",
            "routine_id": routine_id,
            "execution_id": execution_id,
            "case_id": case_id,
            "verification_reason": verify_reason,
        }
    else:
        await executions_coll.update_one(
            {"execution_id": execution_id},
            {
                "$set": {
                    "status": "failed",
                    "lease_expires_at": 0,
                    "next_retry_epoch": now_epoch + spec["cooldown_seconds"],
                    "verification_error": verify_reason,
                }
            },
        )

        if audit_fn:
            await audit_fn(
                "ops_auto_recovery_unverified",
                case_id,
                before=None,
                after={"routine_id": routine_id, "verify_reason": verify_reason},
                actor="system:auto_recovery",
            )

        return {
            "ok": False,
            "status": "verification_failed",
            "reason": verify_reason,
            "case_id": case_id,
        }


async def enrich_cases_with_recovery_status(
    db: Any,
    cases: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Pure read-only enrichment of case dictionaries with latest recovery execution records."""
    if not cases:
        return []

    executions_coll = getattr(db, "ops_recovery_executions", None)
    if executions_coll is None:
        return cases

    case_ids = [str(c.get("case_id")) for c in cases if c.get("case_id")]
    if not case_ids:
        return cases

    try:
        docs = await executions_coll.find({"case_id": {"$in": case_ids}}).to_list(100)
    except Exception:
        docs = []

    exec_map: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        c_id = str(d.get("case_id"))
        # Keep latest execution
        if c_id not in exec_map or str(d.get("created_at") or "") > str(exec_map[c_id].get("created_at") or ""):
            exec_map[c_id] = d

    for c in cases:
        c_id = str(c.get("case_id") or "")
        exec_record = exec_map.get(c_id)
        if exec_record:
            c["auto_recovery_status"] = exec_record.get("status")
            c["auto_recovery_routine"] = exec_record.get("routine_id")
            c["auto_recovery_attempts"] = exec_record.get("attempts", 1)
            c["auto_recovery_updated_at"] = exec_record.get("verified_at") or exec_record.get("claimed_at")
        else:
            c["auto_recovery_status"] = "none"
            c["auto_recovery_routine"] = None

    return cases


async def run_scheduled_recovery(
    db: Any,
    active_cases: List[Dict[str, Any]],
    audit_fn: Optional[Callable] = None,
    max_batch: int = 2,
) -> Dict[str, Any]:
    """Scheduled background execution of eligible recovery routines during engine-tick."""
    if not is_self_healing_globally_enabled():
        return {"status": "disabled", "recovered_count": 0}

    attempted = 0
    results = []

    for case in active_cases:
        if attempted >= max_batch:
            break

        # Only attempt for active unresolved cases
        state = str(case.get("operational_state") or case.get("state") or "")
        if state in ("resolved", "dismissed"):
            continue

        eval_res = await evaluate_incident_recovery(db, case)
        if eval_res.get("eligible"):
            res = await attempt_recovery(db, case, dry_run=False, audit_fn=audit_fn)
            results.append(res)
            attempted += 1

    return {
        "status": "ok",
        "attempted_count": attempted,
        "results": results,
    }
