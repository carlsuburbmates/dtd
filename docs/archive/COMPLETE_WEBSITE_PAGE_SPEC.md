# Complete Website Page Spec

Date: 2026-08-30
Scope: Canonical page-level specification for the intended DTD website.

## Authority

This document is part of the canonical implementation pack.

Rules:
1. It defines the intended website and page-level behavior.
2. It aligns with `docs/strategy/DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md` and `docs/standards/DTD_PROJECT_CONTEXT.md`.
3. If a lower-authority doc conflicts with this page spec, this page spec governs for page-level implementation.

## Locked Website Posture

1. Product: `DTD` / `Dog Trainers Directory`
2. Launch posture: `live_matching_and_discovery` (Open directory + Diagnostic matching)
3. Supply foundation: accepted attributable launch profiles plus trainer submissions; licensed-feed expansion is a separately gated post-launch workflow
4. Commercial model: Flat SaaS Storefront ($19/mo Pro) + Scarcity Suburb Sponsorship ($39/mo, $199/mo)
5. Claim model: Self-serve automated SMS/Email OTP verification
6. `/ops` is an Exception-Handling and Throughput Cockpit (10–15 mins/week)
7. `Database = truth`, `audit_log = decision trail`

## Global Site Contract

Every public-facing page must satisfy these rules:
1. Shared header (`<PublicHeader />`) and footer (`<PublicFooter />`)
2. Clear primary action consistent with page intent
3. Fully responsive mobile and desktop layout
4. Legal links (Terms, Privacy) in footer
5. No dead buttons or dead links
6. Clear customer-facing language without internal jargon or raw metrics

## Global Public-Page Operating Rules

### One Page, One Job
Every public page must have:
1. One primary purpose
2. One dominant action
3. One supporting proof, standard, or boundary block
4. One clear secondary route at most

### CTA Hierarchy
Every public page must follow this hierarchy:
1. One primary CTA (`btn-primary` or `btn-accent`)
2. One clearly secondary CTA (`btn-ghost`)
3. Optional tertiary text link

### Public-Language Guardrail
Do not use internal system terms on public surfaces:
- Strip `Scoring…`, `confidence · 85%`, `follow-up spam`, `activation state`, `autonomous review`.
- Use customer-facing terms: "Verified identity", "Reviewed listing", "Consultation enquiry".

### Copy Discipline
- Write in **Australian English** (`behavioural`, `specialise`, `programme`).
- Marketing H1/H2 headings must **not end with trailing periods (`.`) or question marks (`?`)**.
- Paragraphs must remain concise and high-signal.

---

## Route Specifications

### 1. `/` (Home)
* **Purpose:** High-impact introduction to Melbourne's dog trainer network, quick diagnostic intake, and trainer acquisition entry.
* **Required Sections:**
  1. Hero with Melbourne value proposition and dual CTAs: `[Find local trainers]` & `[Join as trainer]`.
  2. Diagnostic Match Wizard intake (dog age, issue, suburb, in-home vs facility).
  3. Trust & verification pillars.
  4. The First Leash puppy guide preview card.
* **Behavior:** Directly connects owners to matching trainers; captures attribution.

### 2. `/trainers` (All-Melbourne Directory)
* **Purpose:** Open directory of all Greater Melbourne trainers with filters and tiered ranking.
* **Required Controls:**
  1. Suburb selector and specialty filters (Puppy, Reactivity, Obedience, In-Home).
  2. Tiered results list (Melbourne-Wide Sponsors $\rightarrow$ Regional Sponsors $\rightarrow$ Pro Verified $\rightarrow$ Claimed Free $\rightarrow$ Ingested Base).
  3. Header CTA to `/submit` for trainers.

### 3. `/melbourne/:suburb` (Suburb Landing Hub)
* **Purpose:** Hyper-local suburb hub for SEO and targeted discovery.
* **Required Sections:**
  1. Suburb title (e.g. "Dog Trainers in Richmond").
  2. Top Spotlight: Pinned Suburb Sponsors (max 2, 50/50 round-robin rotation).
  3. Mobile Spotlight: Melbourne-Wide Mobile Specialists servicing that suburb.
  4. Community Choice: Highest-rated local trainer based on verified reviews.
  5. Local Pro & Claimed trainers covering the suburb.
  6. Discrete trainer sponsorship prompt if vacancies exist (0/2 or 1/2).

