"""Deterministic matching/scoring/copy services with no vendor lock-in.

Three capabilities:
  - score_trainer: produce a confidence score (0-1) + reasoning from supplied evidence.
  - match_trainers: pick the best trainers from a candidate list given a free-text query.
  - generate_seo_copy: generate suburb/category landing-page copy.

This module is intentionally self-contained and vendor-neutral so the system can
run without any third-party model SDK dependency.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


def _extract_json(text: str) -> Optional[Any]:
    """Extract a JSON object/array from a model response."""
    if not text:
        return None
    # try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # try fenced code block
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    # try first {...} or [...] in text
    obj = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if obj:
        try:
            return json.loads(obj.group(1))
        except Exception:
            return None
    return None


# ---------- Verification scoring ----------

VERIFY_SYSTEM = (
    "You are a verification analyst for a Melbourne dog-trainers directory. "
    "Given a business listing and any source evidence, judge how likely it is to "
    "represent a REAL, currently operating dog-training business in or near Melbourne, Australia. "
    "Return ONLY a JSON object with keys: confidence (0-1 float), reasoning (1-2 sentences), "
    "signals (array of short evidence bullets). Do NOT fabricate facts; reason only from the input."
)


async def score_trainer(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return {confidence, reasoning, signals}."""
    return _heuristic_score(payload)


def _heuristic_score(payload: Dict[str, Any]) -> Dict[str, Any]:
    score = 0.2
    signals: List[str] = []
    if payload.get("website"):
        score += 0.35
        signals.append("Has a website URL")
    if payload.get("suburb"):
        score += 0.15
        signals.append("Suburb provided")
    if payload.get("phone") or payload.get("email"):
        score += 0.15
        signals.append("Contact details provided")
    if payload.get("services"):
        score += 0.10
        signals.append("Services listed")
    bio = payload.get("bio") or ""
    if len(bio) > 80:
        score += 0.05
    score = max(0.0, min(1.0, score))
    return {
        "confidence": round(score, 2),
        "reasoning": "Deterministic heuristic score based on submitted business evidence.",
        "signals": signals,
        "model": "heuristic",
    }


def status_for_score(conf: float) -> str:
    if conf >= 0.85:
        return "verified"
    if conf >= 0.60:
        return "unverified"
    return "hold"


# ---------- AI matching ----------

MATCH_SYSTEM = (
    "You are a calm, expert dog-training advisor. Given a list of trainers (each with id, name, suburb, "
    "services, bio, tier) and a user's description of their dog and goals, return the 3 best-fit trainers. "
    "Respect ranking integrity: only use the trainer's relevance to the user's needs — DO NOT use the "
    "'tier' field to influence ranking. Return ONLY JSON: an array of objects with keys "
    "trainer_id, score (0-1), reasoning (1-2 sentences focused on the user's specific needs)."
)


async def match_trainers(query: str, trainers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _heuristic_match(query, trainers)


def _heuristic_match(query: str, trainers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    q = (query or "").lower()
    scored: List[Dict[str, Any]] = []
    for t in trainers:
        words = (
            (t.get("name") or "")
            + " "
            + (t.get("suburb") or "")
            + " "
            + " ".join(t.get("services") or [])
            + " "
            + " ".join(t.get("categories") or [])
            + " "
            + (t.get("bio") or "")
        ).lower()
        hits = sum(1 for tok in set(q.split()) if len(tok) > 3 and tok in words)
        scored.append(
            {
                "trainer_id": t.get("id"),
                "score": min(1.0, 0.4 + 0.1 * hits),
                "reasoning": "Deterministic keyword-overlap heuristic match for the user request.",
            }
        )
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:3]


# ---------- SEO copy ----------

SEO_SYSTEM = (
    "You are an editorial copywriter for a Melbourne dog-trainers directory. Write authentic, non-spammy, "
    "useful copy for a suburb/category landing page. Avoid superlatives that imply we have ranked or rated "
    "businesses. Tone: warm, confident, factual. Return ONLY JSON: {title, meta_description, intro, sections: "
    "[{heading, body}], faq: [{q, a}]}. Keep meta_description <= 160 chars."
)


async def generate_seo_copy(suburb: str, category: str) -> Dict[str, Any]:
    fallback = {
        "title": f"Dog Trainers in {suburb} — {category.title()}",
        "meta_description": f"Find verified {category} dog trainers in {suburb}, Melbourne.",
        "intro": (
            f"Looking for {category} dog training in {suburb}? Browse a curated, verified directory "
            "of trainers serving the area."
        ),
        "sections": [
            {
                "heading": "What to look for",
                "body": "Check qualifications, training philosophy, and whether the trainer offers in-home or group sessions.",
            }
        ],
        "faq": [
            {
                "q": "How are trainers verified?",
                "a": "Each listing receives an evidence-based confidence score from public sources before publishing.",
            }
        ],
    }
    return fallback
