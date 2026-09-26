"""Unit tests for Supervisory Verification Guardian (Engine 2).

Verifies:
- Clean corpus audit with zero anomalies.
- Statutory truth enforcement (DF-014 enforcer: auto-unpublishing records lacking active ABR).
- Global deduplication audit (remediating duplicate ABNs/domains, protecting claimed winner).
- Anti-hallucination / placeholder detection.
- Persistence of audit state into db.system_state.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

import pytest

from services import pipeline_guardian


class _MockCollection:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None):
        self.rows: List[Dict[str, Any]] = [dict(r) for r in (rows or [])]

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        query = query or {}
        matched = []
        for r in self.rows:
            match = True
            for k, v in query.items():
                if isinstance(v, dict) and "$regex" in v:
                    val = str(r.get(k) or "")
                    flags = re.IGNORECASE if v.get("$options") == "i" else 0
                    if not re.search(v["$regex"], val, flags):
                        match = False
                        break
                elif r.get(k) != v:
                    match = False
                    break
            if match:
                matched.append(r.copy())

        class _Cursor:
            def __init__(self, items):
                self.items = items
            def limit(self, n):
                return _Cursor(self.items[:n])
            async def to_list(self, n=None):
                return self.items[:n] if n is not None else self.items
        return _Cursor(matched)

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        for r in self.rows:
            match = True
            for k, v in query.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                return r.copy()
        return None

    async def insert_one(self, doc: Dict[str, Any]) -> None:
        self.rows.append(doc.copy())

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> None:
        target = None
        for r in self.rows:
            match = True
            for k, v in query.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                target = r
                break
        if target is not None:
            if "$set" in update:
                target.update(update["$set"])
        elif upsert:
            new_doc = query.copy()
            if "$set" in update:
                new_doc.update(update["$set"])
            self.rows.append(new_doc)


class _MockDB:
    def __init__(self):
        self.trainers = _MockCollection()
        self.system_state = _MockCollection()


def test_audit_corpus_integrity_clean():
    db = _MockDB()
    clean_trainer = {
        "id": "t1",
        "name": "Kintala Dog Training",
        "suburb": "Heidelberg",
        "website": "https://kintala.com.au",
        "phone": "+61394575455",
        "abn": "53 780 168 767",
        "abn_verified": True,
        "published": True,
    }
    asyncio.run(db.trainers.insert_one(clean_trainer))

    result = asyncio.run(pipeline_guardian.audit_corpus_integrity(db, auto_remediate=True))
    assert result["status"] == "clean"
    assert result["total_trainers_scanned"] == 1
    assert result["published_trainers_scanned"] == 1
    assert result["duplicates_detected"] == 0
    assert result["statutory_violations"] == 0
    assert result["schema_violations"] == 0
    assert result["remediations_applied"] == 0


def test_audit_corpus_integrity_enforces_statutory_abr():
    """Guardian must auto-unpublish listings marked published without verified active ABR."""
    db = _MockDB()
    invalid_published = {
        "id": "t_invalid",
        "name": "Unverified Listing",
        "suburb": "Brunswick",
        "website": "https://unverified.com.au",
        "phone": "+61411222333",
        "abn": "",
        "abn_verified": False,
        "published": True,  # Violation!
    }
    asyncio.run(db.trainers.insert_one(invalid_published))

    result = asyncio.run(pipeline_guardian.audit_corpus_integrity(db, auto_remediate=True))
    assert result["statutory_violations"] == 1
    assert result["remediations_applied"] == 1

    # Check that trainer was unpublished and held
    trainer = db.trainers.rows[0]
    assert trainer["published"] is False
    assert trainer["ingestion_quality_status"] == "held"
    assert trainer["ingestion_hold_reason"] == "guardian_statutory_abr_unverified"


def test_audit_corpus_integrity_remediates_duplicates():
    """Guardian detects duplicate on ABN or domain, holding loser and keeping claimed winner."""
    db = _MockDB()
    winner_claimed = {
        "id": "t_claimed",
        "name": "Melbourne Dog Training",
        "suburb": "Richmond",
        "website": "https://melbournedogtraining.com.au",
        "phone": "+61400111222",
        "abn": "53780168767",
        "abn_verified": True,
        "published": True,
        "claimed": True,
        "tier": "pro",
    }
    loser_unclaimed = {
        "id": "t_loser",
        "name": "Melbourne Dog Training Duplicate",
        "suburb": "Richmond",
        "website": "https://melbournedogtraining.com.au",
        "phone": "+61400111222",
        "abn": "53780168767",
        "abn_verified": True,
        "published": True,
        "claimed": False,
        "tier": "free",
    }
    asyncio.run(db.trainers.insert_one(winner_claimed))
    asyncio.run(db.trainers.insert_one(loser_unclaimed))

    result = asyncio.run(pipeline_guardian.audit_corpus_integrity(db, auto_remediate=True))
    assert result["duplicates_detected"] >= 1
    assert result["remediations_applied"] >= 1

    # Winner stays published
    w = next(t for t in db.trainers.rows if t["id"] == "t_claimed")
    assert w["published"] is True

    # Loser is unpublished and marked as duplicate
    l = next(t for t in db.trainers.rows if t["id"] == "t_loser")
    assert l["published"] is False
    assert l["ingestion_quality_status"] == "held"
    assert "guardian_duplicate" in l["ingestion_hold_reason"]


def test_audit_corpus_integrity_catches_placeholders():
    """Guardian detects placeholder names, domains, or phone numbers."""
    db = _MockDB()
    placeholder_trainer = {
        "id": "t_ph",
        "name": "Test Dog Trainer",
        "suburb": "Carlton",
        "website": "https://example.com",
        "phone": "0400000000",
        "abn": "53780168767",
        "abn_verified": True,
        "published": True,
    }
    asyncio.run(db.trainers.insert_one(placeholder_trainer))

    result = asyncio.run(pipeline_guardian.audit_corpus_integrity(db, auto_remediate=True))
    assert result["schema_violations"] >= 1
    assert result["remediations_applied"] >= 1

    t = db.trainers.rows[0]
    assert t["published"] is False
    assert t["ingestion_quality_status"] == "held"
    assert t["ingestion_hold_reason"] == "guardian_placeholder_detected"


def test_audit_corpus_integrity_persists_system_state():
    """Guardian records audit run in db.system_state for /ops visibility."""
    db = _MockDB()
    asyncio.run(pipeline_guardian.audit_corpus_integrity(db, auto_remediate=True))

    assert len(db.system_state.rows) == 1
    state = db.system_state.rows[0]
    assert state["key"] == "pipeline_guardian"
    assert state["status"] == "clean"
    assert "last_run" in state
