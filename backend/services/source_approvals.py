"""Fail-closed approval registry for provider-backed trainer ingestion."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, Tuple
from urllib.parse import urlparse


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


def _extract_hostname(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = f"https://{raw}"
    try:
        parsed = urlparse(raw)
        return (parsed.hostname or "").lower()
    except Exception:
        return ""


def is_candidate_url_approved(
    registry: Dict[str, Any],
    url: str,
    *,
    use: str = "trainer_profile_source",
) -> Tuple[bool, str]:
    """Verify that a candidate URL and its domain are authorized for trainer ingestion."""
    if not url or not isinstance(url, str) or not url.strip():
        return False, "missing_candidate_url"

    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        return False, "unsupported_url_scheme"

    domain = _extract_hostname(clean_url)
    if not domain:
        return False, "missing_domain"

    # Find the provider record that governs trainer profile sources
    approved_row = None
    for row in registry.get("sources") or []:
        if not isinstance(row, dict):
            continue
        uses = {str(item) for item in row.get("approved_uses") or []}
        if (
            row.get("approved") is True
            and use in uses
            and str(row.get("terms_reviewed_at") or "").strip()
            and str(row.get("approved_by") or "").strip()
        ):
            approved_row = row
            break

    if not approved_row:
        return False, f"no_approved_provider_for_use:{use}"

    # Check disallowed domains
    disallowed = [str(d).lower().strip() for d in approved_row.get("disallowed_domains") or []]
    for bad_domain in disallowed:
        if domain == bad_domain or domain.endswith(f".{bad_domain}"):
            return False, f"disallowed_domain:{domain}"

    if not _matches_approved_scope(approved_row, clean_url, domain):
        return False, f"unapproved_candidate_source:{domain}"
    return True, "approved"


def _normalized_source_url(url: str) -> str:
    """Normalize scheme/host only; paths and query values retain their meaning."""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username is not None or parsed.password is not None:
            return ""
        return parsed._replace(
            scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower(),
            path=parsed.path or "/", fragment="",
        ).geturl()
    except (TypeError, ValueError):
        return ""


def _matches_approved_scope(row: Dict[str, Any], url: str, domain: str) -> bool:
    normalized = _normalized_source_url(url)
    if not normalized:
        return False
    approved_urls = row.get("approved_source_urls") or []
    if approved_urls:
        return normalized in {_normalized_source_url(str(item)) for item in approved_urls}
    # Named hosts can be approved explicitly. Wildcards and implicit subdomains
    # cannot establish rights for a previously unreviewed source.
    approved_domains = {str(item).lower().strip() for item in row.get("approved_domains") or []}
    return domain in approved_domains and domain != "*"


def is_discovery_source_approved(
    registry: Dict[str, Any],
    source_url: str,
    *,
    use: str = "discovery_scan",
) -> Tuple[bool, str]:
    """Verify that a discovery scan source URL is explicitly authorized in the registry."""
    if not source_url or not isinstance(source_url, str) or not source_url.strip():
        return False, "missing_source_url"

    clean_url = source_url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        return False, "unsupported_url_scheme"

    domain = _extract_hostname(clean_url)
    if not domain:
        return False, "missing_domain"

    # Match an approved source entry for discovery scan
    for row in registry.get("sources") or []:
        if not isinstance(row, dict):
            continue
        uses = {str(item) for item in row.get("approved_uses") or []}
        if (
            row.get("approved") is True
            and use in uses
            and str(row.get("terms_reviewed_at") or "").strip()
            and str(row.get("approved_by") or "").strip()
        ):
            # Check disallowed domains first
            disallowed = [str(d).lower().strip() for d in row.get("disallowed_domains") or []]
            if any(domain == bad or domain.endswith(f".{bad}") for bad in disallowed):
                return False, f"disallowed_domain:{domain}"

            if _matches_approved_scope(row, clean_url, domain):
                return True, "approved"

    return False, f"unapproved_discovery_source:{domain}"

