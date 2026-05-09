from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_key() -> str:
    return (os.environ.get("RESEND_API_KEY") or "").strip()


def _from_email() -> str:
    return (os.environ.get("RESEND_FROM") or "no-reply@dogtrainersdirectory.com.au").strip()


def _reply_to_email() -> str:
    return (os.environ.get("RESEND_REPLY_TO") or "info@dogtrainersdirectory.com.au").strip()


def _retry_attempts() -> int:
    raw = (os.environ.get("NOTIFY_RETRY_ATTEMPTS") or "3").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 3
    return max(1, min(n, 5))


def _build_id(prefix: str, seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


async def _record_event(
    db,
    *,
    kind: str,
    target_kind: str,
    target_id: str,
    to_email: str,
    attempt: int,
    status: str,
    http_status: int,
    provider_id: str = "",
    error: str = "",
) -> None:
    event_id = _build_id(
        "notif",
        f"{kind}|{target_kind}|{target_id}|{to_email}|{attempt}|{status}|{provider_id}|{error}|{now_iso()}",
    )
    await db.notification_events.insert_one(
        {
            "id": event_id,
            "kind": kind,
            "target_kind": target_kind,
            "target_id": target_id,
            "to_email": to_email,
            "attempt": attempt,
            "status": status,
            "http_status": http_status,
            "provider": "resend",
            "provider_id": provider_id,
            "error": error[:240],
            "created_at": now_iso(),
        }
    )


async def _send_with_retry(
    db,
    *,
    target_kind: str,
    target_id: str,
    kind: str,
    to_email: str,
    subject: str,
    html: str,
) -> Dict[str, Any]:
    key = _api_key()
    if not key:
        await _record_event(
            db,
            kind=kind,
            target_kind=target_kind,
            target_id=target_id,
            to_email=to_email,
            attempt=0,
            status="skipped",
            http_status=0,
            error="no_resend_api_key",
        )
        return {"status": "skipped", "attempts": 0, "reason": "no_resend_api_key"}

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    reply_to_email = _reply_to_email()
    payload = {
        "from": _from_email(),
        "to": [to_email],
        "subject": subject,
        "html": html,
        # Resend accepts `reply_to`; we also set an explicit header so the
        # delivered MIME always carries Reply-To across providers.
        "reply_to": [reply_to_email],
        "headers": {"Reply-To": reply_to_email},
    }
    attempts = _retry_attempts()
    last_error = ""

    for attempt in range(1, attempts + 1):
        try:
            resp = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=20)
            ok = 200 <= resp.status_code < 300
            provider_id = ""
            try:
                provider_id = str((resp.json() or {}).get("id") or "")
            except Exception:  # noqa: BLE001
                provider_id = ""
            if ok:
                await _record_event(
                    db,
                    kind=kind,
                    target_kind=target_kind,
                    target_id=target_id,
                    to_email=to_email,
                    attempt=attempt,
                    status="sent",
                    http_status=resp.status_code,
                    provider_id=provider_id,
                )
                return {"status": "sent", "attempts": attempt, "provider_id": provider_id}
            last_error = f"http_{resp.status_code}"
            await _record_event(
                db,
                kind=kind,
                target_kind=target_kind,
                target_id=target_id,
                to_email=to_email,
                attempt=attempt,
                status="failed",
                http_status=resp.status_code,
                provider_id=provider_id,
                error=last_error,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)[:240]
            await _record_event(
                db,
                kind=kind,
                target_kind=target_kind,
                target_id=target_id,
                to_email=to_email,
                attempt=attempt,
                status="failed",
                http_status=0,
                error=last_error,
            )

    return {"status": "failed", "attempts": attempts, "error": last_error or "unknown"}


def _safe_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _public_app_base_url() -> str:
    return (
        (os.environ.get("FRONTEND_BASE_URL") or "")
        .strip()
        .rstrip("/")
    )


