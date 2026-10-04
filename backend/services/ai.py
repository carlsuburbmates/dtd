"""Fail-safe Gemini AI foundation for DTD.

Capabilities:
  - extract_trainer_source: structured extraction of trainer attributes from raw source text/evidence.
  - match_trainers: explainable diagnostic match assessment (paid tier never influences fit).
  - score_trainer: confidence scoring and verification signals from business evidence.
  - generate_seo_copy: suburb/category landing page copy generation.

Reliability and Governance:
  - Strict structured-output validation. Malformed model responses are rejected.
  - Deterministic heuristic fallbacks for every capability.
  - No key required for local development; missing key gracefully uses deterministic fallback.
  - No live network calls during offline tests (mock/client injection supported).
  - Safety boundary: AI output alone NEVER publishes a profile, marks an ABN verified,
    or creates unsupported public trust claims.
  - Provider degradation (timeout, rate limit, malformed response, service unavailable)
    is recorded in a bounded, sanitized event log (no prompts, source text, or secrets)
    and exposed through /ops evidence.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Union
import uuid

logger = logging.getLogger(__name__)

try:
    from services.trainer_quality import build_match_ready_projection  # type: ignore
except ImportError:
    from backend.services.trainer_quality import build_match_ready_projection  # type: ignore

# Configuration contract from DTD Google Ecosystem Migration Spec
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT_S = float(os.environ.get("GEMINI_TIMEOUT_S", "5.0"))
MAX_DEGRADATION_EVENTS = 100
ENABLE_MATCH_READY_PROJECTION_FILTER = (
    os.environ.get("ENABLE_MATCH_READY_PROJECTION_FILTER", "").lower() in ("1", "true", "yes")
)

VALID_PHILOSOPHIES: Set[str] = {
    "Positive Reinforcement / Force-Free",
    "Balanced",
}

CANONICAL_SERVICE_FORMATS: Set[str] = {
    "in_home",
    "facility",
    "board_and_train",
    "online",
}

CANONICAL_SPECIALTIES: Set[str] = {
    "puppy_training",
    "leash_reactivity",
    "separation_anxiety",
    "obedience",
    "aggression",
    "behavioral_consultation",
    "agility",
    "scent_work",
    "recall_training",
    "trick_training",
    "guard_dog_training",
    "assistance_dog_training",
}

# Module-level bounded ring buffer and DB reference
_degradation_events: deque = deque(maxlen=MAX_DEGRADATION_EVENTS)
_mongo_db: Optional[Any] = None


def set_db(db: Any) -> None:
    """Register database handle for degradation persistence."""
    global _mongo_db
    _mongo_db = db


def clear_degradation_events() -> None:
    """Clear in-memory degradation events (primarily for test isolation)."""
    _degradation_events.clear()


class StructuredValidationError(ValueError):
    """Raised when model response fails strict schema or semantic validation."""
    pass


def is_gemini_configured() -> bool:
    """Check whether Gemini is configured (Google AI Studio API key or Vertex AI ADC)."""
    if bool(os.environ.get("GEMINI_API_KEY", "").strip()):
        return True
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true", "yes"):
        return True
    if bool(os.environ.get("VERTEXAI_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")):
        return True
    return False


def get_gemini_client() -> Optional[Any]:
    """Obtain a Google GenAI client if configured, otherwise None.

    Supports dual-mode configuration:
    1. Google AI Studio: via GEMINI_API_KEY (default for local dev & testing).
    2. Google Cloud Vertex AI: via Application Default Credentials (ADC) with
       roles/aiplatform.user on Cloud Run when GOOGLE_GENAI_USE_VERTEXAI=true,
       VERTEXAI_PROJECT, or GOOGLE_CLOUD_PROJECT is set.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    use_vertex = (
        os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true", "yes")
        or bool(os.environ.get("VERTEXAI_PROJECT"))
        or (not api_key and bool(os.environ.get("GOOGLE_CLOUD_PROJECT")))
    )

    if not api_key and not use_vertex:
        return None

    try:
        from google import genai
        if api_key:
            return genai.Client(api_key=api_key)

        # Vertex AI mode via Application Default Credentials (ADC)
        project = os.environ.get("VERTEXAI_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("VERTEXAI_LOCATION", "australia-southeast1")
        return genai.Client(vertexai=True, project=project, location=location)
    except Exception as e:
        logger.debug("Failed to initialize google.genai Client: %s", e)
        return None


def _generate_content_config(**kwargs: Any) -> Any:
    """Build the provider config without making injected-client tests need its SDK.

    A live Gemini client can only be constructed when ``google.genai`` is
    installed. Test doubles are deliberately injectable, however, and only
    need the configuration shape. Returning the plain shape keeps that
    contract offline while preserving the real SDK object in production.
    """
    try:
        from google.genai import types
    except ModuleNotFoundError:
        return kwargs
    return types.GenerateContentConfig(**kwargs)


def _extract_json(text: str) -> Optional[Any]:
    """Extract a JSON object/array from a model response."""
    if not text:
        return None
    # 1. Direct parse
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    # 2. Markdown fenced code block
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except Exception:
            pass
    # 3. First balanced/enclosed JSON object or array
    obj = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if obj:
        try:
            return json.loads(obj.group(1).strip())
        except Exception:
            return None
    return None


# ---------- Bounded Degradation Event Persistence ----------

async def record_degradation_event(
    event_type: str,
    error_code: str,
    message: str,
    operation: str,
    db: Optional[Any] = None,
    latency_ms: Optional[float] = None,
    decision_state: Optional[str] = None,
    policy_version: Optional[str] = "v2",
) -> Dict[str, Any]:
    """Record a sanitized degradation event without prompts, source content, or secrets.

    event_type: timeout | rate_limit | malformed_output | unavailable_service | provider_error
    """
    event = {
        "id": f"ai_deg_{uuid.uuid4().hex[:12]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "gemini",
        "model": GEMINI_MODEL,
        "error_type": event_type,
        "error_code": error_code,
        "message": message,
        "operation": operation,
        "fallback_used": True,
        "recovered": True,
        "latency_ms": latency_ms,
        "decision_state": decision_state,
        "policy_version": policy_version,
    }

    _degradation_events.append(event)

    target_db = db if db is not None else _mongo_db
    if target_db is not None:
        try:
            coll = getattr(target_db, "ai_degradation_events", None)
            if coll is not None and hasattr(coll, "insert_one"):
                await coll.insert_one(event.copy())
        except Exception as err:
            logger.warning("Failed to persist AI degradation event to MongoDB: %s", err)

    return event


async def get_degradation_events(
    limit: int = 50,
    db: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Retrieve recent degradation events from DB or in-memory ring buffer."""
    target_db = db if db is not None else _mongo_db
    if target_db is not None:
        try:
            coll = getattr(target_db, "ai_degradation_events", None)
            if coll is not None and hasattr(coll, "find"):
                docs = await coll.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
                if docs:
                    return docs
        except Exception as err:
            logger.debug("MongoDB read for degradation events failed, using in-memory: %s", err)

    # Return reverse chronological view from ring buffer
    events = list(_degradation_events)
    events.reverse()
    return events[:limit]


async def get_ops_degradation_cases(
    limit: int = 50,
    db: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Format recent degradation events into /ops exception case objects."""
    events = await get_degradation_events(limit=limit, db=db)
    cases: List[Dict[str, Any]] = []
    for ev in events:
        cases.append(
            {
                "case_id": f"ai_degradation:{ev.get('id')}",
                "case_type": "ai_degradation_case",
                "canonical_user_type": "System / AI Integration",
                "workflow": "AI scoring and matching",
                "entity_type": "ai_service",
                "entity_id": ev.get("id"),
                "title": f"AI provider degradation · {str(ev.get('error_type', '')).replace('_', ' ').title()}",
                "summary": (
                    ev.get("message")
                    or "AI provider experienced an operational disruption; deterministic fallback engaged."
                ),
                "severity": "high" if ev.get("error_type") in {"unavailable_service", "rate_limit"} else "medium",
                "state": "detected",
                "owner": "",
                "detected_at": ev.get("timestamp"),
                "last_updated_at": ev.get("timestamp"),
                "source_refs": [{"kind": "ai_service", "id": ev.get("model", "gemini-1.5-flash")}],
                "risk_reason_codes": [ev.get("error_code") or "AI_DEGRADATION"],
                "recommended_next_step": (
                    "Verify Gemini API quota, billing tier, and health status; deterministic fallback remains active."
                ),
                "responsibility_layer": "Layer 1 — Normal Ops",
                "detail_rows": [
                    {"label": "Provider", "value": "Google Gemini"},
                    {"label": "Model", "value": ev.get("model") or GEMINI_MODEL},
                    {"label": "Error type", "value": ev.get("error_type") or "unknown"},
                    {"label": "Operation", "value": ev.get("operation") or "unknown"},
                    {"label": "Fallback used", "value": "true"},
                ],
                "linked_paths": [],
                "audit_refs": [],
            }
        )
    return cases


# ---------- Normalization and Strict Schema Validation ----------

def _normalize_philosophy(val: Any) -> Optional[str]:
    """Normalize raw training philosophy text to canonical choices."""
    if not isinstance(val, str):
        return None
    s = val.strip()
    if s in VALID_PHILOSOPHIES:
        return s
    low = s.lower()
    if re.search(r"(force[- ]free|positive\s*reinforce|r\+|rewards?[- ]based|fear[- ]free|lfs)", low):
        return "Positive Reinforcement / Force-Free"
    if re.search(r"(balanced|e[- ]collar|prong|correction|dominance)", low):
        return "Balanced"
    return None


def _normalize_service_format(val: Any) -> Optional[str]:
    """Normalize a raw service format string to canonical choices."""
    if not isinstance(val, str):
        return None
    low = val.strip().lower().replace("-", "_").replace(" ", "_")
    if low in CANONICAL_SERVICE_FORMATS:
        return low
    if "home" in low or "mobile" in low or "private" in low:
        return "in_home"
    if "facility" in low or "centre" in low or "center" in low or "studio" in low or "hall" in low:
        return "facility"
    if "board" in low or "bootcamp" in low or "residential" in low:
        return "board_and_train"
    if "online" in low or "zoom" in low or "virtual" in low or "remote" in low:
        return "online"
    return None


def _normalize_specialty(val: Any) -> Optional[str]:
    """Normalize a specialty string to snake_case."""
    if not isinstance(val, str):
        return None
    low = val.strip().lower().replace("-", "_").replace(" ", "_")
    low = re.sub(r"[^\w_]", "", low)
    if not low:
        return None
    return low


def validate_extracted_source(data: Any) -> Dict[str, Any]:
    """Strictly validate and normalize structured trainer extraction from AI.

    Raises StructuredValidationError if required fields are missing or invalid.
    Strictly strips and zeroes any unsupported publication or verification flags.
    """
    if not isinstance(data, dict):
        raise StructuredValidationError(f"Expected JSON object, got {type(data).__name__}")

    # 1. Training philosophy
    raw_phil = data.get("training_philosophy")
    norm_phil = _normalize_philosophy(raw_phil)
    if not norm_phil:
        raise StructuredValidationError(
            f"Invalid or missing training_philosophy: {raw_phil!r}. Must resolve to {VALID_PHILOSOPHIES}"
        )

    # 2. Specialties
    raw_specs = data.get("specialties")
    if not isinstance(raw_specs, list) or len(raw_specs) == 0:
        raise StructuredValidationError("Specialties must be a non-empty list of strings")
    specs: List[str] = []
    for s in raw_specs:
        ns = _normalize_specialty(s)
        if ns and ns not in specs:
            specs.append(ns)
    if not specs:
        raise StructuredValidationError("No valid specialties found in list")

    # 3. Service formats
    raw_formats = data.get("service_formats")
    if not isinstance(raw_formats, list) or len(raw_formats) == 0:
        raise StructuredValidationError("Service formats must be a non-empty list of strings")
    formats: List[str] = []
    for f in raw_formats:
        nf = _normalize_service_format(f)
        if nf and nf not in formats:
            formats.append(nf)
    if not formats:
        raise StructuredValidationError("No valid service formats found in list")

    # 4. Serviced suburbs
    raw_suburbs = data.get("serviced_suburbs")
    if not isinstance(raw_suburbs, list) or len(raw_suburbs) == 0:
        raise StructuredValidationError("Serviced suburbs must be a non-empty list of strings")
    suburbs: List[str] = []
    for sub in raw_suburbs:
        if isinstance(sub, str) and sub.strip():
            c = sub.strip()
            if c not in suburbs:
                suburbs.append(c)
    if not suburbs:
        suburbs = ["Melbourne-Wide Mobile"]

    # 5. Confidence
    raw_conf = data.get("confidence")
    if raw_conf is None:
        raise StructuredValidationError("Missing required 'confidence' float")
    try:
        conf = float(raw_conf)
    except (ValueError, TypeError):
        raise StructuredValidationError(f"Invalid confidence: {raw_conf!r}, must be a float between 0.0 and 1.0")
    if not (0.0 <= conf <= 1.0):
        raise StructuredValidationError(f"Confidence {conf} out of bounds [0.0, 1.0]")

    # 6. Reasoning
    raw_reasoning = data.get("reasoning")
    if not isinstance(raw_reasoning, str) or not raw_reasoning.strip():
        raise StructuredValidationError("Missing or non-string 'reasoning' explanation")

    # 7. Signals
    raw_signals = data.get("signals", [])
    if not isinstance(raw_signals, list):
        raw_signals = [str(raw_signals)]
    signals = [str(s).strip() for s in raw_signals if str(s).strip()]

    # Critical Safety Boundary: AI output alone NEVER publishes or verifies ABN
    return {
        "training_philosophy": norm_phil,
        "specialties": specs,
        "service_formats": formats,
        "serviced_suburbs": suburbs,
        "confidence": round(conf, 2),
        "reasoning": raw_reasoning.strip(),
        "signals": signals,
        "published": False,
        "abn_verified": False,
        "trust_badge": None,
    }


def validate_match_output(data: Any, candidate_ids: Set[str]) -> List[Dict[str, Any]]:
    """Strictly validate and normalize model output for diagnostic matching.

    Raises StructuredValidationError if output is not a list or contains invalid IDs/scores.
    """
    if not isinstance(data, list):
        raise StructuredValidationError(f"Expected JSON list of matches, got {type(data).__name__}")
    if len(data) == 0:
        raise StructuredValidationError("Model returned empty match list")

    validated: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise StructuredValidationError(f"Match item must be an object, got {type(item).__name__}")
        t_id = str(item.get("trainer_id") or "").strip()
        if not t_id or t_id not in candidate_ids:
            raise StructuredValidationError(f"Match returned invalid or unrecognised trainer_id: {t_id!r}")
        raw_score = item.get("score")
        try:
            score = float(raw_score)
        except (ValueError, TypeError):
            raise StructuredValidationError(f"Match score must be a float: {raw_score!r}")
        if not (0.0 <= score <= 1.0):
            raise StructuredValidationError(f"Match score {score} out of range [0.0, 1.0]")
        reasoning = str(item.get("reasoning") or "").strip()
        if not reasoning:
            raise StructuredValidationError("Match reasoning is required and cannot be blank")

        validated.append({
            "trainer_id": t_id,
            "score": round(score, 2),
            "reasoning": reasoning,
        })

    validated.sort(key=lambda x: x["score"], reverse=True)
    return validated[:3]


def validate_score_output(data: Any) -> Dict[str, Any]:
    """Strictly validate verification scoring output from model."""
    if not isinstance(data, dict):
        raise StructuredValidationError(f"Expected JSON object for score, got {type(data).__name__}")

    raw_conf = data.get("confidence")
    try:
        conf = float(raw_conf)
    except (ValueError, TypeError):
        raise StructuredValidationError(f"Confidence must be float, got {raw_conf!r}")
    if not (0.0 <= conf <= 1.0):
        raise StructuredValidationError(f"Confidence {conf} out of bounds [0.0, 1.0]")

    reasoning = str(data.get("reasoning") or "").strip()
    if not reasoning:
        raise StructuredValidationError("Reasoning explanation cannot be blank")

    raw_signals = data.get("signals", [])
    if not isinstance(raw_signals, list):
        raw_signals = [str(raw_signals)]
    signals = [str(s).strip() for s in raw_signals if str(s).strip()]

    # Safety boundary: Never accept ABN verified or published flags from model output
    return {
        "confidence": round(conf, 2),
        "reasoning": reasoning,
        "signals": signals,
        "published": False,
        "abn_verified": False,
    }


# ---------- Deterministic Heuristic Fallbacks ----------

def _deterministic_extract_trainer_source(source: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic, zero-dependency extraction of trainer attributes from source text."""
    if isinstance(source, dict):
        text = " ".join(
            str(v)
            for k, v in source.items()
            if k in {"raw_text", "bio", "services", "description", "name", "website", "suburb"}
        )
    else:
        text = str(source or "")

    low = text.lower()
    signals: List[str] = []

    # 1. Philosophy
    if re.search(r"(force[- ]free|positive\s*reinforce|r\+|rewards?[- ]based|fear[- ]free)", low):
        philosophy = "Positive Reinforcement / Force-Free"
        signals.append("Positive reinforcement / force-free terminology detected")
    elif re.search(r"(balanced|e[- ]collar|prong|correction|dominance)", low):
        philosophy = "Balanced"
        signals.append("Balanced training terminology detected")
    else:
        philosophy = "Positive Reinforcement / Force-Free"
        signals.append("Standard positive default applied")

    # 2. Specialties
    specialties: List[str] = []
    spec_patterns = [
        (r"puppy|puppies", "puppy_training"),
        (r"reactiv|barking|lunging", "leash_reactivity"),
        (r"separat.*anxiet|anxious|anxiety", "separation_anxiety"),
        (r"obedienc|manners|recall|sit\s*stay", "obedience"),
        (r"aggress|bite|growl", "aggression"),
        (r"behavio[u]?r", "behavioral_consultation"),
        (r"agilit", "agility"),
        (r"scent|nosework", "scent_work"),
    ]
    for pattern, spec in spec_patterns:
        if re.search(pattern, low):
            specialties.append(spec)
    if not specialties:
        specialties = ["puppy_training", "obedience"]

    # 3. Service formats
    formats: List[str] = []
    if re.search(r"in[- ]home|home\s*visit|mobile|private", low):
        formats.append("in_home")
    if re.search(r"facility|centre|center|hall|studio|grounds", low):
        formats.append("facility")
    if re.search(r"board|bootcamp|residential", low):
        formats.append("board_and_train")
    if re.search(r"online|zoom|virtual|remote", low):
        formats.append("online")
    if not formats:
        formats = ["in_home"]

    # 4. Suburbs
    suburbs = ["Melbourne-Wide Mobile"]
    suburb_pattern = (
        r"\b(richmond|brunswick|st kilda|south yarra|fitzroy|hawthorn|camberwell|brighton|geelong|ballarat)\b"
    )
    suburb_match = re.search(suburb_pattern, low)
    if suburb_match:
        suburbs = [suburb_match.group(1).title()]

    # 5. Confidence
    confidence = 0.50
    if len(specialties) >= 2:
        confidence += 0.15
    if len(formats) >= 1:
        confidence += 0.10
    if len(text) > 100:
        confidence += 0.05
    confidence = min(0.85, round(confidence, 2))

    return {
        "training_philosophy": philosophy,
        "specialties": specialties,
        "service_formats": formats,
        "serviced_suburbs": suburbs,
        "confidence": confidence,
        "reasoning": "Deterministic heuristic extraction based on source keyword matching.",
        "signals": signals,
        "model": "heuristic-fallback",
        "fallback_used": True,
        "published": False,
        "abn_verified": False,
        "trust_badge": None,
    }


def _heuristic_score(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic business evidence scoring."""
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
        "published": False,
        "abn_verified": False,
    }


def status_for_score(conf: float) -> str:
    """Map evidence confidence score to baseline assessment status.

    SAFETY RULE: AI evidence confidence alone NEVER grants 'verified' status.
    Official verification requires statutory non-AI evidence (e.g., active ABN
    confirmed via ABR Web Services) under canonical P2/P4 contracts.
    """
    if conf >= 0.60:
        return "unverified"
    return "hold"


def route_extraction_confidence(conf: float) -> str:
    """Dual-threshold routing contract from Acquisition & Ingestion Pipeline Spec:
    - Tier 1 (>= 0.85): qualified / eligible for auto-publication if ABN is active
    - Tier 2 (0.50 <= conf < 0.85): review_queue for /ops human review
    - Quarantine (< 0.50): quarantined to ingestion state
    """
    if conf >= 0.85:
        return "qualified"
    elif conf >= 0.50:
        return "review_queue"
    return "quarantine"



def _heuristic_match(query: str, trainers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministic keyword overlap matching based strictly on capability facts (bio & paid tier are EXCLUDED)."""
    q = (query or "").lower()
    tokens = [tok for tok in set(q.split()) if len(tok) > 3]
    scored: List[Dict[str, Any]] = []
    for t in trainers:
        # MP-001: Source documents with capabilities/declarations must always be projected fresh
        proj = (
            build_match_ready_projection(t)
            if ("capabilities" in t or "trainer_declared_at" in t or "projection_version" not in t)
            else t
        )
        if ENABLE_MATCH_READY_PROJECTION_FILTER and not proj.get("match_eligible"):
            continue

        words = (
            (proj.get("name") or t.get("name") or "")
            + " "
            + (proj.get("suburb") or t.get("suburb") or "")
            + " "
            + " ".join(proj.get("specialties") or t.get("specialties") or t.get("services") or [])
            + " "
            + " ".join(proj.get("service_formats") or t.get("service_formats") or [])
            + " "
            + " ".join(proj.get("life_stages") or t.get("life_stages") or [])
            + " "
            + (proj.get("training_philosophy") or t.get("training_philosophy") or t.get("philosophy") or "")
            + " "
            + " ".join(proj.get("serviced_suburbs") or t.get("serviced_suburbs") or [])
        ).lower()
        hits = sum(1 for tok in tokens if tok in words)
        score = min(1.0, 0.40 + 0.15 * hits) if hits > 0 else 0.40
        scored.append(
            {
                "trainer_id": proj.get("trainer_id") or t.get("id"),
                "score": round(score, 2),
                "reasoning": f"Deterministic keyword match ({hits} topic overlaps detected) for owner enquiry.",
                "match_ready": bool(proj.get("match_eligible")),
                "eligibility_reasons": proj.get("eligibility_reasons") or [],
            }
        )
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:3]


# ---------- Prompts and System Instructions ----------

EXTRACTION_SYSTEM = (
    "You are a Melbourne canine industry data extraction analyst for Dog Trainers Directory (DTD). "
    "Given raw unstructured text or scraped business information about a dog trainer, extract structured attributes. "
    "You must return ONLY a JSON object conforming strictly to this schema: "
    "{\n"
    "  \"training_philosophy\": \"Positive Reinforcement / Force-Free\" | \"Balanced\",\n"
    "  \"specialties\": [\"puppy_training\", \"leash_reactivity\", \"separation_anxiety\", \"obedience\", ...],\n"
    "  \"service_formats\": [\"in_home\" | \"facility\" | \"board_and_train\" | \"online\"],\n"
    "  \"serviced_suburbs\": [\"Richmond\", \"South Yarra\", ...],\n"
    "  \"confidence\": float (0.0 to 1.0),\n"
    "  \"reasoning\": \"1-2 concise sentences justifying attributes from text\",\n"
    "  \"signals\": [\"evidence bullet 1\", \"evidence bullet 2\"]\n"
    "}\n"
    "CRITICAL RULES: Do NOT invent facts. Do NOT output markdown or backticks. Return ONLY JSON."
)

MATCH_SYSTEM = (
    "You are a calm, expert dog-training diagnostic advisor in Greater Melbourne, Australia. "
    "Given a list of candidate trainers "
    "(each with id, name, suburb, specialties, service_formats, training_philosophy, life_stages, serviced_suburbs) "
    "and a dog owner's enquiry, assess the best diagnostic fit based strictly on clinical, behavioral, "
    "and logistical relevance. "
    "RANKING INTEGRITY RULE: Paid tier or sponsorship MUST NEVER influence match fit — judge purely on "
    "dog needs and trainer capability. "
    "PROJECTION RULE: Freeform marketing bio, unverified claims, and commercial tiers are excluded. Reason only from structured capability facts. "
    "Return ONLY a JSON array of up to 3 objects with keys:\n"
    "  - trainer_id: string\n"
    "  - score: float (0.0 to 1.0)\n"
    "  - reasoning: 1-2 sentences of explainable diagnostic rationale focused on the dog's specific needs.\n"
    "Return ONLY JSON."
)

VERIFY_SYSTEM = (
    "You are a verification analyst for a Melbourne dog-trainers directory. "
    "Given a business listing and any source evidence, judge how likely it is to "
    "represent a REAL, currently operating dog-training business in or near Melbourne, Australia. "
    "Return ONLY a JSON object with keys: confidence (0.0-1.0 float), reasoning (1-2 sentences), "
    "signals (array of short evidence bullets). Do NOT fabricate facts; reason only from the input. "
    "SAFETY RULE: Do NOT verify an ABN or grant official verification badges; evaluate evidence consistency only."
)

SEO_SYSTEM = (
    "You are an editorial copywriter for a Melbourne dog-trainers directory. Write authentic, non-spammy, "
    "useful copy for a suburb/category landing page. Avoid superlatives that imply we have ranked or rated "
    "businesses. Tone: warm, confident, factual. Return ONLY JSON: {title, meta_description, intro, sections: "
    "[{heading, body}], faq: [{q, a}]}. Keep meta_description <= 160 chars."
)


def _classify_exception(e: Exception, operation: str) -> tuple[str, str, str]:
    """Classify provider exceptions into sanitized (event_type, error_code, message)."""
    err_str = str(e)
    err_lower = err_str.lower()
    if any(k in err_str for k in ("429", "RESOURCE_EXHAUSTED")) or any(k in err_lower for k in ("quota", "rate")):
        return "rate_limit", "RATE_LIMIT_429", f"Gemini {operation} rate limited; deterministic fallback engaged."
    if isinstance(e, StructuredValidationError) or "json" in err_lower or "schema" in err_lower:
        return (
            "malformed_output",
            "SCHEMA_VALIDATION_FAILED",
            f"Gemini {operation} produced malformed or invalid schema output; deterministic fallback engaged.",
        )
    if any(k in err_str for k in ("503", "500")) or any(k in err_lower for k in ("unavailable", "connection")):
        return (
            "unavailable_service",
            "SERVICE_UNAVAILABLE",
            f"Gemini service unavailable ({type(e).__name__}); deterministic fallback engaged.",
        )
    return (
        "provider_error",
        "PROVIDER_ERROR",
        f"Gemini {operation} failed ({type(e).__name__}); deterministic fallback engaged.",
    )


# ---------- Primary Service Implementations ----------

async def extract_trainer_source(
    source: Union[str, Dict[str, Any]],
    *,
    db: Optional[Any] = None,
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract structured trainer attributes from source text using Gemini, with deterministic fallback."""
    # Check if client should be resolved
    active_client = client if client is not None else get_gemini_client()
    if active_client is None:
        return _deterministic_extract_trainer_source(source)

    if isinstance(source, dict):
        text_content = json.dumps(source, ensure_ascii=False)
    else:
        text_content = str(source or "")

    operation = "trainer_source_extraction"
    try:
        config = _generate_content_config(
            response_mime_type="application/json",
            system_instruction=EXTRACTION_SYSTEM,
            temperature=0.1,
        )
        response = await asyncio.wait_for(
            active_client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"Extract structured trainer attributes from this text:\n\n{text_content}",
                config=config,
            ),
            timeout=GEMINI_TIMEOUT_S,
        )
        raw_text = response.text or ""
        parsed = _extract_json(raw_text)
        if not parsed:
            raise StructuredValidationError("Empty or non-JSON output from Gemini model")

        validated = validate_extracted_source(parsed)
        validated["model"] = GEMINI_MODEL
        validated["fallback_used"] = False
        return validated

    except asyncio.TimeoutError:
        await record_degradation_event(
            event_type="timeout",
            error_code="TIMEOUT",
            message=f"Gemini {operation} timed out after {GEMINI_TIMEOUT_S}s; deterministic fallback engaged.",
            operation=operation,
            db=db,
        )
        return _deterministic_extract_trainer_source(source)

    except Exception as e:
        event_type, error_code, msg = _classify_exception(e, operation)
        await record_degradation_event(
            event_type=event_type,
            error_code=error_code,
            message=msg,
            operation=operation,
            db=db,
        )
        return _deterministic_extract_trainer_source(source)


async def match_trainers(
    query: str,
    trainers: List[Dict[str, Any]],
    *,
    db: Optional[Any] = None,
    client: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Explainable diagnostic matching between owner enquiry and trainers.

    Paid tier is deliberately stripped to ensure commercial tier NEVER influences match fit.
    """
    active_client = client if client is not None else get_gemini_client()
    if active_client is None:
        return _heuristic_match(query, trainers)

    if not trainers:
        return []

    # Clean candidate payload: project through build_match_ready_projection
    # Deliberately exclude bio, tier, billing_status, pricing, or confidence scores
    candidates = []
    candidate_ids: Set[str] = set()
    diagnostics_by_id: Dict[str, Dict[str, Any]] = {}
    for t in trainers:
        # MP-001: Source documents with capabilities/declarations must always be projected fresh
        proj = (
            build_match_ready_projection(t)
            if ("capabilities" in t or "trainer_declared_at" in t or "projection_version" not in t)
            else t
        )
        if ENABLE_MATCH_READY_PROJECTION_FILTER and not proj.get("match_eligible"):
            continue
        t_id = str(proj.get("trainer_id") or t.get("id") or "")
        candidate_ids.add(t_id)
        diagnostics_by_id[t_id] = {
            "match_ready": bool(proj.get("match_eligible")),
            "eligibility_reasons": proj.get("eligibility_reasons") or [],
        }
        candidates.append({
            "id": t_id,
            "name": proj.get("name") or t.get("name"),
            "suburb": proj.get("suburb") or t.get("suburb"),
            "specialties": proj.get("specialties") or t.get("specialties") or t.get("services") or [],
            "service_formats": proj.get("service_formats") or t.get("service_formats") or [],
            "training_philosophy": proj.get("training_philosophy") or t.get("training_philosophy") or t.get("philosophy") or "",
            "life_stages": proj.get("life_stages") or t.get("life_stages") or [],
            "serviced_suburbs": proj.get("serviced_suburbs") or t.get("serviced_suburbs") or [],
        })

    if not candidates:
        return []

    operation = "diagnostic_matching"
    try:
        config = _generate_content_config(
            response_mime_type="application/json",
            system_instruction=MATCH_SYSTEM,
            temperature=0.2,
        )
        prompt = (
            f"Dog owner enquiry: {query}\n\n"
            f"Candidate trainers:\n{json.dumps(candidates, ensure_ascii=False)}"
        )
        response = await asyncio.wait_for(
            active_client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            ),
            timeout=GEMINI_TIMEOUT_S,
        )
        raw_text = response.text or ""
        parsed = _extract_json(raw_text)
        if not parsed:
            raise StructuredValidationError("Empty or non-JSON output from Gemini match")

        results = validate_match_output(parsed, candidate_ids)
        for item in results:
            t_id = str(item.get("trainer_id") or "")
            if t_id in diagnostics_by_id:
                item["match_ready"] = diagnostics_by_id[t_id]["match_ready"]
                item["eligibility_reasons"] = diagnostics_by_id[t_id]["eligibility_reasons"]
        return results

    except asyncio.TimeoutError:
        await record_degradation_event(
            event_type="timeout",
            error_code="TIMEOUT",
            message=f"Gemini {operation} timed out after {GEMINI_TIMEOUT_S}s; deterministic fallback engaged.",
            operation=operation,
            db=db,
        )
        return _heuristic_match(query, trainers)

    except Exception as e:
        event_type, error_code, msg = _classify_exception(e, operation)
        await record_degradation_event(
            event_type=event_type,
            error_code=error_code,
            message=msg,
            operation=operation,
            db=db,
        )
        return _heuristic_match(query, trainers)


async def score_trainer(
    payload: Dict[str, Any],
    *,
    db: Optional[Any] = None,
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Score trainer business evidence using Gemini, with deterministic fallback.

    Safety rule: AI output alone NEVER verifies ABN or marks profile published.
    """
    active_client = client if client is not None else get_gemini_client()
    if active_client is None:
        return _heuristic_score(payload)

    operation = "trainer_verification_scoring"
    try:
        config = _generate_content_config(
            response_mime_type="application/json",
            system_instruction=VERIFY_SYSTEM,
            temperature=0.1,
        )
        response = await asyncio.wait_for(
            active_client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=(
                    "Assess business validity for this dog trainer evidence:\n"
                    f"{json.dumps(payload, ensure_ascii=False)}"
                ),
                config=config,
            ),
            timeout=GEMINI_TIMEOUT_S,
        )
        raw_text = response.text or ""
        parsed = _extract_json(raw_text)
        if not parsed:
            raise StructuredValidationError("Empty or non-JSON output from Gemini scoring")

        validated = validate_score_output(parsed)
        validated["model"] = GEMINI_MODEL
        validated["fallback_used"] = False
        return validated

    except asyncio.TimeoutError:
        await record_degradation_event(
            event_type="timeout",
            error_code="TIMEOUT",
            message=f"Gemini {operation} timed out after {GEMINI_TIMEOUT_S}s; deterministic fallback engaged.",
            operation=operation,
            db=db,
        )
        return _heuristic_score(payload)

    except Exception as e:
        event_type, error_code, msg = _classify_exception(e, operation)
        await record_degradation_event(
            event_type=event_type,
            error_code=error_code,
            message=msg,
            operation=operation,
            db=db,
        )
        return _heuristic_score(payload)


async def generate_seo_copy(
    suburb: str,
    category: str,
    *,
    db: Optional[Any] = None,
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generate SEO copy with Gemini when configured, retaining deterministic template fallback."""
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
                "body": (
                    "Check qualifications, training philosophy, and whether the trainer offers "
                    "in-home or group sessions."
                ),
            }
        ],
        "faq": [
            {
                "q": "How are trainers verified?",
                "a": "Each listing receives an evidence-based confidence score from public sources before publishing.",
            }
        ],
    }

    active_client = client if client is not None else get_gemini_client()
    if active_client is None:
        return fallback

    operation = "seo_copy_generation"
    try:
        config = _generate_content_config(
            response_mime_type="application/json",
            system_instruction=SEO_SYSTEM,
            temperature=0.3,
        )
        response = await asyncio.wait_for(
            active_client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"Generate SEO copy for suburb={suburb}, category={category}",
                config=config,
            ),
            timeout=GEMINI_TIMEOUT_S,
        )
        raw_text = response.text or ""
        parsed = _extract_json(raw_text)
        if isinstance(parsed, dict) and "title" in parsed and "meta_description" in parsed:
            return parsed
        raise StructuredValidationError("Invalid SEO copy schema from Gemini")

    except asyncio.TimeoutError:
        await record_degradation_event(
            event_type="timeout",
            error_code="TIMEOUT",
            message=f"Gemini {operation} timed out; fallback engaged.",
            operation=operation,
            db=db,
        )
        return fallback

    except Exception as e:
        await record_degradation_event(
            event_type="provider_error",
            error_code="SEO_GENERATION_FAILED",
            message=f"Gemini {operation} failed ({type(e).__name__}); fallback engaged.",
            operation=operation,
            db=db,
        )
        return fallback


# ---------- Constrained Gemini Matching Adapter (Package P3) ----------

MATCHING_SYSTEM_INSTRUCTION = (
    "You are DTD’s constrained fit assessor. Assess fit only among the supplied, already eligible trainer candidates. "
    "You are not a safety triage service and must not give veterinary, medical, legal, behavioural-treatment, handling, "
    "or emergency advice. Use only the supplied structured fields and sanitised owner signals. Do not infer, invent, "
    "embellish, or use commercial status. Never claim availability, credentials, outcomes, personality traits, diagnoses, "
    "guarantees, rankings, reviews, or facts not present in the input. Return JSON only. Every trainer_id must be from "
    "the supplied candidate list. Return a semantic_fit from 0.00 to 1.00 and only approved factual reason codes. "
    "Do not write public-facing prose. The application renders explanations from validated reason codes and permitted facts."
)


def build_gemini_matching_input(
    request: Any,
    eligible_candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct constrained allow-list input payload for Gemini matching."""
    try:
        from services.matching_contract_v2 import sanitize_behaviour_description
    except ImportError:
        from backend.services.matching_contract_v2 import sanitize_behaviour_description

    age_months = getattr(request, "dog_age_months", 12)
    if age_months < 6:
        dog_age_category = "puppy"
    elif age_months <= 18:
        dog_age_category = "adolescent"
    elif age_months <= 83:
        dog_age_category = "adult"
    else:
        dog_age_category = "senior"

    raw_desc = getattr(request, "behaviour_description", "") or ""
    sanitised_desc = sanitize_behaviour_description(raw_desc)

    owner_signals = {
        "dog_age_category": dog_age_category,
        "primary_concerns": list(getattr(request, "primary_concerns", [])),
        "service_format": str(getattr(request, "service_format", "any")),
        "method_preference": str(getattr(request, "method_preference", "no_preference")),
        "behaviour_description": sanitised_desc,
    }

    candidates_input = []
    for cand in eligible_candidates:
        cid = str(cand.get("trainer_id") or cand.get("id"))
        raw_dc = cand.get("delivery_constraints")
        if isinstance(raw_dc, dict):
            dc_items = [
                f"{k}:{v}"
                for k, v in sorted(raw_dc.items())
                if v is not None and k in ("in_home_available", "facility_available", "travel_distance_km")
            ]
        elif isinstance(raw_dc, list):
            dc_items = [str(x) for x in raw_dc]
        else:
            dc_items = []

        candidates_input.append({
            "trainer_id": cid,
            "specialties": list(cand.get("specialties") or []),
            "service_formats": list(cand.get("service_formats") or []),
            "life_stages": list(cand.get("life_stages") or []),
            "training_philosophy": cand.get("training_philosophy") or None,
            "catchment_type": str(cand.get("catchment_type") or "specific_suburbs"),
            "serviced_suburbs": list(cand.get("serviced_suburbs") or []),
            "delivery_constraints": dc_items,
        })

    return {
        "contract_version": "v2",
        "owner": owner_signals,
        "candidates": candidates_input,
    }


class GeminiMatchingAdapter:
    """Production typed async matching adapter using configured Google GenAI/Vertex client.

    Governance (Contract v2 Section 5, DF-019, DF-023, DF-026):
    - System instruction restricts model to constrained fit assessor.
    - Input allow-list: contract_version, owner (dog_age_category, primary_concerns, service_format,
      method_preference, sanitised description), and candidates (trainer_id, specialties, service_formats,
      life_stages, training_philosophy, catchment_type, serviced_suburbs, delivery_constraints).
    - NEVER sends commercial tier, sponsorship, pricing, bios, reviews, URLs, acquisition evidence,
      contact fields, raw trainer documents, or unprojected candidates.
    - Validates candidate IDs against eligible pool, validates semantic_fit range, validates reason codes.
    - Server renders public explanation deterministically from permitted facts.
    - 5.0s timeout enforced.
    - Raises typed exceptions (GeminiTimeoutError, GeminiRateLimitError, GeminiUnavailableError, ValidationError).
    - Records sanitised degradation events (provider/model, error_type, latency_ms, fallback_used, decision_state, policy_version).
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        model: Optional[str] = None,
        timeout_s: Optional[float] = None,
        db: Optional[Any] = None,
    ):
        self.client = client if client is not None else get_gemini_client()
        self.model = model or GEMINI_MODEL
        self.timeout_s = timeout_s if timeout_s is not None else GEMINI_TIMEOUT_S
        self.db = db

    async def call_model_async(
        self,
        request: Any,
        eligible_candidates: List[Dict[str, Any]],
        search_scope: Any = "local",
        triage_state: Optional[Any] = None,
        *,
        candidate_scopes: Optional[Dict[str, str]] = None,
        canonical_locality: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute constrained fit assessment through Gemini or raise typed degradation error."""
        import time
        from pydantic import ValidationError

        try:
            from services.matching_contract_v2 import (
                GeminiTimeoutError,
                GeminiRateLimitError,
                GeminiUnavailableError,
                DecisionState,
                SearchScope,
                QUALIFICATION_THRESHOLD,
                MAX_RECOMMENDED_CANDIDATES,
                apply_fair_presentation,
                compute_deterministic_fit,
            )
        except ImportError:
            from backend.services.matching_contract_v2 import (
                GeminiTimeoutError,
                GeminiRateLimitError,
                GeminiUnavailableError,
                DecisionState,
                SearchScope,
                QUALIFICATION_THRESHOLD,
                MAX_RECOMMENDED_CANDIDATES,
                apply_fair_presentation,
                compute_deterministic_fit,
            )

        # PyMongo/Motor database objects deliberately reject truth-value
        # evaluation. An explicitly supplied request database is valid even
        # though ``bool(database)`` raises NotImplementedError.
        target_db = db if db is not None else self.db
        start_t = time.perf_counter()
        scope_val = search_scope.value if hasattr(search_scope, "value") else str(search_scope)

        if self.client is None:
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            await record_degradation_event(
                event_type="unavailable_service",
                error_code="UNAVAILABLE_UNCONFIGURED",
                message="Gemini client is unconfigured or unavailable; deterministic fallback engaged.",
                operation="matching",
                latency_ms=latency_ms,
                decision_state="degraded_fallback",
                policy_version="v2",
                db=target_db,
            )
            raise GeminiUnavailableError("Gemini client is unconfigured or unavailable")

        if not eligible_candidates:
            return {
                "decision_state": DecisionState.NO_CONFIRMED_MATCH.value,
                "candidates": [],
                "reason_codes": ["no_qualified_candidates"],
                "search_scope": scope_val,
            }

        input_payload = build_gemini_matching_input(request, eligible_candidates)
        config = _generate_content_config(
            response_mime_type="application/json",
            system_instruction=MATCHING_SYSTEM_INSTRUCTION,
            temperature=0.1,
        )

        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model,
                    contents=f"Evaluate fit for these candidates:\n\n{json.dumps(input_payload, ensure_ascii=False)}",
                    config=config,
                ),
                timeout=self.timeout_s,
            )
        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            await record_degradation_event(
                event_type="timeout",
                error_code="TIMEOUT",
                message=f"Gemini matching timed out after {self.timeout_s}s; deterministic fallback engaged.",
                operation="matching",
                latency_ms=latency_ms,
                decision_state="degraded_fallback",
                policy_version="v2",
                db=target_db,
            )
            raise GeminiTimeoutError(f"Gemini matching timed out after {self.timeout_s}s")
        except Exception as err:
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            err_str = str(err)
            err_lower = err_str.lower()
            if "429" in err_str or "quota" in err_lower or "resource_exhausted" in err_lower:
                await record_degradation_event(
                    event_type="rate_limit",
                    error_code="RATE_LIMIT_429",
                    message="Gemini matching rate limited; deterministic fallback engaged.",
                    operation="matching",
                    latency_ms=latency_ms,
                    decision_state="degraded_fallback",
                    policy_version="v2",
                    db=target_db,
                )
                raise GeminiRateLimitError(f"Gemini API quota exceeded (HTTP 429): {err_str}")
            else:
                await record_degradation_event(
                    event_type="unavailable_service",
                    error_code="SERVICE_UNAVAILABLE",
                    message=f"Gemini matching unavailable ({type(err).__name__}); deterministic fallback engaged.",
                    operation="matching",
                    latency_ms=latency_ms,
                    decision_state="degraded_fallback",
                    policy_version="v2",
                    db=target_db,
                )
                raise GeminiUnavailableError(f"Gemini matching service unavailable: {err_str}")

        raw_text = getattr(response, "text", "") or ""
        parsed = _extract_json(raw_text)
        if not isinstance(parsed, dict) or "candidates" not in parsed or not isinstance(parsed["candidates"], list):
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            await record_degradation_event(
                event_type="malformed_output",
                error_code="MALFORMED_OUTPUT",
                message="Gemini matching produced malformed or non-JSON output; deterministic fallback engaged.",
                operation="matching",
                latency_ms=latency_ms,
                decision_state="degraded_fallback",
                policy_version="v2",
                db=target_db,
            )
            raise ValueError("Model returned malformed or non-JSON output")

        eligible_map = {str(c.get("trainer_id") or c.get("id")): c for c in eligible_candidates}
        approved_codes = {
            "capability_concern_match",
            "life_stage_match",
            "format_match",
            "method_preference_match",
            "service_area_match",
            "expanded_service_area",
            "serious_behavioural_support",
        }

        cards_data = []
        for item in parsed["candidates"]:
            if not isinstance(item, dict):
                raise ValueError("Candidate entry is not a dictionary")
            cid = str(item.get("trainer_id") or "")
            if cid not in eligible_map:
                raise ValueError(f"Model returned unauthorized candidate ID not in eligible pool: {cid}")

            cand_doc = eligible_map[cid]
            fit_raw = item.get("semantic_fit")
            if not isinstance(fit_raw, (int, float)):
                raise ValueError(f"Invalid semantic_fit type for {cid}: {fit_raw}")
            fit_score = round(float(fit_raw), 4)
            if not (0.0 <= fit_score <= 1.0):
                raise ValueError(f"semantic_fit out of bounds [0.0, 1.0]: {fit_score}")

            raw_codes = item.get("reason_codes") or []
            if not isinstance(raw_codes, list):
                raise ValueError("reason_codes must be a list")
            val_codes = [c for c in raw_codes if str(c) in approved_codes]
            if not val_codes:
                val_codes = ["capability_concern_match"]

            cand_scope = candidate_scopes.get(cid, scope_val) if candidate_scopes else scope_val

            # Server renders explanation deterministically from permitted facts
            _, _, explanation = compute_deterministic_fit(
                cand_doc, request, search_scope=cand_scope, triage_state=triage_state
            )

            if fit_score >= QUALIFICATION_THRESHOLD:
                cards_data.append({
                    "trainer_id": cid,
                    "match_score": fit_score,
                    "reason_codes": val_codes,
                    "explanation": explanation,
                    "search_scope": cand_scope,
                    "tier": cand_doc.get("tier", "unclaimed"),
                    "policy_penalty": cand_doc.get("policy_penalty", 0.0),
                })

        presented = apply_fair_presentation(cards_data, max_results=MAX_RECOMMENDED_CANDIDATES)

        if not presented:
            return {
                "decision_state": DecisionState.NO_CONFIRMED_MATCH.value,
                "candidates": [],
                "reason_codes": ["no_qualified_candidates"],
                "search_scope": scope_val,
            }

        any_expanded = any(p.get("search_scope") == SearchScope.EXPANDED.value for p in presented)
        dec_state = (
            DecisionState.LIMITED_LOCAL_RESULTS.value
            if any_expanded
            else DecisionState.RECOMMENDATIONS.value
        )

        final_cards = [
            {
                "trainer_id": p["trainer_id"],
                "match_score": p["match_score"],
                "reason_codes": p["reason_codes"],
                "explanation": p["explanation"],
                "search_scope": p["search_scope"],
            }
            for p in presented
        ]

        return {
            "decision_state": dec_state,
            "candidates": final_cards,
            "reason_codes": final_cards[0]["reason_codes"] if final_cards else [],
            "search_scope": scope_val,
        }

    def call_model(
        self,
        request: Any,
        eligible_candidates: List[Dict[str, Any]],
        search_scope: Any = "local",
        triage_state: Optional[Any] = None,
        *,
        candidate_scopes: Optional[Dict[str, str]] = None,
        canonical_locality: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for offline/sync testing."""
        import concurrent.futures
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    lambda: asyncio.run(self.call_model_async(
                        request, eligible_candidates, search_scope, triage_state,
                        candidate_scopes=candidate_scopes, canonical_locality=canonical_locality, db=db
                    ))
                )
                return future.result()
        else:
            return asyncio.run(self.call_model_async(
                request, eligible_candidates, search_scope, triage_state,
                candidate_scopes=candidate_scopes, canonical_locality=canonical_locality, db=db
            ))
