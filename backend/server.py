"""Dog Trainers Directory — Greater Melbourne dog-training discovery and matching platform.

Design intent:
  - Open directory discovery and diagnostic matching for dog owners.
  - Digital storefronts, direct owner enquiries, and optional flat SaaS subscriptions
    (Pro $19/mo, Suburb Featured Sponsor $39/mo, Melbourne-Wide Sponsor $199/mo) for trainers.
  - Value precedes paid upgrades: zero per-intro fees, zero lead fees, and zero commissions.
  - The oversight surface is visibility-first and Normal Ops by default.
    It allows bounded Layer 1 review-state persistence; it does not
    mutate live policy, provider state, runtime, or direct data on a human's
    behalf.

Conventions:
  - All routes live under /api.
  - Mongo `_id` is excluded from every read.
  - The X-Admin-Pass header guards only /api/oversight/*.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import math
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode, urlparse

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Header, Request, Response, Query
from fastapi.responses import JSONResponse
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token as google_id_token
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pymongo.errors import DuplicateKeyError

try:
    import sentry_sdk
except Exception:  # pragma: no cover - optional observability dependency locally
    sentry_sdk = None
from starlette.middleware.cors import CORSMiddleware

from services import ai as ai_service
from services import claim_engine
from services import engine as autonomy
from services import event_contract
from services import follow_up_tokens
from services import fraud as fraud_service
from services import notifications as notifications_service
from services import provider_health
from services import pro_trials
from services import ingestion_manager
from services import pipeline_guardian
from services import trainer_quality
from services import runtime_control
from services import stripe_billing
from services import suburb_catalogue
from services import suburb_inventory
from services import matching_contract_v2
from services import urgent_providers as urgent_providers_service
from services.abr_client import AbrClient
from services.seed import MELBOURNE_TRAINERS

matching_ai_adapter: Optional[Any] = None

try:
    from bson import ObjectId
except Exception:  # noqa: BLE001
    ObjectId = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
mongo_timeout_ms = int(os.environ.get("MONGO_TIMEOUT_MS", "5000"))
mongo_max_pool = int(os.environ.get("MONGO_MAX_POOL_SIZE", "15"))
mongo_min_pool = int(os.environ.get("MONGO_MIN_POOL_SIZE", "1"))
mongo_client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=mongo_timeout_ms,
    maxPoolSize=mongo_max_pool,
    minPoolSize=mongo_min_pool,
)
db_name = os.environ.get("DB_NAME", "dtd")
db = mongo_client[db_name]

app = FastAPI(title="Dog Trainers Directory Match Engine")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dtd")

_SENTRY_INITIALIZED = False


def _initialise_sentry() -> bool:
    """Initialise Sentry in the process that serves API or worker work."""
    global _SENTRY_INITIALIZED
    if _SENTRY_INITIALIZED:
        return True

    dsn = (os.environ.get("SENTRY_DSN") or "").strip()
    if not dsn or sentry_sdk is None:
        return False

    environment = (os.environ.get("SENTRY_ENVIRONMENT") or "development").strip()
    try:
        traces_sample_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    except ValueError:
        traces_sample_rate = 0.1
        logger.warning("Invalid SENTRY_TRACES_SAMPLE_RATE; using 0.1")

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            send_default_pii=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Sentry initialization failed; continuing without Sentry")
        return False

    _SENTRY_INITIALIZED = True
    logger.info("Sentry initialized for environment=%s", environment)
    return True

TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}
STARTUP_SEEDS_ENV = "ENABLE_STARTUP_SEEDS"

PUBLISH_THRESHOLD = 0.85
HOLD_THRESHOLD = 0.60
ACTIVE_REGION = (os.environ.get("ACTIVE_REGION") or "Greater Melbourne").strip()
ACTIVE_REGIONS = [r.strip() for r in os.environ.get("ACTIVE_REGIONS", ACTIVE_REGION).split(",") if r.strip()]
ACTIVE_REGION_SET = {x.lower() for x in ACTIVE_REGIONS}
BILLABILITY_POLICY = (os.environ.get("BILLABILITY_POLICY") or "allow").strip().lower()
CONTACT_READY_POLICY = (os.environ.get("CONTACT_READY_POLICY") or "allow").strip().lower()

# Canonical target state. Keep the response keys for older clients, but do not
# allow environment flags to revive superseded intro-fee or founding-tier copy.
PUBLIC_MONETIZATION_COPY_MODE = "flat_subscription"
PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY = True
PUBLIC_SHOW_FOUNDING_PROFILE_COPY = False

# Decommissioned marketing-claim gates (Task P1-A)
CLAIM_STATE_MODEL_ENABLED = False
CLAIM_STATE_CURRENT = "STATE_4"
CLAIM_ENFORCEMENT_MODE = "disabled"
CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2 = False
_public_launch_phase_env = (os.environ.get("PUBLIC_LAUNCH_PHASE") or "live_matching").strip().lower()
PUBLIC_LAUNCH_PHASE = (
    _public_launch_phase_env
    if _public_launch_phase_env in {"supply_first", "owner_waitlist", "live_matching", "growth"}
    else "live_matching"
)
TRAINER_ACTION_TOKEN_TTL_S = int((os.environ.get("TRAINER_ACTION_TOKEN_TTL_S") or "1209600").strip() or "1209600")
TRAINER_CLAIM_OTP_TTL_S = int((os.environ.get("TRAINER_CLAIM_OTP_TTL_S") or "900").strip() or "900")
TRAINER_CLAIM_OTP_MAX_ATTEMPTS = int((os.environ.get("TRAINER_CLAIM_OTP_MAX_ATTEMPTS") or "5").strip() or "5")
TRAINER_CLAIM_SESSION_TTL_S = int((os.environ.get("TRAINER_CLAIM_SESSION_TTL_S") or "86400").strip() or "86400")
TRAINER_CLAIM_RESEND_COOLDOWN_S = int((os.environ.get("TRAINER_CLAIM_RESEND_COOLDOWN_S") or "60").strip() or "60")
FOLLOW_UP_LINK_TTL_S = follow_up_tokens.follow_up_token_ttl_s()
OVERSIGHT_AUTH_MAX_ATTEMPTS = int((os.environ.get("OVERSIGHT_AUTH_MAX_ATTEMPTS") or "10").strip() or "10")
OVERSIGHT_AUTH_WINDOW_S = int((os.environ.get("OVERSIGHT_AUTH_WINDOW_S") or "600").strip() or "600")
OVERSIGHT_AUTH_LOCK_S = int((os.environ.get("OVERSIGHT_AUTH_LOCK_S") or "900").strip() or "900")

OPS_CASE_ALLOWED_STATES = {
    "detected",
    "acknowledged",
    "investigating",
    "actioned",
    "monitoring",
    "resolved",
    "deferred",
    "dismissed",
    "escalated_to_owner_override",
    "escalated_to_technical_owner",
}
OPS_CASE_HISTORY_LIMIT = 20
MATCH_TIE_BAND = 0.05
MATCH_TIEBREAK_TIER_WEIGHTS = {
    "citywide": 4,
    "suburb_sponsor": 3,
    "pro": 2,
    "claimed": 1,
}


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in TRUTHY_ENV_VALUES


def _startup_seeds_enabled(process_role: runtime_control.ProcessRole) -> bool:
    return process_role == "api" and _env_flag(STARTUP_SEEDS_ENV, default=False)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Any) -> Optional[datetime]:
    """Normalise an ISO string or MongoDB datetime to aware UTC.

    Match-retention timestamps are BSON datetimes so MongoDB TTL indexes can
    enforce deletion.  Older records may still contain ISO strings while the
    one-time backfill runs, so readers remain backwards-compatible.
    """
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _is_expired(value: Any) -> bool:
    parsed = _parse_iso(value)
    return parsed is not None and parsed <= datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items() if k != "_id"}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if ObjectId is not None and isinstance(value, ObjectId):
        return str(value)
    return value


def _scrub(doc: Dict[str, Any]) -> Dict[str, Any]:
    safe = _json_safe(doc)
    return safe if isinstance(safe, dict) else {}


async def _audit(action: str, target: str, before: Any = None, after: Any = None, actor: str = "system") -> None:
    try:
        audit_coll = getattr(db, "audit_log", None)
        if audit_coll is not None:
            await audit_coll.insert_one(
                {
                    "id": new_id(),
                    "action": action,
                    "target": target,
                    "before": before,
                    "after": after,
                    "actor": actor,
                    "ts": now_iso(),
                }
            )
    except Exception:  # noqa: BLE001
        logger.exception("audit write failed action=%s target=%s actor=%s", action, target, actor)


async def _resolve_follow_up_intro(token: str) -> Dict[str, Any]:
    raw = (token or "").strip()
    if "." in raw:
        try:
            payload = follow_up_tokens.verify_follow_up_token(raw)
        except follow_up_tokens.FollowUpTokenExpired as exc:
            raise HTTPException(status_code=410, detail="Follow-up link expired.") from exc
        except follow_up_tokens.FollowUpTokenInvalid as exc:
            raise HTTPException(status_code=404, detail="Follow-up link invalid.") from exc

        intro = await db.intros.find_one({"id": str(payload.get("intro_id") or "")}, {"_id": 0})
        if not intro:
            raise HTTPException(status_code=404, detail="Follow-up link invalid.")
        intro["follow_up_expires_at"] = datetime.fromtimestamp(
            int(payload["exp"]), tz=timezone.utc
        ).isoformat()
        intro["follow_up_token_mode"] = "signed"
        return intro

    intro = await db.intros.find_one({"id": raw}, {"_id": 0})
    if not intro:
        raise HTTPException(status_code=404, detail="Follow-up link invalid.")

    legacy_support_until = follow_up_tokens.legacy_intro_id_support_until()
    if legacy_support_until is not None and datetime.now(timezone.utc) >= legacy_support_until:
        raise HTTPException(
            status_code=410,
            detail="Follow-up link expired. Please use the latest follow-up email or contact support.",
        )

    reference_at = str(intro.get("follow_up_sent_at") or "")
    if not reference_at:
        outreach_coll = getattr(db, "outreach_events", None)
        if outreach_coll is not None:
            outreach = await outreach_coll.find_one(
                {"intro_id": intro["id"], "kind": "t7_hire_check"},
                {"_id": 0, "created_at": 1},
            ) or {}
            reference_at = str(outreach.get("created_at") or "")
    if not reference_at:
        reference_at = str(intro.get("created_at") or "")

    reference_dt = _parse_iso(reference_at)
    if reference_dt is not None:
        expires_at = reference_dt + timedelta(seconds=max(60, FOLLOW_UP_LINK_TTL_S))
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Follow-up link expired.")
        intro["follow_up_expires_at"] = expires_at.isoformat()
    intro["follow_up_token_mode"] = "legacy_intro_id"

    return intro


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def _oversight_auth_blocked(ip: str) -> bool:
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    row = await db.auth_attempts.find_one({"key": f"oversight:{ip}"}, {"_id": 0})
    if not row:
        return False
    return int(row.get("locked_until_epoch") or 0) > now_epoch


async def _record_oversight_auth_attempt(ip: str, *, success: bool) -> None:
    key = f"oversight:{ip}"
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    if success:
        await db.auth_attempts.delete_one({"key": key})
        return

    row = await db.auth_attempts.find_one({"key": key}, {"_id": 0}) or {}
    window_started = int(row.get("window_started_epoch") or now_epoch)
    failures = int(row.get("failures") or 0)
    if now_epoch - window_started > max(OVERSIGHT_AUTH_WINDOW_S, 1):
        window_started = now_epoch
        failures = 0
    failures += 1
    locked_until_epoch = int(row.get("locked_until_epoch") or 0)
    if failures >= max(OVERSIGHT_AUTH_MAX_ATTEMPTS, 1):
        locked_until_epoch = now_epoch + max(OVERSIGHT_AUTH_LOCK_S, 30)
        failures = 0
        window_started = now_epoch

    await db.auth_attempts.update_one(
        {"key": key},
        {
            "$set": {
                "key": key,
                "window_started_epoch": window_started,
                "failures": failures,
                "locked_until_epoch": locked_until_epoch,
                "updated_at": now_iso(),
            }
        },
        upsert=True,
    )


# ---------------------------------------------------------------------------
# Auth dependency (oversight passcode — read-only surface only)
# ---------------------------------------------------------------------------


async def require_oversight(request: Request, x_admin_pass: Optional[str] = Header(default=None)) -> None:
    ip = _client_ip(request)
    if await _oversight_auth_blocked(ip):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
    expected = os.environ.get("ADMIN_PASS")
    if not expected or x_admin_pass != expected:
        await _record_oversight_auth_attempt(ip, success=False)
        raise HTTPException(status_code=401, detail="Invalid passcode.")
    await _record_oversight_auth_attempt(ip, success=True)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class InstantMatchIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = Field(min_length=3)
    suburb: Optional[str] = None
    campaign: Optional[str] = None
    source: Optional[str] = None
    consent_match_processing: bool = False


class IntroIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: str
    description: str = Field(min_length=3, max_length=2000)
    user_email: EmailStr
    user_name: str = Field(min_length=1, max_length=120)
    user_phone: Optional[str] = None
    suburb: Optional[str] = None
    match_id: Optional[str] = None
    client_token: Optional[str] = None
    consent_contact_release: bool = False
    consent_outcome_tracking: bool = False


class MatchFollowUpIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: str
    user_name: str = Field(min_length=1, max_length=120)
    user_email: EmailStr
    user_phone: Optional[str] = None
    notes: Optional[str] = Field(default="", max_length=800)
    consent_contact_release: bool = False


class ConversionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    intro_id: str
    confirmed: bool = True


class EngagementIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    intro_id: str
    kind: str  # website_click | phone_click | email_click | return_visit
    trainer_id: Optional[str] = None


class ConnectClickIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    match_id: str
    trainer_id: str
    rank: Optional[int] = None
    campaign: Optional[str] = None
    source: Optional[str] = None


class DiscoveryIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str
    hint_name: Optional[str] = ""
    hint_suburb: Optional[str] = ""
    hint_bio: Optional[str] = ""
    source: Optional[str] = ""


class SubmissionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    suburb: str
    region: Optional[str] = ""
    website: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    categories: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    bio: Optional[str] = ""
    image_url: Optional[str] = ""
    source_evidence_url: Optional[str] = ""
    tier: Optional[str] = ""
    claim_status: Optional[str] = ""
    abn: Optional[str] = ""
    entity_name: Optional[str] = ""
    trading_name: Optional[str] = ""
    business_type: Optional[str] = ""
    abn_status: Optional[str] = ""
    abn_verified: Optional[bool] = False
    training_philosophy: Optional[str] = ""
    specialties: List[str] = Field(default_factory=list)
    service_formats: List[str] = Field(default_factory=list)
    serviced_suburbs: List[str] = Field(default_factory=list)
    catchment_type: Optional[str] = ""
    life_stages: List[str] = Field(default_factory=list)
    delivery_constraints: Optional[Dict[str, Any]] = None
    booking_url: Optional[str] = ""
    gallery_images: List[str] = Field(default_factory=list)
    sponsored_suburbs: List[str] = Field(default_factory=list)
    review_summary: Optional[str] = ""
    submitter_email: Optional[EmailStr] = None
    consent_public_listing: bool = False
    consent_information_accuracy: bool = False
    consent_intro_billing_terms: bool = False

    @field_validator("website", "booking_url", "image_url", "source_evidence_url")
    @classmethod
    def validate_external_url(cls, value: Optional[str]) -> str:
        return _safe_external_url(value, field_name="URL")

    @field_validator("gallery_images")
    @classmethod
    def validate_gallery_urls(cls, values: List[str]) -> List[str]:
        return [_safe_external_url(value, field_name="Gallery URL") for value in values]


class OwnerWaitlistJoinIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    suburb: str = Field(min_length=1)
    consent_owner_waitlist: bool = False
    campaign: Optional[str] = ""
    source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""


class AttributionEntryIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: str = "generic_entry"  # seo_landing | campaign_landing | home_entry | generic_entry
    campaign: Optional[str] = ""
    source: Optional[str] = ""
    suburb: Optional[str] = ""
    path: Optional[str] = ""
    session_id: Optional[str] = ""


class OversightLogin(BaseModel):
    model_config = ConfigDict(extra="ignore")
    passcode: str


class OpsCaseReviewIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    state: str
    owner: Optional[str] = ""
    note: Optional[str] = ""


class FollowUpOutcomeIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: str = "hired"  # hired | still_deciding | need_another_match


class TrainerBillingActionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: Optional[str] = None
    submission_id: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    trainer_action_token: Optional[str] = None


class TrainerCheckoutIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: str = Field(min_length=1)
    tier: str = Field(min_length=1)
    suburb: Optional[str] = ""
    interval: str = "month"
    consent_subscription_billing_terms: bool = False
    billing_terms_version: str = ""
    trainer_claim_session: Optional[str] = ""
    trainer_action_token: Optional[str] = ""


class TrainerPortalIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: str = Field(min_length=1)
    trainer_claim_session: Optional[str] = ""
    trainer_action_token: Optional[str] = ""


class OpsSubscriptionRefundIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: str = Field(min_length=1)
    stripe_subscription_id: str = Field(min_length=1)
    payment_intent_id: str = Field(min_length=1)
    reason: str = Field(min_length=3, max_length=240)


class TrainerReactivateIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: Optional[str] = None
    submission_id: Optional[str] = None
    trainer_action_token: Optional[str] = None


class TrainerClaimStartIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    method: str = "email"


class TrainerClaimVerifyIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    claim_event_id: str = Field(min_length=1)
    otp: str = Field(min_length=6, max_length=6)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verification_payload(t: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: t.get(k)
        for k in (
            "name",
            "suburb",
            "website",
            "phone",
            "email",
            "services",
            "categories",
            "bio",
            "source_evidence_url",
        )
    }


def _has_contact_channel(trainer: Dict[str, Any]) -> bool:
    return any((trainer.get("website"), trainer.get("phone"), trainer.get("email")))


def _is_billable_ready(trainer: Dict[str, Any]) -> bool:
    return True


def _region_allowed(region: Optional[str]) -> bool:
    if not region:
        return False
    return region.strip().lower() in ACTIVE_REGION_SET


def _require_region(region: Optional[str]) -> None:
    if not _region_allowed(region):
        allowed = ", ".join(ACTIVE_REGIONS)
        raise HTTPException(status_code=403, detail=f"Region not in active scope. Active region(s): {allowed}.")


def _normalize_suburb_key(raw_suburb: Optional[str]) -> str:
    return " ".join((raw_suburb or "").strip().lower().split())


def _normalize_email_key(raw_email: Optional[str]) -> str:
    return (raw_email or "").strip().lower()


def _trainer_action_secret() -> str:
    secret = (os.environ.get("TRAINER_ACTION_TOKEN_SECRET") or "").strip()
    if secret:
        return secret
    admin_fallback = (os.environ.get("ADMIN_PASS") or "").strip()
    if admin_fallback:
        return admin_fallback
    raise RuntimeError("TRAINER_ACTION_TOKEN_SECRET or ADMIN_PASS is required for trainer action tokens.")


def _scheduler_oidc_configuration() -> tuple[str, str]:
    return (
        (os.environ.get("CLOUD_SCHEDULER_OIDC_SERVICE_ACCOUNT") or "").strip(),
        (os.environ.get("CLOUD_SCHEDULER_OIDC_AUDIENCE") or "").strip(),
    )


def _require_cloud_scheduler_oidc(authorization: str, expected_route_audience: Optional[str] = None) -> None:
    expected_email, raw_audience = _scheduler_oidc_configuration()
    raw = (authorization or "").strip()
    scheme, _, token = raw.partition(" ")
    if not expected_email or not raw_audience or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid scheduler credential.")

    accepted_audiences = [a.strip() for a in raw_audience.split(",") if a.strip()]
    if expected_route_audience and expected_route_audience not in accepted_audiences:
        accepted_audiences.append(expected_route_audience)

    verified_claims = None
    last_exc = None
    for aud in accepted_audiences:
        try:
            claims = google_id_token.verify_oauth2_token(
                token.strip(),
                google_auth_requests.Request(),
                aud,
            )
            verified_claims = claims
            break
        except (google_auth_exceptions.GoogleAuthError, ValueError, TypeError) as exc:
            last_exc = exc
            continue

    if verified_claims is None:
        raise HTTPException(status_code=401, detail="Invalid scheduler credential.") from last_exc

    if verified_claims.get("email") != expected_email or verified_claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Invalid scheduler credential.")


def _token_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _token_unb64(raw: str) -> bytes:
    padded = raw + "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _issue_trainer_action_token(*, trainer_id: str, submission_id: str = "", ttl_s: int = TRAINER_ACTION_TOKEN_TTL_S) -> str:
    exp_epoch = int(datetime.now(timezone.utc).timestamp()) + max(60, ttl_s)
    payload = {
        "trainer_id": trainer_id,
        "submission_id": submission_id or "",
        "exp": exp_epoch,
    }
    payload_blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_trainer_action_secret().encode("utf-8"), payload_blob, hashlib.sha256).digest()
    return f"{_token_b64(payload_blob)}.{_token_b64(sig)}"


def _verify_trainer_action_token(
    token: str,
    *,
    trainer_id: str,
    submission_id: Optional[str] = None,
) -> None:
    raw = (token or "").strip()
    if "." not in raw:
        raise HTTPException(status_code=401, detail="Missing or invalid trainer action token.")
    payload_part, sig_part = raw.split(".", 1)
    try:
        payload_blob = _token_unb64(payload_part)
        provided_sig = _token_unb64(sig_part)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid trainer action token encoding.") from exc

    expected_sig = hmac.new(_trainer_action_secret().encode("utf-8"), payload_blob, hashlib.sha256).digest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid trainer action token signature.")

    try:
        payload = json.loads(payload_blob.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid trainer action token payload.") from exc

    token_trainer_id = str(payload.get("trainer_id") or "")
    token_submission_id = str(payload.get("submission_id") or "")
    token_exp = int(payload.get("exp") or 0)
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    if token_exp <= now_epoch:
        raise HTTPException(status_code=401, detail="Trainer action token expired.")
    if token_trainer_id != trainer_id:
        raise HTTPException(status_code=403, detail="Trainer action token does not match trainer context.")
    if submission_id and token_submission_id and token_submission_id != submission_id:
        raise HTTPException(status_code=403, detail="Trainer action token does not match submission context.")


def _issue_trainer_claim_session(*, trainer_id: str, claim_event_id: str) -> Dict[str, Any]:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, TRAINER_CLAIM_SESSION_TTL_S))
    payload = {
        "kind": "trainer_claim_session",
        "trainer_id": trainer_id,
        "claim_event_id": claim_event_id,
        "exp": int(expires_at.timestamp()),
    }
    payload_blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_trainer_action_secret().encode("utf-8"), payload_blob, hashlib.sha256).digest()
    return {"token": f"{_token_b64(payload_blob)}.{_token_b64(signature)}", "expires_at": expires_at.isoformat()}


def _verify_trainer_claim_session(token: str, *, trainer_id: str) -> Dict[str, Any]:
    """Verify the narrow post-claim session used for trainer self-service actions."""
    raw = (token or "").strip()
    if "." not in raw:
        raise HTTPException(status_code=401, detail="Missing or invalid trainer claim session.")
    payload_part, sig_part = raw.split(".", 1)
    try:
        payload_blob = _token_unb64(payload_part)
        provided_sig = _token_unb64(sig_part)
        payload = json.loads(payload_blob.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid trainer claim session encoding.") from exc
    expected_sig = hmac.new(_trainer_action_secret().encode("utf-8"), payload_blob, hashlib.sha256).digest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid trainer claim session signature.")
    if str(payload.get("kind") or "") != "trainer_claim_session":
        raise HTTPException(status_code=401, detail="Invalid trainer claim session kind.")
    if str(payload.get("trainer_id") or "") != trainer_id:
        raise HTTPException(status_code=403, detail="Trainer claim session does not match trainer context.")
    if int(payload.get("exp") or 0) <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=401, detail="Trainer claim session expired.")
    if not str(payload.get("claim_event_id") or ""):
        raise HTTPException(status_code=401, detail="Trainer claim session is incomplete.")
    return payload


async def _abn_profile_fields(raw_abn: Optional[str]) -> Dict[str, Any]:
    abn = (raw_abn or "").strip()
    if not abn:
        return {
            "abn": "",
            "entity_name": "",
            "trading_name": "",
            "business_type": "",
            "abn_status": "not_provided",
            "abn_verified": False,
        }
    result = await AbrClient(db).lookup(abn)
    if not result.get("ok"):
        return {
            "abn": str(result.get("abn") or abn),
            "entity_name": "",
            "trading_name": "",
            "business_type": "",
            "abn_status": str(result.get("state") or "abr_unavailable"),
            "abn_verified": False,
            "abn_verification_reason": str(result.get("reason") or "ABN could not be verified."),
            "abn_checked_at": now_iso(),
        }
    record = result.get("data") or {}
    entity_name = str(record.get("entity_name") or "").strip()
    business_names = record.get("business_names") or []
    trading_name = str(record.get("trading_name") or (business_names[0] if business_names else entity_name)).strip()
    business_type = str(record.get("business_type") or record.get("entity_type_name") or "").strip()
    return {
        "abn": str(record.get("abn") or abn),
        "entity_name": entity_name,
        "trading_name": trading_name,
        "business_type": business_type,
        "abn_status": str(record.get("abn_status") or result.get("state") or "unknown").lower(),
        "abn_verified": bool(record.get("is_active")),
        "abn_verified_at": now_iso() if record.get("is_active") else "",
        "abn_verification_reason": "active" if record.get("is_active") else "inactive",
        "abn_checked_at": now_iso(),
        "abn_badge_payload": {
            "abn": record.get("abn_formatted") or record.get("abn") or abn,
            "status": record.get("abn_status") or "Unknown",
            "entity_name": entity_name,
            "trading_name": trading_name,
            "business_type": business_type,
        },
    }


async def _record_owner_waitlist_event(
    event_type: str,
    *,
    email_norm: str = "",
    suburb_norm: str = "",
    status: str,
    reason_codes: Optional[List[str]] = None,
    waitlist_id: Optional[str] = None,
    campaign: str = "",
    source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
) -> None:
    normalized = event_contract.normalize_prelaunch_event(
        event_type,
        payload={
            "email_norm": email_norm,
            "suburb_norm": suburb_norm,
            "status": status,
            "reason_codes": reason_codes or [],
            "waitlist_id": waitlist_id,
            "campaign": campaign,
            "source": source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
        },
    )
    payload = normalized["payload"]
    await db.owner_waitlist_events.insert_one(
        {
            "id": new_id(),
            "event_type": normalized["event_type"],
            "email_norm": payload.get("email_norm") or "",
            "suburb_norm": payload.get("suburb_norm") or "",
            "status": payload.get("status") or "unknown",
            "reason_codes": payload.get("reason_codes") or [],
            "waitlist_id": payload.get("waitlist_id"),
            "campaign": payload.get("campaign") or "",
            "source": payload.get("source") or "",
            "utm_medium": payload.get("utm_medium") or "",
            "utm_campaign": payload.get("utm_campaign") or "",
            "contract_status": normalized["contract_status"],
            "contract_reason_codes": normalized["contract_reason_codes"],
            "created_at": now_iso(),
        }
    )


async def _owner_waitlist_summary() -> Dict[str, Any]:
    waitlist_coll = getattr(db, "owner_waitlist", None)
    waitlist_events_coll = getattr(db, "owner_waitlist_events", None)
    if waitlist_coll is None:
        return {
            "total_active": 0,
            "joins_24h": 0,
            "top_suburbs": [],
            "duplicate_24h": 0,
            "rejected_24h": 0,
            "duplicate_total": 0,
            "rejected_total": 0,
            "status": "unavailable",
            "reason_codes": ["owner_waitlist_collection_unavailable"],
        }

    since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    total_active = await waitlist_coll.count_documents({"status": "active"})
    joins_24h = await waitlist_coll.count_documents({"status": "active", "created_at": {"$gte": since_24h}})
    top_rows = await waitlist_coll.aggregate(
        [
            {"$match": {"status": "active"}},
            {"$group": {"_id": "$suburb", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
            {"$limit": 5},
        ]
    ).to_list(5)
    top_suburbs = [{"suburb": str(row.get("_id") or ""), "count": int(row.get("count") or 0)} for row in top_rows if row.get("_id")]
    duplicate_24h = 0
    rejected_24h = 0
    duplicate_total = 0
    rejected_total = 0
    if waitlist_events_coll is not None:
        duplicate_24h = int(
            await waitlist_events_coll.count_documents({"event_type": "owner_waitlist_duplicate", "created_at": {"$gte": since_24h}})
        )
        rejected_24h = int(
            await waitlist_events_coll.count_documents({"event_type": "owner_waitlist_rejected", "created_at": {"$gte": since_24h}})
        )
        duplicate_total = int(await waitlist_events_coll.count_documents({"event_type": "owner_waitlist_duplicate"}))
        rejected_total = int(await waitlist_events_coll.count_documents({"event_type": "owner_waitlist_rejected"}))
    return {
        "total_active": int(total_active or 0),
        "joins_24h": int(joins_24h or 0),
        "top_suburbs": top_suburbs,
        "duplicate_24h": duplicate_24h,
        "rejected_24h": rejected_24h,
        "duplicate_total": duplicate_total,
        "rejected_total": rejected_total,
        "status": "ok",
        "reason_codes": ["owner_waitlist_summary_ok"],
    }


async def _kpi_prelaunch_summary() -> Dict[str, Any]:
    """Read-only deterministic KPI rollup for prelaunch oversight."""
    # Repository accepted verified set (current canonical usage).
    verified_statuses = ["verified"]
    try:
        waitlist_coll = getattr(db, "owner_waitlist", None)
        trainers_coll = getattr(db, "trainers", None)
        if waitlist_coll is None or trainers_coll is None:
            return {
                "owner_waitlist_total_active": 0,
                "owner_waitlist_joins_24h": 0,
                "waitlist_suburb_coverage_count": 0,
                "published_trainer_count": 0,
                "verified_trainer_count": 0,
                "trainer_suburb_coverage_count": 0,
                "status": "unavailable",
                "reason_codes": ["kpi_prelaunch_collection_unavailable"],
            }

        since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        owner_waitlist_total_active = int(
            await waitlist_coll.count_documents({"status": "active"})
        )
        owner_waitlist_joins_24h = int(
            await waitlist_coll.count_documents({"status": "active", "created_at": {"$gte": since_24h}})
        )
        waitlist_suburbs = await waitlist_coll.distinct("suburb_norm", {"status": "active"})
        waitlist_suburb_coverage_count = len(
            [s for s in waitlist_suburbs if isinstance(s, str) and s.strip()]
        )

        published_trainer_count = int(await trainers_coll.count_documents({"published": True}))
        verified_trainer_count = int(
            await trainers_coll.count_documents(
                {"published": True, "verification_status": {"$in": verified_statuses}}
            )
        )
        trainer_suburbs = await trainers_coll.distinct("suburb", {"published": True})
        trainer_suburb_coverage_count = len(
            [s for s in trainer_suburbs if isinstance(s, str) and s.strip()]
        )
        return {
            "owner_waitlist_total_active": owner_waitlist_total_active,
            "owner_waitlist_joins_24h": owner_waitlist_joins_24h,
            "waitlist_suburb_coverage_count": int(waitlist_suburb_coverage_count),
            "published_trainer_count": published_trainer_count,
            "verified_trainer_count": verified_trainer_count,
            "trainer_suburb_coverage_count": int(trainer_suburb_coverage_count),
            "status": "ok",
            "reason_codes": ["kpi_prelaunch_ok"],
        }
    except Exception:  # noqa: BLE001
        logger.exception("kpi_prelaunch_summary_failed")
        return {
            "owner_waitlist_total_active": 0,
            "owner_waitlist_joins_24h": 0,
            "waitlist_suburb_coverage_count": 0,
            "published_trainer_count": 0,
            "verified_trainer_count": 0,
            "trainer_suburb_coverage_count": 0,
            "status": "unavailable",
            "reason_codes": ["kpi_prelaunch_compute_failed"],
        }


def _activation_state_for_submission(*, submission_status: str, billing_profile_status: str) -> str:
    status = (submission_status or "").strip().lower()
    if status == "held":
        return "held_for_review"
    if status == "pending":
        return "pending_autonomous_review"
    if status == "published":
        return "intro_ready"
    return "unknown"


async def _growth_attribution_summary() -> Dict[str, Any]:
    growth_coll = getattr(db, "growth_attribution", None)
    entries_coll = getattr(db, "attribution_entries", None)
    if growth_coll is None and entries_coll is None:
        return {
            "status": "unavailable",
            "reason_codes": ["growth_attribution_collections_unavailable"],
            "cohorts": [],
            "totals": {},
        }

    since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    cohorts: List[Dict[str, Any]] = []
    if growth_coll is not None:
        rows = await growth_coll.find({}, {"_id": 0}).to_list(100)
        for row in rows:
            cohorts.append(
                {
                    "campaign": str(row.get("campaign") or "unknown"),
                    "source": str(row.get("source") or "unknown"),
                    "matched": int(row.get("matched") or 0),
                    "connected": int(row.get("connected") or 0),
                    "converted": int(row.get("converted") or 0),
                    "remarketing_candidates": int(row.get("remarketing_candidates") or 0),
                    "conversion_gap_candidates": int(row.get("conversion_gap_candidates") or 0),
                    "entry_events_30d": int(row.get("entry_events_30d") or 0),
                    "waitlist_joins_30d": int(row.get("waitlist_joins_30d") or 0),
                    "updated_at": row.get("updated_at"),
                }
            )
        cohorts.sort(
            key=lambda x: (
                int(x.get("entry_events_30d", 0)),
                int(x.get("matched", 0)),
                int(x.get("connected", 0)),
            ),
            reverse=True,
        )

    entry_events_30d = 0
    if entries_coll is not None:
        entry_events_30d = int(await entries_coll.count_documents({"created_at": {"$gte": since_30d}}))

    totals = {
        "entry_events_30d": entry_events_30d,
        "cohort_count": len(cohorts),
        "matched_30d": sum(int(c.get("matched", 0)) for c in cohorts),
        "connected_30d": sum(int(c.get("connected", 0)) for c in cohorts),
        "converted_30d": sum(int(c.get("converted", 0)) for c in cohorts),
        "waitlist_joins_30d": sum(int(c.get("waitlist_joins_30d", 0)) for c in cohorts),
    }
    return {
        "status": "ok",
        "reason_codes": ["growth_attribution_summary_ok"],
        "cohorts": cohorts[:10],
        "totals": totals,
    }


async def _reactivation_summary() -> Dict[str, Any]:
    candidates_coll = getattr(db, "reactivation_candidates", None)
    trainers_coll = getattr(db, "trainers", None)
    if candidates_coll is None:
        return {
            "status": "unavailable",
            "reason_codes": ["reactivation_candidates_collection_unavailable"],
        }

    since_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    open_count = int(await candidates_coll.count_documents({"status": "open"}))
    resolved_recent_rows = await candidates_coll.find(
        {"status": "resolved", "resolved_at": {"$gte": since_7d}},
        {"_id": 0, "trainer_id": 1},
    ).to_list(1000)
    notified_7d = int(await candidates_coll.count_documents({"last_notified_at": {"$gte": since_7d}}))
    resolved_7d = len(resolved_recent_rows)
    active_after_resolution_7d = 0
    if trainers_coll is not None and resolved_recent_rows:
        for row in resolved_recent_rows:
            trainer_id = str(row.get("trainer_id") or "")
            if not trainer_id:
                continue
            trainer = await trainers_coll.find_one({"id": trainer_id}, {"_id": 0, "published": 1, "confidence_score": 1})
            if trainer and bool(trainer.get("published")) and float(trainer.get("confidence_score") or 0.0) >= HOLD_THRESHOLD:
                active_after_resolution_7d += 1

    return {
        "status": "ok",
        "reason_codes": ["reactivation_summary_ok"],
        "open_candidates": open_count,
        "resolved_7d": resolved_7d,
        "notified_7d": notified_7d,
        "active_after_resolution_7d": active_after_resolution_7d,
    }


async def _trainer_inventory_rows(limit: int = 200) -> List[Dict[str, Any]]:
    rows = await db.trainers.find(
        {},
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "suburb": 1,
            "published": 1,
            "verification_status": 1,
            "claim_status": 1,
            "confidence_score": 1,
            "billing_profile_status": 1,
            "website": 1,
            "phone": 1,
            "email": 1,
            "via_submission_id": 1,
            "via_discovery": 1,
            "source_evidence_url": 1,
            "updated_at": 1,
            "created_at": 1,
            "outcome_score": 1,
            "intros_30d": 1,
            "conversions_30d": 1,
        },
    ).sort("name", 1).to_list(limit)
    inventory: List[Dict[str, Any]] = []
    for trainer in rows:
        blocker_codes = _trainer_blocker_codes(trainer)
        trainer_id = str(trainer.get("id") or "")
        inventory.append(
            {
                "id": trainer_id,
                "name": trainer.get("name") or trainer_id or "unknown",
                "suburb": trainer.get("suburb") or "",
                "published": bool(trainer.get("published")),
                "verification_status": trainer.get("verification_status") or "unknown",
                "claim_status": trainer.get("claim_status") or "unclaimed",
                "intro_ready": _trainer_intro_ready(trainer),
                "confidence_score": float(trainer.get("confidence_score") or 0),
                "billing_profile_status": trainer.get("billing_profile_status") or "unknown",
                "blocker_codes": blocker_codes,
                "source_kind": _trainer_source_kind(trainer),
                "contact_channel_ready": _has_contact_channel(trainer),
                "outcome_score": float(trainer.get("outcome_score") or 0),
                "intros_30d": int(trainer.get("intros_30d") or 0),
                "conversions_30d": int(trainer.get("conversions_30d") or 0),
                "public_detail_path": f"/t/{trainer_id}" if trainer_id else "",
                "created_at": trainer.get("created_at"),
                "updated_at": trainer.get("updated_at") or trainer.get("created_at"),
            }
        )
    return inventory


def _window_start_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def _ops_supply_geography_summary(trainer_inventory: List[Dict[str, Any]], waitlist_summary: Dict[str, Any]) -> Dict[str, Any]:
    trainer_by_suburb: Dict[str, Dict[str, Any]] = {}
    for row in trainer_inventory:
        suburb = str(row.get("suburb") or "").strip()
        if not suburb:
            continue
        key = suburb.lower()
        meta = trainer_by_suburb.setdefault(
            key,
            {
                "suburb": suburb,
                "live_total": 0,
                "intro_ready_total": 0,
                "blocked_total": 0,
                "verified_total": 0,
            },
        )
        meta["live_total"] += 1
        if bool(row.get("intro_ready")):
            meta["intro_ready_total"] += 1
        blocker_codes = row.get("blocker_codes")
        if isinstance(blocker_codes, list) and blocker_codes:
            meta["blocked_total"] += 1
        if str(row.get("verification_status") or "") == "verified":
            meta["verified_total"] += 1

    trainer_suburbs = sorted(
        trainer_by_suburb.values(),
        key=lambda row: (row["intro_ready_total"], row["live_total"], row["suburb"].lower()),
        reverse=True,
    )
    waitlist_top_rows = waitlist_summary.get("top_suburbs")
    if not isinstance(waitlist_top_rows, list):
        waitlist_top_rows = []
    waitlist_top = [
        {
            "suburb": str(row.get("suburb") or ""),
            "demand_count": int(row.get("count") or 0),
            "trainer_live_total": int(trainer_by_suburb.get(str(row.get("suburb") or "").lower(), {}).get("live_total") or 0),
            "intro_ready_total": int(trainer_by_suburb.get(str(row.get("suburb") or "").lower(), {}).get("intro_ready_total") or 0),
        }
        for row in waitlist_top_rows
        if row.get("suburb")
    ]
    demand_gaps = [
        row for row in waitlist_top
        if int(row.get("trainer_live_total") or 0) == 0 or int(row.get("intro_ready_total") or 0) == 0
    ]
    return {
        "trainer_suburbs_top": trainer_suburbs[:8],
        "waitlist_suburbs_top": waitlist_top[:8],
        "demand_gaps": demand_gaps[:5],
        "trainer_suburb_coverage_count": len(trainer_suburbs),
        "waitlist_suburb_coverage_count": len([row for row in waitlist_top if row.get("suburb")]),
    }


def _pace_label(short_window: int, long_window: int, short_days: int, long_days: int) -> str:
    if long_window <= 0 and short_window <= 0:
        return "quiet"
    short_daily = short_window / max(1, short_days)
    long_daily = long_window / max(1, long_days)
    if long_daily == 0:
        return "rising" if short_daily > 0 else "quiet"
    ratio = short_daily / long_daily
    if ratio >= 1.2:
        return "rising"
    if ratio <= 0.8:
        return "slowing"
    return "steady"


async def _ops_supply_trend_summary(
    trainer_inventory: List[Dict[str, Any]],
    submissions_summary: Dict[str, Any],
    growth_attribution_summary: Dict[str, Any],
    reactivation_summary: Dict[str, Any],
) -> Dict[str, Any]:
    submissions_coll = getattr(db, "submissions", None)
    trainers_coll = getattr(db, "trainers", None)
    now_7d = _window_start_iso(7)
    now_30d = _window_start_iso(30)

    submissions_7d = int(await submissions_coll.count_documents({"created_at": {"$gte": now_7d}})) if submissions_coll is not None else 0
    published_trainers_7d = int(await trainers_coll.count_documents({"published": True, "created_at": {"$gte": now_7d}})) if trainers_coll is not None else 0
    published_trainers_30d = int(await trainers_coll.count_documents({"published": True, "created_at": {"$gte": now_30d}})) if trainers_coll is not None else 0
    intro_ready_now = len([row for row in trainer_inventory if bool(row.get("intro_ready"))])
    blocked_now = len([row for row in trainer_inventory if isinstance(row.get("blocker_codes"), list) and row.get("blocker_codes")])

    submitted_total = int(submissions_summary.get("auto_published") or 0) + int(submissions_summary.get("auto_held") or 0) + int(submissions_summary.get("pending") or 0)
    waitlist_joins_30d = int((growth_attribution_summary.get("totals") or {}).get("waitlist_joins_30d") or 0)
    return {
        "submissions_7d": submissions_7d,
        "submitted_total": submitted_total,
        "published_trainers_7d": published_trainers_7d,
        "published_trainers_30d": published_trainers_30d,
        "intro_ready_now": intro_ready_now,
        "blocked_now": blocked_now,
        "waitlist_joins_30d": waitlist_joins_30d,
        "reactivation_notified_7d": int(reactivation_summary.get("notified_7d") or 0),
        "reactivation_resolved_7d": int(reactivation_summary.get("resolved_7d") or 0),
        "submission_pace": _pace_label(submissions_7d, submitted_total, 7, 30),
        "published_pace": _pace_label(published_trainers_7d, published_trainers_30d, 7, 30),
    }


async def _message_log_rows(limit: int = 120) -> List[Dict[str, Any]]:
    notifications_coll = getattr(db, "notification_events", None)
    outreach_coll = getattr(db, "outreach_events", None)
    if notifications_coll is None and outreach_coll is None:
        return []

    notification_events = (
        await notifications_coll.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        if notifications_coll is not None
        else []
    )
    outreach_events = (
        await outreach_coll.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        if outreach_coll is not None
        else []
    )

    events: List[Dict[str, Any]] = [
        {"source_kind": "notification_event", **event}
        for event in notification_events
    ] + [
        {
            "source_kind": "outreach_event",
            "target_kind": "intro",
            "target_id": str(event.get("intro_id") or ""),
            "to_email": event.get("email") or "",
            "attempt": int(event.get("attempt") or 1),
            **event,
        }
        for event in outreach_events
    ]
    events.sort(key=lambda event: str(event.get("created_at") or ""), reverse=True)
    events = events[:limit]

    intro_ids = {str(e.get("target_id") or "") for e in events if str(e.get("target_kind") or "") == "intro" and e.get("target_id")}
    trainer_ids = {str(e.get("target_id") or "") for e in events if str(e.get("target_kind") or "") == "trainer" and e.get("target_id")}
    submission_ids = {str(e.get("target_id") or "") for e in events if str(e.get("target_kind") or "") == "submission" and e.get("target_id")}

    submissions = await db.submissions.find({"id": {"$in": sorted(submission_ids)}}, {"_id": 0, "id": 1, "name": 1}).to_list(max(1, len(submission_ids))) if submission_ids else []
    intros = await db.intros.find({"id": {"$in": sorted(intro_ids)}}, {"_id": 0, "id": 1, "trainer_id": 1}).to_list(max(1, len(intro_ids))) if intro_ids else []
    trainer_ids.update(str(row.get("trainer_id") or "") for row in intros if row.get("trainer_id"))
    trainers = await db.trainers.find({"id": {"$in": sorted(trainer_ids)}}, {"_id": 0, "id": 1, "name": 1}).to_list(max(1, len(trainer_ids))) if trainer_ids else []

    trainers_by_id = {str(row.get("id") or ""): row for row in trainers}
    submissions_by_id = {str(row.get("id") or ""): row for row in submissions}
    intros_by_id = {str(row.get("id") or ""): row for row in intros}

    rows: List[Dict[str, Any]] = []
    for event in events:
        source_kind = str(event.get("source_kind") or "notification_event")
        target_kind = str(event.get("target_kind") or "")
        target_id = str(event.get("target_id") or "")
        entity_label = target_id or "unknown"
        workflow = "communications"
        canonical_user_type = "Oversight operator"
        if target_kind == "trainer":
            trainer = trainers_by_id.get(target_id, {})
            entity_label = str(trainer.get("name") or target_id or "trainer")
            workflow = "trainer lifecycle"
            canonical_user_type = "Trainer / business submitter"
        elif target_kind == "submission":
            submission = submissions_by_id.get(target_id, {})
            entity_label = str(submission.get("name") or target_id or "submission")
            workflow = "trainer submission"
            canonical_user_type = "Trainer / business submitter"
        elif target_kind == "intro":
            intro = intros_by_id.get(target_id, {})
            trainer = trainers_by_id.get(str(intro.get("trainer_id") or ""), {})
            entity_label = str(trainer.get("name") or target_id or "intro")
            workflow = "trainer intro"
            canonical_user_type = "Trainer / business submitter"
            if source_kind == "outreach_event":
                workflow = "t+7 follow-up"
                canonical_user_type = "Dog owner"

        rows.append(
            {
                "id": str(event.get("id") or new_id()),
                "created_at": event.get("created_at"),
                "target_kind": target_kind or "unknown",
                "target_id": target_id,
                "kind": event.get("kind") or "unknown",
                "status": event.get("status") or "unknown",
                "attempt": int(event.get("attempt") or 0),
                "http_status": int(event.get("http_status") or 0),
                "to_email": claim_engine.mask_email(str(event.get("to_email") or "")),
                "error": str(event.get("error") or "")[:240],
                "entity_label": entity_label,
                "workflow": workflow,
                "canonical_user_type": canonical_user_type,
                "provider": event.get("provider") or "",
                "source_kind": source_kind,
            }
        )
    return rows


def _build_message_case(row: Dict[str, Any]) -> Dict[str, Any]:
    status = str(row.get("status") or "unknown")
    severity = "high" if status == "failed" else "low"
    state = "detected" if status == "failed" else "notified"
    canonical_user_type = row.get("canonical_user_type") or "Trainer / business submitter"
    case_type = "owner_follow_up_case" if canonical_user_type == "Dog owner" else "trainer_communications_case"
    return {
        "case_id": f"message:{row.get('id')}",
        "case_type": case_type,
        "canonical_user_type": canonical_user_type,
        "workflow": row.get("workflow") or "communications",
        "entity_type": row.get("target_kind") or "message",
        "entity_id": row.get("target_id") or row.get("id"),
        "title": f"{humanize_case_token(row.get('kind') or 'message')} · {row.get('entity_label') or 'unknown'}",
        "summary": f"Delivery status is {status}. Review message history before trusting the workflow state.",
        "severity": severity,
        "state": state,
        "owner": "",
        "detected_at": row.get("created_at"),
        "last_updated_at": row.get("created_at"),
        "source_refs": [{"kind": row.get("source_kind") or "notification_event", "id": row.get("id")}],
        "risk_reason_codes": [f"notification_{status}"],
        "recommended_next_step": "Review message history and linked workflow.",
        "responsibility_layer": "Layer 1 — Normal Ops",
        "detail_rows": [
            {"label": "Workflow", "value": row.get("workflow") or "communications"},
            {"label": "Target type", "value": row.get("target_kind") or "unknown"},
            {"label": "Delivery status", "value": status},
            {"label": "Provider", "value": row.get("provider") or "unknown"},
            {"label": "Attempt", "value": int(row.get("attempt") or 0)},
            {"label": "HTTP status", "value": int(row.get("http_status") or 0)},
        ],
        "linked_paths": [],
        "audit_refs": [],
    }


def _normalize_ops_case_state(raw_state: str) -> str:
    token = str(raw_state or "").strip().lower()
    return token if token in OPS_CASE_ALLOWED_STATES else ""


def _normalize_ops_case_owner(raw_owner: Optional[str]) -> str:
    owner = " ".join(str(raw_owner or "").strip().split())
    return owner[:80]


def _normalize_ops_case_note(raw_note: Optional[str]) -> str:
    note = " ".join(str(raw_note or "").strip().split())
    return note[:500]


async def _load_ops_case_state_map(case_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    states_coll = getattr(db, "ops_case_states", None)
    if states_coll is None or not case_ids:
        return {}
    try:
        rows = await states_coll.find({"case_id": {"$in": sorted(case_ids)}}, {"_id": 0}).to_list(max(1, len(case_ids)))
        return {str(row.get("case_id") or ""): row for row in rows if row.get("case_id")}
    except Exception:
        return {}


def _merge_ops_case_state(case: Dict[str, Any], override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not override:
        return {
            **case,
            "review": {
                "state": str(case.get("state") or "detected"),
                "owner": str(case.get("owner") or ""),
                "note": "",
                "updated_at": case.get("last_updated_at") or case.get("detected_at"),
                "history": [],
            },
        }

    merged = dict(case)
    override_state = str(override.get("state") or "")
    merged["state"] = override_state or merged.get("state")
    merged["owner"] = str(override.get("owner") or merged.get("owner") or "")
    merged["last_updated_at"] = override.get("updated_at") or merged.get("last_updated_at")
    merged["review"] = {
        "state": merged.get("state"),
        "owner": str(override.get("owner") or ""),
        "note": str(override.get("note") or ""),
        "updated_at": override.get("updated_at") or merged.get("last_updated_at") or merged.get("detected_at"),
        "history": list(override.get("history") or []),
    }
    return merged


async def _ops_case_rows(
    *,
    discovery_summary: Dict[str, Any],
    waitlist_summary: Dict[str, Any],
    loop_statuses: Dict[str, Any],
    fraud_suppression_cases: Optional[List[Dict[str, Any]]] = None,
    claim_cases: Optional[List[Dict[str, Any]]] = None,
    abn_degradation_cases: Optional[List[Dict[str, Any]]] = None,
    billing_recovery_case_rows: Optional[List[Dict[str, Any]]] = None,
    subscription_billing_case_rows: Optional[List[Dict[str, Any]]] = None,
    reactivation_case_rows: List[Dict[str, Any]],
    source_ingestion_state_rows: List[Dict[str, Any]],
    message_log: List[Dict[str, Any]],
    ai_degradation_cases: Optional[List[Dict[str, Any]]] = None,
    sponsor_inventory_cases: Optional[List[Dict[str, Any]]] = None,
    provider_cases: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    try:
        submissions_coll = getattr(db, "submissions", None)
        held_submissions = await submissions_coll.find(
            {"status": {"$in": ["pending", "held"]}},
            {"_id": 0, "id": 1, "name": 1, "status": 1, "created_at": 1, "confidence_score": 1, "verification_model": 1, "reason": 1, "duplicate": 1},
        ).sort("created_at", -1).limit(50).to_list(50) if submissions_coll is not None and hasattr(submissions_coll, "find") else []
    except Exception:
        held_submissions = []
    for row in held_submissions:
        status = str(row.get("status") or "pending")
        severity = "high" if status == "held" else "medium"
        detail_rows = [
            {"label": "Submission status", "value": status},
            {"label": "Created", "value": row.get("created_at")},
            {"label": "Entity", "value": row.get("id")},
        ]
        if row.get("confidence_score") is not None:
            detail_rows.append({"label": "AI confidence", "value": str(row.get("confidence_score"))})
        if row.get("verification_model"):
            detail_rows.append({"label": "AI model", "value": str(row.get("verification_model"))})
        if row.get("duplicate"):
            detail_rows.append({"label": "Duplicate", "value": "true"})
        if row.get("reason"):
            detail_rows.append({"label": "Hold reason", "value": str(row.get("reason"))})
        cases.append(
            {
                "case_id": f"submission:{row.get('id')}",
                "case_type": "trainer_submission_case",
                "canonical_user_type": "Trainer / business submitter",
                "workflow": "trainer submission",
                "entity_type": "submission",
                "entity_id": row.get("id"),
                "title": f"{row.get('name') or 'Unnamed trainer'} · {humanize_case_token(status)}",
                "summary": str(row.get("reason") or "Submission needs review in the trainer workflow."),
                "severity": severity,
                "state": "detected",
                "owner": "",
                "detected_at": row.get("created_at"),
                "last_updated_at": row.get("created_at"),
                "source_refs": [{"kind": "submission", "id": row.get("id")}],
                "risk_reason_codes": [f"submission_{status}"] + ([str(row.get("reason"))] if row.get("reason") else []),
                "recommended_next_step": "Review submission status and linked trainer readiness.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": detail_rows,
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    if int(waitlist_summary.get("duplicate_24h") or 0) > 0 or int(waitlist_summary.get("rejected_24h") or 0) > 0:
        cases.append(
            {
                "case_id": "waitlist:abnormality",
                "case_type": "owner_waitlist_case",
                "canonical_user_type": "Dog owner",
                "workflow": "owner waitlist",
                "entity_type": "waitlist",
                "entity_id": "owner_waitlist",
                "title": "Waitlist abnormalities detected",
                "summary": f"Duplicates {int(waitlist_summary.get('duplicate_24h') or 0)} · rejected {int(waitlist_summary.get('rejected_24h') or 0)} in the last 24h.",
                "severity": "medium",
                "state": "detected",
                "owner": "",
                "detected_at": now_iso(),
                "last_updated_at": now_iso(),
                "source_refs": [{"kind": "owner_waitlist_summary", "id": "owner_waitlist"}],
                "risk_reason_codes": ["waitlist_abnormalities_present"],
                "recommended_next_step": "Review demand quality and attribution health before resuming public exposure.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Duplicate joins (24h)", "value": int(waitlist_summary.get("duplicate_24h") or 0)},
                    {"label": "Rejected joins (24h)", "value": int(waitlist_summary.get("rejected_24h") or 0)},
                    {"label": "Active waitlist", "value": int(waitlist_summary.get("total_active") or 0)},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    if int(discovery_summary.get("pending") or 0) > 0:
        cases.append(
            {
                "case_id": "discovery:pending",
                "case_type": "discovery_case",
                "canonical_user_type": "External contributor / ecosystem actor",
                "workflow": "discovery intake",
                "entity_type": "discovery_queue",
                "entity_id": "pending",
                "title": "Discovery queue awaiting review",
                "summary": f"{int(discovery_summary.get('pending') or 0)} discovery candidates remain pending.",
                "severity": "low",
                "state": "detected",
                "owner": "",
                "detected_at": now_iso(),
                "last_updated_at": now_iso(),
                "source_refs": [{"kind": "discovery_summary", "id": "pending"}],
                "risk_reason_codes": ["discovery_pending"],
                "recommended_next_step": "Review discovery backlog and confirm sources are still appropriate.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Pending discovery items", "value": int(discovery_summary.get("pending") or 0)},
                    {"label": "Promoted", "value": int(discovery_summary.get("promoted") or 0)},
                    {"label": "Discarded", "value": int(discovery_summary.get("discarded") or 0)},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    if int(discovery_summary.get("suppressed") or 0) > 0:
        cases.append(
            {
                "case_id": "discovery:suppressed",
                "case_type": "discovery_suppression_case",
                "canonical_user_type": "External contributor / ecosystem actor",
                "workflow": "lawful source ingestion",
                "entity_type": "discovery_queue",
                "entity_id": "suppressed",
                "title": "Delisted identities blocked from re-ingestion",
                "summary": f"{int(discovery_summary.get('suppressed') or 0)} discovery candidates matched the delisting suppression register.",
                "severity": "medium",
                "state": "detected",
                "owner": "",
                "detected_at": now_iso(),
                "last_updated_at": now_iso(),
                "source_refs": [{"kind": "discovery_summary", "id": "suppressed"}],
                "risk_reason_codes": ["discovery_delisted_identity_suppressed"],
                "recommended_next_step": "Confirm suppression is expected; do not re-publish without technical-owner review.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Suppressed discovery items", "value": int(discovery_summary.get("suppressed") or 0)},
                    {"label": "Duplicates", "value": int(discovery_summary.get("duplicate") or 0)},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    for key, status_meta in loop_statuses.items():
        loop_status = str(status_meta.get("status") or "ok")
        if loop_status == "ok":
            continue
        severity = "high" if loop_status == "escalate" else "medium"
        cases.append(
            {
                "case_id": f"loop:{key}",
                "case_type": "loop_health_case",
                "canonical_user_type": "Autonomous system actor",
                "workflow": "system activity",
                "entity_type": "loop",
                "entity_id": key,
                "title": f"{humanize_case_token(key)} needs review",
                "summary": f"Loop status is {humanize_case_token(loop_status)}.",
                "severity": severity,
                "state": "detected",
                "owner": "",
                "detected_at": now_iso(),
                "last_updated_at": now_iso(),
                "source_refs": [{"kind": "loop_status", "id": key}],
                "risk_reason_codes": [f"loop_{loop_status}"],
                "recommended_next_step": "Inspect system activity and escalate if the loop stays stale.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Loop", "value": key},
                    {"label": "Status", "value": loop_status},
                    {"label": "Age (seconds)", "value": status_meta.get("age_s")},
                    {"label": "Escalates after (seconds)", "value": status_meta.get("stale_after_s")},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    for row in (fraud_suppression_cases or []):
        reasons = row.get("fraud_reasons") or row.get("reasons") or ["suppressed"]
        intro_id = str(row.get("id") or row.get("intro_id") or "")
        cases.append(
            {
                "case_id": f"fraud:{intro_id}",
                "case_type": "fraud_suppression_case",
                "canonical_user_type": "Public consumer",
                "workflow": "fraud suppression",
                "entity_type": "intro",
                "entity_id": intro_id,
                "title": f"Intro suppressed · {', '.join(reasons)}",
                "summary": "Introduction suppressed by anti-gaming rules to protect ranking quality.",
                "severity": "medium",
                "state": "detected",
                "owner": "",
                "detected_at": row.get("created_at"),
                "last_updated_at": row.get("created_at"),
                "source_refs": [{"kind": "intro", "id": intro_id}],
                "risk_reason_codes": reasons,
                "recommended_next_step": "Review IP and duplicate intro signals to confirm legitimate suppression.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Delivery status", "value": row.get("delivery_status") or "suppressed"},
                    {"label": "Reasons", "value": ", ".join(reasons)},
                    {"label": "Trainer", "value": row.get("trainer_name") or row.get("trainer_id") or "unknown"},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    for row in (claim_cases or []):
        status = str(row.get("status") or "unknown")
        reason = str(row.get("reason") or row.get("delivery_error") or "")
        if status in {"claim_disputed", "locked", "delivery_failed"}:
            severity = "high"
        elif status in {"pending_verification"}:
            severity = "low"
        else:
            severity = "medium"
        profile_ownership_state = str(row.get("profile_claim_status") or ("claim_disputed" if status == "claim_disputed" else ""))
        detail_rows = [
            {"label": "Claim status", "value": status},
            {"label": "Delivery status", "value": row.get("delivery_status") or "not_applicable"},
            {"label": "Method", "value": row.get("method") or "unknown"},
            {"label": "Destination", "value": row.get("masked_destination") or "not_recorded"},
            {"label": "Attempts", "value": row.get("attempts", 0)},
        ]
        if profile_ownership_state:
            detail_rows.append({"label": "Profile ownership state", "value": profile_ownership_state})
            detail_rows.append({"label": "Profile claim status", "value": profile_ownership_state})
        cases.append(
            {
                "case_id": f"trainer_claim:{row.get('id')}",
                "case_type": "trainer_claim_case",
                "canonical_user_type": "Trainer / business submitter",
                "workflow": "trainer profile claim",
                "entity_type": "trainer",
                "entity_id": row.get("trainer_id"),
                "title": f"Trainer claim · {humanize_case_token(status)}",
                "summary": reason or f"Trainer claim in {humanize_case_token(status)} state requires workflow review.",
                "severity": severity,
                "state": "detected",
                "owner": "",
                "detected_at": row.get("created_at"),
                "last_updated_at": row.get("updated_at") or row.get("created_at"),
                "source_refs": [{"kind": "claim_event", "id": row.get("id")}],
                "risk_reason_codes": [status] + ([reason] if reason else []) + ([f"profile_{profile_ownership_state}"] if profile_ownership_state else []),
                "recommended_next_step": "Review claim evidence and delivery status before changing listing ownership.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": detail_rows,
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    for row in (abn_degradation_cases or []):
        trainer_id = str(row.get("id") or "")
        cases.append(
            {
                "case_id": f"abn_verification:{trainer_id}",
                "case_type": "abn_verification_case",
                "canonical_user_type": "Trainer / business submitter",
                "workflow": "ABN verification",
                "entity_type": "trainer",
                "entity_id": trainer_id,
                "title": f"ABN verification · {row.get('name') or 'Trainer'}",
                "summary": str(row.get("abn_verification_reason") or "ABR verification is unavailable."),
                "severity": "medium",
                "state": "detected",
                "owner": "",
                "detected_at": row.get("created_at"),
                "last_updated_at": row.get("abn_checked_at") or row.get("created_at"),
                "source_refs": [{"kind": "trainer", "id": trainer_id}],
                "risk_reason_codes": [str(row.get("abn_status") or "abr_unavailable")],
                "recommended_next_step": "Check ABR service configuration or retry verification; do not present an ABN-verified badge until it succeeds.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "ABN", "value": row.get("abn") or "not_recorded"},
                    {"label": "ABN status", "value": row.get("abn_status") or "abr_unavailable"},
                    {"label": "Verification", "value": "not_verified"},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    for row in (ai_degradation_cases or []):
        cases.append(row)

    for row in (subscription_billing_case_rows or []):
        status = str(row.get("status") or "needs_review")
        trainer_id = str(row.get("trainer_id") or "")
        reason = str(row.get("reason") or "subscription_event_needs_review")
        cases.append(
            {
                "case_id": f"subscription_billing:{row.get('id')}",
                "case_type": "subscription_billing_case",
                "canonical_user_type": "Trainer / business submitter",
                "workflow": "trainer subscription billing",
                "entity_type": "stripe_event",
                "entity_id": row.get("id"),
                "title": "Subscription billing needs review",
                "summary": f"{humanize_case_token(status)} · {humanize_case_token(reason)}",
                "severity": "high" if status == "provider_unavailable" else "medium",
                "state": "detected",
                "owner": "",
                "detected_at": row.get("created_at"),
                "last_updated_at": row.get("processed_at") or row.get("created_at"),
                "source_refs": [{"kind": "stripe_event", "id": row.get("id")}],
                "risk_reason_codes": [status, reason],
                "recommended_next_step": "Check the Stripe event and trainer subscription state before changing access manually.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Event", "value": row.get("type") or "unknown"},
                    {"label": "Trainer", "value": trainer_id or "unresolved"},
                    {"label": "Plan", "value": row.get("subscription_tier") or "unknown"},
                    {"label": "Reason", "value": reason},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    for row in (sponsor_inventory_cases or []):
        reason = str(row.get("reason") or row.get("event_type") or "sponsor_inventory_needs_review")
        cases.append(
            {
                "case_id": f"sponsor_inventory:{row.get('id')}",
                "case_type": "sponsor_inventory_case",
                "canonical_user_type": "Trainer / business submitter",
                "workflow": "sponsor inventory",
                "entity_type": "sponsor_inventory",
                "entity_id": row.get("reservation_id") or row.get("id"),
                "title": "Sponsor inventory needs review",
                "summary": humanize_case_token(reason),
                "severity": "high" if row.get("status") == "failed" else "medium",
                "state": "detected",
                "owner": "",
                "detected_at": row.get("created_at"),
                "last_updated_at": row.get("created_at"),
                "source_refs": [{"kind": "sponsor_inventory_event", "id": row.get("id")}],
                "risk_reason_codes": [reason],
                "recommended_next_step": "Review the reservation and linked subscription before changing sponsor placement.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Trainer", "value": row.get("trainer_id") or "unresolved"},
                    {"label": "Scope", "value": row.get("scope") or "unknown"},
                    {"label": "Suburb", "value": row.get("suburb") or "not_applicable"},
                    {"label": "Reason", "value": reason},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    for row in (billing_recovery_case_rows or []):
        trainer_id = str(row.get("trainer_id") or "")
        sub_status = str(row.get("subscription_status") or "unknown")
        cases.append(
            {
                "case_id": f"trainer_subscription:{trainer_id}",
                "case_type": "subscription_billing_case",
                "canonical_user_type": "Trainer / business submitter",
                "workflow": "trainer subscription billing",
                "entity_type": "trainer",
                "entity_id": trainer_id,
                "title": f"Subscription exception · {row.get('trainer_name') or 'Trainer'}",
                "summary": f"Subscription status {sub_status} requires attention.",
                "severity": "high" if sub_status in {"past_due", "unpaid"} else "medium",
                "state": "detected",
                "owner": "",
                "detected_at": row.get("created_at") or now_iso(),
                "last_updated_at": row.get("created_at") or now_iso(),
                "source_refs": [{"kind": "trainer", "id": trainer_id}],
                "risk_reason_codes": [sub_status],
                "recommended_next_step": "Review trainer subscription and billing status.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Trainer", "value": row.get("trainer_name") or trainer_id},
                    {"label": "Tier", "value": row.get("subscription_tier") or "core"},
                    {"label": "Status", "value": sub_status},
                    {"label": "Billing status", "value": row.get("subscription_billing_status") or "unknown"},
                ],
                "linked_paths": [f"/trainer/billing?trainer_id={trainer_id}"] if trainer_id else [],
                "audit_refs": [],
            }
        )

    for row in reactivation_case_rows:
        last_status = str(row.get("last_notification_status") or "")
        state = "monitoring" if last_status == "sent" else "detected"
        trainer_id = str(row.get("trainer_id") or "")
        trainer_token = str(row.get("trainer_action_token") or "")
        cases.append(
            {
                "case_id": f"reactivation:{row.get('trainer_id')}",
                "case_type": "trainer_reactivation_case",
                "canonical_user_type": "Trainer / business submitter",
                "workflow": "reactivation",
                "entity_type": "trainer",
                "entity_id": row.get("trainer_id"),
                "title": f"{row.get('trainer_name') or 'Trainer'} · reactivation",
                "summary": "Listing signals suggest reactivation review is needed.",
                "severity": "medium",
                "state": state,
                "owner": "",
                "detected_at": row.get("updated_at"),
                "last_updated_at": row.get("last_notified_at") or row.get("updated_at"),
                "source_refs": [{"kind": "reactivation_candidate", "id": row.get("trainer_id")}],
                "risk_reason_codes": ["reactivation_open"],
                "recommended_next_step": "Review the trainer reactivation reasons and linked lifecycle route.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Last notification status", "value": last_status or "not_sent"},
                    {"label": "Reasons", "value": ", ".join(row.get("reasons") or []) or "No reasons listed"},
                    {"label": "Updated", "value": row.get("updated_at")},
                ],
                "linked_paths": [
                    {
                        "label": "Open reactivation view",
                        "path": f"/trainer/reactivate?trainer_id={trainer_id}&trainer_action_token={trainer_token}",
                    }
                ] if trainer_id and trainer_token else [],
                "audit_refs": [],
            }
        )

    for row in source_ingestion_state_rows:
        failures = int(row.get("consecutive_failures") or 0)
        has_error = bool(row.get("last_error") or row.get("last_error_code"))
        if failures <= 0 and not row.get("suppressed_until") and not has_error:
            continue
        err_msg = str(row.get("last_error") or f"{row.get('source_url') or 'Source'} has {failures} consecutive failures.")
        risk_code = str(row.get("last_error_code") or "source_ingestion_failures")
        cases.append(
            {
                "case_id": f"source:{hashlib.sha1(str(row.get('source_url') or '').encode('utf-8')).hexdigest()[:12]}",
                "case_type": "source_ingestion_case",
                "canonical_user_type": "External contributor / ecosystem actor",
                "workflow": "source ingestion",
                "entity_type": "source_url",
                "entity_id": row.get("source_url"),
                "title": "Source ingestion needs review",
                "summary": err_msg,
                "severity": "medium",
                "state": "detected",
                "owner": "",
                "detected_at": row.get("last_ok_at") or now_iso(),
                "last_updated_at": row.get("suppressed_until") or row.get("last_ok_at") or now_iso(),
                "source_refs": [{"kind": "source_ingestion_state", "id": row.get("source_url")}],
                "risk_reason_codes": [risk_code],
                "recommended_next_step": "Inspect source health and confirm it should remain in the pipeline.",
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Source URL", "value": row.get("source_url") or "unknown"},
                    {"label": "Consecutive failures", "value": failures},
                    {"label": "Last error", "value": row.get("last_error") or "none"},
                    {"label": "Suppressed until", "value": row.get("suppressed_until") or "not_suppressed"},
                    {"label": "Last success", "value": row.get("last_ok_at") or "unknown"},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )

    for row in message_log:
        if str(row.get("status") or "") in {"failed", "sent"}:
            cases.append(_build_message_case(row))

    cases.extend(provider_cases or [])

    overrides = await _load_ops_case_state_map([str(case.get("case_id") or "") for case in cases if case.get("case_id")])
    cases = [_merge_ops_case_state(case, overrides.get(str(case.get("case_id") or ""))) for case in cases]
    cases.sort(key=_sort_case_priority)
    return cases[:150]


def _loop_interval_seconds() -> Dict[str, int]:
    return {
        "ranking": autonomy.RANKING_INTERVAL_S,
        "verification": autonomy.VERIFICATION_INTERVAL_S,
        "discovery": autonomy.DISCOVERY_INTERVAL_S,
        "inference": autonomy.INFERENCE_INTERVAL_S,
        "health": autonomy.HEALTH_INTERVAL_S,
        "source_ingestion": autonomy.SOURCE_INGEST_INTERVAL_S,
        "outreach": autonomy.OUTREACH_INTERVAL_S,
        "nurture": autonomy.NURTURE_INTERVAL_S,
        "reactivation_route": autonomy.REACTIVATION_ROUTE_INTERVAL_S,
        "pro_trial_warnings": 86400,
    }


def _loop_status(loop_key: str, loop: Dict[str, Any], *, now_dt: datetime) -> Dict[str, Any]:
    interval_s = int(_loop_interval_seconds().get(loop_key) or 0)
    last_run = str(loop.get("last_run") or "")
    try:
        last_dt = datetime.fromisoformat(last_run) if last_run else None
    except Exception:  # noqa: BLE001
        last_dt = None
    age_s = None
    status = "warn"
    if last_dt and interval_s > 0:
        age_s = max(0, int((now_dt - last_dt).total_seconds()))
        if age_s <= interval_s:
            status = "ok"
        elif age_s <= interval_s * 2:
            status = "investigate"
        else:
            status = "escalate"
    return {
        "status": status,
        "interval_s": interval_s,
        "age_s": age_s,
        "stale_after_s": interval_s * 2 if interval_s > 0 else None,
    }


def humanize_case_token(value: str) -> str:
    raw = str(value or "").strip()
    return raw.replace("_", " ") if raw else "unknown"


def _trainer_source_kind(trainer: Dict[str, Any]) -> str:
    if trainer.get("via_submission_id"):
        return "submission"
    if trainer.get("via_discovery"):
        return "discovery"
    if trainer.get("source_evidence_url"):
        return "seed"
    return "unknown"


def _trainer_blocker_codes(trainer: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    if not bool(trainer.get("published")):
        codes.append("held_or_unpublished")
    if float(trainer.get("confidence_score") or 0) < HOLD_THRESHOLD:
        codes.append("low_confidence")
    billing_status = str(trainer.get("billing_profile_status") or "").strip().lower()
    if billing_status in {"missing_email", "profile_incomplete"}:
        codes.append("needs_billing_profile")
    elif billing_status == "consent_required":
        codes.append("needs_billing_consent")
    elif billing_status in {"stripe_unconfigured", "stripe_error"}:
        codes.append("billing_system_blocked")
    if not _has_contact_channel(trainer):
        codes.append("missing_contact_channel")
    deduped: List[str] = []
    for code in codes:
        if code not in deduped:
            deduped.append(code)
    return deduped


def _trainer_intro_ready(trainer: Dict[str, Any]) -> bool:
    if not bool(trainer.get("published")):
        return False
    if float(trainer.get("confidence_score") or 0) < HOLD_THRESHOLD:
        return False
    blocker_codes = set(_trainer_blocker_codes(trainer))
    disqualifying_codes = {
        "held_or_unpublished",
        "low_confidence",
        "needs_billing_profile",
        "needs_billing_consent",
        "billing_system_blocked",
        "missing_contact_channel",
    }
    return not bool(blocker_codes & disqualifying_codes)


def _sort_case_priority(case: Dict[str, Any]) -> tuple[int, int, str]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    state_rank = {
        "detected": 0,
        "notified": 1,
        "acknowledged": 2,
        "investigating": 3,
        "actioned": 4,
        "monitoring": 5,
        "resolved": 6,
        "deferred": 7,
        "dismissed": 8,
        "escalated_to_owner_override": 9,
        "escalated_to_technical_owner": 10,
    }
    return (
        severity_rank.get(str(case.get("severity") or "low"), 99),
        state_rank.get(str(case.get("state") or "detected"), 99),
        str(case.get("detected_at") or ""),
    )


def _claim_policy_snapshot() -> Dict[str, Any]:
    return {
        "status": "decommissioned",
        "enabled": False,
        "state": "STATE_4",
        "model_enabled": False,
        "state_current": "STATE_4",
        "enforcement_mode": "disabled",
        "block_melbourne_wide_below_state_2": False,
        "melbourne_wide_min_state": "STATE_0",
    }


def _phase_public_emphasis(*, phase: str, public_matching_enabled: bool) -> str:
    if public_matching_enabled:
        return "live_matching"
    if phase == "growth":
        return "growth_prep"
    if phase == "owner_waitlist":
        return "owner_waitlist"
    return "live_matching"


def _default_launch_phase_state() -> Dict[str, Any]:
    current_phase = PUBLIC_LAUNCH_PHASE
    return {
        "key": "launch_phase_state",
        "current_phase": current_phase,
        "matching_exposure_enabled": True,
        "public_matching_enabled": True,
        "public_emphasis": "live_matching",
        "trainer_onboarding_open": True,
        "owner_waitlist_mode": "passive_only",
        "evidence_window_mode": "30_day_prelaunch_evidence_window",
        "requires_owner_review_for_phase_change": True,
        "active_regions": list(ACTIVE_REGIONS),
        "updated_at": now_iso(),
        "updated_by": "system",
        "reason": "default_supply_first_matching_open",
    }


async def _read_launch_phase_state() -> Dict[str, Any]:
    system_state = getattr(db, "system_state", None)
    default_state = _default_launch_phase_state()
    if system_state is None:
        return default_state

    row = await system_state.find_one({"key": "launch_phase_state"}, {"_id": 0})
    if row:
        state = {**default_state, **row}
        state["matching_exposure_enabled"] = True
        state["public_matching_enabled"] = True
        state["public_emphasis"] = "live_matching"
        if state.get("current_phase") in {"supply_first", "owner_waitlist"} and PUBLIC_LAUNCH_PHASE == "live_matching":
            state["current_phase"] = "live_matching"
        return state

    return default_state


async def _get_or_create_launch_phase_state() -> Dict[str, Any]:
    system_state = getattr(db, "system_state", None)
    default_state = _default_launch_phase_state()
    if system_state is None:
        return default_state

    row = await system_state.find_one({"key": "launch_phase_state"}, {"_id": 0})
    if row:
        state = {**default_state, **row}
        state["matching_exposure_enabled"] = True
        state["public_matching_enabled"] = True
        state["public_emphasis"] = "live_matching"
        if state.get("current_phase") in {"supply_first", "owner_waitlist"} and PUBLIC_LAUNCH_PHASE == "live_matching":
            state["current_phase"] = "live_matching"
        if (
            row.get("matching_exposure_enabled") is not True
            or row.get("public_matching_enabled") is not True
            or row.get("public_emphasis") != "live_matching"
            or row.get("current_phase") != state.get("current_phase")
            or state != row
        ):
            await system_state.update_one({"key": "launch_phase_state"}, {"$set": state}, upsert=True)
        return state

    await system_state.insert_one(default_state)
    return default_state


async def _phase_blocker_summary() -> Dict[str, Any]:
    trainers_coll = getattr(db, "trainers", None)
    if trainers_coll is None:
        return {
            "intro_ready_trainer_count": 0,
            "blocked_trainer_count": 0,
            "blocker_buckets": {},
            "reason_codes": ["phase_blocker_summary_unavailable"],
        }

    intro_ready_trainer_count = int(await trainers_coll.count_documents({"published": True}))
    held_or_unpublished_count = int(await trainers_coll.count_documents({"published": False}))

    blocker_buckets = {
        "held_or_unpublished": held_or_unpublished_count,
    }
    blocked_trainer_count = held_or_unpublished_count
    return {
        "intro_ready_trainer_count": intro_ready_trainer_count,
        "blocked_trainer_count": blocked_trainer_count,
        "blocker_buckets": blocker_buckets,
        "reason_codes": ["phase_blocker_summary_ok"],
    }


async def _build_phase_readiness_snapshot(phase_state: Dict[str, Any]) -> Dict[str, Any]:
    kpi_prelaunch = await _kpi_prelaunch_summary()
    waitlist_summary = await _owner_waitlist_summary()
    growth_summary = await _growth_attribution_summary()
    reactivation_summary = await _reactivation_summary()
    blocker_summary = await _phase_blocker_summary()
    health = await db.system_state.find_one({"key": "health"}, {"_id": 0}) or {}
    alerts = health.get("alerts", []) if isinstance(health, dict) else []
    high_alert_count = len([a for a in alerts if str((a or {}).get("severity") or "").lower() == "high"])
    blocker_buckets = dict(blocker_summary.get("blocker_buckets") or {})
    if high_alert_count > 0:
        blocker_buckets["high_severity_alerts"] = high_alert_count

    blocker_reasons = [key for key, value in blocker_buckets.items() if int(value or 0) > 0]
    if blocker_reasons:
        readiness_status = "attention_needed"
        recommendation = "resolve_blockers_and_continue_supply_first"
    else:
        readiness_status = "collecting_evidence"
        recommendation = "continue_supply_first_collecting_evidence"

    return {
        "snapshot_kind": "latest",
        "phase": str(phase_state.get("current_phase") or PUBLIC_LAUNCH_PHASE),
        "matching_exposure_enabled": bool(phase_state.get("matching_exposure_enabled", True)),
        "public_emphasis": str(phase_state.get("public_emphasis") or "live_matching"),
        "readiness_status": readiness_status,
        "recommendation": recommendation,
        "blockers_to_next_phase": blocker_reasons,
        "intro_ready_trainer_count": int(blocker_summary.get("intro_ready_trainer_count") or 0),
        "blocked_trainer_count": int(blocker_summary.get("blocked_trainer_count") or 0),
        "blocker_buckets": blocker_buckets,
        "owner_waitlist_total_active": int(waitlist_summary.get("total_active") or 0),
        "owner_waitlist_joins_24h": int(waitlist_summary.get("joins_24h") or 0),
        "published_trainer_count": int(kpi_prelaunch.get("published_trainer_count") or 0),
        "verified_trainer_count": int(kpi_prelaunch.get("verified_trainer_count") or 0),
        "trainer_suburb_coverage_count": int(kpi_prelaunch.get("trainer_suburb_coverage_count") or 0),
        "waitlist_suburb_coverage_count": int(kpi_prelaunch.get("waitlist_suburb_coverage_count") or 0),
        "growth_cohort_count": int((growth_summary.get("totals") or {}).get("cohort_count") or 0),
        "reactivation_open_candidates": int(reactivation_summary.get("open_candidates") or 0),
        "high_severity_alert_count": high_alert_count,
        "evidence_window_mode": "30_day_prelaunch_evidence_window",
        "evidence_window_state": "active",
        "reason_codes": ["phase_readiness_snapshot_ok"],
        "updated_at": now_iso(),
    }


async def _upsert_latest_phase_readiness_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    coll = getattr(db, "phase_readiness_snapshots", None)
    if coll is None:
        return snapshot
    row = await coll.find_one({"snapshot_kind": "latest"}, {"_id": 0})
    payload = {**snapshot}
    if row:
        await coll.update_one({"snapshot_kind": "latest"}, {"$set": payload}, upsert=True)
    else:
        await coll.insert_one(payload)
    return payload


async def _ensure_phase_transition_baseline(
    phase_state: Dict[str, Any],
    readiness_snapshot: Dict[str, Any],
) -> List[Dict[str, Any]]:
    coll = getattr(db, "phase_transition_decisions", None)
    if coll is None:
        return []

    existing = await coll.find({}, {"_id": 0}).to_list(20)
    if existing:
        existing.sort(key=lambda row: str(row.get("decided_at") or ""), reverse=True)
        return existing

    baseline = {
        "id": new_id(),
        "decision_kind": "current_phase_lock",
        "decision_outcome": "approved",
        "from_phase": None,
        "to_phase": str(phase_state.get("current_phase") or PUBLIC_LAUNCH_PHASE),
        "public_matching_enabled": bool(phase_state.get("public_matching_enabled", True)),
        "recommendation_at_decision_time": readiness_snapshot.get("recommendation"),
        "readiness_status_at_decision_time": readiness_snapshot.get("readiness_status"),
        "snapshot_kind": readiness_snapshot.get("snapshot_kind"),
        "snapshot_updated_at": readiness_snapshot.get("updated_at"),
        "reason": "default_supply_first_prelaunch_lock",
        "decision_maker": "system",
        "requires_owner_review_for_next_transition": True,
        "decided_at": now_iso(),
    }
    await coll.insert_one(baseline)
    return [baseline]


async def _refresh_phase_runtime_records() -> Dict[str, Any]:
    phase_state = await _get_or_create_launch_phase_state()
    readiness_snapshot = await _build_phase_readiness_snapshot(phase_state)
    readiness_snapshot = await _upsert_latest_phase_readiness_snapshot(readiness_snapshot)
    phase_decisions = await _ensure_phase_transition_baseline(phase_state, readiness_snapshot)
    return {
        "phase_state": phase_state,
        "readiness_snapshot": readiness_snapshot,
        "phase_decisions": phase_decisions,
    }


def _suburb_meta_identity_snapshot() -> Dict[str, Any]:
    identity: Dict[str, Any] = {
        "list_id": None,
        "suburb_count": None,
        "suburb_hash_sha256_code_name": None,
        "as_of_date_melbourne": None,
    }
    status = {
        "ok": False,
        "warn": True,
        "level": "warn",
        "reason_codes": ["dataset_identity_optional_runtime_evidence_not_configured"],
        "meta_available": False,
    }
    payload: Dict[str, Any] = {
        "identity": identity,
        "status": status,
        "source": "runtime_optional",
    }
    return payload


def _require_trainer_action_token(
    *,
    token: Optional[str],
    trainer_id: str,
    submission_id: Optional[str] = None,
) -> None:
    _verify_trainer_action_token(token or "", trainer_id=trainer_id, submission_id=submission_id)


def _trainer_serves_suburb(trainer: Dict[str, Any], suburb: str) -> bool:
    target = _normalize_suburb_key(suburb)
    covered = {_normalize_suburb_key(str(trainer.get("suburb") or ""))}
    covered.update(_normalize_suburb_key(str(value)) for value in (trainer.get("serviced_suburbs") or []))
    return bool(target and target in covered)


async def _decorate_with_pricing(trainers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pass-through for trainers without legacy pricing metadata."""
    return trainers


