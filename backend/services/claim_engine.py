"""Security primitives for trainer profile claim challenges."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

DEFAULT_OTP_TTL_S = 900  # 15 minutes
DEFAULT_MAX_ATTEMPTS = 5  # Max 5 failed attempts before lock
DEFAULT_CLAIM_SESSION_TTL_S = 86400  # 24 hours


def otp_secret() -> str:
    return (
        os.environ.get("TRAINER_CLAIM_OTP_SECRET")
        or os.environ.get("TRAINER_ACTION_TOKEN_SECRET")
        or os.environ.get("ADMIN_PASS")
        or ""
    ).strip()


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def otp_digest(otp: str, *, secret: str | None = None) -> str:
    key = (secret if secret is not None else otp_secret()).encode("utf-8")
    if not key:
        raise RuntimeError("TRAINER_CLAIM_OTP_SECRET or TRAINER_ACTION_TOKEN_SECRET is required for claim verification.")
    return hmac.new(key, str(otp).encode("utf-8"), hashlib.sha256).hexdigest()


def otp_matches(otp: str, digest: str, *, secret: str | None = None) -> bool:
    return hmac.compare_digest(otp_digest(otp, secret=secret), str(digest or ""))


def mask_email(email: str) -> str:
    local, separator, domain = str(email or "").strip().partition("@")
    if not separator or not local or not domain:
        return ""
    return f"{local[0]}***@{domain}"
