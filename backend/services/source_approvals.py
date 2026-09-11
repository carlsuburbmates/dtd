"""Fail-closed approval registry for provider-backed trainer ingestion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "ingestion_source_approvals.json"


def load(path: Path = DEFAULT_PATH) -> Dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "sources": [], "state": "approval_registry_missing"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "sources": [], "state": "approval_registry_invalid"}
    return value if isinstance(value, dict) else {"version": 1, "sources": [], "state": "approval_registry_invalid"}


def approved(registry: Dict[str, Any], provider: str, use: str) -> bool:
    for row in registry.get("sources") or []:
        if not isinstance(row, dict) or str(row.get("provider") or "") != provider:
            continue
        uses = {str(item) for item in row.get("approved_uses") or []}
        if (
            row.get("approved") is True
            and use in uses
            and str(row.get("terms_reviewed_at") or "").strip()
            and str(row.get("approved_by") or "").strip()
        ):
            return True
    return False
