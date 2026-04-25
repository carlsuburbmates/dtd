"""Bark&Bond — pay-on-outcome dog-training match engine.

Design intent:
  - The product is the match, not the directory. There is no browse view.
  - Visibility is earned only through outcome signals (intros + conversions)
    via a Bayesian outcome score recomputed every minute by services.engine.
  - There are no manual approvals. Submissions auto-publish when score ≥ 0.85
    and auto-hold when < 0.6.
  - Monetisation is purely performance-based: per-intro fee (dynamically
    priced by suburb demand) + per-conversion fee.
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
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from services import ai as ai_service
from services import engine as autonomy
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


class IntroIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: str
    description: str
    user_email: Optional[EmailStr] = None
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    suburb: Optional[str] = None
    match_id: Optional[str] = None


class ConversionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    intro_id: str
    confirmed: bool = True


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


class OversightLogin(BaseModel):
    model_config = ConfigDict(extra="ignore")
    passcode: str


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


async def _decorate_with_pricing(trainers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach the dynamic intro fee for each trainer's suburb."""
    suburbs = list({t.get("suburb") for t in trainers if t.get("suburb")})
    pricing = await db.pricing_state.find({"suburb": {"$in": suburbs}}, {"_id": 0}).to_list(500)
    by_suburb = {p["suburb"]: p for p in pricing}
    for t in trainers:
        ps = by_suburb.get(t.get("suburb"))
        t["intro_fee_cents"] = int(ps["intro_fee_cents"]) if ps else autonomy.BASE_INTRO_FEE
        t["demand_multiplier"] = float(ps["multiplier"]) if ps else 1.0
    return trainers


# ---------------------------------------------------------------------------
# Public — primary product surface
# ---------------------------------------------------------------------------


@api.get("/")
async def root() -> Dict[str, Any]:
    return {"service": "barkbond-match-engine", "ok": True, "ts": now_iso()}


@api.get("/config")
async def config() -> Dict[str, Any]:
    """Lightweight config the frontend can render without auth."""
    suburbs = sorted([s for s in await db.trainers.distinct("suburb", {"published": True}) if s])
    return {
        "base_intro_fee_cents": autonomy.BASE_INTRO_FEE,
        "base_conversion_fee_cents": autonomy.BASE_CONVERSION_FEE,
        "suburbs": suburbs,
    }


@api.post("/match")
async def instant_match(payload: InstantMatchIn) -> Dict[str, Any]:
    """Single input → 3 trainers. The only product surface for end users."""
    pool_query: Dict[str, Any] = {"published": True}
    if payload.suburb:
        pool_query["suburb"] = {"$regex": f"^{payload.suburb}$", "$options": "i"}
    pool = await db.trainers.find(pool_query, {"_id": 0}).to_list(60)
    if not pool:
        pool = await db.trainers.find({"published": True}, {"_id": 0}).to_list(60)

    matches = await ai_service.match_trainers(payload.description, pool)
    by_id = {t["id"]: t for t in pool}

    selected: List[Dict[str, Any]] = []
    for m in matches:
        t = by_id.get(m["trainer_id"])
        if not t:
            continue
        # outcome_score already on the doc; AI provides relevance reason.
        selected.append({**t, "match_score": m["score"], "match_reasoning": m["reasoning"]})

    # Final sort = AI relevance × outcome score. AI relevance is the primary
    # signal; outcome is the tiebreaker / cold-start dampener.
    selected.sort(
        key=lambda t: (t.get("match_score", 0) * 0.7) + (t.get("outcome_score", 0.05) * 0.3),
        reverse=True,
    )
    selected = await _decorate_with_pricing(selected[:3])

    match_id = new_id()
    await db.match_events.insert_one(
        {
            "id": match_id,
            "description": payload.description,
            "suburb": payload.suburb,
            "result_ids": [t["id"] for t in selected],
            "created_at": now_iso(),
        }
    )
    return {"match_id": match_id, "matches": selected}


