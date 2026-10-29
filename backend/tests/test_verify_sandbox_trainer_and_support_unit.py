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
import sys
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
# Normal received-OTP mode: input identity, redaction and early configuration
# -----------------------------------------------------------------------------

def _receipt_context():
    return {
        "run_id": "receipt-run",
        "trainer_id": "sandbox-trainer-receipt-run",
        "claim_event_id": "receipt-claim",
        "phase": "initial",
    }


def test_received_otp_parser_accepts_exact_context_and_preserves_leading_zero(capsys):
    expected = _receipt_context()
    assert runner._parse_received_otp(json.dumps({**expected, "otp": "012345"}), expected) == "012345"
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("field,value", [
    ("run_id", "foreign-run"),
    ("trainer_id", "foreign-trainer"),
    ("claim_event_id", "foreign-claim"),
    ("phase", "renewal"),
    ("run_id", None),
    ("trainer_id", 123),
    ("claim_event_id", False),
    ("phase", ["initial"]),
    ("otp", 654321),
    ("otp", None),
    ("otp", True),
    ("otp", ["654321"]),
    ("otp", "65432"),
    ("otp", "6543210"),
    ("otp", " 654321"),
    ("otp", "654321\n"),
    ("otp", "６５４３２１"),
    ("otp", "65a321"),
])
def test_received_otp_parser_rejects_wrong_identity_or_type_without_echo(field, value, capsys):
    expected = _receipt_context()
    payload = {**expected, "otp": "654321", field: value}
    with pytest.raises(runner.AcceptanceFailure) as exc:
        runner._parse_received_otp(json.dumps(payload), expected)
    rendered = str(exc.value)
    assert rendered
    assert "654321" not in rendered
    for submitted in ("foreign-run", "foreign-trainer", "foreign-claim", "６５４３２１"):
        assert submitted not in rendered
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("line", [
    "not-json-654321",
    "null",
    "[]",
    '"654321"',
    '{"otp":"654321"}',
    '{"run_id":"receipt-run","trainer_id":"sandbox-trainer-receipt-run",'
    '"claim_event_id":"receipt-claim","phase":"initial","otp":"654321"} trailing-654321',
    '{"run_id":"receipt-run","trainer_id":"sandbox-trainer-receipt-run",'
    '"claim_event_id":"receipt-claim","phase":"initial","otp":"654321","otp":"012345"}',
    '{"run_id":"foreign-run","run_id":"receipt-run","trainer_id":"sandbox-trainer-receipt-run",'
    '"claim_event_id":"receipt-claim","phase":"initial","otp":"654321"}',
])
def test_received_otp_parser_rejects_malformed_or_ambiguous_json_without_echo(line, capsys):
    with pytest.raises(runner.AcceptanceFailure) as exc:
        runner._parse_received_otp(line, _receipt_context())
    assert str(exc.value)
    assert "654321" not in str(exc.value)
    assert "012345" not in str(exc.value)
    assert "foreign-run" not in str(exc.value)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("field", ["run_id", "trainer_id", "claim_event_id", "phase", "otp"])
def test_received_otp_parser_requires_each_field(field):
    payload = {**_receipt_context(), "otp": "654321"}
    del payload[field]
    with pytest.raises(runner.AcceptanceFailure) as exc:
        runner._parse_received_otp(json.dumps(payload), _receipt_context())
    assert "654321" not in str(exc.value)


def test_received_otp_parser_rejects_unexpected_fields_without_echo():
    payload = {**_receipt_context(), "otp": "654321", "extra": "private-submitted-marker"}
    with pytest.raises(runner.AcceptanceFailure) as exc:
        runner._parse_received_otp(json.dumps(payload), _receipt_context())
    assert "654321" not in str(exc.value)
    assert "private-submitted-marker" not in str(exc.value)


def test_receipt_configuration_keeps_default_and_accepts_explicit_valid_reader():
    calls = []
    reader = lambda expected: calls.append(expected)
    assert runner._validate_receipt_configuration(None, None) is None
    assert runner._validate_receipt_configuration("fixture-owner@example.invalid", reader) is None
    assert calls == [], "Configuration validation must not request a code"


@pytest.mark.parametrize("email,reader", [
    (None, lambda expected: "unused"),
    ("fixture-owner@example.invalid", None),
    ("fixture-owner@example.invalid", "not-callable"),
    ("", lambda expected: "unused"),
    ("missing-at-sign", lambda expected: "unused"),
    ("@example.invalid", lambda expected: "unused"),
    ("fixture-owner@", lambda expected: "unused"),
    ("fixture-owner@@example.invalid", lambda expected: "unused"),
    ("fixture owner@example.invalid", lambda expected: "unused"),
    ("fixture-owner@example.invalid\nBcc:foreign@example.invalid", lambda expected: "unused"),
    ("fixture-owner@example.invalid\r", lambda expected: "unused"),
])
def test_receipt_configuration_fails_before_preflight_or_fixture_effects(email, reader, monkeypatch, tmp_path):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", runner.SANDBOX_PROJECT)
    effects = []

    def forbidden(*args, **kwargs):
        effects.append("unexpected external or fixture operation")
        raise AssertionError("Receipt configuration must fail before this operation")

    monkeypatch.setattr(runner, "enforce_sandbox_preflight", forbidden)
    monkeypatch.setattr(runner, "MongoClient", forbidden)
    monkeypatch.setattr(runner, "_http_request", forbidden)
    with pytest.raises(runner.AcceptanceFailure):
        asyncio.run(runner.run_acceptance(
            mongo_url="mongodb://localhost:27017/dtd_sandbox",
            admin_pass="synthetic-admin",
            artifact_dir=tmp_path,
            receipt_email=email,
            receipt_reader=reader,
        ))
    assert effects == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("url,allowed", [
    ("https://foreign.example.invalid/api/trainers/fixture/capabilities/prefill", False),
    ("http://dtd-api-dev-625222421634.australia-southeast1.run.app/api/trainers/fixture/capabilities/prefill", False),
    ("https://dtd-api-dev-625222421634.australia-southeast1.run.app:444/api/trainers/fixture/capabilities/prefill", False),
    ("https://dtd-api-dev-625222421634.australia-southeast1.run.app/api/trainers/fixture/capabilities/prefill", True),
])
@pytest.mark.parametrize("header", ["X-Trainer-Claim-Session", "x-trainer-claim-session"])
def test_browser_guard_protects_trainer_session_on_get(url, allowed, header):
    actions = []

    class Route:
        async def abort(self, *args):
            actions.append("blocked")

        async def continue_(self):
            actions.append("continued")

    request = SimpleNamespace(url=url, method="GET", headers={header: "synthetic-session-only"})
    asyncio.run(runner.evaluate_browser_route(Route(), request, {runner.normalize_origin(runner.API_URL)}))
    assert actions == (["continued"] if allowed else ["blocked"])


