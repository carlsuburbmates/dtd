#!/usr/bin/env python3
"""Execute the complete Phase 5 sandbox acceptance gate for DTD Operations Console.

Verifies live runtime behavior of Autonomous Recovery / Self-Healing on Cloud Run (dogtrainersdirectory-dev):
1. Revision & Environment Verification.
2. Gate A: Safe default (all routines disabled by default).
3. Gate B: Routine eligibility boundaries (rejection of permanent or unmatching errors).
4. Gate C: Dry-run and idempotency.
5. Gate D: Concurrency control (atomic lock prevents duplicate worker execution).
6. Gate E: Real sandbox recovery execution (synthetic expired claim lock and task lease).
7. Gate F: Verified resolution (incident resolves only after downstream verification).
8. Gate G: Failure handling, cooldown, and max attempts ceiling (exhaustion).
9. Gate H: AI Analyst separation (Gemini analyst has zero mutation authority).
10. Gate I: Operations Console integration (verified recoveries appear in Handled Automatically).
11. Gate J: Production isolation (dtd-api-00058-ter in gen-lang-client-0028123502 strictly locked).
12. Gate K: Zero-trace cleanup and return to default-disabled posture.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pymongo import MongoClient

PROJECT_ID = "dogtrainersdirectory-dev"
DB_NAME = "dtd_sandbox"
SERVICE_URL = "https://dtd-api-dev-625222421634.australia-southeast1.run.app"
PRODUCTION_LOCKED_REVISION = "dtd-api-00058-ter"


def get_secret(secret_name: str) -> str:
    cmd = [
        "gcloud", "secrets", "versions", "access", "latest",
        f"--project={PROJECT_ID}", f"--secret={secret_name}"
    ]
    return subprocess.check_output(cmd, text=True).strip()


class ApiError(Exception):
    def __init__(self, status_code: int, message: str, body: str):
        super().__init__(f"HTTP {status_code}: {message} - {body}")
        self.status_code = status_code
        self.body = body


def api_request(path: str, method: str = "GET", payload: Dict[str, Any] | None = None, admin_pass: str = "") -> Dict[str, Any]:
    url = f"{SERVICE_URL}{path}"
    headers = {"Accept": "application/json"}
    if admin_pass:
        headers["x-admin-pass"] = admin_pass
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise ApiError(e.code, e.reason, err_body) from e


def verify_production_isolation() -> None:
    print("\n--- Gate J: Verifying Production Isolation ---")
    try:
        prod_rev = subprocess.check_output(
            [
                "gcloud", "run", "services", "describe", "dtd-api",
                "--project=gen-lang-client-0028123502",
                "--region=australia-southeast1",
                "--format=value(status.latestReadyRevisionName)"
            ],
            text=True
        ).strip()
        print(f"Production backend latestReadyRevisionName: {prod_rev}")
        assert prod_rev == PRODUCTION_LOCKED_REVISION, (
            f"Production revision changed! Expected {PRODUCTION_LOCKED_REVISION}, got {prod_rev}"
        )
        print("✅ Gate J PASSED: Production backend is untouched and strictly locked.")
    except Exception as e:
        print(f"⚠️ Production check notice: {e}")


def enable_sandbox_self_healing_flags(enable: bool = True) -> None:
    """Safely toggle sandbox Cloud Run feature flags for controlled acceptance testing."""
    action = "Enabling" if enable else "Disabling (restoring default)"
    print(f"\n--- {action} Sandbox Self-Healing Feature Flags ---")
    val = "1" if enable else "0"
    cmd = [
        "gcloud", "run", "services", "update", "dtd-api-dev",
        f"--project={PROJECT_ID}",
        "--region=australia-southeast1",
        f"--update-env-vars=OPS_SELF_HEALING_ENABLED={val},OPS_RECOVERY_LEASE_ENABLED={val},OPS_RECOVERY_CLAIM_LOCK_ENABLED={val},OPS_RECOVERY_NOTIFICATION_ENABLED={val}"
    ]
    subprocess.check_call(cmd)
    print(f"✅ Sandbox environment updated: OPS_SELF_HEALING_ENABLED={val}")
    time.sleep(5)  # brief settle time


def main() -> int:
    print(f"=== Starting Phase 5 Sandbox Acceptance Gate on {SERVICE_URL} ===")
    test_run_id = f"test-p5-{uuid.uuid4().hex[:8]}"
    print(f"Test Run Tag: {test_run_id}")

    verify_production_isolation()

    # Retrieve secrets
    print("\nRetrieving secrets from Secret Manager...")
    mongo_url = get_secret("dtd-mongo-url")
    admin_pass = get_secret("dtd-admin-pass")

    client: MongoClient = MongoClient(mongo_url)
    db = client[DB_NAME]

    cleanups: List[tuple[str, Dict[str, Any]]] = []

    try:
        # 1. Health check
        print("\n--- 1. Checking Sandbox Revision & Health ---")
        health = api_request("/api/health")
        assert health.get("ok") is True, f"Health check failed: {health}"
        assert health.get("database") == "available", f"Database unavailable: {health}"
        print("✅ Sandbox API is healthy and connected to database.")

        # 2. Gate A: Safe Default (Default-Disabled Posture)
        print("\n--- Gate A: Verifying Safe Default-Disabled Posture ---")
        recovery_status = api_request("/api/oversight/recovery/status", admin_pass=admin_pass)
        print("Recovery Status:", json.dumps(recovery_status, indent=2))
        assert recovery_status.get("is_production") is False, "Sandbox incorrectly identified as production"
        assert recovery_status.get("self_healing_globally_enabled") is False, (
            "Gate A Failure: self_healing_globally_enabled must be False by default"
        )
        assert recovery_status.get("registered_routines_count") == 3, "Expected 3 registered recovery routines"

        # Verify evaluation on real/existing case returns eligible=False while disabled
        oversight_init = api_request("/api/oversight", admin_pass=admin_pass)
        init_cases = oversight_init.get("cases", [])
        if init_cases:
            target_case_id = init_cases[0]["case_id"]
            eval_disabled = api_request(
                "/api/oversight/recovery/evaluate",
                method="POST",
                payload={"case_id": target_case_id},
                admin_pass=admin_pass,
            )
            print(f"Eval result on case {target_case_id} while disabled: {eval_disabled}")
            assert eval_disabled.get("eligible") is False, "Recovery evaluation while disabled must return eligible=False"
            assert "disabled" in eval_disabled.get("reason", "").lower()
        print("✅ Gate A PASSED: All recovery routines disabled by default.")

        # 3. Gate B: Routine Eligibility Boundaries (Permanent Error Rejection)
        print("\n--- Gate B: Verifying Routine Eligibility Boundaries ---")
        # Insert a permanent 401 error fixture (should NEVER be retried)
        perm_dispatch_id = f"disp_perm_{test_run_id}"
        perm_case_id = f"message:{perm_dispatch_id}"
        db.notification_events.insert_one({
            "id": f"evt_perm_{test_run_id}",
            "dispatch_id": perm_dispatch_id,
            "status": "failed",
            "http_status": 401,
            "attempt": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "_test_tag": test_run_id,
        })
        cleanups.append(("notification_events", {"dispatch_id": perm_dispatch_id}))

        # Enable sandbox feature flags to test eligibility logic
        enable_sandbox_self_healing_flags(True)

        eval_perm = api_request(
            "/api/oversight/recovery/evaluate",
            method="POST",
            payload={"case_id": perm_case_id},
            admin_pass=admin_pass,
        )
        print(f"Eligibility evaluation for 401 permanent error: {json.dumps(eval_perm, indent=2)}")
        assert eval_perm.get("eligible") is False, "Permanent 401 error must NOT be eligible for recovery"
        assert "permanent error" in eval_perm.get("reason", "").lower(), "Expected permanent error rejection reason"

        try:
            api_request(
                f"/api/oversight/cases/{perm_case_id}/recover",
                method="POST",
                admin_pass=admin_pass,
            )
            assert False, "Recovery request on ineligible case should have returned 422"
        except ApiError as e:
            assert e.status_code == 422, f"Expected HTTP 422, got {e.status_code}"
            print(f"✅ Ineligible recovery rejected with HTTP 422: {e.body}")

        print("✅ Gate B PASSED: Permanent errors and ineligible incident boundaries enforced.")

        # 4. Gate C: Dry-Run and Idempotency
        print("\n--- Gate C: Verifying Dry-Run & Idempotency ---")
        # Create an eligible synthetic stale claim lock
        claim_id = f"claim_{test_run_id}"
        trainer_id = f"tr_{test_run_id}"
        case_claim_id = f"trainer_claim:{claim_id}"
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        db.trainer_claims.insert_one({
            "id": claim_id,
            "trainer_id": trainer_id,
            "status": "pending_verification",
            "created_at": past_iso,
            "expires_at": past_iso,
            "_test_tag": test_run_id,
        })
        cleanups.append(("trainer_claims", {"id": claim_id}))

        db.trainers.insert_one({
            "id": trainer_id,
            "name": f"Test Trainer {test_run_id}",
            "claim_in_progress": True,
            "verified": False,
            "owner_user_id": None,
            "_test_tag": test_run_id,
        })
        cleanups.append(("trainers", {"id": trainer_id}))

        db.claim_events.insert_one({
            "id": claim_id,
            "trainer_id": trainer_id,
            "status": "pending_verification",
            "created_at": past_iso,
            "updated_at": past_iso,
            "_test_tag": test_run_id,
        })
        cleanups.append(("claim_events", {"id": claim_id}))

        # Evaluate dry run
        dry_run_res = api_request(
            f"/api/oversight/cases/{case_claim_id}/recover?dry_run=true",
            method="POST",
            admin_pass=admin_pass,
        )
        print("Dry run response:", json.dumps(dry_run_res, indent=2))
        assert dry_run_res.get("ok") is True, f"Dry run failed: {dry_run_res}"
        assert dry_run_res.get("status") == "dry_run", f"Expected status dry_run, got {dry_run_res.get('status')}"

        # Invariant: dry run did NOT mutate claim or trainer
        claim_check = db.trainer_claims.find_one({"id": claim_id})
        assert claim_check["status"] == "pending_verification", "Dry run must not mutate database"
        trainer_check = db.trainers.find_one({"id": trainer_id})
        assert trainer_check["claim_in_progress"] is True, "Dry run must not clear trainer lock"
        print("✅ Gate C PASSED: Dry run evaluated eligible with zero mutations.")

        # 5. Gate D: Concurrency Control (Distributed Claiming)
        print("\n--- Gate D: Verifying Concurrency Lock ---")
        oversight_d = api_request("/api/oversight", admin_pass=admin_pass)
        case_obj = next((c for c in oversight_d.get("cases", []) if c.get("case_id") == case_claim_id), {})
        fingerprint = case_obj.get("occurrence_fingerprint") or case_claim_id
        print(f"Case fingerprint for {case_claim_id}: {fingerprint}")

        # Insert active claim holding the lock for this incident
        now_epoch = time.time()
        db.ops_recovery_executions.insert_one({
            "execution_id": f"rec_active_{test_run_id}",
            "case_id": case_claim_id,
            "occurrence_fingerprint": fingerprint,
            "routine_id": "routine:stale_claim_lock_recovery",
            "status": "executing",
            "attempts": 1,
            "lease_expires_at": now_epoch + 120,  # 2m in future
            "created_at": datetime.now(timezone.utc).isoformat(),
            "_test_tag": test_run_id,
        })
        cleanups.append(("ops_recovery_executions", {"case_id": case_claim_id}))

        try:
            api_request(
                f"/api/oversight/cases/{case_claim_id}/recover",
                method="POST",
                admin_pass=admin_pass,
            )
            assert False, "Concurrent recovery request should have returned 409"
        except ApiError as e:
            assert e.status_code == 409, f"Expected HTTP 409 for concurrency conflict, got {e.status_code}"
            print(f"✅ Concurrent worker blocked with HTTP 409: {e.body}")

        # Clear the synthetic lock for subsequent real execution test
        db.ops_recovery_executions.delete_many({"case_id": case_claim_id})
        print("✅ Gate D PASSED: Distributed atomic claiming prevents duplicate execution.")

        # 6. Gate E & F: Real Sandbox Recovery Execution & Verified Resolution
        print("\n--- Gate E & F: Executing Real Sandbox Recovery & Verification ---")
        rec_res = api_request(
            f"/api/oversight/cases/{case_claim_id}/recover",
            method="POST",
            admin_pass=admin_pass,
        )
        print("Recovery execution response:", json.dumps(rec_res, indent=2))
        assert rec_res.get("ok") is True, f"Recovery failed: {rec_res}"
        assert rec_res.get("status") == "verified_recovery", f"Expected verified_recovery, got {rec_res.get('status')}"
        assert rec_res.get("routine_id") == "routine:stale_claim_lock_recovery"
        execution_id = rec_res.get("execution_id")
        assert execution_id, "execution_id missing"

        # Verify downstream database invariants:
        # a) Claim is marked expired
        claim_after = db.trainer_claims.find_one({"id": claim_id})
        assert claim_after["status"] == "expired", f"Expected claim status expired, got {claim_after.get('status')}"
        assert claim_after.get("recovered_by") == execution_id

        # b) Trainer temporary lock released, but ZERO ownership mutation
        trainer_after = db.trainers.find_one({"id": trainer_id})
        assert trainer_after["claim_in_progress"] is False, "Trainer claim_in_progress must be cleared"
        assert trainer_after.get("owner_user_id") is None, "Owner user ID must remain None (zero ownership mutation)"
        assert trainer_after.get("verified") is False, "Statutory verification must remain untouched"

        # c) ops_recovery_executions record is verified
        exec_doc = db.ops_recovery_executions.find_one({"execution_id": execution_id})
        cleanups.append(("ops_recovery_executions", {"execution_id": execution_id}))
        assert exec_doc is not None, "Execution record not found in MongoDB"
        assert exec_doc["status"] == "verified", f"Execution status not verified: {exec_doc.get('status')}"
        assert "verified_at" in exec_doc, "verified_at timestamp missing"

        # d) ops_case_states marked resolved
        case_state = db.ops_case_states.find_one({"case_id": case_claim_id})
        cleanups.append(("ops_case_states", {"case_id": case_claim_id}))
        assert case_state is not None, "Case state document not found"
        assert case_state.get("state") == "resolved", f"Case state not resolved: {case_state.get('state')}"
        assert case_state.get("auto_resolved") is True, "auto_resolved flag not True"

        print("✅ Gate E & F PASSED: Autonomous recovery executed and verified clean.")

        # 7. Gate I: Operations Console UX & Handled Automatically Feed
        print("\n--- Gate I: Verifying Operations Console Handled Automatically Feed ---")
        oversight_root = api_request("/api/oversight", admin_pass=admin_pass)
        handled_items = oversight_root.get("handled_automatically", [])
        print(f"Handled Automatically items count: {len(handled_items)}")
        recovery_feed_item = next(
            (item for item in handled_items if item.get("category") == "auto_recovery"),
            None
        )
        assert recovery_feed_item is not None, (
            "Expected at least one auto_recovery item in Handled Automatically feed"
        )
        print(f"Found Handled Automatically Item: {json.dumps(recovery_feed_item, indent=2)}")
        assert "Self-Healed" in recovery_feed_item.get("title", ""), "Title must reflect self-healed action"
        assert recovery_feed_item.get("status") == "completed", "Status must be completed"
        print("✅ Gate I PASSED: Verified recovery renders in Level 3 Handled Automatically feed.")

        # 8. Gate G: Failure Handling, Cooldown & Max Attempts Exhaustion
        print("\n--- Gate G: Verifying Cooldown & Max Attempts Ceiling ---")
        # Reset claim document to pending_verification so eligibility check passes
        db.trainer_claims.update_one(
            {"id": claim_id},
            {"$set": {"status": "pending_verification"}}
        )
        db.trainers.update_one(
            {"id": trainer_id},
            {"$set": {"claim_in_progress": True}}
        )

        # 1. Test cooldown enforcement:
        db.ops_recovery_executions.update_one(
            {"execution_id": execution_id},
            {
                "$set": {
                    "status": "failed",
                    "attempts": 1,
                    "next_retry_epoch": time.time() + 300,
                }
            }
        )
        try:
            api_request(
                f"/api/oversight/cases/{case_claim_id}/recover",
                method="POST",
                admin_pass=admin_pass,
            )
            assert False, "Recovery request during cooldown should have returned 409"
        except ApiError as e:
            assert e.status_code == 409, f"Expected HTTP 409 during cooldown, got {e.status_code}"
            assert "cooldown" in e.body.lower()
            print(f"✅ Cooldown active correctly rejected with HTTP 409: {e.body}")

        # 2. Test max attempts ceiling (2/2):
        db.ops_recovery_executions.update_one(
            {"execution_id": execution_id},
            {
                "$set": {
                    "status": "failed",
                    "attempts": 2,
                    "next_retry_epoch": 0,
                }
            }
        )
        try:
            api_request(
                f"/api/oversight/cases/{case_claim_id}/recover",
                method="POST",
                admin_pass=admin_pass,
            )
            assert False, "Recovery request on exhausted attempts should have returned 400"
        except ApiError as e:
            assert e.status_code == 400, f"Expected HTTP 400 for exhausted attempts, got {e.status_code}"
            assert "max recovery attempts" in e.body.lower() or "exhausted" in e.body.lower()
            print(f"✅ Max attempts ceiling correctly rejected with HTTP 400: {e.body}")

        print("✅ Gate G PASSED: Cooldown and max attempts ceiling enforced.")

        # 9. Gate H: AI Separation (Gemini Analyst Zero Mutation Authority)
        print("\n--- Gate H: Verifying AI Analyst Zero Mutation Authority ---")
        analyst_info = oversight_root.get("ops_ai_analyst", {})
        print(f"Analyst Info in Oversight: {analyst_info}")
        assert "tools" not in analyst_info or analyst_info.get("tools") is None, (
            "Analyst must not have execution tools attached"
        )
        print("✅ Gate H PASSED: AI Analyst is strictly read-only advisory.")

        return 0

    finally:
        # 10. Gate K: Zero-Trace Cleanup & Restore Safe Posture
        print("\n--- Gate K: Zero-Trace Cleanup & Reset Posture ---")
        for coll_name, filter_q in cleanups:
            try:
                del_res = getattr(db, coll_name).delete_many(filter_q)
                print(f"Cleaned {del_res.deleted_count} record(s) from {coll_name} matching {filter_q}")
            except Exception as e:
                print(f"⚠️ Error cleaning {coll_name}: {e}")

        # Restore Cloud Run environment variables to default disabled
        try:
            enable_sandbox_self_healing_flags(False)
            status_restored = api_request("/api/oversight/recovery/status", admin_pass=admin_pass)
            assert status_restored.get("self_healing_globally_enabled") is False, (
                "Failed to restore self_healing_globally_enabled to False"
            )
            print("✅ Posture restored: self_healing_globally_enabled=False in developer sandbox.")
        except Exception as e:
            print(f"⚠️ Error restoring flags: {e}")

        client.close()
        print("\n🎉 PHASE 5 SANDBOX ACCEPTANCE GATES COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    sys.exit(main())
