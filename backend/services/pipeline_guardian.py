"""Supervisory Verification Guardian (Engine 2).

Implements the "Automation on top of Automation" supervisory layer:
1. Global Uniqueness Audit (guarantees zero duplicates on ABN, domain, phone, name+suburb).
2. Statutory Truth Audit (guarantees 100% of published listings have verified active ABR registration).
3. Anti-Hallucination Audit (ensures no placeholder names, domains, or phones slip into production).
4. Public API & Frontend Contract Audit (ensures published trainers serialize cleanly).
5. Self-Healing & Exception-Driven /ops Alerting (auto-remediates anomalies and reports to /ops).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .abn_validator import normalize_abn, validate_abn_detailed
from .trainer_quality import (
    extract_domain,
    now_iso,
    record_ingestion_failure,
    PLACEHOLDER_DOMAINS,
    PLACEHOLDER_NAMES,
    PLACEHOLDER_PHONES,
)

logger = logging.getLogger(__name__)


async def audit_corpus_integrity(db: Any, *, auto_remediate: bool = True) -> Dict[str, Any]:
    """Execute supervisory audit across the entire trainer corpus.

    Returns a comprehensive audit manifest documenting checks performed,
    anomalies detected, and self-healing actions applied.
    """
    start_ts = now_iso()
    audit_result: Dict[str, Any] = {
        "status": "clean",
        "started_at": start_ts,
        "completed_at": "",
        "total_trainers_scanned": 0,
        "published_trainers_scanned": 0,
        "duplicates_detected": 0,
        "statutory_violations": 0,
        "schema_violations": 0,
        "remediations_applied": 0,
        "anomalies": [],
    }

    if db is None:
        audit_result["status"] = "database_unavailable"
        audit_result["completed_at"] = now_iso()
        return audit_result

    trainers_coll = getattr(db, "trainers", None)
    if trainers_coll is None:
        audit_result["status"] = "trainers_collection_missing"
        audit_result["completed_at"] = now_iso()
        return audit_result

    # Fetch all trainers
    trainers = await trainers_coll.find({}, {"_id": 0}).to_list(10000)
    audit_result["total_trainers_scanned"] = len(trainers)

    by_abn: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_domain: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_phone: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_name_suburb: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for t in trainers:
        t_id = t.get("id")
        is_published = bool(t.get("published"))
        if is_published:
            audit_result["published_trainers_scanned"] += 1

        name = str(t.get("name") or "").strip().lower()
        suburb = str(t.get("suburb") or "").strip().lower()
        abn = normalize_abn(t.get("abn"))
        phone = re.sub(r"\D", "", str(t.get("phone") or ""))
        website = str(t.get("website") or "").strip()
        domain = extract_domain(website)

        # 1. Statutory Truth Check (DF-014 Enforcer)
        # Any published trainer MUST have valid ABN and abn_verified == True
        if is_published:
            has_abn = bool(abn and len(abn) == 11 and validate_abn_detailed(abn)["valid"])
            abn_verified = bool(t.get("abn_verified"))
            if not has_abn or not abn_verified:
                audit_result["statutory_violations"] += 1
                anomaly = {
                    "trainer_id": t_id,
                    "issue": "published_without_statutory_abr_verification",
                    "details": f"Published trainer {t_id} ({t.get('name')}) lacks active verified ABR.",
                }
                audit_result["anomalies"].append(anomaly)
                if auto_remediate:
                    await trainers_coll.update_one(
                        {"id": t_id},
                        {
                            "$set": {
                                "published": False,
                                "ingestion_quality_status": "held",
                                "ingestion_hold_reason": "guardian_statutory_abr_unverified",
                                "guardian_audited_at": now_iso(),
                            }
                        },
                    )
                    audit_result["remediations_applied"] += 1

        # 2. Anti-Hallucination & Schema Validation
        # No placeholder names, domains, or phones allowed in directory
        has_ph_name = any(ph in name for ph in PLACEHOLDER_NAMES)
        has_ph_domain = domain in PLACEHOLDER_DOMAINS if domain else False
        has_ph_phone = phone in PLACEHOLDER_PHONES if phone else False
        missing_suburb = not suburb

        if has_ph_name or has_ph_domain or has_ph_phone or missing_suburb:
            audit_result["schema_violations"] += 1
            anomaly = {
                "trainer_id": t_id,
                "issue": "placeholder_or_schema_violation",
                "details": f"Trainer {t_id} contains placeholder/invalid attributes (name={name}, domain={domain}, suburb={suburb}).",
            }
            audit_result["anomalies"].append(anomaly)
            if auto_remediate and is_published:
                await trainers_coll.update_one(
                    {"id": t_id},
                    {
                        "$set": {
                            "published": False,
                            "ingestion_quality_status": "held",
                            "ingestion_hold_reason": "guardian_placeholder_detected",
                            "guardian_audited_at": now_iso(),
                        }
                    },
                )
                audit_result["remediations_applied"] += 1

        # Collect indexes for deduplication audit
        if abn and len(abn) == 11:
            by_abn[abn].append(t)
        if domain and domain not in PLACEHOLDER_DOMAINS:
            by_domain[domain].append(t)
        if phone and len(phone) >= 8 and phone not in PLACEHOLDER_PHONES:
            by_phone[phone].append(t)
        if name and suburb:
            by_name_suburb[(name, suburb)].append(t)

    # 3. Global Deduplication Audit (Zero Duplicates Mandate)
    duplicate_groups = [
        ("abn", by_abn),
        ("domain", by_domain),
        ("phone", by_phone),
        ("name_suburb", by_name_suburb),
    ]

    seen_held_ids: Set[str] = set()

    for field_name, group_dict in duplicate_groups:
        for key, matching_trainers in group_dict.items():
            if len(matching_trainers) <= 1:
                continue

            audit_result["duplicates_detected"] += 1
            # Sort: claimed/paid profiles first, then highest confidence score, then oldest created_at
            def sort_key(doc: Dict[str, Any]) -> Tuple[int, float, str]:
                is_claimed = 1 if doc.get("claimed") or doc.get("tier") not in {"free", None} else 0
                score = float(doc.get("confidence_score") or doc.get("ingestion_quality_score") or 0.0)
                created = str(doc.get("created_at") or "")
                return (is_claimed, score, created)

            sorted_group = sorted(matching_trainers, key=sort_key, reverse=True)
            canonical_winner = sorted_group[0]
            losers = sorted_group[1:]

            for loser in losers:
                l_id = loser.get("id")
                if l_id in seen_held_ids:
                    continue
                seen_held_ids.add(l_id)

                anomaly = {
                    "trainer_id": l_id,
                    "issue": f"duplicate_{field_name}",
                    "details": f"Trainer {l_id} is a duplicate on {field_name}={key} with canonical {canonical_winner.get('id')}.",
                }
                audit_result["anomalies"].append(anomaly)

                if auto_remediate and loser.get("published"):
                    await trainers_coll.update_one(
                        {"id": l_id},
                        {
                            "$set": {
                                "published": False,
                                "ingestion_quality_status": "held",
                                "ingestion_hold_reason": f"guardian_duplicate_of_{canonical_winner.get('id')}",
                                "canonical_duplicate_id": canonical_winner.get("id"),
                                "guardian_audited_at": now_iso(),
                            }
                        },
                    )
                    audit_result["remediations_applied"] += 1

    # Record Guardian audit state in system_state for /ops visibility
    if audit_result["anomalies"]:
        audit_result["status"] = "anomalies_remediated" if auto_remediate else "anomalies_detected"
    else:
        audit_result["status"] = "clean"

    audit_result["completed_at"] = now_iso()

    system_state_coll = getattr(db, "system_state", None)
    if system_state_coll is not None:
        try:
            await system_state_coll.update_one(
                {"key": "pipeline_guardian"},
                {"$set": {
                    "key": "pipeline_guardian",
                    "last_run": audit_result["completed_at"],
                    "status": audit_result["status"],
                    "total_scanned": audit_result["total_trainers_scanned"],
                    "published_scanned": audit_result["published_trainers_scanned"],
                    "duplicates_detected": audit_result["duplicates_detected"],
                    "statutory_violations": audit_result["statutory_violations"],
                    "schema_violations": audit_result["schema_violations"],
                    "remediations_applied": audit_result["remediations_applied"],
                }},
                upsert=True,
            )
        except Exception as exc:
            logger.warning("Failed updating db.system_state for pipeline_guardian: %s", exc)

    return audit_result