def _safe_external_url(value: Optional[str], *, field_name: str = "URL") -> str:
    """Permit only absolute HTTP(S) links on public trainer surfaces."""
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute http or https URL.")
    return candidate


def _safe_stored_url(value: Any) -> Optional[str]:
    """Fail closed for historical or imported records that predate validation."""
    try:
        return _safe_external_url(str(value or "")) or None
    except ValueError:
        return None


def _released_contact_payload(trainer: Dict[str, Any], *, fallback_name: Optional[str] = None, fallback_suburb: Optional[str] = None) -> Dict[str, Any]:
    return {
        "name": trainer.get("name") or fallback_name,
        "website": _safe_stored_url(trainer.get("website")),
        "phone": trainer.get("phone"),
        "email": trainer.get("email"),
        "suburb": trainer.get("suburb") or fallback_suburb,
    }


def _public_trainer_payload(trainer: Dict[str, Any], *, include_match: bool = False) -> Dict[str, Any]:
    """Return storefront-safe fields without releasing protected contact data."""
    allowed = {
        "id", "slug", "name", "suburb", "region", "bio", "services", "categories",
        "specialties", "training_philosophy", "service_formats", "serviced_suburbs",
        "catchment_type", "price_range", "review_summary", "review_rating", "review_count",
        "claim_status", "tier", "verification_status", "abn_verified", "abn_badge_payload",
        "image_url", "gallery_images", "booking_url", "website", "published", "contact_ready",
        "placement",
    }
    if include_match:
        allowed.add("match_reasoning")
    public = {key: value for key, value in trainer.items() if key in allowed}
    tier = str(trainer.get("tier") or "").lower()
    if tier not in {"pro", "suburb_sponsor", "citywide"}:
        public.pop("booking_url", None)
        public.pop("website", None)
    else:
        for field in ("website", "booking_url"):
            safe_url = _safe_stored_url(public.get(field))
            if safe_url:
                public[field] = safe_url
            else:
                public.pop(field, None)
    safe_image = _safe_stored_url(public.get("image_url"))
    if safe_image:
        public["image_url"] = safe_image
    else:
        public.pop("image_url", None)
    if "gallery_images" in public:
        public["gallery_images"] = [
            safe_url for value in (public.get("gallery_images") or [])
            if (safe_url := _safe_stored_url(value))
        ]
    return public


