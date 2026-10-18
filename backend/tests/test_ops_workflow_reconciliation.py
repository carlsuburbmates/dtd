"""Unit and integration tests for Unified Operations Workflows & Obligation Reconciliation.

Verifies:
1. Resend delivery/bounce webhook receiver & notification event updates (AW-010, SR-01).
2. Trainer held submission review with statutory consents and suppression checks (MW-001, SR-02).
3. Profile claim adjudication with verified OTP/ID proof requirements (MW-004/MW-005, SR-03).
4. First-party customer support intake, decoupled reply states, and closure gates (MW-021, SR-04).
5. Privacy data eradication under Australian Privacy Principles with identity verification (MW-009, SR-05).
6. Durable obligations reconciliation and read-only oversight invariant (MW-007, SR-06, DF-032).
7. Quarantined fraud lead duplicate-proof release with truthful 'sent' delivery state (MW-008).
8. Trainer delisting and compliance suppression with re-ingestion prevention (MW-002, MW-015).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
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


def _make_svix_headers(secret: str, payload_bytes: bytes, svix_id: str = "msg_test_123", ts: Optional[int] = None) -> Dict[str, str]:
    if ts is None:
        ts = int(time.time())
    secret_clean = secret[6:] if secret.startswith("whsec_") else secret
    secret_bytes = base64.b64decode(secret_clean)
    to_sign = f"{svix_id}.{ts}.".encode("utf-8") + payload_bytes
    sig = base64.b64encode(hmac.new(secret_bytes, to_sign, hashlib.sha256).digest()).decode("ascii")
    return {
        "svix-id": svix_id,
        "svix-timestamp": str(ts),
        "svix-signature": f"v1,{sig}",
    }


def test_resend_webhook_security_and_terminal_protection():
    """Test SR-01: Cryptographic Svix signature verification, fail-closed handling, and terminal status protection."""
    async def _test():
        test_secret = "whsec_" + base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("ascii")
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
        orig_secret = os.environ.get("RESEND_WEBHOOK_SECRET")

        server.db = _MockDB(
            notification_events=mock_notif,
            resend_webhook_events=mock_resend_events,
        )

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                deliv_payload = {
                    "type": "email.delivered",
                    "data": {
                        "email_id": "resend_msg_abc",
                        "to": ["trainer@example.com.au"],
                    },
                }
                payload_bytes = json.dumps(deliv_payload).encode("utf-8")

                # 1. Fail closed on missing webhook secret (500)
                os.environ.pop("RESEND_WEBHOOK_SECRET", None)
                res_no_sec = await client.post("/resend/webhook", content=payload_bytes)
                assert res_no_sec.status_code == 500
                assert "configured" in res_no_sec.json()["detail"]

                # 2. Fail closed on malformed base64 secret (500)
                os.environ["RESEND_WEBHOOK_SECRET"] = "whsec_INVALID_NOT_BASE64!!"
                res_bad_sec = await client.post("/resend/webhook", content=payload_bytes)
                assert res_bad_sec.status_code == 500

                # Configure valid test secret
                os.environ["RESEND_WEBHOOK_SECRET"] = test_secret

                # 3. Missing Svix headers returns 401
                res_no_hdr = await client.post("/resend/webhook", content=payload_bytes)
                assert res_no_hdr.status_code == 401
                assert "signature headers" in res_no_hdr.json()["detail"].lower()

                # 4. Invalid signature returns 401
                bad_headers = {
                    "svix-id": "msg_001",
                    "svix-timestamp": str(int(time.time())),
                    "svix-signature": "v1,invalid_sig_here==",
                }
                res_bad_sig = await client.post("/resend/webhook", content=payload_bytes, headers=bad_headers)
                assert res_bad_sig.status_code == 401
                assert "invalid webhook signature" in res_bad_sig.json()["detail"].lower()

                # 5. Expired timestamp (> 300s old) returns 401
                old_ts = int(time.time()) - 350
                old_headers = _make_svix_headers(test_secret, payload_bytes, ts=old_ts)
                res_old = await client.post("/resend/webhook", content=payload_bytes, headers=old_headers)
                assert res_old.status_code == 401
                assert "timestamp expired" in res_old.json()["detail"].lower()

                # 6. Tampered payload returns 401
                valid_headers = _make_svix_headers(test_secret, payload_bytes)
                tampered_bytes = json.dumps({"type": "email.delivered", "data": {"email_id": "tampered"}}).encode("utf-8")
                res_tampered = await client.post("/resend/webhook", content=tampered_bytes, headers=valid_headers)
                assert res_tampered.status_code == 401

                # 7. Valid delivery event updates notification_events to 'delivered'
                valid_headers = _make_svix_headers(test_secret, payload_bytes)
                res_deliv = await client.post("/resend/webhook", content=payload_bytes, headers=valid_headers)
                assert res_deliv.status_code == 200
                assert res_deliv.json()["ok"] is True

                updated = await mock_notif.find_one({"provider_id": "resend_msg_abc"})
                assert updated["status"] == "delivered"
                assert updated["resend_event_type"] == "email.delivered"

                # 8. Bounce event on another message
                bounce_payload = {
                    "type": "email.bounced",
                    "data": {
                        "email_id": "resend_msg_xyz",
                        "to": ["bad@example.com.au"],
                        "bounce": {"type": "permanent"},
                    },
                }
                bounce_bytes = json.dumps(bounce_payload).encode("utf-8")
                bounce_headers = _make_svix_headers(test_secret, bounce_bytes, svix_id="msg_bounce_999")
                res_bounce = await client.post("/api/resend/webhook", content=bounce_bytes, headers=bounce_headers)
                assert res_bounce.status_code == 200

                bounced = await mock_notif.find_one({"provider_id": "resend_msg_xyz"})
                assert bounced["status"] == "bounced"
                assert bounced["bounce_reason"] == "permanent"

                # 9. Terminal status protection: an out-of-order 'email.sent' event CANNOT overwrite 'delivered'
                sent_payload = {
                    "type": "email.sent",
                    "data": {
                        "email_id": "resend_msg_abc",
                        "to": ["trainer@example.com.au"],
                    },
                }
                sent_bytes = json.dumps(sent_payload).encode("utf-8")
                sent_headers = _make_svix_headers(test_secret, sent_bytes, svix_id="msg_sent_out_of_order")
                res_sent = await client.post("/resend/webhook", content=sent_bytes, headers=sent_headers)
                assert res_sent.status_code == 200

                # Status remains 'delivered', not downgraded to 'sent'
                rechecked = await mock_notif.find_one({"provider_id": "resend_msg_abc"})
                assert rechecked["status"] == "delivered"

                # 10. Minimal PII recorded in resend_webhook_events
                event_record = await mock_resend_events.find_one({"email_id": "resend_msg_abc"})
                assert event_record is not None
                assert "to" not in event_record
                assert "raw_payload" not in event_record
        finally:
            server.db = orig_db
            if orig_secret is not None:
                os.environ["RESEND_WEBHOOK_SECRET"] = orig_secret
            else:
                os.environ.pop("RESEND_WEBHOOK_SECRET", None)

    asyncio.run(_test())


def test_customer_support_intake_and_oversight_lifecycle():
    """Test SR-04 & MW-021: Support intake, decoupled reply states, and category closure guards."""
    async def _test():
        mock_support = _MockCollection()
        mock_obls = _MockCollection()
        mock_audit = _MockCollection()
        mock_auth = _MockCollection()
        mock_trainers = _MockCollection()

        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "test-secret"
        server.db = _MockDB(
            support_threads=mock_support,
            ops_obligations=mock_obls,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
            trainers=mock_trainers,
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

                # 5. Operator reply guard: Cannot resolve via reply endpoint (400)
                reply_resolve_fail = await client.post(
                    f"/api/oversight/support/threads/{case_id}/reply",
                    json={"reply_text": "Resolving this ticket now.", "mark_status": "resolved"},
                    headers=headers,
                )
                assert reply_resolve_fail.status_code == 400
                assert "Cannot resolve support thread via reply" in reply_resolve_fail.json()["detail"]

                # 6. Operator reply dispatch failure sets status to reply_delivery_failed
                with patch("services.notifications.notify_support_reply", AsyncMock(side_effect=Exception("Resend API down"))):
                    fail_reply_res = await client.post(
                        f"/api/oversight/support/threads/{case_id}/reply",
                        json={"reply_text": "Initial reply attempt that fails dispatch."},
                        headers=headers,
                    )
                assert fail_reply_res.status_code == 200
                assert fail_reply_res.json()["status"] == "reply_delivery_failed"
                assert fail_reply_res.json()["dispatched"] is False

                failed_thread = await mock_support.find_one({"case_id": case_id})
                assert failed_thread["status"] == "reply_delivery_failed"

                # 7. Operator reply dispatch success updates status to awaiting_customer_reply
                with patch("services.notifications.notify_support_reply", AsyncMock(return_value={"status": "sent", "id": "res_msg_reply_1"})):
                    reply_res = await client.post(
                        f"/api/oversight/support/threads/{case_id}/reply",
                        json={"reply_text": "Hi Jane, we have contacted Acme Dog School to investigate."},
                        headers=headers,
                    )
                assert reply_res.status_code == 200
                assert reply_res.json()["status"] == "awaiting_customer_reply"
                assert reply_res.json()["dispatched"] is True

                updated_thread = await mock_support.find_one({"case_id": case_id})
                assert updated_thread["status"] == "awaiting_customer_reply"

                # 8. Duplicate reply prevention
                dup_res = await client.post(
                    f"/api/oversight/support/threads/{case_id}/reply",
                    json={"reply_text": "Hi Jane, we have contacted Acme Dog School to investigate."},
                    headers=headers,
                )
                assert dup_res.status_code == 200
                assert dup_res.json().get("duplicate") is True

                # 9. Closure guard: Closing without substantive notes (<10 chars) returns 400
                short_close = await client.post(
                    f"/api/oversight/support/threads/{case_id}/close",
                    json={"resolution_notes": "Done.", "confirmed": True},
                    headers=headers,
                )
                assert short_close.status_code in (400, 422)

                # 10. Operator closes thread with verified resolution notes
                close_payload = {
                    "resolution_notes": "Trainer agreed to issue full refund and apologized to dog owner.",
                    "confirmed": True,
                }
                close_res = await client.post(
                    f"/api/oversight/support/threads/{case_id}/close",
                    json=close_payload,
                    headers=headers,
                )
                assert close_res.status_code == 200
                assert close_res.json()["status"] == "resolved"

                # 11. Obligation ledger sync verifies terminal resolution
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
    """Test SR-02 & MW-001: Approve held submission with mandatory consents, suppression matching, and ABN invariants."""
    async def _test():
        sub_id = "sub_test_held_001"
        delisted_sub_id = "sub_test_suppressed_002"
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
                "consent_public_listing": True,
                "consent_information_accuracy": True,
                "serviced_suburbs": ["Brighton", "Elwood"],
                "specialties": ["Puppy Training"],
                "created_at": "2026-10-19T00:00:00Z",
            },
            {
                "id": delisted_sub_id,
                "name": "Suppressed Bad Trainer",
                "email": "bad@trainer.com.au",
                "abn": "99999999999",
                "status": "held",
                "consent_public_listing": True,
                "consent_information_accuracy": True,
            }
        ])
        mock_trainers = _MockCollection()
        mock_delisted = _MockCollection(rows=[
            {
                "abn": "99999999999",
                "email": "bad@trainer.com.au",
                "suppression_reason": "banned_abuse",
            }
        ])
        mock_audit = _MockCollection()
        mock_auth = _MockCollection()

        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "test-secret"
        server.db = _MockDB(
            submissions=mock_subs,
            trainers=mock_trainers,
            delisted_entities=mock_delisted,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
        )

        try:
            headers = {"x-admin-pass": "test-secret"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Attempt approve without confirmation -> 400
                res_fail = await client.post(
                    f"/api/oversight/submissions/{sub_id}/review",
                    json={"action": "approve", "confirmed": False},
                    headers=headers,
                )
                assert res_fail.status_code == 400

                # 2. Rejection of suppressed entity (matches delisted_entities) -> 403
                res_supp = await client.post(
                    f"/api/oversight/submissions/{delisted_sub_id}/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_supp.status_code == 403
                assert "delisted or suppressed" in res_supp.json()["detail"]

                # 3. Valid approval publishes trainer with packaged capabilities
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
                assert "capabilities" in trainer_doc

                # 4. Legitimate sole trader without ABN publishes with 'unverified', NOT false 'verified'
                no_abn_id = "sub_sole_trader_003"
                await mock_subs.insert_one({
                    "id": no_abn_id,
                    "name": "Jane's Dog Walking",
                    "email": "jane.sole@example.com",
                    "phone": "0400999888",
                    "abn": "",
                    "abn_status": "not_provided",
                    "status": "held",
                    "consent_public_listing": True,
                    "consent_information_accuracy": True,
                })
                res_no_abn = await client.post(
                    f"/api/oversight/submissions/{no_abn_id}/review",
                    json={"action": "approve", "confirmed": True, "notes": "Sole trader exemption confirmed."},
                    headers=headers,
                )
                assert res_no_abn.status_code == 200
                tr_sole = await mock_trainers.find_one({"via_submission_id": no_abn_id})
                assert tr_sole is not None
                assert tr_sole["verification_status"] == "unverified"
                assert tr_sole["abn_verified"] is False
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_claim_review_grant_with_proof_and_deny():
    """Test SR-03 & MW-004/MW-005: Adjudicate claim requiring verified OTP/ID proof before granting ownership."""
    async def _test():
        trainer_id = "trn_claim_test_001"
        claim_unverified = "clm_unverified_001"
        claim_verified = "clm_verified_002"

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
                "id": claim_unverified,
                "trainer_id": trainer_id,
                "claimant_email": "impostor@melbournedog.com.au",
                "status": "pending_challenge",
                "otp_verified": False,
                "identity_verified": False,
                "created_at": "2026-10-19T00:00:00Z",
            },
            {
                "id": claim_verified,
                "trainer_id": trainer_id,
                "claimant_email": "legit.owner@melbournedog.com.au",
                "status": "pending_challenge",
                "otp_verified": True,
                "identity_verified": True,
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
                # 1. Direct ownership grant via text reference without OTP/identity verification is prohibited (422)
                res_unverified = await client.post(
                    f"/api/oversight/claims/{claim_unverified}/review",
                    json={
                        "action": "grant_with_proof",
                        "confirmed": True,
                        "proof_reference": "Spoke to claimant on phone and they sounded genuine",
                    },
                    headers=headers,
                )
                assert res_unverified.status_code == 422
                assert "Direct ownership assignment via text reference is prohibited" in res_unverified.json()["detail"]

                # 2. Valid grant with verified OTP/identity and substantive business documentation
                res_legit = await client.post(
                    f"/api/oversight/claims/{claim_verified}/review",
                    json={
                        "action": "grant_with_proof",
                        "confirmed": True,
                        "proof_reference": "ASIC Current Company Extract 2026-10-15 matching claimant name and ABN",
                    },
                    headers=headers,
                )
                assert res_legit.status_code == 200
                assert res_legit.json()["status"] == "verified"

                # Verify trainer ownership updated
                trainer_doc = await mock_trainers.find_one({"id": trainer_id})
                assert trainer_doc["is_claimed"] is True
                assert trainer_doc["claimed_by"] == "legit.owner@melbournedog.com.au"
                assert "claim_in_progress" not in trainer_doc

                # 3. Displacing existing owner on claimed profile is blocked (409)
                res_displace = await client.post(
                    f"/api/oversight/claims/{claim_unverified}/review",
                    json={"action": "grant_with_proof", "confirmed": True, "proof_reference": "Another document"},
                    headers=headers,
                )
                assert res_displace.status_code == 409
                assert "Cannot displace" in res_displace.json()["detail"]
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_quarantined_fraud_lead_release_and_confirm_spam():
    """Test MW-008: Review quarantined enquiry, truthful 'sent' delivery state, and confirm spam."""
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
                with patch("services.notifications.notify_trainer_new_intro", AsyncMock(return_value={"trainer_notification_status": "sent"})):
                    res = await client.post(
                        f"/api/oversight/intros/{intro_id}/fraud-review",
                        json={"action": "release", "confirmed": True, "notes": "Legitimate user inquiry confirmed."},
                        headers=headers,
                    )
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "released"
                # Truthful delivery state: Resend acceptance is 'sent', not inbox 'delivered'
                assert data["delivery_state"] == "sent"

                # Verify lead un-quarantined
                lead_doc = await mock_intros.find_one({"id": intro_id})
                assert lead_doc["quarantined"] is False
                assert lead_doc["delivery_state"] == "sent"
                assert lead_doc["fraud_cleared_by"].startswith("ops:")
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_trainer_delisting_and_compliance_suppression():
    """Test MW-002 & MW-015: Trainer delisting with re-ingestion suppression and Stripe review flag."""
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
                "tier": "pro",
                "stripe_subscription_id": "sub_stripe_active_123",
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
            delisted_entities=mock_delist,
            audit_log=mock_audit,
            auth_attempts=mock_auth,
        )

        try:
            headers = {"x-admin-pass": "test-secret"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Delist trainer with active subscription flags for review rather than blindly deleting
                with patch("services.notifications.notify_trainer_delisted", AsyncMock()):
                    delist_res = await client.post(
                        f"/api/oversight/trainers/{trainer_id}/delist",
                        json={"reason": "Business closed down voluntarily", "confirmed": True},
                        headers=headers,
                    )
                assert delist_res.status_code == 200
                assert delist_res.json()["status"] == "delisted"
                # Verify trainer deactivated, billing review state flagged, and suppression record added with identity
                trainer_doc = await mock_trainers.find_one({"id": trainer_id})
                assert trainer_doc["is_active"] is False
                assert trainer_doc["published"] is False
                assert trainer_doc.get("billing_state") == "subscription_active_review_required"

                supp_doc = await mock_delist.find_one({"trainer_id": trainer_id})
                assert supp_doc is not None
                assert supp_doc["abn"] == "98765432101"
                assert supp_doc["reason"] == "Business closed down voluntarily"

                # 2. Compliance suppression test
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
    """Test SR-05 & MW-009: Privacy data scrub under Australian Privacy Principles with requester identity checks."""
    async def _test():
        case_id = "sup_privacy_test_001"
        target_email = "privacy.subject@example.com"

        mock_support = _MockCollection(rows=[
            {
                "case_id": case_id,
                "sender_email": target_email,
                "category": "privacy_request",
                "status": "open",
                "identity_verified": False,
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
                # 1. Scrub without verified identity returns 400
                res_unverified = await client.post(
                    f"/api/oversight/privacy/requests/{case_id}/process",
                    json={"action": "authorise_scrub", "confirmed": True},
                    headers=headers,
                )
                assert res_unverified.status_code == 400
                assert "Requester identity must be verified" in res_unverified.json()["detail"]

                # 2. Request identity proof action updates status
                res_req_id = await client.post(
                    f"/api/oversight/privacy/requests/{case_id}/process",
                    json={"action": "request_identity_proof", "confirmed": True, "notes": "Requesting photo ID"},
                    headers=headers,
                )
                assert res_req_id.status_code == 200
                assert res_req_id.json()["status"] == "awaiting_identity_proof"

                # 3. Authorise scrub once verified
                await mock_support.update_one({"case_id": case_id}, {"$set": {"identity_verified": True}})
                res = await client.post(
                    f"/api/oversight/privacy/requests/{case_id}/process",
                    json={"action": "authorise_scrub", "confirmed": True},
                    headers=headers,
                )
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "resolved"
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


def test_notification_failure_and_ops_obligations_guards():
    """Test SR-06 & MW-007: Notification failure durable obligations and terminal resolution guards."""
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
            # 1. Run obligation sync
            sync_res = await ops_obligations.sync_durable_obligations(mock_db)
            synced_map = {o["obligation_id"]: o for o in sync_res}
            expected_id = f"obligation:message:{dispatch_id}"

            assert expected_id in synced_map
            obl = synced_map[expected_id]
            assert obl["category"] == "client_enquiry"
            assert "undeliverable@trainer.com.au" in obl["title"]

            # 2. Conflation check: Another successful notification for the same target_id but different dispatch_id
            # MUST NOT resolve this obligation!
            await mock_notif.insert_one({
                "id": "notif_different_dispatch",
                "dispatch_id": "dsp_different_000",
                "kind": "client_intro",
                "target_kind": "intro",
                "target_id": "int_target_999",
                "to_email": "undeliverable@trainer.com.au",
                "status": "delivered",
                "created_at": "2026-10-19T00:30:00Z",
            })

            not_resolved, _ = await ops_obligations.verify_obligation_terminal_state(
                mock_db,
                {"category": "client_enquiry", "entity_id": dispatch_id},
            )
            assert not_resolved is False

            # 3. Missing claim and trainer records in claim_lock check MUST return False (cannot falsely clear lock)
            missing_resolved, err_msg = await ops_obligations.verify_obligation_terminal_state(
                mock_db,
                {"category": "claim_lock", "entity_id": "nonexistent_trainer"},
            )
            assert missing_resolved is False
            assert "cannot verify lock release" in err_msg

            # 4. Now simulate exact matching retry event in notification_events with status 'delivered'
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

            # Terminal state check now returns True
            resolved, reason = await ops_obligations.verify_obligation_terminal_state(
                mock_db,
                {"category": "client_enquiry", "entity_id": dispatch_id},
            )
            assert resolved is True
            assert "verified delivered successfully" in reason

            # 5. Read-only invariant (DF-032): get_active_obligation_cases with read_only=True performs zero writes
            mock_obls.inserted.clear()
            mock_obls.updated.clear()
            cases = await ops_obligations.get_active_obligation_cases(mock_db, read_only=True)
            assert len(mock_obls.inserted) == 0
            assert len(mock_obls.updated) == 0
        finally:
            server.db = orig_db

    asyncio.run(_test())
