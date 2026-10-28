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
   guarded closure (minimum notes length requirement verified via API).
4. Headless Playwright browser UI validation on dtd-web-dev (contact form submit, /ops support cases view).
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
import tempfile
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
    has_auth = "authorization" in headers or "x-admin-pass" in headers

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
    print("\n[5/5] Executing Deterministic Teardown & Cleanup...")
    request_fn = http_request_fn or _http_request
    del_counts: Dict[str, Any] = {
        "trainers": 0,
        "claim_events": 0,
        "trainer_notifications": 0,
        "trainer_audit": 0,
        "trainer_obligations": 0,
        "claim_event_obligations": 0,
        "dispatch_obligations": 0,
        "support_threads": {},
        "support_notifications": {},
        "support_audit": {},
        "ops_obligations": {},
    }
    cleanup_errors: List[str] = []

    recovery_path = recovery_dir or Path(tempfile.gettempdir())
    lineage_file = recovery_path / f"dtd_lineage_{run_id or 'default'}.json"

    # Load existing lineage from disk if not supplied directly
    loaded_lineage = None
    if durable_lineage is not None:
        loaded_lineage = dict(durable_lineage)
    else:
        try:
            if lineage_file.exists():
                loaded_lineage = json.loads(lineage_file.read_text())
        except Exception as e:
            cleanup_errors.append(f"failed to load existing lineage file {lineage_file}: {e}")

    # 1. Validate trainer ownership
    trainer_doc = None
    try:
        if hasattr(db, "trainers"):
            if hasattr(db.trainers, "find_one"):
                trainer_doc = db.trainers.find_one({"id": trainer_id})
            elif hasattr(db.trainers, "find"):
                docs = list(db.trainers.find({"id": trainer_id}))
                trainer_doc = docs[0] if docs else None
    except Exception as e:
        cleanup_errors.append(f"trainer lookup error: {e}")

    trainer_owned = False
    if trainer_doc is not None:
        is_fixture = bool(trainer_doc.get("test_fixture") is True)
        doc_run_id = trainer_doc.get("test_run_id")
        if is_fixture:
            if doc_run_id and run_id:
                trainer_owned = (doc_run_id == run_id)
            else:
                trainer_owned = True
        else:
            trainer_owned = False
            print(f"      [!] Preserving unmarked colliding trainer {trainer_id}")
    else:
        # Parent row absent. Only owned if durable prior proof binds this trainer to run
        if loaded_lineage and loaded_lineage.get("trainer_owned") is True:
            lineage_trainer_id = loaded_lineage.get("trainer_id")
            lineage_run_id = loaded_lineage.get("run_id")
            if (not lineage_trainer_id or lineage_trainer_id == trainer_id) and (not lineage_run_id or not run_id or lineage_run_id == run_id):
                trainer_owned = True

    # 2. Discover support threads created strictly by this run's synthetic emails
    # (Do NOT discover by trainer_id alone, to avoid adopting unrelated customer enquiries)
    try:
        support_coll = getattr(db, "support_threads", None)
        if support_coll is not None and hasattr(support_coll, "find"):
            discovered = support_coll.find({"sender_email": {"$in": run_emails}}, {"case_id": 1})
            for doc in discovered:
                cid = doc.get("case_id")
                if cid:
                    tracked_case_ids.add(cid)
    except Exception as e:
        cleanup_errors.append(f"discovery error: {e}")

    # 3. Validate ownership of all tracked case IDs against database records or durable lineage
    # (Response case IDs or DOM IDs must not delete unowned/foreign records)
    validated_owned_case_ids: Set[str] = set()
    unowned_preserved_cases: List[str] = []
    unverified_missing_cases: List[str] = []

    if loaded_lineage and "owned_case_ids" in loaded_lineage:
        for cid in loaded_lineage["owned_case_ids"]:
            validated_owned_case_ids.add(cid)

    for cid in sorted(tracked_case_ids):
        try:
            thread_doc = None
            if hasattr(db, "support_threads") and hasattr(db.support_threads, "find_one"):
                thread_doc = db.support_threads.find_one({"case_id": cid})
            elif hasattr(db, "support_threads") and hasattr(db.support_threads, "find"):
                docs = list(db.support_threads.find({"case_id": cid}))
                thread_doc = docs[0] if docs else None

            if thread_doc is None:
                if cid in validated_owned_case_ids:
                    # Verified from durable prior proof
                    pass
                else:
                    unowned_preserved_cases.append(cid)
                    unverified_missing_cases.append(cid)
                    print(f"      [!] Preserving unverified missing support case {cid} (no DB record and no durable prior proof)")
            else:
                sender = thread_doc.get("sender_email")
                doc_run_id = thread_doc.get("test_run_id")
                is_owned = False
                if sender in run_emails:
                    is_owned = True
                elif doc_run_id and run_id and doc_run_id == run_id:
                    is_owned = True

                if is_owned:
                    validated_owned_case_ids.add(cid)
                else:
                    unowned_preserved_cases.append(cid)
                    print(f"      [!] Preserving unowned foreign support thread {cid} (sender: {sender!r})")
        except Exception as e:
            cleanup_errors.append(f"case ownership check {cid}: {e}")

    # 4. Gather lineage IDs before deleting source rows
    owned_claim_event_ids_set: Set[str] = set()
    if loaded_lineage and "owned_claim_event_ids" in loaded_lineage:
        for ce_id in loaded_lineage["owned_claim_event_ids"]:
            owned_claim_event_ids_set.add(ce_id)

    if trainer_owned:
        try:
            if hasattr(db, "claim_events") and hasattr(db.claim_events, "find"):
                for ce in db.claim_events.find({"trainer_id": trainer_id}):
                    ce_id = ce.get("id") or str(ce.get("_id", ""))
                    if ce_id:
                        owned_claim_event_ids_set.add(ce_id)
        except Exception as e:
            cleanup_errors.append(f"claim event lineage gather: {e}")

    owned_claim_event_ids = sorted(owned_claim_event_ids_set)

    owned_dispatch_ids_set: Set[str] = set()
    if loaded_lineage and "owned_dispatch_ids" in loaded_lineage:
        for disp_id in loaded_lineage["owned_dispatch_ids"]:
            owned_dispatch_ids_set.add(disp_id)

    target_ids = []
    if trainer_owned:
        target_ids.append(trainer_id)
    target_ids.extend(sorted(validated_owned_case_ids))

    if target_ids:
        try:
            if hasattr(db, "notification_events") and hasattr(db.notification_events, "find"):
                for notif in db.notification_events.find({"target_id": {"$in": target_ids}}):
                    disp_id = notif.get("dispatch_id")
                    if disp_id:
                        owned_dispatch_ids_set.add(disp_id)
        except Exception as e:
            cleanup_errors.append(f"notification dispatch lineage gather: {e}")

    owned_dispatch_ids = sorted(owned_dispatch_ids_set)

    # 5. Persist lineage BEFORE deleting source rows
    current_lineage = {
        "run_id": run_id,
        "trainer_id": trainer_id,
        "trainer_owned": trainer_owned,
        "owned_case_ids": sorted(validated_owned_case_ids),
        "owned_claim_event_ids": owned_claim_event_ids,
        "owned_dispatch_ids": owned_dispatch_ids,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        lineage_file.parent.mkdir(parents=True, exist_ok=True)
        lineage_file.write_text(json.dumps(current_lineage, indent=2) + "\n")
    except Exception as e:
        cleanup_errors.append(f"lineage persistence failed before source deletion: {e}")
        return {
            "status": "FAILED",
            "deleted": del_counts,
            "leftovers": {},
            "endpoint_404s": {},
            "cleanup_errors": cleanup_errors,
            "all_leftovers_zero": False,
            "all_endpoints_404": False,
            "tracked_case_ids": sorted(validated_owned_case_ids),
            "unowned_preserved_cases": sorted(unowned_preserved_cases),
            "unverified_missing_cases": sorted(unverified_missing_cases),
            "owned_claim_event_ids": owned_claim_event_ids,
            "owned_dispatch_ids": owned_dispatch_ids,
            "durable_lineage": current_lineage,
        }

    # 6. Delete synthetic trainer fixtures and dependent records with explicit test fixture requirement
    # (Unmarked pre-existing trainers colliding on ID must never have parent or dependencies deleted)
    if trainer_owned:
        try:
            trainer_del_filter: Dict[str, Any] = {"id": trainer_id, "test_fixture": True}
            if run_id:
                trainer_del_filter["$or"] = [
                    {"test_run_id": run_id},
                    {"test_run_id": {"$exists": False}},
                    {"test_run_id": None},
                ]
            del_counts["trainers"] = db.trainers.delete_many(trainer_del_filter).deleted_count
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

        try:
            del_counts["trainer_obligations"] = db.ops_obligations.delete_many(
                {
                    "$or": [
                        {"entity_id": trainer_id},
                        {"obligation_id": trainer_id},
                        {"obligation_id": f"trainer:{trainer_id}"},
                        {"obligation_id": f"obligation:trainer:{trainer_id}"},
                    ]
                }
            ).deleted_count
        except Exception as e:
            cleanup_errors.append(f"trainer_obligations delete: {e}")

    # Delete claim event obligations keyed by claim_event.id
    if owned_claim_event_ids:
        try:
            ce_ob_query = {
                "$or": [
                    {"entity_id": {"$in": owned_claim_event_ids}},
                    {"obligation_id": {"$in": [f"obligation:claim:{cid}" for cid in owned_claim_event_ids] + [f"claim:{cid}" for cid in owned_claim_event_ids] + owned_claim_event_ids}},
                    {"metadata.claim_event_id": {"$in": owned_claim_event_ids}},
                ]
            }
            if trainer_owned:
                ce_ob_query["$or"].append({"metadata.trainer_id": trainer_id})
            del_counts["claim_event_obligations"] = db.ops_obligations.delete_many(ce_ob_query).deleted_count
        except Exception as e:
            cleanup_errors.append(f"claim_event_obligations delete: {e}")

    # 7. Delete validated support threads independently with full case ID keys and actual schema
    for cid in sorted(validated_owned_case_ids):
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
            del_counts["ops_obligations"][cid] = db.ops_obligations.delete_many(
                {
                    "$or": [
                        {"entity_id": cid},
                        {"obligation_id": cid},
                        {"obligation_id": f"support:{cid}"},
                        {"obligation_id": f"support_{cid}"},
                        {"obligation_id": f"obligation:support:{cid}"},
                        {"metadata.case_id": cid},
                    ]
                }
            ).deleted_count
        except Exception as e:
            cleanup_errors.append(f"ops_obligations {cid} delete: {e}")

    # Delete dispatch obligations keyed by dispatch_id
    if owned_dispatch_ids:
        try:
            disp_ob_query = {
                "$or": [
                    {"entity_id": {"$in": owned_dispatch_ids}},
                    {"obligation_id": {"$in": [f"obligation:message:{did}" for did in owned_dispatch_ids] + [f"message:{did}" for did in owned_dispatch_ids] + owned_dispatch_ids}},
                    {"metadata.dispatch_id": {"$in": owned_dispatch_ids}},
                ]
            }
            del_counts["dispatch_obligations"] = db.ops_obligations.delete_many(disp_ob_query).deleted_count
        except Exception as e:
            cleanup_errors.append(f"dispatch_obligations delete: {e}")

    # 8. Direct datastore leftovers count
    leftovers: Dict[str, Any] = {}
    if trainer_owned:
        try:
            leftovers["trainers"] = db.trainers.count_documents({"id": trainer_id, "test_fixture": True})
        except Exception as e:
            cleanup_errors.append(f"trainers count error: {e}")
            leftovers["trainers"] = -1

        try:
            leftovers["claim_events"] = db.claim_events.count_documents({"trainer_id": trainer_id})
        except Exception as e:
            cleanup_errors.append(f"claim_events count error: {e}")
            leftovers["claim_events"] = -1

        try:
            leftovers["trainer_notifications"] = db.notification_events.count_documents({"target_id": trainer_id})
        except Exception as e:
            cleanup_errors.append(f"trainer_notifications count error: {e}")
            leftovers["trainer_notifications"] = -1

        try:
            leftovers["trainer_audit"] = db.audit_log.count_documents({"target": trainer_id})
        except Exception as e:
            cleanup_errors.append(f"trainer_audit count error: {e}")
            leftovers["trainer_audit"] = -1

        try:
            leftovers["trainer_obligations"] = db.ops_obligations.count_documents(
                {
                    "$or": [
                        {"entity_id": trainer_id},
                        {"obligation_id": trainer_id},
                        {"obligation_id": f"trainer:{trainer_id}"},
                        {"obligation_id": f"obligation:trainer:{trainer_id}"},
                    ]
                }
            )
        except Exception as e:
            cleanup_errors.append(f"trainer_obligations count error: {e}")
            leftovers["trainer_obligations"] = -1

    if owned_claim_event_ids:
        try:
            ce_query = {
                "$or": [
                    {"entity_id": {"$in": owned_claim_event_ids}},
                    {"obligation_id": {"$in": [f"obligation:claim:{cid}" for cid in owned_claim_event_ids] + [f"claim:{cid}" for cid in owned_claim_event_ids] + owned_claim_event_ids}},
                    {"metadata.claim_event_id": {"$in": owned_claim_event_ids}},
                ]
            }
            if trainer_owned:
                ce_query["$or"].append({"metadata.trainer_id": trainer_id})
            leftovers["claim_event_obligations"] = db.ops_obligations.count_documents(ce_query)
        except Exception as e:
            cleanup_errors.append(f"claim_event_obligations count error: {e}")
            leftovers["claim_event_obligations"] = -1

    for cid in sorted(validated_owned_case_ids):
        try:
            leftovers[f"thread_{cid}"] = db.support_threads.count_documents({"case_id": cid})
        except Exception as e:
            cleanup_errors.append(f"thread {cid} count error: {e}")
            leftovers[f"thread_{cid}"] = -1

        try:
            leftovers[f"notif_{cid}"] = db.notification_events.count_documents({"target_id": cid})
        except Exception as e:
            cleanup_errors.append(f"notif {cid} count error: {e}")
            leftovers[f"notif_{cid}"] = -1

        try:
            leftovers[f"audit_{cid}"] = db.audit_log.count_documents({"target": cid})
        except Exception as e:
            cleanup_errors.append(f"audit {cid} count error: {e}")
            leftovers[f"audit_{cid}"] = -1

        try:
            leftovers[f"obligations_{cid}"] = db.ops_obligations.count_documents(
                {
                    "$or": [
                        {"entity_id": cid},
                        {"obligation_id": cid},
                        {"obligation_id": f"support:{cid}"},
                        {"obligation_id": f"support_{cid}"},
                        {"obligation_id": f"obligation:support:{cid}"},
                        {"metadata.case_id": cid},
                    ]
                }
            )
        except Exception as e:
            cleanup_errors.append(f"obligations {cid} count error: {e}")
            leftovers[f"obligations_{cid}"] = -1

    if owned_dispatch_ids:
        try:
            leftovers["dispatch_obligations"] = db.ops_obligations.count_documents(
                {
                    "$or": [
                        {"entity_id": {"$in": owned_dispatch_ids}},
                        {"obligation_id": {"$in": [f"obligation:message:{did}" for did in owned_dispatch_ids] + [f"message:{did}" for did in owned_dispatch_ids] + owned_dispatch_ids}},
                        {"metadata.dispatch_id": {"$in": owned_dispatch_ids}},
                    ]
                }
            )
        except Exception as e:
            cleanup_errors.append(f"dispatch_obligations count error: {e}")
            leftovers["dispatch_obligations"] = -1

    # 9. Public 404 absence checks
    endpoint_404s: Dict[str, bool] = {}
    if trainer_owned:
        try:
            status, _ = request_fn(f"{api_url}/api/trainers/{trainer_id}")
            endpoint_404s[f"trainer_{trainer_id}"] = (status == 404)
        except Exception as e:
            cleanup_errors.append(f"trainer 404 check: {e}")
            endpoint_404s[f"trainer_{trainer_id}"] = False

    for cid in sorted(validated_owned_case_ids):
        try:
            status, _ = request_fn(
                f"{api_url}/api/oversight/support/threads/{cid}",
                headers={"X-Admin-Pass": admin_pass},
            )
            endpoint_404s[f"thread_{cid}"] = (status == 404)
        except Exception as e:
            cleanup_errors.append(f"thread {cid} 404 check: {e}")
            endpoint_404s[f"thread_{cid}"] = False

    all_leftovers_zero = all(count == 0 for count in leftovers.values())
    all_endpoints_404 = all(res is True for res in endpoint_404s.values())
    is_clean = all_leftovers_zero and all_endpoints_404 and len(cleanup_errors) == 0

    report = {
        "status": "CLEAN" if is_clean else "FAILED",
        "deleted": del_counts,
        "leftovers": leftovers,
        "endpoint_404s": endpoint_404s,
        "cleanup_errors": cleanup_errors,
        "all_leftovers_zero": all_leftovers_zero,
        "all_endpoints_404": all_endpoints_404,
        "tracked_case_ids": sorted(validated_owned_case_ids),
        "unowned_preserved_cases": sorted(unowned_preserved_cases),
        "unverified_missing_cases": sorted(unverified_missing_cases),
        "owned_claim_event_ids": owned_claim_event_ids,
        "owned_dispatch_ids": owned_dispatch_ids,
        "durable_lineage": current_lineage,
    }
    print(f"      Cleanup status: {report['status']}. Leftovers: {leftovers}. Errors: {cleanup_errors}")
    return report


async def run_acceptance(
    mongo_url: str,
    admin_pass: str,
    artifact_dir: Optional[Path] = None,
    preflight_runner: Any = None,
    headless: bool = True,
) -> Dict[str, Any]:
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
        # Note: Privileged secret derivation prohibited per audit; delivered OTP verification requires external mailbox access.
        evidence["stages"]["trainer_claim_verification"] = (
            "NOT_VERIFIED (operator OTP or provider mailbox receipt required; privileged secret derivation removed per audit)"
        )
        evidence["stages"]["trainer_capabilities_prefill"] = "SKIPPED (requires verified session)"
        evidence["stages"]["trainer_session_renewal"] = "SKIPPED (requires verified session)"
        evidence["stages"]["trainer_catchment_confirmation"] = "SKIPPED (requires verified session)"
        print("      - Notice: Trainer claim verification marked NOT_VERIFIED (external provider mailbox receipt required; privileged derivation prohibited).")

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
            from playwright.async_api import async_playwright

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
                if m:
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
            artifact_dir=artifact_dir,
            headless=args.headless,
        ))
        print("\n=== ACCEPTANCE EVIDENCE ===")
        print(json.dumps(evidence, indent=2))
        return 0
    except Exception as e:
        print(f"\n[!] ACCEPTANCE FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
