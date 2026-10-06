#!/usr/bin/env python3
"""Execute the safe, disposable API/Ops portion of the M9 matching matrix.

This is deliberately more demanding than the narrow smoke runner.  It creates
only UUID-tagged sandbox fixtures, proves validation, emergency triage,
no-confirmed-match, local-plus-expanded matching, opaque context handoff,
profile visibility, terminal follow-up delivery and protected Ops evidence.
Every record it creates is removed in ``finally`` and the trainers are checked
absent from the public API.  It never calls an email provider or billing API:
the follow-up fixture is intentionally contact-ready for matching but has no
email, so its truthful delivery result is ``terminal_failure``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from pymongo import MongoClient


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.matching_contract_v2 import (  # noqa: E402
    MatchRequestIn,
    check_candidate_eligibility,
)
from backend.services.trainer_quality import (  # noqa: E402
    build_match_ready_projection,
    package_trainer_capabilities,
)


SANDBOX_PROJECT = "dogtrainersdirectory-dev"
SANDBOX_DB = "dtd_sandbox"
DEFAULT_SERVICE_URL = "https://dtd-api-dev-625222421634.australia-southeast1.run.app"


def _request(
    url: str,
    *,
    method: str,
    payload: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=request_headers, method=method)
    with urlopen(req, timeout=25) as response:  # nosec B310: sandbox URL is gated below
        return json.loads(response.read().decode("utf-8"))


def _expect_http_error(action, expected: int, label: str) -> Dict[str, Any]:
    try:
        action()
    except HTTPError as error:
        if error.code != expected:
            raise RuntimeError(f"{label}: expected HTTP {expected}, got {error.code}") from error
        raw = error.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}
    raise RuntimeError(f"{label}: expected HTTP {expected}, but request succeeded")


def _require_sandbox(service_url: str, mongo_url: str, db_name: str) -> None:
    parsed = urlparse(service_url)
    mongo_host = (urlparse(mongo_url).hostname or "").lower()
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".run.app"):
        raise SystemExit("Refusing a non-Cloud-Run acceptance endpoint.")
    if "dtd-api-dev" not in parsed.hostname or db_name != SANDBOX_DB:
        raise SystemExit("Refusing a non-developer-sandbox service or database.")
    if not mongo_host:
        raise SystemExit("MongoDB URI has no host.")


def _match_payload(**overrides: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "suburb_or_postcode": "Fitzroy",
        "dog_age_months": 4,
        "primary_concerns": ["puppy_prep"],
        "service_format": "in_home",
        "method_preference": "positive_reinforcement_only",
        "behaviour_description": "Needs an early puppy training plan.",
        "consent": {
            "match_processing": True,
            "terms": True,
            "referral_contact": False,
            "follow_up": False,
        },
    }
    payload.update(overrides)
    return payload


def _fixture(run_id: str, suffix: str, *, expanded: bool = False) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    trainer_id = f"sandbox-m9-{run_id}-{suffix}"
    capabilities = package_trainer_capabilities(
        specialties=["puppy_training"],
        service_formats=["in_home"],
        life_stages=["puppy"],
        training_philosophy="positive_reinforcement_force_free",
        serviced_suburbs=[] if expanded else ["Fitzroy"],
        catchment_type="melbourne_wide" if expanded else "specific_suburbs",
        delivery_constraints={"in_home_available": True, "facility_available": False, "travel_distance_km": 10},
        basis="trainer_declaration",
        evidence_reference="sandbox_m9_disposable_fixture",
        confirmed_at=now,
    )
    return {
        "id": trainer_id,
        "slug": trainer_id,
        "name": f"Sandbox M9 fixture {suffix} — not a real trainer",
        "suburb": "Fitzroy" if not expanded else "Northcote",
        "region": "Greater Melbourne",
        "published": True,
        # Deliberately no email: follow-up verifies the truthful no-send
        # terminal state without contacting a synthetic or real recipient.
        "contact_ready": True,
        "verification_status": "verified",
        "claim_status": "claimed",
        "tier": "claimed",
        "service_formats": ["in_home"],
        "specialties": ["puppy_training"],
        "capabilities": capabilities,
        "website": "https://example.test/dtd-sandbox-m9",
        "source_evidence_url": "https://example.test/dtd-sandbox-m9",
        "test_run_id": run_id,
        "test_fixture": True,
        "created_at": now,
        "updated_at": now,
    }


def _find_no_match_payload(db: Any) -> Dict[str, Any]:
    """Pick a canonical request with zero eligible candidates before fixtures.

    This avoids assuming the sandbox's current supply remains empty while still
    proving the public no-confirmed-match route without mutating real records.
    The pool is a conservative superset of the route's region-filtered pool,
    so zero eligibility here is safe evidence for the live route.
    """
    docs = list(db.trainers.find({"published": True}, {"_id": 0}))
    pool = [build_match_ready_projection(doc) for doc in docs]
    attempts = [
        _match_payload(primary_concerns=["separation_anxiety"], service_format="online_coaching", method_preference="balanced"),
        _match_payload(primary_concerns=["aggression"], service_format="online_coaching", method_preference="balanced"),
        _match_payload(primary_concerns=["recall"], service_format="group_class", method_preference="balanced"),
    ]
    for payload in attempts:
        request = MatchRequestIn(**payload)
        eligible = [
            candidate
            for candidate in pool
            if check_candidate_eligibility(candidate, request, search_scope="local")[0]
            or check_candidate_eligibility(candidate, request, search_scope="expanded")[0]
        ]
        if not eligible:
            return payload
    raise RuntimeError("No deterministic zero-eligibility request was available without changing sandbox supply.")


def _require_public_absence(service_url: str, trainer_ids: Iterable[str]) -> None:
    for trainer_id in trainer_ids:
        _expect_http_error(
            lambda trainer_id=trainer_id: _request(f"{service_url}/api/trainers/{trainer_id}", method="GET"),
            404,
            f"deleted fixture {trainer_id} public absence",
        )


def _cleanup(
    db: Any,
    *,
    trainer_ids: list[str],
    match_ids: list[str],
    intro_ids: list[str],
    pre_existing_degradation_ids: set[str],
) -> Dict[str, int]:
    new_degradation_ids = [
        str(row.get("id"))
        for row in db.ai_degradation_events.find({"operation": "matching"}, {"_id": 0, "id": 1})
        if row.get("id") and str(row["id"]) not in pre_existing_degradation_ids
    ]
    queries: Dict[str, Dict[str, Any]] = {
        "trainers": {"id": {"$in": trainer_ids}},
        "match_events": {"id": {"$in": match_ids}} if match_ids else {"id": "__none__"},
        "match_contexts": {"match_id": {"$in": match_ids}} if match_ids else {"match_id": "__none__"},
        "intros": {"$or": [{"id": {"$in": intro_ids or ["__none__"]}}, {"match_id": {"$in": match_ids or ["__none__"]}}]},
        "engagements": {"match_id": {"$in": match_ids}} if match_ids else {"match_id": "__none__"},
        "notification_events": {"target_id": {"$in": intro_ids}} if intro_ids else {"target_id": "__none__"},
        "ai_degradation_events": {"id": {"$in": new_degradation_ids}} if new_degradation_ids else {"id": "__none__"},
        "audit_log": {"$or": [
            {"target": {"$in": trainer_ids + intro_ids}},
            {"after.match_id": {"$in": match_ids}},
            {"after.intro_id": {"$in": intro_ids}},
        ]},
    }
    deleted = {name: db[name].delete_many(query).deleted_count for name, query in queries.items()}
    leftovers = {name: db[name].count_documents(query) for name, query in queries.items()}
    if any(leftovers.values()):
        raise RuntimeError(f"Sandbox M9 cleanup was incomplete: {leftovers}")
    return deleted


def _new_degradation_summary(db: Any, pre_existing_ids: set[str]) -> list[Dict[str, str]]:
    """Return only operationally safe diagnostics for this disposable run."""
    rows = db.ai_degradation_events.find(
        {"operation": "matching"},
        {"_id": 0, "id": 1, "error_type": 1, "error_code": 1, "model": 1},
    )
    return [
        {
            "id": str(row.get("id") or ""),
            "error_type": str(row.get("error_type") or "unknown"),
            "error_code": str(row.get("error_code") or "unknown"),
            "model": str(row.get("model") or "unknown"),
        }
        for row in rows
        if row.get("id") and str(row["id"]) not in pre_existing_ids
    ]


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

    service_url = args.service_url.rstrip("/")
    _require_sandbox(service_url, args.mongo_url, SANDBOX_DB)
    run_id = uuid.uuid4().hex
    local_fixture = _fixture(run_id, "local")
    expanded_fixture = _fixture(run_id, "expanded", expanded=True)
    trainer_ids = [local_fixture["id"], expanded_fixture["id"]]
    match_ids: list[str] = []
    intro_ids: list[str] = []
    client = MongoClient(args.mongo_url, serverSelectionTimeoutMS=10000)
    db = client[SANDBOX_DB]
    pre_existing_degradation_ids: set[str] = set()
    cleanup_ready = False
    try:
        client.admin.command("ping")
        pre_existing_degradation_ids = {
            str(row["id"]) for row in db.ai_degradation_events.find({}, {"_id": 0, "id": 1}) if row.get("id")
        }
        cleanup_ready = True

        # Validation happens before the endpoint body: no match event should be created.
        invalid = _match_payload(consent={"match_processing": False, "terms": True})
        _expect_http_error(lambda: _request(f"{service_url}/api/match", method="POST", payload=invalid), 422, "mandatory-consent validation")

        immediate = _request(
            f"{service_url}/api/match", method="POST",
            payload=_match_payload(behaviour_description="There is an active attack and someone has been bitten a child."),
        )
        if immediate.get("decision_state") != "immediate_human_danger" or immediate.get("candidates"):
            raise RuntimeError("Immediate-human-danger route did not stop ordinary matching.")
        match_ids.append(str(immediate.get("match_id") or ""))

        urgent = _request(
            f"{service_url}/api/match", method="POST",
            payload=_match_payload(behaviour_description="My dog may have eaten poison and needs urgent help."),
        )
        if urgent.get("decision_state") != "urgent_animal_health_support" or urgent.get("candidates"):
            raise RuntimeError("Urgent-animal-health route did not stop ordinary matching.")
        match_ids.append(str(urgent.get("match_id") or ""))

        no_match_payload = _find_no_match_payload(db)
        no_match = _request(f"{service_url}/api/match", method="POST", payload=no_match_payload)
        if no_match.get("decision_state") not in {"no_confirmed_match", "degraded_no_confirmed_match"} or no_match.get("candidates"):
            raise RuntimeError("Zero deterministic eligibility did not produce a transparent no-confirmed-match state.")
        match_ids.append(str(no_match.get("match_id") or ""))

        # The contract permits only three requests in thirty seconds per source IP.
        # Wait rather than spoofing X-Forwarded-For, which would hide a limiter defect.
        time.sleep(31)

        db.trainers.insert_many([dict(local_fixture), dict(expanded_fixture)])
        normal = _request(f"{service_url}/api/match", method="POST", payload=_match_payload(
            behaviour_description="Private detail owner@example.test should be removed before model or Ops storage.",
        ))
        normal_id = str(normal.get("match_id") or "")
        match_ids.append(normal_id)
        result_ids = {str(row.get("trainer_id") or row.get("id") or "") for row in normal.get("candidates", []) + normal.get("matches", [])}
        if not normal_id or not set(trainer_ids).issubset(result_ids):
            raise RuntimeError("Local-plus-expanded fixtures were not both returned by matching.")
        if normal.get("search_scope") != "expanded":
            raise RuntimeError("Thin local supply did not disclose expanded matching scope.")
        if normal.get("degraded"):
            diagnostics = _new_degradation_summary(db, pre_existing_degradation_ids)
            print(json.dumps({
                "diagnostic": "normal_match_degraded",
                "decision_state": normal.get("decision_state"),
                "degradation_events": diagnostics,
            }))
            raise RuntimeError("The normal matching fixture fell back instead of proving the configured Gemini path.")
        scopes = {str(row.get("trainer_id") or row.get("id") or ""): row.get("search_scope") for row in normal.get("candidates", [])}
        if scopes.get(local_fixture["id"]) != "local" or scopes.get(expanded_fixture["id"]) != "expanded":
            raise RuntimeError("Result cards did not preserve local versus expanded service-area disclosure.")
        token = str(normal.get("context_token") or "")
        if not token:
            raise RuntimeError("A result-bearing match did not issue an opaque context token.")

        event = db.match_events.find_one({"id": normal_id}, {"_id": 0}) or {}
        forbidden = {"behaviour_description", "owner@example.test", token}
        if not event or any(value in json.dumps(event, sort_keys=True, default=str) for value in forbidden):
            raise RuntimeError("Match event persisted a raw owner description, PII, or context token.")

        context = _request(f"{service_url}/api/match/context", method="GET", headers={"X-Match-Context-Token": token})
        if context.get("match_id") != normal_id or any(key in context for key in ("behaviour_description", "user_email", "token")):
            raise RuntimeError("Context endpoint did not return the restricted header-authenticated shape.")
        _expect_http_error(
            lambda: _request(f"{service_url}/api/match/context?token={quote(token)}", method="GET"),
            400,
            "context query-token rejection",
        )
        profile = _request(f"{service_url}/api/trainers/{local_fixture['id']}", method="GET")
        if profile.get("id") != local_fixture["id"]:
            raise RuntimeError("Matched profile was not publicly retrievable during its controlled fixture lifetime.")

        ops_before = _request(f"{service_url}/api/oversight/matching", method="GET", headers={"X-Admin-Pass": args.admin_pass})
        terminal_before = int(((ops_before.get("follow_up_distribution") or {}).get("by_state") or {}).get("terminal_failure") or 0)
        enquiry_headers = {"X-Match-Context-Token": token, "Idempotency-Key": f"sandbox-m9-{run_id}"}
        enquiry_payload = {
            "trainer_id": local_fixture["id"],
            "user_name": "Sandbox M9 Owner",
            # ``example.com`` is a reserved documentation domain accepted by
            # the runtime email validator. The selected trainer has no email,
            # so this value never reaches an outbound provider.
            "user_email": f"sandbox-m9-owner-{run_id}@example.com",
            "notes": "Disposable acceptance enquiry; do not contact.",
            "consent_contact_release": True,
        }
        try:
            enquiry = _request(f"{service_url}/api/match/follow-up", method="POST", payload=enquiry_payload, headers=enquiry_headers)
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"Controlled terminal follow-up rejected with HTTP {error.code}: {detail}") from error
        intro_id = str(enquiry.get("intro_id") or "")
        intro_ids.append(intro_id)
        if not intro_id or enquiry.get("delivery_state") != "terminal_failure" or enquiry.get("idempotent") is not False:
            raise RuntimeError("Email-free fixture did not produce the expected no-send terminal delivery state.")
        duplicate = _request(f"{service_url}/api/match/follow-up", method="POST", payload=enquiry_payload, headers=enquiry_headers)
        if duplicate.get("intro_id") != intro_id or duplicate.get("idempotent") is not True:
            raise RuntimeError("Follow-up idempotency did not return the original enquiry.")
        if db.notification_events.count_documents({"target_id": intro_id}) != 0:
            raise RuntimeError("Terminal no-recipient follow-up attempted an outbound notification.")
        ops_after = _request(f"{service_url}/api/oversight/matching", method="GET", headers={"X-Admin-Pass": args.admin_pass})
        terminal_after = int(((ops_after.get("follow_up_distribution") or {}).get("by_state") or {}).get("terminal_failure") or 0)
        if terminal_after < terminal_before + 1:
            raise RuntimeError("Protected Ops did not expose the terminal follow-up state.")
        ops_match_ids = {str(row.get("match_id") or "") for row in ops_after.get("presentation_order_sample", [])}
        if normal_id not in ops_match_ids:
            raise RuntimeError("Protected Ops did not expose the matching event.")

        # A context token is intentionally short-lived. This simulates the
        # retention boundary with the disposable fixture only; it neither
        # touches a real owner record nor waits thirty calendar days.
        db.match_contexts.update_one(
            {"match_id": normal_id},
            {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}},
        )
        _expect_http_error(
            lambda: _request(
                f"{service_url}/api/match/context",
                method="GET",
                headers={"X-Match-Context-Token": token},
            ),
            410,
            "expired context-token rejection",
        )

        print(json.dumps({
            "ok": True,
            "sandbox_project": SANDBOX_PROJECT,
            "matrix": ["validation", "immediate_triage", "urgent_triage", "no_confirmed_match", "expanded_scope", "non_degraded_gemini", "context", "context_expiry", "profile", "terminal_follow_up", "ops"],
            "normal_decision_state": normal.get("decision_state"),
            "normal_degraded": bool(normal.get("degraded")),
        }))
        return 0
    finally:
        try:
            if cleanup_ready:
                deleted = _cleanup(
                    db,
                    trainer_ids=trainer_ids,
                    match_ids=[match_id for match_id in match_ids if match_id],
                    intro_ids=[intro_id for intro_id in intro_ids if intro_id],
                    pre_existing_degradation_ids=pre_existing_degradation_ids,
                )
                _require_public_absence(service_url, trainer_ids)
                print(json.dumps({"cleanup_complete": True, "deleted": deleted}))
        finally:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
