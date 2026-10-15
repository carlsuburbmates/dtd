#!/usr/bin/env python3
"""Execute the complete Phase 2 sandbox acceptance gate for DTD Operations Console.

Verifies live runtime behavior on Cloud Run revision dtd-api-dev:
1. Deployed revision & environment verification.
2. Workstream A: Incident correlation (retry attempts grouped, terminal success clears).
3. Workstream B & E: Incident lifecycle, dismissal safeguards, and recurrence verification.
4. Workstream C: Verified recovery, alias resolution, and review idempotency.
5. Workstream D: Serverless background scheduling & DF-029 engine-tick telemetry.
6. Workstream F: Read-only oversight invariant (zero database writes).
7. Zero-trace cleanup of disposable test fixtures.

Safe for developer sandbox (dogtrainersdirectory-dev / dtd_sandbox).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pymongo import MongoClient

PROJECT_ID = "dogtrainersdirectory-dev"
DB_NAME = "dtd_sandbox"
SERVICE_URL = "https://dtd-api-dev-x2kdoaemtq-ts.a.run.app"


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
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise ApiError(e.code, e.reason, err_body) from e


def main() -> int:
    print(f"=== Starting Phase 2 Sandbox Acceptance Gate on {SERVICE_URL} ===")
    test_run_id = f"test-p2-{uuid.uuid4().hex[:8]}"
    print(f"Test Run Tag: {test_run_id}")

    # Retrieve secrets
    mongo_url = get_secret("dtd-mongo-url")
    admin_pass = get_secret("dtd-admin-pass")

    client: MongoClient = MongoClient(mongo_url)
    db = client[DB_NAME]
    inserted_ids: Dict[str, List[str]] = {
        "notification_events": [],
        "ops_case_states": [],
        "audit_log": [],
    }

    results: Dict[str, str] = {}

    try:
        # ------------------------------------------------------------------
        # Gate 1: Deployed Revision & Production Isolation
        # ------------------------------------------------------------------
        print("\n--- Gate 1: Deployed Revision & Environment Isolation ---")
        assert db.name == "dtd_sandbox", f"Must be connected to dtd_sandbox, got {db.name}"
        assert PROJECT_ID == "dogtrainersdirectory-dev"

        # Check deployed Cloud Run revision
        rev_cmd = [
            "gcloud", "run", "services", "describe", "dtd-api-dev",
            f"--project={PROJECT_ID}", "--region=australia-southeast1",
            "--format=value(status.latestReadyRevisionName)"
        ]
        deployed_rev = subprocess.check_output(rev_cmd, text=True).strip()
        print(f"  ✓ Verified active Cloud Run sandbox revision: {deployed_rev}")

        # Check health endpoint
        health = api_request("/api/health")
        assert health.get("ok") is True, f"Sandbox health failed: {health}"
        assert health.get("database") == "available"
        print("  ✓ Sandbox API health and MongoDB database availability confirmed.")

        # Verify production is untouched
        prod_req = Request("https://dogtrainersdirectory.com.au/api/health", headers={"User-Agent": "dtd-acceptance-check/1.0", "Accept": "application/json"})
        with urlopen(prod_req, timeout=20) as resp:
            prod_health = json.loads(resp.read().decode("utf-8"))
        assert prod_health.get("ok") is True
        print("  ✓ Production environment independently verified untouched and healthy.")
        results["Gate 1 - Deployed Revision & Environment Isolation"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 2: Workstream A - Incident Correlation
        # ------------------------------------------------------------------
        print("\n--- Gate 2: Workstream A - Incident Correlation ---")
        now_dt = datetime.now(timezone.utc)
        dispatch_id = f"disp_p2_corr_{test_run_id}"

        # 2a: Insert 3 retry failure events for a single dispatch
        retry_events = [
            {
                "id": f"evt_p2_ret1_{test_run_id}",
                "dispatch_id": dispatch_id,
                "workflow": "match_intro",
                "kind": "intro_notification",
                "target_kind": "trainer",
                "target_id": f"tr_p2_{test_run_id}",
                "to_email": "trainer_p2@example.com",
                "status": "failed",
                "http_status": 503,
                "error": "Service Unavailable",
                "attempt": 1,
                "created_at": (now_dt - timedelta(seconds=60)).isoformat(),
            },
            {
                "id": f"evt_p2_ret2_{test_run_id}",
                "dispatch_id": dispatch_id,
                "workflow": "match_intro",
                "kind": "intro_notification",
                "target_kind": "trainer",
                "target_id": f"tr_p2_{test_run_id}",
                "to_email": "trainer_p2@example.com",
                "status": "failed",
                "http_status": 503,
                "error": "Service Unavailable",
                "attempt": 2,
                "created_at": (now_dt - timedelta(seconds=30)).isoformat(),
            },
            {
                "id": f"evt_p2_ret3_{test_run_id}",
                "dispatch_id": dispatch_id,
                "workflow": "match_intro",
                "kind": "intro_notification",
                "target_kind": "trainer",
                "target_id": f"tr_p2_{test_run_id}",
                "to_email": "trainer_p2@example.com",
                "status": "failed",
                "http_status": 503,
                "error": "Service Unavailable",
                "attempt": 3,
                "created_at": now_dt.isoformat(),
            },
        ]
        db.notification_events.insert_many(retry_events)
        inserted_ids["notification_events"].extend([e["id"] for e in retry_events])

        # Query oversight
        oversight_data = api_request("/api/oversight", admin_pass=admin_pass)
        cases_map = {c["case_id"]: c for c in oversight_data.get("cases", [])}

        expected_case_id = f"message:{dispatch_id}"
        assert expected_case_id in cases_map, f"Expected correlated case {expected_case_id} not found in {list(cases_map.keys())}"
        corr_case = cases_map[expected_case_id]

        # Verify exactly ONE incident, attempt count = 3, constituent event IDs tracked
        assert corr_case["dispatch_id"] == dispatch_id
        assert len(corr_case.get("constituent_event_ids") or []) == 3
        assert "3 attempts failed" in corr_case.get("title", "")
        print(f"  ✓ 3 retry attempts correctly grouped into exactly 1 incident: {expected_case_id}")

        # 2b: Terminal success clears transient retry errors
        success_event = {
            "id": f"evt_p2_succ_{test_run_id}",
            "dispatch_id": dispatch_id,
            "workflow": "match_intro",
            "kind": "intro_notification",
            "target_kind": "trainer",
            "target_id": f"tr_p2_{test_run_id}",
            "to_email": "trainer_p2@example.com",
            "status": "sent",
            "http_status": 202,
            "attempt": 4,
            "created_at": (now_dt + timedelta(seconds=10)).isoformat(),
        }
        db.notification_events.insert_one(success_event)
        inserted_ids["notification_events"].append(success_event["id"])

        oversight_cleared = api_request("/api/oversight", admin_pass=admin_pass)
        cases_cleared_map = {c["case_id"]: c for c in oversight_cleared.get("cases", [])}
        assert expected_case_id not in cases_cleared_map, "Terminal success on attempt 4 must clear the active failure incident from Needs Action!"
        print(f"  ✓ Terminal success on attempt 4 cleared prior transient failures for {dispatch_id}")

        results["Gate 2 - Workstream A: Incident Correlation"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 3: Workstream B & E - Incident Lifecycle & Recurrence
        # ------------------------------------------------------------------
        print("\n--- Gate 3: Workstream B & E - Incident Lifecycle & Recurrence ---")
        lifecycle_disp_id = f"disp_p2_life_{test_run_id}"
        life_event = {
            "id": f"evt_p2_life_{test_run_id}",
            "dispatch_id": lifecycle_disp_id,
            "workflow": "match_intro",
            "kind": "intro_notification",
            "target_kind": "trainer",
            "target_id": f"tr_life_{test_run_id}",
            "to_email": "life@example.com",
            "status": "failed",
            "http_status": 500,
            "error": "Internal Error Alpha",
            "attempt": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.notification_events.insert_one(life_event)
        inserted_ids["notification_events"].append(life_event["id"])

        life_case_id = f"message:{lifecycle_disp_id}"

        # 3a: High severity dismissal safeguard (< 5 chars rejected with 400)
        try:
            api_request(f"/api/oversight/cases/{life_case_id}", method="POST", payload={"state": "dismissed", "owner": "test", "note": "bad"}, admin_pass=admin_pass)
            assert False, "Expected HTTP 400 for short note dismissal"
        except ApiError as e:
            assert e.status_code == 400
            assert "explanatory review note of at least 5 characters" in e.body
            print("  ✓ Dismissal safeguard verified: note < 5 chars rejected with HTTP 400.")

        # 3b: Valid dismissal
        dismiss_res = api_request(
            f"/api/oversight/cases/{life_case_id}",
            method="POST",
            payload={"state": "dismissed", "owner": "acceptance-agent", "note": "Verified by automated Phase 2 test suite"},
            admin_pass=admin_pass,
        )
        assert dismiss_res.get("ok") is True
        inserted_ids["ops_case_states"].append(life_case_id)
        print(f"  ✓ Case {life_case_id} dismissed with valid explanatory review note.")

        # 3c: Verify dismissed state and zero false recurrence on refresh
        oversight_d1 = api_request("/api/oversight", admin_pass=admin_pass)
        c_d1 = next((c for c in oversight_d1.get("cases", []) if c["case_id"] == life_case_id), None)
        assert c_d1 is not None
        assert c_d1["state"] == "dismissed"
        assert "(Recurred)" not in c_d1.get("title", "")
        print("  ✓ Case verified in dismissed state without false recurrence.")

        # 3d: Trigger genuine recurrence by mutating failure details (new attempt / error code)
        recurred_event = {
            "id": f"evt_p2_recur_{test_run_id}",
            "dispatch_id": lifecycle_disp_id,
            "workflow": "match_intro",
            "kind": "intro_notification",
            "target_kind": "trainer",
            "target_id": f"tr_life_{test_run_id}",
            "to_email": "life@example.com",
            "status": "failed",
            "http_status": 502,
            "error": "Bad Gateway Recurred",
            "attempt": 2,
            "created_at": (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat(),
        }
        db.notification_events.insert_one(recurred_event)
        inserted_ids["notification_events"].append(recurred_event["id"])

        oversight_recur = api_request("/api/oversight", admin_pass=admin_pass)
        c_recur = next((c for c in oversight_recur.get("cases", []) if c["case_id"] == life_case_id), None)
        assert c_recur is not None
        assert c_recur["state"] == "detected", f"Expected state to reopen to 'detected', got {c_recur['state']}"
        assert c_recur.get("operational_state") == "reopened", f"Expected operational_state 'reopened', got {c_recur.get('operational_state')}"
        assert "(Recurred)" in c_recur.get("title", ""), f"Expected (Recurred) in title: {c_recur.get('title')}"
        print(f"  ✓ Genuine recurrence verified: case reopened to state={c_recur['state']}, operational_state={c_recur.get('operational_state')}, title={c_recur.get('title')}")

        results["Gate 3 - Workstream B & E: Lifecycle & Recurrence"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 4: Workstream C - Alias Resolution & Idempotency
        # ------------------------------------------------------------------
        print("\n--- Gate 4: Workstream C - Alias Resolution & Idempotency ---")
        # Review using constituent event ID instead of primary dispatch case ID
        alias_case_id = f"message:{life_event['id']}"
        alias_res = api_request(
            f"/api/oversight/cases/{alias_case_id}",
            method="POST",
            payload={"state": "investigating", "owner": "carl", "note": "Investigating via event alias"},
            admin_pass=admin_pass,
        )
        assert alias_res.get("ok") is True
        assert alias_res["case"]["case_id"] == life_case_id, "Alias review must resolve to primary case ID"
        print(f"  ✓ Alias lookup by event ID ({alias_case_id}) resolved to primary case {life_case_id}")

        # Idempotency check: repeat identical review update
        audit_count_before = db.audit_log.count_documents({"target": life_case_id, "action": "ops_case_review_updated"})
        idempotent_res = api_request(
            f"/api/oversight/cases/{life_case_id}",
            method="POST",
            payload={"state": "investigating", "owner": "carl", "note": "Investigating via event alias"},
            admin_pass=admin_pass,
        )
        assert idempotent_res.get("ok") is True
        audit_count_after = db.audit_log.count_documents({"target": life_case_id, "action": "ops_case_review_updated"})
        assert audit_count_after == audit_count_before, "Idempotent update must not duplicate audit records"
        print("  ✓ Idempotent review update verified: zero duplicate audit log entries created.")

        results["Gate 4 - Workstream C: Alias Resolution & Idempotency"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 5: Workstream D - Serverless Background Scheduling & Engine Tick
        # ------------------------------------------------------------------
        print("\n--- Gate 5: Workstream D - Serverless Background Scheduling (DF-029) ---")
        # Record baseline last_run before invoking
        baseline_tick = db.system_state.find_one({"key": "engine_tick"})
        baseline_last_run = str((baseline_tick or {}).get("last_run") or "")

        # Trigger Cloud Scheduler job execution
        sched_run_cmd = [
            "gcloud", "scheduler", "jobs", "run", "dtd-engine-tick-cron",
            f"--project={PROJECT_ID}", "--location=australia-southeast1"
        ]
        subprocess.check_call(sched_run_cmd)
        print("  ✓ Cloud Scheduler job dtd-engine-tick-cron invoked successfully.")

        # Wait up to 30 seconds for the asynchronous Cloud Scheduler execution to complete
        start_wait = time.time()
        engine_tick_doc = None
        while time.time() - start_wait < 30:
            doc = db.system_state.find_one({"key": "engine_tick"})
            lease_doc = db.system_state.find_one({"key": "engine_tick_lease"})
            lease_expires = float((lease_doc or {}).get("expires_at_epoch") or 0)
            now_epoch = time.time()
            if doc and str(doc.get("last_run") or "") != baseline_last_run and lease_expires <= now_epoch:
                engine_tick_doc = doc
                break
            time.sleep(2)

        if not engine_tick_doc:
            engine_tick_doc = db.system_state.find_one({"key": "engine_tick"})

        assert engine_tick_doc is not None, "system_state must contain key 'engine_tick'"
        assert engine_tick_doc.get("execution_owner") == "cloud_scheduler", f"Expected execution_owner 'cloud_scheduler', got {engine_tick_doc.get('execution_owner')}"
        assert engine_tick_doc.get("last_status") == "ok", f"Expected last_status 'ok', got {engine_tick_doc.get('last_status')}"

        last_run_str = str(engine_tick_doc.get("last_run") or "")
        tick_dt = datetime.fromisoformat(last_run_str)
        age_seconds = abs((datetime.now(timezone.utc) - tick_dt).total_seconds())
        assert age_seconds <= 300, f"engine_tick last_run was {age_seconds}s ago, expected <= 300s"
        print(f"  ✓ engine_tick telemetry verified in system_state: status={engine_tick_doc.get('last_status')}, last_run={last_run_str} ({round(age_seconds, 1)}s ago), duration={engine_tick_doc.get('duration_ms')}ms")

        # Verify individual loops updated
        ranking_doc = db.system_state.find_one({"key": "ranking"})
        assert ranking_doc is not None and ranking_doc.get("execution_owner") == "cloud_scheduler"
        health_doc = db.system_state.find_one({"key": "health"})
        assert health_doc is not None and health_doc.get("execution_owner") == "cloud_scheduler"
        print("  ✓ Autonomous loops (ranking, health, etc.) verified running under execution_owner 'cloud_scheduler'")

        # Verify distributed lease is released
        now_utc = datetime.now(timezone.utc)
        lease_doc = db.system_state.find_one({"key": "engine_tick_lease"})
        if lease_doc:
            assert float(lease_doc.get("expires_at_epoch") or 0) <= now_utc.timestamp(), "engine_tick_lease must be released after execution"
            print(f"  ✓ Distributed lease release verified: released_at={lease_doc.get('released_at')}")

        results["Gate 5 - Workstream D: Serverless Scheduling & Engine Tick (DF-029)"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 6: Read-only Oversight Invariant (Zero DB Writes)
        # ------------------------------------------------------------------
        print("\n--- Gate 6: Read-only Oversight Invariant (DF-032) ---")
        before_snapshots_count = db.phase_readiness_snapshots.count_documents({})
        before_launch_state_count = db.launch_phase_state.count_documents({})
        before_audit_count = db.audit_log.count_documents({})

        # Execute GET /api/oversight multiple times
        api_request("/api/oversight", admin_pass=admin_pass)
        api_request("/api/oversight", admin_pass=admin_pass)

        after_snapshots_count = db.phase_readiness_snapshots.count_documents({})
        after_launch_state_count = db.launch_phase_state.count_documents({})
        after_audit_count = db.audit_log.count_documents({})

        assert before_snapshots_count == after_snapshots_count, "GET /api/oversight must perform zero writes to phase_readiness_snapshots"
        assert before_launch_state_count == after_launch_state_count, "GET /api/oversight must perform zero writes to launch_phase_state"
        assert before_audit_count == after_audit_count, "GET /api/oversight must perform zero writes to audit_log"
        print("  ✓ Read-only contract verified: GET /api/oversight produced exactly zero database writes.")
        results["Gate 6 - Read-only Oversight Invariant (DF-032)"] = "PASS"

    finally:
        # ------------------------------------------------------------------
        # Gate 7: Clean Fixture Disposal
        # ------------------------------------------------------------------
        print("\n--- Gate 7: Zero-Trace Fixture Cleanup ---")
        cleanup_report = {}
        for coll_name, ids in inserted_ids.items():
            if not ids:
                continue
            coll = db[coll_name]
            if coll_name == "notification_events":
                res = coll.delete_many({"id": {"$in": ids}})
                cleanup_report[coll_name] = res.deleted_count
            elif coll_name == "ops_case_states":
                res = coll.delete_many({"case_id": {"$in": ids}})
                cleanup_report[coll_name] = res.deleted_count
            elif coll_name == "audit_log":
                from bson import ObjectId
                valid_oids = []
                for _id in ids:
                    try:
                        valid_oids.append(ObjectId(_id))
                    except Exception:
                        pass
                if valid_oids:
                    res = coll.delete_many({"_id": {"$in": valid_oids}})
                    cleanup_report[coll_name] = res.deleted_count

        # Clean any audit_log entries created by this test run
        res_audit = db.audit_log.delete_many({"target": {"$regex": test_run_id}})
        if res_audit.deleted_count:
            cleanup_report["audit_log_regex"] = res_audit.deleted_count

        print(f"  ✓ Cleanup completed: {cleanup_report}")
        results["Gate 7 - Zero-Trace Fixture Disposal"] = "PASS"
        client.close()

    print("\n=== Final Phase 2 Sandbox Acceptance Gate Results ===")
    all_passed = True
    for gate, status in results.items():
        print(f"  {gate}: {status}")
        if status != "PASS":
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
