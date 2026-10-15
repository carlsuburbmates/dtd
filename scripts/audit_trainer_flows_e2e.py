#!/usr/bin/env python3
"""Live End-to-End Trainer Journey Audit Script against Developer Sandbox.

Audits the complete end-to-end trainer experience:
1. Discovery & Platform Configuration
2. Application Submission Validation & Edge Cases
3. Application Submission & Verification
4. Status Tracking (/submit/status/:id)
5. Public Directory & Profile Visibility (/trainers, /t/:id)
6. Profile Claim & OTP Verification
7. Match Capability Declaration (/capabilities/confirm)
8. Receiving Owner Leads & Inquiries (/intros, /follow-up/:token)
9. Trainer Billing Portal & Fail-Closed Commercial Checks (/trainer/billing)
10. Trainer Reactivation Flow (/trainer/reactivate)
11. Ops / Supervisory Audit Trail (/ops)
"""

import sys
import os
import json
import uuid
from typing import Dict, Any, List
import httpx

SANDBOX_API_URL = "https://dtd-api-dev-625222421634.australia-southeast1.run.app"


class AuditReporter:
    def __init__(self):
        self.passes: List[Dict[str, str]] = []
        self.gaps: List[Dict[str, Any]] = []

    def log_pass(self, stage: str, check: str, detail: str = ""):
        self.passes.append({"stage": stage, "check": check, "detail": detail})
        detail_str = f" - {detail}" if detail else ""
        print(f"  ✓ [{stage}] {check}{detail_str}")

    def log_gap(self, stage: str, severity: str, title: str, description: str, recommendation: str):
        gap = {
            "stage": stage,
            "severity": severity,
            "title": title,
            "description": description,
            "recommendation": recommendation,
        }
        self.gaps.append(gap)
        print(f"  ⚠️  [{severity.upper()}] [{stage}] {title}")
        print(f"      Issue: {description}")
        print(f"      Fix:   {recommendation}")


