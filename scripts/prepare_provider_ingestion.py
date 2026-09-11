#!/usr/bin/env python3
"""Prepare legacy provider-readiness evidence without publishing data.

This command does not implement or approve the planned licensed Sensis/Thryv
discovery feed. Google Places remains excluded from persistent acquisition.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")

from services import provider_ingestion, source_approvals  # noqa: E402


async def run(args: argparse.Namespace) -> int:
    registry_path = Path(args.approvals).expanduser().resolve()
    registry = source_approvals.load(registry_path)
    mongo_url = os.environ.get("MONGO_URL") or os.environ.get("MONGODB_URI") or "mongodb://127.0.0.1:27017"
    db_name = os.environ.get("DB_NAME") or "dtd"
    client = None
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        db = client[db_name]
    except Exception:
        db = None

    result = await provider_ingestion.prepare_candidates(
        db,
        [part.strip() for part in args.suburbs.split(",") if part.strip()],
        registry=registry,
        allow_network=bool(args.allow_provider_network),
    )
    manifest = {
        "manifest_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "provider_dry_run",
        "approval_registry": {"path": str(registry_path), "state": registry.get("state"), "source_count": len(registry.get("sources") or [])},
        "credentials": {
            "google_places_api_key": "present" if os.environ.get("GOOGLE_PLACES_API_KEY") else "missing",
            "abr_guid": "present" if os.environ.get("ABR_GUID") else "missing",
        },
        **result,
    }
    output = json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n"
    if args.manifest:
        path = Path(args.manifest).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        print(path)
    else:
        print(output, end="")
    if client:
        client.close()
    return 0 if result.get("ok") else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a fail-closed legacy Places/ABR readiness manifest; never acquire or publish listings.")
    parser.add_argument("--suburbs", default="Richmond", help="Comma-separated approved Greater Melbourne suburbs.")
    parser.add_argument("--approvals", default=str(source_approvals.DEFAULT_PATH), help="Approved source-use registry JSON.")
    parser.add_argument("--manifest", default="", help="Optional output path; stdout is used when omitted.")
    parser.add_argument("--allow-provider-network", action="store_true", help="Allow provider reads only when source approvals and credentials also pass.")
    raise SystemExit(asyncio.run(run(parser.parse_args())))


if __name__ == "__main__":
    main()