async def notify_trainer_new_intro(db, trainer: Dict[str, Any], intro: Dict[str, Any]) -> Dict[str, Any]:
    trainer_id = str(trainer.get("id") or "")
    email = _safe_text(trainer.get("billing_email")) or _safe_text(trainer.get("email"))
    if not email:
        return {
            "trainer_notification_status": "skipped",
            "trainer_notification_attempts": 0,
            "trainer_notification_reason": "missing_email",
        }

    subject = "New Bark&Bond intro"
    html = (
        f"<p>New intro for <strong>{_safe_text(trainer.get('name')) or 'your listing'}</strong>.</p>"
        f"<p>Owner: {_safe_text(intro.get('user_name')) or '(not provided)'}<br/>"
        f"Email: {_safe_text(intro.get('user_email')) or '(not provided)'}<br/>"
        f"Phone: {_safe_text(intro.get('user_phone')) or '(not provided)'}</p>"
        f"<p>Issue: {_safe_text(intro.get('description')) or '(not provided)'}</p>"
    )
    outcome = await _send_with_retry(
        db,
        target_kind="intro",
        target_id=str(intro.get("id") or ""),
        kind="trainer_intro_notification",
        to_email=email,
        subject=subject,
        html=html,
    )
    result = {
        "trainer_notification_status": outcome.get("status", "failed"),
        "trainer_notification_attempts": int(outcome.get("attempts") or 0),
    }
    if outcome.get("status") == "sent":
        result["trainer_notification_sent_at"] = now_iso()
    if outcome.get("error"):
        result["trainer_notification_error"] = str(outcome["error"])[:240]
    await db.trainers.update_one(
        {"id": trainer_id},
        {"$set": {"last_intro_notification_status": result["trainer_notification_status"], "last_intro_notification_at": now_iso()}},
    )
    return result


async def notify_submitter_result(db, submission: Dict[str, Any]) -> Dict[str, Any]:
    email = _safe_text(submission.get("submitter_email"))
    if not email:
        return {
            "submitter_notification_status": "skipped",
            "submitter_notification_attempts": 0,
            "submitter_notification_reason": "missing_submitter_email",
        }

    status = _safe_text(submission.get("status")) or "pending"
    name = _safe_text(submission.get("name")) or "listing"
    subject = f"Bark&Bond submission update: {status}"
    html = (
        f"<p>Your submission for <strong>{name}</strong> is now <strong>{status}</strong>.</p>"
        f"<p>Confidence score: {float(submission.get('confidence_score') or 0):.2f}</p>"
    )
    base = _public_app_base_url()
    if base and submission.get("id"):
        html += f'<p>Track status: <a href="{base}/submit/status/{submission.get("id")}">View submission status</a></p>'
    outcome = await _send_with_retry(
        db,
        target_kind="submission",
        target_id=str(submission.get("id") or ""),
        kind="submission_status_notification",
        to_email=email,
        subject=subject,
        html=html,
    )
    result = {
        "submitter_notification_status": outcome.get("status", "failed"),
        "submitter_notification_attempts": int(outcome.get("attempts") or 0),
    }
    if outcome.get("status") == "sent":
        result["submitter_notification_sent_at"] = now_iso()
    if outcome.get("error"):
        result["submitter_notification_error"] = str(outcome["error"])[:240]
    return result


async def notify_trainer_reactivation_candidate(
    db,
    trainer: Dict[str, Any],
    *,
    reasons: list[str],
) -> Dict[str, Any]:
    trainer_id = str(trainer.get("id") or "")
    email = _safe_text(trainer.get("billing_email")) or _safe_text(trainer.get("email"))
    if not email:
        return {
            "status": "skipped",
            "attempts": 0,
            "reason": "missing_email",
        }

    base = _public_app_base_url()
    reactivate_link = f"{base}/trainer/reactivate?trainerId={trainer_id}" if base else ""
    subject = "Bark&Bond listing reactivation recommended"
    reason_lines = "".join(f"<li>{_safe_text(r)}</li>" for r in reasons if _safe_text(r))
    html = (
        f"<p>Hi {_safe_text(trainer.get('name')) or 'there'},</p>"
        "<p>We detected listing signals that may reduce intros.</p>"
        f"<ul>{reason_lines or '<li>General listing health refresh recommended.</li>'}</ul>"
    )
    if reactivate_link:
        html += f'<p><a href="{reactivate_link}">Open reactivation checklist</a></p>'
    html += "<p>You can also reply to this email for support.</p>"

    outcome = await _send_with_retry(
        db,
        target_kind="trainer",
        target_id=trainer_id,
        kind="trainer_reactivation_notification",
        to_email=email,
        subject=subject,
        html=html,
    )
    return {
        "status": outcome.get("status", "failed"),
        "attempts": int(outcome.get("attempts") or 0),
        "error": str(outcome.get("error") or "")[:240],
    }