### 4. `/t/:slug` and `/t/:id` (Dedicated Trainer Business Profile)
* **Purpose:** High-credibility standalone business storefront for trainers.
* **Required Sections:**
  1. Header: Business name, suburb, gold "Verified Pro" badge (if Pro), and rating summary.
  2. Bio, training philosophy, specialty tags, and service formats.
  3. **For Pro Trainers:** Live calendar/booking embed, transformation gallery, dofollow SEO website link, ad removal.
  4. **For Unclaimed Profiles:** "Is this your business? Claim profile" banner $\rightarrow$ opens OTP Claim Modal.
  5. Direct Consultation Enquiry form (with masked email relay).

### 5. `/pricing` (Pricing & Plans)
* **Purpose:** Transparent, all-inclusive flat SaaS pricing for trainers.
* **Required Sections:**
  1. Tier comparison table: Base Free ($0), Claimed Free ($0), Pro Storefront ($19/mo inc. GST), Suburb Sponsor ($39/mo inc. GST), Melbourne-Wide ($199/mo inc. GST).
  2. 14-day (monthly) and 30-day (annual) 100% money-back guarantee explanation.
  3. Explicit non-guarantee statement (DTD connects owners and trainers; outcome results depend on trainer and owner).

### 6. `/how-it-works` (How It Works)
* **Purpose:** Clear guide for both dog owners and trainers.
* **Required Sections:**
  1. How Owners Find Help: Diagnostic matching and suburb discovery.
  2. How Verification Works: Manual ABN checks, method transparency, and review validation.
  3. How Trainers Grow: Claiming profiles, Pro storefronts, and direct client leads without commission fees.

### 7. `/trust` (Trust & Ethical Standards)
* **Purpose:** Code of conduct and verification standards.
* **Required Sections:**
  1. Verification criteria (ABN, credentials, insurance check).
  2. Method transparency requirements (Positive Reinforcement, Balanced).
  3. Privacy & contact consent rules.
  4. Quality guarantee & incident reporting path.

### 8. `/faq` (Frequently Asked Questions)
* **Required Answers:**
  1. How diagnostic matching works.
  2. Free vs. Pro trainer features.
  3. Suburb sponsorship availability and caps.
  4. Refund policy and cancellation terms.

### 9. `/contact` (Support & Inquiries)
* **Purpose:** Canonical support route.
* **Required Details:**
  1. Direct support mailbox `info@dogtrainersdirectory.com.au`.
  2. Quick link to FAQ and trainer claim help.

### 10. `/the-first-leash` (The First Leash Puppy Guide)
* **Purpose:** Free educational resource for new puppy owners.
* **Required Sections:**
  1. Course overview and module breakdown.
  2. Responsive video player and structured MDX lesson viewer.
  3. Interactive progress tracking and celebration confetti.

### 11. `/privacy` & `/terms` (Legal & Regulatory Compliance)
* **Purpose:** Australian statutory compliance.
* **Required Sections:**
  1. Australian Consumer Law statutory guarantees.
  2. Australian Privacy Principles (APPs) public data disclosure and 1-click delisting mechanism.
  3. Spam Act 2003 sender identification.

### 12. `/ops` (Operations Console)
* **Purpose:** Passcode-gated exception-handling and throughput cockpit.
* **Required Sections:**
  1. Overview & Posture.
  2. Pipeline Throughput (Demand $\rightarrow$ Supply $\rightarrow$ Matches $\rightarrow$ Outcomes $\rightarrow$ Revenue).
  3. Work Queue (1-Click Claim Approvals, Ingestion Anomalies, Stalled Intros).
  4. Suburb Inventory & Sponsorship Matrix (~300 suburbs, vacancy tracking, waitlist queue).
  5. Revenue, Billing & 1-Click Refunds.
  6. Outbound Delivery Log (Resend / Twilio stream).
  7. Immutable Audit Trail (`db.audit_log`).
