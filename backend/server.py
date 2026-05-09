"""Bark&Bond — pay-on-outcome dog-training match engine.

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
from starlette.middleware.cors import CORSMiddleware

from services import ai as ai_service
from services import engine as autonomy
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

app = FastAPI(title="Bark&Bond Match Engine")
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def _scrub(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    return doc


async def _audit(action: str, target: str, before: Any = None, after: Any = None, actor: str = "system") -> None:
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


# ---------------------------------------------------------------------------
# Auth dependency (oversight passcode — read-only surface only)
# ---------------------------------------------------------------------------


def require_oversight(x_admin_pass: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get("ADMIN_PASS")
    if not expected or x_admin_pass != expected:
        raise HTTPException(status_code=401, detail="Invalid passcode.")


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


class TrainerReactivateIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: Optional[str] = None
    submission_id: Optional[str] = None


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
    return {"service": "barkbond-match-engine", "ok": True, "ts": now_iso()}


@api.get("/config")
async def config() -> Dict[str, Any]:
    """Lightweight config the frontend can render without auth."""
    suburbs = sorted([s for s in await db.trainers.distinct("suburb", {"published": True, "region": {"$in": ACTIVE_REGIONS}}) if s])
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
        "suburbs": suburbs,
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
    await db.intros.insert_one(intro.copy())
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
        sub_doc["status"] = "published"
        sub_doc["trainer_id"] = trainer_id
        sub_doc["billing_profile_status"] = billing_profile.get("billing_profile_status")
    else:
        sub_doc["status"] = "held"

    await db.submissions.insert_one(sub_doc.copy())

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
        }
    )


@api.get("/submissions/{submission_id}/status")
async def get_submission_status(submission_id: str) -> Dict[str, Any]:
    sub = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")

    trainer = await _resolve_trainer(trainer_id=sub.get("trainer_id"), submission_id=submission_id)
    billing_profile_status = (
        sub.get("billing_profile_status")
        or (trainer or {}).get("billing_profile_status")
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

    return {
        "id": sub["id"],
        "submitted_at": sub.get("created_at"),
        "status": sub.get("status"),
        "verification_status": sub.get("verification_status"),
        "confidence_score": sub.get("confidence_score"),
        "billing_profile_status": billing_profile_status,
        "submitter_notification_status": sub.get("submitter_notification_status"),
        "trainer": {
            "id": (trainer or {}).get("id"),
            "name": (trainer or {}).get("name") or sub.get("name"),
            "published": bool((trainer or {}).get("published")) if trainer else sub.get("status") == "published",
            "verification_status": (trainer or {}).get("verification_status") or sub.get("verification_status"),
        },
        "blockers": blockers,
    }


@api.get("/trainer/billing")
async def get_trainer_billing_health(
    trainer_id: Optional[str] = Query(default=None),
    submission_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    trainer = await _resolve_trainer(trainer_id=trainer_id, submission_id=submission_id)
    sub = await _resolve_submission(submission_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer context not found.")

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
) -> Dict[str, Any]:
    trainer = await _resolve_trainer(trainer_id=trainer_id, submission_id=submission_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer context not found.")

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
async def oversight_login(payload: OversightLogin) -> Dict[str, Any]:
    expected = os.environ.get("ADMIN_PASS")
    if not expected or payload.passcode != expected:
        raise HTTPException(status_code=401, detail="Invalid passcode")
    return {"ok": True}


@api.get("/oversight")
async def oversight(_: None = Depends(require_oversight)) -> Dict[str, Any]:
    """Single read-only snapshot. No buttons. No actions. Just the truth."""
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

    event_id = str(event.get("id") or "")
    if event_id:
        if await db.stripe_events.find_one({"id": event_id}, {"_id": 0, "id": 1}):
            return {"ok": True, "duplicate": True}

    event_type = str(event.get("type") or "")
    obj = (event.get("data") or {}).get("object") or {}
    invoice_id = stripe_billing.extract_invoice_id(event_type, obj)
    if not invoice_id and event_type.startswith("charge.dispute"):
        charge_id = str(obj.get("charge") or "")
        invoice_id = stripe_billing.invoice_id_from_charge(charge_id)
    intro_id = str(((obj.get("metadata") or {}).get("intro_id")) or "")
    updates: Dict[str, Any] = {"stripe_last_event_type": event_type, "stripe_last_event_at": now_iso()}
    updates.update(stripe_billing.billing_updates_for_event(event_type, obj))

    if invoice_id:
        await db.intros.update_many({"stripe_invoice_id": invoice_id}, {"$set": updates})
    elif intro_id:
        await db.intros.update_many({"id": intro_id}, {"$set": updates})

    if event_id:
        await db.stripe_events.insert_one(
            {
                "id": event_id,
                "type": event_type,
                "invoice_id": invoice_id,
                "created_at": now_iso(),
            }
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

    runtime = runtime_control.resolve_loop_runtime(process_role)
    await _seed_if_empty()
    await _seed_discovery_if_empty()

    # Only the active owner process should execute initial autonomy writes.
    if allow_loop_schedule and runtime.should_schedule_loops:
        try:
            await autonomy.recompute_ranking(db)
            await autonomy.recompute_pricing(db)
            await autonomy.update_health(db)
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