@pytest.mark.parametrize("outcome", ["success", "timeout", "eof", "malformed", "oversized"])
def test_private_receipt_input_restores_echo_without_printing_submitted_data(outcome, monkeypatch, capsys):
    previous = [0, 0, 0, runner.termios.ECHO | 1, 0, 0, []]
    changes = []
    reads = []
    flushed = []
    expected = _receipt_context()
    valid_line = json.dumps({**expected, "otp": "654321"}) + "\n"

    class PrivateInput:
        def isatty(self):
            return True

        def fileno(self):
            return 42

    stream = PrivateInput()
    monkeypatch.setattr(runner.sys, "stdin", stream)
    monkeypatch.setattr(runner.termios, "tcgetattr", lambda fd: previous)

    def set_attributes(fd, mode, attributes):
        assert fd == 42
        changes.append(list(attributes))

    def select_input(inputs, outputs, errors, timeout):
        assert changes and not changes[-1][3] & runner.termios.ECHO
        assert inputs == [42] and outputs == errors == [] and 0 < timeout <= 7
        return ([], [], []) if outcome == "timeout" else ([42], [], [])

    def read_input(fd, size):
        assert fd == 42 and changes and not changes[-1][3] & runner.termios.ECHO
        reads.append(size)
        return {"success": valid_line.encode(), "eof": b"", "malformed": b"private-654321\n", "oversized": b"x" * 4097}[outcome]

    def flush_input(fd, queue):
        assert fd == 42 and queue == runner.termios.TCIFLUSH
        assert changes and not changes[-1][3] & runner.termios.ECHO
        flushed.append(True)

    monkeypatch.setattr(runner.termios, "tcsetattr", set_attributes)
    monkeypatch.setattr(runner.termios, "tcflush", flush_input)
    monkeypatch.setattr(runner.select, "select", select_input)
    monkeypatch.setattr(runner.os, "read", read_input)
    if outcome == "success":
        assert runner.read_received_otp(expected, timeout=7) == "654321"
    else:
        with pytest.raises(runner.AcceptanceFailure) as exc:
            runner.read_received_otp(expected, timeout=7)
        assert "654321" not in str(exc.value)
        assert "private-654321" not in str(exc.value)
    assert len(changes) == 2
    assert changes[0][3] == previous[3] & ~runner.termios.ECHO
    assert changes[1] == previous
    assert flushed == [True], "Private queued input must be flushed before restoring echo"
    assert previous[3] & runner.termios.ECHO, "Original terminal attributes must not be mutated"
    assert reads == ([] if outcome == "timeout" else [4097])
    captured = capsys.readouterr()
    assert "654321" not in captured.out + captured.err
    assert "private-654321" not in captured.out + captured.err


def test_private_receipt_input_rejects_non_tty_before_terminal_access(monkeypatch, capsys):
    monkeypatch.setattr(runner.sys, "stdin", SimpleNamespace(isatty=lambda: False))

    def forbidden(*args):
        raise AssertionError("Non-TTY input must fail before reading terminal attributes")

    monkeypatch.setattr(runner.termios, "tcgetattr", forbidden)
    with pytest.raises(runner.AcceptanceFailure):
        runner.read_received_otp(_receipt_context())
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("mode", ["canonical_partial_ctrl_d", "noncanonical_partial", "canonical_queued", "success"])
def test_private_receipt_real_pty_deadline_restores_echo_and_flushes_queue(mode):
    import pty
    import select
    import subprocess
    import termios
    import time

    # A separate process makes a real blocking readline regression finite and
    # leaves pytest's own terminal and stdin untouched. No provider is invoked.
    program = r'''
import copy, importlib.util, json, os, sys, termios, time
spec = importlib.util.spec_from_file_location("receipt_runner", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
expected = {"run_id":"receipt-run","trainer_id":"sandbox-trainer-receipt-run","claim_event_id":"receipt-claim","phase":"initial"}
started = time.monotonic()
try:
    result = module.read_received_otp(expected, timeout=0.25)
    outcome = "accepted" if result == "654321" else "wrong"
except module.AcceptanceFailure:
    outcome = "rejected"
elapsed = time.monotonic() - started
restored = termios.tcgetattr(0)
probe = copy.deepcopy(restored)
probe[3] &= ~termios.ICANON
probe[6][termios.VMIN] = 0
probe[6][termios.VTIME] = 0
try:
    termios.tcsetattr(0, termios.TCSANOW, probe)
    queue_empty = os.read(0, 4096) == b""
finally:
    termios.tcsetattr(0, termios.TCSANOW, restored)
print("PTY_RESULT " + json.dumps({"outcome":outcome,"elapsed":elapsed,"echo_restored":bool(restored[3] & termios.ECHO),"queue_empty":queue_empty}), flush=True)
'''
    master, slave = pty.openpty()
    attributes = termios.tcgetattr(slave)
    attributes[3] |= termios.ECHO
    if mode == "noncanonical_partial":
        attributes[3] &= ~termios.ICANON
        attributes[6][termios.VMIN] = 1
        attributes[6][termios.VTIME] = 0
    else:
        attributes[3] |= termios.ICANON
    termios.tcsetattr(slave, termios.TCSANOW, attributes)
    source = Path(runner.__file__).resolve()
    process = subprocess.Popen(
        [sys.executable, "-c", program, str(source)],
        stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    output = b""
    try:
        ready_deadline = time.monotonic() + 4
        while b"DTD_RECEIPT_REQUIRED" not in output and time.monotonic() < ready_deadline:
            if select.select([process.stdout], [], [], 0.1)[0]:
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                output += chunk
        assert b"DTD_RECEIPT_REQUIRED" in output, "Private-input reader never became ready"
        assert not termios.tcgetattr(slave)[3] & termios.ECHO
        private_input = b"private-receipt-654321"
        if mode == "canonical_partial_ctrl_d":
            private_input += b"\x04queued-private-tail"
        elif mode == "success":
            private_input = json.dumps({**_receipt_context(), "otp": "654321"}).encode() + b"\n"
        os.write(master, private_input)
        try:
            stdout, stderr = process.communicate(timeout=1.5)
        except subprocess.TimeoutExpired:
            pytest.fail("Private partial input blocked beyond the absolute receipt deadline")
        output += stdout
        assert process.returncode == 0, "Private-input child failed unexpectedly"
        result_lines = [line for line in output.decode().splitlines() if line.startswith("PTY_RESULT ")]
        assert len(result_lines) == 1
        result = json.loads(result_lines[0].removeprefix("PTY_RESULT "))
        assert result["outcome"] == ("accepted" if mode == "success" else "rejected")
        assert result["elapsed"] < 1.25
        assert result["echo_restored"] is True
        assert result["queue_empty"] is True
        assert termios.tcgetattr(slave)[3] & termios.ECHO
        echoed = os.read(master, 65536) if select.select([master], [], [], 0)[0] else b""
        assert b"654321" not in output + stderr + echoed
        assert b"queued-private-tail" not in output + stderr + echoed
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)
        for stream in (process.stdout, process.stderr):
            stream.close()
        os.close(master)
        os.close(slave)


