"""Dog Trainers Directory — pay-on-outcome dog-training match engine.

Design intent:
  - The product is the match, not the directory. There is no browse view.
  - Visibility is earned only through outcome signals (billed intros + tracked outcomes)
    via a Bayesian outcome score recomputed every minute by services.engine.
  - There are no manual approvals. Submissions auto-publish when score ≥ 0.60
    (≥0.85 is marked verified) and auto-hold when < 0.60.
  - Launch monetisation is intro-first: per-intro fee only.
    Conversions are tracked signals by default (bill mode is feature-flagged).
  - The "admin panel" is a single read-only oversight surface; no endpoint in
    here mutates data on a human's behalf.

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
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Header, Request, Query
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pymongo.errors import DuplicateKeyError
from starlette.middleware.cors import CORSMiddleware

from services import ai as ai_service
from services import engine as autonomy
from services import event_contract
from services import fraud as fraud_service
from services import notifications as notifications_service
from services import runtime_control
from services import stripe_billing
from services.seed import MELBOURNE_TRAINERS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ["DB_NAME"]]

app = FastAPI(title="Dog Trainers Directory Match Engine")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dtd")

PUBLISH_THRESHOLD = 0.85
HOLD_THRESHOLD = 0.60
ACTIVE_REGION = (os.environ.get("ACTIVE_REGION") or "Greater Melbourne").strip()
ACTIVE_REGIONS = [r.strip() for r in os.environ.get("ACTIVE_REGIONS", ACTIVE_REGION).split(",") if r.strip()]
ACTIVE_REGION_SET = {x.lower() for x in ACTIVE_REGIONS}
BILLABILITY_POLICY = (os.environ.get("BILLABILITY_POLICY") or "allow").strip().lower()
CONTACT_READY_POLICY = (os.environ.get("CONTACT_READY_POLICY") or "allow").strip().lower()
PUBLIC_MATCHING_ENABLED = (os.environ.get("PUBLIC_MATCHING_ENABLED") or "false").strip().lower() in {"1", "true", "yes", "on"}

PUBLIC_MONETIZATION_COPY_MODE = (os.environ.get("PUBLIC_MONETIZATION_COPY_MODE") or "legacy_intro_fee").strip()
if PUBLIC_MONETIZATION_COPY_MODE not in {"legacy_intro_fee", "founding_profile_prelaunch"}:
    PUBLIC_MONETIZATION_COPY_MODE = "legacy_intro_fee"

PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY = (os.environ.get("PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY") or "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PUBLIC_SHOW_FOUNDING_PROFILE_COPY = (os.environ.get("PUBLIC_SHOW_FOUNDING_PROFILE_COPY") or "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

CLAIM_STATE_MODEL_ENABLED = (os.environ.get("CLAIM_STATE_MODEL_ENABLED") or "0").strip().lower() in {"1", "true", "yes", "on"}
_claim_state_current_env = (os.environ.get("CLAIM_STATE_CURRENT") or "STATE_0").strip().upper()
CLAIM_STATE_CURRENT = _claim_state_current_env if _claim_state_current_env in {"STATE_0", "STATE_1", "STATE_2", "STATE_3", "STATE_4"} else "STATE_0"
CLAIM_ENFORCEMENT_MODE = (os.environ.get("CLAIM_ENFORCEMENT_MODE") or "report_only").strip().lower()
if CLAIM_ENFORCEMENT_MODE not in {"report_only", "block_invalid"}:
    CLAIM_ENFORCEMENT_MODE = "report_only"
CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2 = (
    (os.environ.get("CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2") or "1").strip().lower() in {"1", "true", "yes", "on"}
)
_public_launch_phase_env = (os.environ.get("PUBLIC_LAUNCH_PHASE") or "supply_first").strip().lower()
PUBLIC_LAUNCH_PHASE = (
    _public_launch_phase_env
    if _public_launch_phase_env in {"supply_first", "owner_waitlist", "live_matching", "growth"}
    else "supply_first"
)
TRAINER_ACTION_TOKEN_TTL_S = int((os.environ.get("TRAINER_ACTION_TOKEN_TTL_S") or "1209600").strip() or "1209600")
OVERSIGHT_AUTH_MAX_ATTEMPTS = int((os.environ.get("OVERSIGHT_AUTH_MAX_ATTEMPTS") or "10").strip() or "10")
OVERSIGHT_AUTH_WINDOW_S = int((os.environ.get("OVERSIGHT_AUTH_WINDOW_S") or "600").strip() or "600")
OVERSIGHT_AUTH_LOCK_S = int((os.environ.get("OVERSIGHT_AUTH_LOCK_S") or "900").strip() or "900")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def _scrub(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    return doc


def _require_public_matching(path_label: str) -> None:
    if PUBLIC_MATCHING_ENABLED:
        return
    raise HTTPException(
        status_code=403,
        detail=f"{path_label} is unavailable during education-first prelaunch.",
    )


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
    description: str
    user_email: Optional[EmailStr] = None
    user_name: Optional[str] = None
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
    submitter_email: Optional[EmailStr] = None
    consent_public_listing: bool = False
    consent_information_accuracy: bool = False
    consent_intro_billing_terms: bool = False


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


class FollowUpOutcomeIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: str = "hired"  # hired | still_deciding | need_another_match


class TrainerBillingActionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: Optional[str] = None
    submission_id: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    trainer_action_token: Optional[str] = None


class TrainerReactivateIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: Optional[str] = None
    submission_id: Optional[str] = None
    trainer_action_token: Optional[str] = None


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
    return (trainer.get("billing_profile_status") or "").strip().lower() == "ready"


def _region_allowed(region: Optional[str]) -> bool:
    if not region:
        return False
    return region.strip().lower() in ACTIVE_REGION_SET


def _require_region(region: Optional[str]) -> None:
    if not _region_allowed(region):
        allowed = ", ".join(ACTIVE_REGIONS)
        raise HTTPException(status_code=403, detail=f"Region not in active scope. Active region(s): {allowed}.")


def _normalize_claim_state(raw_state: Optional[str]) -> str:
    token = (raw_state or CLAIM_STATE_CURRENT).strip().upper()
    if token in {"STATE_0", "STATE_1", "STATE_2", "STATE_3", "STATE_4"}:
        return token
    return CLAIM_STATE_CURRENT


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
    if waitlist_coll is None:
        return {
            "total_active": 0,
            "joins_24h": 0,
            "top_suburbs": [],
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
    return {
        "total_active": int(total_active or 0),
        "joins_24h": int(joins_24h or 0),
        "top_suburbs": top_suburbs,
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
    billing = (billing_profile_status or "").strip().lower()
    if status == "held":
        return "held_for_review"
    if status == "pending":
        return "pending_autonomous_review"
    if billing in {"missing_email", "profile_incomplete"}:
        return "needs_billing_profile"
    if billing == "consent_required":
        return "needs_billing_consent"
    if billing in {"stripe_unconfigured", "stripe_error"}:
        return "billing_system_blocked"
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


def _loop_interval_seconds() -> Dict[str, int]:
    return {
        "ranking": autonomy.RANKING_INTERVAL_S,
        "pricing": autonomy.PRICING_INTERVAL_S,
        "verification": autonomy.VERIFICATION_INTERVAL_S,
        "discovery": autonomy.DISCOVERY_INTERVAL_S,
        "inference": autonomy.INFERENCE_INTERVAL_S,
        "health": autonomy.HEALTH_INTERVAL_S,
        "source_ingestion": autonomy.SOURCE_INGEST_INTERVAL_S,
        "outreach": autonomy.OUTREACH_INTERVAL_S,
        "billing_recovery": autonomy.BILLING_RECOVERY_INTERVAL_S,
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


def _claim_policy_snapshot() -> Dict[str, Any]:
    return {
        "enabled": CLAIM_STATE_MODEL_ENABLED,
        "state": CLAIM_STATE_CURRENT,
        "model_enabled": CLAIM_STATE_MODEL_ENABLED,
        "state_current": CLAIM_STATE_CURRENT,
        "enforcement_mode": CLAIM_ENFORCEMENT_MODE,
        "block_melbourne_wide_below_state_2": CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2,
        "melbourne_wide_min_state": "STATE_2" if CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2 else "STATE_0",
    }


def _phase_public_emphasis(*, phase: str, public_matching_enabled: bool) -> str:
    if public_matching_enabled:
        return "live_matching"
    if phase == "growth":
        return "growth_prep"
    if phase == "owner_waitlist":
        return "owner_waitlist"
    return "waitlist_first"


def _default_launch_phase_state() -> Dict[str, Any]:
    current_phase = PUBLIC_LAUNCH_PHASE
    return {
        "key": "launch_phase_state",
        "current_phase": current_phase,
        "matching_exposure_enabled": bool(PUBLIC_MATCHING_ENABLED),
        "public_matching_enabled": bool(PUBLIC_MATCHING_ENABLED),
        "public_emphasis": _phase_public_emphasis(
            phase=current_phase,
            public_matching_enabled=bool(PUBLIC_MATCHING_ENABLED),
        ),
        "trainer_onboarding_open": True,
        "owner_waitlist_mode": "passive_only",
        "evidence_window_mode": "30_day_prelaunch_evidence_window",
        "requires_owner_review_for_phase_change": True,
        "active_regions": list(ACTIVE_REGIONS),
        "updated_at": now_iso(),
        "updated_by": "system",
        "reason": "default_supply_first_prelaunch_lock",
    }


async def _get_or_create_launch_phase_state() -> Dict[str, Any]:
    system_state = getattr(db, "system_state", None)
    default_state = _default_launch_phase_state()
    if system_state is None:
        return default_state

    row = await system_state.find_one({"key": "launch_phase_state"}, {"_id": 0})
    if row:
        state = {**default_state, **row}
        state["matching_exposure_enabled"] = bool(PUBLIC_MATCHING_ENABLED)
        state["public_matching_enabled"] = bool(PUBLIC_MATCHING_ENABLED)
        state["public_emphasis"] = _phase_public_emphasis(
            phase=str(state.get("current_phase") or PUBLIC_LAUNCH_PHASE),
            public_matching_enabled=bool(PUBLIC_MATCHING_ENABLED),
        )
        if state != row:
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

    intro_ready_query = {
        "published": True,
        "billing_profile_status": {
            "$nin": ["missing_email", "profile_incomplete", "consent_required", "stripe_unconfigured", "stripe_error"]
        },
    }
    intro_ready_trainer_count = int(await trainers_coll.count_documents(intro_ready_query))
    held_or_unpublished_count = int(await trainers_coll.count_documents({"published": False}))
    needs_profile_count = int(
        await trainers_coll.count_documents(
            {"billing_profile_status": {"$in": ["missing_email", "profile_incomplete"]}}
        )
    )
    consent_required_count = int(await trainers_coll.count_documents({"billing_profile_status": "consent_required"}))
    billing_system_blocked_count = int(
        await trainers_coll.count_documents(
            {"billing_profile_status": {"$in": ["stripe_unconfigured", "stripe_error"]}}
        )
    )

    blocker_buckets = {
        "held_or_unpublished": held_or_unpublished_count,
        "needs_billing_profile": needs_profile_count,
        "needs_billing_consent": consent_required_count,
        "billing_system_blocked": billing_system_blocked_count,
    }
    blocked_trainer_count = sum(blocker_buckets.values())
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
        "matching_exposure_enabled": bool(PUBLIC_MATCHING_ENABLED),
        "public_emphasis": phase_state.get("public_emphasis") or _phase_public_emphasis(
            phase=str(phase_state.get("current_phase") or PUBLIC_LAUNCH_PHASE),
            public_matching_enabled=bool(PUBLIC_MATCHING_ENABLED),
        ),
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
        "public_matching_enabled": bool(PUBLIC_MATCHING_ENABLED),
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


def _evaluate_claim_local(claim: str, state: str) -> Dict[str, Any]:
    claim_norm = " ".join((claim or "").strip().lower().replace("_", " ").replace("-", " ").split())
    is_melbourne_wide = claim_norm in {"melbourne wide", "all melbourne", "greater melbourne wide"}
    blocks_melbourne_wide = (
        CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2
        and is_melbourne_wide
        and state in {"STATE_0", "STATE_1"}
    )
    reason_codes: List[str] = []
    if is_melbourne_wide:
        reason_codes.append("claim.melbourne_wide_detected")
    if blocks_melbourne_wide:
        reason_codes.append("claim.melbourne_wide_requires_state_2")
    return {
        "allowed": not blocks_melbourne_wide,
        "reason_codes": reason_codes,
        "normalized_claim": claim_norm,
        "normalized_state": state,
    }


async def _evaluate_claim(claim: str, state: str) -> Dict[str, Any]:
    fallback = _evaluate_claim_local(claim, state)
    try:
        from services import claim_state as claim_state_service
    except Exception:  # noqa: BLE001
        return {**fallback, "source": "server_local_fallback", "service_available": False}

    evaluator = getattr(claim_state_service, "evaluate_claim", None)
    if not callable(evaluator):
        return {**fallback, "source": "server_local_fallback", "service_available": False}

    try:
        result = evaluator(
            claim=claim,
            state=state,
            enforcement_mode=CLAIM_ENFORCEMENT_MODE,
            block_melbourne_wide_below_state_2=CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2,
            enabled=CLAIM_STATE_MODEL_ENABLED,
        )
        if asyncio.iscoroutine(result):
            result = await result
        if not isinstance(result, dict):
            return {**fallback, "source": "server_local_fallback", "service_available": True}
    except TypeError:
        try:
            result = evaluator(claim, state)
            if asyncio.iscoroutine(result):
                result = await result
            if not isinstance(result, dict):
                return {**fallback, "source": "server_local_fallback", "service_available": True}
        except Exception:  # noqa: BLE001
            return {**fallback, "source": "server_local_fallback", "service_available": True}
    except Exception:  # noqa: BLE001
        return {**fallback, "source": "server_local_fallback", "service_available": True}

    return {
        "allowed": bool(result.get("allowed", fallback["allowed"])),
        "reason_codes": list(result.get("reason_codes", fallback["reason_codes"])),
        "normalized_claim": str(result.get("normalized_claim", fallback["normalized_claim"])),
        "normalized_state": str(result.get("normalized_state", result.get("state", fallback["normalized_state"]))),
        "source": "services.claim_state",
        "service_available": True,
    }


async def _decorate_with_pricing(trainers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach the current intro fee snapshot for each trainer's suburb."""
    suburbs = list({t.get("suburb") for t in trainers if t.get("suburb")})
    pricing = await db.pricing_state.find({"suburb": {"$in": suburbs}}, {"_id": 0}).to_list(500)
    by_suburb = {p["suburb"]: p for p in pricing}
    for t in trainers:
        ps = by_suburb.get(t.get("suburb"))
        t["intro_fee_cents"] = int(ps["intro_fee_cents"]) if ps else autonomy.FIXED_INTRO_FEE_CENTS
        t["demand_multiplier"] = float(ps["multiplier"]) if ps else 1.0
        t["intro_fee_mode"] = str((ps or {}).get("pricing_mode") or "fixed")
    return trainers


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


