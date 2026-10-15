#!/usr/bin/env python3
"""Exercise the trainer claim UI against one disposable developer fixture.

This runner creates one unmistakably synthetic, temporarily public listing in
the isolated DTD developer sandbox and waits for the browser UI to start and
verify the normal claim flow using Resend's delivered test sink. It never reads
or prints the OTP, session token, or secret values. Every application record
created by the flow is removed in ``finally`` and public absence is checked
before the runner exits.
"""
from __future__ import annotations

import argparse
import json
import os
import select
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pymongo import MongoClient


PROJECT_ID = "dogtrainersdirectory-dev"
DATABASE_NAME = "dtd_sandbox"
TEST_RECIPIENT = "delivered@resend.dev"
API_URL = "https://dtd-api-dev-625222421634.australia-southeast1.run.app"
WEB_URL = "https://dtd-web-dev-x2kdoaemtq-ts.a.run.app"
CLAIM_AUDIT_ACTIONS = {
    "trainer_claim_started",
    "trainer_claim_verified",
    "trainer_claim_rate_limited",
}


def _request_json(url: str, method: str = "GET", payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=20) as response:  # nosec B310: exact sandbox origin is checked below
        return json.loads(response.read().decode("utf-8"))


def _require_sandbox(mongo_url: str) -> None:
    if os.environ.get("DTD_SANDBOX_PROJECT_ID") != PROJECT_ID:
        raise SystemExit("Refusing to run without the explicit developer project identity.")
    if os.environ.get("DTD_SANDBOX_DATABASE") != DATABASE_NAME:
        raise SystemExit("Refusing to run without the explicit developer database identity.")
    if not mongo_url:
        raise SystemExit("MONGO_URL must be supplied by the sandbox wrapper.")
    if urlparse(API_URL).hostname != "dtd-api-dev-625222421634.australia-southeast1.run.app":
        raise SystemExit("Refusing an unexpected API endpoint.")
    if urlparse(WEB_URL).hostname != "dtd-web-dev-x2kdoaemtq-ts.a.run.app":
        raise SystemExit("Refusing an unexpected frontend endpoint.")


def _http_status(url: str) -> int:
    try:
        with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=20) as response:
            return int(response.status)
    except HTTPError as error:
        return int(error.code)


def _cleanup(db: Any, trainer_id: str) -> Dict[str, int]:
    exact = {
        "trainers": {"id": trainer_id, "test_fixture": True},
        "claim_events": {"trainer_id": trainer_id},
        "notification_events": {
            "target_kind": "trainer_claim",
            "target_id": trainer_id,
            "kind": "trainer_claim_otp",
        },
        "audit_log": {"target": trainer_id, "action": {"$in": sorted(CLAIM_AUDIT_ACTIONS)}},
    }
    deleted = {name: db[name].delete_many(query).deleted_count for name, query in exact.items()}
    leftovers = {name: db[name].count_documents(query) for name, query in exact.items()}
    if any(leftovers.values()):
        raise RuntimeError(f"Exact sandbox cleanup left records: {leftovers}")
    if _http_status(f"{API_URL}/api/trainers/{trainer_id}") != 404:
        raise RuntimeError("Synthetic trainer is still publicly retrievable after cleanup.")
    return deleted


def _wait_for_ui_claim_start(db: Any, trainer_id: str, timeout_seconds: int) -> Dict[str, str]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        events = list(db.claim_events.find(
            {"trainer_id": trainer_id},
            {"_id": 0, "id": 1, "status": 1, "delivery_status": 1},
        ))
        if len(events) > 1:
            raise RuntimeError("Synthetic profile received more than one claim challenge; refusing an ambiguous run.")
        event = events[0] if events else {}
        status = str(event.get("status") or "")
        if status == "delivery_failed":
            raise RuntimeError("The claim code was not delivered to the Resend test sink.")
        if status == "pending_verification" and event.get("delivery_status") == "sent":
            notification = db.notification_events.find_one(
                {"target_kind": "trainer_claim", "target_id": trainer_id, "kind": "trainer_claim_otp", "status": "sent", "provider_id": {"$ne": ""}},
                {"_id": 0, "provider_id": 1, "http_status": 1},
            )
            if not notification or not notification.get("provider_id"):
                raise RuntimeError("The UI-started test email has no recorded provider message ID.")
            if not 200 <= int(notification.get("http_status") or 0) < 300:
                raise RuntimeError("The test-sink email did not record a successful provider HTTP response.")
            return {"claim_event_id": str(event["id"]), "provider_id": str(notification["provider_id"])}
        if status and status != "pending_verification":
            raise RuntimeError(f"Claim UI created an unexpected challenge state: {status}.")
        time.sleep(2)
    raise TimeoutError("Timed out waiting for the browser UI to start the claim flow.")


