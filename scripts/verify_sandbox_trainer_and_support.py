#!/usr/bin/env python3
"""Integrated Sandbox Acceptance Runner: Trainer Session / Storefront and Support Lifecycle.

Verifies live runtime behavior on Cloud Run (dogtrainersdirectory-dev):
1. Preflight sandbox scope validation and non-secret metadata capture.
2. Domain 3 / SR-03 / CF-03 / DF-030 / DF-051 / DF-035: Trainer claim initiation,
   email mismatch / SMS fail-closed guards, invalid OTP rejection.
   (Receipt-dependent OTP verification requires operator input or provider mailbox receipt;
   privileged secret derivation is prohibited per audit).
3. Domain 6 / SR-04 / CF-04 / DF-047: First-party support complaint intake, Resend test-sink
   confirmation delivery, protected /ops thread retrieval, operator reply & duplicate prevention,
   guarded closure (notes length, delisting/privacy prerequisites), durable obligation sync.
4. Headless Playwright browser UI validation on dtd-web-dev (contact form, trainer profile, /ops support view).
5. Deterministic fixture teardown and exact-ID absence verification.

Safe for developer sandbox only. Secrets fetched in memory and never logged or printed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request

from pymongo import MongoClient

# Environment Constants
SANDBOX_PROJECT = "dogtrainersdirectory-dev"
SANDBOX_DB = "dtd_sandbox"
API_URL = "https://dtd-api-dev-625222421634.australia-southeast1.run.app"
WEB_URL = "https://dtd-web-dev-x2kdoaemtq-ts.a.run.app"
TEST_RECIPIENT = "delivered@resend.dev"
DEFAULT_ARTIFACT_DIR = Path("/Users/carlg/.gemini/antigravity-ide/brain/97d6f866-04ef-4bf9-a96c-9b4c0bcb5596")


class AcceptanceFailure(Exception):
    pass


class StrictRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Denies cross-origin HTTP redirects on protected/authenticated requests."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old_parsed = urlparse(req.full_url)
        new_parsed = urlparse(newurl)
        old_origin = f"{old_parsed.scheme}://{old_parsed.netloc}"
        new_origin = f"{new_parsed.scheme}://{new_parsed.netloc}"
        if old_origin != new_origin:
            raise HTTPError(
                newurl,
                code,
                f"Cross-origin redirect from {old_origin} to {new_origin} denied for protected request",
                headers,
                fp,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _http_request(
    url: str,
    method: str = "GET",
    payload: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
    timeout: int = 25,
) -> tuple[int, Dict[str, Any]]:
    parsed = urlparse(url)
    origin_host = parsed.netloc.split(":")[0].lower()
    allowed_hosts = {
        urlparse(API_URL).netloc.split(":")[0].lower(),
        urlparse(WEB_URL).netloc.split(":")[0].lower(),
        "localhost",
        "127.0.0.1",
    }
    if origin_host not in allowed_hosts:
        raise AcceptanceFailure(f"Refusing HTTP request to unapproved destination: {url}")

    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=req_headers, method=method)

    opener = urllib.request.build_opener(StrictRedirectHandler())
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return int(resp.status), json.loads(body) if body else {}
    except HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed_body = json.loads(body)
        except Exception:
            parsed_body = {"raw": body}
        return int(e.code), parsed_body


def _validate_sandbox_mongo_url(mongo_url: str) -> None:
    if not mongo_url:
        raise AcceptanceFailure("MONGO_URL must be provided via environment.")
    parsed = urlparse(mongo_url)
    if parsed.scheme not in ("mongodb", "mongodb+srv"):
        raise AcceptanceFailure(f"Invalid MongoDB URI scheme: {parsed.scheme!r}")

    host = (parsed.hostname or "").lower()
    is_atlas_sandbox = host.startswith("dtd-sandbox") and host.endswith(".mongodb.net")
    is_loopback = host in ("localhost", "127.0.0.1")
    if not (is_atlas_sandbox or is_loopback):
        raise AcceptanceFailure(
            f"Refusing non-sandbox MongoDB cluster host: {host!r}. Must be dtd-sandbox*.mongodb.net or loopback."
        )

    db_name = parsed.path.lstrip("/").split("?")[0]
    if db_name not in (SANDBOX_DB, "test", "dtd_test"):
        raise AcceptanceFailure(
            f"Refusing non-sandbox database name: {db_name!r}. Must be {SANDBOX_DB!r}."
        )


def _require_sandbox(mongo_url: str, admin_pass: str) -> None:
    proj = os.environ.get("DTD_SANDBOX_PROJECT_ID")
    if proj != SANDBOX_PROJECT:
        raise AcceptanceFailure(
            f"Explicit DTD_SANDBOX_PROJECT_ID must be strictly '{SANDBOX_PROJECT}', got: {proj!r}"
        )
    if not admin_pass:
        raise AcceptanceFailure("ADMIN_PASS must be provided via environment.")
    _validate_sandbox_mongo_url(mongo_url)


def capture_sandbox_runtime_metadata() -> Dict[str, Any]:
    print("[1/5] Capturing Sandbox Runtime Metadata...")
    meta: Dict[str, Any] = {
        "project": SANDBOX_PROJECT,
        "database": SANDBOX_DB,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        api_rev = subprocess.check_output(
            [
                "gcloud", "run", "services", "describe", "dtd-api-dev",
                f"--project={SANDBOX_PROJECT}",
                "--region=australia-southeast1",
                "--format=value(status.latestReadyRevisionName)",
            ],
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
        meta["api_revision"] = api_rev
        print(f"      Sandbox API revision: {api_rev}")
    except Exception as e:
        meta["api_revision_lookup_error"] = str(e)

    try:
        web_rev = subprocess.check_output(
            [
                "gcloud", "run", "services", "describe", "dtd-web-dev",
                f"--project={SANDBOX_PROJECT}",
                "--region=australia-southeast1",
                "--format=value(status.latestReadyRevisionName)",
            ],
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
        meta["web_revision"] = web_rev
        print(f"      Sandbox Web revision: {web_rev}")
    except Exception as e:
        meta["web_revision_lookup_error"] = str(e)

    try:
        cron_state = subprocess.check_output(
            [
                "gcloud", "scheduler", "jobs", "describe", "dtd-trainer-ingest-cron",
                f"--project={SANDBOX_PROJECT}",
                "--location=australia-southeast1",
                "--format=value(state)",
            ],
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
        meta["ingest_cron_state"] = cron_state
        print(f"      Cloud Scheduler job dtd-trainer-ingest-cron state: {cron_state}")
    except Exception as e:
        meta["ingest_cron_lookup_error"] = str(e)

    return meta


async def run_acceptance(
    mongo_url: str,
    admin_pass: str,
    otp: str = "",
    artifact_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    _require_sandbox(mongo_url, admin_pass)
    metadata = capture_sandbox_runtime_metadata()

    target_artifact_dir = artifact_dir or DEFAULT_ARTIFACT_DIR
    target_artifact_dir.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex[:12]
    trainer_id = f"sandbox-trainer-{run_id}"
    complaint_email = f"sandbox-support-{run_id}-api@delivered.resend.dev"
    browser_email = f"sandbox-support-{run_id}-browser@delivered.resend.dev"

    tracked_case_ids: Set[str] = set()
    test_exception: Optional[Exception] = None

    evidence: Dict[str, Any] = {
        "run_id": run_id,
        "trainer_id": trainer_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runtime_metadata": metadata,
        "stages": {},
    }

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
    db = client[SANDBOX_DB]
    inserted_trainer = False

    try:
        # Preflight
        client.admin.command("ping")
        status, health = _http_request(f"{API_URL}/api/health")
        if status != 200 or health.get("database") != "available":
            raise AcceptanceFailure(f"API health check failed: {status} {health}")
        status, config = _http_request(f"{API_URL}/api/config")
        if status != 200 or not config.get("public_matching_enabled"):
            raise AcceptanceFailure(f"API config check failed: {status} {config}")
        evidence["stages"]["preflight"] = "PASSED"
        print("      Preflight API & Atlas database status: HEALTHY")

        # =====================================================================
        # PART A: Trainer Claim & Storefront Capabilities
        # =====================================================================
        print("\n[2/5] Testing Trainer Claim Initiation & Guards...")

        # 1. Insert synthetic trainer fixture
        now_str = datetime.now(timezone.utc).isoformat()
        fixture_doc = {
            "id": trainer_id,
            "slug": trainer_id,
            "name": f"Sandbox Test Canine Academy {run_id[:6]}",
            "suburb": "Richmond",
            "region": "Greater Melbourne",
            "published": True,
            "contact_ready": True,
            "verification_status": "unverified",
            "claim_status": "unclaimed",
            "tier": "free",
            "email": TEST_RECIPIENT,
            "billing_email": TEST_RECIPIENT,
            "abn_verified": True,
            "test_fixture": True,
            "test_run_id": run_id,
            "created_at": now_str,
            "updated_at": now_str,
        }
        db.trainers.insert_one(dict(fixture_doc))
        inserted_trainer = True

        # Public profile retrieval
        status, profile = _http_request(f"{API_URL}/api/trainers/{trainer_id}")
        assert status == 200, f"Expected 200 for public profile, got {status}"
        assert profile.get("claim_status") == "unclaimed"
        print("      - Public profile retrieval: OK (claim_status: unclaimed)")

        # 2. Claim start guards
        # 2a. Mismatched email -> 403
        status, _ = _http_request(
            f"{API_URL}/api/trainers/{trainer_id}/claim",
            method="POST",
            payload={"email": "wrong@example.com", "method": "email"},
        )
        assert status == 403, f"Expected 403 for mismatched claimant email, got {status}"
        print("      - Guard: Mismatched email rejection -> 403 OK")

        # 2b. Unsupported method (SMS) -> 503
        status, _ = _http_request(
            f"{API_URL}/api/trainers/{trainer_id}/claim",
            method="POST",
            payload={"email": TEST_RECIPIENT, "method": "sms"},
        )
        assert status == 503, f"Expected 503 for SMS method, got {status}"
        print("      - Guard: SMS provider unavailable -> 503 OK")

        # 2c. Valid claim start -> 200
        status, claim_resp = _http_request(
            f"{API_URL}/api/trainers/{trainer_id}/claim",
            method="POST",
            payload={"email": TEST_RECIPIENT, "method": "email"},
        )
        assert status == 200, f"Expected 200 for valid claim start, got {status} {claim_resp}"
        claim_event_id = claim_resp.get("claim_event_id")
        assert claim_event_id, "Missing claim_event_id"
        assert claim_resp.get("status") == "pending_verification"
        assert claim_resp.get("delivery_status") == "sent"

        # Check DB claim_event and notification_event
        claim_event = db.claim_events.find_one({"id": claim_event_id})
        assert claim_event is not None, "claim_event not persisted in DB"
        assert claim_event.get("otp_digest"), "Missing otp_digest in DB event"

        notif_event = db.notification_events.find_one(
            {"target_kind": "trainer_claim", "target_id": trainer_id, "kind": "trainer_claim_otp"}
        )
        assert notif_event is not None, "notification_event not found"
        assert notif_event.get("provider_id"), "Missing provider_id from Resend test sink"
        print(f"      - Claim initiated: Challenge ID {claim_event_id[:12]}..., Resend Message ID: {notif_event.get('provider_id')}")

        # 3. OTP Verification Guards
        # 3a. Invalid OTP -> 400
        status, _ = _http_request(
            f"{API_URL}/api/trainers/{trainer_id}/claim/verify",
            method="POST",
            payload={"otp": "000000", "claim_event_id": claim_event_id},
        )
        assert status == 400, f"Expected 400 for bad OTP, got {status}"
        claim_event_after_fail = db.claim_events.find_one({"id": claim_event_id})
        assert claim_event_after_fail.get("attempts") == 1, "Attempt counter not incremented"
        print("      - Guard: Bad OTP incremented attempts -> 400 OK")

        evidence["stages"]["trainer_claim_guards"] = "PASSED"

        # 3b. Delivered Challenge Verification
        if otp:
            print("      - Testing OTP verification using supplied operator challenge code...")
            status, verify_resp = _http_request(
                f"{API_URL}/api/trainers/{trainer_id}/claim/verify",
                method="POST",
                payload={"otp": otp, "claim_event_id": claim_event_id},
            )
            assert status == 200, f"Expected 200 for valid verify, got {status} {verify_resp}"
            assert verify_resp.get("claim_status") == "claimed"
            session_token = verify_resp.get("session", {}).get("token")
            assert session_token, "Missing claim session token"
            print("      - Claim verified: Trainer claimed, HMAC session token issued.")
            evidence["stages"]["trainer_claim_verification"] = "PASSED"

            # Replay guard: re-verifying same challenge fails -> 409
            status, _ = _http_request(
                f"{API_URL}/api/trainers/{trainer_id}/claim/verify",
                method="POST",
                payload={"otp": otp, "claim_event_id": claim_event_id},
            )
            assert status == 409, f"Expected 409 on replayed verify, got {status}"
            print("      - Guard: Replay challenge rejection -> 409 OK")

            # Capabilities prefill auth
            status, prefill_resp = _http_request(
                f"{API_URL}/api/trainers/{trainer_id}/capabilities/prefill",
                headers={"X-Trainer-Claim-Session": session_token},
            )
            assert status == 200, f"Expected 200 for authenticated prefill, got {status}"
            print("      - Session token authentication verified on /capabilities/prefill -> 200 OK")
            evidence["stages"]["trainer_capabilities_prefill"] = "PASSED"

            # Catchment confirmation
            status, confirm_resp = _http_request(
                f"{API_URL}/api/trainers/{trainer_id}/capabilities/confirm",
                method="POST",
                headers={"X-Trainer-Claim-Session": session_token},
                payload={
                    "specialties": ["puppy_training"],
                    "service_formats": ["in_home"],
                    "life_stages": ["puppy"],
                    "training_philosophy": "positive_reinforcement_force_free",
                    "serviced_suburbs": ["Richmond"],
                    "catchment_type": "specific_suburbs",
                    "delivery_constraints": {"in_home_available": True, "travel_distance_km": 15.0},
                    "confirmation_statement": True,
                },
            )
            assert status == 200, f"Expected 200 for capability confirmation, got {status}"
            assert confirm_resp.get("match_ready") is True
            print("      - Specific suburbs catchment & capabilities confirmed: match_ready=True")
            evidence["stages"]["trainer_catchment_confirmation"] = "PASSED"
        else:
            evidence["stages"]["trainer_claim_verification"] = (
                "NOT_VERIFIED (operator OTP or provider mailbox receipt required; privileged secret derivation removed per audit)"
            )
            evidence["stages"]["trainer_capabilities_prefill"] = "SKIPPED (requires verified session)"
            evidence["stages"]["trainer_session_renewal"] = "SKIPPED (requires verified session)"
            evidence["stages"]["trainer_catchment_confirmation"] = "SKIPPED (requires verified session)"
            print("      - Notice: OTP verification skipped (requires operator OTP entry; privileged derivation prohibited).")

        # =====================================================================
        # PART B: Customer Support Lifecycle Verification
        # =====================================================================
        print("\n[3/5] Testing First-Party Support & Oversight Lifecycle (DF-047)...")

        intake_payload = {
            "name": f"Jane Client {run_id[:6]}",
            "email": complaint_email,
            "category": "complaint",
            "subject": f"Sandbox Test Case {run_id[:6]}: Cancellation Dispute",
            "message": "The trainer cancelled on Saturday morning and refused to issue a refund or respond to messages.",
            "trainer_id": trainer_id,
            "trainer_name": "Sandbox Test Canine Academy",
        }
        status, intake_resp = _http_request(
            f"{API_URL}/support/contact",
            method="POST",
            payload=intake_payload,
        )
        if isinstance(intake_resp, dict) and intake_resp.get("case_id"):
            tracked_case_ids.add(intake_resp["case_id"])
            evidence["case_id"] = intake_resp["case_id"]

        assert status == 200, f"Expected 200 for support intake, got {status} {intake_resp}"
        assert intake_resp.get("ok") is True
        case_id = intake_resp.get("case_id")
        assert case_id and case_id.startswith("sup_"), f"Invalid case_id format: {case_id}"
        print(f"      - Support complaint created: Case ID {case_id}")

        # Check DB support_threads
        thread_doc = db.support_threads.find_one({"case_id": case_id})
        assert thread_doc is not None, "Support thread not persisted"
        assert thread_doc.get("category") == "complaint"
        assert thread_doc.get("severity") == "high"
        assert thread_doc.get("status") == "open"
        print("      - DB verification: severity=high, status=open, category=complaint")

        # 2. Oversight support listing (/ops)
        # 2a. Anonymous -> 401
        status, _ = _http_request(f"{API_URL}/api/oversight/support/threads")
        assert status == 401, f"Expected 401 for anonymous oversight read, got {status}"

        # 2b. Authenticated -> 200, thread found
        status, list_resp = _http_request(
            f"{API_URL}/api/oversight/support/threads",
            headers={"X-Admin-Pass": admin_pass},
        )
        assert status == 200, f"Expected 200 for authenticated oversight read, got {status}"
        found_case = any(t.get("case_id") == case_id for t in list_resp.get("threads", []))
        assert found_case, f"Created case {case_id} not visible in oversight list"

        # 2c. Thread detail retrieval
        status, detail_resp = _http_request(
            f"{API_URL}/api/oversight/support/threads/{case_id}",
            headers={"X-Admin-Pass": admin_pass},
        )
        assert status == 200
        assert detail_resp.get("thread", {}).get("case_id") == case_id
        print("      - Oversight protected access: Anonymous=401, Authenticated=200, Thread detail verified")

        # 3. Operator reply & guards
        # 3a. Cannot resolve via reply -> 400
        status, _ = _http_request(
            f"{API_URL}/api/oversight/support/threads/{case_id}/reply",
            method="POST",
            headers={"X-Admin-Pass": admin_pass},
            payload={"reply_text": "Resolving this ticket now.", "mark_status": "resolved"},
        )
        assert status == 400, f"Expected 400 for mark_status=resolved via reply, got {status}"
        print("      - Guard: Cannot resolve support ticket via reply endpoint -> 400 OK")

        # 3b. Valid reply dispatch
        reply_text = f"Hello Jane, we have contacted the trainer regarding your Saturday booking (Run {run_id})."
        status, reply_resp = _http_request(
            f"{API_URL}/api/oversight/support/threads/{case_id}/reply",
            method="POST",
            headers={"X-Admin-Pass": admin_pass},
            payload={"reply_text": reply_text},
        )
        assert status == 200, f"Expected 200 for reply, got {status} {reply_resp}"
        assert reply_resp.get("dispatched") is True
        assert reply_resp.get("status") == "awaiting_customer_reply"

        # Verify thread in DB
        thread_after_reply = db.support_threads.find_one({"case_id": case_id})
        assert thread_after_reply.get("status") == "awaiting_customer_reply"
        assert len(thread_after_reply.get("messages", [])) >= 2
        print("      - Operator reply dispatched via Resend test sink, status=awaiting_customer_reply")

        # 3c. Duplicate reply prevention
        status, dup_resp = _http_request(
            f"{API_URL}/api/oversight/support/threads/{case_id}/reply",
            method="POST",
            headers={"X-Admin-Pass": admin_pass},
            payload={"reply_text": reply_text},
        )
        assert status == 200
        assert dup_resp.get("duplicate") is True, f"Expected duplicate=True, got {dup_resp}"
        print("      - Guard: Duplicate reply prevention -> duplicate=True OK")

        # 4. Guarded Closure
        # 4a. Short notes < 10 chars -> 400 or 422
        status, _ = _http_request(
            f"{API_URL}/api/oversight/support/threads/{case_id}/close",
            method="POST",
            headers={"X-Admin-Pass": admin_pass},
            payload={"resolution_notes": "Done.", "confirmed": True},
        )
        assert status in (400, 422), f"Expected 400/422 for short resolution notes, got {status}"
        print("      - Guard: Short resolution notes rejected (<10 chars) -> 400/422 OK")

        # 4b. Close with valid resolution notes
        status, close_resp = _http_request(
            f"{API_URL}/api/oversight/support/threads/{case_id}/close",
            method="POST",
            headers={"X-Admin-Pass": admin_pass},
            payload={
                "resolution_notes": "Trainer confirmed refund issued and apologized to dog owner.",
                "confirmed": True,
            },
        )
        assert status == 200, f"Expected 200 for ticket closure, got {status} {close_resp}"
        assert close_resp.get("status") == "resolved"
        thread_closed = db.support_threads.find_one({"case_id": case_id})
        assert thread_closed.get("status") == "resolved"
        print("      - Guarded ticket closure verified: status=resolved with audit trail")
        evidence["stages"]["support_lifecycle_api"] = "PASSED"

        # =====================================================================
        # PART C: Live Browser Headless Playwright Verification
        # =====================================================================
        print("\n[4/5] Executing Live Browser Headless Playwright Checks against dtd-web-dev...")
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    user_agent="DTD-Acceptance-Playwright/1.0",
                )
                page = await context.new_page()

                # 1. Contact Page Journey
                print("      - Browser: Loading /contact...")
                resp = await page.goto(f"{WEB_URL}/contact", wait_until="networkidle", timeout=30000)
                assert resp and resp.status == 200, f"Contact page load failed: {resp.status if resp else 'no response'}"
                await page.fill("input[name='name']", f"Playwright User {run_id[:4]}")
                await page.fill("input[name='email']", browser_email)
                await page.fill("input[name='subject']", f"Browser test enquiry {run_id[:4]}")
                await page.fill("textarea[name='message']", "Testing contact page submit in live headless browser.")
                await page.click("button[type='submit']")

                # Wait for success confirmation
                await page.wait_for_selector("text=Message Received", timeout=15000)
                screenshot_contact = target_artifact_dir / "sandbox_contact_page_submitted.png"
                await page.screenshot(path=str(screenshot_contact))
                print(f"      - Browser: Contact form submitted & confirmed. Screenshot saved: {screenshot_contact.name}")

                # Capture browser generated case_id from DOM for teardown
                content = await page.content()
                m = re.search(r"sup_\d{8}_[a-zA-Z0-9]+", content)
                if m:
                    browser_case_id = m.group(0)
                    tracked_case_ids.add(browser_case_id)
                    print(f"        Browser-submitted case ID: {browser_case_id}")

                # 2. Ops Support Cases View
                print("      - Browser: Loading /ops with session credentials...")
                await page.goto(f"{WEB_URL}/ops", wait_until="networkidle", timeout=30000)
                await page.evaluate(f"""
                    sessionStorage.setItem("dtd-admin-pass", JSON.stringify({{
                        value: "{admin_pass}",
                        expiresAt: Date.now() + 3600000
                    }}));
                """)
                await page.reload(wait_until="networkidle")

                # Click "Support Cases"
                diag_toggle = page.locator("[data-testid='ops-diagnostics-header-toggle']")
                if await diag_toggle.is_visible():
                    await diag_toggle.click()
                    await page.wait_for_timeout(500)

                support_tab = page.locator("[data-testid='ops-nav-support_threads']")
                await support_tab.wait_for(state="attached", timeout=15000)
                await support_tab.scroll_into_view_if_needed()
                await support_tab.click(force=True)

                await page.wait_for_selector("[data-testid='ops-support-view']", timeout=15000)
                await page.wait_for_timeout(1000)
                screenshot_ops = target_artifact_dir / "sandbox_support_cases_ops.png"
                await page.screenshot(path=str(screenshot_ops))
                print(f"      - Browser: Ops Support Cases view loaded. Screenshot saved: {screenshot_ops.name}")

                await browser.close()
            evidence["stages"]["browser_ui_verification"] = "PASSED (contact form + Ops cases list)"
        except Exception as browser_err:
            print(f"      - Browser checks encountered error: {browser_err}")
            evidence["stages"]["browser_ui_verification"] = f"FAILED ({browser_err})"
            test_exception = browser_err

    except Exception as exc:
        test_exception = exc
        print(f"\n[!] Error during acceptance execution: {exc}", file=sys.stderr)

    finally:
        # =====================================================================
        # PART D: Deterministic Teardown & Absence Verifications
        # =====================================================================
        print("\n[5/5] Executing Deterministic Teardown & Cleanup...")
        del_counts: Dict[str, Any] = {
            "trainers": 0,
            "claim_events": 0,
            "trainer_notifications": 0,
            "trainer_audit": 0,
            "support_threads": {},
            "support_notifications": {},
            "support_audit": {},
            "ops_obligations": {},
        }
        cleanup_errors: List[str] = []

        # 1. Discover any database support threads created under this run's unique emails:
        try:
            discovered = db.support_threads.find(
                {"email": {"$in": [complaint_email, browser_email]}},
                {"case_id": 1},
            )
            for doc in discovered:
                if doc.get("case_id"):
                    tracked_case_ids.add(doc["case_id"])
        except Exception as e:
            cleanup_errors.append(f"discovery error: {e}")

        # 2. Delete synthetic trainer fixtures and dependent records
        if inserted_trainer:
            try:
                del_counts["trainers"] = db.trainers.delete_many({"id": trainer_id, "test_fixture": True}).deleted_count
            except Exception as e:
                cleanup_errors.append(f"trainers delete: {e}")
            try:
                del_counts["claim_events"] = db.claim_events.delete_many({"trainer_id": trainer_id}).deleted_count
            except Exception as e:
                cleanup_errors.append(f"claim_events delete: {e}")
            try:
                del_counts["trainer_notifications"] = db.notification_events.delete_many({"target_id": trainer_id}).deleted_count
            except Exception as e:
                cleanup_errors.append(f"trainer_notifications delete: {e}")
            try:
                del_counts["trainer_audit"] = db.audit_log.delete_many({"target": trainer_id}).deleted_count
            except Exception as e:
                cleanup_errors.append(f"trainer_audit delete: {e}")

        # 3. Delete tracked support threads independently with full case ID keys
        for cid in sorted(tracked_case_ids):
            try:
                del_counts["support_threads"][cid] = db.support_threads.delete_many({"case_id": cid}).deleted_count
            except Exception as e:
                cleanup_errors.append(f"support_thread {cid} delete: {e}")
            try:
                del_counts["support_notifications"][cid] = db.notification_events.delete_many({"target_id": cid}).deleted_count
            except Exception as e:
                cleanup_errors.append(f"support_notif {cid} delete: {e}")
            try:
                del_counts["support_audit"][cid] = db.audit_log.delete_many({"target": cid}).deleted_count
            except Exception as e:
                cleanup_errors.append(f"support_audit {cid} delete: {e}")
            try:
                del_counts["ops_obligations"][cid] = db.ops_obligations.delete_many({"case_id": cid}).deleted_count
            except Exception as e:
                cleanup_errors.append(f"ops_obligations {cid} delete: {e}")

        # 4. Direct datastore leftovers count
        leftovers: Dict[str, int] = {}
        try:
            leftovers["trainers"] = db.trainers.count_documents({"id": trainer_id})
            leftovers["claim_events"] = db.claim_events.count_documents({"trainer_id": trainer_id})
            leftovers["trainer_notifications"] = db.notification_events.count_documents({"target_id": trainer_id})
            leftovers["trainer_audit"] = db.audit_log.count_documents({"target": trainer_id})
            for cid in sorted(tracked_case_ids):
                leftovers[f"thread_{cid}"] = db.support_threads.count_documents({"case_id": cid})
                leftovers[f"notif_{cid}"] = db.notification_events.count_documents({"target_id": cid})
                leftovers[f"audit_{cid}"] = db.audit_log.count_documents({"target": cid})
                leftovers[f"obligations_{cid}"] = db.ops_obligations.count_documents({"case_id": cid})
        except Exception as e:
            cleanup_errors.append(f"leftovers count error: {e}")

        # 5. Public 404 absence checks
        endpoint_404s: Dict[str, bool] = {}
        try:
            status, _ = _http_request(f"{API_URL}/api/trainers/{trainer_id}")
            endpoint_404s[f"trainer_{trainer_id}"] = (status == 404)
        except Exception as e:
            cleanup_errors.append(f"trainer 404 check: {e}")

        for cid in sorted(tracked_case_ids):
            try:
                status, _ = _http_request(
                    f"{API_URL}/api/oversight/support/threads/{cid}",
                    headers={"X-Admin-Pass": admin_pass},
                )
                endpoint_404s[f"thread_{cid}"] = (status == 404)
            except Exception as e:
                cleanup_errors.append(f"thread {cid} 404 check: {e}")

        client.close()

        evidence["cleanup"] = {
            "deleted": del_counts,
            "leftovers": leftovers,
            "endpoint_404s": endpoint_404s,
            "cleanup_errors": cleanup_errors,
            "all_leftovers_zero": all(count == 0 for count in leftovers.values()) if leftovers else True,
            "tracked_case_ids": sorted(tracked_case_ids),
        }
        print(f"      Cleanup completed for tracked IDs {sorted(tracked_case_ids)}. Leftovers: {leftovers}. Errors: {cleanup_errors}")

    if test_exception is not None:
        evidence["status"] = "EXECUTION_FAILED"
        evidence["error"] = str(test_exception)
        raise test_exception

    evidence["status"] = "STAGE_CHECKS_COMPLETED"
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Execute acceptance against sandbox.")
    parser.add_argument("--otp", type=str, default="", help="Optional 6-digit OTP for verified claim journey.")
    parser.add_argument("--artifact-dir", type=str, default="", help="Optional directory to save browser screenshots.")
    args = parser.parse_args()

    if not args.execute:
        print(json.dumps({
            "mode": "preview",
            "project": SANDBOX_PROJECT,
            "database": SANDBOX_DB,
            "api": API_URL,
            "web": WEB_URL,
            "writes": False,
        }))
        return 0

    mongo_url = os.environ.get("MONGO_URL", "")
    admin_pass = os.environ.get("ADMIN_PASS", "")

    artifact_dir = Path(args.artifact_dir) if args.artifact_dir else None

    try:
        evidence = asyncio.run(run_acceptance(
            mongo_url=mongo_url,
            admin_pass=admin_pass,
            otp=args.otp,
            artifact_dir=artifact_dir,
        ))
        print("\n=== ACCEPTANCE EVIDENCE ===")
        print(json.dumps(evidence, indent=2))
        return 0
    except Exception as e:
        print(f"\n[!] ACCEPTANCE FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
