# DTD Operations Console Spec

**File:** `docs/governance/OPERATIONS_CONSOLE_SPEC.md`  
**Project:** Dog Trainers Directory / DTD  
**Purpose:** Canonical product spec for the owner-facing Operations Console at `/ops`.  
**Status:** Canonical implementation spec
**Last aligned:** 2026-08-30

---

## 1. Why This Exists

DTD is an automation-first platform for Greater Melbourne. The Operations Console (`/ops`) provides a single, readable, and decisive cockpit for the owner to monitor throughput, resolve exceptions, and manage suburb inventory in **10–15 minutes per week** without needing manual database access or external admin tools.

This document defines:
1. What `/ops` is for and how it functions as an exception-handling cockpit
2. The core sections and work surfaces it contains
3. The 1-click bounded actions available to the operator
4. The data contracts and evidence streams it consumes

---

## 2. Locked Product Role

`/ops` is the **Operations Cockpit**.

It is:
1. Passcode-gated (`ADMIN_PASS`)
2. Workflow and decision-led (not raw charts)
3. Exception-driven (surfacing items only when automated thresholds require human sign-off)
4. A transparent window into autonomous background operations

It is **not**:
1. A manual matchmaking desk (intros are matched and delivered autonomously)
2. A manual invoicing dashboard (Stripe handles subscriptions and recurring billing automatically)
3. An unrestricted admin CRUD console

---

## 3. The 7 Core Console Sections

### 3.1 Overview & Posture
* **Purpose:** 5-second check on platform health, live status, and urgent items.
* **Displays:**
  - Platform Status: `Live & Operating (Melbourne)`
  - Active Supply: Total Ingested (Tier 0), Claimed (Tier 1), Pro (Tier 2), Suburb Sponsored (Tier 3).
  - Financial Health: Active MRR, Last 30-Day Revenue, Failed Payments.
  - Active Work Queue Items: Count of pending tickets requiring 1-click review.

### 3.2 Pipeline Throughput
* **Purpose:** Monitor live conversion throughput from discovery to revenue.
* **Funnel Flow:**
  $$	ext{Demand (Searches / Intakes)} \longrightarrow 	ext{Supply (Profiles)} \longrightarrow 	ext{Matches (Inquiries)} \longrightarrow 	ext{Outcomes (Hires)} \longrightarrow 	ext{Revenue (MRR)}$$
* **Metrics:** 7-day intakes, active consultation deliveries, T+7 confirmed hires, and conversion rates.

### 3.3 Work Queue (1-Click Exception Triage)
* **Purpose:** Presents flagged items as decisive action cards:
  1. **Unmatched Claim Cards:** Shows claimant email/phone + attached ABN proof document preview $\rightarrow$ `[Approve Claim (1-Click)]` | `[Reject with Reason]`.
  2. **Ingestion Anomaly Cards:** Missing/revoked supplier authority, source degradation, or conflicting identity data between approved sources $\rightarrow$ `[Hold]` | `[Merge]` | `[Delist]`.
  3. **Incident Report Cards:** Owner or trainer misconduct reports $\rightarrow$ `[Revoke Pro Badge]` | `[Dismiss]`.

### 3.4 Suburb Inventory & Sponsorship Matrix
* **Purpose:** Control and visibility over Melbourne's ~300 suburbs and 600 sponsorship slots.
* **Displays:**
  - Live table of suburbs: Suburb Name, Active Sponsors (0/2, 1/2, 2/2), Monthly Revenue, Waitlist Count, 30-Day Search Demand.
  - Filters: `Sold Out (2/2)`, `1 Spot Remaining (1/2)`, `High Demand / 0 Sponsors`.
  - Manual 1-click slot release or waitlist trigger.

### 3.5 Revenue, Billing & 1-Click Refunds
* **Purpose:** Direct financial control integrated with Stripe.
* **Controls:**
  - **1-Click Refund Tool:** Enter Trainer ID $\rightarrow$ Select Charge $\rightarrow$ Click `[Refund & Cancel]`. Automatically executes `stripe.Refund.create()`, logs an audit record, and downgrades the tier.
  - **1-Click VIP Founding Partner Grant:** Search Trainer $\rightarrow$ Select Duration (6mo / 1yr) $\rightarrow$ Click `[Grant Pro Tier]`.

### 3.6 Outbound Communication & Delivery Log
* **Purpose:** Complete visibility over automated Resend emails and Twilio SMS.
* **Displays:** Live stream of sent lead alerts, OTP codes, match summaries, T+7 follow-ups, and review invitations with delivery and open statuses.

### 3.7 Immutable Audit Trail (`db.audit_log`)
* **Purpose:** Unalterable system ledger.
* **Displays:** Searchable feed of every database update, tier change, Stripe webhook event, and operator action with `before` and `after` snapshots.

---

## 4. Operator Responsibility Boundaries

1. **Automated System:** Runs the 6 background engines, processes subscriptions, dispatches emails/SMS, and scores diagnostic matches autonomously.
2. **Layer 1 (Normal Ops - The Single Operator):** Reviews `/ops` 1–2 times weekly, clears pending claim tickets with 1-click approvals, and monitors revenue throughput.
3. **Layer 2 (Technical-Owner Mode):** Modifies system configuration, deploys updates, or rotates API keys.
