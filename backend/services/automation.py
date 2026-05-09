"""Automation helpers for discovery input and outreach messaging.

These workflows are intentionally fail-soft:
- If config or credentials are missing, they no-op and report status.
- They are idempotent via database checks to avoid duplicate queue rows/emails.
"""

from __future__ import annotations

import os
import re
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import requests


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_csv(value: str) -> List[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def _parse_int_env(name: str, default: int, *, minimum: int = 1, maximum: int = 10_000) -> int:
    raw = (os.environ.get(name) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _parse_iso(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _extract_links(html: str, base_url: str) -> List[str]:
    # Lightweight link extraction without extra parser dependencies.
    hrefs = re.findall(r'href=[\'"]([^\'"]+)[\'"]', html, flags=re.IGNORECASE)
    out: List[str] = []
    for href in hrefs:
        u = urljoin(base_url, href.strip())
        parsed = urlparse(u)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            out.append(u)
    return list(dict.fromkeys(out))


def _candidate_link(url: str) -> bool:
    u = url.lower()
    needles = ("dog", "trainer", "training", "k9", "canine", "obedience", "behaviour")
    return any(n in u for n in needles)


async def ingest_discovery_sources(db) -> Dict[str, Any]:
    """Scan configured source pages and enqueue candidate URLs for discovery."""
    sources = _parse_csv(os.environ.get("DISCOVERY_SOURCE_URLS", ""))
    if not sources:
        return {"ok": True, "skipped": True, "reason": "no_sources_configured", "sources": 0, "queued": 0}

    suppress_after_failures = _parse_int_env("SOURCE_INGEST_FAILURE_SUPPRESS_AFTER", 3, minimum=1, maximum=50)
    suppress_hours = _parse_int_env("SOURCE_INGEST_SUPPRESS_HOURS", 24, minimum=1, maximum=720)
    alert_after_failures = _parse_int_env("SOURCE_INGEST_ALERT_AFTER", 2, minimum=1, maximum=50)

    queued = 0
    scanned = 0
    failed = 0
    skipped_suppressed = 0
    suppressed_now = 0
    alerts: List[Dict[str, Any]] = []
    now_dt = _now()
    for src in sources:
        state = await db.source_ingestion_state.find_one({"source_url": src}, {"_id": 0}) or {}
        suppressed_until = _parse_iso(str(state.get("suppressed_until") or ""))
        if suppressed_until and suppressed_until > now_dt:
            skipped_suppressed += 1
            suppressed_now += 1
            continue

        scanned += 1
        try:
            r = requests.get(src, timeout=20)
            r.raise_for_status()
            links = _extract_links(r.text, src)
            candidates = [u for u in links if _candidate_link(u)]
            for candidate in candidates:
                exists = await db.discovery_queue.find_one({"url": candidate}, {"_id": 0, "id": 1})
                if exists:
                    continue
                digest = hashlib.sha1(f"{src}|{candidate}".encode("utf-8")).hexdigest()[:20]
                doc = {
                    "id": f"src-{digest}",
                    "url": candidate,
                    "hint_name": "",
                    "hint_suburb": "",
                    "hint_bio": "",
                    "source": f"source_scan:{src}",
                    "status": "pending",
                    "created_at": _now_iso(),
                }
                await db.discovery_queue.insert_one(doc)
                queued += 1
            await db.source_ingestion_state.update_one(
                {"source_url": src},
                {"$set": {
                    "source_url": src,
                    "last_checked_at": _now_iso(),
                    "last_ok_at": _now_iso(),
                    "last_error": "",
                    "last_http_status": r.status_code,
                    "consecutive_failures": 0,
                    "suppressed_until": "",
                    "last_candidates_seen": len(candidates),
                }},
                upsert=True,
            )
        except Exception:
            failed += 1
            prev_failures = int(state.get("consecutive_failures") or 0)
            new_failures = prev_failures + 1
            suppressed_until_value = ""
            if new_failures >= suppress_after_failures:
                suppressed_until_value = (now_dt + timedelta(hours=suppress_hours)).isoformat()
                suppressed_now += 1
            if new_failures >= alert_after_failures:
                alerts.append(
                    {
                        "severity": "medium",
                        "type": "source_ingestion_failures",
                        "source": src,
                        "consecutive_failures": new_failures,
                        "suppressed_until": suppressed_until_value,
                    }
                )
            await db.source_ingestion_state.update_one(
                {"source_url": src},
                {"$set": {
                    "source_url": src,
                    "last_checked_at": _now_iso(),
                    "last_error": "request_failed",
                    "last_http_status": 0,
                    "consecutive_failures": new_failures,
                    "suppressed_until": suppressed_until_value,
                }},
                upsert=True,
            )

    return {
        "ok": True,
        "skipped": False,
        "reason": "",
        "sources": scanned,
        "failed_sources": failed,
        "skipped_suppressed": skipped_suppressed,
        "suppressed_sources": suppressed_now,
        "queued": queued,
        "alerts": alerts,
        "suppress_after_failures": suppress_after_failures,
        "suppress_hours": suppress_hours,
    }


def _outreach_html(trainer_name: str) -> str:
    safe = trainer_name or "your trainer"
    return (
        "<p>Quick follow-up from Bark&amp;Bond.</p>"
        f"<p>Did you hire <strong>{safe}</strong>?</p>"
        "<p>If yes, please confirm in your Bark&amp;Bond session. This helps improve match quality.</p>"
    )


def _public_app_base_url() -> str:
    return (
        (os.environ.get("FRONTEND_BASE_URL") or "")
        .strip()
        .rstrip("/")
    )


async def send_t7_outreach(db) -> Dict[str, Any]:
    """Send a T+7 day follow-up email for intros with no conversion signal."""
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    resend_from = (os.environ.get("RESEND_FROM") or "no-reply@dogtrainersdirectory.com.au").strip()
    resend_reply_to = (os.environ.get("RESEND_REPLY_TO") or "info@dogtrainersdirectory.com.au").strip()
    if not api_key:
        return {"ok": True, "skipped": True, "reason": "no_resend_api_key", "checked": 0, "sent": 0}

    cutoff = _now() - timedelta(days=7)
    cursor = db.intros.find({"user_email": {"$ne": ""}}, {"_id": 0}).limit(5000)

    checked = 0
    sent = 0
    failed = 0
    async for intro in cursor:
        checked += 1
        created = _parse_iso(intro.get("created_at", ""))
        if not created or created > cutoff:
            continue

        intro_id = intro.get("id")
        if not intro_id:
            continue

        prior = await db.outreach_events.find_one({"intro_id": intro_id, "kind": "t7_hire_check"}, {"_id": 0, "id": 1})
        if prior:
            continue

        conv = await db.conversions.find_one({"intro_id": intro_id}, {"_id": 0, "id": 1})
        if conv:
            continue

        follow_up_html = _outreach_html(intro.get("trainer_name", ""))
        base = _public_app_base_url()
        if base:
            follow_link = f"{base}/follow-up/{intro_id}"
            follow_up_html += f'<p><a href="{follow_link}">Confirm outcome</a></p>'

        payload = {
            "from": resend_from,
            "to": [intro["user_email"]],
            "subject": "Quick follow-up on your dog trainer match",
            "html": follow_up_html,
            # Keep both fields to maximize downstream client compatibility.
            "reply_to": [resend_reply_to],
            "headers": {"Reply-To": resend_reply_to},
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            resp = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=20)
            ok = 200 <= resp.status_code < 300
            provider_id = ""
            try:
                provider_id = (resp.json() or {}).get("id", "")
            except Exception:
                provider_id = ""
            digest = hashlib.sha1(f"{intro_id}|{_now_iso()}|{provider_id or resp.status_code}".encode("utf-8")).hexdigest()[:20]
            await db.outreach_events.insert_one(
                {
                    "id": f"out-{digest}",
                    "intro_id": intro_id,
                    "kind": "t7_hire_check",
                    "provider": "resend",
                    "provider_id": provider_id,
                    "status": "sent" if ok else "failed",
                    "email": intro["user_email"],
                    "created_at": _now_iso(),
                    "http_status": resp.status_code,
                }
            )
            if ok:
                sent += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            digest = hashlib.sha1(f"{intro_id}|{_now_iso()}|err".encode("utf-8")).hexdigest()[:20]
            await db.outreach_events.insert_one(
                {
                    "id": f"out-{digest}",
                    "intro_id": intro_id,
                    "kind": "t7_hire_check",
                    "provider": "resend",
                    "provider_id": "",
                    "status": "failed",
                    "email": intro["user_email"],
                    "created_at": _now_iso(),
                    "http_status": 0,
                }
            )

    return {"ok": True, "skipped": False, "reason": "", "checked": checked, "sent": sent, "failed": failed}
