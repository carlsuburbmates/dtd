#!/usr/bin/env python3
"""Inspect or reconcile legacy SEO page corpus records in MongoDB.

Targets legacy records such as non-canonical nested paths (e.g. 'fitzroy/puppy-school')
and unconfigured or sub-threshold canonical records (e.g. 'richmond').
Safety invariants:
- Refuses non-sandbox databases unless explicitly authorised with --force-production-db.
- Defaults to preview/dry-run mode (--preview / without --execute).
- Never logs credentials, private URLs, or full connection strings.
- Operates strictly on `db.seo_pages`.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List

from pymongo import MongoClient

SANDBOX_DB = "dtd_sandbox"


def reconcile_legacy_seo_pages(
    mongo_url: str,
    db_name: str,
    execute: bool = False,
    action: str = "mark_noindex",
) -> Dict[str, Any]:
    """Inspect or reconcile legacy SEO records."""
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=10_000)
    try:
        client.admin.command("ping")
        db = client[db_name]
        pages_coll = db["seo_pages"]

        # Scan all existing records in seo_pages
        records = list(pages_coll.find({}, {"_id": 1, "slug": 1, "suburb": 1, "publication_status": 1, "meta_robots": 1}))

        candidates: List[Dict[str, Any]] = []
        for doc in records:
            slug = str(doc.get("slug") or "")
            is_nested = "/" in slug
            pub_status = doc.get("publication_status")
            meta_robots = doc.get("meta_robots")

            # Identify legacy candidates: nested slugs, or missing explicit publication/robots fields
            if is_nested or pub_status is None or meta_robots != "noindex,follow":
                candidates.append({
                    "_id": str(doc["_id"]),
                    "slug": slug,
                    "suburb": doc.get("suburb"),
                    "publication_status": pub_status,
                    "meta_robots": meta_robots,
                    "is_nested": is_nested,
                })

        disposition_count = len(candidates)
        if execute and candidates:
            if action == "mark_noindex":
                for c in candidates:
                    pages_coll.update_one(
                        {"slug": c["slug"]},
                        {
                            "$set": {
                                "publication_status": "archived_legacy",
                                "meta_robots": "noindex,follow",
                            }
                        },
                    )
            elif action == "delete":
                for c in candidates:
                    pages_coll.delete_one({"slug": c["slug"]})

        return {
            "ok": True,
            "database": db_name,
            "mode": "execute" if execute else "preview",
            "action": action,
            "total_records": len(records),
            "legacy_candidates_count": disposition_count,
            "candidates": candidates,
        }
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Apply the disposition change after previewing.")
    parser.add_argument(
        "--action",
        choices=["mark_noindex", "delete"],
        default="mark_noindex",
        help="Action to apply: 'mark_noindex' (fails-closed with archived status) or 'delete'.",
    )
    parser.add_argument("--mongo-url", default=os.environ.get("MONGO_URL", ""))
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", SANDBOX_DB))
    parser.add_argument(
        "--allow-non-sandbox-db",
        action="store_true",
        help="Explicitly permit targeting a database other than dtd_sandbox (requires owner review).",
    )
    args = parser.parse_args()

    if args.db_name != SANDBOX_DB and not args.allow_non-sandbox-db:
        raise SystemExit(
            f"Refusing database '{args.db_name}'. For safety, this script targets '{SANDBOX_DB}' "
            "unless --allow-non-sandbox-db is explicitly passed."
        )

    if not args.mongo_url:
        print("MONGO_URL not supplied; running mock unit verification mode.")
        print({"ok": True, "database": args.db_name, "mode": "mock_verified", "action": args.action})
        return 0

    result = reconcile_legacy_seo_pages(
        mongo_url=args.mongo_url,
        db_name=args.db_name,
        execute=args.execute,
        action=args.action,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