@api.get("/config")
async def config() -> Dict[str, Any]:
    """Lightweight config the frontend can render without auth."""
    suburbs = sorted([s for s in await db.trainers.distinct("suburb", {"published": True, "region": {"$in": ACTIVE_REGIONS}}) if s])
    phase_state = await _get_or_create_launch_phase_state()
    return {
        "base_intro_fee_cents": autonomy.FIXED_INTRO_FEE_CENTS,
        "fixed_intro_fee_cents": autonomy.FIXED_INTRO_FEE_CENTS,
        "trainer_free_intro_days": stripe_billing.trainer_free_intro_days(),
        "base_conversion_fee_cents": autonomy.BASE_CONVERSION_FEE,
        "active_regions": ACTIVE_REGIONS,
        "active_region_default": ACTIVE_REGION,
        "conversion_billing_mode": autonomy.CONVERSION_BILLING_MODE,
        "stripe_intro_billing_enabled": stripe_billing.billing_enabled(),
        "stripe_webhook_enabled": stripe_billing.webhook_enabled(),
        "public_matching_enabled": PUBLIC_MATCHING_ENABLED,
        "public_launch_phase": phase_state.get("current_phase"),
        "public_emphasis": phase_state.get("public_emphasis"),
        "trainer_onboarding_open": bool(phase_state.get("trainer_onboarding_open", True)),
        "owner_waitlist_mode": phase_state.get("owner_waitlist_mode"),
        "public_monetization_copy_mode": PUBLIC_MONETIZATION_COPY_MODE,
        "public_hide_legacy_intro_fee_copy": PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY,
        "public_show_founding_profile_copy": PUBLIC_SHOW_FOUNDING_PROFILE_COPY,
        "claim_state_model_enabled": CLAIM_STATE_MODEL_ENABLED,
        "claim_state_current": CLAIM_STATE_CURRENT,
        "claim_enforcement_mode": CLAIM_ENFORCEMENT_MODE,
        "claim_block_melbourne_wide_below_state_2": CLAIM_BLOCK_MELBOURNE_WIDE_BELOW_STATE_2,
        "suburbs": suburbs,
    }


