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
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Header, Request, Query
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pymongo.errors import DuplicateKeyError
from starlette.middleware.cors import CORSMiddleware

from services import ai as ai_service
from services import claim_engine
from services import engine as autonomy
from services import event_contract
from services import follow_up_tokens
from services import fraud as fraud_service
from services import notifications as notifications_service
from services import runtime_control
from services import stripe_billing
from services import suburb_catalogue
from services import suburb_inventory
from services.abr_client import AbrClient
from services.seed import MELBOURNE_TRAINERS

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

TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}
STARTUP_SEEDS_ENV = "ENABLE_STARTUP_SEEDS"

PUBLISH_THRESHOLD = 0.85
HOLD_THRESHOLD = 0.60
ACTIVE_REGION = (os.environ.get("ACTIVE_REGION") or "Greater Melbourne").strip()
ACTIVE_REGIONS = [r.strip() for r in os.environ.get("ACTIVE_REGIONS", ACTIVE_REGION).split(",") if r.strip()]
ACTIVE_REGION_SET = {x.lower() for x in ACTIVE_REGIONS}
BILLABILITY_POLICY = (os.environ.get("BILLABILITY_POLICY") or "allow").strip().lower()
CONTACT_READY_POLICY = (os.environ.get("CONTACT_READY_POLICY") or "allow").strip().lower()

PUBLIC_MONETIZATION_COPY_MODE = (os.environ.get("PUBLIC_MONETIZATION_COPY_MODE") or "flat_subscription").strip()
if PUBLIC_MONETIZATION_COPY_MODE not in {"flat_subscription", "founding_profile_prelaunch", "legacy_intro_fee"}:
    PUBLIC_MONETIZATION_COPY_MODE = "flat_subscription"

PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY = (os.environ.get("PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY") or "1").strip().lower() in TRUTHY_ENV_VALUES
PUBLIC_SHOW_FOUNDING_PROFILE_COPY = (os.environ.get("PUBLIC_SHOW_FOUNDING_PROFILE_COPY") or "0").strip().lower() in TRUTHY_ENV_VALUES

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