def _wait_for_verified_claim(db: Any, trainer_id: str, claim_event_id: str, timeout_seconds: int) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        event = db.claim_events.find_one(
            {"id": claim_event_id, "trainer_id": trainer_id},
            {"_id": 0, "id": 1, "status": 1, "delivery_status": 1},
        )
        status = str((event or {}).get("status") or "")
        if status == "verified":
            trainer = db.trainers.find_one(
                {"id": trainer_id, "test_fixture": True},
                {"_id": 0, "claim_status": 1, "tier": 1, "claim_event_id": 1},
            )
            if not trainer or trainer.get("claim_status") != "claimed" or trainer.get("tier") != "claimed":
                raise RuntimeError("Verified claim did not persist the expected trainer state.")
            if trainer.get("claim_event_id") != claim_event_id:
                raise RuntimeError("Claimed trainer references a different claim event.")
            actions = {
                str(row.get("action") or "")
                for row in db.audit_log.find({"target": trainer_id}, {"_id": 0, "action": 1})
            }
            if not {"trainer_claim_started", "trainer_claim_verified"}.issubset(actions):
                raise RuntimeError("Claim lifecycle audit evidence is incomplete.")
            notifications = list(db.notification_events.find(
                {"target_kind": "trainer_claim", "target_id": trainer_id, "kind": "trainer_claim_otp"},
                {"_id": 0, "status": 1, "http_status": 1, "provider_id": 1},
            ))
            sent = [
                row for row in notifications
                if row.get("status") == "sent"
                and row.get("provider_id")
                and 200 <= int(row.get("http_status") or 0) < 300
            ]
            if not sent:
                raise RuntimeError("No successful provider message ID was recorded for the claim OTP.")
            return {"notification_count": len(notifications), "successful_message_count": len(sent)}
        if status in {"delivery_failed", "expired", "locked", "stale", "superseded"}:
            raise RuntimeError(f"Claim challenge ended in {status} before verification.")
        time.sleep(2)
    raise TimeoutError("Timed out waiting for the real browser claim verification.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Create the temporary sandbox listing and start the claim flow.")
    parser.add_argument("--timeout-seconds", type=int, default=600, help="Maximum time to wait for OTP verification (60–900 seconds).")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"mode": "preview", "project": PROJECT_ID, "database": DATABASE_NAME, "recipient": TEST_RECIPIENT, "api": API_URL, "frontend": WEB_URL, "writes": False}))
        return 0
    if not sys.stdin.isatty():
        raise SystemExit("Execute mode requires an interactive terminal for the bounded browser handoff.")
    if not 60 <= args.timeout_seconds <= 900:
        raise SystemExit("--timeout-seconds must be between 60 and 900.")

    mongo_url = os.environ.get("MONGO_URL", "")
    _require_sandbox(mongo_url)
    health = _request_json(f"{API_URL}/api/health")
    config = _request_json(f"{API_URL}/api/config")
    if health.get("database") != "available" or config.get("public_matching_enabled") is not True:
        raise SystemExit("Developer API preflight did not show an available database and active sandbox service.")

    run_id = uuid.uuid4().hex
    trainer_id = f"sandbox-claim-{run_id}"
    now = datetime.now(timezone.utc).isoformat()
    fixture = {
        "id": trainer_id,
        "slug": trainer_id,
        "name": f"Sandbox claim fixture {run_id[:8]} — not a real trainer",
        "suburb": "Richmond",
        "region": "Greater Melbourne",
        "published": True,
        "contact_ready": False,
        "verification_status": "unverified",
        "claim_status": "unclaimed",
        "tier": "free",
        "email": TEST_RECIPIENT,
        "test_fixture": True,
        "test_run_id": run_id,
        "created_at": now,
        "updated_at": now,
    }
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
    db = client[DATABASE_NAME]
    inserted = False
    try:
        client.admin.command("ping")
        if db.trainers.count_documents({"id": trainer_id}):
            raise RuntimeError("Generated fixture ID already exists; refusing to overwrite it.")
        db.trainers.insert_one(dict(fixture))
        inserted = True

        profile_status = _http_status(f"{API_URL}/api/trainers/{trainer_id}")
        if profile_status != 200:
            raise RuntimeError(f"Synthetic developer profile did not load (HTTP {profile_status}).")
        print(json.dumps({
            "stage": "awaiting_browser_claim_start",
            "synthetic_trainer_id": trainer_id,
            "test_recipient": TEST_RECIPIENT,
            "profile_url": f"{WEB_URL}/t/{trainer_id}",
            "instructions": "Use the developer profile UI to start a claim with the exact test recipient. The runner will report the resulting Resend message ID, then wait for UI verification and clean up automatically.",
            "otp_or_session_token_printed": False,
        }), flush=True)

        challenge = _wait_for_ui_claim_start(db, trainer_id, args.timeout_seconds)
        print(json.dumps({
            "stage": "awaiting_browser_verification",
            "synthetic_trainer_id": trainer_id,
            "claim_event_id": challenge["claim_event_id"],
            "resend_message_id": challenge["provider_id"],
            "test_recipient": TEST_RECIPIENT,
            "instructions": "Open only this Resend message ID, enter its OTP in the current developer claim dialog, then skip capability confirmation.",
            "otp_or_session_token_printed": False,
        }), flush=True)

        verified = _wait_for_verified_claim(db, trainer_id, challenge["claim_event_id"], args.timeout_seconds)
        # Give the browser a brief window to render its success state and finish
        # the capability-step skip before removing the temporary public fixture.
        print(json.dumps({"stage": "claim_verified_review_ui", "instructions": "Confirm the browser shows Identity claimed and Manage your listing, then press Enter in the runner terminal to clean up."}), flush=True)
        ready, _, _ = select.select([sys.stdin], [], [], 60)
        if ready:
            sys.stdin.readline()
        else:
            print(json.dumps({"browser_ui_grace_period_elapsed": True}), flush=True)
        print(json.dumps({"verified": True, **verified}), flush=True)
        return 0
    finally:
        try:
            if inserted:
                deleted = _cleanup(db, trainer_id)
                print(json.dumps({"cleanup_complete": True, "deleted": deleted}), flush=True)
        finally:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
