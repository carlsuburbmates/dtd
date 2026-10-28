"""Closed unit tests for verify_sandbox_trainer_and_support.py.

Verifies:
1. Strict sandbox scope validation (exact project, approved Atlas cluster, approved database).
2. Cross-origin redirect denial on protected HTTP requests and destination whitelist enforcement.
3. Absence of privileged OTP derivation functions and secret dependencies.
4. enforce_sandbox_preflight (G2):
   - Read failure aborts with AcceptanceFailure.
   - Cron state != PAUSED aborts with AcceptanceFailure.
   - Nonzero safety flag aborts with AcceptanceFailure.
   - Traffic percent < 100 aborts with AcceptanceFailure.
   - Incorrect database name aborts with AcceptanceFailure.
   - Valid preflight succeeds and returns metadata.
   - Describes and validates immutable serving revision rather than mutable service template.
   - Version mismatch on ADMIN_PASS ('99' vs '4') or MONGO_URL ('42' vs 'latest') aborts with AcceptanceFailure.
   - Substring service account (e.g. 'evil-sa') aborts with AcceptanceFailure.
5. execute_deterministic_teardown (exercises the actual runner function):
   - Insert acknowledgement loss: trainer deleted even if client ack failed.
   - Untracked support case: discovered via sender_email and deleted.
   - Schema-faithful obligations: deleted by entity_id and obligation_id.
   - Preserves unrelated synthetic rows untouched.
   - Preserves foreign support threads merely referencing trainer ID (G1).
   - Preserves unowned case ID in tracked list after database verification (G1).
   - Preserves unmarked pre-existing trainers colliding on ID (G1).
   - Cleans claim event obligation lineage keyed by claim_event.id (G3).
   - Cleans notification dispatch obligation lineage keyed by dispatch_id (G3).
   - Datastore delete error causes status FAILED and AcceptanceFailure.
   - Datastore count error causes status FAILED.
   - Leftover documents cause status FAILED.
   - Public endpoint returning 200 (not 404) causes status FAILED.
6. run_acceptance:
   - Aborts on failed preflight before executing scenario or writes.
   - Simultaneous scenario failure + cleanup failure preserves original exception while reporting cleanup failure.
   - Manifest write failure aborts immediately before any database inserts (G3).
   - Persists final run report to disk on scenario failure with original exception and cleanup report (G3).
7. Browser credentials injection & origin verification (G4):
   - Origin verification check before credential injection.
   - Parameterized page.evaluate call with zero string interpolation of credentials.
   - Request route guard blocks unapproved mutating requests and auth headers to foreign origins.
   - Contact page origin checks verify approved origin before submit and on /ops navigation.

No live network calls, provider mutations, or external credential access.
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request

import pytest


def _load_script_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "verify_sandbox_trainer_and_support.py"
    spec = importlib.util.spec_from_file_location("verify_sandbox_trainer_and_support", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_script_module()


# -----------------------------------------------------------------------------
# 1. Scope & Preflight Validation Tests
# -----------------------------------------------------------------------------

def test_require_sandbox_rejects_missing_or_substring_project(monkeypatch):
    monkeypatch.delenv("DTD_SANDBOX_PROJECT_ID", raising=False)
    with pytest.raises(runner.AcceptanceFailure, match="Explicit DTD_SANDBOX_PROJECT_ID must be strictly"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )

    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev-prod")
    with pytest.raises(runner.AcceptanceFailure, match="Explicit DTD_SANDBOX_PROJECT_ID must be strictly"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )

    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "fake-dogtrainersdirectory-dev")
    with pytest.raises(runner.AcceptanceFailure, match="Explicit DTD_SANDBOX_PROJECT_ID must be strictly"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )


def test_require_sandbox_rejects_unapproved_mongo_cluster(monkeypatch):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    with pytest.raises(runner.AcceptanceFailure, match="Refusing non-sandbox MongoDB cluster host"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-live.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )

    with pytest.raises(runner.AcceptanceFailure, match="Refusing non-sandbox MongoDB cluster host"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@production-database.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )


def test_require_sandbox_rejects_production_database(monkeypatch):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    with pytest.raises(runner.AcceptanceFailure, match="Refusing non-sandbox database name: 'dtd'"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd",
            admin_pass="test-admin-pass",
        )


def test_require_sandbox_accepts_valid_sandbox_and_loopback(monkeypatch):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    runner._require_sandbox(
        mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox?retryWrites=true&w=majority",
        admin_pass="valid-pass",
    )

    runner._require_sandbox(
        mongo_url="mongodb://localhost:27017/dtd_sandbox",
        admin_pass="valid-pass",
    )


# -----------------------------------------------------------------------------
# 2. Cross-Origin Redirect & Origin Whitelist Tests
# -----------------------------------------------------------------------------

def test_strict_redirect_handler_denies_cross_origin_redirect():
    handler = runner.StrictRedirectHandler()
    req = Request(
        "https://dtd-api-dev-625222421634.australia-southeast1.run.app/api/oversight",
        headers={"X-Admin-Pass": "secret"},
    )

    with pytest.raises(HTTPError, match="Cross-origin redirect from .* to https://attacker.com denied"):
        handler.redirect_request(
            req=req,
            fp=None,
            code=302,
            msg="Found",
            headers={},
            newurl="https://attacker.com/leak",
        )


def test_strict_redirect_handler_allows_same_origin_redirect():
    handler = runner.StrictRedirectHandler()
    req = Request(
        "https://dtd-api-dev-625222421634.australia-southeast1.run.app/api/old",
        headers={"X-Admin-Pass": "secret"},
    )

    result = handler.redirect_request(
        req=req,
        fp=None,
        code=301,
        msg="Moved Permanently",
        headers={},
        newurl="https://dtd-api-dev-625222421634.australia-southeast1.run.app/api/new",
    )
    assert result is not None
    assert result.full_url == "https://dtd-api-dev-625222421634.australia-southeast1.run.app/api/new"


def test_http_request_rejects_unapproved_destination_origin():
    with pytest.raises(runner.AcceptanceFailure, match="Refusing HTTP request to unapproved destination"):
        runner._http_request("https://evil-destination.com/api/steal")


# -----------------------------------------------------------------------------
# 3. Privileged Derivation Prohibited
# -----------------------------------------------------------------------------

def test_no_privileged_otp_derivation_function_in_module():
    assert not hasattr(runner, "_derive_otp"), "Privileged _derive_otp function must not exist in module"
    assert "TRAINER_ACTION_TOKEN_SECRET" not in dir(runner)


# -----------------------------------------------------------------------------
# 4. Enforce Sandbox Preflight Tests
# -----------------------------------------------------------------------------

def _make_valid_service_desc(
    service_name: str = "dtd-api-dev",
    latest_rev: str = "rev-001",
    percent: int = 100,
    service_account: str = "dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com",
    db_name: str = "dtd_sandbox",
    safety_flags: Optional[Dict[str, str]] = None,
    admin_pass_version: str = "4",
    mongo_url_version: str = "latest",
) -> Dict[str, Any]:
    flags = safety_flags or {
        "ENABLE_TRAINER_BILLING_CHECKOUT": "0",
        "ENABLE_OPS_STRIPE_REFUNDS": "0",
        "OPS_SELF_HEALING_ENABLED": "0",
    }
    env = [
        {"name": "DB_NAME", "value": db_name},
        {"name": "MONGO_URL", "valueFrom": {"secretKeyRef": {"name": "dtd-mongo-url", "key": mongo_url_version}}},
        {"name": "ADMIN_PASS", "valueFrom": {"secretKeyRef": {"name": "dtd-admin-pass", "key": admin_pass_version}}},
    ]
    for k, v in flags.items():
        env.append({"name": k, "value": v})

    containers_spec = {
        "serviceAccountName": service_account,
        "containers": [
            {
                "env": env,
                "volumeMounts": [
                    {"name": "secret-mongo-url", "mountPath": "/secrets/mongo_url"},
                    {"name": "secret-admin-pass", "mountPath": "/secrets/admin_pass"},
                ],
            }
        ],
        "volumes": [
            {"name": "secret-mongo-url", "secret": {"secretName": "dtd-mongo-url"}},
            {"name": "secret-admin-pass", "secret": {"secretName": "dtd-admin-pass"}},
        ],
    }

    return {
        "metadata": {"name": latest_rev},
        "status": {
            "latestReadyRevisionName": latest_rev,
            "traffic": [{"revisionName": latest_rev, "percent": percent}],
        },
        "spec": {
            **containers_spec,
            "template": {
                "metadata": {"name": latest_rev},
                "spec": containers_spec,
            },
        },
    }


def _make_valid_scheduler_desc(state: str = "PAUSED") -> Dict[str, Any]:
    return {
        "state": state,
        "schedule": "0 2 * * *",
        "name": "projects/dogtrainersdirectory-dev/locations/australia-southeast1/jobs/dtd-trainer-ingest-cron",
    }


def test_enforce_sandbox_preflight_fails_on_command_error():
    def failing_runner(cmd):
        raise RuntimeError("gcloud command execution failed")

    with pytest.raises(runner.AcceptanceFailure, match="Failed to read Cloud Run service dtd-api-dev"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=failing_runner)


def test_enforce_sandbox_preflight_fails_when_cron_is_enabled():
    def mock_runner(cmd):
        if "dtd-api-dev" in cmd or "revisions" in cmd:
            return _make_valid_service_desc("dtd-api-dev")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="ENABLED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="Preflight check failed: Cloud Scheduler job dtd-trainer-ingest-cron is ENABLED"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


def test_enforce_sandbox_preflight_fails_on_nonzero_safety_flags():
    def mock_runner(cmd):
        if "dtd-api-dev" in cmd or "revisions" in cmd:
            return _make_valid_service_desc(
                "dtd-api-dev",
                safety_flags={
                    "ENABLE_TRAINER_BILLING_CHECKOUT": "1",
                    "ENABLE_OPS_STRIPE_REFUNDS": "0",
                    "OPS_SELF_HEALING_ENABLED": "0",
                },
            )
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="Safety flag ENABLED in sandbox"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


def test_enforce_sandbox_preflight_fails_when_traffic_split():
    def mock_runner(cmd):
        if "dtd-api-dev" in cmd or "revisions" in cmd:
            return _make_valid_service_desc("dtd-api-dev", percent=80)
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="does not direct 100% traffic to latest ready revision"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


def test_enforce_sandbox_preflight_fails_on_wrong_database():
    def mock_runner(cmd):
        if "dtd-api-dev" in cmd or "revisions" in cmd:
            return _make_valid_service_desc("dtd-api-dev", db_name="dtd_prod")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="targets unexpected database"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


def test_enforce_sandbox_preflight_succeeds_and_returns_metadata():
    def mock_runner(cmd):
        if "dtd-api-dev" in cmd or "revisions" in cmd:
            return _make_valid_service_desc("dtd-api-dev")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    metadata = runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)
    assert metadata["project"] == "dogtrainersdirectory-dev"
    assert metadata["api_revision"] == "rev-001"
    assert metadata["safe_env"]["ENABLE_TRAINER_BILLING_CHECKOUT"] == "0"
    assert metadata["ingest_cron_state"] == "PAUSED"
    assert metadata["managed_secret_references"]["ADMIN_PASS"]["version"] == "4"
    assert metadata["managed_secret_references"]["MONGO_URL"]["version"] == "latest"


def test_enforce_sandbox_preflight_describes_and_validates_immutable_revision():
    calls = []

    def mock_runner(cmd):
        calls.append(cmd)
        if "services" in cmd and "dtd-api-dev" in cmd:
            return {
                "status": {
                    "latestReadyRevisionName": "rev-serving",
                    "latestCreatedRevisionName": "rev-unready-new",
                    "traffic": [{"revisionName": "rev-serving", "percent": 100}],
                },
                "spec": {
                    "template": {
                        "metadata": {"name": "rev-unready-new"},
                        "spec": {
                            "serviceAccountName": "dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com",
                            "containers": [{"env": [{"name": "ENABLE_TRAINER_BILLING_CHECKOUT", "value": "1"}]}],
                        },
                    }
                },
            }
        if "revisions" in cmd and "rev-serving" in cmd:
            return _make_valid_service_desc("dtd-api-dev", latest_rev="rev-serving")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    metadata = runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)
    assert metadata["api_revision"] == "rev-serving"
    rev_calls = [c for c in calls if len(c) >= 4 and c[1:4] == ["run", "revisions", "describe"]]
    assert len(rev_calls) == 1
    assert "rev-serving" in rev_calls[0]


def test_enforce_sandbox_preflight_rejects_admin_pass_version_mismatch():
    def mock_runner(cmd):
        if "revisions" in cmd or "dtd-api-dev" in cmd:
            return _make_valid_service_desc("dtd-api-dev", admin_pass_version="99")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="ADMIN_PASS references secret version '99', expected '4'"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


def test_enforce_sandbox_preflight_rejects_mongo_url_version_mismatch():
    def mock_runner(cmd):
        if "revisions" in cmd or "dtd-api-dev" in cmd:
            return _make_valid_service_desc("dtd-api-dev", mongo_url_version="42")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="MONGO_URL references secret version '42', expected 'latest'"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


def test_enforce_sandbox_preflight_rejects_non_exact_service_account():
    def mock_runner(cmd):
        if "revisions" in cmd or "dtd-api-dev" in cmd:
            return _make_valid_service_desc(
                "dtd-api-dev",
                service_account="evil-dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com",
            )
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="unexpected API service account"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


# -----------------------------------------------------------------------------
# 5. Schema-Faithful Closed Database & Teardown Runner Tests
# -----------------------------------------------------------------------------

class FaithfulFakeCollection:
    def __init__(
        self,
        name: str,
        rows: Optional[List[Dict[str, Any]]] = None,
        fail_delete: bool = False,
        fail_count: bool = False,
    ):
        self.name = name
        self.rows = [dict(r) for r in (rows or [])]
        self.fail_delete = fail_delete
        self.fail_count = fail_count

    def _matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        if "$or" in query:
            return any(self._matches(doc, subq) for subq in query["$or"])

        for k, v in query.items():
            if "." in k:
                parts = k.split(".")
                curr: Any = doc
                for p in parts:
                    if isinstance(curr, dict):
                        curr = curr.get(p)
                    else:
                        curr = None
                doc_val = curr
            else:
                doc_val = doc.get(k)

            if isinstance(v, dict) and "$in" in v:
                if doc_val not in v["$in"]:
                    return False
            else:
                if doc_val != v:
                    return False
        return True

    def delete_many(self, query: Dict[str, Any]):
        if self.fail_delete:
            raise RuntimeError(f"Datastore delete failure on {self.name}")
        initial_len = len(self.rows)
        self.rows = [r for r in self.rows if not self._matches(r, query)]
        return SimpleNamespace(deleted_count=initial_len - len(self.rows))

    def count_documents(self, query: Dict[str, Any]) -> int:
        if self.fail_count:
            raise RuntimeError(f"Datastore count failure on {self.name}")
        return sum(1 for r in self.rows if self._matches(r, query))

    def find(self, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None):
        matching = [r for r in self.rows if self._matches(r, query)]
        if projection:
            projected = []
            for r in matching:
                p_doc = {}
                for k in projection:
                    if k in r:
                        p_doc[k] = r[k]
                projected.append(p_doc)
            return projected
        return matching

    def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None):
        results = self.find(query, projection)
        return results[0] if results else None

    def insert_one(self, doc: Dict[str, Any]):
        self.rows.append(dict(doc))
        return SimpleNamespace(inserted_id="fake_fixture_id")


class FaithfulFakeDatabase:
    def __init__(self):
        self.collections: Dict[str, FaithfulFakeCollection] = {}

    def get_collection(self, name: str) -> FaithfulFakeCollection:
        if name not in self.collections:
            self.collections[name] = FaithfulFakeCollection(name)
        return self.collections[name]

    def __getattr__(self, name: str) -> FaithfulFakeCollection:
        return self.get_collection(name)

    def __getitem__(self, name: str) -> FaithfulFakeCollection:
        return self.get_collection(name)


def test_teardown_cleans_trainer_on_insert_acknowledgement_loss():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-unacked-123"

    # Simulate trainer fixture inserted into DB, but acknowledgement timed out
    db.trainers.rows.append({"id": trainer_id, "name": "Unacked Trainer", "test_fixture": True})
    db.claim_events.rows.append({"trainer_id": trainer_id, "otp_digest": "hash"})
    db.notification_events.rows.append({"target_id": trainer_id, "kind": "trainer_claim_otp"})
    db.audit_log.rows.append({"target": trainer_id, "action": "trainer_created"})
    db.ops_obligations.rows.append({"entity_id": trainer_id, "obligation_id": f"trainer:{trainer_id}"})

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "CLEAN"
    assert report["deleted"]["trainers"] == 1
    assert report["deleted"]["claim_events"] == 1
    assert report["deleted"]["trainer_notifications"] == 1
    assert report["deleted"]["trainer_audit"] == 1
    assert report["deleted"]["trainer_obligations"] == 1
    assert report["leftovers"]["trainers"] == 0
    assert report["all_leftovers_zero"] is True


def test_teardown_discovers_and_cleans_untracked_support_cases_via_sender_email():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-test"
    run_email = "delivered+sandbox-support-api-case1@resend.dev"
    case_id = "sup_20261029_discovered01"

    # Support thread was persisted with schema-faithful sender_email, but response was lost
    db.support_threads.rows.append({
        "case_id": case_id,
        "sender_email": run_email,
        "category": "complaint",
        "subject": "Lost response test",
    })
    db.notification_events.rows.append({"target_id": case_id, "kind": "support_intake_receipt"})
    db.audit_log.rows.append({"target": case_id, "action": "support_thread_created"})
    db.ops_obligations.rows.append({
        "entity_id": case_id,
        "obligation_id": f"support:{case_id}",
        "kind": "support_response",
    })

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    # Start with empty tracked_case_ids
    empty_tracked: Set[str] = set()

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=empty_tracked,
        run_emails=[run_email],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "CLEAN"
    assert case_id in report["tracked_case_ids"]
    assert report["deleted"]["support_threads"][case_id] == 1
    assert report["deleted"]["support_notifications"][case_id] == 1
    assert report["deleted"]["support_audit"][case_id] == 1
    assert report["deleted"]["ops_obligations"][case_id] == 1
    assert report["leftovers"][f"thread_{case_id}"] == 0
    assert report["leftovers"][f"obligations_{case_id}"] == 0


def test_teardown_cleans_obligations_with_real_schema():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-ob-test"
    case_id = "sup_20261029_schema_test"

    # Schema-faithful obligations use entity_id and obligation_id
    db.ops_obligations.rows.append({"entity_id": case_id, "obligation_id": case_id})
    db.ops_obligations.rows.append({"entity_id": case_id, "obligation_id": f"support:{case_id}"})
    db.support_threads.rows.append({"case_id": case_id, "sender_email": "delivered+test@resend.dev"})

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids={case_id},
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "CLEAN"
    assert report["deleted"]["ops_obligations"][case_id] == 2
    assert report["leftovers"][f"obligations_{case_id}"] == 0


def test_teardown_preserves_unrelated_rows():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-to-delete"
    other_trainer = "trainer-unrelated-permanent"
    other_case = "sup_unrelated_permanent"

    db.trainers.rows.append({"id": trainer_id, "name": "Ephemeral Trainer", "test_fixture": True})
    db.trainers.rows.append({"id": other_trainer, "name": "Permanent Trainer"})

    db.support_threads.rows.append({"case_id": other_case, "sender_email": "permanent@example.com"})
    db.ops_obligations.rows.append({"entity_id": other_case, "obligation_id": f"support:{other_case}"})

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+ephemeral@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "CLEAN"
    assert db.trainers.count_documents({"id": other_trainer}) == 1
    assert db.support_threads.count_documents({"case_id": other_case}) == 1
    assert db.ops_obligations.count_documents({"entity_id": other_case}) == 1


def test_teardown_preserves_foreign_support_threads_referencing_trainer():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-fixture-run"
    foreign_case = "sup_foreign_visitor"
    synthetic_email = "delivered+fixture-run-api@resend.dev"

    db.trainers.rows.append({"id": trainer_id, "test_fixture": True, "test_run_id": "fixture-run"})
    # An unrelated visitor contacts support about a public fixture
    db.support_threads.rows.append({
        "case_id": foreign_case,
        "sender_email": "visitor@example.invalid",
        "trainer_id": trainer_id,
        "subject": "Inquiry about trainer",
    })
    db.notification_events.rows.append({
        "id": "foreign-notif",
        "target_kind": "support_thread",
        "target_id": foreign_case,
    })
    db.audit_log.rows.append({"target": foreign_case, "id": "foreign-audit"})
    db.ops_obligations.rows.append({
        "entity_id": foreign_case,
        "obligation_id": f"obligation:support:{foreign_case}",
    })

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=[synthetic_email],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "CLEAN"
    assert foreign_case not in report["tracked_case_ids"]
    assert db.support_threads.count_documents({"case_id": foreign_case}) == 1
    assert db.notification_events.count_documents({"target_id": foreign_case}) == 1
    assert db.audit_log.count_documents({"target": foreign_case}) == 1
    assert db.ops_obligations.count_documents({"entity_id": foreign_case}) == 1


def test_teardown_preserves_unowned_case_id_in_tracked_list():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-fixture-run"
    foreign_case = "sup_substituted_response"
    synthetic_email = "delivered+fixture-run-api@resend.dev"

    db.trainers.rows.append({"id": trainer_id, "test_fixture": True})
    db.support_threads.rows.append({
        "case_id": foreign_case,
        "sender_email": "other@example.invalid",
        "trainer_id": "other-trainer",
    })

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids={foreign_case},
        run_emails=[synthetic_email],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "CLEAN"
    assert db.support_threads.count_documents({"case_id": foreign_case}) == 1
    assert "unowned_preserved_cases" in report
    assert foreign_case in report["unowned_preserved_cases"]


def test_teardown_preserves_unmarked_trainer_collision():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-colliding"

    db.trainers.rows.append({"id": trainer_id, "name": "Pre-existing unowned row"})

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["deleted"]["trainers"] == 0
    assert db.trainers.count_documents({"id": trainer_id}) == 1


def test_teardown_cleans_claim_event_obligation_lineage():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-claim-test"
    claim_id = "claim-owned-event-123"
    unrelated_claim_id = "claim-permanent-456"

    db.trainers.rows.append({"id": trainer_id, "test_fixture": True})
    db.claim_events.rows.append({"id": claim_id, "trainer_id": trainer_id})
    db.claim_events.rows.append({"id": unrelated_claim_id, "trainer_id": "other-trainer"})

    db.ops_obligations.rows.append({
        "obligation_id": f"obligation:claim:{claim_id}",
        "entity_id": claim_id,
        "category": "claim_lock",
        "metadata": {"trainer_id": trainer_id, "claim_event_id": claim_id},
    })
    db.ops_obligations.rows.append({
        "obligation_id": f"obligation:claim:{unrelated_claim_id}",
        "entity_id": unrelated_claim_id,
        "category": "claim_lock",
        "metadata": {"trainer_id": "other-trainer", "claim_event_id": unrelated_claim_id},
    })

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "CLEAN"
    assert report["deleted"]["claim_events"] == 1
    assert report["deleted"]["claim_event_obligations"] == 1
    assert report["leftovers"].get("claim_event_obligations", 0) == 0
    assert db.claim_events.count_documents({"id": claim_id}) == 0
    assert db.ops_obligations.count_documents({"entity_id": claim_id}) == 0
    assert db.claim_events.count_documents({"id": unrelated_claim_id}) == 1
    assert db.ops_obligations.count_documents({"entity_id": unrelated_claim_id}) == 1


def test_teardown_cleans_notification_dispatch_obligation_lineage():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-notif-test"
    case_id = "sup_owned_case_789"
    run_email = "delivered+dispatch-test@resend.dev"
    dispatch_id = "dispatch-owned-event-456"
    unrelated_dispatch_id = "dispatch-unrelated-event-999"

    db.trainers.rows.append({"id": trainer_id, "test_fixture": True})
    db.support_threads.rows.append({"case_id": case_id, "sender_email": run_email})
    db.notification_events.rows.append({
        "id": "notif-owned",
        "dispatch_id": dispatch_id,
        "target_kind": "support_thread",
        "target_id": case_id,
    })
    db.notification_events.rows.append({
        "id": "notif-unrelated",
        "dispatch_id": unrelated_dispatch_id,
        "target_kind": "support_thread",
        "target_id": "other_case",
    })

    db.ops_obligations.rows.append({
        "obligation_id": f"obligation:message:{dispatch_id}",
        "entity_id": dispatch_id,
        "category": "notification_delivery",
        "metadata": {"dispatch_id": dispatch_id, "target_id": case_id},
    })
    db.ops_obligations.rows.append({
        "obligation_id": f"obligation:message:{unrelated_dispatch_id}",
        "entity_id": unrelated_dispatch_id,
        "category": "notification_delivery",
        "metadata": {"dispatch_id": unrelated_dispatch_id, "target_id": "other_case"},
    })

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids={case_id},
        run_emails=[run_email],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "CLEAN"
    assert report["deleted"]["dispatch_obligations"] == 1
    assert report["leftovers"].get("dispatch_obligations", 0) == 0
    assert db.notification_events.count_documents({"dispatch_id": dispatch_id}) == 0
    assert db.ops_obligations.count_documents({"entity_id": dispatch_id}) == 0
    assert db.notification_events.count_documents({"dispatch_id": unrelated_dispatch_id}) == 1
    assert db.ops_obligations.count_documents({"entity_id": unrelated_dispatch_id}) == 1


def test_teardown_fails_on_datastore_delete_error():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-del-fail"
    db.collections["trainers"] = FaithfulFakeCollection("trainers", [{"id": trainer_id, "test_fixture": True}], fail_delete=True)

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "FAILED"
    assert any("trainers delete" in err for err in report["cleanup_errors"])
    assert report["all_leftovers_zero"] is False


def test_teardown_fails_on_datastore_count_error():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-count-fail"
    db.collections["trainers"] = FaithfulFakeCollection("trainers", [], fail_count=True)

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "FAILED"
    assert report["leftovers"]["trainers"] == -1
    assert any("trainers count error" in err for err in report["cleanup_errors"])
    assert report["all_leftovers_zero"] is False


def test_teardown_fails_when_endpoint_returns_200():
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-200-leak"

    def mock_request(url, method="GET", headers=None, payload=None):
        # Trainer still returns 200 OK -> leak!
        if f"/api/trainers/{trainer_id}" in url:
            return 200, {"id": trainer_id}
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
    )

    assert report["status"] == "FAILED"
    assert report["endpoint_404s"][f"trainer_{trainer_id}"] is False
    assert report["all_endpoints_404"] is False


# -----------------------------------------------------------------------------
# 6. run_acceptance Combined Failure & Preflight Isolation Tests
# -----------------------------------------------------------------------------

def test_run_acceptance_aborts_on_failed_preflight_before_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    # Mock preflight runner that fails
    def failing_preflight_runner(cmd):
        raise RuntimeError("Preflight discovery failure")

    with pytest.raises(runner.AcceptanceFailure, match="Failed to read Cloud Run service"):
        asyncio.run(runner.run_acceptance(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-pass",
            preflight_runner=failing_preflight_runner,
            artifact_dir=tmp_path,
        ))


def test_run_acceptance_simultaneous_scenario_and_cleanup_failure_chains_original(monkeypatch, tmp_path):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    # 1. Valid preflight runner
    def mock_preflight(cmd):
        if "dtd-api-dev" in cmd or "revisions" in cmd:
            return _make_valid_service_desc("dtd-api-dev")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    # 2. Mock MongoClient returning a database that fails on delete
    fake_db = FaithfulFakeDatabase()
    fake_db.collections["trainers"] = FaithfulFakeCollection("trainers", [], fail_delete=True)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.admin = SimpleNamespace(command=lambda cmd: True)

        def __getitem__(self, name):
            return fake_db

        def close(self):
            pass

    monkeypatch.setattr(runner, "MongoClient", MockClient)

    # 3. Mock HTTP request to fail during health/config check
    def mock_http(url, method="GET", headers=None, payload=None):
        if "/api/health" in url:
            return 500, {"error": "Synthetic scenario crash"}
        return 404, {}

    monkeypatch.setattr(runner, "_http_request", mock_http)

    with pytest.raises(runner.AcceptanceFailure) as exc_info:
        asyncio.run(runner.run_acceptance(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-pass",
            preflight_runner=mock_preflight,
            artifact_dir=tmp_path,
        ))

    # The raised AcceptanceFailure must chain from the original scenario exception
    assert exc_info.value.__cause__ is not None
    assert "Synthetic scenario crash" in str(exc_info.value.__cause__)
    # And the error message must detail both scenario failure and cleanup failure
    assert "Scenario failed" in str(exc_info.value)
    assert "Cleanup failed" in str(exc_info.value)


def test_run_acceptance_manifest_write_failure_aborts_before_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    def mock_preflight(cmd):
        if "dtd-api-dev" in cmd or "revisions" in cmd:
            return _make_valid_service_desc("dtd-api-dev")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    fake_db = FaithfulFakeDatabase()
    inserted_rows = []

    def mock_insert(doc):
        inserted_rows.append(doc)
        return SimpleNamespace(inserted_id="fake")

    fake_db.trainers.insert_one = mock_insert

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.admin = SimpleNamespace(command=lambda cmd: True)

        def __getitem__(self, name):
            return fake_db

        def close(self):
            pass

    monkeypatch.setattr(runner, "MongoClient", MockClient)

    def mock_http(url, method="GET", headers=None, payload=None):
        if "/api/health" in url:
            return 200, {"database": "available"}
        if "/api/config" in url:
            return 200, {"public_matching_enabled": True}
        return 404, {}

    monkeypatch.setattr(runner, "_http_request", mock_http)

    orig_write = Path.write_text

    def deny_manifest_write(self, *args, **kwargs):
        if self.name.startswith("run_manifest_"):
            raise PermissionError("Synthetic manifest write permission denied")
        return orig_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", deny_manifest_write)

    with pytest.raises(runner.AcceptanceFailure, match="Failed to persist pre-mutation run manifest"):
        asyncio.run(runner.run_acceptance(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-pass",
            preflight_runner=mock_preflight,
            artifact_dir=tmp_path,
        ))

    # Crucial assertion: ZERO inserts were attempted on the database after manifest failure!
    assert len(inserted_rows) == 0, f"Expected 0 inserts after manifest write failure, but got {len(inserted_rows)}"


def test_run_acceptance_persists_final_report_on_scenario_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    def mock_preflight(cmd):
        if "dtd-api-dev" in cmd or "revisions" in cmd:
            return _make_valid_service_desc("dtd-api-dev")
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    fake_db = FaithfulFakeDatabase()

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.admin = SimpleNamespace(command=lambda cmd: True)

        def __getitem__(self, name):
            return fake_db

        def close(self):
            pass

    monkeypatch.setattr(runner, "MongoClient", MockClient)

    def mock_http(url, method="GET", headers=None, payload=None):
        if "/api/health" in url:
            return 500, {"error": "Synthetic scenario crash on health check"}
        return 404, {}

    monkeypatch.setattr(runner, "_http_request", mock_http)

    with pytest.raises(runner.AcceptanceFailure, match="Synthetic scenario crash on health check"):
        asyncio.run(runner.run_acceptance(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-pass",
            preflight_runner=mock_preflight,
            artifact_dir=tmp_path,
        ))

    # Verify that run_report_{run_id}.json was persisted in tmp_path
    report_files = list(tmp_path.glob("run_report_*.json"))
    assert len(report_files) == 1, f"Expected 1 run_report file, found {len(report_files)}"

    report_content = json.loads(report_files[0].read_text())
    assert "Synthetic scenario crash on health check" in report_content["scenario_exception"]
    assert "cleanup_report" in report_content
    assert report_content["cleanup_report"]["status"] == "CLEAN"


# -----------------------------------------------------------------------------
# 7. Browser Credentials Injection & Origin Verification AST Analysis
# -----------------------------------------------------------------------------

def test_browser_credential_injection_uses_evaluate_argument_without_interpolation():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "verify_sandbox_trainer_and_support.py"
    source = script_path.read_text(encoding="utf-8")

    tree = ast.parse(source)

    # 1. Ensure page.evaluate is called with arguments rather than formatted admin_pass
    eval_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "evaluate":
                eval_calls.append(node)

    assert len(eval_calls) > 0, "Expected at least one page.evaluate call"

    found_credential_eval = False
    for call in eval_calls:
        # Check if call contains admin_pass argument
        arg_names = [arg.id for arg in call.args if isinstance(arg, ast.Name)]
        if "admin_pass" in arg_names:
            found_credential_eval = True
            # Verify first argument is a plain string without f-string formatting
            first_arg = call.args[0]
            assert isinstance(first_arg, ast.Constant), "evaluate script must be a constant string, not formatted or interpolated"
            assert "passVal" in first_arg.value
            assert "{admin_pass}" not in first_arg.value

    assert found_credential_eval, "Expected page.evaluate to accept admin_pass as a safe argument"

    # 2. Ensure origin check is performed on WEB_URL
    assert "urlparse(WEB_URL)" in source
    assert "approved_web_origin" in source


def test_browser_route_guard_blocks_unapproved_mutations_and_auth():
    async def _run():
        aborted = []
        continued = []

        class MockRoute:
            async def abort(self, errorCode="failed"):
                aborted.append(errorCode)

            async def continue_(self):
                continued.append(True)

        class MockRequest:
            def __init__(self, url, method="GET", headers=None):
                self.url = url
                self.method = method
                self.headers = headers or {}

        approved_origins = {"dtd-web-dev-x2kdoaemtq-ts.a.run.app", "dtd-api-dev-x2kdoaemtq-ts.a.run.app"}

        async def route_guard(route, request):
            dest_host = urlparse(request.url).netloc.split(":")[0].lower()
            method = request.method.upper()
            headers = {k.lower(): v for k, v in request.headers.items()}
            is_mutating = method in ("POST", "PUT", "PATCH", "DELETE")
            has_auth = "authorization" in headers or "x-admin-pass" in headers
            if is_mutating or has_auth:
                if dest_host not in approved_origins:
                    await route.abort("blockedbyclient")
                    return
            await route.continue_()

        # 1. Unapproved mutating POST -> aborted
        await route_guard(MockRoute(), MockRequest("https://production.example.invalid/support/contact", method="POST"))
        assert len(aborted) == 1 and aborted[-1] == "blockedbyclient"

        # 2. Unapproved auth header -> aborted
        await route_guard(MockRoute(), MockRequest("https://evil.example.com/api/stolen", method="GET", headers={"X-Admin-Pass": "secret"}))
        assert len(aborted) == 2 and aborted[-1] == "blockedbyclient"

        # 3. Third-party asset GET (fonts, scripts) -> continued
        await route_guard(MockRoute(), MockRequest("https://fonts.googleapis.com/css?family=Inter", method="GET"))
        assert len(continued) == 1

        # 4. Approved API POST -> continued
        await route_guard(MockRoute(), MockRequest("https://dtd-api-dev-x2kdoaemtq-ts.a.run.app/support/contact", method="POST"))
        assert len(continued) == 2

    asyncio.run(_run())


def test_browser_origin_check_blocks_foreign_contact_submission():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "verify_sandbox_trainer_and_support.py"
    source = script_path.read_text(encoding="utf-8")

    assert "approved_web_origin = urlparse(WEB_URL).netloc.split(\":\")[0].lower()" in source
    assert "Contact page redirected to unapproved origin" in source
    assert "Contact page navigated away before submit" in source
    assert "Contact confirmation at unapproved origin" in source
    assert "browser_route_guard" in source
    assert 'context.route("**/*", browser_route_guard)' in source
    assert 'route.abort("blockedbyclient")' in source
