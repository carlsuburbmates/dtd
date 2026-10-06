#!/usr/bin/env python3
"""Prove live Gemini/fallback parity using one disposable sandbox fixture.

This runner intentionally changes *only* the developer Cloud Run service's
``GEMINI_MODEL`` environment variable for the brief forced-fallback leg.  It
refuses any non-sandbox target, requires the normal sandbox model before it
starts, restores that model in ``finally``, and removes every namespaced record
that it created.  It never invokes email, billing, acquisition, or production.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

from pymongo import MongoClient


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.matching_contract_v2 import (  # noqa: E402
    CONCERN_TO_SPECIALTIES_MAP,
    MatchRequestIn,
    get_dog_age_category,
)
from backend.services.trainer_quality import package_trainer_capabilities  # noqa: E402
from scripts.run_sandbox_matching_matrix import (  # noqa: E402
    DEFAULT_SERVICE_URL,
    SANDBOX_DB,
    SANDBOX_PROJECT,
    _expect_http_error,
    _find_no_match_payload,
    _match_payload,
    _request,
    _require_public_absence,
    _require_sandbox,
)


REGION = "australia-southeast1"
SERVICE = "dtd-api-dev"
EXPECTED_NORMAL_MODEL = "gemini-3.5-flash"


def _progress(stage: str) -> None:
    """Emit a safe checkpoint so an interrupted control-plane run is diagnosable."""
    print(json.dumps({"stage": stage}), flush=True)


def _service_env() -> Dict[str, str]:
    """Read literal env values from the explicitly named sandbox service."""
    result = subprocess.run(
        [
            "gcloud", "run", "services", "describe", SERVICE,
            "--project", SANDBOX_PROJECT,
            "--region", REGION,
            "--format=json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    service = json.loads(result.stdout)
    containers = ((service.get("spec") or {}).get("template") or {}).get("spec", {}).get("containers") or []
    if len(containers) != 1:
        raise RuntimeError("Sandbox Cloud Run service did not expose exactly one runtime container.")
    values: Dict[str, str] = {}
    for item in containers[0].get("env") or []:
        if "name" in item and "value" in item:
            values[str(item["name"])] = str(item["value"])
    return values


def _set_model(model: str) -> None:
    """Update the single sandbox model setting without printing command output."""
    subprocess.run(
        [
            "gcloud", "run", "services", "update", SERVICE,
            "--project", SANDBOX_PROJECT,
            "--region", REGION,
            "--update-env-vars", f"GEMINI_MODEL={model}",
            "--quiet",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for_available_health(service_url: str, *, timeout_s: float = 180.0) -> None:
    """Wait for the new sandbox revision to become usable without leaking diagnostics."""
    deadline = time.monotonic() + timeout_s
    last_error = "unknown"
    while time.monotonic() < deadline:
        try:
            health = _request(f"{service_url}/api/health", method="GET")
            if health.get("ok") is True and health.get("database") == "available":
                return
            last_error = "health payload was not available"
        except Exception as exc:  # transient while Cloud Run promotes a revision
            last_error = type(exc).__name__
        time.sleep(3)
    raise RuntimeError(f"Sandbox revision did not regain healthy database access ({last_error}).")


def _request_for_isolated_pool(db: Any) -> Dict[str, Any]:
    """Choose an existing zero-eligibility request, then add exactly one fixture."""
    payload = _find_no_match_payload(db)
    # A model needs no behavioural narrative to assess the structured request;
    # keeping this generic also proves it cannot be retained as owner PII.
    payload["behaviour_description"] = "Needs structured support for the selected concern."
    return payload


def _fixture(run_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    request = MatchRequestIn(**payload)
    specialties = sorted({
        specialty
        for concern in request.primary_concerns
        for specialty in CONCERN_TO_SPECIALTIES_MAP[concern]
    })
    if not specialties:
        raise RuntimeError("The selected no-match request did not contain a matchable canonical concern.")

    format_map = {
        "in_home": "in_home",
        "facility_or_field": "facility",
        "group_class": "group_classes",
        "online_coaching": "online",
        "any": "in_home",
    }
    philosophy = (
        "positive_reinforcement_force_free"
        if request.method_preference == "positive_reinforcement_only"
        else "balanced" if request.method_preference == "balanced" else "positive_reinforcement_force_free"
    )
    now = datetime.now(timezone.utc).isoformat()
    trainer_id = f"sandbox-parity-{run_id}"
    suburb = request.suburb_or_postcode
    capabilities = package_trainer_capabilities(
        specialties=specialties,
        service_formats=[format_map[request.service_format]],
        life_stages=[get_dog_age_category(request.dog_age_months).value],
        training_philosophy=philosophy,
        serviced_suburbs=[suburb],
        catchment_type="specific_suburbs",
        delivery_constraints={"in_home_available": request.service_format == "in_home", "facility_available": False},
        basis="trainer_declaration",
        evidence_reference="sandbox_parity_disposable_fixture",
        confirmed_at=now,
    )
    return {
        "id": trainer_id,
        "slug": trainer_id,
        "name": "Sandbox parity fixture — not a real trainer",
        "suburb": suburb,
        "region": "Greater Melbourne",
        "published": True,
        "contact_ready": True,
        "verification_status": "verified",
        "claim_status": "claimed",
        "tier": "claimed",
        "capabilities": capabilities,
        "test_run_id": run_id,
        "test_fixture": True,
        "created_at": now,
        "updated_at": now,
    }


def _candidate_ids(response: Dict[str, Any]) -> list[str]:
    return [str(card.get("trainer_id") or card.get("id") or "") for card in response.get("candidates") or []]


def _validate_normal(response: Dict[str, Any], trainer_id: str, *, phase: str) -> None:
    if response.get("degraded"):
        raise RuntimeError(f"{phase} Gemini leg degraded instead of using the configured provider.")
    if response.get("decision_state") != "recommendations":
        raise RuntimeError(f"{phase} Gemini leg returned {response.get('decision_state')!r}, not recommendations.")
    if _candidate_ids(response) != [trainer_id]:
        raise RuntimeError(f"{phase} Gemini leg did not return exactly the isolated fixture.")
    card = (response.get("candidates") or [])[0]
    if "capability_concern_match" not in (card.get("reason_codes") or []):
        raise RuntimeError(f"{phase} Gemini leg omitted the required capability-concern reason code.")


def _validate_fallback(response: Dict[str, Any], trainer_id: str) -> None:
    if response.get("degraded") is not True:
        raise RuntimeError("Forced invalid-model leg did not disclose deterministic fallback.")
    if response.get("decision_state") != "degraded_recommendations":
        raise RuntimeError(f"Forced fallback returned {response.get('decision_state')!r}, not degraded_recommendations.")
    if _candidate_ids(response) != [trainer_id]:
        raise RuntimeError("Fallback did not return exactly the same isolated candidate as Gemini.")
    card = (response.get("candidates") or [])[0]
    if "capability_concern_match" not in (card.get("reason_codes") or []):
        raise RuntimeError("Fallback omitted the deterministic capability-concern reason code.")


def _cleanup(db: Any, *, trainer_id: str, match_ids: Iterable[str], forced_model: str) -> Dict[str, int]:
    ids = [match_id for match_id in match_ids if match_id]
    queries = {
        "trainers": {"id": trainer_id},
        "match_events": {"id": {"$in": ids}},
        "match_contexts": {"match_id": {"$in": ids}},
        "engagements": {"match_id": {"$in": ids}},
        # Only remove our uniquely labelled forced-fallback event.  Do not
        # remove other operators' legitimate degradation evidence.
        "ai_degradation_events": {"operation": "matching", "model": forced_model},
        "audit_log": {"after.match_id": {"$in": ids}},
    }
    deleted = {name: db[name].delete_many(query).deleted_count for name, query in queries.items()}
    leftovers = {name: db[name].count_documents(query) for name, query in queries.items()}
    if any(leftovers.values()):
        raise RuntimeError(f"Sandbox parity cleanup was incomplete: {leftovers}")
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Perform the isolated sandbox parity and cleanup cycle.")
    parser.add_argument("--service-url", default=os.environ.get("DTD_SANDBOX_SERVICE_URL", DEFAULT_SERVICE_URL))
    parser.add_argument("--mongo-url", default=os.environ.get("MONGO_URL", ""))
    parser.add_argument("--admin-pass", default=os.environ.get("ADMIN_PASS", ""))
    args = parser.parse_args()
    if not args.execute:
        print("Preview only: pass --execute after supplying sandbox MONGO_URL and ADMIN_PASS.")
        return 0
    if not args.mongo_url or not args.admin_pass:
        raise SystemExit("MONGO_URL and ADMIN_PASS must be supplied through environment variables.")

    service_url = args.service_url.rstrip("/")
    _require_sandbox(service_url, args.mongo_url, SANDBOX_DB)
    normal_model = _service_env().get("GEMINI_MODEL", "")
    if normal_model != EXPECTED_NORMAL_MODEL:
        raise SystemExit(
            f"Refusing parity run: sandbox GEMINI_MODEL must be {EXPECTED_NORMAL_MODEL!r}, got {normal_model!r}."
        )

    run_id = uuid.uuid4().hex
    forced_model = f"dtd-sandbox-parity-forced-{run_id}"
    client = MongoClient(args.mongo_url, serverSelectionTimeoutMS=10000)
    db = client[SANDBOX_DB]
    fixture: Dict[str, Any] = {}
    match_ids: list[str] = []
    mutation_attempted = False
    cleanup_ready = False
    restore_error: Exception | None = None
    try:
        client.admin.command("ping")
        payload = _request_for_isolated_pool(db)
        fixture = _fixture(run_id, payload)
        db.trainers.insert_one(dict(fixture))
        cleanup_ready = True

        _progress("initial_gemini")
        normal = _request(f"{service_url}/api/match", method="POST", payload=payload)
        match_ids.append(str(normal.get("match_id") or ""))
        _validate_normal(normal, fixture["id"], phase="initial")

        # Cloud Run revision changes start a fresh in-process limiter.  This
        # exercise has one match per revision, well below the 3/30-second
        # request burst limit, so artificial sleeps would only lengthen a
        # controlled recovery operation.
        _progress("forcing_sandbox_fallback")
        mutation_attempted = True
        _set_model(forced_model)
        _wait_for_available_health(service_url)
        _progress("forced_fallback")
        fallback = _request(f"{service_url}/api/match", method="POST", payload=payload)
        match_ids.append(str(fallback.get("match_id") or ""))
        _validate_fallback(fallback, fixture["id"])
        fallback_event = db.ai_degradation_events.find_one(
            {"operation": "matching", "model": forced_model}, {"_id": 0, "error_type": 1, "fallback_used": 1}
        )
        if not fallback_event or fallback_event.get("fallback_used") is not True:
            raise RuntimeError("Forced fallback did not create its sanitised degradation event.")
        ops = _request(f"{service_url}/api/oversight/matching", method="GET", headers={"X-Admin-Pass": args.admin_pass})
        if forced_model not in json.dumps(ops, sort_keys=True, default=str):
            raise RuntimeError("Protected Ops did not expose the forced fallback evidence.")

        # Restore the accepted model before proving it can again serve normal matches.
        _progress("restoring_gemini")
        _set_model(normal_model)
        mutation_attempted = False
        _wait_for_available_health(service_url)
        _progress("recovered_gemini")
        recovered = _request(f"{service_url}/api/match", method="POST", payload=payload)
        match_ids.append(str(recovered.get("match_id") or ""))
        _validate_normal(recovered, fixture["id"], phase="recovery")

        # Material parity means the normal and fallback paths return the same
        # closed candidate set and preserve the capability reason. Scores and
        # additional truthful reasons are intentionally not required identical.
        if _candidate_ids(normal) != _candidate_ids(fallback):
            raise RuntimeError("Gemini and fallback candidate sets were materially inconsistent.")
        print(json.dumps({
            "ok": True,
            "sandbox_project": SANDBOX_PROJECT,
            "parity": ["normal_gemini", "forced_fallback", "ops_degradation", "restored_gemini"],
            "candidate_ids": _candidate_ids(normal),
            "normal_state": normal.get("decision_state"),
            "fallback_state": fallback.get("decision_state"),
            "recovered_state": recovered.get("decision_state"),
        }))
        return 0
    finally:
        try:
            if mutation_attempted:
                try:
                    _set_model(normal_model)
                    _wait_for_available_health(service_url)
                except Exception as exc:  # preserve cleanup, but surface a failed recovery
                    restore_error = exc
            if cleanup_ready and fixture:
                deleted = _cleanup(
                    db,
                    trainer_id=str(fixture["id"]),
                    match_ids=match_ids,
                    forced_model=forced_model,
                )
                _require_public_absence(service_url, [str(fixture["id"])])
                print(json.dumps({"cleanup_complete": True, "deleted": deleted}))
        finally:
            client.close()
        if restore_error:
            raise RuntimeError("Sandbox Gemini model restoration failed after parity run.") from restore_error


if __name__ == "__main__":
    raise SystemExit(main())
