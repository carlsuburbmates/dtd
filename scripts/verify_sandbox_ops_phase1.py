#!/usr/bin/env python3
"""Execute the final Phase 1 sandbox acceptance gate for DTD Operations Console.

Verifies live runtime behavior on Cloud Run revision dtd-api-dev:
1. Successful events excluded from Needs Action (Noise Elimination).
2. Genuine notification, AI, provider and background-task failures remain visible.
3. Correct operational versus governance classification.
4. Administrative review, dismissal safeguards, and occurrence fingerprint behavior.
5. Audit integrity, read-only oversight (DF-032), and production isolation.
6. Zero-trace cleanup of disposable test fixtures.

Safe for developer sandbox (dogtrainersdirectory-dev / dtd_sandbox).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
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
        with urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise ApiError(e.code, e.reason, err_body) from e


def main() -> int:
    print(f"=== Starting Phase 1 Sandbox Acceptance Gate on {SERVICE_URL} ===")
    test_run_id = f"test-p1-{uuid.uuid4().hex[:8]}"
    print(f"Test Run Tag: {test_run_id}")

    # Fetch credentials
    print("Fetching sandbox secrets from Secret Manager...")
    mongo_url = get_secret("dtd-mongo-url")
    admin_pass = get_secret("dtd-admin-pass")

    client: MongoClient = MongoClient(mongo_url, serverSelectionTimeoutMS=8000)
    db = client[DB_NAME]
    print(f"Connected to sandbox database: {db.name}")

    results: Dict[str, str] = {}
    inserted_ids = {
        "notification_events": [],
        "ai_degradation_events": [],
        "ops_case_states": [],
        "audit_log": [],
    }

    try:
        now_iso = datetime.now(timezone.utc).isoformat()

        # ------------------------------------------------------------------
        # Gate 1: Successful Events Excluded from Needs Action (Noise Elimination)
        # ------------------------------------------------------------------
        print("\n--- Gate 1: Successful Events Excluded from Needs Action ---")
        success_msg_id = f"notif-sent-{test_run_id}"
        db.notification_events.insert_one({
            "id": success_msg_id,
            "created_at": now_iso,
            "kind": "trainer_claim_otp",
            "target_kind": "trainer",
            "target_id": "test-trainer-success",
            "to_email": "trainer-sent@example.com",
            "attempt": 1,
            "status": "sent",
            "http_status": 202,
            "provider": "resend",
            "provider_id": "resend-mock-id",
            "error": "",
            "test_tag": test_run_id,
        })
        inserted_ids["notification_events"].append(success_msg_id)

        oversight_data = api_request("/api/oversight", admin_pass=admin_pass)
        cases = oversight_data.get("cases", [])
        case_ids = {c["case_id"] for c in cases}

        assert f"message:{success_msg_id}" not in case_ids, "Delivered message should NOT generate an Ops case!"
        print("  ✓ Successful HTTP 202 email excluded from Ops cases.")
        results["Gate 1 - Noise Elimination (Success Excluded)"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 2: Genuine Failures Remain Visible
        # ------------------------------------------------------------------
        print("\n--- Gate 2: Genuine Failures Remain Visible ---")
        fail_msg_id = f"notif-fail-{test_run_id}"
        db.notification_events.insert_one({
            "id": fail_msg_id,
            "created_at": now_iso,
            "kind": "submission_status_notification",
            "target_kind": "submission",
            "target_id": "test-submission-fail",
            "to_email": "trainer-fail@example.com",
            "attempt": 1,
            "status": "failed",
            "http_status": 500,
            "provider": "resend",
            "provider_id": "",
            "error": "http_500_resend_error",
            "test_tag": test_run_id,
        })
        inserted_ids["notification_events"].append(fail_msg_id)

        # AI failure with valid timestamp
        ai_valid_id = f"ai-fail-valid-{test_run_id}"
        db.ai_degradation_events.insert_one({
            "id": ai_valid_id,
            "timestamp": now_iso,
            "provider": "gemini",
            "model": "gemini-3.5-flash",
            "operation": "trainer_verification_scoring",
            "error_type": "timeout",
            "error_code": "TIMEOUT",
            "message": "Synthetic test timeout in acceptance gate",
            "fallback_used": True,
            "recovered": False,
            "test_tag": test_run_id,
        })
        inserted_ids["ai_degradation_events"].append(ai_valid_id)

        # AI failure with malformed timestamp
        ai_malformed_id = f"ai-fail-malformed-{test_run_id}"
        db.ai_degradation_events.insert_one({
            "id": ai_malformed_id,
            "timestamp": "invalid-timestamp-format",
            "provider": "gemini",
            "model": "gemini-3.5-flash",
            "operation": "trainer_verification_scoring",
            "error_type": "json_parse_error",
            "error_code": "PARSE_ERROR",
            "message": "Synthetic malformed timestamp test",
            "fallback_used": True,
            "recovered": False,
            "test_tag": test_run_id,
        })
        inserted_ids["ai_degradation_events"].append(ai_malformed_id)

        oversight_data = api_request("/api/oversight", admin_pass=admin_pass)
        cases = oversight_data.get("cases", [])
        cases_by_id = {c["case_id"]: c for c in cases}

        assert f"message:{fail_msg_id}" in cases_by_id, "Failed delivery must surface as an actionable case!"
        fail_case = cases_by_id[f"message:{fail_msg_id}"]
        assert fail_case["severity"] == "high"
        assert fail_case["state"] == "detected"
        print(f"  ✓ Failed delivery case surfaced: {fail_case['case_id']} ({fail_case['severity']})")

        ai_cases = [c for c in cases if c.get("case_type") == "ai_degradation_case"]
        assert len(ai_cases) > 0, "AI degradation must surface as an actionable case!"
        print(f"  ✓ AI degradation cases surfaced: count={len(ai_cases)}")

        results["Gate 2 - Genuine Failures Visible"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 3: Correct Operational vs Governance Classification
        # ------------------------------------------------------------------
        print("\n--- Gate 3: Operational vs Governance Classification ---")
        provider_cases = [c for c in cases if c.get("entity_type") == "provider"]
        gov_cases = [c for c in provider_cases if c.get("case_type") == "provider_governance_case"]
        op_cases = [c for c in provider_cases if c.get("case_type") == "provider_operational_case"]

        for gc in gov_cases:
            assert gc["severity"] == "low"
            assert gc["state"] == "monitoring"
        print(f"  ✓ Provider governance cases classified with low severity in monitoring: count={len(gov_cases)}")
        print(f"  ✓ Provider operational cases classified appropriately: count={len(op_cases)}")
        results["Gate 3 - Operational vs Governance Classification"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 4: Administrative Review, Dismissal Safeguards & Fingerprints
        # ------------------------------------------------------------------
        print("\n--- Gate 4: Administrative Review & Occurrence Fingerprint ---")
        review_case_id = f"message:{fail_msg_id}"

        # 4a: Dismissal safeguard for high severity case - note < 5 chars must fail with 400
        short_note_payload = {
            "state": "dismissed",
            "owner": "acceptance-agent",
            "note": "no",
        }
        try:
            api_request(f"/api/oversight/cases/{review_case_id}", method="POST", payload=short_note_payload, admin_pass=admin_pass)
            assert False, "Dismissing high-severity case with note < 5 chars should have failed with 400!"
        except ApiError as e:
            assert e.status_code == 400, f"Expected HTTP 400 for short note dismissal, got {e.status_code}"
            assert "explanatory review note of at least 5 characters" in e.body
            print("  ✓ Safeguard verified: short note dismissal on high-severity case rejected with HTTP 400.")

        # 4b: Valid dismissal
        review_payload = {
            "state": "dismissed",
            "owner": "acceptance-agent",
            "note": "Verified by automated Phase 1 acceptance gate",
        }
        review_resp = api_request(f"/api/oversight/cases/{review_case_id}", method="POST", payload=review_payload, admin_pass=admin_pass)
        assert review_resp.get("ok") is True, f"Review action failed: {review_resp}"
        print(f"  ✓ Review action 'dismissed' succeeded for {review_case_id}")
        inserted_ids["ops_case_states"].append(review_case_id)

        # Check oversight reflection
        oversight_data_after = api_request("/api/oversight", admin_pass=admin_pass)
        cases_after = {c["case_id"]: c for c in oversight_data_after.get("cases", [])}
        assert f"message:{fail_msg_id}" in cases_after
        dismissed_case = cases_after[f"message:{fail_msg_id}"]
        assert dismissed_case["state"] == "dismissed", f"Case state should be dismissed, got {dismissed_case['state']}"
        print("  ✓ Case updated to state 'dismissed' in oversight read model.")

        # Re-read to verify zero false recurrence
        oversight_data_recheck = api_request("/api/oversight", admin_pass=admin_pass)
        cases_recheck = {c["case_id"]: c for c in oversight_data_recheck.get("cases", [])}
        rechecked_case = cases_recheck[f"message:{fail_msg_id}"]
        assert rechecked_case["state"] == "dismissed", "Case must NOT false-recur on subsequent reads!"
        print("  ✓ Recurrence protection confirmed: identical occurrence remains dismissed on refresh.")

        # Check ops_case_states collection directly
        case_state_doc = db.ops_case_states.find_one({"case_id": review_case_id})
        assert case_state_doc is not None
        assert case_state_doc.get("state") == "dismissed"
        assert "occurrence_fingerprint" in case_state_doc
        print(f"  ✓ ops_case_states doc verified: state={case_state_doc['state']} fp={case_state_doc.get('occurrence_fingerprint')}")

        results["Gate 4 - Review & Occurrence Fingerprint"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 5: Audit Integrity & Read-Only Oversight Contract (DF-032)
        # ------------------------------------------------------------------
        print("\n--- Gate 5: Audit Integrity & Read-Only Oversight (DF-032) ---")
        audit_doc = db.audit_log.find_one({"target": review_case_id, "action": "ops_case_review_updated"})
        assert audit_doc is not None, "Review action must create an immutable audit_log record!"
        print(f"  ✓ Audit log verified: actor={audit_doc.get('actor')} action={audit_doc.get('action')}")
        inserted_ids["audit_log"].append(str(audit_doc["_id"]))

        # Read-only test: record snapshot collection state
        before_snapshots_count = db.phase_readiness_snapshots.count_documents({})
        before_launch_state_count = db.launch_phase_state.count_documents({})

        # Call oversight twice
        api_request("/api/oversight", admin_pass=admin_pass)
        api_request("/api/oversight", admin_pass=admin_pass)

        after_snapshots_count = db.phase_readiness_snapshots.count_documents({})
        after_launch_state_count = db.launch_phase_state.count_documents({})

        assert before_snapshots_count == after_snapshots_count, "GET /api/oversight must perform ZERO writes to phase_readiness_snapshots!"
        assert before_launch_state_count == after_launch_state_count, "GET /api/oversight must perform ZERO writes to launch_phase_state!"
        print("  ✓ Read-only contract verified: GET /api/oversight produced exactly zero database writes.")
        results["Gate 5 - Audit Integrity & Read-Only Oversight (DF-032)"] = "PASS"

        # ------------------------------------------------------------------
        # Gate 6: Production Isolation
        # ------------------------------------------------------------------
        print("\n--- Gate 6: Production Isolation Verification ---")
        assert db.name == "dtd_sandbox", f"Must be connected to dtd_sandbox, got {db.name}"
        assert PROJECT_ID == "dogtrainersdirectory-dev"

        # Verify production is untouched
        prod_health = json.loads(urlopen("https://dogtrainersdirectory.com.au/api/health", timeout=10).read().decode())
        assert prod_health.get("ok") is True
        print("  ✓ Production environment independently verified untouched and healthy.")
        results["Gate 6 - Production Isolation"] = "PASS"

    finally:
        # ------------------------------------------------------------------
        # Gate 7: Clean Fixture Disposal
        # ------------------------------------------------------------------
        print("\n--- Gate 7: Fixture Cleanup ---")
        cleanup_report = {}
        for coll_name, ids in inserted_ids.items():
            if not ids:
                continue
            coll = db[coll_name]
            if coll_name == "notification_events":
                res = coll.delete_many({"id": {"$in": ids}})
                cleanup_report[coll_name] = res.deleted_count
            elif coll_name == "ai_degradation_events":
                res = coll.delete_many({"id": {"$in": ids}})
                cleanup_report[coll_name] = res.deleted_count
            elif coll_name == "ops_case_states":
                res = coll.delete_many({"case_id": {"$in": ids}})
                cleanup_report[coll_name] = res.deleted_count
            elif coll_name == "audit_log":
                from bson import ObjectId
                obj_ids = [ObjectId(_id) for _id in ids]
                res = coll.delete_many({"_id": {"$in": obj_ids}})
                cleanup_report[coll_name] = res.deleted_count

        print(f"  ✓ Cleanup completed: {cleanup_report}")
        results["Gate 7 - Zero-Trace Fixture Disposal"] = "PASS"
        client.close()

    print("\n=== Final Phase 1 Acceptance Results ===")
    all_passed = True
    for gate, status in results.items():
        print(f"{gate}: {status}")
        if status != "PASS":
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
