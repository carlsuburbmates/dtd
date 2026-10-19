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

    def sort(self, key=None, direction=1, *args, **kwargs):
        if isinstance(key, str):
            self.rows.sort(key=lambda r: str(r.get(key, "")), reverse=(direction == -1))
        return self

    def limit(self, n=None):
        if n is not None:
            self.rows = self.rows[:n]
        return self

    def skip(self, *args, **kwargs):
        return self

    async def to_list(self, _n=None):
        if _n is not None:
            return list(self.rows[:_n])
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
        elif "." in k:
            parts = k.split(".", 1)
            parent = row.get(parts[0])
            if isinstance(parent, list):
                if not any(isinstance(item, dict) and item.get(parts[1]) == v for item in parent):
                    return False
            elif isinstance(parent, dict):
                if parent.get(parts[1]) != v:
                    return False
            else:
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
            for sk, sv in set_vals.items():
                if ".$." in sk:
                    arr_key, elem_key = sk.split(".$.", 1)
                    arr = target.get(arr_key, [])
                    # Find matching item by filter key if present
                    filter_val = None
                    for fk, fv in filt.items():
                        if fk.startswith(f"{arr_key}."):
                            filter_val = (fk.split(".", 1)[1], fv)
                            break
                    for elem in arr:
                        if isinstance(elem, dict):
                            if filter_val and elem.get(filter_val[0]) == filter_val[1]:
                                elem[elem_key] = sv
                                break
                            elif not filter_val:
                                elem[elem_key] = sv
                                break
                else:
                    target[sk] = sv
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
        target = None
        for row in self.rows:
            if _match_doc(row, filt):
                target = row
                break
        if target is None and upsert:
            target = dict(filt)
            self.rows.append(target)
        if target is not None:
            pre = dict(target)
            await self.update_one(filt, update, upsert=False)
            if return_document:
                return dict(target)
            return pre
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
                "source_evidence_url": "https://baysidek9.com.au",
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
                "source_evidence_url": "https://badtrainer.com.au",
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
                    "source_evidence_url": "https://janesdogwalking.com.au",
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

                # 5. Missing source provenance blocks publication (400)
                no_prov_id = "sub_no_provenance_test"
                await mock_subs.insert_one({
                    "id": no_prov_id,
                    "name": "No Source Trainer",
                    "email": "nosource@example.com",
                    "phone": "0400999888",
                    "abn": "",
                    "status": "held",
                    "consent_public_listing": True,
                    "consent_information_accuracy": True,
                })
                res_no_prov = await client.post(
                    f"/api/oversight/submissions/{no_prov_id}/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_no_prov.status_code == 400
                assert "lacks source provenance" in res_no_prov.json()["detail"].lower()
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
                "method": "email_otp",
                "otp_digest": "sha256_legit_challenge_digest",
                "otp_verified": True,
                "identity_verified": True,
                "identity_verified_by": "ops:127.0.0.1",
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

                # 1b. Arbitrary flag without challenge provenance (no method, no otp_digest) is rejected (422)
                claim_arbitrary_flag = "clm_arbitrary_flag_003"
                await mock_claims.insert_one({
                    "id": claim_arbitrary_flag,
                    "trainer_id": trainer_id,
                    "claimant_email": "arbitrary@melbournedog.com.au",
                    "status": "pending_challenge",
                    "otp_verified": True,
                    "created_at": "2026-10-19T00:00:00Z",
                })
                res_arb = await client.post(
                    f"/api/oversight/claims/{claim_arbitrary_flag}/review",
                    json={
                        "action": "grant_with_proof",
                        "confirmed": True,
                        "proof_reference": "ASIC business extract doc_456",
                    },
                    headers=headers,
                )
                assert res_arb.status_code == 422
                assert "verifiable challenge provenance" in res_arb.json()["detail"]

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
                await mock_support.update_one(
                    {"case_id": case_id},
                    {
                        "$set": {
                            "identity_verified": True,
                            "identity_verified_by": "ops:127.0.0.1",
                            "identity_verified_at": "2026-10-19T00:00:00Z",
                            "identity_verification_method": "photo_id",
                        }
                    },
                )
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


def test_cf01_privacy_verification_provenance_and_fail_close():
    """Test CF-01: Strict privacy verification provenance, notes-bypass elimination, and fail-closed error handling."""
    async def _test():
        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "testpass"

        mock_threads = _MockCollection(rows=[
            {
                "case_id": "sup_priv_unverified",
                "category": "privacy_request",
                "status": "open",
                "sender_email": "sarah@user.com",
                "identity_verified": False,
                "messages": [{"sender": "customer", "text": "Please delete my data"}],
            },
            {
                "case_id": "sup_priv_unprovenanced",
                "category": "privacy_request",
                "status": "open",
                "sender_email": "sarah@user.com",
                "identity_verified": True, # Flag set to True without any recorded operator provenance
                "messages": [{"sender": "customer", "text": "Please delete my data"}],
            },
            {
                "case_id": "sup_not_privacy",
                "category": "general_inquiry",
                "status": "open",
                "sender_email": "inquiry@user.com",
                "identity_verified": True,
                "messages": [{"sender": "customer", "text": "Question"}],
            },
            {
                "case_id": "sup_priv_verified",
                "category": "privacy_request",
                "status": "open",
                "sender_email": "sarah@user.com",
                "identity_verified": True,
                "identity_verified_by": "ops:127.0.0.1",
                "identity_verified_at": "2026-10-19T00:00:00Z",
                "identity_verification_method": "passport_match",
                "messages": [{"sender": "customer", "text": "Please delete my data"}],
            },
            {
                "case_id": "sup_hist_thread_other",
                "category": "general_inquiry",
                "status": "closed",
                "sender_email": "sarah@user.com",
                "sender_name": "Sarah Connor",
                "messages": [{"sender": "customer", "text": "Old inquiry"}],
            },
        ])
        mock_intros = _MockCollection(rows=[
            {
                "id": "int_priv_cf01",
                "owner_email": "sarah@user.com",
                "owner_name": "Sarah Connor",
                "owner_phone": "0412345678",
                "dog_notes": "Very reactive dog",
            }
        ])
        mock_subs = _MockCollection(rows=[
            {
                "id": "sub_priv_cf01",
                "email": "sarah@user.com",
                "name": "Sarah Connor",
                "phone": "0412345678",
            }
        ])
        mock_waitlist = _MockCollection(rows=[
            {
                "id": "wait_priv_cf01",
                "email": "sarah@user.com",
                "name": "Sarah Connor",
                "phone": "0412345678",
            }
        ])
        mock_claims = _MockCollection(rows=[
            {
                "id": "clm_priv_cf01",
                "claimant_email": "sarah@user.com",
                "phone": "0412345678",
            }
        ])
        mock_notifs = _MockCollection(rows=[
            {
                "id": "notif_priv_cf01",
                "to_email": "sarah@user.com",
            }
        ])

        mock_db = _MockDB(
            support_threads=mock_threads,
            intros=mock_intros,
            submissions=mock_subs,
            owner_waitlist=mock_waitlist,
            claim_events=mock_claims,
            notification_events=mock_notifs,
            audit_log=_MockCollection(),
        )
        server.db = mock_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = {"x-admin-pass": "testpass"}

                # 1. Adversarial: Operator notes containing "identity_verified" must NOT bypass verification!
                res1 = await client.post(
                    "/api/oversight/privacy/requests/sup_priv_unverified/process",
                    json={"action": "authorise_scrub", "confirmed": True, "notes": "Identity was identity_verified over the phone"},
                    headers=headers,
                )
                assert res1.status_code == 400
                assert "Requester identity must be verified" in res1.json()["detail"]

                # 1b. Unprovenanced identity_verified=True flag (no identity_verified_by or at) is rejected (400)
                res_unprovenanced = await client.post(
                    "/api/oversight/privacy/requests/sup_priv_unprovenanced/process",
                    json={"action": "authorise_scrub", "confirmed": True},
                    headers=headers,
                )
                assert res_unprovenanced.status_code == 400
                assert "recorded verification provenance" in res_unprovenanced.json()["detail"]

                # 2. In-request documentary proof allows unverified case to be verified and scrubbed
                res_in_request = await client.post(
                    "/api/oversight/privacy/requests/sup_priv_unverified/process",
                    json={
                        "action": "authorise_scrub",
                        "confirmed": True,
                        "proof_reference": "VIC Driver Licence 998877",
                        "proof_method": "photo_id",
                    },
                    headers=headers,
                )
                assert res_in_request.status_code == 200
                assert res_in_request.json()["status"] == "resolved"
                thread_updated = await mock_threads.find_one({"case_id": "sup_priv_unverified"})
                assert thread_updated["identity_verified"] is True
                assert thread_updated["identity_verification_method"] == "photo_id"
                assert thread_updated["identity_proof_reference"] == "VIC Driver Licence 998877"

                # 3. Wrong request category is rejected
                res3 = await client.post(
                    "/api/oversight/privacy/requests/sup_not_privacy/process",
                    json={"action": "authorise_scrub", "confirmed": True},
                    headers=headers,
                )
                assert res3.status_code == 400
                assert "Case is not a privacy request" in res3.json()["detail"]

                # 4. Partial failure handling: simulate database exception during intro scrubbing
                mock_db._collections["intros"].update_many = AsyncMock(side_effect=RuntimeError("Mongo connection lost"))
                res_err = await client.post(
                    "/api/oversight/privacy/requests/sup_priv_verified/process",
                    json={"action": "authorise_scrub", "confirmed": True},
                    headers=headers,
                )
                assert res_err.status_code == 500
                # Fail closed: thread status must be 'privacy_scrub_failed', NEVER 'resolved'
                thr_failed = await mock_threads.find_one({"case_id": "sup_priv_verified"})
                assert thr_failed["status"] == "privacy_scrub_failed"
                assert "privacy_error" in thr_failed
                assert thr_failed["failed_at_step"] == "intros"
                assert "scrub_journal" in thr_failed

                # Restore intros.update_many
                del mock_db._collections["intros"].update_many

                # 5. Verified requester completes successfully across all 6 collections
                res_ok = await client.post(
                    "/api/oversight/privacy/requests/sup_priv_verified/process",
                    json={"action": "authorise_scrub", "confirmed": True},
                    headers=headers,
                )
                assert res_ok.status_code == 200
                data = res_ok.json()
                assert data["status"] == "resolved"
                assert data["records_scrubbed"] >= 6
                assert len(data["scrub_journal"]) == 6

                # Verify actual scrubbing happened across collections
                intro_doc = await mock_intros.find_one({"id": "int_priv_cf01"})
                assert intro_doc["owner_email"].startswith("[SCRUBBED_PRIVACY_")
                assert intro_doc["owner_phone"] == "[SCRUBBED]"

                wait_doc = await mock_waitlist.find_one({"id": "wait_priv_cf01"})
                assert wait_doc["email"].startswith("[SCRUBBED_PRIVACY_")

                claim_doc = await mock_claims.find_one({"id": "clm_priv_cf01"})
                assert claim_doc["claimant_email"].startswith("[SCRUBBED_PRIVACY_")

                notif_doc = await mock_notifs.find_one({"id": "notif_priv_cf01"})
                assert notif_doc["to_email"].startswith("[SCRUBBED_PRIVACY_")

                hist_doc = await mock_threads.find_one({"case_id": "sup_hist_thread_other"})
                assert hist_doc["sender_email"].startswith("[SCRUBBED_PRIVACY_")

                # 6. Idempotent repeated processing
                res_repeat = await client.post(
                    "/api/oversight/privacy/requests/sup_priv_verified/process",
                    json={"action": "authorise_scrub", "confirmed": True},
                    headers=headers,
                )
                assert res_repeat.status_code == 200
                assert res_repeat.json()["already_processed"] is True
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_cf02_trainer_publication_authority_dedup_and_concurrency():
    """Test CF-02: Canonical publication authority, duplicate verification, unrelated business protection, and concurrency."""
    async def _test():
        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "testpass"

        mock_subs = _MockCollection(rows=[
            {
                "id": "sub_suppressed_1",
                "status": "held",
                "name": "Banned Dog Training",
                "phone": "+61412000001",
                "email": "banned@trainer.com",
                "website": "bannedtraining.com.au",
                "source_evidence_url": "https://bannedtraining.com.au",
                "abn": "11222333444",
                "consent_public_listing": True,
                "consent_information_accuracy": True,
            },
            {
                "id": "sub_no_consent_1",
                "status": "held",
                "name": "No Consent Academy",
                "email": "noconsent@trainer.com",
                "phone": "+61412000002",
                "website": "noconsent.com.au",
                "source_evidence_url": "https://noconsent.com.au",
                "consent_public_listing": False,
                "consent_information_accuracy": True,
            },
            {
                "id": "sub_unrelated_email_1",
                "status": "held",
                "name": "Paws Unlimited Academy",
                "email": "shared@trainer.com",
                "phone": "+61412000003",
                "website": "pawsunlimited.com.au",
                "source_evidence_url": "https://pawsunlimited.com.au",
                "consent_public_listing": True,
                "consent_information_accuracy": True,
            },
            {
                "id": "sub_claimed_conflict_1",
                "status": "held",
                "name": "Bark Academy Melbourne",
                "email": "bark@trainer.com",
                "phone": "+61412000004",
                "website": "barkacademy.com.au",
                "source_evidence_url": "https://barkacademy.com.au",
                "abn": "99888777666",
                "abn_verified": True,
                "consent_public_listing": True,
                "consent_information_accuracy": True,
            },
            {
                "id": "sub_valid_abn_optional_1",
                "status": "held",
                "name": "Sole Trader Pups",
                "email": "soletrader@trainer.com",
                "phone": "+61412000005",
                "website": "soletraderpups.com.au",
                "source_evidence_url": "https://soletraderpups.com.au",
                "abn": "",
                "consent_public_listing": True,
                "consent_information_accuracy": True,
            },
            {
                "id": "sub_no_provenance_1",
                "status": "held",
                "name": "Ghost Trainer",
                "phone": "+61412000099",
                "consent_public_listing": True,
                "consent_information_accuracy": True,
            },
        ])
        mock_trainers = _MockCollection(rows=[
            {
                "id": "trn_bark_academy",
                "name": "Bark Academy Melbourne",
                "email": "shared@trainer.com",
                "abn": "99888777666",
                "claim_status": "claimed",
                "is_claimed": True,
                "claimed_by": "original_owner@trainer.com",
                "published": True,
                "is_active": True,
            }
        ])
        mock_delisted = _MockCollection(rows=[
            {
                "abn": "11222333444",
                "website_domain": "bannedtraining.com.au",
                "normalized_phone": "+61412000001",
                "reason": "regulatory_enforcement",
            }
        ])

        mock_db = _MockDB(
            submissions=mock_subs,
            trainers=mock_trainers,
            delisted_entities=mock_delisted,
            audit_log=_MockCollection(),
        )
        server.db = mock_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = {"x-admin-pass": "testpass"}

                # 1. Suppressed business entity cannot be published (403)
                res_supp = await client.post(
                    "/api/oversight/submissions/sub_suppressed_1/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_supp.status_code == 403
                assert "matches a delisted or suppressed business entity" in res_supp.json()["detail"]

                # 2. Invalid consent blocks publication (400)
                res_noconsent = await client.post(
                    "/api/oversight/submissions/sub_no_consent_1/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_noconsent.status_code == 400
                assert "consent" in res_noconsent.json()["detail"].lower()

                # 3. Insufficient source provenance blocks publication (400)
                res_noprov = await client.post(
                    "/api/oversight/submissions/sub_no_provenance_1/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_noprov.status_code == 400
                assert "source provenance" in res_noprov.json()["detail"].lower()

                # 4. Matching contact details alone cannot authorise overwriting another trainer (409)
                # "Paws Unlimited Academy" has email "shared@trainer.com", which matches "Bark Academy Melbourne"
                res_unrelated = await client.post(
                    "/api/oversight/submissions/sub_unrelated_email_1/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_unrelated.status_code == 409
                assert "different business identity" in res_unrelated.json()["detail"] or "already claimed" in res_unrelated.json()["detail"]

                # 5. Existing claimed listing cannot be displaced (409)
                res_claimed = await client.post(
                    "/api/oversight/submissions/sub_claimed_conflict_1/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_claimed.status_code == 409
                assert "already claimed" in res_claimed.json()["detail"]

                # 6. Valid ABN-optional submission remains eligible and publishes unverified
                res_valid = await client.post(
                    "/api/oversight/submissions/sub_valid_abn_optional_1/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_valid.status_code == 200
                assert res_valid.json()["status"] == "published"
                created_trainer = await mock_trainers.find_one({"name": "Sole Trader Pups"})
                assert created_trainer is not None
                assert created_trainer["verification_status"] == "unverified"
                assert created_trainer["abn_verified"] is False
                assert created_trainer["published"] is True

                # 7. Repeated approval is idempotent
                res_idempotent = await client.post(
                    "/api/oversight/submissions/sub_valid_abn_optional_1/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res_idempotent.status_code == 200
                assert res_idempotent.json()["idempotent"] is True
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_cf03_claim_verification_provenance_expiry_and_conflicts():
    """Test CF-03: Claim verification provenance, expiry enforcement, conflict protection, and owner safeguards."""
    async def _test():
        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "testpass"

        mock_claims = _MockCollection(rows=[
            {
                "id": "clm_unverified_text_only",
                "trainer_id": "trn_target_claim",
                "claimant_email": "attacker@fake.com",
                "otp_verified": False,
                "identity_verified": False,
                "status": "pending_verification",
                "expires_at": "2099-01-01T00:00:00Z",
            },
            {
                "id": "clm_unprovenanced_flag_only",
                "trainer_id": "trn_unprov_target",
                "claimant_email": "attacker@fake.com",
                "otp_verified": True, # Flag set, but NO method and NO otp_digest/challenge_token
                "identity_verified": False,
                "status": "verified",
                "expires_at": "2099-01-01T00:00:00Z",
            },
            {
                "id": "clm_expired_challenge",
                "trainer_id": "trn_expired_target",
                "claimant_email": "legit@trainer.com",
                "method": "email_otp",
                "otp_digest": "sha256_expired_digest",
                "otp_verified": True,
                "status": "verified",
                "expires_at": "2020-01-01T00:00:00Z",  # Expired in past!
            },
            {
                "id": "clm_already_claimed_trainer",
                "trainer_id": "trn_already_claimed",
                "claimant_email": "newbie@trainer.com",
                "method": "email_otp",
                "otp_digest": "sha256_claimed_digest",
                "otp_verified": True,
                "status": "verified",
                "expires_at": "2099-01-01T00:00:00Z",
            },
            {
                "id": "clm_conflicting_verified_prior",
                "trainer_id": "trn_conflicting_target",
                "claimant_email": "first_verified@trainer.com",
                "method": "email_otp",
                "otp_digest": "sha256_prior_digest",
                "otp_verified": True,
                "status": "verified",
                "expires_at": "2099-01-01T00:00:00Z",
            },
            {
                "id": "clm_conflicting_verified_attacker",
                "trainer_id": "trn_conflicting_target",
                "claimant_email": "rival@trainer.com",
                "method": "email_otp",
                "otp_digest": "sha256_attacker_digest",
                "otp_verified": True,
                "status": "verified",
                "expires_at": "2099-01-01T00:00:00Z",
            },
            {
                "id": "clm_competing_winner",
                "trainer_id": "trn_target_claim",
                "claimant_email": "owner_alice@trainer.com",
                "method": "email_otp",
                "otp_digest": "sha256_winner_digest",
                "otp_verified": True,
                "status": "verified",
                "expires_at": "2099-01-01T00:00:00Z",
            },
            {
                "id": "clm_competing_loser",
                "trainer_id": "trn_target_claim",
                "claimant_email": "challenger_bob@trainer.com",
                "method": "email_otp",
                "otp_digest": "sha256_loser_digest",
                "otp_verified": True,
                "status": "pending_verification",
                "expires_at": "2099-01-01T00:00:00Z",
            },
        ])
        mock_trainers = _MockCollection(rows=[
            {
                "id": "trn_target_claim",
                "name": "Target Pups",
                "claim_status": "unclaimed",
                "is_claimed": False,
                "published": True,
            },
            {
                "id": "trn_unprov_target",
                "name": "Unprovenanced Flag Target Pups",
                "claim_status": "unclaimed",
                "is_claimed": False,
                "published": True,
            },
            {
                "id": "trn_expired_target",
                "name": "Expired Target Pups",
                "claim_status": "unclaimed",
                "is_claimed": False,
                "published": True,
            },
            {
                "id": "trn_conflicting_target",
                "name": "Conflicted Pups",
                "claim_status": "unclaimed",
                "is_claimed": False,
                "published": True,
            },
            {
                "id": "trn_already_claimed",
                "name": "Established Trainer",
                "claim_status": "claimed",
                "is_claimed": True,
                "claimed_by": "existing_verified_owner@trainer.com",
                "published": True,
            },
        ])

        mock_db = _MockDB(
            claim_events=mock_claims,
            trainers=mock_trainers,
            audit_log=_MockCollection(),
        )
        server.db = mock_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = {"x-admin-pass": "testpass"}

                # 1. Self-asserted text reference without canonical verification challenge is rejected (422)
                res1 = await client.post(
                    "/api/oversight/claims/clm_unverified_text_only/review",
                    json={"action": "grant_with_proof", "proof_reference": "ASIC extract 12345", "confirmed": True},
                    headers=headers,
                )
                assert res1.status_code == 422
                assert "verifiable challenge provenance" in res1.json()["detail"] or "complete canonical identity verification challenge" in res1.json()["detail"]

                # 1b. Unprovenanced verification flag without server challenge origin is rejected (422)
                res_unprov = await client.post(
                    "/api/oversight/claims/clm_unprovenanced_flag_only/review",
                    json={"action": "grant_with_proof", "proof_reference": "ASIC extract 12345", "confirmed": True},
                    headers=headers,
                )
                assert res_unprov.status_code == 422
                assert "verifiable challenge provenance" in res_unprov.json()["detail"]

                # 2. Expired verification challenge cannot grant ownership (410)
                res2 = await client.post(
                    "/api/oversight/claims/clm_expired_challenge/review",
                    json={"action": "grant_with_proof", "proof_reference": "ASIC extract 12345", "confirmed": True},
                    headers=headers,
                )
                assert res2.status_code == 410
                assert "expired" in res2.json()["detail"].lower()

                # 3. Existing verified owner cannot be displaced (409)
                res3 = await client.post(
                    "/api/oversight/claims/clm_already_claimed_trainer/review",
                    json={"action": "grant_with_proof", "proof_reference": "ASIC extract 12345", "confirmed": True},
                    headers=headers,
                )
                assert res3.status_code == 409
                assert "Cannot displace an existing verified owner" in res3.json()["detail"]

                # 4. Conflicting verified claim for different claimant is rejected (409)
                res_conflict = await client.post(
                    "/api/oversight/claims/clm_conflicting_verified_attacker/review",
                    json={"action": "grant_with_proof", "proof_reference": "ASIC extract 99999", "confirmed": True},
                    headers=headers,
                )
                assert res_conflict.status_code == 409
                assert "conflicting verified claim exists" in res_conflict.json()["detail"]

                # 5. Valid canonical claim completes successfully (200)
                res_ok = await client.post(
                    "/api/oversight/claims/clm_competing_winner/review",
                    json={"action": "grant_with_proof", "proof_reference": "ASIC business extract doc_999", "confirmed": True},
                    headers=headers,
                )
                assert res_ok.status_code == 200
                assert res_ok.json()["status"] == "verified"

                # Check trainer ownership updated
                trn = await mock_trainers.find_one({"id": "trn_target_claim"})
                assert trn["is_claimed"] is True
                assert trn["claimed_by"] == "owner_alice@trainer.com"

                # 6. Competing pending claims for this trainer were superseded
                competing_claim = await mock_claims.find_one({"id": "clm_competing_loser"})
                assert competing_claim["status"] == "superseded"

                # 7. Idempotent review of granted claim succeeds
                res_idem = await client.post(
                    "/api/oversight/claims/clm_competing_winner/review",
                    json={"action": "grant_with_proof", "proof_reference": "ASIC business extract doc_999", "confirmed": True},
                    headers=headers,
                )
                assert res_idem.status_code == 200
                assert res_idem.json()["idempotent"] is True
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_cf04_support_message_concurrency_and_specialised_closure():
    """Test CF-04: Support message identity, concurrency race prevention, and positive evidence closure safeguards."""
    async def _test():
        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "testpass"

        mock_threads = _MockCollection(rows=[
            {
                "case_id": "sup_reply_concurrency",
                "category": "general_inquiry",
                "status": "open",
                "sender_email": "client@example.com",
                "messages": [
                    {"sender": "customer", "text": "Can I book a session?", "created_at": "2026-10-19T00:00:00Z"}
                ],
            },
            {
                "case_id": "sup_delist_missing_trainer",
                "category": "delisting_request",
                "status": "open",
                "trainer_id": "trn_missing_nonexistent",
                "sender_email": "delist@trainer.com",
                "messages": [{"sender": "customer", "text": "Delist me"}],
            },
            {
                "case_id": "sup_delist_active_trainer",
                "category": "delisting_request",
                "status": "open",
                "trainer_id": "trn_active_listing",
                "sender_email": "delist@trainer.com",
                "messages": [{"sender": "customer", "text": "Delist me"}],
            },
            {
                "case_id": "sup_delist_completed",
                "category": "delisting_request",
                "status": "open",
                "trainer_id": "trn_delisted_listing",
                "sender_email": "delist@trainer.com",
                "messages": [{"sender": "customer", "text": "Delist me"}],
            },
            {
                "case_id": "sup_privacy_unprocessed",
                "category": "privacy_request",
                "status": "open",
                "sender_email": "privacy@user.com",
                "privacy_processed": False,
                "messages": [{"sender": "customer", "text": "Delete my data"}],
            },
        ])
        mock_trainers = _MockCollection(rows=[
            {
                "id": "trn_active_listing",
                "name": "Active Trainer",
                "published": True,
                "is_active": True,
            },
            {
                "id": "trn_delisted_listing",
                "name": "Delisted Trainer",
                "published": False,
                "is_active": False,
            },
        ])

        mock_db = _MockDB(
            support_threads=mock_threads,
            trainers=mock_trainers,
            audit_log=_MockCollection(),
        )
        server.db = mock_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = {"x-admin-pass": "testpass"}

                # 1. Reply message stability: unique message_id and atomic positional update
                with patch("services.notifications.notify_support_reply", new_callable=AsyncMock) as mock_send:
                    mock_send.return_value = {"status": "sent", "id": "resend_msg_001"}
                    res_rep = await client.post(
                        "/api/oversight/support/threads/sup_reply_concurrency/reply",
                        json={"reply_text": "Hello, thank you for contacting us.", "mark_status": "awaiting_customer_reply"},
                        headers=headers,
                    )
                    assert res_rep.status_code == 200
                    assert res_rep.json()["dispatched"] is True
                    assert "message_id" in res_rep.json()

                    thread_after = await mock_threads.find_one({"case_id": "sup_reply_concurrency"})
                    assert len(thread_after["messages"]) == 2
                    op_msg = thread_after["messages"][1]
                    assert op_msg["sender"] == "operator"
                    assert op_msg["delivery_status"] == "accepted"
                    assert op_msg["provider_id"] == "resend_msg_001"
                    assert "message_id" in op_msg

                    # 2. Duplicate retry when previously accepted does not send twice
                    res_dup = await client.post(
                        "/api/oversight/support/threads/sup_reply_concurrency/reply",
                        json={"reply_text": "Hello, thank you for contacting us.", "mark_status": "awaiting_customer_reply"},
                        headers=headers,
                    )
                    assert res_dup.status_code == 200
                    assert res_dup.json()["duplicate"] is True

                # 3. Missing trainer record cannot certify delisting closure (422)
                res_missing = await client.post(
                    "/api/oversight/support/threads/sup_delist_missing_trainer/close",
                    json={"resolution_notes": "Trainer record was deleted manually by someone.", "confirmed": True},
                    headers=headers,
                )
                assert res_missing.status_code == 422
                assert "linked trainer record not found in directory. Missing record cannot certify delisting" in res_missing.json()["detail"]

                # 4. Active trainer listing blocks delisting closure (422)
                res_active = await client.post(
                    "/api/oversight/support/threads/sup_delist_active_trainer/close",
                    json={"resolution_notes": "Attempting to close while trainer is still live.", "confirmed": True},
                    headers=headers,
                )
                assert res_active.status_code == 422
                assert "trainer listing remains active and published" in res_active.json()["detail"]

                # 5. Unprocessed privacy request blocks closure (422)
                res_priv = await client.post(
                    "/api/oversight/support/threads/sup_privacy_unprocessed/close",
                    json={"resolution_notes": "Attempting to close without executing erasure.", "confirmed": True},
                    headers=headers,
                )
                assert res_priv.status_code == 422
                assert "privacy data erasure has not been completed" in res_priv.json()["detail"]

                # 6. Valid delisted trainer allows closure (200)
                res_delist_ok = await client.post(
                    "/api/oversight/support/threads/sup_delist_completed/close",
                    json={"resolution_notes": "Trainer confirmed delisted and unpublished from directory.", "confirmed": True},
                    headers=headers,
                )
                assert res_delist_ok.status_code == 200
                assert res_delist_ok.json()["status"] == "resolved"
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_cf05_durable_obligation_completeness_and_waiting_state():
    """Test CF-05: Durable obligation completeness, >200 failure scan, waiting state handling, and read-only zero writes."""
    async def _test():
        # 1. Generate 250 failed notification records, including an oldest event
        failed_notifs = []
        for i in range(250):
            failed_notifs.append({
                "id": f"notif_fail_{i:03d}",
                "dispatch_id": f"dsp_fail_{i:03d}",
                "kind": "client_intro",
                "target_kind": "intro",
                "target_id": f"int_{i:03d}",
                "to_email": f"trainer_{i:03d}@example.com",
                "status": "failed",
                "error": "bounce",
                "created_at": f"2026-10-01T{i%24:02d}:00:00Z",
            })

        mock_notif = _MockCollection(rows=failed_notifs)
        mock_obls = _MockCollection()
        mock_support = _MockCollection(rows=[
            {
                "case_id": "sup_waiting_case",
                "category": "general_inquiry",
                "status": "awaiting_customer_reply",
                "sender_email": "waiting_cust@example.com",
                "subject": "Waiting on pet medical history",
                "created_at": "2026-10-10T00:00:00Z",
            },
            {
                "case_id": "sup_failed_reply_case",
                "category": "complaint",
                "status": "reply_delivery_failed",
                "sender_email": "angry_cust@example.com",
                "subject": "Service complaint",
                "created_at": "2026-10-18T00:00:00Z",
            },
        ])

        mock_db = _MockDB(
            notification_events=mock_notif,
            ops_obligations=mock_obls,
            support_threads=mock_support,
        )

        # A. Verify sync includes all 250 failures (including oldest) without truncation
        synced = await ops_obligations.sync_durable_obligations(mock_db)
        synced_map = {o["obligation_id"]: o for o in synced}

        # Check oldest event (dsp_fail_000) was ingested
        assert "obligation:message:dsp_fail_000" in synced_map
        # Check newest event (dsp_fail_249) was ingested
        assert "obligation:message:dsp_fail_249" in synced_map

        # B. Waiting case tracking: status is 'waiting', base_severity is 'low', is_overdue is False
        assert "obligation:support:sup_waiting_case" in synced_map
        waiting_obl = synced_map["obligation:support:sup_waiting_case"]
        assert waiting_obl["status"] == "waiting"
        assert waiting_obl["severity"] == "low"
        assert waiting_obl["is_overdue"] is False
        assert waiting_obl["overdue_hours"] == 0.0

        # C. Failed support reply is actionable and high severity
        assert "obligation:support:sup_failed_reply_case" in synced_map
        reply_obl = synced_map["obligation:support:sup_failed_reply_case"]
        assert reply_obl["status"] in ("pending", "escalated")
        assert reply_obl["severity"] == "high"

        # D. Read-only invariant: get_active_obligation_cases with read_only=True performs zero writes
        mock_obls.inserted.clear()
        mock_obls.updated.clear()
        cases = await ops_obligations.get_active_obligation_cases(mock_db, read_only=True)
        assert len(mock_obls.inserted) == 0
        assert len(mock_obls.updated) == 0
        assert len(cases) > 100  # More than 100 cases returned without truncation!

        # E. Source query fails midway: verify existing obligations are preserved
        mock_db._collections["submissions"].find = None  # query failure
        synced_after_error = await ops_obligations.sync_durable_obligations(mock_db)
        assert len(synced_after_error) > 0

    asyncio.run(_test())


def test_cf04_adversarial_gather_concurrent_reply_dispatch():
    """Adversarial test for CF-04: simultaneous requests via asyncio.gather against reply_support_thread.
    Verifies that only one request acquires the in-flight lock, resend is called exactly once,
    and concurrent/duplicate requests are rejected or handled idempotently with zero double-dispatch."""
    async def _test():
        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "testpass"

        mock_threads = _MockCollection(rows=[
            {
                "case_id": "sup_concurrent_gather_01",
                "category": "general_inquiry",
                "status": "open",
                "sender_email": "gather_client@example.com",
                "messages": [
                    {"sender": "customer", "text": "Is training available this Saturday?"}
                ],
            }
        ])
        mock_db = _MockDB(
            support_threads=mock_threads,
            audit_log=_MockCollection(),
        )
        server.db = mock_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = {"x-admin-pass": "testpass"}

                dispatch_count = 0
                async def _delayed_mock_send(db, thread, reply_text):
                    nonlocal dispatch_count
                    dispatch_count += 1
                    await asyncio.sleep(0.05)  # simulate network transit window
                    return {"status": "sent", "id": f"resend_gather_{dispatch_count}"}

                with patch("services.notifications.notify_support_reply", side_effect=_delayed_mock_send):
                    req_payload = {
                        "reply_text": "Yes, we have a slot open at 10 AM.",
                        "mark_status": "awaiting_customer_reply",
                    }
                    tasks = [
                        client.post(
                            "/api/oversight/support/threads/sup_concurrent_gather_01/reply",
                            json=req_payload,
                            headers=headers,
                        )
                        for _ in range(5)
                    ]
                    responses = await asyncio.gather(*tasks)

                # Exactly one email dispatch must occur
                assert dispatch_count == 1

                # Exactly one successful dispatch response
                dispatched_responses = [r for r in responses if r.status_code == 200 and r.json().get("dispatched") is True]
                assert len(dispatched_responses) == 1

                # The other 4 requests must either be rejected as concurrent in-flight (409) or detected as duplicate (200, duplicate=True)
                other_responses = [r for r in responses if r is not dispatched_responses[0]]
                for r in other_responses:
                    assert r.status_code in (200, 409)
                    if r.status_code == 200:
                        assert r.json().get("duplicate") is True
                    elif r.status_code == 409:
                        assert "in progress" in r.json()["detail"].lower() or "concurrent" in r.json()["detail"].lower()

                # Verify thread only has one ops reply message added
                thread_final = await mock_threads.find_one({"case_id": "sup_concurrent_gather_01"})
                ops_messages = [m for m in thread_final["messages"] if m.get("sender") == "operator"]
                assert len(ops_messages) == 1
                assert thread_final.get("reply_dispatching") is not True
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


def test_cf05_adversarial_scale_zero_omissions():
    """Adversarial test for CF-05: >1,000 cases verification demonstrating that unbounded scans (to_list(None))
    and chronological sorting ensure complete zero-omission obligation coverage without silent truncation."""
    async def _test():
        # Generate 1,005 notification failure events
        failed_notifs = []
        for i in range(1005):
            failed_notifs.append({
                "id": f"notif_scale_{i:04d}",
                "dispatch_id": f"dsp_scale_{i:04d}",
                "status": "failed",
                "error": "Resend API 429 Rate Limit",
                "attempt": 3,
                "created_at": f"2026-10-15T{i // 3600:02d}:{(i % 3600) // 60:02d}:{i % 60:02d}Z",
            })

        # Generate 1,005 held submissions
        held_subs = []
        for i in range(1005):
            held_subs.append({
                "id": f"sub_scale_{i:04d}",
                "name": f"Trainer Scale {i}",
                "email": f"trainer_{i}@example.com",
                "status": "held",
                "source_evidence_url": f"https://trainer{i}.com.au",
                "created_at": f"2026-10-16T{i // 3600:02d}:{(i % 3600) // 60:02d}:{i % 60:02d}Z",
            })

        mock_notif = _MockCollection(rows=failed_notifs)
        mock_subs = _MockCollection(rows=held_subs)
        mock_obls = _MockCollection()

        mock_db = _MockDB(
            notification_events=mock_notif,
            submissions=mock_subs,
            ops_obligations=mock_obls,
        )

        # Ingestion across all 2,010 items
        synced = await ops_obligations.sync_durable_obligations(mock_db)
        synced_map = {o["obligation_id"]: o for o in synced}

        # Verify complete coverage without 500 or 1000 limit truncation
        assert "obligation:message:dsp_scale_0000" in synced_map
        assert "obligation:submission:sub_scale_0000" in synced_map
        assert "obligation:message:dsp_scale_0500" in synced_map
        assert "obligation:submission:sub_scale_0500" in synced_map
        assert "obligation:message:dsp_scale_1000" in synced_map
        assert "obligation:submission:sub_scale_1000" in synced_map
        assert "obligation:message:dsp_scale_1004" in synced_map
        assert "obligation:submission:sub_scale_1004" in synced_map

        # Total synced must equal exactly 2,010 items (zero silent omissions)
        assert len(synced) == 2010

        # Read-only active obligation retrieval must also return all 2,010 items
        active_cases = await ops_obligations.get_active_obligation_cases(mock_db, read_only=True)
        assert len(active_cases) == 2010

    asyncio.run(_test())


def test_cf02_strict_dedup_no_fuzzy_overwrite():
    """Adversarial test for CF-02: verify that SequenceMatcher 0.8 fuzzy name matching is removed
    and cannot authorise overwriting another business record. Non-matching ABN with fuzzy name similarity
    creates a distinct trainer record instead of overwriting existing business."""
    async def _test():
        orig_db = server.db
        orig_pass = os.environ.get("ADMIN_PASS")
        os.environ["ADMIN_PASS"] = "testpass"

        # Existing trainer with ABN 11111111111
        mock_trainers = _MockCollection(rows=[
            {
                "id": "trn_melb_k9_existing",
                "name": "Melbourne K9 Training Academy",
                "email": "contact@melbournek9.com.au",
                "abn": "11111111111",
                "abn_verified": True,
                "published": True,
                "is_active": True,
                "via_submission_id": "sub_orig_001",
            }
        ])

        # New submission with highly similar name (~0.96 similarity ratio) but DIFFERENT ABN
        sub_id = "sub_fuzzy_name_diff_abn"
        mock_subs = _MockCollection(rows=[
            {
                "id": sub_id,
                "name": "Melbourne K9 Training Academi",  # 1 character typo -> ~0.96 ratio
                "email": "different@k9academy.com.au",
                "phone": "+61411222333",
                "website": "k9academy.com.au",
                "abn": "22222222222",  # Different ABN!
                "abn_verified": True,
                "source_evidence_url": "https://k9academy.com.au",
                "status": "held",
                "consent_public_listing": True,
                "consent_information_accuracy": True,
            }
        ])

        mock_db = _MockDB(
            submissions=mock_subs,
            trainers=mock_trainers,
            audit_log=_MockCollection(),
        )
        server.db = mock_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = {"x-admin-pass": "testpass"}

                # Approve the submission
                res = await client.post(
                    f"/api/oversight/submissions/{sub_id}/review",
                    json={"action": "approve", "confirmed": True},
                    headers=headers,
                )
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "published"
                new_trainer_id = data["trainer_id"]

                # INVARIANT: Must NOT overwrite the existing trainer trn_melb_k9_existing!
                assert new_trainer_id != "trn_melb_k9_existing"

                # Check existing trainer was NOT modified
                orig_trainer = await mock_trainers.find_one({"id": "trn_melb_k9_existing"})
                assert orig_trainer["name"] == "Melbourne K9 Training Academy"
                assert orig_trainer["abn"] == "11111111111"
                assert orig_trainer["email"] == "contact@melbournek9.com.au"

                # Check new distinct trainer was inserted
                new_trainer = await mock_trainers.find_one({"id": new_trainer_id})
                assert new_trainer["name"] == "Melbourne K9 Training Academi"
                assert new_trainer["abn"] == "22222222222"
                assert new_trainer["via_submission_id"] == sub_id
                # Check canonical schema and capabilities
                assert "capabilities" in new_trainer
                assert new_trainer["published"] is True
        finally:
            server.db = orig_db
            if orig_pass:
                os.environ["ADMIN_PASS"] = orig_pass
            else:
                os.environ.pop("ADMIN_PASS", None)

    asyncio.run(_test())


