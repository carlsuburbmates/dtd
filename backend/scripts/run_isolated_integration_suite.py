#!/usr/bin/env python3
"""Run the full backend suite against a disposable, local API/database.

This is intentionally separate from the production canonical seed.  The test
fixture represents a *verified and published* profile so public matching,
directory browsing, enquiry, notification fallback and `/ops` contracts can be
tested without changing the cautious acquisition lifecycle used in production.

The runner refuses non-loopback MongoDB hosts and drops only the UUID-named
database it creates.
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse
from urllib.request import urlopen

from pymongo import MongoClient


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _require_local_mongo(uri: str) -> None:
    parsed = urlparse(uri)
    if parsed.scheme != "mongodb" or parsed.hostname not in LOOPBACK_HOSTS:
        raise SystemExit(
            "Refusing to run against a non-loopback MongoDB URI. "
            "Use the default local MongoDB service."
        )


def _start_ephemeral_mongo() -> tuple[MongoClient, subprocess.Popen[str], tempfile.TemporaryDirectory[str]]:
    """Start an isolated loopback MongoDB when no local service was supplied.

    The full suite is the documented one-command verification path.  It must
    therefore not depend on a developer having separately started MongoDB, and
    it must not share a persistent database with another local workflow.
    """
    mongod = shutil.which("mongod")
    if not mongod:
        raise SystemExit(
            "MongoDB is required for the isolated integration suite. Install "
            "`mongod`, or provide a loopback service with --mongo-url."
        )

    data_dir = tempfile.TemporaryDirectory(prefix="dtd-isolated-mongo-")
    port = _free_port()
    mongo_url = f"mongodb://127.0.0.1:{port}"
    log_path = Path(data_dir.name) / "mongod.log"
    process = subprocess.Popen(
        [
            mongod,
            "--dbpath", data_dir.name,
            "--bind_ip", "127.0.0.1",
            "--port", str(port),
            "--logpath", str(log_path),
            "--logappend",
            "--quiet",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=500)
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log_tail = log_path.read_text(errors="replace")[-2000:] if log_path.exists() else ""
            client.close()
            data_dir.cleanup()
            raise RuntimeError(
                f"Ephemeral MongoDB exited during startup (exit {process.returncode}):\n{log_tail}"
            )
        try:
            client.admin.command("ping")
            return client, process, data_dir
        except Exception:
            time.sleep(0.15)

    process.terminate()
    process.wait(timeout=5)
    client.close()
    log_tail = log_path.read_text(errors="replace")[-2000:] if log_path.exists() else ""
    data_dir.cleanup()
    raise RuntimeError(f"Timed out starting ephemeral MongoDB:\n{log_tail}")


def _fixture_trainer() -> Dict[str, object]:
    now = datetime.now(timezone.utc).isoformat()
    # This disposable fixture must use the same confirmed, structured facts as
    # a matchable trainer. Legacy descriptive fields alone are deliberately
    # insufficient for v2 matching.
    repo_path = str(REPO_ROOT)
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)
    from backend.services.trainer_quality import package_trainer_capabilities
    capabilities = package_trainer_capabilities(
        specialties=["puppy_training", "leash_reactivity"],
        service_formats=["in_home"],
        life_stages=["puppy", "adolescent"],
        training_philosophy="positive_reinforcement_force_free",
        serviced_suburbs=["Fitzroy", "Carlton"],
        catchment_type="specific_suburbs",
        delivery_constraints={"in_home_available": True, "facility_available": False, "travel_distance_km": 20},
        basis="trainer_declaration",
        evidence_reference="isolated_integration_fixture",
        confirmed_at=now,
    )
    return {
        "id": "integration-fixture-trainer",
        "slug": "integration-fixture-dog-training",
        "name": "Integration Fixture Dog Training",
        "suburb": "Fitzroy",
        "region": "Greater Melbourne",
        "published": True,
        "contact_ready": True,
        "verification_status": "verified",
        "abn_verified": True,
        "claim_status": "unclaimed",
        "tier": "free",
        "services": ["Puppy training", "Reactivity support", "One-on-one training"],
        "categories": ["puppy", "behaviour", "obedience"],
        "specialties": ["leash reactivity", "puppy training"],
        "service_formats": ["in_home"],
        "serviced_suburbs": ["Fitzroy", "Carlton"],
        "training_philosophy": "Force-free",
        "capabilities": capabilities,
        "bio": "Test-only verified fixture for puppy and reactive-dog matching in Fitzroy.",
        "website": "https://example.test/integration-fixture",
        "phone": "0400000000",
        "email": "fixture@example.test",
        "source_evidence_url": "https://example.test/integration-fixture",
        "source_evidence": [{"url": "https://example.test/integration-fixture", "retrieved_at": now}],
        "quality_outcome": "published",
        "suppression_status": "clear",
        "outcome_score": 0.8,
        "review_rating": 4.8,
        "review_count": 12,
        "created_at": now,
        "updated_at": now,
    }


def _wait_for_api(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 20
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"Local API exited during startup (exit {process.returncode}):\n{output[-4000:]}")
        try:
            with urlopen(f"{base_url}/api/", timeout=1.5) as response:  # nosec B310: fixed loopback URL
                if response.status == 200:
                    return
        except Exception as exc:  # API may not yet have bound its socket.
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for isolated API: {last_error}")


def _server_environment(mongo_url: str, db_name: str, base_url: str) -> Dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "MONGO_URL": mongo_url,
            "DB_NAME": db_name,
            "REACT_APP_BACKEND_URL": base_url,
            "REMOTE_BACKEND_URL": base_url,
            "ADMIN_PASS": "dtd-isolated-suite-pass",
            "TRAINER_ACTION_TOKEN_SECRET": "dtd-isolated-suite-token",
            "ENABLE_STARTUP_SEEDS": "0",
            "DISABLE_AUTONOMY": "1",
            # Keep the legacy and explicit ownership settings consistent; the
            # separate DISABLE_AUTONOMY flag prevents every startup/periodic
            # loop from writing during the suite.
            "AUTONOMY_LOOP_OWNER": "api",
            "RUN_AUTONOMY_IN_API": "1",
            "CONTACT_READY_POLICY": "allow",
            # Integration tests must be deterministic and never send messages,
            # bill Stripe or call external AI/location providers.
            "GEMINI_API_KEY": "",
            "GOOGLE_PLACES_API_KEY": "",
            "RESEND_API_KEY": "",
            "STRIPE_SECRET_KEY": "",
            "STRIPE_WEBHOOK_SECRET": "",
            "SENTRY_DSN": "",
            # The suite fixture has one verified local profile. These are test
            # thresholds only; production thresholds remain an owner decision.
            "SEO_MIN_PUBLISHED_TRAINERS": "1",
            "SEO_MIN_CONTENT_WORDS": "1",
        }
    )
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mongo-url",
        help="Existing loopback MongoDB URI. Omit to start a disposable local mongod.",
    )
    args = parser.parse_args()

    db_name = f"dtd_integration_{uuid.uuid4().hex}"
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    client: MongoClient | None = None
    mongo_process: subprocess.Popen[str] | None = None
    mongo_data_dir: tempfile.TemporaryDirectory[str] | None = None
    process: subprocess.Popen[str] | None = None

    try:
        if args.mongo_url:
            _require_local_mongo(args.mongo_url)
            mongo_url = args.mongo_url
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        else:
            client, mongo_process, mongo_data_dir = _start_ephemeral_mongo()
            mongo_url = client.address and f"mongodb://{client.address[0]}:{client.address[1]}"
            if not mongo_url:
                raise RuntimeError("Ephemeral MongoDB did not expose a loopback address")
        client.admin.command("ping")
        client[db_name].trainers.insert_one(_fixture_trainer())
        env = _server_environment(mongo_url, db_name, base_url)
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _wait_for_api(base_url, process)
        result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=BACKEND_DIR, env=env)
        return result.returncode
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=4)
        if client is not None:
            try:
                client.drop_database(db_name)
            finally:
                client.close()
        if mongo_process and mongo_process.poll() is None:
            mongo_process.terminate()
            try:
                mongo_process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                mongo_process.kill()
                mongo_process.wait(timeout=4)
        if mongo_data_dir is not None:
            mongo_data_dir.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