@api.post("/match")
async def instant_match(payload: InstantMatchIn) -> Dict[str, Any]:
    """Single input → 3 trainers. The only product surface for end users."""
    _require_public_matching("Public matching")
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
        billable_ready = _is_billable_ready(t)
        if CONTACT_READY_POLICY == "block" and not contact_ready:
            continue
        if BILLABILITY_POLICY == "block" and not billable_ready:
            continue
        policy_penalty = 0.0
        if CONTACT_READY_POLICY == "rerank" and not contact_ready:
            policy_penalty += 0.15
        if BILLABILITY_POLICY == "rerank" and not billable_ready:
            policy_penalty += 0.20
        # outcome_score already on the doc; AI provides relevance reason.
        selected.append(
            {
                **t,
                "match_score": m["score"],
                "match_reasoning": m["reasoning"],
                "contact_ready": contact_ready,
                "billable_ready": billable_ready,
                "_policy_penalty": policy_penalty,
            }
        )

    # Final sort = AI relevance × outcome score. AI relevance is the primary
    # signal; outcome is the tiebreaker / cold-start dampener.
    selected.sort(
        key=lambda t: ((t.get("match_score", 0) * 0.7) + (t.get("outcome_score", 0.05) * 0.3) - t.get("_policy_penalty", 0.0)),
        reverse=True,
    )
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
    return {"match_id": match_id, "matches": selected}


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


