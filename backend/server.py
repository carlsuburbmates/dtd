"""Dog Trainers Directory — autonomous business OS backend.

Conventions:
  - All routes live under /api.
  - Mongo documents always store ISO-8601 strings for datetimes (so JSON-safe).
  - The MongoDB `_id` is excluded from every read so responses are clean JSON.
  - Admin routes require the `X-Admin-Pass` header to match ADMIN_PASS env var.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Header, Query
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from services import ai as ai_service
from services.seed import MELBOURNE_TRAINERS

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Dog Trainers Directory")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dtd")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Auth dependency (admin passcode)
# ---------------------------------------------------------------------------


def require_admin(x_admin_pass: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get("ADMIN_PASS")
    if not expected or x_admin_pass != expected:
        raise HTTPException(status_code=401, detail="Invalid admin passcode.")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TrainerIn(BaseModel):
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


class TrainerPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    suburb: Optional[str] = None
    region: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    categories: Optional[List[str]] = None
    services: Optional[List[str]] = None
    bio: Optional[str] = None
    image_url: Optional[str] = None
    tier: Optional[str] = None  # free | featured | premium
    published: Optional[bool] = None
    verification_status: Optional[str] = None


class LeadIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trainer_id: str
    user_name: str
    user_email: EmailStr
    user_phone: Optional[str] = ""
    dog_description: str
    goals: Optional[str] = ""
    source: Optional[str] = "trainer_page"


class LeadPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str  # new | viewed | contacted | converted | rejected


class MatchIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str
    suburb: Optional[str] = None
    category: Optional[str] = None


class SubmissionIn(TrainerIn):
    submitter_email: Optional[EmailStr] = None
    submitter_note: Optional[str] = ""


class ABTestIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    metric: str
    variants: List[str] = Field(default_factory=lambda: ["control", "variant"])
    allocation: List[float] = Field(default_factory=lambda: [0.5, 0.5])
    status: str = "running"  # running | paused | completed


class SEORequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    suburb: str
    category: str = "general"


class AdminLogin(BaseModel):
    model_config = ConfigDict(extra="ignore")
    passcode: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scrub(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    return doc


async def _audit(action: str, target: str, before: Any = None, after: Any = None, actor: str = "admin") -> None:
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


def _verification_payload(trainer: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": trainer.get("name"),
        "suburb": trainer.get("suburb"),
        "website": trainer.get("website"),
        "phone": trainer.get("phone"),
        "email": trainer.get("email"),
        "services": trainer.get("services"),
        "categories": trainer.get("categories"),
        "bio": trainer.get("bio"),
        "source_evidence_url": trainer.get("source_evidence_url"),
    }


async def _verify_and_persist(trainer_id: str) -> Dict[str, Any]:
    trainer = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    score = await ai_service.score_trainer(_verification_payload(trainer))
    status = ai_service.status_for_score(score["confidence"])
    update = {
        "confidence_score": score["confidence"],
        "verification_status": status,
        "verification_reasoning": score.get("reasoning", ""),
        "verification_signals": score.get("signals", []),
        "verification_model": score.get("model", "heuristic"),
        "verified_at": now_iso(),
        "published": status in ("verified", "unverified"),
    }
    await db.trainers.update_one({"id": trainer_id}, {"$set": update})
    await _audit("verify", trainer_id, before=trainer.get("verification_status"), after=status, actor="ai")
    trainer.update(update)
    return trainer


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------


@api.get("/")
async def root() -> Dict[str, Any]:
    return {"service": "dog-trainers-directory", "ok": True, "ts": now_iso()}


@api.get("/trainers")
async def list_trainers(
    suburb: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    only_verified: bool = False,
    limit: int = Query(60, ge=1, le=200),
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {"published": True}
    if suburb:
        query["suburb"] = {"$regex": f"^{suburb}$", "$options": "i"}
    if category:
        query["categories"] = {"$in": [category.lower()]}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"bio": {"$regex": q, "$options": "i"}},
            {"suburb": {"$regex": q, "$options": "i"}},
        ]
    if only_verified:
        query["verification_status"] = "verified"
    docs = await db.trainers.find(query, {"_id": 0}).to_list(limit)
    # Featured & premium tiers float to the top, but ranking integrity disclosure
    # is preserved by attaching `placement` field so frontend labels paid placement.
    def sort_key(t: Dict[str, Any]):
        tier_rank = {"premium": 0, "featured": 1, "free": 2}.get(t.get("tier", "free"), 2)
        return (tier_rank, -float(t.get("confidence_score") or 0))
    docs.sort(key=sort_key)
    for d in docs:
        d["placement"] = "paid" if d.get("tier") in ("featured", "premium") else "organic"
    return docs


@api.get("/trainers/{trainer_id}")
async def get_trainer(trainer_id: str) -> Dict[str, Any]:
    doc = await db.trainers.find_one({"id": trainer_id, "published": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return doc


@api.get("/featured")
async def featured() -> List[Dict[str, Any]]:
    docs = await db.trainers.find(
        {"published": True, "tier": {"$in": ["featured", "premium"]}}, {"_id": 0}
    ).to_list(8)
    return docs


@api.get("/suburbs")
async def suburbs() -> List[str]:
    raw = await db.trainers.distinct("suburb", {"published": True})
    return sorted([s for s in raw if s])


@api.get("/categories")
async def categories() -> List[str]:
    raw = await db.trainers.distinct("categories", {"published": True})
    flat = sorted({c for c in raw if c})
    return flat


@api.get("/stats/public")
async def public_stats() -> Dict[str, Any]:
    total = await db.trainers.count_documents({"published": True})
    verified = await db.trainers.count_documents({"published": True, "verification_status": "verified"})
    suburbs_count = len(await db.trainers.distinct("suburb", {"published": True}))
    return {"trainers": total, "verified": verified, "suburbs": suburbs_count}


@api.post("/leads")
async def create_lead(payload: LeadIn) -> Dict[str, Any]:
    trainer = await db.trainers.find_one({"id": payload.trainer_id, "published": True}, {"_id": 0})
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    lead = {
        "id": new_id(),
        "trainer_id": payload.trainer_id,
        "trainer_name": trainer.get("name"),
        "user_name": payload.user_name,
        "user_email": payload.user_email,
        "user_phone": payload.user_phone or "",
        "dog_description": payload.dog_description,
        "goals": payload.goals or "",
        "source": payload.source or "trainer_page",
        "status": "new",
        "created_at": now_iso(),
        # Quality signal — light heuristic so trainers see "completeness"
        "quality_score": round(
            min(
                1.0,
                0.4
                + (0.2 if payload.user_phone else 0)
                + (0.2 if len(payload.dog_description or "") > 40 else 0)
                + (0.2 if (payload.goals or "") else 0),
            ),
            2,
        ),
    }
    await db.leads.insert_one(lead.copy())
    await _audit("lead_created", payload.trainer_id, after=lead["id"], actor="user")
    return _scrub(lead)


@api.post("/submissions")
async def create_submission(payload: SubmissionIn) -> Dict[str, Any]:
    sub = payload.model_dump()
    sub.update(
        {
            "id": new_id(),
            "status": "pending",
            "created_at": now_iso(),
        }
    )
    # Pre-score so the admin queue has signal immediately
    score = await ai_service.score_trainer(_verification_payload(sub))
    sub["confidence_score"] = score["confidence"]
    sub["verification_reasoning"] = score.get("reasoning", "")
    sub["verification_signals"] = score.get("signals", [])
    sub["verification_model"] = score.get("model", "heuristic")
    await db.submissions.insert_one(sub.copy())
    await _audit("submission_received", sub["id"], after=sub["confidence_score"], actor="public")
    return _scrub(sub)


@api.post("/match")
async def match(payload: MatchIn) -> Dict[str, Any]:
    pool_query: Dict[str, Any] = {"published": True}
    if payload.suburb:
        pool_query["suburb"] = {"$regex": f"^{payload.suburb}$", "$options": "i"}
    if payload.category:
        pool_query["categories"] = {"$in": [payload.category.lower()]}
    pool = await db.trainers.find(pool_query, {"_id": 0}).to_list(50)
    if not pool:
        # broaden if too narrow
        pool = await db.trainers.find({"published": True}, {"_id": 0}).to_list(50)
    matches = await ai_service.match_trainers(payload.description, pool)
    by_id = {t["id"]: t for t in pool}
    out = []
    for m in matches:
        t = by_id.get(m["trainer_id"])
        if not t:
            continue
        out.append({**t, "match_score": m["score"], "match_reasoning": m["reasoning"]})
    # log experiment / event
    await db.match_events.insert_one(
        {
            "id": new_id(),
            "description": payload.description,
            "suburb": payload.suburb,
            "category": payload.category,
            "result_ids": [m["trainer_id"] for m in matches],
            "created_at": now_iso(),
        }
    )
    return {"matches": out, "model": ai_service.MODEL_NAME}


@api.get("/seo/{slug:path}")
async def get_seo(slug: str) -> Dict[str, Any]:
    page = await db.seo_pages.find_one({"slug": slug}, {"_id": 0})
    if page:
        return page
    # auto-generate from slug like "fitzroy/obedience" or "fitzroy"
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
# Admin routes
# ---------------------------------------------------------------------------


@api.post("/admin/login")
async def admin_login(payload: AdminLogin) -> Dict[str, Any]:
    expected = os.environ.get("ADMIN_PASS")
    if not expected or payload.passcode != expected:
        raise HTTPException(status_code=401, detail="Invalid passcode")
    return {"ok": True, "passcode": expected}


@api.get("/admin/trainers")
async def admin_list_trainers(_: None = Depends(require_admin)) -> List[Dict[str, Any]]:
    return await db.trainers.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.patch("/admin/trainers/{trainer_id}")
async def admin_patch_trainer(
    trainer_id: str, payload: TrainerPatch, _: None = Depends(require_admin)
) -> Dict[str, Any]:
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    before = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not before:
        raise HTTPException(status_code=404, detail="Trainer not found")
    update["updated_at"] = now_iso()
    await db.trainers.update_one({"id": trainer_id}, {"$set": update})
    after = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    await _audit("trainer_update", trainer_id, before=before, after=after)
    return after


@api.delete("/admin/trainers/{trainer_id}")
async def admin_delete_trainer(trainer_id: str, _: None = Depends(require_admin)) -> Dict[str, Any]:
    before = await db.trainers.find_one({"id": trainer_id}, {"_id": 0})
    if not before:
        raise HTTPException(status_code=404, detail="Trainer not found")
    await db.trainers.delete_one({"id": trainer_id})
    await _audit("trainer_delete", trainer_id, before=before)
    return {"ok": True}


@api.post("/admin/verify/{trainer_id}")
async def admin_verify_trainer(trainer_id: str, _: None = Depends(require_admin)) -> Dict[str, Any]:
    return await _verify_and_persist(trainer_id)


@api.get("/admin/submissions")
async def admin_list_submissions(_: None = Depends(require_admin)) -> List[Dict[str, Any]]:
    return await db.submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/admin/submissions/{sid}/approve")
async def admin_approve_submission(sid: str, _: None = Depends(require_admin)) -> Dict[str, Any]:
    sub = await db.submissions.find_one({"id": sid}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    trainer = {
        "id": new_id(),
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
        "tier": "free",
        "confidence_score": sub.get("confidence_score", 0.0),
        "verification_status": ai_service.status_for_score(sub.get("confidence_score", 0.0)),
        "verification_reasoning": sub.get("verification_reasoning", ""),
        "verification_signals": sub.get("verification_signals", []),
        "verification_model": sub.get("verification_model", "heuristic"),
        "published": True,
        "created_at": now_iso(),
    }
    await db.trainers.insert_one(trainer.copy())
    await db.submissions.update_one({"id": sid}, {"$set": {"status": "approved", "trainer_id": trainer["id"]}})
    await _audit("submission_approve", sid, after=trainer["id"])
    return _scrub(trainer)


@api.post("/admin/submissions/{sid}/reject")
async def admin_reject_submission(sid: str, _: None = Depends(require_admin)) -> Dict[str, Any]:
    sub = await db.submissions.find_one({"id": sid}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    await db.submissions.update_one({"id": sid}, {"$set": {"status": "rejected"}})
    await _audit("submission_reject", sid)
    return {"ok": True}


@api.get("/admin/leads")
async def admin_list_leads(
    trainer_id: Optional[str] = None, _: None = Depends(require_admin)
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if trainer_id:
        q["trainer_id"] = trainer_id
    return await db.leads.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.patch("/admin/leads/{lead_id}")
async def admin_patch_lead(lead_id: str, payload: LeadPatch, _: None = Depends(require_admin)) -> Dict[str, Any]:
    before = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not before:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.leads.update_one({"id": lead_id}, {"$set": {"status": payload.status, "updated_at": now_iso()}})
    after = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    await _audit("lead_update", lead_id, before=before.get("status"), after=payload.status)
    return after


# ---- Monetisation analytics ----

TIER_PRICE = {"free": 0, "featured": 49, "premium": 149}


@api.get("/admin/analytics")
async def admin_analytics(_: None = Depends(require_admin)) -> Dict[str, Any]:
    trainers = await db.trainers.find({}, {"_id": 0}).to_list(1000)
    leads = await db.leads.find({}, {"_id": 0}).to_list(2000)
    submissions = await db.submissions.find({}, {"_id": 0}).to_list(1000)

    by_tier: Dict[str, int] = {"free": 0, "featured": 0, "premium": 0}
    for t in trainers:
        by_tier[t.get("tier", "free")] = by_tier.get(t.get("tier", "free"), 0) + 1
    mrr = sum(TIER_PRICE.get(tier, 0) * count for tier, count in by_tier.items())
    arr = mrr * 12

    # Lead funnel
    funnel: Dict[str, int] = {"new": 0, "viewed": 0, "contacted": 0, "converted": 0, "rejected": 0}
    for lead in leads:
        funnel[lead.get("status", "new")] = funnel.get(lead.get("status", "new"), 0) + 1
    contacted_or_better = funnel["contacted"] + funnel["converted"]
    conv_rate = round(funnel["converted"] / max(1, len(leads)), 3)
    contact_rate = round(contacted_or_better / max(1, len(leads)), 3)

    # Recent activity (14d)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    recent_leads = [lead for lead in leads if lead.get("created_at", "") >= cutoff]
    daily: Dict[str, int] = {}
    for lead in recent_leads:
        day = lead.get("created_at", "")[:10]
        daily[day] = daily.get(day, 0) + 1
    leads_timeseries = [{"date": d, "count": c} for d, c in sorted(daily.items())]

    # Verification mix
    ver_mix: Dict[str, int] = {"verified": 0, "unverified": 0, "hold": 0, "pending": 0}
    for t in trainers:
        ver_mix[t.get("verification_status", "pending")] = ver_mix.get(t.get("verification_status", "pending"), 0) + 1

    return {
        "total_trainers": len(trainers),
        "by_tier": by_tier,
        "mrr": mrr,
        "arr": arr,
        "tier_prices": TIER_PRICE,
        "leads_total": len(leads),
        "lead_funnel": funnel,
        "lead_conversion_rate": conv_rate,
        "lead_contact_rate": contact_rate,
        "leads_timeseries": leads_timeseries,
        "verification_mix": ver_mix,
        "submissions_pending": sum(1 for s in submissions if s.get("status") == "pending"),
    }


# ---- A/B Tests ----

@api.get("/admin/ab-tests")
async def admin_list_ab(_: None = Depends(require_admin)) -> List[Dict[str, Any]]:
    return await db.ab_tests.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)


@api.post("/admin/ab-tests")
async def admin_create_ab(payload: ABTestIn, _: None = Depends(require_admin)) -> Dict[str, Any]:
    doc = payload.model_dump()
    doc.update({"id": new_id(), "created_at": now_iso(), "results": {}})
    await db.ab_tests.insert_one(doc.copy())
    await _audit("ab_create", doc["id"], after=doc)
    return _scrub(doc)


@api.patch("/admin/ab-tests/{ab_id}")
async def admin_patch_ab(ab_id: str, payload: ABTestIn, _: None = Depends(require_admin)) -> Dict[str, Any]:
    update = payload.model_dump()
    before = await db.ab_tests.find_one({"id": ab_id}, {"_id": 0})
    if not before:
        raise HTTPException(status_code=404, detail="A/B test not found")
    await db.ab_tests.update_one({"id": ab_id}, {"$set": update})
    after = await db.ab_tests.find_one({"id": ab_id}, {"_id": 0})
    await _audit("ab_update", ab_id, before=before, after=after)
    return after


# ---- Health & Anomaly monitor ----


@api.get("/admin/health")
async def admin_health(_: None = Depends(require_admin)) -> Dict[str, Any]:
    cutoff_24 = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    leads_24 = await db.leads.count_documents({"created_at": {"$gte": cutoff_24}})
    leads_prev = await db.leads.count_documents(
        {
            "created_at": {
                "$gte": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(),
                "$lt": cutoff_24,
            }
        }
    )
    drop_pct = 0.0
    if leads_prev > 0:
        drop_pct = round((leads_prev - leads_24) / leads_prev, 3)
    suspicious = await db.trainers.count_documents(
        {"$or": [{"verification_status": "hold"}, {"confidence_score": {"$lt": 0.6}}]}
    )
    pending = await db.submissions.count_documents({"status": "pending"})
    audit_recent = await db.audit_log.find({}, {"_id": 0}).sort("ts", -1).to_list(20)
    alerts: List[Dict[str, Any]] = []
    if drop_pct >= 0.5 and leads_prev >= 4:
        alerts.append(
            {
                "severity": "high",
                "type": "lead_drop",
                "message": f"Leads dropped {int(drop_pct*100)}% in last 24h vs prior 24h.",
            }
        )
    if suspicious > 0:
        alerts.append(
            {
                "severity": "medium",
                "type": "low_confidence",
                "message": f"{suspicious} listings below verification threshold.",
            }
        )
    if pending > 5:
        alerts.append(
            {
                "severity": "low",
                "type": "queue_growth",
                "message": f"{pending} pending submissions awaiting review.",
            }
        )
    return {
        "leads_24h": leads_24,
        "leads_prev_24h": leads_prev,
        "leads_change_pct": -drop_pct,
        "suspicious_listings": suspicious,
        "pending_submissions": pending,
        "alerts": alerts,
        "audit_recent": audit_recent,
    }


@api.get("/admin/audit-log")
async def admin_audit_log(_: None = Depends(require_admin)) -> List[Dict[str, Any]]:
    return await db.audit_log.find({}, {"_id": 0}).sort("ts", -1).to_list(200)


# ---- SEO ----


@api.post("/admin/seo/generate")
async def admin_generate_seo(payload: SEORequest, _: None = Depends(require_admin)) -> Dict[str, Any]:
    slug = f"{payload.suburb.lower().replace(' ', '-')}/{payload.category.lower().replace(' ', '-')}"
    copy = await ai_service.generate_seo_copy(payload.suburb, payload.category)
    doc = {
        "id": new_id(),
        "slug": slug,
        "suburb": payload.suburb,
        "category": payload.category,
        "copy": copy,
        "generated_at": now_iso(),
    }
    await db.seo_pages.update_one({"slug": slug}, {"$set": doc}, upsert=True)
    await _audit("seo_generate", slug)
    return _scrub(doc)


@api.get("/admin/seo")
async def admin_list_seo(_: None = Depends(require_admin)) -> List[Dict[str, Any]]:
    return await db.seo_pages.find({}, {"_id": 0}).sort("generated_at", -1).to_list(200)


# ---- Seeding ----


@api.post("/admin/seed")
async def admin_seed(_: None = Depends(require_admin)) -> Dict[str, Any]:
    inserted = 0
    verified = 0
    for entry in MELBOURNE_TRAINERS:
        existing = await db.trainers.find_one({"name": entry["name"]}, {"_id": 0})
        if existing:
            continue
        doc = {
            "id": new_id(),
            "tier": entry.get("tier", "free"),
            "verification_status": "pending",
            "published": False,
            "created_at": now_iso(),
            **entry,
        }
        await db.trainers.insert_one(doc.copy())
        inserted += 1
        # run AI verification (cheap heuristic if no key)
        try:
            await _verify_and_persist(doc["id"])
            verified += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed verify failed for %s: %s", entry["name"], exc)
    await _audit("seed", "trainers", after={"inserted": inserted, "verified": verified})

    # Seed a default A/B test if none exists
    if await db.ab_tests.count_documents({}) == 0:
        await db.ab_tests.insert_one(
            {
                "id": new_id(),
                "name": "Hero CTA: 'Find a trainer' vs 'Match my dog'",
                "metric": "matcher_starts",
                "variants": ["control", "variant"],
                "allocation": [0.5, 0.5],
                "status": "running",
                "results": {"control": {"impressions": 240, "conversions": 18}, "variant": {"impressions": 236, "conversions": 27}},
                "created_at": now_iso(),
            }
        )
    return {"inserted": inserted, "verified": verified, "total": await db.trainers.count_documents({})}


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


@app.on_event("startup")
async def on_startup() -> None:
    await db.trainers.create_index("id", unique=True, sparse=True)
    await db.leads.create_index("trainer_id")
    await db.submissions.create_index("status")
    await db.audit_log.create_index("ts")
    # auto-seed if empty
    if await db.trainers.count_documents({}) == 0:
        logger.info("Empty database — seeding Melbourne trainers")
        for entry in MELBOURNE_TRAINERS:
            doc = {
                "id": new_id(),
                "tier": entry.get("tier", "free"),
                "verification_status": "pending",
                "published": False,
                "created_at": now_iso(),
                **entry,
            }
            await db.trainers.insert_one(doc.copy())
            try:
                await _verify_and_persist(doc["id"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("startup verify failed for %s: %s", entry["name"], exc)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    client.close()