def _directory_sort_key(trainer: Dict[str, Any], suburb: Optional[str]) -> tuple:
    tier = str(trainer.get("tier") or "").lower()
    tier_weight = {"citywide": 4, "suburb_sponsor": 3, "pro": 2, "claimed": 1}.get(tier, 0)
    suburb_sponsor = 1 if suburb and _normalize_suburb_key(suburb) in {
        _normalize_suburb_key(str(value)) for value in (trainer.get("sponsored_suburbs") or [])
    } else 0
    verified = 1 if trainer.get("verification_status") == "verified" else 0
    return (
        suburb_sponsor,
        tier_weight,
        verified,
        float(trainer.get("review_rating") or 0),
        int(trainer.get("review_count") or 0),
        float(trainer.get("outcome_score") or 0),
        str(trainer.get("name") or "").lower(),
    )


def _diagnostic_fit_score(trainer: Dict[str, Any]) -> float:
    return (
        (float(trainer.get("match_score") or 0) * 0.7)
        + (float(trainer.get("outcome_score") or 0.05) * 0.3)
        - float(trainer.get("_policy_penalty") or 0)
    )


def _diagnostic_tier_weight(trainer: Dict[str, Any]) -> int:
    tier = str(trainer.get("subscription_tier") or trainer.get("tier") or "").strip().lower()
    return MATCH_TIEBREAK_TIER_WEIGHTS.get(tier, 0)


