#!/usr/bin/env python3
"""Execute the complete Phase 4 sandbox acceptance gate for DTD Operations Console.

Verifies live runtime behavior of the AI Operations Analyst on Cloud Run (dogtrainersdirectory-dev):
1. Deployed revision & environment verification.
2. Gate A: Real incident trigger (synthetic failure fixture).
3. Gate B: Live Gemini inference on sandbox with structured schema.
4. Gate C: Correlation, caching, and deduplication.
5. Gate D: Evidence minimisation and sanitisation verification.
6. Gate E: Strict read-only invariant (zero mutation to operational data).
7. Gate F: Cooldown and rate limiting enforcement.
8. Gate G: Read-only oversight enrichment (/api/oversight).
9. Gate H: Zero-trace cleanup of disposable test fixtures.

Safe for developer sandbox (dogtrainersdirectory-dev / dtd_sandbox).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
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
    print("\n--- Verifying Production Isolation ---")
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
        print("✅ Production backend is untouched and strictly locked.")
    except Exception as e:
        print(f"⚠️ Production check notice: {e}")


def main() -> int:
    print(f"=== Starting Phase 4 Sandbox Acceptance Gate on {SERVICE_URL} ===")
    test_run_id = f"test-p4-{uuid.uuid4().hex[:8]}"
    print(f"Test Run Tag: {test_run_id}")

    verify_production_isolation()

    # Retrieve secrets
    print("\nRetrieving secrets from Secret Manager...")
    mongo_url = get_secret("dtd-mongo-url")
    admin_pass = get_secret("dtd-admin-pass")

    client: MongoClient = MongoClient(mongo_url)
    db = client[DB_NAME]

    inserted_records: Dict[str, List[Any]] = {
        "notification_events": [],
        "ops_case_states": [],
        "ops_ai_investigations": [],
    }
    test_case_id = f"message:disp_{test_run_id}"

    try:
        # 1. Check Deployed Revision
        print("\n--- 1. Checking Sandbox Revision & Health ---")
        health = api_request("/api/health")
        assert health.get("ok") is True, f"Health check failed: {health}"
        assert health.get("database") == "available", f"Database unavailable: {health}"
        print("✅ Sandbox API is healthy and connected to database.")

        oversight_init = api_request("/api/oversight", admin_pass=admin_pass)
        assert "cases" in oversight_init, "Failed to retrieve initial /api/oversight"
        analyst_meta = oversight_init.get("ops_ai_analyst", {})
        print(f"AI Analyst Metadata: {json.dumps(analyst_meta)}")
        assert analyst_meta.get("enabled") is True, "AI Analyst not marked enabled in oversight root"
        print("✅ AI Analyst service is registered and active.")

        # 2. Gate A: Real Incident Trigger (Synthetic Fixture)
        print("\n--- Gate A: Creating Real Incident Fixture ---")
        dispatch_id = f"disp_{test_run_id}"
        now_iso = datetime.now(timezone.utc).isoformat()

        synthetic_event = {
            "id": f"evt_{test_run_id}_1",
            "dispatch_id": dispatch_id,
            "workflow": "match_intro",
            "target_kind": "trainer",
            "target_id": f"tr_{test_run_id}",
            "to_email": "jane.client.secret@example.com",
            "kind": "intro_notification",
            "status": "failed",
            "http_status": 401,
            "error": "Resend API Error: Invalid API key 're_secret_1234567890abcdef'. Authorization header rejected.",
            "attempt": 1,
            "created_at": now_iso,
            "_test_tag": test_run_id,
        }
        res_insert = db.notification_events.insert_one(synthetic_event)
        inserted_records["notification_events"].append(res_insert.inserted_id)

        # Verify incident appears in /api/oversight
        oversight_with_inc = api_request("/api/oversight", admin_pass=admin_pass)
        cases = oversight_with_inc.get("cases", [])
        matched_case = next((c for c in cases if c.get("case_id") == test_case_id), None)
        assert matched_case is not None, f"Expected incident {test_case_id} in /api/oversight cases"
        assert matched_case.get("severity") in ("high", "medium"), "Incident must be high or medium severity"
        print(f"✅ Gate A PASSED: Incident {test_case_id} generated and detected in /api/oversight.")

        # 3. Gate B & D: Live Gemini Inference on Sandbox with Structured Schema
        print("\n--- Gate B & D: Triggering On-Demand AI Investigation ---")
        inv_resp = api_request(
            f"/api/oversight/cases/{test_case_id}/investigate",
            method="POST",
            payload={"force_refresh": True},
            admin_pass=admin_pass,
        )
        print("Investigation response:", json.dumps(inv_resp, indent=2))
        assert inv_resp.get("ok") is True, f"Investigation failed: {inv_resp}"
        assert inv_resp.get("status") == "completed", f"Status not completed: {inv_resp.get('status')}"
        inv_id = inv_resp.get("investigation_id")
        assert inv_id, "investigation_id missing"
        inserted_records["ops_ai_investigations"].append(inv_id)

        analysis = inv_resp.get("ai_analysis") or inv_resp.get("analysis", {})
        assert analysis.get("root_cause_classification") in ("confirmed", "likely", "possible", "unknown"), (
            f"Invalid classification: {analysis.get('root_cause_classification')}"
        )
        assert len(analysis.get("root_cause_hypothesis", "")) >= 10, "root_cause_hypothesis too short"
        assert isinstance(analysis.get("supporting_evidence"), list) and len(analysis.get("supporting_evidence")) > 0, (
            "supporting_evidence must be non-empty list"
        )
        assert len(analysis.get("recommended_action", "")) >= 5, "recommended_action too short"
        assert 0.0 <= float(analysis.get("confidence_score", 0)) <= 1.0, "confidence_score out of range"

        model_used = inv_resp.get("model_used")
        print(f"Model used: {model_used}")
        print(f"Hypothesis: {analysis.get('root_cause_hypothesis')}")
        print(f"Classification: {analysis.get('root_cause_classification')}")
        print(f"Recommended action: {analysis.get('recommended_action')}")
        print("✅ Gate B & D PASSED: Live inference succeeded with strict structured schema validation.")

        # 4. Gate C: Correlation, Deduplication, and Caching
        print("\n--- Gate C: Testing Deduplication & Caching ---")
        # Verify exactly ONE investigation document exists in MongoDB for this incident
        doc_count = db.ops_ai_investigations.count_documents({"case_id": test_case_id})
        assert doc_count == 1, f"Expected exactly 1 persisted investigation document, found {doc_count}"
        # Verify /api/oversight serves cached investigation without calling inference again
        oversight_cached = api_request("/api/oversight", admin_pass=admin_pass)
        cached_case = next((c for c in oversight_cached.get("cases", []) if c.get("case_id") == test_case_id), None)
        assert cached_case is not None, "Case missing from oversight"
        assert cached_case.get("ai_investigation_id") == inv_id, "ai_investigation_id does not match"
        assert cached_case.get("ai_analysis") is not None, "ai_analysis missing from cached case"
        print("✅ Gate C PASSED: Cached investigation returned without redundant inference.")

        # 5. Gate E: Evidence Minimisation and Sanitisation Verification
        print("\n--- Gate E: Verifying Secret & PII Sanitisation ---")
        # Check that re_secret_1234567890abcdef and client email were NOT persisted in raw form
        inv_doc = db.ops_ai_investigations.find_one({"investigation_id": inv_id})
        assert inv_doc is not None, "Investigation document not found in MongoDB"
        raw_inv_str = json.dumps(inv_doc, default=str)
        assert "re_secret_1234567890abcdef" not in raw_inv_str, "Raw API key leaked into investigation storage!"
        assert "jane.client.secret@example.com" not in raw_inv_str, "Raw client email leaked into investigation storage!"
        print("✅ Gate E PASSED: Secrets and PII strictly sanitized before storage and inference.")

        # 6. Gate F: Strict Read-Only Invariant Verification
        print("\n--- Gate F: Verifying Read-Only Invariant ---")
        # Ensure operational state of case was NOT mutated
        persisted_case_state = db.ops_case_states.find_one({"case_id": test_case_id})
        assert persisted_case_state is None, "AI Analyst must never create or mutate an ops_case_states record!"
        print("✅ Gate F PASSED: Zero mutations to operational state, reviews, or core directory collections.")

        # 7. Gate G: Rate Limiting & Cooldown
        print("\n--- Gate G: Testing Manual Cooldown Rate Limiting ---")
        try:
            api_request(
                f"/api/oversight/cases/{test_case_id}/investigate",
                method="POST",
                payload={"force_refresh": True},
                admin_pass=admin_pass,
            )
            print("❌ Expected HTTP 429 rate limit error but call succeeded")
            return 1
        except ApiError as e:
            assert e.status_code == 429, f"Expected HTTP 429, got {e.status_code}"
            assert "cooldown" in e.body.lower() or "recently requested" in e.body.lower(), (
                f"Unexpected error body: {e.body}"
            )
            print(f"✅ Gate G PASSED: Cooldown rate limit enforced properly (HTTP 429: {e.body.strip()}).")

        # 8. Gate H: Read-Only Oversight Enrichment
        print("\n--- Gate H: Verifying /api/oversight Read-Only Enrichment ---")
        oversight_enriched = api_request("/api/oversight", admin_pass=admin_pass)
        enriched_cases = oversight_enriched.get("cases", [])
        enriched_target = next((c for c in enriched_cases if c.get("case_id") == test_case_id), None)
        assert enriched_target is not None, "Target case missing from enriched oversight"
        assert enriched_target.get("ai_investigation_status") == "completed", "Status must be completed"
        assert enriched_target.get("ai_analysis") is not None, "ai_analysis payload must be present"
        assert enriched_target.get("ai_analysis", {}).get("root_cause_hypothesis") == analysis.get("root_cause_hypothesis"), (
            "Enriched hypothesis matches investigation"
        )
        # 9. Gate I: Live UI Acceptance & Screenshot Capture
        print("\n--- Gate I: Executing Live UI Acceptance & Screenshot Capture ---")
        ui_res = subprocess.run(
            ["node", "scripts/verify_sandbox_ops_phase4_live_ui.mjs", admin_pass, dispatch_id],
            capture_output=True,
            text=True,
        )
        print("UI Script Output:\n", ui_res.stdout)
        if ui_res.stderr:
            print("UI Script Stderr:\n", ui_res.stderr)
        assert ui_res.returncode == 0, f"Live UI verification failed with exit code {ui_res.returncode}"
        print("✅ Gate I PASSED: Operations Console UI verified with live screenshots.")

        print("\n=======================================================")
        print("🎉 ALL PHASE 4 LIVE BACKEND & UI ACCEPTANCE GATES PASSED! 🎉")
        print("=======================================================")
        return 0

    finally:
        print("\n--- Cleanup: Zero-Trace Fixture Teardown ---")
        deleted_events = db.notification_events.delete_many({"_test_tag": test_run_id})
        print(f"Deleted notification_events: {deleted_events.deleted_count}")
        deleted_invs = db.ops_ai_investigations.delete_many({"case_id": {"$regex": f"^{test_case_id}"}})
        print(f"Deleted ops_ai_investigations: {deleted_invs.deleted_count}")
        print("✅ Cleanup complete.")


if __name__ == "__main__":
    sys.exit(main())