def test_received_trainer_browser_failure_suppresses_private_driver_details(monkeypatch, tmp_path, capsys):
    private_marker = "private-receipt-driver-marker-654321"

    async def fail_launch(**kwargs):
        raise RuntimeError(private_marker)

    class PlaywrightContext:
        async def __aenter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(launch=fail_launch))

        async def __aexit__(self, *args):
            return False

    monkeypatch.setitem(sys.modules, "playwright.async_api", SimpleNamespace(
        async_playwright=PlaywrightContext,
        expect=lambda locator: None,
    ))
    with pytest.raises(runner.AcceptanceFailure) as exc:
        asyncio.run(runner.verify_received_trainer_browser(
            db=None,
            trainer_id="sandbox-trainer-receipt-run",
            run_id="receipt-run",
            recipient="fixture-owner@example.invalid",
            receipt_reader=lambda expected: "654321",
            artifact_dir=tmp_path,
            headless=True,
        ))
    assert str(exc.value)
    assert private_marker not in str(exc.value)
    assert "654321" not in str(exc.value)
    assert exc.value.__suppress_context__ is True
    captured = capsys.readouterr()
    assert private_marker not in captured.out + captured.err
    assert "654321" not in captured.out + captured.err
    assert list(tmp_path.iterdir()) == []


def test_receipt_failure_cleans_owned_fixture_without_discovering_owner_mail_support(monkeypatch, tmp_path):
    monkeypatch.setenv("DTD_SANDBOX_PROJECT_ID", runner.SANDBOX_PROJECT)
    owner_email = "fixture-owner@example.invalid"
    db = FaithfulFakeDatabase()
    foreign_case = {"case_id": "sup_preexisting_owner_case", "sender_email": owner_email, "status": "open"}
    db.support_threads.rows.append(dict(foreign_case))

    class Client:
        admin = SimpleNamespace(command=lambda command: {"ok": 1})

        def __init__(self, *args, **kwargs):
            pass

        def __getitem__(self, database):
            assert database == runner.SANDBOX_DB
            return db

        def close(self):
            pass

    def http(url, method="GET", headers=None, payload=None):
        if url.endswith("/api/health"):
            return 200, {"database": "available"}
        if url.endswith("/api/config"):
            return 200, {"public_matching_enabled": True}
        if url.endswith("/claim") and method == "POST":
            return (503, {}) if payload["method"] == "sms" else (403, {})
        if "/api/trainers/" in url and method == "GET":
            trainer_id = url.rsplit("/", 1)[-1]
            row = db.trainers.find_one({"id": trainer_id})
            return (200, {"id": trainer_id, "claim_status": "unclaimed"}) if row else (404, {})
        raise AssertionError("Unexpected HTTP operation in closed receipt-failure test")

    browser_calls = []

    async def failed_receipt_browser(database, trainer_id, run_id, recipient, reader, artifact_dir, headless):
        browser_calls.append((trainer_id, run_id))
        fixture = database.trainers.find_one({"id": trainer_id})
        assert fixture["test_fixture"] is True and fixture["test_run_id"] == run_id
        assert fixture["email"] == fixture["billing_email"] == owner_email
        assert recipient == owner_email
        raise runner.AcceptanceFailure("Synthetic receipt unavailable")

    monkeypatch.setattr(runner, "MongoClient", Client)
    monkeypatch.setattr(runner, "enforce_sandbox_preflight", lambda *args, **kwargs: {})
    monkeypatch.setattr(runner, "_http_request", http)
    monkeypatch.setattr(runner, "verify_received_trainer_browser", failed_receipt_browser)
    with pytest.raises(runner.AcceptanceFailure, match="Synthetic receipt unavailable"):
        asyncio.run(runner.run_acceptance(
            mongo_url="mongodb://localhost:27017/dtd_sandbox",
            admin_pass="synthetic-admin",
            artifact_dir=tmp_path,
            receipt_email=owner_email,
            receipt_reader=lambda expected: "654321",
        ))
    assert len(browser_calls) == 1
    assert db.trainers.rows == []
    assert db.support_threads.rows == [foreign_case]
    reports = list(tmp_path.glob("run_report_*.json"))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text())
    assert report["status"] == "EXECUTION_FAILED"
    cleanup = report["cleanup_report"]
    assert cleanup["status"] == "CLEAN"
    assert cleanup["tracked_case_ids"] == []
    assert owner_email not in cleanup["durable_lineage"]["run_emails"]


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
        fail_find: bool = False,
        fail_find_one: bool = False,
        cursor_error_after: Optional[int] = None,
    ):
        self.name = name
        self.rows = [dict(r) for r in (rows or [])]
        self.fail_delete = fail_delete
        self.fail_count = fail_count
        self.fail_find = fail_find
        self.fail_find_one = fail_find_one
        self.cursor_error_after = cursor_error_after
        self.delete_queries = []

    @staticmethod
    def _lookup(doc: Dict[str, Any], key: str):
        current: Any = doc
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]
        return True, current

    def _matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        # Mongo combines ordinary fields and logical clauses with AND. Do not let
        # a matching $or silently bypass fixture/run ownership predicates.
        for key, value in query.items():
            if key == "$or":
                if not any(self._matches(doc, part) for part in value):
                    return False
                continue
            if key == "$and":
                if not all(self._matches(doc, part) for part in value):
                    return False
                continue
            exists, actual = self._lookup(doc, key)
            if isinstance(value, dict):
                for operator, expected in value.items():
                    if operator == "$in":
                        matches = actual in expected
                    elif operator == "$exists":
                        matches = exists is expected
                    elif operator == "$ne":
                        matches = actual != expected
                    else:
                        raise AssertionError(f"Unsupported closed-fixture operator: {operator}")
                    if not matches:
                        return False
            elif actual != value:
                return False
        return True

    def delete_many(self, query: Dict[str, Any]):
        self.delete_queries.append(query)
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
        if self.fail_find:
            raise RuntimeError(f"Datastore read failure on {self.name}")
        matching = [r for r in self.rows if self._matches(r, query)]
        if self.cursor_error_after is not None:
            def interrupted_cursor():
                yield from matching[:self.cursor_error_after]
                raise RuntimeError(f"Datastore cursor failure on {self.name}")
            return interrupted_cursor()
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
        if self.fail_find_one:
            raise RuntimeError(f"Datastore ownership read failure on {self.name}")
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


