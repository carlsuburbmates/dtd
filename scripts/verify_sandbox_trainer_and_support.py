#!/usr/bin/env python3
"""Integrated Sandbox Acceptance Runner: Trainer Session / Storefront and Support Lifecycle.

Verifies live runtime behavior on Cloud Run (dogtrainersdirectory-dev):
1. Preflight sandbox scope validation and non-secret metadata capture.
2. Domain 3 / SR-03 / CF-03 / DF-030 / DF-051 / DF-035: Trainer claim initiation,
   email mismatch / SMS fail-closed guards, invalid OTP rejection.
   Optional --owner-receipt mode verifies normal browser claim/recovery/capability edits
   using a verified owner inbox and private correlated code input. Default test-sink mode
   does not claim mailbox receipt. Privileged secret derivation is prohibited.
3. Domain 6 / SR-04 / CF-04 / DF-047: First-party support complaint intake, Resend test-sink
   confirmation delivery, protected /ops thread retrieval, operator reply & duplicate prevention,
   guarded closure (minimum notes length requirement verified via API).
4. Headless Playwright browser UI validation on dtd-web-dev (contact submit, owned support
   case detail, reply/duplicate feedback, closure guards and persisted closed-case revisit).
5. Deterministic fixture teardown and exact-ID absence verification.

Safe for developer sandbox only. Secrets fetched in memory and never logged or printed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import select
import subprocess
import sys
import tempfile
import termios
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


def normalize_origin(url: str) -> str:
    """Returns canonical scheme://hostname[:port] without trailing slash, path, or default ports."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if not scheme or not host:
        return ""
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        port = None
    if port is not None:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def is_approved_exact_origin(url: str, approved_origins: Set[str]) -> bool:
    """Verifies that url exactly matches one of the approved origins."""
    origin = normalize_origin(url)
    if not origin:
        return False
    return origin in approved_origins


def verify_page_exact_origin(page_url: str, expected_origin: str, step_name: str) -> None:
    """Asserts that page_url matches expected_origin exactly, rejecting downgrades or altered ports."""
    current_origin = normalize_origin(page_url)
    expected = normalize_origin(expected_origin)
    if not current_origin or current_origin != expected:
        raise AcceptanceFailure(
            f"{step_name}: page navigated or redirected to unapproved origin {current_origin!r}, "
            f"expected exact origin {expected!r} (full URL: {page_url})"
        )


async def evaluate_browser_route(route: Any, request: Any, approved_origins: Set[str]) -> None:
    """Reusable Playwright route guard enforcing exact HTTPS origin matching and blocking downgrades/foreign mutations."""
    req_url = request.url
    dest_origin = normalize_origin(req_url)
    method = request.method.upper()
    headers = {k.lower(): v for k, v in request.headers.items()}
    is_mutating = method in ("POST", "PUT", "PATCH", "DELETE")
    has_auth = any(name in headers for name in ("authorization", "x-admin-pass", "x-trainer-claim-session"))

    # Mutating requests or requests carrying sensitive credentials must match an approved origin exactly
    if is_mutating or has_auth:
        if dest_origin not in approved_origins:
            print(f"      [!] BLOCKED unapproved {method} request to {req_url} (origin: {dest_origin!r})")
            await route.abort("blockedbyclient")
            return

    # Reject HTTP downgrade attempts to cloud services or unapproved destinations with auth/mutation
    parsed = urlparse(req_url)
    if parsed.scheme == "http" and dest_origin not in {"http://localhost", "http://127.0.0.1"}:
        if is_mutating or has_auth or any(parsed.hostname and (parsed.hostname.endswith(".run.app") or parsed.hostname.endswith(".dev")) for _ in [1]):
            print(f"      [!] BLOCKED insecure HTTP request to {req_url}")
            await route.abort("blockedbyclient")
            return

    await route.continue_()


class StrictRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Denies cross-origin HTTP redirects on protected/authenticated requests."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old_origin = normalize_origin(req.full_url)
        new_origin = normalize_origin(newurl)
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
    req_origin = normalize_origin(url)
    allowed_origins = {
        normalize_origin(API_URL),
        normalize_origin(WEB_URL),
        "http://localhost",
        "http://127.0.0.1",
        "https://localhost",
        "https://127.0.0.1",
    }
    if req_origin not in allowed_origins:
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