def _sort_diagnostic_matches(trainers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply commercial priority only inside the named comparable-fit band."""

    if not trainers:
        return trainers
    top_score = max(_diagnostic_fit_score(trainer) for trainer in trainers)

    def sort_key(trainer: Dict[str, Any]) -> tuple:
        fit_score = _diagnostic_fit_score(trainer)
        inside_tie_band = (top_score - fit_score) <= MATCH_TIE_BAND
        if inside_tie_band:
            return (
                0,
                -_diagnostic_tier_weight(trainer),
                -fit_score,
                str(trainer.get("name") or "").lower(),
            )
        return (1, 0, -fit_score, str(trainer.get("name") or "").lower())

    return sorted(trainers, key=sort_key)


async def _resolve_submission(submission_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not submission_id:
        return None
    return await db.submissions.find_one({"id": submission_id}, {"_id": 0})


async def _resolve_trainer(*, trainer_id: Optional[str], submission_id: Optional[str]) -> Optional[Dict[str, Any]]:
    resolved_id = (trainer_id or "").strip()
    if not resolved_id and submission_id:
        sub = await _resolve_submission(submission_id)
        resolved_id = (sub or {}).get("trainer_id", "")
    if not resolved_id:
        return None
    return await db.trainers.find_one({"id": resolved_id}, {"_id": 0})


# ---------------------------------------------------------------------------
# Public — primary product surface
# ---------------------------------------------------------------------------


@api.get("/")
async def root() -> Dict[str, Any]:
    return {"service": "dog-trainers-directory-match-engine", "ok": True, "ts": now_iso()}


@api.get("/health")
async def health() -> JSONResponse:
    """Deep runtime health used by production probes and launch verification."""
    try:
        await db.command("ping")
    except Exception:  # noqa: BLE001
        logger.exception("Deep health check failed")
        return JSONResponse(
            status_code=503,
            content={"ok": False, "service": "dog-trainers-directory-match-engine", "database": "unavailable"},
        )
    return JSONResponse(
        status_code=200,
        content={"ok": True, "service": "dog-trainers-directory-match-engine", "database": "available"},
    )


@app.get("/")
async def app_root() -> Dict[str, Any]:
    return await root()


@app.get("/health")
async def app_health() -> JSONResponse:
    return await health()


@api.post("/internal/jobs/pro-trial-warnings")
async def run_pro_trial_warning_job(
    authorization: str = Header(default="", alias="Authorization"),
) -> Dict[str, Any]:
    """Authenticated, once-daily execution boundary for day-23 warnings."""
    _require_cloud_scheduler_oidc(authorization)

    def billing_url(trainer: Dict[str, Any]) -> str:
        trainer_id = str(trainer.get("id") or "")
        token = _issue_trainer_action_token(trainer_id=trainer_id)
        base = (os.environ.get("FRONTEND_BASE_URL") or "https://dogtrainersdirectory.com.au").strip().rstrip("/")
        return f"{base}/trainer/billing?{urlencode({'trainerId': trainer_id, 'token': token})}"

    return await pro_trials.process_expiry_warnings(db, billing_url_factory=billing_url)


class TrainerIngestJobRequest(BaseModel):
    source_urls: Optional[List[str]] = Field(default=None, description="Optional custom source URLs to ingest.")
    batch_size: Optional[int] = Field(default=10, description="Max batch candidates to process.")
    run_guardian: Optional[bool] = Field(default=True, description="Whether to run Supervisory Guardian after ingestion.")
    dry_run: bool = Field(default=False, description="Verify authenticated scheduler delivery without fetching, mutating trainer data, or running the guardian.")


async def _execute_trainer_ingest_pipeline(
    payload: Optional[TrainerIngestJobRequest] = None,
    trigger: str = "cloud_scheduler",
) -> Dict[str, Any]:
    """Shared execution coordinator for Engine 1 (Ingestion) and Engine 2 (Supervisory Guardian).

    Persists comprehensive run metadata into db.ingestion_runs for full /ops auditability.
    """
    source_urls = payload.source_urls if payload else None
    batch_size = payload.batch_size if payload and payload.batch_size else 10
    run_guardian = payload.run_guardian if payload and payload.run_guardian is not None else True
    dry_run = bool(payload.dry_run) if payload else False
    run_id = f"ingest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(3).hex()}"
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        # A scheduler dry run proves the real OIDC delivery path and produces a
        # bounded Ops record without silently crawling seed URLs, changing
        # trainer records, or invoking providers. It is intentionally explicit
        # so the normal daily scheduler cannot become a no-op by accident.
        if dry_run:
            completed_at = datetime.now(timezone.utc).isoformat()
            result = {
                "id": run_id,
                "ok": True,
                "dry_run": True,
                "trigger": trigger,
                "executed_at": started_at,
                "completed_at": completed_at,
                "ingestion": {
                    "ok": True,
                    "dry_run": True,
                    "total_resolved": 0,
                    "total_processed": 0,
                    "reason_codes": ["scheduler_delivery_verified_no_mutation"],
                },
                "guardian": None,
            }
            if db is not None:
                ingestion_runs_coll = getattr(db, "ingestion_runs", None)
                if ingestion_runs_coll is not None:
                    await ingestion_runs_coll.insert_one(dict(result))
            return result

        # 1. Run Engine 1: Batch Ingestion Orchestrator
        ingestion_summary = await ingestion_manager.run_batch_ingestion_pipeline(
            source_urls=source_urls,
            db=db,
            batch_size=batch_size,
        )

        # 2. Run Engine 2: Supervisory Verification Guardian
        guardian_summary = None
        if run_guardian:
            guardian_summary = await pipeline_guardian.audit_corpus_integrity(db, auto_remediate=True)

        completed_at = datetime.now(timezone.utc).isoformat()
        result = {
            "id": run_id,
            "ok": True,
            "trigger": trigger,
            "executed_at": started_at,
            "completed_at": completed_at,
            "ingestion": ingestion_summary,
            "guardian": guardian_summary,
        }

        if db is not None:
            ingestion_runs_coll = getattr(db, "ingestion_runs", None)
            if ingestion_runs_coll is not None:
                try:
                    await ingestion_runs_coll.insert_one(dict(result))
                except Exception as exc:
                    logger.warning("Failed writing to db.ingestion_runs: %s", exc)

        return result
    except Exception as exc:
        logger.exception("Critical failure in trainer ingest pipeline (trigger=%s): %s", trigger, exc)
        completed_at = datetime.now(timezone.utc).isoformat()
        failure_record = {
            "id": run_id,
            "ok": False,
            "trigger": trigger,
            "executed_at": started_at,
            "completed_at": completed_at,
            "error": str(exc),
        }
        if db is not None:
            ingestion_runs_coll = getattr(db, "ingestion_runs", None)
            if ingestion_runs_coll is not None:
                try:
                    await ingestion_runs_coll.insert_one(dict(failure_record))
                except Exception:
                    pass
            coll = getattr(db, "source_ingestion_state", None)
            if coll is not None:
                try:
                    await coll.update_one(
                        {"source_url": "system_job_failure"},
                        {
                            "$set": {
                                "source_url": "system_job_failure",
                                "last_checked_at": completed_at,
                                "last_error": str(exc),
                                "last_error_code": "internal_job_exception",
                                "consecutive_failures": 1,
                            }
                        },
                        upsert=True,
                    )
                except Exception:
                    pass
        raise HTTPException(status_code=500, detail=f"Trainer ingestion failed: {exc}")


@api.post("/internal/jobs/trainer-ingest")
async def run_trainer_ingest_job(
    payload: Optional[TrainerIngestJobRequest] = None,
    authorization: str = Header(default="", alias="Authorization"),
) -> Dict[str, Any]:
    """Authenticated, serverless execution boundary for automated trainer acquisition.

    Guarded by Google Cloud Scheduler OIDC ID Token authentication.
    Executes Engine 1 (Ingestion Orchestrator) followed by Engine 2 (Supervisory Guardian).
    """
    _require_cloud_scheduler_oidc(authorization)
    return await _execute_trainer_ingest_pipeline(payload=payload, trigger="cloud_scheduler")


@api.get("/config")
async def config() -> Dict[str, Any]:
    """Lightweight config the frontend can render without auth."""
    try:
        suburbs, suburb_catalogue_source = await suburb_catalogue.config_suburb_names(db)
    except Exception as exc:
        logger.warning("Canonical suburb catalogue unavailable for /config: %s", exc)
        suburbs = suburb_catalogue.canonical_suburb_names()
        suburb_catalogue_source = "static_catalogue_fallback"
    try:
        phase_state = await _read_launch_phase_state()
    except Exception as exc:
        logger.warning("Database unavailable reading phase state for /config: %s", exc)
        phase_state = {}
    return {
        "pro_trial_days": stripe_billing.pro_trial_days(),
        "pro_trial_expiry_warning_day": stripe_billing.pro_trial_expiry_warning_day(),
        "pro_trial_cohort_active": stripe_billing.trial_cohort_active(),
        "active_regions": ACTIVE_REGIONS,
        "active_region_default": ACTIVE_REGION,
        "stripe_webhook_enabled": stripe_billing.webhook_enabled(),
        "public_matching_enabled": True,
        "public_launch_phase": phase_state.get("current_phase", "live_matching"),
        "public_emphasis": phase_state.get("public_emphasis", "trainers_and_owners"),
        "trainer_onboarding_open": bool(phase_state.get("trainer_onboarding_open", True)),
        "owner_waitlist_mode": phase_state.get("owner_waitlist_mode", "disabled"),
        "public_monetization_copy_mode": PUBLIC_MONETIZATION_COPY_MODE,
        "public_hide_legacy_intro_fee_copy": PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY,
        "public_show_founding_profile_copy": PUBLIC_SHOW_FOUNDING_PROFILE_COPY,
        "suburbs": suburbs,
        "suburb_count": len(suburbs),
        "suburb_catalogue_version": suburb_catalogue.CATALOGUE_VERSION,
        "suburb_catalogue_source": suburb_catalogue_source,
    }


def _canonical_suburb_for_seo_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Return the canonical locality for an exact public SEO slug.

    This deliberately does not accept arbitrary nested paths or turn display
    text into a locality.  The canonical catalogue, rather than incoming URL
    text or the current trainer sample, is the geography authority.
    """
    normalized = str(slug or "").strip().lower()
    if not normalized or "/" in normalized:
        return None
    for row in suburb_catalogue.canonical_suburbs():
        if row.get("slug") == normalized:
            return row
    return None


def _configured_positive_int(name: str) -> Optional[int]:
    """Read an explicit SEO threshold; missing/invalid values fail closed."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid %s configuration; SEO persistence is disabled", name)
        return None
    return value if value > 0 else None


def _seo_word_count(copy: Dict[str, Any]) -> int:
    text = " ".join(
        [
            str(copy.get("title") or ""),
            str(copy.get("meta_description") or ""),
            str(copy.get("intro") or ""),
            *[
                f"{section.get('heading', '')} {section.get('body', '')}"
                for section in (copy.get("sections") or [])
                if isinstance(section, dict)
            ],
            *[
                f"{question.get('q', '')} {question.get('a', '')}"
                for question in (copy.get("faq") or [])
                if isinstance(question, dict)
            ],
        ]
    )
    return len(re.findall(r"\b[\w'-]+\b", text))


def _unpublished_seo_response(*, slug: str, suburb: str, reason: str) -> Dict[str, Any]:
    """Return useful, non-indexable navigation content without a provider call."""
    return {
        "slug": slug,
        "suburb": suburb,
        "category": "general",
        "publication_status": "not_eligible",
        "meta_robots": "noindex,follow",
        "reason_codes": [reason],
        "copy": {
            "title": f"Dog training guidance in {suburb}",
            "intro": "Browse the directory or use guided matching to find an appropriate trainer. Local availability is updated as eligible trainer profiles are published.",
            "sections": [],
            "faq": [],
        },
    }


def _eligible_trainer_query_for_suburb(suburb: str) -> Dict[str, Any]:
    """Return the one eligibility query shared by public SEO and protected ops."""
    escaped_suburb = re.escape(suburb)
    return {
        "published": True,
        "region": {"$in": ACTIVE_REGIONS},
        "$or": [
            {"suburb": {"$regex": f"^{escaped_suburb}$", "$options": "i"}},
            {"serviced_suburbs": {"$regex": f"^{escaped_suburb}$", "$options": "i"}},
        ],
    }


def _seo_page_word_count(page: Dict[str, Any]) -> int:
    """Recalculate content quality from stored copy rather than trusting a flag."""
    copy = page.get("copy")
    return _seo_word_count(copy) if isinstance(copy, dict) else 0


def _canonical_suburb_name_index() -> Dict[str, Dict[str, Any]]:
    return {
        str(row.get("suburb_name") or "").strip().lower(): row
        for row in suburb_catalogue.canonical_suburbs()
        if str(row.get("suburb_name") or "").strip()
    }


async def _ops_seo_indexation_summary() -> Dict[str, Any]:
    """Read-only SEO inventory for the protected operations console.

    This deliberately does not generate copy, change stored SEO records, or use
    Search Console. It exposes whether existing records still satisfy the same
    canonical/supply/content contract used by the public route.
    """
    minimum_trainers = _configured_positive_int("SEO_MIN_PUBLISHED_TRAINERS")
    minimum_words = _configured_positive_int("SEO_MIN_CONTENT_WORDS")
    canonical_rows = suburb_catalogue.canonical_suburbs()
    canonical_by_slug = {
        str(row.get("slug") or ""): row
        for row in canonical_rows
        if str(row.get("slug") or "")
    }
    canonical_by_name = _canonical_suburb_name_index()

    trainers_coll = getattr(db, "trainers", None)
    published_trainers = (
        await trainers_coll.find(
            {"published": True, "region": {"$in": ACTIVE_REGIONS}},
            {"_id": 0, "id": 1, "suburb": 1, "serviced_suburbs": 1},
        ).to_list(5000)
        if trainers_coll is not None
        else []
    )
    eligible_by_slug: Dict[str, int] = {slug: 0 for slug in canonical_by_slug}
    for trainer in published_trainers:
        matched_slugs = set()
        raw_localities = [trainer.get("suburb")]
        serviced_suburbs = trainer.get("serviced_suburbs")
        if isinstance(serviced_suburbs, list):
            raw_localities.extend(serviced_suburbs)
        for locality in raw_localities:
            canonical = canonical_by_name.get(str(locality or "").strip().lower())
            if canonical:
                matched_slugs.add(str(canonical.get("slug") or ""))
        for matched_slug in matched_slugs:
            if matched_slug in eligible_by_slug:
                eligible_by_slug[matched_slug] += 1

    pages_coll = getattr(db, "seo_pages", None)
    stored_records = int(await pages_coll.count_documents({})) if pages_coll is not None else 0
    inventory_limit = 2000
    page_rows = (
        await pages_coll.find(
            {},
            {
                "_id": 0,
                "id": 1,
                "slug": 1,
                "suburb": 1,
                "publication_status": 1,
                "meta_robots": 1,
                "copy": 1,
                "content_word_count": 1,
                "generated_at": 1,
            },
        ).to_list(inventory_limit)
        if pages_coll is not None
        else []
    )
    pages_by_slug: Dict[str, List[Dict[str, Any]]] = {}
    for page in page_rows:
        pages_by_slug.setdefault(str(page.get("slug") or ""), []).append(page)

    rows: List[Dict[str, Any]] = []
    indexable_now = 0
    review_required = 0
    canonical_records = 0
    noncanonical_records = 0
    for slug, canonical in canonical_by_slug.items():
        pages = pages_by_slug.pop(slug, [])
        if pages:
            canonical_records += len(pages)
        page = pages[0] if pages else None
        eligible_count = int(eligible_by_slug.get(slug) or 0)
        word_count = _seo_page_word_count(page) if page else 0
        reasons: List[str] = []
        if minimum_trainers is None or minimum_words is None:
            reasons.append("thresholds_not_configured")
        elif eligible_count < minimum_trainers:
            reasons.append("insufficient_eligible_supply")
        if page is None:
            reasons.append("no_stored_page")
        elif minimum_words is not None and word_count < minimum_words:
            reasons.append("insufficient_content_quality")
        elif str(page.get("publication_status") or "") != "published":
            reasons.append("stored_page_not_published")
        elif str(page.get("meta_robots") or "") != "index,follow":
            reasons.append("stored_page_not_indexable")
        if len(pages) > 1:
            reasons.append("duplicate_stored_pages")

        indexable = bool(page) and not reasons
        if indexable:
            indexable_now += 1
        elif page:
            review_required += 1
        rows.append(
            {
                "slug": slug,
                "suburb": str(canonical.get("suburb_name") or ""),
                "eligible_trainer_count": eligible_count,
                "content_word_count": word_count if page else None,
                # A stored legacy record with no publication field is not the
                # same thing as an absent record. Keep it visible to Ops as an
                # unconfigured record requiring review.
                "publication_status": str(page.get("publication_status") or "unconfigured") if page else "not_stored",
                "meta_robots": str(page.get("meta_robots") or "noindex,follow") if page else "noindex,follow",
                "indexable_now": indexable,
                "reason_codes": reasons,
                "generated_at": page.get("generated_at") if page else None,
            }
        )

    for slug, pages in pages_by_slug.items():
        noncanonical_records += len(pages)
        page = pages[0]
        review_required += 1
        rows.append(
            {
                "slug": slug or "(missing)",
                "suburb": str(page.get("suburb") or ""),
                "eligible_trainer_count": None,
                "content_word_count": _seo_page_word_count(page),
                "publication_status": str(page.get("publication_status") or "unknown"),
                "meta_robots": str(page.get("meta_robots") or "unknown"),
                "indexable_now": False,
                "reason_codes": ["noncanonical_stored_page"],
                "generated_at": page.get("generated_at"),
            }
        )

    rows.sort(key=lambda row: (bool(row.get("indexable_now")), str(row.get("suburb") or "").lower()))
    return {
        "status": "ready" if minimum_trainers is not None and minimum_words is not None else "thresholds_not_configured",
        "thresholds": {
            "minimum_published_trainers": minimum_trainers,
            "minimum_content_words": minimum_words,
        },
        "canonical_suburb_count": len(canonical_rows),
        "stored_record_count": stored_records,
        "canonical_stored_record_count": canonical_records,
        "noncanonical_stored_record_count": noncanonical_records,
        "indexable_now_count": indexable_now,
        "review_required_count": review_required,
        "inventory_truncated": stored_records > len(page_rows),
        "rows": rows,
    }


@api.post("/match")
async def instant_match(
    payload: Union[matching_contract_v2.MatchRequestIn, InstantMatchIn],
    request: Request = None,
    response: Response = None,
) -> Dict[str, Any]:
    """Owner-to-Trainer Matching Endpoint.

    Governance (Decision Contract v2, CDR-018..024, DF-018, DF-019, DF-022, DF-026):
    - Validates versioned request schema (MatchRequestIn).
    - Rate limits by non-reversible IP hash (10 attempts / 10 min, 30s burst).
    - Resolves canonical locality before querying.
    - Pre-AI triage intercepts emergencies and clarifies unresolved concerns.
    - Enforces fail-closed match-ready capability projections (build_match_ready_projection).
    - Evaluates deterministic eligibility and thin supply expansion (local -> expanded).
    - Issues opaque, single-use/expiring context token (stored hashed in db.match_contexts).
    - Persists sanitised match event with zero PII and zero raw behavioural text.
    - Retains 30-day lifecycle metadata.
    """
    # 1. Rate limiting by IP-derived non-reversible key
    client_ip = ""
    if request:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client and request.client.host:
            client_ip = request.client.host

    if client_ip:
        allowed, limit_reason = matching_contract_v2.match_rate_limiter.check_limit(client_ip)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit_reason}. Please wait before submitting another match request.",
            )
        matching_contract_v2.match_rate_limiter.record_attempt(client_ip)

    # 2. Contract normalization and strict consent check
    if isinstance(payload, InstantMatchIn):
        raise HTTPException(
            status_code=400,
            detail="Legacy two-field match requests are deprecated and rejected. Ordinary matching requires a structured MatchRequestIn with dog_age_months, primary_concerns, service_format, method_preference, and explicit consent.",
        )
    req = payload
    if not (req.consent.match_processing and req.consent.terms):
        raise HTTPException(status_code=400, detail="Consent required to process match request.")
    campaign = getattr(req, "campaign", "") or ""
    source = getattr(req, "source", "") or ""
    is_legacy = False

    # 3. Pre-AI Emergency Triage (evaluated first so emergency/urgent requests are never blocked by locality syntax)
    match_id = new_id()
    now_dt = datetime.now(timezone.utc)
    expires_dt = now_dt + timedelta(days=matching_contract_v2.RETENTION_PERIOD_DAYS)

    triage_state = matching_contract_v2.classify_pre_ai_triage(req.primary_concerns, req.behaviour_description)
    if triage_state in {
        matching_contract_v2.DecisionState.IMMEDIATE_HUMAN_DANGER,
        matching_contract_v2.DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT,
    }:
        loc_res = matching_contract_v2.resolve_canonical_locality(req.suburb_or_postcode)
        canonical_suburb = loc_res.get("canonical_name", req.suburb_or_postcode) if loc_res.get("valid") else req.suburb_or_postcode
        triage_resp = matching_contract_v2.DecisionResponseV2(
            decision_state=triage_state,
            search_scope=matching_contract_v2.SearchScope.LOCAL,
            candidates=[],
            reason_codes=[triage_state.value],
        )
        if hasattr(db, "match_events"):
            await db.match_events.insert_one(
                {
                    "id": match_id,
                    "policy_version": getattr(req, "policy_version", matching_contract_v2.DECISION_CONTRACT_VERSION),
                    "decision_state": triage_state.value,
                    "search_scope": matching_contract_v2.SearchScope.LOCAL.value,
                    "reason_codes": [triage_state.value],
                    "result_ids": [],
                    "locality": canonical_suburb,
                    "suburb_or_postcode": req.suburb_or_postcode,
                    "dog_age_months": req.dog_age_months,
                    "primary_concerns": req.primary_concerns,
                    "service_format": req.service_format,
                    "method_preference": req.method_preference,
                    "consent": req.consent.model_dump(),
                    "campaign": campaign,
                    "source": source,
                    "context_token_hash": None,
                    "created_at": now_dt.isoformat(),
                    "expires_at": expires_dt,
                }
            )
        out = triage_resp.model_dump()
        out["match_id"] = match_id
        out["context_token"] = None
        out["matches"] = []
        if triage_state == matching_contract_v2.DecisionState.IMMEDIATE_HUMAN_DANGER:
            out["emergency_notice"] = urgent_providers_service.TRIPLE_ZERO_VICTORIA_NOTICE
        elif triage_state == matching_contract_v2.DecisionState.URGENT_ANIMAL_HEALTH_SUPPORT:
            urgent_docs = await urgent_providers_service.get_active_urgent_providers(
                db, category="urgent_veterinary_care", suburb=canonical_suburb
            )
            out["urgent_providers"] = urgent_docs
            out["coverage_state"] = "local_coverage" if urgent_docs else "no_local_coverage"
            out["coverage_notice"] = (
                "DTD has no current local listing for this area."
                if not urgent_docs
                else None
            )
            out["coverage_disclosure"] = (
                "Local urgent veterinary care entries are verified against official provider pages. "
                "DTD does not claim Melbourne-wide emergency coverage. In an emergency involving human "
                "safety or active dog attack, call Triple Zero (000)."
            )
            out["veterinary_behaviourist_status"] = (
                "No verified veterinary behaviourist listing currently registered with direct official evidence "
                "and active VPRBV registration."
            )
        return out

    # 4. Canonical Locality Resolution (for standard matchmaking)
    loc_res = matching_contract_v2.resolve_canonical_locality(req.suburb_or_postcode)
    if not loc_res["valid"]:
        raw_reason = loc_res.get("reason", "invalid_locality")
        reason = "ambiguous_postcode" if raw_reason == "ambiguous_postcode" else "invalid_locality"
        resp_clarification = matching_contract_v2.DecisionResponseV2(
            decision_state=matching_contract_v2.DecisionState.NEEDS_CLARIFICATION,
            search_scope=matching_contract_v2.SearchScope.LOCAL,
            candidates=[],
            reason_codes=[matching_contract_v2.DecisionState.NEEDS_CLARIFICATION.value, reason],
        )
        out = resp_clarification.model_dump()
        out["match_id"] = match_id
        out["context_token"] = None
        out["matches"] = []
        return out

    canonical_suburb = loc_res.get("canonical_name", req.suburb_or_postcode)

    # 5. Non-emergency clarification triage (e.g. other/unsure concerns)
    if triage_state == matching_contract_v2.DecisionState.NEEDS_CLARIFICATION:
        triage_resp = matching_contract_v2.DecisionResponseV2(
            decision_state=triage_state,
            search_scope=matching_contract_v2.SearchScope.LOCAL,
            candidates=[],
            reason_codes=[triage_state.value],
        )
        if hasattr(db, "match_events"):
            await db.match_events.insert_one(
                {
                    "id": match_id,
                    "policy_version": getattr(req, "policy_version", matching_contract_v2.DECISION_CONTRACT_VERSION),
                    "decision_state": triage_state.value,
                    "search_scope": matching_contract_v2.SearchScope.LOCAL.value,
                    "reason_codes": [triage_state.value],
                    "result_ids": [],
                    "locality": canonical_suburb,
                    "suburb_or_postcode": req.suburb_or_postcode,
                    "dog_age_months": req.dog_age_months,
                    "primary_concerns": req.primary_concerns,
                    "service_format": req.service_format,
                    "method_preference": req.method_preference,
                    "consent": req.consent.model_dump(),
                    "campaign": campaign,
                    "source": source,
                    "context_token_hash": None,
                    "created_at": now_dt.isoformat(),
                    "expires_at": expires_dt,
                }
            )
        out = triage_resp.model_dump()
        out["match_id"] = match_id
        out["context_token"] = None
        out["matches"] = []
        out["clarification_notice"] = (
            "We need a bit more specific information to find a safe and reliable match. "
            "Please select specific behavioural concerns from the options above."
        )
        return out

    # 5. Fetch candidate pool & build match-ready capability projections
    pool_docs = await db.trainers.find(
        {"published": True, "region": {"$in": ACTIVE_REGIONS}},
        {"_id": 0},
    ).to_list(100)

    candidate_pool: List[Dict[str, Any]] = []
    for doc in pool_docs:
        # MP-001: Always rebuild match-ready projection dynamically from source doc
        # at query time. Never trust a stored projection dictionary which bypasses
        # confirmation age and invalidation checks.
        proj = trainer_quality.build_match_ready_projection(doc)
        # Exclude trainers who fail closed on capability/statutory/dispute gates
        # Never fabricate capability or eligibility for unconfirmed profiles
        if not proj.get("match_eligible"):
            continue
        proj["tier"] = doc.get("tier", "unclaimed")
        candidate_pool.append(proj)

    # 6. Execute matching with AI adapter & deterministic fallback wrapper (Contract v2 Section 3, 4, 5)
    ai_adapter = globals().get("matching_ai_adapter") or matching_contract_v2.get_default_ai_adapter()
    decision_resp = await matching_contract_v2.execute_matching_with_adapter_async(
        req, candidate_pool, ai_adapter, triage_state=triage_state, db=db
    )

    # 7. Context Token & Persistence (issued only when results exist for profile handoff)
    has_results_for_handoff = len(decision_resp.candidates) > 0
    raw_token = None
    token_hash = None

    if has_results_for_handoff:
        raw_token, token_hash = matching_contract_v2.generate_match_context_token()
        if hasattr(db, "match_contexts"):
            await db.match_contexts.insert_one(
                {
                    "token_hash": token_hash,
                    "match_id": match_id,
                    "suburb_or_postcode": canonical_suburb,
                    "dog_age_months": req.dog_age_months,
                    "primary_concerns": req.primary_concerns,
                    "service_format": req.service_format,
                    "method_preference": req.method_preference,
                    "created_at": now_dt.isoformat(),
                    "expires_at": expires_dt,
                }
            )

    # 8. Persist sanitised match event in db.match_events (ZERO raw description or PII)
    if hasattr(db, "match_events"):
        await db.match_events.insert_one(
            {
                "id": match_id,
                "policy_version": getattr(req, "policy_version", matching_contract_v2.DECISION_CONTRACT_VERSION),
                "decision_state": decision_resp.decision_state,
                "degraded": getattr(decision_resp, "degraded", False),
                "search_scope": decision_resp.search_scope,
                "reason_codes": [r if isinstance(r, str) else r.value for r in decision_resp.reason_codes],
                "result_ids": [c.trainer_id for c in decision_resp.candidates],
                "presentation_order": [c.trainer_id for c in decision_resp.candidates],
                "candidate_fit_scores": {
                    c.trainer_id: c.match_score for c in decision_resp.candidates if c.match_score is not None
                },
                "locality": canonical_suburb,
                "suburb_or_postcode": req.suburb_or_postcode,
                "dog_age_months": req.dog_age_months,
                "primary_concerns": req.primary_concerns,
                "service_format": req.service_format,
                "method_preference": req.method_preference,
                "consent": req.consent.model_dump(),
                "campaign": campaign,
                "source": source,
                "context_token_hash": token_hash,
                "created_at": now_dt.isoformat(),
                "expires_at": expires_dt,
            }
        )

    # 9. Format public response: strictly exclude raw fit scores and commercial tiers
    cand_by_id = {t["id"]: t for t in pool_docs}
    out = decision_resp.model_dump()
    out["match_id"] = match_id
    out["context_token"] = raw_token

    # Exclude candidates with missing display names (never use "Verified Trainer")
    valid_candidates = []
    valid_matches = []
    for c in decision_resp.candidates:
        cand_doc = cand_by_id.get(c.trainer_id) or {}
        display_name = (cand_doc.get("name") or "").strip()
        if not display_name:
            continue  # Exclude candidate without genuine display name

        scope_val = c.search_scope.value if hasattr(c.search_scope, "value") else str(c.search_scope)
        expanded_disclosure = "Servicing across Greater Melbourne" if scope_val == "expanded" else None

        card_public = {
            "trainer_id": c.trainer_id,
            "name": display_name,
            "locality": cand_doc.get("suburb", ""),
            "service_formats": list(cand_doc.get("service_formats") or []),
            "explanation": c.explanation,
            "search_scope": scope_val,
            "expanded_disclosure": expanded_disclosure,
            "reason_codes": [r if isinstance(r, str) else r.value for r in c.reason_codes],
        }
        valid_candidates.append(card_public)
        valid_matches.append({
            "id": c.trainer_id,
            "name": display_name,
            "suburb": cand_doc.get("suburb", ""),
            "service_formats": list(cand_doc.get("service_formats") or []),
            "match_reasoning": c.explanation,
            "search_scope": scope_val,
            "expanded_disclosure": expanded_disclosure,
            "reason_codes": [r if isinstance(r, str) else r.value for r in c.reason_codes],
        })

    out["candidates"] = valid_candidates
    out["matches"] = valid_matches

    if not valid_candidates and decision_resp.candidates:
        out["decision_state"] = matching_contract_v2.DecisionState.NO_CONFIRMED_MATCH.value
        out["reason_codes"] = ["no_qualified_candidates"]
        out["context_token"] = None
        raw_token = None

    if has_results_for_handoff and response and raw_token:
        response.headers["X-Match-Context-Token"] = raw_token

    if triage_state == matching_contract_v2.DecisionState.SERIOUS_BEHAVIOURAL_SUPPORT:
        out["support_context"] = (
            "Specialist pathway active: results restricted to trainers with declared "
            "aggression and behavioural modification competencies."
        )

    return out


@api.get("/match/context")
async def get_match_context(
    request: Request,
    x_match_context_token: Optional[str] = Header(default=None, alias="X-Match-Context-Token"),
) -> Dict[str, Any]:
    """Retrieve sanitised match context using the opaque session token.

    Governance (Decision Contract v2 Section 2, DF-018, DF-022):
    - Context retrieval is header-based ONLY (X-Match-Context-Token).
    - Query parameter tokens (?token=...) are strictly forbidden and rejected.
    - Context token is stored hashed (SHA-256); raw token is never persisted.
    - Returns only bounded, non-sensitive request parameters.
    - Zero behavioural description or owner PII returned.
    - Validates 30-day expiration TTL.
    """
    if "token" in request.query_params or "context_token" in request.query_params:
        raise HTTPException(
            status_code=400,
            detail="Query parameter authentication is forbidden. Provide token via X-Match-Context-Token header.",
        )

    raw_token = x_match_context_token if isinstance(x_match_context_token, str) else None
    if not raw_token:
        raw_token = request.headers.get("x-match-context-token")
    if not raw_token or not raw_token.strip():
        raise HTTPException(status_code=401, detail="Missing X-Match-Context-Token header")

    token_hash = matching_contract_v2.hash_match_context_token(raw_token.strip())
    ctx = await db.match_contexts.find_one({"token_hash": token_hash}, {"_id": 0})
    if not ctx:
        raise HTTPException(status_code=404, detail="Match context not found or invalid")

    # Check expiration
    if _is_expired(ctx.get("expires_at")):
        raise HTTPException(status_code=410, detail="Match context expired")

    return {
        "match_id": ctx.get("match_id"),
        "suburb_or_postcode": ctx.get("suburb_or_postcode"),
        "dog_age_months": ctx.get("dog_age_months"),
        "primary_concerns": ctx.get("primary_concerns"),
        "service_format": ctx.get("service_format"),
        "method_preference": ctx.get("method_preference"),
        "created_at": ctx.get("created_at"),
    }


def map_notification_delivery_state(
    initial_delivery_state: str,
    notif_meta: Optional[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    """Map notification dispatch outcome to truthful delivery state.

    Governance Invariants (AGENTS.md, M5, M8, MP-002R):
    - 'delivered' requires actual provider acceptance (status == 'sent').
    - Missing provider configuration (no_resend_api_key) is strictly 'retryable_failure' (never 'delivered').
    - Transport error, network timeout, HTTP 5xx is 'retryable_failure'.
    - Missing recipient email or terminal 4xx is 'terminal_failure'.
    - Anti-gaming / fraud / duplicate detection is 'suppressed'.
    """
    if initial_delivery_state == "suppressed":
        return "suppressed", {
            "delivery_state": "suppressed",
            "delivery_status": "suppressed",
            "status": "suppressed",
            "delivery_reason": "fraud_or_duplicate_suppression",
            "delivery_attempts": 0,
            "delivery_last_attempt_at": now_iso(),
        }

    if initial_delivery_state == "terminal_failure":
        return "terminal_failure", {
            "delivery_state": "terminal_failure",
            "delivery_status": "terminal_failure",
            "status": "terminal_failure",
            "delivery_reason": "missing_recipient_email",
            "delivery_attempts": 0,
            "delivery_last_attempt_at": now_iso(),
        }

    meta = notif_meta or {}
    st = meta.get("trainer_notification_status")
    reason = meta.get("trainer_notification_reason") or ""
    err = meta.get("trainer_notification_error") or ""
    attempts = int(meta.get("trainer_notification_attempts") or 0)

    if st == "sent":
        final_state = "delivered"
        final_reason = "provider_accepted"
    elif st == "suppressed":
        final_state = "suppressed"
        final_reason = "fraud_or_duplicate_suppression"
    elif st == "skipped" and reason == "missing_email":
        final_state = "terminal_failure"
        final_reason = "missing_email"
    elif st == "skipped" and reason == "no_resend_api_key":
        final_state = "retryable_failure"
        final_reason = "no_resend_api_key"
    elif st == "failed":
        if "http_4" in str(err) and "429" not in str(err):
            final_state = "terminal_failure"
            final_reason = str(err)
        else:
            final_state = "retryable_failure"
            final_reason = str(err or "transport_failure")
    else:
        final_state = "retryable_failure"
        final_reason = str(reason or err or "unknown_dispatch_state")

    fields = {
        "delivery_state": final_state,
        "delivery_status": final_state,
        "status": final_state,
        "delivery_reason": final_reason,
        "delivery_attempts": attempts,
        "delivery_last_attempt_at": now_iso(),
        **meta,
    }
    return final_state, fields


@api.post("/match/follow-up")
async def create_match_follow_up(
    payload: MatchFollowUpIn,
    request: Request,
    x_match_context_token: Optional[str] = Header(default=None, alias="X-Match-Context-Token"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Dict[str, Any]:
    """Context-authenticated follow-up enquiry submission (Contract v2 Section 2, DF-018, DF-022).

    - Context retrieval is header-based ONLY (X-Match-Context-Token).
    - Query parameter tokens (?token=...) are strictly forbidden.
    - Requires consent_contact_release.
    - Links enquiry to match context without leaking raw behavioural text.
    - Idempotent via Idempotency-Key or match_id + trainer_id + user_email.
    """
    if "token" in request.query_params or "context_token" in request.query_params:
        raise HTTPException(
            status_code=400,
            detail="Query parameter authentication is forbidden. Provide token via X-Match-Context-Token header.",
        )
    raw_token = x_match_context_token if isinstance(x_match_context_token, str) else None
    if not raw_token:
        raw_token = request.headers.get("x-match-context-token")
    if not raw_token or not raw_token.strip():
        raise HTTPException(status_code=401, detail="Missing X-Match-Context-Token header")

    if not payload.consent_contact_release:
        raise HTTPException(status_code=400, detail="Consent required for contact release.")

    token_hash = matching_contract_v2.hash_match_context_token(raw_token.strip())
    ctx = await db.match_contexts.find_one({"token_hash": token_hash}, {"_id": 0})
    if not ctx:
        raise HTTPException(status_code=404, detail="Match context not found or invalid")

    # Expiration check
    if _is_expired(ctx.get("expires_at")):
        raise HTTPException(status_code=410, detail="Match context has expired.")

    trainer = await db.trainers.find_one({"id": payload.trainer_id, "published": True}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")

    match_id = str(ctx.get("match_id") or "")
    if hasattr(db, "match_events") and match_id:
        match_event = await db.match_events.find_one({"id": match_id}, {"_id": 0, "result_ids": 1})
        if match_event and "result_ids" in match_event:
            res_ids = [str(x) for x in (match_event.get("result_ids") or [])]
            if res_ids and payload.trainer_id not in res_ids:
                raise HTTPException(status_code=400, detail="Trainer is not in eligible match results.")

    # Idempotency: enforce both client Idempotency-Key and server composite key
    email_clean = payload.user_email.strip().lower()
    email_hash = hashlib.sha256(email_clean.encode("utf-8")).hexdigest()[:16]
    composite_idem = f"match:{match_id}:{payload.trainer_id}:{email_hash}"

    raw_idem = idempotency_key.strip() if isinstance(idempotency_key, str) and idempotency_key.strip() else None

    query_filter = (
        {"$or": [{"idempotency_key": raw_idem}, {"composite_idempotency_key": composite_idem}]}
        if raw_idem
        else {"composite_idempotency_key": composite_idem}
    )

    existing = await db.intros.find_one(query_filter, {"_id": 0})
    if existing:
        return {
            "intro_id": str(existing.get("id")),
            "match_id": match_id,
            "trainer_id": str(payload.trainer_id),
            "delivery_state": str(existing.get("delivery_state") or existing.get("delivery_status") or "retryable_failure"),
            "idempotent": True,
        }

    ip = (request.client.host if request.client else "") or ""
    intro_id_val = new_id()

    # MP-002: Evaluate anti-gaming and verify trainer contact before dispatch
    fraud = await fraud_service.evaluate_intro(db, ip, trainer["id"], payload.user_email)
    fraud_status = fraud.get("fraud_status") or "clear"
    fraud_reasons = fraud.get("reasons") or []
    initial_delivery_status = fraud.get("delivery_status") or "pending"

    trainer_email = (trainer.get("billing_email") or trainer.get("email") or "").strip()
    if not trainer_email:
        initial_delivery_state = "terminal_failure"
    elif initial_delivery_status == "suppressed":
        initial_delivery_state = "suppressed"
    else:
        initial_delivery_state = "pending"

    concerns_str = ", ".join(ctx.get("primary_concerns") or [])
    description_text = f"Matching follow-up for {ctx.get('suburb_or_postcode') or trainer.get('suburb') or ''}. Concerns: {concerns_str}. Notes: {payload.notes or 'None'}"

    intro = {
        "id": intro_id_val,
        "trainer_id": trainer["id"],
        "trainer_name": trainer.get("name"),
        "match_id": match_id,
        "suburb": ctx.get("suburb_or_postcode") or trainer.get("suburb"),
        "dog_age_months": ctx.get("dog_age_months"),
        "primary_concerns": ctx.get("primary_concerns") or [],
        "service_format": ctx.get("service_format"),
        "description": description_text,
        "user_name": payload.user_name,
        "user_email": payload.user_email,
        "user_phone": payload.user_phone or "",
        "notes": payload.notes or "",
        "consent_contact_release": True,
        "consent_outcome_tracking": True,
        "delivery_status": initial_delivery_state,
        "delivery_state": initial_delivery_state,
        "status": initial_delivery_state,
        "fraud_status": fraud_status,
        "fraud_reasons": fraud_reasons,
        "idempotency_key": raw_idem or composite_idem,
        "composite_idempotency_key": composite_idem,
        "ip": ip,
        "created_at": now_iso(),
    }

    # MP-002S: Concurrency-safe insert with deterministic DuplicateKeyError recovery
    try:
        await db.intros.insert_one(intro.copy())
    except DuplicateKeyError:
        existing = await db.intros.find_one(query_filter, {"_id": 0})
        if existing:
            return {
                "intro_id": str(existing.get("id")),
                "match_id": match_id,
                "trainer_id": str(payload.trainer_id),
                "delivery_state": str(existing.get("delivery_state") or existing.get("delivery_status") or "retryable_failure"),
                "idempotent": True,
            }
        raise

    final_delivery_state = initial_delivery_state
    if initial_delivery_state not in {"terminal_failure", "suppressed"}:
        try:
            notif_meta = await notifications_service.notify_trainer_new_intro(db, trainer, intro)
            final_delivery_state, update_fields = map_notification_delivery_state(initial_delivery_state, notif_meta)
            await db.intros.update_one({"id": intro_id_val}, {"$set": update_fields})
        except Exception as exc:
            logger.exception("Trainer follow-up notification dispatch failed for intro_id=%s", intro_id_val)
            final_delivery_state, update_fields = map_notification_delivery_state("pending", {
                "trainer_notification_status": "failed",
                "trainer_notification_error": str(exc)[:200],
            })
            await db.intros.update_one({"id": intro_id_val}, {"$set": update_fields})
    else:
        final_delivery_state, update_fields = map_notification_delivery_state(initial_delivery_state, None)
        await db.intros.update_one({"id": intro_id_val}, {"$set": update_fields})

    await _audit(
        "match_follow_up",
        trainer["id"],
        after={"intro_id": intro_id_val, "match_id": match_id, "delivery_state": final_delivery_state},
        actor="user",
    )

    # Return strictly permitted follow-up response shape
    return {
        "intro_id": str(intro_id_val),
        "match_id": match_id,
        "trainer_id": str(payload.trainer_id),
        "delivery_state": final_delivery_state,
        "idempotent": False,
    }


@api.post("/match/connect-click")
async def record_match_connect_click(payload: ConnectClickIn) -> Dict[str, Any]:
    match = await db.match_events.find_one({"id": payload.match_id}, {"_id": 0, "result_ids": 1, "campaign": 1, "source": 1})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    result_ids = [str(x) for x in (match.get("result_ids") or [])]
    if payload.trainer_id not in result_ids:
        raise HTTPException(status_code=400, detail="Trainer not present in match results")

    rank = payload.rank if payload.rank and payload.rank > 0 else (result_ids.index(payload.trainer_id) + 1 if payload.trainer_id in result_ids else None)
    ev = {
        "id": new_id(),
        "match_id": payload.match_id,
        "trainer_id": payload.trainer_id,
        "kind": "result_connect_click",
        "rank": rank,
        "campaign": (payload.campaign or match.get("campaign") or "").strip(),
        "source": (payload.source or match.get("source") or "").strip(),
        "created_at": now_iso(),
    }
    await db.engagements.insert_one(ev.copy())
    await _audit(
        "result_connect_click",
        payload.trainer_id,
        after={"match_id": payload.match_id, "rank": rank, "campaign": ev["campaign"], "source": ev["source"]},
        actor="user",
    )
    return _scrub(ev)


@api.get("/urgent-providers")
async def get_urgent_providers(
    category: Optional[str] = Query(default=None),
    suburb: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Retrieve verified urgent support providers from official sources."""
    providers = await urgent_providers_service.get_active_urgent_providers(
        db, category=category, suburb=suburb
    )
    return {
        "urgent_providers": providers,
        "coverage_state": "local_coverage" if providers else "no_local_coverage",
        "coverage_notice": "DTD has no current local listing for this area." if not providers else None,
        "disclaimer": (
            "Local emergency/urgent listings are verified against official provider pages. "
            "DTD does not claim Melbourne-wide urgent coverage. In an emergency involving human "
            "safety or active dog attack, call Triple Zero (000)."
        ),
        "veterinary_behaviourist_verified_count": 0,
        "veterinary_behaviourist_status": (
            "No verified veterinary behaviourist listing currently registered with direct official evidence "
            "and active VPRBV registration."
        ),
        "emergency_notice": urgent_providers_service.TRIPLE_ZERO_VICTORIA_NOTICE,
    }


@api.post("/urgent-providers/correction")
async def create_urgent_provider_correction(
    payload: urgent_providers_service.UrgentProviderCorrectionIn,
) -> Dict[str, Any]:
    """Submit a public correction request for an urgent provider record."""
    if not payload.provider_name.strip() or not payload.official_source_url.strip():
        raise HTTPException(status_code=400, detail="provider_name and official_source_url are required.")

    correction_id = new_id()
    doc = {
        "id": correction_id,
        "provider_id": payload.provider_id,
        "provider_name": payload.provider_name.strip(),
        "official_source_url": payload.official_source_url.strip(),
        "reason": payload.reason,
        "notes": (payload.notes or "").strip(),
        "status": "pending_review",
        "created_at": now_iso(),
    }
    if hasattr(db, "urgent_provider_corrections"):
        await db.urgent_provider_corrections.insert_one(doc)

    return {
        "status": "received",
        "request_id": correction_id,
        "message": "Correction request received for evidence-backed review.",
    }


@api.get("/trainers")
async def list_trainers(
    suburb: Optional[str] = Query(default=None, max_length=100),
    category: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=60, ge=1, le=100),
) -> Dict[str, Any]:
    filters: List[Dict[str, Any]] = []
    if suburb and suburb.strip():
        exact_suburb = {"$regex": f"^{re.escape(suburb.strip())}$", "$options": "i"}
        filters.append({"$or": [{"suburb": exact_suburb}, {"serviced_suburbs": exact_suburb}]})
    if category and category.strip():
        cat_clean = category.strip().lower()
        if cat_clean == "reactivity":
            category_token = {"$regex": r"(reactivity|behaviou?r)", "$options": "i"}
        elif cat_clean in {"in home", "in-home"}:
            category_token = {"$regex": r"(in[- ]home|in[- ]house)", "$options": "i"}
        else:
            category_token = {"$regex": re.escape(cat_clean), "$options": "i"}
        filters.append({"$or": [{"specialties": category_token}, {"services": category_token}, {"categories": category_token}, {"bio": category_token}]})

    query: Dict[str, Any] = {"published": True, "region": {"$in": ACTIVE_REGIONS}}
    if filters:
        query["$and"] = filters
    try:
        rows = await db.trainers.find(query, {"_id": 0}).to_list(limit)
        rows.sort(key=lambda trainer: _directory_sort_key(trainer, suburb), reverse=True)
        rows = await suburb_inventory.rotate_public_trainers(db, rows, suburb=suburb)
    except Exception as exc:
        logger.warning("Database unavailable reading trainers for /trainers: %s", exc)
        rows = []
    return {
        "trainers": [_public_trainer_payload(row) for row in rows],
        "total": len(rows),
        "filters": {"suburb": (suburb or "").strip(), "category": (category or "").strip()},
    }