def test_teardown_cleans_trainer_on_insert_acknowledgement_loss(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-unacked-123"

    # Simulate trainer fixture inserted into DB, but acknowledgement timed out
    db.trainers.rows.append({"id": trainer_id, "name": "Unacked Trainer", "test_fixture": True, "test_run_id": "fixture-run"})
    db.claim_events.rows.append({"id": "claim-unacked", "trainer_id": trainer_id, "otp_digest": "fixture-hash"})
    db.notification_events.rows.append({"id": "notif-unacked", "dispatch_id": "dispatch-unacked", "target_id": trainer_id, "kind": "trainer_claim_otp"})
    db.audit_log.rows.append({"target": trainer_id, "action": "trainer_created"})
    db.ops_obligations.rows.append({"entity_id": "claim-unacked", "obligation_id": "obligation:claim:claim-unacked"})

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "CLEAN"
    assert report["deleted"]["trainers"] == 1
    assert report["deleted"]["claim_events"] == 1
    assert report["deleted"]["trainer_notifications"] == 1
    assert report["deleted"]["trainer_audit"] == 1
    assert report["deleted"]["claim_event_obligations"] == 1
    assert report["leftovers"]["trainers"] == 0
    assert report["all_leftovers_zero"] is True


def test_teardown_discovers_and_cleans_untracked_support_cases_via_sender_email(tmp_path):
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
    db.notification_events.rows.append({"id": "notif-intake", "dispatch_id": "dispatch-intake", "target_id": case_id, "kind": "support_received_receipt"})
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
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "CLEAN"
    assert case_id in report["tracked_case_ids"]
    assert report["deleted"]["support_threads"][case_id] == 1
    assert report["deleted"]["support_notifications"][case_id] == 1
    assert report["deleted"]["support_audit"][case_id] == 1
    assert report["deleted"]["ops_obligations"][case_id] == 1
    assert report["leftovers"][f"thread_{case_id}"] == 0
    assert report["leftovers"][f"obligations_{case_id}"] == 0


def test_teardown_cleans_obligations_with_real_schema(tmp_path):
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
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "CLEAN"
    assert report["deleted"]["ops_obligations"][case_id] == 2
    assert report["leftovers"][f"obligations_{case_id}"] == 0


def test_teardown_preserves_unrelated_rows(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-to-delete"
    other_trainer = "trainer-unrelated-permanent"
    other_case = "sup_unrelated_permanent"

    db.trainers.rows.append({"id": trainer_id, "name": "Ephemeral Trainer", "test_fixture": True, "test_run_id": "fixture-run"})
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
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "CLEAN"
    assert db.trainers.count_documents({"id": other_trainer}) == 1
    assert db.support_threads.count_documents({"case_id": other_case}) == 1
    assert db.ops_obligations.count_documents({"entity_id": other_case}) == 1


def test_teardown_preserves_foreign_support_threads_referencing_trainer(tmp_path):
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
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "CLEAN"
    assert foreign_case not in report["tracked_case_ids"]
    assert db.support_threads.count_documents({"case_id": foreign_case}) == 1
    assert db.notification_events.count_documents({"target_id": foreign_case}) == 1
    assert db.audit_log.count_documents({"target": foreign_case}) == 1
    assert db.ops_obligations.count_documents({"entity_id": foreign_case}) == 1


def test_teardown_preserves_unowned_case_id_in_tracked_list(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-fixture-run"
    foreign_case = "sup_substituted_response"
    synthetic_email = "delivered+fixture-run-api@resend.dev"

    db.trainers.rows.append({"id": trainer_id, "test_fixture": True, "test_run_id": "fixture-run"})
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
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "FAILED"
    assert db.support_threads.count_documents({"case_id": foreign_case}) == 1
    assert "unowned_preserved_cases" in report
    assert foreign_case in report["unowned_preserved_cases"]


def test_teardown_preserves_unmarked_trainer_collision(tmp_path):
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
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["deleted"]["trainers"] == 0
    assert db.trainers.count_documents({"id": trainer_id}) == 1


def test_teardown_cleans_claim_event_obligation_lineage(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-claim-test"
    claim_id = "claim-owned-event-123"
    unrelated_claim_id = "claim-permanent-456"

    db.trainers.rows.append({"id": trainer_id, "test_fixture": True, "test_run_id": "fixture-run"})
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
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "CLEAN"
    assert report["deleted"]["claim_events"] == 1
    assert report["deleted"]["claim_event_obligations"] == 1
    assert report["leftovers"].get("claim_event_obligations", 0) == 0
    assert db.claim_events.count_documents({"id": claim_id}) == 0
    assert db.ops_obligations.count_documents({"entity_id": claim_id}) == 0
    assert db.claim_events.count_documents({"id": unrelated_claim_id}) == 1
    assert db.ops_obligations.count_documents({"entity_id": unrelated_claim_id}) == 1


def test_teardown_cleans_notification_dispatch_obligation_lineage(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-notif-test"
    case_id = "sup_owned_case_789"
    run_email = "delivered+dispatch-test@resend.dev"
    dispatch_id = "dispatch-owned-event-456"
    unrelated_dispatch_id = "dispatch-unrelated-event-999"

    db.trainers.rows.append({"id": trainer_id, "test_fixture": True, "test_run_id": "fixture-run"})
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
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "CLEAN"
    assert report["deleted"]["dispatch_obligations"] == 1
    assert report["leftovers"].get("dispatch_obligations", 0) == 0
    assert db.notification_events.count_documents({"dispatch_id": dispatch_id}) == 0
    assert db.ops_obligations.count_documents({"entity_id": dispatch_id}) == 0
    assert db.notification_events.count_documents({"dispatch_id": unrelated_dispatch_id}) == 1
    assert db.ops_obligations.count_documents({"entity_id": unrelated_dispatch_id}) == 1


def test_teardown_fails_on_datastore_delete_error(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-del-fail"
    db.collections["trainers"] = FaithfulFakeCollection("trainers", [{"id": trainer_id, "test_fixture": True, "test_run_id": "fixture-run"}], fail_delete=True)

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "FAILED"
    assert any("trainers delete" in err for err in report["cleanup_errors"])
    assert report["all_leftovers_zero"] is False


def test_teardown_fails_on_datastore_count_error(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-count-fail"
    db.collections["trainers"] = FaithfulFakeCollection(
        "trainers", [{"id": trainer_id, "test_fixture": True, "test_run_id": "fixture-run"}], fail_count=True
    )

    def mock_request(url, method="GET", headers=None, payload=None):
        return 404, {}

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=["delivered+test@resend.dev"],
        admin_pass="test-pass",
        http_request_fn=mock_request,
        run_id="fixture-run",
        recovery_dir=tmp_path,
    )

    assert report["status"] == "FAILED"
    assert report["leftovers"]["trainers"] == -1
    assert any("trainers" in err.lower() and "count" in err.lower() for err in report["cleanup_errors"])
    assert report["all_leftovers_zero"] is False


def test_teardown_fails_when_endpoint_returns_200(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-200-leak"
    db.trainers.rows.append({"id": trainer_id, "test_fixture": True, "test_run_id": "fixture-run"})

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
        run_id="fixture-run",
        recovery_dir=tmp_path,
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

    # 3. Mock HTTP request to fail during claim initiation (after trainer fixture inserted)
    def mock_http(url, method="GET", headers=None, payload=None):
        if "/api/health" in url:
            return 200, {"database": "available"}
        if "/api/config" in url:
            return 200, {"public_matching_enabled": True}
        if "/api/trainers/" in url and "/claim" not in url:
            return 200, {"id": "mock-profile", "claim_status": "unclaimed"}
        if "/claim" in url:
            raise runner.AcceptanceFailure("Synthetic scenario crash")
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

    # 2. Ensure exact origin check is performed on WEB_URL
    assert "normalize_origin(WEB_URL)" in source
    assert "approved_web_origin" in source


def test_evaluate_browser_route_blocks_http_downgrade():
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

        approved_origins = {runner.normalize_origin(runner.WEB_URL), runner.normalize_origin(runner.API_URL)}

        # Plaintext HTTP downgrade on cloud API endpoint carrying auth
        downgraded_url = runner.API_URL.replace("https:", "http:") + "/api/oversight"
        req = MockRequest(downgraded_url, method="GET", headers={"X-Admin-Pass": "secret"})
        await runner.evaluate_browser_route(MockRoute(), req, approved_origins)

        assert aborted == ["blockedbyclient"]
        assert len(continued) == 0

    asyncio.run(_run())


def test_evaluate_browser_route_blocks_different_port():
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

        approved_origins = {runner.normalize_origin(runner.WEB_URL), runner.normalize_origin(runner.API_URL)}

        # Different port mutation on approved hostname
        altered_port_url = runner.API_URL + ":8443/support/contact"
        req = MockRequest(altered_port_url, method="POST")
        await runner.evaluate_browser_route(MockRoute(), req, approved_origins)

        assert aborted == ["blockedbyclient"]
        assert len(continued) == 0

    asyncio.run(_run())


def test_evaluate_browser_route_blocks_foreign_mutation():
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

        approved_origins = {runner.normalize_origin(runner.WEB_URL), runner.normalize_origin(runner.API_URL)}

        # Foreign domain mutation
        foreign_url = "https://evil.invalid/support/contact"
        req = MockRequest(foreign_url, method="POST")
        await runner.evaluate_browser_route(MockRoute(), req, approved_origins)

        assert aborted == ["blockedbyclient"]
        assert len(continued) == 0

    asyncio.run(_run())


def test_evaluate_browser_route_allows_approved_https():
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

        approved_origins = {runner.normalize_origin(runner.WEB_URL), runner.normalize_origin(runner.API_URL)}

        # Approved API POST
        req = MockRequest(runner.API_URL + "/support/contact", method="POST")
        await runner.evaluate_browser_route(MockRoute(), req, approved_origins)

        assert len(aborted) == 0
        assert continued == [True]

    asyncio.run(_run())


def test_evaluate_browser_route_allows_harmless_assets():
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

        approved_origins = {runner.normalize_origin(runner.WEB_URL), runner.normalize_origin(runner.API_URL)}

        # Third-party stylesheet / font
        req = MockRequest("https://fonts.googleapis.com/css?family=Inter", method="GET")
        await runner.evaluate_browser_route(MockRoute(), req, approved_origins)

        assert len(aborted) == 0
        assert continued == [True]

    asyncio.run(_run())


def test_verify_page_exact_origin_behavior():
    approved_web = runner.normalize_origin(runner.WEB_URL)

    # 1. Matching exact approved HTTPS origin succeeds
    runner.verify_page_exact_origin(runner.WEB_URL + "/ops", approved_web, "Ops load")
    runner.verify_page_exact_origin(runner.WEB_URL + ":443/contact", approved_web, "Contact load")

    # 2. HTTP downgrade raises AcceptanceFailure
    downgraded_url = runner.WEB_URL.replace("https:", "http:") + "/ops"
    with pytest.raises(runner.AcceptanceFailure, match="page navigated or redirected to unapproved origin"):
        runner.verify_page_exact_origin(downgraded_url, approved_web, "Ops load")

    # 3. Altered port raises AcceptanceFailure
    altered_port_url = runner.WEB_URL + ":8443/ops"
    with pytest.raises(runner.AcceptanceFailure, match="page navigated or redirected to unapproved origin"):
        runner.verify_page_exact_origin(altered_port_url, approved_web, "Ops load")

    # 4. Foreign destination raises AcceptanceFailure
    with pytest.raises(runner.AcceptanceFailure, match="page navigated or redirected to unapproved origin"):
        runner.verify_page_exact_origin("https://attacker.invalid/ops", approved_web, "Ops load")


# -----------------------------------------------------------------------------
# 7. G1: Strict Parent Ownership Gating & Dependency Preservation Tests
# -----------------------------------------------------------------------------

def test_teardown_preserves_unmarked_trainer_collision_and_all_dependencies(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-aaaaaaaaaaaa"
    run_id = "aaaaaaaaaaaa"
    email = "delivered+sandbox-support-aaaaaaaaaaaa-api@resend.dev"

    # Pre-existing unmarked trainer collision with real-schema dependencies
    db.trainers.rows.append({"id": trainer_id, "name": "pre-existing unowned trainer"})
    db.claim_events.rows.append({"id": "foreign-claim", "trainer_id": trainer_id})
    db.notification_events.rows.append({"id": "foreign-notif", "dispatch_id": "foreign-dispatch", "target_id": trainer_id})
    db.audit_log.rows.append({"target": trainer_id, "action": "real_owner_event"})
    db.ops_obligations.rows.extend([
        {"entity_id": "foreign-claim", "obligation_id": "obligation:claim:foreign-claim"},
        {"entity_id": "foreign-dispatch", "obligation_id": "obligation:message:foreign-dispatch"},
    ])

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=[email],
        admin_pass="test-pass",
        run_id=run_id,
        http_request_fn=lambda *a, **k: (404, {}),
        recovery_dir=tmp_path,
    )

    remaining = {k: len(c.rows) for k, c in db.collections.items() if c.rows}
    assert remaining == {
        "trainers": 1,
        "claim_events": 1,
        "notification_events": 1,
        "audit_log": 1,
        "ops_obligations": 2,
    }
    assert report["deleted"]["trainers"] == 0
    assert report["deleted"]["claim_events"] == 0
    assert report["deleted"]["trainer_notifications"] == 0
    assert report["deleted"]["trainer_audit"] == 0
    assert report["deleted"]["trainer_obligations"] == 0


def test_teardown_preserves_another_runs_marked_fixture(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-other"
    other_run_id = "other-run-id-999"
    current_run_id = "current-run-id-111"
    email = "delivered+sandbox-support-current-api@resend.dev"

    db.trainers.rows.append({"id": trainer_id, "test_fixture": True, "test_run_id": other_run_id})
    db.claim_events.rows.append({"id": "other-claim", "trainer_id": trainer_id})
    db.notification_events.rows.append({"id": "other-notif", "dispatch_id": "other-dispatch", "target_id": trainer_id})
    db.audit_log.rows.append({"target": trainer_id, "action": "other_run_audit"})
    db.ops_obligations.rows.append({"entity_id": trainer_id, "obligation_id": f"obligation:trainer:{trainer_id}"})

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids=set(),
        run_emails=[email],
        admin_pass="test-pass",
        run_id=current_run_id,
        http_request_fn=lambda *a, **k: (404, {}),
        recovery_dir=tmp_path,
    )

    remaining = {k: len(c.rows) for k, c in db.collections.items() if c.rows}
    assert remaining == {
        "trainers": 1,
        "claim_events": 1,
        "notification_events": 1,
        "audit_log": 1,
        "ops_obligations": 1,
    }
    assert report["deleted"]["trainers"] == 0


def test_teardown_preserves_missing_parent_unowned_history(tmp_path):
    db = FaithfulFakeDatabase()
    cid = "sup_foreign_removed_parent"
    email = "delivered+sandbox-support-api@resend.dev"

    # Support thread doc is absent, but foreign history exists
    db.audit_log.rows.append({"target": cid, "action": "retained_real_support_history"})
    db.notification_events.rows.append({"target_id": cid, "dispatch_id": "retained-foreign-dispatch"})
    db.ops_obligations.rows.append({"entity_id": cid, "obligation_id": "obligation:support:" + cid})

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id="sandbox-trainer-unrelated",
        tracked_case_ids={cid},
        run_emails=[email],
        admin_pass="test-pass",
        run_id="run-test",
        http_request_fn=lambda *a, **k: (404, {}),
        recovery_dir=tmp_path,
    )

    assert len(db.audit_log.rows) == 1
    assert len(db.notification_events.rows) == 1
    assert len(db.ops_obligations.rows) == 1
    assert cid in report["unowned_preserved_cases"]
    assert cid in report["unverified_missing_cases"]
    assert cid not in report["tracked_case_ids"]


def test_teardown_owned_lost_ack_idempotent_cleanup(tmp_path):
    db = FaithfulFakeDatabase()
    trainer_id = "sandbox-trainer-lostack"
    run_id = "lostack-run-123"
    cid = "sup_lostack_case"
    claim_id = "claim-lostack-1"
    disp_id = "dispatch-lostack-1"
    email = "delivered+lostack@resend.dev"

    durable_lineage = {
        "schema_version": 1,
        "project": runner.SANDBOX_PROJECT,
        "database": runner.SANDBOX_DB,
        "run_emails": [email],
        "run_id": run_id,
        "trainer_id": trainer_id,
        "trainer_owned": True,
        "owned_case_ids": [cid],
        "owned_claim_event_ids": [claim_id],
        "owned_dispatch_ids": [disp_id],
    }

    # Leftover obligations remain while sources are already gone
    db.ops_obligations.rows.extend([
        {"obligation_id": f"obligation:claim:{claim_id}", "entity_id": claim_id},
        {"obligation_id": f"obligation:message:{disp_id}", "entity_id": disp_id},
        {"obligation_id": f"obligation:support:{cid}", "entity_id": cid},
    ])

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer_id,
        tracked_case_ids={cid},
        run_emails=[email],
        admin_pass="test-pass",
        run_id=run_id,
        durable_lineage=durable_lineage,
        http_request_fn=lambda *a, **k: (404, {}),
        recovery_dir=tmp_path,
    )

    assert report["status"] == "CLEAN"
    assert len(db.ops_obligations.rows) == 0
    assert report["leftovers"].get("claim_event_obligations", 0) == 0
    assert report["leftovers"].get("dispatch_obligations", 0) == 0


# -----------------------------------------------------------------------------
# 8. G2: Reject Volume-Only and Literal Shadowing Secret Preflight Tests
# -----------------------------------------------------------------------------

def test_enforce_sandbox_preflight_rejects_unmounted_wrong_volume_versions():
    def mock_runner(cmd):
        if "revisions" in cmd or "dtd-api-dev" in cmd:
            desc = _make_valid_service_desc("dtd-api-dev")
            desc["spec"]["volumes"] = [
                {"name": "secret-admin-pass", "secret": {"secretName": "dtd-admin-pass", "items": [{"key": "99", "path": "val"}]}},
                {"name": "secret-mongo-url", "secret": {"secretName": "dtd-mongo-url", "items": [{"key": "42", "path": "val"}]}},
            ]
            desc["spec"]["template"]["spec"]["volumes"] = desc["spec"]["volumes"]
            return desc
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="declares secret dtd-admin-pass with version '99', expected '4'"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


def test_enforce_sandbox_preflight_rejects_volume_only_bindings():
    def mock_runner(cmd):
        if "revisions" in cmd or "dtd-api-dev" in cmd:
            desc = _make_valid_service_desc("dtd-api-dev")
            container = desc["spec"]["containers"][0]
            container["env"] = [e for e in container["env"] if e.get("name") != "ADMIN_PASS"]
            desc["spec"]["template"]["spec"]["containers"][0]["env"] = container["env"]
            return desc
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="ADMIN_PASS is not bound via container secretKeyRef"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


def test_enforce_sandbox_preflight_rejects_literal_settings_shadowing_secrets():
    def mock_runner(cmd):
        if "revisions" in cmd or "dtd-api-dev" in cmd:
            desc = _make_valid_service_desc("dtd-api-dev")
            container = desc["spec"]["containers"][0]
            container["env"].append({"name": "ADMIN_PASS", "value": "literal-secret-forbidden"})
            desc["spec"]["template"]["spec"]["containers"][0]["env"] = container["env"]
            return desc
        if "dtd-web-dev" in cmd:
            return _make_valid_service_desc("dtd-web-dev")
        if "dtd-trainer-ingest-cron" in cmd:
            return _make_valid_scheduler_desc(state="PAUSED")
        return {}

    with pytest.raises(runner.AcceptanceFailure, match="ADMIN_PASS specifies literal value in container env"):
        runner.enforce_sandbox_preflight("dogtrainersdirectory-dev", runner=mock_runner)


# -----------------------------------------------------------------------------
# 9. G3: Durable Lineage Persistence, Two-Pass Recovery & Report Status Tests
# -----------------------------------------------------------------------------

def test_teardown_two_pass_recovery_retains_lineage_and_cleans_obligations(tmp_path):
    trainer = "sandbox-trainer-recovery-run"
    run = "recovery-run-001"
    email = "delivered+recovery-run-api@resend.dev"
    claim = "owned-claim-id-777"
    dispatch = "owned-dispatch-id-888"
    case = "sup_owned_recovery"

    db = FaithfulFakeDatabase()
    db.trainers.rows.append({"id": trainer, "test_fixture": True, "test_run_id": run})
    db.claim_events.rows.append({"id": claim, "trainer_id": trainer})
    db.support_threads.rows.append({"case_id": case, "sender_email": email})
    db.notification_events.rows.append({"id": "owned-notif", "dispatch_id": dispatch, "target_id": case})
    db.ops_obligations.rows.extend([
        {"obligation_id": f"obligation:claim:{claim}", "entity_id": claim, "category": "claim_lock", "metadata": {"trainer_id": trainer}},
        {"obligation_id": f"obligation:message:{dispatch}", "entity_id": dispatch, "category": "notification_delivery", "metadata": {"target_id": case}},
    ])

    # Pass 1: Transient obligation delete failure
    db.collections["ops_obligations"].fail_delete = True

    first = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer,
        tracked_case_ids={case},
        run_emails=[email],
        admin_pass="test-pass",
        run_id=run,
        recovery_dir=tmp_path,
        http_request_fn=lambda *a, **k: (404, {}),
    )

    assert first["status"] == "FAILED"
    assert len(db.ops_obligations.rows) == 2
    assert len(db.trainers.rows) == 0
    assert len(db.claim_events.rows) == 0
    assert len(db.support_threads.rows) == 0
    assert len(db.notification_events.rows) == 0
    assert claim in first["owned_claim_event_ids"]
    assert dispatch in first["owned_dispatch_ids"]
    lineage_file = tmp_path / f"dtd_lineage_{run}.json"
    assert lineage_file.exists()

    # Pass 2: Transient error resolved. Retry with NO source rows in DB.
    db.collections["ops_obligations"].fail_delete = False

    second = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer,
        tracked_case_ids={case},
        run_emails=[email],
        admin_pass="test-pass",
        run_id=run,
        recovery_dir=tmp_path,
        http_request_fn=lambda *a, **k: (404, {}),
    )

    assert second["status"] == "CLEAN"
    assert len(db.ops_obligations.rows) == 0
    assert second["deleted"]["claim_event_obligations"] == 1
    assert second["deleted"]["dispatch_obligations"] == 1


def test_teardown_aborts_before_source_deletion_if_lineage_persistence_fails(tmp_path, monkeypatch):
    write_attempts = []

    def reject_lineage_write(path, payload):
        write_attempts.append(path)
        raise PermissionError("Synthetic lineage persistence failure")

    monkeypatch.setattr(runner, "_write_atomic_json", reject_lineage_write)

    trainer = "sandbox-trainer-persist-fail"
    run = "persist-fail-run"
    email = "delivered+persist-fail@resend.dev"

    db = FaithfulFakeDatabase()
    db.trainers.rows.append({"id": trainer, "test_fixture": True, "test_run_id": run})
    db.claim_events.rows.append({"id": "claim-persist-fail", "trainer_id": trainer})

    report = runner.execute_deterministic_teardown(
        db=db,
        trainer_id=trainer,
        tracked_case_ids=set(),
        run_emails=[email],
        admin_pass="test-pass",
        run_id=run,
        recovery_dir=tmp_path,
        http_request_fn=lambda *a, **k: (404, {}),
    )

    assert report["status"] == "FAILED"
    assert write_attempts, "The failure must exercise persistence, not an earlier path-validation error"
    assert any("lineage persistence failed" in err.lower() for err in report["cleanup_errors"])
    assert len(db.trainers.rows) == 1
    assert len(db.claim_events.rows) == 1


def test_run_acceptance_final_report_contains_terminal_status_and_error(monkeypatch, tmp_path):
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
            return 500, {"error": "Early synthetic health crash"}
        return 404, {}

    monkeypatch.setattr(runner, "_http_request", mock_http)

    with pytest.raises(runner.AcceptanceFailure):
        asyncio.run(runner.run_acceptance(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-pass",
            preflight_runner=mock_preflight,
            artifact_dir=tmp_path,
        ))

    report_files = list(tmp_path.glob("run_report_*.json"))
    assert len(report_files) == 1
    report = json.loads(report_files[0].read_text())

    assert report["status"] == "EXECUTION_FAILED"
    assert "Early synthetic health crash" in report["error"]
    assert report["evidence"]["status"] == "EXECUTION_FAILED"
    assert "Early synthetic health crash" in report["evidence"]["error"]


def test_run_acceptance_fails_when_report_save_fails(monkeypatch, tmp_path):
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
    monkeypatch.setattr(runner, "_http_request", lambda url, *a, **k: (200, {"database": "available", "public_matching_enabled": True}))

    real_write_text = Path.write_text

    def failing_write_text(self, *args, **kwargs):
        if "run_report_" in self.name:
            raise OSError("Simulated disk write failure on final report")
        return real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failing_write_text)

    with pytest.raises(runner.AcceptanceFailure, match="Failed to persist required final run report"):
        asyncio.run(runner.run_acceptance(
            mongo_url="mongodb+srv://user:pass@dtd-sandbox.wtrfq.mongodb.net/dtd_sandbox",
            admin_pass="test-pass",
            preflight_runner=mock_preflight,
            artifact_dir=tmp_path,
        ))

# -----------------------------------------------------------------------------
# G1/G3 completion: independently scoped recovery, complete reads and retry safety
# -----------------------------------------------------------------------------

def _owned_cleanup_graph(run_id="strict-run"):
    """Synthetic rows follow the authoritative application writers' identities."""
    db = FaithfulFakeDatabase()
    trainer = f"sandbox-trainer-{run_id}"
    email = f"delivered+{run_id}-api@resend.dev"
    case, claim, dispatch = "sup_strict_owned", "claim-strict-owned", "dispatch-strict-owned"
    db.trainers.rows.append({"id": trainer, "test_fixture": True, "test_run_id": run_id})
    db.support_threads.rows.append({"case_id": case, "sender_email": email, "trainer_id": trainer})
    db.claim_events.rows.append({"id": claim, "trainer_id": trainer})
    db.notification_events.rows.append({
        "id": "notif-strict-owned", "dispatch_id": dispatch,
        "target_kind": "support_thread", "target_id": case,
    })
    db.audit_log.rows.append({"id": "audit-strict-owned", "target": case})
    db.ops_obligations.rows.extend([
        {"obligation_id": f"obligation:support:{case}", "entity_id": case},
        {"obligation_id": f"obligation:claim:{claim}", "entity_id": claim,
         "category": "claim_lock", "metadata": {"trainer_id": trainer}},
        {"obligation_id": f"obligation:message:{dispatch}", "entity_id": dispatch,
         "category": "notification_delivery", "metadata": {"target_id": case}},
    ])
    args = {
        "db": db, "trainer_id": trainer, "tracked_case_ids": {case},
        "run_emails": [email], "run_id": run_id, "admin_pass": "synthetic-placeholder",
        "http_request_fn": lambda *a, **k: (404, {}),
    }
    return db, args, (case, claim, dispatch)


def _complete_lineage(args, identifiers):
    case, claim, dispatch = identifiers
    return {
        "schema_version": 1, "project": runner.SANDBOX_PROJECT, "database": runner.SANDBOX_DB,
        "run_id": args["run_id"], "trainer_id": args["trainer_id"],
        "run_emails": list(args["run_emails"]), "trainer_owned": True,
        "owned_case_ids": [case], "owned_claim_event_ids": [claim], "owned_dispatch_ids": [dispatch],
    }


def _rows_snapshot(db):
    # JSON roundtrip prevents nested metadata aliases from concealing mutations.
    return json.loads(json.dumps({name: collection.rows for name, collection in db.collections.items() if collection.rows}))


def _assert_no_deletion(db, before):
    assert _rows_snapshot(db) == before
    assert not any(collection.delete_queries for collection in db.collections.values()), "No delete may follow unverified ownership or inventory"


@pytest.mark.parametrize("missing", ["run_id", "recovery_dir"])
def test_teardown_requires_explicit_recovery_scope_before_deleting(tmp_path, missing):
    db, args, _ = _owned_cleanup_graph()
    args["recovery_dir"] = tmp_path
    args[missing] = "" if missing == "run_id" else None
    before = _rows_snapshot(db)
    report = runner.execute_deterministic_teardown(**args)
    assert report["status"] == "FAILED"
    _assert_no_deletion(db, before)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("field,bad_value", [
    ("schema_version", 2), ("project", "production-project"), ("database", "DTD"),
    ("run_id", "another-run"), ("trainer_id", "another-trainer"),
    ("run_emails", ["delivered+another-run@resend.dev"]), ("trainer_owned", "True"),
    ("owned_case_ids", "not-a-list"), ("owned_claim_event_ids", [17]),
    ("owned_dispatch_ids", {"not": "a-list"}),
])
@pytest.mark.parametrize("source", ["disk", "argument"])
def test_teardown_rejects_mismatched_or_invalid_lineage_without_deletes(tmp_path, field, bad_value, source):
    db, args, identifiers = _owned_cleanup_graph()
    lineage = _complete_lineage(args, identifiers)
    lineage[field] = bad_value
    path = tmp_path / f"dtd_lineage_{args['run_id']}.json"
    original = json.dumps(lineage, sort_keys=True)
    path.write_text(original)
    args["recovery_dir"] = tmp_path
    if source == "argument":
        args["durable_lineage"] = lineage
    before = _rows_snapshot(db)
    report = runner.execute_deterministic_teardown(**args)
    assert report["status"] == "FAILED", (field, source)
    _assert_no_deletion(db, before)
    assert path.read_text() == original, "Invalid recovery evidence must not be silently overwritten"


def test_teardown_rejects_unreadable_lineage_without_overwriting_or_deleting(tmp_path):
    db, args, _ = _owned_cleanup_graph()
    path = tmp_path / f"dtd_lineage_{args['run_id']}.json"
    path.write_text("{partial-json")
    args["recovery_dir"] = tmp_path
    before = _rows_snapshot(db)
    report = runner.execute_deterministic_teardown(**args)
    assert report["status"] == "FAILED"
    _assert_no_deletion(db, before)
    assert path.read_text() == "{partial-json"


@pytest.mark.parametrize("parent", ["trainer", "case"])
def test_teardown_current_foreign_owner_overrides_loaded_lineage_without_deleting(tmp_path, parent):
    db, args, identifiers = _owned_cleanup_graph()
    lineage = _complete_lineage(args, identifiers)
    if parent == "trainer":
        db.trainers.rows[0]["test_run_id"] = "other-run"
    else:
        db.support_threads.rows[0]["sender_email"] = "foreign-owner@example.invalid"
        db.support_threads.rows[0]["test_run_id"] = "other-run"
    path = tmp_path / f"dtd_lineage_{args['run_id']}.json"
    original = json.dumps(lineage)
    path.write_text(original)
    args["recovery_dir"] = tmp_path
    before = _rows_snapshot(db)
    report = runner.execute_deterministic_teardown(**args)
    assert report["status"] == "FAILED"
    _assert_no_deletion(db, before)
    assert path.read_text() == original


def test_teardown_fixture_without_current_run_marker_preserves_whole_graph(tmp_path):
    db, args, _ = _owned_cleanup_graph()
    db.trainers.rows[0].pop("test_run_id")
    args["recovery_dir"] = tmp_path
    before = _rows_snapshot(db)
    report = runner.execute_deterministic_teardown(**args)
    assert report["status"] == "FAILED"
    _assert_no_deletion(db, before)


@pytest.mark.parametrize("collection,operation", [
    ("trainers", "fail_find_one"), ("support_threads", "fail_find_one"),
    ("support_threads", "fail_find"), ("claim_events", "fail_find"),
    ("notification_events", "fail_find"),
])
def test_teardown_required_read_failure_preserves_sources_and_recovery_for_retry(tmp_path, collection, operation):
    db, args, identifiers = _owned_cleanup_graph()
    lineage = _complete_lineage(args, identifiers)
    path = tmp_path / f"dtd_lineage_{args['run_id']}.json"
    original = json.dumps(lineage, sort_keys=True)
    path.write_text(original)
    args["recovery_dir"] = tmp_path
    before = _rows_snapshot(db)
    setattr(db[collection], operation, True)
    first = runner.execute_deterministic_teardown(**args)
    assert first["status"] == "FAILED"
    _assert_no_deletion(db, before)
    assert path.read_text() == original, "Unknown inventory must not overwrite complete recovery evidence"

    setattr(db[collection], operation, False)
    second = runner.execute_deterministic_teardown(**args)
    assert second["status"] == "CLEAN"
    assert not _rows_snapshot(db), "Retry must remove all proven owned rows and obligations"


@pytest.mark.parametrize("collection", ["claim_events", "notification_events"])
def test_teardown_partial_cursor_failure_never_commits_incomplete_inventory(tmp_path, collection):
    db, args, identifiers = _owned_cleanup_graph()
    lineage = _complete_lineage(args, identifiers)
    path = tmp_path / f"dtd_lineage_{args['run_id']}.json"
    original = json.dumps(lineage, sort_keys=True)
    path.write_text(original)
    args["recovery_dir"] = tmp_path
    before = _rows_snapshot(db)
    db[collection].cursor_error_after = 1
    report = runner.execute_deterministic_teardown(**args)
    assert report["status"] == "FAILED"
    _assert_no_deletion(db, before)
    assert path.read_text() == original


def test_teardown_atomic_lineage_replace_failure_preserves_old_proof_and_sources(tmp_path, monkeypatch):
    db, args, identifiers = _owned_cleanup_graph()
    path = tmp_path / f"dtd_lineage_{args['run_id']}.json"
    original = json.dumps(_complete_lineage(args, identifiers), sort_keys=True)
    path.write_text(original)
    args["recovery_dir"] = tmp_path
    before = _rows_snapshot(db)
    replace = os.replace

    def deny_target_replace(source, target):
        if Path(target) == path:
            raise OSError("Synthetic atomic lineage replacement failure")
        return replace(source, target)

    monkeypatch.setattr(os, "replace", deny_target_replace)
    report = runner.execute_deterministic_teardown(**args)
    assert report["status"] == "FAILED"
    _assert_no_deletion(db, before)
    assert path.read_text() == original