@api.get("/trainers/{trainer_id}")
async def get_trainer(trainer_id: str) -> Dict[str, Any]:
    doc = await db.trainers.find_one({"id": trainer_id, "published": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    decorated = await _decorate_with_pricing([doc])
    return decorated[0]


@api.post("/intros")
async def create_intro(payload: IntroIn, request: Request) -> Dict[str, Any]:
    trainer = await db.trainers.find_one({"id": payload.trainer_id, "published": True}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")

    fee = await autonomy.get_intro_fee(db, trainer.get("suburb"))
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
        "intro_fee_cents": fee,
        "billing_status": "billed",  # in production: integrates with Stripe
        "ip": (request.client.host if request.client else "") or "",
        "created_at": now_iso(),
    }
    await db.intros.insert_one(intro.copy())
    await _audit("intro", trainer["id"], after={"fee_cents": fee, "intro_id": intro["id"]}, actor="user")
    # Reveal contact info to the user — that is what they paid for.
    contact = {
        "name": trainer.get("name"),
        "website": trainer.get("website"),
        "phone": trainer.get("phone"),
        "email": trainer.get("email"),
        "suburb": trainer.get("suburb"),
    }
    return _scrub({**intro, "contact": contact})


@api.post("/conversions")
async def create_conversion(payload: ConversionIn) -> Dict[str, Any]:
    intro = await db.intros.find_one({"id": payload.intro_id}, {"_id": 0})
    if not intro:
        raise HTTPException(status_code=404, detail="Intro not found")
    if not payload.confirmed:
        return {"ok": True, "billed": False}
    existing = await db.conversions.find_one({"intro_id": payload.intro_id}, {"_id": 0})
    if existing:
        return {"ok": True, "billed": False, "existing": True}
    conv = {
        "id": new_id(),
        "intro_id": payload.intro_id,
        "trainer_id": intro["trainer_id"],
        "fee_cents": autonomy.BASE_CONVERSION_FEE,
        "billing_status": "billed",
        "created_at": now_iso(),
    }
    await db.conversions.insert_one(conv.copy())
    await _audit("conversion", intro["trainer_id"], after=conv["id"], actor="user")
    return _scrub({**conv, "billed": True})


@api.post("/submissions")
async def create_submission(payload: SubmissionIn) -> Dict[str, Any]:
    """Submit a real Melbourne trainer. Auto-publishes if AI score ≥ 0.85."""
    sub = payload.model_dump()
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
            "created_at": now_iso(),
            "via_submission_id": sub_doc["id"],
        }
        await db.trainers.insert_one(trainer_doc.copy())
        sub_doc["status"] = "published"
        sub_doc["trainer_id"] = trainer_id
    else:
        sub_doc["status"] = "held"

    await db.submissions.insert_one(sub_doc.copy())
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
        }
    )


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
    intros_24 = await db.intros.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}})
    intros_7d = await db.intros.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}})
    conv_24 = await db.conversions.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}})
    conv_7d = await db.conversions.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}})

    intros = await db.intros.find({}, {"_id": 0}).to_list(2000)
    conversions = await db.conversions.find({}, {"_id": 0}).to_list(2000)

    revenue_intro_cents = sum(i.get("intro_fee_cents", 0) for i in intros)
    revenue_conv_cents = sum(c.get("fee_cents", 0) for c in conversions)
    revenue_total_cents = revenue_intro_cents + revenue_conv_cents

    intros_total = max(1, len(intros))
    intro_to_conv = round(len(conversions) / intros_total, 3)

    health = await db.system_state.find_one({"key": "health"}, {"_id": 0}) or {}
    ranking = await db.system_state.find_one({"key": "ranking"}, {"_id": 0}) or {}
    pricing = await db.system_state.find_one({"key": "pricing"}, {"_id": 0}) or {}
    verification = await db.system_state.find_one({"key": "verification"}, {"_id": 0}) or {}

    pricing_state = await db.pricing_state.find({}, {"_id": 0}).sort("multiplier", -1).to_list(20)

    top_trainers = await db.trainers.find(
        {"published": True}, {"_id": 0, "id": 1, "name": 1, "suburb": 1, "outcome_score": 1, "intros_30d": 1, "conversions_30d": 1, "confidence_score": 1, "verification_status": 1}
    ).sort("outcome_score", -1).limit(10).to_list(10)

    audit_recent = await db.audit_log.find({}, {"_id": 0}).sort("ts", -1).to_list(20)

    submissions_summary = {
        "auto_published": await db.submissions.count_documents({"status": "published"}),
        "auto_held": await db.submissions.count_documents({"status": "held"}),
        "pending": await db.submissions.count_documents({"status": "pending"}),
    }

    integrity = {
        "verified": await db.trainers.count_documents({"published": True, "verification_status": "verified"}),
        "unverified": await db.trainers.count_documents({"published": True, "verification_status": "unverified"}),
        "hidden": await db.trainers.count_documents({"published": False}),
        "live_total": await db.trainers.count_documents({"published": True}),
    }

    return {
        "revenue": {
            "intro_cents": revenue_intro_cents,
            "conversion_cents": revenue_conv_cents,
            "total_cents": revenue_total_cents,
        },
        "throughput": {
            "intros_24h": intros_24,
            "intros_7d": intros_7d,
            "conversions_24h": conv_24,
            "conversions_7d": conv_7d,
            "intro_to_conversion_rate": intro_to_conv,
        },
        "loops": {
            "ranking": ranking,
            "pricing": pricing,
            "verification": verification,
            "health": health,
        },
        "alerts": health.get("alerts", []),
        "pricing_state": pricing_state,
        "top_trainers": top_trainers,
        "audit_recent": audit_recent,
        "submissions_summary": submissions_summary,
        "integrity": integrity,
        "ts": now_iso(),
    }


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


@app.on_event("startup")
async def on_startup() -> None:
    await db.trainers.create_index("id", unique=True, sparse=True)
    await db.intros.create_index([("trainer_id", 1), ("created_at", -1)])
    await db.conversions.create_index([("intro_id", 1)], unique=True)
    await db.submissions.create_index("status")
    await db.audit_log.create_index("ts")
    await db.pricing_state.create_index("suburb", unique=True)
    await db.system_state.create_index("key", unique=True)

    await _seed_if_empty()

    # Run an immediate ranking + pricing pass so the first request has data.
    try:
        await autonomy.recompute_ranking(db)
        await autonomy.recompute_pricing(db)
        await autonomy.update_health(db)
    except Exception:  # noqa: BLE001
        logger.exception("initial loop pass failed")

    # Schedule continuous loops.
    _BG_TASKS.extend(autonomy.schedule_all(db, ai_service))
    logger.info("scheduled %s autonomous loops", len(_BG_TASKS))


@app.on_event("shutdown")
async def on_shutdown() -> None:
    for t in _BG_TASKS:
        t.cancel()
    mongo_client.close()