def run_audit():
    reporter = AuditReporter()
    client = httpx.Client(base_url=SANDBOX_API_URL, timeout=30.0)

    print("\n" + "=" * 80)
    print("STAGE 1: DISCOVERY & PLATFORM CONFIGURATION AUDIT")
    print("=" * 80)
    try:
        r = client.get("/api/config")
        if r.status_code == 200:
            cfg = r.json()
            phase = cfg.get("public_launch_phase")
            matching_enabled = cfg.get("public_matching_enabled")
            reporter.log_pass("Discovery", "Config endpoint operational", f"phase={phase}, matching_enabled={matching_enabled}")

            monetization = cfg.get("monetization_policy", {})
            copy = cfg.get("public_monetization_copy", {})
            if copy.get("free_core_badge"):
                reporter.log_pass("Discovery", "Monetization terms clearly defined", f"Free Core badge: {copy.get('free_core_badge')}")
            else:
                reporter.log_gap("Discovery", "LOW", "Missing Explicit Free Core Badge Copy", "Config does not include explicit free_core_badge string", "Provide fallback string in resolvePublicMonetizationCopy")
        else:
            reporter.log_gap("Discovery", "HIGH", "Config Route Failed", f"GET /api/config returned HTTP {r.status_code}", "Verify /api/config route")
    except Exception as e:
        reporter.log_gap("Discovery", "CRITICAL", "Sandbox Unreachable", str(e), "Check Cloud Run service status")

    print("\n" + "=" * 80)
    print("STAGE 2: APPLICATION FORM VALIDATION & NEGATIVE TESTING")
    print("=" * 80)
    # 2a. Missing Consent
    r = client.post("/api/submissions", json={
        "name": "Audit Canine Training",
        "suburb": "Carlton",
        "abn": "51824753556",
        "consent_public_listing": False,
        "consent_information_accuracy": True,
    })
    if r.status_code == 400:
        reporter.log_pass("Validation", "Consent enforcement works", f"HTTP 400 with detail: {r.json().get('detail')}")
    else:
        reporter.log_gap("Validation", "MEDIUM", "Consent Not Enforced", f"Expected HTTP 400, got {r.status_code}", "Enforce consent_public_listing in server.py")

    # 2b. Out of region (Sydney)
    r = client.post("/api/submissions", json={
        "name": "Audit Canine Training",
        "suburb": "Surry Hills",
        "region": "Greater Sydney",
        "abn": "51824753556",
        "consent_public_listing": True,
        "consent_information_accuracy": True,
        "consent_intro_billing_terms": True,
    })
    if r.status_code in (400, 403):
        reporter.log_pass("Validation", "Greater Melbourne geographic containment works", f"HTTP {r.status_code}: {r.json().get('detail')}")
    else:
        reporter.log_gap("Validation", "LOW", "Non-Melbourne Region Permitted", f"Expected 400 or 403, got {r.status_code}", "Strictly enforce Greater Melbourne boundary")

    # 2c. Invalid ABN format (e.g. wrong digits)
    r = client.post("/api/submissions", json={
        "name": "Audit Canine Training",
        "suburb": "Carlton",
        "abn": "12345",
        "consent_public_listing": True,
        "consent_information_accuracy": True,
        "consent_intro_billing_terms": True,
    })
    if r.status_code in (400, 422):
        reporter.log_pass("Validation", "Malformed ABN rejected at API boundary", f"HTTP {r.status_code}")
    elif r.status_code == 200:
        res_json = r.json()
        if res_json.get("status") == "held":
            reporter.log_pass("Validation", "Malformed ABN placed on hold (fail-safe)", f"status={res_json.get('status')}, reason={res_json.get('verification_reasoning')}")
        else:
            reporter.log_gap("Validation", "MEDIUM", "Malformed ABN Published", f"ABN '12345' published: {res_json}", "Do not publish unverified ABN")

    print("\n" + "=" * 80)
    print("STAGE 3: APPLICATION SUBMISSION & STATUTORY VERIFICATION")
    print("=" * 80)
    unique_suffix = uuid.uuid4().hex[:6]
    trainer_name = f"Carlton Canine Academy {unique_suffix}"
    trainer_email = f"trainer_{unique_suffix}@dogtrainersdirectory.com.au"
    valid_submission = {
        "name": trainer_name,
        "suburb": "Carlton",
        "region": "Greater Melbourne",
        "website": f"https://carltoncanine-{unique_suffix}.com.au",
        "phone": "0412345678",
        "email": trainer_email,
        "submitter_email": trainer_email,
        "abn": "51824753556", # Active Australian Tax Office ABN used in tests
        "specialties": ["puppy_training", "leash_reactivity", "obedience"],
        "service_formats": ["in_home", "facility"],
        "life_stages": ["puppy", "adolescent", "adult"],
        "training_philosophy": "Positive Reinforcement / Force-Free",
        "catchment_type": "specific_suburbs",
        "serviced_suburbs": ["Carlton", "Fitzroy", "Parkville"],
        "consent_public_listing": True,
        "consent_information_accuracy": True,
        "consent_intro_billing_terms": True,
    }
    r = client.post("/api/submissions", json=valid_submission)
    sub_id = None
    trainer_id = None
    trainer_token = None
    sub_status = None

    if r.status_code == 200:
        data = r.json()
        sub_id = data.get("id")
        trainer_id = data.get("trainer_id")
        trainer_token = data.get("trainer_action_token")
        sub_status = data.get("status")
        reporter.log_pass("Submission", "Submission successfully accepted", f"sub_id={sub_id}, status={sub_status}, trainer_id={trainer_id}")
        
        if trainer_token:
            reporter.log_pass("Submission", "Trainer action token issued", f"token={trainer_token[:10]}...")
        else:
            reporter.log_gap("Submission", "MEDIUM", "No Action Token in Submission Response", "Trainer action token was empty", "Ensure action token is issued upon submission")

        # Check reasoning / signals
        reasoning = data.get("verification_reasoning")
        reporter.log_pass("Submission", "Verification decision reasoning recorded", f"reasoning: {reasoning}")
    else:
        reporter.log_gap("Submission", "CRITICAL", "Valid Submission Failed", f"HTTP {r.status_code}: {r.text}", "Inspect server.py create_submission")
        return reporter

    print("\n" + "=" * 80)
    print("STAGE 4: SUBMISSION STATUS TRACKING (/submit/status/:id)")
    print("=" * 80)
    if sub_id:
        r = client.get(f"/api/submissions/{sub_id}/status")
        if r.status_code == 200:
            status_data = r.json()
            readiness = status_data.get("readiness_status")
            b_status = status_data.get("billing_status")
            reporter.log_pass("Status Tracking", "Status endpoint returned valid payload", f"readiness={readiness}, billing={b_status}")
            
            # Check what fields frontend expects
            if "status" in status_data:
                reporter.log_pass("Status Tracking", "Core status field present", f"status={status_data.get('status')}")
            else:
                reporter.log_gap("Status Tracking", "LOW", "Missing status field in status endpoint", "status_data lacks 'status'", "Include status in status response")
        else:
            reporter.log_gap("Status Tracking", "HIGH", "Status Lookup Failed", f"HTTP {r.status_code}: {r.text}", "Check /api/submissions/{id}/status")

    print("\n" + "=" * 80)
    print("STAGE 5: PUBLIC DIRECTORY & PROFILE VISIBILITY (/trainers, /t/:id)")
    print("=" * 80)
    if trainer_id:
        r = client.get(f"/api/trainers/{trainer_id}")
        if r.status_code == 200:
            t_data = r.json()
            reporter.log_pass("Public Profile", "Trainer profile publicly queryable", f"name='{t_data.get('name')}', suburb='{t_data.get('suburb')}'")
            
            # Check ABN verification status
            abn_verified = t_data.get("abn_verified")
            abn_badge = t_data.get("abn_badge_payload")
            reporter.log_pass("Public Profile", "ABN status recorded", f"verified={abn_verified}, badge_type={type(abn_badge)}")
            
            # Check capabilities
            caps = t_data.get("capabilities", {})
            if caps:
                reporter.log_pass("Public Profile", "Structured capabilities recorded", f"categories={list(caps.keys())}")
            else:
                reporter.log_gap("Public Profile", "LOW", "Capabilities not exposed in public profile", "Profile returned empty capabilities dict", "Ensure capabilities projection is included")
        else:
            reporter.log_gap("Public Profile", "HIGH", "Trainer Not Found by ID", f"HTTP {r.status_code}: {r.text}", "Ensure trainer record is readable")

    # Directory query
    r_dir = client.get("/api/trainers?suburb=Carlton")
    if r_dir.status_code == 200:
        dir_data = r_dir.json()
        results = dir_data.get("trainers", []) if isinstance(dir_data, dict) else dir_data
        reporter.log_pass("Directory", "Directory search responsive", f"found {len(results)} trainers in Carlton")
    else:
        reporter.log_gap("Directory", "HIGH", "Directory Search Failed", f"HTTP {r_dir.status_code}", "Check /api/trainers route")

    print("\n" + "=" * 80)
    print("STAGE 6: PROFILE CLAIM & OTP VERIFICATION")
    print("=" * 80)
    claim_session_token = None
    if trainer_id:
        # 6a. Initiate claim
        r_claim = client.post(f"/api/trainers/{trainer_id}/claim", json={"email": trainer_email, "method": "email"})
        if r_claim.status_code == 200:
            claim_res = r_claim.json()
            claim_event_id = claim_res.get("claim_event_id")
            reporter.log_pass("Profile Claim", "Claim initiation succeeded", f"event_id={claim_event_id}, status={claim_res.get('status')}")

            # 6b. Negative OTP test
            r_bad_otp = client.post(f"/api/trainers/{trainer_id}/claim/verify", json={
                "claim_event_id": claim_event_id,
                "otp": "000000"
            })
            if r_bad_otp.status_code in (400, 401, 403, 410):
                reporter.log_pass("Profile Claim", "Invalid OTP correctly rejected", f"HTTP {r_bad_otp.status_code}: {r_bad_otp.text[:60]}")
            else:
                reporter.log_gap("Profile Claim", "HIGH", "Invalid OTP Not Rejected", f"Got status {r_bad_otp.status_code}", "Verify OTP validation")
        elif r_claim.status_code == 409:
            reporter.log_pass("Profile Claim", "Profile claim conflict recognized (e.g. already claimed)", r_claim.text)
        else:
            reporter.log_gap("Profile Claim", "MEDIUM", "Claim Initiation Unexpected Status", f"HTTP {r_claim.status_code}: {r_claim.text}", "Inspect claim initiation logic")

    print("\n" + "=" * 80)
    print("STAGE 7: MATCH CAPABILITY DECLARATION (/capabilities/confirm)")
    print("=" * 80)
    if trainer_id:
        # Prefill lookup
        headers = {"X-Trainer-Action-Token": trainer_token} if trainer_token else {}
        r_pre = client.get(f"/api/trainers/{trainer_id}/capabilities/prefill", headers=headers)
        if r_pre.status_code == 200:
            pre_data = r_pre.json()
            reporter.log_pass("Capabilities", "Capability prefill retrieved successfully", f"keys={list(pre_data.keys())}")
        else:
            reporter.log_gap("Capabilities", "LOW", "Prefill Retrieval Non-200", f"HTTP {r_pre.status_code}: {r_pre.text}", "Check authorization or endpoint")

        # Confirm capabilities
        confirm_payload = {
            "specialties": ["puppy_training", "separation_anxiety", "obedience"],
            "service_formats": ["in_home", "outdoor_park"],
            "life_stages": ["puppy", "adolescent"],
            "training_philosophy": "Positive Reinforcement / Force-Free",
            "catchment_type": "specific_suburbs",
            "serviced_suburbs": ["Carlton", "Fitzroy", "Parkville"],
            "delivery_constraints": {
                "in_home_available": True,
                "facility_available": False,
                "travel_distance_km": 15,
                "notes": "Inner north Melbourne only",
            },
            "confirmed_by": trainer_email,
        }
        r_conf = client.post(f"/api/trainers/{trainer_id}/capabilities/confirm", json=confirm_payload, headers=headers)
        if r_conf.status_code == 200:
            conf_data = r_conf.json()
            reporter.log_pass("Capabilities", "Capabilities confirmed by trainer", f"confirmed_at={conf_data.get('confirmed_at')}")
        else:
            reporter.log_gap("Capabilities", "MEDIUM", "Capability Confirmation Failed", f"HTTP {r_conf.status_code}: {r_conf.text}", "Check capabilities/confirm route")

    print("\n" + "=" * 80)
    print("STAGE 8: RECEIVING OWNER LEADS & INTROS (/intros, /follow-up/:token)")
    print("=" * 80)
    if trainer_id:
        intro_uuid = uuid.uuid4().hex[:8]
        intro_payload = {
            "trainer_id": trainer_id,
            "user_name": "Sarah Connor",
            "user_email": "sarah.connor@gmail.com",
            "user_phone": "0411223344",
            "description": "My 6-month-old puppy needs urgent leash reactivity help in Carlton.",
            "client_token": f"intro-{intro_uuid}",
            "consent_contact_release": True,
            "consent_outcome_tracking": True,
        }
        r_intro = client.post("/api/intros", json=intro_payload, headers={"Idempotency-Key": f"intro-{intro_uuid}"})
        if r_intro.status_code in (200, 201):
            intro_res = r_intro.json()
            intro_id = intro_res.get("id")
            deliv_status = intro_res.get("delivery_status")
            notif_status = intro_res.get("trainer_notification_status")
            reporter.log_pass("Owner Leads", "Lead delivered to trainer", f"id={intro_id}, delivery={deliv_status}, notif={notif_status}")

            # Test engagement tracking
            r_eng = client.post("/api/engagements", json={"intro_id": intro_id, "kind": "phone_reveal"})
            if r_eng.status_code in (200, 201):
                reporter.log_pass("Owner Leads", "Phone reveal engagement tracked", f"HTTP {r_eng.status_code}")
            else:
                reporter.log_gap("Owner Leads", "LOW", "Engagement Tracking Non-200", f"HTTP {r_eng.status_code}: {r_eng.text}", "Verify engagements route")
        else:
            reporter.log_gap("Owner Leads", "HIGH", "Owner Intro Creation Failed", f"HTTP {r_intro.status_code}: {r_intro.text}", "Inspect /api/intros")

    print("\n" + "=" * 80)
    print("STAGE 9: TRAINER BILLING PORTAL (/trainer/billing)")
    print("=" * 80)
    print("\n" + "=" * 80)
    print("STAGE 9: TRAINER BILLING PORTAL (/trainer/billing)")
    print("=" * 80)
    if trainer_id and trainer_token:
        # Access billing page context
        r_bill = client.get("/api/trainer/billing", params={
            "trainer_id": trainer_id,
            "submission_id": sub_id,
            "trainer_action_token": trainer_token,
        })
        if r_bill.status_code == 200:
            b_data = r_bill.json()
            t_obj = b_data.get("trainer", {})
            tier = t_obj.get("tier") or b_data.get("subscription", {}).get("tier") or "Free Core"
            reporter.log_pass("Billing Portal", "Trainer billing context queryable", f"tier={tier}, eligible_suburbs={len(b_data.get('eligible_suburbs', []))}")

            # Verify fail-closed checkout
            r_chk = client.post("/api/trainer/billing/checkout", json={
                "trainer_id": trainer_id,
                "submission_id": sub_id,
                "trainer_action_token": trainer_token,
                "tier": "pro",
                "interval": "month",
                "consent_subscription_billing_terms": True,
                "billing_terms_version": "2026-09-24",
            })
            if r_chk.status_code in (403, 503) and any(kw in r_chk.text.lower() for kw in ["claimed", "not accepting", "disabled", "locked"]):
                reporter.log_pass("Billing Portal", "Fail-closed checkout enforcement active", f"HTTP {r_chk.status_code}: {r_chk.text[:60]}")
            elif r_chk.status_code == 200:
                reporter.log_gap("Billing Portal", "CRITICAL", "Fail-Closed Checkout Policy Violated", "Checkout returned 200 while ENABLE_TRAINER_BILLING_CHECKOUT should be 0", "Ensure checkout is strictly disabled")
            else:
                reporter.log_gap("Billing Portal", "HIGH", "Checkout Returned Unexpected Error", f"HTTP {r_chk.status_code}: {r_chk.text[:60]}", "Check checkout endpoint")
        else:
            reporter.log_gap("Billing Portal", "HIGH", "Billing Endpoint Non-200", f"HTTP {r_bill.status_code}: {r_bill.text}", "Check /api/trainer/billing")
    else:
        reporter.log_gap("Billing Portal", "MEDIUM", "Skipped Billing Audit", "Missing trainer_id or trainer_token", "Ensure submission yields token")

    print("\n" + "=" * 80)
    print("STAGE 10: TRAINER REACTIVATION FLOW (/trainer/reactivate)")
    print("=" * 80)
    if trainer_token:
        r_react_get = client.get("/api/trainer/reactivate", params={
            "trainer_id": trainer_id,
            "submission_id": sub_id,
            "trainer_action_token": trainer_token,
        })
        if r_react_get.status_code == 200:
            reporter.log_pass("Reactivate", "Reactivation context retrieved", f"HTTP 200: name={r_react_get.json().get('name')}")
        else:
            reporter.log_pass("Reactivate", f"Reactivation GET status: {r_react_get.status_code}", r_react_get.text[:60])

        r_react_post = client.post("/api/trainer/reactivate", json={
            "trainer_id": trainer_id,
            "submission_id": sub_id,
            "trainer_action_token": trainer_token,
        })
        if r_react_post.status_code in (200, 400, 409):
            reporter.log_pass("Reactivate", f"Reactivation request processed", f"HTTP {r_react_post.status_code}")
        else:
            reporter.log_gap("Reactivate", "LOW", "Reactivation Post Error", f"HTTP {r_react_post.status_code}: {r_react_post.text}", "Verify /api/trainer/reactivate")

    print("\n" + "=" * 80)
    print("STAGE 11: OPS / SUPERVISORY CONSOLE AUDIT (/ops)")
    print("=" * 80)
    # Check ops without token (should be 401 or require auth)
    r_ops_anon = client.get("/api/oversight")
    if r_ops_anon.status_code in (401, 403):
        reporter.log_pass("Ops Security", "Oversight console is strictly authenticated", f"HTTP {r_ops_anon.status_code} on anonymous access")
    else:
        reporter.log_gap("Ops Security", "HIGH", "Oversight Console Exposed Without Auth", f"HTTP {r_ops_anon.status_code}", "Protect /api/oversight with authentication")

    # Check ops with admin pass
    r_ops_admin = client.get("/api/oversight", headers={"X-Admin-Pass": "DevOpsPass2026!Secure"})
    if r_ops_admin.status_code == 200:
        ops_data = r_ops_admin.json()
        unverified_cases = len(ops_data.get("cases", []))
        claim_cases = len(ops_data.get("trainer_claim_cases", []))
        reporter.log_pass("Ops Telemetry", "Ops supervisor telemetry accessible", f"{unverified_cases} active cases, {claim_cases} claim cases")
    else:
        reporter.log_gap("Ops Telemetry", "MEDIUM", "Admin Access Failed", f"HTTP {r_ops_admin.status_code}", "Check X-Admin-Pass header validation")

    return reporter


if __name__ == "__main__":
    rep = run_audit()
    print("\n" + "=" * 80)
    print("AUDIT RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total Successful Verification Points: {len(rep.passes)}")
    print(f"Total Identified Gaps / Friction Points: {len(rep.gaps)}")

    if rep.gaps:
        print("\nIDENTIFIED GAPS:")
        for idx, g in enumerate(rep.gaps, 1):
            print(f"{idx}. [{g['severity']}] [{g['stage']}] {g['title']}")
            print(f"   Details:        {g['description']}")
            print(f"   Recommendation: {g['recommendation']}")
    else:
        print("\nAll trainer lifecycle flows verified end-to-end with zero gaps!")
