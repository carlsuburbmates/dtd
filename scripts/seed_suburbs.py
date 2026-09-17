#!/usr/bin/env python3
"""Validate or idempotently seed DTD's canonical 539-suburb collection."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import suburb_catalogue  # noqa: E402


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_sha256() -> str:
    return hashlib.sha256(suburb_catalogue.CATALOGUE_PATH.read_bytes()).hexdigest()


def database_document(row: Dict[str, Any], *, timestamp: str) -> Dict[str, Any]:
    return {
        **row,
        "id": f"vic:{row['slug']}",
        "catalogue_version": suburb_catalogue.CATALOGUE_VERSION,
        "catalogue_source_sha256": source_sha256(),
        "active": True,
        "updated_at": timestamp,
    }


def comparable_document(row: Dict[str, Any]) -> Dict[str, Any]:
    ignored = {"_id", "created_at", "updated_at"}
    return {key: value for key, value in row.items() if key not in ignored}


async def seed_suburbs(db: Any, *, apply: bool) -> Dict[str, Any]:
    rows = suburb_catalogue.canonical_suburbs()
    collection = db.suburbs
    existing_rows = await collection.find({}, {"_id": 0}).to_list(2000)
    existing = {str(row.get("slug") or ""): row for row in existing_rows}
    timestamp = now_iso()
    summary = {
        "mode": "apply" if apply else "dry_run",
        "source_records": len(rows),
        "existing_records": len(existing_rows),
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "unmanaged_preserved": len(set(existing) - {str(row["slug"]) for row in rows}),
        "source_sha256": source_sha256(),
    }

    if apply:
        await collection.create_index("slug", unique=True)
        await collection.create_index("id", unique=True)
        await collection.create_index("suburb_name")
        await collection.create_index("region_cluster")

    for row in rows:
        slug = str(row["slug"])
        desired = database_document(row, timestamp=timestamp)
        current = existing.get(slug)
        if current is None:
            summary["created"] += 1
        elif comparable_document(current) == comparable_document(desired):
            summary["unchanged"] += 1
            continue
        else:
            summary["updated"] += 1

        if apply:
            await collection.update_one(
                {"slug": slug},
                {
                    "$set": desired,
                    "$setOnInsert": {"created_at": timestamp},
                },
                upsert=True,
            )

    if apply:
        audit = getattr(db, "audit_log", None)
        if audit is not None and hasattr(audit, "insert_one"):
            await audit.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "action": "canonical_suburb_catalogue_seeded",
                    "target": "suburbs:v1",
                    "before": {"existing_records": len(existing_rows)},
                    "after": dict(summary),
                    "actor": "technical_owner",
                    "ts": timestamp,
                }
            )
    return summary


async def run_cli(args: argparse.Namespace) -> int:
    payload = suburb_catalogue.load_catalogue()
    if not args.apply and not args.compare_database:
        print(
            json.dumps(
                {
                    "mode": "validate_only",
                    "records": len(payload["suburbs"]),
                    "source_sha256": source_sha256(),
                },
                indent=2,
            )
        )
        return 0

    load_dotenv(BACKEND_DIR / ".env")
    mongo_url = args.mongo_url or os.environ.get("MONGO_URL") or os.environ.get("MONGODB_URI")
    if not mongo_url:
        print("MONGO_URL is required for --apply or --compare-database", file=sys.stderr)
        return 1

    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
        summary = await seed_suburbs(
            client[args.db_name or os.environ.get("DB_NAME") or "dtd"],
            apply=bool(args.apply),
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Write idempotent upserts and an audit event")
    mode.add_argument(
        "--compare-database",
        action="store_true",
        help="Compare the configured database without writing (default only validates the file)",
    )
    parser.add_argument("--mongo-url", default="")
    parser.add_argument("--db-name", default="")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_cli(args)))


if __name__ == "__main__":
    main()
