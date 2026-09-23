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
import socket
import subprocess
import sys
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


def _fixture_trainer() -> Dict[str, object]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": "integration-fixture-trainer",
        "slug": "integration-fixture-dog-training",
        "name": "Integration Fixture Dog Training",
        "suburb": "Fitzroy",
        "region": "Greater Melbourne",
        "published": True,
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
    parser.add_argument("--mongo-url", default="mongodb://127.0.0.1:27017")
    args = parser.parse_args()
    _require_local_mongo(args.mongo_url)

    db_name = f"dtd_integration_{uuid.uuid4().hex}"
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    client = MongoClient(args.mongo_url, serverSelectionTimeoutMS=2000)
    process: subprocess.Popen[str] | None = None

    try:
        client.admin.command("ping")
        client[db_name].trainers.insert_one(_fixture_trainer())
        env = _server_environment(args.mongo_url, db_name, base_url)
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
        client.drop_database(db_name)
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
