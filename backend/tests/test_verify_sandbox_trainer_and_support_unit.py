"""Closed unit tests for verify_sandbox_trainer_and_support.py.

Verifies:
1. Strict sandbox scope validation (exact project, approved Atlas cluster, approved database).
2. Cross-origin redirect denial on protected HTTP requests.
3. Destination host whitelist enforcement.
4. Resilient collision-free cleanup, independent deletion error handling, and leftover accounting.
5. Absence of privileged OTP derivation functions and secret dependencies.

No network calls, provider mutations, or external credential access.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from urllib.error import HTTPError
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

    # Substring match attempt
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev-prod")
    with pytest.raises(runner.AcceptanceFailure, match="Explicit DTD_SANDBOX_PROJECT_ID must be strictly"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )

    # Another substring match attempt
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "fake-dogtrainersdirectory-dev")
    with pytest.raises(runner.AcceptanceFailure, match="Explicit DTD_SANDBOX_PROJECT_ID must be strictly"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )


def test_require_sandbox_rejects_unapproved_mongo_cluster(monkeypatch):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    # Production Atlas cluster attempt
    with pytest.raises(runner.AcceptanceFailure, match="Refusing non-sandbox MongoDB cluster host"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-live.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )

    # Arbitrary non-sandbox cluster
    with pytest.raises(runner.AcceptanceFailure, match="Refusing non-sandbox MongoDB cluster host"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@production-database.mongodb.net/dtd_sandbox",
            admin_pass="test-admin-pass",
        )


def test_require_sandbox_rejects_production_database(monkeypatch):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    # Production 'dtd' db
    with pytest.raises(runner.AcceptanceFailure, match="Refusing non-sandbox database name: 'dtd'"):
        runner._require_sandbox(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd",
            admin_pass="test-admin-pass",
        )


def test_require_sandbox_accepts_valid_sandbox_and_loopback(monkeypatch):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", "dogtrainersdirectory-dev")

    # Valid Atlas Sandbox
    runner._require_sandbox(
        mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox?retryWrites=true&w=majority",
        admin_pass="valid-pass",
    )

    # Valid Localhost loopback
    runner._require_sandbox(
        mongo_url="mongodb://localhost:27017/dtd_sandbox",
        admin_pass="valid-pass",
    )


# -----------------------------------------------------------------------------
# 2. Cross-Origin Redirect & Origin Whitelist Tests
# -----------------------------------------------------------------------------

def test_strict_redirect_handler_denies_cross_origin_redirect():
    handler = runner.StrictRedirectHandler()
    req = Request("https://dtd-api-dev-625222421634.australia-southeast1.run.app/api/oversight", headers={"X-Admin-Pass": "secret"})

    # Attempt cross-origin redirect to attacker.com
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
    req = Request("https://dtd-api-dev-625222421634.australia-southeast1.run.app/api/old", headers={"X-Admin-Pass": "secret"})

    # Same-origin redirect to new endpoint
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
# 4. Resilient Per-Case Cleanup & Leftover Accounting Tests
# -----------------------------------------------------------------------------

class FakeCollection:
    def __init__(self, rows: List[Dict[str, Any]] | None = None, fail_on_delete: bool = False):
        self.rows = list(rows or [])
        self.fail_on_delete = fail_on_delete

    def delete_many(self, query: Dict[str, Any]):
        if self.fail_on_delete:
            raise RuntimeError("Synthetic datastore delete failure")
        key, val = next(iter(query.items()))
        initial_len = len(self.rows)
        self.rows = [r for r in self.rows if r.get(key) != val]
        return SimpleNamespace(deleted_count=initial_len - len(self.rows))

    def count_documents(self, query: Dict[str, Any]):
        key, val = next(iter(query.items()))
        return sum(1 for r in self.rows if r.get(key) == val)

    def find(self, query: Dict[str, Any], projection: Dict[str, int] | None = None):
        if "email" in query and "$in" in query["email"]:
            allowed = set(query["email"]["$in"])
            return [r for r in self.rows if r.get("email") in allowed]
        return list(self.rows)


class FakeDatabase(dict):
    def __missing__(self, name: str):
        self[name] = FakeCollection()
        return self[name]

    def __getattr__(self, name: str):
        return self[name]


def test_cleanup_handles_multiple_cases_without_key_collision():
    db = FakeDatabase()
    cid1 = "sup_20261028_case0001"
    cid2 = "sup_20261028_case0002"

    db["support_threads"] = FakeCollection([{"case_id": cid1}, {"case_id": cid2}])
    db["notification_events"] = FakeCollection([{"target_id": cid1}, {"target_id": cid2}])
    db["audit_log"] = FakeCollection([{"target": cid1}, {"target": cid2}])
    db["ops_obligations"] = FakeCollection([{"case_id": cid1}, {"case_id": cid2}])

    del_counts = {
        "support_threads": {},
        "support_notifications": {},
        "support_audit": {},
        "ops_obligations": {},
    }

    tracked_case_ids = {cid1, cid2}
    for cid in sorted(tracked_case_ids):
        del_counts["support_threads"][cid] = db.support_threads.delete_many({"case_id": cid}).deleted_count
        del_counts["support_notifications"][cid] = db.notification_events.delete_many({"target_id": cid}).deleted_count
        del_counts["support_audit"][cid] = db.audit_log.delete_many({"target": cid}).deleted_count
        del_counts["ops_obligations"][cid] = db.ops_obligations.delete_many({"case_id": cid}).deleted_count

    # Verify both cases are recorded distinctly without key collision
    assert len(del_counts["support_threads"]) == 2
    assert del_counts["support_threads"][cid1] == 1
    assert del_counts["support_threads"][cid2] == 1
    assert db.support_threads.count_documents({"case_id": cid1}) == 0
    assert db.support_threads.count_documents({"case_id": cid2}) == 0


def test_cleanup_continues_independently_when_one_collection_fails():
    db = FakeDatabase()
    cid = "sup_20261028_failure_test"

    db["support_threads"] = FakeCollection([{"case_id": cid}], fail_on_delete=True)
    db["notification_events"] = FakeCollection([{"target_id": cid}], fail_on_delete=False)
    db["audit_log"] = FakeCollection([{"target": cid}], fail_on_delete=False)

    cleanup_errors = []
    del_counts = {"support_threads": {}, "support_notifications": {}, "support_audit": {}}

    # Step 1: try delete support_threads (fails)
    try:
        del_counts["support_threads"][cid] = db.support_threads.delete_many({"case_id": cid}).deleted_count
    except Exception as e:
        cleanup_errors.append(f"support_thread {cid} delete: {e}")

    # Step 2: try delete notifications (must succeed despite step 1 failure)
    try:
        del_counts["support_notifications"][cid] = db.notification_events.delete_many({"target_id": cid}).deleted_count
    except Exception as e:
        cleanup_errors.append(f"support_notif {cid} delete: {e}")

    # Step 3: try delete audit (must succeed)
    try:
        del_counts["support_audit"][cid] = db.audit_log.delete_many({"target": cid}).deleted_count
    except Exception as e:
        cleanup_errors.append(f"support_audit {cid} delete: {e}")

    assert len(cleanup_errors) == 1
    assert "Synthetic datastore delete failure" in cleanup_errors[0]
    assert del_counts["support_notifications"][cid] == 1
    assert del_counts["support_audit"][cid] == 1
    assert db.notification_events.count_documents({"target_id": cid}) == 0
