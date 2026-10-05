#!/usr/bin/env python3
"""Run one disposable, end-to-end owner-to-trainer matching acceptance test.

The runner is deliberately opt-in and sandbox-only. It creates a uniquely
tagged trainer with confirmed structured capability facts, performs a public
``POST /api/match``, verifies the protected matching Ops read model, then
removes the fixture and every matching record produced by the test in a
``finally`` block. It never submits an enquiry, so it cannot send email or
touch billing. Secrets are provided only through process environment variables
by the small shell wrapper and are never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pymongo import MongoClient


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.trainer_quality import package_trainer_capabilities  # noqa: E402


SANDBOX_PROJECT = "dogtrainersdirectory-dev"
SANDBOX_DB = "dtd_sandbox"
DEFAULT_SERVICE_URL = "https://dtd-api-dev-625222421634.australia-southeast1.run.app"


def _json_request(url: str, *, method: str, payload: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=request_headers, method=method)
    with urlopen(req, timeout=20) as response:  # nosec B310: caller is sandbox-gated below
        return json.loads(response.read().decode("utf-8"))


def _require_sandbox(url: str, mongo_url: str, db_name: str) -> None:
    parsed = urlparse(url)
    mongo_host = (urlparse(mongo_url).hostname or "").lower()
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".run.app"):
        raise SystemExit("Refusing a non-Cloud-Run acceptance endpoint.")
    if "dtd-api-dev" not in parsed.hostname or db_name != SANDBOX_DB:
        raise SystemExit("Refusing a non-developer-sandbox service or database.")
    if not mongo_host:
        raise SystemExit("MongoDB URI has no host.")


def _fixture(run_id: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    trainer_id = f"sandbox-acceptance-{run_id}"
    capabilities = package_trainer_capabilities(
        specialties=["puppy_training", "leash_reactivity"],
        service_formats=["in_home"],
        life_stages=["puppy", "adolescent"],
        training_philosophy="positive_reinforcement_force_free",
        serviced_suburbs=["Fitzroy"],
        catchment_type="specific_suburbs",
        delivery_constraints={"in_home_available": True, "facility_available": False, "travel_distance_km": 10},
        basis="trainer_declaration",
        evidence_reference="sandbox_acceptance_fixture",
        confirmed_at=now,
    )
    return {
        "id": trainer_id,
        "slug": trainer_id,
        "name": "Sandbox acceptance fixture — not a real trainer",
        "suburb": "Fitzroy",
        "region": "Greater Melbourne",
        "published": True,
        "contact_ready": True,
        "verification_status": "verified",
        "claim_status": "claimed",
        "tier": "claimed",
        "capabilities": capabilities,
        "website": "https://example.test/dtd-sandbox-acceptance",
        "email": "sandbox-acceptance@example.test",
        "source_evidence_url": "https://example.test/dtd-sandbox-acceptance",
        "test_run_id": run_id,
        "test_fixture": True,
        "created_at": now,
        "updated_at": now,
    }


def _require_public_absence(service_url: str, trainer_id: str) -> None:
    """Confirm the deleted fixture cannot remain visible to directory UI calls."""
    try:
        _json_request(f"{service_url.rstrip('/')}/api/trainers/{trainer_id}", method="GET")
    except HTTPError as error:
        if error.code == 404:
            return
        raise
    raise RuntimeError("Deleted sandbox fixture remains publicly retrievable.")


def _cleanup(
    db: Any,
    *,
    run_id: str,
    trainer_id: str,
    match_id: str | None,
    pre_existing_degradation_ids: set[str],
) -> Dict[str, int]:
    # Matching may enter its safe Gemini fallback. The current degradation
    # record schema has no request correlation field, so snapshot IDs before
    # the test and remove only the newly-created matching entries afterwards.
    # This runner is restricted to the isolated developer sandbox for that
    # reason; it must never be used against shared production traffic.
    new_degradation_ids = [
        str(row.get("id"))
        for row in db.ai_degradation_events.find({"operation": "matching"}, {"_id": 0, "id": 1})
        if row.get("id") and str(row.get("id")) not in pre_existing_degradation_ids
    ]
    matching_event_ids = {
        str(row.get("id"))
        for row in db.match_events.find({"result_ids": trainer_id}, {"_id": 0, "id": 1})
        if row.get("id")
    }
    if match_id:
        matching_event_ids.add(match_id)
    context_query: Dict[str, Any] = {"match_id": {"$in": sorted(matching_event_ids)}} if matching_event_ids else {"match_id": "__none__"}
    queries = {
        "trainers": {"test_run_id": run_id},
        "match_events": {"id": {"$in": sorted(matching_event_ids)}} if matching_event_ids else {"result_ids": trainer_id},
        "match_contexts": context_query,
        "ai_degradation_events": {"id": {"$in": new_degradation_ids}} if new_degradation_ids else {"id": "__none__"},
    }
    deleted: Dict[str, int] = {}
    for collection, query in queries.items():
        deleted[collection] = db[collection].delete_many(query).deleted_count
    remaining = sum(db[name].count_documents(query) for name, query in queries.items())
    if remaining:
        raise RuntimeError("Sandbox fixture cleanup was incomplete.")
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Perform the sandbox write/test/cleanup cycle.")
    parser.add_argument("--service-url", default=os.environ.get("DTD_SANDBOX_SERVICE_URL", DEFAULT_SERVICE_URL))
    parser.add_argument("--mongo-url", default=os.environ.get("MONGO_URL", ""))
    parser.add_argument("--admin-pass", default=os.environ.get("ADMIN_PASS", ""))
    args = parser.parse_args()
    if not args.execute:
        print("Preview only: pass --execute after supplying sandbox MONGO_URL and ADMIN_PASS.")
        return 0
    if not args.mongo_url or not args.admin_pass:
        raise SystemExit("MONGO_URL and ADMIN_PASS must be supplied through environment variables.")

    _require_sandbox(args.service_url.rstrip("/"), args.mongo_url, SANDBOX_DB)
    run_id = uuid.uuid4().hex
    fixture = _fixture(run_id)
    client = MongoClient(args.mongo_url, serverSelectionTimeoutMS=10000)
    db = client[SANDBOX_DB]
    match_id: str | None = None
    pre_existing_degradation_ids: set[str] = set()
    degradation_snapshot_ready = False
    try:
        client.admin.command("ping")
        pre_existing_degradation_ids = {
            str(row.get("id"))
            for row in db.ai_degradation_events.find({}, {"_id": 0, "id": 1})
            if row.get("id")
        }
        degradation_snapshot_ready = True
        db.trainers.insert_one(dict(fixture))
        response = _json_request(
            f"{args.service_url.rstrip('/')}/api/match",
            method="POST",
            payload={
                "suburb_or_postcode": "Fitzroy",
                "dog_age_months": 4,
                "primary_concerns": ["puppy_prep"],
                "service_format": "in_home",
                "method_preference": "positive_reinforcement_only",
                "behaviour_description": "Needs a calm plan for early puppy training.",
                "consent": {"match_processing": True, "terms": True, "referral_contact": False, "follow_up": False},
            },
        )
        match_id = str(response.get("match_id") or "")
        candidate_ids = {str(row.get("trainer_id") or row.get("id") or "") for row in response.get("candidates", []) + response.get("matches", [])}
        if not match_id or fixture["id"] not in candidate_ids:
            raise RuntimeError("Live matching did not return the disposable match-ready trainer.")
        stored_event = db.match_events.find_one({"id": match_id}, {"_id": 0})
        if not stored_event or "behaviour_description" in stored_event:
            raise RuntimeError("Match event persistence was absent or retained raw owner description.")
        ops = _json_request(
            f"{args.service_url.rstrip('/')}/api/oversight/matching",
            method="GET",
            headers={"X-Admin-Pass": args.admin_pass},
        )
        ops_ids = {str(row.get("match_id") or "") for row in ops.get("presentation_order_sample", [])}
        if match_id not in ops_ids:
            raise RuntimeError("The match event was not visible in the protected matching Ops read model.")
        print(json.dumps({"ok": True, "sandbox_project": SANDBOX_PROJECT, "match_persisted": True, "ops_visible": True, "raw_description_stored": False}))
        return 0
    finally:
        try:
            deleted = _cleanup(
                db,
                run_id=run_id,
                trainer_id=str(fixture["id"]),
                match_id=match_id,
                pre_existing_degradation_ids=pre_existing_degradation_ids if degradation_snapshot_ready else {str(row.get("id")) for row in db.ai_degradation_events.find({}, {"_id": 0, "id": 1}) if row.get("id")},
            )
            _require_public_absence(args.service_url, str(fixture["id"]))
            print(json.dumps({"cleanup_complete": True, "deleted": deleted}))
        finally:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