@api.get("/trainers/{trainer_id}")
async def get_trainer(trainer_id: str) -> Dict[str, Any]:
    doc = await db.trainers.find_one({"id": trainer_id, "published": True, "region": {"$in": ACTIVE_REGIONS}}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    decorated = await _decorate_with_pricing([doc])
    return decorated[0]


@api.post("/intros")
async def create_intro(
    payload: IntroIn,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Dict[str, Any]:
    _require_public_matching("Public contact release")
    if not payload.consent_contact_release or not payload.consent_outcome_tracking:
        raise HTTPException(status_code=400, detail="Consent required before contact release.")
    trainer = await db.trainers.find_one({"id": payload.trainer_id, "published": True}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    _require_region(trainer.get("region"))

    idem = (idempotency_key or payload.client_token or "").strip()
    if idem:
        existing = await db.intros.find_one({"idempotency_key": idem}, {"_id": 0})
        if existing:
            existing_trainer = await db.trainers.find_one({"id": existing["trainer_id"]}, {"_id": 0})
            contact_existing = {
                "name": existing_trainer.get("name") if existing_trainer else existing.get("trainer_name"),
                "website": existing_trainer.get("website") if existing_trainer else None,
                "phone": existing_trainer.get("phone") if existing_trainer else None,
                "email": existing_trainer.get("email") if existing_trainer else None,
                "suburb": existing_trainer.get("suburb") if existing_trainer else existing.get("suburb"),
            }
            return _scrub({**existing, "contact": contact_existing})

    fee = await autonomy.get_intro_fee(db, trainer.get("suburb"))
    ip = (request.client.host if request.client else "") or ""

    # Anti-gaming evaluation. Always record; sometimes mark suppressed.
    fraud = await fraud_service.evaluate_intro(db, ip, trainer["id"], payload.user_email or "")

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
        "intro_fee_cents": fee if fraud["billing_status"] == "billed" else 0,
        "billing_status": fraud["billing_status"],
        "fraud_reasons": fraud["reasons"],
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
                existing_trainer = await db.trainers.find_one({"id": existing["trainer_id"]}, {"_id": 0})
                contact_existing = {
                    "name": existing_trainer.get("name") if existing_trainer else existing.get("trainer_name"),
                    "website": existing_trainer.get("website") if existing_trainer else None,
                    "phone": existing_trainer.get("phone") if existing_trainer else None,
                    "email": existing_trainer.get("email") if existing_trainer else None,
                    "suburb": existing_trainer.get("suburb") if existing_trainer else existing.get("suburb"),
                }
                return _scrub({**existing, "contact": contact_existing})
        raise
    await _audit("intro", trainer["id"], after={"intro_id": intro["id"], "billing_status": fraud["billing_status"], "reasons": fraud["reasons"]}, actor="user")

    # Bill the trainer side in Stripe (fail-soft). User-facing connect flow must
    # continue even when billing infrastructure is unavailable.
    billing_meta = await stripe_billing.bill_intro(db, trainer, intro)
    if billing_meta:
        await db.intros.update_one({"id": intro["id"]}, {"$set": billing_meta})
        intro.update(billing_meta)

    # Notify trainer about the new intro; never block owner experience.
    try:
        notif_meta = await notifications_service.notify_trainer_new_intro(db, trainer, intro)
        if notif_meta:
            await db.intros.update_one({"id": intro["id"]}, {"$set": notif_meta})
            intro.update(notif_meta)
    except Exception:  # noqa: BLE001
        logger.exception("trainer intro notification failed for intro_id=%s", intro.get("id"))

    contact = {
        "name": trainer.get("name"),
        "website": trainer.get("website"),
        "phone": trainer.get("phone"),
        "email": trainer.get("email"),
        "suburb": trainer.get("suburb"),
    }
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
        target_status = "billed" if autonomy.CONVERSION_BILLING_MODE == "bill" else "pending"
        await db.conversions.insert_one(
            {
                "id": new_id(),
                "intro_id": payload.intro_id,
                "trainer_id": intro["trainer_id"],
                "match_id": intro.get("match_id"),
                "campaign": intro.get("campaign", ""),
                "attribution_source": intro.get("source", ""),
                "fee_cents": autonomy.BASE_CONVERSION_FEE if target_status == "billed" else 0,
                "billing_status": target_status,
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
        return {"ok": True, "billed": False}
    existing = await db.conversions.find_one(
        {"intro_id": payload.intro_id, "billing_status": {"$in": ["tracked", "billed", "suspicious"]}},
        {"_id": 0},
    )
    if existing:
        return {"ok": True, "billed": False, "existing": True, "billing_status": existing.get("billing_status")}

    decision = await fraud_service.evaluate_conversion(db, intro)
    if decision["billing_status"] == "suspicious":
        status = "suspicious"
    elif autonomy.CONVERSION_BILLING_MODE == "bill":
        status = "billed"
    else:
        status = "tracked"

    conv = {
        "id": new_id(),
        "intro_id": payload.intro_id,
        "trainer_id": intro["trainer_id"],
        "match_id": intro.get("match_id"),
        "campaign": intro.get("campaign", ""),
        "attribution_source": intro.get("source", ""),
        "fee_cents": autonomy.BASE_CONVERSION_FEE if status == "billed" else 0,
        "billing_status": status,
        "fraud_reason": decision["reason"],
        "inferred": False,
        "confidence": 1.0,
        "source": "manual_confirm",
        "created_at": now_iso(),
        "billed_at": now_iso() if status == "billed" else None,
    }
    # If a prior pending inferred conversion exists, supersede it.
    await db.conversions.update_many(
        {"intro_id": payload.intro_id, "billing_status": "pending"},
        {"$set": {"billing_status": "superseded"}},
    )
    await db.conversions.insert_one(conv.copy())
    await _audit("conversion", intro["trainer_id"], after={"intro_id": payload.intro_id, "billing_status": conv["billing_status"]}, actor="user")
    return _scrub({**conv, "billed": status == "billed"})


@api.get("/follow-up/{token}")
async def get_follow_up(token: str) -> Dict[str, Any]:
    intro = await db.intros.find_one({"id": token}, {"_id": 0})
    if not intro:
        raise HTTPException(status_code=404, detail="Follow-up link invalid or expired.")

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
    intro = await db.intros.find_one({"id": token}, {"_id": 0})
    if not intro:
        raise HTTPException(status_code=404, detail="Follow-up link invalid or expired.")

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
    """Public endpoint to feed the autonomous ingestion queue.

    Anyone (or any external scraper) can post candidate URLs.  The discovery
    loop deduplicates, scores, and decides — no human review.
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
    """Submit a real Melbourne trainer. Auto-publishes if AI score ≥ 0.60."""
    if not payload.consent_public_listing or not payload.consent_information_accuracy:
        raise HTTPException(status_code=400, detail="Consent required for public listing.")

    sub = payload.model_dump()
    sub["region"] = (sub.get("region") or ACTIVE_REGION).strip() or ACTIVE_REGION
    # Preserve explicit submitter email when provided; otherwise fall back to
    # the listing email so status notifications are still deliverable.
    sub["submitter_email"] = (sub.get("submitter_email") or sub.get("email") or "").strip()
    _require_region(sub["region"])
    score = await ai_service.score_trainer(_verification_payload(sub))
    conf = float(score["confidence"])
    status = ai_service.status_for_score(conf)

    sub_doc = {
        "id": new_id(),
        "status": "pending",
        "created_at": now_iso(),
        "confidence_score": conf,
        "verification_reasoning": score.get("reasoning", ""),
        "verification_signals": score.get("signals", []),
        "verification_model": score.get("model", "heuristic"),
        **sub,
    }

    auto_action: str
    trainer_id: Optional[str] = None
    if conf >= PUBLISH_THRESHOLD:
        auto_action = "auto_published"
    elif conf >= HOLD_THRESHOLD:
        auto_action = "auto_published_unverified"
    else:
        auto_action = "auto_held"

    if conf >= HOLD_THRESHOLD:
        # Insert a published trainer immediately — no human in the loop.
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
            "confidence_score": conf,
            "verification_status": status,
            "verification_reasoning": score.get("reasoning", ""),
            "verification_signals": score.get("signals", []),
            "verification_model": score.get("model", "heuristic"),
            "verified_at": now_iso(),
            "outcome_score": 0.05,
            "intros_30d": 0,
            "conversions_30d": 0,
            "published": True,
            "contact_ready": bool(sub.get("website") or sub.get("phone") or sub.get("email")),
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
        sub_doc["status"] = "published"
        sub_doc["trainer_id"] = trainer_id
        sub_doc["billing_profile_status"] = billing_profile.get("billing_profile_status")
        sub_doc["trainer_action_token"] = trainer_action_token
    else:
        sub_doc["status"] = "held"

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

    await _audit(auto_action, sub_doc["id"], after={"confidence": conf, "trainer_id": trainer_id}, actor="system")
    return _scrub(
        {
            "id": sub_doc["id"],
            "status": sub_doc["status"],
            "confidence_score": conf,
            "verification_status": status,
            "verification_reasoning": sub_doc["verification_reasoning"],
            "verification_signals": sub_doc["verification_signals"],
            "trainer_id": trainer_id,
            "billing_profile_status": sub_doc.get("billing_profile_status"),
            "submitter_notification_status": sub_doc.get("submitter_notification_status"),
            "trainer_action_token": sub_doc.get("trainer_action_token"),
        }
    )


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
) -> Dict[str, Any]:
    trainer = await _resolve_trainer(trainer_id=trainer_id, submission_id=submission_id)
    sub = await _resolve_submission(submission_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer context not found.")
    _require_trainer_action_token(
        token=trainer_action_token,
        trainer_id=str(trainer.get("id") or ""),
        submission_id=submission_id,
    )

    intros = await db.intros.find(
        {"trainer_id": trainer.get("id")},
        {"_id": 0, "intro_fee_cents": 1, "billing_collection_status": 1, "billing_retry_state": 1},
    ).to_list(1000)
    statuses: Dict[str, int] = {}
    billed_total_cents = 0
    retry_states: Dict[str, int] = {}
    for intro in intros:
        status = str(intro.get("billing_collection_status") or "not_billable")
        statuses[status] = statuses.get(status, 0) + 1
        billed_total_cents += int(intro.get("intro_fee_cents") or 0)
        retry_state = str(intro.get("billing_retry_state") or "")
        if retry_state:
            retry_states[retry_state] = retry_states.get(retry_state, 0) + 1

    issues = {
        "profile_incomplete": str(trainer.get("billing_profile_status") or "") in {"missing_email", "profile_incomplete"},
        "consent_required": str(trainer.get("billing_profile_status") or "") == "consent_required",
        "stripe_unconfigured": str(trainer.get("billing_profile_status") or "") in {"stripe_unconfigured", "stripe_error"},
        "payment_failed_or_disputed": (statuses.get("payment_failed", 0) + statuses.get("disputed", 0) + statuses.get("uncollectible", 0)) > 0,
    }
    try:
        max_attempts = max(1, int(os.environ.get("BILLING_RETRY_MAX_ATTEMPTS", "3")))
    except ValueError:
        max_attempts = 3
    try:
        base_delay_hours = max(1, int(os.environ.get("BILLING_RETRY_BASE_DELAY_HOURS", "24")))
    except ValueError:
        base_delay_hours = 24
    return {
        "trainer": {
            "id": trainer.get("id"),
            "name": trainer.get("name"),
            "billing_email": trainer.get("billing_email") or trainer.get("email"),
            "billing_profile_status": trainer.get("billing_profile_status") or (sub or {}).get("billing_profile_status") or "unknown",
            "stripe_customer_id": trainer.get("stripe_customer_id"),
        },
        "submission_id": (sub or {}).get("id"),
        "status_counts": statuses,
        "retry_state_counts": retry_states,
        "retry_policy": {
            "max_attempts": max_attempts,
            "base_delay_hours": base_delay_hours,
        },
        "billed_total_cents": billed_total_cents,
        "issues": issues,
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
    status = ai_service.status_for_score(conf)
    published = conf >= HOLD_THRESHOLD
    await db.trainers.update_one(
        {"id": trainer["id"]},
        {"$set": {
            "confidence_score": conf,
            "verification_status": status,
            "verification_reasoning": score.get("reasoning", ""),
            "verification_signals": score.get("signals", []),
            "verification_model": score.get("model", "heuristic"),
            "verified_at": now_iso(),
            "published": published,
        }},
    )
    await _audit("trainer_reactivate", trainer["id"], after={"published": published, "confidence_score": conf}, actor="user")
    return {"ok": True, "trainer_id": trainer["id"], "published": published, "confidence_score": conf, "verification_status": status}


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
# Oversight — read-only surface; no mutations.
# ---------------------------------------------------------------------------


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


@api.get("/oversight")
async def oversight(_: None = Depends(require_oversight)) -> Dict[str, Any]:
    """Single read-only snapshot. No buttons. No actions. Just the truth."""
    phase_runtime = await _refresh_phase_runtime_records()
    phase_state = phase_runtime["phase_state"]
    readiness_snapshot = phase_runtime["readiness_snapshot"]
    phase_decisions = phase_runtime["phase_decisions"]
    conversion_statuses = autonomy.confirmed_conversion_statuses()
    intros_24 = await db.intros.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}, "billing_status": "billed"})
    intros_7d = await db.intros.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}, "billing_status": "billed"})
    conv_24 = await db.conversions.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}, "billing_status": {"$in": conversion_statuses}})
    conv_7d = await db.conversions.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}, "billing_status": {"$in": conversion_statuses}})

    intros = await db.intros.find({"billing_status": "billed"}, {"_id": 0}).to_list(2000)
    conversions = await db.conversions.find({"billing_status": {"$in": conversion_statuses}}, {"_id": 0}).to_list(2000)
    suppressed = await db.intros.count_documents({"billing_status": "suppressed"})
    suspicious_conv = await db.conversions.count_documents({"billing_status": "suspicious"})
    inferred_pending = await db.conversions.count_documents({"inferred": True, "billing_status": "pending"})
    engagements_total = await db.engagements.count_documents({})

    billing_status_defaults = {
        "invoice_sent": 0,
        "invoice_finalized": 0,
        "paid": 0,
        "trial_free": 0,
        "payment_failed": 0,
        "uncollectible": 0,
        "waived": 0,
        "refunded": 0,
        "disputed": 0,
        "dispute_resolved": 0,
        "profile_incomplete": 0,
        "consent_required": 0,
        "stripe_unconfigured": 0,
        "invoice_error": 0,
        "not_billable": 0,
    }
    billing_rows = await db.intros.aggregate(
        [
            {"$match": {"billing_collection_status": {"$exists": True}}},
            {"$group": {"_id": "$billing_collection_status", "n": {"$sum": 1}}},
        ]
    ).to_list(100)
    billing_summary = dict(billing_status_defaults)
    for row in billing_rows:
        k = str(row.get("_id") or "")
        if not k:
            continue
        billing_summary[k] = int(row.get("n") or 0)

    non_billable_causes = {
        "trial_free": billing_summary.get("trial_free", 0),
        "profile_incomplete": billing_summary.get("profile_incomplete", 0),
        "consent_required": billing_summary.get("consent_required", 0),
        "stripe_unconfigured": billing_summary.get("stripe_unconfigured", 0),
        "invoice_error": billing_summary.get("invoice_error", 0),
    }

    notification_summary = {
        "trainer_intro_sent": await db.intros.count_documents({"trainer_notification_status": "sent"}),
        "trainer_intro_failed": await db.intros.count_documents({"trainer_notification_status": "failed"}),
        "trainer_intro_skipped": await db.intros.count_documents({"trainer_notification_status": "skipped"}),
        "submission_sent": await db.submissions.count_documents({"submitter_notification_status": "sent"}),
        "submission_failed": await db.submissions.count_documents({"submitter_notification_status": "failed"}),
        "submission_skipped": await db.submissions.count_documents({"submitter_notification_status": "skipped"}),
    }

    revenue_intro_cents = sum(i.get("intro_fee_cents", 0) for i in intros)
    revenue_conv_cents = sum(c.get("fee_cents", 0) for c in conversions)
    revenue_total_cents = revenue_intro_cents + revenue_conv_cents
    collected_statuses = {"paid", "dispute_resolved"}
    at_risk_statuses = {
        "payment_failed",
        "uncollectible",
        "disputed",
        "invoice_error",
        "profile_incomplete",
        "consent_required",
        "stripe_unconfigured",
    }
    collected_intro_cents = sum(
        int(i.get("intro_fee_cents", 0) or 0)
        for i in intros
        if str(i.get("billing_collection_status") or "") in collected_statuses
    )
    at_risk_intro_cents = sum(
        int(i.get("intro_fee_cents", 0) or 0)
        for i in intros
        if str(i.get("billing_collection_status") or "") in at_risk_statuses
    )
    booked_revenue_cents = revenue_total_cents
    collected_revenue_cents = collected_intro_cents
    at_risk_revenue_cents = at_risk_intro_cents

    intros_total = max(1, len(intros))
    intro_to_conv = round(len(conversions) / intros_total, 3)

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

    pricing_state = await db.pricing_state.find({}, {"_id": 0}).sort("suburb", 1).to_list(200)

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
    source_ingestion_state_rows = await source_ingestion_state_coll.find({}, {"_id": 0}).to_list(20) if source_ingestion_state_coll is not None else []
    source_ingestion_state_rows.sort(
        key=lambda row: (
            int(row.get("consecutive_failures") or 0),
            str(row.get("suppressed_until") or ""),
            str(row.get("source_url") or ""),
        ),
        reverse=True,
    )
    billing_recovery_cases = await db.intros.find(
        {
            "billing_status": "billed",
            "billing_retry_state": {"$in": ["retry_exhausted", "retry_failed", "needs_remediation", "retry_sent"]},
        },
        {
            "_id": 0,
            "id": 1,
            "trainer_id": 1,
            "billing_collection_status": 1,
            "billing_retry_state": 1,
            "billing_retry_attempts": 1,
            "billing_last_retry_at": 1,
            "intro_fee_cents": 1,
            "created_at": 1,
        },
    ).to_list(20)
    trainer_ids_for_cases = sorted({str(row.get("trainer_id") or "") for row in billing_recovery_cases if row.get("trainer_id")})
    trainer_rows = await db.trainers.find(
        {"id": {"$in": trainer_ids_for_cases}},
        {"_id": 0, "id": 1, "name": 1, "billing_profile_status": 1, "published": 1, "confidence_score": 1},
    ).to_list(max(1, len(trainer_ids_for_cases))) if trainer_ids_for_cases else []
    trainers_by_id = {str(row.get("id") or ""): row for row in trainer_rows}
    billing_recovery_case_rows = []
    for row in billing_recovery_cases:
        trainer = trainers_by_id.get(str(row.get("trainer_id") or ""), {})
        trainer_id = str(row.get("trainer_id") or "")
        billing_recovery_case_rows.append(
            {
                "intro_id": row.get("id"),
                "trainer_id": trainer_id,
                "trainer_name": trainer.get("name") or trainer_id or "unknown",
                "billing_collection_status": row.get("billing_collection_status") or "unknown",
                "billing_retry_state": row.get("billing_retry_state") or "unknown",
                "billing_retry_attempts": int(row.get("billing_retry_attempts") or 0),
                "billing_last_retry_at": row.get("billing_last_retry_at"),
                "billing_profile_status": trainer.get("billing_profile_status") or "unknown",
                "intro_fee_cents": int(row.get("intro_fee_cents") or 0),
                "created_at": row.get("created_at"),
                "trainer_action_token": _issue_trainer_action_token(trainer_id=trainer_id) if trainer_id else None,
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

    return {
        "revenue": {
            "booked_revenue_cents": booked_revenue_cents,
            "collected_revenue_cents": collected_revenue_cents,
            "at_risk_revenue_cents": at_risk_revenue_cents,
            "booked_intro_cents": revenue_intro_cents,
            "booked_conversion_cents": revenue_conv_cents,
            "collected_intro_cents": collected_intro_cents,
            "at_risk_intro_cents": at_risk_intro_cents,
            "intro_cents": revenue_intro_cents,
            "conversion_cents": revenue_conv_cents,
            "total_cents": revenue_total_cents,
            "conversion_billing_mode": autonomy.CONVERSION_BILLING_MODE,
        },
        "throughput": {
            "intros_24h": intros_24,
            "intros_7d": intros_7d,
            "conversions_24h": conv_24,
            "conversions_7d": conv_7d,
            "intro_to_conversion_rate": intro_to_conv,
            "engagements_total": engagements_total,
        },
        "trust": {
            "intros_suppressed": suppressed,
            "conversions_suspicious": suspicious_conv,
            "inferred_pending": inferred_pending,
        },
        "loops": {
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
        },
        "alerts": health.get("alerts", []),
        "rollback_recent": rollback_recent,
        "pricing_state": pricing_state,
        "top_trainers": top_trainers,
        "audit_recent": audit_recent,
        "submissions_summary": submissions_summary,
        "discovery_summary": discovery_summary,
        "billing_summary": billing_summary,
        "non_billable_causes": non_billable_causes,
        "notification_summary": notification_summary,
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
        "ops_investigation": {
            "loop_statuses": loop_statuses,
            "billing_recovery_cases": billing_recovery_case_rows,
            "reactivation_cases": reactivation_case_rows,
            "source_ingestion_sources": source_ingestion_state_rows,
            "discovery_alerts": discovery_alerts,
        },
        "ts": now_iso(),
    }


@api.get("/claims/validate")
async def validate_claim(
    claim: str = Query(..., min_length=1),
    state: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Read-only deterministic claim validation. Never mutates state."""
    effective_state = _normalize_claim_state(state)
    evaluation = await _evaluate_claim(claim, effective_state)
    claim_policy = _claim_policy_snapshot()

    allowed = bool(evaluation.get("allowed", False))
    would_block = bool(CLAIM_STATE_MODEL_ENABLED and not allowed)
    if CLAIM_ENFORCEMENT_MODE == "block_invalid" and would_block:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "claim_blocked",
                "claim": claim,
                "state": effective_state,
                "reason_codes": evaluation.get("reason_codes", []),
            },
        )

    return {
        "ok": True,
        "claim": claim,
        "state": effective_state,
        "allowed": allowed,
        "would_block": would_block,
        "enforced": CLAIM_ENFORCEMENT_MODE == "block_invalid",
        "enforcement_mode": CLAIM_ENFORCEMENT_MODE,
        "reason_codes": evaluation.get("reason_codes", []),
        "normalized_claim": evaluation.get("normalized_claim"),
        "evaluation_source": evaluation.get("source"),
        "service_available": evaluation.get("service_available"),
        "claim_policy": claim_policy,
        "ts": now_iso(),
    }


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
    if event_id:
        try:
            await db.stripe_events.insert_one(
                {
                    "id": event_id,
                    "type": event_type,
                    "invoice_id": invoice_id,
                    "status": "processing",
                    "created_at": now_iso(),
                }
            )
        except DuplicateKeyError:
            return {"ok": True, "duplicate": True}

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
            {"$set": {"status": "processed", "processed_at": now_iso()}},
        )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
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
    logger.info("Empty trainer collection — seeding %s real Melbourne trainers", len(MELBOURNE_TRAINERS))
    for entry in MELBOURNE_TRAINERS:
        doc = {
            "id": new_id(),
            "verification_status": "pending",
            "published": False,
            "contact_ready": bool(entry.get("website") or entry.get("phone") or entry.get("email")),
            "outcome_score": 0.05,
            "intros_30d": 0,
            "conversions_30d": 0,
            "created_at": now_iso(),
            **entry,
        }
        # remove the legacy 'tier' field — visibility is no longer tier-driven
        doc.pop("tier", None)
        await db.trainers.insert_one(doc.copy())
        try:
            score = await ai_service.score_trainer(_verification_payload(doc))
            conf = float(score["confidence"])
            status = ai_service.status_for_score(conf)
            await db.trainers.update_one(
                {"id": doc["id"]},
                {
                    "$set": {
                        "confidence_score": conf,
                        "verification_status": status,
                        "verification_reasoning": score.get("reasoning", ""),
                        "verification_signals": score.get("signals", []),
                        "verification_model": score.get("model", "heuristic"),
                        "verified_at": now_iso(),
                        "published": conf >= HOLD_THRESHOLD,
                    }
                },
            )
        except Exception:  # noqa: BLE001
            logger.exception("seed verify failed for %s", entry.get("name"))


async def _seed_discovery_if_empty() -> None:
    """Seed a small starter set of public discovery URLs so the autonomous
    ingestion loop has something to crank on out-of-the-box.
    """
    if await db.discovery_queue.count_documents({}) > 0:
        return
    candidates = [
        {
            "url": "https://urbanpawsmelbourne.com.au",
            "hint_name": "Urban Paws Melbourne",
            "hint_suburb": "Melbourne",
            "hint_bio": "Melbourne dog training and behaviour services.",
            "source": "discovery_seed",
        },
        {
            "url": "https://www.dogforce1.com.au",
            "hint_name": "Dog Force 1",
            "hint_suburb": "Melbourne",
            "hint_bio": "Melbourne dog training franchise focusing on behaviour.",
            "source": "discovery_seed",
        },
        {
            "url": "https://www.melbournek9.com.au",
            "hint_name": "Melbourne K9 Force",
            "hint_suburb": "Melbourne",
            "hint_bio": "Specialist behaviour modification and obedience training in Melbourne.",
            "source": "discovery_seed",
        },
    ]
    for c in candidates:
        await db.discovery_queue.insert_one(
            {"id": new_id(), "status": "pending", "created_at": now_iso(), **c}
        )
    logger.info("seeded %s discovery URLs", len(candidates))


def _cancel_bg_tasks() -> None:
    for task in _BG_TASKS:
        task.cancel()
    _BG_TASKS.clear()


@app.on_event("startup")
async def on_startup(process_role: runtime_control.ProcessRole = "api", allow_loop_schedule: bool = True) -> None:
    await db.trainers.create_index("id", unique=True, sparse=True)
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
    await db.trainers.create_index("stripe_customer_id", sparse=True)
    await db.stripe_events.create_index("id", unique=True, sparse=True)
    await db.config_snapshots.create_index("applied_at")
    await db.outreach_events.create_index([("intro_id", 1), ("kind", 1)], unique=True)
    await db.notification_events.create_index("id", unique=True, sparse=True)
    await db.auth_attempts.create_index("key", unique=True)
    await db.auth_attempts.create_index("updated_at")
    await db.phase_readiness_snapshots.create_index("snapshot_kind", unique=True)
    await db.phase_transition_decisions.create_index("id", unique=True, sparse=True)
    await db.phase_transition_decisions.create_index("decided_at")
    await db.owner_waitlist.create_index([("email_norm", 1), ("suburb_norm", 1), ("status", 1)], unique=True)
    await db.owner_waitlist.create_index([("status", 1), ("created_at", -1)])
    await db.owner_waitlist_events.create_index("id", unique=True, sparse=True)
    await db.owner_waitlist_events.create_index([("event_type", 1), ("created_at", -1)])

    runtime = runtime_control.resolve_loop_runtime(process_role)
    await _seed_if_empty()
    await _seed_discovery_if_empty()

    # Only the active owner process should execute initial autonomy writes.
    startup_holder = runtime.should_schedule_loops
    if runtime.lease_enabled and startup_holder:
        lease_probe = autonomy.LoopLease(
            db,
            owner_id=runtime.owner_id,
            ttl_s=runtime.lease_ttl_s,
            renew_s=runtime.lease_renew_s,
        )
        startup_holder = await lease_probe.heartbeat()
        if not startup_holder:
            logger.info(
                "initial loop pass skipped: lease not held by owner_id=%s (current_owner=%s)",
                runtime.owner_id,
                lease_probe.last_seen_owner,
            )
    if allow_loop_schedule and startup_holder:
        try:
            await autonomy.recompute_ranking(db)
            await autonomy.recompute_pricing(db)
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