@api.get("/trainers/{trainer_id}")
async def get_trainer(trainer_id: str) -> Dict[str, Any]:
    doc = await db.trainers.find_one(
        {
            "$or": [{"id": trainer_id}, {"slug": trainer_id}],
            "published": True,
            "region": {"$in": ACTIVE_REGIONS},
        },
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    decorated = await _decorate_with_pricing([doc])
    return _public_trainer_payload(decorated[0])


@api.post("/intros")
async def create_intro(
    payload: IntroIn,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Dict[str, Any]:
    if not payload.consent_contact_release or not payload.consent_outcome_tracking:
        raise HTTPException(status_code=400, detail="Consent required before contact release.")
    trainer = await db.trainers.find_one({"id": payload.trainer_id, "published": True}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    _require_region(trainer.get("region"))

    raw_idem = idempotency_key if isinstance(idempotency_key, str) else None
    idem = (raw_idem or payload.client_token or "").strip()
    if idem:
        existing = await db.intros.find_one({"idempotency_key": idem}, {"_id": 0})
        if existing:
            if existing.get("trainer_id") != payload.trainer_id or str(existing.get("user_email") or "").lower() != str(payload.user_email).lower():
                raise HTTPException(status_code=409, detail="Idempotency key already used for a different enquiry.")
            existing_trainer = await db.trainers.find_one({"id": existing["trainer_id"]}, {"_id": 0})
            contact_existing = _released_contact_payload(
                existing_trainer or {},
                fallback_name=existing.get("trainer_name"),
                fallback_suburb=existing.get("suburb"),
            )
            return _scrub({**existing, "contact": contact_existing})

    if payload.match_id:
        raise HTTPException(
            status_code=400,
            detail="Direct enquiries cannot attach match_id; use /api/match/follow-up with verified context token.",
        )

    ip = (request.client.host if request.client else "") or ""

    # Anti-gaming evaluation.
    fraud = await fraud_service.evaluate_intro(db, ip, trainer["id"], payload.user_email or "")
    fraud_status = fraud.get("fraud_status") or "clear"
    fraud_reasons = fraud.get("reasons") or []
    fraud_delivery = fraud.get("delivery_status") or "pending"

    trainer_email = (trainer.get("billing_email") or trainer.get("email") or "").strip()
    if not trainer_email:
        initial_delivery_state = "terminal_failure"
    elif fraud_status == "suppressed" or fraud_delivery == "suppressed":
        initial_delivery_state = "suppressed"
    else:
        initial_delivery_state = "pending"

    intro = {
        "id": new_id(),
        "trainer_id": trainer["id"],
        "trainer_name": trainer.get("name"),
        "match_id": None,
        "description": payload.description,
        "user_name": payload.user_name or "",
        "user_email": payload.user_email or "",
        "user_phone": payload.user_phone or "",
        "suburb": trainer.get("suburb"),
        "consent_contact_release": True,
        "consent_outcome_tracking": True,
        "delivery_state": initial_delivery_state,
        "delivery_status": initial_delivery_state,
        "status": initial_delivery_state,
        "fraud_status": fraud_status,
        "fraud_reasons": fraud_reasons,
        "ip": ip,
        "user_agent": request.headers.get("user-agent", "")[:200],
        "created_at": now_iso(),
    }
    if idem:
        intro["idempotency_key"] = idem
    try:
        await db.intros.insert_one(intro.copy())
    except DuplicateKeyError:
        if idem:
            existing = await db.intros.find_one({"idempotency_key": idem}, {"_id": 0})
            if existing:
                if existing.get("trainer_id") != payload.trainer_id or str(existing.get("user_email") or "").lower() != str(payload.user_email).lower():
                    raise HTTPException(status_code=409, detail="Idempotency key already used for a different enquiry.")
                existing_trainer = await db.trainers.find_one({"id": existing["trainer_id"]}, {"_id": 0})
                contact_existing = _released_contact_payload(
                    existing_trainer or {},
                    fallback_name=existing.get("trainer_name"),
                    fallback_suburb=existing.get("suburb"),
                )
                return _scrub({**existing, "contact": contact_existing})
        raise

    final_delivery_state = initial_delivery_state
    if initial_delivery_state not in {"terminal_failure", "suppressed"}:
        try:
            notif_meta = await notifications_service.notify_trainer_new_intro(db, trainer, intro)
            final_delivery_state, update_fields = map_notification_delivery_state(initial_delivery_state, notif_meta)
            await db.intros.update_one({"id": intro["id"]}, {"$set": update_fields})
            intro.update(update_fields)
        except Exception as exc:
            logger.exception("trainer intro notification failed for intro_id=%s", intro.get("id"))
            final_delivery_state, update_fields = map_notification_delivery_state("pending", {
                "trainer_notification_status": "failed",
                "trainer_notification_error": str(exc)[:200],
            })
            await db.intros.update_one({"id": intro["id"]}, {"$set": update_fields})
            intro.update(update_fields)
    else:
        final_delivery_state, update_fields = map_notification_delivery_state(initial_delivery_state, None)
        await db.intros.update_one({"id": intro["id"]}, {"$set": update_fields})
        intro.update(update_fields)

    await _audit(
        "intro",
        trainer["id"],
        after={
            "intro_id": intro["id"],
            "delivery_state": final_delivery_state,
            "delivery_status": final_delivery_state,
            "fraud_status": fraud_status,
            "reasons": fraud_reasons,
        },
        actor="user",
    )

    contact = _released_contact_payload(trainer)
    return _scrub({**intro, "contact": contact})


@api.post("/engagements")
async def create_engagement(payload: EngagementIn) -> Dict[str, Any]:
    """Record a user signal after a connection (website click, phone click,
    return visit).  Drives both ranking (response/engagement) and inferred
    conversion confidence.
    """
    intro = await db.intros.find_one({"id": payload.intro_id}, {"_id": 0})
    if not intro:
        raise HTTPException(status_code=404, detail="intro not found")
    ev = {
        "id": new_id(),
        "intro_id": payload.intro_id,
        "trainer_id": intro["trainer_id"],
        "kind": payload.kind,
        "created_at": now_iso(),
    }
    await db.engagements.insert_one(ev.copy())

    # Lightweight inference: ≥2 distinct engagement kinds within 48h → inferred conversion (0.7-0.85 confidence).
    distinct_kinds = await db.engagements.distinct("kind", {"intro_id": payload.intro_id})
    if len(distinct_kinds) >= 2 and not await db.conversions.find_one({"intro_id": payload.intro_id}):
        confidence = min(0.85, 0.55 + 0.10 * len(distinct_kinds))
        target_status = "pending"
        await db.conversions.insert_one(
            {
                "id": new_id(),
                "intro_id": payload.intro_id,
                "trainer_id": intro["trainer_id"],
                "match_id": intro.get("match_id"),
                "campaign": intro.get("campaign", ""),
                "attribution_source": intro.get("source", ""),
                "billing_status": target_status,
                "status": target_status,
                "quality_status": target_status,
                "inferred": True,
                "confidence": round(confidence, 2),
                "source": "engagement_inference",
                "created_at": now_iso(),
            }
        )
        await _audit("inferred_conversion", intro["trainer_id"], after={"intro_id": payload.intro_id, "confidence": confidence}, actor="system")
    return _scrub(ev)


@api.post("/conversions")
async def create_conversion(payload: ConversionIn) -> Dict[str, Any]:
    intro = await db.intros.find_one({"id": payload.intro_id}, {"_id": 0})
    if not intro:
        raise HTTPException(status_code=404, detail="Intro not found")
    if not payload.confirmed:
        return {"ok": True, "confirmed": False, "billed": False}
    existing = await db.conversions.find_one(
        {
            "intro_id": payload.intro_id,
            "$or": [
                {"billing_status": {"$in": ["tracked", "billed", "suspicious"]}},
                {"status": {"$in": ["tracked", "billed", "suspicious"]}},
            ],
        },
        {"_id": 0},
    )
    if existing:
        return {
            "ok": True,
            "confirmed": True,
            "billed": False,
            "existing": True,
            "status": existing.get("status") or existing.get("billing_status"),
            "billing_status": existing.get("billing_status") or existing.get("status"),
        }

    decision = await fraud_service.evaluate_conversion(db, intro)
    quality_status = decision.get("quality_status") or decision.get("status") or ("suspicious" if decision.get("billing_status") == "suspicious" else "tracked")
    status = "suspicious" if quality_status == "suspicious" else "tracked"

    conv = {
        "id": new_id(),
        "intro_id": payload.intro_id,
        "trainer_id": intro["trainer_id"],
        "match_id": intro.get("match_id"),
        "campaign": intro.get("campaign", ""),
        "attribution_source": intro.get("source", ""),
        "billing_status": status,
        "status": status,
        "quality_status": status,
        "fraud_reason": decision.get("reason", ""),
        "inferred": False,
        "confidence": 1.0,
        "source": "manual_confirm",
        "created_at": now_iso(),
    }
    # If a prior pending inferred conversion exists, supersede it.
    await db.conversions.update_many(
        {"intro_id": payload.intro_id, "billing_status": "pending"},
        {"$set": {"billing_status": "superseded", "status": "superseded"}},
    )
    await db.conversions.insert_one(conv.copy())
    await _audit("conversion", intro["trainer_id"], after={"intro_id": payload.intro_id, "status": conv["status"], "billing_status": conv["billing_status"]}, actor="user")
    return _scrub({**conv, "confirmed": True, "billed": False, "fee_cents": 0})


@api.get("/follow-up/{token}")
async def get_follow_up(token: str) -> Dict[str, Any]:
    intro = await _resolve_follow_up_intro(token)

    trainer = await db.trainers.find_one({"id": intro.get("trainer_id")}, {"_id": 0})
    existing = await db.conversions.find_one(
        {"intro_id": intro["id"], "billing_status": {"$in": ["tracked", "billed", "suspicious"]}},
        {"_id": 0, "id": 1, "billing_status": 1, "created_at": 1},
    )
    return {
        "token": token,
        "intro_id": intro["id"],
        "description": intro.get("description", ""),
        "created_at": intro.get("created_at"),
        "expires_at": intro.get("follow_up_expires_at"),
        "already_confirmed": bool(existing),
        "conversion_status": (existing or {}).get("billing_status"),
        "trainer": {
            "id": (trainer or {}).get("id"),
            "name": (trainer or {}).get("name") or intro.get("trainer_name", ""),
            "suburb": (trainer or {}).get("suburb") or intro.get("suburb"),
            "website": (trainer or {}).get("website", ""),
            "phone": (trainer or {}).get("phone", ""),
            "email": (trainer or {}).get("email", ""),
        },
    }


@api.post("/follow-up/{token}/outcome")
async def submit_follow_up_outcome(token: str, payload: FollowUpOutcomeIn) -> Dict[str, Any]:
    intro = await _resolve_follow_up_intro(token)

    action = (payload.action or "").strip().lower()
    if action == "hired":
        conversion = await create_conversion(ConversionIn(intro_id=intro["id"], confirmed=True))
        await db.outreach_events.update_one(
            {"intro_id": intro["id"], "kind": "t7_response_hired"},
            {"$set": {"id": new_id(), "intro_id": intro["id"], "kind": "t7_response_hired", "status": "recorded", "created_at": now_iso()}},
            upsert=True,
        )
        return {"ok": True, "action": "hired", "conversion": conversion}
    if action in {"still_deciding", "need_another_match"}:
        kind = "t7_response_still_deciding" if action == "still_deciding" else "t7_response_need_another_match"
        await db.outreach_events.update_one(
            {"intro_id": intro["id"], "kind": kind},
            {"$set": {"id": new_id(), "intro_id": intro["id"], "kind": kind, "status": "recorded", "created_at": now_iso()}},
            upsert=True,
        )
        await _audit("follow_up_outcome", intro.get("trainer_id", ""), after={"intro_id": intro["id"], "action": action}, actor="user")
        return {"ok": True, "action": action}
    raise HTTPException(status_code=400, detail="Invalid follow-up action.")


@api.post("/discovery")
async def submit_discovery(payload: DiscoveryIn) -> Dict[str, Any]:
    """Accept an untrusted legacy URL contribution into the held queue.

    This endpoint is not proof of source rights and is not the pending licensed
    Sensis/Thryv adapter. The discovery loop may deduplicate or discard the
    contribution, but any promoted trainer remains unpublished and unverified
    until separate statutory and source evidence passes the publication gate.
    """
    doc = {
        "id": new_id(),
        "url": payload.url,
        "hint_name": payload.hint_name or "",
        "hint_suburb": payload.hint_suburb or "",
        "hint_bio": payload.hint_bio or "",
        "source": payload.source or "public",
        "status": "pending",
        "created_at": now_iso(),
    }
    await db.discovery_queue.insert_one(doc.copy())
    return _scrub(doc)


@api.post("/submissions")
async def create_submission(payload: SubmissionIn) -> Dict[str, Any]:
    """Submit a real Melbourne trainer; publish only with active ABR evidence and the quality gate."""
    if not payload.consent_public_listing or not payload.consent_information_accuracy:
        raise HTTPException(status_code=400, detail="Consent required for public listing.")

    sub = payload.model_dump()
    sub["region"] = (sub.get("region") or ACTIVE_REGION).strip() or ACTIVE_REGION
    # Claims and commercial tier are server-owned. A public submission may
    # enrich a profile, but cannot self-assert ownership or verification.
    sub["tier"] = "unclaimed"
    sub["claim_status"] = "unclaimed"
    sub.update(await _abn_profile_fields(sub.get("abn")))
    # Preserve explicit submitter email when provided; otherwise fall back to
    # the listing email so status notifications are still deliverable.
    sub["submitter_email"] = (sub.get("submitter_email") or sub.get("email") or "").strip()
    _require_region(sub["region"])
    score = await ai_service.score_trainer(_verification_payload(sub))
    conf = float(score["confidence"])

    # Duplicate identity matching:
    # 1. By non-empty ABN
    # 2. By non-empty email
    # 3. By non-empty website
    existing_trainer = None
    clean_abn = str(sub.get("abn") or "").strip()
    if clean_abn:
        existing_trainer = await db.trainers.find_one({"abn": clean_abn}, {"_id": 0})
    if not existing_trainer and sub.get("email"):
        existing_trainer = await db.trainers.find_one({"email": str(sub["email"]).strip()}, {"_id": 0})
    if not existing_trainer and sub.get("website"):
        existing_trainer = await db.trainers.find_one({"website": str(sub["website"]).strip()}, {"_id": 0})

    if existing_trainer and str(existing_trainer.get("claim_status") or "").lower() in {"claimed", "claim_disputed"}:
        # R4: Atomically invalidate capabilities upon ownership dispute
        inv_caps = trainer_quality.invalidate_trainer_capabilities(existing_trainer, reason="ownership_dispute")
        await db.trainers.update_one(
            {"id": existing_trainer["id"]},
            {"$set": {"claim_status": "claim_disputed", "capabilities": inv_caps, "updated_at": now_iso()}},
        )
        await _audit("trainer_capabilities_invalidated", existing_trainer["id"], after={"reason": "ownership_dispute"}, actor="system")

        sub_doc = {
            "id": new_id(),
            "trainer_id": existing_trainer["id"],
            "status": "held",
            "duplicate": True,
            "reason": "profile_already_claimed",
            "created_at": now_iso(),
            "confidence_score": conf,
            "verification_status": "hold",
            "verification_reasoning": "Competing submission for an already claimed listing.",
            "verification_signals": score.get("signals", []),
            "verification_model": score.get("model", "heuristic"),
            **sub,
        }
        await db.submissions.insert_one(sub_doc.copy())
        await _audit("trainer_submission_disputed", existing_trainer["id"], after={"submission_id": sub_doc["id"], "reason": "profile_already_claimed"}, actor="system")
        return _scrub({
            "id": sub_doc["id"],
            "status": sub_doc["status"],
            "confidence_score": conf,
            "verification_status": sub_doc["verification_status"],
            "verification_reasoning": sub_doc["verification_reasoning"],
            "verification_signals": sub_doc["verification_signals"],
            "trainer_id": existing_trainer["id"],
            "billing_profile_status": "not_applicable",
            "submitter_notification_status": "skipped",
            "trainer_action_token": "",
            "duplicate": True,
            "reason": "profile_already_claimed",
        })

    # M1-AI Safety Boundary: Gemini or heuristic confidence assessment alone NEVER
    # publishes a profile or marks it verified. Canonical non-AI quality evidence
    # (statutory ABN verification via ABR Web Services) is strictly required before
    # publication or verified lifecycle status.
    has_statutory_abn = bool(sub.get("abn_verified"))
    is_eligible_for_publish = has_statutory_abn and conf >= HOLD_THRESHOLD

    if is_eligible_for_publish:
        published = True
        verification_status = "verified"
        contact_ready = bool(sub.get("website") or sub.get("phone") or sub.get("email"))
        auto_action = "auto_published"
        sub_status = "published"
    else:
        published = False
        verification_status = "unverified" if conf >= HOLD_THRESHOLD else "hold"
        contact_ready = False
        auto_action = "auto_held"
        sub_status = "held"

    sub_doc = {
        "id": new_id(),
        "status": sub_status,
        "created_at": now_iso(),
        "confidence_score": conf,
        "verification_status": verification_status,
        "verification_reasoning": score.get("reasoning", ""),
        "verification_signals": score.get("signals", []),
        "verification_model": score.get("model", "heuristic"),
        **sub,
    }

    declared_capabilities = trainer_quality.package_trainer_capabilities(
        specialties=sub.get("specialties"),
        service_formats=sub.get("service_formats"),
        life_stages=sub.get("life_stages"),
        training_philosophy=sub.get("training_philosophy"),
        serviced_suburbs=sub.get("serviced_suburbs"),
        catchment_type=sub.get("catchment_type"),
        delivery_constraints=sub.get("delivery_constraints"),
        basis="trainer_declaration",
        evidence_reference=sub_doc["id"],
        confirmed_at=now_iso(),
    )

    if existing_trainer:
        trainer_id = existing_trainer["id"]
        update_fields = {
            "name": sub.get("name") or existing_trainer.get("name"),
            "suburb": sub.get("suburb") or existing_trainer.get("suburb"),
            "region": sub.get("region") or existing_trainer.get("region", ""),
            "website": sub.get("website") or existing_trainer.get("website", ""),
            "phone": sub.get("phone") or existing_trainer.get("phone", ""),
            "email": sub.get("email") or existing_trainer.get("email", ""),
            "categories": sub.get("categories") or existing_trainer.get("categories", []),
            "services": sub.get("services") or existing_trainer.get("services", []),
            "bio": sub.get("bio") or existing_trainer.get("bio", ""),
            "image_url": sub.get("image_url") or existing_trainer.get("image_url", ""),
            "source_evidence_url": sub.get("source_evidence_url") or existing_trainer.get("source_evidence_url", ""),
            "abn": sub.get("abn") or existing_trainer.get("abn", ""),
            "entity_name": sub.get("entity_name") or existing_trainer.get("entity_name", ""),
            "trading_name": sub.get("trading_name") or existing_trainer.get("trading_name", ""),
            "business_type": sub.get("business_type") or existing_trainer.get("business_type", ""),
            "abn_status": sub.get("abn_status") or existing_trainer.get("abn_status", "not_provided"),
            "abn_verified": bool(sub.get("abn_verified")),
            "abn_verified_at": sub.get("abn_verified_at") or existing_trainer.get("abn_verified_at", ""),
            "abn_verification_reason": sub.get("abn_verification_reason") or existing_trainer.get("abn_verification_reason", ""),
            "abn_badge_payload": sub.get("abn_badge_payload") or existing_trainer.get("abn_badge_payload"),
            "training_philosophy": sub.get("training_philosophy") or existing_trainer.get("training_philosophy", ""),
            "specialties": sub.get("specialties") or existing_trainer.get("specialties", []),
            "service_formats": sub.get("service_formats") or existing_trainer.get("service_formats", []),
            "serviced_suburbs": sub.get("serviced_suburbs") or existing_trainer.get("serviced_suburbs", []),
            "catchment_type": sub.get("catchment_type") or existing_trainer.get("catchment_type", ""),
            "capabilities": declared_capabilities,
            "booking_url": sub.get("booking_url") or existing_trainer.get("booking_url", ""),
            "gallery_images": sub.get("gallery_images") or existing_trainer.get("gallery_images", []),
            "sponsored_suburbs": sub.get("sponsored_suburbs") or existing_trainer.get("sponsored_suburbs", []),
            "review_summary": sub.get("review_summary") or existing_trainer.get("review_summary", ""),
            "confidence_score": conf,
            "verification_status": verification_status,
            "verification_reasoning": score.get("reasoning", ""),
            "verification_signals": score.get("signals", []),
            "verification_model": score.get("model", "heuristic"),
            "verified_at": now_iso() if verification_status == "verified" else "",
            "published": published,
            "contact_ready": contact_ready,
            "updated_at": now_iso(),
            "via_submission_id": sub_doc["id"],
        }
        await db.trainers.update_one({"id": trainer_id}, {"$set": update_fields})
        trainer_doc = {**existing_trainer, **update_fields}
    else:
        trainer_id = new_id()
        trainer_doc = {
            "id": trainer_id,
            "name": sub.get("name"),
            "suburb": sub.get("suburb"),
            "region": sub.get("region", ""),
            "website": sub.get("website", ""),
            "phone": sub.get("phone", ""),
            "email": sub.get("email", ""),
            "categories": sub.get("categories", []),
            "services": sub.get("services", []),
            "bio": sub.get("bio", ""),
            "image_url": sub.get("image_url", ""),
            "source_evidence_url": sub.get("source_evidence_url", ""),
            "tier": "unclaimed",
            "claim_status": "unclaimed",
            "abn": sub.get("abn", ""),
            "entity_name": sub.get("entity_name", ""),
            "trading_name": sub.get("trading_name", ""),
            "business_type": sub.get("business_type", ""),
            "abn_status": sub.get("abn_status", "not_provided"),
            "abn_verified": bool(sub.get("abn_verified")),
            "abn_verified_at": sub.get("abn_verified_at", ""),
            "abn_verification_reason": sub.get("abn_verification_reason", ""),
            "abn_badge_payload": sub.get("abn_badge_payload"),
            "training_philosophy": sub.get("training_philosophy", ""),
            "specialties": sub.get("specialties", []),
            "service_formats": sub.get("service_formats", []),
            "serviced_suburbs": sub.get("serviced_suburbs", []),
            "catchment_type": sub.get("catchment_type", ""),
            "capabilities": declared_capabilities,
            "booking_url": sub.get("booking_url", ""),
            "gallery_images": sub.get("gallery_images", []),
            "sponsored_suburbs": sub.get("sponsored_suburbs", []),
            "review_summary": sub.get("review_summary", ""),
            "confidence_score": conf,
            "verification_status": verification_status,
            "verification_reasoning": score.get("reasoning", ""),
            "verification_signals": score.get("signals", []),
            "verification_model": score.get("model", "heuristic"),
            "verified_at": now_iso() if verification_status == "verified" else "",
            "outcome_score": 0.05,
            "intros_30d": 0,
            "conversions_30d": 0,
            "published": published,
            "contact_ready": contact_ready,
            "registered_at": now_iso(),
            "created_at": now_iso(),
            "via_submission_id": sub_doc["id"],
        }
        await db.trainers.insert_one(trainer_doc.copy())

    # Prepare trainer billing profile (fail-soft). This does not block
    # publication and gives ops visibility into billing readiness.
    billing_profile = await stripe_billing.provision_trainer_billing_profile(
        db,
        trainer_doc,
        consent_granted=payload.consent_intro_billing_terms,
    )
    trainer_action_token = _issue_trainer_action_token(
        trainer_id=trainer_id,
        submission_id=sub_doc["id"],
    )
    sub_doc["trainer_id"] = trainer_id
    sub_doc["billing_profile_status"] = billing_profile.get("billing_profile_status")
    sub_doc["trainer_action_token"] = trainer_action_token

    try:
        await db.submissions.insert_one(sub_doc.copy())
    except Exception:
        if trainer_id:
            await db.trainers.delete_one({"id": trainer_id, "via_submission_id": sub_doc["id"]})
        raise

    try:
        submission_notif = await notifications_service.notify_submitter_result(db, sub_doc)
        if submission_notif:
            await db.submissions.update_one({"id": sub_doc["id"]}, {"$set": submission_notif})
            sub_doc.update(submission_notif)
    except Exception:  # noqa: BLE001
        logger.exception("submission notification failed for submission_id=%s", sub_doc.get("id"))

    await _audit(
        auto_action,
        sub_doc["id"],
        after={
            "confidence": conf,
            "trainer_id": trainer_id,
            "published": published,
            "verification_status": verification_status,
        },
        actor="system",
    )
    return _scrub(
        {
            "id": sub_doc["id"],
            "status": sub_doc["status"],
            "confidence_score": conf,
            "verification_status": verification_status,
            "verification_reasoning": sub_doc["verification_reasoning"],
            "verification_signals": sub_doc["verification_signals"],
            "trainer_id": trainer_id,
            "billing_profile_status": sub_doc.get("billing_profile_status"),
            "submitter_notification_status": sub_doc.get("submitter_notification_status"),
            "trainer_action_token": sub_doc.get("trainer_action_token"),
        }
    )


@api.post("/trainers/{trainer_id}/claim")
async def start_trainer_claim(trainer_id: str, payload: TrainerClaimStartIn) -> Dict[str, Any]:
    """Start a bounded profile claim against the listing's existing email."""
    trainer = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found.")

    now = datetime.now(timezone.utc)
    claimant_email = _normalize_email_key(str(payload.email))
    listed_email = _normalize_email_key(str(trainer.get("billing_email") or trainer.get("email") or ""))
    method = (payload.method or "email").strip().lower()

    current_status = str(trainer.get("claim_status") or "").lower()
    if current_status in {"claimed", "claim_disputed"}:
        raise HTTPException(
            status_code=409,
            detail="This profile already has a claim. A review case has been opened." if current_status == "claim_disputed" else "This profile has already been claimed.",
        )

    if method != "email":
        event = {
            "id": new_id(),
            "trainer_id": trainer_id,
            "claimant_email": claimant_email,
            "masked_destination": claim_engine.mask_email(claimant_email),
            "method": method or "unknown",
            "status": "provider_unavailable",
            "reason": "sms_unavailable_firebase_phone_auth_not_configured",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await db.claim_events.insert_one(event)
        raise HTTPException(status_code=503, detail="SMS/phone claim verification is not available yet. Use the listed email address.")

    if not listed_email:
        event = {
            "id": new_id(),
            "trainer_id": trainer_id,
            "claimant_email": claimant_email,
            "masked_destination": claim_engine.mask_email(claimant_email),
            "method": "email",
            "status": "needs_review",
            "reason": "listing_has_no_claim_email",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await db.claim_events.insert_one(event)
        raise HTTPException(status_code=409, detail="This profile has no claimable email address. A review case has been opened.")

    if claimant_email != listed_email:
        event = {
            "id": new_id(),
            "trainer_id": trainer_id,
            "claimant_email": claimant_email,
            "masked_destination": claim_engine.mask_email(claimant_email),
            "method": "email",
            "status": "needs_review",
            "reason": "claim_email_does_not_match_listing",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await db.claim_events.insert_one(event)
        raise HTTPException(status_code=403, detail="Use the email address currently recorded on this listing.")

    # Rate limit: enforce cooldown between challenge dispatches for the same listing
    if TRAINER_CLAIM_RESEND_COOLDOWN_S > 0:
        recent_pending = await db.claim_events.find_one(
            {"trainer_id": trainer_id, "status": "pending_verification"}
        )
        if recent_pending:
            created_dt = _parse_iso(recent_pending.get("created_at"))
            if created_dt and (now - created_dt).total_seconds() < TRAINER_CLAIM_RESEND_COOLDOWN_S:
                cooldown_remaining = max(1, int(TRAINER_CLAIM_RESEND_COOLDOWN_S - (now - created_dt).total_seconds()))
                event = {
                    "id": new_id(),
                    "trainer_id": trainer_id,
                    "claimant_email": claimant_email,
                    "masked_destination": claim_engine.mask_email(claimant_email),
                    "method": method,
                    "status": "rate_limited",
                    "reason": "resend_cooldown_active",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
                await db.claim_events.insert_one(event)
                await _audit("trainer_claim_rate_limited", trainer_id, after={"claim_event_id": event["id"], "cooldown_remaining": cooldown_remaining}, actor="user")
                raise HTTPException(status_code=429, detail=f"Please wait {cooldown_remaining}s before requesting another claim code.")

    # New challenges supersede older unsatisfied attempts for this trainer.
    await db.claim_events.update_many(
        {"trainer_id": trainer_id, "status": "pending_verification"},
        {"$set": {"status": "superseded", "updated_at": now.isoformat()}},
    )
    otp = claim_engine.generate_otp()
    event = {
        "id": new_id(),
        "trainer_id": trainer_id,
        "claimant_email": claimant_email,
        "masked_destination": claim_engine.mask_email(listed_email),
        "method": "email",
        "otp_digest": claim_engine.otp_digest(otp),
        "attempts": 0,
        "max_attempts": max(1, TRAINER_CLAIM_OTP_MAX_ATTEMPTS),
        "status": "pending_verification",
        "delivery_status": "pending",
        "expires_at": (now + timedelta(seconds=max(60, TRAINER_CLAIM_OTP_TTL_S))).isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.claim_events.insert_one(event)
    await db.trainers.update_one({"id": trainer_id}, {"$set": {"claim_status": "pending_verification", "claim_pending_at": now.isoformat()}})

    try:
        delivery = await notifications_service.notify_trainer_claim_otp(db, trainer, to_email=listed_email, otp=otp)
    except Exception:  # noqa: BLE001
        logger.exception("trainer claim notification failed trainer_id=%s", trainer_id)
        delivery = {"claim_notification_status": "failed", "claim_notification_attempts": 0, "claim_notification_error": "notification_exception"}
    delivery_status = str(delivery.get("claim_notification_status") or "failed")
    event_status = "pending_verification" if delivery_status == "sent" else "delivery_failed"
    if event_status == "delivery_failed":
        await db.trainers.update_one({"id": trainer_id, "claim_status": "pending_verification"}, {"$set": {"claim_status": "unclaimed"}})
    await db.claim_events.update_one(
        {"id": event["id"]},
        {"$set": {"status": event_status, "delivery_status": delivery_status, "delivery_attempts": int(delivery.get("claim_notification_attempts") or 0), "delivery_error": str(delivery.get("claim_notification_error") or delivery.get("claim_notification_reason") or "")[:240], "updated_at": now_iso()}},
    )
    await _audit("trainer_claim_started", trainer_id, after={"claim_event_id": event["id"], "delivery_status": delivery_status}, actor="user")
    return _scrub({
        "claim_event_id": event["id"],
        "status": event_status,
        "delivery_status": delivery_status,
        "masked_destination": event["masked_destination"],
        "expires_at": event["expires_at"],
    })


@api.post("/trainers/{trainer_id}/claim/verify")
@api.post("/trainers/{trainer_id}/verify")
async def verify_trainer_claim(trainer_id: str, payload: TrainerClaimVerifyIn) -> Dict[str, Any]:
    """Verify an email challenge and create a narrow, signed claim session."""
    trainer = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found.")
    now = datetime.now(timezone.utc)
    if str(trainer.get("claim_status") or "").lower() == "claim_disputed":
        if payload.claim_event_id:
            await db.claim_events.update_one(
                {"id": payload.claim_event_id, "trainer_id": trainer_id, "status": "pending_verification"},
                {"$set": {"status": "stale", "reason": "profile_claim_disputed", "updated_at": now.isoformat()}},
            )
        raise HTTPException(status_code=409, detail="This profile is under ownership dispute and cannot be claimed automatically.")
    event = await db.claim_events.find_one({"id": payload.claim_event_id, "trainer_id": trainer_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Claim challenge not found.")
    if str(event.get("status") or "") != "pending_verification":
        raise HTTPException(status_code=409, detail="Claim challenge is not available for verification.")

    expires_at = _parse_iso(str(event.get("expires_at") or ""))
    if not expires_at or expires_at <= now:
        await db.claim_events.update_one({"id": event["id"]}, {"$set": {"status": "expired", "updated_at": now.isoformat()}})
        raise HTTPException(status_code=410, detail="Claim code expired. Request a new code.")
    attempts = int(event.get("attempts") or 0)
    max_attempts = max(1, int(event.get("max_attempts") or TRAINER_CLAIM_OTP_MAX_ATTEMPTS))
    if attempts >= max_attempts:
        await db.claim_events.update_one({"id": event["id"]}, {"$set": {"status": "locked", "updated_at": now.isoformat()}})
        raise HTTPException(status_code=429, detail="Claim code is locked. Request a new code.")
    if not claim_engine.otp_matches(payload.otp, str(event.get("otp_digest") or "")):
        next_attempt = attempts + 1
        status = "locked" if next_attempt >= max_attempts else "pending_verification"
        await db.claim_events.update_one(
            {"id": event["id"]},
            {"$set": {"attempts": next_attempt, "status": status, "updated_at": now.isoformat()}},
        )
        if status == "locked":
            raise HTTPException(status_code=429, detail="Claim code is locked. Request a new code.")
        raise HTTPException(status_code=400, detail="Claim code is invalid.")

    current_status = str(trainer.get("claim_status") or "").lower()
    if current_status == "claimed":
        await db.claim_events.update_one(
            {"id": event["id"]},
            {"$set": {"status": "stale", "reason": "profile_already_claimed", "updated_at": now.isoformat()}},
        )
        raise HTTPException(status_code=409, detail="This profile has already been claimed.")
    if current_status == "claim_disputed":
        await db.claim_events.update_one(
            {"id": event["id"]},
            {"$set": {"status": "stale", "reason": "profile_claim_disputed", "updated_at": now.isoformat()}},
        )
        raise HTTPException(status_code=409, detail="This profile is under ownership dispute and cannot be claimed automatically.")

    # R2: Keep identity/ownership claim verification separate from capability confirmation.
    # The server MUST NOT promote capabilities solely because OTP verification succeeded.
    claim_update = await db.trainers.update_one(
        {"id": trainer_id, "claim_status": {"$in": ["", "unclaimed", "pending_verification"]}},
        {
            "$set": {
                "claim_status": "claimed",
                "tier": "claimed",
                "claimed_at": now.isoformat(),
                "claim_event_id": event["id"],
            }
        },
    )
    if getattr(claim_update, "matched_count", 1) != 1:
        await db.claim_events.update_one(
            {"id": event["id"], "status": "pending_verification"},
            {"$set": {"status": "stale", "reason": "profile_already_claimed", "updated_at": now.isoformat()}},
        )
        raise HTTPException(status_code=409, detail="This profile has already been claimed.")
    await db.claim_events.update_one(
        {"id": event["id"], "status": "pending_verification"},
        {"$set": {"status": "verified", "verified_at": now.isoformat(), "updated_at": now.isoformat()}},
    )
    session = _issue_trainer_claim_session(trainer_id=trainer_id, claim_event_id=event["id"])
    await _audit("trainer_claim_verified", trainer_id, after={"claim_event_id": event["id"]}, actor="user")
    return _scrub({
        "ok": True,
        "trainer_id": trainer_id,
        "claim_status": "claimed",
        "tier": "claimed",
        "capabilities_confirmed": bool(trainer.get("capabilities_confirmed_at")),
        "session": session,
    })


class DeliveryConstraintsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    in_home_available: Optional[bool] = None
    facility_available: Optional[bool] = None
    travel_distance_km: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("in_home_available", "facility_available", mode="before")
    @classmethod
    def validate_strict_bool(cls, v: Any) -> Optional[bool]:
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        raise ValueError("Availability flags must be actual booleans (true or false), not strings or numbers.")

    @field_validator("travel_distance_km", mode="before")
    @classmethod
    def validate_distance(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("travel_distance_km must be a number, not a boolean or string.")
        val = float(v)
        if math.isnan(val) or math.isinf(val):
            raise ValueError("travel_distance_km must be finite.")
        if val < 0.0 or val > 200.0:
            raise ValueError("travel_distance_km must be between 0 and 200 km.")
        return val

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Notes must be a string.")
        trimmed = v.strip()
        if len(trimmed) > 200:
            raise ValueError("Notes must not exceed 200 characters.")
        return trimmed


class TrainerCapabilitiesConfirmIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    specialties: Optional[List[str]] = None
    service_formats: Optional[List[str]] = None
    life_stages: Optional[List[str]] = None
    training_philosophy: Optional[str] = None
    serviced_suburbs: Optional[List[str]] = None
    catchment_type: Optional[str] = None
    delivery_constraints: Optional[DeliveryConstraintsIn] = None
    confirmation_statement: bool = False
    trainer_claim_session: Optional[str] = None


@api.get("/trainers/{trainer_id}/capabilities/prefill")
async def get_trainer_capabilities_prefill(
    trainer_id: str,
    request: Request,
    x_trainer_claim_session: Optional[str] = Header(None, alias="X-Trainer-Claim-Session"),
) -> Dict[str, Any]:
    """Retrieve prefilled trainer capabilities and canonical taxonomy options for confirmation UI.

    Requires valid trainer claim session matching trainer_id or administrative oversight credentials.
    """
    req_headers = request.headers if request else {}
    session_hdr = x_trainer_claim_session if isinstance(x_trainer_claim_session, str) else None
    token = (
        session_hdr
        or req_headers.get("X-Trainer-Claim-Session")
        or (req_headers.get("Authorization") or "").replace("Bearer ", "").strip()
    )
    admin_pass = req_headers.get("X-Admin-Pass") or ""
    expected_admin_pass = os.environ.get("ADMIN_PASS")
    is_admin = bool(expected_admin_pass and admin_pass and hmac.compare_digest(admin_pass, expected_admin_pass))

    if not is_admin:
        if not token:
            raise HTTPException(status_code=401, detail="Trainer claim session or admin authorization required.")
        _verify_trainer_claim_session(token, trainer_id=trainer_id)

    trainer = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found.")

    caps = trainer.get("capabilities") or {}
    prefill = {
        "specialties": (
            (caps.get("specialties") or {}).get("canonical_value")
            or trainer.get("specialties")
            or trainer.get("services")
            or []
        ),
        "service_formats": (
            (caps.get("service_formats") or {}).get("canonical_value")
            or trainer.get("service_formats")
            or []
        ),
        "life_stages": (
            (caps.get("life_stages") or {}).get("canonical_value")
            or trainer.get("life_stages")
            or []
        ),
        "training_philosophy": (
            (caps.get("training_philosophy") or {}).get("canonical_value")
            or trainer.get("training_philosophy")
            or trainer.get("philosophy")
            or ""
        ),
        "serviced_suburbs": (
            (caps.get("serviced_suburbs") or {}).get("canonical_value")
            or trainer.get("serviced_suburbs")
            or ([trainer.get("suburb")] if trainer.get("suburb") else [])
        ),
        "catchment_type": (
            (caps.get("catchment_type") or {}).get("canonical_value")
            or trainer.get("catchment_type")
            or "specific_suburbs"
        ),
        "delivery_constraints": (
            ((caps.get("delivery_constraints") or {}).get("canonical_value") or (caps.get("delivery_constraints") or {}).get("value"))
            if (caps.get("delivery_constraints") or {}).get("permitted_in_projection")
            else {
                "in_home_available": False,
                "facility_available": False,
                "travel_distance_km": 0.0,
                "notes": "",
            }
        ),
        "capabilities_confirmed_at": trainer.get("capabilities_confirmed_at") or "",
        "claim_status": trainer.get("claim_status") or "unclaimed",
    }
    options = {
        "specialties": [
            {"id": k, "label": v["label"]}
            for k, v in trainer_quality.CANONICAL_SPECIALTIES.items()
        ],
        "service_formats": [
            {"id": k, "label": v["label"]}
            for k, v in trainer_quality.CANONICAL_SERVICE_FORMATS.items()
        ],
        "life_stages": [
            {"id": k, "label": v["label"]}
            for k, v in trainer_quality.CANONICAL_LIFE_STAGES.items()
        ],
        "training_philosophies": [
            {"id": k, "label": v["label"]}
            for k, v in trainer_quality.VALID_TRAINING_PHILOSOPHIES.items()
        ],
        "catchment_types": [
            {"id": k, "label": v["label"]}
            for k, v in trainer_quality.VALID_CATCHMENT_TYPES.items()
        ],
    }
    return _scrub({
        "ok": True,
        "trainer_id": trainer_id,
        "prefill": prefill,
        "prefilled": prefill,
        "options": options,
        "canonical_options": options,
    })


@api.post("/trainers/{trainer_id}/capabilities/confirm")
async def confirm_trainer_capabilities(
    trainer_id: str,
    payload: TrainerCapabilitiesConfirmIn,
    request: Request,
    x_trainer_claim_session: Optional[str] = Header(None, alias="X-Trainer-Claim-Session"),
) -> Dict[str, Any]:
    """Explicitly confirm and declare structured trainer capabilities (R2).

    Requires explicit confirmation statement and valid trainer claim session or admin pass.
    """
    req_headers = request.headers if request else {}
    session_hdr = x_trainer_claim_session if isinstance(x_trainer_claim_session, str) else None
    token = (
        session_hdr
        or req_headers.get("X-Trainer-Claim-Session")
        or payload.trainer_claim_session
        or (req_headers.get("Authorization") or "").replace("Bearer ", "").strip()
    )
    admin_pass = req_headers.get("X-Admin-Pass") or ""
    expected_admin_pass = os.environ.get("ADMIN_PASS")
    is_admin = bool(expected_admin_pass and admin_pass and hmac.compare_digest(admin_pass, expected_admin_pass))

    claim_session = None
    if not is_admin:
        if not token:
            raise HTTPException(status_code=401, detail="Trainer claim session or admin authorization required.")
        claim_session = _verify_trainer_claim_session(token, trainer_id=trainer_id)

    trainer = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found.")

    if str(trainer.get("claim_status") or "").lower() == "claim_disputed":
        raise HTTPException(status_code=409, detail="This profile is under ownership dispute and capabilities cannot be confirmed.")

    # R2: Strict confirmation statement requirement
    if not payload.confirmation_statement:
        raise HTTPException(
            status_code=422,
            detail="Explicit confirmation statement is required before capabilities gain trainer declaration basis.",
        )

    now_ts = now_iso()
    claim_ref = f"claim_confirmation:{claim_session['claim_event_id']}" if claim_session else f"ops_confirmation:{now_ts}"

    dc_dict = (
        payload.delivery_constraints.model_dump(exclude_unset=True)
        if hasattr(payload.delivery_constraints, "model_dump")
        else payload.delivery_constraints
    )

    # Package validated structured capabilities
    confirmed_caps = trainer_quality.package_trainer_capabilities(
        specialties=payload.specialties,
        service_formats=payload.service_formats,
        life_stages=payload.life_stages,
        training_philosophy=payload.training_philosophy,
        serviced_suburbs=payload.serviced_suburbs,
        catchment_type=payload.catchment_type,
        delivery_constraints=dc_dict,
        basis="trainer_declaration",
        evidence_reference=claim_ref,
        confirmed_at=now_ts,
    )

    if payload.delivery_constraints is not None:
        dc_fact = confirmed_caps.get("delivery_constraints")
        if dc_fact and not dc_fact.get("validation_result", {}).get("valid", True):
            reason = dc_fact.get("validation_result", {}).get("reason", "invalid_delivery_constraints")
            raise HTTPException(status_code=422, detail=f"Invalid delivery_constraints: {reason}")

    # R4: Preserve historical audit trail; omit/corrected fields receive invalidation rather than deletion
    existing_caps = trainer.get("capabilities") or {}
    for cat, old_fact in existing_caps.items():
        if cat not in confirmed_caps and isinstance(old_fact, dict):
            old_fact["permitted_in_projection"] = False
            old_fact["invalidated_at"] = now_ts
            old_fact["invalidation_reason"] = "trainer_corrected"
            confirmed_caps[cat] = old_fact

    update_data: Dict[str, Any] = {
        "capabilities": confirmed_caps,
        "capabilities_confirmed_at": now_ts,
        "updated_at": now_ts,
    }
    if payload.specialties is not None:
        update_data["specialties"] = payload.specialties
    if payload.service_formats is not None:
        update_data["service_formats"] = payload.service_formats
    if payload.life_stages is not None:
        update_data["life_stages"] = payload.life_stages
    if payload.training_philosophy is not None:
        update_data["training_philosophy"] = payload.training_philosophy
    if payload.serviced_suburbs is not None:
        update_data["serviced_suburbs"] = payload.serviced_suburbs
    if payload.catchment_type is not None:
        update_data["catchment_type"] = payload.catchment_type
    if payload.delivery_constraints is not None:
        update_data["delivery_constraints"] = (
            (confirmed_caps.get("delivery_constraints") or {}).get("canonical_value")
            or payload.delivery_constraints
        )

    await db.trainers.update_one({"id": trainer_id}, {"$set": update_data})
    await _audit(
        "trainer_capabilities_confirmed",
        trainer_id,
        after={"categories": list(confirmed_caps.keys()), "confirmed_at": now_ts, "ref": claim_ref},
        actor="trainer" if claim_session else "ops",
    )

    updated_trainer = {**trainer, **update_data}
    projection = trainer_quality.build_match_ready_projection(updated_trainer)

    return _scrub({
        "ok": True,
        "trainer_id": trainer_id,
        "capabilities": confirmed_caps,
        "match_ready": projection["match_eligible"],
        "projection": projection,
    })


@api.post("/owner-waitlist")
async def join_owner_waitlist(payload: OwnerWaitlistJoinIn) -> Dict[str, Any]:
    email_norm = _normalize_email_key(str(payload.email))
    suburb_raw = (payload.suburb or "").strip()
    suburb_norm = _normalize_suburb_key(suburb_raw)
    campaign = (payload.campaign or "").strip()
    source = (payload.source or "").strip()
    utm_medium = (payload.utm_medium or "").strip()
    utm_campaign = (payload.utm_campaign or "").strip()

    await _record_owner_waitlist_event(
        "owner_waitlist_started",
        email_norm=email_norm,
        suburb_norm=suburb_norm,
        status="started",
        campaign=campaign,
        source=source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )

    reason_codes: List[str] = []
    if not suburb_raw:
        reason_codes.append("suburb_required")
    if not payload.consent_owner_waitlist:
        reason_codes.append("consent_required")

    if reason_codes:
        await _record_owner_waitlist_event(
            "owner_waitlist_rejected",
            email_norm=email_norm,
            suburb_norm=suburb_norm,
            status="rejected",
            reason_codes=reason_codes,
            campaign=campaign,
            source=source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
        )
        raise HTTPException(status_code=400, detail={"code": "waitlist_rejected", "reason_codes": reason_codes})

    existing = await db.owner_waitlist.find_one(
        {"email_norm": email_norm, "suburb_norm": suburb_norm, "status": "active"},
        {"_id": 0},
    )
    if existing:
        await _record_owner_waitlist_event(
            "owner_waitlist_duplicate",
            email_norm=email_norm,
            suburb_norm=suburb_norm,
            status="duplicate",
            reason_codes=["duplicate_active_waitlist_record"],
            waitlist_id=existing.get("id"),
            campaign=campaign,
            source=source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
        )
        return {"accepted": True, "duplicate": True, "status": "duplicate", "id": existing.get("id")}

    doc = {
        "id": new_id(),
        "email": str(payload.email).strip(),
        "email_norm": email_norm,
        "suburb": suburb_raw,
        "suburb_norm": suburb_norm,
        "consent_owner_waitlist": True,
        "status": "active",
        "campaign": campaign,
        "source": source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    try:
        await db.owner_waitlist.insert_one(doc.copy())
    except Exception:  # noqa: BLE001
        existing = await db.owner_waitlist.find_one(
            {"email_norm": email_norm, "suburb_norm": suburb_norm, "status": "active"},
            {"_id": 0},
        )
        if existing:
            await _record_owner_waitlist_event(
                "owner_waitlist_duplicate",
                email_norm=email_norm,
                suburb_norm=suburb_norm,
                status="duplicate",
                reason_codes=["duplicate_active_waitlist_record"],
                waitlist_id=existing.get("id"),
                campaign=campaign,
                source=source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
            )
            return {"accepted": True, "duplicate": True, "status": "duplicate", "id": existing.get("id")}
        raise

    await _record_owner_waitlist_event(
        "owner_waitlist_submitted",
        email_norm=email_norm,
        suburb_norm=suburb_norm,
        status="submitted",
        waitlist_id=doc["id"],
        campaign=campaign,
        source=source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )
    await db.growth_attribution.update_one(
        {"campaign": campaign or "unknown", "source": source or "unknown"},
        {
            "$setOnInsert": {
                "campaign": campaign or "unknown",
                "source": source or "unknown",
                "matched": 0,
                "connected": 0,
                "converted": 0,
                "remarketing_candidates": 0,
                "conversion_gap_candidates": 0,
                "entry_events_30d": 0,
            },
            "$inc": {"waitlist_joins_30d": 1},
            "$set": {"updated_at": now_iso()},
        },
        upsert=True,
    )
    return {"accepted": True, "duplicate": False, "status": "accepted", "id": doc["id"]}


@api.post("/attribution/entry")
async def record_attribution_entry(payload: AttributionEntryIn) -> Dict[str, Any]:
    campaign = (payload.campaign or "").strip().lower() or "unknown"
    source = (payload.source or "").strip().lower() or "unknown"
    kind = (payload.kind or "").strip().lower() or "generic_entry"
    path = (payload.path or "").strip()
    suburb = (payload.suburb or "").strip()
    session_id = (payload.session_id or "").strip()
    now_ts = now_iso()

    entry = {
        "id": new_id(),
        "kind": kind,
        "campaign": campaign,
        "source": source,
        "suburb": suburb,
        "path": path,
        "session_id": session_id,
        "created_at": now_ts,
    }
    await db.attribution_entries.insert_one(entry.copy())

    await db.growth_attribution.update_one(
        {"campaign": campaign, "source": source},
        {
            "$setOnInsert": {
                "campaign": campaign,
                "source": source,
                "matched": 0,
                "connected": 0,
                "converted": 0,
                "remarketing_candidates": 0,
                "conversion_gap_candidates": 0,
                "waitlist_joins_30d": 0,
            },
            "$inc": {"entry_events_30d": 1},
            "$set": {"last_entry_at": now_ts, "updated_at": now_ts},
        },
        upsert=True,
    )
    return {"ok": True, "id": entry["id"]}


@api.get("/submissions/{submission_id}/status")
async def get_submission_status(submission_id: str) -> Dict[str, Any]:
    sub = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")

    trainer = await _resolve_trainer(trainer_id=sub.get("trainer_id"), submission_id=submission_id)
    # Prefer live trainer state so remediation/reconnect actions are reflected
    # immediately in the submission status surface.
    billing_profile_status = (
        (trainer or {}).get("billing_profile_status")
        or sub.get("billing_profile_status")
        or "unknown"
    )
    blockers: List[Dict[str, str]] = []
    if sub.get("status") == "held":
        blockers.append({"code": "held", "message": "Submission is held. Add stronger evidence and contact details."})
    if sub.get("status") != "published":
        if billing_profile_status in {"missing_email", "profile_incomplete"}:
            blockers.append({"code": "billing_profile", "message": "Billing profile is incomplete. Add billing email and trainer details."})
        if billing_profile_status == "consent_required":
            blockers.append({"code": "billing_consent", "message": "Billing consent is required to activate collection."})
        if billing_profile_status in {"stripe_unconfigured", "stripe_error"}:
            blockers.append({"code": "billing_integration", "message": "Billing integration needs remediation before collection."})
    activation_state = _activation_state_for_submission(
        submission_status=str(sub.get("status") or ""),
        billing_profile_status=str(billing_profile_status or ""),
    )

    return {
        "id": sub["id"],
        "submitted_at": sub.get("created_at"),
        "status": sub.get("status"),
        "verification_status": sub.get("verification_status"),
        "confidence_score": sub.get("confidence_score"),
        "billing_profile_status": billing_profile_status,
        "activation_state": activation_state,
        "submitter_notification_status": sub.get("submitter_notification_status"),
        "trainer": {
            "id": (trainer or {}).get("id"),
            "name": (trainer or {}).get("name") or sub.get("name"),
            "published": bool((trainer or {}).get("published")) if trainer else sub.get("status") == "published",
            "verification_status": (trainer or {}).get("verification_status") or sub.get("verification_status"),
        },
        "trainer_action_token": (
            _issue_trainer_action_token(
                trainer_id=(trainer or {}).get("id"),
                submission_id=submission_id,
            )
            if trainer and (trainer or {}).get("id")
            else None
        ),
        "blockers": blockers,
    }


@api.get("/trainer/billing")
async def get_trainer_billing_health(
    trainer_id: Optional[str] = Query(default=None),
    submission_id: Optional[str] = Query(default=None),
    trainer_action_token: Optional[str] = None,
    trainer_claim_session: Optional[str] = None,
) -> Dict[str, Any]:
    trainer = await _resolve_trainer(trainer_id=trainer_id, submission_id=submission_id)
    sub = await _resolve_submission(submission_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer context not found.")
    if str(trainer_claim_session or "").strip():
        _verify_trainer_claim_session(str(trainer_claim_session), trainer_id=str(trainer.get("id") or ""))
    else:
        _require_trainer_action_token(
            token=trainer_action_token,
            trainer_id=str(trainer.get("id") or ""),
            submission_id=submission_id,
        )

    intros = await db.intros.find(
        {"trainer_id": trainer.get("id")},
        {"_id": 0, "intro_fee_cents": 1, "billing_collection_status": 1},
    ).to_list(1000)
    statuses: Dict[str, int] = {}
    billed_total_cents = 0
    for intro in intros:
        status = str(intro.get("billing_collection_status") or "not_billable")
        statuses[status] = statuses.get(status, 0) + 1
        billed_total_cents += int(intro.get("intro_fee_cents") or 0)

    sub_tier = str(trainer.get("subscription_tier") or trainer.get("tier") or "claimed")
    sub_status = str(trainer.get("subscription_status") or ("active" if sub_tier in stripe_billing.SUBSCRIPTION_PLANS else "free"))
    sub_billing_status = str(trainer.get("subscription_billing_status") or "normal")
    sub_suburb = trainer.get("subscription_suburb") or trainer.get("suburb")
    trial = stripe_billing.trial_status(trainer)
    eligible_suburbs = list(
        dict.fromkeys(
            str(value).strip()
            for value in ([trainer.get("suburb")] + list(trainer.get("serviced_suburbs") or []))
            if str(value or "").strip()
        )
    )
    sponsor_inventory = await suburb_inventory.availability(db, eligible_suburbs)

    issues = {
        "profile_incomplete": str(trainer.get("billing_profile_status") or "") in {"missing_email", "profile_incomplete"},
        "consent_required": str(trainer.get("billing_profile_status") or "") == "consent_required",
        "stripe_unconfigured": str(trainer.get("billing_profile_status") or "") in {"stripe_unconfigured", "stripe_error"},
        "payment_failed_or_disputed": (
            sub_status in {"past_due", "unpaid"}
            or sub_billing_status == "payment_failed"
        ),
    }
    return {
        "trainer": {
            "id": trainer.get("id"),
            "name": trainer.get("name"),
            "billing_email": trainer.get("billing_email") or trainer.get("email"),
            "billing_profile_status": trainer.get("billing_profile_status") or (sub or {}).get("billing_profile_status") or "unknown",
            "billing_terms_version": trainer.get("billing_terms_version") or "",
            "stripe_customer_id": trainer.get("stripe_customer_id"),
            "tier": sub_tier,
            "subscription_tier": sub_tier,
            "subscription_status": sub_status,
            "subscription_billing_status": sub_billing_status,
            "subscription_suburb": sub_suburb,
        },
        "subscription": {
            "tier": sub_tier,
            "status": sub_status,
            "billing_status": sub_billing_status,
            "suburb": sub_suburb,
            "stripe_subscription_id": trainer.get("stripe_subscription_id"),
            "stripe_customer_id": trainer.get("stripe_customer_id"),
            "trial": trial,
        },
        "billing": {
            "checkout_available": stripe_billing.checkout_enabled(),
            "terms_version": stripe_billing.billing_terms_version(),
        },
        "submission_id": (sub or {}).get("id"),
        "status_counts": statuses,
        "retry_state_counts": {},
        "retry_policy": {},
        "billed_total_cents": billed_total_cents,
        "historical_billed_total_cents": billed_total_cents,
        "historical_intro_count": len(intros),
        "issues": issues,
        "eligible_suburbs": eligible_suburbs,
        "sponsor_inventory": sponsor_inventory,
    }


@api.post("/trainer/billing/reconnect")
async def reconnect_trainer_billing(payload: TrainerBillingActionIn) -> Dict[str, Any]:
    trainer = await _resolve_trainer(trainer_id=payload.trainer_id, submission_id=payload.submission_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer context not found.")
    _require_trainer_action_token(
        token=payload.trainer_action_token,
        trainer_id=str(trainer.get("id") or ""),
        submission_id=payload.submission_id,
    )

    update_fields: Dict[str, Any] = {}
    if payload.billing_email:
        update_fields["billing_email"] = payload.billing_email.strip()
    if update_fields:
        await db.trainers.update_one({"id": trainer["id"]}, {"$set": update_fields})
        trainer.update(update_fields)

    profile = await stripe_billing.provision_trainer_billing_profile(db, trainer, consent_granted=False)
    await _audit("trainer_billing_reconnect", trainer["id"], after={"billing_profile_status": profile.get("billing_profile_status")}, actor="user")
    return {"ok": True, "trainer_id": trainer["id"], "billing_profile_status": profile.get("billing_profile_status")}


@api.post("/trainer/billing/checkout")
async def create_trainer_billing_checkout(payload: TrainerCheckoutIn) -> Dict[str, Any]:
    """Start a hosted subscription checkout for the verified profile owner."""
    trainer_id = payload.trainer_id.strip()
    auth_reference = ""
    if str(payload.trainer_claim_session or "").strip():
        claim_session = _verify_trainer_claim_session(str(payload.trainer_claim_session), trainer_id=trainer_id)
        auth_reference = str(claim_session.get("claim_event_id") or "")
    elif str(payload.trainer_action_token or "").strip():
        action_payload = _verify_trainer_action_token(str(payload.trainer_action_token), trainer_id=trainer_id)
        auth_reference = str(action_payload.get("submission_id") or action_payload.get("trainer_id") or "")
    else:
        raise HTTPException(status_code=401, detail="A current trainer session or action link is required.")
    trainer = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found.")
    if str(trainer.get("claim_status") or "").lower() != "claimed":
        raise HTTPException(status_code=403, detail="Only a claimed trainer profile can start subscription checkout.")
    if not payload.consent_subscription_billing_terms or payload.billing_terms_version != stripe_billing.billing_terms_version():
        raise HTTPException(status_code=400, detail="Accept the current subscription billing terms before checkout.")

    try:
        plan = stripe_billing.subscription_plan(tier=payload.tier, suburb=payload.suburb, interval=payload.interval)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if plan["tier"] == "suburb_sponsor" and not _trainer_serves_suburb(trainer, plan["suburb"]):
        raise HTTPException(status_code=403, detail="Suburb sponsorship must match a suburb served by this profile.")
    if not stripe_billing.checkout_enabled():
        raise HTTPException(status_code=503, detail="Trainer billing is not accepting purchases yet.")

    reservation: Dict[str, Any] = {}
    if plan["tier"] in {"suburb_sponsor", "citywide"}:
        reservation_result = await suburb_inventory.reserve(
            db,
            trainer_id=trainer_id,
            tier=plan["tier"],
            suburb=plan["suburb"],
            idempotency_key=f"{auth_reference}:{plan['tier']}:{plan['interval']}:{_normalize_suburb_key(plan['suburb']) or 'all'}",
        )
        if not reservation_result.get("ok"):
            code = str(reservation_result.get("code") or "inventory_unavailable")
            status_code = 409 if code in {"inventory_sold_out", "duplicate_sponsor_for_suburb", "trainer_suburb_cap_reached"} else 503
            raise HTTPException(status_code=status_code, detail=code)
        reservation = dict(reservation_result.get("reservation") or {})

    checkout = await stripe_billing.create_checkout_session(
        db,
        trainer,
        tier=plan["tier"],
        suburb=plan["suburb"],
        interval=plan["interval"],
        consent_granted=payload.consent_subscription_billing_terms,
        consent_version=payload.billing_terms_version,
        idempotency_key=f"dtd-checkout:{auth_reference}:{plan['tier']}:{plan['interval']}:{_normalize_suburb_key(plan['suburb']) or 'all'}",
        reservation_id=str(reservation.get("reservation_id") or ""),
        billing_return_url=(
            f"{(os.environ.get('FRONTEND_BASE_URL') or 'http://127.0.0.1:3001').strip().rstrip('/')}/trainer/billing?"
            f"{urlencode({'trainerId': trainer_id})}"
        ),
    )
    if not checkout.get("ok"):
        code = str(checkout.get("code") or "stripe_checkout_failed")
        status = "provider_unavailable" if code == "stripe_unconfigured" else "needs_review"
        event_id = f"checkout:{new_id()}"
        await db.stripe_events.insert_one(
            {
                "id": event_id,
                "type": "checkout.session.create",
                "status": status,
                "trainer_id": trainer_id,
                "subscription_tier": plan["tier"],
                "suburb": plan["suburb"],
                "reason": code,
                "created_at": now_iso(),
            }
        )
        await _audit("trainer_subscription_checkout_failed", trainer_id, after={"reason": code, "stripe_event_id": event_id}, actor="user")
        if reservation.get("reservation_id"):
            await suburb_inventory.release_reservation(
                db,
                reservation_id=str(reservation["reservation_id"]),
                reason="checkout_failed",
            )
        http_status = 503 if code in {"stripe_unconfigured", "stripe_error"} else 409
        raise HTTPException(status_code=http_status, detail="Subscription checkout is unavailable. The issue has been recorded for review.")

    try:
        await db.stripe_events.insert_one(
            {
                "id": f"checkout:{checkout['session_id']}",
                "type": "checkout.session.created",
                "status": "created",
                "trainer_id": trainer_id,
                "stripe_checkout_session_id": checkout["session_id"],
                "stripe_customer_id": checkout.get("customer_id"),
                "subscription_tier": plan["tier"],
                "suburb": plan["suburb"],
                "reservation_id": reservation.get("reservation_id"),
                "reservation_expires_at": reservation.get("expires_at"),
                "created_at": now_iso(),
            }
        )
    except DuplicateKeyError:
        pass
    await _audit("trainer_subscription_checkout_started", trainer_id, after={"tier": plan["tier"], "suburb": plan["suburb"], "session_id": checkout["session_id"]}, actor="user")
    return {
        "ok": True,
        "url": checkout["url"],
        "session_id": checkout["session_id"],
        "tier": plan["tier"],
        "suburb": plan["suburb"],
        "reservation_id": reservation.get("reservation_id"),
        "reservation_expires_at": reservation.get("expires_at"),
    }


@api.post("/trainer/billing/portal")
async def create_trainer_billing_portal(payload: TrainerPortalIn) -> Dict[str, Any]:
    trainer_id = payload.trainer_id.strip()
    if str(payload.trainer_claim_session or "").strip():
        _verify_trainer_claim_session(str(payload.trainer_claim_session), trainer_id=trainer_id)
    elif str(payload.trainer_action_token or "").strip():
        _verify_trainer_action_token(str(payload.trainer_action_token), trainer_id=trainer_id)
    else:
        raise HTTPException(status_code=401, detail="A current trainer session or action link is required.")
    trainer = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found.")
    frontend_base = (os.environ.get("FRONTEND_BASE_URL") or "http://127.0.0.1:3001").strip().rstrip("/")
    portal = await stripe_billing.create_customer_portal_session(
        trainer,
        return_url=f"{frontend_base}/trainer/billing?{urlencode({'trainerId': trainer_id})}",
    )
    if not portal.get("ok"):
        await db.stripe_events.insert_one(
            {
                "id": f"portal:{new_id()}",
                "type": "billing_portal.session.create",
                "status": "provider_unavailable" if portal.get("code") == "stripe_unconfigured" else "needs_review",
                "trainer_id": trainer_id,
                "subscription_tier": trainer.get("subscription_tier") or trainer.get("tier"),
                "reason": str(portal.get("code") or "stripe_portal_failed"),
                "created_at": now_iso(),
            }
        )
        raise HTTPException(status_code=503, detail="Subscription management is unavailable. The issue has been recorded for review.")
    await _audit("trainer_subscription_portal_opened", trainer_id, actor="user")
    return {"ok": True, "url": portal["url"]}


@api.get("/sponsor-inventory")
async def get_sponsor_inventory(suburb: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    return await suburb_inventory.availability(db, [suburb] if suburb else [])


@api.post("/oversight/subscriptions/refund")
async def refund_trainer_subscription(
    payload: OpsSubscriptionRefundIn,
    _: None = Depends(require_oversight),
) -> Dict[str, Any]:
    if (os.environ.get("ENABLE_OPS_STRIPE_REFUNDS") or "0").strip().lower() not in TRUTHY_ENV_VALUES:
        raise HTTPException(status_code=503, detail="Stripe refunds are not enabled in this runtime.")
    trainer = await db.trainers.find_one(
        {"id": payload.trainer_id, "stripe_subscription_id": payload.stripe_subscription_id},
        {"_id": 0},
    )
    if not trainer:
        raise HTTPException(status_code=404, detail="Subscription trainer not found.")
    started_at = _parse_iso(trainer.get("subscription_active_at"))
    interval = str(trainer.get("subscription_interval") or "month")
    guarantee_days = 30 if interval == "year" else 14
    if not started_at or datetime.now(timezone.utc) > started_at + timedelta(days=guarantee_days):
        raise HTTPException(status_code=409, detail="This subscription is outside the configured money-back window.")

    event_id = f"refund:{payload.payment_intent_id}"
    try:
        await db.stripe_events.insert_one(
            {
                "id": event_id,
                "type": "subscription.refund.requested",
                "status": "processing",
                "trainer_id": payload.trainer_id,
                "subscription_tier": trainer.get("subscription_tier") or trainer.get("tier"),
                "reason": payload.reason.strip(),
                "created_at": now_iso(),
            }
        )
    except DuplicateKeyError:
        return {"ok": True, "duplicate": True}

    refund = await stripe_billing.refund_subscription_payment(
        payment_intent_id=payload.payment_intent_id,
        idempotency_key=event_id,
    )
    if not refund.get("ok"):
        await db.stripe_events.update_one(
            {"id": event_id},
            {"$set": {"status": "needs_review", "reason": str(refund.get("code") or "stripe_refund_failed"), "processed_at": now_iso()}},
        )
        raise HTTPException(status_code=503, detail="Refund could not be completed. The case remains visible for review.")

    await db.trainers.update_one(
        {"id": payload.trainer_id, "stripe_subscription_id": payload.stripe_subscription_id},
        {
            "$set": {
                "tier": "claimed",
                "subscription_status": "refunded",
                "subscription_billing_status": "refunded",
                "subscription_ended_at": now_iso(),
            }
        },
    )
    await suburb_inventory.release_reservation(
        db,
        reservation_id=str(trainer.get("sponsor_reservation_id") or ""),
        subscription_id="" if trainer.get("sponsor_reservation_id") else payload.stripe_subscription_id,
        reason="refunded",
    )
    await db.stripe_events.update_one(
        {"id": event_id},
        {"$set": {"status": "processed", "stripe_refund_id": refund.get("refund_id"), "processed_at": now_iso()}},
    )
    await _audit(
        "trainer_subscription_refunded",
        payload.trainer_id,
        after={"stripe_subscription_id": payload.stripe_subscription_id, "stripe_refund_id": refund.get("refund_id")},
        actor="operator",
    )
    return {"ok": True, "refund_id": refund.get("refund_id"), "status": refund.get("status")}


@api.get("/trainer/reactivate")
async def get_trainer_reactivation_health(
    trainer_id: Optional[str] = Query(default=None),
    submission_id: Optional[str] = Query(default=None),
    trainer_action_token: Optional[str] = None,
) -> Dict[str, Any]:
    trainer = await _resolve_trainer(trainer_id=trainer_id, submission_id=submission_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer context not found.")
    _require_trainer_action_token(
        token=trainer_action_token,
        trainer_id=str(trainer.get("id") or ""),
        submission_id=submission_id,
    )

    billing_status = str(trainer.get("billing_profile_status") or "")
    reasons: List[Dict[str, str]] = []
    if int(trainer.get("intros_30d") or 0) == 0:
        reasons.append({"code": "low_activity", "message": "No billed intro activity in the recent window."})
    if not bool(trainer.get("published")) or float(trainer.get("confidence_score") or 0) < HOLD_THRESHOLD:
        reasons.append({"code": "verification_drift", "message": "Listing confidence/publication is below active threshold."})
    if billing_status in {"missing_email", "profile_incomplete", "consent_required", "stripe_unconfigured", "stripe_error"}:
        reasons.append({"code": "billing_blocker", "message": "Billing profile has unresolved blockers."})
    if not reasons:
        reasons.append({"code": "healthy", "message": "No hard blockers detected. Refresh profile for better performance."})

    return {
        "trainer": {
            "id": trainer.get("id"),
            "name": trainer.get("name"),
            "published": bool(trainer.get("published")),
            "verification_status": trainer.get("verification_status"),
            "confidence_score": trainer.get("confidence_score"),
            "billing_profile_status": trainer.get("billing_profile_status"),
            "intros_30d": trainer.get("intros_30d", 0),
            "conversions_30d": trainer.get("conversions_30d", 0),
            "outcome_score": trainer.get("outcome_score", 0),
        },
        "reasons": reasons,
    }


@api.post("/trainer/reactivate")
async def reactivate_trainer_listing(payload: TrainerReactivateIn) -> Dict[str, Any]:
    trainer = await _resolve_trainer(trainer_id=payload.trainer_id, submission_id=payload.submission_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer context not found.")
    _require_trainer_action_token(
        token=payload.trainer_action_token,
        trainer_id=str(trainer.get("id") or ""),
        submission_id=payload.submission_id,
    )

    score = await ai_service.score_trainer(_verification_payload(trainer))
    conf = float(score.get("confidence") or 0)
    has_statutory_abn = bool(trainer.get("abn_verified"))
    is_eligible_for_publish = has_statutory_abn and conf >= HOLD_THRESHOLD

    if is_eligible_for_publish:
        published = True
        verification_status = "verified"
        contact_ready = bool(trainer.get("website") or trainer.get("phone") or trainer.get("email"))
        verified_at = trainer.get("verified_at") or now_iso()
    else:
        published = False
        verification_status = "unverified" if conf >= HOLD_THRESHOLD else "hold"
        contact_ready = False
        verified_at = trainer.get("verified_at") if has_statutory_abn else ""

    await db.trainers.update_one(
        {"id": trainer["id"]},
        {"$set": {
            "confidence_score": conf,
            "verification_status": verification_status,
            "verification_reasoning": score.get("reasoning", ""),
            "verification_signals": score.get("signals", []),
            "verification_model": score.get("model", "heuristic"),
            "verified_at": verified_at,
            "published": published,
            "contact_ready": contact_ready,
        }},
    )
    await _audit(
        "trainer_reactivate",
        trainer["id"],
        after={"published": published, "confidence_score": conf, "verification_status": verification_status},
        actor="user",
    )
    return {
        "ok": True,
        "trainer_id": trainer["id"],
        "published": published,
        "confidence_score": conf,
        "verification_status": verification_status,
    }


@api.get("/seo/{slug:path}")
async def get_seo(slug: str) -> Dict[str, Any]:
    canonical_suburb = _canonical_suburb_for_seo_slug(slug)
    if not canonical_suburb:
        # Crucially, unknown paths do not call AI or write seo_pages.
        raise HTTPException(status_code=404, detail="Unknown canonical suburb")

    minimum_trainers = _configured_positive_int("SEO_MIN_PUBLISHED_TRAINERS")
    minimum_words = _configured_positive_int("SEO_MIN_CONTENT_WORDS")
    slug = str(canonical_suburb["slug"])
    suburb = str(canonical_suburb["suburb_name"])
    if minimum_trainers is None or minimum_words is None:
        return _unpublished_seo_response(
            slug=slug,
            suburb=suburb,
            reason="seo_thresholds_not_configured",
        )

    eligible_trainers = await db.trainers.count_documents(_eligible_trainer_query_for_suburb(suburb))
    if eligible_trainers < minimum_trainers:
        return _unpublished_seo_response(
            slug=slug,
            suburb=suburb,
            reason="insufficient_eligible_supply",
        )

    page = await db.seo_pages.find_one({"slug": slug}, {"_id": 0})
    if page:
        if _seo_page_word_count(page) < minimum_words:
            return _unpublished_seo_response(
                slug=slug,
                suburb=suburb,
                reason="insufficient_content_quality",
            )
        if str(page.get("publication_status") or "") != "published" or str(page.get("meta_robots") or "") != "index,follow":
            return _unpublished_seo_response(
                slug=slug,
                suburb=suburb,
                reason="stored_page_not_indexable",
            )
        return _scrub(page)

    copy = await ai_service.generate_seo_copy(suburb, "general")
    word_count = _seo_word_count(copy)
    if word_count < minimum_words:
        return _unpublished_seo_response(
            slug=slug,
            suburb=suburb,
            reason="insufficient_content_quality",
        )
    page = {
        "id": new_id(),
        "slug": slug,
        "suburb": suburb,
        "category": "general",
        "copy": copy,
        "publication_status": "published",
        "meta_robots": "index,follow",
        "eligible_trainer_count": eligible_trainers,
        "content_word_count": word_count,
        "generated_at": now_iso(),
    }
    await db.seo_pages.insert_one(page.copy())
    return _scrub(page)


# ---------------------------------------------------------------------------
# Oversight — visibility-first surface with bounded Layer 1 review-state writes
# only; no policy, provider, runtime, or direct-data mutations.
# ---------------------------------------------------------------------------


async def _current_ops_cases() -> List[Dict[str, Any]]:
    discovery_summary = {
        "pending": await db.discovery_queue.count_documents({"status": "pending"}),
        "promoted": await db.discovery_queue.count_documents({"status": "promoted"}),
        "duplicate": await db.discovery_queue.count_documents({"status": "duplicate"}),
        "discarded": await db.discovery_queue.count_documents({"status": "discarded"}),
        "suppressed": await db.discovery_queue.count_documents({"status": "suppressed"}),
    }
    waitlist_summary = await _owner_waitlist_summary()
    now_dt = datetime.now(timezone.utc)
    health = await db.system_state.find_one({"key": "health"}, {"_id": 0}) or {}
    ranking = await db.system_state.find_one({"key": "ranking"}, {"_id": 0}) or {}
    pricing = await db.system_state.find_one({"key": "pricing"}, {"_id": 0}) or {}
    verification = await db.system_state.find_one({"key": "verification"}, {"_id": 0}) or {}
    discovery = await db.system_state.find_one({"key": "discovery"}, {"_id": 0}) or {}
    inference = await db.system_state.find_one({"key": "inference"}, {"_id": 0}) or {}
    source_ingestion = await db.system_state.find_one({"key": "source_ingestion"}, {"_id": 0}) or {}
    outreach = await db.system_state.find_one({"key": "outreach"}, {"_id": 0}) or {}
    billing_recovery = await db.system_state.find_one({"key": "billing_recovery"}, {"_id": 0}) or {}
    nurture = await db.system_state.find_one({"key": "nurture"}, {"_id": 0}) or {}
    reactivation_route = await db.system_state.find_one({"key": "reactivation_route"}, {"_id": 0}) or {}
    pro_trial_warnings = await db.system_state.find_one({"key": "pro_trial_warnings"}, {"_id": 0}) or {}
    source_ingestion_state_coll = getattr(db, "source_ingestion_state", None)
    source_ingestion_state_rows = await source_ingestion_state_coll.find({}, {"_id": 0}).sort("last_checked_at", -1).limit(100).to_list(100) if source_ingestion_state_coll is not None else []
    source_ingestion_state_rows.sort(
        key=lambda row: (
            int(row.get("consecutive_failures") or 0),
            str(row.get("suppressed_until") or ""),
            str(row.get("source_url") or ""),
        ),
        reverse=True,
    )
    trainers_coll = getattr(db, "trainers", None)
    subscription_exception_trainers = await trainers_coll.find(
        {
            "$or": [
                {"subscription_status": {"$in": ["past_due", "unpaid", "incomplete_expired"]}},
                {"subscription_billing_status": "payment_failed"},
                {
                    "tier": {"$in": ["pro", "suburb_sponsor", "citywide"]},
                    "billing_profile_status": {"$in": ["stripe_error", "stripe_unconfigured"]},
                },
            ]
        },
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "tier": 1,
            "subscription_tier": 1,
            "subscription_status": 1,
            "subscription_billing_status": 1,
            "subscription_suburb": 1,
            "billing_profile_status": 1,
            "billing_email": 1,
            "email": 1,
            "updated_at": 1,
            "created_at": 1,
        },
    ).to_list(20) if trainers_coll is not None else []
    billing_recovery_case_rows: List[Dict[str, Any]] = []
    for t in subscription_exception_trainers:
        t_id = str(t.get("id") or "")
        sub_status = str(t.get("subscription_status") or "none")
        billing_status = str(t.get("subscription_billing_status") or t.get("billing_profile_status") or "normal")
        billing_recovery_case_rows.append(
            {
                "trainer_id": t_id,
                "trainer_name": t.get("name") or t_id or "unknown",
                "tier": t.get("subscription_tier") or t.get("tier") or "core",
                "subscription_tier": t.get("subscription_tier") or t.get("tier") or "core",
                "subscription_status": sub_status,
                "subscription_billing_status": billing_status,
                "billing_collection_status": billing_status,
                "billing_profile_status": t.get("billing_profile_status") or "unknown",
                "billing_retry_state": sub_status if sub_status in {"past_due", "unpaid"} else billing_status,
                "suburb": t.get("subscription_suburb") or "",
                "created_at": t.get("updated_at") or t.get("created_at"),
                "trainer_action_token": _issue_trainer_action_token(trainer_id=t_id) if t_id else None,
            }
        )
    stripe_events_coll = getattr(db, "stripe_events", None)
    subscription_billing_case_rows = await stripe_events_coll.find(
        {"status": {"$in": ["provider_unavailable", "needs_review", "failed"]}},
        {"_id": 0, "id": 1, "type": 1, "status": 1, "trainer_id": 1, "subscription_tier": 1, "reason": 1, "created_at": 1, "processed_at": 1},
    ).sort("created_at", -1).limit(50).to_list(50) if stripe_events_coll is not None and hasattr(stripe_events_coll, "find") else []
    reactivation_candidates_coll = getattr(db, "reactivation_candidates", None)
    reactivation_case_rows_raw = await reactivation_candidates_coll.find(
        {"status": "open"},
        {"_id": 0, "trainer_id": 1, "trainer_name": 1, "email": 1, "reasons": 1, "last_notified_at": 1, "last_notification_status": 1, "updated_at": 1},
    ).to_list(20) if reactivation_candidates_coll is not None else []
    reactivation_case_rows: List[Dict[str, Any]] = []
    for row in reactivation_case_rows_raw:
        trainer_id = str(row.get("trainer_id") or "")
        reactivation_case_rows.append(
            {
                **row,
                "trainer_action_token": _issue_trainer_action_token(trainer_id=trainer_id) if trainer_id else None,
            }
        )
    loop_statuses = {
        key: _loop_status(key, loop, now_dt=now_dt)
        for key, loop in {
            "ranking": ranking,
            "pricing": pricing,
            "verification": verification,
            "discovery": discovery,
            "inference": inference,
            "source_ingestion": source_ingestion,
            "outreach": outreach,
            "health": health,
            "billing_recovery": billing_recovery,
            "nurture": nurture,
            "reactivation_route": reactivation_route,
            "pro_trial_warnings": pro_trial_warnings,
        }.items()
    }
    message_log = await _message_log_rows()
    ai_degradation_cases = await ai_service.get_ops_degradation_cases(db=db)
    sponsor_inventory_snapshot = await suburb_inventory.ops_snapshot(db)
    provider_snapshot = provider_health.snapshot()
    return await _ops_case_rows(
        discovery_summary=discovery_summary,
        waitlist_summary=waitlist_summary,
        loop_statuses=loop_statuses,
        billing_recovery_case_rows=billing_recovery_case_rows,
        subscription_billing_case_rows=subscription_billing_case_rows,
        reactivation_case_rows=reactivation_case_rows,
        source_ingestion_state_rows=source_ingestion_state_rows,
        message_log=message_log,
        ai_degradation_cases=ai_degradation_cases,
        sponsor_inventory_cases=sponsor_inventory_snapshot.get("exceptions", []),
        provider_cases=provider_health.cases(provider_snapshot),
    )


@api.post("/oversight/login")
async def oversight_login(payload: OversightLogin, request: Request) -> Dict[str, Any]:
    ip = _client_ip(request)
    if await _oversight_auth_blocked(ip):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
    expected = os.environ.get("ADMIN_PASS")
    if not expected or payload.passcode != expected:
        await _record_oversight_auth_attempt(ip, success=False)
        raise HTTPException(status_code=401, detail="Invalid passcode")
    await _record_oversight_auth_attempt(ip, success=True)
    return {"ok": True}


@api.post("/oversight/cases/{case_id}")
async def update_oversight_case_review(
    case_id: str,
    payload: OpsCaseReviewIn,
    _: None = Depends(require_oversight),
) -> Dict[str, Any]:
    normalized_state = _normalize_ops_case_state(payload.state)
    if not normalized_state:
        raise HTTPException(status_code=400, detail="Invalid case state.")
    owner = _normalize_ops_case_owner(payload.owner)
    note = _normalize_ops_case_note(payload.note)
    current_cases = await _current_ops_cases()
    current_case = next((row for row in current_cases if str(row.get("case_id") or "") == case_id), None)
    if not current_case:
        raise HTTPException(status_code=404, detail="Ops case not found.")

    states_coll = getattr(db, "ops_case_states", None)
    if states_coll is None:
        raise HTTPException(status_code=503, detail="Ops case state store unavailable.")

    before = await states_coll.find_one({"case_id": case_id}, {"_id": 0}) or {}
    updated_at = now_iso()
    history = list(before.get("history") or [])
    history.append(
        {
            "state": normalized_state,
            "owner": owner,
            "note": note,
            "updated_at": updated_at,
            "actor": f"ops:{owner}" if owner else "ops",
        }
    )
    history = history[-OPS_CASE_HISTORY_LIMIT:]
    after = {
        "case_id": case_id,
        "case_type": current_case.get("case_type"),
        "workflow": current_case.get("workflow"),
        "entity_type": current_case.get("entity_type"),
        "entity_id": current_case.get("entity_id"),
        "state": normalized_state,
        "owner": owner,
        "note": note,
        "updated_at": updated_at,
        "history": history,
    }
    await states_coll.update_one({"case_id": case_id}, {"$set": after}, upsert=True)
    await _audit("ops_case_review_updated", case_id, before=before or None, after=after, actor=f"ops:{owner}" if owner else "ops")
    merged_case = _merge_ops_case_state(current_case, after)
    return _scrub({"ok": True, "case": merged_case})


@api.get("/oversight")
async def oversight(_: None = Depends(require_oversight)) -> Dict[str, Any]:
    """Primary oversight snapshot for the Operations Console.

    This route is read-only. The wider Ops surface may still persist bounded
    Layer 1 review-state history through dedicated review endpoints.
    """
    phase_runtime = await _refresh_phase_runtime_records()
    phase_state = phase_runtime["phase_state"]
    readiness_snapshot = phase_runtime["readiness_snapshot"]
    phase_decisions = phase_runtime["phase_decisions"]
    conversion_statuses = autonomy.confirmed_conversion_statuses()
    delivered_intro_filter = {
        "$or": [
            {"delivery_status": "delivered"},
            {"status": "delivered"},
            {"billing_status": "billed"},
        ],
        "billing_status": {"$ne": "suppressed"},
        "delivery_status": {"$ne": "suppressed"},
    }
    conversion_statuses = autonomy.confirmed_conversion_statuses()
    intros_24 = await db.intros.count_documents({
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()},
        **delivered_intro_filter,
    })
    intros_7d = await db.intros.count_documents({
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()},
        **delivered_intro_filter,
    })
    conv_24 = await db.conversions.count_documents({
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()},
        "billing_status": {"$in": conversion_statuses},
    })
    conv_7d = await db.conversions.count_documents({
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()},
        "billing_status": {"$in": conversion_statuses},
    })

    intros = await db.intros.find(delivered_intro_filter, {"_id": 0}).to_list(2000)
    conversions = await db.conversions.find({"billing_status": {"$in": conversion_statuses}}, {"_id": 0}).to_list(2000)
    suppressed = await db.intros.count_documents({
        "$or": [{"delivery_status": "suppressed"}, {"billing_status": "suppressed"}]
    })
    suspicious_conv = await db.conversions.count_documents({
        "$or": [{"status": "suspicious"}, {"billing_status": "suspicious"}]
    })
    inferred_pending = await db.conversions.count_documents({
        "inferred": True,
        "$or": [{"status": "pending"}, {"billing_status": "pending"}],
    })
    engagements_total = await db.engagements.count_documents({})

    converted_intro_ids = await db.conversions.distinct("intro_id")
    stalled_intros = await db.intros.count_documents({
        "id": {"$nin": converted_intro_ids},
        "created_at": {"$lt": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()},
        **delivered_intro_filter,
    })

    notification_summary = {
        "trainer_intro_sent": await db.intros.count_documents({"trainer_notification_status": "sent"}),
        "trainer_intro_failed": await db.intros.count_documents({"trainer_notification_status": "failed"}),
        "trainer_intro_skipped": await db.intros.count_documents({"trainer_notification_status": "skipped"}),
        "trainer_intro_suppressed": await db.intros.count_documents({"trainer_notification_status": "suppressed"}),
        "submission_sent": await db.submissions.count_documents({"submitter_notification_status": "sent"}),
        "submission_failed": await db.submissions.count_documents({"submitter_notification_status": "failed"}),
        "submission_skipped": await db.submissions.count_documents({"submitter_notification_status": "skipped"}),
    }

    intros_total = max(1, len(intros))
    intro_to_conv = round(len(conversions) / intros_total, 3)

    health = await db.system_state.find_one({"key": "health"}, {"_id": 0}) or {}
    ranking = await db.system_state.find_one({"key": "ranking"}, {"_id": 0}) or {}
    verification = await db.system_state.find_one({"key": "verification"}, {"_id": 0}) or {}
    discovery = await db.system_state.find_one({"key": "discovery"}, {"_id": 0}) or {}
    inference = await db.system_state.find_one({"key": "inference"}, {"_id": 0}) or {}
    source_ingestion = await db.system_state.find_one({"key": "source_ingestion"}, {"_id": 0}) or {}
    outreach = await db.system_state.find_one({"key": "outreach"}, {"_id": 0}) or {}
    nurture = await db.system_state.find_one({"key": "nurture"}, {"_id": 0}) or {}
    reactivation_route = await db.system_state.find_one({"key": "reactivation_route"}, {"_id": 0}) or {}
    pro_trial_warnings = await db.system_state.find_one({"key": "pro_trial_warnings"}, {"_id": 0}) or {}

    top_trainers = await db.trainers.find(
        {"published": True},
        {"_id": 0, "id": 1, "name": 1, "suburb": 1, "outcome_score": 1, "outcome_breakdown": 1,
         "intros_30d": 1, "conversions_30d": 1, "engagements_30d": 1, "confidence_score": 1,
         "verification_status": 1},
    ).sort("outcome_score", -1).limit(10).to_list(10)

    audit_recent = await db.audit_log.find({}, {"_id": 0}).sort("ts", -1).to_list(20)

    submissions_summary = {
        "auto_published": await db.submissions.count_documents({"status": "published"}),
        "auto_held": await db.submissions.count_documents({"status": "held"}),
        "pending": await db.submissions.count_documents({"status": "pending"}),
    }

    discovery_summary = {
        "pending": await db.discovery_queue.count_documents({"status": "pending"}),
        "promoted": await db.discovery_queue.count_documents({"status": "promoted"}),
        "duplicate": await db.discovery_queue.count_documents({"status": "duplicate"}),
        "discarded": await db.discovery_queue.count_documents({"status": "discarded"}),
        "suppressed": await db.discovery_queue.count_documents({"status": "suppressed"}),
    }

    integrity = {
        "verified": await db.trainers.count_documents({"published": True, "verification_status": "verified"}),
        "unverified": await db.trainers.count_documents({"published": True, "verification_status": "unverified"}),
        "hidden": await db.trainers.count_documents({"published": False}),
        "live_total": await db.trainers.count_documents({"published": True}),
    }

    capability_health_summary = await trainer_quality.compute_capability_health_summary(db.trainers)

    rollback_recent = await db.config_snapshots.find(
        {"rolled_back": True}, {"_id": 0}
    ).sort("rolled_back_at", -1).to_list(5)
    suburb_dataset = _suburb_meta_identity_snapshot()
    claim_policy = _claim_policy_snapshot()
    suburb_identity = suburb_dataset.get("identity", {})
    suburb_status = suburb_dataset.get("status", {})
    waitlist_summary = await _owner_waitlist_summary()
    kpi_prelaunch = await _kpi_prelaunch_summary()
    growth_attribution_summary = await _growth_attribution_summary()
    reactivation_summary = await _reactivation_summary()
    now_dt = datetime.now(timezone.utc)
    ingestion_runs_coll = getattr(db, "ingestion_runs", None)
    recent_ingestion_runs = (
        await ingestion_runs_coll.find({}, {"_id": 0}).sort("executed_at", -1).limit(10).to_list(10)
        if ingestion_runs_coll is not None
        else []
    )
    last_ingestion_run = recent_ingestion_runs[0] if recent_ingestion_runs else None
    pipeline_guardian_state = await db.system_state.find_one({"key": "pipeline_guardian"}, {"_id": 0}) or {}

    source_ingestion_state_coll = getattr(db, "source_ingestion_state", None)
    source_ingestion_state_rows = await source_ingestion_state_coll.find({}, {"_id": 0}).sort("last_checked_at", -1).limit(100).to_list(100) if source_ingestion_state_coll is not None else []
    source_ingestion_state_rows.sort(
        key=lambda row: (
            int(row.get("consecutive_failures") or 0),
            str(row.get("suppressed_until") or ""),
            str(row.get("source_url") or ""),
        ),
        reverse=True,
    )
    delivered_cases_raw = await db.intros.find(
        delivered_intro_filter,
        {"_id": 0, "id": 1, "trainer_id": 1, "delivery_status": 1, "created_at": 1, "region": 1, "suburb": 1},
    ).sort("created_at", -1).limit(20).to_list(20)
    intro_delivery_cases = [
        {
            "intro_id": row.get("id"),
            "trainer_id": row.get("trainer_id"),
            "delivery_status": row.get("delivery_status") or "delivered",
            "created_at": row.get("created_at"),
            "region": row.get("region") or "",
            "suburb": row.get("suburb") or "",
        }
        for row in delivered_cases_raw
    ]
    fraud_cases_raw = await db.intros.find(
        {"$or": [{"delivery_status": "suppressed"}, {"billing_status": "suppressed"}]},
        {"_id": 0, "id": 1, "trainer_id": 1, "delivery_status": 1, "fraud_status": 1, "fraud_reasons": 1, "created_at": 1},
    ).sort("created_at", -1).limit(20).to_list(20)
    fraud_suppression_cases = [
        {
            "intro_id": row.get("id"),
            "trainer_id": row.get("trainer_id"),
            "delivery_status": row.get("delivery_status") or "suppressed",
            "fraud_status": row.get("fraud_status") or "suppressed",
            "fraud_reasons": row.get("fraud_reasons") or [],
            "created_at": row.get("created_at"),
        }
        for row in fraud_cases_raw
    ]
    conversion_cases_raw = await db.conversions.find(
        {},
        {"_id": 0, "id": 1, "intro_id": 1, "trainer_id": 1, "status": 1, "billing_status": 1, "inferred": 1, "created_at": 1},
    ).sort("created_at", -1).limit(20).to_list(20)
    conversion_quality_cases = [
        {
            "conversion_id": row.get("id"),
            "intro_id": row.get("intro_id"),
            "trainer_id": row.get("trainer_id"),
            "status": row.get("status") or row.get("billing_status") or "tracked",
            "inferred": bool(row.get("inferred")),
            "created_at": row.get("created_at"),
        }
        for row in conversion_cases_raw
    ]
    claim_events_coll = getattr(db, "claim_events", None)
    claim_cases = await claim_events_coll.find(
        {"status": {"$nin": ["verified", "superseded"]}},
        {"_id": 0, "id": 1, "trainer_id": 1, "status": 1, "reason": 1, "delivery_status": 1, "delivery_error": 1, "method": 1, "masked_destination": 1, "attempts": 1, "profile_claim_status": 1, "created_at": 1, "updated_at": 1},
    ).sort("updated_at", -1).limit(50).to_list(50) if claim_events_coll is not None else []
    abn_degradation_cases = []
    if not (os.environ.get("ABR_GUID") or "").strip():
        abn_degradation_cases.append(
            {
                "id": "system_abr_guid_missing",
                "name": "ABR Web Services",
                "abn": "",
                "abn_status": "abr_guid_missing",
                "abn_verification_reason": "ABR_GUID is not configured in the environment.",
                "abn_checked_at": now_iso(),
                "created_at": now_iso(),
            }
        )
    trainers_coll = getattr(db, "trainers", None)
    if trainers_coll is not None:
        trainer_degraded = await trainers_coll.find(
            {
                "$or": [
                    {
                        "abn_status": {
                            "$in": [
                                "abr_unavailable",
                                "degraded",
                                "abr_guid_missing",
                                "abr_maintenance",
                                "abr_network_error",
                                "pending_verification",
                                "invalid_checksum",
                                "checksum_failed",
                                "invalid_length",
                                "unverified",
                            ]
                        }
                    },
                    {"abn": {"$ne": "", "$exists": True}, "abn_verified": False},
                ]
            },
            {"_id": 0, "id": 1, "name": 1, "abn": 1, "abn_status": 1, "abn_verification_reason": 1, "abn_checked_at": 1, "created_at": 1},
        ).sort("created_at", -1).limit(50).to_list(50)
        abn_degradation_cases.extend(trainer_degraded)
    ai_degradation_cases = await ai_service.get_ops_degradation_cases(db=db)
    stripe_events_coll = getattr(db, "stripe_events", None)
    subscription_billing_case_rows = await stripe_events_coll.find(
        {"status": {"$in": ["provider_unavailable", "needs_review", "failed"]}},
        {"_id": 0, "id": 1, "type": 1, "status": 1, "trainer_id": 1, "subscription_tier": 1, "reason": 1, "created_at": 1, "processed_at": 1},
    ).sort("created_at", -1).limit(50).to_list(50) if stripe_events_coll is not None and hasattr(stripe_events_coll, "find") else []
    subscription_exception_trainers = await trainers_coll.find(
        {
            "$or": [
                {"subscription_status": {"$in": ["past_due", "unpaid", "incomplete_expired"]}},
                {"subscription_billing_status": "payment_failed"},
                {
                    "tier": {"$in": ["pro", "suburb_sponsor", "citywide"]},
                    "billing_profile_status": {"$in": ["stripe_error", "stripe_unconfigured"]},
                },
            ]
        },
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "tier": 1,
            "subscription_tier": 1,
            "subscription_status": 1,
            "subscription_billing_status": 1,
            "subscription_suburb": 1,
            "billing_profile_status": 1,
            "billing_email": 1,
            "email": 1,
            "updated_at": 1,
            "created_at": 1,
        },
    ).to_list(20) if trainers_coll is not None else []
    billing_recovery_case_rows = []
    for t in subscription_exception_trainers:
        t_id = str(t.get("id") or "")
        sub_status = str(t.get("subscription_status") or "none")
        billing_status = str(t.get("subscription_billing_status") or t.get("billing_profile_status") or "normal")
        billing_recovery_case_rows.append(
            {
                "trainer_id": t_id,
                "trainer_name": t.get("name") or t_id or "unknown",
                "tier": t.get("subscription_tier") or t.get("tier") or "core",
                "subscription_tier": t.get("subscription_tier") or t.get("tier") or "core",
                "subscription_status": sub_status,
                "subscription_billing_status": billing_status,
                "billing_collection_status": billing_status,
                "billing_profile_status": t.get("billing_profile_status") or "unknown",
                "billing_retry_state": sub_status if sub_status in {"past_due", "unpaid"} else billing_status,
                "suburb": t.get("subscription_suburb") or "",
                "created_at": t.get("updated_at") or t.get("created_at"),
                "trainer_action_token": _issue_trainer_action_token(trainer_id=t_id) if t_id else None,
            }
        )
    reactivation_candidates_coll = getattr(db, "reactivation_candidates", None)
    reactivation_case_rows_raw = await reactivation_candidates_coll.find(
        {"status": "open"},
        {"_id": 0, "trainer_id": 1, "trainer_name": 1, "email": 1, "reasons": 1, "last_notified_at": 1, "last_notification_status": 1, "updated_at": 1},
    ).to_list(20) if reactivation_candidates_coll is not None else []
    reactivation_case_rows = []
    for row in reactivation_case_rows_raw:
        trainer_id = str(row.get("trainer_id") or "")
        reactivation_case_rows.append(
            {
                **row,
                "trainer_action_token": _issue_trainer_action_token(trainer_id=trainer_id) if trainer_id else None,
            }
        )
    discovery_alerts = list(source_ingestion.get("alerts") or [])
    loop_statuses = {
        key: _loop_status(key, loop, now_dt=now_dt)
        for key, loop in {
            "ranking": ranking,
            "verification": verification,
            "discovery": discovery,
            "inference": inference,
            "source_ingestion": source_ingestion,
            "outreach": outreach,
            "health": health,
            "nurture": nurture,
            "reactivation_route": reactivation_route,
            "pro_trial_warnings": pro_trial_warnings,
        }.items()
    }
    trainer_inventory = await _trainer_inventory_rows()
    sponsor_inventory_snapshot = await suburb_inventory.ops_snapshot(db)
    provider_snapshot = provider_health.snapshot()
    message_log = await _message_log_rows()
    supply_geography = await _ops_supply_geography_summary(trainer_inventory, waitlist_summary)
    supply_trends = await _ops_supply_trend_summary(
        trainer_inventory=trainer_inventory,
        submissions_summary=submissions_summary,
        growth_attribution_summary=growth_attribution_summary,
        reactivation_summary=reactivation_summary,
    )
    seo_indexation = await _ops_seo_indexation_summary()
    ops_cases = await _ops_case_rows(
        discovery_summary=discovery_summary,
        waitlist_summary=waitlist_summary,
        loop_statuses=loop_statuses,
        fraud_suppression_cases=fraud_suppression_cases,
        claim_cases=claim_cases,
        abn_degradation_cases=abn_degradation_cases,
        billing_recovery_case_rows=billing_recovery_case_rows,
        subscription_billing_case_rows=subscription_billing_case_rows,
        reactivation_case_rows=reactivation_case_rows,
        source_ingestion_state_rows=source_ingestion_state_rows,
        message_log=message_log,
        ai_degradation_cases=ai_degradation_cases,
        sponsor_inventory_cases=sponsor_inventory_snapshot.get("exceptions", []),
        provider_cases=provider_health.cases(provider_snapshot),
    )

    return _scrub({
        "throughput": {
            "intros_24h": intros_24,
            "intros_7d": intros_7d,
            "conversions_24h": conv_24,
            "conversions_7d": conv_7d,
            "intro_to_conversion_rate": intro_to_conv,
            "engagements_total": engagements_total,
            "stalled_intros": stalled_intros,
        },
        "trust": {
            "intros_suppressed": suppressed,
            "conversions_suspicious": suspicious_conv,
            "inferred_pending": inferred_pending,
        },
        "loops": {
            "ranking": ranking,
            "verification": verification,
            "discovery": discovery,
            "inference": inference,
            "source_ingestion": source_ingestion,
            "outreach": outreach,
            "health": health,
            "nurture": nurture,
            "reactivation_route": reactivation_route,
            "pro_trial_warnings": pro_trial_warnings,
            "pipeline_guardian": pipeline_guardian_state,
        },
        "alerts": health.get("alerts", []),
        "rollback_recent": rollback_recent,
        "top_trainers": top_trainers,
        "audit_recent": audit_recent,
        "submissions_summary": submissions_summary,
        "discovery_summary": discovery_summary,
        "notification_summary": notification_summary,
        "intro_delivery_cases": intro_delivery_cases,
        "fraud_suppression_cases": fraud_suppression_cases,
        "conversion_quality_cases": conversion_quality_cases,
        "trainer_claim_cases": claim_cases,
        "abn_degradation_cases": abn_degradation_cases,
        "ai_degradation_cases": ai_degradation_cases,
        "subscription_billing_cases": subscription_billing_case_rows,
        "billing_recovery_cases": billing_recovery_case_rows,
        "integrity": integrity,
        "claim_policy": claim_policy,
        "claim_policy_summary": {
            "enabled": claim_policy.get("enabled"),
            "state": claim_policy.get("state"),
            "enforcement_mode": claim_policy.get("enforcement_mode"),
        },
        "launch_phase_state": phase_state,
        "phase_readiness_snapshot": readiness_snapshot,
        "phase_transition_decisions": phase_decisions[:10],
        "launch_phase": phase_state.get("current_phase"),
        "public_emphasis": phase_state.get("public_emphasis"),
        "readiness_status": readiness_snapshot.get("readiness_status"),
        "readiness_recommendation": readiness_snapshot.get("recommendation"),
        "intro_ready_trainer_count": readiness_snapshot.get("intro_ready_trainer_count"),
        "blocked_trainer_count": readiness_snapshot.get("blocked_trainer_count"),
        "blockers_to_next_phase": readiness_snapshot.get("blockers_to_next_phase", []),
        "dataset_identity": {
            "list_id": suburb_identity.get("list_id"),
            "suburb_count": suburb_identity.get("suburb_count"),
            "hash": suburb_identity.get("suburb_hash_sha256_code_name"),
            "as_of_date": suburb_identity.get("as_of_date_melbourne"),
        },
        "integrity_status": suburb_status.get("level", "warn"),
        "integrity_reason_codes": suburb_status.get("reason_codes", []),
        "suburb_dataset": suburb_dataset.get("identity", {}),
        "suburb_dataset_integrity": suburb_dataset.get("status", {}),
        "owner_waitlist_summary": waitlist_summary,
        "kpi_prelaunch": kpi_prelaunch,
        "growth_attribution_summary": growth_attribution_summary,
        "reactivation_summary": reactivation_summary,
        "capability_health_summary": capability_health_summary,
        "recent_ingestion_runs": recent_ingestion_runs,
        "last_ingestion_run": last_ingestion_run,
        "pipeline_guardian": pipeline_guardian_state,
        "ops_supply_geography": supply_geography,
        "ops_supply_trends": supply_trends,
        "ops_seo_indexation": seo_indexation,
        "trainer_inventory": trainer_inventory,
        "sponsor_inventory": sponsor_inventory_snapshot,
        "provider_health": provider_snapshot,
        "message_log": message_log,
        "ops_cases": ops_cases,
        "cases": ops_cases,
        "ops_investigation": {
            "loop_statuses": loop_statuses,
            "intro_delivery_cases": intro_delivery_cases,
            "fraud_suppression_cases": fraud_suppression_cases,
            "conversion_quality_cases": conversion_quality_cases,
            "trainer_claim_cases": claim_cases,
            "abn_degradation_cases": abn_degradation_cases,
            "ai_degradation_cases": ai_degradation_cases,
            "billing_recovery_cases": billing_recovery_case_rows,
            "subscription_billing_cases": subscription_billing_case_rows,
            "sponsor_inventory_cases": sponsor_inventory_snapshot.get("exceptions", []),
            "reactivation_cases": reactivation_case_rows,
            "source_ingestion_sources": source_ingestion_state_rows,
            "discovery_alerts": discovery_alerts,
            "provider_health": provider_snapshot,
        },
        "matching": await build_matching_oversight_read_model(db),
        "ts": now_iso(),
    })


async def build_matching_oversight_read_model(target_db: Any) -> Dict[str, Any]:
    """Protected, redacted matching read model for the Operations Console.

    Governance (Contract v2, P6, DF-015, DF-018, DF-024):
    - Policy version, decision/triage distribution, local vs expanded scope.
    - Eligible count, AI usage, latency, and degradation reasons.
    - Reason-code distribution, presentation IDs/order.
    - Capability freshness/invalidation and anti-gaming events.
    - Urgent-provider freshness, coverage gaps, and correction requests.
    - Enquiry/follow-up delivery states (pending, delivered, retryable_failure, terminal_failure, suppressed).
    - NEVER exposes raw descriptions, contact details, IPs, token values, prompts, scores, tiers, or manual match overrides.
    """
    match_events_coll = getattr(target_db, "match_events", None)
    events: List[Dict[str, Any]] = []
    if match_events_coll is not None:
        try:
            events = await match_events_coll.find({}, {"_id": 0}).sort("created_at", -1).limit(500).to_list(500)
        except Exception as exc:
            logger.warning("Failed to query match events for oversight: %s", exc)

    # 1. Decision & Triage distribution
    decision_dist: Dict[str, int] = {
        "recommendations": 0,
        "limited_local_results": 0,
        "no_confirmed_match": 0,
        "degraded_recommendations": 0,
        "degraded_no_confirmed_match": 0,
        "immediate_human_danger": 0,
        "urgent_animal_health_support": 0,
        "serious_behavioural_support": 0,
        "needs_clarification": 0,
    }
    scope_dist: Dict[str, int] = {"local": 0, "expanded": 0}
    reason_code_dist: Dict[str, int] = {}
    eligible_counts: List[int] = []

    for ev in events:
        state = str(ev.get("decision_state") or "")
        if state in decision_dist:
            decision_dist[state] += 1
        elif state:
            decision_dist[state] = decision_dist.get(state, 0) + 1

        scope = str(ev.get("search_scope") or "local")
        scope_dist[scope] = scope_dist.get(scope, 0) + 1

        res_ids = ev.get("result_ids") or []
        eligible_counts.append(len(res_ids))

        for rc in ev.get("reason_codes") or []:
            rc_str = str(rc)
            reason_code_dist[rc_str] = reason_code_dist.get(rc_str, 0) + 1

    total_events = len(events)
    avg_eligible = round(sum(eligible_counts) / max(1, len(eligible_counts)), 2) if eligible_counts else 0.0

    # 2. AI usage & degradation events
    degradation_events = await ai_service.get_degradation_events(limit=50, db=target_db)
    degradation_by_error: Dict[str, int] = {}
    latencies: List[float] = []
    sanitized_degradation_events: List[Dict[str, Any]] = []

    for dev in degradation_events:
        err_type = str(dev.get("error_type") or "unknown")
        degradation_by_error[err_type] = degradation_by_error.get(err_type, 0) + 1
        lat = dev.get("latency_ms")
        if lat and isinstance(lat, (int, float)):
            latencies.append(float(lat))
        sanitized_degradation_events.append({
            "id": dev.get("id"),
            "provider": dev.get("provider", "google_genai"),
            "model": dev.get("model", ai_service.GEMINI_MODEL),
            "error_type": err_type,
            "latency_ms": lat,
            "fallback_used": dev.get("fallback_used", True),
            "decision_state": dev.get("decision_state"),
            "timestamp": dev.get("timestamp"),
        })

    avg_latency = round(sum(latencies) / max(1, len(latencies)), 2) if latencies else 0.0

    # 3. Presentation order sample (last 20 events) - strictly redacted
    presentation_sample: List[Dict[str, Any]] = []
    for ev in events[:20]:
        presentation_sample.append({
            "match_id": ev.get("id"),
            "created_at": ev.get("created_at"),
            "policy_version": ev.get("policy_version", matching_contract_v2.DECISION_CONTRACT_VERSION),
            "decision_state": ev.get("decision_state"),
            "search_scope": ev.get("search_scope"),
            "result_ids": ev.get("result_ids") or [],
            "reason_codes": ev.get("reason_codes") or [],
        })

    # 4. Capability freshness & anti-gaming
    capability_health = {}
    trainers_coll = getattr(target_db, "trainers", None)
    if trainers_coll is not None:
        try:
            capability_health = await trainer_quality.compute_capability_health_summary(trainers_coll)
        except Exception:
            pass

    audit_coll = getattr(target_db, "audit_log", None)
    anti_gaming_count = 0
    if audit_coll is not None:
        try:
            anti_gaming_count = await audit_coll.count_documents({
                "action": {"$in": ["trainer_capability_invalidation", "anti_gaming_detected", "trainer_recheck"]}
            })
        except Exception:
            pass

    # 5. Urgent provider freshness & coverage (MP-003T: dynamic recomputation)
    urgent_coll = getattr(target_db, "urgent_providers", None)
    urgent_by_freshness: Dict[str, int] = {"current": 0, "stale": 0, "suppressed": 0}
    urgent_total = 0
    covered_localities: set[str] = set()

    urgent_docs: List[Dict[str, Any]] = []
    if urgent_coll is not None:
        try:
            urgent_docs = await urgent_coll.find({}, {"_id": 0}).to_list(100)
        except Exception:
            urgent_docs = []

    if not urgent_docs:
        urgent_docs = [dict(p) for p in urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS]

    urgent_total = len(urgent_docs)
    for doc in urgent_docs:
        st, is_fresh = urgent_providers_service.compute_urgent_provider_freshness(doc)
        eff_st = st.value if isinstance(st, urgent_providers_service.FreshnessState) else str(st)
        if eff_st in urgent_by_freshness:
            urgent_by_freshness[eff_st] += 1
        else:
            urgent_by_freshness["stale"] += 1

        if is_fresh and eff_st == "current":
            for loc in doc.get("service_area", []):
                covered_localities.add(str(loc).strip().lower())

    coverage_gaps_count = max(0, 100 - len(covered_localities))

    corrections_coll = getattr(target_db, "urgent_provider_corrections", None)
    pending_corrections_count = 0
    recent_corrections: List[Dict[str, Any]] = []
    if corrections_coll is not None:
        try:
            pending_corrections_count = await corrections_coll.count_documents({"status": "pending_review"})
            raw_corrections = await corrections_coll.find({}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)
            for rc in raw_corrections:
                recent_corrections.append({
                    "id": rc.get("id"),
                    "provider_id": rc.get("provider_id"),
                    "provider_name": rc.get("provider_name"),
                    "reason": rc.get("reason"),
                    "status": rc.get("status"),
                    "created_at": rc.get("created_at"),
                })
        except Exception:
            pass

    # 6. Follow-up distribution
    intros_coll = getattr(target_db, "intros", None)
    follow_up_dist: Dict[str, int] = {
        "pending": 0,
        "delivered": 0,
        "retryable_failure": 0,
        "terminal_failure": 0,
        "suppressed": 0,
    }
    follow_up_total = 0
    if intros_coll is not None:
        try:
            follow_up_filter = {"match_id": {"$exists": True, "$ne": None}}
            follow_up_total = await intros_coll.count_documents(follow_up_filter)
            for s in ["pending", "delivered", "retryable_failure", "terminal_failure", "suppressed"]:
                follow_up_dist[s] = await intros_coll.count_documents({
                    **follow_up_filter,
                    "$or": [{"delivery_state": s}, {"delivery_status": s}],
                })
        except Exception:
            pass

    return {
        "policy_version": matching_contract_v2.DECISION_CONTRACT_VERSION,
        "total_match_events": total_events,
        "decision_triage_distribution": decision_dist,
        "scope_distribution": scope_dist,
        "eligible_count": {
            "average_eligible_count": avg_eligible,
            "total_match_events": total_events,
        },
        "ai_usage": {
            "total_degradations": len(degradation_events),
            "by_error_type": degradation_by_error,
            "average_latency_ms": avg_latency,
            "recent_degradation_events": sanitized_degradation_events[:10],
        },
        "reason_code_distribution": reason_code_dist,
        "presentation_order_sample": presentation_sample,
        "capability_freshness_and_anti_gaming": {
            "capability_health": capability_health,
            "anti_gaming_events_count": anti_gaming_count,
        },
        "urgent_provider_status": {
            "total_providers": urgent_total,
            "by_freshness": urgent_by_freshness,
            "current_records": urgent_by_freshness.get("current", 0),
            "stale_records": urgent_by_freshness.get("stale", 0),
            "suppressed_records": urgent_by_freshness.get("suppressed", 0),
            "coverage_gaps": [
                "No verified veterinary behaviourist registered with active VPRBV endorsement",
                "Local urgent veterinary care coverage currently limited to Inner North Melbourne; outer regions unserved",
            ],
            "coverage_gaps_count": coverage_gaps_count,
            "has_local_coverage": len(covered_localities) > 0,
            "pending_corrections_count": pending_corrections_count,
            "recent_corrections": recent_corrections,
        },
        "follow_up_distribution": {
            "total_follow_ups": follow_up_total,
            "by_state": follow_up_dist,
        },
        "ts": now_iso(),
    }


@api.get("/oversight/matching")
async def oversight_matching(_: None = Depends(require_oversight)) -> Dict[str, Any]:
    """Protected, redacted matching read model for the Operations Console."""
    return await build_matching_oversight_read_model(db)


class OversightDegradationAcknowledgeIn(BaseModel):
    action: str = Field(..., description="e.g. acknowledge or reset_circuit")
    confirmed: bool = Field(..., description="Must be explicitly confirmed")
    notes: Optional[str] = None


@api.post("/oversight/matching/degradation/acknowledge")
async def oversight_matching_degradation_acknowledge(
    payload: OversightDegradationAcknowledgeIn,
    _: None = Depends(require_oversight),
) -> Dict[str, Any]:
    """Acknowledge AI degradation and reset circuit safely."""
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirmation required.")

    ai_service.clear_degradation_events()
    await _audit(
        "ai_degradation_acknowledged",
        "matching_ai",
        after={"action": payload.action, "notes": payload.notes},
        actor="ops",
    )
    return {"ok": True, "action": payload.action, "circuit_status": "reset", "ts": now_iso()}


class OversightUrgentCorrectionReviewIn(BaseModel):
    action: str = Field(..., description="accept, reject, or suppress_provider")
    confirmed: bool = Field(..., description="Must be explicitly confirmed")
    official_source_url: Optional[str] = Field(default=None, description="Documented first-party official URL verifying provider facts")
    verified_official_source: bool = Field(default=False, description="Operator certification of verified first-party official source")
    evidence_reference: Optional[str] = Field(default=None, description="Recorded section/page citation on official provider site")
    reviewed_field_values: Optional[Dict[str, Any]] = Field(default=None, description="Exact verified field values e.g. contact_method, stated_hours")
    notes: Optional[str] = None


@api.post("/oversight/urgent-providers/corrections/{correction_id}/review")
async def oversight_urgent_provider_correction_review(
    correction_id: str,
    payload: OversightUrgentCorrectionReviewIn,
    request: Request,
    _: None = Depends(require_oversight),
) -> Dict[str, Any]:
    """Review and act on urgent provider public correction request with bounded recorded evidence."""
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirmation required.")
    if payload.action not in {"accept", "reject", "suppress_provider"}:
        raise HTTPException(status_code=400, detail="Invalid action. Must be accept, reject, or suppress_provider.")

    corrections_coll = getattr(db, "urgent_provider_corrections", None)
    if corrections_coll is None:
        raise HTTPException(status_code=503, detail="Store unavailable")

    corr = await corrections_coll.find_one({"id": correction_id}, {"_id": 0})
    if not corr:
        raise HTTPException(status_code=404, detail="Correction request not found")

    operator_identity = f"ops:{_client_ip(request)}"
    reviewed_ts = now_iso()

    verified_official_url = ""
    if payload.action == "accept":
        verified_official_url = (payload.official_source_url or corr.get("official_source_url") or "").strip()
        if not payload.verified_official_source or not verified_official_url:
            raise HTTPException(
                status_code=400,
                detail="Cannot accept correction or mark provider current without verified official source URL and explicit operator verification.",
            )

        # Refinement 2: Bounded recorded evidence model
        if not payload.evidence_reference or len(payload.evidence_reference.strip()) < 5:
            raise HTTPException(
                status_code=400,
                detail="Recorded evidence reference is required (e.g. section, page, or document citation on official site).",
            )
        if not payload.reviewed_field_values or not isinstance(payload.reviewed_field_values, dict):
            raise HTTPException(
                status_code=400,
                detail="Exact checked fields (reviewed_field_values) must be provided with verified values.",
            )

        # Approved provider-domain relationship check
        clean_url = verified_official_url.lower()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            raise HTTPException(status_code=400, detail="Invalid official source URL scheme.")

        parsed = urlparse(verified_official_url)
        domain = parsed.netloc.lower()

        # Reject aggregators, social media, shorteners, search grounding/maps, and generic blog platforms
        disallowed_aggregators = [
            "facebook.com", "instagram.com", "yellowpages", "truelocal", "google.com/maps",
            "goo.gl", "yelp.com", "womo.com.au", "twitter.com", "x.com", "tiktok.com",
            "linkedin.com", "wordpress.com", "wixsite.com", "blogspot.com", "medium.com",
            "bit.ly", "tinyurl.com"
        ]
        if any(agg in domain or agg in clean_url for agg in disallowed_aggregators):
            raise HTTPException(status_code=400, detail="Aggregators, social media, directory blogs, and maps links are not permitted official sources.")

        # Approved domain relationship:
        provider_id = corr.get("provider_id") or ""
        provider_name = (corr.get("provider_name") or "").lower()

        is_approved_domain = False
        if "lost_dogs_home" in provider_id or "lost dogs" in provider_name:
            if domain == "dogshome.com" or domain.endswith(".dogshome.com"):
                is_approved_domain = True
        elif domain.endswith(".gov.au") or domain.endswith(".edu.au"):
            is_approved_domain = True
        elif provider_id:
            urgent_coll = getattr(db, "urgent_providers", None)
            if urgent_coll is not None:
                existing_prov = await urgent_coll.find_one({"provider_id": provider_id}, {"_id": 0})
                if existing_prov and existing_prov.get("official_source_url"):
                    registered_domain = urlparse(existing_prov["official_source_url"]).netloc.lower()
                    if domain == registered_domain or domain.endswith(f".{registered_domain}"):
                        is_approved_domain = True

        if not is_approved_domain:
            raise HTTPException(
                status_code=400,
                detail=f"URL domain '{domain}' does not have an approved first-party provider relationship for {provider_id or provider_name}.",
            )

    new_status = "accepted" if payload.action == "accept" else ("suppressed" if payload.action == "suppress_provider" else "rejected")
    await corrections_coll.update_one(
        {"id": correction_id},
        {
            "$set": {
                "status": new_status,
                "reviewed_at": reviewed_ts,
                "reviewed_by": operator_identity,
                "review_notes": payload.notes or "",
                "verified_official_source": payload.verified_official_source,
                "verified_official_url": verified_official_url,
                "evidence_reference": payload.evidence_reference,
                "reviewed_field_values": payload.reviewed_field_values,
            }
        },
    )

    urgent_coll = getattr(db, "urgent_providers", None)
    provider_id = corr.get("provider_id")
    if urgent_coll is not None and provider_id:
        if payload.action == "suppress_provider":
            await urgent_coll.update_one({"provider_id": provider_id}, {"$set": {"freshness_state": "suppressed"}})
        elif payload.action == "accept":
            update_provider_doc = {
                "freshness_state": "current",
                "official_source_url": verified_official_url,
                "last_verified_at": reviewed_ts,
                "verified_by": operator_identity,
                "evidence_reference": payload.evidence_reference,
                "reviewed_field_values": payload.reviewed_field_values,
                "verification_notes": payload.notes or "",
            }
            if payload.reviewed_field_values:
                for k in ["contact_method", "stated_hours", "service_area", "name"]:
                    if k in payload.reviewed_field_values:
                        update_provider_doc[k] = payload.reviewed_field_values[k]

            await urgent_coll.update_one({"provider_id": provider_id}, {"$set": update_provider_doc})

    await _audit(
        "urgent_provider_correction_reviewed",
        correction_id,
        after={
            "action": payload.action,
            "status": new_status,
            "provider_id": provider_id,
            "verified_official_url": verified_official_url,
            "evidence_reference": payload.evidence_reference,
            "operator": operator_identity,
        },
        actor="ops",
    )
    return {"ok": True, "correction_id": correction_id, "status": new_status, "ts": reviewed_ts}


RETRY_LEASE_SECONDS = 300


class OversightFollowUpRetryIn(BaseModel):
    confirmed: bool = Field(..., description="Must be explicitly confirmed")
    notes: Optional[str] = None


@api.post("/oversight/matching/follow-ups/{intro_id}/retry")
async def oversight_matching_follow_up_retry(
    intro_id: str,
    payload: OversightFollowUpRetryIn,
    request: Request,
    _: None = Depends(require_oversight),
) -> Dict[str, Any]:
    """Retry a failed or pending match follow-up enquiry with atomic lease claim and crash recovery."""
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirmation required.")

    intro = await db.intros.find_one({"id": intro_id}, {"_id": 0})
    if not intro:
        raise HTTPException(status_code=404, detail="Follow-up intro not found")

    current_state = str(intro.get("delivery_state") or intro.get("delivery_status") or "")
    if current_state == "delivered":
        return {"ok": True, "intro_id": intro_id, "delivery_state": "delivered", "idempotent": True}

    if current_state == "terminal_failure":
        raise HTTPException(status_code=409, detail="Terminal failure cannot be automatically retried without schema remediation.")

    if current_state == "suppressed":
        raise HTTPException(status_code=409, detail="Suppressed follow-up cannot be automatically retried without manual fraud clearance.")

    now_dt = datetime.now(timezone.utc)
    lease_cutoff = (now_dt - timedelta(seconds=RETRY_LEASE_SECONDS)).isoformat()

    # MP-002S: Atomic compare-and-set claim with recovery lease
    claimed = await db.intros.find_one_and_update(
        {
            "id": intro_id,
            "$or": [
                {"delivery_state": {"$in": ["retryable_failure", "pending"]}},
                {"delivery_status": {"$in": ["retryable_failure", "pending"]}},
                {
                    "delivery_state": "in_progress",
                    "$or": [
                        {"retry_claimed_at": {"$lt": lease_cutoff}},
                        {"retry_claimed_at": {"$exists": False}},
                    ],
                },
            ],
        },
        {
            "$set": {
                "delivery_state": "in_progress",
                "delivery_status": "in_progress",
                "status": "in_progress",
                "retry_claimed_at": now_dt.isoformat(),
                "retry_claimed_by": f"ops:{_client_ip(request)}",
            }
        },
        return_document=True,
    )

    if not claimed:
        refreshed = await db.intros.find_one({"id": intro_id}, {"_id": 0}) or {}
        st = str(refreshed.get("delivery_state") or refreshed.get("delivery_status") or "")
        if st == "delivered":
            return {"ok": True, "intro_id": intro_id, "delivery_state": "delivered", "idempotent": True}
        if st == "in_progress":
            raise HTTPException(status_code=409, detail="Retry already in progress by another worker (lease active).")
        raise HTTPException(status_code=409, detail=f"Cannot retry follow-up in state: {st}")

    trainer = await db.trainers.find_one({"id": intro.get("trainer_id")}, {"_id": 0})
    if not trainer:
        await db.intros.update_one({"id": intro_id}, {"$set": {"delivery_state": "terminal_failure", "delivery_status": "terminal_failure"}})
        raise HTTPException(status_code=404, detail="Trainer not found")

    try:
        notif_meta = await notifications_service.notify_trainer_new_intro(db, trainer, intro)
        new_state, update_fields = map_notification_delivery_state("pending", notif_meta)
    except Exception as exc:
        logger.exception("Retry dispatch failed for intro_id=%s", intro_id)
        new_state, update_fields = map_notification_delivery_state("pending", {
            "trainer_notification_status": "failed",
            "trainer_notification_error": str(exc)[:200],
        })

    update_doc = {
        **update_fields,
        "retried_at": now_dt.isoformat(),
        "retry_notes": payload.notes or "",
        "retry_claimed_at": None,
    }
    await db.intros.update_one({"id": intro_id}, {"$set": update_doc})

    await _audit(
        "matching_follow_up_retried",
        intro_id,
        before={"delivery_state": current_state},
        after={"delivery_state": new_state},
        actor="ops",
    )
    return {"ok": True, "intro_id": intro_id, "delivery_state": new_state, "idempotent": False}


class OversightCapabilityRecheckIn(BaseModel):
    confirmed: bool = Field(..., description="Must be explicitly confirmed")
    notes: Optional[str] = None


@api.post("/oversight/trainers/{trainer_id}/capability/recheck")
async def oversight_trainer_capability_recheck(
    trainer_id: str,
    payload: OversightCapabilityRecheckIn,
    _: None = Depends(require_oversight),
) -> Dict[str, Any]:
    """Recheck trainer capability projection under strict statutory rules without policy override."""
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Confirmation required.")

    trainer = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")

    proj = trainer_quality.build_match_ready_projection(trainer)
    await db.trainers.update_one(
        {"id": trainer_id},
        {"$set": {
            "projection_version": proj.get("projection_version"),
            "match_eligible": proj.get("match_eligible"),
            "invalidation_reasons": proj.get("invalidation_reasons"),
            "rechecked_at": now_iso(),
        }}
    )
    await _audit(
        "trainer_capability_rechecked",
        trainer_id,
        after={"match_eligible": proj.get("match_eligible"), "invalidation_reasons": proj.get("invalidation_reasons")},
        actor="ops",
    )
    return {
        "ok": True,
        "trainer_id": trainer_id,
        "match_eligible": proj.get("match_eligible"),
        "invalidation_reasons": proj.get("invalidation_reasons"),
        "ts": now_iso(),
    }


@api.get("/claims/validate")
async def validate_claim(
    claim: str = Query(..., min_length=1),
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """Read-only non-blocking compatibility claim validation. Never blocks or mutates state."""
    normalized_claim = " ".join((claim or "").strip().split())
    return {
        "ok": True,
        "claim": claim,
        "normalized_claim": normalized_claim,
        "allowed": True,
        "valid": True,
        "status": "valid",
        "ts": now_iso(),
    }


def _is_subscription_event(event_type: str, obj: Dict[str, Any]) -> bool:
    return (
        event_type == "checkout.session.completed"
        or event_type.startswith("customer.subscription.")
        or (event_type.startswith("invoice.") and bool(stripe_billing.subscription_id_for_event(obj)))
        or (event_type == "charge.refunded" and bool((obj.get("metadata") or {}).get("trainer_id")))
    )


async def _subscription_trainer_id(event_type: str, obj: Dict[str, Any]) -> str:
    trainer_id = stripe_billing.subscription_trainer_id(event_type, obj)
    if trainer_id:
        return trainer_id
    subscription_id = stripe_billing.subscription_id_for_event(obj)
    trainers_coll = getattr(db, "trainers", None)
    if not subscription_id or trainers_coll is None:
        return ""
    trainer = await trainers_coll.find_one({"stripe_subscription_id": subscription_id}, {"_id": 0, "id": 1})
    return str((trainer or {}).get("id") or "")


@api.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> Dict[str, Any]:
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe_billing.construct_webhook_event(payload=payload, signature=signature)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Stripe webhook rejected: {str(exc)}")

    event_type = str(event.get("type") or "")
    obj = (event.get("data") or {}).get("object") or {}
    invoice_id = stripe_billing.extract_invoice_id(event_type, obj)
    if not invoice_id and event_type.startswith("charge.dispute"):
        charge_id = str(obj.get("charge") or "")
        invoice_id = stripe_billing.invoice_id_from_charge(charge_id)
    event_id = str(event.get("id") or "")
    subscription_event = _is_subscription_event(event_type, obj)
    trainer_id = await _subscription_trainer_id(event_type, obj) if subscription_event else ""
    if event_id:
        try:
            await db.stripe_events.insert_one(
                {
                    "id": event_id,
                    "type": event_type,
                    "invoice_id": invoice_id,
                    "status": "processing",
                    "trainer_id": trainer_id,
                    "created_at": now_iso(),
                }
            )
        except DuplicateKeyError:
            return {"ok": True, "duplicate": True}

    processed_status = "processed"
    processed_reason = ""
    if subscription_event:
        subscription_updates = stripe_billing.subscription_update_for_event(event_type, obj)
        if not trainer_id:
            processed_status = "needs_review"
            processed_reason = "subscription_trainer_unresolved"
            subscription_updates = {}
        elif subscription_updates:
            metadata = stripe_billing.subscription_metadata(obj)
            event_tier = str(metadata.get("tier") or subscription_updates.get("subscription_tier") or "").lower()
            event_status = str(subscription_updates.get("subscription_status") or obj.get("status") or "").lower()
            reservation_id = str(metadata.get("reservation_id") or subscription_updates.get("sponsor_reservation_id") or "")
            subscription_id_for_inventory = str(
                subscription_updates.get("stripe_subscription_id") or obj.get("subscription") or obj.get("id") or ""
            )
            if event_tier in {"suburb_sponsor", "citywide"} and event_status in stripe_billing.ACTIVE_SUBSCRIPTION_STATUSES:
                activation = await suburb_inventory.activate_reservation(
                    db,
                    reservation_id=reservation_id,
                    subscription_id=subscription_id_for_inventory,
                )
                if not activation.get("ok"):
                    processed_status = "needs_review"
                    processed_reason = str(activation.get("code") or "sponsor_inventory_activation_failed")
                    subscription_updates = {}
            trainer_filter: Dict[str, Any] = {"id": trainer_id}
            subscription_id = str(subscription_updates.get("stripe_subscription_id") or "")
            if event_type in {
                "customer.subscription.updated",
                "customer.subscription.resumed",
                "customer.subscription.deleted",
                "customer.subscription.paused",
            } and subscription_id:
                trainer_filter["stripe_subscription_id"] = subscription_id
            if subscription_updates:
                result = await db.trainers.update_one(trainer_filter, {"$set": subscription_updates})
                if getattr(result, "matched_count", 1) != 1:
                    processed_status = "needs_review"
                    processed_reason = "subscription_trainer_state_conflict"
                elif subscription_updates.get("subscription_metadata_error"):
                    processed_status = "needs_review"
                    processed_reason = "subscription_metadata_invalid"
                elif (
                    event_type in {"customer.subscription.deleted", "customer.subscription.paused"}
                    or event_status in stripe_billing.TERMINAL_NONPAYMENT_SUBSCRIPTION_STATUSES
                ) and (reservation_id or subscription_id_for_inventory):
                    await suburb_inventory.release_reservation(
                        db,
                        reservation_id=reservation_id,
                        subscription_id="" if reservation_id else subscription_id_for_inventory,
                        reason="cancelled" if event_type.endswith("deleted") else "payment_failed",
                    )
                elif event_type == "charge.refunded" and (reservation_id or subscription_id_for_inventory):
                    await suburb_inventory.release_reservation(
                        db,
                        reservation_id=reservation_id,
                        subscription_id="" if reservation_id else subscription_id_for_inventory,
                        reason="refunded",
                    )
        else:
            processed_status = "needs_review"
            processed_reason = "subscription_event_unsupported"
    else:
        intro_id = str(((obj.get("metadata") or {}).get("intro_id")) or "")
        updates: Dict[str, Any] = {"stripe_last_event_type": event_type, "stripe_last_event_at": now_iso()}
        updates.update(stripe_billing.billing_updates_for_event(event_type, obj))
        if invoice_id:
            await db.intros.update_many({"stripe_invoice_id": invoice_id}, {"$set": updates})
        elif intro_id:
            await db.intros.update_many({"id": intro_id}, {"$set": updates})

    if event_id:
        await db.stripe_events.update_one(
            {"id": event_id},
            {
                "$set": {
                    "status": processed_status,
                    "trainer_id": trainer_id,
                    "processed_at": now_iso(),
                    "reason": processed_reason,
                    "subscription_tier": str((obj.get("metadata") or {}).get("tier") or ""),
                }
            },
        )
    return {"ok": True, "needs_review": processed_status == "needs_review"}


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------

app.include_router(api)

raw_cors = os.environ.get("CORS_ORIGINS", "*")
parsed_origins = [o.strip() for o in re.split(r"[,|\s]+", raw_cors) if o.strip()]
if not parsed_origins:
    parsed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=parsed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:  # type: ignore[override]
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


_BG_TASKS: List[asyncio.Task] = []


async def _seed_if_empty() -> None:
    if await db.trainers.count_documents({}) > 0:
        return
    # Delegate to the canonical seeding pipeline to prevent any bypass of
    # schema validation, deduplication, claimed-profile preservation, or /ops failure recording.
    from scripts.seed_melbourne_trainers import process_seeding, DEFAULT_SEED_FILE, load_seed_file
    try:
        candidates, _ = load_seed_file(DEFAULT_SEED_FILE)
    except Exception:
        logger.exception("Failed to load seed file %s for startup seeding", DEFAULT_SEED_FILE)
        candidates = []

    if not candidates:
        logger.info("Canonical seed file contains 0 candidates; startup seeding creates 0 records")
        return

    logger.info("Empty trainer collection — canonical startup seeding %s candidates", len(candidates))
    summary = await process_seeding(db, candidates, dry_run=False)
    logger.info("Canonical startup seeding completed: %s", summary)


async def _seed_discovery_if_empty() -> None:
    """Seed a small starter set of public discovery URLs so the autonomous
    ingestion loop has something to crank on out-of-the-box.
    """
    if await db.discovery_queue.count_documents({}) > 0:
        return
    # Any candidates with unresolved DNS, 404s, or lacking primary source evidence
    # must not be seeded. Currently 0 authentic primary sources qualify locally.
    candidates: List[Dict[str, Any]] = []
    for c in candidates:
        await db.discovery_queue.insert_one(
            {"id": new_id(), "status": "pending", "created_at": now_iso(), **c}
        )
    if candidates:
        logger.info("seeded %s discovery URLs", len(candidates))


def _cancel_bg_tasks() -> None:
    for task in _BG_TASKS:
        task.cancel()
    _BG_TASKS.clear()


async def _ensure_indexes() -> None:
    try:
        await db.trainers.create_index("id", unique=True, sparse=True)
        await db.suburbs.create_index("slug", unique=True)
        await db.suburbs.create_index("id", unique=True)
        await db.suburbs.create_index("suburb_name")
        await db.suburbs.create_index("region_cluster")
        await db.intros.create_index([("trainer_id", 1), ("created_at", -1)])
        await db.intros.create_index("ip")
        await db.intros.create_index("idempotency_key", unique=True, sparse=True)
        await db.intros.create_index("composite_idempotency_key", unique=True, sparse=True)
        await db.intros.create_index("stripe_invoice_id", sparse=True)
        # TTL requires BSON datetimes, not ISO strings. Matching writes a
        # timezone-aware datetime; the migration script converts pre-fix
        # sandbox records before this index is relied on for acceptance.
        await db.match_events.create_index("id", unique=True, sparse=True)
        await db.match_events.create_index("expires_at", expireAfterSeconds=0, sparse=True)
        await db.match_contexts.create_index("token_hash", unique=True, sparse=True)
        await db.match_contexts.create_index("expires_at", expireAfterSeconds=0, sparse=True)
        await db.conversions.create_index([("intro_id", 1), ("billing_status", 1)])
        await db.engagements.create_index([("intro_id", 1), ("created_at", -1)])
        await db.submissions.create_index("status")
        await db.audit_log.create_index("ts")
        await db.pricing_state.create_index("suburb", unique=True)
        await db.system_state.create_index("key", unique=True)
        await db.discovery_queue.create_index("status")
        await db.discovery_queue.create_index("url")
        await db.discovery_queue.create_index([("source_url", 1), ("status", 1)])
        delisted_coll = getattr(db, "delisted_entities", None)
        if delisted_coll is not None and hasattr(delisted_coll, "create_index"):
            await delisted_coll.create_index("abn", sparse=True)
            await delisted_coll.create_index("normalized_phone", sparse=True)
            await delisted_coll.create_index("website_domain", sparse=True)
        await db.trainers.create_index("stripe_customer_id", sparse=True)
        await db.trainers.create_index("stripe_subscription_id", sparse=True)
        await db.trainers.create_index("claim_status")
        await db.trainers.create_index("abn", sparse=True)
        claim_events_coll = getattr(db, "claim_events", None)
        if claim_events_coll is not None and hasattr(claim_events_coll, "create_index"):
            await claim_events_coll.create_index("id", unique=True, sparse=True)
            await claim_events_coll.create_index([("trainer_id", 1), ("status", 1), ("updated_at", -1)])
            await claim_events_coll.create_index("expires_at")
            await claim_events_coll.create_index("status")
        abn_cache_coll = getattr(db, "abn_cache", None)
        if abn_cache_coll is not None and hasattr(abn_cache_coll, "create_index"):
            await abn_cache_coll.create_index("abn", unique=True, sparse=True)
            await abn_cache_coll.create_index("cached_at")
            await abn_cache_coll.create_index("expires_at", expireAfterSeconds=0, sparse=True)
        await db.stripe_events.create_index("id", unique=True, sparse=True)
        await db.stripe_events.create_index([("status", 1), ("created_at", -1)])
        await db.stripe_events.create_index([("trainer_id", 1), ("created_at", -1)])
        sponsor_inventory_coll = getattr(db, "sponsor_inventory", None)
        if sponsor_inventory_coll is not None and hasattr(sponsor_inventory_coll, "create_index"):
            await sponsor_inventory_coll.create_index("id", unique=True)
            await sponsor_inventory_coll.create_index("occupancy_key", unique=True, sparse=True)
            await sponsor_inventory_coll.create_index([("scope", 1), ("key", 1), ("status", 1)])
            await sponsor_inventory_coll.create_index([("trainer_id", 1), ("status", 1)])
            await sponsor_inventory_coll.create_index("expires_at", sparse=True)
        sponsor_events_coll = getattr(db, "sponsor_inventory_events", None)
        if sponsor_events_coll is not None and hasattr(sponsor_events_coll, "create_index"):
            await sponsor_events_coll.create_index("id", unique=True)
            await sponsor_events_coll.create_index([("status", 1), ("created_at", -1)])
        sponsor_rotation_coll = getattr(db, "sponsor_rotation_counters", None)
        if sponsor_rotation_coll is not None and hasattr(sponsor_rotation_coll, "create_index"):
            await sponsor_rotation_coll.create_index("id", unique=True)
        await db.config_snapshots.create_index("applied_at")
        await db.outreach_events.create_index([("intro_id", 1), ("kind", 1)], unique=True)
        await db.notification_events.create_index("id", unique=True, sparse=True)
        await db.ops_case_states.create_index("case_id", unique=True, sparse=True)
        await db.ops_case_states.create_index("updated_at")
        await db.auth_attempts.create_index("key", unique=True)
        await db.auth_attempts.create_index("updated_at")
        await db.phase_readiness_snapshots.create_index("snapshot_kind", unique=True)
        await db.phase_transition_decisions.create_index("id", unique=True, sparse=True)
        await db.phase_transition_decisions.create_index("decided_at")
        await db.owner_waitlist.create_index([("email_norm", 1), ("suburb_norm", 1), ("status", 1)], unique=True)
        await db.owner_waitlist.create_index([("status", 1), ("created_at", -1)])
        await db.owner_waitlist_events.create_index("id", unique=True, sparse=True)
        await db.owner_waitlist_events.create_index([("event_type", 1), ("created_at", -1)])
        if hasattr(db, "urgent_providers"):
            await db.urgent_providers.create_index("provider_id", unique=True, sparse=True)
            await db.urgent_providers.create_index("category")
            await db.urgent_providers.create_index("freshness_state")
        if hasattr(db, "urgent_provider_corrections"):
            await db.urgent_provider_corrections.create_index("id", unique=True, sparse=True)
            await db.urgent_provider_corrections.create_index([("status", 1), ("created_at", -1)])
    except Exception as exc:
        logger.warning("Startup database index creation non-fatal warning: %s", exc)


async def _seed_urgent_providers_if_empty() -> None:
    """Seed official-source urgent providers if collection is empty."""
    try:
        if hasattr(db, "urgent_providers") and await db.urgent_providers.count_documents({}) == 0:
            for p in urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS:
                await db.urgent_providers.insert_one(dict(p))
            logger.info("Canonical startup seeding: seeded %d official urgent provider records", len(urgent_providers_service.OFFICIAL_STATIC_URGENT_PROVIDERS))
    except Exception as exc:
        logger.warning("Urgent providers startup seeding warning: %s", exc)


@app.on_event("startup")
async def on_startup(process_role: runtime_control.ProcessRole = "api", allow_loop_schedule: bool = True) -> None:
    _initialise_sentry()
    ai_service.set_db(db)
    try:
        await asyncio.wait_for(_ensure_indexes(), timeout=10.0)
    except Exception as exc:
        logger.warning("Startup database indexing deferred: %s", exc)

    runtime = runtime_control.resolve_loop_runtime(process_role)
    if _startup_seeds_enabled(process_role):
        try:
            await asyncio.wait_for(_seed_if_empty(), timeout=10.0)
            await asyncio.wait_for(_seed_discovery_if_empty(), timeout=10.0)
            await asyncio.wait_for(_seed_urgent_providers_if_empty(), timeout=10.0)
        except Exception as exc:
            logger.warning("Startup seeding deferred: %s", exc)
    else:
        logger.info(
            "startup seeds skipped: process=%s %s=%s",
            process_role,
            STARTUP_SEEDS_ENV,
            os.environ.get(STARTUP_SEEDS_ENV, "0"),
        )

    # Only the active owner process should execute initial autonomy writes.
    startup_holder = runtime.should_schedule_loops
    if runtime.lease_enabled and startup_holder:
        lease_probe = autonomy.LoopLease(
            db,
            owner_id=runtime.owner_id,
            ttl_s=runtime.lease_ttl_s,
            renew_s=runtime.lease_renew_s,
        )
        try:
            startup_holder = await lease_probe.heartbeat()
        except Exception as exc:
            startup_holder = False
            logger.warning("Startup lease heartbeat probe non-fatal warning: %s", exc)
        if not startup_holder:
            logger.info(
                "initial loop pass skipped: lease not held by owner_id=%s (current_owner=%s)",
                runtime.owner_id,
                lease_probe.last_seen_owner,
            )
    if allow_loop_schedule and startup_holder:
        try:
            await autonomy.recompute_ranking(db)
            await autonomy.update_health(db)
            await _refresh_phase_runtime_records()
        except Exception:  # noqa: BLE001
            logger.exception("initial loop pass failed")
    else:
        logger.info(
            "initial loop pass skipped: process=%s owner=%s allow_loop_schedule=%s",
            runtime.process_role,
            runtime.loop_owner,
            allow_loop_schedule,
        )

    scheduled = 0

    if not allow_loop_schedule:
        logger.info(
            "autonomy startup: process=%s owner=%s source=%s lease=%s scheduled_loops=%s (disabled by caller)",
            runtime.process_role,
            runtime.loop_owner,
            runtime.source,
            runtime.lease_enabled,
            scheduled,
        )
        return

    if _BG_TASKS:
        logger.warning("autonomy startup called with %s existing tasks; rescheduling from clean state", len(_BG_TASKS))
        _cancel_bg_tasks()

    if runtime.should_schedule_loops:
        tasks = autonomy.schedule_all(
            db,
            ai_service,
            owner_id=runtime.owner_id,
            lease_enabled=runtime.lease_enabled,
            lease_ttl_s=runtime.lease_ttl_s,
            lease_renew_s=runtime.lease_renew_s,
        )
        _BG_TASKS.extend(tasks)
        scheduled = max(0, len(tasks) - (1 if runtime.lease_enabled else 0))

    logger.info(
        "autonomy startup: process=%s owner=%s source=%s lease=%s owner_id=%s scheduled_loops=%s",
        runtime.process_role,
        runtime.loop_owner,
        runtime.source,
        runtime.lease_enabled,
        runtime.owner_id,
        scheduled,
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    _cancel_bg_tasks()
    mongo_client.close()