def enforce_sandbox_preflight(
    project_id: str = SANDBOX_PROJECT,
    runner: Any = None,
    expected_admin_pass_version: str = "4",
    expected_mongo_url_version: str = "latest",
) -> Dict[str, Any]:
    print("[1/5] Enforcing Sandbox Preflight & Verifying Runtime Scope...")

    def _run_cmd(cmd: List[str]) -> Any:
        if runner is not None:
            try:
                return runner(cmd, text=True, stderr=subprocess.PIPE)
            except TypeError:
                return runner(cmd)
        return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE)

    # 1. API Service describe
    try:
        api_raw = _run_cmd([
            "gcloud", "run", "services", "describe", "dtd-api-dev",
            f"--project={project_id}",
            "--region=australia-southeast1",
            "--format=json",
        ])
        api_data = json.loads(api_raw) if isinstance(api_raw, str) else api_raw
    except Exception as e:
        raise AcceptanceFailure(f"Failed to read Cloud Run service dtd-api-dev: {e}")

    status = api_data.get("status", {})
    traffic = status.get("traffic", [])
    serving_rev = status.get("latestReadyRevisionName", "")
    if not serving_rev:
        raise AcceptanceFailure("Preflight check failed: dtd-api-dev has no latestReadyRevisionName.")

    pct_serving = sum(t.get("percent", 0) for t in traffic if t.get("revisionName") == serving_rev)
    if pct_serving != 100:
        raise AcceptanceFailure(
            f"Preflight check failed: dtd-api-dev does not direct 100% traffic to latest ready revision {serving_rev} (found {pct_serving}%)."
        )

    # 2. Immutable traffic-serving revision describe & validation
    try:
        rev_raw = _run_cmd([
            "gcloud", "run", "revisions", "describe", serving_rev,
            f"--project={project_id}",
            "--region=australia-southeast1",
            "--format=json",
        ])
        rev_data = json.loads(rev_raw) if isinstance(rev_raw, str) else rev_raw
    except Exception as e:
        raise AcceptanceFailure(f"Failed to read immutable serving revision {serving_rev}: {e}")

    rev_spec = rev_data.get("spec", {})
    if "template" in rev_spec and "spec" in rev_spec["template"]:
        rev_containers_spec = rev_spec["template"]["spec"]
    else:
        rev_containers_spec = rev_spec

    sa = rev_containers_spec.get("serviceAccountName") or rev_spec.get("serviceAccountName", "")
    expected_sa = f"dtd-api-dev-runtime@{project_id}.iam.gserviceaccount.com"
    if sa != expected_sa:
        raise AcceptanceFailure(
            f"Preflight check failed: unexpected API service account: {sa!r}, expected exact {expected_sa!r}"
        )

    containers = rev_containers_spec.get("containers", [{}])
    env_list = containers[0].get("env", []) if containers else []
    env_map = {e.get("name"): e.get("value") for e in env_list if "value" in e}

    env_secrets: Dict[str, Dict[str, str]] = {}
    for e in env_list:
        v_from = e.get("valueFrom", {})
        if "secretKeyRef" in v_from and e.get("name"):
            sec_ref = v_from["secretKeyRef"]
            env_secrets[e["name"]] = {
                "name": str(sec_ref.get("name", "")),
                "key": str(sec_ref.get("key", "")),
            }

    volumes = rev_containers_spec.get("volumes", [])
    vol_secrets: Dict[str, Dict[str, Any]] = {}
    for v in volumes:
        v_name = v.get("name")
        sec = v.get("secret", {})
        if sec and v_name:
            vol_secrets[v_name] = {
                "secretName": str(sec.get("secretName", "")),
                "items": sec.get("items", []),
            }

    if env_map.get("DB_NAME") != "dtd_sandbox":
        raise AcceptanceFailure(
            f"Preflight check failed: dtd-api-dev serving revision {serving_rev} targets unexpected database {env_map.get('DB_NAME')!r}, expected 'dtd_sandbox'."
        )
    if env_map.get("ENABLE_TRAINER_BILLING_CHECKOUT") != "0":
        raise AcceptanceFailure(
            f"Preflight check failed: Safety flag ENABLED in sandbox: ENABLE_TRAINER_BILLING_CHECKOUT={env_map.get('ENABLE_TRAINER_BILLING_CHECKOUT')!r}"
        )
    if env_map.get("ENABLE_OPS_STRIPE_REFUNDS") != "0":
        raise AcceptanceFailure(
            f"Preflight check failed: Safety flag ENABLED in sandbox: ENABLE_OPS_STRIPE_REFUNDS={env_map.get('ENABLE_OPS_STRIPE_REFUNDS')!r}"
        )
    if env_map.get("OPS_SELF_HEALING_ENABLED") != "0":
        raise AcceptanceFailure(
            f"Preflight check failed: Safety flag ENABLED in sandbox: OPS_SELF_HEALING_ENABLED={env_map.get('OPS_SELF_HEALING_ENABLED')!r}"
        )

    # Validate volume declarations if present (ensure declared keys do not mismatch)
    for v_name, v_info in vol_secrets.items():
        s_name = v_info.get("secretName")
        items = v_info.get("items", [])
        if s_name == "dtd-admin-pass":
            for itm in items:
                key = itm.get("key")
                if key and key != expected_admin_pass_version:
                    raise AcceptanceFailure(
                        f"Preflight check failed: volume {v_name} declares secret {s_name} with version {key!r}, expected {expected_admin_pass_version!r}."
                    )
        if s_name == "dtd-mongo-url":
            for itm in items:
                key = itm.get("key")
                if key and key != expected_mongo_url_version:
                    raise AcceptanceFailure(
                        f"Preflight check failed: volume {v_name} declares secret {s_name} with version {key!r}, expected {expected_mongo_url_version!r}."
                    )

    # Reject literal secret values shadowing secretKeyRef bindings
    if env_map.get("ADMIN_PASS") is not None:
        raise AcceptanceFailure(
            "Preflight check failed: ADMIN_PASS specifies literal value in container env; must use secretKeyRef."
        )
    if env_map.get("MONGO_URL") is not None:
        raise AcceptanceFailure(
            "Preflight check failed: MONGO_URL specifies literal value in container env; must use secretKeyRef."
        )

    # Validate container environment secretKeyRef bindings (volume-only or missing secret bindings are unsupported)
    if "ADMIN_PASS" not in env_secrets:
        raise AcceptanceFailure(
            "Preflight check failed: ADMIN_PASS is not bound via container secretKeyRef (volume-only or missing secret bindings are unsupported)."
        )
    admin_sec_name = env_secrets["ADMIN_PASS"]["name"]
    admin_effective_version = env_secrets["ADMIN_PASS"]["key"]
    if admin_sec_name != "dtd-admin-pass":
        raise AcceptanceFailure(
            f"Preflight check failed: ADMIN_PASS references secret {admin_sec_name!r}, expected 'dtd-admin-pass'."
        )
    if admin_effective_version != expected_admin_pass_version:
        raise AcceptanceFailure(
            f"Preflight check failed: ADMIN_PASS references secret version {admin_effective_version!r}, expected {expected_admin_pass_version!r}."
        )

    if "MONGO_URL" not in env_secrets:
        raise AcceptanceFailure(
            "Preflight check failed: MONGO_URL is not bound via container secretKeyRef (volume-only or missing secret bindings are unsupported)."
        )
    mongo_sec_name = env_secrets["MONGO_URL"]["name"]
    mongo_effective_version = env_secrets["MONGO_URL"]["key"]
    if mongo_sec_name != "dtd-mongo-url":
        raise AcceptanceFailure(
            f"Preflight check failed: MONGO_URL references secret {mongo_sec_name!r}, expected 'dtd-mongo-url'."
        )
    if mongo_effective_version != expected_mongo_url_version:
        raise AcceptanceFailure(
            f"Preflight check failed: MONGO_URL references secret version {mongo_effective_version!r}, expected {expected_mongo_url_version!r}."
        )

    # 3. Web Service describe
    try:
        web_raw = _run_cmd([
            "gcloud", "run", "services", "describe", "dtd-web-dev",
            f"--project={project_id}",
            "--region=australia-southeast1",
            "--format=json",
        ])
        web_data = json.loads(web_raw) if isinstance(web_raw, str) else web_raw
    except Exception as e:
        raise AcceptanceFailure(f"Failed to read Cloud Run service dtd-web-dev: {e}")

    web_status = web_data.get("status", {})
    web_traffic = web_status.get("traffic", [])
    web_rev = web_status.get("latestReadyRevisionName", "")
    if not web_rev:
        raise AcceptanceFailure("Preflight check failed: dtd-web-dev has no latestReadyRevisionName.")
    web_pct = sum(t.get("percent", 0) for t in web_traffic if t.get("revisionName") == web_rev)
    if web_pct != 100:
        raise AcceptanceFailure(
            f"Preflight check failed: dtd-web-dev traffic not 100% on serving revision {web_rev} (found {web_pct}%)."
        )

    # 4. Cloud Scheduler state
    try:
        cron_raw = _run_cmd([
            "gcloud", "scheduler", "jobs", "describe", "dtd-trainer-ingest-cron",
            f"--project={project_id}",
            "--location=australia-southeast1",
            "--format=value(state)",
        ])
        if isinstance(cron_raw, dict):
            cron_state = str(cron_raw.get("state", "")).strip()
        else:
            cron_state = str(cron_raw).strip()
    except Exception as e:
        raise AcceptanceFailure(f"Failed to read Cloud Scheduler job dtd-trainer-ingest-cron: {e}")

    if cron_state != "PAUSED":
        raise AcceptanceFailure(f"Preflight check failed: Cloud Scheduler job dtd-trainer-ingest-cron is {cron_state}.")

    return {
        "project": project_id,
        "database": env_map.get("DB_NAME"),
        "api_revision": serving_rev,
        "web_revision": web_rev,
        "ingest_cron_state": cron_state,
        "service_account": sa,
        "safe_env": {
            "DB_NAME": env_map.get("DB_NAME"),
            "ENABLE_TRAINER_BILLING_CHECKOUT": env_map.get("ENABLE_TRAINER_BILLING_CHECKOUT"),
            "ENABLE_OPS_STRIPE_REFUNDS": env_map.get("ENABLE_OPS_STRIPE_REFUNDS"),
            "OPS_SELF_HEALING_ENABLED": env_map.get("OPS_SELF_HEALING_ENABLED"),
        },
        "managed_secret_references": {
            "MONGO_URL": {
                "secret_name": mongo_sec_name,
                "version": mongo_effective_version,
            },
            "ADMIN_PASS": {
                "secret_name": admin_sec_name,
                "version": admin_effective_version,
            },
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _write_atomic_json(path: Path, payload: Dict[str, Any]) -> None:
    """Publish a complete recovery record durably before destructive work."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def execute_deterministic_teardown(
    db: Any,
    trainer_id: str,
    tracked_case_ids: Set[str],
    run_emails: List[str],
    admin_pass: str,
    api_url: str = API_URL,
    run_id: str = "",
    http_request_fn: Any = None,
    durable_lineage: Optional[Dict[str, Any]] = None,
    recovery_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Validate ownership, persist a complete inventory, then remove only that inventory.

    Inventory/read failures perform zero deletes and never replace existing proof.
    A retry uses the same explicit run context and durable identifiers, even after
    its source rows have disappeared. Current contradictory records always win.
    """
    request_fn = http_request_fn or _http_request
    errors: List[str] = []
    preserved: Set[str] = set()
    missing: Set[str] = set()
    deleted: Dict[str, Any] = {
        "trainers": 0, "claim_events": 0, "trainer_notifications": 0,
        "trainer_audit": 0, "trainer_obligations": 0,
        "claim_event_obligations": 0, "dispatch_obligations": 0,
        "support_threads": {}, "support_notifications": {},
        "support_audit": {}, "ops_obligations": {},
    }
    report: Dict[str, Any] = {
        "status": "FAILED", "deleted": deleted, "leftovers": {},
        "endpoint_404s": {}, "cleanup_errors": errors,
        "all_leftovers_zero": False, "all_endpoints_404": False,
        "tracked_case_ids": [], "unowned_preserved_cases": [],
        "unverified_missing_cases": [], "owned_claim_event_ids": [],
        "owned_dispatch_ids": [], "durable_lineage": None,
    }

    def failed(message: str) -> Dict[str, Any]:
        errors.append(message)
        report["unowned_preserved_cases"] = sorted(preserved)
        report["unverified_missing_cases"] = sorted(missing)
        return report

    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        return failed("An explicit valid run_id is required for cleanup.")
    if recovery_dir is None or not isinstance(trainer_id, str) or not trainer_id:
        return failed("Explicit recovery_dir and trainer_id are required for cleanup.")
    if not run_emails or any(not isinstance(value, str) or not value for value in run_emails):
        return failed("Explicit synthetic run_emails are required for cleanup.")
    context = {
        "schema_version": 1, "project": SANDBOX_PROJECT, "database": SANDBOX_DB,
        "run_id": run_id, "trainer_id": trainer_id, "run_emails": sorted(set(run_emails)),
    }
    lineage_file = Path(recovery_dir) / f"dtd_lineage_{run_id}.json"
    cases: Set[str] = set()
    claims: Set[str] = set()
    dispatches: Set[str] = set()
    prior_trainer_owned = False
    try:
        records = []
        if lineage_file.exists():
            records.append(json.loads(lineage_file.read_text(encoding="utf-8")))
        if durable_lineage is not None:
            records.append(durable_lineage)
        for record in records:
            if not isinstance(record, dict) or any(record.get(k) != v for k, v in context.items()):
                raise AcceptanceFailure("Recovery proof does not match the exact run/trainer/sandbox context.")
            if type(record.get("schema_version")) is not int or type(record.get("trainer_owned")) is not bool:
                raise AcceptanceFailure("Invalid recovery schema or trainer ownership type.")
            for key in ("owned_case_ids", "owned_claim_event_ids", "owned_dispatch_ids"):
                values = record.get(key)
                if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                    raise AcceptanceFailure(f"Invalid recovery identifier list: {key}.")
            if record["owned_claim_event_ids"] and not record["trainer_owned"]:
                raise AcceptanceFailure("Claim recovery proof requires validated trainer ownership.")
            cases.update(record["owned_case_ids"])
            claims.update(record["owned_claim_event_ids"])
            dispatches.update(record["owned_dispatch_ids"])
            prior_trainer_owned |= record["trainer_owned"]
    except Exception as exc:
        return failed(f"Recovery proof could not be validated: {exc}")

    # Required reads complete before any persistence/deletion. Cursor errors are
    # failures too; eagerly materialise each cursor rather than saving half a scan.
    try:
        parent = db.trainers.find_one({"id": trainer_id})
        if parent is not None:
            if parent.get("test_fixture") is not True or parent.get("test_run_id") != run_id:
                return failed("Trainer ownership is unknown or contradicts this run; all records preserved.")
            trainer_owned = True
        else:
            trainer_owned = prior_trainer_owned

        discovered = list(db.support_threads.find({"sender_email": {"$in": context["run_emails"]}}))
        for row in discovered:
            if not isinstance(row.get("case_id"), str) or not row["case_id"]:
                raise AcceptanceFailure("Support inventory contains a row without a case ID.")
        candidates = cases | set(tracked_case_ids) | {row["case_id"] for row in discovered}
        for cid in sorted(candidates):
            if not isinstance(cid, str) or not cid:
                raise AcceptanceFailure("Invalid candidate support identifier.")
            thread = db.support_threads.find_one({"case_id": cid})
            if thread is None:
                if cid not in cases:
                    preserved.add(cid)
                    missing.add(cid)
                    return failed("Missing support parent has no validated prior ownership proof.")
            elif (thread.get("sender_email") not in context["run_emails"] or
                  thread.get("test_run_id") not in (None, "", run_id)):
                preserved.add(cid)
                cases.discard(cid)
                return failed("Current support ownership contradicts this run; all records preserved.")
            cases.add(cid)

        claim_rows = list(db.claim_events.find({"trainer_id": trainer_id}))
        if not trainer_owned and claim_rows:
            return failed("Orphan trainer claims lack validated ownership; all records preserved.")
        if trainer_owned:
            for row in claim_rows:
                if not isinstance(row.get("id"), str) or not row["id"]:
                    raise AcceptanceFailure("Claim inventory contains a row without an ID.")
                claims.add(row["id"])
        if claims:
            for row in list(db.claim_events.find({"id": {"$in": sorted(claims)}})):
                if row.get("trainer_id") != trainer_id:
                    raise AcceptanceFailure("Current claim ownership contradicts recovery proof.")

        targets = sorted(cases | ({trainer_id} if trainer_owned else set()))
        notification_rows = list(db.notification_events.find({"target_id": {"$in": targets}})) if targets else []
        if not trainer_owned:
            if (db.notification_events.count_documents({"target_id": trainer_id}) or
                db.audit_log.count_documents({"target": trainer_id}) or
                db.ops_obligations.count_documents({"entity_id": trainer_id})):
                return failed("Orphan trainer history lacks validated ownership; all records preserved.")
        for row in notification_rows:
            dispatch = row.get("dispatch_id") or row.get("id")
            if not isinstance(dispatch, str) or not dispatch:
                raise AcceptanceFailure("Notification inventory contains no recoverable identifier.")
            dispatches.add(dispatch)
        if dispatches:
            existing = list(db.notification_events.find({"$or": [
                {"dispatch_id": {"$in": sorted(dispatches)}}, {"id": {"$in": sorted(dispatches)}},
            ]}))
            if any(row.get("target_id") not in targets for row in existing):
                raise AcceptanceFailure("Current notification ownership contradicts recovery proof.")
    except Exception as exc:
        return failed(f"Required ownership/lineage inventory failed; nothing deleted: {exc}")

    current_lineage = {
        **context, "trainer_owned": trainer_owned, "owned_case_ids": sorted(cases),
        "owned_claim_event_ids": sorted(claims), "owned_dispatch_ids": sorted(dispatches),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    report.update({
        "tracked_case_ids": sorted(cases), "owned_claim_event_ids": sorted(claims),
        "owned_dispatch_ids": sorted(dispatches), "durable_lineage": current_lineage,
    })
    try:
        _write_atomic_json(lineage_file, current_lineage)
    except Exception as exc:
        return failed(f"Lineage persistence failed before source deletion: {exc}")

    # Every destructive query derives from the validated, durable inventory.
    # No speculative legacy aliases or metadata-wide trainer sweeps are needed.
    operations = []
    if trainer_owned:
        operations.extend([
            ("trainers", db.trainers, {"id": trainer_id, "test_fixture": True, "test_run_id": run_id}, None),
            ("claim_events", db.claim_events, {"trainer_id": trainer_id, "id": {"$in": sorted(claims)}}, None),
            ("trainer_notifications", db.notification_events, {"target_id": trainer_id}, None),
            ("trainer_audit", db.audit_log, {"target": trainer_id}, None),
            ("trainer_obligations", db.ops_obligations, {"entity_id": trainer_id}, None),
        ])
    if claims:
        operations.append(("claim_event_obligations", db.ops_obligations, {"$or": [
            {"entity_id": {"$in": sorted(claims)}},
            {"obligation_id": {"$in": [f"obligation:claim:{cid}" for cid in sorted(claims)]}},
        ]}, None))
    for cid in sorted(cases):
        operations.extend([
            ("support_threads", db.support_threads, {"case_id": cid}, cid),
            ("support_notifications", db.notification_events, {"target_id": cid}, cid),
            ("support_audit", db.audit_log, {"target": cid}, cid),
            ("ops_obligations", db.ops_obligations, {"$or": [
                {"entity_id": cid}, {"obligation_id": f"obligation:support:{cid}"},
            ]}, cid),
        ])
    if dispatches:
        operations.append(("dispatch_obligations", db.ops_obligations, {"$or": [
            {"entity_id": {"$in": sorted(dispatches)}},
            {"obligation_id": {"$in": [f"obligation:message:{did}" for did in sorted(dispatches)]}},
        ]}, None))
    for key, collection, query, cid in operations:
        try:
            count = collection.delete_many(query).deleted_count
            if cid is None:
                deleted[key] = count
            else:
                deleted[key][cid] = count
        except Exception as exc:
            errors.append(f"{key} delete failed: {exc}")

    leftovers = report["leftovers"]
    for key, collection, query, cid in operations:
        prefixes = {"support_threads": "thread", "support_notifications": "notif", "support_audit": "audit", "ops_obligations": "obligations"}
        label = key if cid is None else f"{prefixes[key]}_{cid}"
        try:
            leftovers[label] = collection.count_documents(query)
        except Exception as exc:
            leftovers[label] = -1
            errors.append(f"{label} count failed: {exc}")
    # Also detect newly created source rows outside the saved claim-ID snapshot.
    if trainer_owned:
        try:
            leftovers["claim_events"] = db.claim_events.count_documents({"trainer_id": trainer_id})
        except Exception as exc:
            leftovers["claim_events"] = -1
            errors.append(f"claim inventory count failed: {exc}")
    endpoints = [
        (f"trainer_{trainer_id}", f"{api_url}/api/trainers/{trainer_id}", {}),
        *[(f"thread_{cid}", f"{api_url}/api/oversight/support/threads/{cid}", {"X-Admin-Pass": admin_pass}) for cid in sorted(cases)],
    ]
    for label, url, headers in endpoints:
        try:
            status, _ = request_fn(url, headers=headers)
            report["endpoint_404s"][label] = status == 404
        except Exception as exc:
            report["endpoint_404s"][label] = False
            errors.append(f"{label} absence check failed: {exc}")
    report["all_leftovers_zero"] = all(count == 0 for count in leftovers.values())
    report["all_endpoints_404"] = all(report["endpoint_404s"].values())
    report["status"] = "CLEAN" if (not errors and report["all_leftovers_zero"] and report["all_endpoints_404"]) else "FAILED"
    return report


def _validate_receipt_configuration(receipt_email: Optional[str], receipt_reader: Any) -> None:
    if receipt_email is None and receipt_reader is None:
        return
    if (not isinstance(receipt_email, str) or
            not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", receipt_email) or
            receipt_email.lower().endswith("@resend.dev") or not callable(receipt_reader)):
        raise AcceptanceFailure("Owner receipt mode requires a verified owner inbox and private receipt reader.")


def _parse_received_otp(line: str, expected: Dict[str, str]) -> str:
    def unique_object(pairs):
        if len(pairs) != len({key for key, _ in pairs}):
            raise ValueError
        return dict(pairs)
    try:
        value = json.loads(line, object_pairs_hook=unique_object)
        keys = {"run_id", "trainer_id", "claim_event_id", "phase"}
        if (not isinstance(value, dict) or set(value) != keys | {"otp"} or
                any(value.get(key) != expected.get(key) for key in keys) or
                not isinstance(value.get("otp"), str) or not re.fullmatch(r"[0-9]{6}", value["otp"])):
            raise ValueError
        return value["otp"]
    except Exception:
        raise AcceptanceFailure("Received code input did not match the pending challenge.") from None


def read_received_otp(expected: Dict[str, str], timeout: int = 180) -> str:
    """Consume one correlated mailbox receipt through private, bounded terminal input."""
    if not sys.stdin.isatty():
        raise AcceptanceFailure("Owner receipt mode requires private terminal input.")
    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    hidden = list(previous)
    hidden[3] &= ~termios.ECHO
    try:
        termios.tcsetattr(fd, termios.TCSANOW, hidden)
        print("DTD_RECEIPT_REQUIRED " + json.dumps(expected), flush=True)
        deadline = time.monotonic() + timeout
        received = bytearray()
        while b"\n" not in received:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                raise AcceptanceFailure("Mailbox receipt deadline elapsed.")
            chunk = os.read(fd, 4097 - len(received))
            if not chunk:
                raise AcceptanceFailure("Mailbox receipt input was missing.")
            received.extend(chunk)
            if len(received) > 4096:
                raise AcceptanceFailure("Mailbox receipt input was too long.")
        return _parse_received_otp(received.decode("utf-8"), expected)
    except (KeyboardInterrupt, EOFError, OSError, UnicodeDecodeError):
        raise AcceptanceFailure("Mailbox receipt input was interrupted.") from None
    finally:
        try:
            termios.tcflush(fd, termios.TCIFLUSH)
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, previous)


async def verify_received_trainer_browser(
    db: Any, trainer_id: str, run_id: str, recipient: str,
    receipt_reader: Any, artifact_dir: Path, headless: bool,
) -> Dict[str, str]:
    """Use received email codes and the normal trainer UI; never mint credentials."""
    from playwright.async_api import async_playwright, expect
    step = "open trainer"
    stages: Dict[str, str] = {}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            try:
                context = await browser.new_context(viewport={"width": 1440, "height": 1000})
                approved = {normalize_origin(WEB_URL), normalize_origin(API_URL)}
                async def guard(route, request):
                    await evaluate_browser_route(route, request, approved)
                await context.route("**/*", guard)
                page = await context.new_page()
                await page.goto(f"{WEB_URL}/trainers/{trainer_id}", wait_until="networkidle")
                verify_page_exact_origin(page.url, WEB_URL, "Trainer listing")
                await page.get_by_test_id("claim-profile-open").click()
                first_token = None
                for phase in ("initial", "recovery"):
                    step = f"{phase} email challenge"
                    await page.get_by_test_id("claim-email").fill(recipient)
                    async with page.expect_response(lambda r: r.url == f"{API_URL}/api/trainers/{trainer_id}/claim" and r.request.method == "POST") as pending:
                        await page.get_by_test_id("claim-start").click()
                    response = await pending.value
                    claim = await response.json()
                    assert response.status == 200 and claim.get("delivery_status") == "sent"
                    assert claim.get("status") == "pending_verification"
                    assert claim.get("is_renewal") is (phase == "recovery")
                    claim_id = claim.get("claim_event_id")
                    stored = db.claim_events.find_one({"id": claim_id, "trainer_id": trainer_id})
                    assert stored and stored.get("claimant_email") == recipient
                    receipt_context = {"run_id": run_id, "trainer_id": trainer_id, "claim_event_id": claim_id, "phase": phase}
                    code = await asyncio.to_thread(receipt_reader, receipt_context)
                    if not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code):
                        raise AcceptanceFailure("Mailbox receipt returned an invalid code shape.")
                    step = f"{phase} code verification"
                    code_input = page.get_by_test_id("claim-otp")
                    if phase == "initial":
                        wrong_code = f"{(int(code) + 1) % 1000000:06d}"
                        await code_input.fill(wrong_code)
                        async with page.expect_response(lambda r: r.url == f"{API_URL}/api/trainers/{trainer_id}/claim/verify") as rejected:
                            await page.get_by_test_id("claim-verify").click()
                        assert (await rejected.value).status == 400
                        assert db.claim_events.find_one({"id": claim_id}).get("attempts") == 1
                    await code_input.fill(code)
                    async with page.expect_response(lambda r: r.url == f"{API_URL}/api/trainers/{trainer_id}/capabilities/prefill" and r.request.method == "GET") as prefilled:
                        async with page.expect_response(lambda r: r.url == f"{API_URL}/api/trainers/{trainer_id}/claim/verify") as verified:
                            await page.get_by_test_id("claim-verify").click()
                    prefill_response = await prefilled.value
                    assert prefill_response.status == 200
                    assert (await prefill_response.json()).get("trainer_id") == trainer_id
                    assert "x-trainer-claim-session" in prefill_response.request.headers
                    assert "x-admin-pass" not in prefill_response.request.headers
                    response = await verified.value
                    session_result = await response.json()
                    assert response.status == 200
                    token = (session_result.get("session") or {}).get("token") or session_result.get("trainer_claim_session")
                    assert isinstance(token, str) and token
                    if phase == "initial":
                        first_token = token
                        stages["trainer_claim_verification"] = "PASSED (received mailbox code, normal browser verification)"
                        stages["trainer_claim_guards"] = "PASSED (mismatch, unavailable SMS, genuinely different invalid code)"
                    else:
                        assert token != first_token and session_result.get("session_renewed") is True
                        stages["trainer_session_renewal"] = "PASSED (received second code after browser session removal; not signed-token expiry)"
                    replay_status, _ = _http_request(
                        f"{API_URL}/api/trainers/{trainer_id}/claim/verify", method="POST",
                        payload={"claim_event_id": claim_id, "otp": code},
                    )
                    assert replay_status == 409
                    code = None
                    session_result = None
                    await expect(page.get_by_test_id("claim-catchment-type")).to_be_visible()
                    step = f"{phase} capability confirmation"
                    if phase == "initial":
                        await page.get_by_test_id("claim-specialty-puppy_training").check()
                        await page.get_by_test_id("claim-format-in_home").check()
                        await page.get_by_test_id("claim-stage-puppy").check()
                        await page.get_by_test_id("claim-philosophy").select_option("positive_reinforcement_force_free")
                        await page.get_by_test_id("claim-catchment-type").select_option("specific_suburbs")
                        await page.get_by_test_id("claim-serviced-suburbs").fill("Richmond, Fitzroy")
                        await page.get_by_test_id("claim-delivery-in-home").check()
                        await page.get_by_test_id("claim-confirm-submit").click()
                        await expect(page.get_by_test_id("claim-confirm-error")).to_contain_text("affirm")
                    else:
                        await expect(page.get_by_test_id("claim-catchment-type")).to_have_value("specific_suburbs")
                        await page.get_by_test_id("claim-catchment-type").select_option("melbourne_wide")
                    await page.get_by_test_id("claim-confirm-statement").check()
                    async with page.expect_response(lambda r: r.url == f"{API_URL}/api/trainers/{trainer_id}/capabilities/confirm") as confirmation:
                        await page.get_by_test_id("claim-confirm-submit").click()
                    confirmed = await confirmation.value
                    assert confirmed.status == 200
                    await expect(page.get_by_test_id("claim-success")).to_be_visible()
                    saved = db.trainers.find_one({"id": trainer_id, "test_fixture": True, "test_run_id": run_id})
                    expected_catchment = "specific_suburbs" if phase == "initial" else "melbourne_wide"
                    assert saved and saved.get("catchment_type") == expected_catchment
                    assert saved.get("tier") == "claimed"
                    assert "puppy_training" in saved.get("specialties", [])
                    assert "in_home" in saved.get("service_formats", [])
                    assert "puppy" in saved.get("life_stages", [])
                    assert saved.get("training_philosophy") == "positive_reinforcement_force_free"
                    assert saved.get("capabilities_confirmed_at")
                    if phase == "initial":
                        assert {v.casefold() for v in saved.get("serviced_suburbs", [])} == {"richmond", "fitzroy"}
                    await page.keyboard.press("Escape")
                    await page.reload(wait_until="networkidle")
                    await expect(page.get_by_test_id("trainer-owner-controls")).to_be_visible()
                    async with page.expect_response(lambda r: r.url == f"{API_URL}/api/trainers/{trainer_id}/capabilities/prefill" and r.request.method == "GET") as prefilled:
                        await page.get_by_test_id("edit-capabilities-open").click()
                    prefill_response = await prefilled.value
                    assert prefill_response.status == 200
                    assert (await prefill_response.json()).get("trainer_id") == trainer_id
                    assert "x-trainer-claim-session" in prefill_response.request.headers
                    assert "x-admin-pass" not in prefill_response.request.headers
                    await expect(page.get_by_test_id("claim-catchment-type")).to_have_value(expected_catchment)
                    await expect(page.get_by_test_id("claim-specialty-puppy_training")).to_be_checked()
                    await expect(page.get_by_test_id("claim-format-in_home")).to_be_checked()
                    await expect(page.get_by_test_id("claim-stage-puppy")).to_be_checked()
                    await page.screenshot(path=str(artifact_dir / f"trainer_{phase}_capability_revisit.png"))
                    stages["trainer_capabilities_prefill"] = "PASSED (protected editor prefill and persisted browser revisit)"
                    stages["trainer_catchment_confirmation"] = "PASSED (specific suburbs then Melbourne-wide; explicit confirmation guard)"
                    if phase == "initial":
                        step = "claimed profile privacy and session removal"
                        await page.keyboard.press("Escape")
                        await page.evaluate("(id) => sessionStorage.removeItem('dtd-trainer-billing-auth:' + id)", trainer_id)
                        await page.reload(wait_until="networkidle")
                        await expect(page.get_by_test_id("trainer-owner-login-prompt")).to_be_visible()
                        await expect(page.get_by_test_id("trainer-owner-controls")).to_have_count(0)
                        await expect(page.get_by_test_id("trainer-billing-link")).to_have_count(0)
                        await page.screenshot(path=str(artifact_dir / "trainer_claimed_public_privacy.png"))
                        await page.get_by_test_id("edit-capabilities-open").click()
                stages["trainer_claimed_profile_privacy"] = "PASSED (claimed profile without stored session hides owner and billing controls)"
            finally:
                await browser.close()
        return stages
    except Exception:
        # Browser errors can echo fill values or session-bearing responses.
        raise AcceptanceFailure(f"Received trainer browser check failed at {step}; private details suppressed.") from None


async def run_acceptance(
    mongo_url: str,
    admin_pass: str,
    artifact_dir: Optional[Path] = None,
    preflight_runner: Any = None,
    headless: bool = True,
    receipt_email: Optional[str] = None,
    receipt_reader: Any = None,
) -> Dict[str, Any]:
    _validate_receipt_configuration(receipt_email, receipt_reader)
    _require_sandbox(mongo_url, admin_pass)
    metadata = enforce_sandbox_preflight(SANDBOX_PROJECT, runner=preflight_runner)

    target_artifact_dir = artifact_dir or DEFAULT_ARTIFACT_DIR
    target_artifact_dir.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex[:12]
    trainer_id = f"sandbox-trainer-{run_id}"
    complaint_email = f"delivered+sandbox-support-{run_id}-api@resend.dev"
    browser_email = f"delivered+sandbox-support-{run_id}-browser@resend.dev"

    # Durable run manifest written before any mutations
    manifest = {
        "run_id": run_id,
        "trainer_id": trainer_id,
        "complaint_email": complaint_email,
        "browser_email": browser_email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": SANDBOX_PROJECT,
        "database": SANDBOX_DB,
    }
    manifest_path = target_artifact_dir / f"run_manifest_{run_id}.json"
    try:
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"      Pre-mutation run manifest saved to: {manifest_path}")
    except Exception as e:
        raise AcceptanceFailure(f"Failed to persist pre-mutation run manifest to {manifest_path}: {e}") from e

    tracked_case_ids: Set[str] = set()
    test_exception: Optional[Exception] = None

    evidence: Dict[str, Any] = {
        "run_id": run_id,
        "trainer_id": trainer_id,
        "manifest_saved": str(manifest_path),
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
            "name": f"Sandbox Test Canine Academy {run_id}",
            "suburb": "Richmond",
            "region": "Greater Melbourne",
            "published": True,
            "contact_ready": True,
            "verification_status": "unverified",
            "claim_status": "unclaimed",
            "tier": "free",
            "email": receipt_email or TEST_RECIPIENT,
            "billing_email": receipt_email or TEST_RECIPIENT,
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
        assert not receipt_email or receipt_email not in json.dumps(profile), "Public profile exposed the private receipt inbox"
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
            payload={"email": receipt_email or TEST_RECIPIENT, "method": "sms"},
        )
        assert status == 503, f"Expected 503 for SMS method, got {status}"
        print("      - Guard: SMS provider unavailable -> 503 OK")

        if receipt_email is None:
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
            # Note: Privileged secret derivation prohibited per audit; delivered OTP verification requires external mailbox access.
            evidence["stages"]["trainer_claim_verification"] = (
                "NOT_VERIFIED (operator OTP or provider mailbox receipt required; privileged secret derivation removed per audit)"
            )
            evidence["stages"]["trainer_capabilities_prefill"] = "SKIPPED (requires verified session)"
            evidence["stages"]["trainer_session_renewal"] = "SKIPPED (requires verified session)"
            evidence["stages"]["trainer_catchment_confirmation"] = "SKIPPED (requires verified session)"
            print("      - Notice: Trainer claim verification marked NOT_VERIFIED (external provider mailbox receipt required; privileged derivation prohibited).")

        else:
            evidence["stages"].update(await verify_received_trainer_browser(
                db, trainer_id, run_id, receipt_email, receipt_reader, target_artifact_dir, headless,
            ))

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
        print("      - Guarded ticket closure verified: status=resolved (API status confirmed)")
        evidence["stages"]["support_lifecycle_api"] = "PASSED"

        # =====================================================================
        # PART C: Live Browser Headless Playwright Verification
        # =====================================================================
        print("\n[4/5] Executing Live Browser Headless Playwright Checks against dtd-web-dev...")
        try:
            from playwright.async_api import async_playwright, expect

            approved_web_origin = normalize_origin(WEB_URL)
            approved_api_origin = normalize_origin(API_URL)
            approved_origins = {approved_web_origin, approved_api_origin}

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                context = await browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    user_agent="DTD-Acceptance-Playwright/1.0",
                )

                async def browser_route_guard(route, request):
                    await evaluate_browser_route(route, request, approved_origins)

                await context.route("**/*", browser_route_guard)
                page = await context.new_page()

                # 1. Contact Page Journey
                print("      - Browser: Loading /contact...")
                resp = await page.goto(f"{WEB_URL}/contact", wait_until="networkidle", timeout=30000)
                assert resp and resp.status == 200, f"Contact page load failed: {resp.status if resp else 'no response'}"

                verify_page_exact_origin(page.url, approved_web_origin, "Contact page load")

                await page.fill("input[name='name']", f"Playwright User {run_id[:4]}")
                await page.fill("input[name='email']", browser_email)
                await page.fill("input[name='subject']", f"Browser test enquiry {run_id[:4]}")
                await page.fill("textarea[name='message']", "Testing contact page submit in live headless browser.")

                verify_page_exact_origin(page.url, approved_web_origin, "Contact page submit pre-check")

                await page.click("button[type='submit']")

                # Wait for success confirmation
                await page.wait_for_selector("text=Message Received", timeout=15000)

                verify_page_exact_origin(page.url, approved_web_origin, "Contact confirmation")

                screenshot_contact = target_artifact_dir / "sandbox_contact_page_submitted.png"
                await page.screenshot(path=str(screenshot_contact))
                print(f"      - Browser: Contact form submitted & confirmed. Screenshot saved: {screenshot_contact.name}")

                # Capture browser generated case_id from DOM for teardown
                content = await page.content()
                m = re.search(r"sup_\d{8}_[a-zA-Z0-9]+", content)
                assert m, "Contact confirmation has no case reference; refusing to select any Ops case"
                browser_case_id = m.group(0)
                tracked_case_ids.add(browser_case_id)
                print(f"        Browser-submitted case ID: {browser_case_id}")

                # 2. Ops Support Cases View
                print("      - Browser: Loading /ops with session credentials...")
                await page.goto(f"{WEB_URL}/ops", wait_until="networkidle", timeout=30000)

                verify_page_exact_origin(page.url, approved_web_origin, "Ops page load")

                await page.evaluate("""(passVal) => {
                    sessionStorage.setItem("dtd-admin-pass", JSON.stringify({
                        value: passVal,
                        expiresAt: Date.now() + 3600000
                    }));
                }""", admin_pass)
                await page.reload(wait_until="networkidle")

                verify_page_exact_origin(page.url, approved_web_origin, "Ops page reload")

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

                # Select only the case created by this browser run, never a pre-existing row.
                owned_row = page.get_by_test_id("ops-support-thread-row").filter(
                    has=page.get_by_text(browser_case_id, exact=True)
                )
                await expect(owned_row).to_have_count(1)
                await owned_row.click()
                detail = page.get_by_test_id("ops-support-detail")
                await expect(detail.get_by_text(browser_case_id, exact=True)).to_be_visible()
                await expect(detail).to_contain_text("Status: open")
                await expect(detail.get_by_text("Testing contact page submit in live headless browser.", exact=True)).to_be_visible()

                browser_reply = f"Sandbox browser acceptance reply for run {run_id}."
                reply_input = page.get_by_test_id("ops-support-reply-input")
                reply_button = page.get_by_test_id("ops-support-reply-btn")
                await expect(reply_button).to_be_disabled()
                await reply_input.fill(browser_reply)
                await reply_button.click()
                await expect(detail.get_by_text("Reply dispatched to customer.", exact=True)).to_be_visible()
                await expect(detail).to_contain_text("Status: awaiting_customer_reply")
                await expect(reply_input).to_have_value("")
                await reply_input.fill(browser_reply)
                await reply_button.click()
                await expect(detail.get_by_text(
                    "This reply was already dispatched. No additional email was sent.", exact=True
                )).to_be_visible()
                thread_after_reply = db.support_threads.find_one({"case_id": browser_case_id})
                assert thread_after_reply and thread_after_reply.get("status") == "awaiting_customer_reply"
                matching_replies = [message for message in thread_after_reply.get("messages", [])
                                    if message.get("sender") == "operator" and message.get("text") == browser_reply]
                assert len(matching_replies) == 1, "Duplicate UI reply created an extra operator message"
                assert matching_replies[0].get("delivery_status") == "accepted"
                await page.screenshot(path=str(target_artifact_dir / "sandbox_support_selected_reply.png"))

                close_notes = page.get_by_test_id("ops-support-close-notes")
                close_confirm = page.get_by_test_id("ops-support-close-confirm")
                close_button = page.get_by_test_id("ops-support-close-btn")
                await close_notes.fill("Short")
                await close_confirm.check()
                await expect(close_button).to_be_disabled()
                await close_confirm.uncheck()
                resolution = f"Synthetic sandbox case {run_id}: browser reply and duplicate guard verified; no customer action required."
                await close_notes.fill(resolution)
                await expect(close_button).to_be_disabled()
                await close_confirm.check()
                await expect(close_button).to_be_enabled()
                await close_button.click()
                await expect(detail.get_by_text("Case status: resolved.", exact=True)).to_be_visible()
                closed_thread = db.support_threads.find_one({"case_id": browser_case_id})
                assert closed_thread and closed_thread.get("status") == "resolved"
                assert closed_thread.get("resolution_notes") == resolution

                # Navigate away and back so acceptance proves a fresh persisted read.
                await page.get_by_test_id("ops-nav-overview").click()
                await page.get_by_test_id("ops-nav-support_threads").click()
                await expect(owned_row).to_have_count(1)
                await owned_row.click()
                await expect(detail.get_by_text(browser_case_id, exact=True)).to_be_visible()
                await expect(detail.get_by_text("Case status: resolved.", exact=True)).to_be_visible()
                await expect(detail).to_contain_text(resolution)
                await expect(page.get_by_test_id("ops-support-reply-input")).to_have_count(0)
                await page.screenshot(path=str(target_artifact_dir / "sandbox_support_selected_closed_revisit.png"))
                evidence["stages"]["support_selected_browser_lifecycle"] = (
                    "PASSED (owned detail, reply, duplicate feedback, closure guards, persisted closed-case revisit)"
                )
                await browser.close()
            evidence["stages"]["browser_ui_verification"] = "PASSED (contact form + selected Ops support lifecycle)"
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
        cleanup_report = execute_deterministic_teardown(
            db=db,
            trainer_id=trainer_id,
            tracked_case_ids=tracked_case_ids,
            run_emails=[complaint_email, browser_email],
            admin_pass=admin_pass,
            api_url=API_URL,
            http_request_fn=_http_request,
            run_id=run_id,
            recovery_dir=target_artifact_dir,
        )
        try:
            client.close()
        except Exception:
            pass

        evidence["cleanup"] = cleanup_report

        # Resolve terminal status and error before saving final report
        terminal_status = "STAGE_CHECKS_COMPLETED"
        terminal_error = None
        if test_exception is not None and cleanup_report.get("status") == "FAILED":
            terminal_status = "EXECUTION_AND_CLEANUP_FAILED"
            terminal_error = (
                f"Scenario failed: {test_exception}; Cleanup failed: "
                f"{cleanup_report.get('cleanup_errors')}, leftovers: {cleanup_report.get('leftovers')}"
            )
        elif test_exception is not None:
            terminal_status = "EXECUTION_FAILED"
            terminal_error = str(test_exception)
        elif cleanup_report.get("status") == "FAILED":
            terminal_status = "CLEANUP_FAILED"
            terminal_error = (
                f"Cleanup failed: {cleanup_report.get('cleanup_errors')}, "
                f"leftovers: {cleanup_report.get('leftovers')}"
            )

        evidence["status"] = terminal_status
        if terminal_error:
            evidence["error"] = terminal_error

        # Persist sanitized final evidence report on both success and failure
        report_path = target_artifact_dir / f"run_report_{run_id}.json"
        report_save_error = None
        try:
            final_report = {
                "run_id": run_id,
                "trainer_id": trainer_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": terminal_status,
                "error": terminal_error,
                "scenario_exception": str(test_exception) if test_exception else None,
                "cleanup_report": cleanup_report,
                "evidence": evidence,
            }
            report_path.write_text(json.dumps(final_report, indent=2) + "\n")
            evidence["report_saved"] = str(report_path)
            print(f"      Final run report saved to: {report_path}")
        except Exception as e:
            report_save_error = e
            print(f"      [!] Error: failed to save final run report to disk: {e}", file=sys.stderr)

    # If saving required report failed, fail nonzero while preserving original scenario/cleanup error
    if report_save_error is not None:
        save_err_msg = f"Failed to persist required final run report to {report_path}: {report_save_error}"
        if terminal_error:
            save_err_msg = f"{save_err_msg} (prior error: {terminal_error})"
        if test_exception is not None:
            raise AcceptanceFailure(save_err_msg) from test_exception
        raise AcceptanceFailure(save_err_msg) from report_save_error

    if terminal_status == "EXECUTION_AND_CLEANUP_FAILED":
        raise AcceptanceFailure(terminal_error) from test_exception
    elif terminal_status == "EXECUTION_FAILED":
        raise test_exception
    elif terminal_status == "CLEANUP_FAILED":
        raise AcceptanceFailure(terminal_error)

    evidence["status"] = "STAGE_CHECKS_COMPLETED"
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Execute acceptance against sandbox.")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser checks in headless mode (default: True).")
    parser.add_argument("--owner-receipt", action="store_true", help="Use an existing verified owner inbox via private terminal receipt input.")
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
        receipt_email = os.environ.get("DTD_ACCEPTANCE_RECEIPT_EMAIL", "") if args.owner_receipt else None
        if args.owner_receipt and not sys.stdin.isatty():
            raise AcceptanceFailure("Owner receipt mode requires private terminal input before creating fixtures.")
        evidence = asyncio.run(run_acceptance(
            mongo_url=mongo_url,
            admin_pass=admin_pass,
            artifact_dir=artifact_dir,
            headless=args.headless,
            receipt_email=receipt_email,
            receipt_reader=read_received_otp if args.owner_receipt else None,
        ))
        print("\n=== ACCEPTANCE EVIDENCE ===")
        print(json.dumps(evidence, indent=2))
        return 0
    except Exception as e:
        print(f"\n[!] ACCEPTANCE FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
