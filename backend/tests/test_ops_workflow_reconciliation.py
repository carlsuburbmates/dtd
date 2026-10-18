"""Unit and integration tests for Unified Operations Workflows & Obligation Reconciliation.

Verifies:
1. Resend delivery/bounce webhook receiver & notification event updates (AW-010).
2. First-party customer support & complaint intake (MW-021).
3. Support thread oversight management & operator reply dispatch.
4. Trainer held submission review (MW-001).
5. Profile claim adjudication with verified proof requirements (MW-004/MW-005).
6. Quarantined spam/fraud lead review and duplicate-proof release (MW-008).
7. Trainer delisting with re-ingestion suppression (MW-002).
8. Assisted trainer profile editing with audited diff (MW-006).
9. Statutory compliance & safety suppression (MW-015).
10. Privacy data eradication under Australian Privacy Principles (MW-009).
11. Notification events to obligation ledger sync repair (MW-007).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import server
from server import app
from services import ops_obligations


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self._iter = iter(self.rows)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n=None):
        if n is not None:
            self.rows = self.rows[:n]
        return self

    def skip(self, *args, **kwargs):
        return self

    async def to_list(self, _n=None):
        return list(self.rows)

    def __aiter__(self):
        self._iter = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


def _match_doc(row: Dict[str, Any], filt: Optional[Dict[str, Any]]) -> bool:
    if not filt or not isinstance(filt, dict):
        return True
    for k, v in filt.items():
        if k == "$or" and isinstance(v, list):
            if not any(_match_doc(row, cond) for cond in v):
                return False
        elif k == "$and" and isinstance(v, list):
            if not all(_match_doc(row, cond) for cond in v):
                return False
        elif isinstance(v, dict):
            if "$in" in v:
                if row.get(k) not in v["$in"]:
                    return False
            elif "$nin" in v:
                if row.get(k) in v["$nin"]:
                    return False
            elif "$ne" in v:
                if row.get(k) == v["$ne"]:
                    return False
            elif "$lte" in v:
                if float(row.get(k) or 0) > float(v["$lte"]):
                    return False
            elif "$gte" in v:
                if float(row.get(k) or 0) < float(v["$gte"]):
                    return False
        else:
            if row.get(k) != v:
                return False
    return True


class _MockCollection:
    def __init__(self, *, rows=None):
        self.rows = list(rows) if rows else []
        self.updated = []
        self.inserted = []

    async def distinct(self, key, filt=None):
        return list({r.get(key) for r in self.rows if r.get(key) is not None})

    async def find_one(self, filt=None, *_args, **_kwargs):
        if filt and isinstance(filt, dict):
            for row in self.rows:
                if _match_doc(row, filt):
                    return dict(row)
        elif self.rows:
            return dict(self.rows[0])
        return None

    def find(self, filt=None, *_args, **_kwargs):
        if not filt:
            return _Cursor(self.rows)
        matched = [r for r in self.rows if _match_doc(r, filt)]
        return _Cursor(matched)

    async def count_documents(self, filt=None, *_args, **_kwargs):
        if not filt:
            return len(self.rows)
        return len([r for r in self.rows if _match_doc(r, filt)])

    async def insert_one(self, doc):
        d = dict(doc)
        self.rows.append(d)
        self.inserted.append(d)
        return SimpleNamespace(inserted_id=d.get("id"))

    async def update_one(self, filt, update, upsert=False):
        self.updated.append((filt, update, upsert))
        target = None
        for row in self.rows:
            if _match_doc(row, filt):
                target = row
                break
        if target is None and upsert:
            target = dict(filt)
            self.rows.append(target)
        if target is not None:
            set_vals = update.get("$set", {}) if isinstance(update, dict) else {}
            target.update(set_vals)
            unset_vals = update.get("$unset", {}) if isinstance(update, dict) else {}
            for uk in unset_vals:
                target.pop(uk, None)
            push_vals = update.get("$push", {}) if isinstance(update, dict) else {}
            for pk, pv in push_vals.items():
                if pk not in target or not isinstance(target[pk], list):
                    target[pk] = list(target.get(pk, []))
                target[pk].append(pv)
            return SimpleNamespace(matched_count=1, modified_count=1, upserted_id=target.get("id"))
        return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)

    async def update_many(self, filt, update):
        matched = 0
        set_vals = update.get("$set", {}) if isinstance(update, dict) else {}
        unset_vals = update.get("$unset", {}) if isinstance(update, dict) else {}
        push_vals = update.get("$push", {}) if isinstance(update, dict) else {}
        for row in self.rows:
            if _match_doc(row, filt):
                row.update(set_vals)
                for uk in unset_vals:
                    row.pop(uk, None)
                for pk, pv in push_vals.items():
                    if pk not in row or not isinstance(row[pk], list):
                        row[pk] = list(row.get(pk, []))
                    row[pk].append(pv)
                matched += 1
        return SimpleNamespace(matched_count=matched, modified_count=matched)

    async def delete_one(self, filt):
        for i, row in enumerate(self.rows):
            if _match_doc(row, filt):
                del self.rows[i]
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    async def delete_many(self, filt):
        before = len(self.rows)
        self.rows = [r for r in self.rows if not _match_doc(r, filt)]
        return SimpleNamespace(deleted_count=before - len(self.rows))

    async def find_one_and_update(self, filt, update, upsert=False, return_document=None):
        for row in self.rows:
            if _match_doc(row, filt):
                set_vals = update.get("$set", {}) if isinstance(update, dict) else {}
                row.update(set_vals)
                return dict(row)
        if upsert:
            doc = dict(filt)
            set_vals = update.get("$set", {}) if isinstance(update, dict) else {}
            doc.update(set_vals)
            self.rows.append(doc)
            return dict(doc)
        return None


class _MockDB:
    def __init__(self, **collections):
        self._collections = collections

    def __getattr__(self, name: str):
        if name not in self._collections:
            self._collections[name] = _MockCollection()
        return self._collections[name]


def test_resend_webhook_delivered_and_bounced_updates():
    """Test Resend webhook idempotency and status updating in notification_events."""
    async def _test():
        mock_notif = _MockCollection(rows=[
            {
                "id": "notif_test_123",
                "dispatch_id": "dsp_test_123",
                "provider_id": "resend_msg_abc",
                "to_email": "trainer@example.com.au",
                "status": "sent",
                "created_at": "2026-10-19T00:00:00Z",
            },
            {
                "id": "notif_test_456",
                "dispatch_id": "dsp_test_456",
                "provider_id": "resend_msg_xyz",
                "to_email": "bad@example.com.au",
                "status": "sent",
                "created_at": "2026-10-19T00:00:00Z",
            }
        ])
        mock_resend_events = _MockCollection()
        orig_db = server.db
        server.db = _MockDB(
            notification_events=mock_notif,
            resend_webhook_events=mock_resend_events,
        )

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Deliver event
                deliv_payload = {
                    "type": "email.delivered",
                    "data": {
                        "email_id": "resend_msg_abc",
                        "to": ["trainer@example.com.au"],
                    },
                }
                res = await client.post("/resend/webhook", json=deliv_payload)
                assert res.status_code == 200
                assert res.json()["ok"] is True

                updated = await mock_notif.find_one({"provider_id": "resend_msg_abc"})
                assert updated["status"] == "delivered"
                assert updated["resend_event_type"] == "email.delivered"

                # 2. Bounce event on another message
                bounce_payload = {
                    "type": "email.bounced",
                    "data": {
                        "email_id": "resend_msg_xyz",
                        "to": ["bad@example.com.au"],
                        "bounce": {"type": "permanent"},
                    },
                }
                res2 = await client.post("/api/resend/webhook", json=bounce_payload)
                assert res2.status_code == 200

                bounced = await mock_notif.find_one({"provider_id": "resend_msg_xyz"})
                assert bounced["status"] == "bounced"
                assert bounced["bounce_reason"] == "permanent"
        finally:
            server.db = orig_db

    asyncio.run(_test())


def test_customer_support_intake_and_oversight_lifecycle():
    """Test MW-021: First-party support intake, receipt dispatch, obligation sync, operator reply, and closure."""
    async def _test():
        mock_support = _MockCollection()
        mock_obls = _MockCollection()
        mock_audit = _MockCollection()
        mock_auth = _MockCollection()

        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "test-secret"
        server.db = _MockDB(
            support_threads=mock_support,
            ops_obligations=mock_obls,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
        )

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Customer submits complaint
                inquiry_payload = {
                    "name": "Jane Owner",
                    "email": "jane@example.com",
                    "category": "complaint",
                    "subject": "Trainer cancelled and refused refund",
                    "message": "The trainer booked for Saturday cancelled without notice and refused to respond.",
                    "trainer_name": "Acme Dog School",
                }
                with patch("services.notifications.notify_support_received", AsyncMock()):
                    res = await client.post("/support/contact", json=inquiry_payload)
                assert res.status_code == 200
                data = res.json()
                assert data["ok"] is True
                case_id = data["case_id"]
                assert case_id.startswith("sup_")

                # 2. Verify persistence in support_threads
                thread = await mock_support.find_one({"case_id": case_id})
                assert thread is not None
                assert thread["category"] == "complaint"
                assert thread["severity"] == "high"
                assert thread["status"] == "open"

                # 3. Verify obligation ledger sync captures this complaint
                obl_res = await ops_obligations.sync_durable_obligations(server.db)
                synced_map = {o["obligation_id"]: o for o in obl_res}
                expected_obl_id = f"obligation:support:{case_id}"
                assert expected_obl_id in synced_map
                assert synced_map[expected_obl_id]["category"] == "customer_complaint"
                assert synced_map[expected_obl_id]["severity"] == "high"

                # 4. Operator views thread
                headers = {"x-admin-pass": "test-secret"}
                list_res = await client.get("/api/oversight/support/threads", headers=headers)
                assert list_res.status_code == 200
                threads = list_res.json()["threads"]
                assert any(t["case_id"] == case_id for t in threads)

                get_res = await client.get(f"/api/oversight/support/threads/{case_id}", headers=headers)
                assert get_res.status_code == 200
                assert get_res.json()["thread"]["sender_name"] == "Jane Owner"

                # 5. Operator replies to customer
                reply_payload = {
                    "reply_text": "Hi Jane, we have contacted Acme Dog School to investigate your cancellation.",
                    "mark_status": "awaiting_customer_reply",
                }
                with patch("services.notifications.notify_support_reply", AsyncMock(return_value={"status": "sent"})):
                    reply_res = await client.post(
                        f"/api/oversight/support/threads/{case_id}/reply",
                        json=reply_payload,
                        headers=headers,
                    )
                assert reply_res.status_code == 200
                assert reply_res.json()["status"] == "awaiting_customer_reply"

                # Verify thread updated
                updated_thread = await mock_support.find_one({"case_id": case_id})
                assert updated_thread["status"] == "awaiting_customer_reply"
                assert len(updated_thread["messages"]) == 2

                # 6. Operator closes thread with verified resolution
                close_payload = {
                    "resolution_notes": "Trainer agreed to issue full refund and apologized.",
                    "confirmed": True,
                }
                close_res = await client.post(
                    f"/api/oversight/support/threads/{case_id}/close",
                    json=close_payload,
                    headers=headers,
                )
                assert close_res.status_code == 200
                assert close_res.json()["status"] == "resolved"

                # 7. Obligation ledger sync verifies terminal resolution
                terminal_ok, reason = await ops_obligations.verify_obligation_terminal_state(
                    server.db,
                    {"category": "customer_complaint", "entity_id": case_id},
                )
                assert terminal_ok is True
                assert "verified resolved" in reason
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_held_submission_review_and_publication():
    """Test MW-001: Approve held trainer submission and verify atomic publication."""
    async def _test():
        sub_id = "sub_test_held_001"
        mock_subs = _MockCollection(rows=[
            {
                "id": sub_id,
                "name": "Bayside K9 Academy",
                "email": "info@baysidek9.com.au",
                "phone": "0412345678",
                "abn": "12345678901",
                "abn_status": "active",
                "abn_verified": True,
                "status": "held",
                "serviced_suburbs": ["Brighton", "Elwood"],
                "specialties": ["Puppy Training"],
                "created_at": "2026-10-19T00:00:00Z",
            }
        ])
        mock_trainers = _MockCollection()
        mock_audit = _MockCollection()
        mock_auth = _MockCollection()

        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "test-secret"
        server.db = _MockDB(
            submissions=mock_subs,
            trainers=mock_trainers,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
        )

        try:
            headers = {"x-admin-pass": "test-secret"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Attempt approve without confirmation -> 400
                res_fail = await client.post(
                    f"/api/oversight/submissions/{sub_id}/review",
                    json={"action": "approve", "confirmed": False},
                    headers=headers,
                )
                assert res_fail.status_code == 400

                # Valid approval
                res = await client.post(
                    f"/api/oversight/submissions/{sub_id}/review",
                    json={"action": "approve", "confirmed": True, "notes": "ABN confirmed active on ABR."},
                    headers=headers,
                )
                assert res.status_code == 200
                data = res.json()
                assert data["ok"] is True
                assert data["status"] == "published"
                trainer_id = data["trainer_id"]

                # Verify database state
                sub_doc = await mock_subs.find_one({"id": sub_id})
                assert sub_doc["status"] == "published"
                assert sub_doc["trainer_id"] == trainer_id

                trainer_doc = await mock_trainers.find_one({"id": trainer_id})
                assert trainer_doc is not None
                assert trainer_doc["name"] == "Bayside K9 Academy"
                assert trainer_doc["published"] is True
                assert trainer_doc["is_active"] is True
                assert trainer_doc["verification_status"] == "verified"
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_claim_review_grant_with_proof_and_deny():
    """Test MW-004 / MW-005: Adjudicate contested claim with mandatory proof citation."""
    async def _test():
        trainer_id = "trn_claim_test_001"
        claim_id = "clm_test_001"
        mock_trainers = _MockCollection(rows=[
            {
                "id": trainer_id,
                "name": "Melbourne Dog Training",
                "email": "original@melbournedog.com.au",
                "is_claimed": False,
                "claim_in_progress": True,
            }
        ])
        mock_claims = _MockCollection(rows=[
            {
                "id": claim_id,
                "trainer_id": trainer_id,
                "claimant_email": "owner@melbournedog.com.au",
                "status": "pending_challenge",
                "created_at": "2026-10-19T00:00:00Z",
            }
        ])
        mock_audit = _MockCollection()
        mock_auth = _MockCollection()

        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "test-secret"
        server.db = _MockDB(
            trainers=mock_trainers,
            claim_events=mock_claims,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
        )

        try:
            headers = {"x-admin-pass": "test-secret"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Attempt grant without proof -> 400
                res_fail = await client.post(
                    f"/api/oversight/claims/{claim_id}/review",
                    json={"action": "grant_with_proof", "confirmed": True, "proof_reference": ""},
                    headers=headers,
                )
                assert res_fail.status_code == 400

                # Grant with verified ASIC proof
                res = await client.post(
                    f"/api/oversight/claims/{claim_id}/review",
                    json={
                        "action": "grant_with_proof",
                        "confirmed": True,
                        "proof_reference": "ASIC Current Company Extract 2026-10-15 matching claimant name",
                    },
                    headers=headers,
                )
                assert res.status_code == 200
                assert res.json()["status"] == "verified"

                # Verify trainer ownership updated
                trainer_doc = await mock_trainers.find_one({"id": trainer_id})
                assert trainer_doc["is_claimed"] is True
                assert trainer_doc["claimed_by"] == "owner@melbournedog.com.au"
                assert "claim_in_progress" not in trainer_doc

                # Verify claim marked verified
                claim_doc = await mock_claims.find_one({"id": claim_id})
                assert claim_doc["status"] == "verified"
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_quarantined_fraud_lead_release_and_confirm_spam():
    """Test MW-008: Review and release quarantined false-positive enquiry."""
    async def _test():
        trainer_id = "trn_fraud_test_001"
        intro_id = "int_quarantine_001"
        mock_trainers = _MockCollection(rows=[
            {
                "id": trainer_id,
                "name": "Inner City Dog Trainer",
                "email": "trainer@innercitydogs.com.au",
                "is_active": True,
            }
        ])
        mock_intros = _MockCollection(rows=[
            {
                "id": intro_id,
                "trainer_id": trainer_id,
                "owner_name": "Legitimate Dog Owner",
                "owner_email": "doglover@gmail.com",
                "quarantined": True,
                "fraud_flags": ["high_velocity_ip"],
                "delivery_state": "suppressed",
                "created_at": "2026-10-19T00:00:00Z",
            }
        ])
        mock_audit = _MockCollection()
        mock_auth = _MockCollection()

        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "test-secret"
        server.db = _MockDB(
            trainers=mock_trainers,
            intros=mock_intros,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
        )

        try:
            headers = {"x-admin-pass": "test-secret"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.post(
                    f"/api/oversight/intros/{intro_id}/fraud-review",
                    json={"action": "release", "confirmed": True, "notes": "Legitimate user inquiry confirmed."},
                    headers=headers,
                )
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "released"

                # Verify lead un-quarantined
                lead_doc = await mock_intros.find_one({"id": intro_id})
                assert lead_doc["quarantined"] is False
                assert lead_doc["fraud_cleared_by"].startswith("ops:")
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_trainer_delisting_and_compliance_suppression():
    """Test MW-002 & MW-015: Trainer voluntary delisting and compliance suppression."""
    async def _test():
        trainer_id = "trn_delist_test_001"
        trainer2_id = "trn_suppress_test_002"
        mock_trainers = _MockCollection(rows=[
            {
                "id": trainer_id,
                "name": "Retired Trainer Service",
                "email": "retired@trainers.com.au",
                "phone": "0400111222",
                "abn": "98765432101",
                "is_active": True,
                "published": True,
            },
            {
                "id": trainer2_id,
                "name": "Defamatory Trainer Listing",
                "is_active": True,
                "published": True,
            }
        ])
        mock_delist = _MockCollection()
        mock_audit = _MockCollection()
        mock_auth = _MockCollection()

        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "test-secret"
        server.db = _MockDB(
            trainers=mock_trainers,
            delisted_suppression_list=mock_delist,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
        )

        try:
            headers = {"x-admin-pass": "test-secret"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Delist trainer
                with patch("services.notifications.notify_trainer_delisted", AsyncMock()):
                    delist_res = await client.post(
                        f"/api/oversight/trainers/{trainer_id}/delist",
                        json={"reason": "Business closed down voluntarily", "confirmed": True},
                        headers=headers,
                    )
                assert delist_res.status_code == 200
                assert delist_res.json()["status"] == "delisted"

                # Verify trainer deactivated and suppression record added
                trainer_doc = await mock_trainers.find_one({"id": trainer_id})
                assert trainer_doc["is_active"] is False
                assert trainer_doc["published"] is False

                supp_doc = await mock_delist.find_one({"trainer_id": trainer_id})
                assert supp_doc is not None
                assert supp_doc["reason"] == "Business closed down voluntarily"

                # Compliance suppression test
                supp_res = await client.post(
                    f"/api/oversight/trainers/{trainer2_id}/suppress",
                    json={
                        "legal_grounds": "defamation_notice",
                        "evidence_reference": "Formal solicitors concerns notice ref 2026/894",
                        "confirmed": True,
                    },
                    headers=headers,
                )
                assert supp_res.status_code == 200
                assert supp_res.json()["status"] == "suppressed"

                suppressed_doc = await mock_trainers.find_one({"id": trainer2_id})
                assert suppressed_doc["compliance_suppressed"] is True
                assert suppressed_doc["published"] is False
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_privacy_scrub_pipeline_under_app_guidelines():
    """Test MW-009: Statutory personal data scrub across leads and submissions."""
    async def _test():
        case_id = "sup_privacy_test_001"
        target_email = "privacy.subject@example.com"

        mock_support = _MockCollection(rows=[
            {
                "case_id": case_id,
                "sender_email": target_email,
                "category": "privacy_request",
                "status": "open",
            }
        ])
        mock_intros = _MockCollection(rows=[
            {
                "id": "int_priv_01",
                "owner_email": target_email,
                "owner_name": "John Doe",
                "owner_phone": "0499888777",
            }
        ])
        mock_subs = _MockCollection(rows=[
            {
                "id": "sub_priv_01",
                "email": target_email,
                "name": "John Doe Training",
                "phone": "0499888777",
            }
        ])
        mock_audit = _MockCollection()
        mock_auth = _MockCollection()

        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "test-secret"
        server.db = _MockDB(
            support_threads=mock_support,
            intros=mock_intros,
            submissions=mock_subs,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
        )

        try:
            headers = {"x-admin-pass": "test-secret"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.post(
                    f"/api/oversight/privacy/requests/{case_id}/process",
                    json={"action": "authorise_scrub", "confirmed": True},
                    headers=headers,
                )
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "scrubbed_and_resolved"
                assert data["records_scrubbed"] == 2

                # Verify intros PII scrubbed
                intro_doc = await mock_intros.find_one({"id": "int_priv_01"})
                assert intro_doc["owner_email"].startswith("[SCRUBBED_PRIVACY_")
                assert intro_doc["owner_phone"] == "[SCRUBBED]"

                # Verify submission PII scrubbed
                sub_doc = await mock_subs.find_one({"id": "sub_priv_01"})
                assert sub_doc["email"].startswith("[SCRUBBED_PRIVACY_")
                assert sub_doc["phone"] == "[SCRUBBED]"
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_notification_failure_creates_durable_obligation():
    """Test A1 Repair: notification_events failure produces durable obligation in ops_obligations."""
    async def _test():
        dispatch_id = "dsp_failed_test_999"
        mock_notif = _MockCollection(rows=[
            {
                "id": "notif_fail_999",
                "dispatch_id": dispatch_id,
                "kind": "client_intro",
                "target_kind": "intro",
                "target_id": "int_target_999",
                "to_email": "undeliverable@trainer.com.au",
                "attempt": 3,
                "status": "failed",
                "error": "http_550_mailbox_unavailable",
                "created_at": "2026-10-19T00:00:00Z",
            }
        ])
        mock_obls = _MockCollection()

        orig_db = server.db
        mock_db = _MockDB(
            notification_events=mock_notif,
            ops_obligations=mock_obls,
        )
        server.db = mock_db

        try:
            # Run obligation sync
            sync_res = await ops_obligations.sync_durable_obligations(mock_db)
            synced_map = {o["obligation_id"]: o for o in sync_res}
            expected_id = f"obligation:message:{dispatch_id}"

            assert expected_id in synced_map
            obl = synced_map[expected_id]
            assert obl["category"] == "client_enquiry"
            assert "undeliverable@trainer.com.au" in obl["title"]

            # Now simulate successful retry event in notification_events
            await mock_notif.insert_one({
                "id": "notif_retry_success",
                "dispatch_id": dispatch_id,
                "kind": "client_intro",
                "target_kind": "intro",
                "target_id": "int_target_999",
                "to_email": "undeliverable@trainer.com.au",
                "attempt": 4,
                "status": "delivered",
                "created_at": "2026-10-19T01:00:00Z",
            })

            # Terminal state check returns True
            resolved, reason = await ops_obligations.verify_obligation_terminal_state(
                mock_db,
                {"category": "client_enquiry", "entity_id": dispatch_id},
            )
            assert resolved is True
            assert "verified delivered successfully" in reason
        finally:
            server.db = orig_db

    asyncio.run(_test())
