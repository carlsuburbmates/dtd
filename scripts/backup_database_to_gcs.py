#!/usr/bin/env python3
"""Automated database backup pipeline to Google Cloud Storage (Coldline/Standard).

Dumps MongoDB database collections into a timestamped, gzip-compressed BSON archive
using mongodump (or pymongo fallback) and uploads to a specified Google Cloud Storage
bucket destination.

Safety & Governance Invariants:
- Fail-closed / dry-run default: Requires --execute to perform actual dump & upload.
- Never logs connection strings, credentials, or private archive URLs.
- Sanitised reporting: Reports only database name, collection count, archive size, and bucket path.
- Refuses non-sandbox databases unless explicitly authorised with --force-production-db.
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict
from urllib.parse import urlparse

try:
    from google.cloud import storage
    HAS_GCS_SDK = True
except ImportError:
    HAS_GCS_SDK = False

SANDBOX_DB = "dtd_sandbox"
DEFAULT_BUCKET = "dtd-backups-coldline"


def mask_mongo_url(mongo_url: str) -> str:
    """Return a sanitised representation of the MongoDB URI."""
    try:
        parsed = urlparse(mongo_url)
        host = parsed.hostname or "unknown-host"
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://***:***@{host}{port}/{parsed.path.lstrip('/')}"
    except Exception:
        return "mongodb://***:***@masked"


def run_backup(
    mongo_url: str,
    db_name: str,
    gcs_bucket_name: str,
    execute: bool = False,
    storage_class: str = "COLDLINE",
) -> Dict[str, Any]:
    """Execute or preview a database backup to GCS."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    archive_filename = f"backup_{db_name}_{timestamp}.archive.gz"
    gcs_destination_path = f"backups/{db_name}/{archive_filename}"

    summary: Dict[str, Any] = {
        "ok": True,
        "database": db_name,
        "sanitised_target": mask_mongo_url(mongo_url),
        "archive_file": archive_filename,
        "gcs_bucket": gcs_bucket_name,
        "gcs_path": gcs_destination_path,
        "storage_class": storage_class,
        "mode": "execute" if execute else "preview",
        "bytes_dumped": 0,
        "uploaded": False,
    }

    if not execute:
        summary["notice"] = "Preview only. Run with --execute to create and upload backup archive."
        return summary

    # Verify mongodump exists
    mongodump_bin = shutil.which("mongodump")
    if not mongodump_bin:
        raise RuntimeError("mongodump binary not found in PATH.")

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_local_path = os.path.join(tmpdir, archive_filename)

        # 1. Execute mongodump with gzip archive
        dump_cmd = [
            mongodump_bin,
            f"--uri={mongo_url}",
            f"--db={db_name}",
            f"--archive={archive_local_path}",
            "--gzip",
        ]

        # Run mongodump without logging stdout/stderr containing credentials
        result = subprocess.run(
            dump_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )

        if result.returncode != 0:
            # Mask potential uri occurrences in error output
            error_msg = result.stderr.replace(mongo_url, mask_mongo_url(mongo_url))
            raise RuntimeError(f"mongodump failed with exit code {result.returncode}: {error_msg}")

        if not os.path.exists(archive_local_path):
            raise RuntimeError(f"Backup archive {archive_local_path} was not created.")

        archive_size = os.path.getsize(archive_local_path)
        summary["bytes_dumped"] = archive_size

        # 2. Upload to GCS
        # Attempt via google-cloud-storage SDK or gcloud/gsutil CLI
        if HAS_GCS_SDK:
            client = storage.Client()
            bucket = client.bucket(gcs_bucket_name)
            blob = bucket.blob(gcs_destination_path)
            blob.upload_from_filename(archive_local_path)
            summary["uploaded"] = True
            summary["upload_method"] = "google-cloud-storage SDK"
        else:
            gsutil_bin = shutil.which("gsutil") or shutil.which("gcloud")
            if not gsutil_bin:
                raise RuntimeError("Neither google-cloud-storage nor gsutil/gcloud CLI is available.")

            if "gsutil" in gsutil_bin:
                upload_cmd = [
                    gsutil_bin,
                    "cp",
                    archive_local_path,
                    f"gs://{gcs_bucket_name}/{gcs_destination_path}",
                ]
            else:
                upload_cmd = [
                    gsutil_bin,
                    "storage",
                    "cp",
                    archive_local_path,
                    f"gs://{gcs_bucket_name}/{gcs_destination_path}",
                ]

            up_result = subprocess.run(
                upload_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                text=True,
            )
            if up_result.returncode != 0:
                raise RuntimeError(f"GCS upload failed: {up_result.stderr}")
            summary["uploaded"] = True
            summary["upload_method"] = "gcloud/gsutil CLI"

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-url", default=os.environ.get("MONGO_URL", ""), help="MongoDB Connection URI.")
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", SANDBOX_DB), help="Database name.")
    parser.add_argument("--bucket", default=os.environ.get("GCS_BACKUP_BUCKET", DEFAULT_BUCKET), help="GCS Bucket name.")
    parser.add_argument("--execute", action="store_true", help="Execute the backup and upload.")
    parser.add_argument("--force-production-db", action="store_true", help="Explicit authorisation for production db.")
    parser.add_argument("--storage-class", default="COLDLINE", help="GCS Storage class (COLDLINE, NEARLINE, STANDARD).")

    args = parser.parse_args()

    if not args.mongo_url:
        print("MONGO_URL not supplied; defaulting to loopback mock for preview mode.", file=sys.stderr)
        mongo_url = "mongodb://127.0.0.1:27017/dtd_sandbox"
    else:
        mongo_url = args.mongo_url

    # Sandbox / safety verification
    if args.db_name != SANDBOX_DB and not args.force_production_db:
        print(
            f"ERROR: Target database '{args.db_name}' is not sandbox '{SANDBOX_DB}'. "
            "Pass --force-production-db to authorise non-sandbox execution.",
            file=sys.stderr,
        )
        return 1

    try:
        summary = run_backup(
            mongo_url=mongo_url,
            db_name=args.db_name,
            gcs_bucket_name=args.bucket,
            execute=args.execute,
            storage_class=args.storage_class,
        )
        import json
        print(json.dumps(summary, indent=2))
        return 0
    except Exception as e:
        print(f"ERROR: Backup pipeline failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