def _parse_iso(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


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
        await db.audit_log.insert_one(
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


class FirstLeashLeadIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    user_type: str = Field(min_length=1)
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
    rows = await states_coll.find({"case_id": {"$in": sorted(case_ids)}}, {"_id": 0}).to_list(max(1, len(case_ids)))
    return {str(row.get("case_id") or ""): row for row in rows if row.get("case_id")}


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
) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []

    submissions_coll = getattr(db, "submissions", None)
    held_submissions = await submissions_coll.find(
        {"status": {"$in": ["pending", "held"]}},
        {"_id": 0, "id": 1, "name": 1, "status": 1, "created_at": 1, "confidence_score": 1, "verification_model": 1, "reason": 1, "duplicate": 1},
    ).sort("created_at", -1).limit(50).to_list(50) if submissions_coll is not None and hasattr(submissions_coll, "find") else []
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


@api.post("/match")
async def instant_match(payload: InstantMatchIn) -> Dict[str, Any]:
    """Single input → 3 trainers. The only product surface for end users."""
    if not payload.consent_match_processing:
        raise HTTPException(status_code=400, detail="Consent required to process match request.")

    pool_query: Dict[str, Any] = {"published": True, "region": {"$in": ACTIVE_REGIONS}}
    if payload.suburb:
        pool_query["suburb"] = {"$regex": f"^{payload.suburb}$", "$options": "i"}
    pool = await db.trainers.find(pool_query, {"_id": 0}).to_list(60)
    if not pool:
        pool = await db.trainers.find({"published": True, "region": {"$in": ACTIVE_REGIONS}}, {"_id": 0}).to_list(60)

    matches = await ai_service.match_trainers(payload.description, pool)
    by_id = {t["id"]: t for t in pool}

    selected: List[Dict[str, Any]] = []
    for m in matches:
        t = by_id.get(m["trainer_id"])
        if not t:
            continue
        contact_ready = _has_contact_channel(t)
        if CONTACT_READY_POLICY == "block" and not contact_ready:
            continue
        policy_penalty = 0.0
        if CONTACT_READY_POLICY == "rerank" and not contact_ready:
            policy_penalty += 0.15
        # outcome_score already on the doc; AI provides relevance reason.
        selected.append(
            {
                **t,
                "match_score": m["score"],
                "match_reasoning": m["reasoning"],
                "contact_ready": contact_ready,
                "billable_ready": True,
                "_policy_penalty": policy_penalty,
            }
        )

    # Fit remains the primary score. Commercial tier is consulted only for
    # trainers inside the five-percentage-point comparable-fit band.
    selected = _sort_diagnostic_matches(selected)
    for t in selected:
        t.pop("_policy_penalty", None)
    selected = await _decorate_with_pricing(selected[:3])

    match_id = new_id()
    await db.match_events.insert_one(
        {
            "id": match_id,
            "description": payload.description,
            "suburb": payload.suburb,
            "campaign": (payload.campaign or "").strip(),
            "source": (payload.source or "").strip(),
            "result_ids": [t["id"] for t in selected],
            "created_at": now_iso(),
        }
    )
    return {"match_id": match_id, "matches": [_public_trainer_payload(t, include_match=True) for t in selected]}


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

    ip = (request.client.host if request.client else "") or ""

    # Anti-gaming evaluation. Always record; mark suppressed if suspicious.
    fraud = await fraud_service.evaluate_intro(db, ip, trainer["id"], payload.user_email or "")
    delivery_status = fraud.get("delivery_status") or "delivered"
    fraud_status = fraud.get("fraud_status") or "clear"
    fraud_reasons = fraud.get("reasons") or []

    intro = {
        "id": new_id(),
        "trainer_id": trainer["id"],
        "trainer_name": trainer.get("name"),
        "match_id": payload.match_id,
        "description": payload.description,
        "user_name": payload.user_name or "",
        "user_email": payload.user_email or "",
        "user_phone": payload.user_phone or "",
        "suburb": trainer.get("suburb"),
        "consent_contact_release": True,
        "consent_outcome_tracking": True,
        "delivery_status": delivery_status,
        "status": delivery_status,
        "fraud_status": fraud_status,
        "fraud_reasons": fraud_reasons,
        "ip": ip,
        "user_agent": request.headers.get("user-agent", "")[:200],
        "created_at": now_iso(),
    }
    if payload.match_id:
        match_event = await db.match_events.find_one(
            {"id": payload.match_id},
            {"_id": 0, "campaign": 1, "source": 1, "created_at": 1},
        )
        if match_event:
            intro["campaign"] = (match_event.get("campaign") or "").strip()
            intro["source"] = (match_event.get("source") or "").strip()
            intro["match_created_at"] = match_event.get("created_at")
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
    await _audit(
        "intro",
        trainer["id"],
        after={
            "intro_id": intro["id"],
            "delivery_status": delivery_status,
            "fraud_status": fraud_status,
            "reasons": fraud_reasons,
        },
        actor="user",
    )

    # Notify trainer about the new intro; never block owner experience.
    try:
        notif_meta = await notifications_service.notify_trainer_new_intro(db, trainer, intro)
        if notif_meta:
            await db.intros.update_one({"id": intro["id"]}, {"$set": notif_meta})
            intro.update(notif_meta)
    except Exception:  # noqa: BLE001
        logger.exception("trainer intro notification failed for intro_id=%s", intro.get("id"))

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

    claim_update = await db.trainers.update_one(
        {"id": trainer_id, "claim_status": {"$in": ["", "unclaimed", "pending_verification"]}},
        {"$set": {"claim_status": "claimed", "tier": "claimed", "claimed_at": now.isoformat(), "claim_event_id": event["id"]}},
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
    return _scrub({"ok": True, "trainer_id": trainer_id, "claim_status": "claimed", "tier": "claimed", "session": session})


@api.post("/first-leash")
async def capture_first_leash_lead(payload: FirstLeashLeadIn) -> Dict[str, Any]:
    email_norm = _normalize_email_key(str(payload.email))
    user_type = payload.user_type.strip().lower()
    campaign = (payload.campaign or "").strip()
    source = (payload.source or "").strip()
    utm_medium = (payload.utm_medium or "").strip()
    utm_campaign = (payload.utm_campaign or "").strip()

    if user_type not in ["owner", "trainer"]:
        raise HTTPException(status_code=400, detail="Invalid user type")

    leads_coll = getattr(db, "first_leash_leads", None)
    if leads_coll is None:
        raise HTTPException(status_code=503, detail="Database unready")

    now = datetime.now(timezone.utc)

    existing = await leads_coll.find_one({"email_norm": email_norm})
    if existing:
        return {"status": "exists", "id": str(existing["_id"])}

    doc = {
        "email_norm": email_norm,
        "email_raw": str(payload.email),
        "user_type": user_type,
        "created_at": now,
        "campaign": campaign,
        "source": source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
    }

    res = await leads_coll.insert_one(doc)
    return {"status": "success", "id": str(res.inserted_id)}


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
    if not payload.consent_subscription_billing_terms:
        raise HTTPException(status_code=400, detail="Subscription billing consent is required before checkout.")

    try:
        plan = stripe_billing.subscription_plan(tier=payload.tier, suburb=payload.suburb, interval=payload.interval)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if plan["tier"] == "suburb_sponsor" and not _trainer_serves_suburb(trainer, plan["suburb"]):
        raise HTTPException(status_code=403, detail="Suburb sponsorship must match a suburb served by this profile.")

    reservation: Dict[str, Any] = {}
    if plan["tier"] in {"suburb_sponsor", "citywide"}:
        reservation_result = await suburb_inventory.reserve(
            db,
            trainer_id=trainer_id,
            tier=plan["tier"],
            suburb=plan["suburb"],
            idempotency_key=f"{auth_reference}:{plan['tier']}:{_normalize_suburb_key(plan['suburb']) or 'all'}",
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
        idempotency_key=f"dtd-checkout:{auth_reference}:{plan['tier']}:{_normalize_suburb_key(plan['suburb']) or 'all'}",
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
    page = await db.seo_pages.find_one({"slug": slug}, {"_id": 0})
    if page:
        return page
    parts = slug.split("/")
    suburb = parts[0].replace("-", " ").title()
    category = (parts[1] if len(parts) > 1 else "general").replace("-", " ").lower()
    copy = await ai_service.generate_seo_copy(suburb, category)
    page = {
        "id": new_id(),
        "slug": slug,
        "suburb": suburb,
        "category": category,
        "copy": copy,
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
        }.items()
    }
    message_log = await _message_log_rows()
    ai_degradation_cases = await ai_service.get_ops_degradation_cases(db=db)
    sponsor_inventory_snapshot = await suburb_inventory.ops_snapshot(db)
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
        }.items()
    }
    trainer_inventory = await _trainer_inventory_rows()
    sponsor_inventory_snapshot = await suburb_inventory.ops_snapshot(db)
    message_log = await _message_log_rows()
    supply_geography = await _ops_supply_geography_summary(trainer_inventory, waitlist_summary)
    supply_trends = await _ops_supply_trend_summary(
        trainer_inventory=trainer_inventory,
        submissions_summary=submissions_summary,
        growth_attribution_summary=growth_attribution_summary,
        reactivation_summary=reactivation_summary,
    )
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
        "ops_supply_geography": supply_geography,
        "ops_supply_trends": supply_trends,
        "trainer_inventory": trainer_inventory,
        "sponsor_inventory": sponsor_inventory_snapshot,
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
        },
        "ts": now_iso(),
    })


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
                    or event_status == "incomplete_expired"
                ) and (reservation_id or subscription_id_for_inventory):
                    await suburb_inventory.release_reservation(
                        db,
                        reservation_id=reservation_id,
                        subscription_id="" if reservation_id else subscription_id_for_inventory,
                        reason="cancelled" if event_type.endswith("deleted") else "released",
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
        await db.intros.create_index("stripe_invoice_id", sparse=True)
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
    except Exception as exc:
        logger.warning("Startup database index creation non-fatal warning: %s", exc)


@app.on_event("startup")
async def on_startup(process_role: runtime_control.ProcessRole = "api", allow_loop_schedule: bool = True) -> None:
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
