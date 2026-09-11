from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class FollowUpTokenInvalid(Exception):
    pass


class FollowUpTokenExpired(Exception):
    pass


def follow_up_token_ttl_s() -> int:
    raw = (
        os.environ.get("FOLLOW_UP_LINK_TTL_S")
        or os.environ.get("TRAINER_ACTION_TOKEN_TTL_S")
        or "1209600"
    ).strip()
    try:
        ttl_s = int(raw)
    except ValueError:
        ttl_s = 1209600
    return max(60, ttl_s)


def legacy_intro_id_support_until() -> Optional[datetime]:
    raw = (os.environ.get("FOLLOW_UP_LEGACY_INTRO_ID_SUPPORT_UNTIL") or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _secret() -> str:
    secret = (os.environ.get("FOLLOW_UP_TOKEN_SECRET") or "").strip()
    if secret:
        return secret
    trainer_fallback = (os.environ.get("TRAINER_ACTION_TOKEN_SECRET") or "").strip()
    if trainer_fallback:
        return trainer_fallback
    admin_fallback = (os.environ.get("ADMIN_PASS") or "").strip()
    if admin_fallback:
        return admin_fallback
    raise RuntimeError(
        "FOLLOW_UP_TOKEN_SECRET, TRAINER_ACTION_TOKEN_SECRET, or ADMIN_PASS is required for follow-up tokens."
    )


def _token_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _token_unb64(raw: str) -> bytes:
    padded = raw + "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def issue_follow_up_token(*, intro_id: str, ttl_s: int | None = None) -> str:
    exp_epoch = int(datetime.now(timezone.utc).timestamp()) + max(60, int(ttl_s or follow_up_token_ttl_s()))
    payload = {
        "kind": "follow_up",
        "intro_id": intro_id,
        "exp": exp_epoch,
    }
    payload_blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_secret().encode("utf-8"), payload_blob, hashlib.sha256).digest()
    return f"{_token_b64(payload_blob)}.{_token_b64(sig)}"


def verify_follow_up_token(token: str) -> Dict[str, Any]:
    raw = (token or "").strip()
    if "." not in raw:
        raise FollowUpTokenInvalid("Missing or invalid follow-up token.")
    payload_part, sig_part = raw.split(".", 1)
    try:
        payload_blob = _token_unb64(payload_part)
        provided_sig = _token_unb64(sig_part)
    except Exception as exc:  # noqa: BLE001
        raise FollowUpTokenInvalid("Invalid follow-up token encoding.") from exc

    expected_sig = hmac.new(_secret().encode("utf-8"), payload_blob, hashlib.sha256).digest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise FollowUpTokenInvalid("Invalid follow-up token signature.")

    try:
        payload = json.loads(payload_blob.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise FollowUpTokenInvalid("Invalid follow-up token payload.") from exc

    if str(payload.get("kind") or "") != "follow_up":
        raise FollowUpTokenInvalid("Invalid follow-up token kind.")
    intro_id = str(payload.get("intro_id") or "").strip()
    if not intro_id:
        raise FollowUpTokenInvalid("Missing follow-up intro id.")

    token_exp = int(payload.get("exp") or 0)
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    if token_exp <= now_epoch:
        raise FollowUpTokenExpired("Follow-up token expired.")

    return payload
