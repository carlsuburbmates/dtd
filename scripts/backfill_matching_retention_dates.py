#!/usr/bin/env python3
"""Convert legacy sandbox matching expiry strings to MongoDB TTL datetimes.

The matching service now writes BSON datetimes to ``expires_at``. This helper
only repairs pre-existing developer-sandbox records; it refuses any other
database and is dry-run by default. It never prints a connection string or
record content.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
import sys
from typing import Any

from pymongo import MongoClient


SANDBOX_DB = "dtd_sandbox"
COLLECTIONS = ("match_events", "match_contexts")


def _parse_expiry(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Apply the conversion after previewing scope.")
    parser.add_argument("--mongo-url", default=os.environ.get("MONGO_URL", ""))
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", SANDBOX_DB))
    args = parser.parse_args()

    if args.db_name != SANDBOX_DB:
        raise SystemExit("Refusing a non-developer-sandbox database.")
    if not args.mongo_url:
        raise SystemExit("MONGO_URL is required through the environment or --mongo-url.")

    client = MongoClient(args.mongo_url, serverSelectionTimeoutMS=10_000)
    try:
        client.admin.command("ping")
        db = client[args.db_name]
        summary: dict[str, dict[str, int]] = {}
        for name in COLLECTIONS:
            collection = db[name]
            converted = invalid = 0
            for row in collection.find({"expires_at": {"$type": "string"}}, {"_id": 1, "expires_at": 1}):
                parsed = _parse_expiry(row.get("expires_at"))
                if parsed is None:
                    invalid += 1
                    continue
                if args.execute:
                    collection.update_one({"_id": row["_id"]}, {"$set": {"expires_at": parsed}})
                converted += 1
            summary[name] = {"converted" if args.execute else "would_convert": converted, "invalid": invalid}
        print({"ok": True, "database": args.db_name, "executed": bool(args.execute), "collections": summary})
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
